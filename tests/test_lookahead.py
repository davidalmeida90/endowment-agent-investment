"""
The look-ahead suite. This is the wall, tested.

Run:  py -3 tests/test_lookahead.py
      py -3 tests/test_lookahead.py --plant     (adds the planted-violation cases)

Nine tests, in three groups.

  STATIC     Walks the import graph of the whole package with ast and fails if
             any analysis module can reach data without an as-of date. This is
             the one that closes the hole a convention leaves open, because a
             desk that never imports the raw store cannot forget to use the gate.

  RUNTIME    Exercises the guard and the as-of gate on real cached data, at real
             dates, including the two ways a look-ahead actually gets in:
             revision, and publication lag.

  PLANTED    Deliberate violations, each of which must be caught. A test that has
             only ever passed is not evidence of anything.

tests/mutation_test.py then breaks the enforcement on purpose and asserts this
suite goes red. If deleting the check leaves these tests green, the tests were
never checking anything, and that is the failure this office cares about most.
"""

from __future__ import annotations

import ast
import datetime as dt
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# Redirect this suite's writes away from outputs/ before taa.config is imported.
# The anachronism test deliberately reads a current-vintage series, which
# pitdata logs to the point-in-time access log. Left alone, that entry lands in
# the production log and is then attributed to whichever committee meeting
# shares its as-of date, so running the tests would put a fabricated limitation
# into the decision record. A test suite must not be able to alter a deliverable.
os.environ.setdefault("TAA_OUTPUT_DIR",
                      tempfile.mkdtemp(prefix="ashcroft_test_outputs_"))

import pandas as pd  # noqa: E402

from taa import _rawstore, config, pitdata  # noqa: E402

RESULTS: list[tuple[str, bool, str]] = []


def record(name: str, ok: bool, detail: str = "") -> None:
    RESULTS.append((name, ok, detail))
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f"  {detail}" if detail else ""))


# ==========================================================================
# STATIC. The import graph.
# ==========================================================================
FORBIDDEN_IMPORTS = {"yfinance", "requests", "urllib", "urllib.request", "http.client",
                     "socket", "pandas_datareader"}
RAW_STORE = "_rawstore"

# Only these files may reach the network or the raw cache. The list is explicit
# rather than a pattern, so a new file that reaches the raw store fails this
# test on the day it appears instead of quietly inheriting an exemption.
# tests/ files are here because a suite that tests the guard has to be able to
# call it; that is the whole of their business with it.
NETWORK_ALLOWED = {"taa/datapull.py"}
RAWSTORE_ALLOWED = {"taa/pitdata.py", "taa/datapull.py",
                    "tests/test_lookahead.py", "tests/mutation_test.py"}


def _py_files() -> list[Path]:
    out = []
    for d in ("taa", "tests"):
        out += sorted((ROOT / d).rglob("*.py"))
    return [p for p in out if "__pycache__" not in str(p) and "sandbox" not in str(p)]


def _rel(p: Path) -> str:
    return p.relative_to(ROOT).as_posix()


def test_static_import_graph() -> None:
    net_offenders, raw_offenders = [], []
    for p in _py_files():
        rel = _rel(p)
        if rel.startswith("taa/_rawstore"):
            continue
        try:
            tree = ast.parse(p.read_text(encoding="utf-8"))
        except SyntaxError as e:
            record("static: files parse", False, f"{rel}: {e}")
            return
        for node in ast.walk(tree):
            names = []
            if isinstance(node, ast.Import):
                names = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom):
                base = node.module or ""
                names = [base] + [f"{base}.{a.name}" for a in node.names]
            for n in names:
                top = n.split(".")[0]
                if (top in FORBIDDEN_IMPORTS or n in FORBIDDEN_IMPORTS) and rel not in NETWORK_ALLOWED:
                    net_offenders.append(f"{rel} imports {n}")
                if RAW_STORE in n and rel not in RAWSTORE_ALLOWED:
                    raw_offenders.append(f"{rel} imports {n}")
    record("static: no analysis module reaches the network",
           not net_offenders, "; ".join(net_offenders) or f"{len(_py_files())} files scanned")
    record("static: no analysis module imports the raw store",
           not raw_offenders, "; ".join(raw_offenders) or "only pitdata and datapull")


def test_static_no_raw_path_literals() -> None:
    """
    An analysis module must not open anything under data/raw by path either.

    Checked on the parse tree rather than by grepping the file. A substring
    search for "config.RAW" also matches a sentence *about* config.RAW, and it
    duly failed on tests/audit2.py, which carries the string in a table
    describing the time this rule caught the Quantitative desk. Prose about a
    guard is not a breach of it, and a test that cannot tell the difference will
    eventually be switched off by someone who is right to.
    """
    offenders = []
    for p in _py_files():
        rel = _rel(p)
        if rel in RAWSTORE_ALLOWED or rel.startswith("taa/_rawstore") or rel.startswith("taa/config"):
            continue
        try:
            tree = ast.parse(p.read_text(encoding="utf-8"))
        except SyntaxError:
            continue
        docstrings = set()
        for node in ast.walk(tree):
            if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                d = ast.get_docstring(node, clean=False)
                if d:
                    docstrings.add(d)
        for node in ast.walk(tree):
            # real attribute access: config.RAW
            if (isinstance(node, ast.Attribute) and node.attr == "RAW"
                    and isinstance(node.value, ast.Name) and node.value.id == "config"):
                offenders.append(f"{rel}:{node.lineno} accesses config.RAW")
            # a path literal that is not prose in a docstring
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                v = node.value
                if v in docstrings:
                    continue
                if ("data/raw" in v or "data\\raw" in v) and len(v) < 200:
                    offenders.append(f"{rel}:{node.lineno} holds the path {v!r}")
    if offenders:
        offenders.append("(allowlist: " + ", ".join(sorted(RAWSTORE_ALLOWED)) + ")")
    record("static: no analysis module references the raw cache by path",
           not offenders, "; ".join(offenders) or "clean")


# ==========================================================================
# RUNTIME. The guard and the gate.
# ==========================================================================
def test_runtime_guard_blocks_direct_read() -> None:
    try:
        _rawstore.read("px_SPY")
    except _rawstore.RawAccessViolation:
        record("runtime: raw store refuses a caller that is not pitdata", True,
               "RawAccessViolation raised")
        return
    except FileNotFoundError:
        record("runtime: raw store refuses a caller that is not pitdata", False,
               "read was PERMITTED (it only failed because the file is missing)")
        return
    record("runtime: raw store refuses a caller that is not pitdata", False,
           "the read succeeded; the wall has a hole")


def test_runtime_price_gate() -> None:
    """No price dated after the as-of date, at several dates across the window."""
    bad = []
    for d in ("2021-09-30", "2022-06-30", "2024-03-31", "2026-06-30"):
        as_of = dt.date.fromisoformat(d)
        px = pitdata.as_of(as_of).prices(["SPY", "IEF"])
        if len(px) and px.index.max().date() > as_of:
            bad.append(f"{d}: last obs {px.index.max().date()}")
    record("runtime: price reads are truncated at the as-of date", not bad,
           "; ".join(bad) or "4 dates checked, SPY and IEF")


def test_runtime_publication_lag() -> None:
    """
    A figure released after the trade date is a look-ahead even when the
    observation is correctly dated earlier. Series carrying a declared lag must
    exclude observations inside the lag window.
    """
    sid, (label, lag) = "BAA10Y", pitdata.MARKET_FRED["BAA10Y"]
    if lag <= 0:
        record("runtime: publication lag is applied", False, f"{sid} has no declared lag")
        return

    # The as-of date must be one on which the series ACTUALLY HAS an observation,
    # otherwise the lag makes no difference and the test passes whatever the code
    # does. The first version of this test used 29 March 2024, which was Good
    # Friday: no observation existed on the day, so deleting the lag changed
    # nothing and the mutation test caught the test rather than the code.
    probe = pitdata.as_of(config.WINDOW_END).fred(sid)
    candidates = [d.date() for d in probe.index
                  if dt.date(2023, 1, 1) <= d.date() <= config.WINDOW_END]
    if not candidates:
        record("runtime: publication lag is applied", False, "no candidate dates in window")
        return
    as_of = candidates[len(candidates) // 2]
    s = pitdata.as_of(as_of).fred(sid)
    cutoff = as_of - dt.timedelta(days=lag)
    has_obs_on_day = as_of in candidates
    ok = (len(s) > 0 and s.index.max().date() <= cutoff and has_obs_on_day
          and s.index.max().date() < as_of)
    record("runtime: publication lag is applied, not just the observation date", ok,
           f"{sid} lag {lag}d, as-of {as_of} has its own observation, "
           f"last served {s.index.max().date()} <= {cutoff}")


def _qoq_saar(s: pd.Series, obs: pd.Timestamp) -> float:
    """Annualised quarter-on-quarter growth, which is how a GDP print is read."""
    prev = obs - pd.offsets.QuarterBegin(startingMonth=1)
    return (float(s.loc[obs]) / float(s.loc[prev])) ** 4 - 1.0


def test_runtime_vintage_differs_from_current() -> None:
    """
    The headline case, and the reason this office built the wall.

    Real GDP for 2022 Q2 as published on 28 July 2022 against the same quarter
    read today. Compared as an annualised growth rate rather than as a level,
    because BEA rebased the chained-dollar index between these two vintages and
    the levels are therefore in different units. The growth rate is what a desk
    actually reads and it is unit free.

    If the two agree, either the vintage machinery is not working or the
    revision never happened. Both matter and both should fail loudly.
    """
    obs = pd.Timestamp("2022-04-01")   # 2022 Q2
    then = pitdata.as_of("2022-07-28").macro("GDPC1")
    now = pitdata.as_of(config.REPORT_DATE).macro("GDPC1")
    if obs not in then.index or obs not in now.index:
        record("runtime: macro vintages differ from the current revision", False,
               "2022Q2 absent from one of the vintages")
        return
    g_then, g_now = _qoq_saar(then, obs), _qoq_saar(now, obs)
    sign_flip = (g_then < 0) and (g_now > 0)
    record("runtime: macro vintages differ from the current revision",
           abs(g_then - g_now) > 1e-6,
           f"2022Q2 real GDP: {g_then * 100:+.2f}% saar as published 2022-07-28, "
           f"{g_now * 100:+.2f}% saar today"
           + ("  [SIGN FLIPPED]" if sign_flip else "  [same sign]"))


def test_runtime_vintage_omits_unpublished() -> None:
    """
    An observation that had not yet been published must be absent from the
    vintage, which is the publication-lag problem handled at source.
    """
    as_of = dt.date(2022, 7, 28)
    s = pitdata.as_of(as_of).macro("GDPC1")
    ok = len(s) and s.index.max() <= pd.Timestamp(as_of)
    record("runtime: a vintage carries no observation published after it", bool(ok),
           f"last GDP observation in the 2022-07-28 vintage is {s.index.max().date()}")


def test_runtime_investable_dates() -> None:
    """IPS 4.1: investable dates bind."""
    try:
        pitdata.as_of("2005-06-30").line_prices(["us_hy"])
    except pitdata.NotInvestableError:
        record("runtime: a line is refused before its vehicle listed", True,
               "us_hy (HYG, lists 2007) refused at 2005-06-30")
        return
    record("runtime: a line is refused before its vehicle listed", False,
           "HYG was served for a date before it existed")


# ==========================================================================
# PLANTED. Violations that must be caught.
# ==========================================================================
def test_planted_future_frame_is_caught() -> None:
    """Hand the gate a frame that contains tomorrow and demand it object."""
    as_of = dt.date(2024, 6, 28)
    idx = pd.to_datetime([as_of - dt.timedelta(days=1), as_of + dt.timedelta(days=30)])
    frame = pd.DataFrame({"x": [1.0, 2.0]}, index=idx)
    try:
        pitdata.assert_no_future(frame, as_of, "planted frame")
    except pitdata.LookAheadError as e:
        record("planted: a frame holding a future observation is rejected", True, str(e)[:70])
        return
    record("planted: a frame holding a future observation is rejected", False,
           "the planted violation was NOT caught")


def test_planted_unregistered_series_refused() -> None:
    """A series with neither vintage history nor a declared lag cannot be read."""
    try:
        pitdata.as_of("2024-06-28").fred("MADEUPSERIES")
    except KeyError:
        record("planted: an unregistered series is refused", True, "KeyError raised")
        return
    record("planted: an unregistered series is refused", False, "it was served")


def test_planted_anachronism_requires_a_reason() -> None:
    """
    A current-vintage file used in a historical context must be declared.

    Tested against house_cme, which exists in the cache. The first version of
    this test used shiller_ie, which is not cached, so the read failed with
    FileNotFoundError and the test passed without ever reaching the check it was
    supposed to be testing. The mutation test found that: deleting the reason
    requirement left this green. A test that passes for the wrong reason is
    worse than no test, because it is counted as evidence.
    """
    v = pitdata.as_of("2022-06-30")
    try:
        v.static("house_cme", reason="")
    except FileNotFoundError:
        record("planted: an undeclared anachronism is refused", False,
               "house_cme is not cached, so the reason requirement was never reached")
        return
    except ValueError:
        # Correct. Now confirm the same call succeeds WITH a reason, so the test
        # is not passing because the path is broken in general.
        try:
            v.static("house_cme", reason="current house forecasts admitted to a historical "
                                         "context to price the policy portfolio")
        except Exception as e:
            record("planted: an undeclared anachronism is refused", False,
                   f"refused even with a reason: {type(e).__name__}")
            return
        record("planted: an undeclared anachronism is refused", True,
               "ValueError without a reason, served with one")
        return
    record("planted: an undeclared anachronism is refused", False, "it was served silently")


# ==========================================================================
def main() -> int:
    print(f"\nLOOK-AHEAD SUITE — Ashcroft University Endowment")
    print(f"  package    {ROOT}")
    print(f"  cache      {config.RAW}")
    print(f"  window     {config.WINDOW_START} .. {config.WINDOW_END}\n")

    print("STATIC — the import graph")
    test_static_import_graph()
    test_static_no_raw_path_literals()

    print("\nRUNTIME — the guard and the as-of gate")
    test_runtime_guard_blocks_direct_read()
    test_runtime_price_gate()
    test_runtime_publication_lag()
    test_runtime_vintage_differs_from_current()
    test_runtime_vintage_omits_unpublished()
    test_runtime_investable_dates()

    print("\nPLANTED — violations that must be caught")
    test_planted_future_frame_is_caught()
    test_planted_unregistered_series_refused()
    test_planted_anachronism_requires_a_reason()

    failed = [r for r in RESULTS if not r[1]]
    print(f"\n  {len(RESULTS) - len(failed)} of {len(RESULTS)} passed")
    if failed:
        print("  FAILED:")
        for n, _, d in failed:
            print(f"    {n}  {d}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
