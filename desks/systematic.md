# Systematic Desk

**Ashcroft University Endowment · Tactical Asset Allocation Programme**
**What predicts asset-class returns, how well, and what the programme can earn**

28 July 2026 · 200bps ex-ante tracking error · quarterly rebalance · nine lines
Evidence pack: `outputs/systematic_evidence.json` (40 claims, 32 verified)
Check: `tests/check_systematic.py`

---

## Warning that belongs before anything else

An estimated Sharpe ratio computed on sixty monthly observations carries a
standard error of **0.45 in annualised units**. Under IID returns, Lo's
asymptotic result gives

```
SE(SR) = sqrt( (1 + SR² / 2) / n )
```

At n = 60 the formula returns 0.137 for a per-period Sharpe of 0.50 and 0.158
for 1.00, which reproduces Lo's Table 1 exactly.[^lo] Converting to the units
people actually quote: an **annualised** Sharpe of 0.50 estimated over five
years of monthly data has a monthly Sharpe of 0.1443, a monthly standard error
of 0.1298, and therefore an annualised standard error of **0.4495**. The 95%
confidence interval runs from **−0.38 to +1.38**. For an annualised Sharpe of
1.00 the standard error is 0.4564 and the interval runs from 0.11 to 1.89.

Five years of monthly data cannot separate a good programme from a bad one.
Lo shows serial correlation makes this materially worse, inflating naively
annualised Sharpe ratios by more than 65% in some cases. Any backtest
presented to this committee on a five-year window is a coin flip dressed as
evidence, and the committee should say so out loud when one is presented.

---

## 1. What fraction of published predictors survive out of sample

**Answer: somewhere between 0.18 and 0.82, and the spread is the finding.**

The literature does not disagree about the data. It disagrees about four
methodological choices, and each one moves the number by tens of percentage
points.

| Study | Universe | Survival rate reported |
|---|---|---|
| Hou, Xue & Zhang (2020), RFS | 452 anomalies | **35%** at \|t\|>1.96; **17.9%** at \|t\|>2.78[^hxz] |
| Harvey, Liu & Zhu (2016), RFS | 296 significant published factors | **47%–73%** survive; 80 to 158 are likely false discoveries[^hlz] |
| McLean & Pontiff (2016), JF | 97 predictors | **74%** of return survives out of sample; **42%** survives post-publication[^mp] |
| Goyal, Welch & Zafirov (2024), RFS | 29 post-2008 + 17 original equity-premium predictors | ~**33%** implied (>⅓ fail in-sample, half the remainder fail out of sample)[^gwz] |
| Chen & Zimmermann (2022) | CZ22 open-source dataset | **74%** of in-sample return persists in the first three years out of sample[^cz] |
| Jensen, Kelly & Pedersen (2023), JF | 153 factors, 93 countries | **82.4%** Bayesian; **75.6%** under Benjamini-Yekutieli[^jkp] |

### Why they differ

Jensen, Kelly and Pedersen do the useful thing and decompose the entire gap
between their number and Hou-Xue-Zhang's in a single figure.[^jkp]

```
35.0%   Hou, Xue & Zhang (2020) baseline
55.6%   + longer sample, 15 added factors, conservative construction choices
61.3%   + drop factors the original studies themselves reported as insignificant
82.4%   + test the CAPM alpha rather than the raw return
75.6%   + Benjamini-Yekutieli multiple-testing correction
82.4%   + Bayesian hierarchical multiple-testing model
82.4%   + global sample, 93 countries
```

The single largest step, 61.3% to 82.4%, comes from testing risk-adjusted
alpha instead of raw return. That choice is defensible on theory: a factor
whose raw return is significant only because it loads on the market has not
found an anomaly, and a factor whose raw return is insignificant while its
alpha is positive is masked by its risk exposure, which is precisely what
betting-against-beta predicts. Hou, Xue and Zhang test raw returns and
therefore count the low-beta factor as a failure, which is the opposite of
what the theory says it should be counted as.

Chen and Zimmermann attack the same number from a different angle and land
harder. The usual reconciliation of Hou-Xue-Zhang with the rest of the
literature is that they de-emphasise microcaps. Chen and Zimmermann show this
reconciliation is wrong. **Only about 26% of Hou, Xue and Zhang's long-short
strategies were shown to be clearly statistically significant in the original
papers.**[^cz] Counting a factor as a failed replication when its own authors
never claimed it worked inflates the failure rate mechanically. Jensen, Kelly
and Pedersen make the same point from their side, and independently kill the
microcap explanation: replication rates by size bucket are 77.3% for mega-caps
and 79.8% for large-caps against 82.4% overall, so the result is not a
small-stock artefact.[^jkp]

Running the other way, Harvey, Liu and Zhu's hurdle survives all of this.
They catalogue 316 factors from 313 papers and argue the significance
threshold should be t > 3.0, while stating explicitly that 316 undercounts
the true number of tests and that the true hurdle is therefore higher.[^hlz]
Hou, Xue and Zhang note that a direct Benjamini-Hochberg-Yekutieli adjustment
on their own 452 anomalies yields cutoffs of 3.47 and 4.27 at the 5% and 1%
levels.[^hxz] Nobody in this literature disputes that the conventional t = 2.0
is wrong. They dispute how much wrong.

### What the desk takes from this

The replication rate is the wrong number to manage against. What matters for
a programme that must actually earn money is the **decay** rate, and there
the literature is much closer to agreement:

- McLean and Pontiff: **26%** decline out of sample, **58%** decline
  post-publication, implying a **32%** publication effect.[^mp]
- Chen and Zimmermann, replicating on a different dataset: 74% of return
  persists in the first three years out of sample, decaying to roughly **50%**
  far from the original samples, of which multiple-testing statistics imply
  only about 12 percentage points is publication bias and the remaining 38
  points is a genuine decline in the expected return.[^cz]

**Operating rule for this desk: halve the backtested edge of any signal
this committee can read about in a journal.** That haircut is not
conservatism. It is the central estimate from two independent meta-studies
that disagree about almost everything else.

**Falsifier.** If a signal built on published research delivers, over a
rolling five-year window, more than 80% of its backtested information ratio
net of costs, the haircut is too severe and should be revisited. Given the
Sharpe standard error above, five years will not be enough to conclude that
with confidence, which is itself part of the finding.

---

## 2. Does anything predict asset-class returns out of sample

Stock-level anomaly replication is a different literature from asset-class
prediction, and the asset-class record is worse.

### 2.1 The equity risk premium

Welch and Goyal's abstract is the honest starting point: the classic
predictors "have predicted poorly both in-sample (IS) and out-of-sample (OOS)
for 30 years now", are unstable, and "would not have helped an investor with
access only to available information to profitably time the market."[^wg]
Their Table 1 is unambiguous. **Every one of the twelve classic monthly
predictors has a negative full-sample out-of-sample R², ranging from −1.78%
for the earnings-price ratio to −27.14% for stock variance,** against
adjusted in-sample R² values between −1.18% and +1.08%.[^wg] Selected rows:

| Predictor | Adj. IS R² | OOS R² (full sample) |
|---|---:|---:|
| Earnings-price ratio | +1.08% | −1.78% |
| Dividend yield | +0.91% | −1.93% |
| Dividend price ratio | +0.49% | −2.06% |
| Term spread | +0.16% | −2.42% |
| Treasury bill rate | +0.34% | −3.37% |
| Default yield spread | −1.18% | −3.29% |
| Stock variance | −0.76% | −27.14% |

Campbell and Thompson rescue part of this, and the mechanism matters. They
impose two weak restrictions: set the slope to zero when it carries the sign
opposite to theory, and set the equity-premium forecast to zero when it comes
out negative. With those in place "most of these predictor variables, and
almost all that are statistically significant in-sample, perform better
out-of-sample than the historical average return forecast."[^ct] The
out-of-sample explanatory power is small.

Goyal, Welch and Zafirov extend the exercise through 2021 across 29 variables
from 26 post-2008 papers plus the original 17. **More than one third have lost
in-sample significance entirely, and of those that retain it, half perform
poorly out of sample.**[^gwz] The predictors published to answer the 2008
critique have largely failed the same test.

### 2.2 Why 0.5% monthly is economically meaningful

The number sounds trivial and is not. Campbell and Thompson show the correct
yardstick for R² is the squared Sharpe ratio at the same frequency, because
for a mean-variance investor the proportional increase in expected portfolio
return is approximately **R² / S²**.[^ct] In their monthly data since 1871
the monthly Sharpe ratio is 0.108, so **S² = 1.2%**. Their worked case: an
out-of-sample R² of 0.25% against S² of 1.2% delivers 0.25/1.2 = **21%** more
average monthly portfolio return, which is about 25bps a month at unit risk
aversion and about 1% a year at risk aversion three. **A monthly R²_oos of
0.5% therefore delivers roughly a 42% proportional lift.**

Their closing observation is the one to keep: "Regressions with large R²
statistics would be too profitable to believe." A signal reporting a 5%
monthly out-of-sample R² is not a discovery. It is a bug.

### 2.3 Time-series momentum

Moskowitz, Ooi and Pedersen document time-series momentum across 58 liquid
futures and forward instruments, with the past twelve-month excess return
positively predicting the next month's return, persisting about a year and
then partially reversing. Their extended out-of-sample test delivers an
annualised Sharpe ratio of about 1.1, and the correlation between an
instrument's illiquidity and its TSMOM Sharpe is −0.16, so the effect is not a
liquidity artefact.[^tsmom]

Huang, Li, Wang and Zhou dismantle the statistical case.[^huang] Three
findings, all directly relevant:

1. Asset-by-asset time-series regressions "reveal little evidence of TSM, both
   in- and out-of-sample."
2. The pooled regression t-statistic of 4.34 looks decisive but sits below the
   5% bootstrap critical values of **12.53** (parametric wild) and **4.83**
   (nonparametric pairs). The apparent significance is largely a fixed-effects
   artefact; the null that all 55 assets share a common mean is strongly
   rejected.
3. A "time-series history" strategy that buys assets with positive historical
   mean returns and requires no predictability whatsoever performs
   **virtually identically** to TSMOM, and the differences in average and
   risk-adjusted returns are indistinguishable from zero.

Point three is the one that should change behaviour. If a strategy requiring
no predictability matches a strategy premised on predictability, the
predictability is not what is earning the money.

### 2.4 Carry, value and momentum across asset classes

Koijen, Moskowitz, Pedersen and Vrugt find carry predicts returns both
cross-sectionally and in the time series across asset classes. Average
carry-strategy Sharpe ratio is **0.74** across nine asset classes, ranging from
0.37 for call options to 1.80 for put options, and the diversified global carry
factor reaches **1.10** against 0.47 for a diversified passive long.[^carry]
Asness, Moskowitz and Pedersen document value and momentum across eight
markets and asset classes with a common global factor structure, and
critically, value and momentum are **negatively correlated** with each
other.[^amp]

The constraint for this mandate is that carry, value and momentum as tested
in these papers are long-short and largely market-neutral. This programme is
long-only against a fixed policy portfolio with no fund-level leverage. The
signals map onto relative-weight tilts across nine lines and nothing more, so
the reported Sharpe ratios are the wrong reference point. What does transfer
is the negative value-momentum correlation, which raises effective breadth
more than adding a third correlated equity line does.

### 2.5 Two econometric traps that inflate everything above

**Stambaugh bias.** When returns are regressed on a lagged persistent
stochastic regressor such as dividend yield, the disturbance correlates with
the regressor's innovation and the OLS estimator is biased in finite samples.
The bias is severe when the regressor is persistent, and over 1927 to 1996 it
runs to roughly one third of the OLS estimate in the excess-return-on-dividend-
yield regression. *Recalled, not verified: the one-third magnitude comes from
secondary summaries rather than the paper opened in this session.* The
direction and mechanism are not in dispute.[^stambaugh]

**Overlapping long-horizon regressions.** Boudoukh, Richardson and Whitelaw
show that under the null of no predictability with persistent regressors, the
estimators are almost perfectly correlated across horizons. At dividend-yield
persistence the analytical correlation is **99% between the one- and two-year
horizon estimators and 94% between the one- and five-year**, and reaches 99.6%
between the four- and five-year.[^brw] The common sampling error makes
coefficients and R² roughly proportional to the horizon under the null, which
is exactly the pattern that appears in the data and has been read for decades
as evidence that long-horizon predictability is stronger. A one-year, a
three-year and a five-year result are not three pieces of evidence. They are
one piece of evidence reported three times.

### 2.6 Summary for question 2

| Signal | Reported magnitude | Horizon | Reading for this mandate |
|---|---|---|---|
| Classic equity-premium predictors | R²_oos −1.78% to −27.14% | monthly | Do not use unrestricted |
| Campbell-Thompson restricted | small positive R²_oos; 0.5% ≈ 42% return lift | monthly | Usable, restrictions mandatory |
| Time-series momentum | Sharpe ~1.1 diversified | monthly | Contested; matches a no-predictability strategy |
| Carry | Sharpe 0.74 avg, 1.10 diversified | monthly | Long-short; partially transferable |
| Value & momentum across assets | common global factor | monthly | Transferable via the negative correlation |
| Term spread | R²_oos −2.42% | monthly | Negative out of sample |
| Credit spread | R²_oos −3.29% | monthly | Negative out of sample |
| Long-horizon valuation | R² proportional to horizon under the null | 1–5 yr | Largely an artefact |

---

## 3. Does volatility management work

Two claims get conflated. They have different answers.

### 3.1 Is volatility forecastable? Yes, and it is not close.

Conditional variance is autoregressive. Engle's ARCH and Bollerslev's GARCH
established volatility clustering and are uncontested.[^garch] Corsi's
heterogeneous autoregressive model of realised volatility produces
**out-of-sample Mincer-Zarnowitz R² of roughly 0.76 to 0.82** for S&P 500
realised volatility across one- to twenty-day horizons.[^corsi]

Set that against the return side of this paper. The monthly equity premium
delivers an out-of-sample R² of 0.005 in the good cases and negative numbers
in most. **Volatility is roughly two orders of magnitude more forecastable
than return.** If this programme has an edge anywhere, it has it here.

### 3.2 Does scaling by a volatility forecast improve risk-adjusted return? Contested.

**For.** Moreira and Muir scale monthly factor returns by the inverse of the
prior month's realised variance. On the market factor: annualised alpha of
**4.86%**, appraisal ratio **0.33**, a **25% increase** in the buy-and-hold
Sharpe ratio, and utility gains of about **65% of lifetime utility**, roughly
double the 35% Campbell and Thompson attribute to timing expected returns.
The mechanism is clean: variance is highly forecastable at short horizons and
variance forecasts are only weakly related to future returns, so the
mean-variance trade-off weakens in high-volatility periods. They also show the
result survives 1bp and 10bp transaction-cost assumptions plus a 4bp add-on
for high-VIX regimes.[^mm]

**Against.** Cederburg, O'Doherty, Wang and Yan test 103 equity strategies and
find that the trading strategies implied by Moreira and Muir's spanning
regressions **are not implementable in real time**. Reasonable out-of-sample
versions generally earn lower certainty-equivalent returns and Sharpe ratios
than simple investments in the original unmanaged portfolios, and the cause is
**structural instability in the underlying spanning regressions**.[^ced] Liu,
Tang and Zhou identify a look-ahead bias in the standard implementation and
report maximum drawdowns of **68% to 93%** after correcting it, with
outperformance concentrated in the financial crisis. *Recalled from the SSRN
abstract, not the paper.*[^ltz]

**Where the benefit actually lives.** Harvey and co-authors run volatility
targeting across 60 assets with daily data from 1926 to 2017. The Sharpe ratio
improvement holds **only for risk assets, equities and credit**, and is
negligible for bonds, currencies and commodities. What holds everywhere is the
reduction in left-tail severity, because tail events occur when volatility is
already elevated and a target-volatility portfolio is already small. *Recalled
from the abstract; SSRN blocks automated fetch.*[^harvey18] Barroso and
Santa-Clara give the strongest positive case: targeting 12% constant volatility
on the momentum factor virtually eliminates crashes and nearly doubles its
Sharpe ratio.[^bsc] Momentum is a levered long-short factor with a fat left
tail, which is not this portfolio.

### 3.3 Honest verdict for this mandate

**Use volatility scaling to control risk, not to add return. Book zero alpha
for it.**

The supporting literature tests levered, monthly-rebalanced, long-short factor
portfolios and takes most of its benefit from crash avoidance in the
equity-shaped legs. This mandate is long-only, unlevered under UBTI, rebalanced
quarterly, and holds nine correlated asset-class lines. It cannot capture the
mechanism that generates the alpha in Moreira and Muir. Worse, the real-time
implementation problem identified by Cederburg et al. and Liu et al. bites
harder at a quarterly frequency than at a monthly one, because the volatility
forecast decays fastest at short horizons and Moreira and Muir themselves
report that their alphas decline as the rebalancing period lengthens.

What does transfer is the Harvey et al. result on tail shape, and it transfers
to the constraint the board actually set. The endowment carries a hard −20%
peak-to-trough limit against an 18% operating-budget dependency, sitting at
rank 3 in the constraint hierarchy and above the return objective. Scaling
equity exposure down when the volatility forecast rises, and parking the risk
in the 0–10% cash range the IPS explicitly created for this purpose, is the
cheapest available defence of that limit.

Justify it under constraint 3. Budget zero alpha. Expect it to cost a small
amount of expected return.

**Falsifier.** If a real-time volatility-scaled version of the policy
portfolio, run point-in-time with expanding-window scaling constants and no
full-sample normalisation, fails to reduce realised maximum drawdown relative
to the unscaled policy portfolio over the available history, the risk-control
justification fails too and the overlay should be switched off.

---

## 4. What can this programme actually earn

### 4.1 The law

Grinold: `IR = IC × √BR`.[^grinold] Clarke, de Silva and Thorley add the
transfer coefficient, the cross-sectional correlation between risk-adjusted
active weights and risk-adjusted expected residual returns, giving
`IR = TC × IC × √BR`. Their simulation study puts the typical transfer
coefficient at **0.3 to 0.8**.[^cdt]

### 4.2 Breadth: nominal 36, effective 2.0

Nominal breadth is nine lines times four meetings, which is 36. Two haircuts
apply and both are large.

**Cross-sectional collapse.** The nine lines are not nine bets. US equity,
developed ex-US and emerging markets move together at pairwise correlations of
roughly 0.78 to 0.87. Listed real estate and high yield carry equity beta at
roughly 0.72 to 0.75. Investment grade sits between credit and duration. Cash
is the mirror of the aggregate risk decision rather than an independent line.
Taking an average pairwise correlation of 0.45 across the nine and applying the
equicorrelated effective-sample-size expression:[^buckle]

```
BR_cross = N / (1 + ρ(N − 1))
         = 9 / (1 + 0.45 × 8)
         = 9 / 4.6
         = 1.96 independent cross-sectional bets
```

**Time-series collapse.** Quarterly decisions are not independent because the
signals are persistent. A twelve-month trend signal sampled quarterly shares
three of four lookback quarters between consecutive readings, giving quarterly
autocorrelation near 0.75. Valuation ratios run near 0.95. Carry near 0.85. A
composite weighted toward the faster signals gives γ ≈ 0.60. The effective
number of independent draws from an AR(1) of length T is T(1−γ)/(1+γ):

```
BR_time = 4 × (1 − 0.60) / (1 + 0.60)
        = 4 × 0.25
        = 1.00 independent decisions per year
```

**Effective breadth = 1.96 × 1.00 = 1.96, taken as 2.0.** That is 5.4% of the
nominal 36. In the term that matters, √2.0 = 1.41 against √36 = 6.00, so the
breadth contribution is worth 1.41 rather than 6.00, a factor of 4.2.

**The counter-argument, stated fairly.** Sneddon models the full
portfolio-construction problem and finds that both return correlation and alpha
correlation **increase** the information ratio, reversing the popular belief
that correlation destroys breadth.[^sneddon] His mechanism is real: inverting
the covariance matrix produces negatively correlated active weights, which
combine with positively correlated returns to reduce risk while leaving return
unchanged, so IR improves. If Sneddon is right, the haircut above is wrong in
sign, not merely in magnitude. This desk cannot resolve the dispute from the
literature. What it can do is present the sensitivity table below and let the
committee see how much the answer depends on the choice.

### 4.3 Information coefficient: 0.03

Grinold and Kahn put a good forecaster at IC = 0.05, a great one at 0.10, a
world-class one at 0.15, and note that an IC above 0.20 "usually signals a
faulty backtest or imminent investigation for insider trading."[^gkic]

Working independently from the prediction literature rather than from the
practitioner range: the best-case published monthly equity-premium R²_oos after
Campbell-Thompson restrictions is about 0.5%, implying a correlation of about
0.071. Goyal, Welch and Zafirov find half the in-sample survivors fail out of
sample, and McLean and Pontiff measure a 58% post-publication return decline.
An honest ex-ante haircut of roughly half on that correlation lands near 0.035.
**IC = 0.03 is the conservative end of a defensible range and is what this desk
uses.**

The most important citation in this section is Grinold and Kahn's own, on a
mandate structurally identical to this one:

> "Since IR_BT = IC_BT √BR, an independent benchmark timing forecast every
> quarter only leads to a breadth of 4. To generate a benchmark timing
> information ratio of 0.5 requires an information coefficient of 0.25! The
> fundamental law captures exactly why most institutional managers focus on
> stock selection."[^gkbt]

An IC of 0.25 exceeds the 0.20 level the same authors say indicates a faulty
backtest. The founding text of the fundamental law states that a
quarterly timing programme does not work, and states it about this mandate.

### 4.4 Transfer coefficient: 0.50

Clarke, de Silva and Sapra measure transfer coefficients directly on a
constrained long-only equity portfolio.[^cds] With all constraints imposed,
**TC = 0.332**, meaning about a third of the information in the rankings
reaches the active positions. Relaxing constraints one at a time:

| Constraint relaxed | TC |
|---|---:|
| None (all constraints) | 0.332 |
| Position limits | 0.298 |
| Sector | 0.340 |
| Industry | 0.347 |
| Industry and sector together | 0.422 |
| Market cap | 0.471 |
| **Long-only** | **0.678** |

Long-only is the single largest destroyer of information transfer.

This mandate: long-only, no fund leverage under UBTI, per-line ranges, sleeve
ranges, and a 50bps minimum trade size. Four of the nine lines are
asymmetrically truncated because their policy weight sits near the bottom of
their range (cash 0% in 0–10%, real estate 2% in 0–6%, commodities 3% in 0–8%,
high yield 5% in 0–10%), so the desk can overweight them freely and underweight
them barely at all. Working the other way, the ranges are wide relative to a
200bps tracking-error budget (US equity's 28–48% band is ±10pp, five times the
whole TE budget) and will bind less often than in the Clarke-de Silva-Sapra
equity study. The 50bps minimum trade size truncates precisely the small
positions where a low-IC signal expresses itself.

**TC = 0.50**, mid-range within the Clarke-de Silva-Thorley 0.3 to 0.8 band.

### 4.5 The arithmetic

```
IR  = IC × √BR × TC
    = 0.03 × √2.0 × 0.50
    = 0.03 × 1.414214 × 0.50
    = 0.021213
    = 0.0212

Expected annual alpha = IR × TE budget
                      = 0.0212 × 200bps
                      = 4.2bps per year
```

**Costs.** Gross active weight at 200bps ex-ante tracking error is about 30% of
NAV: roughly two effective independent bets at about 10% residual volatility
each requires about 14% active weight per bet. A signal with quarterly
autocorrelation 0.60 retrades most of that book each quarter. For a
standardised AR(1), `E|s_t − s_{t−1}| / E|s_t| = √(2(1−γ)) = 0.894`, so about
89% of the active book turns over per quarter before filtering. The 50bps
minimum trade size suppresses roughly a quarter of that, leaving about 20% of
NAV traded per quarter and about 80% per year. At a blended 8bps one-way all-in
cost across the nine vehicles (SPY/VTI 1–2bps, VEA/LQD/IEF 2–4bps,
EEM/VNQ/HYG 4–8bps, DBC/GSG 6–12bps, including half-spread, market impact and
commission):

```
Annual cost = 80% × 8bps = 6.4bps
```

### 4.6 The plain sentence

**On the desk's central assumptions the programme is expected to produce 4.2bps
a year of gross alpha against 6.4bps a year of implementation cost, so it loses
2.2bps a year, or about USD 187,000 on an 850m fund, before any staff or
governance cost.**

### 4.7 Sensitivity, because the point estimate is not the point

Break-even requires an IR of 0.032. Holding the other two inputs at their
central values, that means **IC = 0.045, or effective breadth = 4.6, or
TC = 0.75.** Expected annual alpha in bps, against a 6.4bps cost line:

| | BR = 2.0 | BR = 4.0 | BR = 9.0 | BR = 36 (nominal) |
|---|---:|---:|---:|---:|
| **IC 0.02, TC 0.50** | 2.8 | 4.0 | 6.0 | 12.0 |
| **IC 0.03, TC 0.50** | **4.2** | 6.0 | 9.0 | 18.0 |
| **IC 0.05, TC 0.50** | 7.1 | 10.0 | 15.0 | 30.0 |
| **IC 0.03, TC 0.68** | 5.8 | 8.2 | 12.2 | 24.5 |
| **IC 0.05, TC 0.68** | 9.6 | 13.6 | 20.4 | 40.8 |

Read the table honestly. The naive calculation using nominal breadth of 36 and
a good-forecaster IC of 0.05 produces 30bps a year and would sail through a
committee. The same arithmetic with an effective breadth of 2 and a
literature-calibrated IC produces 4.2bps and fails. **Nothing separates those
two answers except the breadth assumption, which the literature has not
settled.** Even the most favourable cell in the table, 40.8bps, is 0.41% a year
against an 8.10% required return, so at its best this programme contributes
about 5% of the return objective.

**Falsifier for the whole programme.** Track the realised information
coefficient of the composite signal, quarter by quarter, across the nine lines.
If the trailing mean IC has not exceeded 0.045 after twenty quarters, the
programme is not clearing its costs and should be shut down. Qian and Hua's
warning applies to the measurement: the fundamental law understates true active
risk because it ignores variation in the IC itself, and realised active risk is
often materially above the risk model's tracking error. They measure quarterly
IC standard deviations of 2.7% and 3.4% for two equity valuation factors over
67 quarters.[^qh] An IC mean of 0.03 against an IC standard deviation of 0.03
is an information ratio of 1.0 in their formulation and a coin flip in
practice.

---

## 5. How to compute R²_oos, for the desk that implements it

**Definition** (Campbell-Thompson, identical benchmark to Welch-Goyal):[^ct]

```
                 Σ_{t=t0}^{T} (r_t − r̂_t)²
R²_oos = 1 −  ────────────────────────────────
                 Σ_{t=t0}^{T} (r_t − r̄_t)²
```

where

- `r_t` is the realised excess return in period t
- `r̂_t` is the predictive-regression forecast of `r_t`, formed with data
  through **t−1 only**, with coefficients re-estimated on an **expanding
  window** through t−1
- `r̄_t` is the **expanding-window historical mean** of r through t−1

`R²_oos > 0` means the predictive model beats the recursively updated
historical mean.

**Campbell-Thompson restrictions**, applied in this order:

1. If the estimated slope carries the sign opposite to the theoretically
   expected sign, set it to zero for that forecast.
2. If the resulting equity-premium forecast is negative, set it to zero.

**Significance** (Clark-West MSPE-adjusted, equation 2.1):[^cw]

```
f̂_t = (r_t − r̄_t)² − [ (r_t − r̂_t)² − (r̄_t − r̂_t)² ]
```

Regress `f̂` on a constant. Take the **one-sided** t-statistic on that constant
against standard normal critical values: **1.282 at 10%, 1.645 at 5%**. Use
Newey-West standard errors with lag J−1 for J-step-ahead or overlapping
forecasts. Clark and West note the statistic is not asymptotically normal under
their preferred conditions and that normal critical values give actual size
slightly below nominal, so the test is mildly conservative.

**Two traps.**

First, the benchmark must be the recursively updated mean computed with data
through t−1 only, never the full-sample mean. Using the full-sample mean is the
single most common way a negative R²_oos becomes positive by accident, and it
is the same class of error Liu, Tang and Zhou found in the volatility-timing
literature.

Second, R²_oos and Clark-West can disagree, and that is expected rather than a
bug. Clark-West tests the null that the predictor's population coefficient is
zero, so it can reject while R²_oos is negative, because a small true
coefficient still costs more in estimation noise than it earns in forecast
accuracy. Report both and read them as answering different questions. For a
programme that must trade, R²_oos is the operative statistic and Clark-West is
the diagnostic.

---

## 6. Check output

`tests/check_systematic.py`, standard library only, run against
`outputs/systematic_evidence.json`.

```
=== Systematic desk evidence check ===
    file: C:\Users\david\Financial_models\youtube_test_agents\outputs\systematic_evidence.json
========================================================================
[PASS] claims list is non-empty                                   |  40 claims
[PASS] every claim has an id
[PASS] every claim has a non-empty source_url                     |  40/40 ok
[PASS] every claim status is VERIFIED or RECALLED                 |  40/40 ok
[PASS] claim ids are unique                                       |  40 ids, 40 unique
[PASS] VERIFIED fraction >= 60%                                   |  32/40 = 80.0% (floor 60%)
[PASS] fundamental_law block present
[PASS] fundamental_law has all required keys
[PASS] inputs are in sane ranges                                  |  ic=0.03 br=2.0 tc=0.5 te=200.0bps
[PASS] ir == round(ic * sqrt(breadth) * tc, 4)                    |  stated 0.021200 vs recomputed 0.021200
[PASS] expected_alpha_bps == round(ir * te_budget_bps, 1)         |  stated 4.2000 vs recomputed 4.2000
[PASS] clears_costs is consistent with alpha vs cost              |  alpha 4.2bps vs cost 6.4bps -> False
[PASS] net_alpha_bps == round(alpha - cost, 1)                    |  stated -2.2 vs recomputed -2.2
[PASS] derivation shows the arithmetic                            |  3878 chars
[PASS] predictor_survival block present
[PASS] survival low is strictly between 0 and 1                   |  low = 0.18
[PASS] survival high is strictly between 0 and 1                  |  high = 0.82
[PASS] survival range is ordered low < high                       |  [0.18, 0.82]
[PASS] survival range carries >= 2 distinct sources               |  6 distinct of 6 listed
[PASS] the sources actually disagree (non-degenerate range)       |  spread = 0.64
[PASS] survival note explains why the sources differ              |  1092 chars
[PASS] sharpe_se_n60 block present
[PASS] sharpe_se_n60.sr_0_5 matches Lo (2002) eq. 9               |  stated 0.137 vs formula 0.1370
[PASS] sharpe_se_n60.sr_1_0 matches Lo (2002) eq. 9               |  stated 0.158 vs formula 0.1580
[PASS] r2oos_definition benchmarks the expanding historical mean  |  expanding historical mean
[PASS] vol_management separates forecastability from scaling
------------------------------------------------------------------------
26 checks, 26 passed, 0 failed
EXIT=0
```

The check can fail. `--demo-fail` corrupts an in-memory copy three ways: it
strips a `source_url`, sets `ir` to 0.0850, and collapses the survival range to
a single source.

```
=== DEMO-FAIL MODE: running against a corrupted in-memory copy ===
    injected: (1) stripped source_url on the first claim,
              (2) wrong ir in fundamental_law,
              (3) survival range collapsed to one source
========================================================================
[FAIL] every claim has a non-empty source_url                     |  offenders: welch_goyal_2008_headline
[FAIL] ir == round(ic * sqrt(breadth) * tc, 4)                    |  stated 0.085000 vs recomputed 0.021200
[FAIL] expected_alpha_bps == round(ir * te_budget_bps, 1)         |  stated 4.2000 vs recomputed 17.0000
[FAIL] survival range is ordered low < high                       |  [0.18, 0.18]
[FAIL] survival range carries >= 2 distinct sources               |  1 distinct of 1 listed
[FAIL] the sources actually disagree (non-degenerate range)       |  spread = 0.00
------------------------------------------------------------------------
26 checks, 20 passed, 6 failed
demo-fail behaved correctly: the check went red.
```

*(FAIL rows shown; the 20 passing rows are identical to the clean run and are
omitted here for length.)*

---

## 7. What the desk recommends

1. **Halve the backtested edge of any published signal.** McLean-Pontiff and
   Chen-Zimmermann converge on roughly 50% decay far from the original sample.
   This is the central estimate, not a conservative one.

2. **Run the volatility overlay as drawdown control, book zero alpha.** The
   forecastability is real and large. The alpha from scaling is contested and
   does not survive real-time implementation in the form this mandate would
   have to use. The board's −20% limit is where the overlay earns its keep.

3. **Do not present a Sharpe ratio on fewer than sixty months without its
   standard error attached.** At n = 60 the annualised standard error is about
   0.45 and the confidence interval on a Sharpe of 0.50 includes zero.

4. **Size the tactical programme to what the arithmetic supports.** The
   fundamental law, applied honestly to nine correlated lines, four meetings,
   persistent signals and a long-only constrained book, returns 4.2bps a year
   against 6.4bps of cost. Either the desk finds an IC of 0.045 and can
   demonstrate it out of sample, or the programme does not pay for itself.
   Grinold and Kahn reached the same conclusion about quarterly benchmark
   timing in the book that introduced the law.

5. **If the programme runs anyway, it must run on the falsifiers.** Track the
   realised IC quarterly. Twenty quarters below a trailing mean of 0.045 is the
   trigger to stop. Publish the number to the committee each quarter so the
   decision is made by the data rather than by whoever argues most confidently
   in the moment.

---

## Sources

[^lo]: Lo (2002), "The Statistics of Sharpe Ratios", *Financial Analysts Journal* 58(4), 36–52, equation (9) and Table 1. <https://traders.studentorg.berkeley.edu/papers/The-Statistics-of-Sharpe-Ratios.pdf>
[^hxz]: Hou, Xue & Zhang (2020), "Replicating Anomalies", *Review of Financial Studies* 33(5), 2019–2133. <https://global-q.org/uploads/1/2/2/6/122679606/houxuezhang2020rfs.pdf>
[^hlz]: Harvey, Liu & Zhu (2016), "…and the Cross-Section of Expected Returns", *RFS* 29(1), 5–68; NBER WP 20592. <https://www.nber.org/system/files/working_papers/w20592/w20592.pdf>
[^mp]: McLean & Pontiff (2016), "Does Academic Research Destroy Stock Return Predictability?", *Journal of Finance* 71(1), 5–32. <https://tevgeniou.github.io/EquityRiskFactors/bibliography/AcademicReviewFactor.pdf>
[^gwz]: Goyal, Welch & Zafirov (2024), "A Comprehensive 2022 Look at the Empirical Performance of Equity Premium Prediction", *RFS* 37(11), 3490–3557. <https://academic.oup.com/rfs/article/37/11/3490/7749383>
[^cz]: Chen & Zimmermann (2022), "Publication Bias in Asset Pricing Research". <https://arxiv.org/pdf/2209.13623>
[^jkp]: Jensen, Kelly & Pedersen (2023), "Is There a Replication Crisis in Finance?", *Journal of Finance* 78(5), 2465–2518. <https://research-api.cbs.dk/ws/portalfiles/portal/95651880/theis_ingerslev_jensen_et_al_is_there_a_replication_crisis_in_finance_publishersversion.pdf>
[^wg]: Welch & Goyal (2008), "A Comprehensive Look at the Empirical Performance of Equity Premium Prediction", *RFS* 21(4), 1455–1508. <https://breesefine7110.tulane.edu/wp-content/uploads/sites/16/2015/10/Goyal-and-Welch-2008.pdf>
[^ct]: Campbell & Thompson (2008), "Predicting Excess Stock Returns Out of Sample: Can Anything Beat the Historical Average?", *RFS* 21(4), 1509–1531; NBER WP 11468. <https://www.nber.org/system/files/working_papers/w11468/w11468.pdf>
[^tsmom]: Moskowitz, Ooi & Pedersen (2012), "Time Series Momentum", *Journal of Financial Economics* 104(2), 228–250. <https://w4.stern.nyu.edu/facdir/lpederse/papers/TimeSeriesMomentum.pdf>
[^huang]: Huang, Li, Wang & Zhou (2020), "Time series momentum: Is it there?", *JFE* 135(3), 774–794. <https://ink.library.smu.edu.sg/context/lkcsb_research/article/7520/viewcontent/Time_series_momentum_JFE_sv.pdf>
[^carry]: Koijen, Moskowitz, Pedersen & Vrugt (2018), "Carry", *JFE* 127(2), 197–225; NBER WP 19325. <https://www.nber.org/system/files/working_papers/w19325/w19325.pdf>
[^amp]: Asness, Moskowitz & Pedersen (2013), "Value and Momentum Everywhere", *Journal of Finance* 68(3), 929–985. <https://pages.stern.nyu.edu/~lpederse/papers/ValMomEverywhere.pdf>
[^stambaugh]: Stambaugh (1999), "Predictive Regressions", *JFE* 54(3), 375–421. <https://www.sciencedirect.com/science/article/pii/S0304405X99000410> — *recalled, not verified*
[^brw]: Boudoukh, Richardson & Whitelaw (2008), "The Myth of Long-Horizon Predictability", *RFS* 21(4), 1577–1605. <https://pages.stern.nyu.edu/~rwhitela/papers/mlhp%20rfs08.pdf>
[^garch]: Engle (1982), *Econometrica* 50(4), 987–1007; Bollerslev (1986), *Journal of Econometrics* 31(3), 307–327. <https://www.jstor.org/stable/1912773> — *recalled, not verified*
[^corsi]: Corsi (2009), "A Simple Approximate Long-Memory Model of Realized Volatility", *Journal of Financial Econometrics* 7(2), 174–196; author's lecture slides, SNS Pisa 2010. <https://homepage.sns.it/marmi/lezioni/corsi-pisa-2010.pdf>
[^mm]: Moreira & Muir (2017), "Volatility-Managed Portfolios", *Journal of Finance* 72(4), 1611–1644; NBER WP 22208. <https://www.nber.org/system/files/working_papers/w22208/w22208.pdf>
[^ced]: Cederburg, O'Doherty, Wang & Yan (2020), "On the performance of volatility-managed portfolios", *JFE* 138(1), 95–117. <https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3357038>
[^ltz]: Liu, Tang & Zhou (2019/2020), "Volatility-Managed Portfolio: Does It Really Work?", *Journal of Portfolio Management* 46(1), 38–51. <https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3283395> — *recalled, not verified*
[^harvey18]: Harvey, Hoyle, Korgaonkar, Rattray, Sargaison & Van Hemert (2018), "The Impact of Volatility Targeting", *JPM* 45(1), 14–33. <https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3175538> — *recalled, not verified*
[^bsc]: Barroso & Santa-Clara (2015), "Momentum has its moments", *JFE* 116(1), 111–120. <https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2041429>
[^grinold]: Grinold (1989), "The Fundamental Law of Active Management", *Journal of Portfolio Management* 15(3), 30–37. <https://www.pm-research.com/content/iijpormgmt/15/3/30> — *recalled, not verified (paywalled); formula restated verbatim in the two sources below*
[^cdt]: Clarke, de Silva & Thorley (2002), *Financial Analysts Journal* 58(5), 48–66, as restated and quoted in Zhou, "The Fundamental Law of Active Management: Redux". <https://math.nyu.edu/inmemoriam/avellaneda/FundamentalLawFT.pdf>
[^cds]: Clarke, de Silva & Sapra (2004), "Toward More Information-Efficient Portfolios", *JPM* Fall 2004, 54–63. <https://www.hillsdaleinv.com/uploads/Toward_More_Information-Efficient_Portfolios,_Roger_G._Clarke,_Harindra_de_Silva,_Steven_Sapra,_The_Journal_of_Portfolio_Management,_Fall_2004,_Pages_54-63.pdf>
[^buckle]: Buckle (2004), "How to calculate breadth: An evolution of the fundamental law of active portfolio management", *Journal of Asset Management* 4(6), 393–405. <https://link.springer.com/article/10.1057/palgrave.jam.2240118> — *recalled, not verified (paywalled); the expression is the standard equicorrelated effective-sample-size formula and is checkable independently*
[^sneddon]: Sneddon (2020), "Strategy Design and the Fallacies of Breadth", *Journal of Asset Management* 21, 626–635; Northfield webinar deck, March 2021. <https://www.northinfo.com/Documents/989.pdf>
[^gkic]: Grinold & Kahn, *Active Portfolio Management*, ch. 10 (Forecasting), as reproduced in Yan's chapter study notes. <https://people.brandeis.edu/~yanzp/Study%20Notes/Active%20Portfolio%20Management.pdf>
[^gkbt]: Grinold & Kahn, *Active Portfolio Management*, ch. 15 (Benchmark Timing), same source.
[^qh]: Qian & Hua, "Active Risk and Information Ratio", *Journal of Investment Management*. <https://www.panagora.com/assets/JOIM-Active-Risk-and-Information-Ratio.pdf>
[^cw]: Clark & West (2007), "Approximately normal tests for equal predictive accuracy in nested models", *Journal of Econometrics* 138(1), 291–311, equations (2.1) and (3.15). <https://www.ecb.europa.eu/events/pdf/conferences/ftworkshop05/Clark_West.pdf>
