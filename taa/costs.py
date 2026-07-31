"""
taa.costs -- transaction cost vector and rebalancing corridors for the
Ashcroft University Endowment (USD 850,000,000, perpetual, daily-liquid only).

===========================================================================
UNIT CONTRACT. READ THIS BEFORE CALLING ANYTHING IN THIS MODULE.
===========================================================================

    THIS MODULE WORKS IN PERCENTAGE POINTS OF NAV, NOT FRACTIONS.

    A 38% policy weight is 38.0 here. It is NOT 0.38.
    MIN_TRADE_PP is 0.50, meaning 50bp of NAV, meaning USD 4,250,000.

The rest of the investment office works in fractions, where the same weight
is 0.38. Both conventions are defensible and this module does not change.
The boundary between them is the thing that has to be visible, so it is
stated here and repeated in desks/implementation.md.

The concrete failure this prevents: a caller passing fractional weights
hands apply_min_trade a 60bp trade as 0.006, which is compared against a
0.50 minimum, suppressed, and returned as a hold. The result is internally
valid before and after, so neither a look-ahead test nor a compliance test
catches it. Every decision comes back as "no trade" and the reasoning
written around that outcome is reasoning about an arithmetic error.

Conversion adapter lives at the top of taa/simulate.py. Boundary assertions
live in tests/check_units.py. Do not convert inline at call sites.

Signature by signature:

    NAME                    TAKES                 RETURNS
    --------------------    ------------------    ---------------------
    POLICY_PP               (constant)            pp of NAV
    RANGE_PP                (constant)            pp of NAV, (low, high)
    CORRIDOR_PP             (constant)            pp of NAV, half-width
    MIN_TRADE_PP            (constant)            pp of NAV  (0.50)
    ONE_WAY_BPS             (constant)            bps of TRADED NOTIONAL
    QUOTED_SPREAD_BPS       (constant)            bps of traded notional
    ACTIVE_VOL_PCT          (constant)            annualised %, not pp
    round_trip_cost         pp of NAV             ->  bps of NAV
    turnover_pp             pp of NAV             ->  pp of NAV
    trades_pp               pp of NAV             ->  pp of NAV, signed
    apply_min_trade         pp of NAV             ->  pp of NAV
    band                    line key              ->  pp of NAV, (low, high)
    breaches                pp of NAV             ->  pp of NAV, signed
    range_breaches          pp of NAV             ->  pp of NAV
    drift_te_bps            pp of NAV             ->  bps
    corridor_te_bps         (none)                ->  bps
    usd                     pp of NAV             ->  USD

Note the two asymmetric ones, because they are the easiest to misread:
round_trip_cost TAKES percentage points of NAV and RETURNS basis points of
NAV, and drift_te_bps does the same. Everything named *_pp is percentage
points on both sides. Everything named *_bps returns basis points.

===========================================================================

Owner: Implementation & Operations desk. Adopted 28 July 2026.
Governing document: Investment Policy Statement v7.2, effective 1 July 2026.

Standard library only. No third-party imports. Runs on any Python 3.8+.

--------------------------------------------------------------------------
WHAT THIS MODULE IS FOR
--------------------------------------------------------------------------
Other desks import ONE_WAY_BPS to price the turnover implied by a proposed
allocation, and CORRIDOR_PP to test whether a drift is actionable. Both are
adopted numbers, not estimates to be re-derived per proposal. If a desk
disagrees with a number it changes this file and re-runs
tests/check_implementation.py, so that the change is visible.

--------------------------------------------------------------------------
GLOSSARY
--------------------------------------------------------------------------
bps           basis points, 1bp = 0.01%
pp            percentage points of NAV. 1pp of NAV = USD 8,500,000.
              A weight of 38% is written 38.0, never 0.38. See the unit
              contract at the top of this docstring.
one-way       the cost of executing a single buy OR a single sell. A
              rebalance that sells one line and buys another pays one-way
              cost on BOTH legs.
ONE_WAY_BPS   bps of the traded notional, not bps of NAV.
CORRIDOR_PP   half-width of the no-trade band, in pp of NAV, measured from
              the line's policy weight.

--------------------------------------------------------------------------
SOURCES FOR EVERY NUMBER
--------------------------------------------------------------------------
Bid-ask spreads are the 30-day median bid-ask spread published by the issuer
under SEC Rule 6c-11(c)(1)(v), which requires an ETF to post on its website
the median bid-ask spread over the most recent 30 calendar days, computed
from the NBBO sampled at the end of each 10-second interval.
    https://www.sec.gov/about/divisions-offices/division-investment-management/accounting-disclosure-information/adi-2025-15-website-posting-requirements

All spreads, expense ratios, premiums and discounts below were pulled on
28 July 2026 and carry an issuer as-of date of 27 July 2026. Dollar average
daily volume is the median of (close x volume) over the 60 US trading
sessions ended 28 July 2026, from the Yahoo Finance public chart endpoint.
Three-year active volatility is the annualised standard deviation of the
line's daily log return minus the policy portfolio's daily log return, over
the 750 common sessions from 31 July 2023 to 28 July 2026, same source.

Per-vehicle detail, with URLs and VERIFIED / RECALLED status, is in
outputs/implementation.json. The narrative build-up is in
desks/implementation.md.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# The nine policy lines. Order is the IPS Section 4.1 order.
# ---------------------------------------------------------------------------

LINES = [
    "us_equity",
    "dev_ex_us",
    "em_equity",
    "ust_duration",
    "us_ig",
    "us_hy",
    "commodities",
    "listed_re",
    "cash",
]

# ---------------------------------------------------------------------------
# Policy weights and permitted ranges. IPS v7.2 Section 4.1, page 5.
# These bind independently of the tracking-error budget: a position inside
# the TE budget but outside its range is a breach.
# ---------------------------------------------------------------------------

POLICY_PP = {
    "us_equity": 38.0,
    "dev_ex_us": 20.0,
    "em_equity": 12.0,
    "ust_duration": 12.0,
    "us_ig": 8.0,
    "us_hy": 5.0,
    "commodities": 3.0,
    "listed_re": 2.0,
    "cash": 0.0,
}

RANGE_PP = {
    "us_equity": (28.0, 48.0),
    "dev_ex_us": (12.0, 28.0),
    "em_equity": (5.0, 19.0),
    "ust_duration": (5.0, 22.0),
    "us_ig": (3.0, 13.0),
    "us_hy": (0.0, 10.0),
    "commodities": (0.0, 8.0),
    "listed_re": (0.0, 6.0),
    "cash": (0.0, 10.0),
}

NAV_USD = 850_000_000.0

# IPS v7.2 Section 4.2, page 5: "Minimum trade 50bps. Anything smaller does
# not justify the turnover." Expressed here in pp of NAV, so 0.50pp =
# USD 4,250,000.
MIN_TRADE_PP = 0.50

# IPS v7.2 Section 4.2: 200bps ex ante tracking error against the policy
# portfolio. Used below only to size the corridor set, not enforced here.
TE_BUDGET_BPS = 200.0


# ---------------------------------------------------------------------------
# PRIMARY VEHICLES
#
# One vehicle per line is designated primary. The primary is the vehicle the
# desk actually holds and trades in normal size; the alternate is the deeper
# book used when size or urgency demands it. Where the IPS names two vehicles
# the primary is the cheaper one to HOLD, because a perpetual fund pays the
# expense ratio every year and the spread only on turnover. Holding VTI over
# SPY saves 6.45bp a year on 38% of NAV, roughly USD 2.08m a year, against a
# one-off spread difference measured in tenths of a basis point.
# ---------------------------------------------------------------------------

PRIMARY_VEHICLE = {
    "us_equity": "VTI",       # alternate SPY, deepest book in the world
    "dev_ex_us": "VEA",       # alternate EFA
    "em_equity": "VWO",       # alternate EEM
    "ust_duration": "IEF",    # alternate TLT for long-end duration tilts
    "us_ig": "LQD",           # only vehicle named at IPS 4.1
    "us_hy": "HYG",           # only vehicle named at IPS 4.1
    "commodities": "DBC",     # alternate GSG
    "listed_re": "VNQ",       # only vehicle named at IPS 4.1
    "cash": "SGOV",           # alternate BIL
}

# Quoted 30-day median bid-ask spread of the PRIMARY vehicle, in bps, as
# published by the issuer on 27 July 2026. This is the full quoted spread;
# the half-spread is the minimum plausible one-way cost and is the floor the
# check in tests/check_implementation.py enforces against ONE_WAY_BPS.
#
# Sources, all VERIFIED 28 July 2026:
#   VTI  0.0055%  Vanguard 30-day median bid/ask spread service
#                 https://advisors.vanguard.com/investments/bidaskspread
#   VEA  0.0142%  same
#   VWO  0.0170%  same
#   VNQ  0.0102%  same
#   IEF  0.01%    https://www.ishares.com/us/products/239456/ishares-7-10-year-treasury-bond-etf
#   LQD  0.01%    https://www.ishares.com/us/products/239566/ishares-iboxx-investment-grade-corporate-bond-etf
#   HYG  0.01%    https://www.ishares.com/us/products/239565/ishares-iboxx-high-yield-corporate-bond-etf
#   SGOV 0.01%    https://www.ishares.com/us/products/314116/ishares-0-3-month-treasury-bond-etf
#   DBC  0.04%    https://www.invesco.com/us/financial-products/etfs/product-detail?audienceType=Investor&ticker=DBC
#
# iShares and Invesco round the published figure to two decimal places in
# percent, so "0.01%" is a rounded value and the true median lies inside
# roughly 0.5bp to 1.5bp. Vanguard publishes to eight decimal places, which
# is why the Vanguard vehicles carry sub-basis-point figures here. SPY's
# published figure is 0.00%, meaning below 0.005%; a one-cent spread on a
# USD 739 share is 0.135bp, which is consistent.
QUOTED_SPREAD_BPS = {
    "us_equity": 0.55,
    "dev_ex_us": 1.42,
    "em_equity": 1.70,
    "ust_duration": 1.00,
    "us_ig": 1.00,
    "us_hy": 1.00,
    "commodities": 4.00,
    "listed_re": 1.02,
    "cash": 1.00,
}


# ---------------------------------------------------------------------------
# THE ADOPTED ONE-WAY COST VECTOR
#
# Built as: half of the quoted spread, plus the market maker's risk premium
# for the exposure the ETF wrapper cannot hedge cleanly during US hours, plus
# the primary-market frictions (creation fee, underlying basket spread, the
# roll for the commodity vehicles) that bind at USD 8.5m and above.
#
# The half-spread is a floor, never the answer. Angel, Broms and Gastineau
# (2016), "ETF Transaction Costs Are Often Higher Than Investors Realize",
# Journal of Portfolio Management 42(3), Spring 2016, pp. 65-75, show for EEM
# that a screen spread "of about 3 basis points" sat alongside a closing price
# that "deviated from the NAV by an average of 48 basis points" through 2014,
# median 15bp, with 5% of observations at 136bp or worse. Their conclusion,
# verbatim: "the cost to trade most index ETFs is more than a few basis
# points."
#   https://centerforfinancialstability.org/etfs/ETFAnalysis/etf-trans-costs-are-often-higher-than-inv-realize-spring2016.pdf
#
# Sizing context. A 100bp allocation move is USD 8,500,000. As a share of the
# 60-session median dollar ADV to 28 July 2026:
#   SPY  0.02%   VTI  0.73%   LQD  0.29%   HYG  0.35%   TLT  0.42%
#   SGOV 0.45%   EEM  0.47%   EFA  0.63%   VEA  1.16%   IEF  1.54%
#   VWO  1.88%   VNQ  2.79%   DBC 31.1%    GSG 41.1%
# The commodity line is the only one where a single tactical move is a
# material fraction of a day's trading. Every other line absorbs it inside
# the first hour.
# ---------------------------------------------------------------------------

ONE_WAY_BPS = {
    # 0.28bp half-spread. Underlying is 3,500 US listed equities with penny
    # spreads and a futures hedge available continuously. USD 8.5m is 0.7% of
    # VTI ADV and 0.02% of SPY ADV. 1.5bp is conservative for this line and
    # is set there so the vector never flatters the cheapest trade.
    "us_equity": 1.50,
    # 0.71bp half-spread. Europe and Japan are closed when the US trades, so
    # the market maker carries overnight beta and FX and prices it in. VEA's
    # premium to NAV was +0.16% and EFA's +0.22% on 27 July 2026, which is a
    # stale-NAV artefact rather than a cost, but it is the same mechanism that
    # makes the effective cost several times the screen spread.
    "dev_ex_us": 4.00,
    # 0.85bp half-spread. Same overnight problem plus emerging FX, settlement
    # frictions and a basket that cannot be fully hedged intraday. Angel et al.
    # measure EEM's realised deviation from NAV at 48bp average, and the desk
    # has no evidence it trades inside a third of that at size.
    "em_equity": 8.00,
    # 0.50bp half-spread. Underlying is on-the-run and near-on-the-run US
    # Treasuries, the deepest cash bond market there is. The wrapper adds
    # little. 3bp allows for the creation fee and a wider screen on a rate
    # event day.
    "ust_duration": 6.00 / 2,
    # 0.50bp half-spread on a fund holding 3,144 corporate bonds whose own
    # round-lot spreads run tens of basis points. The secondary market absorbs
    # USD 8.5m easily (0.29% of LQD's USD 2.9bn ADV), so the desk pays the
    # ETF's spread and not the basket's, but the gap between the two is the
    # reason the adopted number is four times the half-spread.
    "us_ig": 6.00,
    # 0.50bp half-spread on 1,328 high yield bonds. Underlying HY round-lot
    # spreads are wider again, and in stress the ETF is the price-discovery
    # instrument and its own spread widens by a multiple. 12bp is the adopted
    # normal-market figure; the desk assumes 3x in a stressed tape.
    "us_hy": 12.00,
    # 2.00bp half-spread, and the only line where secondary liquidity is a
    # real constraint: USD 8.5m is 31% of DBC's USD 27.3m median dollar ADV
    # and a full 3pp move to zero is USD 25.5m, close to a full day. DBC also
    # closed at a 43.5bp discount to NAV on 27 July 2026 and GSG at a 50bp
    # discount, on a day the index fell 3%. Creation against futures is the
    # release valve, and it carries the creation fee and the futures roll.
    "commodities": 25.00,
    # 0.51bp half-spread. Underlying is roughly 160 listed US REITs, liquid
    # listed equities. USD 8.5m is 2.8% of VNQ's USD 305m ADV.
    "listed_re": 5.00,
    # 0.50bp half-spread on 0-3 month Treasury bills. Effectively frictionless;
    # kept at 1bp rather than zero so that no optimiser treats cash as a free
    # place to park risk.
    "cash": 1.00,
}
# ust_duration is written as 6.00/2 above to make the arithmetic visible;
# normalise it so downstream code sees a plain float.
ONE_WAY_BPS["ust_duration"] = 3.00


# ---------------------------------------------------------------------------
# RISK INPUTS FOR CORRIDOR SIZING
#
# ACTIVE_VOL_PCT is the annualised standard deviation of the line's daily log
# return minus the policy portfolio's daily log return, 750 common sessions
# 31 July 2023 to 28 July 2026, computed from Yahoo Finance adjusted closes on
# the primary vehicles, policy portfolio built at the IPS 4.1 weights. The
# policy portfolio's own realised volatility over the same window was 11.10%.
#
# This single statistic carries all five of the corridor determinants the CFA
# Institute curriculum lists, and carries them in the right direction:
#   higher asset-class volatility  -> higher active vol -> narrower corridor
#   higher volatility of the rest  -> higher active vol -> narrower corridor
#   higher correlation with the rest-> lower active vol -> wider corridor
# leaving transaction cost and risk tolerance to enter separately below.
#   https://www.cfainstitute.org/insights/professional-learning/refresher-readings/2026/principles-asset-allocation
#
# A drift of c pp in line i moves ex-post tracking error by approximately
# c/100 x ACTIVE_VOL_PCT[i], which is how the TE column in the corridor table
# in desks/implementation.md is computed.
# ---------------------------------------------------------------------------

ACTIVE_VOL_PCT = {
    "us_equity": 6.26,     # VTI
    "dev_ex_us": 6.90,     # VEA
    "em_equity": 9.26,     # VWO
    "ust_duration": 11.10,  # IEF
    "us_ig": 9.51,         # LQD
    "us_hy": 7.39,         # HYG
    "commodities": 18.70,  # DBC
    "listed_re": 13.17,    # VNQ
    "cash": 11.11,         # SGOV
}


# ---------------------------------------------------------------------------
# THE ADOPTED CORRIDOR TABLE
#
# Half-width of the no-trade band, in pp of NAV, measured from the policy
# weight. Rule, applied mechanically and then rounded to the nearest 0.25pp:
#
#     c_i = clip( 5 * (ONE_WAY_BPS[i] ** (1/3)) / ACTIVE_VOL_PCT[i],
#                 floor = MIN_TRADE_PP,
#                 cap   = min( 0.25 * POLICY_PP[i], 0.80 * distance to the
#                              nearer edge of the IPS range ) )
#
# The cube root on transaction cost is Leland's result, not a convenience.
# Leland, Hayne E. (December 1999), "Optimal Portfolio Management with
# Transactions Costs and Capital Gains Taxes", Haas School of Business
# working paper RPF-290, free at https://escholarship.org/uc/item/0fw6k0hm :
# "The size of the optimal no-trade interval (w_max - w_min) is proportional
# to the cube root of transactions costs", so "doubling transactions costs
# will increase the no-trade interval by a factor of about 2^(1/3) = 1.26."
# The same exponent falls out of Constantinides (1986) and Davis and Norman
# (1990), where the no-trade band width is O(eps^(1/3)) in the proportional
# cost eps.
#
# The 25%-of-policy-weight cap is the relative leg of the practitioner 5/25
# rule and is what stops a small line carrying an absurd relative band. The
# 50bp floor is the IPS minimum trade at Section 4.2: a corridor narrower
# than the minimum trade cannot be acted on, because breaching it by
# definition generates a trade smaller than the minimum.
#
# Constant 5 was set so that the aggregate drift-induced tracking error, with
# every line simultaneously at its corridor edge, is about 27bp, roughly one
# seventh of the 200bp budget. The rest of the budget is reserved for
# deliberate views rather than consumed by drift the desk chose not to fix.
#
# Cash is a special case and is documented as one. Its policy weight is 0%
# and its range floor is 0%, so a symmetric band is impossible. Cash carries
# a one-sided upward band of 0.50pp: cash may accumulate to 0.50% of NAV from
# distributions and dividends without action, and any deliberate cash holding
# above that is a tactical position governed by the tracking-error budget,
# not by this table.
# ---------------------------------------------------------------------------

CORRIDOR_PP = {
    "us_equity": 1.00,     # rule 0.91, cap 9.50 -> 1.00. Band 37.00-39.00
    "dev_ex_us": 1.25,     # rule 1.15, cap 5.00 -> 1.25. Band 18.75-21.25
    "em_equity": 1.00,     # rule 1.08, cap 3.00 -> 1.00. Band 11.00-13.00
    "ust_duration": 0.75,  # rule 0.65, cap 3.00 -> 0.75. Band 11.25-12.75
    "us_ig": 1.00,         # rule 0.96, cap 2.00 -> 1.00. Band  7.00- 9.00
    "us_hy": 1.25,         # rule 1.55, cap 1.25 -> 1.25. Band  3.75- 6.25
    "commodities": 0.75,   # rule 0.78, cap 0.75 -> 0.75. Band  2.25- 3.75
    "listed_re": 0.50,     # rule 0.65, cap 0.50 -> 0.50. Band  1.50- 2.50
    "cash": 0.50,          # rule 0.45, floor binds -> 0.50. Band 0.00-0.50
}

# Lines whose band is one-sided because the policy weight sits on the edge of
# the IPS range. Only cash qualifies. Documented rather than hidden so that
# the containment check in tests/check_implementation.py can test the one
# side that exists rather than silently pass a side that does not.
ONE_SIDED_UP = {"cash"}


# ---------------------------------------------------------------------------
# FUNCTIONS
# ---------------------------------------------------------------------------


def _check_line(line: str) -> None:
    if line not in ONE_WAY_BPS:
        raise KeyError(
            f"unknown line {line!r}; expected one of {', '.join(LINES)}"
        )


def round_trip_cost(trades_pp: dict) -> float:
    """Cost, in bps of NAV, of executing a set of one-way trades.

    UNITS: takes percentage points of NAV, returns basis points of NAV.
    The input and the output are in different units and that is deliberate.
    A 2pp trade is 2.0, never 0.02.

    ``trades_pp`` maps a line key to the size of the trade in percentage
    points of NAV. Sign is ignored: a 2pp sale costs the same as a 2pp
    purchase, because ONE_WAY_BPS is symmetric on this fund's vehicles.

    A rebalance is normally passed in whole, both the sells and the buys, so
    the returned figure is the full round-trip cost of that rebalance. The
    function is named for that use.

    Arithmetic: a trade of x pp of NAV in a line costing c bps of notional
    costs (x / 100) * c bps of NAV.

        >>> round(round_trip_cost({"us_equity": 1.0, "cash": 1.0}), 4)
        0.025

    Selling 1pp of US equity into cash costs 1.5bp on the equity leg and 1bp
    on the bill leg, both on 1% of NAV, so 0.025bp of NAV, about USD 21,250.

        >>> round(round_trip_cost({"commodities": 3.0, "cash": 3.0}), 4)
        0.78

    Taking commodities to zero and parking the proceeds costs 0.78bp of NAV,
    about USD 66,300, on a 3pp move. Same size in US equity costs 0.075bp.
    """
    total = 0.0
    for line, size_pp in trades_pp.items():
        _check_line(line)
        total += abs(float(size_pp)) / 100.0 * ONE_WAY_BPS[line]
    return total


def turnover_pp(w_from: dict, w_to: dict) -> float:
    """One-way turnover between two weight vectors, in pp of NAV.

    Defined as half the sum of absolute weight changes, which is the standard
    convention: moving 2pp out of one line and into another is 2pp of
    turnover, not 4pp. Lines absent from either dictionary are treated as
    zero, so a partial vector is accepted.

        >>> turnover_pp({"us_equity": 38.0, "cash": 0.0},
        ...             {"us_equity": 36.0, "cash": 2.0})
        2.0
    """
    keys = set(w_from) | set(w_to)
    for line in keys:
        _check_line(line)
    gross = sum(abs(float(w_to.get(k, 0.0)) - float(w_from.get(k, 0.0)))
                for k in keys)
    return gross / 2.0


def trades_pp(w_from: dict, w_to: dict) -> dict:
    """Per-line trade sizes, signed, in pp of NAV. Positive is a purchase.

    The return is built in sorted key order, not set order. Python randomises
    string hashing per process, so iterating the set directly serialised this
    dict differently on every run. No value moved, but decision_record.json came
    back byte-different from a clean rerun and a reader following the README's
    reproduce instructions saw a 66-line diff that meant nothing. Sorting costs
    nothing and makes the record diffable, which is the only way a reader can
    check a rerun against the published file. See AUDIT.md §7.
    """
    keys = set(w_from) | set(w_to)
    for line in keys:
        _check_line(line)
    return {k: float(w_to.get(k, 0.0)) - float(w_from.get(k, 0.0))
            for k in sorted(keys)}


def apply_min_trade(w_from: dict, w_to: dict,
                    min_pp: float = MIN_TRADE_PP,
                    reconcile_into: str = "cash") -> dict:
    """Suppress every proposed trade smaller than the minimum trade size.

    UNITS: percentage points of NAV throughout, in and out. A 38% weight is
    38.0. A 60bp trade is a change of 0.60. Passing fractional weights here
    is the one call in this module that fails silently: a fractional 60bp
    trade reads as 0.006 against a 0.50 minimum, gets suppressed, and comes
    back as a hold that is internally valid and completely wrong. Convert at
    the adapter in taa/simulate.py, never at the call site.

    IPS v7.2 Section 4.2: "Minimum trade 50bps. Anything smaller does not
    justify the turnover." This function applies that rule literally. Any
    line whose proposed change is strictly below ``min_pp`` in absolute size
    is held at its starting weight. Lines at or above ``min_pp`` pass through
    untouched.

    Suppressing trades leaves the weights short or long of their original
    total. The residual is absorbed by ``reconcile_into``, which defaults to
    cash because IPS Section 4.1 makes cash the funding line rather than a
    residual to be ignored, and because the bill vehicles cost 1bp to trade.
    The reconciling adjustment is itself exempt from the minimum, since it is
    a funding entry and not a discretionary position change. Pass
    ``reconcile_into=None`` to skip reconciliation and receive the raw
    suppressed vector.

        >>> out = apply_min_trade({"us_equity": 38.0, "cash": 0.0},
        ...                       {"us_equity": 38.3, "cash": -0.3},
        ...                       reconcile_into=None)
        >>> out["us_equity"]          # 30bp move, suppressed
        38.0
        >>> out = apply_min_trade({"us_equity": 38.0, "cash": 0.0},
        ...                       {"us_equity": 38.6, "cash": -0.6},
        ...                       reconcile_into=None)
        >>> out["us_equity"]          # 60bp move, allowed
        38.6
    """
    keys = set(w_from) | set(w_to)
    for line in keys:
        _check_line(line)

    out = {}
    for k in keys:
        start = float(w_from.get(k, 0.0))
        target = float(w_to.get(k, 0.0))
        out[k] = target if abs(target - start) >= min_pp else start

    if reconcile_into is not None:
        _check_line(reconcile_into)
        original_total = sum(float(w_to.get(k, 0.0)) for k in keys)
        out.setdefault(reconcile_into, float(w_from.get(reconcile_into, 0.0)))
        out[reconcile_into] += original_total - sum(out.values())

    return out


def band(line: str) -> tuple:
    """The no-trade band for a line, as (low, high) in pp of NAV.

    Symmetric around the policy weight, except for lines in ONE_SIDED_UP,
    whose policy weight sits on the floor of the IPS range and whose band
    therefore only exists above it.
    """
    _check_line(line)
    w = POLICY_PP[line]
    c = CORRIDOR_PP[line]
    if line in ONE_SIDED_UP:
        return (w, w + c)
    return (w - c, w + c)


def breaches(weights: dict) -> dict:
    """Lines outside their no-trade band, and the trade back to policy.

    Returns a mapping line -> signed trade in pp of NAV that would restore
    the policy weight. Trades are guaranteed to be at least CORRIDOR_PP in
    size, and every corridor is at least MIN_TRADE_PP wide, so every entry
    returned is actionable under IPS Section 4.2.
    """
    out = {}
    for line, w in weights.items():
        _check_line(line)
        low, high = band(line)
        if float(w) < low or float(w) > high:
            out[line] = POLICY_PP[line] - float(w)
    return out


def range_breaches(weights: dict) -> dict:
    """Lines outside their permitted IPS range. These are compliance breaches.

    IPS Section 4.1: the range "binds independently of the tracking-error
    budget. A position inside the tracking-error budget but outside its range
    is a breach."
    """
    out = {}
    for line, w in weights.items():
        _check_line(line)
        low, high = RANGE_PP[line]
        if float(w) < low or float(w) > high:
            out[line] = (float(w), (low, high))
    return out


def drift_te_bps(weights: dict) -> float:
    """Approximate tracking error, in bps, from drift away from policy.

    Root sum of squares of each line's drift in pp times its active
    volatility. Deliberately ignores the cross-correlation of the drifts,
    which is negative by construction because the weights sum to one, so the
    figure is an upper bound rather than a forecast. Used to show the
    Committee what the corridor set costs against the 200bp budget.
    """
    acc = 0.0
    for line, w in weights.items():
        _check_line(line)
        d = float(w) - POLICY_PP[line]
        acc += (d * ACTIVE_VOL_PCT[line]) ** 2
    return acc ** 0.5


def corridor_te_bps() -> float:
    """Drift tracking error with every line simultaneously at its band edge.

    The worst case the corridor set permits. 26.7bp on the adopted table,
    against a 200bp budget.
    """
    edges = {line: POLICY_PP[line] + CORRIDOR_PP[line] for line in LINES}
    return drift_te_bps(edges)


def usd(pp: float) -> float:
    """Convert pp of NAV to US dollars at the IPS Section 1 fund size."""
    return float(pp) / 100.0 * NAV_USD


if __name__ == "__main__":  # pragma: no cover
    w = max(len(k) for k in LINES)
    print(f"{'line':<{w}}  {'policy':>7} {'range':>12} {'corr':>6} "
          f"{'band':>14} {'cost':>6} {'TEbp':>6}")
    for line in LINES:
        lo, hi = RANGE_PP[line]
        blo, bhi = band(line)
        print(f"{line:<{w}}  {POLICY_PP[line]:>6.1f}% "
              f"{lo:>5.0f}-{hi:<5.0f}% {CORRIDOR_PP[line]:>5.2f} "
              f"{blo:>6.2f}-{bhi:<6.2f} {ONE_WAY_BPS[line]:>5.2f} "
              f"{CORRIDOR_PP[line] * ACTIVE_VOL_PCT[line]:>6.1f}")
    print(f"\ncorridor-edge tracking error: {corridor_te_bps():.1f}bp "
          f"of the {TE_BUDGET_BPS:.0f}bp budget")
    print(f"minimum trade: {MIN_TRADE_PP:.2f}pp = USD {usd(MIN_TRADE_PP):,.0f}")
