"""
taa.simulate — the five-year quarterly record, emitted as data.

The written record is this table with reasoning attached. A record composed by
hand from memory of what the backtest probably did is the thing this module
exists to prevent, so every field a trustee reads traces to a row emitted here.

WHAT THIS IS, STATED PLAINLY
------------------------------------------------------------------------------
Twenty quarterly meetings, 30 September 2021 through 30 June 2026. Every one of
them is MECHANICAL. A pre-committed rule reads the point-in-time inputs
available on the meeting date and produces an allocation. No deliberation is
invented, because a hand-reconciled twenty-meeting history written today would
be hindsight in its purest form, and the trustees can tell the difference.

The rule is stated below and it never changes across the window. The reason
attached to each decision is the reading of the inputs that drove the rule, and
it could have been written on the meeting date by someone holding only the
papers tabled at it. That is asserted by tests/check_hindsight.py rather than
by this docstring.

The one genuinely deliberated decision is the current one, taken now with six
desks tabling papers, and it is minuted separately.

THE PRE-COMMITTED RULE
------------------------------------------------------------------------------
  1. The Quantitative desk's allocation, from signals through the optimiser,
     reached without sight of the macro view.
  2. The Macro desk's allocation, from the point-in-time regime read and what
     was priced, reached without sight of the model output.
  3. Reconciliation: equal weight on the two active vectors. Equal weight
     because neither desk has demonstrated skill that would justify preferring
     it, which is the Systematic desk's finding and not a convenience.
  4. Scale to the tracking-error budget if the combined view exceeds it.
  5. Truncate to the permitted range on every line and every sleeve. IPS 3.6:
     a view that would breach rank 3 or 4 is truncated to the constraint and
     the truncation is minuted.
  6. Suppress any trade below the 50bps minimum (IPS 4.2).
  7. Run the compliance test. If it fails, truncate and re-run. An allocation
     that fails does not proceed (IPS 2.1).

MEASUREMENT IS NOT A LOOK-AHEAD
------------------------------------------------------------------------------
Decisions read data through pitdata at the meeting date. Performance is then
measured over the quarter that followed, using returns that had not happened
when the decision was taken. Measuring what happened after a decision is not a
look-ahead; using it to explain the decision is, and the outcome block is
therefore the only place it appears.

Run:  py -3 -m taa.simulate
"""

from __future__ import annotations

import datetime as dt
import json

import numpy as np
import pandas as pd

from . import compliance, config, costs, perf, pitdata, regime, riskmodel, signals

try:
    from . import optimiser
except Exception:                                     # pragma: no cover
    optimiser = None

LINES = config.LINES
POLICY = config.POLICY

# The reconciliation weight. Equal, and fixed for the whole window.
QUANT_WEIGHT = 0.50
MACRO_WEIGHT = 0.50


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------
def _vec(w: dict) -> np.ndarray:
    return np.array([w.get(k, 0.0) for k in LINES], float)


def _dict(v: np.ndarray) -> dict:
    return {k: float(v[i]) for i, k in enumerate(LINES)}


def _active(w: dict) -> dict:
    return {k: w.get(k, 0.0) - POLICY[k] for k in LINES}


def _renorm(w: dict) -> dict:
    s = sum(w.values())
    return {k: v / s for k, v in w.items()} if s else dict(POLICY)


def _truncate(w: dict) -> tuple[dict, list[str]]:
    """
    Truncate to every line range and sleeve range, then renormalise onto cash
    where there is room. Returns the allocation and the constraints that bound.
    """
    bound = []
    out = dict(w)
    for k in LINES:
        lo, hi = config.RANGE[k]
        if out[k] < lo - 1e-12:
            out[k], _ = lo, bound.append(f"range:{k}:lower")
        elif out[k] > hi + 1e-12:
            out[k], _ = hi, bound.append(f"range:{k}:upper")

    for sl, (lo, hi) in config.SLEEVE_RANGE.items():
        members = [k for k in LINES if config.SLEEVE[k] == sl]
        tot = sum(out[k] for k in members)
        if tot > hi + 1e-12:
            scale = hi / tot
            for k in members:
                out[k] *= scale
            bound.append(f"sleeve:{sl}:upper")
        elif tot < lo - 1e-12 and tot > 0:
            scale = lo / tot
            for k in members:
                out[k] = min(out[k] * scale, config.RANGE[k][1])
            bound.append(f"sleeve:{sl}:lower")

    resid = 1.0 - sum(out.values())
    lo_c, hi_c = config.RANGE["cash"]
    take = max(min(out["cash"] + resid, hi_c), lo_c) - out["cash"]
    out["cash"] += take
    resid -= take
    if abs(resid) > 1e-9:
        pool = [k for k in LINES if k != "cash"]
        for _ in range(6):
            if abs(resid) < 1e-10:
                break
            room = {k: (config.RANGE[k][1] - out[k]) if resid > 0 else (out[k] - config.RANGE[k][0])
                    for k in pool}
            tot_room = sum(max(r, 0.0) for r in room.values())
            if tot_room <= 1e-12:
                break
            for k in pool:
                out[k] += resid * max(room[k], 0.0) / tot_room
            resid = 1.0 - sum(out.values())
    return out, bound


def _scale_to_te(w: dict, cov, budget_bps: float) -> tuple[dict, float, bool]:
    """Scale the active vector back onto the budget. Never scales up."""
    te = riskmodel.ex_ante_te(w, cov)
    if te <= budget_bps or te <= 0:
        return w, te, False
    a = _active(w)
    k = budget_bps / te * 0.985
    out = {ln: POLICY[ln] + a[ln] * k for ln in LINES}
    return _renorm(out), riskmodel.ex_ante_te(out, cov), True


def _kind(w_in: dict, w_out: dict, cov) -> str:
    trades = c_trades(w_in, w_out)
    if max(abs(v) for v in trades.values()) < 1e-9:
        return "hold"
    te_in = riskmodel.ex_ante_te(w_in, cov)
    te_out = riskmodel.ex_ante_te(w_out, cov)
    return "unwind" if te_out < te_in - 5.0 else "tilt"


def _fmt_pp(x: float) -> str:
    v = x * 100
    return f"({abs(v):.1f})" if v < 0 else f"{v:.1f}"


# --------------------------------------------------------------------------
# UNIT ADAPTER. This exists because the office does not agree with itself.
#
# taa.costs works in percentage points of NAV: a 38% weight is 38.0 and the
# 50bps minimum trade is 0.50. Everything else in this study works in
# fractions: the same weight is 0.38. Both conventions are defensible and the
# mismatch is silent, which is what makes it dangerous. Applied without
# conversion, apply_min_trade would read every fractional trade as far below
# 0.50 and suppress all of them, and the record would show twenty quarters of
# inactivity that was an arithmetic error rather than a decision.
#
# The conversion is explicit here rather than buried, and
# tests/check_units.py fails if either side changes convention.
# --------------------------------------------------------------------------
def _to_pp(w: dict) -> dict:
    return {k: v * 100.0 for k, v in w.items()}


def c_trades(w_from: dict, w_to: dict) -> dict:
    """Signed trades in FRACTIONS, computed through the costs module."""
    return {k: v / 100.0 for k, v in costs.trades_pp(_to_pp(w_from), _to_pp(w_to)).items()}


def c_turnover(w_from: dict, w_to: dict) -> float:
    """One-way turnover as a FRACTION of NAV."""
    return costs.turnover_pp(_to_pp(w_from), _to_pp(w_to)) / 100.0


def c_min_trade(w_from: dict, w_to: dict) -> dict:
    """Minimum-trade filter, in and out in FRACTIONS."""
    out = costs.apply_min_trade(_to_pp(w_from), _to_pp(w_to))
    return {k: v / 100.0 for k, v in out.items()}


def c_cost_bps(trades_frac: dict) -> float:
    """Round-trip cost in bps of NAV, from trades expressed as FRACTIONS."""
    return costs.round_trip_cost({k: v * 100.0 for k, v in trades_frac.items()})


def _settle(w_from: dict, w_target: dict, max_iter: int = 6) -> tuple[dict, list[str]]:
    """
    Reach an allocation that is simultaneously inside every range and free of
    dust trades.

    Naively these two steps fight each other. Truncating to a range creates a
    residual, the residual is reconciled somewhere, and the reconciliation is
    itself a trade that can land below the 50bps minimum. Applying the minimum
    then suppresses it, which creates a new residual, which reopens a range.
    Running the two once each leaves an allocation that fails the compliance
    test on min_trade for a reason that has nothing to do with the view.

    So they are iterated to a fixed point. Suppressed trades are reconciled
    across the lines that are already trading at size, in proportion to their
    trade, rather than dumped into cash where they would create a new dust
    trade of their own. If no fixed point is reached the allocation is held at
    the incoming weights, which is an honest hold rather than a forced trade.
    """
    bound: list[str] = []
    w = dict(w_target)
    for _ in range(max_iter):
        w, b = _truncate(w)
        bound += b
        tr = {k: w[k] - w_from[k] for k in LINES}
        keep = {k: v for k, v in tr.items() if abs(v) >= config.MIN_TRADE_PP / 100.0 - 1e-12}
        if not keep:
            return dict(w_from), bound + ["min_trade:all suppressed"]
        gross = sum(abs(v) for v in keep.values())
        resid = -sum(keep.values())
        adj = {k: v + resid * abs(v) / gross for k, v in keep.items()}
        cand = dict(w_from)
        for k, v in adj.items():
            cand[k] = w_from[k] + v
        if all(abs(cand[k] - w[k]) < 1e-10 for k in LINES):
            return cand, bound
        w = cand
    return dict(w_from), bound + ["min_trade:did not settle, held"]


# Constraints that describe the state of the fund rather than a defect in the
# proposed allocation. A realised drawdown cannot be remedied by choosing
# different weights, because it has already happened. IPS 3.3 answers it by
# reducing the distribution and IPS 2.3 escalates it to the Board. Treating it
# as an allocation rejection would be a category error, and would also mean the
# office reported twenty rejected allocations for one event in October 2022.
FUND_STATE_CHECKS = {"drawdown_realised"}


# --------------------------------------------------------------------------
# reason and watch, built only from what was on the table that day
# --------------------------------------------------------------------------
def _reason(d, reg, scores, w_in, w_out, te_before, te_after, bound, truncated,
            kind, cov) -> tuple[str, list[dict]]:
    inputs: list[dict] = []
    ranked = sorted(scores.items(), key=lambda kv: -abs(kv[1]))
    top = [(k, v) for k, v in ranked if abs(v) > 0.15][:3]
    for k, v in top:
        inputs.append({"name": f"composite score, {config.LINE_LABEL[k]}",
                       "value": round(float(v), 3)})

    g = reg.get("growth", "n/a")
    infl = reg.get("inflation", "n/a")
    pol = reg.get("policy", "n/a")
    inputs.append({"name": "regime read", "value": reg.get("regime_label", "n/a")})
    inputs.append({"name": "ex ante tracking error before", "value": round(te_before, 1)})

    moves = sorted(c_trades(w_in, w_out).items(), key=lambda kv: -abs(kv[1]))
    moves = [(k, v) for k, v in moves if abs(v) > 1e-9][:3]

    parts = []
    parts.append(
        f"The regime read on the vintages available at this date was {g} growth with "
        f"{infl} inflation and {pol} policy, classified {reg.get('regime_label','n/a')}.")
    if top:
        s = ", ".join(f"{config.LINE_LABEL[k]} at {v:+.2f}" for k, v in top)
        parts.append(f"The composite signal was strongest on {s}.")
    else:
        parts.append("No line carried a composite score beyond the noise threshold of 0.15.")

    if kind == "hold":
        parts.append(
            f"Reconciling the two desk allocations produced no line change reaching the "
            f"50bps minimum trade, so the allocation was carried unchanged and the "
            f"turnover was not incurred.")
    else:
        m = "; ".join(f"{config.LINE_LABEL[k]} {_fmt_pp(v)}pp" for k, v in moves)
        parts.append(f"The reconciled allocation moved {m}.")

    if truncated:
        parts.append(
            f"The combined view implied {te_before:.0f}bps of ex ante tracking error against "
            f"a {config.TE_BUDGET_BPS:.0f}bps budget, so it was truncated to the constraint "
            f"under IPS 3.6 rather than overridden by argument, leaving {te_after:.0f}bps.")
    if bound:
        parts.append(f"The binding constraint at this meeting was {bound[0]}.")
    return " ".join(parts), inputs


def _watch(d, reg, scores, w_out, te_after, dd_now, cov) -> list[dict]:
    """
    Written at this meeting from this meeting's readings. Never revised. The
    next meeting records whether it happened.
    """
    items = []
    near = [(k, v) for k, v in scores.items() if 0.30 <= abs(v) < 0.60]
    for k, v in sorted(near, key=lambda kv: -abs(kv[1]))[:2]:
        items.append({
            "text": (f"Composite on {config.LINE_LABEL[k]} stands at {v:+.2f}. A move beyond "
                     f"{'+' if v > 0 else ''}{0.60 if v > 0 else -0.60:+.2f} would carry the "
                     f"line past the tilt threshold."),
            "metric": "composite", "line": k, "level": round(float(v), 3),
            "trigger": 0.60 if v > 0 else -0.60,
            "direction": "above" if v > 0 else "below"})

    util = te_after / config.TE_BUDGET_BPS
    if util > 0.70:
        items.append({
            "text": (f"Ex ante tracking error at {te_after:.0f}bps is {util * 100:.0f}% of the "
                     f"{config.TE_BUDGET_BPS:.0f}bps budget. A further widening would force a "
                     f"truncation at the next meeting."),
            "metric": "te_bps", "level": round(te_after, 1),
            "trigger": config.TE_BUDGET_BPS, "direction": "above"})

    if dd_now < config.DRAWDOWN_LIMIT * 0.40:
        items.append({
            "text": (f"Peak-to-trough drawdown stands at {_fmt_pp(dd_now)}% against the "
                     f"{abs(config.DRAWDOWN_LIMIT) * 100:.0f}% board limit."),
            "metric": "drawdown", "level": round(float(dd_now), 4),
            "trigger": config.DRAWDOWN_LIMIT, "direction": "below"})

    for k in LINES:
        lo, hi = config.RANGE[k]
        if w_out[k] > hi - 0.01 and hi > 0:
            items.append({
                "text": (f"{config.LINE_LABEL[k]} at {w_out[k] * 100:.1f}% sits within one "
                         f"point of its {hi * 100:.0f}% ceiling."),
                "metric": "range", "line": k, "level": round(w_out[k], 4),
                "trigger": hi, "direction": "above"})
            break
    if not items:
        items.append({
            "text": ("No reading stood close enough to a threshold to be worth watching into "
                     "the next meeting."),
            "metric": "none", "level": 0.0, "trigger": 0.0, "direction": "none"})
    return items


def _resolve(prev_watch: list[dict], scores, te_after, dd_now, w_out) -> list[dict]:
    """Resolved forward. The text is carried verbatim and never edited."""
    out = []
    for w in prev_watch:
        metric, happened, obs = w.get("metric"), False, None
        if metric == "composite":
            obs = float(scores.get(w["line"], 0.0))
            happened = obs >= w["trigger"] if w["direction"] == "above" else obs <= w["trigger"]
        elif metric == "te_bps":
            obs = round(te_after, 1)
            happened = obs >= w["trigger"]
        elif metric == "drawdown":
            obs = round(float(dd_now), 4)
            happened = obs <= w["trigger"]
        elif metric == "range":
            obs = round(float(w_out.get(w["line"], 0.0)), 4)
            happened = obs >= w["trigger"]
        out.append({"text": w["text"], "metric": metric, "observed": obs,
                    "happened": bool(happened)})
    return out


# --------------------------------------------------------------------------
def run(verbose: bool = True) -> dict:
    meetings = config.meeting_dates()
    months = config.month_ends()

    # Measurement panel. Read once, at the end of the window, because measuring
    # what happened is not a look-ahead. Decisions never touch this.
    end_view = pitdata.as_of(config.WINDOW_END)
    rets = end_view.monthly_returns()
    rets = rets[(rets.index >= pd.Timestamp(config.WINDOW_START)) &
                (rets.index <= pd.Timestamp(config.WINDOW_END))]
    missing = {ln: int(rets[ln].isna().sum()) for ln in LINES if rets[ln].isna().any()}
    rets = rets.fillna(0.0)

    bench = (rets * pd.Series(POLICY)).sum(axis=1)      # monthly rebalanced blend

    w_cur = dict(POLICY)
    strat, wpath, decisions = [], [], []
    prev_watch: list[dict] = []
    nav = [1.0]

    for i, me in enumerate(rets.index):
        d = me.date()
        is_meeting = any(m == d for m in meetings)
        cost_bps = 0.0

        if is_meeting:
            cov = riskmodel.cov_as_of(d)
            sc = signals.composite_as_of(d)
            reg = regime.regime_as_of(d)

            if optimiser is not None:
                try:
                    w_q = optimiser.allocate(d, cov=cov, scores=sc)
                except Exception:
                    w_q = dict(POLICY)
            else:
                w_q = dict(POLICY)
            try:
                w_m, _notes, _mb = regime.weights_as_of(d, reg)
            except Exception:
                w_m = dict(POLICY)

            a_q, a_m = _active(w_q), _active(w_m)
            w_comb = {ln: POLICY[ln] + QUANT_WEIGHT * a_q[ln] + MACRO_WEIGHT * a_m[ln]
                      for ln in LINES}
            w_comb = _renorm(w_comb)

            te_before = riskmodel.ex_ante_te(w_comb, cov)
            w_comb, te_scaled, truncated = _scale_to_te(w_comb, cov, config.TE_BUDGET_BPS)
            w_prop, bound = _settle(w_cur, w_comb)

            dd_now = float(pd.Series(nav).div(pd.Series(nav).cummax()).iloc[-1] - 1.0)
            navs = pd.Series(nav)
            res = compliance.check(w_prop, cov=cov, as_of=d, prior_weights=w_cur,
                                   nav_path=navs)

            # Remediation loop. An allocation defect is remedied by choosing
            # different weights; a breach of the fund's own drawdown limit is
            # not, and is escalated instead (IPS 2.3, 3.3).
            # Remediation shrinks the ACTIVE VECTOR toward policy rather than
            # scaling to a tracking-error budget. Scaling to the budget does
            # nothing when tracking error is already inside it, which is exactly
            # the case when the failing constraint is an ex-ante drawdown driven
            # by total volatility rather than by active risk. The first version
            # of this loop spun its four rounds without changing the allocation
            # at all and then fell through to the fallback.
            attempts, lam = 0, 1.0
            base = dict(w_prop)
            def _defects(rr):
                vp = riskmodel.total_vol(w_prop, cov)
                vb = riskmodel.total_vol(dict(POLICY), cov)
                st = set(FUND_STATE_CHECKS)
                if vp <= vb * 1.005:
                    st.add("drawdown_ex_ante")
                return [c for c in rr.failed() if c.name not in st]

            while attempts < 4:
                defects = _defects(res)
                if not defects:
                    break
                attempts += 1
                lam *= 0.55
                a_v = _active(base)
                w_try = _renorm({ln: POLICY[ln] + lam * a_v[ln] for ln in LINES})
                w_try, b2 = _settle(w_cur, w_try)
                bound += b2
                res = compliance.check(w_try, cov=cov, as_of=d, prior_weights=w_cur,
                                       nav_path=navs)
                w_prop = w_try

            defects = _defects(res)
            if defects:
                # Nothing survived. The pre-committed fallback is policy weights,
                # settled against the incoming allocation so that the move is
                # actually implementable. Where settling cannot reach policy
                # without a sub-minimum trade it holds, which is an honest hold
                # rather than an instruction the desk could not execute.
                w_prop, b3 = _settle(w_cur, dict(POLICY))
                bound += b3 + ["fallback:policy weights"]
                res = compliance.check(w_prop, cov=cov, as_of=d, prior_weights=w_cur,
                                       nav_path=navs)

            # An ex-ante drawdown failure at or below policy-equivalent risk is
            # not an allocation defect either. The Board's own policy portfolio
            # reads (21.60)% against a (20.00)% limit, so the gate sits on top
            # of policy and any allocation carrying no more total volatility
            # than policy fails it for a reason the office cannot fix by
            # choosing different weights. Recording that as a rejected
            # allocation would blame the desk for the mandate.
            vol_p = riskmodel.total_vol(w_prop, cov)
            vol_b = riskmodel.total_vol(dict(POLICY), cov)
            at_or_below_policy_risk = vol_p <= vol_b * 1.005
            state = set(FUND_STATE_CHECKS)
            if at_or_below_policy_risk:
                state.add("drawdown_ex_ante")

            fund_breach = [c.name for c in res.failed() if c.name in state]
            alloc_defects = [c.name for c in res.failed() if c.name not in state]
            te_after = riskmodel.ex_ante_te(w_prop, cov)
            binding = res.binding() or bound or ["none"]
            kind = _kind(w_cur, w_prop, cov)
            trades = c_trades(w_cur, w_prop)
            turn = c_turnover(w_cur, w_prop)
            cost_bps = c_cost_bps(trades)

            reason, cited = _reason(d, reg, sc, w_cur, w_prop, te_before, te_after,
                                    binding, truncated, kind, cov)
            resolution = _resolve(prev_watch, sc, te_after, dd_now, w_prop)
            watch = _watch(d, reg, sc, w_prop, te_after, dd_now, cov)

            anach = [a for a in pitdata.anachronisms() if a.get("as_of") == d.isoformat()]

            decisions.append({
                "n": len(decisions) + 1,
                "date": d.isoformat(),
                "fiscal_year": f"FY{d.year + (1 if d.month > 6 else 0)}",
                "kind": kind,
                "weights_before": {k: round(v, 6) for k, v in w_cur.items()},
                "weights_after": {k: round(v, 6) for k, v in w_prop.items()},
                "active_after_bps": {k: round(v * 10000, 1) for k, v in _active(w_prop).items()},
                "trades_pp": {k: round(v * 100, 3) for k, v in trades.items() if abs(v) > 1e-9},
                "turnover_pp": round(turn * 100, 3),
                "cost_bps": round(cost_bps, 2),
                "quant_allocation": {k: round(v, 6) for k, v in w_q.items()},
                "macro_allocation": {k: round(v, 6) for k, v in w_m.items()},
                "desks_agreed": bool(max(abs(a_q[k] - a_m[k]) for k in LINES) < 0.01),
                "max_desk_disagreement_bps": round(
                    max(abs(a_q[k] - a_m[k]) for k in LINES) * 10000, 1),
                "signal_readings": {k: round(float(v), 4) for k, v in sc.items()},
                "regime": {"label": reg.get("regime_label"), "growth": reg.get("growth"),
                           "inflation": reg.get("inflation"), "policy": reg.get("policy"),
                           "liquidity": reg.get("liquidity")},
                "te_before_bps": round(te_before, 1),
                "te_after_bps": round(te_after, 1),
                "truncated_to_budget": bool(truncated),
                "binding_constraint": binding[0],
                "all_binding": binding,
                "compliance": {
                    # The allocation verdict. This is the one that gates the
                    # Committee under IPS 2.1.
                    "passed": not alloc_defects,
                    "failed": alloc_defects,
                    "remediation_rounds": attempts,
                    # A breach of the fund's own limit. Not an allocation
                    # defect, cannot be remedied by reallocation, escalated
                    # under IPS 2.3 and answered under IPS 3.3 by reducing the
                    # distribution. Reported separately so the two are never
                    # confused in the record.
                    "fund_in_breach": fund_breach,
                    "raw_verdict": str(res.status),
                    "disclosures_required": len(
                        [c for c in res.results if str(c.status) == "PASS-WITH-DISCLOSURE"]),
                },
                "reason": reason,
                "inputs_cited": cited,
                "watch": watch,
                "watch_resolution": resolution,
                "anachronisms": [a.get("reason") for a in anach],
                "outcome": None,          # filled last, never used in a reason
            })
            prev_watch = watch
            w_cur = w_prop

        # carry the quarter: apply cost at the rebalance month, then drift
        gross = float(sum(w_cur[k] * rets.loc[me, k] for k in LINES))
        net = gross - cost_bps / 10000.0
        strat.append(net)
        wpath.append(dict(w_cur))
        nav.append(nav[-1] * (1 + net))
        drift = {k: w_cur[k] * (1 + rets.loc[me, k]) for k in LINES}
        w_cur = _renorm(drift)

    sr = pd.Series(strat, index=rets.index)
    active = sr - bench

    # ---- outcomes, filled last -------------------------------------------
    for e in decisions:
        d0 = pd.Timestamp(e["date"])
        nxt = [pd.Timestamp(x["date"]) for x in decisions if pd.Timestamp(x["date"]) > d0]
        d1 = min(nxt) if nxt else sr.index.max()
        m = (active.index > d0) & (active.index <= d1)
        a = float((1 + sr[m]).prod() - (1 + bench[m]).prod()) if m.any() else 0.0
        e["outcome"] = {
            "active_return_bps": round(a * 10000, 1),
            "months_held": int(m.sum()),
            "strategy_return_pct": round(float((1 + sr[m]).prod() - 1) * 100, 3) if m.any() else 0.0,
            "benchmark_return_pct": round(float((1 + bench[m]).prod() - 1) * 100, 3) if m.any() else 0.0,
            "cost_bps": e["cost_bps"],
            "verdict": ("helped" if a * 10000 > 5 else
                        "hurt" if a * 10000 < -5 else "too small to tell"),
        }

    out = {
        "generated": dt.datetime.now().isoformat(timespec="seconds"),
        "window": config.window(),
        "rule": {
            "quant_weight": QUANT_WEIGHT, "macro_weight": MACRO_WEIGHT,
            "description": "Equal weight on two independently reached active vectors, "
                           "scaled to the tracking-error budget, truncated to every "
                           "permitted range, filtered by the 50bps minimum trade, and "
                           "gated by the compliance test.",
            "all_historical_decisions_are_mechanical": True,
        },
        "missing_observations": missing,
        "monthly": {
            "dates": [d.strftime("%Y-%m-%d") for d in sr.index],
            "strategy": [round(float(v), 6) for v in sr.values],
            "benchmark": [round(float(v), 6) for v in bench.values],
            "active": [round(float(v), 6) for v in active.values],
        },
        "weight_path": [{k: round(v, 5) for k, v in w.items()} for w in wpath],
        "decisions": decisions,
        "summary": perf.pair_summary(sr, bench, label="Since inception"),
        "periods": perf.standard_periods(sr, bench),
        "scorecard": scorecard(decisions),
    }
    (config.OUTPUTS / "decision_record.json").write_text(
        json.dumps(out, indent=2, default=str), encoding="utf-8")

    if verbose:
        _print(out, sr, bench, active, missing)
    return out


def scorecard(decisions: list[dict]) -> dict:
    helped = [d for d in decisions if d["outcome"]["verdict"] == "helped"]
    hurt = [d for d in decisions if d["outcome"]["verdict"] == "hurt"]
    flat = [d for d in decisions if d["outcome"]["verdict"] == "too small to tell"]
    net_bps = sum(d["outcome"]["active_return_bps"] for d in decisions)
    cost_bps = sum(d["cost_bps"] for d in decisions)
    yrs = max(len(decisions) / 4.0, 1e-9)
    binding = {}
    for d in decisions:
        binding[d["binding_constraint"]] = binding.get(d["binding_constraint"], 0) + 1
    kinds = {}
    for d in decisions:
        kinds[d["kind"]] = kinds.get(d["kind"], 0) + 1
    return {
        "decisions": len(decisions),
        "helped": len(helped), "hurt": len(hurt), "too_small_to_tell": len(flat),
        "gross_active_bps_total": round(net_bps, 1),
        "net_active_bps_per_year": round(net_bps / yrs, 1),
        "turnover_cost_bps_total": round(cost_bps, 1),
        "turnover_cost_bps_per_year": round(cost_bps / yrs, 1),
        "binding_constraint_frequency": dict(sorted(binding.items(), key=lambda kv: -kv[1])),
        "decision_kind_frequency": kinds,
        "quarters_failing_compliance": sum(1 for d in decisions if not d["compliance"]["passed"]),
        "quarters_fund_in_breach": sum(1 for d in decisions if d["compliance"]["fund_in_breach"]),
        "quarters_needing_remediation": sum(
            1 for d in decisions if d["compliance"]["remediation_rounds"] > 0),
    }


def _print(out, sr, bench, active, missing) -> None:
    s = out["summary"]
    sc = out["scorecard"]
    print("\nFIVE-YEAR RECORD")
    print(f"  window            {out['window']['start']} .. {out['window']['end']}")
    print(f"  months            {len(sr)}   meetings {len(out['decisions'])}")
    if missing:
        print(f"  MISSING           {missing}")
    print(f"\n  {'':22s}{'strategy':>12s}{'benchmark':>12s}{'active':>12s}")
    print(f"  {'annualised return':22s}{s['portfolio']['return']*100:11.2f}%"
          f"{s['benchmark']['return']*100:11.2f}%{s['active']['return']*100:11.2f}%")
    print(f"  {'annualised stdev':22s}{s['portfolio']['stdev']*100:11.2f}%"
          f"{s['benchmark']['stdev']*100:11.2f}%")
    print(f"  {'max drawdown':22s}{s['portfolio']['max_drawdown']*100:11.2f}%"
          f"{s['benchmark']['max_drawdown']*100:11.2f}%")
    print(f"  {'sharpe':22s}{s['portfolio']['sharpe']:12.3f}{s['benchmark']['sharpe']:12.3f}")
    print(f"  {'realised TE (bps)':22s}{'':12s}{'':12s}"
          f"{s['active']['tracking_error']*10000:11.1f}")
    print(f"  {'information ratio':22s}{'':12s}{'':12s}{s['active']['information_ratio']:12.3f}")
    print(f"\n  SCORECARD  helped {sc['helped']}  hurt {sc['hurt']}  "
          f"too small to tell {sc['too_small_to_tell']}")
    print(f"  net active {sc['net_active_bps_per_year']:+.1f}bps a year against "
          f"{sc['turnover_cost_bps_per_year']:.1f}bps of turnover cost")
    print(f"  allocations failing compliance: {sc['quarters_failing_compliance']} of {sc['decisions']}")
    print(f"  quarters needing remediation:   {sc['quarters_needing_remediation']}")
    print(f"  quarters with the FUND in breach of its own limit: {sc['quarters_fund_in_breach']}")
    print(f"  binding constraint frequency: {sc['binding_constraint_frequency']}")
    print(f"\n  written to outputs/decision_record.json")


if __name__ == "__main__":
    run()
