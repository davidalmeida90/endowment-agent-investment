"""
Generates methods.ipynb.

The notebook is a deliverable; this file is the thing that writes it, so that
the notebook can be regenerated after any change to the study rather than
drifting away from the code it documents.

Run:  py -3 build_notebook.py
"""

from __future__ import annotations

import json
from pathlib import Path

import nbformat as nbf

ROOT = Path(__file__).resolve().parent
nb = nbf.v4.new_notebook()
C: list = []


def md(text: str) -> None:
    C.append(nbf.v4.new_markdown_cell(text.strip("\n")))


def code(src: str) -> None:
    C.append(nbf.v4.new_code_cell(src.strip("\n")))


def method(n: int, title: str, paper: str, url: str, claims: str) -> None:
    md(f"""
## {n}. {title}

**The paper.** {paper}
{url}

**What it claims.** {claims}
""")


def departure(text: str) -> None:
    md(f"**Where this implementation departs from the paper.** {text}")


# ==========================================================================
md("""
# Methods

### Ashcroft University Endowment · tactical asset allocation study

This notebook is the quantitative machinery of the study, worked through top to
bottom. It runs on a clean kernel against the study's own cached data and
reproduces the figures quoted in the report. If a number in the report cannot be
traced to a cell in here, one of the two is wrong.

Each method is presented in the same order: **the paper** it comes from, named
with author and year and a link you can open; **what it claims**, in two or three
sentences; **the implementation**, as a cell running against this study's data
rather than a toy example; **the output**, the number this study actually uses;
and **where this implementation departs from the paper**.

That last section is the one usually left out and the one a reader most needs.
Almost every implementation deviates from its source through a shorter window, a
different standardisation, a shrinkage the original did not use. A deviation
stated is a modelling choice. A deviation unstated is a citation doing work it
has not earned, and a reader who knows the paper will find it.

**Nothing in this notebook reads data directly.** Every historical read goes
through `taa.pitdata`, which takes an as-of date and refuses to return anything
published after it. That is the same path every desk used and the same path the
look-ahead suite tests.
""")

code("""
import warnings, json, math
warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
import sys; sys.path.insert(0, ".")

from taa import config, pitdata, signals, riskmodel, optimiser, evidence, costs, perf, compliance

W = config.window()
print("Study window (a parameter, defined once in taa/config.py):")
for k, v in W.items():
    print(f"  {k:26s} {v}")
print()
print(f"  meetings   {config.meeting_dates()[0]} .. {config.meeting_dates()[-1]}")
print(f"  lines      {', '.join(config.LINES)}")
print(f"  required return {config.REQUIRED_RETURN:.2%}   drawdown limit {config.DRAWDOWN_LIMIT:.0%}"
      f"   TE budget {config.TE_BUDGET_BPS:.0f}bps   min trade {config.MIN_TRADE_PP:.2f}pp")
""")

md("""
### The window is a parameter

Everything below reads the window from `taa.config`. Change it in one place, or
set `TAA_WINDOW_START` and `TAA_WINDOW_END`, or write `outputs/window.json`, and
rerun. Nothing else needs editing. On sixty monthly observations that matters
more than it sounds: the study's headline active return moves from **+22bps a
year over five years** to **(6)bps a year over three**, on the same programme.
""")

# ---------------------------------------------------------------- 0
md("""
---

## 0. The point-in-time layer, before any method

Everything downstream is worthless if this is wrong, so it comes first.
`taa.pitdata` handles the two ways a look-ahead gets in. A **revision** is a
statistic restated later; it is handled by reading the ALFRED vintage current on
the as-of date. A **publication lag** is a figure released after the trade date
even though the observation is correctly dated earlier; the vintage mechanism
handles it for free, and series without vintage history carry a declared lag.
""")

code("""
obs = pd.Timestamp("2022-04-01")   # 2022 Q2

def saar(s, o):
    prev = o - pd.offsets.QuarterBegin(startingMonth=1)
    return (float(s.loc[o]) / float(s.loc[prev])) ** 4 - 1

then = pitdata.as_of("2022-07-28").macro("GDPC1")
now  = pitdata.as_of(config.REPORT_DATE).macro("GDPC1")

print(f"US real GDP, 2022 Q2, annualised quarter on quarter")
print(f"  as published 28 July 2022 : {saar(then, obs):+.2%}")
print(f"  as it reads today         : {saar(now,  obs):+.2%}")
print(f"  revision                  : {(saar(now,obs)-saar(then,obs))*100:+.2f} percentage points")
print()
print("Compared as growth rates rather than levels, because BEA rebased the")
print("chained-dollar index between these vintages, so the levels are in")
print(f"different units: {float(then.loc[obs]):,.0f} then against {float(now.loc[obs]):,.0f} now.")
""")

md("""
A desk backtesting off today's values believes the economy grew in a quarter
where every person actually trading it saw a contraction. The sign did not cross
zero until the annual benchmark revision of 26 September 2024, which is 791 days
later. Under the Macro desk's regime rule that flips the reading from
*stagflation risk* to *overheat* and reverses the tilt, seven percentage points
of gross weight apart. **The backtest looks clean the entire time.**
""")

# ---------------------------------------------------------------- 1
method(1, "Signal construction and standardisation",
       "Moskowitz, Ooi and Pedersen (2012), *Time Series Momentum*, Journal of "
       "Financial Economics 104(2). Asness, Moskowitz and Pedersen (2013), *Value "
       "and Momentum Everywhere*, Journal of Finance 68(3).",
       "https://www.sciencedirect.com/science/article/pii/S0304405X11002613 · "
       "https://onlinelibrary.wiley.com/doi/10.1111/jofi.12021",
       "Past twelve-month excess return, skipping the most recent month, predicts "
       "the next month's return in the time series of an asset's own history, "
       "across equity indices, bonds, currencies and commodities. The effect is "
       "distinct from cross-sectional momentum and survives in a diversified "
       "portfolio of futures.")

code("""
d = config.meeting_dates()[-1]     # 30 June 2026
raw = signals.signals_as_of(d)
sig_names = sorted({k for v in raw.items() if isinstance(v[1], dict) for k in v[1]}
                   - {"_meta"}) if False else None

comp = signals.composite_as_of(d)
tbl = pd.DataFrame({"composite z": pd.Series(comp)})
tbl.index = [config.LINE_LABEL[i] for i in tbl.index]
print(f"Composite signal, as of {d}\\n")
print(tbl.round(3).to_string())
print(f"\\nDegrees of freedom in the signal set: see taa/signals.py, which counts them.")
""")

departure("""
Three departures, all of which make the signal weaker rather than stronger.

**Universe.** The paper tests 58 liquid futures across four asset classes. This
study has nine long-only ETF lines, three of which are equity indices that are
close to one bet. The diversification that carries the published result is not
available here.

**Standardisation.** The paper scales positions by ex-ante volatility to a
constant target and goes long or short. This study standardises each signal
against that line's own expanding history, winsorises, and is long-only with
permitted ranges. Long-only removes roughly half the information in any signal
by construction, which is the transfer-coefficient problem quantified in
section 5.

**Valuation.** The study deliberately excludes a CAPE-based value signal from
the historical work, because Shiller's series has no vintage history and
`pitdata.static()` will only serve it with a logged anachronism. A
dividend-yield construction from the divergence of adjusted and unadjusted
closes is used instead, which is point-in-time clean and weaker.
""")

# ---------------------------------------------------------------- 2
method(2, "Out-of-sample R², and against what benchmark forecast",
       "Campbell and Thompson (2008), *Predicting Excess Stock Returns Out of "
       "Sample*, Review of Financial Studies 21(4). Welch and Goyal (2008), *A "
       "Comprehensive Look at the Empirical Performance of Equity Premium "
       "Prediction*, RFS 21(4). Clark and West (2007), Journal of Econometrics 138(1).",
       "https://academic.oup.com/rfs/article/21/4/1509/1567518 · "
       "https://academic.oup.com/rfs/article/21/4/1455/1565737",
       "Welch and Goyal show that essentially no published equity-premium "
       "predictor beats the expanding-window historical mean out of sample. "
       "Campbell and Thompson show that imposing weak economic restrictions "
       "rescues some predictability, and that a monthly R² as small as 0.5% is "
       "economically meaningful for a mean-variance investor. Clark and West give "
       "the adjusted statistic for comparing nested models, since the standard "
       "test is biased against the larger model.")

code("""
r2 = json.loads((config.OUTPUTS / "quant" / "r2oos.json").read_text(encoding="utf-8"))
h = r2["headline"]
print(h["sentence"])
print()
print(f"  cells positive        {h['cells_positive']} of {h['cells_total']}"
      f"   ({h['cells_positive']/h['cells_total']:.1%})")
print(f"  composite pooled R2   {h['composite_pooled_r2oos']:+.4%}")
print(f"  Clark-West t          {h['composite_cw_t']:+.2f}")
print()
print("The definition, implemented in taa/evidence.py:")
print("  R2_oos = 1 - sum((r_t - rhat_t)^2) / sum((r_t - rbar_t)^2)")
print("  where rbar_t is the mean of returns THROUGH t-1 ONLY.")
""")

code("""
# The benchmark forecast must be the EXPANDING mean, not the full-sample mean.
# On a series with drift the two differ materially, and using the full-sample
# mean silently hands the benchmark forecast information it did not have.
y = pd.Series(np.linspace(-0.02, 0.02, 60))
exp_mean  = evidence.expanding_mean_benchmark(y)
full_mean = pd.Series(y.mean(), index=y.index)
print(f"expanding mean at t=10 : {exp_mean.iloc[10]:+.5f}")
print(f"full-sample mean       : {full_mean.iloc[10]:+.5f}")
print(f"difference             : {exp_mean.iloc[10]-full_mean.iloc[10]:+.5f}"
      "   <- this is the look-ahead the expanding form removes")
""")

departure("""
**Sample length.** Welch and Goyal run 1927 to 2005 with a long burn-in. This
study's out-of-sample period is constrained by the sanctioned price cache, which
begins July 2009, and by ETF listing dates. That is roughly 130 usable monthly
observations per line against their 900. Every R² here carries a standard error
several times theirs.

**Restrictions not imposed.** Campbell and Thompson rescue predictability by
forcing the equity premium forecast to be non-negative and the slope coefficient
to have the theoretically expected sign. This study does **not** impose them,
and reports the unrestricted number. Imposing them would raise the reported R²
and would be a choice made after seeing the data. The report says the signals do
not work; imposing restrictions to make them work would be exactly the practice
the replication literature is about.

**Pooling.** The headline pools across lines. The paper works one series at a
time. The per-cell table is given in full so a reader can unpool it.
""")

# ---------------------------------------------------------------- 3
method(3, "The volatility model",
       "Corsi (2009), *A Simple Approximate Long-Memory Model of Realized "
       "Volatility*, Journal of Financial Econometrics 7(2). Moreira and Muir "
       "(2017), *Volatility-Managed Portfolios*, Journal of Finance 72(4). "
       "Cederburg, O'Doherty, Wang and Yan (2020), *On the performance of "
       "volatility-managed portfolios*, Journal of Financial Economics 138(1).",
       "https://academic.oup.com/jfec/article/7/2/174/856522 · "
       "https://onlinelibrary.wiley.com/doi/10.1111/jofi.12513",
       "Corsi shows realised volatility is strongly forecastable with a simple "
       "cascade of daily, weekly and monthly components. Moreira and Muir claim "
       "that scaling a portfolio by the inverse of last month's realised variance "
       "raises the Sharpe ratio substantially. Cederburg and co-authors test that "
       "claim in real time across 103 strategies and find it does not survive.")

code("""
vm = json.loads((config.OUTPUTS / "quant" / "volmgmt.json").read_text(encoding="utf-8"))
qa = vm["question_a_is_variance_forecastable"]["cells"]["us_equity"]
qb = vm["question_b_does_scaling_help_this_mandate"]

print("QUESTION A. Is variance forecastable?  (US equity, out of sample)")
print(f"  R2_oos, log-variance, EWMA   {qa['r2oos_logvar_ewma']:+.4f}")
print(f"  R2_oos, log-variance, HAR    {qa['r2oos_logvar_har']:+.4f}")
print(f"  Clark-West t, EWMA           {qa['cw_t_logvar_ewma']:+.2f}")
print(f"  rank correlation             {qa['rank_corr_ewma']:+.3f}")
print(f"  top-5 squared errors as a share of total: {qa['top5_sq_error_share_pct']:.1f}%")
print()
print("QUESTION B. Does scaling by it help THIS mandate?")
print(json.dumps({k: v for k, v in list(qb.items())[:8]}, indent=2, default=str)[:900])
""")

departure("""
**The two questions are reported separately and they have different answers.**
That separation is the point: forecastability is settled and large, and the
Sharpe-ratio gain from acting on it is contested. Papers that conflate them read
as stronger than the evidence supports.

**Leverage.** Moreira and Muir's managed portfolio scales exposure without an
upper bound, which requires leverage in calm periods. IPS 3.5 prohibits leverage
at fund level for UBTI reasons, so the scaled portfolio here is capped at 100%
gross. That cap removes most of the published effect, and the study says so
rather than reporting an uncapped figure it could not implement.

**Application.** The supporting literature tests levered, monthly-rebalanced,
long-short factor portfolios. This is long-only, unlevered, quarterly, and
nine correlated lines. The study therefore adopts volatility-responsive risk
control and books **no alpha** for it.
""")

# ---------------------------------------------------------------- 4
method(4, "Covariance estimation and shrinkage",
       "Ledoit and Wolf (2003), *Improved estimation of the covariance matrix of "
       "stock returns with an application to portfolio selection*, Journal of "
       "Empirical Finance 10(5); and Ledoit and Wolf (2004), *Honey, I Shrunk the "
       "Sample Covariance Matrix*, Journal of Portfolio Management 30(4).",
       "https://www.sciencedirect.com/science/article/pii/S0927539803000070 · "
       "https://www.econ.uzh.ch/static/wp_iew/iewwp122.pdf",
       "The sample covariance matrix is badly conditioned when the number of "
       "observations is not large relative to the number of parameters, and "
       "optimisers amplify its errors. Shrinking it toward a structured target "
       "with an analytically optimal intensity reduces estimation error and "
       "improves out-of-sample portfolio performance.")

code("""
rm = json.loads((config.OUTPUTS / "quant" / "riskmodel.json").read_text(encoding="utf-8"))
print("Ledoit-Wolf constant-correlation shrinkage, as used by this study")
for k in ("shrinkage_intensity", "delta", "condition_number_before", "condition_number_after"):
    for kk, vv in rm.items():
        if k in str(kk).lower():
            print(f"  {kk:34s} {vv if not isinstance(vv, list) else '(path, see json)'}")
            break

d = config.meeting_dates()[-1]
det = riskmodel.cov_detail_as_of(d)
cov = riskmodel.cov_as_of(d)
print(f"\\n  observations 60, parameters {9*10//2} -> the ratio that motivates shrinkage")
print(f"  ex-ante TE of the policy portfolio against itself: "
      f"{riskmodel.ex_ante_te(dict(config.POLICY), cov):.2f}bps  (must be 0)")
print(f"  annualised vol of the policy portfolio: "
      f"{riskmodel.total_vol(dict(config.POLICY), cov):.2%}")
""")

departure("""
**Target.** Ledoit and Wolf (2003) shrink toward a single-index (market model)
target; Ledoit and Wolf (2004) toward a scaled identity. This study shrinks
toward a **constant-correlation** target, which is the variant in Ledoit and
Wolf's 2003 companion work and is better suited to nine asset classes than a
market model built from one of them.

**Estimation window.** The papers use long panels of individual stocks. This
study uses monthly returns over an expanding window from the start of the price
cache, so the earliest meetings estimate on materially less data than the
latest. The shrinkage intensity moves from 0.33 early to 0.16 now, which is the
estimator correctly doing more work when there is less data.

**Frequency.** Monthly rather than daily, to match the decision frequency. Daily
data would give a better-conditioned matrix and a worse match to the horizon
being optimised over.
""")

# ---------------------------------------------------------------- 5
method(5, "The fundamental law, applied to this mandate",
       "Grinold (1989), *The Fundamental Law of Active Management*, Journal of "
       "Portfolio Management 15(3). Clarke, de Silva and Thorley (2002), "
       "*Portfolio Constraints and the Fundamental Law of Active Management*, "
       "Financial Analysts Journal 58(5).",
       "https://www.pm-research.com/content/iijpormgmt/15/3/30 · "
       "https://www.tandfonline.com/doi/abs/10.2469/faj.v58.n5.2468",
       "Grinold: the information ratio a manager can achieve is approximately the "
       "information coefficient times the square root of breadth, where breadth "
       "is the number of independent bets a year. Clarke, de Silva and Thorley "
       "add the transfer coefficient, the correlation between the ideal active "
       "position and the constrained one, which multiplies the whole thing and "
       "is typically well below one for long-only portfolios.")

code("""
sysj = json.loads((config.OUTPUTS / "systematic_evidence.json").read_text(encoding="utf-8"))
fl = sysj["fundamental_law"]
ic, bn, be, tc = fl["ic"], fl["nominal_breadth"], fl["effective_breadth"], fl["tc"]
ir = ic * math.sqrt(be) * tc
alpha = ir * fl["te_budget_bps"]

print("IR  =  IC  x  sqrt(effective breadth)  x  TC")
print(f"    = {ic}  x  sqrt({be})  x  {tc}")
print(f"    = {ir:.4f}          (desk reported {fl['ir']})")
print()
print(f"Expected alpha = IR x TE budget = {ir:.4f} x {fl['te_budget_bps']:.0f}bps"
      f" = {alpha:.1f}bps a year   (desk reported {fl['expected_alpha_bps']}bps)")
print(f"Expected cost                                        = {fl['cost_bps']}bps a year")
print(f"NET                                                  = {alpha - fl['cost_bps']:+.1f}bps a year")
print()
print(f"Nominal breadth {bn} collapses to effective breadth {be}, which is "
      f"{be/bn:.1%} of nominal.")
print(f"Clears its costs: {fl['clears_costs']}")
print()
print("On a USD 850m fund, " + f"{(alpha - fl['cost_bps'])/10000*config.FUND_NAV_USD:,.0f} USD a year, before staff.")
""")

departure("""
**Breadth is the whole argument and it is a modelling choice.** Grinold's BR is
"the number of independent bets per year". Nine lines times four meetings is 36
only if the nine lines are independent and consecutive quarters are independent.
Neither holds: three equity lines are close to one bet, credit carries equity
beta, and the signals are persistent quarter to quarter. This study collapses
cross-sectionally at an average correlation of 0.45 and through time at a signal
autocorrelation of 0.60, reaching an effective breadth of 2.0.

**That haircut is contested and the study says so.** Sneddon (2020) argues that
correlation across bets *raises* the achievable information ratio, which would
reverse the sign. The recommendation does not rest on the haircut: at full
nominal breadth of 36 the expected alpha is roughly 18bps against 6.4bps of
cost, an information ratio near 0.09, which is still not fundable.

**IC is assumed, not measured.** 0.03 is taken from the practitioner range
Grinold and Kahn describe. The study's own out-of-sample evidence puts the
realised IC on the wrong side of zero, so 0.03 is generous to the programme.
""")

# ---------------------------------------------------------------- 6
method(6, "The optimiser and its constraints",
       "Markowitz (1952), *Portfolio Selection*, Journal of Finance 7(1), as "
       "constrained by IPS 4.1 and 4.2 rather than by the paper.",
       "https://www.jstor.org/stable/2975974",
       "Mean-variance optimisation selects the portfolio maximising expected "
       "return for a given variance. In practice it is an error-maximiser: small "
       "changes in expected returns produce large changes in weights, which is "
       "why the constraint set below does more work than the objective.")

code("""
d = config.meeting_dates()[-1]
cov = riskmodel.cov_as_of(d)
sc = signals.composite_as_of(d)
w = optimiser.allocate(d, cov=cov, scores=sc)

rows = []
for k in config.LINES:
    lo, hi = config.RANGE[k]
    a = w[k] - config.POLICY[k]
    at = "at LOWER bound" if abs(w[k]-lo) < 1e-6 else ("at UPPER bound" if abs(w[k]-hi) < 1e-6 else "")
    rows.append([config.LINE_LABEL[k], config.POLICY[k]*100, w[k]*100, a*10000, f"{lo*100:.0f}-{hi*100:.0f}", at])
df = pd.DataFrame(rows, columns=["line","policy %","model %","active bps","range","binding"])
print(df.to_string(index=False, float_format=lambda v: f"{v:,.2f}"))
print()
print(f"ex-ante tracking error {riskmodel.ex_ante_te(w, cov):.1f}bps against a "
      f"{config.TE_BUDGET_BPS:.0f}bps budget")
print()
print("The constraint that binds is the LINE RANGE, not the tracking-error budget.")
print("The model uses less than half the budget because it runs into range bounds first.")
""")

departure("""
**The objective is not Markowitz's.** Expected returns are not the capital
market assumptions; they are standardised signal scores mapped to active
positions. Using the CMAs as the optimiser's expected returns would produce a
portfolio driven by the ten-year forecast rather than by a tactical view, which
is a different exercise.

**Constraints dominate.** Long-only, sum to one, per-line ranges, sleeve ranges,
no leverage, and a 50bps minimum trade. Four line bounds bind simultaneously at
the current date and the US investment grade floor binds at **every one of the
twenty meetings**. This is the transfer-coefficient problem from section 5
appearing in the actual portfolio: the signal is rarely what sets position size.

**No transaction-cost term in the objective.** Costs are applied after
optimisation through the minimum-trade filter rather than inside it. A
cost-aware objective would be better and would require a quadratic program the
study does not build.
""")

# ---------------------------------------------------------------- 7
method(7, "Rebalancing and the no-trade region",
       "Masters (2003), *Rebalancing*, Journal of Portfolio Management 29(3). "
       "Leland (1999), *Optimal Portfolio Management with Transactions Costs and "
       "Capital Gains Taxes*. Constantinides (1986), Journal of Political Economy "
       "94(4). Jaconetti, Kinniry and Zilbering (2010), Vanguard.",
       "https://www.jstor.org/stable/1831177 · "
       "https://www.vanguard.com/pdf/icrpr.pdf",
       "With proportional transaction costs the optimal policy is not to hold a "
       "target but to tolerate a no-trade region around it and trade only to its "
       "edge when breached. The width grows with transaction cost and with risk "
       "tolerance, and narrows with volatility and with the correlation of the "
       "asset to the rest of the portfolio.")

code("""
rows = []
for k in config.LINES:
    p = config.POLICY[k]*100
    c = costs.CORRIDOR_PP[k]
    rows.append([config.LINE_LABEL[k], p, costs.ONE_WAY_BPS[k], c,
                 (c/p*100) if p > 0 else float("nan"),
                 "yes" if c <= config.MIN_TRADE_PP + 1e-9 else ""])
df = pd.DataFrame(rows, columns=["line","policy %","one-way bps","corridor pp",
                                 "relative %","at the 50bps floor"])
print(df.to_string(index=False, float_format=lambda v: f"{v:,.2f}"))
print()
print("Rule:  c = clip(5 * cost^(1/3) / active_vol, floor 0.50pp, cap min(25% relative, 80% headroom))")
print("The cube root on cost is Leland (1999).")
print()
print("Direction check, which is the part most often stated backwards:")
print("  cost UP    -> corridor WIDER")
print("  volatility UP -> corridor NARROWER")
print("  correlation with the rest of the portfolio UP -> corridor WIDER")
""")

departure("""
**Destination.** Constantinides and the transaction-cost literature say to trade
to the **near edge** of the no-trade region, not back to target. Under IPS 4.2's
50bps minimum trade, trading to the edge generates a trade of approximately
zero, which cannot be executed. This study trades to target and records the
departure and its cause rather than citing the theory and quietly doing
something else.

**The floor is binding, not chosen.** The risk-optimal corridor is 0.37pp for
commodities and 0.53pp for listed real estate. Both are at or below the 50bps
minimum trade, so both are held at the floor. IPS 4.5 anticipated exactly this
interaction and the study reports which lines it bites on.
""")

# ---------------------------------------------------------------- 8
method(8, "Sharpe ratio standard errors, and why sixty observations is thin",
       "Lo (2002), *The Statistics of Sharpe Ratios*, Financial Analysts Journal 58(4).",
       "https://www.tandfonline.com/doi/abs/10.2469/faj.v58.n4.2453",
       "The Sharpe ratio is an estimate with a sampling distribution. For iid "
       "returns its asymptotic standard error is sqrt((1 + SR^2/2)/n) in the same "
       "units as SR. Serial correlation inflates it further. At small n the "
       "interval is wide enough to contain most answers.")

code("""
rec = json.loads((config.OUTPUTS / "decision_record.json").read_text(encoding="utf-8"))
five = rec["summary"]
n = five["months"]
for lbl, sr in (("fund", five["portfolio"]["sharpe"]), ("benchmark", five["benchmark"]["sharpe"])):
    se = perf.sharpe_stderr(sr, n)
    print(f"{lbl:10s} Sharpe {sr:5.3f}   SE {se:5.3f}   95% interval "
          f"[{sr-1.96*se:+.2f}, {sr+1.96*se:+.2f}]")
print()
ir = five["active"]["information_ratio"]
print(f"information ratio {ir:.3f} on {n} monthly observations")
print(f"  approximate SE of an IR over {n/12:.0f} years = 1/sqrt(years) = {1/math.sqrt(n/12):.2f}")
print(f"  so the interval comfortably contains zero, and comfortably contains twice the result.")
""")

departure("""
**iid is assumed and is false.** Lo's formula above is the iid case. Monthly
asset-class returns are serially correlated and Lo gives a corrected estimator
using a Newey-West style adjustment, which this study does **not** implement.
The correction almost always *widens* the interval, so the figures reported here
are the narrowest defensible ones and the true uncertainty is greater.

**Genuinely independent observations.** Sixty monthly observations is not sixty
independent draws. The window contains one tightening cycle and one recovery, so
the effective number of independent regime observations is closer to two. Every
statistic in this study should be read with that in mind, and the report says so
on page one rather than in a footnote.
""")

# ---------------------------------------------------------------- 9
method(9, "The compliance test and the rebalancing simulation",
       "IPS Sections 2.1, 3.3, 3.4, 3.5, 3.6, 4.1, 4.2 and 4.5. The governing "
       "document rather than a paper.",
       "IPS.pdf in brief/",
       "The risk function holds no allocation authority. It applies the "
       "constraints in the Statement and returns pass or fail. An allocation that "
       "fails does not proceed to the Committee, and the remedy is a different "
       "allocation or an amendment to the Statement, never an adjustment to the "
       "test.")

code("""
cov = riskmodel.cov_as_of(config.meeting_dates()[-1])
res = compliance.check(dict(config.POLICY), cov=cov, as_of="2026-06-30",
                       prior_weights=dict(config.POLICY))
print("CONTROL: the Board's own policy portfolio through the compliance test")
print(f"  verdict {res.status}")
print(f"  gating failures: {[c.name for c in res.failed()] or 'none'}")
print()

# and the case IPS 4.1 names by name
bad = dict(config.POLICY); bad["us_ig"] = 0.025; bad["cash"] = 0.055
r2_ = compliance.check(bad, cov=cov, as_of="2026-06-30", prior_weights=dict(config.POLICY))
te = [c for c in r2_.results if c.name == "tracking_error"][0]
lr = [c for c in r2_.results if c.name == "line_range"][0]
print("THE CASE IPS 4.1 NAMES: inside the TE budget, outside a permitted range")
print(f"  tracking error  {te.status:6s}  {te.observed:.1f}bps of {config.TE_BUDGET_BPS:.0f}")
print(f"  line range      {lr.status:6s}")
print(f"  OVERALL         {r2_.status}")
print()
print("IPS 4.1: the range binds independently of the tracking-error budget.")
print("A position inside the budget and outside its range is a breach.")
""")

code("""
sc = rec["scorecard"]
print("THE FIVE-YEAR SIMULATION, as emitted by taa/simulate.py\\n")
print(f"  decisions                {sc['decisions']}")
print(f"  helped / hurt / neither  {sc['helped']} / {sc['hurt']} / {sc['too_small_to_tell']}")
print(f"  net active               {sc['net_active_bps_per_year']:+.1f}bps a year")
print(f"  turnover cost            {sc['turnover_cost_bps_per_year']:.1f}bps a year")
print(f"  allocations failing      {sc['quarters_failing_compliance']} of {sc['decisions']}")
print(f"  quarters fund in breach  {sc['quarters_fund_in_breach']} of {sc['decisions']}")
print(f"  binding constraints      {sc['binding_constraint_frequency']}")
print()
print("  Fund      {:.2%} a year, sigma {:.2%}, max drawdown {:.2%}".format(
    five['portfolio']['return'], five['portfolio']['stdev'], five['portfolio']['max_drawdown']))
print("  Benchmark {:.2%} a year, sigma {:.2%}, max drawdown {:.2%}".format(
    five['benchmark']['return'], five['benchmark']['stdev'], five['benchmark']['max_drawdown']))
print()
print("  The BENCHMARK, which is the Board's own policy portfolio held passively,")
print("  breached the (20.00)% drawdown limit. That is the finding of the study.")
""")

departure("""
**Every historical decision is mechanical.** A pre-committed rule reads the
point-in-time inputs and produces an allocation, unchanged across all twenty
meetings. No deliberation is invented. A hand-reconciled twenty-meeting history
written today would be hindsight in its purest form.

**Two kinds of failure are separated.** An allocation defect is remedied by
choosing different weights. A breach of the fund's own drawdown limit cannot be,
because it has already happened, and IPS 3.3 answers it by reducing the
distribution while IPS 2.3 escalates it. Treating the second as a rejected
allocation would report twenty rejections for one event in October 2022.
""")

# ----------------------------------------------------------------
md("""
---

## 10. Reproducing the report's headline figures

Every number below appears in the report. If any of them disagrees with the
report, the report is wrong.
""")

code("""
cme = json.loads((config.OUTPUTS / "cme.json").read_text(encoding="utf-8"))
s = pd.Series(rec["monthly"]["strategy"], index=pd.to_datetime(rec["monthly"]["dates"]))
b = pd.Series(rec["monthly"]["benchmark"], index=pd.to_datetime(rec["monthly"]["dates"]))
ttm = perf.pair_summary(s.iloc[-12:], b.iloc[-12:], "FY2026")

checks = [
    ("policy portfolio priced to earn", f"{cme['policy_expected_return']['adopted']:.2%}"),
    ("gap to the 8.10% required return", f"{cme['gap_bps']:.0f}bps"),
    ("most optimistic line-wise assembly", f"{cme['policy_expected_return']['high']:.2%}"),
    ("FY2026 fund return", f"{ttm['portfolio']['return']:.2%}"),
    ("FY2026 benchmark return", f"{ttm['benchmark']['return']:.2%}"),
    ("FY2026 active return", f"{ttm['active']['return']*10000:.0f}bps"),
    ("five-year fund return", f"{five['portfolio']['return']:.2%}"),
    ("five-year benchmark return", f"{five['benchmark']['return']:.2%}"),
    ("five-year realised tracking error", f"{five['active']['tracking_error']*10000:.0f}bps"),
    ("five-year information ratio", f"{five['active']['information_ratio']:.2f}"),
    ("fund worst drawdown", f"{five['portfolio']['max_drawdown']:.2%}"),
    ("BENCHMARK worst drawdown", f"{five['benchmark']['max_drawdown']:.2%}"),
    ("board drawdown limit", f"{config.DRAWDOWN_LIMIT:.2%}"),
    ("signal cells positive out of sample", f"{r2['headline']['cells_positive']} of {r2['headline']['cells_total']}"),
    ("composite pooled R2_oos", f"{r2['headline']['composite_pooled_r2oos']:+.2%}"),
    ("expected alpha, fundamental law", f"{fl['expected_alpha_bps']}bps"),
    ("expected turnover cost", f"{fl['cost_bps']}bps"),
]
for k, v in checks:
    print(f"  {k:40s} {v:>12s}")
""")

md("""
---

## Reproducing this notebook

```
py -3 -m taa.datapull        # once, populates data/raw/ from public sources, no key
py -3 -m taa.simulate        # the five-year record
py -3 -m taa.report_main     # the report and the decision record
py -3 -m taa.dashboard       # the dashboard
py -3 tests/test_lookahead.py
py -3 tests/mutation_test.py
py -3 tests/check_hindsight.py
py -3 tests/check_units.py
py -3 tests/check_mandate.py
py -3 tests/test_compliance.py
```

Everything runs offline against the cached data after the first pull. No API key
is used anywhere in this study and no paywalled source was consulted.
""")

nb["cells"] = C
nb.metadata["kernelspec"] = {"display_name": "Python 3", "language": "python", "name": "python3"}
nb.metadata["language_info"] = {"name": "python", "version": "3.14"}
out = ROOT / "methods.ipynb"
nbf.write(nb, str(out))
print(f"wrote {out}  ({len(C)} cells)")
