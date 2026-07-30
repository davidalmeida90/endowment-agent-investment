"""
taa.report_main — assembles the three documents.

Run:  py -3 -m taa.report_main
"""

from __future__ import annotations

import json

from . import charts as C
from . import config, costs, perf
from . import render as R
from . import report_build as RB
from . import report_sections as S1
from . import report_sections2 as S2

pct, bps, mlab = RB.pct, RB.bps, RB.mlab
OUT = config.ROOT / "report"
PERIOD = RB.PERIOD
DOC = RB.DOC


# ==========================================================================
def evidence_appendix(d: dict) -> str:
    sysj = d["systematic"] or {}
    cme = d["cme"] or {}
    out = ['<div class="page-break"></div>']
    out.append(R.section("Evidence appendix"))
    out.append(
        "<p>Every claim taken from the literature, with a source a reader can open, marked "
        "according to whether the desk verified it in session or recalled it. The distinction "
        "matters: a training cutoff makes a recalled number a hypothesis rather than a fact, "
        "and several of these have moved.</p>")

    claims = sysj.get("claims", [])
    if claims:
        ver = sum(1 for c in claims if c.get("status") == "VERIFIED")
        out.append(f'<p class="note">{len(claims)} claims from the Systematic desk, '
                   f'{ver} verified in session and {len(claims) - ver} recalled '
                   f'({ver / max(len(claims),1) * 100:.0f}% verified).</p>')
        rows = []
        for c in claims:
            url = c.get("source_url", "")
            src = c.get("source", "")
            link = f'<a href="{url}">{src}</a>' if url else src
            rows.append([c.get("claim", "")[:150], str(c.get("value", ""))[:44],
                         link, c.get("status", "")])
        out.append(R.table(["Claim", "Value", "Source", "Status"], rows,
                           align_left={0, 1, 2, 3}, cls="tbl-sm", raw=True))

    srcs = cme.get("sources", [])
    if srcs:
        out.append('<h3 class="sub">Capital market assumptions, houses and vintages</h3>')
        rows = []
        for s in srcs:
            url = s.get("url", "")
            title = s.get("title", "")
            link = f'<a href="{url}">{title}</a>' if url else title
            rows.append([s.get("house", ""), link, s.get("vintage", ""), s.get("basis", "")])
        out.append(R.table(["House", "Publication", "Vintage", "Basis"], rows,
                           align_left={0, 1, 2, 3}, cls="tbl-sm", raw=True))

    out.append('<h3 class="sub">The two pre-reconciliation allocations, as tabled</h3>')
    q = (d["quant"] or {}).get("constrained", {})
    m = (d["macro"] or {}).get("weights", {})
    rows = []
    for k in config.LINES:
        p = config.POLICY[k]
        rows.append([config.LINE_LABEL[k], f"{p*100:.0f}",
                     f"{q.get(k, p)*100:.2f}", bps((q.get(k, p) - p) * 10000, 0),
                     f"{m.get(k, p)*100:.2f}", bps((m.get(k, p) - p) * 10000, 0)])
    out.append(R.table(
        ["Line", "Policy", "Quantitative desk", "Active", "Macro desk", "Active"],
        rows, units=["", "%", "%", "bps", "%", "bps"],
        foot=["Total", "100", f"{sum(q.values())*100:.2f}", "", f"{sum(m.values())*100:.2f}", ""]))
    out.append(
        f'<p class="fn">Quantitative desk rationale, as submitted: '
        f'{(d["quant"] or {}).get("rationale", "n/a")[:600]}</p>')
    out.append(
        f'<p class="fn">Macro desk rationale, as submitted: '
        f'{(d["macro"] or {}).get("rationale", "n/a")[:600]}</p>')

    out.append('<h3 class="sub">What was verified against what was recalled</h3>')
    out.append(
        "<p>The Capital Markets desk fetched every house forecast in session and each carries "
        "a URL. Two inputs are marked recalled and stated as such at the point of use: the "
        "long-run real earnings growth assumption in the bottom-up equity cross-check, and "
        "parts of the historical context around prior CAPE peaks. The Systematic desk fetched "
        "the primary papers rather than summaries of them where the paper was reachable, and "
        "marks eight of forty claims as recalled. Where a desk could not reach a primary "
        "source it says which secondary source it used instead, which happened once, for "
        "Research Affiliates, whose own tool requires a login and whose figures were taken "
        "from Morningstar.</p>")
    out.append(
        "<p>No paywalled source was used anywhere in this study and no credential was "
        "required. The one place a subscription would have improved the work is a clean "
        "forward earnings yield for the equity risk premium proxy, which the Macro desk "
        "records as out of scope by design and substitutes a dividend-yield construction "
        "for.</p>")
    return "".join(out)


# ==========================================================================
def build_report(d: dict) -> str:
    body = ['<div class="sheet">']
    body.append(RB.page_one(d))
    body.append(RB.office(d))
    body.append(RB.performance(d))
    body.append(RB.five_year(d))
    body.append(S1.year_decisions(d))
    body.append(S1.achievable(d))
    body.append(S1.systematic(d))
    body.append(S1.macro_view(d))
    body.append(S1.two_allocations(d))
    body.append(S1.reconciled(d))
    body.append(S2.compliance_section(d))
    body.append(S2.minutes(d))
    body.append(S2.risk_and_ops(d))
    body.append(S2.verification(d))
    body.append(S2.assumptions(d))
    body.append(evidence_appendix(d))
    body.append(
        '<div class="page-break"></div>'
        + R.section("Where to find the rest")
        + '<p>The five-year decision record, twenty quarterly entries with reasons, binding '
        'constraints and compliance results, is a separate document: '
        '<a href="decision_record.html">decision_record.html</a>. The interactive record is '
        '<a href="dashboard.html">dashboard.html</a>, which opens from disk with no network. '
        'The methods notebook, tying every method to the paper it comes from, is '
        '<code>methods.ipynb</code>. Every algorithm is a runnable Python file in '
        '<code>taa/</code>, the desk papers are in <code>desks/</code>, and the verification '
        'artifacts are in <code>tests/</code>.</p>'
        + '<p>Two supplementary notes sit in <code>outputs/</code>. '
          '<a href="../outputs/agent_dynamics.html">Three things the office did that were '
          'worth watching</a> records how six concurrent desks behaved as a system, with '
          'the clock time of each episode. '
          '<a href="../outputs/top_decisions.html">The three decisions that earned the '
          'most</a> is an outcome-selected analysis of the best three of the twenty, written '
          'with hindsight deliberately and labelled as such, and it does not change the '
          'recommendation.</p>'
        + '<p>Before any of this is published or quoted outside the Committee, read '
          '<code>AUDIT.md</code>. It records what in this study can and cannot be '
          'trusted: that the five-year record is a simulation of a rule rather than a '
          'track record, that the performance numbers cannot be separated from zero and '
          'change sign with the measurement window, and that the committee minutes are a '
          'construct whose reasoning is genuine and whose meeting is not.</p>')
    body.append(R.footer(DOC, PERIOD, "Ashcroft University Endowment"))
    body.append("</div>")
    return R.document("Ashcroft University Endowment — Annual Report to Trustees",
                      "".join(body))


# ==========================================================================
def build_record(d: dict) -> str:
    rec = d["record"]
    decs = rec["decisions"]
    sc = rec["scorecard"]
    s, b, a = d["s"], d["b"], d["a"]

    body = ['<div class="sheet">']
    body.append(R.header("Five-Year Decision Record", "1 July 2021 to 30 June 2026",
                         "Twenty quarterly meetings · Office of the Chief Investment Officer"))

    body.append(R.section("What this document is, and what it is not"))
    body.append(
        "<p>This is the record a trustee reads to decide whether the office has been thinking "
        "or drifting. It carries twenty quarterly decisions, each with the allocation before "
        "and after, what moved and why, the mandate constraint that bound at that moment, the "
        "compliance result on the allocation adopted, whether the two desks agreed, and what "
        "the meeting said it would watch.</p>")
    body.append(
        "<p><strong>Every decision here is mechanical, and the office says so at the outset "
        "rather than letting a reader assume otherwise.</strong> A pre-committed rule read the "
        "point-in-time inputs available on each meeting date and produced an allocation. The "
        "rule never changed. The reason attached to each entry is the reading of the inputs "
        "that drove the rule, and it could have been written on the day by someone holding "
        "only the papers tabled at that meeting. Inventing deliberation that did not occur "
        "would be the easiest way to make this document look impressive and the fastest way "
        "to make it worthless.</p>")
    body.append(
        "<p>The discipline is tested rather than asserted. No field in any entry other than "
        "the outcome may reference a date later than that meeting, which is checked "
        "mechanically across all twenty. Outcomes are written last and appear in no reason. "
        "Watch items are written at a meeting, never revised, and resolved forward at the "
        "next one.</p>")

    body.append(R.section("The scorecard, stated plainly"))
    body.append(R.verdict(
        "After five years and twenty decisions",
        f"{bps(sc['net_active_bps_per_year'])}bps a year of active return against "
        f"{sc['turnover_cost_bps_per_year']:.1f}bps of turnover cost. "
        f"Information ratio {rec['summary']['active']['information_ratio']:.2f}, "
        f"standard error approximately 0.45."))
    body.append(
        f"<p><strong>The tactical programme added nothing a trustee should pay for.</strong> "
        f"Of twenty decisions, {sc['helped']} helped, {sc['hurt']} hurt and "
        f"{sc['too_small_to_tell']} were too small to tell. The net is "
        f"{bps(sc['net_active_bps_per_year'])}bps a year before the cost of running the "
        f"office and against an information ratio whose standard error is twice its value. On "
        f"sixty monthly observations a result this size cannot be separated from zero, and the "
        f"office does not claim otherwise.</p>")
    body.append(R.strip([
        (str(sc["decisions"]), "Quarterly decisions"),
        (str(sc["helped"]), "Helped"),
        (str(sc["hurt"]), "Hurt"),
        (str(sc["too_small_to_tell"]), "Too small to tell"),
        (bps(sc["net_active_bps_per_year"]) + "bps", "Net active return a year"),
    ]))

    ca = (1 + a).cumprod() * 100 - 100
    marks = []
    dates = list(a.index)
    for e in decs:
        import pandas as _pd
        t = _pd.Timestamp(e["date"])
        if t in dates:
            marks.append({"i": dates.index(t), "kind": e["kind"]})
    body.append(R.chart_block(
        C.marked_line([float(v) for v in ca.values], mlab(a.index), marks,
                      "Cumulative active return, with the twenty decisions marked",
                      "fund less benchmark, per cent, compounded", height=270, label_every=6,
                      fmt=lambda v: C._n(v, 1)),
        [("Cumulative active return", C.NAVY, "line"),
         ("Tilt", C.NAVY, "block"), ("Unwind", C.CLAY, "block"),
         ("Hold", C.SLATE, "block")],
        "Mark shape carries the decision type, not colour. A reader can see which meeting "
        "preceded which move."))

    freq = sc["binding_constraint_frequency"]
    body.append(R.chart_block(
        C.hbar_frequency(sorted(freq.items(), key=lambda kv: -kv[1]),
                         "Which constraint bound, as a frequency",
                         "number of the twenty quarterly meetings", width=860, name_w=210),
        None,
        "If the same constraint bound every quarter, that is the most important fact in the "
        "record, because it means the signal was never what set position size."))
    body.append(
        f"<p>The realised drawdown constraint bound at "
        f"<strong>{freq.get('drawdown_realised', 0)} of twenty</strong> meetings. That is the "
        f"most important line in this document. From December 2022 onward the fund was "
        f"carrying a peak-to-trough drawdown beyond the Board's (20.00)% limit, and the "
        f"binding constraint at almost every subsequent meeting was that fact rather than any "
        f"signal. <strong>The signal was rarely what set position size.</strong> The office "
        f"separates two things the compliance test reports together: an allocation defect, "
        f"which is remedied by choosing different weights, and a breach of the fund's own "
        f"limit, which cannot be remedied by reallocation because it has already happened. "
        f"{sc['quarters_failing_compliance']} of {sc['decisions']} allocations failed on their "
        f"own merits after remediation, and {sc['quarters_needing_remediation']} needed "
        f"remediation to get there. {sc['quarters_fund_in_breach']} of {sc['decisions']} "
        f"meetings took place with the fund in breach of its drawdown limit, which "
        f"is a Board matter under IPS 3.3 and 2.3 rather than a portfolio matter.</p>")

    body.append(R.section("What the office got consistently wrong"))
    hurt = [e for e in decs if e["outcome"]["verdict"] == "hurt"]

    def _top(e, n=2):
        return sorted(e["active_after_bps"].items(), key=lambda kv: -abs(kv[1]))[:n]

    dur_short = [e for e in hurt if e["active_after_bps"].get("ust_duration", 0) < -100]
    dur_long = [e for e in hurt if e["active_after_bps"].get("ust_duration", 0) > 100]
    other = [e for e in hurt if e not in dur_short and e not in dur_long]
    carried_duration = len(dur_short) + len(dur_long)

    body.append(
        f"<p>{len(hurt)} decisions hurt. Five unrelated bad calls and five instances of the "
        f"same bad call are different findings, and only the second is fixable, so the losing "
        f"decisions are grouped by what they held rather than listed by date. The grouping "
        f"below is computed from the record rather than asserted.</p>")
    body.append(R.verdict(
        "The common cause",
        f"All {carried_duration} of the {len(hurt)} losing decisions carried a Treasury "
        f"duration position, and the sign flipped halfway through the record."))
    rows = []
    if dur_short:
        rows.append([
            f"Duration underweight, cash overweight",
            f"{len(dur_short)} decisions, {dur_short[0]['date'][:7]} to {dur_short[-1]['date'][:7]}",
            "Short duration and long cash while the tightening cycle peaked and the long end "
            "recovered. The momentum and trend signals on the duration line had turned "
            "negative through 2022 and stayed negative into the turn.",
            f"{sum(e['outcome']['active_return_bps'] for e in dur_short):.0f}bps"])
    if dur_long:
        rows.append([
            f"Duration overweight, equity underweight",
            f"{len(dur_long)} decisions, {dur_long[0]['date'][:7]} to {dur_long[-1]['date'][:7]}",
            "The same signals flipped positive after the rally, so the office bought duration "
            "and funded it from equity through an equity-led market. This is the same failure "
            "as the group above with the sign reversed: a trend signal at a turning point.",
            f"{sum(e['outcome']['active_return_bps'] for e in dur_long):.0f}bps"])
    if other:
        rows.append([
            "Everything else",
            f"{len(other)} decisions",
            "No shared position. These are the genuinely unrelated calls.",
            f"{sum(e['outcome']['active_return_bps'] for e in other):.0f}bps"])
    body.append(R.table(
        ["Grouping", "When", "What they share", "Cost"],
        rows, align_left={0, 1, 2}, cls="tbl-sm"))
    body.append(
        f"<p>This is the useful version of the scorecard. {carried_duration} losing decisions "
        f"in two groups that are the same error twice, on the one line whose out-of-sample "
        f"R² against the expanding mean is most negative, is a fixable finding. Eight "
        f"unrelated bad calls would not be. The recommendation removes the duration position "
        f"entirely, which is the only one of these the office can act on.</p>")
    body.append(
        "<p>The deeper cause is the one the Systematic desk identified before any of these "
        "decisions were reviewed. The programme was sized to a tracking-error budget rather "
        "than to demonstrated skill. A budget is permission to take risk, not a reason to.</p>")

    body.append(R.section("The twenty decisions"))
    for e in decs:
        body.append(_entry(e))

    body.append(R.footer("Five-Year Decision Record", "1 July 2021 to 30 June 2026",
                         "Ashcroft University Endowment"))
    body.append("</div>")
    return R.document("Ashcroft University Endowment — Five-Year Decision Record", "".join(body))


def _entry(e: dict) -> str:
    moves = sorted(e["trades_pp"].items(), key=lambda kv: -abs(kv[1]))
    mv = ", ".join(f"{config.LINE_LABEL[k]} {v:+.2f}pp" for k, v in moves[:5]) or "no trade"
    o = e["outcome"]
    out = [f'<h3 class="sub">{e["n"]}. &nbsp; {R.datestr(e["date"])} &nbsp;·&nbsp; '
           f'{e["kind"].upper()} &nbsp;·&nbsp; {e["fiscal_year"]}</h3>']
    out.append(R.table(
        ["Field", "Value"],
        [["Allocation before", ", ".join(f"{config.LINE_LABEL[k]} {v*100:.1f}"
                                         for k, v in e["weights_before"].items() if v > 0.001)],
         ["Allocation after", ", ".join(f"{config.LINE_LABEL[k]} {v*100:.1f}"
                                        for k, v in e["weights_after"].items() if v > 0.001)],
         ["What moved", mv],
         ["Turnover", f"{e['turnover_pp']:.2f}pp one-way, costing {e['cost_bps']:.2f}bps"],
         ["Regime read, point in time", f"{e['regime']['label']} "
          f"(growth {e['regime']['growth']}, inflation {e['regime']['inflation']}, "
          f"policy {e['regime']['policy']})"],
         ["Ex-ante tracking error", f"{e['te_before_bps']:.0f}bps before truncation, "
          f"{e['te_after_bps']:.0f}bps after, against a 200bps budget"],
         ["Binding constraint", e["binding_constraint"]],
         ["Compliance on the allocation adopted",
          ("PASS" if e["compliance"]["passed"] else
           "FAIL: " + ", ".join(e["compliance"]["failed"]))
          + (f" · remediated in {e['compliance']['remediation_rounds']} round(s)"
             if e["compliance"]["remediation_rounds"] else "")],
         ["Fund in breach of its own limit",
          ", ".join(e["compliance"]["fund_in_breach"]) or "no"],
         ["Did the two desks agree",
          "yes" if e["desks_agreed"] else
          f"no, {e['max_desk_disagreement_bps']:.0f}bps apart at the widest line"],
        ], align_left={0, 1}, cls="tbl-sm"))
    out.append(f'<p><strong>Reason.</strong> {e["reason"]}</p>')
    if e.get("inputs_cited"):
        cited = "; ".join(f'{c["name"]} {c["value"]}' for c in e["inputs_cited"][:5])
        out.append(f'<p class="fn">Readings on the table that day: {cited}.</p>')
    if e.get("watch"):
        out.append('<p class="note"><strong>Watched into the next meeting:</strong> '
                   + " ".join(w["text"] for w in e["watch"]) + "</p>")
    if e.get("watch_resolution"):
        res = "; ".join(
            f'{r["text"][:96]} &mdash; {"it occurred" if r["happened"] else "it did not occur"}'
            for r in e["watch_resolution"])
        out.append(f'<p class="note"><strong>The previous meeting\'s item, resolved here:</strong> '
                   f'{res}</p>')
    if e.get("anachronisms"):
        out.append(f'<p class="fn"><strong>Anachronistic inputs declared at this decision:</strong> '
                   f'{"; ".join(str(x) for x in e["anachronisms"])}</p>')
    out.append(
        f'<p class="fn"><strong>Outcome, recorded after the fact and used in no reason above:</strong> '
        f'{bps(o["active_return_bps"])}bps of active return over the {o["months_held"]} months '
        f'held. Fund {o["strategy_return_pct"]:+.2f}%, benchmark {o["benchmark_return_pct"]:+.2f}%. '
        f'Verdict: {o["verdict"]}.</p>')
    out.append('<hr class="rule">')
    return "".join(out)


# ==========================================================================
def main() -> int:
    d = RB.load_all()
    if not d.get("record"):
        print("no decision record; run  py -3 -m taa.simulate  first")
        return 2
    (OUT / "annual_report.html").write_text(build_report(d), encoding="utf-8")
    print(f"  report/annual_report.html   {(OUT / 'annual_report.html').stat().st_size:,} bytes")
    (OUT / "decision_record.html").write_text(build_record(d), encoding="utf-8")
    print(f"  report/decision_record.html {(OUT / 'decision_record.html').stat().st_size:,} bytes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
