"""
taa.signals — signal construction and standardisation for the Quantitative desk.

SCOPE AND METHOD
------------------------------------------------------------------------------
Everything in this module is an estimator applied to a time series. No view is
formed here about the economy, the policy cycle or what is priced. A number
enters the allocation if and only if it can be computed from a series that
taa.pitdata will serve at the as-of date, and it enters with the sign the
published evidence gives it.

Every read goes through taa.pitdata.as_of(d). This module imports no data
source and holds no cache that spans as-of dates, so signals_as_of(d) sees
exactly the world of date d whatever the raw store happens to contain.

THE SIGNAL SET, AND WHY IT IS SMALL
------------------------------------------------------------------------------
Five signals, each with a published reference, each defined identically on all
nine lines. The set was fixed before any out-of-sample number was computed and
nothing was added or dropped afterwards. That discipline is the whole point:
the replication literature (Harvey, Liu and Zhu 2016; Hou, Xue and Zhang 2020;
Welch and Goyal 2008) documents what happens when a set is selected on the
evidence it is later tested against.

  momentum   Cumulative total return over months t-12 to t-1, the most recent
             month skipped. Moskowitz, Ooi and Pedersen (2012), "Time series
             momentum", JFE 104(2), find a positive own-past-return effect at
             the 12-month horizon across 58 futures markets. The one-month skip
             follows Jegadeesh (1990) short-horizon reversal. Sign +.

  trend      Month-end price divided by the mean of the last ten month-end
             prices, less one. Faber (2007), "A quantitative approach to
             tactical asset allocation", JWM 9(4), uses the ten-month moving
             average on the same asset-class set. Sign +. Correlated with
             momentum by construction; the correlation is reported rather than
             assumed away.

  carry      The compensation the line pays for being held, measured in the
             instrument natural to that line: the ten-year TIPS real yield for
             Treasury duration, a corporate spread over the ten-year Treasury
             for the two credit lines, the three-month bill yield for cash, and
             the trailing twelve-month distribution yield of the vehicle for the
             equity and real-asset lines (see _distribution_yield). Koijen,
             Moskowitz, Pedersen and Vrugt (2018), "Carry", JFE 127(2) 197-225,
             find carry predicts returns in every asset class they examine, each
             measured in its own natural units. Sign +.

             On the credit proxy. The intended series were the ICE BofA
             option-adjusted spreads, BAMLC0A0CM and BAMLH0A0HYM2. The free FRED
             endpoint serves only a rolling three-year window of them; in this
             cache they begin 2023-07-31, two years after the study window
             opens, so a historical signal built on them would exist for four of
             the twenty meetings and be absent for sixteen. They are therefore
             not used in any historical work. The substitutes are Moody's
             seasoned corporate yields less the ten-year Treasury, AAA10Y for
             investment grade and BAA10Y for high yield, daily and public back
             to 1986. These are spreads over the curve rather than
             option-adjusted spreads, so their LEVEL is not the level of the
             spread the line actually earns: Baa over Treasuries is a fraction
             of a high-yield OAS. That does not matter here, because the signal
             is standardised against its own expanding history and only its time
             variation enters. It would matter if the level were used directly,
             and it is not. The gap in the OAS series is reported in
             coverage_report() rather than filled.

  reversal   Negative of the cumulative total return over months t-60 to t-13,
             a long-horizon mean-reversion proxy. De Bondt and Thaler (1985);
             Asness, Moskowitz and Pedersen (2013), "Value and momentum
             everywhere", JF 68(3), use the five-year-ago price as the
             asset-class value proxy. The most recent twelve months are excluded
             so the measure does not simply invert the momentum signal. Sign +
             (the negation is inside the raw value).

  volatility Exponentially weighted realised volatility of monthly returns,
             six-month halflife. Moreira and Muir (2017), "Volatility-managed
             portfolios", JF 72(4), scale exposure by the inverse of forecast
             variance. Sign - (high forecast volatility is a reason to hold
             less of the line, not more).

WHY NOT CAPE
------------------------------------------------------------------------------
Shiller's cyclically adjusted price-earnings ratio is the obvious value proxy
and it is excluded from all historical work here. It has no vintage history:
the file distributed today carries today's revised earnings for every past date,
and taa.pitdata will serve it only through .static() with a logged anachronism
reason. A predictor whose historical values were not available on the dates they
are tested against cannot produce an honest out-of-sample statistic. The
long-horizon reversal signal above is the substitute; it is built from prices
alone, which are not revised, and is therefore clean at every as-of date.

STANDARDISATION
------------------------------------------------------------------------------
Each raw signal is standardised against ITS OWN LINE'S EXPANDING HISTORY, not
cross-sectionally. The lines are not commensurable in raw units: a distribution
yield of 5.9% on high yield and 1.1% on US equity is a statement about coupon
conventions, not about relative attractiveness, and the same is true of the
volatility of cash against the volatility of emerging markets. Standardising
each line against its own past asks the only question the estimator can answer,
which is whether this line is cheap, trending or calm relative to how it usually
looks. The cross-sectional step happens once, at the composite stage, after the
units are already comparable.

The expanding window includes the observation at t, which was known at t, and
nothing after it. A minimum of Z_MIN_OBS observations is required before a
z-score is produced; before that the signal is absent, not zero.

Z-scores are winsorised at +/- WINSOR_Z.

DEGREES OF FREEDOM
------------------------------------------------------------------------------
Counted in PARAMS and reported in the paper. Every one was set at the value used
in the cited paper, or at the obvious round number, before any result was seen.
None was searched over.
"""

from __future__ import annotations

import datetime as _dt

import numpy as np
import pandas as pd

from . import config, pitdata

# --------------------------------------------------------------------------
# Parameters. Each entry is one degree of freedom. Nothing was tuned.
# --------------------------------------------------------------------------
PARAMS = {
    "momentum_lookback_m": 12,    # MOP (2012) headline horizon
    "momentum_skip_m": 1,         # Jegadeesh (1990) short-horizon reversal
    "trend_ma_months": 10,        # Faber (2007)
    "carry_window_m": 12,         # a full distribution cycle
    "reversal_start_m": 60,       # AMP (2013) five-year value proxy
    "reversal_end_m": 13,         # skip the momentum window
    "vol_halflife_m": 6,          # RiskMetrics-style, monthly
    "vol_window_m": 36,           # observations entering the EWMA
    "z_min_obs": 36,              # minimum expanding history for a z-score
    "winsor_z": 2.5,              # z-score clip
}

N_DEGREES_OF_FREEDOM = len(PARAMS)

SIGNALS = ("momentum", "trend", "carry", "reversal", "volatility")

# Prior sign from the cited evidence. Applied at the composite stage only; the
# out-of-sample regressions in taa.evidence do not impose it in the primary
# specification, so the data is allowed to disagree.
SIGN = {
    "momentum": +1.0,
    "trend": +1.0,
    "carry": +1.0,
    "reversal": +1.0,
    "volatility": -1.0,
}

CITATION = {
    "momentum": "Moskowitz, Ooi & Pedersen (2012), JFE 104(2) 228-250",
    "trend": "Faber (2007), Journal of Wealth Management 9(4) 69-79",
    "carry": "Koijen, Moskowitz, Pedersen & Vrugt (2018), JFE 127(2) 197-225",
    "reversal": "De Bondt & Thaler (1985), JF 40(3); Asness, Moskowitz & Pedersen (2013), JF 68(3)",
    "volatility": "Moreira & Muir (2017), JF 72(4) 1611-1644",
    "carry_dy": "robustness variant of carry; does not enter the composite",
}

# Carry measured from a market-quoted rate rather than from the vehicle's own
# distributions. Values are read as percentages and converted to decimals.
CARRY_MARKET = {
    "ust_duration": "DFII10",     # ten-year TIPS real yield
    "us_ig": "AAA10Y",            # Moody's Aaa less ten-year Treasury
    "us_hy": "BAA10Y",            # Moody's Baa less ten-year Treasury
    "cash": "DGS3MO",             # three-month bill
}

# Registered but deliberately unused in historical work. Reported as a gap.
CARRY_INTENDED_UNUSED = {
    "us_ig": "BAMLC0A0CM",
    "us_hy": "BAMLH0A0HYM2",
}


# --------------------------------------------------------------------------
# Panels. One pitdata read per as-of date; the memo is keyed on the raw-store
# path as well as the date, so redirecting the store invalidates it. Nothing
# is ever carried from one as-of date to another.
# --------------------------------------------------------------------------
_PANEL_MEMO: dict = {}


def clear_caches() -> None:
    """Drop every memo. tests/check_quant.py calls this between store swaps."""
    _PANEL_MEMO.clear()


def _memo_key(date: _dt.date, lines: tuple) -> tuple:
    # Keyed on the store identity as well as the date, so that redirecting the
    # raw store invalidates every memo. This is what makes the store-swap test
    # in tests/check_quant.py meaningful rather than a test of a cache hit.
    # The identifier comes from the sanctioned path; analysis code does not name
    # the raw cache.
    return (pitdata.store_id(), date.isoformat(), lines)


def panels_as_of(date, lines=None) -> dict:
    """
    Monthly panels as they stood on `date`.

      px_adj : month-end total-return price level (dividends reinvested)
      tr     : month-end to month-end total return
      pr     : month-end to month-end price return
      income : tr - pr, the distribution component of the month

    Only month ends at or before `date` appear. The last row is the last
    complete month on or before the as-of date.
    """
    d = pitdata._to_date(date)
    lines = tuple(lines or config.LINES)
    key = _memo_key(d, lines)
    if key in _PANEL_MEMO:
        return _PANEL_MEMO[key]

    a = pitdata.as_of(d)
    adj = a.line_prices(list(lines))
    cls = a.prices([config.VEHICLE[ln] for ln in lines], field="close")
    cls.columns = list(lines)

    m_adj = adj.resample("ME").last()
    m_cls = cls.resample("ME").last()
    m_adj = m_adj[m_adj.index <= pd.Timestamp(d)]
    m_cls = m_cls[m_cls.index <= pd.Timestamp(d)]

    tr = m_adj.pct_change()
    pr = m_cls.pct_change()
    income = tr - pr

    pitdata.assert_no_future(m_adj, d, "signals.panels[px_adj]")
    pitdata.assert_no_future(tr, d, "signals.panels[tr]")

    # Market-quoted rates used by the carry signal.
    #
    # The value recorded against month end T is the last quote knowable on T,
    # which is the last observation dated on or before T minus the series'
    # publication lag. Resampling to the month end and taking the last value
    # inside the month is the obvious thing to do and it is wrong: for a series
    # carrying a one-day lag it records a number that was not published until
    # the following day. The error is small in magnitude and invisible in a
    # single reading, and it makes the panel depend on the date it was built
    # on, which is a look-ahead in the out-of-sample walk. It was found by
    # check 3 in tests/check_quant.py, which compares a panel built at the end
    # of the sample against the value computed standing on the date itself.
    mkt = {}
    last_mkt = None
    for sid in sorted(set(CARRY_MARKET.values())):
        s = a.fred(sid)
        pitdata.assert_no_future(s.to_frame(), d, f"signals.panels[{sid}]")
        if not len(s):
            continue
        last_mkt = max(last_mkt, s.index.max().date()) if last_mkt else s.index.max().date()
        lag = pitdata.MARKET_FRED[sid][1]
        knowable_by = m_adj.index - pd.Timedelta(days=int(lag))
        vals = s.reindex(s.index.union(knowable_by)).ffill().reindex(knowable_by)
        mkt[sid] = pd.Series(vals.to_numpy(), index=m_adj.index) / 100.0
    m_mkt = pd.DataFrame(mkt, index=m_adj.index) if mkt else pd.DataFrame(index=m_adj.index)

    last_obs = max(adj.index.max(), cls.index.max()).date() if len(adj) else None
    if last_mkt and last_obs:
        last_obs = max(last_obs, last_mkt)

    out = {
        "px_adj": m_adj,
        "tr": tr.dropna(how="all"),
        "pr": pr.dropna(how="all"),
        "income": income.dropna(how="all"),
        "mkt": m_mkt,
        "last_observation": last_obs,
        "as_of": d,
        "lines": list(lines),
    }
    _PANEL_MEMO[key] = out
    return out


# --------------------------------------------------------------------------
# Raw signal panels. Each returns a DataFrame indexed by month end, one column
# per line, holding the value of the signal AS OF that month end. Row t uses
# only information dated t or earlier, so any row may be read at any as-of date
# at or after t without leakage.
# --------------------------------------------------------------------------
def _cum_return(tr: pd.DataFrame, start_lag: int, end_lag: int) -> pd.DataFrame:
    """
    Cumulative total return over months [t-start_lag, t-end_lag], inclusive of
    both endpoints, expressed as a simple return. start_lag > end_lag >= 0.
    """
    g = np.log1p(tr)
    csum = g.cumsum()
    # sum of g over (t-start_lag .. t-end_lag) = csum[t-end_lag] - csum[t-start_lag-1]
    hi = csum.shift(end_lag)
    lo = csum.shift(start_lag + 1)
    return np.expm1(hi - lo)


def raw_momentum(p: dict) -> pd.DataFrame:
    k = PARAMS["momentum_lookback_m"]
    s = PARAMS["momentum_skip_m"]
    return _cum_return(p["tr"], start_lag=k - 1, end_lag=s)


def raw_trend(p: dict) -> pd.DataFrame:
    n = PARAMS["trend_ma_months"]
    px = p["px_adj"]
    return px / px.rolling(n).mean() - 1.0


def _distribution_yield(p: dict) -> pd.DataFrame:
    """
    Trailing twelve-month distribution yield, from the divergence of the
    adjusted and unadjusted close.

    Why this is point-in-time clean, which is the part that usually is not.
    The adjusted close is restated retroactively every time a distribution is
    paid: a dividend paid in 2026 rescales every adjusted close before it by the
    same constant factor. A ratio of two past adjusted closes is therefore
    invariant to every distribution paid after the later of the two dates, and
    the total return between two past month ends computed from adjusted closes
    is exactly the total return that was realised over that interval. The
    unadjusted close is split-adjusted only, so the price return between the
    same two dates is likewise invariant. Their difference is the distribution
    actually paid inside the interval, which was public when it was paid. No
    step in this calculation looks at anything dated after the later month end.
    """
    return p["income"].rolling(PARAMS["carry_window_m"]).sum()


def raw_carry(p: dict) -> pd.DataFrame:
    """
    Carry in the units natural to each line. Market-quoted rates where one
    exists with full history, the vehicle's own trailing distribution yield
    otherwise. Both are in decimals.
    """
    dy = _distribution_yield(p)
    out = dy.copy()
    mkt = p.get("mkt")
    for ln in p["lines"]:
        sid = CARRY_MARKET.get(ln)
        if sid and mkt is not None and sid in mkt.columns:
            out[ln] = mkt[sid].reindex(out.index)
    return out


def raw_carry_dy(p: dict) -> pd.DataFrame:
    """
    Robustness variant: the trailing distribution yield on every line, one
    uniform definition. Reported in the out-of-sample table so the reader can
    see whether the choice of carry proxy changed the answer. It does not enter
    the composite and it is not a sixth signal.
    """
    return _distribution_yield(p)


def raw_reversal(p: dict) -> pd.DataFrame:
    return -_cum_return(p["tr"],
                        start_lag=PARAMS["reversal_start_m"] - 1,
                        end_lag=PARAMS["reversal_end_m"])


def raw_volatility(p: dict) -> pd.DataFrame:
    """
    Annualised exponentially weighted volatility of monthly returns. The mean is
    not removed; at a monthly frequency the squared mean is a rounding error
    against the squared return and removing an expanding mean would import a
    second estimator into a risk measure.
    """
    hl = PARAMS["vol_halflife_m"]
    win = PARAMS["vol_window_m"]
    tr = p["tr"]
    var = (tr ** 2).ewm(halflife=hl, min_periods=min(12, win), adjust=True).mean()
    return np.sqrt(var * 12.0)


_RAW_BUILDERS = {
    "momentum": raw_momentum,
    "trend": raw_trend,
    "carry": raw_carry,
    "reversal": raw_reversal,
    "volatility": raw_volatility,
}

# Built and reported, never composited.
_ROBUSTNESS_BUILDERS = {
    "carry_dy": raw_carry_dy,
}


def raw_panels_as_of(date, lines=None, include_robustness: bool = False) -> dict:
    """{signal: DataFrame(month_end x line)} of raw values, PIT at `date`."""
    p = panels_as_of(date, lines)
    out = {name: fn(p) for name, fn in _RAW_BUILDERS.items()}
    if include_robustness:
        out.update({name: fn(p) for name, fn in _ROBUSTNESS_BUILDERS.items()})
    return out


# --------------------------------------------------------------------------
# Standardisation
# --------------------------------------------------------------------------
def expanding_z(df: pd.DataFrame, min_obs: int | None = None,
                winsor: float | None = None) -> pd.DataFrame:
    """
    Expanding-window z-score, per column, using observations through t
    inclusive and nothing after. Returns NaN until min_obs observations exist.
    """
    min_obs = PARAMS["z_min_obs"] if min_obs is None else min_obs
    winsor = PARAMS["winsor_z"] if winsor is None else winsor
    mu = df.expanding(min_periods=min_obs).mean()
    sd = df.expanding(min_periods=min_obs).std(ddof=1)
    z = (df - mu) / sd.replace(0.0, np.nan)
    return z.clip(-winsor, winsor)


# --------------------------------------------------------------------------
# The public interface
# --------------------------------------------------------------------------
def signals_as_of(date, lines=None) -> dict:
    """
    {line: {signal: z}} plus "_raw" and "_meta", as at `date`.

    z is the expanding-window standardised value with the winsorisation applied
    and WITHOUT the prior sign; the sign is applied in composite_as_of so that
    the stored z is comparable with the raw value it came from. A signal with
    insufficient history is absent from the line's dict rather than set to zero.
    """
    d = pitdata._to_date(date)
    lines = list(lines or config.LINES)
    lines = [ln for ln in lines if d >= config.INVESTABLE_FROM[ln]]

    p = panels_as_of(d, lines)
    raws = {name: fn(p) for name, fn in _RAW_BUILDERS.items()}

    out: dict = {ln: {} for ln in lines}
    raw_out: dict = {ln: {} for ln in lines}
    n_avail = 0
    for name, df in raws.items():
        z = expanding_z(df)
        if not len(z):
            continue
        zr = z.iloc[-1]
        rr = df.iloc[-1]
        for ln in lines:
            if ln in zr.index and np.isfinite(zr[ln]):
                out[ln][name] = float(zr[ln])
                n_avail += 1
            if ln in rr.index and np.isfinite(rr[ln]):
                raw_out[ln][name] = float(rr[ln])

    meta = {
        "as_of": d.isoformat(),
        "last_observation": (p["last_observation"].isoformat()
                             if p["last_observation"] else None),
        "last_monthly_return": (str(p["tr"].index.max().date())
                                if len(p["tr"]) else None),
        "lines": lines,
        "signals": list(SIGNALS),
        "n_z_available": n_avail,
        "params": dict(PARAMS),
        "degrees_of_freedom": N_DEGREES_OF_FREEDOM,
        "standardisation": "expanding own-history z, winsorised, then cross-sectional demean at composite",
        "carry_sources": {ln: CARRY_MARKET.get(ln, "vehicle distribution yield")
                          for ln in lines},
    }
    out["_raw"] = raw_out
    out["_meta"] = meta
    return out


def composite_as_of(date, lines=None) -> dict:
    """
    {line: composite score}.

    Stage one: apply the prior sign to each standardised signal and average the
    signals that are available for that line. Equal weights. No signal is given
    a larger weight than another, because any weighting scheme fitted on this
    sample would be fitted on the sample it is then reported against.

    Stage two: subtract the cross-sectional mean across the investable lines.
    The result is a relative statement, which is what a tracking-error budget
    measured against a fully invested policy portfolio can express. An absolute
    level of enthusiasm about every asset at once has nowhere to go inside a
    long-only, fully invested, no-leverage mandate.
    """
    s = signals_as_of(date, lines)
    lns = s["_meta"]["lines"]
    comp = {}
    for ln in lns:
        vals = [SIGN[k] * v for k, v in s[ln].items()]
        comp[ln] = float(np.mean(vals)) if vals else 0.0
    if comp:
        mu = float(np.mean(list(comp.values())))
        comp = {k: v - mu for k, v in comp.items()}
    return comp


def signal_history(end_date, lines=None, include_robustness: bool = True) -> dict:
    """
    {signal: DataFrame(month_end x line)} of RAW values through `end_date`.

    Used by taa.evidence for the out-of-sample regressions. Row t is the value
    an analyst standing on month end t would have computed, so the panel can be
    walked forward without the walk itself leaking. taa.evidence never reads a
    row dated later than the forecast origin it is standing on, and
    tests/check_quant.py asserts that row t of this panel equals the value
    signals_as_of(t) returns, which is what licences the shortcut.
    """
    return raw_panels_as_of(end_date, lines, include_robustness=include_robustness)


def coverage_report(date=None, lines=None) -> dict:
    """
    Which inputs exist, from when, and which quarters of the window lack one.

    The dashboard shows this. A signal that is absent for part of the record is
    reported as absent; it is never carried backwards or filled.
    """
    d = pitdata._to_date(date or config.WINDOW_END)
    lines = list(lines or config.LINES)
    raws = raw_panels_as_of(d, lines, include_robustness=True)

    meetings = config.meeting_dates()
    per_signal = {}
    for name, df in raws.items():
        z = expanding_z(df)
        entry = {"raw_first": {}, "z_first": {}, "missing_meetings": {}}
        for ln in lines:
            if ln not in df.columns:
                continue
            fr = df[ln].first_valid_index()
            fz = z[ln].first_valid_index()
            entry["raw_first"][ln] = str(fr.date()) if fr is not None else None
            entry["z_first"][ln] = str(fz.date()) if fz is not None else None
            missing = [m.isoformat() for m in meetings
                       if fz is None or pd.Timestamp(m) < fz]
            if missing:
                entry["missing_meetings"][ln] = missing
        per_signal[name] = entry

    # Registered series the desk chose not to use, and why.
    a = pitdata.as_of(d)
    excluded = {}
    for ln, sid in CARRY_INTENDED_UNUSED.items():
        try:
            s = a.fred(sid)
            first = str(s.index.min().date()) if len(s) else None
            n = len(s)
        except Exception as e:                       # pragma: no cover
            first, n = None, 0
            _ = e
        covered = [m.isoformat() for m in meetings
                   if first and m >= _dt.date.fromisoformat(first)]
        excluded[sid] = {
            "line": ln,
            "first_observation": first,
            "observations": n,
            "meetings_covered": len(covered),
            "meetings_total": len(meetings),
            "used": False,
            "reason": ("free FRED endpoint serves a rolling three-year window; "
                       "the series does not reach the start of the study window, "
                       "so it cannot support a signal evaluated across it"),
            "substitute": CARRY_MARKET.get(ln),
        }

    return {
        "as_of": d.isoformat(),
        "signals": per_signal,
        "carry_sources": {ln: CARRY_MARKET.get(ln, "vehicle distribution yield")
                          for ln in lines},
        "excluded_series": excluded,
        "meetings_total": len(meetings),
    }


def monthly_returns_as_of(date, lines=None) -> pd.DataFrame:
    return panels_as_of(date, lines)["tr"]


if __name__ == "__main__":
    import json

    d = config.WINDOW_END
    s = signals_as_of(d)
    print(f"signals as of {d}   last observation {s['_meta']['last_observation']}")
    print(f"degrees of freedom {N_DEGREES_OF_FREEDOM}\n")
    rows = []
    for ln in s["_meta"]["lines"]:
        rows.append({"line": ln, **{k: round(v, 2) for k, v in s[ln].items()}})
    print(pd.DataFrame(rows).set_index("line").to_string())
    print("\ncomposite (cross-sectionally demeaned)")
    print(json.dumps({k: round(v, 3) for k, v in composite_as_of(d).items()}, indent=2))
