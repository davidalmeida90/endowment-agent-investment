"""
The audit pass. Gathers evidence for AUDIT.md.

This does not change any result. It interrogates the study for the things a
reader should not trust, and writes what it finds to outputs/audit.json so the
written audit can be checked against it rather than believed.

Run:  py -3 tests/audit.py
"""

from __future__ import annotations

import ast
import datetime as dt
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import pandas as pd  # noqa: E402

from taa import config, pitdata  # noqa: E402

F: dict = {}


def head(t):
    print(f"\n{t}\n" + "-" * len(t))


def note(k, v, detail=""):
    F[k] = {"value": v, "detail": detail}
    print(f"  {k:44s} {str(v):>10s}  {detail}")


# ==========================================================================
head("1. FUTURE DATA IN DECISIONS")

rec = json.loads((config.OUTPUTS / "decision_record.json").read_text(encoding="utf-8"))
decs = rec["decisions"]

# every date-like token in every non-outcome field, against the meeting date
DATE_RX = re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b")
worst = None
viol = 0
for e in decs:
    d = dt.date.fromisoformat(e["date"])
    blob = json.dumps({k: v for k, v in e.items() if k != "outcome"})
    for m in DATE_RX.finditer(blob):
        try:
            f = dt.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            continue
        if f > d:
            viol += 1
            worst = (e["date"], str(f))
note("decision fields referencing a later date", viol, str(worst or "none"))

# the outcome block is the only place forward information may live
missing_outcome = sum(1 for e in decs if not isinstance(e.get("outcome"), dict))
note("decisions missing an outcome block", missing_outcome)

# ==========================================================================
head("2. THE POINT-IN-TIME ACCESS LOG")

log = config.OUTPUTS / "pit_access_log.jsonl"
rows, bad = [], 0
for line in log.read_text(encoding="utf-8").splitlines():
    if not line.strip():
        continue
    try:
        rows.append(json.loads(line))
    except Exception:
        bad += 1
note("access log entries", len(rows))
note("access log lines corrupted by concurrent writes", bad,
     f"{bad / max(len(rows) + bad, 1) * 100:.3f}% of writes")

late = 0
for r in rows:
    a, lo = r.get("as_of"), r.get("last_obs")
    if a and lo and lo > a:
        late += 1
note("reads returning an observation after the as-of date", late)

anach = [r for r in rows if r.get("kind") == "STATIC_ANACHRONISM"]
note("anachronistic (current-vintage) inputs admitted", len(anach),
     "; ".join(sorted({a.get("series", "") for a in anach})) or "none")

kinds = {}
for r in rows:
    kinds[r.get("kind", "?")] = kinds.get(r.get("kind", "?"), 0) + 1
note("read kinds", len(kinds), str(kinds))

# ==========================================================================
head("3. DO THE EXTRA CLAIM VINTAGES CHANGE ANY MEETING'S READ?")
# The Macro desk added BEA release dates to the vintage set. If any of them sits
# between a meeting date and that meeting's own vintage, the meeting would read
# a vintage it should not have. Checked rather than assumed.
try:
    from taa.datapull import CLAIM_VINTAGES
except Exception:
    CLAIM_VINTAGES = []
meetings = config.meeting_dates()

# The definitive test, not a heuristic: for every meeting and every vintage
# series, confirm the vintage actually served is that meeting's own dated file.
# If it is, an extra claim vintage sitting between two meetings cannot reach a
# decision, because the resolver takes the latest vintage at or before the
# as-of date and an exact match always exists.
wrong = []
for m in meetings:
    for sid in pitdata.VINTAGE_ALFRED:
        key = pitdata._nearest_vintage_key(sid, m)
        if not key or not key.endswith(m.isoformat()):
            wrong.append((str(m), sid, key))
note("meeting/series reads not using that meeting's own vintage", len(wrong),
     str(wrong[:2]) if wrong else
     f"0 of {len(meetings) * len(pitdata.VINTAGE_ALFRED)} checked; claim vintages cannot reach a decision")
note("extra claim vintages added by the Macro desk", len(CLAIM_VINTAGES),
     "used only for the published-print demonstration, never by a meeting")

# ==========================================================================
head("4. WHAT THE DESKS SAID THEY DID NOT VERIFY")

sysj = json.loads((config.OUTPUTS / "systematic_evidence.json").read_text(encoding="utf-8"))
claims = sysj.get("claims", [])
recalled = [c for c in claims if c.get("status") != "VERIFIED"]
note("systematic desk claims", len(claims))
note("of those, RECALLED rather than verified", len(recalled),
     f"{len(recalled) / max(len(claims),1) * 100:.0f}%")

impl = json.loads((config.OUTPUTS / "implementation.json").read_text(encoding="utf-8"))
blob = json.dumps(impl)
note("implementation desk RECALLED markers", blob.count("RECALLED"))

cme = json.loads((config.OUTPUTS / "cme.json").read_text(encoding="utf-8"))
srcs = cme.get("sources", [])
nourl = [s for s in srcs if not s.get("url")]
note("capital markets houses cited", len(srcs), f"{len(nourl)} without a URL")

# ==========================================================================
head("5. STATISTICAL STRENGTH")

five = rec["summary"]
n = five["months"]
sr = five["portfolio"]["sharpe"]
se = five["portfolio"]["sharpe_stderr"]
ir = five["active"]["information_ratio"]
note("monthly observations", n)
note("years", f"{n/12:.1f}")
note("Sharpe ratio", f"{sr:.3f}", f"standard error {se:.3f} (Lo 2002, iid)")
note("Sharpe 95% interval", f"[{sr-1.96*se:+.2f}, {sr+1.96*se:+.2f}]",
     "contains zero" if sr - 1.96 * se < 0 else "excludes zero")
ir_se = (12 / n) ** 0.5
note("information ratio", f"{ir:.3f}", f"approx SE {ir_se:.2f}")
note("IR 95% interval", f"[{ir-1.96*ir_se:+.2f}, {ir+1.96*ir_se:+.2f}]",
     "contains zero" if ir - 1.96 * ir_se < 0 else "excludes zero")

# window sensitivity: the same programme on shorter windows
idx = pd.to_datetime(rec["monthly"]["dates"])
s = pd.Series(rec["monthly"]["strategy"], index=idx)
b = pd.Series(rec["monthly"]["benchmark"], index=idx)
sens = {}
for months in (12, 24, 36, 48, 60):
    ss, bb = s.iloc[-months:], b.iloc[-months:]
    a = float((1 + ss).prod() ** (12 / months) - (1 + bb).prod() ** (12 / months)) * 10000
    sens[f"{months}m"] = round(a, 1)
note("active return a year, by window", "see detail", str(sens))
F["window_sensitivity_bps"] = sens

# ==========================================================================
head("6. DATA COVERAGE GAPS")

v = pitdata.as_of(config.WINDOW_END)
gaps = {}
for sid in ("BAMLC0A0CM", "BAMLH0A0HYM2", "BAA10Y", "DGS10"):
    try:
        ser = v.fred(sid)
        gaps[sid] = {"first": str(ser.index.min().date()), "n": int(len(ser))}
    except Exception as e:
        gaps[sid] = {"error": type(e).__name__}
note("credit/rate series coverage", "see detail", json.dumps(gaps))
F["series_coverage"] = gaps

blind = sum(1 for m in config.meeting_dates() if m < dt.date(2023, 7, 31))
note("meetings before the ICE OAS series begins", f"{blind} of {len(config.meeting_dates())}",
     "ran on fewer liquidity indicators")

px = v.prices(["SPY"])
note("price cache begins", str(px.index.min().date()), "2008 crisis is outside the replay")

miss = rec.get("missing_observations", {})
note("months with a missing line return", sum(miss.values()) if miss else 0, str(miss or "none"))

# ==========================================================================
head("7. MODELLING CHOICES WITH A LARGE PRESENTATIONAL EFFECT")

fail = sum(1 for e in decs if not e["compliance"]["passed"])
breach = sum(1 for e in decs if e["compliance"]["fund_in_breach"])
note("allocations recorded as failing compliance", f"{fail} of {len(decs)}")
note("quarters recorded as the FUND in breach", f"{breach} of {len(decs)}",
     "reclassified from allocation failure; see AUDIT.md item 7")
remed = sum(1 for e in decs if e["compliance"]["remediation_rounds"] > 0)
note("allocations that needed remediation", f"{remed} of {len(decs)}")

# ==========================================================================
head("8. WHAT IS SIMULATED RATHER THAN OBSERVED")
note("committee meetings actually held", 0, "the record is a simulation of a rule")
note("historical decisions that were deliberated", 0, "all twenty are mechanical")
note("live decisions that were deliberated", 1, "the FY2027 recommendation")
note("transaction costs", "modelled", "static per-line vector, no live execution")

(config.OUTPUTS / "audit.json").write_text(json.dumps(F, indent=2, default=str), encoding="utf-8")
print(f"\n  written to outputs/audit.json")
