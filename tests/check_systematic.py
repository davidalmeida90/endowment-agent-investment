#!/usr/bin/env python3
"""Check for the Systematic desk evidence pack.

Standard library only. Loads outputs/systematic_evidence.json and asserts the
things that would make the paper wrong if they were false:

  1. every claim carries a non-empty source_url and a status of exactly
     VERIFIED or RECALLED
  2. VERIFIED claims are at least 60% of all claims
  3. the fundamental-law arithmetic recomputes:
        ir == round(ic * sqrt(effective_breadth) * tc, 4)
        expected_alpha_bps == round(ir * te_budget_bps, 1)
  4. the predictor survival range lies in (0, 1) and carries at least two
     distinct sources that disagree

Usage:
    py -3 tests/check_systematic.py
    py -3 tests/check_systematic.py --demo-fail

Exit code 0 on all-pass, 1 on any failure.
"""

import argparse
import copy
import json
import math
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA_PATH = os.path.join(ROOT, "outputs", "systematic_evidence.json")

VALID_STATUS = ("VERIFIED", "RECALLED")
MIN_VERIFIED_FRACTION = 0.60
TOL = 1e-9


class Results:
    def __init__(self):
        self.rows = []

    def check(self, name, ok, detail=""):
        self.rows.append((name, bool(ok), detail))
        return bool(ok)

    def report(self):
        width = max(len(n) for n, _, _ in self.rows)
        for name, ok, detail in self.rows:
            tag = "PASS" if ok else "FAIL"
            line = "[{}] {}".format(tag, name.ljust(width))
            if detail:
                line += "  |  " + detail
            print(line)
        failed = [n for n, ok, _ in self.rows if not ok]
        print("-" * 72)
        print("{} checks, {} passed, {} failed".format(
            len(self.rows), len(self.rows) - len(failed), len(failed)))
        return 1 if failed else 0


def load(path):
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


# --------------------------------------------------------------------------
# assertion 1: every claim has a non-empty source_url and a legal status
# --------------------------------------------------------------------------
def check_claim_integrity(data, res):
    claims = data.get("claims", [])
    res.check("claims list is non-empty", len(claims) > 0,
              "{} claims".format(len(claims)))

    missing_url = []
    bad_status = []
    missing_id = []
    for i, c in enumerate(claims):
        cid = c.get("id") or "<index {}>".format(i)
        if not c.get("id"):
            missing_id.append(str(i))
        url = c.get("source_url")
        if not isinstance(url, str) or not url.strip():
            missing_url.append(cid)
        elif not re.match(r"^https?://\S+$", url.strip()):
            missing_url.append(cid + " (malformed)")
        if c.get("status") not in VALID_STATUS:
            bad_status.append("{}={!r}".format(cid, c.get("status")))

    res.check("every claim has an id", not missing_id,
              "missing: " + ", ".join(missing_id) if missing_id else "")
    res.check("every claim has a non-empty source_url", not missing_url,
              "offenders: " + ", ".join(missing_url) if missing_url
              else "{}/{} ok".format(len(claims), len(claims)))
    res.check("every claim status is VERIFIED or RECALLED", not bad_status,
              "offenders: " + ", ".join(bad_status) if bad_status
              else "{}/{} ok".format(len(claims), len(claims)))

    ids = [c.get("id") for c in claims if c.get("id")]
    res.check("claim ids are unique", len(ids) == len(set(ids)),
              "{} ids, {} unique".format(len(ids), len(set(ids))))


# --------------------------------------------------------------------------
# assertion 2: VERIFIED >= 60% of all claims
# --------------------------------------------------------------------------
def check_verified_fraction(data, res):
    claims = data.get("claims", [])
    if not claims:
        res.check("VERIFIED fraction >= 60%", False, "no claims")
        return
    n_ver = sum(1 for c in claims if c.get("status") == "VERIFIED")
    frac = n_ver / float(len(claims))
    res.check(
        "VERIFIED fraction >= 60%",
        frac >= MIN_VERIFIED_FRACTION,
        "{}/{} = {:.1%} (floor {:.0%})".format(
            n_ver, len(claims), frac, MIN_VERIFIED_FRACTION),
    )


# --------------------------------------------------------------------------
# assertion 3: the fundamental-law arithmetic recomputes
# --------------------------------------------------------------------------
def check_fundamental_law(data, res):
    fl = data.get("fundamental_law")
    if not isinstance(fl, dict):
        res.check("fundamental_law block present", False, "missing")
        return
    res.check("fundamental_law block present", True, "")

    required = ("ic", "nominal_breadth", "effective_breadth", "tc", "ir",
                "te_budget_bps", "expected_alpha_bps", "cost_bps",
                "clears_costs")
    missing = [k for k in required if k not in fl]
    res.check("fundamental_law has all required keys", not missing,
              "missing: " + ", ".join(missing) if missing else "")
    if missing:
        return

    ic = float(fl["ic"])
    br = float(fl["effective_breadth"])
    tc = float(fl["tc"])
    ir = float(fl["ir"])
    te = float(fl["te_budget_bps"])
    alpha = float(fl["expected_alpha_bps"])
    cost = float(fl["cost_bps"])

    res.check("inputs are in sane ranges",
              0.0 < ic < 0.30 and 0.0 < br <= float(fl["nominal_breadth"])
              and 0.0 < tc <= 1.0 and te > 0.0,
              "ic={} br={} tc={} te={}bps".format(ic, br, tc, te))

    ir_expected = round(ic * math.sqrt(br) * tc, 4)
    res.check(
        "ir == round(ic * sqrt(breadth) * tc, 4)",
        abs(ir - ir_expected) <= TOL,
        "stated {:.6f} vs recomputed {:.6f}".format(ir, ir_expected),
    )

    alpha_expected = round(ir * te, 1)
    res.check(
        "expected_alpha_bps == round(ir * te_budget_bps, 1)",
        abs(alpha - alpha_expected) <= TOL,
        "stated {:.4f} vs recomputed {:.4f}".format(alpha, alpha_expected),
    )

    clears = bool(fl["clears_costs"])
    res.check(
        "clears_costs is consistent with alpha vs cost",
        clears == (alpha > cost),
        "alpha {:.1f}bps vs cost {:.1f}bps -> {}".format(
            alpha, cost, alpha > cost),
    )

    if "net_alpha_bps" in fl:
        net_expected = round(alpha - cost, 1)
        res.check(
            "net_alpha_bps == round(alpha - cost, 1)",
            abs(float(fl["net_alpha_bps"]) - net_expected) <= 0.05,
            "stated {} vs recomputed {}".format(fl["net_alpha_bps"],
                                                net_expected),
        )

    deriv = fl.get("derivation", "")
    res.check("derivation shows the arithmetic", len(deriv) > 400,
              "{} chars".format(len(deriv)))


# --------------------------------------------------------------------------
# assertion 4: survival rate in (0,1), >= 2 distinct disagreeing sources
# --------------------------------------------------------------------------
def check_predictor_survival(data, res):
    ps = data.get("predictor_survival")
    if not isinstance(ps, dict):
        res.check("predictor_survival block present", False, "missing")
        return
    res.check("predictor_survival block present", True, "")

    for key in ("low", "high"):
        if key not in ps:
            res.check("predictor_survival has '{}'".format(key), False,
                      "missing")
            return

    low = float(ps["low"])
    high = float(ps["high"])

    res.check("survival low is strictly between 0 and 1", 0.0 < low < 1.0,
              "low = {}".format(low))
    res.check("survival high is strictly between 0 and 1", 0.0 < high < 1.0,
              "high = {}".format(high))
    res.check("survival range is ordered low < high", low < high,
              "[{}, {}]".format(low, high))

    sources = ps.get("sources", [])
    distinct = {s.strip() for s in sources if isinstance(s, str) and s.strip()}
    res.check(
        "survival range carries >= 2 distinct sources",
        len(distinct) >= 2,
        "{} distinct of {} listed".format(len(distinct), len(sources)),
    )
    res.check(
        "the sources actually disagree (non-degenerate range)",
        (high - low) > 0.05,
        "spread = {:.2f}".format(high - low),
    )

    # the disagreement must be documented, not just asserted
    res.check("survival note explains why the sources differ",
              len(ps.get("note", "")) > 200,
              "{} chars".format(len(ps.get("note", ""))))


# --------------------------------------------------------------------------
# supporting blocks the paper depends on
# --------------------------------------------------------------------------
def check_supporting_blocks(data, res):
    se = data.get("sharpe_se_n60", {})
    ok = isinstance(se, dict) and "sr_0_5" in se and "sr_1_0" in se
    res.check("sharpe_se_n60 block present", ok, "")
    if ok:
        for label, sr in (("sr_0_5", 0.5), ("sr_1_0", 1.0)):
            expected = round(math.sqrt((1.0 + sr * sr / 2.0) / 60.0), 3)
            res.check(
                "sharpe_se_n60.{} matches Lo (2002) eq. 9".format(label),
                abs(float(se[label]) - expected) <= 0.0006,
                "stated {} vs formula {:.4f}".format(se[label], expected),
            )

    r2 = data.get("r2oos_definition", {})
    res.check(
        "r2oos_definition benchmarks the expanding historical mean",
        isinstance(r2, dict)
        and r2.get("benchmark") == "expanding historical mean"
        and "source_url" in r2 and bool(str(r2.get("source_url", "")).strip()),
        r2.get("benchmark", "<missing>"),
    )

    vm = data.get("vol_management", {})
    res.check(
        "vol_management separates forecastability from scaling",
        isinstance(vm, dict)
        and all(k in vm and len(str(vm[k])) > 80
                for k in ("forecastable", "scaling_works",
                          "verdict_for_this_mandate")),
        "",
    )


def run(data):
    res = Results()
    check_claim_integrity(data, res)
    check_verified_fraction(data, res)
    check_fundamental_law(data, res)
    check_predictor_survival(data, res)
    check_supporting_blocks(data, res)
    return res


def corrupt(data):
    """Break the data in three independent ways so the check goes red."""
    bad = copy.deepcopy(data)
    # 1. strip a source_url
    if bad.get("claims"):
        bad["claims"][0]["source_url"] = ""
    # 2. break the fundamental-law arithmetic
    if "fundamental_law" in bad:
        bad["fundamental_law"]["ir"] = 0.0850
    # 3. collapse the survival disagreement to a single source
    if "predictor_survival" in bad:
        bad["predictor_survival"]["sources"] = [
            bad["predictor_survival"]["sources"][0]
        ] if bad["predictor_survival"].get("sources") else []
        bad["predictor_survival"]["high"] = bad["predictor_survival"]["low"]
    return bad


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--demo-fail", action="store_true",
                    help="run against a corrupted copy to show the check fail")
    ap.add_argument("--data", default=DATA_PATH)
    args = ap.parse_args()

    if not os.path.exists(args.data):
        print("FAIL: evidence file not found at {}".format(args.data))
        return 1

    data = load(args.data)

    if args.demo_fail:
        print("=== DEMO-FAIL MODE: running against a corrupted in-memory copy ===")
        print("    injected: (1) stripped source_url on the first claim,")
        print("              (2) wrong ir in fundamental_law,")
        print("              (3) survival range collapsed to one source")
        print("=" * 72)
        data = corrupt(data)
    else:
        print("=== Systematic desk evidence check ===")
        print("    file: {}".format(args.data))
        print("=" * 72)

    res = run(data)
    code = res.report()

    if args.demo_fail:
        if code != 0:
            print("demo-fail behaved correctly: the check went red.")
            return 0
        print("demo-fail did NOT go red, which is itself a failure.")
        return 1
    return code


if __name__ == "__main__":
    sys.exit(main())
