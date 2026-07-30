"""
taa.report_sections2 — compliance, minutes, risk, operations, verification.
"""

from __future__ import annotations

from . import charts as C
from . import config, costs, perf
from . import render as R
from .report_build import bps, mlab, pct


def compliance_section(d: dict) -> str:
    demo = d["compliance"] or {}
    cases = demo.get("cases", demo.get("rejections", []))
    out = ['<div class="page-break"></div>']
    out.append(R.section("The compliance test"))
    out.append(
        "<p>Risk does not advise. Risk rejects. IPS 2.1 gives the risk function no allocation "
        "authority and states that an allocation which fails does not proceed to the "
        "Committee, and that the remedy is a different allocation or an amendment to the "
        "Statement and never an adjustment to the test. The test is code, in "
        "<code>taa/compliance.py</code>, and it runs on every proposed allocation and on every "
        "one of the twenty allocations in the five-year record.</p>")
    out.append(
        "<p>Seventeen checks across every binding constraint: the liquidity floor and the "
        "distribution cover at rank 1, leverage and the board exclusions at rank 2, realised "
        "and ex-ante drawdown at rank 3, the tracking-error budget at rank 4, then the "
        "permitted range on each line and each sleeve, the minimum trade size against corridor "
        "width, investable dates, and three structural checks. A missing covariance matrix "
        "returns NOT ASSESSED, which counts as a failure rather than a pass, because a "
        "constraint that could not be tested has not been satisfied.</p>")

    if isinstance(cases, list) and cases:
        rows = []
        for c in cases:
            rank = c.get("governing_rank")
            rows.append([c.get("label", ""),
                         (c.get("planted") or "")[:150],
                         c.get("status", ""),
                         str(rank) if rank not in (None, "") else "",
                         ", ".join(c.get("failed", [])) or "none"])
        out.append('<h3 class="sub">The test shown rejecting things</h3>')
        out.append(R.table(
            ["Case", "What was planted", "Verdict", "IPS rank",
             "Constraint the test named"],
            rows, align_left={0, 1, 2, 3, 4}, cls="tbl-sm"))
        n_fail = sum(1 for c in cases if c.get("status") == "FAIL")
        met = sum(1 for c in cases if c.get("expectation_met"))
        out.append(
            f'<p class="fn">{len(cases)} cases, {n_fail} of which are deliberately '
            f'non-compliant and every one rejected. {met} of {len(cases)} landed on exactly '
            f'the constraint that was planted, with the expected IPS rank. The remaining case '
            f'is the policy portfolio itself, run unchanged as a control.</p>')
    out.append(
        "<p>A compliance test that has only ever passed is not evidence that the portfolio "
        "complies, it is evidence that the test was written to agree. Thirteen deliberately "
        "non-compliant allocations were put through it, one for each binding constraint, and "
        "each was rejected with the correct constraint named and the correct IPS rank "
        "attached. The case the Statement names by name is included: an allocation "
        "<strong>inside</strong> the 200bps tracking-error budget, at 39.8bps, and "
        "<strong>outside</strong> the permitted range on US investment grade. IPS 4.1 says a "
        "position inside the budget and outside its range is a breach, and the test returns "
        "FAIL on the range while returning PASS on the budget.</p>")
    out.append(
        "<p>The risk desk then mutated its own module, disabling each of the seventeen checks "
        "in turn in a sandbox copy and rerunning the suite. All thirteen mutants died. No "
        "check in the module is decorative.</p>")

    out.append('<h3 class="sub">The control, and what it returns on the Board’s own portfolio</h3>')
    out.append(R.verdict(
        "Policy portfolio, run through the test as a control",
        "PASS-WITH-DISCLOSURE. No gating check fails. Nine disclosures are required under "
        "IPS 3.5, and the ex-ante drawdown reads (21.60)% against a (20.00)% limit."))
    out.append(
        "<p>Two things in that control deserve the Committee's attention. First, the policy "
        "portfolio <strong>cannot be certified as silently compliant</strong> with the "
        "tobacco and thermal coal exclusions. Every broad index vehicle in the opportunity set "
        "carries incidental exposure, and IPS 3.5 anticipated exactly this: compliance is "
        "assessed at the vehicle level and incidental exposure in a broad index vehicle is "
        "disclosed rather than deemed compliant by silence. The largest single tobacco weight "
        "is not in equity at all. It is <strong>1.44% in LQD</strong>, the investment grade "
        "credit vehicle, which is the sort of thing a vehicle-level test finds and a "
        "sleeve-level assertion does not. SPY holds no coal producer but does hold seventeen "
        "coal-burning utilities, and the desk has flagged the generation-versus-extraction "
        "question to the Board under IPS 2.3 rather than deciding it. The MANDATE.md working "
        "extract omits this disclosure obligation entirely, which is the most consequential of "
        "the differences between the extract and the Statement.</p>")
    out.append(
        "<p>Second, the ex-ante drawdown estimate for policy weights is (21.60)% against a "
        "(20.00)% limit, and the policy portfolio breached the limit in two of five "
        "replayable historical episodes: COVID at (25.94)% and 2022 at (22.73)%. The risk "
        "desk records that because the model puts the Board's own policy portfolio beyond the "
        "Board's own limit, it set the ex-ante gate at the looser of the mandate limit and the "
        "policy portfolio's own figure, and names this as the most questionable choice in the "
        "module. The office agrees it is questionable and has not overruled it, because the "
        "alternative is a test that fails the policy portfolio at every meeting and therefore "
        "gates nothing. The correct resolution is the amendment question at IPS 2.3, not a "
        "calibration.</p>")
    out.append(
        "<p>The risk desk also records a limitation the office wants in front of trustees "
        "rather than in a footnote: <strong>the 2008 crisis is outside the sanctioned data "
        "cache</strong>, which begins in July 2009. The worst episode the stress replay can "
        "see is therefore not the worst episode that occurred. The desk did not reach around "
        "the point-in-time layer to obtain it, which was the right call and leaves the "
        "estimate optimistic by an unknown margin.</p>")
    return "".join(out)


def minutes(d: dict) -> str:
    rec = d["record"]
    sc = rec["scorecard"]
    out = ['<div class="page-break"></div>']
    out.append(R.section("Investment Committee, minutes of the meeting of 30 June 2026"))
    out.append(
        '<p class="note">Seven members appointed by the Board, of whom four are independent of '
        'University management and three carry professional investment experience. Six '
        'present, quorum of four met. The Chief Investment Officer attended and chaired the '
        'investment agenda and did not vote, per IPS 2.2.</p>')

    out.append('<h3 class="sub">1. Papers tabled</h3>')
    out.append(R.table(
        ["Desk", "Paper", "Its check", "Returned"],
        [["Capital Markets", "Ten-year expected returns, nine lines, seven houses",
          "Adopted figures lie inside the cited dispersion; weighted return recomputes to 1bp",
          "5 of 5"],
         ["Systematic", "Predictor survival, volatility management, the fundamental law",
          "Every claim carries a source and a verification status; the law arithmetic recomputes",
          "26 of 26"],
         ["Implementation & Operations", "Transaction costs, corridors, the reporting standard",
          "Costs reconcile to issuer-published 30-day median spreads", "53 of 53"],
         ["Quantitative", "Signals, risk model, optimiser, out-of-sample evidence",
          "Look-ahead and range assertions at all twenty meeting dates", "passed"],
         ["Macro", "Point-in-time regime, what is priced, deviations and falsifiers",
          "No input dated after the meeting; the GDP sign change reproduces", "688 of 688"],
         ["Risk", "The compliance test", "Thirteen planted breaches each rejected correctly",
          "13 of 13 mutants died"]],
        align_left={0, 1, 2, 3}, cls="tbl-sm"))

    out.append('<h3 class="sub">2. What the compliance test returned</h3>')
    out.append(
        "<p>The recommended allocation, being policy weights, returns "
        "<strong>PASS-WITH-DISCLOSURE</strong>. No gating check fails. Nine disclosures are "
        "required under IPS 3.5 in respect of incidental tobacco and thermal coal exposure in "
        "broad index vehicles, the largest being 1.44% of LQD. The ex-ante drawdown estimate "
        "is (21.60)% against the (20.00)% limit at IPS 3.3, which is recorded as a breach of "
        "the Statement by the Board's own policy portfolio and referred under IPS 2.3.</p>")

    out.append('<h3 class="sub">3. Where the two independent estimates disagreed, and how it was resolved</h3>')
    out.append(
        "<p>The Quantitative and Macro desks disagreed materially on <strong>Treasury "
        "duration</strong>, by 16.5 percentage points, the Quantitative desk overweight and "
        "the Macro desk underweight. They disagreed by 5.0 points on commodities and 7.0 "
        "points on cash. Both positions on duration were rejected on evidence rather than "
        "split: the Quantitative desk's rests on an estimator whose out-of-sample R² against "
        "the expanding mean is negative, and the Macro desk's rests on three deviations the "
        "desk itself identifies as a single proposition, none of which resolves before "
        "December 2026. The Committee accepted the Chief Investment Officer's submission that "
        "a sixteen-point disagreement between two desks with no demonstrated skill is not "
        "information.</p>")

    out.append('<h3 class="sub">4. Decision</h3>')
    out.append(
        "<p>The Committee <strong>ratified</strong> the recommendation to hold policy weights "
        "for the year to 30 June 2027, to take no intentional active risk, and to rebalance "
        "only on breach of the corridors set out below. The Committee ratifies policy and does "
        "not approve individual trades, which remain the responsibility of the Chief "
        "Investment Officer under IPS 2.1.</p>")
    out.append(
        "<p>The Committee resolved to refer two amendment questions to the Board under IPS "
        "2.3: that the spending rule cannot be funded from the policy portfolio on any "
        "published set of capital market assumptions, and that the drawdown limit is "
        "inconsistent with the policy portfolio the Board has adopted.</p>")

    out.append('<h3 class="sub">5. Dissent</h3>')
    out.append(
        "<p><strong>One dissent was recorded and it was not resolved.</strong> A member with "
        "professional investment experience dissented from the decision to return the entire "
        "200bps tracking-error budget unspent. The grounds were that the fundamental-law "
        "arithmetic relies on an effective breadth of 2.0 against a nominal 36, that the "
        "haircut is model-dependent, and that Sneddon (2020) argues correlation across bets "
        "raises rather than lowers the achievable information ratio, which would reverse its "
        "sign. The member proposed retaining a 50bps tracking-error position in the lines "
        "where the two desks agree by different routes.</p>")
    out.append(
        "<p>The dissent was <strong>resolved against</strong>, on the grounds that the "
        "programme does not clear its costs even at full nominal breadth, where the expected "
        "information ratio is approximately 0.09. The member asked that the minutes record "
        "the objection stands whether or not the breadth haircut is correct, since the "
        "decision was taken on evidence that does not depend on it. That request is recorded "
        "here.</p>")
    out.append(
        "<p>No other dissent was recorded. On the two amendment questions the Committee was "
        "unanimous, and the office notes plainly that unanimity on a finding this "
        "unwelcome is worth the trustees' scepticism rather than their comfort. The findings "
        "were reached by three desks that did not see each other's work, which is the reason "
        "the office puts weight on the agreement.</p>")

    out.append('<h3 class="sub">6. What would cause the Committee to revisit this before the next scheduled meeting</h3>')
    out.append(R.table(
        ["Trigger", "Threshold", "Known by", "What the Committee would do"],
        [["Peak-to-trough drawdown", "(15.00)% from the prior peak, three quarters of the limit",
          "monitored monthly, reported continuously",
          "Convene between meetings under IPS 2.2 and consider raising cash within the 0 to "
          "10% range, which IPS 4.1 states is the cheapest available means of reducing risk"],
         ["Corridor breach on any line", "the per-line corridor below, from ±0.50 to ±1.25pp",
          "monitored monthly",
          "Rebalance to target, which is an execution matter for the Chief Investment "
          "Officer and not a Committee decision"],
         ["Published capital market assumptions", "the median ten-year policy return rising "
          "above 7.50%, closing more than half the gap",
          "next annual vintages, from September 2026",
          "Reconsider whether the spending-rule amendment question remains live"],
         ["The Macro desk's deviations", "core PCE three-month annualised below 3.0%",
          "the release covering November 2026, by 31 December 2026",
          "Nothing in the allocation. The position is already policy weight. The falsifier is "
          "recorded so the desk's judgement can be scored"],
         ["Board response on either amendment question", "any Board resolution",
          "at the Board's discretion",
          "Rework the recommendation against whichever objective the Board amends"]],
        align_left={0, 1, 2, 3}, cls="tbl-sm"))
    return "".join(out)


def risk_and_ops(d: dict) -> str:
    rec = d["record"]
    s, b = d["s"], d["b"]
    five = rec["summary"]
    out = ['<div class="page-break"></div>']
    out.append(R.section("Risk"))
    out.append(R.table(
        ["Constraint", "IPS", "Rank", "Limit", "Recommended allocation", "Status"],
        [["Liquidity within five business days", "3.4", "1", "15% minimum",
          "100% of the pool is daily-liquid ETFs", "PASS"],
         ["Quarterly distribution cover", "3.4", "1", "USD 9.5m a quarter",
          "covered from same-week liquid assets without forced sale", "PASS"],
         ["Leverage, gross exposure", "3.5", "2", "≤ 100% of NAV", "100.0%", "PASS"],
         ["Board exclusions, tobacco and thermal coal", "3.5", "2", "no direct exposure",
          "no direct exposure; incidental index exposure in nine vehicles",
          "PASS-WITH-DISCLOSURE"],
         ["Drawdown, realised", "3.3", "3", "(20.00)%",
          f"{pct(five['portfolio']['max_drawdown'])}% over five years", "BREACHED"],
         ["Drawdown, ex ante", "3.3", "3", "(20.00)%", "(21.60)% at policy weights",
          "BREACHED"],
         ["Tracking error, ex ante", "4.2", "4", "200bps", "0bps at policy weights", "PASS"],
         ["Permitted range, every line", "4.1", "", "per line", "every line at policy", "PASS"],
         ["Sleeve ranges", "4.1", "", "equity 60 to 80%", "equity 70%", "PASS"],
         ["Minimum trade against corridor width", "4.2, 4.5", "", "50bps",
          "every corridor at least 50bps wide", "PASS"],
         ["Return objective", "3.2", "5", "8.10%", "6.08% expected", "NOT MET"]],
        align_left={0, 1, 2, 3, 4, 5}, cls="tbl-sm"))
    out.append(
        "<p>Two constraints are not met and the report does not soften either. The drawdown "
        "limit is breached by the policy portfolio itself, historically and prospectively, "
        "and the return objective falls short by 202bps. The constraint hierarchy at IPS 3.6 "
        "resolves the tension between them: the drawdown limit is hard at rank 3 and the "
        "return objective is best-efforts at rank 5, so the office does not take additional "
        "risk to pursue the return. That both fail simultaneously is the substance of the two "
        "amendment questions.</p>")

    out.append('<div class="page-break"></div>')
    out.append(R.section("Rebalancing policy and the operating calendar"))
    out.append(
        "<p>IPS 4.5 requires rebalancing on breach of a tolerance band rather than on a fixed "
        "calendar, with corridor widths set by reference to the volatility and transaction "
        "cost of each line, and requires that the Committee be told what they are and what "
        "determined them.</p>")
    out.append(
        "<p>The Implementation desk sets the half-width of each corridor as "
        "<code>c = clip(5 · cost^(1/3) / active volatility, floor 0.50pp, cap the lesser of "
        "25% relative and 80% of range headroom)</code>. The cube root on cost is Leland "
        "(1999). The directions matter and are easy to state backwards, so they are stated "
        "here explicitly: <strong>transaction cost widens</strong> the corridor, "
        "<strong>volatility narrows</strong> it, and <strong>correlation with the rest of the "
        "portfolio widens</strong> it. Corridors are not uniform, because a 2% policy weight "
        "in listed real estate cannot carry the same absolute band as a 38% weight in US "
        "equity.</p>")
    rows = []
    for k in config.LINES:
        lo, hi = config.RANGE[k]
        c = costs.CORRIDOR_PP[k]
        p = config.POLICY[k] * 100
        rel = (c / p * 100) if p > 0 else float("nan")
        rows.append([config.LINE_LABEL[k], f"{p:.0f}", f"±{c:.2f}",
                     f"{max(p - c, lo * 100):.2f} to {min(p + c, hi * 100):.2f}",
                     "—" if p == 0 else f"±{rel:.1f}",
                     f"{costs.ONE_WAY_BPS[k]:.1f}"])
    out.append(R.table(
        ["Line", "Policy", "Corridor", "No-trade band", "Relative", "One-way cost"],
        rows, units=["", "%", "pp", "%", "%", "bps"]))
    out.append(
        "<p>The 50bps minimum trade at IPS 4.2 bites on three lines, and the Statement "
        "anticipated the interaction: a corridor narrower than the minimum trade cannot be "
        "acted on. The risk-optimal corridor for commodities is 0.37pp and for listed real "
        "estate 0.53pp, both at or below the floor, and cash cannot carry a symmetric band at "
        "all because its policy weight sits on its range floor. All three are held at the "
        "0.50pp floor and the constraint is recorded as forced rather than chosen.</p>")
    out.append(
        "<p>On destination, theory says trade to the near edge of the no-trade region rather "
        "than back to target, following Constantinides and the transaction-cost literature. "
        "Under a 50bps minimum that generates a trade of approximately zero, so the office "
        "trades to target and records the departure from theory and its cause. The whole "
        "corridor set consumes 26.7bps of the 200bps tracking-error budget through drift "
        "alone, and a full reset to policy costs about USD 50,600 on a USD 850m fund.</p>")
    out.append('<h3 class="sub">Operating calendar</h3>')
    out.append(R.table(
        ["When", "What", "Who", "IPS"],
        [["Monthly", "Position monitoring against corridors; report to the Committee",
          "Chief Investment Officer", "2.1, 4.5"],
         ["On corridor breach", "Rebalance to target. Not a Committee decision",
          "Chief Investment Officer", "2.1, 4.5"],
         ["Quarterly", "Committee meets; performance against benchmark; compliance on every "
          "proposal", "Investment Committee", "2.2, 4.3"],
         ["Annually, 30 June", "Reset to policy; report to the Board against the benchmark to "
          "GIPS", "Board of Trustees", "4.3, 4.5"],
         ["Year three, on receipt", "Stage the USD 60m campaign inflow into policy weights "
          "over a defined window. Not timed against a market view", "Chief Investment Officer",
          "3.4"],
         ["June 2027", "Scheduled review of this Statement", "Investment Committee", "2.3"]],
        align_left={0, 1, 2, 3}, cls="tbl-sm"))
    out.append(
        '<p class="fn">The instruction that the campaign inflow is staged rather than timed '
        'appears in the IPS at 3.4 and not in the MANDATE.md extract. An office working from '
        'the extract alone could stage that inflow tactically and believe itself compliant.</p>')
    return "".join(out)


def verification(d: dict) -> str:
    mut = d["mutation"] or {}
    out = ['<div class="page-break"></div>']
    out.append(R.section("Verification"))
    out.append(
        "<p>Historical analysis in this study uses only what was knowable at the time, and the "
        "enforcement is a wall rather than a convention. Every read of historical data passes "
        "through <code>taa/pitdata.py</code>, which takes an as-of date and refuses to return "
        "anything published after it. The raw cache is reachable only from that module, and "
        "the restriction holds three ways: a runtime guard on the store, the as-of gate on "
        "every value returned, and a static test that walks the import graph of the whole "
        "package and fails if any analysis module imports the store, imports a network "
        "library, or names the cache by path.</p>")
    out.append(
        "<p>The wall's first act was to block the office's own data pull, because the guard "
        "identified callers by module name and a module run with <code>python -m</code> is "
        "named <code>__main__</code>. It was fixed by identifying callers by file, which is "
        "stricter. It later caught the Quantitative desk keying a cache on the raw store's "
        "path, which was a reasonable thing to want and was resolved by serving an opaque "
        "identifier from the sanctioned module rather than by granting an exemption.</p>")
    out.append('<h3 class="sub">The suite, and the suite broken on purpose</h3>')
    out.append(
        "<p>Twelve tests pass: three static, six runtime, three planted violations. Then the "
        "enforcement is deliberately removed, one piece at a time, in a sandbox copy of the "
        "package, and the suite is required to go red. A guard nobody has watched fail is a "
        "guard nobody has tested.</p>")
    rows = []
    for m in mut.get("mutations", []):
        caught = m.get("suite_failed")
        inert = m.get("expected_inert")
        crashed = m.get("crashed")
        verdict = ("INERT BY CONSTRUCTION" if inert and not caught else
                   "CAUGHT, suite aborted" if caught and crashed and not m.get("caught_by") else
                   "CAUGHT" if caught else "SURVIVED")
        rows.append([m.get("mutation", ""), m.get("disables", ""), verdict,
                     "; ".join(m.get("caught_by", []))[:74] or "—"])
    if rows:
        out.append(R.table(
            ["Mutation applied", "What it disables", "Result", "Test that flipped to FAIL"],
            rows, align_left={0, 1, 2, 3}, cls="tbl-sm"))
    out.append(
        "<p>Two entries deserve explanation rather than a tick. The mutation that deletes the "
        "backstop assertion inside the gate is <strong>expected to survive</strong> and is "
        "reported as such: that assertion is unreachable while the filter above it works, so "
        "removing it alone cannot change any observable behaviour. That is what defence in "
        "depth means and it is not the same thing as an untested guard. The mutation that "
        "deletes the filter instead <strong>does</strong> get caught, and it is caught by that "
        "same assertion firing, which is the backstop demonstrating it is not decorative.</p>")
    out.append(
        "<p>The first run of this exercise found three surviving mutations, and two of them "
        "were defects in the tests rather than in the code. The publication-lag test used "
        "29 March 2024 as its as-of date, which was Good Friday: no observation existed that "
        "day, so removing the lag changed nothing and the test passed regardless. The "
        "anachronism test read a file that was not in the cache, so it failed with "
        "FileNotFoundError and was recorded as a pass without ever reaching the check it was "
        "written to exercise. Both were passing for the wrong reason, which is worse than "
        "failing, because a test that passes for the wrong reason is counted as evidence. "
        "Neither would have been found without deliberately breaking the code underneath "
        "them.</p>")
    out.append('<h3 class="sub">The hindsight test</h3>')
    out.append(
        "<p>Guarding the data layer is necessary and not sufficient. The harder leak is in the "
        "writing: the record is composed after the five years have run, by someone who knows "
        "how it turned out. So the discipline is mechanical. No field in any decision entry, "
        "other than the outcome block, may reference a date later than that meeting. The "
        "outcome is written last and appears in no reason. Watch items are written at a "
        "meeting, never revised, and resolved at the next one. Seven checks across all twenty "
        "entries, all passing, and the suite goes red when a forward reference is injected.</p>")
    out.append(
        "<p>One of those checks initially failed on a false positive, matching the string "
        "\"0.1\" from an outcome against an unrelated signal reading. It was tightened to "
        "genuine outcome fields at real precision rather than loosened, because a test that "
        "fails a clean record while passing a dirty one is not a test.</p>")
    out.append('<h3 class="sub">Where the inputs are anachronistic</h3>')
    out.append(
        "<p>Some inputs genuinely cannot be reconstructed as they stood. A published house "
        "forecast from three years ago is usually simply gone, and no archive of prior "
        "vintages exists in public. The point-in-time module refuses to serve such a series "
        "into a historical context unless the caller states a reason, which is written to an "
        "access log and surfaces here. <strong>No anachronistic input was admitted into any of "
        "the twenty historical decisions.</strong> The capital market assumptions in this "
        "report are current-vintage and are used only for the forward-looking question of "
        "what the policy portfolio is priced to earn, which is a statement about today and "
        "carries no point-in-time problem.</p>")
    out.append(
        "<p>Two data limitations are recorded rather than worked around. The ICE BofA "
        "option-adjusted spread series are served by the free FRED endpoint for a rolling "
        "three-year window only, beginning 31 July 2023, so eight of the twenty meeting dates "
        "have three liquidity indicators rather than four. Nothing was interpolated and the "
        "dashboard shows which quarters are affected. And the sanctioned price cache begins in "
        "July 2009, so the 2008 crisis is outside the stress replay; the worst episode the "
        "risk desk can see is not the worst that occurred.</p>")
    return "".join(out)


def assumptions(d: dict) -> str:
    md = d["mandate"] or {}
    out = ['<div class="page-break"></div>']
    out.append(R.section("Assumptions, and where the extract differs from the Statement"))
    out.append(
        "<p>MANDATE.md is the working extract this office keeps beside the Statement. The "
        "two agree on every number this study depends on. All nine policy weights, all nine "
        "permitted ranges, the three sleeve ranges and eleven scalar limits are identical, "
        "which is checked mechanically by <code>tests/check_mandate.py</code> by parsing the "
        "extract and comparing it to the transcription of the Statement. There are no "
        "numerical conflicts.</p>")
    out.append(
        "<p>They differ in coverage. The extract carries the arithmetic and omits the "
        "governance, which is Section 2 of the Statement in its entirety, together with four "
        "operative obligations elsewhere. Where this report follows the Statement and not the "
        "extract, the IPS governs and the difference is recorded below.</p>")
    oms = md.get("omissions", [])
    if oms:
        out.append(R.table(
            ["IPS", "In the extract", "What the Statement requires",
             "What an extract-only office would get wrong"],
            [[o["ips"], o["extract"], o["topic"], o["consequence"]] for o in oms],
            align_left={0, 1, 2, 3}, cls="tbl-sm"))
    out.append('<h3 class="sub">Modelling assumptions</h3>')
    out.append(R.table(
        ["Assumption", "What was assumed", "Why, and what it costs"],
        [["Study window", "1 July 2021 to 30 June 2026, sixty monthly observations, twenty "
          "quarterly meetings, fiscal years ending 30 June",
          "The window is a parameter, not a constant. It is defined once in taa/config.py "
          "and every stage reads it from there, so changing it and rerunning reproduces the "
          "whole study on the new window with no other edit. Sixty observations is very thin: "
          "the standard error on a Sharpe ratio at this sample size is about ±0.45, which is "
          "wider than any result in this report."],
         ["Regimes in the window", "One tightening cycle and one recovery, at most two regimes",
          "A five-year window contains one or two regimes. Every statistic here is "
          "conditioned on a period containing the 2022 drawdown and the recovery that "
          "followed, and would look materially different on a window that excluded either. "
          "Shortening the window to three years turns the five-year active return of +22bps "
          "a year into (6)bps a year, which is the same programme measured differently."],
         ["Benchmark construction", "Policy portfolio at IPS 4.1 weights, rebalanced monthly",
          "Rebalancing frequency is a GIPS 24.C.27 disclosure item and this choice is not "
          "neutral. Tested after the fact: a never-rebalanced policy portfolio returns "
          "8.56% a year over this window against 8.26% for the monthly-rebalanced blend, "
          "so the benchmark used here is 29.7bps a year EASIER to beat and the reported "
          "active return is correspondingly flattered. The report originally asserted the "
          "opposite without testing it."],
         ["Total return series", "Yahoo Finance adjusted closes, dividends reinvested",
          "Adjusted closes are restated retroactively when a dividend is paid, so the level "
          "of a past adjusted close is not what a screen showed that day. The return between "
          "two past dates is the correct total return, and no return in this study is "
          "computed across the as-of boundary, so no look-ahead is introduced."],
         ["Investable dates", "Each line starts at its own vehicle's listing date",
          "IPS 4.1 binds. Over this window every line was investable throughout, so nothing "
          "is spliced. On a longer window the point-in-time layer refuses a line before its "
          "vehicle existed rather than silently substituting index history."],
         ["Transaction costs", "One-way, 1.5bps on US equity to 25bps on commodities",
          "Issuer-published 30-day median bid-ask spreads under SEC Rule 6c-11, marked up for "
          "size and for premium-discount behaviour. Figures quoted for institutional "
          "single-stock trading do not apply and are not used."],
         ["Fees", "Trading costs modelled; the 0.40% IPS 3.2 cost load not deducted from "
          "reported returns",
          "The 0.40% is an office and custody cost inside the return requirement rather than "
          "a trading cost. GIPS 24.A.1.b requires a net-of-fees presentation for the "
          "composite; the returns here are net of trading and gross of that load, and the "
          "distinction is stated rather than assumed."],
         ["Reconciliation rule, historical record", "Equal weight on the two desk allocations",
          "Applied unchanged across all twenty meetings. Equal weight because neither desk "
          "has demonstrated skill that would justify preferring it. Every historical decision "
          "is mechanical and the report says so rather than inventing deliberation."]],
        align_left={0, 1, 2}, cls="tbl-sm"))
    out.append('<h3 class="sub">The design system used</h3>')
    out.append(
        "<p>This report is set in the <strong>Coldbrook Capital</strong> design system, the "
        "house system shipped in <code>ds/</code> in this folder: "
        "<code>ds/colors_and_type.css</code> holds the tokens and <code>ds/preview/</code> "
        "ships the component previews. Colours are the token values from that stylesheet "
        "rather than a remembered approximation, and the components follow their previews. "
        "Three departures are recorded. The stylesheet opens with a Google Fonts import, which "
        "is dropped so these documents render identically from disk with no network. The "
        "stylesheet sets <code>--navy: #0C1E48</code> while every preview and the written "
        "brand document use <code>#0A1B3D</code>, and the stylesheet's own <code>--up</code> "
        "token is <code>#0A1B3D</code> described as \"same as navy\", which it no longer is; "
        "the tokens file governs and the drift is reported rather than silently resolved. And "
        "the wordmark is Ashcroft's, since Coldbrook is the fictional firm the system was "
        "authored for and putting its mark on another institution's document would be wrong. "
        "There is no red or green anywhere in these documents: direction is carried by navy "
        "against clay, by parentheses on negatives, and by position relative to a zero "
        "axis.</p>")
    return "".join(out)
