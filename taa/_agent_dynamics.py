"""
The agent-dynamics note. Imported into taa.reports_extra.

This is an account of how six concurrent desks behaved as a system, not an
account of the portfolio. Every event carries the clock time it happened at,
taken from file modification times and from the point-in-time access log, so a
reader can reconstruct the sequence rather than take the narrative on trust.
"""

from __future__ import annotations

from . import charts as C
from . import config
from . import render as R

# Desk telemetry, as reported by the runtime when each agent completed.
DESKS = [
    ("Capital Markets", "23:12", "23:35", 23.2, 76, 247_038),
    ("Systematic", "23:12", "23:35", 23.1, 82, 239_993),
    ("Implementation & Operations", "23:12", "23:45", 32.6, 87, 265_588),
    ("Risk", "23:28", "23:59", 30.9, 69, 234_597),
    ("Quantitative", "23:28", "00:11", 43.1, 115, 281_868),
    ("Macro", "23:28", "23:53", 24.8, 55, 200_574),
]


def build() -> str:
    body = ['<div class="sheet">']
    body.append(R.header("Three Episodes Worth Watching",
                         "Agent dynamics", "Six concurrent desks · 28 to 29 July 2026"))

    body.append(R.section("What this note is"))
    body.append(
        "<p>Six desks ran on this mandate as independent agents. Three were commissioned at "
        "<strong>23:12</strong> and three at <strong>23:28</strong>, and the last of them "
        "finished at <strong>00:11</strong>. Between them they made 484 tool calls and "
        "consumed about 1.47 million tokens. This note is about what happened <em>between</em> "
        "them, which is the part of a multi-agent run that a summary of the conclusions hides "
        "completely.</p>")
    body.append(
        "<p>Three episodes are worth a trustee's attention, and none of them is about markets. "
        "They are ranked by what they say about whether this way of working is trustworthy.</p>")

    body.append(R.table(
        ["Desk", "Commissioned", "Delivered", "Elapsed", "Tool calls", "Tokens"],
        [[n, a, b, f"{m:.0f} min", str(t), f"{k:,}"] for n, a, b, m, t, k in DESKS],
        units=["", "", "", "", "", ""],
        foot=["Six desks", "23:12", "00:11", "—",
              str(sum(d[4] for d in DESKS)), f"{sum(d[5] for d in DESKS):,}"],
        align_left={0, 1, 2, 3}))
    body.append(
        '<p class="fn">The three commissioned at 23:28 were held back only until the '
        'point-in-time data layer existed for them to read through. The Quantitative and Macro '
        'desks were started in the same instruction, deliberately, so that neither could see '
        'the other\'s output because neither existed yet.</p>')

    # ================================================================== 1
    body.append('<div class="page-break"></div>')
    body.append(R.section("One. Two blind agents disagreed by 16 points, and both were wrong"))
    body.append(R.verdict(
        "23:28 to 00:11 · the Quantitative and Macro desks",
        "Reconciliation was not splitting the difference. The evidence rejected both sides "
        "of the largest disagreement in the study."))
    body.append(
        "<p>The two desks were run concurrently on disjoint briefs, each barred by name from "
        "the other's files, writing to separate directories. Neither brief contained any "
        "conclusion, number or framing from the other. The Macro desk delivered at "
        "<strong>23:49</strong> and the Quantitative desk at <strong>00:06</strong>, so for "
        "the whole of the Macro desk's working life the Quantitative desk's answer did not "
        "exist anywhere on disk.</p>")
    body.append(
        "<p>The design question this was built to answer is whether independence buys anything "
        "or just costs time. It bought something specific and it was not agreement.</p>")

    import json as _json
    _q = _json.loads((config.OUTPUTS / "quant" / "allocation.json").read_text(
        encoding="utf-8")).get("constrained", {})
    _m = _json.loads((config.OUTPUTS / "macro" / "allocation.json").read_text(
        encoding="utf-8")).get("weights", {})
    _gaps = sorted(
        [(config.LINE_LABEL[k],
          (_q.get(k, config.POLICY[k]) - _m.get(k, config.POLICY[k])) * 10000)
         for k in config.LINES],
        key=lambda t: -abs(t[1]))
    body.append(R.chart_block(
        C.diverging_bars(
            _gaps,
            "Where the two blind desks disagreed",
            "quantitative active weight less macro active weight, basis points",
            width=860, name_w=190),
        [("Quantitative more positive", C.NAVY, "block"),
         ("Macro more positive", C.CLAY, "block")]))

    body.append(
        "<p>The disagreement was <strong>concentrated rather than diffuse</strong>, which is "
        "what made it usable. On Treasury duration the Quantitative desk was 10.0 points "
        "overweight and the Macro desk 6.5 points underweight, a gap of 16.5 points on a line "
        "with a 12% policy weight. Two agents given the same mandate and the same data layer, "
        "each working carefully, landed on opposite sides of the single largest position in "
        "the study.</p>")
    body.append(
        "<p>The interesting part is what happened next. The obvious move with two independent "
        "estimates is to average them, and the historical simulation does exactly that under a "
        "pre-committed rule. For the live recommendation it would have been wrong. The "
        "Quantitative desk's overweight rests on momentum and carry signals whose "
        "out-of-sample R² against the expanding historical mean is negative, so the "
        "position stands on an estimator that desk's own evidence does not support. The Macro "
        "desk's underweight rests on three deviations from consensus that <em>the desk itself "
        "states are one proposition rather than three</em>, none of which resolves before "
        "December 2026. <strong>Both sides were rejected and the line went to policy "
        "weight.</strong></p>")
    body.append(
        "<p>A sixteen-point disagreement between two agents with no demonstrated skill is not "
        "information. It is noise with two authors, and averaging noise produces a smaller "
        "number that is no more informative than either input. The reconciliation that mattered "
        "was the one that refused both.</p>")

    body.append('<h3 class="sub">Where they agreed, and why most of it does not count</h3>')
    body.append(
        "<p>They agreed on developed ex-US and listed real estate, both at policy, and agreed "
        "in direction on US equity, investment grade and high yield. Most of that agreement is "
        "weaker than it looks, because both desks read the same prices through the same module. "
        "A common input producing a common answer is one fact counted twice, and the US equity "
        "underweight is exactly that: both desks reach it from the observation that the line is "
        "expensive against its own history.</p>")
    body.append(
        "<p><strong>One agreement is genuine.</strong> On high yield the Quantitative desk "
        "arrives from spread carry measured against realised volatility, and the Macro desk "
        "from a credit spread sitting in the tightest decile of its available history against "
        "a policy rate it judges insufficiently restrictive. Different instruments, different "
        "reasoning, same position. That is the only place in this study where independence "
        "produced confirmation rather than duplication, and it is worth more than the size of "
        "the position warrants.</p>")

    # ================================================================== 2
    body.append('<div class="page-break"></div>')
    body.append(R.section("Two. Every check in the office fired on its own author"))
    body.append(R.verdict(
        "23:26, 23:44, 23:52, 23:57 and 00:06 · five separate occasions",
        "Nobody's work was exempt, including the work of whoever wrote the check."))
    body.append(
        "<p>This is the episode that says most about whether the process is worth anything. "
        "Over roughly forty minutes, five checks fired, and in every case the thing caught "
        "belonged to the same party that built the check or to the office that commissioned "
        "it. None of them fired on a convenient outsider.</p>")
    body.append(R.table(
        ["Time", "What fired", "What it caught", "Whose work"],
        [["23:26", "The raw-store caller guard",
          "The study's own data pull. The guard identified callers by module name and a module "
          "run with <code>python -m</code> is named <code>__main__</code>, so the very first "
          "thing the wall did was refuse the office that built it.",
          "Mine"],
         ["23:44", "A two-line smoke test on the cost interface",
          "A unit mismatch between the Implementation desk's module and the rest of the study. "
          "Left alone it would have suppressed every trade in all twenty quarters and produced "
          "a record of twenty holds that were an arithmetic error.",
          "The seam between a desk and me"],
         ["23:52", "The Risk desk's own compliance suite",
          "The Risk desk's own most important test case, the one IPS 4.1 names by name. The "
          "suite exited red on the desk that wrote it.",
          "The Risk desk's"],
         ["23:57", "The static import-graph test",
          "The Quantitative desk reaching the raw cache through a memoisation key, while that "
          "desk was still building.",
          "The Quantitative desk's"],
         ["00:06", "The Quantitative desk's own look-ahead check",
          "Two real look-aheads inside that desk's own work: a missing one-day publication lag "
          "in the credit carry panel, and sub-threshold trades reintroduced by its own "
          "minimum-trade repair. The desk documented both rather than fixing them quietly.",
          "The Quantitative desk's"]],
        align_left={0, 1, 2, 3}, raw=True))
    body.append(
        "<p>The last row is the one to weigh. An agent's self-check found errors in that "
        "agent's own analysis and the agent <strong>reported them in its paper</strong> rather "
        "than repairing them silently and presenting clean work. Nothing in the office would "
        "have detected either error if it had chosen otherwise. That is a disposition rather "
        "than a control, and it is the part of this that a test cannot enforce.</p>")
    body.append(
        "<p>The 23:52 row is the one where the wrong fix was available and tempting. The Risk "
        "desk's suite was red on a case that the compliance module actually handled correctly; "
        "the defect was in the harness. Three fixes would have turned the suite green while "
        "destroying it: loosen the check, make the range constraint non-gating, or change the "
        "case's expectation. The instruction sent to the desk named all three and forbade "
        "them. <strong>A green suite is not the objective.</strong></p>")

    # ================================================================== 3
    body.append('<div class="page-break"></div>')
    body.append(R.section("Three. An agent rewrote shared infrastructure that five others "
                          "were reading, and nobody had to approve it"))
    body.append(R.verdict(
        "23:54 · the Macro desk, editing taa/datapull.py",
        "It was right, additive and kept. It could as easily not have been, and no mechanism "
        "in this office would have stopped it."))
    body.append(
        "<p>At <strong>23:54</strong> the Macro desk modified <code>taa/datapull.py</code>, "
        "the shared ingestion layer that every other desk depends on. It added six specific "
        "BEA release dates to the list of macro vintages the study fetches.</p>")
    body.append(
        "<p>Its reasoning was better than the instruction it was given. The office had told "
        "every desk to read macro data at the committee meeting dates. The Macro desk noticed "
        "that a BEA release lands on a Thursday in the middle of a quarter, so a quarter-end "
        "vintage cannot show what a release <em>said on the day it landed</em>, and a desk "
        "asserting &ldquo;this printed at X on date D&rdquo; while reading the vintage from the previous "
        "quarter end is asserting something it has not looked at. It added the release dates so "
        "its own central claim would be checkable. The change was additive, it moved no "
        "existing reading, and it was kept.</p>")
    body.append(
        "<p><strong>The office found out because a linter diagnostic fired on the file.</strong> "
        "There was no lock, no announcement, no review and no approval. An agent with write "
        "access to shared state changed it mid-run while five other agents were reading it. "
        "This time the change improved the study. The same freedom would have allowed a desk to "
        "widen a date range, alter a constant, or change a series definition that every other "
        "desk was consuming, and the first anyone would have known is a number that moved for "
        "no stated reason.</p>")

    body.append('<h3 class="sub">The same hazard, in its smaller and more measurable form</h3>')
    body.append(
        "<p>The point-in-time layer writes an audit line for every historical read. Six agents "
        "ran concurrently and all of them appended to the same file with no coordination. The "
        "result is measurable: of <strong>7,778 log lines</strong>, <strong>2 were "
        "corrupted</strong> by interleaved writes, a rate of 0.026%. Small enough to be "
        "harmless here, and it is the identical failure as the paragraph above with the stakes "
        "turned down. Concurrent agents plus shared mutable state plus no locking gives "
        "corruption at some rate, and the rate is a property of timing rather than of "
        "care.</p>")
    body.append(
        "<p>A related case went the other way and is worth recording as the contrast. When the "
        "credit-spread series turned out to be served for a rolling three-year window only, "
        "four substitute series were added and <strong>the identical note was sent to the "
        "Quantitative and Macro desks at the same moment</strong>. Sending it to one would have "
        "given that desk information the other could not see, and the independence claim on "
        "page one of the report would have been false. Shared infrastructure has to be "
        "distributed symmetrically or the barrier it sits behind is decorative.</p>")

    # ================================================================== close
    body.append('<div class="page-break"></div>')
    body.append(R.section("Two more, recorded without ranking"))
    body.append(R.table(
        ["What happened", "Why it is worth a line"],
        [["Three desks reached the same recommendation by three unrelated routes, without "
          "contact. Capital Markets from published ten-year forecasts against the spending "
          "rule; Systematic from the fundamental law applied to this mandate's breadth and "
          "constraints; Quantitative from out-of-sample R² against the historical mean. "
          "All three point to policy weights.",
          "Convergence between agents that cannot see each other is the strongest evidence in "
          "the study. It is also not free of a shared prior: all three read the same academic "
          "literature, which pushes in the same direction. The report says so rather than "
          "presenting the convergence as three independent votes."],
         ["The Macro desk was told, in writing, that if its computation of the 2022 GDP "
          "revision disagreed with the office's it should <strong>say so rather than reconcile "
          "to it</strong>. It computed (0.93)% and +0.63% independently, matching.",
          "The instruction matters more than the outcome. An agent that quietly adopts the "
          "coordinator's number produces agreement that carries no information. The only way "
          "to know a second computation is a check rather than an echo is to have told it not "
          "to echo before it ran."]],
        align_left={0, 1}, raw=True))

    body.append(R.section("What this run suggests about working this way"))
    body.append(
        "<p>Three things, stated as observations rather than conclusions, because this is one "
        "run of six agents on one mandate.</p>")
    body.append(
        "<p><strong>The errors that mattered were at the seams, not inside any desk.</strong> "
        "Every desk's work was internally correct and internally tested. The failure that would "
        "have destroyed the study was a unit convention at the boundary between two correct "
        "modules, and no test living inside either would ever have found it. Where work is "
        "divided, the tests should be concentrated where the divisions are.</p>")
    body.append(
        "<p><strong>Independence is expensive and it bought one thing.</strong> Running the two "
        "desks blind cost coordination, duplicated data work, and produced a sixteen-point "
        "disagreement that had to be resolved by rejecting both sides. What it bought was one "
        "position, high yield, confirmed by two genuinely different routes, and the certainty "
        "that the agreements elsewhere were duplication rather than confirmation. Without the "
        "barrier the office would have had the same allocation and no way to tell which of "
        "those two things it was looking at.</p>")
    body.append(
        "<p><strong>The disposition of the agents did more work than the controls.</strong> The "
        "Quantitative desk reporting look-aheads in its own analysis, and the Macro desk "
        "improving shared infrastructure so that its own claim could be falsified, are both "
        "behaviours no check in this office requires or could detect the absence of. The "
        "controls caught what they were built to catch. The things that would have been "
        "hardest to catch were volunteered.</p>")

    body.append(R.footer("Agent dynamics", "28 to 29 July 2026",
                         "Ashcroft University Endowment"))
    body.append("</div>")
    return R.document(
        "Ashcroft University Endowment — Agent Dynamics",
        "".join(body))
