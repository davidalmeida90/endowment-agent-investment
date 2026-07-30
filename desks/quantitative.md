# Quantitative desk

**Ashcroft University Endowment, tactical asset allocation study**
As at 30 June 2026. Prepared 29 July 2026. Study window 1 July 2021 to 30 June 2026,
sixty monthly observations, twenty quarterly Investment Committee meetings.

---

## 1. The finding, first

**The signals this desk built do not beat the historical average out of sample. The
implication is policy weights.**

Across five signals and eight risky lines, nine of forty signal-line cells have a
positive out-of-sample R² against an expanding-window historical mean. The composite
that feeds the optimiser scores (1.61) per cent pooled over the longest sample the
point-in-time data supports, with a Clark and West t-statistic of (0.77). It is negative
on six of the eight lines. Restricted to the study window it scores (1.99) per cent on
seven of eight lines negative. Neither number is far from zero and neither is on the
side of zero that would justify spending the tracking-error budget.

Two subsidiary findings, both of which cut against a prior this desk held going in.

**Volatility is forecastable, and scaling by the forecast did not pay.** A
six-month-halflife exponentially weighted forecast of realised variance has a rank
correlation with what subsequently happened of between 0.27 and 0.68 across the nine
lines, which is real information. Scaling the policy portfolio by that forecast,
long-only and quarterly as the mandate requires, moved the annualised Sharpe ratio from
0.750 to 0.688 over the full post-warmup sample and from 0.463 to 0.466 over the study
window. Neither movement is meaningful against a standard error of roughly 0.25 and 0.46
respectively.

**A page-one caveat on every Sharpe ratio in this paper.** At sixty monthly
observations, the Lo (2002) standard error on a Sharpe ratio of 0.50 is 0.13 monthly and
0.46 annualised. The study window's own policy Sharpe of 0.463 carries a standard error
of 0.461. An interval that contains zero and also contains one is not a measurement of
skill. Every comparison of two Sharpe ratios made on sixty observations in this paper is
reported with that standard error attached, and none of them is large enough to survive
it.

---

## 2. Scope and method

This desk fits estimators to time series. It forms no view about the economy, the policy
cycle, the election or what is priced, and nothing in this paper should be read as one.
A number entered the allocation if and only if it could be computed from a series that
`taa/pitdata.py` would serve at the as-of date. Where the estimator and a story
disagree, this paper reports the estimator.

Every historical read runs through `pitdata.as_of(d)`. No module written by this desk
imports the raw store, the network, or names the cache by path, which
`tests/test_lookahead.py` verifies statically across the whole package.

### Deliverables

| File | Contents |
|---|---|
| `taa/signals.py` | five signals, point-in-time, computable at any as-of date |
| `taa/riskmodel.py` | Ledoit-Wolf shrunk covariance, ex-ante tracking error |
| `taa/optimiser.py` | the constrained allocation and the minimum trade filter |
| `taa/evidence.py` | R²_oos, Clark-West, Lo standard errors, volatility studies |
| `taa/run_quant.py` | writes every file in `outputs/quant/` |
| `tests/check_quant.py` | the check, with `--demo-fail` |

### Degrees of freedom, counted

Seventeen numeric parameters. Ten in the signal construction (`signals.PARAMS`), four in
the evaluation (`evidence.EVAL_PARAMS`), two in the covariance window (`COV_WINDOW_M`,
`MIN_COV_OBS`), one numerical guard (`DEGENERATE_SD`). Every one was set at the value
used in the cited paper or at the obvious round number, before any out-of-sample result
was computed. None was searched over.

Five structural choices sit alongside them and are larger degrees of freedom than any of
the numbers: the choice of five signals rather than twenty, equal weighting of the
signals in the composite, standardisation against each line's own history rather than
cross-sectionally, the constant-correlation shrinkage target, and the risk-metric
projection in the optimiser. Each is argued below rather than assumed.

Two parameters were added after seeing a result, and both are disclosed at the point
they appear: the degeneracy guard in section 5 and the forecast truncation in the same
section. Both were responses to an arithmetic failure rather than to a disappointing
number, and the untruncated results are reported beside the truncated ones so the reader
can see what changed.

---

## 3. The signal set

Five signals, each with a published reference, each defined identically on all nine
lines, fixed before any out-of-sample number was computed. Nothing was added or dropped
afterwards. That discipline is the whole point: the replication literature documents
what happens when a set is chosen on the evidence it is later tested against.

| Signal | Definition | Reference | Prior sign |
|---|---|---|---|
| Momentum | cumulative total return over months t−12 to t−1, most recent month skipped | Moskowitz, Ooi and Pedersen (2012), JFE 104(2) 228-250 | + |
| Trend | month-end price over the mean of the last ten month-end prices, less one | Faber (2007), JWM 9(4) 69-79 | + |
| Carry | the compensation the line pays, in the units natural to it (see below) | Koijen, Moskowitz, Pedersen and Vrugt (2018), JFE 127(2) 197-225 | + |
| Reversal | negative of the cumulative total return over months t−60 to t−13 | De Bondt and Thaler (1985), JF 40(3); Asness, Moskowitz and Pedersen (2013), JF 68(3) | + |
| Volatility | exponentially weighted realised volatility of monthly returns, six-month halflife | Moreira and Muir (2017), JF 72(4) 1611-1644 | (−) |

### Carry, measured per asset class

| Line | Source |
|---|---|
| US Treasury duration | DFII10, ten-year TIPS real yield |
| US investment grade | AAA10Y, Moody's Aaa less the ten-year Treasury |
| US high yield | BAA10Y, Moody's Baa less the ten-year Treasury |
| Cash | DGS3MO, three-month bill |
| Equity, commodities, listed real estate | trailing twelve-month distribution yield of the vehicle |

The intended credit series were the ICE BofA option-adjusted spreads, BAMLC0A0CM and
BAMLH0A0HYM2. The free FRED endpoint serves a rolling three-year window of them. In this
cache they begin 31 July 2023, which covers twelve of the twenty meetings and none of
the first eight, so a signal built on them would be absent for the period the Committee
most needs to reconstruct. They are excluded from all historical work and the gap is
recorded in `outputs/quant/coverage.json` rather than filled.

The substitutes are spreads over the curve rather than option-adjusted spreads, so their
level is not the level of the spread the line earns. Baa over Treasuries is a fraction of
a high-yield option-adjusted spread. That does not matter here, because each signal is
standardised against its own expanding history and only its time variation enters. It
would matter if the level were used directly, and it is not.

With those substitutes, every one of the five signals has a defined z-score on every one
of the nine lines at all twenty meeting dates. No meeting lacks an input.

### The distribution yield is point-in-time clean, and here is why

The adjusted close is restated retroactively whenever a distribution is paid: a dividend
paid in 2026 rescales every adjusted close before it by the same constant factor. A ratio
of two past adjusted closes is therefore invariant to every distribution paid after the
later of the two dates, so the total return between two past month ends computed from
them is exactly the return realised over that interval. The unadjusted close is
split-adjusted only, so the price return over the same interval is likewise invariant.
Their difference is the distribution actually paid inside the interval, which was public
when it was paid. No step looks at anything dated after the later month end.

### Why Shiller's CAPE appears nowhere in the historical work

CAPE is the obvious value proxy and it is excluded. It has no vintage history: the file
distributed today carries today's revised earnings for every past date, and `pitdata`
will serve it only through `.static()` with a logged anachronism reason. A predictor
whose historical values were not available on the dates it is tested against cannot
produce an honest out-of-sample statistic; it produces a number that flatters whoever
computed it. The long-horizon reversal signal is the substitute, built from prices alone,
which are not revised.

### Standardisation, and why against own history

Each raw signal is standardised against its own line's expanding history, using
observations through t inclusive and nothing after, with a minimum of 36 observations
before a z-score is produced and winsorisation at ±2.5.

The lines are not commensurable in raw units. A distribution yield of 5.9 per cent on
high yield against 1.1 per cent on US equity is a statement about coupon conventions. The
annualised volatility of cash at 0.6 per cent against emerging markets at 17.7 per cent is
a statement about what the assets are. Standardising each line against its own past asks
the only question the estimator can answer, which is whether this line is cheap,
trending or calm relative to how it usually looks. The cross-sectional step happens once,
at the composite stage, after the units are already comparable, and it is there because a
long-only fully invested mandate can express a relative statement and has nowhere to put
an absolute one.

### The signals are correlated, and here is by how much

Pooled across 972 line-months of standardised values:

| | Momentum | Trend | Carry | Reversal | Volatility |
|---|---:|---:|---:|---:|---:|
| Momentum | 1.00 | 0.74 | 0.13 | (0.07) | 0.11 |
| Trend | 0.74 | 1.00 | 0.21 | (0.10) | 0.22 |
| Carry | 0.13 | 0.21 | 1.00 | (0.28) | 0.12 |
| Reversal | (0.07) | (0.10) | (0.28) | 1.00 | (0.19) |
| Volatility | 0.11 | 0.22 | 0.12 | (0.19) | 1.00 |

Momentum and trend correlate at 0.74. They are close to the same signal measured two
ways, and the equal-weighted composite therefore gives trend-following roughly twice the
weight the other three ideas carry. That is a defect and it is stated rather than
repaired, because repairing it would mean fitting a weighting scheme on the sample the
composite is then reported against.

### Two known defects in the signal set

The reversal signal is degenerate on the cash line. A money-market total-return index is
monotone, so its five-year cumulative return is always positive and the negation of it is
always negative. What the signal measures on that line is the level of the bill rate over
the preceding five years, not a valuation. It is left in place under the uniform
definition and reported here, rather than carved out, because per-line exceptions are the
degree of freedom this whole approach is meant to avoid.

The carry signal is degenerate on commodities over part of the sample. DBC paid no
distributions for years at a stretch, so the trailing distribution yield is exactly zero
to floating-point noise between 2013 and 2019. Section 5 describes what that did to the
regression and how it was handled.

---

## 4. Point-in-time construction, and the two look-aheads found in it

Both were found by this desk's own check, and both are recorded because a check that has
only ever passed is not evidence of anything.

**A publication lag in the carry signal.** The market-quoted rates were resampled to
month ends by taking the last observation inside the month. For AAA10Y and BAA10Y, which
carry a one-day publication lag, that records against 31 March a number that was not
published until 1 April. The magnitude is small, a basis point or two, and invisible in a
single reading. The consequence is not small: it made the signal panel depend on the date
the panel was built, so the value for March 2022 differed depending on whether it was
computed in March 2022 or in June 2026. Check 3 in `tests/check_quant.py` compares those
two constructions directly and caught it. The panel now records against month end T the
last quote dated on or before T less the series' publication lag.

**A sub-threshold trade created by the minimum trade filter.** Suppressing trades below
50bps and normalising the remainder pushed a sleeve outside its range at the December 2021
meeting, and repairing that afterwards reintroduced three trades of under 0.02 percentage
points, which are precisely the trades the filter exists to remove. Check 5c caught it.
The filter now pins the suppressed lines at their prior weight as hard bounds and
re-solves, so the result is feasible by construction. Where the pins make the problem
infeasible the hard limits win, which is the pre-committed order in IPS 3.6, and the
override is recorded rather than hidden.

**The shortcut that the check licences.** `taa/evidence.py` reads the signal panels once
at the end of the sample and walks them forward, rather than rebuilding them at each of
roughly two hundred month ends. That is legitimate only because row t of each panel
depends on nothing dated after t. Check 3 asserts that property directly by recomputing
`signals_as_of(t)` at sampled dates and requiring an exact match. If it ever fails, the
out-of-sample table is not out of sample and every number in it is void.

---

## 5. Out-of-sample evidence

### Definition

Following Campbell and Thompson (2008), RFS 21(4) 1509-1531, and Welch and Goyal (2008),
RFS 21(4) 1455-1508:

    R²_oos = 1 − Σ(r_t − r̂_t)² / Σ(r_t − r̄_t)²

where r̄_t is the mean of the realised series through t−1 and nothing later, and r̂_t comes
from a one-regressor OLS refitted at every date on pairs whose target date is strictly
before t. Sixty paired observations are required before the first forecast. Strict
chronological order, no overlap, nothing tuned on the test period.

Clark and West (2007), Journal of Econometrics 138(1) 291-311, adjust for the fact that
under the null the larger model still estimates a slope and pays for it in mean squared
error. The statistic is the mean of

    f_t = (r_t − r̄_t)² − [(r_t − r̂_t)² − (r̄_t − r̂_t)²]

with a one-sided normal t-statistic. A positive Clark-West t with a negative R²_oos is
the common outcome. It means the model may contain a signal too weak to pay for the cost
of estimating it. It is not a licence to trade.

The target is the monthly total return less the cash line. Cash is reported separately.
The trap that avoids is worth stating because it would have produced a flattering
headline: the cash line's monthly total return is the bill rate, which is close to
deterministic month to month, and regressing it on any persistent predictor, the bill
yield most of all, produces an R²_oos of the order of 50 per cent that measures the
persistence of the front end and nothing else. Reported as predictability it would be
false.

### Two guards, both disclosed, both added after seeing a result

The commodities carry regression produced a forecast of minus fifty thousand per cent for
one month. The cause was the DBC distribution yield being exactly zero to floating-point
noise across the training window, so the fit was regressing excess returns on rounding
error and returned a slope of minus fifty-four thousand. That is an artifact of
arithmetic and reporting it as a result would have been reporting a bug. Two responses,
applied uniformly to every signal and every line:

- **Degeneracy.** Where the training sample's predictor has a standard deviation below
  1e-8 the regression is not identified and no forecast is produced. Real signals here
  live at 1e-2 to 1e-1; the case this catches lives at 1e-17.
- **Truncation.** The forecast is capped to the range of the target observed in the
  training window, following the restriction philosophy of Campbell and Thompson, who
  truncate the equity premium forecast from below. Both the truncated and untruncated
  series are carried in `outputs/quant/r2oos.json`, cell by cell.

### The table, including every negative number

R²_oos in per cent. Negatives in parentheses. Longest sample the point-in-time data
supports, which begins between 2015 and 2019 depending on the signal's own warm-up.

| Line | Momentum | Trend | Carry | Reversal | Volatility | Composite |
|---|---:|---:|---:|---:|---:|---:|
| us_equity | (2.86) | 0.80 | (2.62) | (2.14) | 0.03 | (2.74) |
| dev_ex_us | (0.62) | (1.12) | (1.74) | (2.23) | 1.66 | 0.68 |
| em_equity | (2.71) | (6.49) | (2.12) | (1.54) | (0.46) | (1.21) |
| ust_duration | 0.13 | (0.83) | (1.06) | (0.62) | (1.15) | 1.99 |
| us_ig | (2.44) | (2.51) | 0.39 | (0.55) | (3.52) | (0.78) |
| us_hy | (1.75) | (4.74) | 2.12 | (0.30) | 1.98 | (1.61) |
| commodities | (1.63) | 0.00 | (19.02) | (11.19) | (0.96) | (2.95) |
| listed_re | (0.23) | (0.45) | (0.22) | (0.82) | 0.81 | (2.20) |
| **Pooled** | **(1.58)** | **(1.72)** | **(4.63)** | **(3.32)** | **0.03** | **(1.61)** |
| Clark-West t, pooled | (0.59) | 0.90 | (0.79) | (1.08) | 2.39 | (0.77) |
| Cells positive | 1/8 | 2/8 | 2/8 | 0/8 | 4/8 | 2/8 |

Nine of forty cells are positive. One Clark-West t-statistic in forty exceeds 2.0, which
is roughly what forty independent tests produce by chance at the five per cent level, and
these forty are not independent.

### The same table on the study window only

| Line | Momentum | Trend | Carry | Reversal | Volatility | Composite |
|---|---:|---:|---:|---:|---:|---:|
| us_equity | (4.46) | (0.76) | (3.45) | 0.01 | (3.08) | (5.68) |
| dev_ex_us | (1.16) | (0.27) | (2.08) | (1.19) | (0.54) | (0.31) |
| em_equity | (2.16) | (2.79) | 1.06 | 4.59 | (1.22) | (0.48) |
| ust_duration | 0.16 | (1.06) | (4.48) | (0.03) | (1.80) | 2.36 |
| us_ig | (3.10) | (3.11) | 0.66 | (0.25) | (4.14) | (0.27) |
| us_hy | (2.32) | (3.70) | (0.92) | 1.82 | (3.50) | (3.54) |
| commodities | (1.64) | (0.69) | (1.47) | (4.57) | (4.33) | (1.20) |
| listed_re | (0.90) | 1.47 | 0.94 | 0.62 | (4.46) | (3.32) |
| **Pooled** | **(1.96)** | **(0.80)** | **(0.81)** | **0.08** | **(2.93)** | **(1.99)** |
| Clark-West t, pooled | (1.22) | 0.62 | 0.53 | 1.19 | (0.40) | (1.31) |
| Cells positive | 1/8 | 1/8 | 3/8 | 4/8 | 0/8 | 1/8 |

**Read the two tables together, because the comparison is the most informative thing in
this paper.** The ranking reverses. Volatility is the only signal with a positive pooled
R²_oos on the full sample and it is the worst on the study window, negative on eight of
eight lines. Reversal is the worst on the full sample, negative on eight of eight, and it
is the only positive one on the study window. If either sample were carrying information
about which signal works, the two would agree. They disagree completely, which is what
sampling noise looks like when it is mistaken for a result. Anyone selecting a signal on
one of these tables would have selected the worst performer on the other.

### The robustness variant

A uniform trailing distribution yield on all nine lines, in place of the per-asset-class
carry measure, scores (4.56) per cent pooled against carry's (4.63) per cent, with three
positive cells against two. The choice of carry proxy did not change the conclusion. It
is reported in `outputs/quant/r2oos.json` under `carry_dy` and does not enter the
composite.

### Where this sits against the base rate

The replication literature is explicit about what to expect. Welch and Goyal (2008) find
that almost no equity-premium predictor beats the historical mean out of sample. Harvey,
Liu and Zhu (2016), RFS 29(1) 5-68, argue that most published cross-sectional factors
would not survive a multiple-testing correction and propose a t-statistic hurdle above
3.0. Hou, Xue and Zhang (2020), RFS 33(5) 2019-2133, replicate 452 anomalies and find 65
per cent fail at conventional significance.

**This desk's conclusion sits with that prior, not against it.** Nine of forty cells
positive, a composite that is negative on both samples, a single Clark-West t above 2.0
out of forty tests, and a signal ranking that reverses completely between the two
samples. There is no claim of membership of the surviving minority here, and no argument
is offered for one. The honest reading is that five well-documented signals, implemented
carefully and tested strictly, produced no evidence of out-of-sample forecasting power on
this opportunity set over this history.

---

## 6. Volatility, two separate questions

### (a) Is variance forecastable?

Target is annualised realised variance from daily log returns, monthly. The squared
monthly return is an unbiased but extremely noisy proxy for the latent variance
(Andersen and Bollerslev 1998, IER 39(4) 885-905), so a forecast scored against it looks
worse than it is; realised variance from daily data is the standard fix and daily prices
are available here. Benchmark is the expanding mean of realised variance through t−1.
Forecast is an exponentially weighted mean of past realised variance, halflife fixed at
six months before any result was seen, with nothing fitted. A Corsi (2009) heterogeneous
autoregression is reported alongside in `outputs/quant/volmgmt.json`.

R²_oos in per cent against the expanding mean, 132 out-of-sample months.

| Series | Variance loss | Volatility loss | Log-variance loss | Rank corr | CW t (variance) | Top five squared errors, share of total |
|---|---:|---:|---:|---:|---:|---:|
| us_equity | (2.54) | (7.06) | 4.19 | 0.34 | 1.40 | 91% |
| dev_ex_us | (2.40) | 10.58 | 30.37 | 0.34 | 1.15 | 91% |
| em_equity | (3.40) | 4.15 | 20.46 | 0.27 | 0.87 | 89% |
| ust_duration | 16.51 | 26.09 | 31.06 | 0.55 | 4.64 | 76% |
| us_ig | (2.56) | (14.10) | (14.84) | 0.68 | 1.53 | 96% |
| us_hy | (0.63) | 6.20 | 26.40 | 0.39 | 1.17 | 91% |
| commodities | 4.13 | 5.58 | 8.03 | 0.35 | 2.77 | 75% |
| listed_re | (1.46) | 4.06 | 26.32 | 0.44 | 1.37 | 94% |
| cash | 55.80 | 57.54 | 57.79 | 0.77 | 7.44 | 31% |
| Policy portfolio | (3.36) | (3.44) | 13.79 | 0.33 | 0.95 | 92% |

**The answer depends on the loss function, and that is the finding rather than an
evasion.** On squared error applied to the level of variance, which is the literal
reading of the question, the forecast beats the expanding mean on three of ten series.
On squared error applied to log variance it beats it on eight of ten. The rank
correlation between forecast and outcome is positive on every series, between 0.27 and
0.68.

The reason is in the last column. On the policy portfolio the five largest squared errors
are 92 per cent of the total, out of 132 months. March 2020 alone realised an annualised
variance of 0.45 against a forecast of 0.010 and a benchmark of 0.014, and no forecast
built on history was going to be close. A statistic decided by five observations out of
132 is reported here as being decided by five observations. Excluding March 2020 does not
rescue it; the variance-loss R²_oos falls further, to (11.65) per cent, so this is not one
outlier but a systematic inability to anticipate the largest months.

The halflife was preset at six months. The sensitivity curve is reported because the two
losses move in opposite directions with it, which is a better disclosure than one number
from one halflife.

| Halflife (months) | Variance loss | Log-variance loss |
|---|---:|---:|
| 3 | (5.88) | 20.67 |
| 6 (preset) | (3.36) | 13.79 |
| 12 | (1.96) | 10.96 |
| 24 | (1.12) | 8.64 |

**Verdict on (a).** There is real information in the volatility forecast. It ranks quiet
months against noisy ones on every line. It cannot anticipate the months that matter most
to a squared-error loss, and on that loss it does not beat a constant on this sample.

### (b) Does scaling exposure by the forecast help this mandate?

Constructed at the twenty meeting dates. The forecast is the same six-month exponentially
weighted volatility of the policy portfolio. The target is the expanding mean of realised
policy volatility through the meeting date, so it is not chosen with hindsight. The scale
is the ratio, capped at 1.0, and the residual goes to cash. The cap is the mandate: IPS
3.5 forbids leverage at the fund level for UBTI reasons, so the unlevered leg is the only
leg available. The uncapped version is computed and reported as a diagnostic, marked as
outside the mandate, because the difference between the two is most of what the
literature is arguing about.

**Full post-warmup sample, July 2010 to June 2026, 192 months, 65 rebalances**

| | Return | Volatility | Sharpe | Lo SE | Max drawdown |
|---|---:|---:|---:|---:|---:|
| Policy, unscaled | 9.50% | 11.18% | 0.750 | 0.253 | (22.5%) |
| Policy, volatility-scaled, capped (mandate) | 8.27% | 10.43% | 0.688 | 0.252 | (21.5%) |
| Policy, volatility-scaled, uncapped (outside mandate) | 8.58% | 12.05% | 0.635 | 0.252 | (21.8%) |

**Study window, October 2021 to June 2026, 57 months, 20 rebalances**

| | Return | Volatility | Sharpe | Lo SE | Max drawdown |
|---|---:|---:|---:|---:|---:|
| Policy, unscaled | 8.92% | 12.52% | 0.463 | 0.461 | (22.5%) |
| Policy, volatility-scaled, capped (mandate) | 8.68% | 11.78% | 0.466 | 0.461 | (21.5%) |
| Policy, volatility-scaled, uncapped (outside mandate) | 9.63% | 12.57% | 0.515 | 0.461 | (21.8%) |

Annual turnover of the scaling leg is 0.105 on the full sample and 0.093 on the study
window. The mean scale is 0.954 and 0.965, with a minimum of 0.546 and 0.814.

**Verdict on (b). No, on this window.** The scaled portfolio is worse over the full
sample and indistinguishable over the study window. Neither difference approaches its own
standard error. The result lands with Cederburg, O'Doherty, Wang and Yan (2020), JFE
138(1) 95-117, rather than with Moreira and Muir (2017), and the mechanism is visible in
the third row of each table: the uncapped version, which is the one the published result
requires, is also the one this mandate forbids. Removing the leverage removes the
strategy.

**A caveat that limits this verdict.** The window contains one or two volatility regimes
at most. The full sample runs from July 2010, so it contains the 2011 euro-area episode,
2015, 2018, the 2020 shock and 2022. It contains no 2008. A test of a volatility-scaling
rule on a sample without a prolonged high-volatility bear market is a weak test of a rule
whose entire claim is about prolonged high-volatility bear markets. The negative result
here should be read as "did not help on this data" and not as "does not work".

**One further measurement, reported because this desk found it and it belongs to
someone.** The policy portfolio's maximum drawdown over both samples is (22.5) per cent,
which occurred inside the study window. The board's limit in IPS 3.3 is (20) per cent and
ranks above the tracking-error budget in the hierarchy. Volatility scaling reduced it only
to (21.5) per cent, so it is not a remedy for that constraint. This desk offers the
measurement and no view on the response, which is a policy-portfolio question rather than
a tactical one.

---

## 7. Risk model

### Estimator

Ledoit and Wolf (2004), JPM 30(4) 110-119, with the constant-correlation target of
Ledoit and Wolf (2003), Journal of Empirical Finance 10(5) 603-621. Implemented from the
published formulae in `taa/riskmodel.ledoit_wolf_cc`, not imported. Sixty monthly
observations, nine lines, annualised by twelve.

The shrinkage intensity δ is not a parameter. It is the analytical minimiser of expected
squared Frobenius distance to the true covariance, computed from the data at each date:
δ = max(0, min(1, ((π − ρ)/γ)/n)), where π measures how noisy the sample matrix is, γ how
wrong the target is, and ρ the part of the sample noise the target shares.

The implementation was validated three ways before use. The vectorised π, ρ, γ and δ
match a brute-force double loop over the definitions to machine precision. In Monte Carlo
at n=60 and p=9 the estimator reduces expected squared Frobenius error against the sample
matrix by 31.8 per cent when the population truly has constant correlation, by 6.6 per
cent under a one-factor population the target cannot represent, and by 5.2 per cent under
a block population, with δ averaging 0.997, 0.663 and 0.130 respectively, which is the
behaviour the derivation predicts. The output is positive definite and reproduces the
convex combination exactly.

### What it chose

| | Value |
|---|---|
| δ at 30 June 2026 | 0.162 |
| δ across the twenty meetings | 0.162 to 0.327, mean 0.236 |
| Mean sample correlation (the target) | 0.465 |
| Condition number of the correlation, sample | 182.7 |
| Condition number of the correlation, shrunk | 46.7 |
| Same, range across the twenty meetings | 82.1 to 207.5, shrunk to 16.0 to 46.7 |
| Condition number of the covariance, sample | 4,574 |
| Condition number of the covariance, shrunk | 4,060 |

**The two condition numbers say different things and the difference matters.** The
covariance figure barely moves, from 4,574 to 4,060, because it is dominated by the cash
line, whose annualised variance of 0.000036 is three orders of magnitude below listed
real estate. That is a scale fact about a money-market fund, not an estimation problem,
and shrinkage is not meant to fix it. The correlation condition number is what measures
conditioning, and it falls by a factor of four, from 182.7 to 46.7. Quoting only the
covariance figure would have understated what the estimator did; quoting only the
correlation figure would have overstated how well-conditioned the matrix an optimiser
actually inverts is. Both are reported.

δ of 0.162 to 0.327 says the sample matrix is being given between two thirds and five
sixths of the weight. The estimator is not saying the sample is useless. It is saying
that at sixty observations against forty-five parameters, roughly a quarter of the way
toward a ten-parameter target is where expected error is lowest.

An exponentially weighted variant with a 24-month halflife gives δ of 0.232. It is
reported in `outputs/quant/riskmodel.json` and is not used in the allocation.

### Ex-ante tracking error

`ex_ante_te(weights, cov, benchmark)` returns √(aᵀΣa) × 10,000 in basis points, with a the
active vector against the policy portfolio. The policy portfolio's own annualised
volatility at 30 June 2026 is 1,213bps.

---

## 8. The allocation

### Construction

The unconstrained tilt is the closed-form maximiser of sᵀa subject to aᵀΣa equal to the
budget squared and the active weights summing to zero:

    a = k Σ⁻¹(s − λ1),    λ = 1ᵀΣ⁻¹s / 1ᵀΣ⁻¹1

with k scaling to the tracking-error budget. The constrained allocation is the feasible
portfolio with the smallest tracking error against that tilt, then scaled along its own
direction until the first mandate limit is reached.

**Why the constrained step is a projection and not a linear programme.** Maximising sᵀa
subject to the budget and the ranges was tried first. Because the objective is linear the
solution sits at a vertex, and at 30 June 2026 it drove all nine lines onto a range bound
simultaneously. That answer is determined entirely by where the ranges are and discards
the magnitudes of the scores, so it is a use of the ranges rather than a use of the
signal. The projection metric is the covariance itself, so "closest" means the portfolio
whose tracking error against the target is smallest, which is the risk-space distance a
transition manager minimises and which treats five points of commodities as the larger
departure it is against five points of Treasuries.

**A conditioning caveat on the unconstrained tilt, reported because it is large.** Σ⁻¹
loads on the directions the sample estimated least well, which is Michaud's (1989)
error-maximisation property. The same scores expressed as an inverse-volatility tilt,
which uses only the nine diagonal entries and none of the 36 off-diagonal ones, differ
from the mean-variance tilt by 236bps of tracking error, more than the entire budget. The
disagreement is a direct measurement of how much of the mean-variance answer comes from
correlation estimates rather than from the signal. Both are in
`outputs/quant/allocation.json`.

### The model allocation at 30 June 2026

| Line | Policy | Unconstrained | Constrained | Active | Composite score |
|---|---:|---:|---:|---:|---:|
| us_equity | 38.00% | 37.41% | 32.46% | (5.54%) | (0.32) |
| dev_ex_us | 20.00% | 22.47% | 21.80% | 1.80% | 0.21 |
| em_equity | 12.00% | 13.89% | 14.44% | 2.44% | 0.39 |
| ust_duration | 12.00% | 60.44% | 22.00% | 10.00% | 0.40 |
| us_ig | 8.00% | (17.54%) | 3.00% | (5.00%) | (0.07) |
| us_hy | 5.00% | (3.01%) | 0.00% | (5.00%) | (0.29) |
| commodities | 3.00% | 6.70% | 3.11% | 0.11% | (0.04) |
| listed_re | 2.00% | 0.41% | 3.19% | 1.19% | 0.09 |
| cash | 0.00% | (20.78%) | 0.00% | 0.00% | (0.38) |
| **Total** | **100%** | **100%** | **100%** | **0%** | |

Ex-ante tracking error 84bps. Total portfolio volatility 1,194bps against the policy
portfolio's 1,213bps.

### Which constraint bound

**The line ranges, not the tracking-error budget.** At 30 June 2026 four limits bind
simultaneously: the ust_duration ceiling at 22 per cent, the us_ig floor at 3 per cent,
the us_hy floor at zero, and the cash floor at zero. The allocation stops at 84bps of
ex-ante tracking error against a 200bps budget, so 58 per cent of the budget is
unreachable in the direction the signals point.

This is not a statement that the budget is unreachable in general. A search over 400
random score vectors finds allocations reaching 249bps inside the same ranges, so IPS 4.2
and IPS 4.1 are mutually consistent. The 200bps figure is simply not the operative limit
for this signal set. The same pattern holds across the record: over the twenty meetings
the model's tracking error spans 75bps to 131bps and never approaches the budget, and the
us_ig floor binds at all twenty.

The minimum trade filter suppressed three lines at this meeting, holding em_equity,
ust_duration and commodities at the weights set on 31 March 2026, with no hard-constraint
override required.

### The record, all twenty meetings

Written in full to `outputs/quant/model_path.json`, chained so that the minimum trade
filter at each meeting sees the position the fund would actually have been holding.

| Meeting | TE (bps) | Lines traded | Binding |
|---|---:|---:|---|
| 2021-09-30 | 89 | 8 | us_ig floor, us_hy ceiling, listed_re ceiling, cash ceiling |
| 2021-12-31 | 115 | 3 | dev_ex_us ceiling, us_ig floor, us_hy ceiling, listed_re ceiling |
| 2022-03-31 | 104 | 8 | ust_duration floor, us_ig floor, fixed income sleeve floor |
| 2022-06-30 | 104 | 8 | us_ig floor, cash ceiling, fixed income sleeve floor |
| 2022-09-30 | 99 | 2 | us_ig floor, cash ceiling, fixed income sleeve floor |
| 2022-12-31 | 91 | 6 | us_ig floor, cash ceiling |
| 2023-03-31 | 85 | 5 | us_ig floor, cash ceiling, fixed income sleeve floor |
| 2023-06-30 | 75 | 5 | us_ig floor, commodities floor, cash ceiling |
| 2023-09-30 | 76 | 5 | us_ig floor, commodities floor, cash ceiling |
| 2023-12-31 | 98 | 6 | us_ig floor, commodities floor, cash ceiling |
| 2024-03-31 | 78 | 6 | us_ig floor, commodities floor, fixed income sleeve floor |
| 2024-06-30 | 92 | 6 | us_ig floor, fixed income sleeve floor |
| 2024-09-30 | 126 | 5 | us_ig floor, cash floor |
| 2024-12-31 | 84 | 6 | us_ig floor, cash floor |
| 2025-03-31 | 131 | 5 | ust_duration ceiling, us_ig floor, cash floor |
| 2025-06-30 | 125 | 4 | ust_duration ceiling, us_ig floor, cash floor |
| 2025-09-30 | 110 | 6 | ust_duration ceiling, us_ig floor, us_hy floor |
| 2025-12-31 | 118 | 5 | ust_duration ceiling, us_ig floor, us_hy floor |
| 2026-03-31 | 122 | 4 | ust_duration ceiling, us_ig floor, us_hy floor |
| 2026-06-30 | 84 | 3 | ust_duration ceiling, us_ig floor, us_hy floor, cash floor |

---

## 9. Recommendation

**Hold policy weights for the coming twelve months. Do not spend the tracking-error
budget on this signal set.**

The recommendation follows from section 5 and not from caution. The size of an active
position should follow the evidence for the signal driving it, and by Grinold's
relationship the optimal active risk scales with the information coefficient. The
composite's out-of-sample information coefficient on this data has a point estimate on
the wrong side of zero and a confidence interval that comfortably contains it. An
estimator with no demonstrated forecasting power multiplied by a 200bps budget is
200bps of tracking error with no expected return attached to it, plus turnover.

The table in section 8 is the model's answer, produced at the full budget, and it is what
`outputs/quant/model_path.json` holds at every meeting so the Committee can reconstruct
what was on the table without hindsight. It is reported in full and it is not what this
desk recommends carrying.

**Confidence: low.** Defined as: this desk's own out-of-sample test does not reject the
null that the signal has no forecasting power, and the point estimate is on the wrong
side of zero.

### What would change this

Stated as falsifiers, per IPS 4.4, so that the recommendation can be wrong in a way
somebody can check.

1. **The composite's rolling out-of-sample R² turns positive and stays positive.** Rerun
   `taa.evidence.r2oos_table` at each future meeting. A pooled composite R²_oos above zero
   sustained over eight consecutive quarters, with a Clark-West t above 2.0, would move
   the recommendation off policy weights. One quarter would not.
2. **The two samples stop disagreeing.** If the full-sample and study-window signal
   rankings converge, the ranking is carrying information. While they invert, it is not.
3. **The line ranges widen or the signal set changes.** The current ranges cap this
   signal set at 84bps, so even a signal that worked could express only 42 per cent of
   the budget in this direction. A widened range would raise the stake on the evidence
   question rather than settle it.
4. **A longer history becomes admissible.** The estimation prefix in `taa/config.py` is
   twelve years, so the entire evidence base begins in July 2009 and contains no 2008.
   Extending it would test every conclusion here, particularly the volatility-scaling
   verdict in section 6(b), which is weakest precisely where the missing data is.

---

## 10. Limitations, stated plainly

1. **Sixty observations.** The study window is sixty months. The Lo standard error on a
   Sharpe ratio at that n is roughly 0.46 annualised, so the window cannot distinguish
   a good strategy from a mediocre one. The longer post-warmup sample used for the
   out-of-sample table reaches 192 months at most and still begins after the global
   financial crisis.
2. **One or two regimes.** The price history begins July 2009. It contains no 2008, no
   prolonged bear market, and one inflation episode. Any conclusion about a rule whose
   claim concerns rare states is under-tested here, and the volatility-management verdict
   is the clearest case.
3. **Momentum and trend are 0.74 correlated**, so the equal-weighted composite is roughly
   40 per cent trend-following. Left unrepaired rather than fitted.
4. **The credit carry signal is a proxy.** Moody's Baa and Aaa spreads over the Treasury
   curve stand in for option-adjusted spreads that the free endpoint does not serve far
   enough back. Only the time variation enters, so the level mismatch is immaterial, but
   the proxy is not the thing.
5. **Two defects were left in the signal set on purpose**, the reversal signal on cash
   and the carry signal on commodities, because carving out per-line exceptions after
   seeing the data is a larger methodological cost than the defects themselves.
6. **No transaction costs.** The minimum trade filter is a turnover control, not a cost
   model. The volatility-management turnover figures are reported gross.
7. **Back-adjusted prices.** Adjusted closes are restated when a distribution is paid, so
   their level on a past date is not what a screen showed that day. Every return in this
   study is computed between two dates on the same side of the as-of boundary, where the
   adjustment cancels, so no look-ahead is introduced. This is a modelling choice and is
   stated rather than left implicit.
8. **The desk has not seen the Macro desk's work** and has formed no regime view. Nothing
   in this paper should be read as agreement or disagreement with it.

---

## 11. The check

`tests/check_quant.py`. Six checks, thirteen assertions. Three of them failed on first
run and each failure was a real defect in this desk's work, described in section 4 and
section 5.

```
CHECK_QUANT — Ashcroft University Endowment, Quantitative desk
  window       2021-07-01 .. 2026-06-30
  meetings     20
  TE budget    200 bps   min trade 0.5 pp
  signal DoF   10

1 — as-of metadata
  [PASS] 1. signals_as_of reports no observation dated after the as-of date  4 dates checked

2 — the strong version: identical answer against a truncated store
  [PASS] 2a. sandbox store is genuinely truncated at the as-of date  120/219 files cut, 20,329 rows removed
  [PASS] 2b. signals_as_of(d) is identical with and without data after d  max |diff| z 1.732e-14 (us_equity.carry), raw 4.441e-16, composite 1.943e-15, tolerance 1e-12

3 — the panel shortcut taa.evidence relies on
  [PASS] 3. panel row t equals signals_as_of(t), which licences the walk  3 dates x 5 signals x 9 lines checked

4 — expanding mean and expanding OLS
  [PASS] 4a. R2_oos benchmark at T is the mean through T-1  max |benchmark - hand-computed expanding mean| = 0.00e+00
  [PASS] 4b. the benchmark is not the full-sample mean  full-sample mean 20.5; benchmark ranges 1.0 to 20.0
  [PASS] 4c. using the full-sample mean as benchmark changes the answer  R2_oos +0.1057 against the expanding mean, +0.0000 against the full-sample mean
  [PASS] 4d. expanding OLS at T is fitted on rows strictly before T  max |model forecast - hand-computed| = 1.24e-14 over 30 refits
  [PASS] 4e. the fit at the regime break has not seen the regime  beta at T=K is +5.00; it is +5 before the break and -5 after, and a full-sample fit would give about +2.20

5 — the mandate at every meeting date
  [PASS] 5a. every meeting's allocation satisfies RANGE, SLEEVE_RANGE, long-only and the sum to one  20 meetings checked
  [PASS] 5b. ex-ante tracking error is at or below the budget at every meeting  TE spans 74.7 to 131.1 bps against a 200 bps budget
  [PASS] 5c. no trade smaller than the minimum trade size survives  threshold 0.5pp, 20 rebalances

6 — Lo (2002) standard error
  [PASS] 6. Sharpe standard error is Lo (2002) sqrt((1+SR^2/2)/n)  n=60, monthly SR 0.35: SE 0.1330 monthly, 0.4607 annualised

  13 of 13 passed
```

**Check 2b is the one that matters.** It builds a copy of the data directory with every
row dated after 31 December 2023 removed, 20,329 rows across 120 files, and recomputes
`signals_as_of(2023-12-31)` against it in a separate process so that nothing is inherited
through an import or a memo. All 45 z-scores, all 45 raw values and all nine composite
scores match the run against the full store, which holds data through July 2026, to
within 1.7e-14. That is floating-point noise from a different summation order, not a
difference in information.

`--demo-fail` plants three look-aheads and requires each to be caught: a signal reporting
an observation one month past the as-of date, an R²_oos benchmark computed on the full
sample, and an allocation pushed outside the line ranges. All three are caught.

```
  3 of 3 planted look-aheads were caught
    caught   as-of metadata check
    caught   expanding-mean check
    caught   mandate check
```

`tests/test_lookahead.py` passes 12 of 12 against this desk's modules, including the
static import-graph test, which confirms that no module written here reaches the network,
imports the raw store, or names the raw cache by path.

---

## 12. Outputs

| File | Contents |
|---|---|
| `outputs/quant/allocation.json` | the allocation at 30 June 2026, unconstrained and constrained, active weights, ex-ante TE, binding constraint, composite scores, confidence, rationale, recommendation |
| `outputs/quant/model_path.json` | the model allocation at all twenty meetings, chained |
| `outputs/quant/r2oos.json` | the full table, both samples, every cell, truncated and untruncated, with Clark-West t-statistics |
| `outputs/quant/volmgmt.json` | variance forecastability on three loss scales, halflife sensitivity, and the volatility-management backtest |
| `outputs/quant/riskmodel.json` | shrinkage intensity path, condition numbers, current covariance and correlation |
| `outputs/quant/signals.json` | current z-scores, raw values, citations, sign priors, parameters |
| `outputs/quant/coverage.json` | which inputs exist from when, and which series were excluded and why |
| `outputs/quant/summary.json` | the compact index |

Reproduce with `py -3 -m taa.run_quant` (18 seconds) and verify with
`py -3 tests/check_quant.py`.

---

## References

Andersen, T. and Bollerslev, T. (1998). Answering the skeptics: yes, standard volatility
models do provide accurate forecasts. *International Economic Review* 39(4), 885-905.

Asness, C., Moskowitz, T. and Pedersen, L. (2013). Value and momentum everywhere.
*Journal of Finance* 68(3), 929-985.

Campbell, J. and Thompson, S. (2008). Predicting excess stock returns out of sample: can
anything beat the historical average? *Review of Financial Studies* 21(4), 1509-1531.

Cederburg, S., O'Doherty, M., Wang, F. and Yan, X. (2020). On the performance of
volatility-managed portfolios. *Journal of Financial Economics* 138(1), 95-117.

Clark, T. and West, K. (2007). Approximately normal tests for equal predictive accuracy
in nested models. *Journal of Econometrics* 138(1), 291-311.

Corsi, F. (2009). A simple approximate long-memory model of realized volatility.
*Journal of Financial Econometrics* 7(2), 174-196.

De Bondt, W. and Thaler, R. (1985). Does the stock market overreact? *Journal of Finance*
40(3), 793-805.

Faber, M. (2007). A quantitative approach to tactical asset allocation. *Journal of
Wealth Management* 9(4), 69-79.

Harvey, C., Liu, Y. and Zhu, H. (2016). ...and the cross-section of expected returns.
*Review of Financial Studies* 29(1), 5-68.

Hou, K., Xue, C. and Zhang, L. (2020). Replicating anomalies. *Review of Financial
Studies* 33(5), 2019-2133.

Jegadeesh, N. (1990). Evidence of predictable behavior of security returns. *Journal of
Finance* 45(3), 881-898.

Koijen, R., Moskowitz, T., Pedersen, L. and Vrugt, E. (2018). Carry. *Journal of
Financial Economics* 127(2), 197-225.

Ledoit, O. and Wolf, M. (2003). Improved estimation of the covariance matrix of stock
returns with an application to portfolio selection. *Journal of Empirical Finance* 10(5),
603-621.

Ledoit, O. and Wolf, M. (2004). Honey, I shrunk the sample covariance matrix. *Journal of
Portfolio Management* 30(4), 110-119.

Lo, A. (2002). The statistics of Sharpe ratios. *Financial Analysts Journal* 58(4), 36-52.

Michaud, R. (1989). The Markowitz optimization enigma: is optimized optimal? *Financial
Analysts Journal* 45(1), 31-42.

Moreira, A. and Muir, T. (2017). Volatility-managed portfolios. *Journal of Finance*
72(4), 1611-1644.

Moskowitz, T., Ooi, Y. and Pedersen, L. (2012). Time series momentum. *Journal of
Financial Economics* 104(2), 228-250.

Patton, A. (2011). Volatility forecast comparison using imperfect volatility proxies.
*Journal of Econometrics* 160(1), 246-256.

Welch, I. and Goyal, A. (2008). A comprehensive look at the empirical performance of
equity premium prediction. *Review of Financial Studies* 21(4), 1455-1508.
