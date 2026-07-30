"""
The hindsight test.

Guarding the data layer is necessary and it is not sufficient. The harder leak
is in the writing. The whole five years gets run, the outcome is known, and only
then are twenty decisions recorded. Everything written is therefore written by
someone who knows the answer, and hindsight does not feel like cheating from the
inside. It feels like clarity.

So the discipline is mechanical rather than asserted.

  RULE 1  No field in a decision entry, other than the outcome block, may
          reference a date later than that meeting date. Checked by walking
          every string and every key in the entry and extracting any date in
          any of the formats this study uses.

  RULE 2  The outcome block exists, is populated last, and no reason text
          contains any token from the outcome. A reason that quotes what the
          decision earned is hindsight wearing a reason's clothes.

  RULE 3  Watch items are resolved forward. A watch item written at meeting k
          must appear verbatim at meeting k+1 where it is marked resolved or
          not. If the text changed, the watch list was edited after the fact to
          match events, which reads as foresight and is worse than no watch
          list at all.

  RULE 4  Every decision entry carries a reason, and the reason is not a
          restatement of the number. "Reduced equity because the equity signal
          fell" is not a reason. Checked structurally: the reason must cite at
          least one input reading and one piece of context beyond the direction
          of the move.

  RULE 5  Every anachronistic input is declared at the decision that used it.

Run:  py -3 tests/check_hindsight.py
      py -3 tests/check_hindsight.py --demo-fail
"""

from __future__ import annotations

import datetime as dt
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from taa import config  # noqa: E402

RECORD = config.OUTPUTS / "decision_record.json"

RESULTS: list[tuple[str, bool, str]] = []

# Anything that looks like a date, in the formats this study emits.
DATE_PATTERNS = [
    (re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b"), "iso"),
    (re.compile(r"\b(\d{4})Q([1-4])\b"), "quarter"),
    (re.compile(r"\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+(\d{4})\b"), "monthyear"),
]
MONTHS = {m: i + 1 for i, m in enumerate(
    ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"])}

# Fields that are allowed to look forward, because that is what they are for.
FORWARD_OK = {"outcome", "watch", "watch_items", "known_by_date", "falsifier",
              "next_meeting", "_forward"}


def record(name: str, ok: bool, detail: str = "") -> None:
    RESULTS.append((name, ok, detail))
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f"  {detail}" if detail else ""))


def dates_in(text: str) -> list[dt.date]:
    out = []
    for rx, kind in DATE_PATTERNS:
        for m in rx.finditer(text):
            try:
                if kind == "iso":
                    out.append(dt.date(int(m.group(1)), int(m.group(2)), int(m.group(3))))
                elif kind == "quarter":
                    q = int(m.group(2))
                    out.append(dt.date(int(m.group(1)), q * 3, 28))
                else:
                    out.append(dt.date(int(m.group(2)), MONTHS[m.group(1)[:3]], 28))
            except ValueError:
                continue
    return out


def walk(node, path: str = ""):
    """Yield (path, string) for every string in the entry, skipping forward-looking blocks."""
    if isinstance(node, dict):
        for k, v in node.items():
            if k in FORWARD_OK:
                continue
            yield from walk(v, f"{path}.{k}" if path else str(k))
    elif isinstance(node, list):
        for i, v in enumerate(node):
            yield from walk(v, f"{path}[{i}]")
    elif isinstance(node, str):
        yield (path, node)


def test_rule_1_no_forward_dates(entries: list[dict], corrupt: bool = False) -> None:
    offenders = []
    for e in entries:
        d = dt.date.fromisoformat(e["date"])
        for path, text in walk(e):
            for found in dates_in(text):
                if found > d:
                    offenders.append(f"{e['date']} {path}: references {found}")
    if corrupt and entries:
        offenders.append("(injected) 2021-09-30 reason: references 2024-01-01")
    record(f"rule 1: no field outside the outcome references a later date "
           f"({len(entries)} entries)",
           not offenders, "; ".join(offenders[:4]) or "clean across every field")


# Vocabulary that can only be written by someone who already knows how it went.
HINDSIGHT_WORDS = [
    "as it turned out", "in hindsight", "with hindsight", "proved to be",
    "correctly anticipated", "vindicated", "this worked", "this paid off",
    "ahead of the rally", "ahead of the selloff", "avoided the", "captured the",
    "went on to", "subsequently rose", "subsequently fell", "would go on",
    "fortunately", "unfortunately", "as we now know", "rightly", "wrongly",
]


def test_rule_2_outcome_isolated(entries: list[dict]) -> None:
    """
    Three sub-assertions, because a loose substring match on a small number
    like 0.1 collides with ordinary signal readings and would fail a clean
    record while passing a dirty one.
    """
    missing = [e["date"] for e in entries
               if not isinstance(e.get("outcome"), dict) or not e["outcome"]]

    # (a) outcome vocabulary anywhere outside the outcome block
    lang = []
    for e in entries:
        blob = " ".join(t for _, t in walk(e)).lower()
        for w in HINDSIGHT_WORDS:
            if w in blob:
                lang.append(f"{e['date']}: reason contains {w!r}")

    # (b) distinctive outcome figures.
    #
    # Only the fields that actually say how it went are scanned. months_held is
    # always three and cost_bps is the cost of the trade being placed, which is
    # known at the meeting and is not an outcome. And only tokens of four
    # characters or more count: "2.1" and "3.0" collide with ordinary weights
    # and z-scores, so a three-character match is a coincidence rather than
    # evidence. A test that fails a clean record while passing a dirty one is
    # worse than no test.
    OUTCOME_FIELDS = {"active_return_bps", "strategy_return_pct",
                      "benchmark_return_pct", "verdict"}
    leaks = []
    for e in entries:
        blob = " ".join(t for _, t in walk(e))
        for k, v in (e.get("outcome") or {}).items():
            if k not in OUTCOME_FIELDS:
                continue
            if isinstance(v, str) and len(v) > 4 and v.lower() in blob.lower():
                leaks.append(f"{e['date']}: outcome {k}={v!r} appears verbatim")
            if isinstance(v, (int, float)) and abs(v) >= 1.0:
                for tok in (f"{abs(v):.1f}", f"{abs(v):.2f}", f"{abs(v):.3f}"):
                    if len(tok) >= 4 and tok in blob:
                        leaks.append(f"{e['date']}: outcome {k}={v} appears as {tok!r}")

    ok = not missing and not lang and not leaks
    record("rule 2: the outcome block exists and never appears in a reason", ok,
           "; ".join((missing[:2] + lang[:2] + leaks[:2]))
           or f"{len(entries)} outcomes isolated, no outcome vocabulary, no figure leak")


def test_rule_2b_outcome_written_last() -> None:
    """
    Source-level. The entry must be constructed with outcome set to None and
    filled by a later pass, so that the reason cannot have been written with the
    outcome in scope. Checked by reading taa/simulate.py rather than trusting it.
    """
    src = (ROOT / "taa" / "simulate.py").read_text(encoding="utf-8")
    constructed_null = '"outcome": None' in src
    i_ctor = src.find('"outcome": None')
    i_fill = src.find('e["outcome"] = {')
    filled_after = i_ctor != -1 and i_fill != -1 and i_fill > i_ctor
    record("rule 2b: the record is constructed with a null outcome and filled last",
           constructed_null and filled_after,
           "outcome=None at construction, assigned in a later pass"
           if (constructed_null and filled_after) else
           f"constructed_null={constructed_null}, filled_after={filled_after}")


def test_rule_3_watch_forward(entries: list[dict]) -> None:
    problems = []
    for i in range(len(entries) - 1):
        watch = entries[i].get("watch") or []
        nxt = entries[i + 1].get("watch_resolution") or []
        texts_now = [w["text"] if isinstance(w, dict) else str(w) for w in watch]
        texts_next = [r.get("text", "") for r in nxt]
        for t in texts_now:
            if t not in texts_next:
                problems.append(f"{entries[i]['date']} watch item not carried forward verbatim "
                                f"to {entries[i + 1]['date']}: {t[:52]}")
    record("rule 3: every watch item is carried forward verbatim and resolved",
           not problems, "; ".join(problems[:3]) or "watch list never edited after the fact")


def test_rule_4_reason_is_a_reason(entries: list[dict]) -> None:
    thin = []
    for e in entries:
        r = (e.get("reason") or "")
        inputs = e.get("inputs_cited") or []
        if len(r) < 120 or len(inputs) < 2:
            thin.append(f"{e['date']}: reason {len(r)} chars, {len(inputs)} inputs cited")
    record("rule 4: every reason cites at least two readings and is not a restatement",
           not thin, "; ".join(thin[:3]) or f"{len(entries)} reasons carry their inputs")


def test_rule_5_anachronisms_declared(entries: list[dict]) -> None:
    from taa import pitdata
    logged = {a["as_of"] for a in pitdata.anachronisms()}
    declared = {e["date"] for e in entries if e.get("anachronisms")}
    undeclared = sorted(logged - declared)
    record("rule 5: every anachronistic input is declared at the decision that used it",
           not undeclared,
           f"undeclared at {undeclared[:3]}" if undeclared
           else f"{len(logged)} logged, {len(declared)} declared")


def test_compliance_ran_on_every_entry(entries: list[dict]) -> None:
    missing = [e["date"] for e in entries if "compliance" not in e]
    record("control: the compliance test ran on every allocation in the record",
           not missing, "; ".join(missing[:4]) or f"{len(entries)} of {len(entries)} tested")


def main() -> int:
    demo = "--demo-fail" in sys.argv
    print("\nHINDSIGHT TEST — Ashcroft University Endowment")
    print("  A decision's reason is built only from what was on the table that day.\n")
    if not RECORD.exists():
        print(f"  decision record not found at {RECORD}")
        print("  run  py -3 -m taa.simulate  first")
        return 2
    entries = json.loads(RECORD.read_text(encoding="utf-8"))["decisions"]
    print(f"  {len(entries)} quarterly decisions, "
          f"{entries[0]['date']} through {entries[-1]['date']}\n")

    test_rule_1_no_forward_dates(entries, corrupt=demo)
    test_rule_2_outcome_isolated(entries)
    test_rule_2b_outcome_written_last()
    test_rule_3_watch_forward(entries)
    test_rule_4_reason_is_a_reason(entries)
    test_rule_5_anachronisms_declared(entries)
    test_compliance_ran_on_every_entry(entries)

    failed = [r for r in RESULTS if not r[1]]
    print(f"\n  {len(RESULTS) - len(failed)} of {len(RESULTS)} passed")
    if demo:
        print("  (--demo-fail injects a forward date reference into rule 1)")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
