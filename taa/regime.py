"""
taa.regime — the Macro desk's point-in-time regime read.

WHAT THIS IS
------------------------------------------------------------------------------
A judgement, made mechanical. Not an optimiser, not a signal, not a fitted
model. Four axes a macro desk actually watches, each scored by a rule written
down in this file, combined into a named regime by a lookup a trustee can apply
with a printout and a pencil. The mapping from regime to portfolio tilt is a
table, also in this file, so that a reader who disagrees can disagree with the
table rather than with a black box.

Nothing here is estimated from the data. Every threshold is a stated prior. The
point of that is falsifiability: a threshold you can read is a threshold you can
argue with, and IPS 4.4 requires that a view can be shown wrong.

WHY IT IS POINT-IN-TIME AND WHAT THAT COSTS
------------------------------------------------------------------------------
Every input is read through taa.pitdata at the as-of date, so the read at
2022-09-30 sees the vintage published by 2022-09-30 and nothing later. This is
not decoration. US real GDP for 2022 Q2 was first published at (0.93)% annualised
on 28 July 2022 and did not cross zero until the BEA annual update of
26 September 2024, 790 days later. On this framework that single input moves the
2022-09-30 growth read by two notches and the regime name from stagflation_risk
to overheat. A desk backtesting off current values spends two years holding the
wrong end of that. See gdp_vintage_demonstration().

Every value returned in `inputs` carries the observation date it came from, so
the assertion "no field references data dated after the meeting" is checkable by
walking the dict rather than by trusting this docstring.

THE FOUR AXES AND THEIR RULES
------------------------------------------------------------------------------
GROWTH. Five indicators, each scored (1), 0 or +1, summed to G in [-5, +4].

    G1 real GDP, annualised quarter on quarter, latest quarter published on this
       vintage          > 2.0% -> +1 ;  0.0 to 2.0% -> 0 ;  < 0.0% -> (1)
    G2 payrolls, mean monthly change over the last three months
                        > 150k -> +1 ;  0 to 150k  -> 0 ;  < 0     -> (1)
    G3 Sahm gap: 3-month mean unemployment rate less its lowest 3-month mean of
       the prior twelve months
                        < 0.20pp -> +1 ; 0.20 to 0.50 -> 0 ; >= 0.50 -> (1)
    G4 industrial production, year on year
                        > 1.5% -> +1 ; (1.5)% to 1.5% -> 0 ; < (1.5)% -> (1)
    G5 technical recession: the two most recent published quarters both negative
       on this vintage  true -> (1) ; false -> 0        [cannot score positive]

    G >= 2 -> expansion ; 0 to 1 -> slowdown ; (2) to (1) -> stall ; <= (3) -> contraction

INFLATION. Level of core PCE year on year against the 2% target, then adjusted
one bucket for direction.

    >= 3.5% -> high ; 2.8 to 3.5 -> above_target ; 2.0 to 2.8 -> at_target ;
    < 2.0% -> below_target
    direction: core PCE 3-month annualised less core PCE year on year.
       below (0.50)pp -> disinflating  -> demote one bucket
       above +0.50pp  -> reaccelerating -> promote one bucket
       otherwise      -> stable         -> no change

POLICY. Three indicators, each (1), 0 or +1, summed to P in [-3, +3], where +1
means restrictive.

    P1 real 10y yield (DFII10)      > 1.5% -> +1 ; 0.5 to 1.5 -> 0 ; < 0.5 -> (1)
    P2 curve, 10y less 3m           < 0    -> +1 ; 0 to 1.0   -> 0 ; > 1.0 -> (1)
    P3 real policy rate, 3m bill less core PCE year on year
                                    > 1.0% -> +1 ; 0 to 1.0   -> 0 ; < 0   -> (1)

    P >= 2 -> restrictive ; 0 to 1 -> neutral ; <= (1) -> accommodative
    direction, from 2y less 3m: < (0.25) -> easing_priced ;
                                > +0.25  -> tightening_priced ; else on_hold_priced

LIQUIDITY. Four indicators, each (1), 0 or +1, averaged over those available, so
that a missing series reduces the evidence rather than silently scoring zero.

    L1 Moody's Baa less 10y Treasury, percentile against its own trailing ten
       years   < 33rd -> +1 ; 33 to 67 -> 0 ; > 67th -> (1)
    L2 high yield OAS, percentile against its own available history
              < 33rd -> +1 ; 33 to 67 -> 0 ; > 67th -> (1)
       UNAVAILABLE before 2023-07-31 and excluded from the mean on those dates.
    L3 VIX     < 18 -> +1 ; 18 to 25 -> 0 ; > 25 -> (1)
    L4 broad dollar, 12-month change
               < (2)% -> +1 ; (2)% to +5% -> 0 ; > +5% -> (1)

    mean >= 0.5 -> ample ; 0 to 0.5 -> neutral ; (0.5) to 0 -> tightening ;
    <= (0.5) -> stressed

REGIME NAME. Growth crossed with inflation. Liquidity does not enter the name
except through one narrow override, because a liquidity axis wide enough to
rename the regime swallows the growth and inflation reads whenever volatility
rises, which is exactly when the distinction between an overheat and a slump
matters most.

    growth          inflation hot            inflation cool
                    {high, above_target}     {at_target, below_target}
    expansion       overheat                 goldilocks
    slowdown        stagflation_risk         soft_landing
    stall/contract  stagflation              disinflationary_slump

    OVERRIDE -> financial_stress when VIX > 35 AND the credit percentile exceeds
    the 90th. This is a dislocation test, not a drawdown test. It does not fire
    at any of the twenty meeting dates in this window, which is itself reported.

A LIMITATION STATED UP FRONT
------------------------------------------------------------------------------
The ICE BofA OAS series reach this study through the free FRED endpoint, which
serves a rolling three-year window. They begin 2023-07-31, two years after the
study window opens. For the eight meeting dates from 2021-09-30 to 2023-06-30
the L2 indicator is absent and the liquidity mean is taken over three indicators
rather than four. Those dates are marked `oas_available: false` and carry
`liquidity_n_indicators: 3`. Nothing is interpolated across the gap. The BAA10Y
substitute is a yield spread over the Treasury curve rather than an
option-adjusted spread, so its level is not comparable to an OAS; its direction
tracks one closely and it is used on percentile rather than on level for that
reason.
"""

from __future__ import annotations

import datetime as _dt
import json

import pandas as pd

from . import config, pitdata

TARGET_INFLATION = 2.0

# --------------------------------------------------------------------------
# Regime to tilt. Active weights in percentage points of NAV against POLICY.
# Each column sums to zero. Cash policy is 0.00, so no table may carry a
# negative cash tilt: there is no cash to spend, and the funding for a risk-on
# tilt has to come from a line that holds something.
# --------------------------------------------------------------------------
BASE_TILT_PP = {
    "overheat": {
        "us_equity": -2.0, "dev_ex_us": 0.0, "em_equity": -1.0,
        "ust_duration": -3.0, "us_ig": -1.0, "us_hy": 0.0,
        "commodities": 4.0, "listed_re": 0.5, "cash": 2.5,
    },
    "goldilocks": {
        "us_equity": 3.0, "dev_ex_us": 1.0, "em_equity": 2.0,
        "ust_duration": -4.0, "us_ig": -2.0, "us_hy": 1.0,
        "commodities": -1.0, "listed_re": 0.0, "cash": 0.0,
    },
    "stagflation_risk": {
        "us_equity": -2.0, "dev_ex_us": -1.0, "em_equity": -1.0,
        "ust_duration": -1.0, "us_ig": 0.0, "us_hy": -2.0,
        "commodities": 3.0, "listed_re": 0.5, "cash": 3.5,
    },
    "soft_landing": {
        "us_equity": 0.5, "dev_ex_us": 0.5, "em_equity": 0.5,
        "ust_duration": 1.0, "us_ig": 0.5, "us_hy": 0.0,
        "commodities": -2.0, "listed_re": -1.0, "cash": 0.0,
    },
    "stagflation": {
        "us_equity": -4.0, "dev_ex_us": -1.5, "em_equity": -2.0,
        "ust_duration": 0.0, "us_ig": 0.0, "us_hy": -2.0,
        "commodities": 3.0, "listed_re": 1.0, "cash": 5.5,
    },
    "disinflationary_slump": {
        "us_equity": -3.0, "dev_ex_us": -1.5, "em_equity": -2.0,
        "ust_duration": 6.0, "us_ig": 2.0, "us_hy": -2.5,
        "commodities": -1.5, "listed_re": -0.5, "cash": 3.0,
    },
    "financial_stress": {
        "us_equity": -5.0, "dev_ex_us": -2.0, "em_equity": -3.0,
        "ust_duration": 4.0, "us_ig": 1.0, "us_hy": -3.0,
        "commodities": -1.0, "listed_re": -1.0, "cash": 10.0,
    },
}

# Conditional overlays. Each sums to zero and states the condition in its name.
MODIFIERS = {
    "policy_restrictive_easing_priced": {"ust_duration": 2.0, "us_ig": -1.0, "cash": -1.0},
    "policy_loose_tightening_priced": {"ust_duration": -2.0, "cash": 2.0},
    "credit_rich": {"us_hy": -1.5, "cash": 1.5},
    "credit_cheap": {"us_hy": 1.5, "cash": -1.5},
    "dollar_strong": {"em_equity": -1.5, "us_equity": 1.5},
    "dollar_weak": {"em_equity": 1.5, "us_equity": -1.5},
    "breakeven_below_core": {"commodities": 1.5, "ust_duration": -1.5},
}


# --------------------------------------------------------------------------
# small helpers
# --------------------------------------------------------------------------
def _d(x) -> _dt.date:
    if isinstance(x, _dt.datetime):
        return x.date()
    if isinstance(x, _dt.date):
        return x
    return _dt.date.fromisoformat(str(x)[:10])


def _obs(series: pd.Series):
    """Last value and its observation date, or (None, None) if the series is empty."""
    if series is None or not len(series):
        return None, None
    return float(series.iloc[-1]), str(series.index.max().date())


def _entry(value, obs_date, source, **extra) -> dict:
    e = {"value": value, "obs_date": obs_date, "source": source}
    e.update(extra)
    return e


def _later(*dates) -> str | None:
    ds = [d for d in dates if d]
    return max(ds) if ds else None


def _saar(level: pd.Series, i: int = -1):
    """Annualised quarter-on-quarter growth in per cent from a quarterly level."""
    if level is None or len(level) < abs(i) + 1:
        return None
    return float((level.iloc[i] / level.iloc[i - 1]) ** 4 - 1) * 100


def _pct_change(s: pd.Series, periods: int):
    if s is None or len(s) < periods + 1:
        return None
    return float(s.iloc[-1] / s.iloc[-1 - periods] - 1) * 100


def _ann_3m(s: pd.Series):
    if s is None or len(s) < 4:
        return None
    return float((s.iloc[-1] / s.iloc[-4]) ** 4 - 1) * 100


def _sahm_gap(u: pd.Series):
    """3-month mean unemployment rate less its lowest 3-month mean of the prior year."""
    if u is None or len(u) < 15:
        return None
    m3 = u.rolling(3).mean()
    return float(m3.iloc[-1] - m3.iloc[-12:].min())


def _percentile(s: pd.Series, value, lookback_years: int = 10):
    """Percentile of `value` within the trailing history of s. Point in time by
    construction: s has already been truncated at the as-of date by pitdata."""
    if s is None or not len(s) or value is None:
        return None, None
    cut = s.index.max() - pd.DateOffset(years=lookback_years)
    hist = s[s.index >= cut]
    if len(hist) < 60:
        hist = s
    if not len(hist):
        return None, None
    yrs = round((hist.index.max() - hist.index.min()).days / 365.25, 2)
    return round(float((hist < value).mean() * 100), 1), yrs


def _score(x, hi, lo, invert=False):
    """+1 above hi, (1) below lo, 0 between. invert flips the sign."""
    if x is None:
        return None
    s = 1 if x > hi else (-1 if x < lo else 0)
    return -s if invert else s


# --------------------------------------------------------------------------
# the read
# --------------------------------------------------------------------------
def regime_as_of(date) -> dict:
    """
    The regime as it could have been read on `date`, from what was published by
    then. Every entry in `inputs` carries the observation date it came from.
    """
    d = _d(date)
    a = pitdata.as_of(d)
    inp: dict = {}

    # ---------------- growth -------------------------------------------
    gdp = a.macro("GDPC1")
    gdp_saar = _saar(gdp)
    gdp_prev = _saar(gdp, -2)
    gdp_obs = str(gdp.index.max().date()) if len(gdp) else None
    inp["gdp_saar"] = _entry(
        None if gdp_saar is None else round(gdp_saar, 3), gdp_obs, "GDPC1",
        note="annualised quarter on quarter, latest quarter on this vintage")
    inp["gdp_saar_prior_quarter"] = _entry(
        None if gdp_prev is None else round(gdp_prev, 3), gdp_obs, "GDPC1")
    tech_rec = bool(gdp_saar is not None and gdp_prev is not None
                    and gdp_saar < 0 and gdp_prev < 0)
    inp["technical_recession"] = _entry(
        tech_rec, gdp_obs, "GDPC1",
        note="two most recent published quarters both negative on this vintage")

    unrate = a.macro("UNRATE")
    u_val, u_obs = _obs(unrate)
    sahm = _sahm_gap(unrate)
    inp["unemployment_rate"] = _entry(u_val, u_obs, "UNRATE")
    inp["sahm_gap_pp"] = _entry(None if sahm is None else round(sahm, 3), u_obs, "UNRATE",
                                note="3m mean less lowest 3m mean of the prior 12 months")

    pay = a.macro("PAYEMS")
    pay3 = float(pay.diff().iloc[-3:].mean()) if len(pay) > 3 else None
    _, pay_obs = _obs(pay)
    inp["payrolls_3m_avg_k"] = _entry(None if pay3 is None else round(pay3, 1),
                                      pay_obs, "PAYEMS",
                                      note="mean monthly change, thousands")

    indpro = a.macro("INDPRO")
    ip_yoy = _pct_change(indpro, 12)
    _, ip_obs = _obs(indpro)
    inp["indpro_yoy"] = _entry(None if ip_yoy is None else round(ip_yoy, 3),
                               ip_obs, "INDPRO")

    g1 = _score(gdp_saar, 2.0, 0.0)
    g2 = _score(pay3, 150.0, 0.0)
    g3 = _score(sahm, 0.50, 0.20, invert=True)   # a bigger gap is worse
    g4 = _score(ip_yoy, 1.5, -1.5)
    g5 = -1 if tech_rec else 0
    gparts = {"gdp": g1, "payrolls": g2, "sahm": g3, "indpro": g4, "technical_recession": g5}
    G = sum(v for v in gparts.values() if v is not None)
    growth = ("expansion" if G >= 2 else "slowdown" if G >= 0
              else "stall" if G >= -2 else "contraction")
    inp["growth_score"] = _entry(G, _later(gdp_obs, u_obs, pay_obs, ip_obs),
                                 "derived", parts=gparts, range="[-5,+4]")

    # ---------------- inflation ----------------------------------------
    core = a.macro("PCEPILFE")
    core_yoy = _pct_change(core, 12)
    core_3m = _ann_3m(core)
    _, core_obs = _obs(core)
    cpi = a.macro("CPIAUCSL")
    cpi_yoy = _pct_change(cpi, 12)
    _, cpi_obs = _obs(cpi)
    inp["core_pce_yoy"] = _entry(None if core_yoy is None else round(core_yoy, 3),
                                 core_obs, "PCEPILFE")
    inp["core_pce_3m_annualised"] = _entry(None if core_3m is None else round(core_3m, 3),
                                           core_obs, "PCEPILFE")
    inp["cpi_yoy"] = _entry(None if cpi_yoy is None else round(cpi_yoy, 3),
                            cpi_obs, "CPIAUCSL")
    inp["core_pce_vs_target_pp"] = _entry(
        None if core_yoy is None else round(core_yoy - TARGET_INFLATION, 3),
        core_obs, "derived", target=TARGET_INFLATION)

    ladder = ["below_target", "at_target", "above_target", "high"]
    lvl = (3 if core_yoy >= 3.5 else 2 if core_yoy >= 2.8
           else 1 if core_yoy >= 2.0 else 0) if core_yoy is not None else 1
    gap3 = None if (core_3m is None or core_yoy is None) else core_3m - core_yoy
    if gap3 is None:
        direction = "unknown"
    elif gap3 < -0.50:
        direction, lvl = "disinflating", max(0, lvl - 1)
    elif gap3 > 0.50:
        direction, lvl = "reaccelerating", min(3, lvl + 1)
    else:
        direction = "stable"
    inflation = ladder[lvl]
    inp["inflation_direction"] = _entry(direction, core_obs, "derived",
                                        gap_3m_less_yoy=None if gap3 is None else round(gap3, 3))
    inflation_hot = inflation in ("high", "above_target")

    # ---------------- policy -------------------------------------------
    dgs10, o10 = _obs(a.fred("DGS10"))
    dgs2, o2 = _obs(a.fred("DGS2"))
    dgs3m, o3m = _obs(a.fred("DGS3MO"))
    real10, or10 = _obs(a.fred("DFII10"))
    be10, obe = _obs(a.fred("T10YIE"))
    inp["ust_10y"] = _entry(dgs10, o10, "DGS10")
    inp["ust_2y"] = _entry(dgs2, o2, "DGS2")
    inp["ust_3m"] = _entry(dgs3m, o3m, "DGS3MO")
    inp["real_10y"] = _entry(real10, or10, "DFII10")
    inp["breakeven_10y"] = _entry(be10, obe, "T10YIE")

    slope_10y2y = None if None in (dgs10, dgs2) else round(dgs10 - dgs2, 3)
    slope_10y3m = None if None in (dgs10, dgs3m) else round(dgs10 - dgs3m, 3)
    slope_2y3m = None if None in (dgs2, dgs3m) else round(dgs2 - dgs3m, 3)
    inp["slope_10y_2y"] = _entry(slope_10y2y, _later(o10, o2), "derived from DGS10, DGS2")
    inp["slope_10y_3m"] = _entry(slope_10y3m, _later(o10, o3m), "derived from DGS10, DGS3MO")
    inp["slope_2y_3m"] = _entry(slope_2y3m, _later(o2, o3m), "derived from DGS2, DGS3MO",
                                note="the market's near-term policy path: positive prices "
                                     "a higher average rate over two years than today's bill")

    real_policy = None if None in (dgs3m, core_yoy) else round(dgs3m - core_yoy, 3)
    inp["real_policy_rate"] = _entry(real_policy, _later(o3m, core_obs), "derived",
                                     note="3m bill less core PCE year on year")

    p1 = _score(real10, 1.5, 0.5)
    p2 = _score(slope_10y3m, 1.0, 0.0, invert=True)   # inversion is restrictive
    p3 = _score(real_policy, 1.0, 0.0)
    pparts = {"real_10y": p1, "curve_10y_3m": p2, "real_policy_rate": p3}
    P = sum(v for v in pparts.values() if v is not None)
    policy = "restrictive" if P >= 2 else "neutral" if P >= 0 else "accommodative"
    policy_direction = ("unknown" if slope_2y3m is None else
                        "easing_priced" if slope_2y3m < -0.25 else
                        "tightening_priced" if slope_2y3m > 0.25 else "on_hold_priced")
    inp["policy_score"] = _entry(P, _later(or10, o10, o3m, core_obs), "derived",
                                 parts=pparts, range="[-3,+3]")
    inp["policy_direction"] = _entry(policy_direction, _later(o2, o3m), "derived from DGS2, DGS3MO")

    # ---------------- liquidity ----------------------------------------
    baa = a.fred("BAA10Y")
    baa_val, baa_obs = _obs(baa)
    baa_pct, baa_yrs = _percentile(baa, baa_val, 10)
    inp["baa_spread"] = _entry(baa_val, baa_obs, "BAA10Y",
                               percentile=baa_pct, history_years=baa_yrs,
                               note="Moody's Baa yield less 10y Treasury. A yield spread "
                                    "over the curve, not an option-adjusted spread; used on "
                                    "percentile rather than level for that reason")

    hy = a.fred("BAMLH0A0HYM2")
    hy_val, hy_obs = _obs(hy)
    hy_pct, hy_yrs = _percentile(hy, hy_val, 10)
    ig = a.fred("BAMLC0A0CM")
    ig_val, ig_obs = _obs(ig)
    ig_pct, ig_yrs = _percentile(ig, ig_val, 10)
    oas_available = hy_val is not None
    inp["hy_oas"] = _entry(hy_val, hy_obs, "BAMLH0A0HYM2",
                           percentile=hy_pct, history_years=hy_yrs,
                           available=oas_available,
                           note=None if oas_available else
                           "the free FRED endpoint serves a rolling three-year window; this "
                           "series begins 2023-07-31 and does not exist at this date. Not "
                           "interpolated. The liquidity mean is taken over three indicators")
    inp["ig_oas"] = _entry(ig_val, ig_obs, "BAMLC0A0CM",
                           percentile=ig_pct, history_years=ig_yrs,
                           available=ig_val is not None)

    vix, vix_obs = _obs(a.fred("VIXCLS"))
    inp["vix"] = _entry(vix, vix_obs, "VIXCLS")

    usd = a.fred("DTWEXBGS")
    usd_val, usd_obs = _obs(usd)
    usd_12m = None
    if len(usd):
        prior = usd[usd.index <= usd.index.max() - pd.Timedelta(days=365)]
        if len(prior):
            usd_12m = round(float(usd_val / prior.iloc[-1] - 1) * 100, 3)
    inp["dollar_broad"] = _entry(usd_val, usd_obs, "DTWEXBGS", change_12m_pct=usd_12m)

    l1 = _score(baa_pct, 67, 33, invert=True)
    l2 = _score(hy_pct, 67, 33, invert=True)
    l3 = _score(vix, 25, 18, invert=True)
    l4 = _score(usd_12m, 5.0, -2.0, invert=True)
    lparts = {"baa_percentile": l1, "hy_oas_percentile": l2, "vix": l3, "dollar_12m": l4}
    avail = [v for v in lparts.values() if v is not None]
    L = sum(avail) / len(avail) if avail else 0.0
    liquidity = ("ample" if L >= 0.5 else "neutral" if L >= 0
                 else "tightening" if L > -0.5 else "stressed")
    inp["liquidity_score"] = _entry(round(L, 3), _later(baa_obs, hy_obs, vix_obs, usd_obs),
                                    "derived", parts=lparts, n_indicators=len(avail),
                                    range="[-1,+1] mean over available indicators")
    inp["oas_available"] = _entry(oas_available, hy_obs or baa_obs, "derived")

    # ---------------- the name -----------------------------------------
    dislocation = bool(vix is not None and vix > 35
                       and baa_pct is not None and baa_pct > 90)
    if dislocation:
        label = "financial_stress"
    elif growth == "expansion":
        label = "overheat" if inflation_hot else "goldilocks"
    elif growth == "slowdown":
        label = "stagflation_risk" if inflation_hot else "soft_landing"
    else:
        label = "stagflation" if inflation_hot else "disinflationary_slump"
    inp["dislocation_override"] = _entry(dislocation, _later(vix_obs, baa_obs), "derived",
                                         rule="VIX > 35 and credit percentile > 90")

    vintage_note = (
        f"All macro inputs read from the ALFRED vintage current on {d}. "
        f"Real GDP last published quarter {gdp_obs}; unemployment {u_obs}; "
        f"payrolls {pay_obs}; core PCE {core_obs}. Market series are quoted, not "
        f"revised, and are gated at the as-of date. "
        + ("High yield and IG option-adjusted spreads do not exist at this date "
           "(the free endpoint serves a rolling three-year window beginning "
           "2023-07-31); the liquidity read uses three indicators, not four, and "
           "nothing is interpolated across the gap. "
           if not oas_available else "")
        + "No current-vintage (static) input is used in this read, so there is no "
          "anachronism to declare."
    )

    return {
        "growth": growth,
        "inflation": inflation,
        "policy": policy,
        "liquidity": liquidity,
        "regime_label": label,
        "inputs": inp,
        "vintage_note": vintage_note,
        "as_of": d.isoformat(),
    }


# --------------------------------------------------------------------------
# regime -> tilt -> weights
# --------------------------------------------------------------------------
def _active_modifiers(r: dict) -> list[str]:
    inp = r["inputs"]
    out = []
    if r["policy"] == "restrictive" and inp["policy_direction"]["value"] == "easing_priced":
        out.append("policy_restrictive_easing_priced")
    if r["policy"] in ("neutral", "accommodative") and \
            inp["policy_direction"]["value"] == "tightening_priced":
        out.append("policy_loose_tightening_priced")

    pct = inp["hy_oas"]["percentile"] if inp["hy_oas"]["available"] else inp["baa_spread"]["percentile"]
    if pct is not None:
        if pct < 20:
            out.append("credit_rich")
        elif pct > 80:
            out.append("credit_cheap")

    u12 = inp["dollar_broad"]["change_12m_pct"]
    if u12 is not None:
        if u12 > 5.0:
            out.append("dollar_strong")
        elif u12 < -5.0:
            out.append("dollar_weak")

    be, core = inp["breakeven_10y"]["value"], inp["core_pce_yoy"]["value"]
    if be is not None and core is not None and be < core - 1.0:
        out.append("breakeven_below_core")
    return out


def _project(tilt_pp: dict, pinned: frozenset = frozenset()) -> tuple[dict, list[str]]:
    """
    Turn a tilt into weights that respect every line range and sleeve range,
    long only and summing to one. Returns the weights and the bounds that bound.

    Excess is pushed to cash first, because cash is the line the mandate says is
    a real position rather than a residual, and it is the only line whose policy
    weight leaves room in both directions.

    `pinned` lines are held exactly at their policy weight and take no share of
    any residual. That is how config.MIN_TRADE_PP is enforced: a line whose
    surviving position would be smaller than the minimum trade is not traded at
    all, and the projection is then rerun without it rather than being nudged
    back over the threshold by a rounding step.
    """
    w = {k: config.POLICY[k] + tilt_pp.get(k, 0.0) / 100.0 for k in config.LINES}
    for k in pinned:
        w[k] = config.POLICY[k]
    free = [k for k in config.LINES if k not in pinned]
    bound: list[str] = []

    for _ in range(60):
        residual = 0.0
        for k in config.LINES:
            lo, hi = config.RANGE[k]
            if w[k] < lo - 1e-12:
                residual += w[k] - lo
                w[k] = lo
                bound.append(f"line {k} lower {lo:.0%}")
            elif w[k] > hi + 1e-12:
                residual += w[k] - hi
                w[k] = hi
                bound.append(f"line {k} upper {hi:.0%}")

        for sl, (slo, shi) in config.SLEEVE_RANGE.items():
            members = [k for k in config.LINES if config.SLEEVE[k] == sl]
            movable = [k for k in members if k not in pinned]
            tot = sum(w[k] for k in members)
            if tot > shi + 1e-12:
                excess = tot - shi
                room = {k: max(0.0, w[k] - config.RANGE[k][0]) for k in movable}
                tr = sum(room.values())
                if tr > 1e-12:
                    for k in movable:
                        w[k] -= excess * room[k] / tr
                    residual += excess
                    bound.append(f"sleeve {sl} upper {shi:.0%}")
            elif tot < slo - 1e-12:
                short = slo - tot
                room = {k: max(0.0, config.RANGE[k][1] - w[k]) for k in movable}
                tr = sum(room.values())
                if tr > 1e-12:
                    for k in movable:
                        w[k] += short * room[k] / tr
                    residual -= short
                    bound.append(f"sleeve {sl} lower {slo:.0%}")

        residual += 1.0 - sum(w.values())
        if abs(residual) < 1e-10:
            break

        if "cash" not in pinned:
            clo, chi = config.RANGE["cash"]
            take = max(min(w["cash"] + residual, chi), clo) - w["cash"]
            w["cash"] += take
            residual -= take
        if abs(residual) > 1e-10:
            room = {k: (config.RANGE[k][1] - w[k]) if residual > 0
                    else (w[k] - config.RANGE[k][0]) for k in free}
            room = {k: max(0.0, v) for k, v in room.items()}
            tr = sum(room.values())
            if tr <= 1e-12:
                break
            for k in free:
                w[k] += residual * room[k] / tr

    s = sum(w.values())
    if abs(s - 1.0) > 1e-12:
        w["cash"] += 1.0 - s
    return {k: round(w[k], 6) for k in config.LINES}, sorted(set(bound))


def tilt_as_of(date, regime: dict | None = None) -> dict:
    """
    The desk's judgement expressed as active weights in percentage points against
    POLICY. Base table for the regime, plus any modifier whose condition holds,
    then any position smaller than config.MIN_TRADE_PP is set to zero because the
    mandate says a trade that small is not worth the turnover, then the result is
    projected onto the mandate's ranges.
    """
    r = regime if regime is not None else regime_as_of(date)
    base = dict(BASE_TILT_PP[r["regime_label"]])
    mods = _active_modifiers(r)
    for m in mods:
        for k, v in MODIFIERS[m].items():
            base[k] = base.get(k, 0.0) + v

    for k in list(base):
        if abs(base[k]) < config.MIN_TRADE_PP:
            base[k] = 0.0

    # Project, then pin out any line the projection left holding a position
    # smaller than the minimum trade, and project again. Clipping a sleeve moves
    # every line in it, so a position can fall under the minimum after the
    # projection even though it cleared the threshold before it.
    pinned: set[str] = set()
    for _ in range(len(config.LINES) + 1):
        w, bound = _project(base, frozenset(pinned))
        small = {k for k in config.LINES
                 if 1e-9 < abs(w[k] - config.POLICY[k]) * 100 < config.MIN_TRADE_PP}
        if not small - pinned:
            break
        pinned |= small

    active = {k: round((w[k] - config.POLICY[k]) * 100, 4) for k in config.LINES}
    active["_meta"] = {"regime": r["regime_label"], "modifiers": mods,
                       "binding_constraints": bound,
                       "min_trade_pp": config.MIN_TRADE_PP,
                       "untraded_below_min_trade": sorted(pinned)}
    return active


def weights_as_of(date, regime: dict | None = None) -> tuple[dict, list[str], list[str]]:
    r = regime if regime is not None else regime_as_of(date)
    t = tilt_as_of(date, r)
    mods = t["_meta"]["modifiers"]
    bound = t["_meta"]["binding_constraints"]
    w = {k: round(config.POLICY[k] + t[k] / 100.0, 6) for k in config.LINES}
    return w, bound, mods


def regime_path() -> list[dict]:
    """The read, the tilt and the weights at each of the twenty meeting dates."""
    out = []
    for d in config.meeting_dates():
        r = regime_as_of(d)
        t = tilt_as_of(d, r)
        w, bound, mods = weights_as_of(d, r)
        out.append({"date": d.isoformat(), "regime": r,
                    "tilt": {k: v for k, v in t.items() if k != "_meta"},
                    "weights": w, "modifiers": mods, "binding_constraints": bound})
    return out


# --------------------------------------------------------------------------
# what the market is discounting
# --------------------------------------------------------------------------
def priced_as_of(date) -> dict:
    """
    What observable prices are currently discounting. No forecast enters here.
    Assumptions are named at the value they produce.
    """
    d = _d(date)
    a = pitdata.as_of(d)
    y3m, o3m = _obs(a.fred("DGS3MO"))
    y2, o2 = _obs(a.fred("DGS2"))
    y10, o10 = _obs(a.fred("DGS10"))
    be, obe = _obs(a.fred("T10YIE"))
    real, oreal = _obs(a.fred("DFII10"))
    hy, ohy = _obs(a.fred("BAMLH0A0HYM2"))
    ig, oig = _obs(a.fred("BAMLC0A0CM"))

    out: dict = {"as_of": d.isoformat()}

    # Policy path. Assume the overnight rate travels linearly from today's bill
    # to a terminal level over two years, so that the 2y yield is the mean of the
    # path. Terminal = 2 * y2 - y3m. A crude assumption, stated because it is the
    # only thing standing between three yields and a "path".
    if None not in (y3m, y2):
        terminal = 2 * y2 - y3m
        out["policy_path"] = {
            "spot_3m": y3m, "spot_2y": y2,
            "implied_terminal_2y_horizon": round(terminal, 3),
            "implied_change_bp": round((terminal - y3m) * 100, 1),
            "obs_date": _later(o3m, o2),
            "assumption": "the overnight rate travels linearly from the spot 3m bill to a "
                          "terminal level over two years, so the 2y yield equals the mean of "
                          "that path. Terminal = 2*y2 - y3m",
        }
    # 8y rate starting in 2 years, from the 2y and the 10y.
    if None not in (y2, y10):
        f = (((1 + y10 / 100) ** 10 / (1 + y2 / 100) ** 2) ** (1 / 8) - 1) * 100
        out["forward_8y_in_2y"] = {"value": round(f, 3), "obs_date": _later(o2, o10),
                                   "assumption": "annually compounded, from par yields treated "
                                                 "as zero yields. A simplification"}
    if None not in (be, real):
        out["inflation_compensation"] = {"breakeven_10y": be, "real_10y": real,
                                         "nominal_10y_check": round(be + real, 3),
                                         "quoted_nominal_10y": y10,
                                         "obs_date": _later(obe, oreal)}
    # Credit. Decomposition assumptions stated at the number.
    for name, val, obs, rec in (("hy", hy, ohy, 0.40), ("ig", ig, oig, 0.45)):
        if val is None:
            out[f"{name}_credit"] = {"available": False,
                                     "note": "OAS does not exist at this date on the free endpoint"}
            continue
        out[f"{name}_credit"] = {
            "available": True, "oas_pct": val, "obs_date": obs,
            "implied_annual_default_rate_pct": round(val / (1 - rec), 3),
            "recovery_assumption": rec,
            "assumption": f"OAS = default rate x (1 - recovery), recovery {rec:.0%}, and the "
                          f"whole spread is credit loss with no liquidity or risk premium. "
                          f"That upper-bounds the implied default rate: any premium you demand "
                          f"comes out of it",
        }
    # Equity. Dividend yield derived from the divergence between the adjusted and
    # unadjusted close, which is the only route to a yield without a subscription.
    try:
        tr = a.prices(["SPY"], field="adj_close")["SPY"]
        pr = a.prices(["SPY"], field="close")["SPY"]
        tr_y = tr[tr.index <= tr.index.max() - pd.Timedelta(days=365)]
        pr_y = pr[pr.index <= pr.index.max() - pd.Timedelta(days=365)]
        if len(tr_y) and len(pr_y):
            dy = ((tr.iloc[-1] / tr_y.iloc[-1]) / (pr.iloc[-1] / pr_y.iloc[-1]) - 1) * 100
            g_real = 2.0
            out["equity"] = {
                "spy_trailing_12m_dividend_yield_pct": round(float(dy), 3),
                "obs_date": str(tr.index.max().date()),
                "assumed_real_dividend_growth_pct": g_real,
                "real_10y": real,
                "erp_proxy_pct": None if real is None else round(float(dy) + g_real - real, 3),
                "method": "trailing twelve-month dividend yield backed out of the divergence "
                          "between SPY's adjusted and unadjusted close, then a Gordon "
                          "construction: expected real return = D/P + assumed real growth, "
                          "less the 10y TIPS yield",
                "limitation": "a forward earnings yield needs a consensus estimate feed behind "
                              "a subscription, which IPS 4.4 puts out of scope. A trailing "
                              "dividend yield understates the cash returned by an index that "
                              "distributes heavily through buybacks, so this proxy is "
                              "conservative and its level should not be compared to a "
                              "published forward ERP",
            }
    except Exception as e:  # pragma: no cover
        out["equity"] = {"error": f"{type(e).__name__}: {e}"}
    return out


# --------------------------------------------------------------------------
# the 2022 Q2 demonstration
# --------------------------------------------------------------------------
def gdp_vintage_demonstration() -> dict:
    """
    2022 Q2 real GDP, as published on the day and as it reads now.

    Compared as annualised growth rates rather than as levels, because the BEA
    rebased the chained-dollar index between these vintages and the levels are in
    different units. A level comparison across a rebasing measures the rebasing.
    """
    q1, q2 = "2022-01-01", "2022-04-01"

    def rates(vintage: str) -> dict:
        s = pitdata.as_of(vintage).macro("GDPC1")
        out = {"vintage": vintage, "last_published_quarter": str(s.index.max().date())}
        for tag, q in (("2022Q1", q1), ("2022Q2", q2)):
            ts = pd.Timestamp(q)
            if ts not in s.index:
                out[tag] = None
                out[f"{tag}_level"] = None
                continue
            i = s.index.get_loc(ts)
            out[tag] = round(float((s.iloc[i] / s.iloc[i - 1]) ** 4 - 1) * 100, 4)
            out[f"{tag}_level"] = round(float(s.iloc[i]), 3)
        a, b = out.get("2022Q1"), out.get("2022Q2")
        out["two_consecutive_negative_quarters"] = (
            None if (a is None or b is None) else bool(a < 0 and b < 0))
        return out

    vintages = sorted(set([d.isoformat() for d in config.meeting_dates()]
                          + [config.REPORT_DATE.isoformat()]
                          + ["2022-04-28", "2022-07-28", "2022-08-25",
                             "2022-09-29", "2024-09-25", "2024-09-26"]))
    series = [rates(v) for v in vintages]

    first = next(r for r in series if r["vintage"] == "2022-07-28")
    now = next(r for r in series if r["vintage"] == config.REPORT_DATE.isoformat())

    crossed, prev = None, None
    for r in series:
        if r["2022Q2"] is None:
            continue
        if prev is not None and prev < 0 <= r["2022Q2"]:
            crossed = r["vintage"]
            break
        prev = r["2022Q2"]

    last_neg = None
    for r in series:
        if r["2022Q2"] is not None and r["2022Q2"] < 0:
            last_neg = r["vintage"]

    d0 = _dt.date.fromisoformat("2022-07-28")
    d1 = _dt.date.fromisoformat(crossed) if crossed else None

    return {
        "claim": "US real GDP for 2022 Q2 was first published as a contraction on "
                 "28 July 2022 and reads as growth today. The revision did not cross "
                 "zero until an annual benchmark revision more than two years later.",
        "verdict": "CONFIRMED" if (first["2022Q2"] is not None and now["2022Q2"] is not None
                                   and first["2022Q2"] < 0 <= now["2022Q2"]) else "NOT CONFIRMED",
        "as_first_published": {
            "vintage": "2022-07-28",
            "release": "BEA advance estimate of 2022 Q2 real GDP",
            "q2_2022_saar_pct": first["2022Q2"],
            "q1_2022_saar_pct": first["2022Q1"],
            "two_consecutive_negative_quarters": first["two_consecutive_negative_quarters"],
        },
        "as_it_reads_now": {
            "vintage": config.REPORT_DATE.isoformat(),
            "q2_2022_saar_pct": now["2022Q2"],
            "q1_2022_saar_pct": now["2022Q1"],
            "two_consecutive_negative_quarters": now["two_consecutive_negative_quarters"],
        },
        "sign_crossed_on_vintage": crossed,
        "last_vintage_still_negative": last_neg,
        "days_wrong": (d1 - d0).days if d1 else None,
        "revision_pp": (None if (first["2022Q2"] is None or now["2022Q2"] is None)
                        else round(now["2022Q2"] - first["2022Q2"], 4)),
        "level_comparison_refused": (
            "The chained-dollar level moved from 19,895.271 on the 2022-07-28 vintage to "
            "21,967.045 today. Almost all of that is the 2023 rebasing of the chained index "
            "from 2012 to 2017 dollars, not a revision to activity. The comparison is made on "
            "annualised growth rates for that reason."),
        "nber": "The NBER has never dated a recession beginning in 2022. USREC reads 0 "
                "throughout 2021 and 2022 on the current vintage. The two-negative-quarters "
                "heuristic and the NBER's dating disagreed then and disagree now.",
        "series": series,
    }


def vintage_counterfactual(date=_dt.date(2022, 9, 30)) -> dict:
    """
    What this framework would have read at `date` if the GDP input came from
    today's vintage instead of the one published by then, holding every other
    input at its point-in-time value.

    This is an anachronism on purpose. It is the backtest the office is not
    running, computed so the Committee can see the size of the error rather than
    be told it is large. Only the GDP-derived inputs are swapped; substituting
    the whole current vintage would confound the GDP revision with revisions to
    payrolls and to the price indices.
    """
    d = _d(date)
    pit = regime_as_of(d)

    cur = pitdata.as_of(config.REPORT_DATE).macro("GDPC1")
    cur = cur[cur.index <= pd.Timestamp(pit["inputs"]["gdp_saar"]["obs_date"])]
    g_now, g_prev_now = _saar(cur), _saar(cur, -2)
    tech_now = bool(g_now is not None and g_prev_now is not None
                    and g_now < 0 and g_prev_now < 0)

    i = pit["inputs"]
    parts = dict(i["growth_score"]["parts"])
    parts["gdp"] = _score(g_now, 2.0, 0.0)
    parts["technical_recession"] = -1 if tech_now else 0
    G = sum(v for v in parts.values() if v is not None)
    growth = ("expansion" if G >= 2 else "slowdown" if G >= 0
              else "stall" if G >= -2 else "contraction")
    hot = pit["inflation"] in ("high", "above_target")
    label = ({"expansion": "overheat" if hot else "goldilocks",
              "slowdown": "stagflation_risk" if hot else "soft_landing"}
             .get(growth, "stagflation" if hot else "disinflationary_slump"))

    w_pit, _, _ = weights_as_of(d, pit)
    cf_regime = dict(pit)
    cf_regime["growth"], cf_regime["regime_label"] = growth, label
    w_cf, _, _ = weights_as_of(d, cf_regime)

    return {
        "date": d.isoformat(),
        "point_in_time": {
            "gdp_saar": i["gdp_saar"]["value"],
            "gdp_saar_prior_quarter": i["gdp_saar_prior_quarter"]["value"],
            "technical_recession": i["technical_recession"]["value"],
            "growth_score": i["growth_score"]["value"],
            "growth": pit["growth"], "regime_label": pit["regime_label"],
            "weights": w_pit,
        },
        "current_vintage_counterfactual": {
            "gdp_saar": None if g_now is None else round(g_now, 3),
            "gdp_saar_prior_quarter": None if g_prev_now is None else round(g_prev_now, 3),
            "technical_recession": tech_now,
            "growth_score": G, "growth": growth, "regime_label": label,
            "weights": w_cf,
        },
        "weight_difference_pp": {k: round((w_cf[k] - w_pit[k]) * 100, 2)
                                 for k in config.LINES},
        "note": "An acknowledged anachronism, computed to size the error. The GDP "
                "inputs are taken from the current vintage and every other input is "
                "left at its point-in-time value, so the difference is attributable "
                "to the GDP revision alone.",
    }


# --------------------------------------------------------------------------
# outputs
# --------------------------------------------------------------------------
MACRO_OUT = config.OUTPUTS / "macro"

CONVICTION = {
    "us_equity": "medium", "dev_ex_us": "none", "em_equity": "low",
    "ust_duration": "high", "us_ig": "low", "us_hy": "medium",
    "commodities": "high", "listed_re": "none", "cash": "high",
}

RATIONALE = (
    "Overheat. Growth is expansion on the 30 June vintage (growth score 4 of a "
    "possible 4: real GDP 2.09% annualised for 2026 Q1, payrolls averaging 188k "
    "over three months, a Sahm gap of 0.10pp, industrial production 1.67% year on "
    "year), and inflation is above target and firming (core PCE 3.41% year on year "
    "with a 3.52% three-month annualised run rate). The position that follows is "
    "not a growth call. It is a call on the price of two things. First, policy: the "
    "3-month bill at 3.87% against core PCE at 3.41% is a real policy rate of "
    "0.46%, below any plausible neutral, so the stance is neutral rather than "
    "restrictive and the disinflation consensus expects has to arrive without help "
    "from the Fed. Second, inflation compensation: a 10-year breakeven of 2.24% "
    "prices CPI at 2.24% for a decade, below the Survey of Professional "
    "Forecasters' own 2.40% long-run median, while realised core runs 3.41%. The "
    "portfolio is therefore short nominal duration (6.5pp), long commodities to the "
    "line limit (5.0pp) and long cash (7.0pp), which is the only line paid to wait "
    "while the curve prices 54bp of tightening over two years. Credit is trimmed "
    "(1.5pp of high yield) because a 2.80% option-adjusted spread at the 17th "
    "percentile of its available history leaves roughly 70bp over a long-run "
    "expected loss. US equity is trimmed 2pp on the price of the entry rather than "
    "on the outlook: the dividend-based equity risk premium proxy is 0.91%, the "
    "lowest of the twenty meeting dates and down from 4.26% at the first. "
    "Developed ex-US and listed real estate are held at policy because this desk "
    "has no view on them, and a desk with a view on all nine lines has a view on "
    "none of them."
)


def build_outputs() -> dict:
    """Write everything the CIO consumes. Returns a summary for the console."""
    MACRO_OUT.mkdir(parents=True, exist_ok=True)
    asof = config.WINDOW_END

    r = regime_as_of(asof)
    w, bound, mods = weights_as_of(asof, r)
    t = tilt_as_of(asof, r)

    allocation = {
        "as_of": asof.isoformat(),
        "regime": r["regime_label"],
        "regime_axes": {k: r[k] for k in ("growth", "inflation", "policy", "liquidity")},
        "weights": w,
        "active_vs_policy": {k: t[k] for k in config.LINES},
        "binding_constraint": (bound[0] if bound else "none"),
        "binding_constraints_all": bound,
        "untraded_below_min_trade": t["_meta"]["untraded_below_min_trade"],
        "modifiers_applied": mods,
        "conviction": CONVICTION,
        "rationale": RATIONALE,
        "sleeves": {sl: round(sum(w[k] for k in config.LINES if config.SLEEVE[k] == sl), 6)
                    for sl in config.SLEEVE_RANGE},
        "tracking_error_note": (
            f"Ex-ante tracking error against the policy portfolio is not computed here. It "
            f"requires a covariance matrix, which is a risk model, which is the Quantitative "
            f"desk's instrument and not this desk's. If this tilt breaches the "
            f"{config.TE_BUDGET_BPS:.0f}bp budget it is truncated to the constraint under IPS "
            f"3.6 rank 4, by the mandate rather than by argument."),
        "vintage_note": r["vintage_note"],
    }
    (MACRO_OUT / "allocation.json").write_text(
        json.dumps(allocation, indent=2), encoding="utf-8")

    path = regime_path()
    (MACRO_OUT / "macro_path.json").write_text(
        json.dumps(path, indent=2, default=str), encoding="utf-8")

    demo = gdp_vintage_demonstration()
    (MACRO_OUT / "gdp_vintage_demo.json").write_text(
        json.dumps(demo, indent=2, default=str), encoding="utf-8")

    (MACRO_OUT / "counterfactual.json").write_text(
        json.dumps(vintage_counterfactual(), indent=2, default=str), encoding="utf-8")

    priced = {d.isoformat(): priced_as_of(d) for d in
              (config.WINDOW_END, config.REPORT_DATE)}
    (MACRO_OUT / "priced.json").write_text(
        json.dumps(priced, indent=2, default=str), encoding="utf-8")

    return {"allocation": allocation, "path_len": len(path), "demo": demo}


def main() -> int:
    r = regime_as_of(config.WINDOW_END)
    print(f"Regime read, as of {r['as_of']}")
    for k in ("growth", "inflation", "policy", "liquidity", "regime_label"):
        print(f"  {k:14s} {r[k]}")
    print(f"\n  {r['vintage_note']}\n")
    w, bound, mods = weights_as_of(config.WINDOW_END, r)
    print(f"  modifiers: {mods}")
    print(f"  binding:   {bound or 'none'}")
    print(f"\n  {'line':14s} {'policy':>8s} {'weight':>8s} {'active pp':>10s}")
    for k in config.LINES:
        print(f"  {k:14s} {config.POLICY[k]:8.2%} {w[k]:8.2%} "
              f"{(w[k]-config.POLICY[k])*100:+10.2f}")
    print(f"  {'TOTAL':14s} {'':8s} {sum(w.values()):8.2%}")
    demo = gdp_vintage_demonstration()
    print(f"\n2022 Q2 GDP vintage demonstration: {demo['verdict']}")
    print(f"  as first published (2022-07-28 vintage) {demo['as_first_published']['q2_2022_saar_pct']:+.4f}% saar")
    print(f"  as it reads now    ({demo['as_it_reads_now']['vintage']} vintage) "
          f"{demo['as_it_reads_now']['q2_2022_saar_pct']:+.4f}% saar")
    print(f"  sign crossed on vintage {demo['sign_crossed_on_vintage']} "
          f"after {demo['days_wrong']} days")
    s = build_outputs()
    print(f"\nWrote {MACRO_OUT} ({s['path_len']} meeting dates)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
