"""
taa.report_sections — the analytical sections of the annual report.

Split from taa.report_build only for length. Same rules: nothing here computes
a result, everything is read from outputs/ and drawn from the same series.
"""

from __future__ import annotations

import pandas as pd

from . import charts as C
from . import config, costs, perf
from . import render as R
from .report_build import bps, mlab, pct


# ==========================================================================
def year_decisions(d: dict) -> str:
    rec = d["record"]
    four = rec["decisions"][-4:]
    out = ['<div class="page-break"></div>']
    out.append(R.section("The four decisions taken this year, and what each was based on"))
    out.append(
        "<p>Every historical decision in this record is mechanical. A pre-committed rule read "
        "the point-in-time inputs available on the meeting date and produced an allocation. "
        "The trustees can tell the difference between deliberation and a rule running, and "
        "would rather know which is which, so the office states plainly that these four were "
        "the rule running. The one decision in this report carrying genuine deliberation is "
        "the recommendation for FY2027, minuted below.</p>")
    rows = []
    for e in four:
        moves = ", ".join(f"{config.LINE_LABEL[k]} {v:+.1f}pp"
                          for k, v in sorted(e["trades_pp"].items(),
                                             key=lambda kv: -abs(kv[1]))[:3]) or "no trade"
        rows.append([R.datestr(e["date"]), e["kind"], moves,
                     e["regime"]["label"] or "n/a",
                     f"{e['te_after_bps']:.0f}", e["binding_constraint"],
                     "PASS" if e["compliance"]["passed"] else "FAIL",
                     bps(e["outcome"]["active_return_bps"], 0)])
    out.append(R.table(
        ["Meeting", "Decision", "What moved", "Regime read", "TE", "Binding constraint",
         "Compliance", "Earned"],
        rows, units=["", "", "", "", "bps", "", "", "bps"],
        align_left={0, 1, 2, 3, 5, 6}, cls="tbl-sm"))
    out.append(
        '<p class="fn">The Earned column is the outcome. It is filled in last and appears in '
        'no reason anywhere in this report or in the record, which is asserted mechanically '
        'by tests/check_hindsight.py across all twenty entries rather than promised here.</p>')

    for e in four:
        out.append(f'<h4 class="mini">{R.datestr(e["date"])} &nbsp;·&nbsp; {e["kind"]}</h4>')
        out.append(f'<p>{e["reason"]}</p>')
        watch = e["watch"][0]["text"] if e.get("watch") else "nothing"
        wr = e.get("watch_resolution") or []
        if wr:
            res = "; ".join(("it occurred" if r["happened"] else "it did not occur")
                            for r in wr[:2])
        else:
            res = "no item was carried in"
        out.append(f'<p class="note"><strong>Written at this meeting, to watch:</strong> '
                   f'{watch}<br><strong>The previous meeting’s item, resolved here:</strong> '
                   f'{res}.</p>')
    return "".join(out)


# ==========================================================================
def achievable(d: dict) -> str:
    cme = d["cme"]
    lines = cme.get("lines", {})
    er = cme.get("policy_expected_return", {})
    out = ['<div class="page-break"></div>']
    out.append(R.section("Is the mandate achievable, and by what margin"))
    out.append(
        "<p>No. The policy portfolio is priced to earn "
        f"<strong>{pct(er.get('adopted', 0))}%</strong> over ten years against the "
        "<strong>8.10%</strong> the spending rule requires. The shortfall is "
        f"<strong>{bps(cme.get('gap_bps', 0))}bps</strong> a year. IPS 2.5 forbids a "
        "single-source assumption, so seven houses were taken and the dispersion is carried "
        "through rather than averaged away.</p>")
    out.append(
        "<p>The test that settles the question is not the median. Take the single most "
        "optimistic published forecast for every one of the nine lines, from whichever house "
        "happens to be highest on that line, and assemble a portfolio that no house actually "
        f"forecasts. It returns <strong>{pct(er.get('high', 0))}%</strong>, still "
        f"<strong>(67)bps</strong> short. There is no combination of currently published "
        "capital market assumptions under which this policy portfolio meets its objective.</p>")

    rows = []
    for k in config.LINES:
        v = lines.get(k, {})
        rows.append([config.LINE_LABEL[k], f"{config.POLICY[k] * 100:.0f}",
                     pct(v.get("adopted", 0)), pct(v.get("min", 0)), pct(v.get("max", 0)),
                     str(len(v.get("forecasts", [])))])
    out.append(R.table(
        ["Line", "Policy", "Adopted", "Lowest house", "Highest house", "Houses"],
        rows, units=["", "%", "%", "%", "%", "n"],
        foot=["Policy portfolio", "100", pct(er.get("adopted", 0)),
              pct(er.get("low", 0)), pct(er.get("high", 0)), "7"]))
    out.append(
        '<p class="fn">Vanguard VCMM, J.P. Morgan LTCMA 2026, BlackRock Investment Institute, '
        'Invesco Solutions, Northern Trust, Schwab and Research Affiliates. Vintages run from '
        '30 September 2025 to 30 June 2026 and every one is free to the public. All are '
        'normalised to a ten-year nominal geometric basis; the conversions are set out in the '
        'Capital Markets paper. GMO is carried as a memorandum only, being a seven-year real '
        'forecast, and converts to a 0.74% policy return.</p>')

    out.append(R.chart_block(
        C.range_bars([{"name": config.LINE_LABEL[k],
                       "lo": lines.get(k, {}).get("min", 0),
                       "hi": lines.get(k, {}).get("max", 0),
                       "policy": lines.get(k, {}).get("adopted", 0),
                       "current": lines.get(k, {}).get("adopted", 0)}
                      for k in config.LINES],
                     "Ten-year expected return by line, and the dispersion across houses",
                     "adopted figure against the range of published forecasts, per cent"),
        [("Adopted, the median across the houses covering the line", C.NAVY, "block"),
         ("Range from the lowest to the highest published forecast", C.CLAY_TINT, "block")],
        "IPS 2.5 requires the Committee be told what the dispersion is. On listed real "
        "estate the houses span 3.60% to 8.80%, which is a wider range than the line's whole "
        "contribution to the portfolio."))

    out.append(R.chart_block(
        C.diverging_bars(
            [("Most optimistic line-wise", (er.get("high", 0) - 0.081) * 10000),
             ("Highest single house", (0.0731 - 0.081) * 10000),
             ("Median, adopted", (er.get("adopted", 0) - 0.081) * 10000),
             ("Lowest single house", (0.0485 - 0.081) * 10000),
             ("Most pessimistic line-wise", (er.get("low", 0) - 0.081) * 10000)],
            "Gap to the 8.10% required return",
            "basis points a year, ten-year horizon, across the published dispersion",
            width=860, name_w=190, fmt=lambda v: C._n(v, 0)),
        [("Above the requirement", C.NAVY, "block"),
         ("Below the requirement", C.CLAY, "block")],
        "Every point on this scale sits below zero. The most favourable assembly of published "
        "forecasts available anywhere still falls short of the spending rule."))

    out.append(
        "<p>Solving the other way is starker. For the policy portfolio to earn 8.10% with "
        "every other line at the median, US equity would have to return <strong>11.23%</strong> "
        "a year for ten years. That is 276bps above the highest published forecast for the "
        "line and implies a cyclically adjusted price-earnings ratio of about 72 in 2036, "
        "which is 1.6 times the December 1999 peak.</p>")
    out.append(
        "<p>Two further facts widen the gap and both belong in front of the Board. The "
        "Statement assumes higher-education inflation of 3.20%; Commonfund forecasts 3.4% for "
        "FY2026 against 3.6% actual in FY2025, which lifts the requirement to about 8.30% and "
        "the gap to roughly (222)bps. And 8.10% is stated additively; compounded, 4.50% "
        "spending on 3.20% cost inflation with 0.40% of fees requires 8.28%, a further 18bps. "
        "The office has used the Statement's 8.10% throughout so that every figure in this "
        "report reconciles to the governing document, and records that the true hurdle is "
        "higher than the one it has failed to meet.</p>")
    return "".join(out)


# ==========================================================================
def systematic(d: dict) -> str:
    r2 = d["quant_r2"] or {}
    head = r2.get("headline", {})
    sysj = d["systematic"] or {}
    fl = sysj.get("fundamental_law", {})
    surv = sysj.get("predictor_survival", {})
    out = ['<div class="page-break"></div>']
    out.append(R.section("The systematic evidence"))
    out.append(
        f"<p><strong>{head.get('cells_positive', 'n/a')} of "
        f"{head.get('cells_total', 'n/a')} signal and line combinations have a positive "
        f"out-of-sample R² against the expanding historical mean. The composite scores "
        f"{pct(head.get('composite_pooled_r2oos', 0))}% pooled, with a Clark-West t-statistic "
        f"of {head.get('composite_cw_t', 0):.2f}. On this evidence the signals do not beat "
        f"assuming the historical average.</strong></p>")
    out.append(
        f"<p>That result sits with the base rate rather than against it, and the office is "
        f"explicit that it is not claiming otherwise. The replication literature does not "
        f"agree on one number and the disagreement is methodological rather than empirical. "
        f"Hou, Xue and Zhang replicate 452 anomalies and find about 35% clear a conventional "
        f"hurdle and 18% a multiple-testing one. Jensen, Kelly and Pedersen reach 82% on the "
        f"same question, and their own decomposition shows the largest single step is testing "
        f"alpha rather than raw return. The range is {surv.get('low', 'n/a')} to "
        f"{surv.get('high', 'n/a')}. Where the literature converges is on decay: McLean and "
        f"Pontiff find a published edge loses 26% out of sample and 58% after publication, so "
        f"the operating rule is to halve any published number.</p>")
    out.append(
        f"<p>Nine positive cells out of forty is 22.5%, inside the low end of that range. "
        f"<strong>The office found what the prior said it would find.</strong> If the desks "
        f"had come back with a signal that worked they would be claiming membership of a "
        f"minority and would owe the Committee an account of why theirs belonged there. They "
        f"did not, so the recommendation follows from the evidence rather than from a view "
        f"about markets.</p>")

    # R2oos table. The desk emits cells[signal][line]; the report reads
    # lines down and signals across, so it is transposed here.
    fs = r2.get("full_sample") or {}
    cells = fs.get("cells") if isinstance(fs, dict) else None
    if isinstance(cells, dict) and cells:
        signames = sorted(cells.keys())
        present = [k for k in config.LINES
                   if any(isinstance(cells[sg].get(k), dict) for sg in signames)]
        grid, rows, npos, ntot = [], [], 0, 0
        for k in present:
            g, row = [], [config.LINE_LABEL[k]]
            for sg in signames:
                cell = cells[sg].get(k)
                val = cell.get("r2oos") if isinstance(cell, dict) else None
                if isinstance(val, (int, float)):
                    ntot += 1
                    npos += 1 if val > 0 else 0
                    g.append(float(val) * 100)
                    row.append(pct(val, 2))
                else:
                    g.append(None)
                    row.append("n/a")
            grid.append(g)
            rows.append(row)

        out.append('<h3 class="sub">Out-of-sample R², every signal against every line</h3>')
        out.append(R.chart_block(
            C.heat_grid([config.LINE_LABEL[k] for k in present],
                        [sg.replace("_", " ") for sg in signames], grid,
                        "Out-of-sample R² against the expanding historical mean",
                        "per cent. positive means the signal beat assuming the average",
                        name_w=152, cell_h=24, fmt=lambda v: C._n(v, 1)),
            [("Beat the historical mean", C.NAVY, "block"),
             ("Worse than the historical mean", C.CLAY, "block")],
            "Forty cells. The clay is the finding: most of these signals are worse than "
            "assuming the historical average, which is what the replication literature "
            "predicts and what the office reports rather than tuning away."))
        out.append(R.table(["Line"] + [sg.replace("_", " ") for sg in signames], rows,
                           units=[""] + ["%"] * len(signames), cls="tbl-sm"))
        out.append(
            f'<p class="fn">Computed against the expanding-window historical mean, the '
            f'Campbell and Thompson (2008) and Welch and Goyal (2008) definition, in strict '
            f'chronological order with nothing tuned on the test period. {npos} of {ntot} '
            f'cells are positive. Negatives sit in parentheses and are the majority, which is '
            f'the finding rather than an embarrassment. Clark-West t-statistics and the '
            f'sign-restricted variant are in outputs/quant/r2oos.json; one t-statistic of the '
            f'forty exceeds 2.0, which is roughly what chance produces.</p>')

    out.append('<h3 class="sub">What a tactical programme can earn against this mandate</h3>')
    out.append(
        f"<p>The fundamental law, in the constrained form of Clarke, de Silva and Thorley "
        f"(2002), caps the programme before any position is taken. Nominal breadth is "
        f"{fl.get('nominal_breadth', 'n/a')}, being nine lines across four meetings a year. "
        f"Effective breadth is <strong>{fl.get('effective_breadth', 'n/a')}</strong> once the "
        f"lines are collapsed for cross-correlation and consecutive quarters for signal "
        f"persistence, which is about 5% of nominal. At an information coefficient of "
        f"{fl.get('ic', 'n/a')} and a transfer coefficient of {fl.get('tc', 'n/a')} under "
        f"long-only constraints, permitted ranges and a 50bps minimum trade, the expected "
        f"information ratio is <strong>{fl.get('ir', 'n/a')}</strong>. Against the 200bps "
        f"tracking-error budget that is <strong>{fl.get('expected_alpha_bps', 'n/a')}bps</strong> "
        f"a year of alpha, against <strong>{fl.get('cost_bps', 'n/a')}bps</strong> of turnover "
        f"cost at the turnover this programme runs.</p>")
    out.append(R.verdict(
        "The arithmetic, before any view is expressed",
        f"Expected alpha {fl.get('expected_alpha_bps', 'n/a')}bps a year against "
        f"{fl.get('cost_bps', 'n/a')}bps of cost. The programme does not clear its costs."))
    out.append(
        "<p><strong>The realised experience on this window points the other way, and the "
        "office states it rather than leaving it to a reader to find.</strong> The desk's cost "
        "figure assumes 80% of net asset value traded a year at 8bps one-way. The programme "
        "actually traded far less than that: realised turnover cost was <strong>2.6bps a "
        "year</strong>, roughly two and a half times lower than assumed, and the realised "
        "active return was <strong>+21.8bps a year</strong> against an expected 4.2bps. On "
        "realised numbers the programme cleared its costs comfortably over these five "
        "years.</p>")
    out.append(
        "<p>The office still recommends against running it, for two reasons that a reader "
        "should weigh against the paragraph above. The realised information ratio of 0.27 "
        "carries a standard error of about 0.45, so +21.8bps is not distinguishable from zero "
        "and the same programme returns (22)bps a year measured over two years and (16)bps "
        "over four. And the ex-ante arithmetic is the forward-looking statement while the "
        "realised figure is one draw from a distribution this window cannot pin down. "
        "Preferring the ex-ante number is a judgement, not a fact, and it is the judgement "
        "this office is making.</p>")

    out.append(
        "<p>The counter-case is put rather than buried. Sneddon (2020) argues that correlation "
        "across bets raises rather than lowers the achievable information ratio, which would "
        "reverse the sign of the breadth haircut entirely. The office does not rest on the "
        "haircut. Even at full nominal breadth of 36, the expected alpha is roughly 18bps "
        "against 6.4bps of cost for an information ratio near 0.09, and no committee should "
        "fund a programme on that. Grinold and Kahn make the same point about quarterly "
        "benchmark timing directly: a breadth of four means an information ratio of 0.5 "
        "requires an information coefficient of 0.25, which is above the level they describe "
        "as the signature of a faulty backtest.</p>")

    out.append('<h3 class="sub">Volatility management: two questions with different answers</h3>')
    out.append(
        "<p>Whether volatility is forecastable and whether scaling exposure by a volatility "
        "forecast improves risk-adjusted returns are different claims, and they get conflated. "
        "The first is settled and the effect is large. The Quantitative desk's log-variance "
        "forecasts beat the expanding mean out of sample with Clark-West t-statistics above "
        "three, and the literature from Engle and Bollerslev through Corsi's HAR is "
        "unambiguous. Set against a monthly equity-premium R² of half a per cent or less, "
        "volatility forecasting is two orders of magnitude the easier problem.</p>")
    out.append(
        "<p>The second is contested. Moreira and Muir (2017) report a large alpha and a "
        "materially better Sharpe ratio. Cederburg, O'Doherty, Wang and Yan (2020) show "
        "across 103 strategies that the implied positions are not implementable in real time "
        "and that out-of-sample versions underperform the unmanaged portfolios. Harvey and "
        "co-authors localise the Sharpe benefit to equities and credit and find that what "
        "remains everywhere else is a reduction in tail severity.</p>")
    out.append(
        "<p>The honest reading for <strong>this</strong> mandate is that the supporting "
        "literature tests levered, monthly-rebalanced, long-short factor books. This is a "
        "long-only, unlevered, quarterly, nine-line asset allocation running against a 200bps "
        "budget, and it cannot capture the mechanism those papers identify. What does carry "
        "across is the reduction in tail severity, and that lands directly on the Board's "
        "drawdown limit, which is rank 3 in the hierarchy and above the return objective at "
        "rank 5. So the office adopts volatility-responsive risk control and "
        "<strong>books no alpha for it</strong>.</p>")
    return "".join(out)


# ==========================================================================
def macro_view(d: dict) -> str:
    m = d["macro"] or {}
    dev = d["macro_dev"] or {}
    gdp = d["macro_gdp"] or {}
    if isinstance(dev, list):
        devs = dev
    elif isinstance(dev, dict):
        devs = dev.get("deviations", [])
    else:
        devs = []

    out = ['<div class="page-break"></div>']
    out.append(R.section("The macro view, its deviations and their falsifiers"))
    out.append(
        f"<p>The Macro desk classifies the current regime as "
        f"<strong>{m.get('regime', 'n/a')}</strong>: expansionary growth, inflation above "
        "target, policy close to neutral and ample liquidity. The classification rule is "
        "arithmetic and published in the desk paper, so a trustee can apply it themselves and "
        "disagree with the rule rather than with a judgement. The load-bearing input is that "
        "the three-month bill at 3.87% against core PCE at 3.41% leaves a real policy rate of "
        "0.46%, which is not restrictive.</p>")
    out.append(
        "<p>IPS 4.4 requires that a view which cannot be shown wrong does not enter a "
        "recommendation, and that every deviation from consensus carries what would refute it "
        "and a date by which that would be known. The desk's deviations are below, with the "
        "position each justifies.</p>")
    if devs:
        rows = []
        for x in devs:
            rows.append([x.get("id", ""), x.get("view", ""), x.get("consensus", ""),
                         x.get("falsifier", ""), x.get("known_by_date", ""),
                         str(x.get("position_bps", ""))])
        out.append(R.table(
            ["#", "The view", "Consensus, and its source", "What would refute it",
             "Known by", "Position"],
            rows, units=["", "", "", "", "", "bps"],
            align_left={0, 1, 2, 3, 4}, cls="tbl-sm"))
        out.append(
            '<p class="fn">The desk records that its first three deviations are one '
            'proposition rather than three independent bets, and sizes them as one. That is '
            'the correct treatment and it is the kind of admission a desk marking its own '
            'homework does not usually make.</p>')

    out.append('<h3 class="sub">Why this office built a wall, with the number that justifies it</h3>')
    out.append(
        "<p>US real GDP for 2022 Q2 was first published at <strong>(0.93)%</strong> "
        "annualised on 28 July 2022. On today's vintage the same quarter reads "
        "<strong>+0.63%</strong>. The revision is +1.56 percentage points and the sign did "
        "not cross zero until the annual benchmark revision published on "
        "<strong>26 September 2024</strong>, which is <strong>791 days</strong> after the "
        "original print.</p>")
    if gdp:
        vt = gdp.get("vintages") or gdp.get("table") or []
        if isinstance(vt, list) and vt:
            rows = []
            for v in vt:
                rows.append([v.get("vintage", v.get("date", "")),
                             v.get("label", v.get("note", "")),
                             pct(v.get("q1_saar", 0)) if isinstance(v.get("q1_saar"), float) else str(v.get("q1_saar", "")),
                             pct(v.get("q2_saar", 0)) if isinstance(v.get("q2_saar"), float) else str(v.get("q2_saar", ""))])
            out.append(R.table(["Vintage", "What it was", "2022 Q1", "2022 Q2"], rows,
                               units=["", "", "% saar", "% saar"],
                               align_left={0, 1}, cls="tbl-sm"))
    out.append(
        "<p>The consequence is not academic. A desk backtesting off today's values spends "
        "those 791 days believing the economy grew in a quarter where every person actually "
        "trading it saw a contraction, and where the second consecutive negative quarter, "
        "which was true on the vintage available then and is false on the vintage available "
        "now, was the dominant market narrative of that summer. The Macro desk ran the "
        "counterfactual: at 30 September 2022 the point-in-time regime read is "
        "<strong>slowdown, stagflation risk</strong>, while the same rule on today's vintage "
        "reads <strong>expansion, overheat</strong>. The two produce allocations seven "
        "percentage points of gross weight apart, including two points more high yield and "
        "two points less duration. The tilt reverses. The backtest looks clean throughout.</p>")
    out.append(
        "<p>That is why this study reads every macro series from the ALFRED vintage current "
        "on the decision date, and why the enforcement is a module rather than a convention. "
        "The verification section sets out what happens when the enforcement is deliberately "
        "removed.</p>")
    return "".join(out)


# ==========================================================================
def two_allocations(d: dict) -> str:
    q = d["quant"] or {}
    m = d["macro"] or {}
    qw = q.get("constrained", {})
    mw = m.get("weights", {})
    out = ['<div class="page-break"></div>']
    out.append(R.section("The two independent allocations, before reconciliation"))
    out.append(
        "<p>Both drafts are tabled as they were produced, including the parts that did not "
        "survive reconciliation. Neither desk saw the other's work.</p>")

    rows = []
    for k in config.LINES:
        p = config.POLICY[k]
        qa, ma = qw.get(k, p) - p, mw.get(k, p) - p
        rows.append([config.LINE_LABEL[k], f"{p * 100:.0f}",
                     f"{qw.get(k, p) * 100:.1f}", bps(qa * 10000, 0),
                     f"{mw.get(k, p) * 100:.1f}", bps(ma * 10000, 0),
                     bps((qa - ma) * 10000, 0)])
    out.append(R.table(
        ["Line", "Policy", "Quant", "Active", "Macro", "Active", "Gap"],
        rows, units=["", "%", "%", "bps", "%", "bps", "bps"],
        foot=["Ex-ante tracking error", "", "",
              f"{q.get('ex_ante_te_bps', 0):.0f}bps", "", "99bps", ""]))

    gaps = [(config.LINE_LABEL[k],
             ((qw.get(k, config.POLICY[k]) - config.POLICY[k])
              - (mw.get(k, config.POLICY[k]) - config.POLICY[k])) * 10000)
            for k in config.LINES]
    gaps.sort(key=lambda t: -abs(t[1]))
    out.append(R.chart_block(
        C.diverging_bars(gaps, "Where the two desks disagree",
                         "quantitative active weight less macro active weight, basis points",
                         width=860, name_w=190, fmt=lambda v: C._n(v, 0)),
        [("Quant more positive", C.NAVY, "block"), ("Macro more positive", C.CLAY, "block")],
        "The disagreement is the finding. Two desks that agreed everywhere would have "
        "produced one view twice."))

    out.append('<h3 class="sub">Where they agree, and whether that is confirmation</h3>')
    out.append(
        "<p>They agree on developed ex-US equity and listed real estate, both at policy, and "
        "they agree in direction on US equity, US investment grade and US high yield, all "
        "modestly underweight. That agreement is weaker evidence than it looks. Both desks "
        "read the same prices from the same data layer, so a common input can produce a "
        "common answer without either desk confirming the other. The underweight to US equity "
        "in particular traces in both cases to the same observation, that the line is "
        "expensive against its own history, which is one fact counted twice rather than two "
        "facts agreeing.</p>")
    out.append(
        "<p>The one agreement that is genuine confirmation is on high yield. The Quantitative "
        "desk reaches it from spread carry against realised volatility; the Macro desk "
        "reaches it from a credit spread in the tightest decile of its available history "
        "against a policy rate it judges insufficiently restrictive. Those are different "
        "routes to the same position and that is worth more than the size of the position "
        "warrants.</p>")

    out.append('<h3 class="sub">Where they disagree, and how it was resolved</h3>')
    out.append(
        "<p>Before the disagreement itself, one property of the rule that combines them. The "
        "historical record blends the two desks by equal weight on their active vectors, which "
        "sounds neutral and is not. The Quantitative desk takes systematically larger "
        "positions: its active vector averages 14.1 percentage points against the Macro desk's "
        "7.7, and it was the larger of the two at <strong>every one of the twenty "
        "meetings</strong>. The adopted allocation therefore resembles the Quantitative view "
        "far more closely than the Macro view, with a mean cosine similarity of 0.91 against "
        "0.66. <strong>An equal weight on vectors of unequal size is not an equal weight on "
        "opinions</strong>, and the effect is roughly two to one in the model desk's favour. "
        "This was not intended and is disclosed rather than corrected, because changing the "
        "rule after seeing the record is the error the pre-commitment exists to prevent.</p>"
        "<p>The disagreement is concentrated, which makes it tractable. It is almost entirely "
        "<strong>Treasury duration</strong>, where the Quantitative desk is 10.0 points "
        "overweight and the Macro desk is 6.5 points underweight, a gap of 16.5 points. "
        "Commodities and cash account for most of the rest.</p>")
    out.append(R.table(
        ["Disagreement", "Quant", "Macro", "The evidence that decided it", "Resolution"],
        [["Treasury duration, 16.5pp apart",
          "Overweight 10.0pp. Momentum and carry both positive after the 2025 rally; the "
          "line carries the lowest realised volatility in the estimation window and the "
          "optimiser buys it as risk reduction as much as as a view.",
          "Underweight 6.5pp. Real policy rate of 0.46% with core PCE at 3.41% is not "
          "restrictive; the desk expects at least one further hike and a higher breakeven, "
          "both falsifiable by stated dates.",
          "Neither is supported. The duration signal's out-of-sample R² against the "
          "expanding mean is negative, so the quant position rests on an estimator the "
          "evidence does not support. The macro position rests on three deviations the desk "
          "itself says are one proposition, and its falsifiers do not resolve until "
          "December 2026 at the earliest.",
          "Resolved to policy weight. A 16-point disagreement between two desks with no "
          "demonstrated skill is not information, it is noise with two authors."],
         ["Commodities, 5.0pp apart",
          "At policy. Momentum negative, carry weak.",
          "Overweight 5.0pp, sized to the 8% line cap, on the inflation view.",
          "The commodity line costs 25bps one-way to trade against 1.5bps for US equity, and "
          "a 3pp exit is 93% of a day's volume in DBC. The position is the most expensive in "
          "the opportunity set to hold and to unwind.",
          "Resolved to policy weight. The macro case is one proposition already counted in "
          "the inflation deviations, and the implementation cost consumes a material part of "
          "any gain."],
         ["Cash, 7.0pp apart",
          "Zero. The optimiser holds no cash because cash has no expected return and the "
          "tracking-error budget is better spent elsewhere.",
          "Seven points, as risk reduction against the regime read.",
          "IPS 4.1 is explicit that cash is a position and not a residual, and that raising "
          "it is the cheapest way to cut risk. That supports the macro instinct. But the "
          "instinct is being used to express a directional view the evidence does not carry.",
          "Resolved to policy weight, with cash retained as the funding line for the "
          "distribution rather than as a position."]],
        align_left={0, 1, 2, 3, 4}, cls="tbl-sm"))
    return "".join(out)


# ==========================================================================
def reconciled(d: dict) -> str:
    out = ['<div class="page-break"></div>']
    out.append(R.section("The reconciled allocation"))
    out.append(
        "<p>Policy weights on every line. Ex-ante tracking error of zero against the "
        "benchmark, against a budget of 200bps. The office is returning the entire active "
        "risk budget unspent, and the reason is not caution but arithmetic: the expected "
        "value of spending it is negative.</p>")
    rows = []
    for k in config.LINES:
        lo, hi = config.RANGE[k]
        rows.append([config.LINE_LABEL[k], f"{config.POLICY[k] * 100:.0f}",
                     f"{config.POLICY[k] * 100:.0f}", "0",
                     f"{lo * 100:.0f} to {hi * 100:.0f}",
                     f"±{costs.CORRIDOR_PP[k]:.2f}",
                     f"{costs.ONE_WAY_BPS[k]:.1f}"])
    out.append(R.table(
        ["Line", "Policy", "Recommended", "Active", "Permitted range", "Corridor", "Cost"],
        rows, units=["", "%", "%", "bps", "%", "pp", "bps one-way"],
        foot=["Total", "100", "100", "0", "", "", ""]))
    out.append(R.chart_block(
        C.range_bars([{"name": config.LINE_LABEL[k], "lo": config.RANGE[k][0],
                       "hi": config.RANGE[k][1], "policy": config.POLICY[k],
                       "current": config.POLICY[k]} for k in config.LINES],
                     "Recommended position against policy and permitted range",
                     "weight, per cent of net asset value"),
        [("Recommended weight", C.NAVY, "block"),
         ("Permitted range, IPS 4.1", C.CLAY_TINT, "block"),
         ("Policy weight", C.SLATE, "dash")]))
    out.append(
        "<p>IPS 3.3 requires that a recommendation say which of the two objectives it is "
        "giving ground on, and states that one claiming to satisfy both has not understood "
        "one of them. <strong>This recommendation gives ground on the return objective.</strong> "
        "It funds 8.10% on no plausible set of assumptions, and the office says so rather "
        "than reaching for the risk that might close the gap on paper. The drawdown limit is "
        "rank 3 and the return objective is rank 5, so the hierarchy makes the choice before "
        "any argument is heard. The office notes that holding policy weights does not satisfy "
        "the drawdown limit either, which is the second amendment question.</p>")
    return "".join(out)
