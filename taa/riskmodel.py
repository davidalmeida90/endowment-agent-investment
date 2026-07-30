"""
taa.riskmodel — covariance estimation and ex-ante tracking error.

THE CONDITIONING PROBLEM, STATED BEFORE IT IS SOLVED
------------------------------------------------------------------------------
Nine lines is 45 free parameters in a covariance matrix (9 variances and 36
covariances). Sixty monthly observations is 60 numbers per line. The ratio of
observations to parameters is 60 to 45, which is not a large-sample problem
wearing a disguise; it is a small-sample problem. The sample covariance matrix
is still invertible at that ratio, and it is still a bad thing to invert: its
smallest eigenvalues are biased downward and its largest upward, so the inverse
loads on exactly the directions the sample estimated worst, and an optimiser
handed that inverse will find them.

The fix used here is Ledoit and Wolf (2004), "Honey, I shrunk the sample
covariance matrix", Journal of Portfolio Management 30(4) 110-119, with the
constant-correlation target of Ledoit and Wolf (2003), "Improved estimation of
the covariance matrix of stock returns with an application to portfolio
selection", Journal of Empirical Finance 10(5) 603-621. The shrinkage intensity
is the analytical optimum, not a parameter: delta minimises the expected squared
Frobenius distance to the true covariance and is computed from the data at each
date. It is implemented here from the published formulae rather than imported,
so that every step is on the page.

  Target F      f_ii = s_ii, f_ij = rbar * sqrt(s_ii * s_jj), rbar the average
                sample correlation. Same variances as the sample, all
                correlations set equal. It has 10 parameters against the sample
                matrix's 45, so it is badly biased and barely varies, which is
                the trade being made.
  Estimator     Sigma = delta * F + (1 - delta) * S.
  delta         max(0, min(1, (pi - rho) / gamma / n)), from LW (2003) eq. 2.

The shrinkage intensity chosen at each date and the condition number before and
after are reported, because delta is the honest measure of how little the sample
matrix was trusted.
"""

from __future__ import annotations

import datetime as _dt

import numpy as np
import pandas as pd

from . import config, pitdata, signals

# Number of monthly observations entering the covariance. One degree of freedom.
COV_WINDOW_M = 60
MIN_COV_OBS = 36


class CovarianceResult(dict):
    """dict with .matrix for convenience."""

    @property
    def matrix(self) -> np.ndarray:
        return self["cov"]


# --------------------------------------------------------------------------
# Ledoit-Wolf, constant-correlation target
# --------------------------------------------------------------------------
def ledoit_wolf_cc(X: np.ndarray, already_centred: bool = False) -> dict:
    """
    Ledoit and Wolf (2003) shrinkage to the constant-correlation target.

    X is (n observations, p assets), in the frequency of the observations.
    Returns a dict with the shrunk matrix, the intensity delta, the sample
    matrix and the target, all in that same frequency.

    The formulae, in the notation of LW (2003) section 3:

      S       maximum-likelihood sample covariance, divisor n
      rbar    mean of the off-diagonal sample correlations
      F       f_ii = s_ii,  f_ij = rbar * sqrt(s_ii s_jj)
      pi_ij   (1/n) sum_t [ xc_ti xc_tj - s_ij ]^2 ,  pi = sum_ij pi_ij
      th_ii,ij (1/n) sum_t [ xc_ti^2 - s_ii ][ xc_ti xc_tj - s_ij ]
               which reduces to  M3_ij - s_ii s_ij,  M3_ij = (1/n) sum_t xc_ti^3 xc_tj
      rho     sum_i pi_ii
               + sum_{i!=j} (rbar/2)[ sqrt(s_jj/s_ii) th_ii,ij + sqrt(s_ii/s_jj) th_jj,ij ]
      gamma   sum_ij (f_ij - s_ij)^2
      delta   max(0, min(1, ((pi - rho)/gamma)/n))

    pi is how noisy the sample matrix is, gamma is how wrong the target is, and
    rho is the part of the sample noise the target shares. delta is the ratio of
    the first net of the third to the second, per observation. Nothing in it is
    chosen.
    """
    X = np.asarray(X, dtype=float)
    n, p = X.shape
    if n < 2:
        raise ValueError("need at least two observations")

    Xc = X if already_centred else X - X.mean(axis=0)
    S = (Xc.T @ Xc) / n

    var = np.diag(S).copy()
    sd = np.sqrt(var)
    outer_sd = np.outer(sd, sd)
    off = ~np.eye(p, dtype=bool)

    with np.errstate(divide="ignore", invalid="ignore"):
        R = np.where(outer_sd > 0, S / outer_sd, 0.0)
    np.fill_diagonal(R, 1.0)
    rbar = float(R[off].mean())

    F = rbar * outer_sd
    np.fill_diagonal(F, var)

    # pi
    Y = Xc ** 2
    pi_mat = (Y.T @ Y) / n - S ** 2
    pi_hat = float(pi_mat.sum())

    # rho
    M3 = ((Xc ** 3).T @ Xc) / n                 # M3[i, j]
    theta = M3 - var[:, None] * S               # theta[i, j] = th_ii,ij
    np.fill_diagonal(theta, 0.0)
    with np.errstate(divide="ignore", invalid="ignore"):
        A = np.where(sd[:, None] > 0, np.outer(1.0 / np.where(sd > 0, sd, np.nan), sd), 0.0)
    A = np.nan_to_num(A)                        # A[i, j] = sd_j / sd_i = sqrt(s_jj/s_ii)
    rho_off = (rbar / 2.0) * float((A * theta + A.T * theta.T)[off].sum())
    rho_hat = float(np.trace(pi_mat)) + rho_off

    gamma_hat = float(((F - S) ** 2).sum())

    if gamma_hat <= 0:
        delta = 0.0
    else:
        delta = max(0.0, min(1.0, ((pi_hat - rho_hat) / gamma_hat) / n))

    shrunk = delta * F + (1.0 - delta) * S
    # Restore the unbiased scale of the sample matrix (n/(n-1)). Shrinkage is a
    # statement about structure, not about the degrees-of-freedom correction.
    scale = n / (n - 1.0)
    return {
        "shrunk": shrunk * scale,
        "delta": float(delta),
        "sample": S * scale,
        "target": F * scale,
        "rbar": rbar,
        "pi": pi_hat,
        "rho": rho_hat,
        "gamma": gamma_hat,
        "n": n,
        "p": p,
    }


# --------------------------------------------------------------------------
# Public interface
# --------------------------------------------------------------------------
def cov_as_of(date, lines=None, halflife_months=None) -> np.ndarray:
    """
    Annualised covariance matrix of the mandate lines as at `date`, in the
    order of `lines` (default config.LINES).

    Sixty monthly observations ending at the last complete month on or before
    `date`, Ledoit-Wolf shrunk to the constant-correlation target, multiplied by
    twelve. If halflife_months is given the observations are exponentially
    weighted with that halflife before the sample moments are formed, which is
    a different estimator and is reported separately rather than substituted in.
    """
    return cov_detail_as_of(date, lines, halflife_months)["cov"]


def cov_detail_as_of(date, lines=None, halflife_months=None) -> CovarianceResult:
    d = pitdata._to_date(date)
    lines = list(lines or config.LINES)
    lines = [ln for ln in lines if d >= config.INVESTABLE_FROM[ln]]

    r = signals.monthly_returns_as_of(d, lines)
    r = r.dropna(how="any")
    if len(r) > COV_WINDOW_M:
        r = r.iloc[-COV_WINDOW_M:]
    if len(r) < MIN_COV_OBS:
        raise ValueError(
            f"only {len(r)} monthly observations available at {d}; "
            f"{MIN_COV_OBS} required"
        )
    X = r[lines].to_numpy(dtype=float)

    if halflife_months:
        # Exponential weights, then rows rescaled so that an unweighted second
        # moment of the rescaled rows reproduces the weighted second moment of
        # the originals. The rows are already centred on the weighted mean, so
        # the estimator is told not to centre them again.
        lam = 0.5 ** (1.0 / float(halflife_months))
        n = len(X)
        w = lam ** np.arange(n - 1, -1, -1)
        w = w / w.sum()
        Xc = X - (w[:, None] * X).sum(axis=0)
        Xw = Xc * np.sqrt(w * n)[:, None]
        lw = ledoit_wolf_cc(Xw, already_centred=True)
        used_n = int(round(1.0 / (w ** 2).sum()))   # effective sample size
    else:
        lw = ledoit_wolf_cc(X)
        used_n = len(X)

    shrunk, delta, S, F = lw["shrunk"], lw["delta"], lw["sample"], lw["target"]

    ann = 12.0
    cov = shrunk * ann
    sample = S * ann
    target = F * ann

    sd = np.sqrt(np.diag(cov))
    corr = cov / np.outer(sd, sd)
    sd_s = np.sqrt(np.diag(sample))
    corr_sample = sample / np.outer(sd_s, sd_s)

    return CovarianceResult({
        "cov": cov,
        "sample_cov": sample,
        "target_cov": target,
        "corr": corr,
        "vol": sd,
        "delta": delta,
        "lines": lines,
        "n_obs": int(len(X)),
        "effective_n": int(used_n),
        "halflife_months": halflife_months,
        "as_of": d.isoformat(),
        "first_obs": str(r.index.min().date()),
        "last_obs": str(r.index.max().date()),
        "corr_sample": corr_sample,
        # Condition numbers on the covariance and, separately, on the
        # correlation. The covariance figure is dominated by the cash line,
        # whose annualised variance is three orders of magnitude below the
        # equity lines; that is a scale fact, not an estimation problem. The
        # correlation condition number is the one that measures conditioning,
        # and it is the one shrinkage is supposed to move.
        "cond_sample": float(np.linalg.cond(sample)),
        "cond_shrunk": float(np.linalg.cond(cov)),
        "cond_corr_sample": float(np.linalg.cond(corr_sample)),
        "cond_corr_shrunk": float(np.linalg.cond(corr)),
        "eig_min_sample": float(np.linalg.eigvalsh(sample).min()),
        "eig_min_shrunk": float(np.linalg.eigvalsh(cov).min()),
        "rbar": lw["rbar"],
        "window_months": COV_WINDOW_M,
    })


def ex_ante_te(weights: dict, cov, benchmark=None, lines=None) -> float:
    """
    Annualised ex-ante tracking error in basis points.

    `cov` is an annualised covariance matrix ordered by `lines` (default
    config.LINES); `weights` and `benchmark` are dicts keyed by line, the
    benchmark defaulting to the policy portfolio. Lines absent from a dict are
    taken as zero.
    """
    lines = list(lines or config.LINES)
    cov = np.asarray(cov, dtype=float)
    if cov.shape[0] != len(lines):
        # allow a covariance built on a subset, matched by name
        raise ValueError(
            f"covariance is {cov.shape[0]}x{cov.shape[0]} but {len(lines)} lines were given; "
            f"pass lines= matching the matrix"
        )
    b = dict(benchmark or config.POLICY)
    a = np.array([float(weights.get(ln, 0.0)) - float(b.get(ln, 0.0)) for ln in lines])
    v = float(a @ cov @ a)
    v = max(v, 0.0)
    return float(np.sqrt(v) * 10_000.0)


def total_vol(weights: dict, cov, lines=None) -> float:
    """Annualised total volatility of a weight vector, in basis points."""
    lines = list(lines or config.LINES)
    w = np.array([float(weights.get(ln, 0.0)) for ln in lines])
    return float(np.sqrt(max(float(w @ np.asarray(cov) @ w), 0.0)) * 10_000.0)


def shrinkage_path(dates=None, lines=None) -> pd.DataFrame:
    """delta and condition numbers at every meeting date."""
    dates = dates or config.meeting_dates()
    rows = []
    for d in dates:
        c = cov_detail_as_of(d, lines)
        rows.append({
            "date": d.isoformat(),
            "delta": round(c["delta"], 4),
            "n_obs": c["n_obs"],
            "rbar": round(c["rbar"], 4),
            "cond_cov_sample": round(c["cond_sample"], 1),
            "cond_cov_shrunk": round(c["cond_shrunk"], 1),
            "cond_corr_sample": round(c["cond_corr_sample"], 2),
            "cond_corr_shrunk": round(c["cond_corr_shrunk"], 2),
            "policy_vol_bps": round(total_vol(config.POLICY, c["cov"], c["lines"]), 1),
        })
    return pd.DataFrame(rows)


if __name__ == "__main__":
    d = config.WINDOW_END
    c = cov_detail_as_of(d)
    print(f"covariance as of {d}  n={c['n_obs']}  {c['first_obs']} .. {c['last_obs']}")
    print(f"  shrinkage delta      {c['delta']:.4f}   (mean sample corr {c['rbar']:.3f})")
    print(f"  cond(cov)  sample    {c['cond_sample']:.1f}   shrunk {c['cond_shrunk']:.1f}")
    print(f"  cond(corr) sample    {c['cond_corr_sample']:.2f}   shrunk {c['cond_corr_shrunk']:.2f}")
    print(f"  policy total vol     {total_vol(config.POLICY, c['cov'], c['lines']):.0f} bps")
    print()
    print(pd.DataFrame(c["cov"], index=c["lines"], columns=c["lines"]).round(4).to_string())
    print()
    print(shrinkage_path().to_string(index=False))
