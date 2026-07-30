#!/usr/bin/env python3
"""
check_implementation.py -- the Implementation & Operations desk's own check.

Standard library only. Run from anywhere:

    py -3 tests/check_implementation.py
    py -3 tests/check_implementation.py --demo-fail

Exits 0 if every assertion passes, 1 otherwise. --demo-fail plants a violation
(a corridor narrower than the IPS minimum trade size) so that a reader can see
the check catching something rather than take on trust that it would.

What is asserted, and why each one can fail:

  1. Sourcing.        Every vehicle in outputs/implementation.json carries a
                      spread_bps with a non-empty source_url and a status of
                      VERIFIED or RECALLED. A number without a source is not
                      evidence (IPS Section 4.4).
  2. Cost floor.      The adopted one-way cost for each line is at least the
                      quoted half-spread of that line's primary vehicle. The
                      desk does not get to assume it trades inside the spread.
  3. Cost shape.      SPY's line costs strictly less than DBC's and HYG's. If
                      that inverts, the vector has been mis-keyed.
  4. Corridor width.  Every corridor is at least MIN_TRADE_PP wide, so that
                      breaching it generates a trade the IPS permits.
  5. Corridor range.  Every corridor keeps its line inside the IPS Section 4.1
                      permitted range, which binds independently of the
                      tracking-error budget.
  6. Minimum trade.   apply_min_trade suppresses a 30bp trade and passes a
                      60bp one.
"""

import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

from taa import costs  # noqa: E402

JSON_PATH = os.path.join(ROOT, "outputs", "implementation.json")

_RESULTS = []


def check(name, condition, detail=""):
    _RESULTS.append((bool(condition), name))
    tag = "PASS" if condition else "FAIL"
    line = f"[{tag}] {name}"
    if detail:
        line += f"\n         {detail}"
    print(line)
    return bool(condition)


def section(title):
    print()
    print(title)
    print("-" * len(title))


def main(demo_fail=False):
    print("=" * 78)
    print("Ashcroft University Endowment -- Implementation & Operations desk")
    print("check_implementation.py                                 28 Jul 2026")
    print("=" * 78)

    if demo_fail:
        print()
        print("*** --demo-fail: planting a violation before running the check.")
        print("*** listed_re corridor 0.50pp -> 0.30pp, which is narrower than")
        print("*** the IPS Section 4.2 minimum trade of 50bp, so a breach of")
        print("*** that corridor would generate a trade the mandate forbids.")
        costs.CORRIDOR_PP["listed_re"] = 0.30

    if not os.path.exists(JSON_PATH):
        print(f"\n[FAIL] outputs/implementation.json not found at {JSON_PATH}")
        return 1
    with open(JSON_PATH, encoding="utf-8") as fh:
        doc = json.load(fh)
    vehicles = doc["vehicles"]

    # ------------------------------------------------------------------
    section("1. Every vehicle carries a sourced, statused bid-ask spread")
    # ------------------------------------------------------------------
    check("outputs/implementation.json lists at least the nine primary vehicles",
          len(vehicles) >= 9, f"{len(vehicles)} vehicles present")
    for tk in sorted(vehicles):
        v = vehicles[tk]
        sp = v.get("spread_bps")
        ok_obj = isinstance(sp, dict)
        val = sp.get("value_bps") if ok_obj else None
        url = (sp.get("source_url") or "").strip() if ok_obj else ""
        status = sp.get("status") if ok_obj else None
        ok = (ok_obj
              and isinstance(val, (int, float))
              and val >= 0
              and len(url) > 0
              and status in ("VERIFIED", "RECALLED"))
        check(f"{tk:<5} spread_bps sourced and statused",
              ok,
              f"{val}bp  status={status}  {url[:72] if url else 'NO SOURCE URL'}")

    # ------------------------------------------------------------------
    section("2. Adopted one-way cost >= half-spread of the primary vehicle")
    # ------------------------------------------------------------------
    for line in costs.LINES:
        prim = costs.PRIMARY_VEHICLE[line]
        if prim not in vehicles:
            check(f"{line:<13} primary vehicle {prim} present in JSON", False)
            continue
        quoted = float(vehicles[prim]["spread_bps"]["value_bps"])
        half = quoted / 2.0
        adopted = costs.ONE_WAY_BPS[line]
        check(f"{line:<13} {adopted:>5.2f}bp >= half-spread of {prim}",
              adopted >= half,
              f"quoted {quoted:.4f}bp, half {half:.4f}bp, "
              f"adopted is {adopted / half:.1f}x the half-spread"
              if half else f"quoted {quoted:.4f}bp")

    # ------------------------------------------------------------------
    section("3. Cost vector has the right shape")
    # ------------------------------------------------------------------
    line_of = {tk: vehicles[tk]["line"] for tk in vehicles}
    spy = costs.ONE_WAY_BPS[line_of["SPY"]]
    dbc = costs.ONE_WAY_BPS[line_of["DBC"]]
    hyg = costs.ONE_WAY_BPS[line_of["HYG"]]
    check("SPY line cost < DBC line cost", spy < dbc,
          f"us_equity {spy:.2f}bp < commodities {dbc:.2f}bp")
    check("SPY line cost < HYG line cost", spy < hyg,
          f"us_equity {spy:.2f}bp < us_hy {hyg:.2f}bp")
    check("every line has a strictly positive one-way cost",
          all(costs.ONE_WAY_BPS[ln] > 0 for ln in costs.LINES),
          "no line is free to trade")

    # ------------------------------------------------------------------
    section("4. Every corridor is at least one minimum trade wide")
    # ------------------------------------------------------------------
    for line in costs.LINES:
        c = costs.CORRIDOR_PP[line]
        check(f"{line:<13} corridor {c:.2f}pp >= "
              f"minimum trade {costs.MIN_TRADE_PP:.2f}pp",
              c >= costs.MIN_TRADE_PP,
              f"a breach trades {c:.2f}pp = USD {costs.usd(c):,.0f}"
              if c >= costs.MIN_TRADE_PP else
              f"a breach would trade {c:.2f}pp = USD {costs.usd(c):,.0f}, "
              f"below the IPS Section 4.2 minimum, so it could not be acted on")

    # ------------------------------------------------------------------
    section("5. Every corridor keeps its line inside the IPS range")
    # ------------------------------------------------------------------
    for line in costs.LINES:
        lo, hi = costs.RANGE_PP[line]
        blo, bhi = costs.band(line)
        ok = (blo >= lo - 1e-9) and (bhi <= hi + 1e-9)
        side = " (one-sided: policy weight sits on the range floor)" \
            if line in costs.ONE_SIDED_UP else ""
        check(f"{line:<13} band [{blo:.2f}, {bhi:.2f}] inside "
              f"range [{lo:.0f}, {hi:.0f}]", ok,
              f"headroom {blo - lo:.2f}pp below, {hi - bhi:.2f}pp above{side}")

    # ------------------------------------------------------------------
    section("6. apply_min_trade honours the IPS Section 4.2 minimum")
    # ------------------------------------------------------------------
    start = {"us_equity": 38.0, "cash": 0.0}

    small = costs.apply_min_trade(start, {"us_equity": 38.3, "cash": -0.3},
                                  reconcile_into=None)
    check("30bp proposed trade is suppressed",
          abs(small["us_equity"] - 38.0) < 1e-12,
          f"us_equity stays at {small['us_equity']:.2f}%, "
          f"below the {costs.MIN_TRADE_PP:.2f}pp minimum")

    big = costs.apply_min_trade(start, {"us_equity": 38.6, "cash": -0.6},
                                reconcile_into=None)
    check("60bp proposed trade passes",
          abs(big["us_equity"] - 38.6) < 1e-12,
          f"us_equity moves to {big['us_equity']:.2f}%, "
          f"at or above the {costs.MIN_TRADE_PP:.2f}pp minimum")

    edge = costs.apply_min_trade(start, {"us_equity": 38.5, "cash": -0.5},
                                 reconcile_into=None)
    check("a trade of exactly 50bp passes",
          abs(edge["us_equity"] - 38.5) < 1e-12,
          "the minimum is inclusive, per 'anything smaller' at IPS 4.2")

    recon = costs.apply_min_trade(start, {"us_equity": 38.3, "cash": -0.3})
    check("suppression reconciles into cash so weights still sum",
          abs(sum(recon.values()) - 38.0) < 1e-9,
          f"total {sum(recon.values()):.4f}%, cash absorbs "
          f"{recon['cash']:.2f}pp")

    # ------------------------------------------------------------------
    section("Cross-checks the desk uses to sanity-test itself")
    # ------------------------------------------------------------------
    te = costs.corridor_te_bps()
    check("corridor set consumes less than a quarter of the TE budget",
          te < 0.25 * costs.TE_BUDGET_BPS,
          f"{te:.1f}bp of drift TE with every line at its edge, against a "
          f"{costs.TE_BUDGET_BPS:.0f}bp budget")

    full_reset = costs.round_trip_cost(
        {ln: costs.CORRIDOR_PP[ln] for ln in costs.LINES})
    check("a full reset from every corridor edge costs under 1bp of NAV",
          full_reset < 1.0,
          f"{full_reset:.3f}bp of NAV = USD {full_reset / 10000 * costs.NAV_USD:,.0f}")

    check("module reports the JSON's one-way vector unchanged",
          doc["one_way_bps"] == dict(costs.ONE_WAY_BPS)
          or demo_fail,
          "taa/costs.py and outputs/implementation.json agree")

    # ------------------------------------------------------------------
    passed = sum(1 for ok, _ in _RESULTS if ok)
    failed = len(_RESULTS) - passed
    print()
    print("=" * 78)
    print(f"{passed} passed, {failed} failed, {len(_RESULTS)} assertions")
    if failed:
        print()
        for ok, name in _RESULTS:
            if not ok:
                print(f"  FAILED: {name}")
    print("=" * 78)
    return 1 if failed else 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--demo-fail", action="store_true",
                    help="plant a corridor narrower than the minimum trade "
                         "and show the check catching it")
    args = ap.parse_args()
    sys.exit(main(demo_fail=args.demo_fail))
