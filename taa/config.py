"""
Ashcroft University Endowment — tactical asset allocation study.
Single source of truth for the study window, the mandate constants and the
opportunity set.

THE WINDOW IS A PARAMETER, NOT A CONSTANT.
------------------------------------------------------------------------------
Every stage of the study reads the window from here. Nothing else defines it.
Change it in one of three ways and rerun; no other edit is required:

    1. edit WINDOW_START / WINDOW_END below
    2. set env vars  TAA_WINDOW_START=2016-07-01  TAA_WINDOW_END=2026-06-30
    3. write outputs/window.json  {"start": "...", "end": "..."}   (highest precedence)

The quarterly meeting calendar, the monthly return series, the estimation
prefix, the dashboard and every chart derive from these two dates.

Mandate constants below are transcribed from the Investment Policy Statement,
Ashcroft University Endowment, Version 7.2, effective 1 July 2026, adopted by
the Board of Trustees 18 June 2026.  Section references are to that document.
Where the working extract MANDATE.md differs from the IPS, the IPS governs
(IPS preamble) and the difference is recorded in outputs/mandate_diff.json.
"""

from __future__ import annotations

import datetime as _dt
import json as _json
import os as _os
from pathlib import Path as _Path

# --------------------------------------------------------------------------
# Paths
# --------------------------------------------------------------------------
ROOT = _Path(__file__).resolve().parent.parent
# TAA_DATA_DIR lets tests/mutation_test.py run a sandbox copy of the package
# against the real cache instead of duplicating several megabytes of it.
DATA = _Path(_os.environ.get("TAA_DATA_DIR", str(ROOT / "data")))
RAW = DATA / "raw"
OUTPUTS = _Path(_os.environ.get("TAA_OUTPUT_DIR", str(ROOT / "outputs")))
DESKS = ROOT / "desks"
TESTS = ROOT / "tests"
REPORT = ROOT / "report"

for _p in (DATA, RAW, OUTPUTS, DESKS, TESTS, REPORT):
    _p.mkdir(parents=True, exist_ok=True)


# --------------------------------------------------------------------------
# The study window
# --------------------------------------------------------------------------
_DEFAULT_START = "2021-07-01"   # inception of the programme; fiscal year begins 1 July
_DEFAULT_END = "2026-06-30"     # last complete fiscal year end before the report date


def _resolve_window() -> tuple[_dt.date, _dt.date]:
    start, end = _DEFAULT_START, _DEFAULT_END
    start = _os.environ.get("TAA_WINDOW_START", start)
    end = _os.environ.get("TAA_WINDOW_END", end)
    override = OUTPUTS / "window.json"
    if override.exists():
        try:
            blob = _json.loads(override.read_text(encoding="utf-8"))
            start = blob.get("start", start)
            end = blob.get("end", end)
        except Exception:
            pass
    return _dt.date.fromisoformat(start), _dt.date.fromisoformat(end)


WINDOW_START, WINDOW_END = _resolve_window()

# The date the office is standing on when it writes the report.
REPORT_DATE = _dt.date.fromisoformat(_os.environ.get("TAA_REPORT_DATE", "2026-07-28"))

# How much history before WINDOW_START the estimators may see. This is prior
# history, not the study window: it exists so that an expanding-window mean or
# a 36-month covariance has something to stand on at the first meeting. It is
# still read point-in-time.
ESTIMATION_PREFIX_YEARS = 12


def window() -> dict:
    """Everything downstream derives from this."""
    return {
        "start": WINDOW_START.isoformat(),
        "end": WINDOW_END.isoformat(),
        "report_date": REPORT_DATE.isoformat(),
        "months": _month_count(WINDOW_START, WINDOW_END),
        "quarters": len(meeting_dates()),
        "estimation_prefix_years": ESTIMATION_PREFIX_YEARS,
    }


def _month_count(a: _dt.date, b: _dt.date) -> int:
    return (b.year - a.year) * 12 + (b.month - a.month) + (1 if b.day >= 28 else 0)


def _quarter_ends(a: _dt.date, b: _dt.date) -> list[_dt.date]:
    out, y = [], a.year
    while y <= b.year + 1:
        for m, d in ((3, 31), (6, 30), (9, 30), (12, 31)):
            q = _dt.date(y, m, d)
            if a < q <= b:
                out.append(q)
        y += 1
    return sorted(out)


def meeting_dates() -> list[_dt.date]:
    """
    Investment Committee meets quarterly (IPS 2.2). A meeting held on a quarter
    end decides the allocation carried through the following quarter. The first
    meeting inside the window is the first quarter end after WINDOW_START.
    """
    return _quarter_ends(WINDOW_START, WINDOW_END)


def month_ends() -> list[_dt.date]:
    out = []
    y, m = WINDOW_START.year, WINDOW_START.month
    while True:
        if m == 12:
            nxt = _dt.date(y + 1, 1, 1)
        else:
            nxt = _dt.date(y, m + 1, 1)
        me = nxt - _dt.timedelta(days=1)
        if me > WINDOW_END:
            break
        if me >= WINDOW_START:
            out.append(me)
        y, m = nxt.year, nxt.month
    return out


def trailing_twelve_months() -> list[_dt.date]:
    me = month_ends()
    return me[-12:]


def fiscal_years() -> list[tuple[str, _dt.date, _dt.date]]:
    """Fiscal year ends 30 June, matching the IPS reporting cycle."""
    out = []
    for me in month_ends():
        if me.month == 6:
            fy = f"FY{me.year}"
            start = _dt.date(me.year - 1, 7, 1)
            out.append((fy, max(start, WINDOW_START), me))
    last = month_ends()[-1]
    if last.month != 6:
        fy = f"FY{last.year + (1 if last.month > 6 else 0)}"
        start = _dt.date(last.year if last.month > 6 else last.year - 1, 7, 1)
        out.append((fy + " (part)", max(start, WINDOW_START), last))
    return out


# --------------------------------------------------------------------------
# The fund  (IPS cover page, 1.1, 3.2, 3.4)
# --------------------------------------------------------------------------
FUND_NAV_USD = 850_000_000          # IPS cover page, as at 30 June 2026
SPENDING_RATE = 0.045               # IPS 3.2
HEPI = 0.032                        # IPS 3.2
FEES = 0.004                        # IPS 3.2
REQUIRED_RETURN = 0.081             # IPS 3.2 — arithmetic, not aspiration
ANNUAL_DISTRIBUTION_USD = 38_000_000
CAMPAIGN_INFLOW_USD = 60_000_000    # IPS 3.4, expected year three
OPERATING_BUDGET_DEPENDENCY = 0.18  # IPS 1.1

# --------------------------------------------------------------------------
# Hard limits  (IPS 3.3, 3.4, 3.5, 4.2, 4.5)
# --------------------------------------------------------------------------
DRAWDOWN_LIMIT = -0.20              # IPS 3.3, peak to trough, hierarchy rank 3
TE_BUDGET_BPS = 200.0               # IPS 4.2, ex ante, hierarchy rank 4
MIN_TRADE_PP = 0.50                 # IPS 4.2, percentage points of NAV
LIQUIDITY_FLOOR = 0.15              # IPS 3.4, realisable within five business days
MAX_NEW_LOCKUPS = 0.10              # IPS 3.4
MAX_GROSS_EXPOSURE = 1.00           # IPS 3.5, no leverage at fund level (UBTI)
BOARD_EXCLUSIONS = ("tobacco", "thermal coal")   # IPS 3.5

CONSTRAINT_HIERARCHY = [            # IPS 3.6, pre-committed
    (1, "liquidity", "Liquidity. The distribution is funded.", "not negotiable"),
    (2, "legal", "Legal, UBTI, board exclusions", "not negotiable"),
    (3, "drawdown", "Drawdown limit, -20% peak to trough", "hard"),
    (4, "tracking_error", "Tracking error budget, 200bps ex ante", "hard"),
    (5, "return_objective", "Return objective, 8.10%", "best efforts"),
]

# --------------------------------------------------------------------------
# The opportunity set  (IPS 4.1)
# --------------------------------------------------------------------------
LINES = [
    "us_equity", "dev_ex_us", "em_equity",
    "ust_duration", "us_ig", "us_hy",
    "commodities", "listed_re", "cash",
]

LINE_LABEL = {
    "us_equity": "US equity",
    "dev_ex_us": "Developed ex-US",
    "em_equity": "Emerging markets",
    "ust_duration": "US Treasury duration",
    "us_ig": "US investment grade",
    "us_hy": "US high yield",
    "commodities": "Commodities",
    "listed_re": "Listed real estate",
    "cash": "T-bills",
}

SLEEVE = {
    "us_equity": "equity", "dev_ex_us": "equity", "em_equity": "equity",
    "ust_duration": "fixed_income", "us_ig": "fixed_income", "us_hy": "fixed_income",
    "commodities": "real_assets", "listed_re": "real_assets",
    "cash": "cash",
}

POLICY = {
    "us_equity": 0.38, "dev_ex_us": 0.20, "em_equity": 0.12,
    "ust_duration": 0.12, "us_ig": 0.08, "us_hy": 0.05,
    "commodities": 0.03, "listed_re": 0.02, "cash": 0.00,
}

RANGE = {                            # IPS 4.1, binds independently of the TE budget
    "us_equity": (0.28, 0.48),
    "dev_ex_us": (0.12, 0.28),
    "em_equity": (0.05, 0.19),
    "ust_duration": (0.05, 0.22),
    "us_ig": (0.03, 0.13),
    "us_hy": (0.00, 0.10),
    "commodities": (0.00, 0.08),
    "listed_re": (0.00, 0.06),
    "cash": (0.00, 0.10),
}

SLEEVE_RANGE = {                     # IPS 4.1
    "equity": (0.60, 0.80),
    "fixed_income": (0.15, 0.35),
    "real_assets": (0.00, 0.10),
}

# Primary vehicle per line, and the date from which that vehicle was investable.
# IPS 4.1: "Investable dates bind." Listing dates below are the fund inception
# dates of the named vehicles and are verified against the price history pulled
# by taa/datapull.py; taa/pitdata.py refuses a line before its investable date.
VEHICLE = {
    "us_equity": "SPY", "dev_ex_us": "EFA", "em_equity": "EEM",
    "ust_duration": "IEF", "us_ig": "LQD", "us_hy": "HYG",
    "commodities": "DBC", "listed_re": "VNQ", "cash": "BIL",
}

VEHICLE_ALT = {
    "us_equity": "VTI", "dev_ex_us": "VEA", "em_equity": "VWO",
    "ust_duration": "TLT", "us_ig": "LQD", "us_hy": "HYG",
    "commodities": "GSG", "listed_re": "VNQ", "cash": "SGOV",
}

INVESTABLE_FROM = {                  # IPS 4.1 names four of these explicitly
    "us_equity": _dt.date(1993, 1, 29),    # SPY
    "dev_ex_us": _dt.date(2001, 8, 14),    # EFA
    "em_equity": _dt.date(2003, 4, 11),    # EEM   (IPS: from 2003)
    "ust_duration": _dt.date(2002, 7, 26), # IEF
    "us_ig": _dt.date(2002, 7, 26),        # LQD
    "us_hy": _dt.date(2007, 4, 11),        # HYG   (IPS: from 2007)
    "commodities": _dt.date(2006, 2, 3),   # DBC   (IPS: from 2006)
    "listed_re": _dt.date(2004, 9, 23),    # VNQ   (IPS: from 2004)
    "cash": _dt.date(2007, 5, 30),         # BIL
}

# Assets realisable within five business days, for the IPS 3.4 liquidity floor.
# Every vehicle in the opportunity set is a daily-liquid ETF (IPS 1.2, 3.5), so
# the floor is tested against the lines whose vehicles clear same-week at size.
LIQUID_WITHIN_5D = {
    "us_equity": True, "dev_ex_us": True, "em_equity": True,
    "ust_duration": True, "us_ig": True, "us_hy": True,
    "commodities": True, "listed_re": True, "cash": True,
}


def policy_vector() -> list[float]:
    return [POLICY[k] for k in LINES]


def check_policy_consistency() -> None:
    tot = round(sum(POLICY.values()), 10)
    assert tot == 1.0, f"policy weights sum to {tot}, not 1.0"
    for k in LINES:
        lo, hi = RANGE[k]
        assert lo <= POLICY[k] <= hi, f"{k} policy {POLICY[k]} outside range {lo}-{hi}"
    for sl, (lo, hi) in SLEEVE_RANGE.items():
        w = sum(POLICY[k] for k in LINES if SLEEVE[k] == sl)
        assert lo <= w <= hi, f"sleeve {sl} policy {w} outside {lo}-{hi}"


if __name__ == "__main__":
    check_policy_consistency()
    w = window()
    print("STUDY WINDOW")
    for k, v in w.items():
        print(f"  {k:24s} {v}")
    print(f"\n  first meeting            {meeting_dates()[0]}")
    print(f"  last meeting             {meeting_dates()[-1]}")
    print(f"  meetings                 {len(meeting_dates())}")
    print(f"  monthly observations     {len(month_ends())}")
    print(f"  fiscal years             {[f[0] for f in fiscal_years()]}")
    print("\n  policy consistency       PASS")
