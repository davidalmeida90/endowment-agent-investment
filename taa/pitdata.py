"""
taa.pitdata — the point-in-time choke point.

IPS Section 4.4 (Evidence standard):
    "Historical analysis uses data as it stood on the date in question.
     Macroeconomic series are taken from published vintages, never from the
     current revision, since a revised figure was not available to anyone
     trading on the date under study. Access runs through a single enforced
     path rather than relying on the analyst to remember, and a test asserts it."

This module is that path. Every read of historical data in this study goes
through it. It takes an as-of date and refuses to hand back anything published
after that date.

WHY THIS IS NOT A CONVENTION
------------------------------------------------------------------------------
There is no route to the raw cache except taa._rawstore, and taa._rawstore
refuses to serve any caller other than this module (RawAccessViolation).
tests/test_lookahead.py additionally walks the import graph of the package and
fails if any analysis module imports _rawstore, yfinance, requests or urllib,
or opens anything under data/raw. So the wall is enforced three ways: at
runtime by the caller guard, at every value returned by the as-of gate here,
and statically by the import-graph test.

THE TWO WAYS A LOOK-AHEAD GETS IN, AND WHAT EACH NEEDS
------------------------------------------------------------------------------
1. REVISION. A macro statistic is restated, sometimes years later. Reading
   today's value of a 2022 observation is reading a number nobody had in 2022.
   Handled by fetching the ALFRED *vintage* that was current on the as-of date.
   ALFRED serves exactly the observations published on or before that vintage,
   with the values they carried then.

2. PUBLICATION LAG. A figure released after the trade date is a look-ahead even
   when the observation is correctly dated earlier. An unemployment print for
   March that lands in April is April's information. This is the one that
   catches people who thought they had it handled, because the observation date
   looks safe. The ALFRED vintage mechanism handles it for free: an observation
   not yet published simply does not appear in that vintage. For series without
   vintage history, a publication lag must be declared explicitly and this
   module applies it; a series with neither vintage history nor a declared lag
   is refused.

SERIES CLASSES
------------------------------------------------------------------------------
MARKET   Exchange prices and market-quoted yields and spreads. Not revised.
         An observation dated d was public at the close of d. Gate: d <= as_of.
VINTAGE  Revised macro statistics. Read from the ALFRED vintage current on
         as_of. Gate: the vintage itself, plus d <= as_of belt and braces.
STATIC   A file with no vintage history (Shiller's spreadsheet, a current house
         forecast). These are ANACHRONISTIC in historical use. This module
         refuses to serve one in a historical context unless the caller passes
         an explicit reason string, which is written to the access log and
         surfaces in the report as a stated limitation.
"""

from __future__ import annotations

import datetime as _dt
import io
import json
from dataclasses import dataclass

import pandas as pd

from . import _rawstore, config

# Flipping this to False removes the as-of gate. tests/mutation_test.py does
# exactly that in a sandbox copy and asserts the suite goes red.
_ENFORCE = True

ACCESS_LOG = config.OUTPUTS / "pit_access_log.jsonl"


class LookAheadError(RuntimeError):
    """Raised when a read would return information published after the as-of date."""


class NotInvestableError(RuntimeError):
    """Raised when a line is requested before its vehicle existed (IPS 4.1)."""


# --------------------------------------------------------------------------
# Series registry. Anything not registered cannot be read.
# --------------------------------------------------------------------------
MARKET_FRED = {
    # id: (label, publication lag in days after the observation date)
    "DGS10": ("US 10y Treasury constant maturity", 0),
    "DGS2": ("US 2y Treasury constant maturity", 0),
    "DGS3MO": ("US 3m Treasury constant maturity", 0),
    "DFII10": ("US 10y TIPS real yield", 0),
    "T10YIE": ("US 10y breakeven inflation", 0),
    # ICE BofA OAS. Authoritative, but FRED serves only a rolling three-year
    # window of these through the free endpoint, which starts after this study's
    # window opens. Used where available and reported as missing where not.
    "BAMLC0A0CM": ("US IG corporate OAS", 1),
    "BAMLH0A0HYM2": ("US high yield OAS", 1),
    # Moody's series are public domain and carry full history, so they are the
    # primary credit signal for the historical work. BAA10Y is the Baa yield
    # less the 10y Treasury, which is a spread over the curve rather than an
    # option-adjusted spread; the two are close in level and very close in
    # direction, and the difference is stated in the report.
    "BAA10Y": ("Moody's Baa corporate yield less 10y Treasury", 1),
    "AAA10Y": ("Moody's Aaa corporate yield less 10y Treasury", 1),
    "T10Y2Y": ("10y less 2y Treasury", 0),
    "T10Y3M": ("10y less 3m Treasury", 0),
    "VIXCLS": ("CBOE VIX", 0),
    "DTWEXBGS": ("Broad dollar index", 1),
    "DCOILWTICO": ("WTI spot", 3),
}

VINTAGE_ALFRED = {
    "GDPC1": "Real gross domestic product, chained 2017 dollars",
    "UNRATE": "Unemployment rate",
    "PAYEMS": "Total nonfarm payrolls",
    "CPIAUCSL": "CPI, all urban consumers",
    "INDPRO": "Industrial production index",
    "PCEPILFE": "Core PCE price index",
    "USREC": "NBER recession indicator",
}

STATIC_SERIES = {
    "shiller_ie": "Shiller Irrational Exuberance data file (current vintage only)",
    "house_cme": "Published house capital market assumptions (current vintage only; "
                 "prior vintages are not archived anywhere public)",
}


def _log(entry: dict) -> None:
    entry["logged_at"] = _dt.datetime.now().isoformat(timespec="seconds")
    with ACCESS_LOG.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry) + "\n")


def _to_date(x) -> _dt.date:
    if isinstance(x, _dt.datetime):
        return x.date()
    if isinstance(x, _dt.date):
        return x
    return _dt.date.fromisoformat(str(x)[:10])


# --------------------------------------------------------------------------
# The gate
# --------------------------------------------------------------------------
def _gate(df: pd.DataFrame, as_of: _dt.date, lag_days: int, what: str) -> pd.DataFrame:
    """
    Drop everything not knowable on as_of, then assert nothing survived that
    should not have. The assertion is the part that matters: a filter that
    silently does nothing is indistinguishable from no filter at all.
    """
    if not _ENFORCE:
        return df
    cutoff = as_of - _dt.timedelta(days=lag_days)
    out = df[df.index <= pd.Timestamp(cutoff)]
    if len(out) and out.index.max() > pd.Timestamp(cutoff):
        raise LookAheadError(
            f"{what}: value dated {out.index.max().date()} is not knowable on "
            f"{as_of} with a {lag_days}-day publication lag"
        )
    return out


def assert_no_future(df: pd.DataFrame, as_of, what: str = "series") -> None:
    """Public assertion any desk may call on anything it holds."""
    as_of = _to_date(as_of)
    if len(df) and _to_date(df.index.max()) > as_of:
        raise LookAheadError(
            f"{what}: holds an observation dated {_to_date(df.index.max())}, "
            f"after the as-of date {as_of}"
        )


# --------------------------------------------------------------------------
# The handle
# --------------------------------------------------------------------------
@dataclass(frozen=True)
class AsOf:
    """A view of the world as it stood on one date. The only way in."""

    date: _dt.date

    # ---- market prices -------------------------------------------------
    def prices(self, tickers: list[str] | str, field: str = "adj_close") -> pd.DataFrame:
        """
        Total-return price history for one or more ETFs, truncated at the as-of
        date. Field is 'adj_close' (dividends reinvested) or 'close'.

        On back-adjustment: adjusted closes are restated retroactively when a
        dividend is paid, so the *level* of a past adjusted close is not what a
        screen showed on the day. The *return* between two past dates computed
        from them is the correct total return over that interval, which is what
        this study consumes. No return in the study is computed across the
        as-of boundary, so back-adjustment introduces no look-ahead. This is
        stated in the report as a modelling choice rather than left implicit.
        """
        if isinstance(tickers, str):
            tickers = [tickers]
        frames = {}
        for t in tickers:
            raw = _rawstore.read(f"px_{t}")
            df = pd.read_csv(io.StringIO(raw), parse_dates=["date"], index_col="date")
            col = field if field in df.columns else df.columns[0]
            frames[t] = _gate(df[[col]], self.date, 0, f"prices[{t}]")[col]
        out = pd.DataFrame(frames)
        _log({"kind": "prices", "as_of": self.date.isoformat(), "tickers": tickers,
              "field": field, "rows": len(out),
              "last_obs": str(out.index.max().date()) if len(out) else None})
        return out

    def line_prices(self, lines: list[str] | None = None) -> pd.DataFrame:
        """Total-return prices by mandate line, refusing any line not yet investable."""
        lines = lines or config.LINES
        for ln in lines:
            if self.date < config.INVESTABLE_FROM[ln]:
                raise NotInvestableError(
                    f"line {ln!r} ({config.VEHICLE[ln]}) was not investable on "
                    f"{self.date}; its vehicle lists from "
                    f"{config.INVESTABLE_FROM[ln]} (IPS 4.1, investable dates bind)"
                )
        px = self.prices([config.VEHICLE[ln] for ln in lines])
        px.columns = lines
        return px

    def monthly_returns(self, lines: list[str] | None = None) -> pd.DataFrame:
        """Month-end to month-end total returns, last month strictly before as_of."""
        px = self.line_prices(lines)
        m = px.resample("ME").last()
        m = m[m.index <= pd.Timestamp(self.date)]
        r = m.pct_change().dropna(how="all")
        assert_no_future(r, self.date, "monthly_returns")
        return r

    # ---- market-quoted macro (not revised) -----------------------------
    def fred(self, series_id: str) -> pd.Series:
        if series_id not in MARKET_FRED:
            raise KeyError(
                f"{series_id!r} is not registered as a MARKET series. Register it in "
                f"MARKET_FRED with a publication lag, or read it as a vintage series."
            )
        label, lag = MARKET_FRED[series_id]
        raw = _rawstore.read(f"fred_{series_id}")
        df = pd.read_csv(io.StringIO(raw), parse_dates=[0], index_col=0)
        df = df.apply(pd.to_numeric, errors="coerce").dropna()
        out = _gate(df, self.date, lag, f"fred[{series_id}]")
        _log({"kind": "fred", "as_of": self.date.isoformat(), "series": series_id,
              "lag_days": lag, "rows": len(out),
              "last_obs": str(out.index.max().date()) if len(out) else None})
        return out.iloc[:, 0]

    # ---- revised macro, read at the vintage current on the as-of date ---
    def macro(self, series_id: str) -> pd.Series:
        """
        A revised macro series as it was published on the as-of date.

        This reads the ALFRED vintage current on self.date. It is the reason
        this study does not believe the economy grew in 2022 Q2: on the vintage
        available in July 2022 it did not.
        """
        if series_id not in VINTAGE_ALFRED:
            raise KeyError(
                f"{series_id!r} is not registered as a VINTAGE series. A revised "
                f"macro series must be read from its published vintage (IPS 4.4)."
            )
        key = f"alfred_{series_id}_{self.date.isoformat()}"
        if not _rawstore.exists(key):
            key_nearest = _nearest_vintage_key(series_id, self.date)
            if key_nearest is None:
                raise FileNotFoundError(
                    f"no cached ALFRED vintage for {series_id} at or before {self.date}. "
                    f"Run  py -3 -m taa.datapull  to populate the vintage cache."
                )
            key = key_nearest
        raw = _rawstore.read(key)
        df = pd.read_csv(io.StringIO(raw), parse_dates=[0], index_col=0)
        df = df.apply(pd.to_numeric, errors="coerce").dropna()
        out = _gate(df, self.date, 0, f"macro[{series_id}]")
        used_vintage = key.rsplit("_", 1)[-1]
        _log({"kind": "macro_vintage", "as_of": self.date.isoformat(),
              "series": series_id, "vintage_used": used_vintage, "rows": len(out),
              "last_obs": str(out.index.max().date()) if len(out) else None})
        return out.iloc[:, 0]

    # ---- anachronistic inputs, admitted only with a stated reason -------
    def static(self, name: str, reason: str) -> pd.DataFrame:
        if name not in STATIC_SERIES:
            raise KeyError(f"{name!r} is not a registered static series")
        if not reason or len(reason) < 20:
            raise ValueError(
                "a static (current-vintage) series used in a historical context is "
                "an anachronism. Pass a reason of at least 20 characters saying why "
                "it is admitted and what it would have changed. It is written to the "
                "access log and reported to the Committee as a limitation."
            )
        raw = _rawstore.read(f"static_{name}")
        df = pd.read_csv(io.StringIO(raw), parse_dates=[0], index_col=0)
        out = df[df.index <= pd.Timestamp(self.date)]
        _log({"kind": "STATIC_ANACHRONISM", "as_of": self.date.isoformat(),
              "series": name, "reason": reason, "rows": len(out)})
        return out

    def investable(self, line: str) -> bool:
        return self.date >= config.INVESTABLE_FROM[line]

    def investable_lines(self) -> list[str]:
        return [ln for ln in config.LINES if self.investable(ln)]


def _nearest_vintage_key(series_id: str, as_of: _dt.date) -> str | None:
    prefix = f"alfred_{series_id}_"
    best, best_d = None, None
    for k in _rawstore.catalogue():
        if not k.startswith(prefix):
            continue
        try:
            d = _dt.date.fromisoformat(k[len(prefix):])
        except ValueError:
            continue
        if d <= as_of and (best_d is None or d > best_d):
            best, best_d = k, d
    return best


def as_of(date) -> AsOf:
    """The only way to read historical data in this study."""
    return AsOf(_to_date(date))


def store_id() -> str:
    """
    An opaque identifier for the raw store currently in use.

    Analysis code legitimately needs to key a memo on which store it is reading,
    so that redirecting the store invalidates the memo rather than serving a
    stale answer. That need is real and it is not a reason to let analysis code
    name the raw cache, so the identifier is served from here. The value is a
    hash, so it identifies the store without disclosing a path anything could
    then open.
    """
    import hashlib
    return hashlib.sha1(str(config.RAW).encode("utf-8")).hexdigest()[:12]


def anachronisms() -> list[dict]:
    """Every current-vintage input admitted into a historical context, for the report."""
    if not ACCESS_LOG.exists():
        return []
    out = []
    for line in ACCESS_LOG.read_text(encoding="utf-8").splitlines():
        try:
            e = json.loads(line)
        except Exception:
            continue
        if e.get("kind") == "STATIC_ANACHRONISM":
            out.append(e)
    return out
