"""
taa.perf — performance and risk statistics, strategy against benchmark.

IPS 4.3: "Performance is reported to the Committee quarterly and to the Board
annually, always against the benchmark and never in isolation. Presentation
follows the Global Investment Performance Standards, including the risk
statistics required for the benchmark as well as for the portfolio, and the
disclosure required of a blended benchmark."

So every statistic in this module is computed for the portfolio and for the
benchmark, side by side, and nothing returns a portfolio number alone. The
three-year annualised ex-post standard deviation is computed for both, which is
the specific requirement that most in-house reporting misses.

The benchmark is the policy portfolio blended at the IPS 4.1 weights and
rebalanced monthly. That rebalancing frequency is a disclosure item, not an
implementation detail, and it is stated wherever the benchmark appears.

Nothing here touches data. It takes return series and returns numbers, so it is
independent of every desk and of the point-in-time layer.
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd

from . import config

MONTHS = 12


# --------------------------------------------------------------------------
# Building blocks
# --------------------------------------------------------------------------
def cumulative(r: pd.Series) -> pd.Series:
    """Growth of one unit, starting at 1.0 the month before the first return."""
    out = (1.0 + r).cumprod()
    first = out.index[0] - pd.offsets.MonthEnd(1)
    return pd.concat([pd.Series([1.0], index=[first]), out])


def annualised_return(r: pd.Series) -> float:
    """Geometric, annualised. Periods under a year are not annualised (GIPS)."""
    n = len(r)
    if n == 0:
        return float("nan")
    total = float((1.0 + r).prod())
    if n < MONTHS:
        return total - 1.0
    return total ** (MONTHS / n) - 1.0


def cumulative_return(r: pd.Series) -> float:
    return float((1.0 + r).prod()) - 1.0


def annualised_vol(r: pd.Series) -> float:
    """Sample standard deviation, annualised. GIPS uses the sample form."""
    if len(r) < 2:
        return float("nan")
    return float(r.std(ddof=1)) * math.sqrt(MONTHS)


def drawdown_path(r: pd.Series) -> pd.Series:
    c = cumulative(r)
    return c / c.cummax() - 1.0


def max_drawdown(r: pd.Series) -> float:
    dd = drawdown_path(r)
    return float(dd.min()) if len(dd) else float("nan")


def max_drawdown_dates(r: pd.Series) -> tuple:
    dd = drawdown_path(r)
    if not len(dd):
        return (None, None, float("nan"))
    trough = dd.idxmin()
    c = cumulative(r)
    peak = c.loc[:trough].idxmax()
    return (peak, trough, float(dd.loc[trough]))


def tracking_error(active: pd.Series) -> float:
    """Realised, annualised. The ex-ante figure comes from the risk model."""
    return annualised_vol(active)


def information_ratio(active: pd.Series) -> float:
    te = tracking_error(active)
    if not te or math.isnan(te):
        return float("nan")
    return annualised_return_arith(active) / te


def annualised_return_arith(r: pd.Series) -> float:
    return float(r.mean()) * MONTHS


def sharpe(r: pd.Series, rf: pd.Series | float = 0.0) -> float:
    ex = r - rf if isinstance(rf, pd.Series) else r - rf / MONTHS
    v = annualised_vol(ex)
    if not v or math.isnan(v):
        return float("nan")
    return annualised_return_arith(ex) / v


def sharpe_stderr(sr: float, n: int) -> float:
    """
    Lo (2002), The Statistics of Sharpe Ratios, Financial Analysts Journal.
    SE(SR) = sqrt((1 + SR^2 / 2) / n) for iid returns, in the same units as SR.

    Quoted in annual terms here by scaling the monthly SR standard error, which
    is the reason a Sharpe ratio on sixty observations carries a standard error
    wide enough to contain most answers.
    """
    if n < 2 or math.isnan(sr):
        return float("nan")
    sr_m = sr / math.sqrt(MONTHS)
    se_m = math.sqrt((1.0 + 0.5 * sr_m ** 2) / n)
    return se_m * math.sqrt(MONTHS)


def rolling_stdev_36m(r: pd.Series) -> pd.Series:
    """
    Three-year annualised ex-post standard deviation, computed monthly.

    This is the GIPS risk measure and the standard requires it for the
    benchmark as well as for the portfolio. Returns NaN until 36 observations
    exist, which is itself a disclosure: on a sixty-month record only the last
    twenty-five months carry one.
    """
    return r.rolling(36).std(ddof=1) * math.sqrt(MONTHS)


def downside_deviation(r: pd.Series, mar: float = 0.0) -> float:
    d = r[r < mar / MONTHS] - mar / MONTHS
    if len(d) < 2:
        return float("nan")
    return float(np.sqrt((d ** 2).sum() / (len(r) - 1))) * math.sqrt(MONTHS)


def beta_alpha(r: pd.Series, b: pd.Series) -> tuple[float, float]:
    if len(r) < 3:
        return (float("nan"), float("nan"))
    cov = np.cov(r.values, b.values, ddof=1)
    beta = float(cov[0, 1] / cov[1, 1])
    alpha = annualised_return_arith(r) - beta * annualised_return_arith(b)
    return beta, alpha


def hit_rate(active: pd.Series) -> float:
    if not len(active):
        return float("nan")
    return float((active > 0).sum()) / len(active)


# --------------------------------------------------------------------------
# The paired summary. Nothing returns the strategy alone.
# --------------------------------------------------------------------------
def pair_summary(r: pd.Series, b: pd.Series, label: str = "",
                 rf: pd.Series | float = 0.0) -> dict:
    """
    Every statistic for the portfolio and for the benchmark, side by side, plus
    the active difference. IPS 4.3 and GIPS both require the benchmark figures,
    so this function refuses to produce a one-sided answer by construction.
    """
    r, b = r.align(b, join="inner")
    a = r - b
    n = len(r)
    sr_p, sr_b = sharpe(r, rf), sharpe(b, rf)
    ddp, ddb = max_drawdown_dates(r), max_drawdown_dates(b)
    beta, alpha = beta_alpha(r, b)
    return {
        "label": label,
        "months": n,
        "period_start": str(r.index.min().date()) if n else None,
        "period_end": str(r.index.max().date()) if n else None,
        "annualised": n >= MONTHS,
        "portfolio": {
            "cumulative_return": cumulative_return(r),
            "return": annualised_return(r),
            "stdev": annualised_vol(r),
            "max_drawdown": ddp[2],
            "max_drawdown_peak": str(ddp[0].date()) if ddp[0] is not None else None,
            "max_drawdown_trough": str(ddp[1].date()) if ddp[1] is not None else None,
            "sharpe": sr_p,
            "sharpe_stderr": sharpe_stderr(sr_p, n),
            "downside_deviation": downside_deviation(r),
            "best_month": float(r.max()) if n else float("nan"),
            "worst_month": float(r.min()) if n else float("nan"),
        },
        "benchmark": {
            "cumulative_return": cumulative_return(b),
            "return": annualised_return(b),
            "stdev": annualised_vol(b),
            "max_drawdown": ddb[2],
            "max_drawdown_peak": str(ddb[0].date()) if ddb[0] is not None else None,
            "max_drawdown_trough": str(ddb[1].date()) if ddb[1] is not None else None,
            "sharpe": sr_b,
            "sharpe_stderr": sharpe_stderr(sr_b, n),
            "downside_deviation": downside_deviation(b),
            "best_month": float(b.max()) if n else float("nan"),
            "worst_month": float(b.min()) if n else float("nan"),
        },
        "active": {
            "cumulative_return": cumulative_return(r) - cumulative_return(b),
            "return": annualised_return(r) - annualised_return(b),
            "arithmetic_return": annualised_return_arith(a),
            "tracking_error": tracking_error(a),
            "information_ratio": information_ratio(a),
            "hit_rate": hit_rate(a),
            "beta": beta,
            "alpha": alpha,
            "best_month": float(a.max()) if n else float("nan"),
            "worst_month": float(a.min()) if n else float("nan"),
        },
        "drawdown_limit": config.DRAWDOWN_LIMIT,
        "te_budget_bps": config.TE_BUDGET_BPS,
    }


def monthly_table(r: pd.Series, b: pd.Series) -> pd.DataFrame:
    """
    The series a reader takes away and checks: strategy, benchmark and the
    active difference, for every month in the window. Annual and since-inception
    summaries sit on top of this rather than replacing it.
    """
    r, b = r.align(b, join="inner")
    out = pd.DataFrame({"strategy": r, "benchmark": b, "active": r - b})
    out.index.name = "month_end"
    return out


def period_table(r: pd.Series, b: pd.Series, periods: list[tuple]) -> list[dict]:
    """periods: list of (label, start_date, end_date)."""
    rows = []
    for label, s, e in periods:
        m = (r.index >= pd.Timestamp(s)) & (r.index <= pd.Timestamp(e))
        if not m.any():
            continue
        rows.append(pair_summary(r[m], b[m], label=label))
    return rows


def standard_periods(r: pd.Series, b: pd.Series) -> list[dict]:
    """Trailing periods GIPS-style, then each fiscal year, then since inception."""
    end = r.index.max()
    out = []
    for label, months in (("3 months", 3), ("1 year", 12), ("3 years", 36), ("5 years", 60)):
        if len(r) >= months:
            out.append(pair_summary(r.iloc[-months:], b.iloc[-months:], label=label))
    for fy, s, e in config.fiscal_years():
        m = (r.index >= pd.Timestamp(s)) & (r.index <= pd.Timestamp(e))
        if m.any():
            out.append(pair_summary(r[m], b[m], label=fy))
    out.append(pair_summary(r, b, label="Since inception"))
    return out


def fmt_pct(x: float, dp: int = 2, paren: bool = True) -> str:
    """House convention: negatives in parentheses, never a minus sign, never colour."""
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return "—"
    v = x * 100.0
    s = f"{abs(v):,.{dp}f}"
    return f"({s})" if (v < 0 and paren) else s


def fmt_bps(x: float, dp: int = 0) -> str:
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return "—"
    v = x * 10000.0
    s = f"{abs(v):,.{dp}f}"
    return f"({s})" if v < 0 else s


def fmt_num(x: float, dp: int = 2) -> str:
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return "—"
    s = f"{abs(x):,.{dp}f}"
    return f"({s})" if x < 0 else s
