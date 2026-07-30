"""
The mutation test. Breaks the wall on purpose and demands the suite go red.

A guard nobody has watched fail is a guard nobody has tested. If deleting the
check leaves tests/test_lookahead.py green, then the tests were never checking
anything, and this file is what finds that out.

Method
------
For each mutation: copy the package to a temporary sandbox, apply a single
source edit that disables one specific piece of enforcement, run the look-ahead
suite against the sandbox, and require that the suite fails. The real source
tree is never touched. The sandbox reads the real cache through TAA_DATA_DIR so
nothing is duplicated and nothing is written back.

The output is a table of which named test flips from PASS to FAIL under which
mutation, which is a stronger statement than a pass count: it says what each
test is actually holding up.

Run:  py -3 tests/mutation_test.py
Exit code 0 means every mutation was caught. Non-zero means at least one
mutation survived, and a surviving mutation is a hole in the wall.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# (name, relative file, pattern, replacement, what it disables)
MUTATIONS = [
    ("as-of gate disabled",
     "taa/pitdata.py", r"^_ENFORCE = True$", "_ENFORCE = False",
     "the truncation that drops observations after the as-of date"),

    ("gate truncation deleted",
     "taa/pitdata.py",
     r"^    out = df\[df\.index <= pd\.Timestamp\(cutoff\)\]$",
     "    out = df  # MUTANT: truncation removed",
     "the filter itself, leaving the assertion in place"),

    # Deliberately expected to survive, and reported as such rather than
    # counted as a hole. The assertion on the line below the filter is
    # unreachable while the filter above it works, so removing it alone cannot
    # change any observable behaviour. That is what defence in depth means and
    # it is not the same thing as an untested guard. The filter itself is
    # mutated separately, above, and that mutation is caught.
    ("gate assertion deleted (expected inert)",
     "taa/pitdata.py",
     r"^    if len\(out\) and out\.index\.max\(\) > pd\.Timestamp\(cutoff\):$",
     "    if False:  # MUTANT: assertion removed",
     "a redundant backstop behind a working filter"),

    ("publication lag ignored",
     "taa/pitdata.py",
     r"^    cutoff = as_of - _dt\.timedelta\(days=lag_days\)$",
     "    cutoff = as_of  # MUTANT: publication lag ignored",
     "the lag between an observation's date and its release"),

    ("raw-store caller guard disabled",
     "taa/_rawstore.py", r"^_GUARD_ENABLED = True$", "_GUARD_ENABLED = False",
     "the rule that only pitdata may read the raw cache"),

    ("investable-date check removed",
     "taa/pitdata.py",
     r"^            if self\.date < config\.INVESTABLE_FROM\[ln\]:$",
     "            if False:  # MUTANT: investable dates ignored",
     "IPS 4.1, investable dates bind"),

    ("anachronism reason not required",
     "taa/pitdata.py",
     r"^        if not reason or len\(reason\) < 20:$",
     "        if False:  # MUTANT: anachronism admitted silently",
     "the requirement to declare a current-vintage input used historically"),
]


def parse_results(stdout: str) -> dict[str, bool]:
    out = {}
    for line in stdout.splitlines():
        m = re.match(r"\s*\[(PASS|FAIL)\]\s+(.*?)(?:\s{2,}.*)?$", line)
        if m:
            out[m.group(2).strip()] = (m.group(1) == "PASS")
    return out


def run_suite(package_root: Path) -> tuple[int, dict[str, bool], str]:
    env = dict(os.environ)
    env["TAA_DATA_DIR"] = str(ROOT / "data")
    env["TAA_OUTPUT_DIR"] = str(package_root / "_outputs")
    (package_root / "_outputs").mkdir(exist_ok=True)
    env["PYTHONPATH"] = str(package_root)
    proc = subprocess.run(
        [sys.executable, str(package_root / "tests" / "test_lookahead.py")],
        capture_output=True, text=True, env=env, cwd=str(package_root), timeout=900)
    return proc.returncode, parse_results(proc.stdout), proc.stdout + proc.stderr


def sandbox() -> Path:
    tmp = Path(tempfile.mkdtemp(prefix="ashcroft_mutant_"))
    shutil.copytree(ROOT / "taa", tmp / "taa",
                    ignore=shutil.ignore_patterns("__pycache__"))
    shutil.copytree(ROOT / "tests", tmp / "tests",
                    ignore=shutil.ignore_patterns("__pycache__"))
    return tmp


def apply_mutation(root: Path, rel: str, pattern: str, repl: str) -> bool:
    p = root / rel
    src = p.read_text(encoding="utf-8")
    new, n = re.subn(pattern, repl, src, count=1, flags=re.MULTILINE)
    if n == 0:
        return False
    p.write_text(new, encoding="utf-8")
    return True


def main() -> int:
    print("\nMUTATION TEST — Ashcroft University Endowment")
    print("  Breaking the look-ahead enforcement on purpose and requiring the suite to fail.\n")

    print("BASELINE — unmutated source")
    base_rc, base_results, base_out = run_suite(ROOT)
    print(f"  suite exit code {base_rc}, {sum(base_results.values())} of {len(base_results)} tests pass")
    if base_rc != 0:
        print("  BASELINE IS ALREADY RED. Fix the suite before running mutations.")
        print(base_out[-3000:])
        return 2
    print()

    rows, survived = [], []
    for name, rel, pattern, repl, disables in MUTATIONS:
        tmp = sandbox()
        try:
            if not apply_mutation(tmp, rel, pattern, repl):
                print(f"  [ERROR] mutation {name!r} did not match its target in {rel}. "
                      f"The source moved and this test is stale.")
                survived.append(name)
                rows.append({"mutation": name, "file": rel, "disables": disables,
                             "applied": False, "suite_failed": None, "caught_by": []})
                continue
            rc, results, out_txt = run_suite(tmp)
            crashed = "Traceback (most recent call last)" in out_txt
            flipped = sorted(k for k, ok in results.items()
                             if base_results.get(k) and not ok)
            caught = rc != 0
            inert = "expected inert" in name
            rows.append({"mutation": name, "file": rel, "disables": disables,
                         "applied": True, "suite_failed": caught, "caught_by": flipped,
                         "crashed": crashed, "expected_inert": inert})
            label = ("INERT   " if (inert and not caught) else
                     "CRASHED " if (caught and crashed and not flipped) else
                     "CAUGHT  " if caught else "SURVIVED")
            print(f"  [{label}] {name}")
            print(f"             disables {disables}")
            if flipped:
                for f in flipped:
                    print(f"             flipped to FAIL: {f}")
            elif crashed and caught:
                print("             no named test flipped; the suite aborted. The backstop "
                      "assertion in _gate raised where the filter should have prevented it, "
                      "which is defence in depth firing rather than a test catching it.")
            elif inert:
                print("             no test changed, and none can. This assertion is "
                      "unreachable while the filter above it works, so removing it alone "
                      "has no observable effect. The filter is mutated separately and that "
                      "mutation is caught.")
            else:
                print("             no test changed. The wall here is untested.")
            if not caught and not inert:
                survived.append(name)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        print()

    out = ROOT / "outputs" / "mutation_test.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(
        {"baseline_exit_code": base_rc,
         "baseline_tests": len(base_results),
         "baseline_passed": sum(base_results.values()),
         "mutations": rows,
         "survived": survived}, indent=2), encoding="utf-8")

    print(f"  {len(MUTATIONS) - len(survived)} of {len(MUTATIONS)} mutations caught")
    if survived:
        print("  SURVIVING MUTATIONS (each is a hole in the wall):")
        for s in survived:
            print(f"    {s}")
        return 1
    print("  Every deliberate break was detected. The suite is testing something.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
