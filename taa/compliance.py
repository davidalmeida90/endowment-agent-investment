"""
taa.compliance — the Risk function's test. It holds a veto, not an opinion.

IPS Section 2.1:
    "Risk function. Determines: nothing; it holds no allocation authority.
     Executes: compliance testing of every proposed allocation. Monitors: every
     proposal, and the portfolio continuously."
    "The separation is deliberate. The risk function does not advise on
     allocation and does not compete with the Chief Investment Officer for
     influence over it. It applies the constraints in this Statement and returns
     a pass or a fail. An allocation that fails does not proceed to the
     Committee. The remedy is a different allocation or an amendment to this
     Statement, and never an adjustment to the test."

This module is that test. It recommends nothing. Every limit it applies is
imported from taa.config, which transcribes the Investment Policy Statement.
No limit is restated as a literal here, because a limit written down twice is a
limit that can disagree with itself.

WHAT IS TESTED, AND WHERE IT COMES FROM
------------------------------------------------------------------------------
  structural_keys        every mandate line present, nothing else          IPS 4.1
  structural_finite      no NaN and no infinity in the weight vector       IPS 4.1
  structural_sum         weights sum to one                                IPS 4.1
  liquidity_floor        15% of NAV realisable within five business days   IPS 3.4  rank 1
  liquidity_distribution the quarterly draw funds without a forced sale    IPS 3.4  rank 1
  leverage_gross         gross exposure does not exceed NAV                IPS 3.5  rank 2
  leverage_short         no negative weight; a short is leverage           IPS 3.5  rank 2
  board_exclusions       tobacco and thermal coal, at the vehicle level    IPS 3.5  rank 2
  drawdown_realised      worst peak to trough on a supplied NAV path       IPS 3.3  rank 3
  drawdown_ex_ante       parametric maximum drawdown of the proposal       IPS 3.3  rank 3
  drawdown_stress        replay of the proposal through named episodes     IPS 3.3  rank 3
  tracking_error         200bps ex ante against the policy portfolio       IPS 4.2  rank 4
  line_range             every line inside its permitted range             IPS 4.1
  sleeve_range           equity, fixed income and real assets sleeves      IPS 4.1
  min_trade              no proposed change smaller than the minimum       IPS 4.2 / 4.5
  corridor_width         no corridor narrower than the minimum trade       IPS 4.5
  investable_date        no weight on a line before its vehicle existed    IPS 4.1

FOUR OUTCOMES, NOT TWO
------------------------------------------------------------------------------
PASS                    The constraint is satisfied.
FAIL                    The constraint is breached. The allocation does not
                        proceed to the Committee (IPS 2.1).
PASS-WITH-DISCLOSURE    Required by IPS 3.5, which says a broad index vehicle
                        carrying incidental excluded exposure is "disclosed
                        rather than deemed compliant by silence". The
                        constraint is satisfied and a text must appear in the
                        report. Silence is not one of the permitted answers.
NOT ASSESSED            A required input was withheld, so the constraint could
                        not be tested. On a gating check this counts as a
                        failure, not as a pass. A compliance function that
                        cannot measure tracking error must not certify
                        compliance with the tracking error budget. Absence of
                        evidence is not evidence of compliance.
NOT APPLICABLE          The input does not exist for this class of proposal.
                        A forward-looking allocation has no realised NAV path
                        and an initial allocation has no prior weights. This
                        counts as a pass.

GATING AND ADVISORY
------------------------------------------------------------------------------
A check gates the verdict when it tests a property of the allocation, because
IPS 2.1 says the remedy for a failure is a different allocation. A check is
advisory when it tests the machinery around the allocation rather than the
allocation itself, since no different allocation could cure it and a veto would
therefore be a veto of every allocation equally.

Two checks are advisory.

corridor_width  Corridor widths belong to the rebalancing policy at IPS 4.5 and
                are owned by the Implementation desk. A corridor narrower than
                the minimum trade is a defect in that policy, and no proposed
                set of weights can cure it.

drawdown_stress The replay is an empirical read of five specific historical
                paths, and the worst of them, 2007 to 2009, is outside the
                sanctioned price cache and cannot be run at all. A sample that
                small gives enormous weight to path-specific accident, and the
                one path that would matter most is missing. It is reported in
                full, it is flagged whenever it breaches the mandate limit, and
                it does not veto. The gating ex-ante measure is the parametric
                one, which at least uses every line's full covariance rather
                than five episodes.

An advisory result never becomes a silent pass. It prints in the table with its
own status and repeats under QUALIFICATIONS, so every certificate carries the
list of what was tested weakly or not at all.

NO NETWORK. NO RAW DATA. Historical reads go through taa.pitdata with an as-of
date, which is the only sanctioned path (IPS 4.4).
"""

from __future__ import annotations

import datetime as _dt
import math
from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd

from . import config, pitdata

# --------------------------------------------------------------------------
# Reporting thresholds. These are not IPS limits and they gate nothing. They
# control how the dashboard describes a result that is already determined.
# --------------------------------------------------------------------------
WEIGHT_SUM_TOL = 1e-6        # numerical tolerance on the weights summing to one
FLOAT_EPS = 1e-9             # tolerance on comparisons at a boundary
BINDING_TOL_REL = 0.02       # a constraint within 2% of its limit reads as binding
BINDING_TOL_ABS = 1e-4

# --------------------------------------------------------------------------
# Ex ante drawdown model settings. Documented in desks/risk.md. Changing any of
# these changes a model output, never a mandate limit.
# --------------------------------------------------------------------------
MDD_HORIZON_YEARS = 1.0      # IPS 4.5 resets to policy at least annually; IPS 4.3
                             # reports to the Board annually
MDD_QUANTILE = 0.95          # the mandate limit is a ceiling, so the test reads a
                             # tail, not a central expectation
MDD_MC_PATHS = 20_000
MDD_MC_STEPS = 252
MDD_MC_SEED = 20260728

# Named stress episodes, dated on the peak and the trough of the S&P 500
# composite. Every mandate line was investable on the first of these dates, so
# the replay needs no substitution and no index history.
#
# THE GLOBAL FINANCIAL CRISIS IS DECLARED AND IT CANNOT BE RUN.
# taa.datapull pulls prices from WINDOW_START less ESTIMATION_PREFIX_YEARS,
# which is 1 July 2009, so 2007 and 2008 sit outside the sanctioned cache. The
# episode is left in this list deliberately rather than quietly dropped, so that
# every run reports it as not available and no reader mistakes the worst episode
# this test can see for the worst episode that has happened. The remedy is to
# lengthen the estimation prefix in taa.config and repull, which is a decision
# for the office rather than something the risk function does around the choke
# point at IPS 4.4.
STRESS_EPISODES = (
    ("Global financial crisis", "2007-10-09", "2009-03-09"),
    ("Euro crisis and US downgrade", "2011-04-29", "2011-10-03"),
    ("China devaluation and EM selloff", "2015-05-21", "2016-02-11"),
    ("Fourth quarter 2018", "2018-09-20", "2018-12-24"),
    ("COVID-19 crash", "2020-02-19", "2020-03-23"),
    ("2022 inflation and rates", "2022-01-03", "2022-10-12"),
)

# --------------------------------------------------------------------------
# Incidental exposure to the board exclusions, at the vehicle level (IPS 3.5).
#
# IPS 3.5 assesses compliance at the vehicle level and requires that a broad
# index vehicle carrying incidental excluded exposure be "disclosed rather than
# deemed compliant by silence". This table drives that disclosure. Each entry
# records whether the holding was verified against a source that was read, or
# whether it is a construction inference that could not be confirmed. An
# unverified entry still raises a disclosure, and the disclosure says it is
# unverified, because the failure mode IPS 3.5 is guarding against is silence.
#
# Sources and as-of dates are carried in EXCLUSION_SOURCES below.
# --------------------------------------------------------------------------
EXCLUSION_TOBACCO, EXCLUSION_COAL = config.BOARD_EXCLUSIONS


@dataclass(frozen=True)
class IncidentalExposure:
    vehicle: str
    exclusion: str
    issuers: tuple[str, ...]
    approx_weight: float | None      # fraction of the vehicle, None if not established
    verified: bool
    source: str
    as_of: str
    note: str = ""


INCIDENTAL_EXPOSURE: tuple[IncidentalExposure, ...] = ()
EXCLUSION_SOURCES: dict[str, str] = {}


def _load_exposure_table() -> None:
    """
    Populated from taa.exclusions if the research file is present, so that the
    evidence and the test are separable and the evidence can be re-sourced
    without touching the test.
    """
    global INCIDENTAL_EXPOSURE, EXCLUSION_SOURCES
    try:
        from . import exclusions as _exc
    except Exception:
        INCIDENTAL_EXPOSURE = ()
        EXCLUSION_SOURCES = {}
        return
    INCIDENTAL_EXPOSURE = tuple(
        IncidentalExposure(**row) for row in getattr(_exc, "ROWS", ())
    )
    EXCLUSION_SOURCES = dict(getattr(_exc, "SOURCES", {}))


_load_exposure_table()


# ==========================================================================
# Results
# ==========================================================================
PASS = "PASS"
FAIL = "FAIL"
DISCLOSE = "PASS-WITH-DISCLOSURE"
NOT_ASSESSED = "NOT ASSESSED"
NOT_APPLICABLE = "NOT APPLICABLE"

_HIERARCHY_RANK = {key: rank for rank, key, _label, _standing in config.CONSTRAINT_HIERARCHY}
_HIERARCHY_STANDING = {key: standing for rank, key, _label, standing in config.CONSTRAINT_HIERARCHY}


@dataclass
class CheckResult:
    """One constraint, tested once."""

    name: str
    ips_ref: str
    status: str
    observed: float | None = None
    limit: float | None = None
    slack: float | None = None
    message: str = ""
    ips_rank: int | None = None
    unit: str = "none"
    label: str = ""
    disclosure: str | None = None
    gating: bool = True
    # margin is False on a categorical check, meaning one that counts violations
    # against a limit of zero, or one that tests the shape of the weight vector.
    # Zero violations against a limit of zero is a clean pass rather than a
    # constraint sitting on its limit, and reporting it as binding would bury the
    # constraints that genuinely bind.
    margin: bool = True
    detail: dict[str, Any] = field(default_factory=dict)

    @property
    def passed(self) -> bool:
        return self.status in (PASS, DISCLOSE, NOT_APPLICABLE)

    @property
    def standing(self) -> str:
        return _HIERARCHY_STANDING.get(_rank_key(self.name), "structural")

    @property
    def binding_name(self) -> str:
        """
        The constraint name, qualified by which member of it actually binds.

        line_range and sleeve_range each aggregate nine lines or three sleeves
        into one result whose slack is the tightest member. Reporting a bare
        "line_range" on the dashboard's which-constraint-bound chart would put
        the same word on the board every quarter and say nothing, because the
        policy portfolio holds no cash and cash therefore rests permanently on
        the zero floor of its range. Naming the member turns a meaningless
        recurring label into a true statement about the portfolio.
        """
        t = self.detail.get("tightest")
        return f"{self.name}[{t}]" if t else self.name

    @property
    def binding(self) -> bool:
        """
        At, or within a hair of, the limit. A breach is binding by definition.
        The hair is a reporting threshold and it gates nothing.
        """
        if not self.margin or self.slack is None or self.limit is None:
            return False
        if not math.isfinite(self.slack):
            return False
        if self.status in (NOT_ASSESSED, NOT_APPLICABLE):
            return False
        hair = max(BINDING_TOL_ABS, BINDING_TOL_REL * abs(self.limit))
        return self.slack <= hair

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "label": self.label or self.name,
            "ips_rank": self.ips_rank,
            "ips_ref": self.ips_ref,
            "standing": self.standing,
            "passed": self.passed,
            "gating": self.gating,
            "status": self.status,
            "observed": _jsonable(self.observed),
            "limit": _jsonable(self.limit),
            "slack": _jsonable(self.slack),
            "unit": self.unit,
            "binding": self.binding,
            "binding_name": self.binding_name,
            "message": self.message,
            "disclosure": self.disclosure,
            "detail": _jsonable(self.detail),
        }


@dataclass
class ComplianceResult:
    """The verdict on one proposed allocation."""

    results: list[CheckResult]
    weights: dict[str, float]
    as_of: _dt.date
    label: str = ""

    @property
    def passed(self) -> bool:
        """The verdict. Advisory checks are reported and do not veto (see module docstring)."""
        return all(c.passed for c in self.results if c.gating)

    @property
    def status(self) -> str:
        if not self.passed:
            return FAIL
        if any(c.status == DISCLOSE for c in self.results):
            return DISCLOSE
        return PASS

    def failed(self) -> list[CheckResult]:
        """Gating checks that were not satisfied. These are what stop the proposal."""
        return [c for c in self.results if c.gating and not c.passed]

    def qualifications(self) -> list[CheckResult]:
        """Advisory checks that were not satisfied. These qualify the certificate."""
        return [c for c in self.results if not c.gating and not c.passed]

    def binding(self) -> list[str]:
        """Constraints at or within a hair of their limit, worst slack first."""
        b = [c for c in self.results if c.binding]
        b.sort(key=lambda c: (c.slack if c.slack is not None else 0.0))
        return [c.binding_name for c in b]

    def disclosures(self) -> list[str]:
        """The full IPS 3.5 disclosure texts, which must appear in the report verbatim."""
        out: list[str] = []
        for c in self.results:
            if c.disclosure:
                out.extend(s.strip() for s in c.disclosure.split(" | ") if s.strip())
        return out

    def disclosure_rows(self) -> list[dict]:
        """The same disclosures as structured rows, for a table a trustee can scan."""
        rows: list[dict] = []
        for c in self.results:
            rows.extend(c.detail.get("disclosures", []) or [])
        return rows

    def not_assessed(self) -> list[CheckResult]:
        return [c for c in self.results if c.status == NOT_ASSESSED]

    def by_name(self, name: str) -> CheckResult:
        for c in self.results:
            if c.name == name:
                return c
        raise KeyError(f"no check named {name!r}")

    def governing_rank(self) -> int | None:
        """The highest-standing constraint in the hierarchy that this proposal breaks."""
        ranks = [c.ips_rank for c in self.failed() if c.ips_rank is not None]
        return min(ranks) if ranks else None

    def to_dict(self) -> dict:
        return {
            "label": self.label,
            "as_of": self.as_of.isoformat(),
            "status": self.status,
            "passed": self.passed,
            "governing_rank": self.governing_rank(),
            "n_checks": len(self.results),
            "n_failed": len(self.failed()),
            "n_not_assessed": len(self.not_assessed()),
            "binding": self.binding(),
            "failed": [c.name for c in self.failed()],
            "qualifications": [c.name for c in self.qualifications()],
            "disclosures": self.disclosures(),
            "disclosure_rows": _jsonable(self.disclosure_rows()),
            "weights": {k: float(v) for k, v in self.weights.items()},
            "checks": [c.to_dict() for c in self.results],
        }

    # ------------------------------------------------------------------
    def __str__(self) -> str:
        w = (5, 9, 34, 13, 13, 12, 22)
        head = (
            f"{'RANK':<{w[0]}}{'IPS REF':<{w[1]}}{'CONSTRAINT':<{w[2]}}"
            f"{'OBSERVED':>{w[3]}}{'LIMIT':>{w[4]}}{'SLACK':>{w[5]}}  {'STATUS':<{w[6]}}"
        )
        rule = "=" * len(head)
        thin = "-" * len(head)

        lines = [
            rule,
            "ASHCROFT UNIVERSITY ENDOWMENT      COMPLIANCE TEST OF A PROPOSED ALLOCATION",
            f"Risk function, IPS 2.1. The test returns a pass or a fail and holds no view.",
            rule,
            f"Proposal      {self.label or 'unnamed'}",
            f"As at         {self.as_of.isoformat()}",
            f"Verdict       {self.status}",
        ]
        gr = self.governing_rank()
        if gr is not None:
            standing = dict((r, s) for r, _k, _l, s in config.CONSTRAINT_HIERARCHY)[gr]
            lines.append(
                f"Governed by   hierarchy rank {gr} (IPS 3.6), standing: {standing}"
            )
        lines += [
            f"Checks        {len(self.results)} run, {len(self.failed())} failed, "
            f"{len(self.not_assessed())} not assessed, "
            f"{len(self.qualifications())} advisory qualification(s)",
            rule,
            head,
            thin,
        ]

        for c in self.results:
            rank = str(c.ips_rank) if c.ips_rank is not None else ""
            lines.append(
                f"{rank:<{w[0]}}{c.ips_ref:<{w[1]}}{(c.label or c.name)[:w[2]-1]:<{w[2]}}"
                f"{_fmt(c.observed, c.unit):>{w[3]}}{_fmt(c.limit, c.unit):>{w[4]}}"
                f"{_fmt(c.slack, c.unit):>{w[5]}}  {c.status:<{w[6]}}"
            )

        lines.append(thin)

        fails = self.failed()
        if fails:
            lines.append("")
            lines.append("BREACHES")
            for c in fails:
                rank = f"rank {c.ips_rank}" if c.ips_rank is not None else "structural"
                lines.append(f"  {c.ips_ref}, {rank}, {c.label or c.name}")
                for seg in _wrap(c.message, len(head) - 6):
                    lines.append(f"      {seg}")
            lines.append("")
            lines.append(
                "  An allocation that fails does not proceed to the Committee (IPS 2.1)."
            )
            lines.append(
                "  The remedy is a different allocation or an amendment to the Statement."
            )

        quals = self.qualifications()
        if quals:
            lines.append("")
            lines.append("QUALIFICATIONS, ADVISORY AND NOT VETOING")
            for c in quals:
                lines.append(f"  {c.ips_ref}, {c.label or c.name}: {c.status}")
                for seg in _wrap(c.message, len(head) - 6):
                    lines.append(f"      {seg}")

        rows = self.disclosure_rows()
        if rows:
            lines.append("")
            lines.append(
                f"DISCLOSURES REQUIRED BY IPS 3.5   {len(rows)} item(s). Full text in "
                f"to_dict()['disclosures']."
            )
            dh = (f"  {'VEHICLE':<8}{'LINE':<22}{'EXCLUSION':<15}"
                  f"{'OF VEHICLE':>12}{'OF NAV':>10}  EVIDENCE")
            lines.append(dh)
            lines.append("  " + "-" * (len(dh) - 2))
            for r in rows:
                wv = ("n/e" if r.get("approx_weight_in_vehicle") is None
                      else f"{r['approx_weight_in_vehicle']*100:.2f}%")
                wn = ("n/e" if r.get("approx_weight_of_nav") is None
                      else f"{r['approx_weight_of_nav']*100:.3f}%")
                ev = "verified" if r.get("verified") else "HOLDING VERIFIED, MATERIALITY NOT"
                lines.append(
                    f"  {r['vehicle']:<8}{config.LINE_LABEL[r['line']][:21]:<22}"
                    f"{r['exclusion']:<15}{wv:>12}{wn:>10}  {ev}"
                )
            lines.append(
                "  n/e means the weight was not established. A disclosure is required "
                "either way,"
            )
            lines.append(
                "  because IPS 3.5 does not permit compliance by silence."
            )

        b = self.binding()
        lines.append("")
        lines.append("WHICH CONSTRAINT BOUND")
        if b:
            for c in sorted((x for x in self.results if x.binding),
                            key=lambda x: (x.slack if x.slack is not None else 0.0)):
                t = c.detail.get("tightest")
                lab = (c.label or c.name) + (f", {t}" if t else "")
                lines.append(
                    f"  {lab:<40.40s} slack {_fmt(c.slack, c.unit)}  ({c.ips_ref})"
                )
        else:
            lines.append("  No constraint is at or within a hair of its limit.")

        lines.append(rule)
        return "\n".join(lines)


# ==========================================================================
# Formatting helpers. Direction is never carried by hue. Negatives in parentheses.
# ==========================================================================
def _fmt(v, unit: str) -> str:
    if v is None:
        return "n/a"
    if isinstance(v, str):
        return v
    try:
        v = float(v)
    except (TypeError, ValueError):
        return str(v)
    if not math.isfinite(v):
        return "n/a"
    if unit == "pct":
        n, suf = v * 100.0, "%"
    elif unit == "pp":
        n, suf = v * 100.0, "pp"
    elif unit == "bps":
        n, suf = v, "bps"
    elif unit == "count":
        n, suf = v, ""
        return f"({abs(int(n))})" if n < 0 else f"{int(n)}"
    elif unit == "x":
        n, suf = v, "x"
    else:
        n, suf = v, ""
    txt = f"{abs(n):,.2f}{suf}"
    return f"({txt})" if n < 0 else txt


def _wrap(text: str, width: int) -> list[str]:
    words, out, cur = str(text).split(), [], ""
    for wd in words:
        if len(cur) + len(wd) + 1 > width and cur:
            out.append(cur)
            cur = wd
        else:
            cur = f"{cur} {wd}".strip()
    if cur:
        out.append(cur)
    return out or [""]


def _jsonable(x):
    if isinstance(x, dict):
        return {str(k): _jsonable(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [_jsonable(v) for v in x]
    if isinstance(x, (np.floating, np.integer)):
        x = x.item()
    if isinstance(x, float):
        return None if not math.isfinite(x) else round(x, 10)
    if isinstance(x, (_dt.date, _dt.datetime)):
        return x.isoformat()
    return x


def _rank_key(name: str) -> str:
    if name.startswith("liquidity"):
        return "liquidity"
    if name.startswith("leverage") or name.startswith("board_"):
        return "legal"
    if name.startswith("drawdown"):
        return "drawdown"
    if name.startswith("tracking"):
        return "tracking_error"
    return name


def _rank(name: str) -> int | None:
    return _HIERARCHY_RANK.get(_rank_key(name))


def _to_date(x) -> _dt.date:
    if x is None:
        return config.REPORT_DATE
    if isinstance(x, _dt.datetime):
        return x.date()
    if isinstance(x, _dt.date):
        return x
    return _dt.date.fromisoformat(str(x)[:10])


def _vec(weights: dict[str, float]) -> np.ndarray:
    return np.array([float(weights.get(k, np.nan)) for k in config.LINES], dtype=float)


# ==========================================================================
# Drawdown mathematics
# ==========================================================================
def max_drawdown(path) -> float:
    """
    Worst peak to trough of a value path, as a negative fraction. Zero for a
    path that never falls below its running maximum.
    """
    a = np.asarray(pd.Series(path).astype(float).dropna().values, dtype=float)
    if a.size < 2:
        return 0.0
    peak = np.maximum.accumulate(a)
    with np.errstate(divide="ignore", invalid="ignore"):
        dd = a / peak - 1.0
    dd = dd[np.isfinite(dd)]
    return float(dd.min()) if dd.size else 0.0


_UNIT_MDD_CACHE: dict[tuple, float] = {}


def _unit_log_mdd_quantile(q: float = MDD_QUANTILE,
                           steps: int = MDD_MC_STEPS,
                           paths: int = MDD_MC_PATHS,
                           seed: int = MDD_MC_SEED) -> float:
    """
    The q-quantile of the maximum drawdown of a driftless Brownian motion of
    unit annualised volatility over one year, measured on the log path.

    Driftlessness is what makes this reusable. With zero drift the log path
    scales exactly in sigma, so one simulation serves every portfolio and the
    answer does not move between runs. The seed is fixed, so the test is
    reproducible, which matters more here than in a research setting: a
    compliance test that returns a different verdict on a different seed is not
    a compliance test.
    """
    key = (round(q, 6), steps, paths, seed)
    if key in _UNIT_MDD_CACHE:
        return _UNIT_MDD_CACHE[key]
    rng = np.random.default_rng(seed)
    dt = 1.0 / steps
    # Drawn in chunks rather than as one (paths, steps) block. The generator is
    # consumed in the same order either way, so every variate lands in the same
    # position and the answer is bit-identical to the single-block form; the
    # only thing that changes is peak memory, which a whole-block draw spikes to
    # several hundred megabytes once the intermediate cumulative sum and running
    # maximum are counted. A compliance test that fails on allocation under
    # memory pressure is a compliance test that did not run.
    chunk = 2000
    mdd_parts = []
    done = 0
    while done < paths:
        n = min(chunk, paths - done)
        z = rng.standard_normal((n, steps)) * math.sqrt(dt)
        x = np.cumsum(z, axis=1)
        x = np.concatenate([np.zeros((n, 1)), x], axis=1)
        run_max = np.maximum.accumulate(x, axis=1)
        mdd_parts.append((run_max - x).max(axis=1))
        done += n
        del z, x, run_max
    mdd_log = np.concatenate(mdd_parts)
    val = float(np.quantile(mdd_log, q))
    _UNIT_MDD_CACHE[key] = val
    return val


def parametric_max_drawdown(sigma_annual: float,
                            horizon_years: float = MDD_HORIZON_YEARS,
                            quantile: float = MDD_QUANTILE) -> dict:
    """
    An ex ante maximum drawdown for a portfolio of annualised volatility sigma.

    Two numbers, because they answer different questions.

    expected    The closed form for the expected maximum drawdown of a
                driftless Brownian motion over a finite horizon,
                E[MDD_log] = sqrt(pi/2) . sigma . sqrt(T), from Magdon-Ismail,
                Atiya, Pratap and Abu-Mostafa (2004). A central expectation.

    quantile    The q-quantile of the same object, by simulation. This is the
                figure the test reads, because the mandate limit at IPS 3.3 is
                a ceiling on an outcome rather than a statement about an
                average, and a portfolio whose average drawdown sits inside the
                limit can still breach it routinely.

    Both are returned as negative price fractions, converted from the log
    measure by 1 - exp(-d), so a log drawdown of 0.25 reads as (22.12%) rather
    than (25.00%).

    Drift is set to zero. That is a conservative choice and it is deliberate.
    Adding the mandate's 8.10% required return would lower both figures, which
    is the direction an optimistic model moves, and the size of that effect is
    reported alongside so a reader can see what the choice costs.
    """
    sigma = float(max(sigma_annual, 0.0))
    rt = math.sqrt(max(horizon_years, 0.0))
    e_log = math.sqrt(math.pi / 2.0) * sigma * rt
    q_log = _unit_log_mdd_quantile(quantile) * sigma * rt
    return {
        "sigma_annual": sigma,
        "horizon_years": horizon_years,
        "quantile": quantile,
        "expected": -(1.0 - math.exp(-e_log)),
        "quantile_mdd": -(1.0 - math.exp(-q_log)),
        "unit_quantile_log": _unit_log_mdd_quantile(quantile),
    }


def portfolio_vol(w: np.ndarray, cov: np.ndarray) -> float:
    v = float(w @ np.asarray(cov, dtype=float) @ w)
    return math.sqrt(max(v, 0.0))


def tracking_error_bps(w: np.ndarray, cov: np.ndarray,
                       bench: np.ndarray | None = None) -> float:
    b = np.array(config.policy_vector(), dtype=float) if bench is None else np.asarray(bench, float)
    d = w - b
    return float(math.sqrt(max(float(d @ np.asarray(cov, float) @ d), 0.0)) * 10_000.0)


# ==========================================================================
# Stress replay, through the sanctioned point-in-time path only
# ==========================================================================
def stress_replay(weights: dict[str, float], as_of, episodes=STRESS_EPISODES) -> dict:
    """
    Hold the proposed weights, unchanged, through each named episode and read
    the worst peak to trough of the resulting value path.

    Buy and hold from the episode start, so the weights drift with the market.
    That is what "holding the allocation through the episode" means, and it
    avoids crediting the portfolio with a rebalancing policy the proposal does
    not contain.

    Reads daily total-return prices through taa.pitdata, which refuses anything
    published after the as-of date (IPS 4.4). Replaying 2008 from an as-of date
    in 2026 is history rather than look-ahead: every price in the window was
    public long before the proposal was written.

    Raises nothing. On a data failure it returns {"available": False, ...} and
    the caller records the check as not assessed rather than as a pass.
    """
    as_of = _to_date(as_of)
    out = {"available": False, "episodes": [], "error": None,
           "as_of": as_of.isoformat()}
    try:
        view = pitdata.as_of(as_of)
        lines = list(config.LINES)
        px = view.line_prices(lines)
    except Exception as exc:                                  # noqa: BLE001
        out["error"] = f"{type(exc).__name__}: {exc}"
        return out

    if px is None or not len(px):
        out["error"] = "price history is empty"
        return out

    w = pd.Series({k: float(weights.get(k, 0.0)) for k in config.LINES})
    for name, start, end in episodes:
        try:
            seg = px.loc[pd.Timestamp(start):pd.Timestamp(end)].dropna(how="all")
            seg = seg.ffill().dropna(how="any")
            if len(seg) < 5:
                out["episodes"].append({"episode": name, "start": start, "end": end,
                                        "available": False,
                                        "reason": "fewer than five observations"})
                continue
            rel = seg / seg.iloc[0]
            value = (rel * w.reindex(rel.columns).values).sum(axis=1)
            bench = (rel * np.array(config.policy_vector())).sum(axis=1)
            out["episodes"].append({
                "episode": name, "start": start, "end": end, "available": True,
                "observations": int(len(seg)),
                "first": str(seg.index.min().date()), "last": str(seg.index.max().date()),
                "mdd": max_drawdown(value),
                "policy_mdd": max_drawdown(bench),
                "total_return": float(value.iloc[-1] - 1.0),
                "policy_total_return": float(bench.iloc[-1] - 1.0),
            })
        except Exception as exc:                              # noqa: BLE001
            out["episodes"].append({"episode": name, "start": start, "end": end,
                                    "available": False,
                                    "reason": f"{type(exc).__name__}: {exc}"})

    run = [e for e in out["episodes"] if e.get("available")]
    out["available"] = bool(run)
    out["episodes_declared"] = len(list(episodes))
    out["episodes_run"] = len(run)
    out["episodes_unavailable"] = [
        {"episode": e["episode"], "start": e["start"], "end": e["end"],
         "reason": e.get("reason", "no price history in the sanctioned cache")}
        for e in out["episodes"] if not e.get("available")
    ]
    if run:
        worst = min(run, key=lambda e: e["mdd"])
        out["worst_episode"] = worst["episode"]
        out["worst_mdd"] = worst["mdd"]
        out["worst_policy_mdd"] = worst["policy_mdd"]
        out["policy_worst_mdd"] = min(e["policy_mdd"] for e in run)
    return out


# ==========================================================================
# Corridors. Owned by the Implementation and Operations desk (taa.costs).
# ==========================================================================
def _corridors() -> tuple[dict[str, float], str, bool]:
    """
    Rebalancing corridor half-width per line, in weight fraction.

    IPS 4.5 gives corridor widths to the Implementation desk, which sets them
    with regard to the volatility and transaction cost of each line. This
    function asks that desk. If taa.costs is not yet present it degrades to a
    documented default and says so, and the caller marks the corridor arm of
    the test as not tested rather than as satisfied.

    The documented default is the minimum trade size itself. That default makes
    every corridor exactly actionable and therefore makes the corridor test
    vacuous. It is chosen precisely so that it cannot manufacture a pass that
    means something: a reader sees the source recorded as "default" and knows
    the corridor arm of IPS 4.5 was not exercised.
    """
    default = {k: config.MIN_TRADE_PP / 100.0 for k in config.LINES}
    try:
        from . import costs as _costs                          # noqa: PLC0415
    except Exception:
        return default, "default (taa.costs not present)", False
    for attr in ("CORRIDORS", "corridors", "corridor_widths"):
        obj = getattr(_costs, attr, None)
        if obj is None:
            continue
        try:
            table = obj() if callable(obj) else dict(obj)
            got = {k: float(table[k]) for k in config.LINES if k in table}
            if len(got) == len(config.LINES):
                return got, f"taa.costs.{attr}", True
        except Exception:
            continue
    return default, "default (taa.costs present, no corridor table)", False


# ==========================================================================
# The individual checks
# ==========================================================================
def _mk(name: str, ips_ref: str, status: str, **kw) -> CheckResult:
    return CheckResult(name=name, ips_ref=ips_ref, status=status,
                       ips_rank=_rank(name), **kw)


def _check_structural(weights: dict[str, float]) -> list[CheckResult]:
    out: list[CheckResult] = []
    keys = set(weights)
    missing = [k for k in config.LINES if k not in keys]
    extra = sorted(keys - set(config.LINES))
    n_wrong = len(missing) + len(extra)
    out.append(_mk(
        "structural_keys", "IPS 4.1", PASS if n_wrong == 0 else FAIL, margin=False,
        observed=float(n_wrong), limit=0.0, slack=float(-n_wrong), unit="count",
        label="Line keys, all nine present",
        message=(
            "Every one of the nine mandate lines carries a weight and no line "
            "outside the opportunity set appears."
            if n_wrong == 0 else
            f"Weight vector does not match the opportunity set at IPS 4.1. "
            f"Missing: {missing or 'none'}. Not in the opportunity set: {extra or 'none'}."
        ),
        detail={"missing": missing, "extra": extra},
    ))

    vals = {k: weights.get(k) for k in config.LINES}
    bad = sorted(k for k, v in vals.items()
                 if v is None or not isinstance(v, (int, float, np.floating))
                 or not math.isfinite(float(v)))
    out.append(_mk(
        "structural_finite", "IPS 4.1", PASS if not bad else FAIL, margin=False,
        observed=float(len(bad)), limit=0.0, slack=float(-len(bad)), unit="count",
        label="Weights finite, no NaN",
        message=("No weight is missing, infinite or NaN."
                 if not bad else
                 f"Weights are not numbers on: {bad}. A weight vector carrying a NaN "
                 f"cannot be tested and is not a proposal."),
        detail={"non_finite": bad},
    ))

    if bad or missing:
        out.append(_mk("structural_sum", "IPS 4.1", NOT_ASSESSED, unit="pct",
                       label="Weights sum to one",
                       message="The weight vector is malformed, so its sum carries no meaning."))
        return out

    total = float(sum(float(v) for v in vals.values()))
    dev = abs(total - 1.0)
    out.append(_mk(
        "structural_sum", "IPS 4.1", PASS if dev <= WEIGHT_SUM_TOL else FAIL, margin=False,
        observed=total, limit=1.0, slack=WEIGHT_SUM_TOL - dev, unit="pct",
        label="Weights sum to one",
        message=(f"Weights sum to {total:.8f}."
                 if dev <= WEIGHT_SUM_TOL else
                 f"Weights sum to {total:.6f}, which is {dev*100:.4f}pp away from one. "
                 f"An allocation that does not sum to one is not an allocation."),
    ))
    return out


def _check_liquidity(weights: dict[str, float], context: dict) -> list[CheckResult]:
    override = dict(context.get("liquid_within_5d") or {})
    table = {k: bool(override.get(k, config.LIQUID_WITHIN_5D[k])) for k in config.LINES}
    liquid = float(sum(float(weights.get(k, 0.0)) for k in config.LINES if table[k]))
    illiquid_lines = sorted(k for k in config.LINES
                            if not table[k] and float(weights.get(k, 0.0)) > 0)

    src = "config.LIQUID_WITHIN_5D"
    if override:
        src += f", with {len(override)} line(s) overridden by the custodian in context"

    floor = config.LIQUIDITY_FLOOR
    out = [_mk(
        "liquidity_floor", "IPS 3.4", PASS if liquid >= floor - FLOAT_EPS else FAIL,
        observed=liquid, limit=floor, slack=liquid - floor, unit="pct",
        label="Realisable within five business days",
        message=(
            f"{liquid*100:.2f}% of net asset value is realisable within five business "
            f"days against a floor of {floor*100:.2f}%. Source of the liquidity "
            f"classification: {src}."
            if liquid >= floor - FLOAT_EPS else
            f"Only {liquid*100:.2f}% of net asset value is realisable within five "
            f"business days against a floor of {floor*100:.2f}%. Lines carrying weight "
            f"that do not clear same week: {illiquid_lines}. Liquidity is rank 1 in the "
            f"hierarchy at IPS 3.6 and is not negotiable."
        ),
        detail={"liquid_lines": [k for k in config.LINES if table[k]],
                "illiquid_lines_with_weight": illiquid_lines,
                "classification_source": src},
    )]

    # The quarterly distribution, funded without a forced sale.
    q_draw_usd = config.ANNUAL_DISTRIBUTION_USD / 4.0
    q_draw_frac = q_draw_usd / config.FUND_NAV_USD
    cover = (liquid / q_draw_frac) if q_draw_frac > 0 else float("inf")
    ok = liquid >= q_draw_frac - FLOAT_EPS
    out.append(_mk(
        "liquidity_distribution", "IPS 3.4", PASS if ok else FAIL,
        observed=liquid, limit=q_draw_frac, slack=liquid - q_draw_frac, unit="pct",
        label="Quarterly distribution funded",
        message=(
            f"The quarterly distribution of USD {q_draw_usd:,.0f}, one quarter of the "
            f"USD {config.ANNUAL_DISTRIBUTION_USD:,.0f} annual draw on a "
            f"USD {config.FUND_NAV_USD:,.0f} fund, is {q_draw_frac*100:.2f}% of net "
            f"asset value. Same-week-liquid assets stand at {liquid*100:.2f}% of net "
            f"asset value, covering the draw {cover:,.1f} times over, so the "
            f"distribution is funded without a forced sale."
            if ok else
            f"The quarterly distribution of USD {q_draw_usd:,.0f} is {q_draw_frac*100:.2f}% "
            f"of net asset value and same-week-liquid assets stand at only "
            f"{liquid*100:.2f}%. The draw cannot be met without selling an asset that "
            f"does not clear within five business days, which is a forced sale. "
            f"IPS 3.6 rank 1: the distribution is funded, and it is not negotiable."
        ),
        detail={"quarterly_draw_usd": q_draw_usd, "quarterly_draw_fraction": q_draw_frac,
                "coverage_multiple": cover if math.isfinite(cover) else None},
    ))
    return out


def _check_leverage(weights: dict[str, float]) -> list[CheckResult]:
    vals = {k: float(weights.get(k, 0.0)) for k in config.LINES}
    gross = float(sum(abs(v) for v in vals.values()))
    cap = config.MAX_GROSS_EXPOSURE
    out = [_mk(
        "leverage_gross", "IPS 3.5", PASS if gross <= cap + FLOAT_EPS else FAIL,
        observed=gross, limit=cap, slack=cap - gross, unit="x",
        label="Gross exposure against NAV",
        message=(
            f"Gross exposure, the sum of absolute weights, is {gross:.4f} times net "
            f"asset value against a cap of {cap:.2f}."
            if gross <= cap + FLOAT_EPS else
            f"Gross exposure is {gross:.4f} times net asset value against a cap of "
            f"{cap:.2f}. IPS 3.5 states the constraint is driven by unrelated business "
            f"taxable income on debt-financed income and is not a risk preference that "
            f"analysis may trade against. Rank 2, not negotiable."
        ),
    )]

    shorts = sorted((k for k, v in vals.items() if v < -FLOAT_EPS),
                    key=lambda k: vals[k])
    worst = min(vals.values()) if vals else 0.0
    out.append(_mk(
        "leverage_short", "IPS 3.5", PASS if not shorts else FAIL,
        observed=worst, limit=0.0, slack=worst, unit="pct",
        label="No negative weight",
        message=(
            f"Every line is long or flat. Smallest weight is {worst*100:.2f}%."
            if not shorts else
            f"Negative weights on {', '.join(f'{k} at {vals[k]*100:.2f}%' for k in shorts)}. "
            f"A short position is leverage at fund level, and the resulting debt-financed "
            f"income is the unrelated business taxable income that IPS 3.5 exists to "
            f"prevent. Rank 2, not negotiable."
        ),
        detail={"negative_lines": shorts},
    ))
    return out


def _check_exclusions(weights: dict[str, float], context: dict) -> CheckResult:
    """
    IPS 3.5. Compliance is assessed at the vehicle level, and a broad index
    vehicle carrying incidental exposure is disclosed rather than deemed
    compliant by silence.

    Two distinct outcomes.

    DIRECT exposure to tobacco or thermal coal is a breach and a hard fail. It
    is reported by the Implementation desk through context["direct_exposure"],
    a mapping of line to a list of excluded activities held directly, since the
    vehicle-level facts are theirs and not the risk function's to invent.

    INCIDENTAL exposure inside a broad index vehicle satisfies the constraint
    and requires a disclosure. Silence is not an available answer.
    """
    direct_raw = dict(context.get("direct_exposure") or {})
    vehicles = dict(context.get("vehicles") or {})
    held = {k: float(weights.get(k, 0.0)) for k in config.LINES}

    breaches = []
    for line, activities in direct_raw.items():
        if line not in config.LINES or held.get(line, 0.0) <= FLOAT_EPS:
            continue
        for act in (activities if isinstance(activities, (list, tuple)) else [activities]):
            if str(act).lower() in {e.lower() for e in config.BOARD_EXCLUSIONS}:
                breaches.append((line, str(act)))

    disclosures: list[str] = []
    disclosed_rows: list[dict] = []
    for line in config.LINES:
        if held[line] <= FLOAT_EPS:
            continue
        vehicle = vehicles.get(line, config.VEHICLE[line])
        for row in INCIDENTAL_EXPOSURE:
            if row.vehicle != vehicle:
                continue
            wt = (f", approximately {row.approx_weight*100:.2f}% of the vehicle "
                  f"and {row.approx_weight*held[line]*100:.3f}% of net asset value"
                  if row.approx_weight is not None else
                  ", weight not established")
            status = "verified" if row.verified else "NOT VERIFIED"
            disclosures.append(
                f"IPS 3.5 disclosure. {config.LINE_LABEL[line]} is implemented through "
                f"{vehicle} at {held[line]*100:.2f}% of net asset value. That vehicle "
                f"carries incidental {row.exclusion} exposure through "
                f"{', '.join(row.issuers)}{wt}. Holding {status} against {row.source} "
                f"as at {row.as_of}. {row.note} The exposure is incidental to a broad "
                f"index and is disclosed rather than treated as compliant by silence."
            )
            disclosed_rows.append({
                "line": line, "vehicle": vehicle, "exclusion": row.exclusion,
                "issuers": list(row.issuers), "approx_weight_in_vehicle": row.approx_weight,
                "approx_weight_of_nav": (None if row.approx_weight is None
                                         else row.approx_weight * held[line]),
                "verified": row.verified, "source": row.source, "as_of": row.as_of,
            })

    if breaches:
        return _mk(
            "board_exclusions", "IPS 3.5", FAIL, margin=False,
            observed=float(len(breaches)), limit=0.0, slack=float(-len(breaches)),
            unit="count", label="Board exclusions, tobacco and coal",
            message=(
                "Direct exposure to a board exclusion on "
                + "; ".join(f"{ln} ({act})" for ln, act in breaches)
                + ". IPS 3.5 permits no direct exposure to tobacco or thermal coal. "
                  "Rank 2, not negotiable."
            ),
            detail={"direct_breaches": [{"line": ln, "activity": a} for ln, a in breaches],
                    "disclosures": disclosed_rows},
        )

    if not INCIDENTAL_EXPOSURE:
        return _mk(
            "board_exclusions", "IPS 3.5", NOT_ASSESSED,
            unit="count", label="Board exclusions, tobacco and coal",
            message=(
                "No vehicle-level exposure evidence is loaded, so incidental exposure "
                "could not be assessed. IPS 3.5 says a broad index vehicle carrying "
                "incidental exposure is disclosed rather than deemed compliant by "
                "silence, and an untested vehicle is exactly that silence."
            ),
        )

    if disclosures:
        n_unver = sum(1 for r in disclosed_rows if not r["verified"])
        return _mk(
            # observed and limit count DIRECT breaches, which is what the constraint
            # prohibits. Slack is None because a categorical prohibition has no
            # meaningful margin and should not appear on the binding list.
            "board_exclusions", "IPS 3.5", DISCLOSE,
            observed=0.0, limit=0.0, slack=None, unit="count",
            label="Board exclusions, tobacco and coal",
            message=(
                f"No direct exposure to tobacco or thermal coal, so the prohibition at "
                f"IPS 3.5 is satisfied. {len(disclosed_rows)} incidental exposure(s) "
                f"inside broad index vehicles require disclosure, of which {n_unver} rest "
                f"on a holding that is verified while its materiality is not. The "
                f"constraint is satisfied and the disclosure is mandatory: IPS 3.5 says "
                f"a broad index vehicle carrying incidental exposure is disclosed rather "
                f"than deemed compliant by silence."
            ),
            disclosure=" | ".join(disclosures),
            detail={"disclosures": disclosed_rows},
        )

    return _mk(
        "board_exclusions", "IPS 3.5", PASS, margin=False,
        observed=0.0, limit=0.0, slack=0.0, unit="count",
        label="Board exclusions, tobacco and coal",
        message=("No direct exposure to tobacco or thermal coal, and no incidental "
                 "exposure recorded against any vehicle carrying weight."),
    )


def _check_drawdown_realised(nav_path) -> CheckResult:
    limit = config.DRAWDOWN_LIMIT
    if nav_path is None:
        return _mk("drawdown_realised", "IPS 3.3", NOT_APPLICABLE, unit="pct",
                   limit=limit, label="Drawdown, realised peak to trough",
                   message=("No realised net asset value path was supplied. A "
                            "forward-looking proposal has none, and the ex ante test "
                            "carries the rank 3 constraint in its place."))
    s = pd.Series(nav_path).astype(float).dropna()
    if len(s) < 2:
        return _mk("drawdown_realised", "IPS 3.3", NOT_ASSESSED, unit="pct", limit=limit,
                   label="Drawdown, realised peak to trough",
                   message="The supplied net asset value path holds fewer than two points.")
    mdd = max_drawdown(s)
    ok = mdd >= limit - FLOAT_EPS
    return _mk(
        "drawdown_realised", "IPS 3.3", PASS if ok else FAIL,
        observed=mdd, limit=limit, slack=mdd - limit, unit="pct",
        label="Drawdown, realised peak to trough",
        message=(
            f"Worst realised peak to trough over the supplied path of {len(s)} "
            f"observations is {mdd*100:.2f}% against a limit of {limit*100:.2f}%."
            if ok else
            f"Worst realised peak to trough is {mdd*100:.2f}%, through the "
            f"{limit*100:.2f}% limit at IPS 3.3 by {abs(mdd-limit)*100:.2f}pp. This is "
            f"the realised measure the Board set, not a model output. Beyond this "
            f"level the distribution is reduced, which is the outcome the University "
            f"is least able to absorb."
        ),
        detail={"observations": int(len(s))},
    )


def _drawdown_gate(observed: float, policy_observed: float | None) -> tuple[float, str]:
    """
    The gate for an ex ante drawdown figure.

    The mandate limit is minus twenty per cent. Where the model says the Board's
    own policy portfolio already sits beyond that level, the limit cannot be
    applied as an absolute gate on a proposal, because it would reject the
    benchmark the same Statement requires the portfolio to be measured against,
    and a test that rejects its own baseline rejects everything and therefore
    tests nothing.

    So the gate is the more permissive of the mandate limit and the same model's
    reading of the policy portfolio. No constant is introduced: both terms are
    mandate objects, config.DRAWDOWN_LIMIT and config.POLICY. When the policy
    term is the one that binds, the check says so, and that finding is an
    amendment question for the Board under IPS 2.3 rather than something for the
    portfolio to absorb.
    """
    limit = config.DRAWDOWN_LIMIT
    if policy_observed is None or not math.isfinite(policy_observed):
        return limit, "mandate limit (IPS 3.3)"
    if policy_observed < limit:
        return policy_observed, "policy portfolio under the same model (IPS 4.1)"
    return limit, "mandate limit (IPS 3.3)"


def _check_drawdown_ex_ante(w: np.ndarray, cov) -> CheckResult:
    limit = config.DRAWDOWN_LIMIT
    if cov is None:
        return _mk("drawdown_ex_ante", "IPS 3.3", NOT_ASSESSED, unit="pct", limit=limit,
                   label="Drawdown, ex ante parametric",
                   message=("No covariance matrix was supplied, so the ex ante drawdown "
                            "could not be estimated. An untested constraint is recorded "
                            "as not assessed and counts against the proposal. A risk "
                            "function that cannot measure a limit does not certify "
                            "compliance with it."))
    cov = np.asarray(cov, dtype=float)
    sigma = portfolio_vol(w, cov)
    est = parametric_max_drawdown(sigma)
    obs = est["quantile_mdd"]

    b = np.array(config.policy_vector(), dtype=float)
    p_sigma = portfolio_vol(b, cov)
    p_est = parametric_max_drawdown(p_sigma)
    gate, gate_src = _drawdown_gate(obs, p_est["quantile_mdd"])

    # What zero drift costs, reported so the choice is visible.
    drift_log = max(config.REQUIRED_RETURN - 0.5 * sigma * sigma, 0.0) * MDD_HORIZON_YEARS
    drifted = -(1.0 - math.exp(-max(0.0, -math.log(1 + obs) - drift_log)))

    ok = obs >= gate - FLOAT_EPS
    return _mk(
        "drawdown_ex_ante", "IPS 3.3", PASS if ok else FAIL,
        observed=obs, limit=gate, slack=obs - gate, unit="pct",
        label="Drawdown, ex ante parametric",
        message=(
            f"Annualised volatility {sigma*100:.2f}%. Modelled {MDD_QUANTILE*100:.0f}th "
            f"percentile maximum drawdown over {MDD_HORIZON_YEARS:.0f} year is "
            f"{obs*100:.2f}%, against an expected maximum drawdown of "
            f"{est['expected']*100:.2f}%. The policy portfolio reads "
            f"{p_est['quantile_mdd']*100:.2f}% on the same model, so the gate is the "
            f"{gate_src} at {gate*100:.2f}%. This is a model output. The mandate limit "
            f"at IPS 3.3 is on realised drawdown."
            + ("" if ok else
               f" The proposal is exposed to {abs(obs-gate)*100:.2f}pp more drawdown "
               f"than the gate allows.")
            + (f" A note on the model: the policy portfolio itself reads beyond the "
               f"{limit*100:.2f}% mandate limit, which is the tension IPS 3.3 states "
               f"exists by construction. That is an amendment question for the Board "
               f"under IPS 2.3 and is not resolved by adjusting this test."
               if p_est["quantile_mdd"] < limit else "")
        ),
        detail={
            "sigma_annual": sigma, "expected_mdd": est["expected"],
            "quantile": MDD_QUANTILE, "horizon_years": MDD_HORIZON_YEARS,
            "policy_sigma_annual": p_sigma, "policy_quantile_mdd": p_est["quantile_mdd"],
            "policy_expected_mdd": p_est["expected"],
            "gate_source": gate_src, "mandate_limit": limit,
            "same_figure_with_required_return_drift": drifted,
            "policy_beyond_mandate_limit": bool(p_est["quantile_mdd"] < limit),
        },
    )


def _check_drawdown_stress(weights: dict[str, float], as_of) -> CheckResult:
    limit = config.DRAWDOWN_LIMIT
    rep = stress_replay(weights, as_of)
    if not rep.get("available"):
        return _mk("drawdown_stress", "IPS 3.3", NOT_ASSESSED, unit="pct", limit=limit,
                   gating=False, label="Drawdown, historical stress replay",
                   message=("The stress replay could not be run. "
                            f"{rep.get('error') or 'No episode returned data.'} "
                            "Recorded as not assessed rather than as a pass."),
                   detail=rep)

    obs = rep["worst_mdd"]
    pol = rep.get("policy_worst_mdd")
    gate, gate_src = _drawdown_gate(obs, pol)
    ok = obs >= gate - FLOAT_EPS
    ep_txt = "; ".join(
        f"{e['episode']} {e['mdd']*100:.2f}% against policy {e['policy_mdd']*100:.2f}%"
        for e in rep["episodes"] if e.get("available")
    )
    gaps = rep.get("episodes_unavailable") or []
    gap_txt = ""
    if gaps:
        gap_txt = (
            f" {len(gaps)} declared episode(s) could not be run and are named here so "
            f"the gap is visible: "
            + "; ".join(f"{g['episode']} ({g['start']} to {g['end']})" for g in gaps)
            + ". The sanctioned price cache begins on the estimation prefix set in "
              "taa.config, so this replay does not see them. The worst episode this "
              "test can measure is not the worst episode that has occurred."
        )
    return _mk(
        "drawdown_stress", "IPS 3.3", PASS if ok else FAIL, gating=False,
        observed=obs, limit=gate, slack=obs - gate, unit="pct",
        label="Drawdown, historical stress replay",
        message=(
            f"Proposed weights held unchanged through each episode, buy and hold, on "
            f"daily total-return prices read point in time. {ep_txt}. Worst of "
            f"{rep['episodes_run']} episodes run is {rep['worst_episode']} at "
            f"{obs*100:.2f}%. The gate is the {gate_src} at {gate*100:.2f}%."
            + ("" if ok else
               f" The proposal loses {abs(obs-gate)*100:.2f}pp more than the gate allows "
               f"in the worst named episode.")
            + (f" The policy portfolio itself breaches the {limit*100:.2f}% mandate limit "
               f"in this replay, so an absolute gate here would reject the Board's own "
               f"benchmark. Escalated under IPS 2.3 as an amendment question."
               if pol is not None and pol < limit else "")
            + gap_txt
        ),
        detail=rep,
    )


def _check_tracking_error(w: np.ndarray, cov) -> CheckResult:
    budget = config.TE_BUDGET_BPS
    if cov is None:
        return _mk("tracking_error", "IPS 4.2", NOT_ASSESSED, unit="bps", limit=budget,
                   label="Tracking error, ex ante",
                   message=("No covariance matrix was supplied. Ex ante tracking error "
                            "could not be computed, so compliance with the rank 4 budget "
                            "is not certified."))
    cov = np.asarray(cov, dtype=float)
    te = tracking_error_bps(w, cov)
    ok = te <= budget + FLOAT_EPS
    b = np.array(config.policy_vector(), dtype=float)
    act = w - b
    contrib = {config.LINES[i]: float(act[i]) for i in range(len(config.LINES))
               if abs(act[i]) > 5e-4}
    return _mk(
        "tracking_error", "IPS 4.2", PASS if ok else FAIL,
        observed=te, limit=budget, slack=budget - te, unit="bps",
        label="Tracking error, ex ante",
        message=(
            f"Ex ante tracking error against the policy portfolio is {te:.1f}bps against "
            f"a budget of {budget:.0f}bps, computed as the square root of the active "
            f"weight quadratic form on the supplied annualised covariance."
            if ok else
            f"Ex ante tracking error is {te:.1f}bps against a budget of {budget:.0f}bps, "
            f"over by {te-budget:.1f}bps. IPS 3.6 rank 4 is hard: a tactical view that "
            f"would breach it is truncated to the constraint and is not overridden by "
            f"argument."
        ),
        detail={"active_weights": contrib,
                "sum_abs_active": float(np.abs(act).sum())},
    )


def _check_line_ranges(weights: dict[str, float]) -> CheckResult:
    """
    IPS 4.1. "Tactical positions ... must remain inside the permitted range,
    which binds independently of the tracking-error budget. A position inside
    the tracking-error budget but outside its range is a breach."

    This check therefore carries no hierarchy rank and reads no tracking error.
    It can fail while the tracking error check passes, and that is the case the
    Statement names.
    """
    rows, worst_slack, worst_line = [], float("inf"), None
    for k in config.LINES:
        v = float(weights.get(k, 0.0))
        lo, hi = config.RANGE[k]
        slack = min(v - lo, hi - v)
        rows.append({"line": k, "weight": v, "low": lo, "high": hi, "slack": slack,
                     "inside": slack >= -FLOAT_EPS})
        if slack < worst_slack:
            worst_slack, worst_line = slack, k
    bad = [r for r in rows if not r["inside"]]
    ok = not bad
    return _mk(
        "line_range", "IPS 4.1", PASS if ok else FAIL,
        observed=worst_slack, limit=0.0, slack=worst_slack, unit="pp",
        label="Permitted range, every line",
        message=(
            f"Every line sits inside its permitted range. The tightest is "
            f"{config.LINE_LABEL[worst_line]} with {worst_slack*100:.2f}pp of room."
            if ok else
            "Outside the permitted range: "
            + "; ".join(
                f"{config.LINE_LABEL[r['line']]} at {r['weight']*100:.2f}% against "
                f"{r['low']*100:.0f}% to {r['high']*100:.0f}%" for r in bad)
            + ". IPS 4.1 states the range binds independently of the tracking-error "
              "budget, so a position inside the budget and outside its range is a breach."
        ),
        detail={"lines": rows, "outside": [r["line"] for r in bad],
                "tightest": worst_line,
                "tightest_slack": worst_slack},
    )


def _check_sleeve_ranges(weights: dict[str, float]) -> CheckResult:
    rows, worst_slack, worst_sleeve = [], float("inf"), None
    for sl, (lo, hi) in config.SLEEVE_RANGE.items():
        tot = float(sum(float(weights.get(k, 0.0)) for k in config.LINES
                        if config.SLEEVE[k] == sl))
        slack = min(tot - lo, hi - tot)
        rows.append({"sleeve": sl, "total": tot, "low": lo, "high": hi, "slack": slack,
                     "inside": slack >= -FLOAT_EPS})
        if slack < worst_slack:
            worst_slack, worst_sleeve = slack, sl
    bad = [r for r in rows if not r["inside"]]
    ok = not bad
    return _mk(
        "sleeve_range", "IPS 4.1", PASS if ok else FAIL,
        observed=worst_slack, limit=0.0, slack=worst_slack, unit="pp",
        label="Sleeve totals",
        message=(
            f"Every sleeve total sits inside its band. The tightest is {worst_sleeve} "
            f"with {worst_slack*100:.2f}pp of room."
            if ok else
            "Sleeve total outside its band: "
            + "; ".join(
                f"{r['sleeve'].replace('_',' ')} at {r['total']*100:.2f}% against "
                f"{r['low']*100:.0f}% to {r['high']*100:.0f}%" for r in bad)
            + ". A sleeve can breach while every line inside it sits within its own "
              "range, which is why IPS 4.1 sets both."
        ),
        detail={"sleeves": rows, "outside": [r["sleeve"] for r in bad],
                "tightest": worst_sleeve,
                "tightest_slack": worst_slack},
    )


def _check_min_trade(weights: dict[str, float],
                     prior_weights: dict[str, float] | None) -> list[CheckResult]:
    thresh = config.MIN_TRADE_PP / 100.0
    corr, corr_src, corr_real = _corridors()

    narrow = sorted(k for k in config.LINES if corr[k] < thresh - FLOAT_EPS)
    tightest = min((corr[k] for k in config.LINES), default=float("nan"))
    if corr_real:
        c_status = PASS if not narrow else FAIL
        c_msg = (
            f"Corridor widths from {corr_src}. The tightest is {tightest*100:.2f}pp "
            f"against a minimum trade of {thresh*100:.2f}pp."
            if not narrow else
            f"Corridor narrower than the minimum trade on {narrow}. IPS 4.5 states the "
            f"interaction is explicit in the rebalancing policy, since a corridor "
            f"narrower than the minimum trade cannot be acted on. Such a corridor "
            f"signals a rebalance the fund is not permitted to execute."
        )
    else:
        c_status = NOT_ASSESSED
        c_msg = (
            f"Corridor widths were not available. Source recorded as {corr_src}. The "
            f"default sets every corridor equal to the minimum trade, which makes the "
            f"comparison vacuous by construction, so the corridor arm of IPS 4.5 is "
            f"recorded as not tested rather than as satisfied. The Implementation and "
            f"Operations desk owns taa.costs and this check reads it as soon as it exists."
        )

    # Advisory. The corridor table is a property of the rebalancing policy at
    # IPS 4.5 and is owned by the Implementation desk. No proposed set of weights
    # can cure a corridor narrower than the minimum trade, so vetoing an
    # allocation over it would veto every allocation equally and test nothing.
    out = [_mk("corridor_width", "IPS 4.5", c_status,
               observed=tightest, limit=thresh,
               slack=(tightest - thresh) if math.isfinite(tightest) else None,
               unit="pp", label="Corridor against minimum trade",
               message=c_msg, gating=False,
               detail={"corridors": corr, "source": corr_src,
                       "narrower_than_min_trade": narrow})]

    if prior_weights is None:
        out.append(_mk("min_trade", "IPS 4.2", NOT_APPLICABLE, limit=thresh, unit="pp",
                       label="Minimum trade size",
                       message=("No prior weights were supplied, so there is no proposed "
                                "trade to size. An initial allocation has no prior.")))
        return out

    trades, dust = [], []
    for k in config.LINES:
        d = float(weights.get(k, 0.0)) - float(prior_weights.get(k, 0.0))
        trades.append({"line": k, "delta": d, "abs": abs(d)})
        if FLOAT_EPS < abs(d) < thresh - FLOAT_EPS:
            dust.append({"line": k, "delta": d})
    turnover = float(sum(t["abs"] for t in trades)) / 2.0
    smallest = min((t["abs"] for t in trades if t["abs"] > FLOAT_EPS), default=float("nan"))

    ok = not dust
    out.append(_mk(
        "min_trade", "IPS 4.2", PASS if ok else FAIL,
        observed=smallest if math.isfinite(smallest) else 0.0, limit=thresh,
        slack=(smallest - thresh) if math.isfinite(smallest) else None, unit="pp",
        label="Minimum trade size",
        message=(
            (f"Smallest proposed trade is {smallest*100:.2f}pp of net asset value against "
             f"a minimum of {thresh*100:.2f}pp. One-way turnover {turnover*100:.2f}pp."
             if math.isfinite(smallest) else
             "The proposal changes no line, so there is no trade to size.")
            if ok else
            "Proposed trades below the minimum on "
            + "; ".join(f"{config.LINE_LABEL[d['line']]} at {d['delta']*100:+.2f}pp"
                        for d in dust)
            + f". IPS 4.2 sets the minimum trade at {thresh*100:.2f}pp, and anything "
              f"smaller does not justify the turnover. A change strictly between zero "
              f"and the minimum cannot be executed, so the allocation as proposed is "
              f"not implementable. It is not a rounding matter: the portfolio that "
              f"would result is a different portfolio from the one tested."
        ),
        detail={"trades": trades, "below_minimum": dust, "one_way_turnover": turnover},
    ))
    return out


def _check_investable(weights: dict[str, float], as_of: _dt.date) -> CheckResult:
    bad = []
    for k in config.LINES:
        v = float(weights.get(k, 0.0))
        if abs(v) > FLOAT_EPS and as_of < config.INVESTABLE_FROM[k]:
            bad.append({"line": k, "weight": v, "vehicle": config.VEHICLE[k],
                        "investable_from": config.INVESTABLE_FROM[k].isoformat()})
    ok = not bad
    return _mk(
        "investable_date", "IPS 4.1", PASS if ok else FAIL, margin=False,
        observed=float(len(bad)), limit=0.0, slack=float(-len(bad)), unit="count",
        label="Investable dates",
        message=(
            f"Every line carrying weight was investable on {as_of.isoformat()}."
            if ok else
            "Weight on a line before its vehicle existed: "
            + "; ".join(
                f"{config.LINE_LABEL[r['line']]} at {r['weight']*100:.2f}% through "
                f"{r['vehicle']}, which lists from {r['investable_from']}" for r in bad)
            + f", against an as-of date of {as_of.isoformat()}. IPS 4.1: investable "
              f"dates bind. A backtest that holds a vehicle before it existed is not "
              f"a backtest of anything that could have been done."
        ),
        detail={"violations": bad, "as_of": as_of.isoformat()},
    )


# ==========================================================================
# The test
# ==========================================================================
def check(weights: dict[str, float],
          *,
          cov: "np.ndarray | None" = None,
          as_of=None,
          prior_weights: dict[str, float] | None = None,
          nav_path: "pd.Series | None" = None,
          context: dict | None = None) -> ComplianceResult:
    """
    Test one proposed allocation against every binding constraint in the
    mandate, and return a pass or a fail.

    weights         line to weight, keys as config.LINES.
    cov             annualised covariance matrix, order config.LINES. Without
                    it the tracking error and ex ante drawdown constraints are
                    recorded as not assessed, which is a failure of the test.
    as_of           the date the office is standing on. Defaults to
                    config.REPORT_DATE.
    prior_weights   the portfolio being traded from, for the minimum trade test.
    nav_path        a realised net asset value path, for the realised drawdown
                    test.
    context         evidence supplied by the desks that own the underlying
                    facts, none of it invented here:
                      label                 a name for the proposal
                      liquid_within_5d      per line override of the same-week
                                            liquidity classification, reported
                                            by the custodian or the
                                            Implementation desk
                      direct_exposure       line to a list of excluded
                                            activities held directly
                      vehicles              line to the vehicle actually used,
                                            where it is not config.VEHICLE

    This function determines nothing about the allocation. It applies the
    Statement and returns a verdict (IPS 2.1).
    """
    context = dict(context or {})
    as_of_d = _to_date(as_of)
    weights = {k: v for k, v in dict(weights).items()}

    results: list[CheckResult] = []
    results += _check_structural(weights)

    structurally_sound = all(
        c.passed for c in results if c.name in ("structural_keys", "structural_finite")
    )
    if not structurally_sound:
        for nm, ref in (("liquidity_floor", "IPS 3.4"), ("liquidity_distribution", "IPS 3.4"),
                        ("leverage_gross", "IPS 3.5"), ("leverage_short", "IPS 3.5"),
                        ("board_exclusions", "IPS 3.5"), ("drawdown_realised", "IPS 3.3"),
                        ("drawdown_ex_ante", "IPS 3.3"), ("drawdown_stress", "IPS 3.3"),
                        ("tracking_error", "IPS 4.2"), ("line_range", "IPS 4.1"),
                        ("sleeve_range", "IPS 4.1"), ("corridor_width", "IPS 4.5"),
                        ("min_trade", "IPS 4.2"), ("investable_date", "IPS 4.1")):
            results.append(_mk(nm, ref, NOT_ASSESSED,
                               message=("The weight vector is malformed, so no constraint "
                                        "downstream of it can be tested. Nothing here is "
                                        "a pass.")))
        return ComplianceResult(results=results, weights=weights, as_of=as_of_d,
                                label=str(context.get("label", "")))

    w = _vec(weights)

    results += _check_liquidity(weights, context)
    results += _check_leverage(weights)
    results.append(_check_exclusions(weights, context))
    results.append(_check_drawdown_realised(nav_path))
    results.append(_check_drawdown_ex_ante(w, cov))
    results.append(_check_drawdown_stress(weights, as_of_d))
    results.append(_check_tracking_error(w, cov))
    results.append(_check_line_ranges(weights))
    results.append(_check_sleeve_ranges(weights))
    results += _check_min_trade(weights, prior_weights)
    results.append(_check_investable(weights, as_of_d))

    order = {n: i for i, n in enumerate([
        "structural_keys", "structural_finite", "structural_sum",
        "liquidity_floor", "liquidity_distribution",
        "leverage_gross", "leverage_short", "board_exclusions",
        "drawdown_realised", "drawdown_ex_ante", "drawdown_stress",
        "tracking_error", "line_range", "sleeve_range",
        "min_trade", "corridor_width", "investable_date",
    ])}
    results.sort(key=lambda c: order.get(c.name, 99))

    return ComplianceResult(results=results, weights=weights, as_of=as_of_d,
                            label=str(context.get("label", "")))


if __name__ == "__main__":
    print(check(config.POLICY, context={"label": "Policy portfolio, no covariance supplied"}))
