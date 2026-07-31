"""
The determinism check.

The study's headline claim is that you can clone the folder, run the commands in
the README, and get the same numbers. That claim was true and unverifiable at the
same time: every value reproduced exactly, but `outputs/decision_record.json`
came back byte-different from a clean rerun, so a reader had no cheap way to tell
a real difference from noise. A 66-line diff that means nothing is worse than no
diff at all, because it trains the reader to ignore the diff.

The cause was a dict built by iterating a `set` of line keys in taa.costs. Python
randomises string hashing per process, so the same values serialised in a
different order on every run. It is fixed by sorting, and this check exists so it
cannot come back quietly.

Two things are asserted, and they are deliberately held to different standards:

  1. Two fresh runs under DIFFERENT hash seeds produce byte-identical records.
     Exact, no tolerance. One process cannot catch this on its own: within a
     single process the seed is fixed, so an in-process double-run would pass
     while the defect was live.

  2. A fresh run matches the record committed to the repository, to a numeric
     tolerance, with key order still compared exactly. This is the reproduction
     claim itself, tested rather than asserted.

The second is not byte-exact for a reason that is a fact about hardware rather
than about this study. Windows and Linux link different math libraries and
different BLAS backends, so the last one or two bits of a float64 are not
portable. The committed record was generated on Windows and a Linux run of the
same code reproduces every decision, every weight and every rounded figure while
landing about 1e-15 away on the unrounded signal readings. Asserting byte
equality there would fail honest work on the wrong machine, which is how a check
gets switched off by someone right to switch it off. The gate is at 1e-9 and the
observed deviation is printed, so drift is visible rather than hidden.

Both runs write to their own temporary directory via TAA_OUTPUT_DIR, so the
check never touches the published outputs.

Run:  py -3 tests/check_determinism.py
      py -3 tests/check_determinism.py --demo-fail
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RECORD = "decision_record.json"

# Written fresh on every run by design, so it can never match. Nothing else in
# the record is permitted to vary.
VOLATILE = {"generated"}


def _strip(obj):
    """Drop the fields that are supposed to differ between runs."""
    if isinstance(obj, dict):
        return {k: _strip(v) for k, v in obj.items() if k not in VOLATILE}
    if isinstance(obj, list):
        return [_strip(v) for v in obj]
    return obj


def _canonical(path: Path) -> str:
    """The record as text, with volatile fields removed and order preserved.

    Order is deliberately NOT normalised here. Key order is the thing under
    test, so sorting before comparing would defeat the check entirely.
    """
    return json.dumps(_strip(json.loads(path.read_text(encoding="utf-8"))),
                      indent=2, default=str)


# Float64 carries about 16 significant digits, and the last one or two are not
# portable: Windows and Linux link different math libraries and different BLAS
# backends, so exp, log and every matrix operation can land a unit or two apart
# in the last place. Accumulated through a pipeline that shrinks a covariance
# matrix and solves a constrained optimisation, that noise stays around 1e-15
# relative. This gate sits six orders of magnitude above it, so last-bit drift
# passes and any change with a real cause does not. The observed maximum is
# printed either way, so the number is visible instead of hidden by the gate.
NUMERIC_TOL = 1e-9


def _compare(expected, actual, path="") -> tuple[float, list[str]]:
    """Compare two decoded records. Returns (max relative deviation, mismatches).

    Key order is compared exactly, because that is the defect this file was
    written for. Numbers are compared to NUMERIC_TOL. Everything else must be
    equal outright.
    """
    worst, bad = 0.0, []

    if isinstance(expected, dict):
        if not isinstance(actual, dict):
            return worst, [f"{path}: expected an object, got {type(actual).__name__}"]
        if list(expected) != list(actual):
            missing = [k for k in expected if k not in actual]
            extra = [k for k in actual if k not in expected]
            if missing or extra:
                bad.append(f"{path}: keys differ (missing {missing}, extra {extra})")
            else:
                bad.append(f"{path}: same keys in a different order, which breaks "
                           f"byte-stability")
            return worst, bad
        for k in expected:
            w, b = _compare(expected[k], actual[k], f"{path}.{k}" if path else k)
            worst = max(worst, w)
            bad += b
        return worst, bad

    if isinstance(expected, list):
        if not isinstance(actual, list) or len(expected) != len(actual):
            n = len(actual) if isinstance(actual, list) else "n/a"
            return worst, [f"{path}: list length {len(expected)} became {n}"]
        for i, (x, y) in enumerate(zip(expected, actual)):
            w, b = _compare(x, y, f"{path}[{i}]")
            worst = max(worst, w)
            bad += b
        return worst, bad

    if isinstance(expected, bool) or isinstance(actual, bool):
        return worst, ([] if expected == actual
                       else [f"{path}: {expected!r} became {actual!r}"])

    if isinstance(expected, (int, float)) and isinstance(actual, (int, float)):
        if expected == actual:
            return worst, bad
        scale = max(abs(expected), abs(actual))
        rel = abs(expected - actual) / scale if scale else abs(expected - actual)
        if rel > NUMERIC_TOL:
            bad.append(f"{path}: {expected!r} became {actual!r} "
                       f"(relative {rel:.2e}, gate {NUMERIC_TOL:.0e})")
        return rel, bad

    return worst, ([] if expected == actual
                   else [f"{path}: {expected!r} became {actual!r}"])


def _report_diff(expected: str, actual: str, limit: int = 6) -> None:
    """Show the first few differing lines, so a failure names what moved.

    A check that only says "these differ" sends the reader back to the shell to
    do the work the check already did. The distinction that matters here is
    whether a value moved or only its position did, and the lines say which.
    """
    exp, act = expected.splitlines(), actual.splitlines()
    if len(exp) != len(act):
        print(f"         line counts differ: committed {len(exp)}, "
              f"this run {len(act)}")
    shown = 0
    for n, (x, y) in enumerate(zip(exp, act), 1):
        if x == y:
            continue
        print(f"         line {n}\n"
              f"           committed: {x.strip()[:110]}\n"
              f"           this run : {y.strip()[:110]}")
        shown += 1
        if shown >= limit:
            break
    total = sum(1 for x, y in zip(exp, act) if x != y)
    if total > shown:
        print(f"         ... and {total - shown} more differing lines")


def _run(seed: int, out_dir: Path) -> Path:
    """Run the simulation in its own process with a fixed hash seed."""
    env = dict(os.environ)
    env["PYTHONHASHSEED"] = str(seed)
    env["TAA_OUTPUT_DIR"] = str(out_dir)
    proc = subprocess.run([sys.executable, "-m", "taa.simulate"],
                          cwd=ROOT, env=env, capture_output=True, text=True)
    if proc.returncode != 0:
        print(proc.stdout[-2000:])
        print(proc.stderr[-2000:], file=sys.stderr)
        raise SystemExit(f"taa.simulate failed under PYTHONHASHSEED={seed}")
    record = out_dir / RECORD
    if not record.exists():
        raise SystemExit(f"no {RECORD} written under PYTHONHASHSEED={seed}")
    return record


def _shuffle_one_dict(path: Path) -> None:
    """Reverse the key order of one nested dict, changing no value.

    This is what the defect looked like: identical numbers, different order. If
    the check cannot see this, it cannot see the thing it was written for.
    """
    doc = json.loads(path.read_text(encoding="utf-8"))
    entries = doc["decisions"] if "decisions" in doc else next(
        v for v in doc.values() if isinstance(v, list) and v)
    for entry in entries:
        for key, value in entry.items():
            if isinstance(value, dict) and len(value) > 1:
                entry[key] = dict(reversed(list(value.items())))
                path.write_text(json.dumps(doc, indent=2, default=str),
                                encoding="utf-8")
                print(f"*** --demo-fail: reversed key order of '{key}' in one "
                      f"decision. Every value is unchanged.")
                return
    raise SystemExit("--demo-fail found no nested dict to reorder")


def main(demo: bool = False) -> int:
    print("\nDETERMINISM  the record must be byte-stable across runs\n")
    print("  running taa.simulate twice, in separate processes, with different")
    print("  hash seeds. This takes a few minutes.\n")

    failures = []
    drift = 0.0

    with tempfile.TemporaryDirectory() as tmp:
        a_dir, b_dir = Path(tmp) / "a", Path(tmp) / "b"
        a_dir.mkdir()
        b_dir.mkdir()

        a = _run(0, a_dir)
        print("  [ok] run 1 complete  PYTHONHASHSEED=0")
        b = _run(12345, b_dir)
        print("  [ok] run 2 complete  PYTHONHASHSEED=12345\n")

        if demo:
            _shuffle_one_dict(b)
            print()

        text_a, text_b = _canonical(a), _canonical(b)

        if text_a == text_b:
            print("  [PASS] two runs under different hash seeds are identical")
        else:
            diff = sum(1 for x, y in zip(text_a.splitlines(),
                                         text_b.splitlines()) if x != y)
            failures.append("two runs of the same code produced different "
                            f"records ({diff} lines differ)")
            print(f"  [FAIL] two runs differ on {diff} lines")
            print("         values may be identical and only the order moved. "
                  "That still breaks\n         reproduction, because a reader "
                  "cannot tell the two cases apart.")
            _report_diff(text_a, text_b)

        published = ROOT / "outputs" / RECORD
        if not published.exists():
            failures.append(f"outputs/{RECORD} is missing from the repository")
            print(f"  [FAIL] outputs/{RECORD} not found")
        else:
            want = _strip(json.loads(published.read_text(encoding="utf-8")))
            got = _strip(json.loads(a.read_text(encoding="utf-8")))
            worst, bad = _compare(want, got)
            drift = worst
            if bad:
                failures.append("a fresh run does not match the committed record")
                print("  [FAIL] a fresh run does not match the committed record")
                for line in bad[:8]:
                    print(f"         {line}")
                if len(bad) > 8:
                    print(f"         ... and {len(bad) - 8} more")
            elif worst == 0.0:
                print("  [PASS] a fresh run matches the committed record exactly")
            else:
                print("  [PASS] a fresh run matches the committed record")
                print(f"         largest relative deviation {worst:.2e}, "
                      f"gate {NUMERIC_TOL:.0e}")
                print("         last-bit float noise. The committed record was "
                      "generated on Windows;\n         a different platform "
                      "links a different libm and will not match bit for bit.")

    print()
    if failures:
        for f in failures:
            print(f"  FAILED: {f}")
        print("\n  2 checks, "
              f"{2 - len(failures)} passed, {len(failures)} failed\n")
        return 1

    if drift == 0.0:
        print("  2 of 2 passed. The record reproduces byte for byte.\n")
    else:
        print(f"  2 of 2 passed. The record reproduces to {drift:.0e} relative, "
              f"which is\n  last-bit float noise from a different platform, not "
              f"a different answer.\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(demo="--demo-fail" in sys.argv))
