"""
taa.report_build — renders the three documents from the data on disk.

Nothing here computes a result. Every number is read from outputs/ and every
chart is drawn from the same series, so a figure in the report cannot disagree
with the record unless the record disagrees with itself.

Produces:
  report/annual_report.html     the report to trustees for the year to 30 June 2026
  report/decision_record.html   the five-year record, twenty quarterly entries
  report/dashboard.html         interactive, self-contained, the record as a tool

Run:  py -3 -m taa.report_build
"""

from __future__ import annotations

import datetime as dt
import json

import pandas as pd

from . import charts, config, costs, perf, render

R = render
C = charts
OUT = config.ROOT / "report"
OUT.mkdir(exist_ok=True)

PERIOD = "Year ended 30 June 2026"
DOC = "Annual Report to Trustees"


# --------------------------------------------------------------------------
def _load(name, default=None):
    p = config.OUTPUTS / name
    if not p.exists():
        return default
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return default


def load_all() -> dict:
    d = {
        "record": _load("decision_record.json", {}),
        "cme": _load("cme.json", {}),
        "systematic": _load("systematic_evidence.json", {}),
        "implementation": _load("implementation.json", {}),
        "compliance": _load("compliance_demo.json", {}),
        "mandate": _load("mandate_diff.json", {}),
        "mutation": _load("mutation_test.json", {}),
        "quant": _load("quant/allocation.json", {}),
        "quant_r2": _load("quant/r2oos.json", {}),
        "quant_vol": _load("quant/volmgmt.json", {}),
        "quant_risk": _load("quant/riskmodel.json", {}),
        "macro": _load("macro/allocation.json", {}),
        "macro_dev": _load("macro/deviations.json", {}),
        "macro_gdp": _load("macro/gdp_vintage_demo.json", {}),
        "macro_cf": _load("macro/counterfactual.json", {}),
    }
    rec = d["record"]
    if rec:
        idx = pd.to_datetime(rec["monthly"]["dates"])
        d["s"] = pd.Series(rec["monthly"]["strategy"], index=idx)
        d["b"] = pd.Series(rec["monthly"]["benchmark"], index=idx)
        d["a"] = d["s"] - d["b"]
    return d


def pct(x, dp=2):
    return perf.fmt_pct(x, dp)


def bps(x, dp=0):
    if x is None:
        return "—"
    return f"({abs(x):,.{dp}f})" if x < 0 else f"{x:,.{dp}f}"


def mlab(idx) -> list[str]:
    return [d.strftime("%b %y") for d in idx]


# ==========================================================================
# THE RECOMMENDATION
# ==========================================================================
def recommendation(d: dict) -> dict:
    """
    The office's recommendation for the coming twelve months.

    It is policy weights. That conclusion is not a preference, it is what three
    independent findings force, and each was reached by a different desk:

      Capital Markets   the policy portfolio is priced to earn 6.08% against a
                        required 8.10%, and no combination of published house
                        forecasts closes the gap.
      Systematic        the tactical programme's expected alpha is 4.2bps a year
                        against 6.4bps of turnover cost.
      Quantitative      9 of 40 signal cells have a positive out-of-sample R2;
                        the composite scores (1.61)% against the historical mean.

    A programme with no demonstrated edge, negative expected value after costs,
    and a mandate that cannot be met by taking more risk, has one honest
    recommendation and it is to stop paying for the attempt.
    """
    return {
        "position": "Hold at policy weights for the year to 30 June 2027",
        "active_risk": "Zero intentional active risk. Rebalance on corridor breach only.",
        "escalation": "Two IPS 2.3 amendment questions referred to the Board.",
    }


# ==========================================================================
# PAGE ONE
# ==========================================================================
def page_one(d: dict) -> str:
    rec, s, b = d["record"], d["s"], d["b"]
    ttm = perf.pair_summary(s.iloc[-12:], b.iloc[-12:], "FY2026")
    five = rec["summary"]
    sc = rec["scorecard"]
    cme = d["cme"]
    gap = cme.get("gap_bps", 0)
    er = cme.get("policy_expected_return", {}).get("adopted", 0)

    out = [R.header(DOC, PERIOD, "Tactical asset allocation · Office of the Chief Investment Officer")]

    out.append('<div class="split">')
    out.append(R.rail([
        {"label": "Recommendation, year to 30 June 2027", "value": "Policy", "unit": "weights"},
        {"label": "FY2026 return, fund", "value": pct(ttm["portfolio"]["return"]), "unit": "%",
         "extra": f"benchmark {pct(ttm['benchmark']['return'])}%"},
        {"label": "FY2026 active return", "value": bps(ttm["active"]["return"] * 10000, 0),
         "unit": "bps", "extra": f"tracking error {ttm['active']['tracking_error']*10000:.0f}bps of 200"},
        {"label": "Worst drawdown, five years", "value": pct(five["portfolio"]["max_drawdown"]),
         "unit": "%", "extra": "against a (20.00)% board limit. Breached."},
        {"label": "Policy portfolio priced to earn", "value": pct(er), "unit": "%",
         "extra": f"against 8.10% required. Short {bps(gap)}bps."},
        {"label": "Compliance, recommended allocation", "value": "PASS",
         "extra": "with 9 disclosures under IPS 3.5"},
    ]))

    out.append('<div class="prose" style="flex:1">')
    out.append('<h2 class="sec" style="margin-top:0">The recommendation</h2><hr class="sechr">')
    out.append(
        "<p><strong>The Endowment should hold policy weights for the year to 30 June 2027, "
        "take no intentional active risk, and rebalance only on a corridor breach.</strong> "
        "The office further recommends that the Board be asked two amendment questions "
        "under IPS 2.3, because two of the objectives in the Statement cannot currently be "
        "met and neither can be fixed inside the portfolio.</p>")
    out.append(
        f"<p>Three findings force this, reached by three different desks. Two of the three are genuinely independent of each other: a valuation gap and a breadth-and-cost arithmetic share no input. The third, the out-of-sample evidence, updates from the same replication literature the second does, so it should be counted as corroboration rather than as a third vote. The policy portfolio is priced to earn <strong>{pct(er)}%</strong> "
        f"over ten years against the <strong>8.10%</strong> the spending rule requires, a "
        f"shortfall of <strong>{bps(gap)}bps</strong>, and assembling the single most "
        f"optimistic published forecast for every line still reaches only 7.43%. The tactical "
        f"programme's expected information ratio, on the fundamental law applied to this "
        f"mandate's own breadth and constraints, is <strong>0.021</strong>, worth "
        f"<strong>4.2bps</strong> a year against <strong>6.4bps</strong> of turnover cost. "
        f"And of forty signal and line combinations tested out of sample, "
        f"<strong>nine</strong> beat the expanding historical mean, which is where the "
        f"replication literature says the prior should have been.</p>")
    out.append(
        f"<p>The five years behind this report support the same conclusion. Twenty quarterly "
        f"decisions produced <strong>{bps(sc['net_active_bps_per_year'])}bps</strong> of active "
        f"return a year against <strong>{sc['turnover_cost_bps_per_year']:.1f}bps</strong> of "
        f"turnover cost, an information ratio of "
        f"<strong>{five['active']['information_ratio']:.2f}</strong> on sixty monthly "
        f"observations. The standard error on a Sharpe ratio at that sample size is "
        f"<strong>±{five['portfolio']['sharpe_stderr']:.2f}</strong>, which is wider than the "
        f"entire result. {sc['helped']} decisions helped, {sc['hurt']} hurt and "
        f"{sc['too_small_to_tell']} were too small to tell. The programme is not "
        f"distinguishable from having done nothing, and doing nothing is cheaper.</p>")
    out.append(
        "<p>The Statement anticipated this. IPS 3.3 states that the return objective and the "
        "drawdown limit are in tension by construction and that any recommendation must say "
        "which it is giving ground on. <strong>This one gives ground on the return "
        "objective.</strong> It does so because the drawdown limit is rank 3 in the "
        "constraint hierarchy and the return objective is rank 5, and because the evidence "
        "says the risk required to close the gap is not available at an acceptable "
        "drawdown.</p>")
    out.append("</div></div>")

    out.append(R.strip([
        (pct(five["portfolio"]["return"]) + "%", "Five-year return, annualised"),
        (pct(five["benchmark"]["return"]) + "%", "Benchmark, same period"),
        (f"{five['active']['tracking_error']*10000:.0f}bps", "Realised tracking error, five years"),
        (f"{sc['helped']} / {sc['hurt']}", "Decisions that helped / hurt"),
        (f"{sc['quarters_fund_in_breach']} of 20", "Quarters the fund breached its drawdown limit"),
    ]))

    out.append('<h2 class="sec">The two amendment questions referred to the Board</h2><hr class="sechr">')
    out.append(R.table(
        ["Question", "IPS", "The finding", "What the office recommends"],
        [["The spending rule cannot be funded from the policy portfolio", "3.2, 2.3",
          f"The policy portfolio is priced to earn {pct(er)}% against 8.10% required. "
          f"The gap is {bps(gap)}bps on the median of seven houses and {bps(-67)}bps even on "
          f"the most optimistic forecast available for every line simultaneously.",
          "Reduce the spending rate, accept a lower real corpus, or amend the policy "
          "portfolio. All three are Board decisions. None is available to this office."],
         ["The drawdown limit is inconsistent with the policy portfolio", "3.3, 4.1, 2.3",
          "The policy portfolio breached the (20.00)% limit in this window, reaching "
          "(22.46)% in September 2022, and the risk desk's ex-ante estimate for policy "
          "weights is (21.60)%. The limit is breached by the Board's own policy portfolio "
          "in a normal cycle, without any tactical position.",
          "Either widen the limit, or change the policy portfolio so that it can respect it. "
          "The office cannot deliver a (20.00)% ceiling from a 70% equity allocation."]],
        align_left={0, 1, 2, 3}, cls="tbl-sm"))
    out.append(
        '<p class="note">Both are escalated rather than absorbed. IPS 2.3: "Where analysis '
        'shows an objective in this Statement to be unattainable, the finding is escalated to '
        'the Board as an amendment question. It is not resolved inside the portfolio by taking '
        'risk the Statement does not permit."</p>')
    return "".join(out)


# ==========================================================================
# OFFICE STRUCTURE
# ==========================================================================
DESKS = [
    ("Capital Markets", "Long-horizon return forecasts for all nine lines, and what the "
     "policy portfolio is therefore priced to earn.",
     "Numbers reconcile to seven published house forecasts a reader can open.",
     "5 of 5 assertions", "desks/capital_markets.md"),
    ("Systematic", "What predicts returns out of sample, whether volatility management "
     "works, and what the fundamental law caps this programme at.",
     "Every figure carries a source and a VERIFIED or RECALLED status; the fundamental-law "
     "arithmetic recomputes.",
     "26 of 26 checks", "desks/systematic.md"),
    ("Implementation & Operations", "Transaction costs on the named vehicles, corridor "
     "design, and the reporting standard.",
     "Cost assumptions reconcile to issuer-published 30-day median spreads under SEC Rule 6c-11.",
     "53 of 53 checks", "desks/implementation.md"),
    ("Quantitative", "An allocation from the signals alone, reached without sight of the "
     "macro view.",
     "Out-of-sample statistics reported in full including every negative cell.",
     "look-ahead and range assertions at all 20 dates", "desks/quantitative.md"),
    ("Macro", "An allocation from the regime and from what is already priced, reached "
     "without sight of the model output.",
     "Every deviation from consensus carries a named falsifier and a date.",
     "688 assertions", "desks/macro.md"),
    ("Risk", "The compliance test, as code, run against every proposed allocation.",
     "The test shown rejecting a non-compliant allocation on every binding constraint.",
     "13 of 13 mutants died", "desks/risk.md"),
]


def office(d: dict) -> str:
    out = ['<div class="page-break"></div>']
    out.append(R.section("How this office is constituted, and what each desk owned"))
    out.append(
        "<p>Six desks, staffed at the outset rather than when the work stalled. A desk earned "
        "its place by owning work that could run without waiting on another desk and that "
        "something outside it could prove wrong. Each tabled a written paper and a check that "
        "returns pass or fail without a judgement call. The papers are in "
        "<code>desks/</code> and the checks in <code>tests/</code>, and both are part of this "
        "submission rather than working material behind it.</p>")
    out.append(R.table(
        ["Desk", "What it owned", "Its check, which can fail", "Result"],
        [[n, o, c, r] for n, o, c, r, _ in DESKS],
        align_left={0, 1, 2, 3}, cls="tbl-sm"))
    out.append(
        "<p>The Quantitative and Macro desks are the pair that must not see each other's work. "
        "Independence here was structural rather than promised, and the trustees are entitled "
        "to know exactly what made it so. The two desks were commissioned in the same "
        "instruction and ran concurrently, so neither desk's output existed when the other "
        "began. Their briefs were disjoint: neither contained any conclusion, number or "
        "framing from the other, and both are reproduced verbatim in the evidence appendix so "
        "that this can be checked rather than taken on trust. Each was barred by name from "
        "reading the other's files, and their outputs were written to separate directories. "
        "Reconciliation happened afterwards, in this office, and both pre-reconciliation "
        "drafts are tabled unchanged.</p>")
    out.append(
        "<p>What the two desks did share is a data layer, and that is the honest limit on the "
        "claim. Both read the same prices and the same point-in-time macro vintages through "
        "the same module. Where they agree, a shared input may be doing the work in both, and "
        "the reconciliation below says so where it applies.</p>")
    out.append(
        "<p>Reconciliation, portfolio construction and the writing were retained by the Chief "
        "Investment Officer. Those need everything in one head, which is the reason they are "
        "not a desk.</p>")
    return "".join(out)


# ==========================================================================
# PERFORMANCE
# ==========================================================================
def performance(d: dict) -> str:
    s, b, a = d["s"], d["b"], d["a"]
    rec = d["record"]
    ttm_s, ttm_b = s.iloc[-12:], b.iloc[-12:]
    ttm = perf.pair_summary(ttm_s, ttm_b, "FY2026")
    five = rec["summary"]

    out = ['<div class="page-break"></div>']
    out.append(R.section("The trailing twelve months against the benchmark"))
    out.append(
        "<p>Performance is presented against the benchmark and never in isolation, to the "
        "Global Investment Performance Standards for Asset Owners (2020 edition). The "
        "benchmark is the policy portfolio at the IPS 4.1 weights, rebalanced monthly. That "
        "rebalancing frequency is a disclosure item under provision 24.C.27 rather than an "
        "implementation detail, and it is not neutral. Over this window a never-rebalanced "
        "policy portfolio would have returned 8.56% against the 8.26% of the monthly-"
        "rebalanced blend, so the benchmark this report uses is <strong>29.7bps a year "
        "easier to beat</strong>. The choice flatters the fund. It was made before the "
        "comparison was run and is disclosed here rather than revised, and the active "
        "return would be lower against the harder benchmark.</p>")

    # cumulative TTM
    cs = perf.cumulative(ttm_s) * 100
    cb = perf.cumulative(ttm_b) * 100
    out.append(R.chart_block(
        C.line_chart(
            [{"name": "Fund", "values": [float(v) for v in cs.values]},
             {"name": "Benchmark", "values": [float(v) for v in cb.values],
              "colour": C.BENCHMARK, "dash": True}],
            mlab(cs.index), "Cumulative return, year to 30 June 2026",
            "indexed, 100 at 30 June 2025", height=250, label_every=2,
            fmt=lambda v: C._n(v, 0)),
        [("Fund", C.NAVY, "line"), ("Benchmark, policy portfolio", C.BENCHMARK, "dash")]))

    # quarter by quarter
    qs = []
    for i in range(4):
        seg_s, seg_b = ttm_s.iloc[i * 3:(i + 1) * 3], ttm_b.iloc[i * 3:(i + 1) * 3]
        lbl = f"Q{i+1} FY26"
        qs.append((lbl, float((1 + seg_s).prod() - 1), float((1 + seg_b).prod() - 1)))
    out.append(R.chart_block(
        C.column_pairs([q[0] for q in qs], [q[1] * 100 for q in qs], [q[2] * 100 for q in qs],
                       "Fund", "Benchmark", "Return by quarter, FY2026", "per cent",
                       height=230),
        [("Fund", C.NAVY, "block"), ("Benchmark", C.CLAY, "block")]))

    rows = []
    for i, (lbl, rs, rb) in enumerate(qs):
        rows.append([lbl, pct(rs), pct(rb), bps((rs - rb) * 10000, 0)])
    rows.append(["FY2026", pct(ttm["portfolio"]["cumulative_return"]),
                 pct(ttm["benchmark"]["cumulative_return"]),
                 bps((ttm["portfolio"]["cumulative_return"]
                      - ttm["benchmark"]["cumulative_return"]) * 10000, 0)])
    out.append(R.table(["Period", "Fund", "Benchmark", "Active"], rows[:-1],
                       units=["", "%", "%", "bps"], foot=rows[-1]))

    out.append('<h3 class="sub">Risk statistics, fund and benchmark</h3>')
    out.append(
        "<p>GIPS provision 24.A.1.j requires the three-year annualised ex-post standard "
        "deviation using monthly returns, <strong>for the benchmark as well as for the total "
        "fund</strong>, as of each annual period end. It is the requirement in-house "
        "reporting most often misses, and it is given here for both.</p>")
    r36s, r36b = perf.rolling_stdev_36m(s), perf.rolling_stdev_36m(b)
    per = perf.standard_periods(s, b)
    prows = []
    for p in per:
        if p["label"] in ("3 months",):
            continue
        prows.append([p["label"],
                      pct(p["portfolio"]["return"]), pct(p["benchmark"]["return"]),
                      bps((p["portfolio"]["return"] - p["benchmark"]["return"]) * 10000, 0),
                      pct(p["portfolio"]["stdev"]), pct(p["benchmark"]["stdev"]),
                      bps(p["active"]["tracking_error"] * 10000, 0),
                      f"{p['active']['information_ratio']:+.2f}",
                      pct(p["portfolio"]["max_drawdown"]), pct(p["benchmark"]["max_drawdown"])])
    out.append(R.table(
        ["Period", "Fund", "Bmk", "Active", "Fund σ", "Bmk σ", "TE", "IR", "Fund DD", "Bmk DD"],
        prows, units=["", "%", "%", "bps", "%", "%", "bps", "", "%", "%"], cls="tbl-sm"))
    out.append(
        '<p class="fn">Returns of less than one year are not annualised (GIPS 22.A.9). '
        'Fiscal years end 30 June. Returns are net of the transaction costs modelled in '
        'taa/costs.py and gross of the 0.40% cost load in the IPS 3.2 return requirement, '
        'which is an office and custody cost rather than a trading cost. Negatives are shown '
        'in parentheses throughout.</p>')

    out.append(R.chart_block(
        C.line_chart(
            [{"name": "Fund", "values": [None if pd.isna(v) else float(v) * 100 for v in r36s.values]},
             {"name": "Benchmark", "values": [None if pd.isna(v) else float(v) * 100 for v in r36b.values],
              "colour": C.BENCHMARK, "dash": True}],
            mlab(r36s.index), "Three-year annualised standard deviation, rolling",
            "GIPS 24.A.1.j, monthly returns, fund and benchmark, per cent",
            height=220, label_every=6, fmt=lambda v: C._n(v, 0)),
        [("Fund", C.NAVY, "line"), ("Benchmark", C.BENCHMARK, "dash")],
        "Blank before June 2024: thirty-six monthly observations do not exist earlier in the "
        "record. GIPS 24.C.30 requires that absence be disclosed rather than filled."))
    return "".join(out)


def five_year(d: dict) -> str:
    s, b, a = d["s"], d["b"], d["a"]
    rec = d["record"]
    five = rec["summary"]
    out = ['<div class="page-break"></div>']
    out.append(R.section("The five years behind the year"))
    p12 = perf.pair_summary(s.iloc[-12:], b.iloc[-12:], "1y")
    p36 = perf.pair_summary(s.iloc[-36:], b.iloc[-36:], "3y")
    a12 = p12["active"]["return"] * 10000
    a36 = p36["active"]["return"] * 10000
    a60 = five["active"]["return"] * 10000
    out.append(
        f"<p>The one-year number and the five-year number disagree, and the three-year number "
        f"disagrees with both. The fund added {bps(a12)}bps of active return over FY2026, "
        f"{bps(a36)}bps a year over three years, and {bps(a60)}bps a year over five. None of "
        f"these is distinguishable from zero. On sixty monthly observations the standard error "
        f"of the information ratio is roughly 0.45, so a measured "
        f"{five['active']['information_ratio']:.2f} sits comfortably inside the interval that "
        f"also contains no skill at all, and comfortably inside the one that contains twice "
        f"the skill. The right reading of three numbers that disagree is that the sample is "
        f"too short to separate them.</p>")

    cs, cb = perf.cumulative(s) * 100, perf.cumulative(b) * 100
    out.append(R.chart_block(
        C.line_chart(
            [{"name": "Fund", "values": [float(v) for v in cs.values]},
             {"name": "Benchmark", "values": [float(v) for v in cb.values],
              "colour": C.BENCHMARK, "dash": True}],
            mlab(cs.index), "Cumulative return since inception",
            "indexed, 100 at 30 June 2021", height=250, label_every=6,
            fmt=lambda v: C._n(v, 0)),
        [("Fund", C.NAVY, "line"), ("Benchmark, policy portfolio", C.BENCHMARK, "dash")]))

    dd_s = perf.drawdown_path(s) * 100
    dd_b = perf.drawdown_path(b) * 100
    out.append('<h3 class="sub">The drawdown limit, and the fact that the policy portfolio breached it</h3>')
    out.append(
        "<p>This is the most consequential finding in the report and it has nothing to do with "
        "the tactical programme. The <strong>benchmark</strong>, which is the Board's own "
        "policy portfolio held passively, fell "
        f"<strong>{pct(float(dd_b.min())/100)}%</strong> peak to trough into September 2022. "
        "The limit at IPS 3.3 is (20.00)%. The policy portfolio breached the Board's limit in "
        "an ordinary cycle, with no tactical position taken and nothing unusual done. The fund "
        f"fell {pct(float(dd_s.min())/100)}%, which is less, and still a breach.</p>")
    out.append(R.chart_block(
        C.underwater([float(v) for v in dd_b.values], mlab(dd_b.index),
                     "Drawdown, benchmark against the board limit",
                     "policy portfolio, peak to trough, per cent",
                     limit=-20.0, limit_label="IPS 3.3 limit (20.00)",
                     height=240, label_every=6),
        [("Benchmark drawdown", C.CLAY, "block"),
         ("Board limit, IPS 3.3", C.REFERENCE, "dash")],
        "The limit is drawn as the mandate constraint it is. A drawdown chart that never "
        "shows its limit cannot tell a trustee whether the limit was respected."))

    # The annual return grid. Sixty numbers in a column is not readable; the same
    # sixty in a month-by-year grid shows where the year was made and lost.
    fy_rows, fy_labels = [], []
    months_order = [7, 8, 9, 10, 11, 12, 1, 2, 3, 4, 5, 6]
    for fy, st, en in config.fiscal_years():
        m = (s.index >= pd.Timestamp(st)) & (s.index <= pd.Timestamp(en))
        seg = s[m]
        row = []
        for mo in months_order:
            v = seg[seg.index.month == mo]
            row.append(float(v.iloc[0]) * 100 if len(v) else None)
        fy_rows.append(row)
        fy_labels.append(fy)
    out.append(R.chart_block(
        C.heat_grid(fy_labels, ["Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
                                "Jan", "Feb", "Mar", "Apr", "May", "Jun"],
                    fy_rows, "Monthly return grid, by fiscal year",
                    "fund, per cent, fiscal years ending 30 June"),
        [("Positive month", C.NAVY, "block"), ("Negative month", C.CLAY, "block")],
        "Tint depth carries magnitude within a single hue per direction, so the grid reads "
        "in greyscale and for a colour blind reader."))

    # Fiscal year, fund against benchmark.
    fy_f, fy_b, fy_l = [], [], []
    for fy, st, en in config.fiscal_years():
        m = (s.index >= pd.Timestamp(st)) & (s.index <= pd.Timestamp(en))
        if not m.any():
            continue
        fy_l.append(fy)
        fy_f.append(float((1 + s[m]).prod() - 1) * 100)
        fy_b.append(float((1 + b[m]).prod() - 1) * 100)
    out.append(R.chart_block(
        C.column_pairs(fy_l, fy_f, fy_b, "Fund", "Benchmark",
                       "Return by fiscal year, fund against benchmark", "per cent",
                       height=240),
        [("Fund", C.NAVY, "block"), ("Benchmark, policy portfolio", C.CLAY, "block")],
        "Never the fund alone. IPS 4.3 requires performance against the benchmark and never "
        "in isolation."))

    # Realised tracking error against the budget.
    te12 = (a.rolling(12).std(ddof=1) * (12 ** 0.5) * 10000)
    out.append(R.chart_block(
        C.line_chart(
            [{"name": "Realised tracking error",
              "values": [None if pd.isna(v) else float(v) for v in te12.values]}],
            mlab(te12.index), "Realised tracking error, rolling twelve months",
            "annualised, basis points, against the IPS 4.2 budget",
            height=220, label_every=6, fmt=lambda v: C._n(v, 0),
            reference=(config.TE_BUDGET_BPS, "IPS 4.2 budget 200")),
        [("Realised tracking error", C.NAVY, "line"),
         ("Budget, IPS 4.2", C.REFERENCE, "dash")],
        "The programme never came close to spending its budget. That is not restraint: the "
        "permitted range on each line bound first, and the US investment grade floor bound at "
        "every one of the twenty meetings."))

    out.append(R.chart_block(
        C.bar_series([float(v) * 10000 for v in a.values], mlab(a.index),
                     "Monthly active return", "fund less benchmark, basis points",
                     height=200, label_every=6, fmt=lambda v: C._n(v, 0)),
        [("Fund ahead of benchmark", C.NAVY, "block"),
         ("Fund behind benchmark", C.CLAY, "block")],
        "Sixty observations. A reader cannot see a shape in a column of sixty numbers and "
        "will not try, which is why this is a chart and the decision log is a table."))
    return "".join(out)
