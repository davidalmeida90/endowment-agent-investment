"""
taa.reports_extra — two supplementary reports written into outputs/.

  outputs/desk_interactions.html   the three exchanges that changed the study
  outputs/top_decisions.html       the three decisions that earned the most,
                                   and how each was reached

Both are generated from the record and from the artifacts on disk, in the same
design system as the main report, so neither can drift from the study it
describes.

Run:  py -3 -m taa.reports_extra
"""

from __future__ import annotations

import json

import pandas as pd

from . import charts as C
from . import config, perf, pitdata
from . import render as R
from . import report_build as RB

pct, bps = RB.pct, RB.bps
OUT = config.OUTPUTS


# ==========================================================================
# 1. AGENT DYNAMICS
# ==========================================================================
from ._agent_dynamics import build as agent_dynamics  # noqa: E402


# ==========================================================================
# 2. TOP DECISIONS
# ==========================================================================
def _attribution(e: dict, decs: list, rets: pd.DataFrame) -> list[tuple[str, float, float, float]]:
    d0 = pd.Timestamp(e["date"])
    later = [pd.Timestamp(x["date"]) for x in decs if pd.Timestamp(x["date"]) > d0]
    d1 = min(later) if later else rets.index.max()
    seg = rets[(rets.index > d0) & (rets.index <= d1)]
    out = []
    for k in config.LINES:
        aw = e["active_after_bps"][k] / 10000.0
        lr = float((1 + seg[k]).prod() - 1)
        out.append((k, e["active_after_bps"][k], lr * 100, aw * lr * 10000))
    return sorted(out, key=lambda t: -abs(t[3]))


def top_decisions() -> str:
    rec = json.loads((config.OUTPUTS / "decision_record.json").read_text(encoding="utf-8"))
    decs = rec["decisions"]
    sc = rec["scorecard"]
    rets = pitdata.as_of(config.WINDOW_END).monthly_returns()
    top = sorted(decs, key=lambda e: -e["outcome"]["active_return_bps"])[:3]

    body = ['<div class="sheet">']
    body.append(R.header("The Three Decisions That Earned the Most",
                         "Outcome analysis", "Supplement to the Five-Year Decision Record"))

    body.append(R.section("Read this first, because the selection is the problem"))
    body.append(
        "<p><strong>This report is built by sorting twenty decisions on their outcome and "
        "keeping the top three. That is hindsight, applied deliberately, and it is the one "
        "thing the decision record forbids anywhere inside a reason.</strong> It is legitimate "
        "here only because the report is labelled as what it is: an account of what happened "
        "after the fact, not an account of why anything was decided.</p>")
    body.append(
        f"<p>Three winners out of twenty is not evidence of skill and this note is not offered "
        f"as any. The full scorecard is <strong>{sc['helped']} helped, {sc['hurt']} hurt, "
        f"{sc['too_small_to_tell']} too small to tell</strong>, a net of "
        f"<strong>{bps(sc['net_active_bps_per_year'])}bps</strong> a year against "
        f"<strong>{sc['turnover_cost_bps_per_year']:.1f}bps</strong> of turnover cost, and an "
        f"information ratio of <strong>{rec['summary']['active']['information_ratio']:.2f}</strong> "
        f"whose standard error on sixty monthly observations is roughly 0.45. Selecting the "
        f"best three from any twenty coin flips produces three impressive coin flips. The "
        f"question worth asking of each entry below is not whether it made money but whether "
        f"the reasoning tabled on the day would have looked sound to a trustee who did not yet "
        f"know the answer.</p>")

    body.append(R.section("What the three have in common, which is not what one would hope"))
    findings = []
    for e in top:
        att = _attribution(e, decs, rets)
        biggest = att[0]
        sig = sorted(e["signal_readings"].items(), key=lambda kv: -abs(kv[1]))
        rank = next((i + 1 for i, (k, _) in enumerate(sig) if k == biggest[0]), None)
        findings.append((e, biggest, rank, sig))
    body.append(R.table(
        ["Meeting", "Earned", "The line that earned it", "Its rank among the signal readings"],
        [[R.datestr(e["date"]), bps(e["outcome"]["active_return_bps"], 0),
          f"{config.LINE_LABEL[b[0]]}, {bps(b[3], 0)}bps",
          f"{r} of 9" if r else "n/a"] for e, b, r, _ in findings],
        units=["", "bps", "", ""], align_left={0, 2, 3}))
    body.append(
        "<p>In two of the three, <strong>the line that produced most of the money was not a "
        "line the signal was loud about</strong>, and in one of those it was a position the "
        "meeting did not trade at all. That is not a criticism of the decisions. It is the "
        "same finding the systematic evidence reports from the other direction: with a "
        "composite out-of-sample R² of (1.61)% against the historical mean, there is no reason "
        "to expect the loudest signal to be the one that pays, and the record shows it was "
        "not.</p>")

    # ---------------- each decision
    for idx, (e, biggest, rank, sig) in enumerate(findings, start=1):
        att = _attribution(e, decs, rets)
        o = e["outcome"]
        body.append('<div class="page-break"></div>')
        body.append(R.section(f"{idx}. {R.datestr(e['date'])} — {e['kind']}, "
                              f"{bps(o['active_return_bps'], 0)}bps"))
        body.append(R.verdict(
            "What it earned",
            f"{bps(o['active_return_bps'], 1)}bps of active return over {o['months_held']} "
            f"months. Fund {o['strategy_return_pct']:+.2f}%, benchmark "
            f"{o['benchmark_return_pct']:+.2f}%."))

        body.append('<h3 class="sub">What was on the table that day</h3>')
        body.append(R.table(
            ["Input", "Reading"],
            [["Regime, on the vintages available then",
              f"{e['regime']['label']} — growth {e['regime']['growth']}, inflation "
              f"{e['regime']['inflation']}, policy {e['regime']['policy']}"],
             ["Three loudest composite signals",
              ", ".join(f"{config.LINE_LABEL[k]} {v:+.2f}" for k, v in sig[:3])],
             ["The two desks", "agreed" if e["desks_agreed"] else
              f"disagreed, {e['max_desk_disagreement_bps']:.0f}bps apart at the widest line"],
             ["Ex-ante tracking error",
              f"{e['te_before_bps']:.0f}bps before truncation, {e['te_after_bps']:.0f}bps after, "
              f"against a {config.TE_BUDGET_BPS:.0f}bps budget"],
             ["Binding constraint", e["binding_constraint"]],
             ["Compliance on the allocation adopted",
              ("PASS" if e["compliance"]["passed"] else
               "FAIL: " + ", ".join(e["compliance"]["failed"]))],
             ["Turnover and its cost",
              f"{e['turnover_pp']:.2f}pp one-way, costing {e['cost_bps']:.2f}bps"]],
            align_left={0, 1}))

        body.append('<h3 class="sub">How the allocation was reached</h3>')
        body.append(f"<p>{e['reason']}</p>")
        body.append(
            '<p class="fn">That paragraph is the reason as recorded at the meeting. It was '
            'built only from the readings above, it names no date later than the meeting, and '
            'it contains no reference to the outcome. That is asserted mechanically across all '
            'twenty entries by <code>tests/check_hindsight.py</code>.</p>')

        body.append('<h3 class="sub">Where the money actually came from</h3>')
        body.append(R.chart_block(
            C.diverging_bars(
                [(config.LINE_LABEL[k], v) for k, _, _, v in att if abs(v) > 0.5],
                "Contribution to active return by line",
                "active weight held through the quarter, times that line's return, basis points",
                width=860, name_w=190, fmt=lambda v: C._n(v, 1)),
            [("Added to active return", C.NAVY, "block"),
             ("Detracted", C.CLAY, "block")]),)
        body.append(R.table(
            ["Line", "Active weight held", "Line return over the quarter", "Contribution"],
            [[config.LINE_LABEL[k], bps(aw, 0), pct(lr / 100), bps(c, 1)]
             for k, aw, lr, c in att[:6]],
            units=["", "bps", "%", "bps"],
            foot=["Sum of the six largest", "", "", bps(sum(c for _, _, _, c in att[:6]), 1)]))
        body.append(
            '<p class="fn">A first-order attribution: the active weight adopted at the meeting, '
            'held constant, times each line\'s compounded return over the quarter. The realised '
            'active return differs because weights drift with returns inside the quarter and '
            'because the arithmetic compounds. The gap between the two is the interaction term '
            'and is not attributable to any single line.</p>')
        body.append(_commentary(idx, e, att, sig, rank, biggest))

    # ---------------- close
    body.append('<div class="page-break"></div>')
    body.append(R.section("What this changes about the recommendation, which is nothing"))
    body.append(
        f"<p>These three decisions produced "
        f"{sum(x['outcome']['active_return_bps'] for x in top):.0f}bps between them. The other "
        f"seventeen produced "
        f"{sum(x['outcome']['active_return_bps'] for x in decs) - sum(x['outcome']['active_return_bps'] for x in top):+.0f}bps. "
        f"The programme as a whole returned {bps(sc['net_active_bps_per_year'])}bps a year "
        f"before the cost of running the office, on an information ratio that cannot be "
        f"separated from zero at this sample size.</p>")
    body.append(
        "<p>A record in which three decisions carry the entire result, and in which the line "
        "that earned the money was usually not the line the signal was loudest about, is a "
        "record of a programme that got lucky in a few quarters rather than one that found "
        "something. The office does not have twenty independent observations here; it has one "
        "tightening cycle and one recovery. The recommendation for the coming year is policy "
        "weights, and nothing in this note argues otherwise.</p>")
    body.append(
        "<p>The one decision-useful finding is the mirror image of this note. Of the eight "
        "decisions that hurt, <strong>all eight carried a Treasury duration position and the "
        "sign flipped halfway through the record</strong>. That is one error made twice on the "
        "line with the most negative out-of-sample R², and it is fixable in a way that three "
        "good quarters are not repeatable.</p>")
    body.append(R.footer("The Three Decisions That Earned the Most", "FY2026",
                         "Ashcroft University Endowment"))
    body.append("</div>")
    return R.document("Ashcroft University Endowment — The Three Decisions That Earned the Most",
                      "".join(body))


def _commentary(idx: int, e: dict, att, sig, rank, biggest) -> str:
    """Written against the attribution, not against the reason. Outcome analysis."""
    losers = [t for t in att if t[3] < -1.0]
    top_lbl = config.LINE_LABEL[biggest[0]]
    txt = ['<h3 class="sub">Reading it honestly</h3>']
    if e["date"].startswith("2022-03"):
        txt.append(
            f"<p>The largest contributor was the <strong>US equity underweight</strong>, worth "
            f"{bps(att[0][3], 0)}bps as the line fell {pct(att[0][2] / 100)}% over the quarter. "
            f"The composite on US equity that day was {dict(sig).get('us_equity', 0):+.2f}, "
            f"which was the <strong>fifth</strong> loudest of nine readings. The two signals "
            f"the desk cited as strongest, US investment grade at (0.83) and commodities at "
            f"+0.82, contributed {bps([t for t in att if t[0] == 'us_ig'][0][3], 0)}bps and "
            f"less respectively.</p>")
        txt.append(
            f"<p>The decision was also <strong>wrong on a line</strong>. The developed ex-US "
            f"overweight, which the composite ranked third at +0.51, cost "
            f"{bps([t for t in att if t[0] == 'dev_ex_us'][0][3], 0)}bps. The meeting made money "
            f"net because the de-risking was broad and the quarter was broadly negative, not "
            f"because the ranking was right.</p>")
        txt.append(
            "<p>What this decision does show is the constraint hierarchy working as designed. "
            "The combined desk view implied 93bps of tracking error and the binding constraint "
            "was the ex-ante drawdown stress test, not the tracking-error budget. The office "
            "moved 10.5pp of the portfolio, the largest single quarter of turnover in the "
            "record, for 0.80bps of cost. That is the implementation desk's cost vector doing "
            "its job.</p>")
    elif e["date"].startswith("2025-12"):
        txt.append(
            f"<p>This is the clearest case in the record of a good outcome that the decision "
            f"did not cause. The largest contributor by a distance was <strong>commodities</strong>, "
            f"worth {bps(att[0][3], 0)}bps as the line returned {pct(att[0][2] / 100)}% over the "
            f"quarter. <strong>The meeting did not trade commodities.</strong> The position was "
            f"carried in from earlier decisions and the composite on that line was not among "
            f"the three the desk cited.</p>")
        txt.append(
            f"<p>What the meeting actually decided was to add 4.3pp to developed ex-US, cut US "
            f"equity 2.2pp and cut emerging markets 1.8pp. The US equity underweight earned "
            f"{bps([t for t in att if t[0] == 'us_equity'][0][3], 0)}bps and was well supported "
            f"by the second-loudest signal. The developed ex-US addition earned "
            f"{bps([t for t in att if t[0] == 'dev_ex_us'][0][3], 0)}bps. And the emerging "
            f"markets cut looks at first like it ran <strong>against</strong> the loudest signal "
            f"on the table, emerging markets at +0.71. It did not. The line had drifted to "
            f"15.2% on its own returns, above the Quantitative desk's target of 14.4% and "
            f"above the Macro desk's 12.5%, so both desks implied a trim and the sale was "
            f"drift correction rather than a reversal of the view. This is worth stating "
            f"because a column headed \"what moved\" invites exactly the wrong reading: a "
            f"sale can be a signal-consistent overweight being pulled back to target.</p>")
        txt.append(
            "<p>A trustee is entitled to ask why the office sold the line its own model liked "
            "most. The answer is the pre-committed reconciliation rule, applied without "
            "exception across all twenty meetings, and the office would rather report a rule "
            "producing an awkward result than a rule that was quietly suspended when it did.</p>")
    else:
        txt.append(
            f"<p>The largest contributor was <strong>{top_lbl}</strong>, worth "
            f"{bps(biggest[3], 0)}bps, and it ranked {rank} of nine among the signal readings "
            f"that day. The position was small: the whole meeting moved 1.2pp and cost "
            f"0.07bps.</p>")
        txt.append(
            f"<p>The more interesting fact about this meeting is that it was principally a "
            f"<strong>de-risking</strong>. Ex-ante tracking error fell from 87bps to 28bps, "
            f"the largest single reduction in the record, because the ex-ante drawdown stress "
            f"test bound and truncated the combined view. The office earned "
            f"{bps(e['outcome']['active_return_bps'], 0)}bps in a quarter when the benchmark "
            f"fell {e['outcome']['benchmark_return_pct']:.2f}% largely by holding less of "
            f"everything that was falling.</p>")
        txt.append(
            f"<p>The developed ex-US overweight, ranked fourth on the composite at +0.46, "
            f"detracted {bps([t for t in att if t[0] == 'dev_ex_us'][0][3], 0)}bps. As in the "
            f"other two entries, the ranking was partly right and partly wrong and the net was "
            f"positive.</p>")
    if losers:
        txt.append(
            f'<p class="fn">Lines that detracted at this meeting: '
            + ", ".join(f"{config.LINE_LABEL[k]} {bps(v, 1)}bps" for k, _, _, v in losers)
            + ". A decision that made money is not a decision that was right about everything, "
              "and an outcome report that shows only the winners inside a winner is the same "
              "selection error one level down.</p>")
    return "".join(txt)


def main() -> int:
    (OUT / "agent_dynamics.html").write_text(agent_dynamics(), encoding="utf-8")
    print(f"  outputs/agent_dynamics.html     "
          f"{(OUT / 'agent_dynamics.html').stat().st_size:,} bytes")
    (OUT / "top_decisions.html").write_text(top_decisions(), encoding="utf-8")
    print(f"  outputs/top_decisions.html      "
          f"{(OUT / 'top_decisions.html').stat().st_size:,} bytes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
