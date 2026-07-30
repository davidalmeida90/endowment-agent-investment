#!/usr/bin/env python3
"""
check_capital_markets.py

Verification harness for the Capital Markets desk output, outputs/cme.json.
Standard library only.

Assertions
  1. At least 3 distinct houses are cited for every equity line, and every cited
     house resolves to a source register entry carrying a non-empty URL.
  2. Every one of the nine policy lines carries a forecast from at least 2 named
     sources.
  3. The adopted number for each line lies inside [min, max] of its cited sources,
     and the stated min/max/median actually match the cited forecasts.
  4. The weighted policy expected return recomputes from the adopted line numbers
     and the policy weights to within 1bp of the stated headline figure.
  5. Policy weights sum to 1.0.

Usage
  python check_capital_markets.py
  python check_capital_markets.py --demo-fail
      Mutates an in-memory copy of the data so that one assertion is violated,
      and shows the harness catching it. Exits 0 if the mutation was caught,
      non-zero if it was not, so the demo itself cannot silently pass.
"""

import json
import os
import sys
import copy

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.normpath(os.path.join(HERE, os.pardir, "outputs", "cme.json"))

LINE_KEYS = [
    "us_equity", "dev_ex_us", "em_equity", "ust_duration",
    "us_ig", "us_hy", "commodities", "listed_re", "cash",
]
EQUITY_KEYS = ["us_equity", "dev_ex_us", "em_equity"]

BP = 1e-4          # one basis point in decimal return terms
TOL = 1e-9         # floating point slack


def median(values):
    s = sorted(values)
    n = len(s)
    if n == 0:
        raise ValueError("median of empty sequence")
    mid = n // 2
    return s[mid] if n % 2 else (s[mid - 1] + s[mid]) / 2.0


def load(path=DATA):
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


# --------------------------------------------------------------------------
# assertions. each returns (ok: bool, list_of_detail_lines)
# --------------------------------------------------------------------------

def a1_three_houses_for_equity(d):
    detail, ok = [], True
    urls = {}
    for s in d.get("sources", []):
        urls[s.get("house", "")] = (s.get("url") or "").strip()

    for key in EQUITY_KEYS:
        line = d["lines"][key]
        houses = sorted({f["house"] for f in line["forecasts"]})
        if len(houses) < 3:
            ok = False
            detail.append("  %-13s only %d distinct house(s): %s"
                          % (key, len(houses), ", ".join(houses) or "none"))
            continue
        missing = [h for h in houses if not urls.get(h)]
        if missing:
            ok = False
            detail.append("  %-13s %d houses, but no usable URL for: %s"
                          % (key, len(houses), ", ".join(missing)))
        else:
            detail.append("  %-13s %d houses, all with URLs: %s"
                          % (key, len(houses), ", ".join(houses)))
    return ok, detail


def a2_two_sources_per_line(d):
    detail, ok = [], True
    for key in LINE_KEYS:
        line = d["lines"].get(key)
        if line is None:
            ok = False
            detail.append("  %-13s MISSING from lines" % key)
            continue
        houses = sorted({f["house"] for f in line["forecasts"]})
        if len(houses) < 2:
            ok = False
            detail.append("  %-13s only %d named source(s)" % (key, len(houses)))
        else:
            detail.append("  %-13s %d named sources" % (key, len(houses)))
    return ok, detail


def a3_adopted_within_range(d):
    detail, ok = [], True
    for key in LINE_KEYS:
        line = d["lines"][key]
        vals = [f["value"] for f in line["forecasts"]]
        lo, hi = min(vals), max(vals)
        med = median(vals)
        adopted = line["adopted"]

        problems = []
        if not (lo - TOL <= adopted <= hi + TOL):
            problems.append("adopted %.4f outside [%.4f, %.4f]" % (adopted, lo, hi))
        if abs(line["min"] - lo) > TOL:
            problems.append("stated min %.4f != cited min %.4f" % (line["min"], lo))
        if abs(line["max"] - hi) > TOL:
            problems.append("stated max %.4f != cited max %.4f" % (line["max"], hi))
        if abs(line["median"] - med) > TOL:
            problems.append("stated median %.4f != cited median %.4f"
                            % (line["median"], med))

        if problems:
            ok = False
            detail.append("  %-13s %s" % (key, "; ".join(problems)))
        else:
            detail.append("  %-13s adopted %6.2f%% in [%5.2f%%, %5.2f%%], median %6.2f%%"
                          % (key, adopted * 100, lo * 100, hi * 100, med * 100))
    return ok, detail


def a4_weighted_recompute(d):
    total = sum(d["lines"][k]["policy_weight"] * d["lines"][k]["adopted"]
                for k in LINE_KEYS)
    stated = d["policy_expected_return"]["adopted"]
    diff = abs(total - stated)
    ok = diff <= BP + TOL
    detail = ["  recomputed %.5f%%  stated %.5f%%  difference %.2fbp (tolerance 1.00bp)"
              % (total * 100, stated * 100, diff * 1e4)]
    return ok, detail


def a5_weights_sum(d):
    total = sum(d["lines"][k]["policy_weight"] for k in LINE_KEYS)
    ok = abs(total - 1.0) <= 1e-9
    detail = ["  policy weights sum to %.10f" % total]
    return ok, detail


CHECKS = [
    ("1. at least 3 distinct houses per equity line, each with a URL", a1_three_houses_for_equity),
    ("2. every one of the nine lines has >= 2 named sources", a2_two_sources_per_line),
    ("3. adopted lies within [min, max] of cited sources", a3_adopted_within_range),
    ("4. weighted policy return recomputes to within 1bp of headline", a4_weighted_recompute),
    ("5. policy weights sum to 1.0", a5_weights_sum),
]


def run(d, header):
    print(header)
    print("=" * len(header))
    failures = 0
    for name, fn in CHECKS:
        try:
            ok, detail = fn(d)
        except Exception as exc:                       # a malformed file is a failure
            ok, detail = False, ["  raised %s: %s" % (type(exc).__name__, exc)]
        print("%s  %s" % ("PASS" if ok else "FAIL", name))
        for line in detail:
            print(line)
        if not ok:
            failures += 1
    print("-" * len(header))
    print("%d of %d assertions passed." % (len(CHECKS) - failures, len(CHECKS)))
    return failures


def demo_fail(d):
    """Mutate a copy so exactly one assertion breaks, and prove the harness sees it."""
    m = copy.deepcopy(d)
    before = m["lines"]["us_equity"]["adopted"]
    after = m["lines"]["us_equity"]["max"] + 0.02     # push adopted above every cited house
    m["lines"]["us_equity"]["adopted"] = after
    print("DEMO-FAIL MUTATION")
    print("  us_equity.adopted %.4f -> %.4f (above the cited max of %.4f)"
          % (before, after, m["lines"]["us_equity"]["max"]))
    print("  This should break assertion 3, and assertion 4 as a consequence,")
    print("  because the headline no longer recomputes from the adopted numbers.")
    print()
    failures = run(m, "CAPITAL MARKETS CHECK (mutated data)")
    print()
    if failures:
        print("DEMO OK: the mutation was caught by %d assertion(s)." % failures)
        return 0
    print("DEMO BROKEN: the mutation was not caught. The harness is not doing its job.")
    return 1


def main(argv):
    if not os.path.exists(DATA):
        print("FAIL  cannot find %s" % DATA)
        return 2
    d = load()

    if "--demo-fail" in argv:
        return demo_fail(d)

    failures = run(d, "CAPITAL MARKETS CHECK  (%s, as of %s)"
                   % (os.path.basename(DATA), d.get("as_of", "unknown")))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
