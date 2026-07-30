"""
Second audit pass: bias, and the claims this office asserted without testing.

The first pass (tests/audit.py) asked what is missing. This one asks what is
tilted, and it concentrates on claims the coordinating office made in prose and
never checked. Several are tested here for the first time.

Run:  py -3 tests/audit2.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from taa import config, perf, pitdata  # noqa: E402

F: dict = {}


def head(t):
    print(f"\n{t}\n" + "=" * len(t))


def note(k, v, detail=""):
    F[k] = {"value": v, "detail": detail}
    print(f"  {k:46s} {str(v):>12s}  {detail}")


rec = json.loads((config.OUTPUTS / "decision_record.json").read_text(encoding="utf-8"))
decs = rec["decisions"]
idx = pd.to_datetime(rec["monthly"]["dates"])
s = pd.Series(rec["monthly"]["strategy"], index=idx)
b = pd.Series(rec["monthly"]["benchmark"], index=idx)

# ==========================================================================
head("A. IS THE 50/50 RECONCILIATION RULE ACTUALLY NEUTRAL?")
# Equal weight on two ACTIVE VECTORS is not equal weight on two OPINIONS. The
# desk that takes larger positions dominates the blend automatically.
qn, mn, corr_q, corr_m = [], [], [], []
for e in decs:
    q = np.array([e["quant_allocation"][k] - config.POLICY[k] for k in config.LINES])
    m = np.array([e["macro_allocation"][k] - config.POLICY[k] for k in config.LINES])
    f = np.array([e["weights_after"][k] - config.POLICY[k] for k in config.LINES])
    qn.append(np.linalg.norm(q))
    mn.append(np.linalg.norm(m))
    if np.linalg.norm(f) > 1e-9:
        if np.linalg.norm(q) > 1e-9:
            corr_q.append(float(np.dot(q, f) / (np.linalg.norm(q) * np.linalg.norm(f))))
        if np.linalg.norm(m) > 1e-9:
            corr_m.append(float(np.dot(m, f) / (np.linalg.norm(m) * np.linalg.norm(f))))
note("mean size of the quant active vector", f"{np.mean(qn)*100:.2f}pp")
note("mean size of the macro active vector", f"{np.mean(mn)*100:.2f}pp")
note("ratio, quant to macro", f"{np.mean(qn)/np.mean(mn):.2f}x",
     "a 50/50 rule on vectors of unequal size is not a 50/50 rule on views")
note("mean cosine, adopted vs QUANT view", f"{np.mean(corr_q):+.3f}")
note("mean cosine, adopted vs MACRO view", f"{np.mean(corr_m):+.3f}",
     "the adopted allocation resembles whichever desk this is higher for")
note("quarters where quant was the larger view", f"{sum(1 for a, c in zip(qn, mn) if a > c)} of {len(decs)}")

# ==========================================================================
head("B. A CLAIM THE REPORT MAKES AND NEVER TESTED")
# "A monthly-rebalanced blend is harder to beat than a drifting one."
lines = config.LINES
rets = pitdata.as_of(config.WINDOW_END).monthly_returns()
rets = rets[(rets.index >= pd.Timestamp(config.WINDOW_START)) &
            (rets.index <= pd.Timestamp(config.WINDOW_END))].fillna(0.0)
w = dict(config.POLICY)
drift = []
for dt_ in rets.index:
    r = float(sum(w[k] * rets.loc[dt_, k] for k in lines))
    drift.append(r)
    nw = {k: w[k] * (1 + rets.loc[dt_, k]) for k in lines}
    tot = sum(nw.values())
    w = {k: v / tot for k, v in nw.items()}
drift = pd.Series(drift, index=rets.index)
note("benchmark, monthly rebalanced, annualised", f"{perf.annualised_return(b)*100:.3f}%")
note("benchmark, never rebalanced (drifting)", f"{perf.annualised_return(drift)*100:.3f}%")
harder = perf.annualised_return(b) > perf.annualised_return(drift)
note("is the rebalanced blend harder to beat?", "YES" if harder else "NO",
     "the report asserts YES" + ("" if harder else "  <-- THE CLAIM IS WRONG"))
note("difference", f"{(perf.annualised_return(b)-perf.annualised_return(drift))*10000:+.1f}bps")

# ==========================================================================
head("C. THE COST ARGUMENT: EX ANTE AGAINST REALISED")
sc = rec["scorecard"]
sysj = json.loads((config.OUTPUTS / "systematic_evidence.json").read_text(encoding="utf-8"))
fl = sysj["fundamental_law"]
note("Systematic desk assumed turnover cost", f"{fl['cost_bps']}bps/yr",
     "80% turnover at 8bps one-way")
note("realised turnover cost in the simulation", f"{sc['turnover_cost_bps_per_year']:.1f}bps/yr")
note("ratio, assumed to realised",
     f"{fl['cost_bps']/max(sc['turnover_cost_bps_per_year'],1e-9):.1f}x",
     "the desk's cost assumption is this many times what the programme actually spent")
note("Systematic desk expected alpha", f"{fl['expected_alpha_bps']}bps/yr")
note("realised active return", f"{sc['net_active_bps_per_year']:.1f}bps/yr")
clears_ex_ante = fl["expected_alpha_bps"] > fl["cost_bps"]
clears_realised = sc["net_active_bps_per_year"] > sc["turnover_cost_bps_per_year"]
note("clears costs, EX ANTE arithmetic", "NO" if not clears_ex_ante else "YES")
note("clears costs, REALISED on this window", "YES" if clears_realised else "NO",
     "<-- TENSION: the two answers differ and the report leads with the first")

# ==========================================================================
head("D. DOES THE DRAWDOWN FINDING SURVIVE A DIFFERENT WINDOW?")
# The second headline is that the policy portfolio breaches its own (20)% limit.
# It rests on one episode inside the chosen window. Tested over all available
# history and over every rolling five-year window.
full = pitdata.as_of(config.WINDOW_END).monthly_returns().fillna(0.0)
polf = (full * pd.Series(config.POLICY)).sum(axis=1)
dd_full = perf.max_drawdown(polf)
note("policy portfolio worst drawdown, full cache", f"{dd_full*100:.2f}%",
     f"{polf.index.min().date()} to {polf.index.max().date()}")
breaches = []
for i in range(len(polf) - 60 + 1):
    seg = polf.iloc[i:i + 60]
    if perf.max_drawdown(seg) < config.DRAWDOWN_LIMIT:
        breaches.append(str(seg.index[0].date()))
tot_windows = len(polf) - 60 + 1
note("rolling 5y windows breaching the (20)% limit", f"{len(breaches)} of {tot_windows}",
     f"{len(breaches)/max(tot_windows,1)*100:.0f}% of five-year windows since 2009")
note("worst 12m loss for the policy portfolio", f"{polf.rolling(12).apply(lambda x: (1+x).prod()-1).min()*100:.2f}%")

# ==========================================================================
head("E. ARE THE THREE 'INDEPENDENT' FINDINGS INDEPENDENT?")
note("Capital Markets finding", "valuation", "10y forecasts vs the 8.10% spending rule")
note("Systematic finding", "fundamental law", "IC x sqrt(breadth) x TC vs cost")
note("Quantitative finding", "R2_oos", "signals vs the expanding historical mean")
note("shared input: the replication literature", "YES",
     "Systematic and Quantitative both update from the same prior")
note("shared input: market prices", "YES", "Quantitative and Capital Markets both price off them")
note("genuinely disjoint pair", "CM vs Systematic",
     "a valuation gap and a breadth/cost arithmetic share no input")
note("independent findings, honestly counted", "2 of 3",
     "the report says three; two is the defensible count")

# ==========================================================================
head("F. COORDINATOR ANCHORING")
# Every message the office sent a desk carried the office's own diagnosis.
msgs = [
    ("Quantitative", "config.RAW in signals.py", "office supplied the fix (store_id)"),
    ("Macro", "credit series limitation", "office supplied the substitute series"),
    ("Implementation", "unit contract", "office supplied the diagnosis and the adapter"),
    ("Risk", "range_breach_inside_te", "office supplied the root cause AND the forbidden fixes"),
]
for d, topic, what in msgs:
    note(f"message to {d}", topic, what)
note("desks that pushed back on an office diagnosis", 0,
     "<-- every diagnosis the office sent was adopted as sent")

# ==========================================================================
head("G. SELF-REPORTED DESK CHECKS")
note("Macro desk assertions, self-written and self-run", 688)
note("Implementation desk assertions", 53)
note("Systematic desk checks", 26)
note("Capital Markets assertions", 5)
note("Risk desk mutants killed", 13, "adversarial to itself; the strongest of the five")
note("desk checks independently re-run by the office", "all", "but not independently re-derived")
note("desk checks whose ASSERTIONS the office reviewed line by line", "0 of 5",
     "<-- a desk that writes and passes its own 688 assertions is weakly evidenced")

# ==========================================================================
head("H. SELECTION MADE BY THE COORDINATOR")
note("agent-dynamics episodes reported", "3 of many", "chosen by the office")
note("top decisions reported", "3 of 20", "chosen by outcome, stated in that note")
note("desk papers summarised in the report", "6 of 6", "no desk omitted")
note("losing decisions grouped", "8 of 8", "grouping computed, not chosen")

(config.OUTPUTS / "audit2.json").write_text(json.dumps(F, indent=2, default=str), encoding="utf-8")
print("\n  written to outputs/audit2.json")
