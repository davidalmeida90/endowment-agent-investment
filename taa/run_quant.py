"""
taa.run_quant — produces every file in outputs/quant/.

Run:  py -3 -m taa.run_quant
"""

from __future__ import annotations

import datetime as _dt
import json
import time

import numpy as np
import pandas as pd

from . import config, evidence, optimiser, riskmodel, signals

OUT = config.OUTPUTS / "quant"
OUT.mkdir(parents=True, exist_ok=True)


def _clean(o):
    if isinstance(o, dict):
        return {str(k): _clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_clean(v) for v in o]
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        return None if not np.isfinite(o) else float(o)
    if isinstance(o, float):
        return None if not np.isfinite(o) else o
    if isinstance(o, (np.bool_,)):
        return bool(o)
    if isinstance(o, np.ndarray):
        return _clean(o.tolist())
    if isinstance(o, (_dt.date, _dt.datetime)):
        return o.isoformat()
    if isinstance(o, (pd.Timestamp,)):
        return str(o.date())
    return o


def write(name: str, blob) -> None:
    p = OUT / name
    p.write_text(json.dumps(_clean(blob), indent=2), encoding="utf-8")
    print(f"  wrote {p.relative_to(config.ROOT)}  ({p.stat().st_size:,} bytes)")


def main() -> int:
    t0 = time.time()
    d = config.WINDOW_END
    print(f"Ashcroft TAA — Quantitative desk")
    print(f"  window   {config.WINDOW_START} .. {config.WINDOW_END}  "
          f"({len(config.month_ends())} months, {len(config.meeting_dates())} meetings)")
    print(f"  as of    {d}\n")

    # ---- risk model -----------------------------------------------------
    print("risk model")
    cd = riskmodel.cov_detail_as_of(d)
    path = riskmodel.shrinkage_path()
    write("riskmodel.json", {
        "as_of": d.isoformat(),
        "estimator": ("Ledoit-Wolf (2003/2004) shrinkage of the sample covariance "
                      "toward a constant-correlation target, implemented from the "
                      "published formulae; the intensity is analytical, not chosen"),
        "window_months": riskmodel.COV_WINDOW_M,
        "lines": cd["lines"],
        "current": {
            "delta": cd["delta"],
            "mean_sample_correlation": cd["rbar"],
            "n_obs": cd["n_obs"],
            "first_obs": cd["first_obs"],
            "last_obs": cd["last_obs"],
            "cond_cov_sample": cd["cond_sample"],
            "cond_cov_shrunk": cd["cond_shrunk"],
            "cond_corr_sample": cd["cond_corr_sample"],
            "cond_corr_shrunk": cd["cond_corr_shrunk"],
            "min_eigenvalue_sample": cd["eig_min_sample"],
            "min_eigenvalue_shrunk": cd["eig_min_shrunk"],
            "annualised_vol": dict(zip(cd["lines"], cd["vol"])),
            "covariance": {a: dict(zip(cd["lines"], cd["cov"][i]))
                           for i, a in enumerate(cd["lines"])},
            "correlation": {a: dict(zip(cd["lines"], cd["corr"][i]))
                            for i, a in enumerate(cd["lines"])},
            "sample_correlation": {a: dict(zip(cd["lines"], cd["corr_sample"][i]))
                                   for i, a in enumerate(cd["lines"])},
        },
        "shrinkage_path": path.to_dict(orient="records"),
        "condition_number_note": (
            "the covariance condition number is dominated by the cash line, whose "
            "annualised variance is three orders of magnitude below the equity "
            "lines; that is scale, not conditioning. The correlation condition "
            "number is the one shrinkage is meant to move and it is reported "
            "beside it."),
        "halflife_variant": {
            "halflife_months": 24,
            "delta": riskmodel.cov_detail_as_of(d, halflife_months=24)["delta"],
            "note": "reported as a robustness check; not used in the allocation",
        },
    })

    # ---- signals and coverage -------------------------------------------
    print("signals")
    s_now = signals.signals_as_of(d)
    cov_rep = signals.coverage_report(d)
    write("signals.json", {
        "as_of": d.isoformat(),
        "meta": s_now["_meta"],
        "citations": signals.CITATION,
        "sign_prior": signals.SIGN,
        "z_scores": {ln: s_now[ln] for ln in s_now["_meta"]["lines"]},
        "raw": s_now["_raw"],
        "composite": signals.composite_as_of(d),
    })
    write("coverage.json", cov_rep)

    # ---- evidence -------------------------------------------------------
    print("out-of-sample evidence")
    r2_full = evidence.r2oos_table(d, window_only=False)
    r2_win = evidence.r2oos_table(d, window_only=True)
    write("r2oos.json", {
        "headline": _headline(r2_full),
        "full_sample": r2_full,
        "study_window_only": r2_win,
        "base_rate_context": (
            "Welch and Goyal (2008) find almost no equity-premium predictor "
            "beats the historical mean out of sample; Harvey, Liu and Zhu (2016) "
            "argue most published cross-sectional factors would not survive a "
            "multiple-testing correction; Hou, Xue and Zhang (2020) replicate 452 "
            "anomalies and find 65 per cent fail at conventional significance. "
            "The prior a reader should hold before reading this table is that a "
            "minority of these cells will be positive."),
    })

    print("volatility")
    vf = evidence.variance_forecast_study(d)
    vm = evidence.vol_management_study(d)
    write("volmgmt.json", {
        "as_of": d.isoformat(),
        "question_a_is_variance_forecastable": vf,
        "question_b_does_scaling_help_this_mandate": vm,
        "verdict": _vol_verdict(vf, vm),
    })

    # ---- allocation -----------------------------------------------------
    # The model path is built first so that the allocation at the report date is
    # chained to the position the fund would actually be holding coming into the
    # meeting. Running it against the policy portfolio instead would let the
    # minimum trade filter see a position nobody held.
    print("model path")
    mp = optimiser.model_path()
    write("model_path.json", mp)

    print("allocation")
    prior = mp[-2]["constrained"] if len(mp) > 1 else dict(config.POLICY)
    det = optimiser.allocate_detail(d, prior=prior)
    mx = optimiser.max_attainable_te(d, lines=det["lines"])
    ev_comp = r2_full["pooled"].get("composite", {})

    n_pos, n_tot = _cell_counts(r2_full)
    confidence = "low"
    rationale = (
        "The desk recommends the policy portfolio. The composite signal has a "
        "pooled out-of-sample R2 of "
        f"{100 * ev_comp.get('r2oos_pooled', float('nan')):+.2f} per cent against "
        "the expanding historical mean, negative on "
        f"{ev_comp.get('n_negative')} of {ev_comp.get('n_cells')} lines, with a "
        f"Clark-West t of {ev_comp.get('cw_t_pooled', float('nan')):+.2f}. Across "
        f"the five signals and eight risky lines, {n_pos} of {n_tot} cells are "
        "positive. On that evidence the estimator does not earn active risk, and "
        "the size of a tilt should follow the evidence for it rather than the size "
        "of the budget available to express it. The constrained allocation reported "
        "here is the mechanical output of the optimiser run at the full budget; it "
        "is the model's answer and it is what outputs/quant/model_path.json holds at "
        "every meeting, so that the Committee can reconstruct the record. It is not "
        "what the desk recommends carrying. The binding constraint at this date is "
        f"{det['binding_constraint']}, at "
        f"{det['ex_ante_te_bps']:.0f}bps of ex-ante tracking error against a "
        f"{config.TE_BUDGET_BPS:.0f}bps budget: the line ranges stop the tilt long "
        "before the budget does, although the budget is reachable in other "
        f"directions (up to {mx['max_te_bps_within_ranges']:.0f}bps)."
    )

    write("allocation.json", {
        "as_of": d.isoformat(),
        "unconstrained": det["unconstrained"],
        "constrained": det["constrained"],
        "active_vs_policy": det["active_vs_policy"],
        "ex_ante_te_bps": det["ex_ante_te_bps"],
        "binding_constraint": det["binding_constraint"],
        "composite_scores": det["composite_scores"],
        "confidence": confidence,
        "rationale": rationale,

        # --- everything below is additional to the required schema ---
        "recommendation": {
            "headline": "hold policy weights; do not spend the tracking-error budget",
            "weights": dict(config.POLICY),
            "active_vs_policy": {ln: 0.0 for ln in det["lines"]},
            "ex_ante_te_bps": 0.0,
            "basis": ("composite pooled R2_oos "
                      f"{100 * ev_comp.get('r2oos_pooled', float('nan')):+.2f}%, "
                      f"{n_pos}/{n_tot} signal-line cells positive"),
        },
        "confidence_definition": (
            "low: the desk's own out-of-sample test does not reject the null that "
            "the signal has no forecasting power, and the point estimate is on the "
            "wrong side of zero"),
        "policy": dict(config.POLICY),
        "te_budget_bps": config.TE_BUDGET_BPS,
        "unconstrained_te_bps": det["unconstrained_te_bps"],
        "unconstrained_inverse_vol": det["unconstrained_inverse_vol"],
        "tilt_disagreement_bps": det["tilt_disagreement_bps"],
        "constrained_pre_min_trade": det["constrained_pre_min_trade"],
        "projection_te_bps": det["projection_te_bps"],
        "scale_to_budget": det["scale_to_budget"],
        "binding_constraints_all": det["binding_constraints_all"],
        "first_binding_limit": det["first_binding_limit"],
        "min_trade": det["min_trade"],
        "max_attainable_te": {k: v for k, v in mx.items() if k != "argmax_weights"},
        "total_vol_bps": det["total_vol_bps"],
        "policy_vol_bps": det["policy_vol_bps"],
        "optimiser": det["optimiser_status"],
        "feasibility": optimiser.check_feasible(
            det["constrained"], riskmodel.cov_as_of(d, det["lines"]), det["lines"]),
        "horizon": "twelve months from 30 June 2026, reviewed quarterly (IPS 2.2)",
        "prior_holding": prior,
        "prior_holding_source": ("the constrained model allocation set at the "
                                 "31 March 2026 meeting, chained through "
                                 "outputs/quant/model_path.json"),
    })

    # a compact index for the dashboard
    write("summary.json", {
        "as_of": d.isoformat(),
        "window": config.window(),
        "degrees_of_freedom_signals": signals.N_DEGREES_OF_FREEDOM,
        "degrees_of_freedom_evaluation": len(evidence.EVAL_PARAMS),
        "composite_r2oos_pooled": ev_comp.get("r2oos_pooled"),
        "composite_cw_t": ev_comp.get("cw_t_pooled"),
        "cells_positive": n_pos,
        "cells_total": n_tot,
        "recommendation": "policy weights",
        "model_te_bps": det["ex_ante_te_bps"],
        "binding_constraint": det["binding_constraint"],
        "shrinkage_delta_now": cd["delta"],
        "vol_management_verdict": _vol_verdict(vf, vm)["headline"],
        "runtime_seconds": round(time.time() - t0, 1),
    })

    print(f"\ndone in {time.time() - t0:.1f}s")
    return 0


def _cell_counts(tbl):
    pos = tot = 0
    for sname in signals.SIGNALS:
        for c in tbl["cells"].get(sname, {}).values():
            if c.get("r2oos") is None:
                continue
            tot += 1
            if c["r2oos"] > 0:
                pos += 1
    return pos, tot


def _headline(tbl):
    pos, tot = _cell_counts(tbl)
    comp = tbl["pooled"].get("composite", {})
    return {
        "sentence": (
            f"{pos} of {tot} signal-line cells have a positive out-of-sample R2 "
            "against the expanding historical mean. The composite scores "
            f"{100 * comp.get('r2oos_pooled', float('nan')):+.2f} per cent pooled, "
            f"Clark-West t {comp.get('cw_t_pooled', float('nan')):+.2f}. On this "
            "evidence the signals do not beat assuming the historical average, and "
            "the implication is policy weights."),
        "cells_positive": pos,
        "cells_total": tot,
        "composite_pooled_r2oos": comp.get("r2oos_pooled"),
        "composite_cw_t": comp.get("cw_t_pooled"),
    }


def _vol_verdict(vf, vm):
    cells = vf["cells"]
    n_var = sum(1 for c in cells.values() if c["r2oos_variance_ewma"] > 0)
    n_log = sum(1 for c in cells.values() if c["r2oos_logvar_ewma"] > 0)
    fs, sw = vm["full_sample"], vm["study_window"]
    return {
        "headline": (
            "variance is forecastable in rank terms and on a proportional loss, "
            "and scaling the policy portfolio by the forecast did not improve "
            "risk-adjusted return on this window"),
        "a_forecastable": {
            "series_with_positive_variance_r2oos": f"{n_var}/{len(cells)}",
            "series_with_positive_logvariance_r2oos": f"{n_log}/{len(cells)}",
            "policy_rank_correlation": cells.get("_policy", {}).get("rank_corr_ewma"),
            "reading": ("the forecast ranks quiet months against noisy ones, which "
                        "is real information, and it loses on squared error in the "
                        "level of variance because a handful of spike months "
                        "dominate that loss"),
        },
        "b_does_it_pay": {
            "full_sample_sharpe": [fs["unscaled"]["sharpe_ann"],
                                   fs["scaled_capped"]["sharpe_ann"]],
            "full_sample_sharpe_se": fs["unscaled"]["sharpe_ann_se"],
            "study_window_sharpe": [sw["unscaled"]["sharpe_ann"],
                                    sw["scaled_capped"]["sharpe_ann"]],
            "study_window_sharpe_se": sw["unscaled"]["sharpe_ann_se"],
            "max_drawdown": [fs["unscaled"]["max_drawdown"],
                             fs["scaled_capped"]["max_drawdown"]],
            "reading": ("no. On the full post-warmup sample the scaled portfolio "
                        "is worse; on the study window it is indistinguishable. "
                        "Neither difference is large against a Sharpe standard "
                        "error of this size. This lands with Cederburg, O'Doherty, "
                        "Wang and Yan (2020) rather than with Moreira and Muir "
                        "(2017), and the reason is the leverage cap: the mandate "
                        "forbids the levered leg that carries the published result."),
        },
    }


if __name__ == "__main__":
    raise SystemExit(main())
