"""
taa.evidence — out-of-sample evidence. The part of the desk that can fail.

WHAT IS BEING MEASURED
------------------------------------------------------------------------------
The question is not whether a signal fits. Everything fits. The question is
whether a forecast built only from information available at the forecast origin
beats the simplest possible alternative, which is to assume next month looks
like the average of every month so far.

R2_oos follows Campbell and Thompson (2008), "Predicting excess stock returns
out of sample: can anything beat the historical average?", RFS 21(4) 1509-1531,
and Welch and Goyal (2008), "A comprehensive look at the empirical performance
of equity premium prediction", RFS 21(4) 1455-1508:

    R2_oos = 1 - sum_T (y_T - yhat_T)^2 / sum_T (y_T - ybar_T)^2

where ybar_T is the mean of the realised series through T-1 and nothing later,
and yhat_T comes from a regression estimated on data through T-1 and nothing
later. A negative R2_oos means the signal is worse than the historical average.
In this literature most of them are, and the sign of that number is reported
here with the same prominence whichever way it falls.

Clark and West (2007), "Approximately normal tests for equal predictive accuracy
in nested models", Journal of Econometrics 138(1) 291-311, note that under the
null of no predictability the larger model still estimates a slope, and that
estimation noise pushes its MSPE above the benchmark's. Their adjustment removes
that term:

    f_T = (y_T - ybar_T)^2 - [ (y_T - yhat_T)^2 - (ybar_T - yhat_T)^2 ]

and the t-statistic on the mean of f is compared to a one-sided standard normal.
A positive Clark-West t with a negative R2_oos is the common outcome and means
the model may contain a signal too weak to pay for the cost of estimating it.
It is not a licence to trade.

TIMING, WHICH IS THE WHOLE THING
------------------------------------------------------------------------------
y_T is the return earned during month T. x is indexed by the month end at which
it is known, so the predictor used for y_T is x_{T-1}. The training set at
forecast origin T-1 is every pair (x_{s-1}, y_s) with s <= T-1. Every one of
those was on a screen at the close of month T-1. The benchmark mean at T is
formed from y_s for s <= T-1 on the same rule. tests/check_quant.py plants a
synthetic series on which the expanding mean and the full-sample mean differ by
a known amount and asserts this module uses the former.

TOTAL RETURNS, EXCESS RETURNS, AND ONE TRAP
------------------------------------------------------------------------------
The table is computed on returns in excess of the cash line. The trap it avoids
is worth stating because it would have produced a flattering headline. The cash
line's monthly total return is the bill rate, which is close to deterministic
month to month; regressing it on any persistent predictor, the bill yield most
of all, produces a large positive R2_oos that measures the persistence of the
front end and nothing else. Reported as a predictability result it would be
false. Cash is therefore reported separately, in total-return terms, with that
statement attached.
"""

from __future__ import annotations

import datetime as _dt

import numpy as np
import pandas as pd

from . import config, pitdata, signals

# Degrees of freedom belonging to the evaluation rather than to the signals.
EVAL_PARAMS = {
    "min_train_obs": 60,       # pairs required before the first OOS forecast
    "var_min_train_obs": 60,   # same, for the variance regressions
    "har_lags_m": (1, 3, 12),  # Corsi (2009) heterogeneous autoregressive lags
    "vol_ewma_halflife_m": 6,
}

CASH = "cash"
RISKY = [ln for ln in config.LINES if ln != CASH]


# --------------------------------------------------------------------------
# Primitives
# --------------------------------------------------------------------------
def expanding_mean_benchmark(y: pd.Series) -> pd.Series:
    """
    The Campbell-Thompson benchmark forecast: at target date T, the mean of the
    realised series through T-1. The shift is the entire content of this
    function and it is what tests/check_quant.py checks.
    """
    return y.shift(1).expanding(min_periods=1).mean()


# A predictor whose training-sample standard deviation is below this is a
# constant contaminated by floating-point noise, not a predictor. It is not a
# tuning parameter: real signals here live at 1e-2 to 1e-1 and the case this
# catches lives at 1e-17.
DEGENERATE_SD = 1e-8


def expanding_ols_forecast(y: pd.Series, x_lagged: pd.Series,
                           min_train: int) -> pd.DataFrame:
    """
    One-regressor expanding-window OLS, refitted at every date, forecasting y_T
    from x_{T-1} using only pairs whose target date is strictly before T.

    Returned columns: y, x, n_train, alpha, beta, forecast_raw, forecast,
    truncated, degenerate.

    TWO GUARDS, BOTH DISCLOSED
    --------------------------------------------------------------------------
    Degeneracy. Where the training sample's predictor has essentially no
    variation the regression is not identified and no forecast is produced. This
    was added after the commodities carry signal produced a forecast of minus
    fifty thousand percent for one month: the DBC distribution yield is exactly
    zero for years at a time, so the fit was regressing excess returns on
    floating-point rounding noise and returned a slope of minus fifty-four
    thousand. That is an artifact of arithmetic, not a finding, and reporting it
    as a result would have been reporting a bug.

    Truncation. The forecast is capped to the range of the target observed in
    the training window, following the restriction philosophy of Campbell and
    Thompson (2008), who truncate the equity premium forecast from below.
    An unrestricted forecast from an extrapolated regressor can leave the space
    of returns any asset has ever produced, and Welch and Goyal (2008) observe
    that such forecasts are a large part of why unrestricted models fail. Both
    the truncated and the untruncated series are returned, R2_oos is reported on
    both, and the difference between them is shown rather than absorbed.
    """
    df = pd.DataFrame({"y": y, "x": x_lagged}).dropna()
    cols = ["y", "x", "n_train", "alpha", "beta", "forecast_raw", "forecast",
            "truncated", "degenerate"]
    if df.empty:
        return pd.DataFrame(columns=cols)

    d = df.assign(xy=df["x"] * df["y"], xx=df["x"] ** 2, one=1.0)
    cum = d[["one", "x", "y", "xy", "xx"]].cumsum().shift(1)   # through T-1 only
    n = cum["one"]
    sx, sy, sxy, sxx = cum["x"], cum["y"], cum["xy"], cum["xx"]

    with np.errstate(invalid="ignore", divide="ignore"):
        ssx = sxx - sx * sx / n                       # training sum of squares
        sd_x = np.sqrt((ssx / n).clip(lower=0.0))
        beta = (sxy - sx * sy / n) / ssx
        alpha = sy / n - beta * sx / n

    degenerate = ~(sd_x > DEGENERATE_SD)
    ok = (n >= min_train) & ~degenerate & np.isfinite(beta) & np.isfinite(alpha)
    beta = beta.where(ok)
    alpha = alpha.where(ok)
    fc_raw = alpha + beta * df["x"]

    ylo = df["y"].shift(1).expanding(min_periods=1).min()
    yhi = df["y"].shift(1).expanding(min_periods=1).max()
    fc = fc_raw.clip(lower=ylo, upper=yhi)

    out = df.copy()
    out["n_train"] = n
    out["alpha"] = alpha
    out["beta"] = beta
    out["forecast_raw"] = fc_raw
    out["forecast"] = fc
    out["truncated"] = (fc_raw.notna()) & (~np.isclose(fc_raw.fillna(0), fc.fillna(0)))
    out["degenerate"] = degenerate
    return out


def r2_oos(y: pd.Series, bench: pd.Series, model: pd.Series) -> float:
    m = pd.DataFrame({"y": y, "b": bench, "f": model}).dropna()
    if len(m) < 2:
        return float("nan")
    sse_m = float(((m["y"] - m["f"]) ** 2).sum())
    sse_b = float(((m["y"] - m["b"]) ** 2).sum())
    if sse_b <= 0:
        return float("nan")
    return 1.0 - sse_m / sse_b


def clark_west(y: pd.Series, bench: pd.Series, model: pd.Series) -> dict:
    m = pd.DataFrame({"y": y, "b": bench, "f": model}).dropna()
    if len(m) < 8:
        return {"cw_mean": float("nan"), "cw_t": float("nan"), "n": int(len(m))}
    f = ((m["y"] - m["b"]) ** 2
         - ((m["y"] - m["f"]) ** 2 - (m["b"] - m["f"]) ** 2))
    n = len(f)
    se = float(f.std(ddof=1)) / np.sqrt(n)
    return {"cw_mean": float(f.mean()),
            "cw_t": float(f.mean() / se) if se > 0 else float("nan"),
            "n": int(n)}


def lo_sharpe_se(sr_period: float, n: int, periods_per_year: int = 12) -> dict:
    """
    Lo (2002), "The statistics of Sharpe ratios", FAJ 58(4) 36-52, equation 9
    under the IID assumption:  SE(SR) = sqrt((1 + SR^2/2)/n).

    The standard error is a property of the estimate, not of the strategy. At
    n = 60 monthly observations it is large enough that most differences between
    two Sharpe ratios computed on this window are not distinguishable from zero,
    which is the point of quoting it.
    """
    if n < 2 or not np.isfinite(sr_period):
        return {"sr_period": float("nan"), "se_period": float("nan"),
                "sr_ann": float("nan"), "se_ann": float("nan"), "n": int(n)}
    se = float(np.sqrt((1.0 + 0.5 * sr_period ** 2) / n))
    k = np.sqrt(periods_per_year)
    return {"sr_period": float(sr_period), "se_period": se,
            "sr_ann": float(sr_period * k), "se_ann": float(se * k),
            "t_stat": float(sr_period / se), "n": int(n)}


def max_drawdown(returns: pd.Series) -> float:
    if returns.empty:
        return float("nan")
    wealth = (1.0 + returns.fillna(0.0)).cumprod()
    return float((wealth / wealth.cummax() - 1.0).min())


def perf_summary(r: pd.Series, rf: pd.Series, label: str) -> dict:
    r = r.dropna()
    rf = rf.reindex(r.index).fillna(0.0)
    ex = r - rf
    n = len(r)
    mu_m = float(ex.mean())
    sd_m = float(ex.std(ddof=1))
    sr_m = mu_m / sd_m if sd_m > 0 else float("nan")
    lo = lo_sharpe_se(sr_m, n)
    ann_ret = float((1.0 + r).prod() ** (12.0 / n) - 1.0) if n else float("nan")
    return {
        "label": label,
        "n_months": n,
        "ann_return": ann_ret,
        "ann_vol": float(r.std(ddof=1) * np.sqrt(12)),
        "ann_excess_return": float(ex.mean() * 12),
        "sharpe_ann": lo["sr_ann"],
        "sharpe_ann_se": lo["se_ann"],
        "sharpe_t": lo.get("t_stat", float("nan")),
        "max_drawdown": max_drawdown(r),
        "start": str(r.index.min().date()) if n else None,
        "end": str(r.index.max().date()) if n else None,
    }


# --------------------------------------------------------------------------
# Panels used by the evaluation
# --------------------------------------------------------------------------
def _returns_and_signals(end_date=None):
    """
    Monthly returns and the raw signal panels, both read at one as-of date.

    The panels are read once at `end_date` rather than rebuilt at every month
    end. That is a performance shortcut and it is legitimate only because row t
    of each panel depends on nothing dated after t, which is a property of the
    construction rather than a hope about it. tests/check_quant.py verifies it
    directly by recomputing signals_as_of(t) at sampled dates and asserting the
    values match the corresponding row here. If that assertion ever fails, this
    shortcut is invalid and the walk must be rebuilt date by date.
    """
    d = pitdata._to_date(end_date or config.WINDOW_END)
    tr = signals.monthly_returns_as_of(d)
    raws = signals.signal_history(d, include_robustness=True)

    # composite predictor: signed, standardised, averaged. This is the object
    # the allocation actually uses, before the cross-sectional demean, which is
    # a construction step rather than a forecast.
    zs = {k: signals.expanding_z(v) for k, v in raws.items() if k in signals.SIGNALS}
    acc, cnt = None, None
    for k, z in zs.items():
        sgn = signals.SIGN[k] * z
        acc = sgn if acc is None else acc.add(sgn, fill_value=0.0)
        c = z.notna().astype(float)
        cnt = c if cnt is None else cnt.add(c, fill_value=0.0)
    composite = acc / cnt.replace(0.0, np.nan)

    panels = {k: signals.expanding_z(v) for k, v in raws.items()}
    panels["composite"] = composite
    return d, tr, raws, panels


def excess_returns(tr: pd.DataFrame) -> pd.DataFrame:
    """Line total return less the cash line. Cash itself is dropped."""
    return tr[RISKY].sub(tr[CASH], axis=0)


# --------------------------------------------------------------------------
# The R2_oos table
# --------------------------------------------------------------------------
def r2oos_table(end_date=None, window_only: bool = False) -> dict:
    d, tr, raws, panels = _returns_and_signals(end_date)
    ex = excess_returns(tr)
    min_train = EVAL_PARAMS["min_train_obs"]

    lo_lim = pd.Timestamp(config.WINDOW_START) if window_only else None
    hi_lim = pd.Timestamp(d)

    predictors = {k: raws[k] for k in raws}          # raw values, unstandardised
    predictors["composite"] = panels["composite"]     # already standardised

    cells, pooled = {}, {}
    for sname, panel in predictors.items():
        cells[sname] = {}
        num = den = 0.0
        cw_all = []
        for ln in RISKY:
            if ln not in panel.columns:
                continue
            y = ex[ln].dropna()
            x = panel[ln].shift(1)                    # known at T-1
            fit = expanding_ols_forecast(y, x, min_train)
            if fit.empty or fit["forecast"].notna().sum() < 8:
                cells[sname][ln] = {"r2oos": None, "n_oos": 0,
                                    "note": "insufficient history"}
                continue
            bench_full = expanding_mean_benchmark(y).reindex(fit.index)
            f = fit["forecast"]

            mask = f.notna() & bench_full.notna()
            if lo_lim is not None:
                mask &= fit.index >= lo_lim
            mask &= fit.index <= hi_lim
            yy, bb, ff = fit["y"][mask], bench_full[mask], f[mask]
            if len(yy) < 8:
                cells[sname][ln] = {"r2oos": None, "n_oos": int(len(yy)),
                                    "note": "insufficient out-of-sample months"}
                continue

            # Campbell-Thompson sign restriction: when the fitted slope
            # contradicts the sign the published evidence gives the signal,
            # fall back on the historical mean.
            prior = signals.SIGN.get(sname, 0.0)
            if sname in ("composite",):
                prior = +1.0
            if sname == "carry_dy":
                prior = +1.0
            if prior:
                wrong = np.sign(fit["beta"][mask].fillna(0.0)) != np.sign(prior)
                ff_sr = ff.where(~wrong, bb)
            else:
                ff_sr = ff

            ff_raw = fit["forecast_raw"][mask]
            r2 = r2_oos(yy, bb, ff)
            r2sr = r2_oos(yy, bb, ff_sr)
            cw = clark_west(yy, bb, ff)
            cells[sname][ln] = {
                "r2oos": r2,
                "r2oos_sign_restricted": r2sr,
                "r2oos_untruncated": r2_oos(yy, bb, ff_raw),
                "cw_t": cw["cw_t"],
                "n_oos": int(len(yy)),
                "oos_start": str(yy.index.min().date()),
                "oos_end": str(yy.index.max().date()),
                "mean_beta": float(fit["beta"][mask].mean()),
                "beta_sign_agrees_pct": float((~wrong).mean() * 100) if prior else None,
                "pct_truncated": float(fit["truncated"][mask].mean() * 100),
                "pct_degenerate": float(fit["degenerate"][mask].mean() * 100),
            }
            num += float(((yy - ff) ** 2).sum())
            den += float(((yy - bb) ** 2).sum())
            cw_all.append(pd.Series(
                ((yy - bb) ** 2 - ((yy - ff) ** 2 - (bb - ff) ** 2)).values))

        if den > 0:
            fp = pd.concat(cw_all, ignore_index=True) if cw_all else pd.Series(dtype=float)
            se = float(fp.std(ddof=1)) / np.sqrt(len(fp)) if len(fp) > 2 else float("nan")
            pooled[sname] = {
                "r2oos_pooled": 1.0 - num / den,
                "cw_t_pooled": float(fp.mean() / se) if se and se > 0 else float("nan"),
                "n_cells": sum(1 for c in cells[sname].values() if c.get("r2oos") is not None),
                "n_obs": int(len(fp)),
                "n_negative": sum(1 for c in cells[sname].values()
                                  if c.get("r2oos") is not None and c["r2oos"] < 0),
            }
        else:
            pooled[sname] = {"r2oos_pooled": None}

    # cash, reported separately and labelled
    cash_cells = {}
    for sname, panel in predictors.items():
        if CASH not in panel.columns:
            continue
        y = tr[CASH].dropna()
        fit = expanding_ols_forecast(y, panel[CASH].shift(1), min_train)
        if fit.empty or fit["forecast"].notna().sum() < 8:
            continue
        bench = expanding_mean_benchmark(y).reindex(fit.index)
        mask = fit["forecast"].notna() & bench.notna()
        if lo_lim is not None:
            mask &= fit.index >= lo_lim
        if mask.sum() < 8:
            continue
        cash_cells[sname] = {
            "r2oos_total_return": r2_oos(fit["y"][mask], bench[mask], fit["forecast"][mask]),
            "n_oos": int(mask.sum()),
        }

    return {
        "as_of": d.isoformat(),
        "sample": "study window only" if window_only else "longest available, post-warmup",
        "definition": ("R2_oos = 1 - SSE(model)/SSE(expanding historical mean); "
                       "benchmark at T uses realised returns through T-1 only"),
        "target": "monthly total return less the cash line",
        "min_train_obs": min_train,
        "cells": cells,
        "pooled": pooled,
        "cash": {
            "note": ("cash is excluded from the table above because its excess "
                     "return over itself is identically zero. Reported here on "
                     "total returns, where a large positive R2_oos measures the "
                     "month-to-month persistence of the bill rate and is not "
                     "evidence that anything tradeable has been forecast."),
            "cells": cash_cells,
        },
        "eval_params": dict(EVAL_PARAMS),
    }


# --------------------------------------------------------------------------
# Volatility, question (a): is it forecastable?
# --------------------------------------------------------------------------
def _daily_returns(end_date) -> pd.DataFrame:
    d = pitdata._to_date(end_date)
    a = pitdata.as_of(d)
    px = a.line_prices()
    return np.log(px / px.shift(1)).dropna(how="all")


def realised_variance_ann(end_date=None, lines=None) -> pd.DataFrame:
    """
    Monthly realised variance from daily log returns, annualised.

    The target is realised variance rather than the squared monthly return.
    Andersen and Bollerslev (1998), "Answering the skeptics: yes, standard
    volatility models do provide accurate forecasts", IER 39(4) 885-905, show
    the squared return is an unbiased but extremely noisy proxy for the latent
    variance, so a forecast evaluated against it scores far worse than it
    deserves. Realised variance from daily data is the standard fix and it is
    available here because the price history is daily.
    """
    d = pitdata._to_date(end_date or config.WINDOW_END)
    lr = _daily_returns(d)
    if lines is not None:
        lr = lr[lines]
    cnt = lr.resample("ME").count()
    rv_m = (lr ** 2).resample("ME").sum()        # variance realised within the month
    rv_m = rv_m.where(cnt >= 15)
    return rv_m * 12.0                           # annualised


def policy_daily_returns(end_date=None) -> pd.Series:
    """
    Daily simple return of the policy portfolio, rebalanced monthly. Monthly
    rebalancing is the modelling choice; the mandate's quarterly cycle applies
    to tactical positions, not to keeping the policy weights on target.
    """
    d = pitdata._to_date(end_date or config.WINDOW_END)
    a = pitdata.as_of(d)
    px = a.line_prices()
    r = px.pct_change().dropna(how="all")
    w = pd.Series(config.POLICY)[r.columns]
    return (r * w).sum(axis=1)


def _rank_corr(a: pd.Series, b: pd.Series) -> float:
    return float(pd.Series(a).rank().corr(pd.Series(b).rank()))


def _qlike(y: pd.Series, f: pd.Series) -> float:
    """QLIKE loss, log(f) + y/f. Lower is better. Unlike squared error it is
    scale-free in the variance and it punishes under-prediction hard, which is
    the error a risk model must not make."""
    f = f.clip(lower=1e-8)
    return float((np.log(f) + y / f).mean())


def variance_forecast_study(end_date=None) -> dict:
    """
    Is variance forecastable? Reported on three loss scales, because on this
    sample they disagree and a single number would hide that.

    Two forecasts, both estimated only on history:

      EWMA   exponentially weighted mean of past realised variance, halflife
              fixed at six months before any result was seen. Nothing fitted.
      HAR    Corsi (2009), "A simple approximate long-memory model of realized
             volatility", Journal of Financial Econometrics 7(2) 174-196:
             regress RV_T on RV_{T-1}, the mean of the last three and the mean
             of the last twelve. Expanding OLS, refitted monthly, trained only
             on data through T-1.

    Losses:
      variance      squared error on the level of RV. The literal reading of
                    "R2 of the variance forecast". It is dominated by a handful
                    of months: on the policy portfolio the five largest squared
                    errors are more than nine tenths of the total. A statistic
                    decided by five observations out of 138 is reported, and
                    then reported as being decided by five observations.
      volatility    squared error on sqrt(RV).
      log variance  squared error on log(RV). Symmetric in proportional terms,
                    which is how a risk model is actually wrong.
      QLIKE         Patton (2011), "Volatility forecast comparison using
                    imperfect volatility proxies", Journal of Econometrics
                    160(1) 246-256, shows QLIKE and squared error are the two
                    loss functions robust to noise in the volatility proxy.

    The halflife sensitivity curve is reported alongside. The pre-set value is
    six months; the curve exists so the Committee can see that the answer moves
    with it and in opposite directions under the two losses, which is a better
    disclosure than a single number from a single halflife.
    """
    d = pitdata._to_date(end_date or config.WINDOW_END)
    rv = realised_variance_ann(d)
    pol_d = policy_daily_returns(d)
    cnt = pol_d.resample("ME").count()
    rv["_policy"] = ((np.log1p(pol_d) ** 2).resample("ME").sum().where(cnt >= 15)) * 12.0

    hl = EVAL_PARAMS["vol_ewma_halflife_m"]
    _, l3, l12 = EVAL_PARAMS["har_lags_m"]
    min_train = EVAL_PARAMS["var_min_train_obs"]

    out = {}
    for col in rv.columns:
        y = rv[col].dropna()
        if len(y) < min_train + 20:
            continue
        bench = expanding_mean_benchmark(y)
        ewma = y.ewm(halflife=hl, min_periods=12, adjust=True).mean().shift(1)

        X = pd.DataFrame({
            "d": y.shift(1),
            "w": y.rolling(l3).mean().shift(1),
            "m": y.rolling(l12).mean().shift(1),
        })
        har = _expanding_multi_ols(y, X, min_train)
        # a variance forecast below zero is not a forecast
        floor = y.shift(1).expanding(min_periods=1).min().clip(lower=1e-8)
        har = har.clip(lower=floor)

        m = pd.DataFrame({"y": y, "b": bench, "e": ewma, "h": har}).dropna()
        m = m[m["y"] > 0]
        if len(m) < 12:
            continue

        sq = (m["y"] - m["e"]) ** 2
        entry = {
            "n_oos": int(len(m)),
            "oos_start": str(m.index.min().date()),
            "oos_end": str(m.index.max().date()),
            "r2oos_variance_ewma": r2_oos(m["y"], m["b"], m["e"]),
            "r2oos_variance_har": r2_oos(m["y"], m["b"], m["h"]),
            "r2oos_vol_ewma": r2_oos(np.sqrt(m["y"]), np.sqrt(m["b"]), np.sqrt(m["e"])),
            "r2oos_logvar_ewma": r2_oos(np.log(m["y"]), np.log(m["b"]), np.log(m["e"])),
            "r2oos_logvar_har": r2_oos(np.log(m["y"]), np.log(m["b"]), np.log(m["h"])),
            "cw_t_variance_ewma": clark_west(m["y"], m["b"], m["e"])["cw_t"],
            "cw_t_logvar_ewma": clark_west(np.log(m["y"]), np.log(m["b"]),
                                           np.log(m["e"]))["cw_t"],
            "qlike_ewma": _qlike(m["y"], m["e"]),
            "qlike_bench": _qlike(m["y"], m["b"]),
            "qlike_ewma_beats_bench": bool(_qlike(m["y"], m["e"]) < _qlike(m["y"], m["b"])),
            "corr_ewma": float(np.corrcoef(m["e"], m["y"])[0, 1]),
            "rank_corr_ewma": _rank_corr(m["e"], m["y"]),
            "top5_sq_error_share_pct": float(100 * sq.nlargest(5).sum() / sq.sum()),
        }
        out[col] = entry

    # halflife sensitivity on the policy portfolio only
    y = rv["_policy"].dropna()
    bench = expanding_mean_benchmark(y)
    sens = {}
    for h in (3, 6, 12, 24):
        e = y.ewm(halflife=h, min_periods=12, adjust=True).mean().shift(1)
        m = pd.DataFrame({"y": y, "b": bench, "e": e}).dropna()
        m = m[m.index >= pd.Timestamp(out.get("_policy", {}).get("oos_start", m.index.min()))]
        m = m[m["y"] > 0]
        sens[h] = {
            "r2oos_variance": r2_oos(m["y"], m["b"], m["e"]),
            "r2oos_logvar": r2_oos(np.log(m["y"]), np.log(m["b"]), np.log(m["e"])),
            "preset": h == hl,
        }

    return {
        "as_of": d.isoformat(),
        "target": "annualised realised variance from daily log returns, monthly",
        "benchmark": "expanding mean of realised variance through T-1",
        "cells": out,
        "halflife_sensitivity_policy": sens,
        "params": {"ewma_halflife_m": hl, "har_lags_m": list(EVAL_PARAMS["har_lags_m"]),
                   "min_train_obs": min_train},
    }


def _expanding_multi_ols(y: pd.Series, X: pd.DataFrame, min_train: int) -> pd.Series:
    """Expanding-window OLS with an intercept, refitted every date, using only
    pairs whose target date is strictly before T. Loop is explicit; the sample
    is small enough that clarity is worth more than speed."""
    df = pd.concat([y.rename("_y"), X], axis=1).dropna()
    if df.empty:
        return pd.Series(dtype=float)
    cols = list(X.columns)
    A = df[cols].to_numpy(float)
    yv = df["_y"].to_numpy(float)
    n = len(df)
    fc = np.full(n, np.nan)
    for t in range(min_train, n):
        Xt = np.column_stack([np.ones(t), A[:t]])
        try:
            beta, *_ = np.linalg.lstsq(Xt, yv[:t], rcond=None)
        except np.linalg.LinAlgError:            # pragma: no cover
            continue
        fc[t] = float(np.r_[1.0, A[t]] @ beta)
    return pd.Series(fc, index=df.index)


# --------------------------------------------------------------------------
# Volatility, question (b): does scaling by it help THIS mandate?
# --------------------------------------------------------------------------
def vol_management_study(end_date=None) -> dict:
    """
    A direct test of the thing the office would actually do.

    Moreira and Muir (2017) scale a portfolio by the inverse of its forecast
    variance and report large Sharpe ratio gains. Cederburg, O'Doherty, Wang and
    Yan (2020), "On the performance of volatility-managed portfolios", JFE
    138(1) 95-117, show the gains are not available to a real-time investor once
    the scaling is required to be implementable. The disagreement is about
    implementability, so the test here is run under this mandate's constraints
    and not under the paper's.

    Construction, quarterly, at the twenty meeting dates:
      sigma_hat   EWMA forecast of policy-portfolio volatility, six-month
                  halflife, from realised variance through the meeting date
      sigma_star  the expanding mean of realised policy volatility through the
                  meeting date, so the target is not chosen with hindsight
      scale       sigma_star / sigma_hat, capped at 1.0
      portfolio   scale x policy + (1 - scale) x cash, held for the quarter

    The cap is the mandate. IPS 3.5 forbids leverage at the fund level, so the
    unlevered leg of Moreira-Muir is the only leg available. The uncapped
    version is computed as well and reported as a diagnostic, clearly marked as
    outside the mandate, because the difference between the two is most of what
    the literature is arguing about.
    """
    d = pitdata._to_date(end_date or config.WINDOW_END)
    hl = EVAL_PARAMS["vol_ewma_halflife_m"]

    pol_d = policy_daily_returns(d)
    cnt = pol_d.resample("ME").count()
    rv = ((np.log1p(pol_d) ** 2).resample("ME").sum().where(cnt >= 15)) * 12.0
    rv = rv.dropna()

    tr = signals.monthly_returns_as_of(d)
    w = pd.Series(config.POLICY)[tr.columns]
    pol_m = (tr * w).sum(axis=1)
    cash_m = tr[CASH]

    sigma_hat = np.sqrt(rv.ewm(halflife=hl, min_periods=12, adjust=True).mean())
    sigma_star = np.sqrt(rv.expanding(min_periods=12).mean())

    meetings = [pd.Timestamp(m) for m in config.meeting_dates()]
    # extend backwards over the full post-warmup sample as well
    all_q = [t for t in rv.index if t.month in (3, 6, 9, 12)]

    def build(qdates, cap):
        scale = pd.Series(index=pol_m.index, dtype=float)
        applied = {}
        for i, q in enumerate(qdates):
            if q not in sigma_hat.index or not np.isfinite(sigma_hat.get(q, np.nan)):
                continue
            if not np.isfinite(sigma_star.get(q, np.nan)):
                continue
            s = float(sigma_star[q] / sigma_hat[q])
            if cap is not None:
                s = min(s, cap)
            s = max(s, 0.0)
            nxt = qdates[i + 1] if i + 1 < len(qdates) else pol_m.index.max()
            months = pol_m.index[(pol_m.index > q) & (pol_m.index <= nxt)]
            scale.loc[months] = s
            applied[q.date().isoformat()] = s
        scale = scale.dropna()
        r = scale * pol_m.reindex(scale.index) + (1.0 - scale) * cash_m.reindex(scale.index)
        turn = float(scale.diff().abs().sum() / (len(scale) / 12.0)) if len(scale) else 0.0
        return r, scale, applied, turn

    results = {}
    for label, qd in (("full_sample", all_q), ("study_window", meetings)):
        capped, sc_c, appl_c, turn_c = build(qd, cap=1.0)
        uncapped, sc_u, _, turn_u = build(qd, cap=None)
        base = pol_m.reindex(capped.index)
        rf = cash_m.reindex(capped.index)

        p_base = perf_summary(base, rf, "policy, unscaled")
        p_cap = perf_summary(capped, rf, "policy, vol-scaled, capped at 1.0 (mandate)")
        p_unc = perf_summary(uncapped.reindex(capped.index), rf,
                             "policy, vol-scaled, uncapped (OUTSIDE MANDATE, diagnostic)")

        # turnover of the policy leg: sum of |change in scale| across rebalances
        results[label] = {
            "unscaled": p_base,
            "scaled_capped": p_cap,
            "scaled_uncapped_diagnostic": p_unc,
            "sharpe_difference": p_cap["sharpe_ann"] - p_base["sharpe_ann"],
            "sharpe_difference_se_note": (
                "the two series are highly correlated, so the standard error on "
                "the difference is smaller than the standard error on either "
                "level; neither is small enough at this n to call the difference"),
            "annual_turnover_scaled": turn_c,
            "annual_turnover_unscaled": 0.0,
            "mean_scale": float(sc_c.mean()) if len(sc_c) else float("nan"),
            "min_scale": float(sc_c.min()) if len(sc_c) else float("nan"),
            "max_scale": float(sc_c.max()) if len(sc_c) else float("nan"),
            "scale_path": appl_c,
            "n_rebalances": len(appl_c),
        }

    results["as_of"] = d.isoformat()
    results["params"] = {"ewma_halflife_m": hl, "cap": 1.0,
                         "target_vol": "expanding mean realised policy vol, PIT"}
    return results


if __name__ == "__main__":
    import json
    t = r2oos_table()
    print("POOLED R2_oos, longest available sample, excess returns over cash")
    for k, v in t["pooled"].items():
        if v.get("r2oos_pooled") is None:
            continue
        print(f"  {k:12s} {100*v['r2oos_pooled']:+7.3f}%   CW t {v['cw_t_pooled']:+6.2f}   "
              f"negative cells {v['n_negative']}/{v['n_cells']}   n {v['n_obs']}")
    print()
    v = variance_forecast_study()
    print("VARIANCE FORECAST R2_oos   (variance loss | log-variance loss | rank corr)")
    for k, c in v["cells"].items():
        print(f"  {k:14s} EWMA {100*c['r2oos_variance_ewma']:+7.2f}% | "
              f"{100*c['r2oos_logvar_ewma']:+7.2f}% | rho {c['rank_corr_ewma']:+.2f}   "
              f"HAR var {100*c['r2oos_variance_har']:+7.2f}%   n {c['n_oos']}")
    print()
    m = vol_management_study()
    for lab in ("full_sample", "study_window"):
        r = m[lab]
        print(f"{lab}: unscaled SR {r['unscaled']['sharpe_ann']:.3f} "
              f"(SE {r['unscaled']['sharpe_ann_se']:.3f})  "
              f"scaled SR {r['scaled_capped']['sharpe_ann']:.3f} "
              f"(SE {r['scaled_capped']['sharpe_ann_se']:.3f})  "
              f"maxDD {r['unscaled']['max_drawdown']:.3f} -> {r['scaled_capped']['max_drawdown']:.3f}")
