"""
The figure-drift check.

Prose is written once and data is regenerated every run. When a desk redelivers,
a number in a sentence can quietly stop matching the number in the file it came
from, and nothing in the study notices, because both documents build cleanly and
both look right.

That happened in this build. The Quantitative desk's final write moved Treasury
duration from 21.8% to 22.0%, and four sentences across three documents went on
saying the two desks were 16.3 points apart when the files said 16.5. It was
found by hand, which is not a method.

So the headline figures are extracted from the rendered HTML and compared to the
JSON they are supposed to come from. Any sentence that has drifted fails here.

Run:  py -3 tests/check_figures.py
      py -3 tests/check_figures.py --demo-fail
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from taa import config  # noqa: E402

RESULTS: list[tuple[str, bool, str]] = []


def record(name: str, ok: bool, detail: str = "") -> None:
    RESULTS.append((name, ok, detail))
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f"  {detail}" if detail else ""))


def load(p: str) -> dict:
    return json.loads((config.OUTPUTS / p).read_text(encoding="utf-8"))


def text_of(p: Path, prose_only: bool = False) -> str:
    """
    prose_only strips tables and SVG before extracting text. A figure inside a
    table cell is data; the same digits inside a sentence are a claim. Checks
    about what the office *says* must read only the sentences, or they trip on
    a neighbouring row label and fail a clean document.
    """
    h = p.read_text(encoding="utf-8")
    h = re.sub(r"<script.*?</script>", " ", h, flags=re.S)
    h = re.sub(r"<style.*?</style>", " ", h, flags=re.S)
    if prose_only:
        h = re.sub(r"<table.*?</table>", " ", h, flags=re.S)
        h = re.sub(r"<svg.*?</svg>", " ", h, flags=re.S)
    return re.sub(r"<[^>]+>", " ", h)


def main() -> int:
    demo = "--demo-fail" in sys.argv
    print("\nFIGURE-DRIFT CHECK")
    print("  Every headline number in the prose, against the file it came from.\n")

    paths = list((ROOT / "report").glob("*.html")) + list(config.OUTPUTS.glob("*.html"))
    docs = {p.name: text_of(p) for p in paths}
    allprose = " ".join(docs.values())
    prose = " ".join(text_of(p, prose_only=True) for p in paths)
    if demo:
        allprose += " the two desks disagreed by 99.9 percentage points on Treasury duration "
        prose += " the two desks disagreed by 99.9 percentage points on Treasury duration "

    rec = load("decision_record.json")
    cme = load("cme.json")
    q = load("quant/allocation.json")["constrained"]
    m = load("macro/allocation.json")["weights"]
    sc = rec["scorecard"]
    five = rec["summary"]

    # ---- 1. the duration disagreement, the figure that actually drifted
    qa = (q["ust_duration"] - config.POLICY["ust_duration"]) * 100
    ma = (m["ust_duration"] - config.POLICY["ust_duration"]) * 100
    gap = qa - ma
    # Only sentences that are about DURATION. The report also says the desks
    # "disagreed by 5.0 points on commodities", which is correct and is not a
    # claim about duration; an unscoped pattern reads it as one and fails a
    # document that is right.
    wrong = []
    for mt in re.finditer(r"(?:gap of|disagreed by)\s+(\d{1,3}\.\d)\s*(?:percentage )?p", prose):
        # What the figure is followed by identifies what it is a claim about.
        # Looking backwards is unreliable: "...by 16.5 percentage points [on
        # duration]... They disagreed by 5.0 points on commodities" puts the
        # word "duration" behind BOTH numbers.
        after = prose[mt.end():mt.end() + 60].lower()
        before = prose[max(0, mt.start() - 90):mt.start()].lower()
        other = ("commodit", "cash", "t-bill", "equity", "high yield",
                 "investment grade", "real estate", "emerging")
        if any(o in after for o in other):
            continue
        if "duration" not in after and "duration" not in before:
            continue
        if abs(float(mt.group(1)) - gap) > 0.05:
            wrong.append(mt.group(1))
    wrong = sorted(set(wrong))
    record("duration disagreement in prose matches the desk files",
           not wrong, f"files say {gap:.1f}pp"
           + (f"; prose also says {wrong}" if wrong else "; no other value appears"))

    # ---- 2. the capital markets headline
    er = cme["policy_expected_return"]["adopted"] * 100
    record("policy expected return appears and matches outputs/cme.json",
           f"{er:.2f}%" in allprose, f"{er:.2f}%")
    record("gap to the required return matches outputs/cme.json",
           f"{abs(cme['gap_bps']):.0f}" in allprose, f"({abs(cme['gap_bps']):.0f})bps")

    # ---- 3. the scorecard
    for k, lbl in (("helped", "helped"), ("hurt", "hurt")):
        record(f"scorecard {lbl} count matches the record",
               re.search(rf"\b{sc[k]}\b\s+{lbl}", allprose) is not None, f"{sc[k]} {lbl}")

    # ---- 4. drawdowns
    dd_b = abs(five["benchmark"]["max_drawdown"]) * 100
    dd_p = abs(five["portfolio"]["max_drawdown"]) * 100
    record("benchmark drawdown in prose matches the record",
           f"({dd_b:.2f})" in allprose, f"({dd_b:.2f})%")
    record("fund drawdown in prose matches the record",
           f"({dd_p:.2f})" in allprose, f"({dd_p:.2f})%")

    # ---- 5. no stale figure survives IN THE SENTENCES THAT QUOTE IT
    #
    # Scoped to context rather than to the bare digits. An unscoped search bans
    # "21.8" everywhere and then trips on a genuine 21.8% portfolio weight and a
    # genuine (9.8)% drawdown reading, which is a test failing clean documents
    # while a real drift elsewhere would still pass. The figures below are only
    # wrong when they appear as a claim about the two desks' duration positions.
    banned = {"16.3": gap, "9.8": qa, "21.8": q["ust_duration"] * 100}
    hits = []
    for k, v in banned.items():
        if abs(float(k) - v) <= 0.05:
            continue
        for mt in re.finditer(rf"(?<![\d.]){re.escape(k)}(?![\d])", prose):
            ctx = prose[max(0, mt.start() - 150):mt.start() + 150].lower()
            if ("duration" in ctx and ("desk" in ctx or "overweight" in ctx
                                       or "apart" in ctx or "gap" in ctx)):
                hits.append(f"{k} quoted as a duration claim (files say {v:.1f})")
                break
    record("no superseded duration figure survives in a sentence that claims it",
           not hits, "; ".join(hits) or "clean; bare occurrences elsewhere are real data")

    # ---- 6. the two supplementary notes exist and are linked
    have = {"agent_dynamics.html", "top_decisions.html"} <= set(docs)
    linked = "agent_dynamics.html" in (ROOT / "report" / "annual_report.html").read_text(
        encoding="utf-8")
    record("both supplementary notes exist and the report links them", have and linked,
           f"{sorted(set(docs))}")

    failed = [r for r in RESULTS if not r[1]]
    print(f"\n  {len(RESULTS) - len(failed)} of {len(RESULTS)} passed")
    if demo:
        print("  (--demo-fail injects a stale 99.9pp disagreement into the prose)")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
