"""
The unit-consistency check.

taa.costs works in percentage points of NAV. Everything else in this study works
in fractions. Both conventions are defensible; holding both at once without
saying so is how a study produces a confident wrong number.

The specific failure this guards against was live in this build. Applied without
conversion, costs.apply_min_trade reads a fractional 60bps trade as 0.006 against
a 0.50 minimum, suppresses it, and every one of the twenty quarterly decisions
comes back as a hold. The record would then have carried twenty reasoned entries
explaining an inactivity that was an arithmetic error. Nothing in the look-ahead
suite or the compliance test would have caught it, because both allocations were
internally valid.

So the conversion lives in one place, taa.simulate's adapter, and this asserts it.

Run:  py -3 tests/check_units.py
      py -3 tests/check_units.py --demo-fail
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from taa import config, costs, simulate  # noqa: E402

RESULTS: list[tuple[str, bool, str]] = []


def record(name: str, ok: bool, detail: str = "") -> None:
    RESULTS.append((name, ok, detail))
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f"  {detail}" if detail else ""))


def main() -> int:
    demo = "--demo-fail" in sys.argv
    print("\nUNIT-CONSISTENCY CHECK")
    print("  taa.costs speaks percentage points. Everything else speaks fractions.\n")

    base = dict(config.POLICY)

    # 1. costs.py is in percentage points: its own doctest values must behave.
    pp_from = {"us_equity": 38.0, "cash": 0.0}
    pp_to_small = {"us_equity": 38.3, "cash": -0.3}
    pp_to_big = {"us_equity": 38.6, "cash": -0.6}
    a = costs.apply_min_trade(pp_from, pp_to_small, reconcile_into=None)
    b = costs.apply_min_trade(pp_from, pp_to_big, reconcile_into=None)
    record("costs.apply_min_trade is in percentage points",
           a["us_equity"] == 38.0 and b["us_equity"] == 38.6,
           f"30bp -> {a['us_equity']}, 60bp -> {b['us_equity']}")

    # 2. The adapter must reproduce that behaviour on FRACTIONAL weights.
    f_small = dict(base); f_small["us_equity"] += 0.003; f_small["cash"] -= 0.003
    f_big = dict(base);   f_big["us_equity"] += 0.006;   f_big["cash"] -= 0.006
    if demo:
        f_big["us_equity"] = base["us_equity"] + 0.0006      # 6bps, must be suppressed
    out_s = simulate.c_min_trade(base, f_small)
    out_b = simulate.c_min_trade(base, f_big)
    supp = abs(out_s["us_equity"] - base["us_equity"]) < 1e-9
    passed = abs(out_b["us_equity"] - base["us_equity"]) > 1e-9
    record("adapter suppresses a 30bps trade expressed as a fraction", supp,
           f"us_equity {base['us_equity']:.4f} -> {out_s['us_equity']:.4f}")
    record("adapter passes a 60bps trade expressed as a fraction", passed,
           f"us_equity {base['us_equity']:.4f} -> {out_b['us_equity']:.4f}")

    # 3. The threshold sits exactly where the IPS puts it.
    at = dict(base); at["us_equity"] += config.MIN_TRADE_PP / 100.0; at["cash"] -= config.MIN_TRADE_PP / 100.0
    under = dict(base); under["us_equity"] += 0.0049; under["cash"] -= 0.0049
    o_at = simulate.c_min_trade(base, at)
    o_un = simulate.c_min_trade(base, under)
    record("the minimum-trade boundary is exactly 50bps (IPS 4.2)",
           abs(o_at["us_equity"] - at["us_equity"]) < 1e-9
           and abs(o_un["us_equity"] - base["us_equity"]) < 1e-9,
           "50bps passes, 49bps suppressed")

    # 4. Turnover and cost round-trip in fractional units.
    tr = simulate.c_trades(base, f_big)
    turn = simulate.c_turnover(base, f_big)
    cost = simulate.c_cost_bps(tr)
    record("adapter turnover is a fraction of NAV",
           0.0 < turn < 0.05, f"{turn * 100:.3f}pp one-way")
    record("adapter cost is in bps of NAV and is positive for a real trade",
           0.0 < cost < 50.0, f"{cost:.3f}bps on a 60bps switch")

    # 5. A full-portfolio move must not cost an absurd amount.
    extreme = dict(base)
    extreme["us_equity"] = 0.28
    extreme["cash"] = base["cash"] + 0.10
    c2 = simulate.c_cost_bps(simulate.c_trades(base, extreme))
    record("a 10pp switch out of US equity costs a sane number of bps",
           0.1 < c2 < 25.0, f"{c2:.2f}bps")

    # 6. Corridors are in percentage points and are all actionable.
    bad = [k for k, v in costs.CORRIDOR_PP.items() if v < config.MIN_TRADE_PP - 1e-9]
    record("every corridor is at least as wide as the minimum trade",
           not bad, f"narrowest {min(costs.CORRIDOR_PP.values()):.2f}pp" if not bad else str(bad))

    failed = [r for r in RESULTS if not r[1]]
    print(f"\n  {len(RESULTS) - len(failed)} of {len(RESULTS)} passed")
    if demo:
        print("  (--demo-fail proposes a 6bps trade where a 60bps trade is expected)")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
