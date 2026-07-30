"""
tests/check_macro.py — the Macro desk's own check. It can fail.

Run:  py -3 tests/check_macro.py
      py -3 tests/check_macro.py --demo-fail

Four assertions, in the order they would embarrass the desk:

  1. LOOK-AHEAD. At each of the twenty meeting dates, walk every entry in the
     `inputs` dict returned by regime_as_of and assert no observation carries a
     date after the meeting. This is the one the CIO runs. It walks the structure
     rather than trusting the module, because a docstring is not a control.

  2. THE 2022 Q2 DEMONSTRATION. Assert the sign actually changes between the
     July-2022 vintage and the current one, and fail loudly if it does not. If it
     does not, either the point-in-time wall is broken or the claim the desk has
     put in front of the trustees is wrong, and the desk would rather find out
     here than in the meeting.

  3. FALSIFIERS. Every entry in deviations.json carries a non-empty falsifier and
     a known_by_date in the future relative to the report date. IPS 4.4: a view
     that cannot be shown wrong does not enter a recommendation, and a falsifier
     whose date has already passed is a fact, not a test.

  4. MANDATE. The allocation respects every config.RANGE and config.SLEEVE_RANGE
     bound at all twenty dates, is long only, sums to one, and carries no active
     position smaller than config.MIN_TRADE_PP.

--demo-fail corrupts each check in turn in memory and asserts it goes red, which
is the only evidence that a green run means anything.
"""

from __future__ import annotations

import datetime as _dt
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from taa import config, regime  # noqa: E402

MACRO = config.OUTPUTS / "macro"
FAILURES: list[str] = []
CHECKS = 0


def ok(cond: bool, msg: str) -> bool:
    global CHECKS
    CHECKS += 1
    if not cond:
        FAILURES.append(msg)
    return bool(cond)


def _walk_dates(node, out: list[tuple[str, str]], trail: str = "") -> None:
    """Collect every value that parses as a date, with the path that led to it."""
    if isinstance(node, dict):
        for k, v in node.items():
            _walk_dates(v, out, f"{trail}.{k}" if trail else str(k))
    elif isinstance(node, (list, tuple)):
        for i, v in enumerate(node):
            _walk_dates(v, out, f"{trail}[{i}]")
    elif isinstance(node, str) and len(node) >= 10:
        try:
            _dt.date.fromisoformat(node[:10])
        except ValueError:
            return
        out.append((trail, node[:10]))
    elif isinstance(node, (_dt.date, _dt.datetime)):
        out.append((trail, str(node)[:10]))


# --------------------------------------------------------------------------
def check_lookahead(path: list[dict]) -> None:
    print("\n1. LOOK-AHEAD  no input dated after its own meeting date")
    worst = None
    for e in path:
        meet = _dt.date.fromisoformat(e["date"])
        found: list[tuple[str, str]] = []
        _walk_dates(e["regime"]["inputs"], found)
        ok(len(found) >= 20, f"{e['date']}: only {len(found)} dated fields found in inputs; "
                             f"a read with nothing to check is not a read that passed")
        bad = [(p, d) for p, d in found if _dt.date.fromisoformat(d) > meet]
        ok(not bad, f"{e['date']}: {len(bad)} input(s) dated after the meeting: {bad[:4]}")
        lag = max((meet - _dt.date.fromisoformat(d)).days for _, d in found) if found else 0
        newest = min((meet - _dt.date.fromisoformat(d)).days for _, d in found) if found else 0
        if worst is None or newest < worst[1]:
            worst = (e["date"], newest)
        print(f"   {e['date']}  {len(found):3d} dated fields  "
              f"newest {newest:2d}d before, oldest {lag:4d}d before  "
              f"{'ok' if not bad else 'LOOK-AHEAD'}")
    if worst:
        print(f"   tightest margin: {worst[0]}, newest observation {worst[1]} days "
              f"before the meeting")


def check_gdp_demo(demo: dict) -> None:
    print("\n2. 2022 Q2 GDP VINTAGE DEMONSTRATION")
    first = demo["as_first_published"]["q2_2022_saar_pct"]
    now = demo["as_it_reads_now"]["q2_2022_saar_pct"]
    print(f"   2022-07-28 vintage (BEA advance estimate) {first:+.4f}% annualised")
    print(f"   {demo['as_it_reads_now']['vintage']} vintage (today)          {now:+.4f}% annualised")
    print(f"   revision {demo['revision_pp']:+.4f}pp, sign crossed on the "
          f"{demo['sign_crossed_on_vintage']} vintage after {demo['days_wrong']} days")
    print(f"   two consecutive negative quarters: "
          f"{demo['as_first_published']['two_consecutive_negative_quarters']} then, "
          f"{demo['as_it_reads_now']['two_consecutive_negative_quarters']} now")

    ok(first is not None and now is not None,
       "2022 Q2 GDP is missing on one of the two vintages")
    ok(first is not None and first < 0,
       f"2022 Q2 does NOT read as a contraction on the 2022-07-28 vintage (got {first}). "
       f"Either the vintage cache is serving the wrong file or the wall is broken")
    ok(now is not None and now > 0,
       f"2022 Q2 does NOT read positive on the current vintage (got {now}). "
       f"The claim put to the trustees is wrong and must be withdrawn")
    ok(demo["verdict"] == "CONFIRMED", f"verdict is {demo['verdict']}, not CONFIRMED")
    ok(demo["as_first_published"]["two_consecutive_negative_quarters"] is True,
       "the two-negative-quarters reading was NOT true on the 2022-07-28 vintage")
    ok(demo["as_it_reads_now"]["two_consecutive_negative_quarters"] is False,
       "the two-negative-quarters reading is still true on the current vintage")
    ok(demo["sign_crossed_on_vintage"] is not None and demo["days_wrong"] is not None
       and demo["days_wrong"] > 365,
       "the revision crossed zero within a year, so the 'more than two years' claim is wrong")


def check_falsifiers(devs: list[dict]) -> None:
    print("\n3. FALSIFIERS  every deviation can be shown wrong, by a date still ahead")
    ok(len(devs) > 0, "deviations.json is empty; a desk with no deviation has no view")
    for d in devs:
        f = (d.get("falsifier") or "").strip()
        kb = d.get("known_by_date")
        good_f = ok(len(f) > 0, f"{d.get('id')}: empty falsifier")
        good_u = ok(bool((d.get('consensus_source_url') or '').startswith('http')),
                    f"{d.get('id')}: consensus_source_url is not a URL")
        good_d = False
        try:
            kd = _dt.date.fromisoformat(str(kb))
            good_d = ok(kd > config.REPORT_DATE,
                        f"{d.get('id')}: known_by_date {kb} is not after "
                        f"{config.REPORT_DATE}; a date already passed is not a test")
        except (TypeError, ValueError):
            ok(False, f"{d.get('id')}: known_by_date {kb!r} is not a date")
        ok(isinstance(d.get("position_bps"), (int, float)) and d["position_bps"] > 0,
           f"{d.get('id')}: position_bps missing or not positive")
        print(f"   {d.get('id')} {d.get('line'):14s} {str(kb):12s} "
              f"{d.get('position_bps'):4}bps  "
              f"{'ok' if (good_f and good_d and good_u) else 'FAIL'}  {f[:64]}...")


def check_mandate(path: list[dict]) -> None:
    print("\n4. MANDATE  ranges, sleeves, long only, sums to one, minimum trade")
    for e in path:
        w = e["weights"]
        for k in config.LINES:
            lo, hi = config.RANGE[k]
            ok(lo - 1e-9 <= w[k] <= hi + 1e-9,
               f"{e['date']}: {k} at {w[k]:.4f} outside RANGE {lo}-{hi}")
            ok(w[k] >= -1e-12, f"{e['date']}: {k} is short at {w[k]}")
            act = abs(w[k] - config.POLICY[k]) * 100
            ok(act < 1e-7 or act >= config.MIN_TRADE_PP - 1e-9,
               f"{e['date']}: {k} active {act:.3f}pp is below MIN_TRADE_PP "
               f"{config.MIN_TRADE_PP}")
        for sl, (lo, hi) in config.SLEEVE_RANGE.items():
            t = sum(w[k] for k in config.LINES if config.SLEEVE[k] == sl)
            ok(lo - 1e-9 <= t <= hi + 1e-9,
               f"{e['date']}: sleeve {sl} at {t:.4f} outside {lo}-{hi}")
        ok(abs(sum(w.values()) - 1.0) < 1e-9,
           f"{e['date']}: weights sum to {sum(w.values())}, not 1")
    eq = [sum(e["weights"][k] for k in config.LINES if config.SLEEVE[k] == "equity")
          for e in path]
    print(f"   {len(path)} dates, all lines inside RANGE, all sleeves inside SLEEVE_RANGE")
    print(f"   equity sleeve spans {min(eq):.1%} to {max(eq):.1%} against a 60%-80% band")
    print(f"   every active position is zero or at least {config.MIN_TRADE_PP}pp")


# --------------------------------------------------------------------------
def demo_fail() -> int:
    """Corrupt each check in turn and assert it goes red."""
    print("=" * 78)
    print("DEMO-FAIL  each check is fed a corrupted input and must reject it")
    print("=" * 78)
    global FAILURES
    results = []

    path = regime.regime_path()

    FAILURES = []
    bad = json.loads(json.dumps(path, default=str))
    bad[3]["regime"]["inputs"]["core_pce_yoy"]["obs_date"] = "2027-01-01"
    check_lookahead(bad)
    results.append(("look-ahead, an input dated after its meeting", bool(FAILURES)))

    FAILURES = []
    demo = regime.gdp_vintage_demonstration()
    demo["as_first_published"]["q2_2022_saar_pct"] = 1.23
    demo["as_first_published"]["two_consecutive_negative_quarters"] = False
    check_gdp_demo(demo)
    results.append(("2022 Q2 sign change absent", bool(FAILURES)))

    FAILURES = []
    check_falsifiers([{"id": "X", "line": "us_equity", "falsifier": "  ",
                       "known_by_date": "2020-01-01", "position_bps": 0,
                       "consensus_source_url": "n/a"}])
    results.append(("empty falsifier, past date, no URL", bool(FAILURES)))

    FAILURES = []
    bad = json.loads(json.dumps(path, default=str))
    bad[0]["weights"]["us_equity"] = 0.60
    bad[0]["weights"]["cash"] = -0.02
    check_mandate(bad)
    results.append(("weights outside RANGE and short", bool(FAILURES)))

    print("\n" + "=" * 78)
    for name, caught in results:
        print(f"  {'CAUGHT ' if caught else 'MISSED '} {name}")
    all_caught = all(c for _, c in results)
    print("=" * 78)
    print(f"DEMO-FAIL {'PASS' if all_caught else 'FAIL'} "
          f"({sum(c for _, c in results)}/{len(results)} corruptions rejected)")
    return 0 if all_caught else 1


def main(argv: list[str]) -> int:
    if "--demo-fail" in argv:
        return demo_fail()

    print("=" * 78)
    print("MACRO DESK CHECK — Ashcroft University Endowment")
    print(f"window {config.WINDOW_START} .. {config.WINDOW_END}   "
          f"report date {config.REPORT_DATE}   {len(config.meeting_dates())} meetings")
    print("=" * 78)

    path = regime.regime_path()
    check_lookahead(path)
    check_gdp_demo(regime.gdp_vintage_demonstration())

    devfile = MACRO / "deviations.json"
    if not devfile.exists():
        FAILURES.append(f"{devfile} does not exist")
        print("\n3. FALSIFIERS  deviations.json missing")
    else:
        check_falsifiers(json.loads(devfile.read_text(encoding="utf-8")))

    check_mandate(path)

    print("\n" + "=" * 78)
    if FAILURES:
        print(f"FAIL  {len(FAILURES)} of {CHECKS} assertions failed")
        for f in FAILURES[:25]:
            print(f"   - {f}")
        print("=" * 78)
        return 1
    print(f"PASS  {CHECKS} assertions, 0 failures")
    print("=" * 78)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
