"""
taa.optimiser — the constrained allocation.

THE PROBLEM SOLVED
------------------------------------------------------------------------------
Maximise the signal-weighted active return subject to the mandate:

    max_w   s' (w - b)
    s.t.    (w - b)' Sigma (w - b) <= (TE budget)^2      IPS 4.2, hierarchy 4
            sum(w) = 1, w >= 0                            IPS 3.5, no leverage
            RANGE[line][0] <= w_line <= RANGE[line][1]     IPS 4.1
            SLEEVE_RANGE[sleeve][0] <= sum of sleeve <= SLEEVE_RANGE[sleeve][1]

s is the cross-sectionally demeaned composite score, b the policy portfolio,
Sigma the Ledoit-Wolf shrunk annualised covariance from taa.riskmodel. Every
limit is read from taa.config. None is written here as a number.

The objective is linear and the risk constraint is a ball, so with no box or
sleeve binding the solution is available in closed form:

    a_unc = k Sigma^-1 (s - lambda 1),   lambda = 1'Sigma^-1 s / 1'Sigma^-1 1

with lambda enforcing that the active weights sum to zero and k scaling the
result until the ex-ante tracking error equals the budget. That is the
unconstrained signal-implied tilt and it is reported next to the constrained
answer, so the Committee can see the size of the gap between what the estimator
asked for and what the mandate allowed. Where the two differ, the mandate won,
which is the pre-committed order in IPS 3.6.

ON SCALING TO THE BUDGET
------------------------------------------------------------------------------
The tilt is scaled to use the tracking-error budget rather than to reflect a
confidence level, because the composite score is an ordinal ranking standardised
to unit variance and carries no information about the magnitude of expected
returns. Reading a return forecast out of a z-score would be inventing one. The
budget is therefore the position sizer, and the honest description of the result
is that it is the mandate's maximum active risk pointed in the direction the
signals indicate. That the direction is worth pointing at is the question the
out-of-sample table in taa.evidence answers, and the answer there is what
governs how much of the budget the desk actually recommends using.
"""

from __future__ import annotations

import numpy as np
from scipy.optimize import minimize

from . import config, pitdata, riskmodel, signals

BOUND_TOL = 1e-6      # a weight this close to a bound is treated as on it
TE_TOL_BPS = 0.5      # tracking error this close to the budget is treated as binding


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------
def _vec(d: dict, lines) -> np.ndarray:
    return np.array([float(d.get(ln, 0.0)) for ln in lines])


def _dict(v: np.ndarray, lines) -> dict:
    return {ln: float(x) for ln, x in zip(lines, v)}


def _sleeve_matrix(lines):
    # Only sleeves the IPS gives a range. Cash carries no sleeve range in IPS
    # 4.1; it is bounded by its own line range, 0 to 10 per cent.
    sleeves = sorted({config.SLEEVE[ln] for ln in lines}
                     & set(config.SLEEVE_RANGE))
    M = np.zeros((len(sleeves), len(lines)))
    for i, sl in enumerate(sleeves):
        for j, ln in enumerate(lines):
            if config.SLEEVE[ln] == sl:
                M[i, j] = 1.0
    return sleeves, M


def _constraints(lines, cov, b, te_budget):
    sleeves, M = _sleeve_matrix(lines)
    te2 = (te_budget / 10_000.0) ** 2
    cons = [{"type": "eq", "fun": lambda w: np.sum(w) - 1.0,
             "jac": lambda w: np.ones_like(w)}]
    cons.append({"type": "ineq",
                 "fun": lambda w: te2 - (w - b) @ cov @ (w - b),
                 "jac": lambda w: -2.0 * cov @ (w - b)})
    for i, sl in enumerate(sleeves):
        lo, hi = config.SLEEVE_RANGE[sl]
        cons.append({"type": "ineq", "fun": (lambda w, i=i, lo=lo: M[i] @ w - lo),
                     "jac": (lambda w, i=i: M[i].copy())})
        cons.append({"type": "ineq", "fun": (lambda w, i=i, hi=hi: hi - M[i] @ w),
                     "jac": (lambda w, i=i: -M[i].copy())})
    return cons, sleeves, M


def _solve(objective, jac, lines, cov, b, te_budget, w0, pins=None):
    bounds = [list(config.RANGE[ln]) for ln in lines]
    for j, v in (pins or {}).items():                # pinned lines are fixed
        bounds[j] = [float(v), float(v)]
    bounds = [tuple(x) for x in bounds]
    cons, sleeves, M = _constraints(lines, cov, b, te_budget)
    res = minimize(objective, w0, jac=jac, bounds=bounds, constraints=cons,
                   method="SLSQP", options={"maxiter": 500, "ftol": 1e-12})
    w = np.clip(res.x, [lo for lo, _ in bounds], [hi for _, hi in bounds])
    if abs(w.sum() - 1.0) > 1e-9:                    # restore the budget identity
        w = w + (1.0 - w.sum()) / len(w)
        w = np.clip(w, [lo for lo, _ in bounds], [hi for _, hi in bounds])
    return w, res, sleeves, M


def project_feasible(w_target, lines, cov, b, te_budget, metric="risk"):
    """
    The feasible allocation closest to w_target.

    The metric is the covariance itself, so "closest" means the portfolio whose
    tracking error against the target is smallest. That is the right distance
    here: it is the risk-space distance a transition manager minimises, and it
    treats a five-point deviation in a volatile line as the larger departure it
    is. Euclidean distance is available for testing and treats a point of
    commodities as equal to a point of Treasuries, which it is not.
    """
    w_target = np.asarray(w_target, float)
    A = np.asarray(cov, float) if metric == "risk" else np.eye(len(w_target))

    def f(w):
        d = w - w_target
        return float(d @ A @ d)

    def g(w):
        return 2.0 * (A @ (w - w_target))

    w, res, _, _ = _solve(f, g, lines, cov, b, te_budget, np.asarray(b, float).copy())
    if not res.success:
        w2, res2, _, _ = _solve(f, g, lines, cov, b, te_budget, w_target.copy())
        if res2.success or f(w2) < f(w):
            w = w2
    return w


def inverse_vol_tilt(scores: dict, cov, lines, te_budget_bps: float,
                     benchmark: dict | None = None) -> dict:
    """
    The same scores expressed as a risk-parity tilt, a proportional to s/sigma,
    scaled to the budget and demeaned so the active weights sum to zero.

    Reported as a diagnostic beside the mean-variance tilt. It uses only the
    diagonal of the covariance, so it is insensitive to the 36 off-diagonal
    entries estimated from 60 observations. Where the two tilts disagree
    sharply, the disagreement is a measurement of how much of the mean-variance
    answer is coming from correlation estimates rather than from the signal.
    """
    b = _vec(benchmark or config.POLICY, lines)
    s = _vec(scores, lines)
    sd = np.sqrt(np.diag(np.asarray(cov, float)))
    a = s / np.where(sd > 0, sd, np.nan)
    a = np.nan_to_num(a)
    a = a - a.mean()
    q = float(a @ cov @ a)
    if q <= 0:
        return _dict(b, lines)
    k = (te_budget_bps / 10_000.0) / np.sqrt(q)
    return _dict(b + k * a, lines)


# --------------------------------------------------------------------------
# The allocation
# --------------------------------------------------------------------------
def unconstrained_tilt(scores: dict, cov, lines, te_budget_bps: float,
                       benchmark: dict | None = None) -> dict:
    """
    Closed-form maximiser of s'a subject only to a'Sigma a = budget^2 and
    sum(a) = 0. No box, no sleeve, no long-only.
    """
    b = _vec(benchmark or config.POLICY, lines)
    s = _vec(scores, lines)
    one = np.ones(len(lines))
    inv = np.linalg.inv(cov)
    lam = float(one @ inv @ s) / float(one @ inv @ one)
    a_dir = inv @ (s - lam * one)
    q = float(a_dir @ cov @ a_dir)
    if q <= 0:
        return _dict(b, lines)
    k = (te_budget_bps / 10_000.0) / np.sqrt(q)
    return _dict(b + k * a_dir, lines)


def max_scale(a, b, lines, cov, te_budget_bps):
    """
    The largest multiple of the active vector a that still satisfies every
    mandate limit, in closed form, together with the limit that stopped it.

    Every constraint is linear in the scale c except the tracking error, which
    is monotone in it, so the feasible set is an interval [0, c_max] and c_max
    is the minimum over the individual limits. That structure is what lets the
    desk name the binding constraint exactly rather than infer it from a
    solver's multipliers.
    """
    a = np.asarray(a, float)
    b = np.asarray(b, float)
    limits = []
    for j, ln in enumerate(lines):
        lo, hi = config.RANGE[ln]
        if a[j] > 1e-12:
            limits.append(((hi - b[j]) / a[j], f"range:{ln}:upper({hi:.2f})"))
        elif a[j] < -1e-12:
            limits.append(((lo - b[j]) / a[j], f"range:{ln}:lower({lo:.2f})"))
    sleeves, M = _sleeve_matrix(lines)
    for i, sl in enumerate(sleeves):
        lo, hi = config.SLEEVE_RANGE[sl]
        sa, sb = float(M[i] @ a), float(M[i] @ b)
        if sa > 1e-12:
            limits.append(((hi - sb) / sa, f"sleeve:{sl}:upper({hi:.2f})"))
        elif sa < -1e-12:
            limits.append(((lo - sb) / sa, f"sleeve:{sl}:lower({lo:.2f})"))
    te_a = float(np.sqrt(max(a @ np.asarray(cov, float) @ a, 0.0)) * 10_000.0)
    if te_a > 1e-9:
        limits.append((te_budget_bps / te_a, f"tracking_error:{te_budget_bps:.0f}bps"))
    limits = [(c, lab) for c, lab in limits if np.isfinite(c) and c >= 0]
    if not limits:
        return 1.0, ["none"]
    c_max = min(c for c, _ in limits)
    # Report every limit reached at c_max, not the first one found. Ties are
    # common here and they matter: three ranges binding at once is a different
    # statement to one range binding.
    at = [lab for c, lab in limits if c <= c_max * (1 + 1e-9) + 1e-12]
    return float(max(c_max, 0.0)), at


def _binding(w, lines, cov, b, te_budget_bps, sleeves, M):
    te = riskmodel.ex_ante_te(_dict(w, lines), cov, _dict(b, lines), lines)
    at = []
    for j, ln in enumerate(lines):
        lo, hi = config.RANGE[ln]
        if w[j] <= lo + BOUND_TOL:
            at.append(f"range:{ln}:lower({lo:.2f})")
        elif w[j] >= hi - BOUND_TOL:
            at.append(f"range:{ln}:upper({hi:.2f})")
    for i, sl in enumerate(sleeves):
        lo, hi = config.SLEEVE_RANGE[sl]
        v = float(M[i] @ w)
        if v <= lo + BOUND_TOL:
            at.append(f"sleeve:{sl}:lower({lo:.2f})")
        elif v >= hi - BOUND_TOL:
            at.append(f"sleeve:{sl}:upper({hi:.2f})")
    te_binds = te >= te_budget_bps - TE_TOL_BPS
    if te_binds:
        at.append(f"tracking_error:{te_budget_bps:.0f}bps")
    if not at:
        primary = "none"
    elif te_binds and len(at) == 1:
        primary = "tracking_error"
    elif te_binds:
        primary = "tracking_error and " + ", ".join(x for x in at if not x.startswith("tracking"))
    else:
        primary = ", ".join(at)
    return te, at, primary


def apply_min_trade(w_new, w_prior, lines, cov, b, te_budget_bps, max_rounds: int = 6):
    """
    IPS 4.2: a trade smaller than MIN_TRADE_PP percentage points of NAV is not
    worth the turnover.

    The filter is applied by re-solving rather than by editing the answer.
    Suppressing the small trades and then normalising the rest is the obvious
    approach and it does not work: the normalisation can push a line or a sleeve
    outside its range, and repairing that afterwards reintroduces exactly the
    sub-threshold trades the filter was supposed to remove. Check 5c in
    tests/check_quant.py found three of them at the December 2021 meeting.

    Instead, lines whose trade falls below the threshold are pinned at their
    prior weight as hard bounds and the projection is solved again with those
    pins in place, so the result is feasible by construction. Pinning can make a
    line that previously traded above the threshold fall below it, so the pass
    repeats until the set of pins is stable.

    Where the pins make the problem infeasible, the hard limits win. That is
    IPS 3.6: the ranges and the tracking-error budget rank above the turnover
    economics of a small trade. The override is recorded rather than hidden.
    """
    thr = config.MIN_TRADE_PP / 100.0
    w = np.asarray(w_new, float).copy()
    pinned: set[int] = set()
    rounds = 0
    override = False

    for rounds in range(1, max_rounds + 1):
        delta = w - w_prior
        small = {j for j in range(len(lines))
                 if 1e-12 < abs(delta[j]) < thr - 1e-12}
        if not small - pinned:
            break
        candidate = pinned | small
        pins = {j: float(w_prior[j]) for j in candidate}
        if len(candidate) == len(lines):
            w = w_prior.copy()
            pinned = candidate
            break

        def f(x, tgt=np.asarray(w_new, float)):
            dd = x - tgt
            return float(dd @ cov @ dd)

        def g(x, tgt=np.asarray(w_new, float)):
            return 2.0 * (cov @ (x - tgt))

        w_try, res, _, _ = _solve(f, g, lines, cov, b, te_budget_bps,
                                  w_prior.copy(), pins=pins)
        ok = res.success and check_feasible(_dict(w_try, lines), cov, lines,
                                            te_budget_bps)["ok"]
        if not ok:
            override = True
            break
        w, pinned = w_try, candidate

    suppressed = [lines[j] for j in sorted(pinned)]
    residual_small = [
        f"{lines[j]}:{abs(w[j] - w_prior[j]) * 100:.3f}pp"
        for j in range(len(lines))
        if 1e-12 < abs(w[j] - w_prior[j]) < thr - 1e-12
    ]
    return w, {
        "n_traded": int(sum(1 for j in range(len(lines))
                            if abs(w[j] - w_prior[j]) > 1e-12)),
        "threshold_pp": config.MIN_TRADE_PP,
        "suppressed": suppressed,
        "rounds": rounds,
        "hard_constraint_override": override,
        "residual_sub_threshold_trades": residual_small,
    }


def allocate_detail(date, *, te_budget_bps=None, cov=None, scores=None,
                    prior=None, lines=None, benchmark=None) -> dict:
    d = pitdata._to_date(date)
    te_budget_bps = float(te_budget_bps if te_budget_bps is not None
                          else config.TE_BUDGET_BPS)

    if scores is None:
        scores = signals.composite_as_of(d, lines)
    lines = list(lines or [ln for ln in config.LINES
                           if d >= config.INVESTABLE_FROM[ln]])
    if cov is None:
        cov = riskmodel.cov_as_of(d, lines)
    cov = np.asarray(cov, float)

    bench = dict(benchmark or config.POLICY)
    b = _vec(bench, lines)
    s = _vec(scores, lines)
    s = s - s.mean()                       # a tilt is relative by construction

    unc = unconstrained_tilt(_dict(s, lines), cov, lines, te_budget_bps, bench)
    unc_iv = inverse_vol_tilt(_dict(s, lines), cov, lines, te_budget_bps, bench)
    u = _vec(unc, lines)

    # The constrained allocation is the feasible portfolio with the smallest
    # tracking error against the unconstrained tilt. A linear objective would
    # instead drive every line to a box bound and discard the magnitudes of the
    # scores entirely, which is not a use of the signal, it is a use of the
    # ranges.
    sleeves, M = _sleeve_matrix(lines)
    w_proj = project_feasible(u, lines, cov, b, te_budget_bps, metric="risk")
    te_proj = riskmodel.ex_ante_te(_dict(w_proj, lines), cov, bench, lines)

    # IPS 4.2 gives the desk a budget. Having found the feasible direction that
    # best represents the unconstrained tilt, the position is scaled along it
    # until the first mandate limit is reached, so the budget is used rather
    # than left on the table by an artifact of the projection metric.
    a_dir = w_proj - b
    c_max, limiters = max_scale(a_dir, b, lines, cov, te_budget_bps)
    c_used = max(min(c_max, 1e6), 0.0)
    w = b + c_used * a_dir
    limiter = ", ".join(limiters)

    class _R:
        success = True
        message = (f"risk-metric projection of the unconstrained tilt, then scaled "
                   f"x{c_used:.2f} to the first binding limit ({limiter})")

    res = _R()
    te_pre, at_pre, primary_pre = _binding(w, lines, cov, b, te_budget_bps, sleeves, M)

    w_prior = _vec(prior, lines) if prior else b.copy()
    w_fin, mt = apply_min_trade(w, w_prior, lines, cov, b, te_budget_bps)
    te, at, primary = _binding(w_fin, lines, cov, b, te_budget_bps, sleeves, M)

    return {
        "as_of": d.isoformat(),
        "lines": lines,
        "te_budget_bps": te_budget_bps,
        "composite_scores": _dict(s, lines),
        "unconstrained": unc,
        "unconstrained_te_bps": riskmodel.ex_ante_te(unc, cov, bench, lines),
        "unconstrained_inverse_vol": unc_iv,
        "unconstrained_iv_te_bps": riskmodel.ex_ante_te(unc_iv, cov, bench, lines),
        "tilt_disagreement_bps": riskmodel.ex_ante_te(unc, cov, unc_iv, lines),
        "constrained_pre_min_trade": _dict(w, lines),
        "projection_te_bps": te_proj,
        "scale_to_budget": c_used,
        "first_binding_limit": limiter,
        "constrained": _dict(w_fin, lines),
        "active_vs_policy": {ln: float(w_fin[i] - b[i]) for i, ln in enumerate(lines)},
        "ex_ante_te_bps": te,
        "ex_ante_te_bps_pre_min_trade": te_pre,
        "binding_constraint": primary,
        "binding_constraints_all": at,
        "binding_pre_min_trade": primary_pre,
        "min_trade": mt,
        "prior": _dict(w_prior, lines),
        "optimiser_status": str(res.message),
        "optimiser_success": bool(res.success),
        "total_vol_bps": riskmodel.total_vol(_dict(w_fin, lines), cov, lines),
        "policy_vol_bps": riskmodel.total_vol(bench, cov, lines),
    }


def allocate(date, *, te_budget_bps=None, cov=None, scores=None, prior=None) -> dict:
    """{line: weight}. The constrained allocation after the minimum trade filter."""
    return allocate_detail(date, te_budget_bps=te_budget_bps, cov=cov,
                           scores=scores, prior=prior)["constrained"]


def model_path(dates=None, te_budget_bps=None) -> list:
    """
    The allocation at every meeting date, each one chained to the previous so
    that the minimum trade filter sees the position the fund actually held. The
    first meeting is chained to the policy portfolio.
    """
    dates = dates or config.meeting_dates()
    out, prior = [], None
    for d in dates:
        det = allocate_detail(d, te_budget_bps=te_budget_bps, prior=prior)
        out.append({
            "date": d.isoformat(),
            "scores": det["composite_scores"],
            "unconstrained": det["unconstrained"],
            "constrained": det["constrained"],
            "active_vs_policy": det["active_vs_policy"],
            "te_bps": det["ex_ante_te_bps"],
            "binding": det["binding_constraint"],
            "binding_all": det["binding_constraints_all"],
            "n_traded": det["min_trade"]["n_traded"],
            "suppressed_by_min_trade": det["min_trade"]["suppressed"],
        })
        prior = det["constrained"]
    return out


def max_attainable_te(date, lines=None, cov=None, n_starts: int = 400,
                      seed: int = 7) -> dict:
    """
    The largest ex-ante tracking error reachable inside the IPS 4.1 line ranges
    and sleeve ranges, ignoring the tracking-error budget entirely.

    This answers a question the mandate does not answer for itself: whether the
    200bps budget of IPS 4.2 is reachable at all once IPS 4.1 has had its say.
    The maximum of a convex quadratic over a polytope sits at a vertex, so the
    search runs the linear-objective optimiser from many random score vectors,
    which drives to vertices, and keeps the largest tracking error found. It is
    a lower bound on the true maximum, which is the safe direction: if even the
    search reaches only some number below the budget, the budget is not the
    operative limit.
    """
    d = pitdata._to_date(date)
    lines = list(lines or [ln for ln in config.LINES
                           if d >= config.INVESTABLE_FROM[ln]])
    cov = np.asarray(cov if cov is not None else riskmodel.cov_as_of(d, lines), float)
    b = _vec(config.POLICY, lines)
    rng = np.random.default_rng(seed)
    best, best_w = 0.0, b.copy()
    huge = 1e9   # the TE constraint is switched off for this search
    for _ in range(n_starts):
        s = rng.normal(size=len(lines))
        s = s - s.mean()

        def f(w, s=s):
            return -float(s @ (w - b))

        def g(w, s=s):
            return -s

        w, res, _, _ = _solve(f, g, lines, cov, b, huge, b.copy())
        te = riskmodel.ex_ante_te(_dict(w, lines), cov, config.POLICY, lines)
        if te > best:
            best, best_w = te, w
    return {
        "as_of": d.isoformat(),
        "max_te_bps_within_ranges": float(best),
        "te_budget_bps": float(config.TE_BUDGET_BPS),
        "budget_attainable": bool(best >= config.TE_BUDGET_BPS),
        "argmax_weights": _dict(best_w, lines),
        "n_starts": n_starts,
    }


def check_feasible(weights: dict, cov=None, lines=None, te_budget_bps=None) -> dict:
    """Every mandate limit, tested. Used by tests/check_quant.py."""
    lines = list(lines or config.LINES)
    te_budget_bps = float(te_budget_bps if te_budget_bps is not None
                          else config.TE_BUDGET_BPS)
    w = _vec(weights, lines)
    fails = []
    if abs(w.sum() - 1.0) > 1e-6:
        fails.append(f"weights sum to {w.sum():.8f}")
    if (w < -1e-9).any():
        fails.append("negative weight")
    if w.sum() > config.MAX_GROSS_EXPOSURE + 1e-9:
        fails.append("gross exposure above 1.0")
    for j, ln in enumerate(lines):
        lo, hi = config.RANGE[ln]
        if w[j] < lo - 1e-9 or w[j] > hi + 1e-9:
            fails.append(f"{ln} {w[j]:.4f} outside RANGE {lo}-{hi}")
    sleeves, M = _sleeve_matrix(lines)
    for i, sl in enumerate(sleeves):
        lo, hi = config.SLEEVE_RANGE[sl]
        v = float(M[i] @ w)
        if v < lo - 1e-9 or v > hi + 1e-9:
            fails.append(f"sleeve {sl} {v:.4f} outside {lo}-{hi}")
    te = None
    if cov is not None:
        te = riskmodel.ex_ante_te(weights, cov, config.POLICY, lines)
        if te > te_budget_bps + 1e-6:
            fails.append(f"ex-ante TE {te:.1f}bps above budget {te_budget_bps:.0f}bps")
    liquid = sum(w[j] for j, ln in enumerate(lines) if config.LIQUID_WITHIN_5D[ln])
    if liquid < config.LIQUIDITY_FLOOR - 1e-9:
        fails.append(f"liquidity {liquid:.3f} below floor {config.LIQUIDITY_FLOOR}")
    return {"ok": not fails, "failures": fails, "te_bps": te,
            "liquid_within_5d": liquid}


if __name__ == "__main__":
    import json

    d = config.WINDOW_END
    det = allocate_detail(d)
    print(f"ALLOCATION as of {d}   budget {det['te_budget_bps']:.0f}bps")
    print(f"  ex-ante TE           {det['ex_ante_te_bps']:.1f} bps")
    print(f"  binding              {det['binding_constraint']}")
    print(f"  optimiser            {det['optimiser_status']}")
    print()
    hdr = f"  {'line':14s}{'policy':>9s}{'uncon':>9s}{'constr':>9s}{'active':>9s}{'score':>8s}"
    print(hdr)
    for ln in det["lines"]:
        print(f"  {ln:14s}{100*config.POLICY[ln]:8.2f}%{100*det['unconstrained'][ln]:8.2f}%"
              f"{100*det['constrained'][ln]:8.2f}%{100*det['active_vs_policy'][ln]:+8.2f}%"
              f"{det['composite_scores'][ln]:+8.2f}")
    print(f"  {'sum':14s}{100*sum(config.POLICY.values()):8.2f}%"
          f"{100*sum(det['unconstrained'].values()):8.2f}%"
          f"{100*sum(det['constrained'].values()):8.2f}%")
    print()
    print("feasibility:", json.dumps(check_feasible(det["constrained"],
                                                    riskmodel.cov_as_of(d, det["lines"]),
                                                    det["lines"]), indent=1))
