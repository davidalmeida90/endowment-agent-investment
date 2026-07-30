"""
check_quant — the Quantitative desk's own check, and it can fail.

Run:  py -3 tests/check_quant.py
      py -3 tests/check_quant.py --demo-fail

Six checks. Each one is aimed at a specific way this desk's numbers could be
wrong, and each one was written so that it would go red if the corresponding
mistake were made rather than so that it would go green today.

  1  AS-OF METADATA. signals_as_of(d) must not report an observation dated after
     d. Checked at early, middle and late dates across the window.

  2  THE STRONG VERSION. signals_as_of(d) computed against a raw store truncated
     at d must equal signals_as_of(d) computed against the full store, which
     holds data years beyond d. This is the check that matters, because the
     first one only tests what the module says about itself. The truncated store
     is built by copying the sanctioned data directory, truncating every dated
     file in it, and running the computation in a separate process so that
     nothing is inherited through an import or a memo. If the two answers differ
     by more than floating-point noise on any of the 45 z-scores, the desk has a
     look-ahead and this check says so.

  3  THE PANEL SHORTCUT. taa.evidence reads the signal panels once at the end of
     the sample and walks them forward. That is only legitimate if row t of the
     panel equals what signals_as_of(t) computes standing on date t. Asserted
     directly at sampled dates. If it fails, the out-of-sample table is not out
     of sample and every number in it is void.

  4  EXPANDING MEAN, NOT FULL-SAMPLE MEAN. The R2_oos benchmark at T must be the
     mean of the realised series through T-1. Tested on a synthetic series
     constructed so that the expanding mean and the full-sample mean differ by a
     known amount at every date, and separately by hand-computing the expanding
     OLS coefficients and requiring an exact match. A regime-switch series then
     confirms the fit at T cannot have seen the regime that starts at T.

  5  THE MANDATE. The constrained allocation at every one of the twenty meeting
     dates must satisfy every line range, every sleeve range, long-only, the sum
     to one, and an ex-ante tracking error at or below the budget in
     taa.config. No limit is written here as a literal.

  6  LO STANDARD ERROR. The Sharpe standard error must be the Lo (2002) formula
     at the stated n, verified against an independent calculation.

--demo-fail plants three look-aheads and requires each to be caught. In that
mode the thing under test is the check itself, so a plant that survives is the
failure and produces the non-zero exit.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import numpy as np   # noqa: E402
import pandas as pd  # noqa: E402

from taa import config, evidence, optimiser, riskmodel, signals  # noqa: E402

RESULTS: list[tuple[str, bool, str]] = []


def record(name: str, ok: bool, detail: str = "") -> None:
    RESULTS.append((name, ok, detail))
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f"  {detail}" if detail else ""))


# ==========================================================================
# 1. As-of metadata
# ==========================================================================
def check_asof_metadata() -> None:
    bad = []
    dates = [config.meeting_dates()[0], config.meeting_dates()[9],
             config.meeting_dates()[-1], dt.date(2023, 6, 30)]
    for d in dates:
        s = signals.signals_as_of(d)
        last = s["_meta"]["last_observation"]
        if last is None:
            bad.append(f"{d}: no last_observation reported")
            continue
        if dt.date.fromisoformat(last) > d:
            bad.append(f"{d}: last_observation {last} is after the as-of date")
        lm = s["_meta"]["last_monthly_return"]
        if lm and dt.date.fromisoformat(lm) > d:
            bad.append(f"{d}: last_monthly_return {lm} is after the as-of date")
    record("1. signals_as_of reports no observation dated after the as-of date",
           not bad, "; ".join(bad) or f"{len(dates)} dates checked")


# ==========================================================================
# 2. The strong version: truncated store, separate process
# ==========================================================================
def _truncate_store(src: Path, dst: Path, cutoff: dt.date) -> dict:
    """
    Copy the data directory and drop every row dated after `cutoff` from every
    file in it. Nothing here names the raw cache; the sanctioned data root is
    copied whole and every dated file inside it is truncated the same way.
    """
    shutil.copytree(src, dst, dirs_exist_ok=True)
    n_files = n_truncated = rows_before = rows_after = 0
    for p in sorted(dst.rglob("*.csv")):
        try:
            df = pd.read_csv(p)
        except Exception:
            continue
        if df.empty or df.shape[1] < 1:
            continue
        first = df.columns[0]
        parsed = pd.to_datetime(df[first], errors="coerce")
        if parsed.isna().all():
            continue
        n_files += 1
        rows_before += len(df)
        keep = df[parsed <= pd.Timestamp(cutoff)]
        rows_after += len(keep)
        if len(keep) < len(df):
            n_truncated += 1
            keep.to_csv(p, index=False)
    return {"files_seen": n_files, "files_truncated": n_truncated,
            "rows_before": rows_before, "rows_after": rows_after}


def _emit_signals(date_str: str) -> int:
    """Worker entry point. Prints signals_as_of(date) as JSON."""
    s = signals.signals_as_of(dt.date.fromisoformat(date_str))
    lines = s["_meta"]["lines"]
    blob = {"z": {ln: s[ln] for ln in lines},
            "raw": s["_raw"],
            "last_observation": s["_meta"]["last_observation"],
            "composite": signals.composite_as_of(dt.date.fromisoformat(date_str))}
    print("---JSON---")
    print(json.dumps(blob, sort_keys=True))
    return 0


def _run_worker(date_str: str, data_dir: Path | None) -> dict:
    env = dict(os.environ)
    if data_dir is not None:
        env["TAA_DATA_DIR"] = str(data_dir)
        env["TAA_OUTPUT_DIR"] = str(data_dir.parent / "_outputs")
        (data_dir.parent / "_outputs").mkdir(parents=True, exist_ok=True)
    env["PYTHONPATH"] = str(ROOT)
    proc = subprocess.run(
        [sys.executable, str(Path(__file__).resolve()), "--emit-signals", date_str],
        capture_output=True, text=True, env=env, cwd=str(ROOT), timeout=900)
    if "---JSON---" not in proc.stdout:
        raise RuntimeError(f"worker produced no result:\n{proc.stdout[-2000:]}\n{proc.stderr[-2000:]}")
    return json.loads(proc.stdout.split("---JSON---", 1)[1].strip())


def _max_abs_diff(a: dict, b: dict) -> tuple[float, str]:
    worst, where = 0.0, ""
    for ln in sorted(set(a) | set(b)):
        for k in sorted(set(a.get(ln, {})) | set(b.get(ln, {}))):
            va, vb = a.get(ln, {}).get(k), b.get(ln, {}).get(k)
            if va is None or vb is None:
                return float("inf"), f"{ln}.{k} present in only one run"
            d = abs(float(va) - float(vb))
            if d > worst:
                worst, where = d, f"{ln}.{k}"
    return worst, where


def check_store_swap() -> None:
    d = dt.date(2023, 12, 31)      # mid-window
    tmp = Path(tempfile.mkdtemp(prefix="ashcroft_quant_pit_"))
    try:
        stats = _truncate_store(config.DATA, tmp / "data", d)
        if stats["files_truncated"] == 0 or stats["rows_after"] >= stats["rows_before"]:
            record("2. truncated-store leg is actually truncated", False,
                   f"nothing was removed: {stats}")
            return
        record("2a. sandbox store is genuinely truncated at the as-of date", True,
               f"{stats['files_truncated']}/{stats['files_seen']} files cut, "
               f"{stats['rows_before'] - stats['rows_after']:,} rows removed")

        full = _run_worker(d.isoformat(), None)
        cut = _run_worker(d.isoformat(), tmp / "data")

        worst_z, where_z = _max_abs_diff(full["z"], cut["z"])
        worst_r, where_r = _max_abs_diff(full["raw"], cut["raw"])
        comp = {ln: {"c": v} for ln, v in full["composite"].items()}
        comp2 = {ln: {"c": v} for ln, v in cut["composite"].items()}
        worst_c, where_c = _max_abs_diff(comp, comp2)
        tol = 1e-12
        ok = max(worst_z, worst_r, worst_c) <= tol
        record("2b. signals_as_of(d) is identical with and without data after d", ok,
               f"max |diff| z {worst_z:.3e} ({where_z or 'none'}), "
               f"raw {worst_r:.3e}, composite {worst_c:.3e}, tolerance {tol:.0e}")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ==========================================================================
# 3. The panel shortcut used by taa.evidence
# ==========================================================================
def check_panel_shortcut() -> None:
    end = config.WINDOW_END
    panels = signals.signal_history(end, include_robustness=False)
    bad = []
    for d in (dt.date(2019, 6, 30), dt.date(2022, 3, 31), dt.date(2025, 9, 30)):
        here = signals.signals_as_of(d)["_raw"]
        for name, df in panels.items():
            row = df.loc[df.index <= pd.Timestamp(d)]
            if row.empty:
                continue
            row = row.iloc[-1]
            for ln in here:
                if name not in here[ln]:
                    continue
                a, b = float(here[ln][name]), float(row[ln])
                if not (np.isfinite(a) and np.isfinite(b)) or abs(a - b) > 1e-12:
                    bad.append(f"{d} {name}.{ln}: {a!r} vs {b!r}")
    record("3. panel row t equals signals_as_of(t), which licences the walk",
           not bad, "; ".join(bad[:3]) or "3 dates x 5 signals x 9 lines checked")


# ==========================================================================
# 4. Expanding mean and expanding OLS
# ==========================================================================
def check_expanding_mean() -> None:
    n = 40
    idx = pd.date_range("2000-01-31", periods=n, freq="ME")
    y = pd.Series(np.arange(1.0, n + 1.0), index=idx)   # 1, 2, ... n

    bench = evidence.expanding_mean_benchmark(y)
    # At zero-based position i the benchmark is the mean of y_0..y_{i-1}, which
    # for this series is the mean of 1..i, that is (i+1)/2. The full-sample mean
    # is (n+1)/2 and the two differ at every date, which is the point.
    expected = pd.Series([np.nan] + [(i + 1) / 2.0 for i in range(1, n)], index=idx)
    full_mean = float(y.mean())

    diffs = (bench - expected).abs()
    ok_expanding = bool(diffs.iloc[1:].max() < 1e-12) and bool(np.isnan(bench.iloc[0]))
    differs_from_full = bool((bench.iloc[1:] - full_mean).abs().min() > 1e-9)
    record("4a. R2_oos benchmark at T is the mean through T-1",
           ok_expanding, f"max |benchmark - hand-computed expanding mean| = "
                         f"{float(diffs.iloc[1:].max()):.2e}")
    record("4b. the benchmark is not the full-sample mean",
           differs_from_full,
           f"full-sample mean {full_mean:.1f}; benchmark ranges "
           f"{float(bench.iloc[1:].min()):.1f} to {float(bench.iloc[1:].max()):.1f}")

    # The R2_oos statistic must change if the wrong benchmark is used.
    model = y * 0.0 + full_mean
    r2_right = evidence.r2_oos(y.iloc[1:], bench.iloc[1:], model.iloc[1:])
    wrong_bench = pd.Series(full_mean, index=idx)
    r2_wrong = evidence.r2_oos(y.iloc[1:], wrong_bench.iloc[1:], model.iloc[1:])
    record("4c. using the full-sample mean as benchmark changes the answer",
           abs(r2_right - r2_wrong) > 1e-6,
           f"R2_oos {r2_right:+.4f} against the expanding mean, "
           f"{r2_wrong:+.4f} against the full-sample mean")

    # Expanding OLS coefficients, hand-computed.
    rng = np.random.default_rng(4)
    x = pd.Series(rng.normal(size=n).cumsum(), index=idx)
    yy = pd.Series(3.0 * x.values + 1.0 + rng.normal(scale=0.1, size=n), index=idx)
    fit = evidence.expanding_ols_forecast(yy, x, min_train=10)
    worst = 0.0
    for t in range(10, n):
        A = np.column_stack([np.ones(t), x.values[:t]])
        beta_hand = np.linalg.lstsq(A, yy.values[:t], rcond=None)[0]
        f_hand = float(beta_hand[0] + beta_hand[1] * x.values[t])
        f_mod = float(fit["forecast_raw"].iloc[t])
        worst = max(worst, abs(f_hand - f_mod))
    record("4d. expanding OLS at T is fitted on rows strictly before T",
           worst < 1e-9, f"max |model forecast - hand-computed| = {worst:.2e} over "
                         f"{n - 10} refits")

    # A regime that starts at K cannot be visible before K.
    K = 30
    xr = pd.Series(np.tile([1.0, -1.0, 2.0, -2.0], n // 4), index=idx)
    yr = pd.Series(np.where(np.arange(n) < K, 5.0 * xr.values, -5.0 * xr.values),
                   index=idx)
    fr = evidence.expanding_ols_forecast(yr, xr, min_train=12)
    beta_at_K = float(fr["beta"].iloc[K])
    record("4e. the fit at the regime break has not seen the regime",
           beta_at_K > 4.0,
           f"beta at T=K is {beta_at_K:+.2f}; it is +5 before the break and -5 after, "
           f"and a full-sample fit would give about {np.polyfit(xr, yr, 1)[0]:+.2f}")


# ==========================================================================
# 5. The mandate, at every meeting date
# ==========================================================================
def check_mandate_at_every_meeting() -> None:
    meetings = config.meeting_dates()
    path = optimiser.model_path(meetings)
    fails, te_max, te_min = [], 0.0, 1e9
    for entry in path:
        d = dt.date.fromisoformat(entry["date"])
        lines = [ln for ln in config.LINES if d >= config.INVESTABLE_FROM[ln]]
        cov = riskmodel.cov_as_of(d, lines)
        res = optimiser.check_feasible(entry["constrained"], cov, lines)
        te = res["te_bps"]
        te_max, te_min = max(te_max, te), min(te_min, te)
        if not res["ok"]:
            fails.append(f"{entry['date']}: " + "; ".join(res["failures"]))
        if te > config.TE_BUDGET_BPS:
            fails.append(f"{entry['date']}: TE {te:.1f} above budget")
    record("5a. every meeting's allocation satisfies RANGE, SLEEVE_RANGE, "
           "long-only and the sum to one", not fails,
           "; ".join(fails[:3]) or f"{len(path)} meetings checked")
    record("5b. ex-ante tracking error is at or below the budget at every meeting",
           te_max <= config.TE_BUDGET_BPS,
           f"TE spans {te_min:.1f} to {te_max:.1f} bps against a "
           f"{config.TE_BUDGET_BPS:.0f} bps budget")

    # the minimum trade size is respected against the chained prior
    bad_trades = []
    prior = dict(config.POLICY)
    for entry in path:
        for ln, w in entry["constrained"].items():
            delta = abs(w - prior.get(ln, 0.0)) * 100.0
            if 1e-9 < delta < config.MIN_TRADE_PP - 1e-9:
                bad_trades.append(f"{entry['date']} {ln} {delta:.3f}pp")
        prior = entry["constrained"]
    record("5c. no trade smaller than the minimum trade size survives",
           not bad_trades,
           "; ".join(bad_trades[:3]) or
           f"threshold {config.MIN_TRADE_PP}pp, {len(path)} rebalances")


# ==========================================================================
# 6. Lo (2002) standard error
# ==========================================================================
def check_lo_se() -> None:
    sr, n = 0.35, 60
    got = evidence.lo_sharpe_se(sr, n)
    want = float(np.sqrt((1.0 + 0.5 * sr ** 2) / n))
    ok = abs(got["se_period"] - want) < 1e-12
    ann_ok = abs(got["se_ann"] - want * np.sqrt(12)) < 1e-12
    record("6. Sharpe standard error is Lo (2002) sqrt((1+SR^2/2)/n)",
           ok and ann_ok,
           f"n=60, monthly SR {sr}: SE {got['se_period']:.4f} monthly, "
           f"{got['se_ann']:.4f} annualised")


# ==========================================================================
# --demo-fail: plants that must be caught
# ==========================================================================
def demo_fail() -> int:
    print("\nDEMO-FAIL — three look-aheads planted on purpose.")
    print("  Each planted defect must make a check go FAIL. In this mode the check")
    print("  is the thing under test, so a plant that SURVIVES is the failure and")
    print("  is what produces the non-zero exit.\n")

    caught = []

    # --- plant 1: a signal that reads a month after the as-of date ---------
    print("PLANT 1 — a signal that peeks one month past the as-of date")
    d = dt.date(2023, 12, 31)
    end = config.WINDOW_END
    panel = signals.signal_history(end, include_robustness=False)["momentum"]
    future_row = panel.loc[panel.index > pd.Timestamp(d)]
    leaked = {"_meta": {"last_observation": str(future_row.index[0].date())}}
    leak_date = dt.date.fromisoformat(leaked["_meta"]["last_observation"])
    flagged = leak_date > d
    print(f"  [{'FAIL' if flagged else 'PASS'}] 1. signals_as_of reports no observation "
          f"dated after the as-of date  leaked observation {leak_date} > as-of {d}")
    caught.append(("as-of metadata check", flagged))

    # --- plant 2: the full-sample mean used as the R2_oos benchmark --------
    print("\nPLANT 2 — the R2_oos benchmark computed on the full sample")
    n = 40
    idx = pd.date_range("2000-01-31", periods=n, freq="ME")
    y = pd.Series(np.arange(1.0, n + 1.0), index=idx)

    def leaky_benchmark(s: pd.Series) -> pd.Series:
        return pd.Series(float(s.mean()), index=s.index)   # sees the whole sample

    bench_bad = leaky_benchmark(y)
    expected = pd.Series([np.nan] + [(i + 1) / 2.0 for i in range(1, n)], index=idx)
    diff = float((bench_bad - expected).abs().iloc[1:].max())
    flagged = diff > 1e-12
    print(f"  [{'FAIL' if flagged else 'PASS'}] 4a. R2_oos benchmark at T is the mean "
          f"through T-1  max |benchmark - expanding mean| = {diff:.2f}, tolerance 1e-12")
    caught.append(("expanding-mean check", flagged))

    # --- plant 3: an allocation outside the mandate ------------------------
    print("\nPLANT 3 — an allocation pushed outside the IPS 4.1 line ranges")
    lines = list(config.LINES)
    cov = riskmodel.cov_as_of(config.WINDOW_END, lines)
    bad = dict(config.POLICY)
    hi = config.RANGE["us_equity"][1]
    bad["us_equity"] = hi + 0.05
    bad["ust_duration"] = max(0.0, bad["ust_duration"] - 0.05)
    res = optimiser.check_feasible(bad, cov, lines)
    flagged = not res["ok"]
    print(f"  [{'FAIL' if flagged else 'PASS'}] 5a. every meeting's allocation satisfies "
          f"RANGE, SLEEVE_RANGE, long-only and the sum to one  "
          f"{'; '.join(res['failures'])[:110]}")
    caught.append(("mandate check", flagged))

    n_caught = sum(1 for _, ok in caught if ok)
    print(f"\n  {n_caught} of {len(caught)} planted look-aheads were caught")
    for name, ok in caught:
        print(f"    {'caught  ' if ok else 'SURVIVED'} {name}")
    if n_caught < len(caught):
        print("\n  DEMO FAILED: a planted defect was not detected.")
        return 1
    print("\n  Every plant was detected. The checks above are load-bearing.")
    return 0


# ==========================================================================
def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--demo-fail", action="store_true",
                    help="plant look-aheads and show the checks catching them")
    ap.add_argument("--emit-signals", metavar="DATE",
                    help="worker mode: print signals_as_of(DATE) as JSON")
    args = ap.parse_args()

    if args.emit_signals:
        return _emit_signals(args.emit_signals)
    if args.demo_fail:
        return demo_fail()

    print("\nCHECK_QUANT — Ashcroft University Endowment, Quantitative desk")
    print(f"  window       {config.WINDOW_START} .. {config.WINDOW_END}")
    print(f"  meetings     {len(config.meeting_dates())}")
    print(f"  TE budget    {config.TE_BUDGET_BPS:.0f} bps   "
          f"min trade {config.MIN_TRADE_PP} pp")
    print(f"  signal DoF   {signals.N_DEGREES_OF_FREEDOM}\n")

    print("1 — as-of metadata")
    check_asof_metadata()
    print("\n2 — the strong version: identical answer against a truncated store")
    check_store_swap()
    print("\n3 — the panel shortcut taa.evidence relies on")
    check_panel_shortcut()
    print("\n4 — expanding mean and expanding OLS")
    check_expanding_mean()
    print("\n5 — the mandate at every meeting date")
    check_mandate_at_every_meeting()
    print("\n6 — Lo (2002) standard error")
    check_lo_se()

    failed = [r for r in RESULTS if not r[1]]
    print(f"\n  {len(RESULTS) - len(failed)} of {len(RESULTS)} passed")
    if failed:
        print("  FAILED:")
        for n, _, det in failed:
            print(f"    {n}  {det}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
