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

Two things are asserted, and the second is the one that matters:

  1. Two fresh runs under DIFFERENT hash seeds produce byte-identical records.
     One process cannot catch this on its own: within a single process the seed
     is fixed, so an in-process double-run would pass while the defect was live.

  2. A fresh run matches the record committed to the repository. This is the
     reproduction claim itself, tested rather than asserted.

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

        published = ROOT / "outputs" / RECORD
        if not published.exists():
            failures.append(f"outputs/{RECORD} is missing from the repository")
            print(f"  [FAIL] outputs/{RECORD} not found")
        elif _canonical(published) == text_a:
            print("  [PASS] a fresh run matches the record committed here")
        else:
            failures.append("a fresh run does not match the committed record")
            print("  [FAIL] a fresh run does not match the committed record")
            print("         either the code moved and the record was not "
                  "regenerated, or the\n         record was edited by hand.")

    print()
    if failures:
        for f in failures:
            print(f"  FAILED: {f}")
        print("\n  2 checks, "
              f"{2 - len(failures)} passed, {len(failures)} failed\n")
        return 1

    print("  2 of 2 passed. The record reproduces byte for byte.\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(demo="--demo-fail" in sys.argv))
