"""
tests/test_compliance.py — the test of the test.

    "Show the test rejecting something. A compliance test that has only ever
     passed is not evidence that the portfolio complies, it is evidence that the
     test was written to agree."

This file plants a defect in an allocation, one defect per binding constraint,
and asserts that taa.compliance names the right constraint at the right rank.
It also runs the policy portfolio itself, which is the control: a test that
rejects the Board's own benchmark is broken, and a test that has never rejected
anything has not been shown to work.

Two failure modes are asserted, not one.

  A rejection case must FAIL, and it must fail on the constraint that was
  planted. A case that fails for the wrong reason is recorded as an error,
  because it means the test agreed with the verdict by accident.

  A rejection case must also PASS the constraints it was designed not to
  breach. This is what makes case 2 worth anything: IPS 4.1 says a position
  inside the tracking-error budget and outside its range is a breach, so the
  case is only evidence if the tracking error check genuinely passes while the
  range check genuinely fails.

Exits non-zero if any expectation is unmet. Writes every result to
outputs/compliance_demo.json.

Run:  py -3 -m tests.test_compliance
      py -3 tests/test_compliance.py
"""

from __future__ import annotations

import datetime as dt
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

if __package__ in (None, ""):                      # py -3 tests/test_compliance.py
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from taa import compliance, config, pitdata        # noqa: E402


# ==========================================================================
# The covariance matrix
# ==========================================================================
def covariance(max_wait_s: int = 360) -> tuple[np.ndarray, str]:
    """
    Annualised covariance of the nine mandate lines, from monthly total returns
    read point in time through taa.pitdata (IPS 4.4).

    The raw cache is populated by a background job, so this waits for it. If it
    never arrives the suite falls back to a synthetic covariance so that the
    logic of every check is still exercised, and it says so loudly, because a
    rejection demonstrated on invented numbers is a demonstration of the code
    and not of the portfolio.
    """
    deadline = time.time() + max_wait_s
    last = None
    while time.time() < deadline:
        try:
            r = pitdata.as_of(config.REPORT_DATE).monthly_returns()
            if len(r) >= 36:
                return r.cov().values * 12.0, (
                    f"taa.pitdata monthly returns, {len(r)} months to "
                    f"{r.index.max().date()}, annualised"
                )
            last = f"only {len(r)} monthly observations"
        except FileNotFoundError as exc:
            last = f"FileNotFoundError: {exc}"
        except Exception as exc:                                  # noqa: BLE001
            last = f"{type(exc).__name__}: {exc}"
        time.sleep(30)

    vol = np.array([0.155, 0.165, 0.200, 0.070, 0.075, 0.085, 0.180, 0.185, 0.006])
    c = np.array([
        [1.00, 0.86, 0.78, -0.20, 0.20, 0.72, 0.35, 0.75, 0.00],
        [0.86, 1.00, 0.85, -0.12, 0.28, 0.72, 0.42, 0.68, 0.00],
        [0.78, 0.85, 1.00, -0.08, 0.32, 0.70, 0.46, 0.60, 0.00],
        [-0.20, -0.12, -0.08, 1.00, 0.78, 0.10, -0.10, 0.22, 0.05],
        [0.20, 0.28, 0.32, 0.78, 1.00, 0.60, 0.10, 0.45, 0.04],
        [0.72, 0.72, 0.70, 0.10, 0.60, 1.00, 0.35, 0.62, 0.00],
        [0.35, 0.42, 0.46, -0.10, 0.10, 0.35, 1.00, 0.30, 0.00],
        [0.75, 0.68, 0.60, 0.22, 0.45, 0.62, 0.30, 1.00, 0.00],
        [0.00, 0.00, 0.00, 0.05, 0.04, 0.00, 0.00, 0.00, 1.00],
    ])
    return (np.outer(vol, vol) * c), (
        f"SYNTHETIC covariance. The point-in-time cache did not become available "
        f"within {max_wait_s}s ({last}). Every number below is a demonstration of "
        f"the code and not of the portfolio."
    )


# ==========================================================================
# Weight helpers
# ==========================================================================
def w(**over) -> dict[str, float]:
    """The policy portfolio with named lines overridden."""
    out = dict(config.POLICY)
    for k, v in over.items():
        if k not in config.LINES:
            raise KeyError(f"{k} is not a mandate line")
        out[k] = v
    return out


def nav_with_drawdown(depth: float, n: int = 260) -> pd.Series:
    """A NAV path that rises, falls by `depth`, then partially recovers."""
    up = np.linspace(1.00, 1.18, n // 3)
    down = np.linspace(1.18, 1.18 * (1.0 + depth), n // 3)
    back = np.linspace(1.18 * (1.0 + depth), 1.18 * (1.0 + depth) * 1.06, n - 2 * (n // 3))
    idx = pd.bdate_range("2024-01-01", periods=n)
    return pd.Series(np.concatenate([up, down, back]) * config.FUND_NAV_USD, index=idx)


ALL_ILLIQUID_BUT_CASH = {k: False for k in config.LINES if k != "cash"}


# ==========================================================================
# The cases
# ==========================================================================
# expect_fail  constraints that MUST appear in .failed()
# expect_pass  constraints that MUST have passed, which is what isolates a case
CASES: list[dict] = [
    {
        "name": "policy_control",
        "planted": "Nothing. This is the Board's own policy portfolio (IPS 4.1).",
        "why": "The control. If the policy portfolio fails this test, the test is wrong.",
        "weights": dict(config.POLICY),
        "kwargs": {"prior_weights": dict(config.POLICY)},
        "expect_pass_overall": True,
        "expect_fail": set(),
        "expect_pass": {"liquidity_floor", "liquidity_distribution", "leverage_gross",
                        "leverage_short", "drawdown_ex_ante", "drawdown_stress",
                        "tracking_error", "line_range", "sleeve_range", "min_trade",
                        "investable_date", "structural_sum"},
    },
    {
        "name": "range_breach_inside_te",
        "planted": "US investment grade cut to 2.50% against a 3% to 13% range, moved "
                   "into cash. A defensive tilt, so tracking error stays at roughly a "
                   "quarter of the budget and portfolio volatility falls.",
        "why": "The case IPS 4.1 names by name: a position inside the tracking-error "
               "budget and outside its range is a breach. It is planted on the "
               "defensive side deliberately, so that no other constraint can be "
               "credited with the rejection. Tracking error passes, the drawdown "
               "tests pass because the proposal carries less risk than policy, and the "
               "range check fails on its own.",
        "weights": w(us_ig=0.025, cash=0.055),
        "kwargs": {"prior_weights": dict(config.POLICY)},
        "expect_pass_overall": False,
        "expect_fail": {"line_range"},
        "expect_pass": {"tracking_error", "sleeve_range", "leverage_gross",
                        "liquidity_floor", "min_trade", "drawdown_ex_ante",
                        "drawdown_stress"},
    },
    {
        "name": "te_breach_ranges_ok",
        "planted": "Every line pushed to an end of its own permitted range at once. "
                   "US equity 48%, developed ex-US 12%, EM 5%, Treasuries 22%, IG 3%, "
                   "high yield 0%, commodities 0%, real estate 0%, cash 10%.",
        "why": "The mirror of the previous case. Every line is legal on its own and the "
               "combination is not, which is what a tracking-error budget exists to "
               "catch and a range set cannot.",
        "weights": {"us_equity": 0.48, "dev_ex_us": 0.12, "em_equity": 0.05,
                    "ust_duration": 0.22, "us_ig": 0.03, "us_hy": 0.00,
                    "commodities": 0.00, "listed_re": 0.00, "cash": 0.10},
        "kwargs": {"prior_weights": dict(config.POLICY)},
        "expect_pass_overall": False,
        "expect_fail": {"tracking_error"},
        "expect_pass": {"line_range", "sleeve_range", "leverage_gross", "leverage_short",
                        "liquidity_floor", "drawdown_ex_ante"},
    },
    {
        "name": "negative_weight_leverage",
        "planted": "Cash at (5.00%), funding US equity at 43%. Gross exposure 1.10 times "
                   "net asset value.",
        "why": "A short is leverage at fund level. IPS 3.5 ties the prohibition to "
               "unrelated business taxable income on debt-financed income and says it is "
               "not a risk preference that analysis may trade against. Rank 2.",
        "weights": w(us_equity=0.43, cash=-0.05),
        "kwargs": {"prior_weights": dict(config.POLICY)},
        "expect_pass_overall": False,
        "expect_fail": {"leverage_gross", "leverage_short"},
        "expect_pass": {"structural_sum", "sleeve_range"},
    },
    {
        "name": "liquidity_floor_breach",
        "planted": "The custodian reports that every vehicle except the T-bill line has "
                   "stopped clearing within five business days at fund size. Cash stands "
                   "at 1% of NAV, so 1% of the fund is realisable same week.",
        "why": "Rank 1, not negotiable. It also fails the second arm: the quarterly "
               "distribution is 1.12% of NAV and cannot be met from 1%, so the draw "
               "forces a sale.",
        "weights": w(us_equity=0.37, cash=0.01),
        "kwargs": {"prior_weights": dict(config.POLICY),
                   "context": {"liquid_within_5d": ALL_ILLIQUID_BUT_CASH}},
        "expect_pass_overall": False,
        "expect_fail": {"liquidity_floor", "liquidity_distribution"},
        "expect_pass": {"leverage_gross", "line_range", "sleeve_range"},
    },
    {
        "name": "dust_trade_30bp",
        "planted": "A 30bps shift from emerging markets into US equity, against a 50bps "
                   "minimum trade.",
        "why": "IPS 4.2 sets the minimum trade at 50bps and IPS 4.5 says a corridor "
               "narrower than the minimum cannot be acted on. A change strictly between "
               "zero and the minimum cannot be executed, so the portfolio that would "
               "result is a different portfolio from the one tested. Every other "
               "constraint is satisfied, which is the point: the allocation is legal "
               "and it is not implementable.",
        "weights": w(us_equity=0.383, em_equity=0.117),
        "kwargs": {"prior_weights": dict(config.POLICY)},
        "expect_pass_overall": False,
        "expect_fail": {"min_trade"},
        "expect_pass": {"line_range", "sleeve_range", "tracking_error", "leverage_gross",
                        "drawdown_ex_ante", "liquidity_floor"},
    },
    {
        "name": "sleeve_breach_lines_ok",
        "planted": "Equity sleeve at 82% against a 60% to 80% band, built from US equity "
                   "45%, developed ex-US 24% and EM 13%, each comfortably inside its own "
                   "line range.",
        "why": "A sleeve can breach while every line inside it is legal, which is why "
               "IPS 4.1 sets both and why testing only the lines would miss it.",
        "weights": {"us_equity": 0.45, "dev_ex_us": 0.24, "em_equity": 0.13,
                    "ust_duration": 0.08, "us_ig": 0.05, "us_hy": 0.03,
                    "commodities": 0.01, "listed_re": 0.01, "cash": 0.00},
        "kwargs": {"prior_weights": dict(config.POLICY)},
        "expect_pass_overall": False,
        "expect_fail": {"sleeve_range"},
        "expect_pass": {"line_range", "leverage_gross", "leverage_short",
                        "liquidity_floor"},
    },
    {
        "name": "drawdown_breach",
        "planted": "The most drawdown-exposed allocation the range set permits. Equity at "
                   "the 80% sleeve ceiling with EM at its 19% maximum, high yield at its "
                   "10% maximum, Treasury duration at its 5% floor and no cash.",
        "why": "Every line and every sleeve is legal. The drawdown exposure is not. "
               "Rank 3, hard.",
        "weights": {"us_equity": 0.48, "dev_ex_us": 0.13, "em_equity": 0.19,
                    "ust_duration": 0.05, "us_ig": 0.03, "us_hy": 0.10,
                    "commodities": 0.00, "listed_re": 0.02, "cash": 0.00},
        "kwargs": {"prior_weights": dict(config.POLICY)},
        "expect_pass_overall": False,
        "expect_fail": {"drawdown_ex_ante"},
        "expect_pass": {"line_range", "sleeve_range", "leverage_gross", "liquidity_floor"},
    },
    {
        "name": "realised_drawdown_breach",
        "planted": "The policy weights, with a realised NAV path that fell 26% peak to "
                   "trough.",
        "why": "The mandate limit at IPS 3.3 is on realised drawdown. This is the only "
               "arm of the drawdown test that measures the thing the Board actually "
               "wrote down rather than a model's opinion about it.",
        "weights": dict(config.POLICY),
        "kwargs": {"prior_weights": dict(config.POLICY),
                   "nav_path": nav_with_drawdown(-0.26)},
        "expect_pass_overall": False,
        "expect_fail": {"drawdown_realised"},
        "expect_pass": {"line_range", "sleeve_range", "tracking_error"},
    },
    {
        "name": "direct_exclusion_breach",
        "planted": "The commodities line implemented through a vehicle carrying direct "
                   "thermal coal exposure, as reported by the Implementation desk.",
        "why": "IPS 3.5 permits no direct exposure to tobacco or thermal coal. Direct is "
               "a hard fail and is a different outcome from the incidental index exposure "
               "that the same section requires to be disclosed.",
        "weights": dict(config.POLICY),
        "kwargs": {"prior_weights": dict(config.POLICY),
                   "context": {"direct_exposure": {"commodities": ["thermal coal"]}}},
        "expect_pass_overall": False,
        "expect_fail": {"board_exclusions"},
        "expect_pass": {"line_range", "sleeve_range", "leverage_gross"},
    },
    {
        "name": "investable_date_breach",
        "planted": "The policy weights proposed as at 30 June 2005, when high yield "
                   "(HYG, 2007) and commodities (DBC, 2006) did not yet exist.",
        "why": "IPS 4.1: investable dates bind. A portfolio that holds a vehicle before "
               "it listed is not a portfolio anyone could have held. The stress replay "
               "refuses to run for the same reason and is recorded as a qualification, "
               "which is the point-in-time wall at IPS 4.4 doing its job rather than a "
               "second defect.",
        "weights": dict(config.POLICY),
        "kwargs": {"as_of": dt.date(2005, 6, 30), "prior_weights": dict(config.POLICY)},
        "expect_pass_overall": False,
        "expect_fail": {"investable_date"},
        "expect_pass": {"line_range", "sleeve_range", "leverage_gross"},
    },
    {
        "name": "malformed_nan",
        "planted": "US equity set to NaN.",
        "why": "A weight vector carrying a NaN is not a proposal. Nothing downstream of "
               "it may report a pass, because a check that silently treats NaN as zero "
               "certifies a portfolio nobody proposed.",
        "weights": w(us_equity=float("nan")),
        "kwargs": {"prior_weights": dict(config.POLICY)},
        "expect_pass_overall": False,
        "expect_fail": {"structural_finite", "line_range", "tracking_error",
                        "liquidity_floor", "drawdown_ex_ante"},
        "expect_pass": set(),
    },
    {
        "name": "weights_do_not_sum",
        "planted": "US equity at 40%, leaving the weights summing to 102%.",
        "why": "An allocation that does not sum to one is not an allocation. Caught "
               "before any economic constraint is read.",
        "weights": w(us_equity=0.40),
        "kwargs": {"prior_weights": dict(config.POLICY)},
        "expect_pass_overall": False,
        "expect_fail": {"structural_sum"},
        "expect_pass": {"line_range", "leverage_short"},
    },
    {
        "name": "covariance_withheld",
        "planted": "The policy weights, with no covariance matrix supplied.",
        "why": "Absence of evidence is not evidence of compliance. A risk function that "
               "cannot measure the rank 4 tracking-error budget must not certify "
               "compliance with it, so a withheld input reads as NOT ASSESSED and the "
               "proposal does not proceed.",
        "weights": dict(config.POLICY),
        "kwargs": {"prior_weights": dict(config.POLICY), "no_cov": True},
        "expect_pass_overall": False,
        "expect_fail": {"tracking_error", "drawdown_ex_ante"},
        "expect_pass": {"line_range", "sleeve_range", "liquidity_floor", "leverage_gross"},
    },
]


# ==========================================================================
# Runner
# ==========================================================================
def run() -> int:
    cov, cov_source = covariance()
    synthetic = cov_source.startswith("SYNTHETIC")

    print("=" * 110)
    print("ASHCROFT UNIVERSITY ENDOWMENT      TEST OF THE COMPLIANCE TEST")
    print("=" * 110)
    print(f"As at           {config.REPORT_DATE}")
    print(f"Covariance      {cov_source}")
    print(f"Cases           {len(CASES)}, of which 1 is the control")
    print("=" * 110)
    print()

    records, errors = [], []

    for case in CASES:
        kw = dict(case["kwargs"])
        kw.pop("no_cov", None)
        use_cov = None if case["kwargs"].get("no_cov") else cov
        ctx = dict(kw.pop("context", {}) or {})
        ctx.setdefault("label", case["name"])

        res = compliance.check(case["weights"], cov=use_cov, context=ctx, **kw)

        failed = {c.name for c in res.failed()}
        passed = {c.name for c in res.results if c.passed}

        problems = []
        if res.passed != case["expect_pass_overall"]:
            problems.append(
                f"expected overall {'PASS' if case['expect_pass_overall'] else 'FAIL'}, "
                f"got {res.status}"
            )
        missing_fail = case["expect_fail"] - failed
        if missing_fail:
            problems.append(
                f"planted defect not caught: expected these to fail and they did not: "
                f"{sorted(missing_fail)}"
            )
        missing_pass = case["expect_pass"] - passed
        if missing_pass:
            problems.append(
                f"case is not isolated: expected these to pass and they did not: "
                f"{sorted(missing_pass)}"
            )
        if case["expect_pass_overall"] and failed:
            problems.append(f"control failed on {sorted(failed)}")

        if problems:
            errors.append((case["name"], problems))

        rec = res.to_dict()
        rec["case"] = case["name"]
        rec["planted"] = case["planted"]
        rec["why_it_matters"] = case["why"]
        rec["expected_overall"] = "PASS" if case["expect_pass_overall"] else "FAIL"
        rec["expected_failures"] = sorted(case["expect_fail"])
        rec["expected_passes"] = sorted(case["expect_pass"])
        rec["expectation_met"] = not problems
        rec["expectation_problems"] = problems
        rec["report"] = str(res)
        records.append(rec)

        mark = "as expected" if not problems else "UNEXPECTED"
        print(f"{case['name']:<28} {res.status:<22} "
              f"rank {str(res.governing_rank() or '-'):<3} "
              f"named: {', '.join(sorted(failed)) or 'nothing':<60.60} [{mark}]")

    # ---------------------------------------------------------------- table
    print()
    print("=" * 118)
    print("REJECTION TABLE")
    print("=" * 118)
    hdr = (f"{'CASE':<28}{'PLANTED DEFECT':<44}{'VERDICT':<22}"
           f"{'RANK':<6}{'CONSTRAINT NAMED BY THE TEST':<30}")
    print(hdr)
    print("-" * 118)
    for r in records:
        named = ", ".join(r["failed"]) or "none"
        planted = r["planted"]
        planted = planted if len(planted) <= 43 else planted[:40] + "..."
        print(f"{r['case']:<28}{planted:<44}{r['status']:<22}"
              f"{str(r['governing_rank'] or '-'):<6}{named[:29]:<30}")
    print("-" * 118)

    # ------------------------------------------------------ the named case
    print()
    print("THE CASE IPS 4.1 NAMES: INSIDE THE TRACKING-ERROR BUDGET AND OUTSIDE A RANGE")
    print("-" * 118)
    c2 = next(r for r in records if r["case"] == "range_breach_inside_te")
    te = next(c for c in c2["checks"] if c["name"] == "tracking_error")
    lr = next(c for c in c2["checks"] if c["name"] == "line_range")
    outside = ", ".join(lr["detail"]["outside"]) or "none"
    print(f"  Planted          {c2['planted']}")
    print(f"  Tracking error   {te['observed']:.1f}bps against {te['limit']:.0f}bps, "
          f"{te['slack']:.1f}bps of budget unused    {te['status']}")
    print(f"  Line range       outside its permitted range: {outside}    {lr['status']}")
    print(f"  Overall          {c2['status']}, governed by {c2['failed']}")
    print("  IPS 4.1: the permitted range binds independently of the tracking-error budget.")
    print("  A position inside the tracking-error budget but outside its range is a breach.")

    # -------------------------------------------------------------- control
    print()
    print("CONTROL: THE POLICY PORTFOLIO")
    print("-" * 118)
    ctrl = next(r for r in records if r["case"] == "policy_control")
    print(f"  Verdict          {ctrl['status']}")
    print(f"  Failed checks    {ctrl['failed'] or 'none'}")
    print(f"  Binding          {', '.join(ctrl['binding']) or 'none'}")
    print(f"  Disclosures      {len(ctrl['disclosure_rows'])} required under IPS 3.5")
    print(f"  Qualifications   {ctrl['qualifications'] or 'none'}")

    # ----------------------------------------------------------------- json
    out = {
        "generated": dt.datetime.now().isoformat(timespec="seconds"),
        "report_date": config.REPORT_DATE.isoformat(),
        "covariance_source": cov_source,
        "covariance_is_synthetic": synthetic,
        "drawdown_model": {
            "method": "driftless Brownian motion, quantile of the maximum drawdown",
            "horizon_years": compliance.MDD_HORIZON_YEARS,
            "quantile": compliance.MDD_QUANTILE,
            "monte_carlo_paths": compliance.MDD_MC_PATHS,
            "monte_carlo_steps": compliance.MDD_MC_STEPS,
            "seed": compliance.MDD_MC_SEED,
            "closed_form_expected": "sqrt(pi/2) . sigma . sqrt(T), Magdon-Ismail, Atiya, "
                                    "Pratap and Abu-Mostafa (2004)",
            "gate": "the more permissive of config.DRAWDOWN_LIMIT and the same model's "
                    "reading of config.POLICY, so the test cannot reject the Board's own "
                    "benchmark",
        },
        "stress_episodes_declared": [
            {"episode": n, "start": s, "end": e} for n, s, e in compliance.STRESS_EPISODES
        ],
        "n_cases": len(records),
        "n_expectations_met": sum(1 for r in records if r["expectation_met"]),
        "all_expectations_met": not errors,
        "cases": records,
    }
    path = config.OUTPUTS / "compliance_demo.json"
    path.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print()
    print(f"Written  {path}")

    # ---------------------------------------------------------------- verdict
    print()
    print("=" * 118)
    if errors:
        print(f"SUITE FAILED. {len(errors)} case(s) did not behave as specified.")
        for name, problems in errors:
            print(f"  {name}")
            for p in problems:
                print(f"      {p}")
        print("=" * 118)
        return 1
    print(f"SUITE PASSED. {len(CASES)} cases. Every planted defect was rejected on the "
          f"constraint that was planted,")
    print("and the policy portfolio passed the same test unchanged.")
    if synthetic:
        print()
        print("QUALIFICATION: the covariance was synthetic, so the tracking-error and "
              "ex-ante drawdown")
        print("numbers demonstrate the code rather than the portfolio.")
    print("=" * 118)
    return 0


# ==========================================================================
# Mutation sweep
# ==========================================================================
# A suite that passes proves the code agrees with the suite. It does not prove
# the suite would notice if the code stopped working. Each entry below disables
# one check by making it return PASS unconditionally, in a sandbox copy of the
# package, and the sweep asserts the suite fails. A mutation that survives is
# a check nothing is testing.
MUTATIONS = [
    ('"line_range", "IPS 4.1", PASS if ok else FAIL,',
     '"line_range", "IPS 4.1", PASS,'),
    ('"sleeve_range", "IPS 4.1", PASS if ok else FAIL,',
     '"sleeve_range", "IPS 4.1", PASS,'),
    ('"tracking_error", "IPS 4.2", PASS if ok else FAIL,',
     '"tracking_error", "IPS 4.2", PASS,'),
    ('"leverage_gross", "IPS 3.5", PASS if gross <= cap + FLOAT_EPS else FAIL,',
     '"leverage_gross", "IPS 3.5", PASS,'),
    ('"leverage_short", "IPS 3.5", PASS if not shorts else FAIL,',
     '"leverage_short", "IPS 3.5", PASS,'),
    ('"liquidity_floor", "IPS 3.4", PASS if liquid >= floor - FLOAT_EPS else FAIL,',
     '"liquidity_floor", "IPS 3.4", PASS,'),
    ('"liquidity_distribution", "IPS 3.4", PASS if ok else FAIL,',
     '"liquidity_distribution", "IPS 3.4", PASS,'),
    ('"min_trade", "IPS 4.2", PASS if ok else FAIL,',
     '"min_trade", "IPS 4.2", PASS,'),
    ('"investable_date", "IPS 4.1", PASS if ok else FAIL, margin=False,',
     '"investable_date", "IPS 4.1", PASS, margin=False,'),
    ('"drawdown_realised", "IPS 3.3", PASS if ok else FAIL,',
     '"drawdown_realised", "IPS 3.3", PASS,'),
    ('"drawdown_ex_ante", "IPS 3.3", PASS if ok else FAIL,',
     '"drawdown_ex_ante", "IPS 3.3", PASS,'),
    ('"structural_sum", "IPS 4.1", PASS if dev <= WEIGHT_SUM_TOL else FAIL, margin=False,',
     '"structural_sum", "IPS 4.1", PASS, margin=False,'),
    ('"structural_finite", "IPS 4.1", PASS if not bad else FAIL, margin=False,',
     '"structural_finite", "IPS 4.1", PASS, margin=False,'),
]


def mutate() -> int:
    """Run the suite against one disabled check at a time. Every mutant must die."""
    import shutil
    import subprocess
    import tempfile

    root = Path(__file__).resolve().parent.parent
    print("=" * 100)
    print("MUTATION SWEEP. Each run disables one check. The suite must fail every time.")
    print("=" * 100)
    survivors = []
    for i, (old, new) in enumerate(MUTATIONS, 1):
        with tempfile.TemporaryDirectory() as td:
            sandbox = Path(td) / "study"
            shutil.copytree(root, sandbox, ignore=shutil.ignore_patterns(
                "__pycache__", ".git", "*.pyc"))
            target = sandbox / "taa" / "compliance.py"
            src = target.read_text(encoding="utf-8")
            if src.count(old) != 1:
                print(f"{i:>3}. ANCHOR MISS, mutation not applied: {old[:58]}")
                survivors.append(old)
                continue
            target.write_text(src.replace(old, new), encoding="utf-8")
            proc = subprocess.run(
                [sys.executable, "-m", "tests.test_compliance"],
                cwd=sandbox, capture_output=True, text=True)
            died = proc.returncode != 0
            name = old.split('"')[1]
            print(f"{i:>3}. {name:<26} disabled -> suite exit {proc.returncode}  "
                  f"{'mutant died' if died else 'MUTANT SURVIVED'}")
            if not died:
                survivors.append(name)
    print("-" * 100)
    if survivors:
        print(f"{len(survivors)} mutant(s) survived: {survivors}")
        print("A surviving mutant is a check that nothing in the suite is testing.")
        print("=" * 100)
        return 1
    print(f"All {len(MUTATIONS)} mutants died. Every check is load bearing.")
    print("=" * 100)
    return 0


if __name__ == "__main__":
    if "--mutate" in sys.argv:
        raise SystemExit(mutate())
    raise SystemExit(run())
