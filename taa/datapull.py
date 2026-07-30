"""
taa.datapull — ingestion. Writes the raw cache; never reads it for analysis.

This is the only module allowed to touch the network. It pulls to disk once and
everything downstream runs offline against the cache, so a trustee who clones
the folder reproduces every number without a network connection and without
credentials.

Public sources only (IPS 4.4). No API key is used anywhere in this study:

  Prices      Yahoo Finance daily OHLC and adjusted close, via yfinance.
  Market rates FRED CSV endpoint, fredgraph.csv. No key required.
  Macro vintages ALFRED CSV endpoint, alfredgraph.csv?vintage_date=. No key
              required. This is what makes the point-in-time wall real rather
              than aspirational: it serves the series as it was published on a
              stated date.

Run:  py -3 -m taa.datapull            (incremental; skips what is cached)
      py -3 -m taa.datapull --force    (refetch everything)
"""

from __future__ import annotations

import datetime as _dt
import io
import sys

import pandas as pd

from . import _rawstore, config, pitdata

FRED_CSV = "https://fred.stlouisfed.org/graph/fredgraph.csv?id={sid}&cosd={start}&coed={end}"
ALFRED_CSV = ("https://alfred.stlouisfed.org/graph/alfredgraph.csv"
              "?id={sid}&vintage_date={vintage}&cosd={start}&coed={vintage}")

ALL_TICKERS = sorted(set(list(config.VEHICLE.values()) + list(config.VEHICLE_ALT.values())))

# --------------------------------------------------------------------------
# Claim vintages.
#
# The committee calendar is the set of dates on which the study forms a VIEW.
# It is not the set of dates on which the study makes a CLAIM about what was
# published. A BEA release lands on a Thursday in the middle of a quarter, so a
# quarter-end vintage cannot show what a release said on the day it landed, and
# a desk that asserts "this printed at X on date D" while reading the vintage
# from the previous quarter end is asserting something it has not looked at.
#
# These are BEA release dates on which this study asserts a specific published
# figure. Adding them is additive: pitdata._nearest_vintage_key takes the latest
# vintage at or before the as-of date, and none of these falls between a meeting
# date and that meeting's own vintage, so no committee-date read changes.
# --------------------------------------------------------------------------
CLAIM_VINTAGES = [
    _dt.date(2022, 4, 28),   # 2022 Q1 real GDP, advance estimate
    _dt.date(2022, 7, 28),   # 2022 Q2 real GDP, advance estimate  (the -0.9% print)
    _dt.date(2022, 8, 25),   # 2022 Q2 second estimate
    _dt.date(2022, 9, 29),   # 2022 Q2 third estimate + 2022 annual update
    _dt.date(2024, 9, 25),   # day before the 2024 annual update, control observation
    _dt.date(2024, 9, 26),   # 2024 annual update of the national accounts
]


def _hist_start() -> _dt.date:
    return _dt.date(config.WINDOW_START.year - config.ESTIMATION_PREFIX_YEARS,
                    config.WINDOW_START.month, 1)


# --------------------------------------------------------------------------
def pull_prices(force: bool = False) -> None:
    import yfinance as yf

    start = _hist_start().isoformat()
    end = (config.REPORT_DATE + _dt.timedelta(days=1)).isoformat()
    for t in ALL_TICKERS:
        key = f"px_{t}"
        if _rawstore.exists(key) and not force:
            print(f"  px {t:6s} cached")
            continue
        df = yf.download(t, start=start, end=end, auto_adjust=False,
                         progress=False, actions=False)
        if df is None or len(df) == 0:
            print(f"  px {t:6s} EMPTY")
            continue
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        out = pd.DataFrame({
            "date": pd.to_datetime(df.index).date,
            "close": df["Close"].astype(float).values,
            "adj_close": (df["Adj Close"] if "Adj Close" in df.columns
                          else df["Close"]).astype(float).values,
            "volume": df["Volume"].astype("int64").values,
        })
        _rawstore.write(key, out.to_csv(index=False),
                        {"source": "Yahoo Finance via yfinance", "ticker": t,
                         "first": str(out["date"].iloc[0]), "last": str(out["date"].iloc[-1]),
                         "rows": len(out), "field_note": "adj_close is dividend and split adjusted"})
        print(f"  px {t:6s} {len(out):5d} rows  {out['date'].iloc[0]} .. {out['date'].iloc[-1]}")


def pull_fred(force: bool = False) -> None:
    start = _hist_start().isoformat()
    end = config.REPORT_DATE.isoformat()
    for sid, (label, lag) in pitdata.MARKET_FRED.items():
        key = f"fred_{sid}"
        if _rawstore.exists(key) and not force:
            print(f"  fred {sid:14s} cached")
            continue
        txt = _rawstore.http_get(FRED_CSV.format(sid=sid, start=start, end=end))
        df = pd.read_csv(io.StringIO(txt))
        _rawstore.write(key, txt, {"source": "FRED fredgraph.csv (no key)", "series": sid,
                                   "label": label, "publication_lag_days": lag,
                                   "rows": len(df)})
        print(f"  fred {sid:14s} {len(df):5d} rows")


def pull_alfred_vintages(force: bool = False) -> None:
    """
    One ALFRED request per (series, vintage). Vintages are the committee meeting
    dates plus the report date, which is exactly the set of dates on which this
    study forms a view.
    """
    vintages = sorted(set(list(config.meeting_dates()) + [config.REPORT_DATE] + CLAIM_VINTAGES))
    start = _dt.date(config.WINDOW_START.year - 20, 1, 1).isoformat()
    n_new = 0
    for sid in pitdata.VINTAGE_ALFRED:
        for v in vintages:
            key = f"alfred_{sid}_{v.isoformat()}"
            if _rawstore.exists(key) and not force:
                continue
            txt = _rawstore.http_get(ALFRED_CSV.format(sid=sid, vintage=v.isoformat(), start=start))
            _rawstore.write(key, txt, {"source": "ALFRED alfredgraph.csv (no key)",
                                       "series": sid, "vintage_date": v.isoformat(),
                                       "label": pitdata.VINTAGE_ALFRED[sid]})
            n_new += 1
        print(f"  alfred {sid:12s} {len(vintages)} vintages")
    print(f"  alfred: {n_new} new vintage files")


def pull_static(force: bool = False) -> None:
    """
    Series with no vintage history. Admitted only through pitdata.static() with
    a stated reason, and reported as an anachronism wherever used historically.

    house_cme is the clearest example the study has of the problem the brief
    describes: a published long-horizon house forecast from three years ago is
    often simply gone from the internet. Only the current vintage exists. Using
    it inside a historical decision is therefore an anachronism by construction,
    which is exactly why it is registered here rather than alongside the market
    series, and why pitdata.static() refuses to serve it without a stated reason.
    """
    key = "static_house_cme"
    if not _rawstore.exists(key) or force:
        src = config.OUTPUTS / "cme.json"
        rows = ["date,line,expected_return"]
        if src.exists():
            import json
            blob = json.loads(src.read_text(encoding="utf-8"))
            asof = blob.get("as_of", config.REPORT_DATE.isoformat())
            for ln, v in blob.get("lines", {}).items():
                rows.append(f"{asof},{ln},{v.get('adopted')}")
        else:
            rows.append(f"{config.REPORT_DATE.isoformat()},us_equity,")
        _rawstore.write(key, "\n".join(rows) + "\n",
                        {"source": "Capital Markets desk, outputs/cme.json",
                         "vintage_history": "none — current vintage only",
                         "note": "anachronistic in any historical context"})
        print(f"  static house_cme written, {len(rows) - 1} lines")
    else:
        print("  static house_cme cached")

    key = "static_shiller_ie"
    if _rawstore.exists(key) and not force:
        print("  static shiller_ie cached")
        return
    for url in ("https://shillerdata.com/wp-content/uploads/2025/01/ie_data.xls",
                "http://www.econ.yale.edu/~shiller/data/ie_data.xls"):
        try:
            _rawstore.http_get(url)
            print(f"  static shiller_ie reachable at {url}, not parsed (xls, needs xlrd)")
            break
        except Exception as e:
            print(f"  static shiller_ie unavailable at {url}: {type(e).__name__}")


def main(argv: list[str]) -> int:
    force = "--force" in argv
    print(f"Ashcroft TAA study — data pull")
    print(f"  window        {config.WINDOW_START} .. {config.WINDOW_END}")
    print(f"  history from  {_hist_start()}")
    print(f"  report date   {config.REPORT_DATE}")
    print("\nPrices (Yahoo Finance)")
    pull_prices(force)
    print("\nMarket rates and spreads (FRED, no key)")
    pull_fred(force)
    print("\nMacro vintages (ALFRED, no key) — one per committee meeting date")
    pull_alfred_vintages(force)
    print("\nStatic / current-vintage")
    pull_static(force)
    print("\nDone.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
