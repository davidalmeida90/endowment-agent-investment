# Macro desk

**Ashcroft University Endowment, tactical asset allocation study**
Allocation as at 30 June 2026. Paper written 28 July 2026.
Deliverables: `taa/regime.py`, `outputs/macro/`, `tests/check_macro.py`.

This desk derives its allocation from the regime and from what is already
priced. It does not fit an optimiser, build a statistical signal or take a
weight from a z-score. The Quantitative desk does that, at the same moment, on
the same mandate, and neither desk has seen the other's work. What follows is a
judgement, written so that each piece of it can be shown wrong.

---

## 1. The regime read and the rule that produces it

At 30 June 2026 the read is **overheat**: growth `expansion`, inflation
`above_target`, policy `neutral`, liquidity `ample`.

The classification rule is mechanical and is stated in full in the docstring of
`taa/regime.py`. In summary, four axes are scored from indicators a macro desk
watches, each read point in time.

**Growth.** Five indicators, each scored (1), 0 or +1, summed to a score in
[(5), +4]. Real GDP annualised quarter on quarter above 2.0% scores +1 and below
zero scores (1). Payroll growth averaging above 150k a month over three months
scores +1 and below zero scores (1). A Sahm gap, the three-month mean
unemployment rate less its lowest three-month mean of the prior year, below
0.20pp scores +1 and at or above 0.50pp scores (1). Industrial production above
1.5% year on year scores +1 and below (1.5)% scores (1). A technical recession,
meaning the two most recent published quarters are both negative on this
vintage, scores (1) and cannot score positive. A score of 2 or more is
`expansion`, 0 to 1 is `slowdown`, (2) to (1) is `stall`, (3) or below is
`contraction`.

**Inflation.** Core PCE year on year against the 2% target: 3.5% or above is
`high`, 2.8% to 3.5% is `above_target`, 2.0% to 2.8% is `at_target`, below 2.0%
is `below_target`. The bucket then moves one notch on direction. Core PCE three
month annualised more than 0.50pp below the year on year rate demotes it, more
than 0.50pp above promotes it.

**Policy.** Three indicators summed to a score in [(3), +3], where positive
means restrictive. Real ten year yield above 1.5% scores +1 and below 0.5%
scores (1). A ten year less three month curve below zero scores +1 and above
1.0% scores (1). A real policy rate, the three month bill less core PCE year on
year, above 1.0% scores +1 and below zero scores (1). Two or more is
`restrictive`, 0 to 1 is `neutral`, (1) or below is `accommodative`. Direction
comes from the two year less the three month: below (0.25) is `easing_priced`,
above +0.25 is `tightening_priced`.

**Liquidity.** Four indicators averaged over those available. The Moody's Baa
spread percentile against its own trailing ten years, the high yield OAS
percentile against its available history, the VIX, and the twelve month change
in the broad dollar. Below the 33rd percentile, below 18 on the VIX, and a
dollar down more than 2% each score +1. A mean of 0.5 or more is `ample`, down
to `stressed` at (0.5) or below.

**The name.** Growth crossed with inflation, with inflation `high` or
`above_target` treated as hot.

| growth | inflation hot | inflation cool |
|---|---|---|
| expansion | overheat | goldilocks |
| slowdown | stagflation_risk | soft_landing |
| stall or contraction | stagflation | disinflationary_slump |

A `financial_stress` override applies when the VIX exceeds 35 and the credit
percentile exceeds the 90th. It does not fire at any of the twenty meeting
dates. The highest VIX at a quarter end in this window is 31.62, on 30 September
2022. Liquidity does not otherwise enter the regime name, because an axis wide
enough to rename the regime whenever volatility rises would swallow the
distinction between an overheat and a slump at exactly the moment that
distinction matters.

### The inputs behind the current read

| Input | 30 Jun 2026 | Observation | 28 Jul 2026 |
|---|---:|---|---:|
| Real GDP, annualised QoQ | 2.09% | 2026 Q1 | 2.09% |
| Payrolls, 3m average | 188.3k | May 2026 | 111.3k |
| Unemployment rate | 4.3% | May 2026 | 4.2% |
| Sahm gap | 0.10pp | May 2026 | 0.07pp |
| Industrial production, YoY | 1.67% | May 2026 | 1.14% |
| Core PCE, YoY | 3.41% | May 2026 | 3.41% |
| Core PCE, 3m annualised | 3.52% | May 2026 | 3.52% |
| CPI, YoY | 4.27% | May 2026 | 3.73% |
| 3m bill | 3.87% | 30 Jun | 3.96% |
| 2y | 4.14% | 30 Jun | 4.31% |
| 10y | 4.44% | 30 Jun | 4.65% |
| Real 10y (DFII10) | 2.20% | 30 Jun | 2.44% |
| 10y breakeven (T10YIE) | 2.24% | 30 Jun | 2.20% |
| Real policy rate | 0.46% | derived | 0.55% |
| 10y less 2y | +0.30 | 30 Jun | +0.34 |
| 10y less 3m | +0.57 | 30 Jun | +0.69 |
| 2y less 3m | +0.27 | 30 Jun | +0.35 |
| IG OAS | 0.76% | 29 Jun | 0.81% |
| HY OAS | 2.80% (17th pctile) | 29 Jun | 2.81% (21st pctile) |
| Baa spread | 7th pctile | 29 Jun | 11th pctile |
| VIX | 16.45 | 30 Jun | 18.67 |
| Broad dollar, 12m | +1.08% | 30 Jun | +0.96% |

CPI year on year is computed from CPIAUCSL, which is seasonally adjusted,
because that is the series registered and vintaged in this study. The published
headline for June 2026 on the unadjusted index was 3.5%
[VERIFIED: computed from BLS series CUUR0000SA0, June 2026 333.952 against June
2025 322.561]. The 3.73% above is therefore not the printed headline and should
not be quoted as one.

Two things stand out. The real policy rate is 0.46% at 30 June and 0.55% at the
report date. Against the FOMC's own longer run dot of 3.1% nominal and a 2%
target, implying roughly 1.1% real, the stance is neutral at best. And growth is
softer at the report date than at the allocation date: the payroll three month
average falls from 188k to 111k once the June print enters, and the growth score
falls from 4 to 2. The regime name is unchanged. One further weak payroll print
takes the score to 1 and the name to `stagflation_risk`.

### The path, all twenty meetings

`outputs/macro/macro_path.json` carries the full read, tilt and weights at each
date. The regime sequence is:

| | | | |
|---|---|---|---|
| 2021-09-30 overheat | 2022-09-30 stagflation_risk | 2023-09-30 overheat | 2024-09-30 soft_landing |
| 2021-12-31 overheat | 2022-12-31 overheat | 2023-12-31 goldilocks | 2024-12-31 overheat |
| 2022-03-31 overheat | 2023-03-31 overheat | 2024-03-31 overheat | 2025-03-31 overheat |
| 2022-06-30 overheat | 2023-06-30 overheat | 2024-06-30 soft_landing | 2025-06-30 disinflationary_slump |
| 2025-09-30 overheat | 2025-12-31 overheat | 2026-03-31 stagflation_risk | 2026-06-30 overheat |

The window is overheat-heavy because core PCE sat above 2.8% for most of it.
That is a property of the period rather than of the framework.

---

## 2. The 2022 Q2 demonstration

`outputs/macro/gdp_vintage_demo.json`. Twenty-seven vintages, every committee
date plus six BEA release dates on which this study asserts a specific published
figure.

A quarter-end vintage cannot show what a release said on the day it landed. The
committee calendar is the set of dates on which this study forms a view, and it
is not the set of dates on which it makes a claim about what was published. The
BEA advance estimate for 2022 Q2 landed on Thursday 28 July 2022, between the
30 June and 30 September vintages. Six release-date vintages were therefore
added to the ingestion layer as `CLAIM_VINTAGES` in `taa/datapull.py`. The
addition is additive: `pitdata` takes the latest vintage at or before the as-of
date and none of the six falls between a meeting date and that meeting's own
vintage, so no committee-date read changes.

| Vintage | Release | 2022 Q1 | 2022 Q2 | Two negative quarters |
|---|---|---:|---:|---|
| 2022-04-28 | Q1 advance | (1.4141)% | not yet published | |
| 2022-06-30 | quarter end | (1.5734)% | not yet published | |
| **2022-07-28** | **Q2 advance** | **(1.5734)%** | **(0.9342)%** | **yes** |
| 2022-08-25 | Q2 second | (1.5734)% | (0.5757)% | yes |
| 2022-09-29 | Q2 third, 2022 annual update | (1.6313)% | (0.5773)% | yes |
| 2023-09-30 | after 2023 annual update | (1.9759)% | (0.5639)% | yes |
| 2024-09-25 | day before annual update | (1.9759)% | (0.5639)% | yes |
| **2024-09-26** | **2024 annual update** | **(1.0258)%** | **+0.2810%** | **no** |
| 2025-09-30 | after 2025 update | (1.0153)% | +0.6277% | no |
| **2026-07-28** | **today** | **(1.0153)%** | **+0.6277%** | **no** |

**The numbers.** US real GDP for 2022 Q2 was first published at **(0.93)%
annualised** on the 28 July 2022 vintage. It reads **+0.63% annualised** today.
The revision is **+1.5619 percentage points**. The sign crossed zero on the
**26 September 2024** vintage, the BEA annual update of the national accounts,
**791 days** after the advance print. The 25 September 2024 vintage still reads
(0.5639)%, which pins the crossing to that single release rather than to a
quarter.

The Chief Investment Officer ran this independently through the look-ahead suite
and obtained (0.93)% against +0.63%. The two computations agree.

**2022 Q1 and the two-quarter question.** On 28 July 2022, Q1 read (1.5734)% and
Q2 read (0.9342)%. Two consecutive negative quarters, which is the popular
technical-recession heuristic, was **true** as it stood that day, and remained
true on every vintage until 25 September 2024. It is **false** today, because Q2
is positive, although Q1 remains negative at (1.0153)%. The NBER has never dated
a recession beginning in 2022; USREC reads 0 throughout 2021 and 2022 on the
current vintage. The heuristic and the NBER's dating disagreed then and
disagree now.

**Why growth rates and not levels.** The chained-dollar level for 2022 Q2 moved
from 19,895.271 on the 2022-07-28 vintage to 21,967.045 today. Almost all of
that is the rebasing of the chained index from 2012 to 2017 dollars, not a
revision to activity. A level comparison across a rebasing measures the
rebasing.

### What it would have cost

`outputs/macro/counterfactual.json` recomputes the 30 September 2022 read with
the GDP input taken from today's vintage and every other input left at its point
in time value, so the difference is attributable to the GDP revision alone. This
is an anachronism on purpose, computed so the Committee can see the size of the
error rather than be told it is large.

| | Point in time | Current vintage |
|---|---|---|
| 2022 Q2 annualised | (0.577)% | +0.628% |
| 2022 Q1 annualised | (1.631)% | (1.015)% |
| Technical recession | true | false |
| Growth score | 1 | 3 |
| Growth | slowdown | expansion |
| **Regime** | **stagflation_risk** | **overheat** |

The regime name changes and the portfolio changes with it: high yield 3.0%
against 5.0%, Treasury duration 7.5% against 5.5%, investment grade 8.0% against
7.0%, developed ex-US 19.0% against 20.0%. Seven percentage points of gross
difference. A desk backtesting off current values would have carried two extra
points of high yield and two fewer of duration into the autumn of 2022, the
period in which the Moody's Baa spread reached the 47.6th percentile of its own
trailing decade, the highest reading at any of the twenty meeting dates. The
high yield OAS itself cannot be quoted for that period, since the free endpoint
serves only a rolling three-year window and the series does not reach back to
2022. The desk would have carried that position for 791 days, and its backtest
would have shown it was right to.

---

## 3. What is already priced

`outputs/macro/priced.json`. Every figure below is from observable prices read
through `pitdata`. Assumptions are named at the value they produce.

**The policy path.** At 30 June the three month bill is 3.87% and the two year
is 4.14%. Assuming the overnight rate travels linearly from the spot bill to a
terminal level over two years, so that the two year yield is the mean of that
path, the implied terminal rate is **4.41%**, which is **54bp of tightening**
priced over two years. At the report date the bill is 3.96% and the two year
4.31%, implying a terminal of **4.66%** and **70bp**. The eight year rate
beginning in two years, from the two year and the ten year, is 4.515% at 30 June
and 4.735% at the report date. The linear-path assumption is crude and is the
only thing standing between three yields and a path; it is stated for that
reason.

The three month bill at 3.96% sits 33bp above the 3.625% fed funds target
midpoint. A bill market does not carry that into a meeting it expects to be
uneventful.

**Inflation compensation.** The ten year breakeven is 2.24% at 30 June and 2.20%
at the report date. The ten year real yield is 2.20% and 2.44%. Between those two
dates the market simultaneously priced more Fed tightening and less long-run
inflation. That combination is a market expressing confidence that the Fed
succeeds.

**Credit.** On the standard decomposition, OAS equals the expected default rate
times one less recovery, plus whatever premium the buyer demands for illiquidity
and volatility. Assuming 40% recovery, a high yield OAS of 2.81% implies a
**4.68% annual default rate** if the buyer demands no premium at all, which
upper-bounds the implied default rate since any premium comes out of it. At 45%
recovery an investment grade OAS of 0.81% implies 1.47% on the same basis, which
is far above any plausible investment grade default rate and confirms that
almost the whole investment grade spread is premium rather than expected loss.
Against a long-run US high yield default rate near 3.5% [RECALLED, Moody's
long-run average, not verified in this session] the expected loss is roughly
210bp, leaving about 70bp of the 281bp spread for everything else.

**Equity.** A clean forward earnings yield needs a consensus estimate feed behind
a subscription, which IPS 4.4 puts out of scope by design. Instead the trailing
twelve month dividend yield is backed out of the divergence between SPY's
adjusted and unadjusted closes, which is the only route to a yield from price
data alone. That gives 1.108% at 30 June. A Gordon construction, expected real
return equals dividend yield plus assumed real growth of 2.0%, less the ten year
TIPS yield, gives an equity risk premium proxy of **0.91%** at 30 June and
**0.67%** at the report date.

The level is understated by construction, because an index that returns most of
its cash through buybacks has a total shareholder yield well above its dividend
yield. Only the direction carries information, and the direction is stark:

| | Sep 2021 | Sep 2022 | Dec 2023 | Dec 2024 | Jun 2026 |
|---|---:|---:|---:|---:|---:|
| Dividend yield | 1.41% | 1.51% | 1.52% | 1.28% | 1.11% |
| Real 10y | (0.85)% | 1.68% | 1.72% | 2.24% | 2.20% |
| ERP proxy | 4.26% | 1.83% | 1.80% | 1.04% | **0.91%** |

The proxy is at its lowest of the twenty meeting dates. The whole of the decline
is the real yield rising while the dividend yield fell.

**Consensus forecasts.** All retrieved this session.

| | 2026 | 2027 | Source |
|---|---|---|---|
| SPF median real GDP | 2.2% | 1.9% | [VERIFIED: SPF Q2 2026, released 15 May 2026] |
| SPF median unemployment | 4.4% | 4.5% | same |
| SPF median core PCE, Q4/Q4 | 3.3% | 2.4% | same |
| SPF median headline CPI, Q4/Q4 | 3.5% | 2.5% | same |
| SPF 10-year CPI, annual average | 2.40% | | same |
| FOMC SEP median real GDP | 2.2% | 2.3% | [VERIFIED: SEP, 17 June 2026] |
| FOMC SEP median core PCE | 3.3% | 2.5% | same |
| FOMC SEP median fed funds dot | 3.8% | 3.6% | same, longer run 3.1% |
| Atlanta Fed GDPNow, 2026 Q2 | 1.6% | | [VERIFIED: as of 27 July 2026] |
| NY Fed SCE median, 3y / 5y | 3.3% / 3.0% | | [VERIFIED: June 2026, released 7 July 2026] |
| NY Fed dealer modal funds path | 3.63% through Mar 2027 | | [VERIFIED: SME June 2026] |

URLs are carried in `outputs/macro/deviations.json`.

Two features of the consensus are worth isolating. The FOMC's end-2026 median
dot of 3.8% sits above the current 3.625% midpoint, so the median participant
projects a tightening, a 40bp upward revision from March driven by the PCE
inflation median rising from 2.7% to 3.6%. And the dealer modal path shows no
change at all through March 2027. Consensus is split, and the split runs between
the committee and the sell side.

---

## 4. Deviations from consensus, with falsifiers

`outputs/macro/deviations.json` carries the full entries, each with its consensus
source URL and the strongest argument against it. IPS 4.4 requires that a view
which cannot be shown wrong does not enter a recommendation.

| # | View | Consensus | Falsifier | Known by | Size |
|---|---|---|---|---|---|
| D1 | Core PCE three month annualised stays at or above 3.0% through the November 2026 reference month | SPF core PCE 2.4% Q4/Q4 2027, FOMC 2.5%, both requiring the run rate through 3% inside two quarters | Core PCE three month annualised, from PCEPILFE, prints below 3.0% in the BEA release covering November 2026 data | 2026-12-31 | 500bp commodities |
| D2 | The ten year breakeven rises to 2.45% or above within twelve months | The market at 2.20%; the SPF's own ten year CPI median is 2.40% and households say 3.0% over five years | T10YIE fails to close at or above 2.45% on any day before 30 June 2027 | 2027-06-30 | 650bp duration |
| D3 | The FOMC delivers at least one further tightening | NY Fed dealer modal midpoint 3.63% at every meeting through March 2027, 9% probability on a July hike. The FOMC's own 3.8% dot is on this desk's side | The fed funds target range is still 3.50-3.75% or lower immediately after the March 2027 meeting | 2027-03-31 | 700bp cash |
| D4 | High yield OAS trades above 4.00% at some point within twelve months | The market at 2.81%, the 21st percentile of available history, while the SPF puts a 25% probability on a negative quarter in 2026 Q3 | BAMLH0A0HYM2 fails to close at or above 4.00% on any day before 30 June 2027 | 2027-06-30 | 150bp high yield |
| D5 | No deviation on growth. The trim rests on the price of the entry | SPF 2.2% and FOMC 2.2% for 2026, GDPNow 1.6% for Q2. This desk accepts all three | The ERP proxy rises above 1.50% before 30 June 2027 | 2027-06-30 | 200bp US equity |

The thread running through D1, D2 and D3 is one proposition: a real policy rate
of roughly 0.5% is not restrictive, so the disinflation consensus expects has to
arrive without help from the Fed. If that proposition is wrong, all three
positions are wrong together, and the desk is not running three independent bets.
The Committee should size it as one.

The strongest argument against the whole structure is in D1. Core PCE at 3.41%
is running roughly 80bp above core CPI at 2.6% for June 2026. Core PCE normally
prints below core CPI on weighting and the treatment of shelter, so this is a
110bp anomaly against the usual relationship. If it is an artifact concentrated
in imputed categories such as medical care and financial services, it closes by
core PCE falling toward core CPI, consensus is right, and this desk is wrong for
a reason it has not priced. Both figures are from the respective statistical
agencies, so the inversion is a real feature of the data rather than a
transcription error.

---

## 5. The allocation, 30 June 2026

`outputs/macro/allocation.json`. Long only, sums to one, inside every range.

| Line | Policy | Weight | Active | Conviction |
|---|---:|---:|---:|---|
| US equity | 38.00% | 36.00% | (2.00) | medium |
| Developed ex-US | 20.00% | 20.00% | 0.00 | none |
| Emerging markets | 12.00% | 11.00% | (1.00) | low |
| US Treasury duration | 12.00% | 5.50% | (6.50) | high |
| US investment grade | 8.00% | 7.00% | (1.00) | low |
| US high yield | 5.00% | 3.50% | (1.50) | medium |
| Commodities | 3.00% | 8.00% | +5.00 | high |
| Listed real estate | 2.00% | 2.00% | 0.00 | none |
| T-bills | 0.00% | 7.00% | +7.00 | high |

Equity sleeve 67.0% against a 60% to 80% band. Fixed income 16.0% against 15% to
35%. Real assets 10.0% against 0% to 10%.

**The binding constraint is the commodity line cap at 8%.** The view wanted more
commodity exposure than the mandate permits. The real assets sleeve then sits at
exactly its 10% cap as a consequence, so the two bind at the same point and the
sleeve cap would have bound had the line cap not. Fixed income at 16.0% is
within 1pp of its 15% floor, which means a further duration cut is not available
without selling investment grade or high yield.

**Listed real estate is untraded.** The rule wanted +0.38pp, which is below the
50bp minimum trade size in IPS 4.2, so the line is held at policy and the
position is recorded in `untraded_below_min_trade`. Developed ex-US is at policy
because this desk has no view on it. A desk with a view on all nine lines has a
view on none of them.

**Tracking error is not computed here.** Ex-ante tracking error requires a
covariance matrix, which is a risk model, which is the Quantitative desk's
instrument. If this tilt breaches the 200bp budget it is truncated to the
constraint under IPS 3.6 rank 4, by the mandate rather than by argument. The
Chief Investment Officer measures it at reconciliation.

**How the tilt was produced.** The base table for `overheat` gives US equity
(2.0), emerging markets (1.0), duration (3.0), investment grade (1.0),
commodities +4.0, listed real estate +0.5 and cash +2.5. Three modifiers fired,
each stated in `taa/regime.py` and each summing to zero:
`policy_loose_tightening_priced` (duration (2.0), cash +2.0),
`credit_rich` (high yield (1.5), cash +1.5) and
`breakeven_below_core` (commodities +1.5, duration (1.5)). The result was then
projected onto the mandate's ranges, which clipped commodities to 8% and returned
the excess to cash, and any position under 50bp was set to zero.

The same table produces the tilt at all twenty meeting dates in
`outputs/macro/macro_path.json`, so the Committee can reconstruct the five year
record without hindsight.

---

## 6. Limitations, stated at the decision

**No anachronism enters the regime read.** `pitdata.static()` was not called.
Every input at every one of the twenty dates comes from the vintage current at
that date. The single deliberate anachronism in this desk's work is
`vintage_counterfactual()`, which exists precisely to measure an anachronism and
is labelled as one in its own output.

**The credit gap.** The ICE BofA OAS series reach this study through the free
FRED endpoint, which serves a rolling three-year window. They begin 31 July 2023,
two years after the study window opens. At the eight meeting dates from
30 September 2021 to 30 June 2023 the high yield OAS indicator does not exist,
the liquidity mean is taken over three indicators rather than four, and those
dates carry `oas_available: false` and `liquidity_n_indicators: 3`. Nothing is
interpolated across the gap. The Moody's Baa spread used in its place is a yield
spread over the Treasury curve rather than an option-adjusted spread; its level
is not comparable to an OAS and it is used on percentile rather than on level for
that reason. Those eight quarters have less evidence behind them than the twelve
that follow, and the record should be read that way.

**Thin percentile history.** The high yield percentile at recent dates is
computed against roughly three years of history that is itself entirely a
tight-spread regime, which makes it close to uninformative about the level. D4
rests on that percentile and is weaker for it.

**The dividend yield proxy.** Understated by construction for an index that
distributes through buybacks. Only its direction is used.

**CPI basis.** CPIAUCSL is seasonally adjusted and its year on year rate differs
from the published unadjusted headline. The figures in this paper are on the
seasonally adjusted series and are labelled where they appear.

---

## 7. Check output

`py -3 tests/check_macro.py`

```
==============================================================================
MACRO DESK CHECK — Ashcroft University Endowment
window 2021-07-01 .. 2026-06-30   report date 2026-07-28   20 meetings
==============================================================================

1. LOOK-AHEAD  no input dated after its own meeting date
   2021-09-30   30 dated fields  newest  0d before, oldest  182d before  ok
   2021-12-31   30 dated fields  newest  0d before, oldest  183d before  ok
   2022-03-31   30 dated fields  newest  0d before, oldest  181d before  ok
   2022-06-30   30 dated fields  newest  0d before, oldest  180d before  ok
   2022-09-30   30 dated fields  newest  0d before, oldest  182d before  ok
   2022-12-31   30 dated fields  newest  1d before, oldest  183d before  ok
   2023-03-31   30 dated fields  newest  0d before, oldest  181d before  ok
   2023-06-30   30 dated fields  newest  0d before, oldest  180d before  ok
   2023-09-30   32 dated fields  newest  1d before, oldest  182d before  ok
   2023-12-31   32 dated fields  newest  2d before, oldest  183d before  ok
   2024-03-31   32 dated fields  newest  2d before, oldest  182d before  ok
   2024-06-30   32 dated fields  newest  2d before, oldest  181d before  ok
   2024-09-30   32 dated fields  newest  0d before, oldest  182d before  ok
   2024-12-31   32 dated fields  newest  0d before, oldest  183d before  ok
   2025-03-31   32 dated fields  newest  0d before, oldest  181d before  ok
   2025-06-30   32 dated fields  newest  0d before, oldest  180d before  ok
   2025-09-30   32 dated fields  newest  0d before, oldest  182d before  ok
   2025-12-31   32 dated fields  newest  0d before, oldest  183d before  ok
   2026-03-31   32 dated fields  newest  0d before, oldest  181d before  ok
   2026-06-30   32 dated fields  newest  0d before, oldest  180d before  ok
   tightest margin: 2021-09-30, newest observation 0 days before the meeting

2. 2022 Q2 GDP VINTAGE DEMONSTRATION
   2022-07-28 vintage (BEA advance estimate) -0.9342% annualised
   2026-07-28 vintage (today)          +0.6277% annualised
   revision +1.5619pp, sign crossed on the 2024-09-26 vintage after 791 days
   two consecutive negative quarters: True then, False now

3. FALSIFIERS  every deviation can be shown wrong, by a date still ahead
   D1 commodities    2026-12-31    500bps  ok  Core PCE three-month annualised...
   D2 ust_duration   2027-06-30    650bps  ok  T10YIE fails to close at or above 2.45%...
   D3 cash           2027-03-31    700bps  ok  The fed funds target range is still 3.50-3.75%...
   D4 us_hy          2027-06-30    150bps  ok  BAMLH0A0HYM2 fails to close at or above 4.00%...
   D5 us_equity      2027-06-30    200bps  ok  The proxy, computed as SPY trailing dividend yield...

4. MANDATE  ranges, sleeves, long only, sums to one, minimum trade
   20 dates, all lines inside RANGE, all sleeves inside SLEEVE_RANGE
   equity sleeve spans 63.5% to 76.0% against a 60%-80% band
   every active position is zero or at least 0.5pp

==============================================================================
PASS  688 assertions, 0 failures
==============================================================================
```

`py -3 tests/check_macro.py --demo-fail`

```
  CAUGHT  look-ahead, an input dated after its meeting
  CAUGHT  2022 Q2 sign change absent
  CAUGHT  empty falsifier, past date, no URL
  CAUGHT  weights outside RANGE and short
==============================================================================
DEMO-FAIL PASS (4/4 corruptions rejected)
```

The office-wide `tests/test_lookahead.py` passes 12 of 12 and independently
reports the 2022 Q2 sign flip at (0.93)% against +0.63%.

---

## 8. What would change this desk's mind

The June payroll print has already taken the growth score from 4 to 2. A second
soft print takes it to 1, the growth read to `slowdown`, and the regime to
`stagflation_risk`, which cuts equity a further 2pp and high yield a further 2pp
rather than adding to commodities. The June PCE release and the 2026 Q2 advance
GDP estimate both land on 30 July 2026, and the FOMC decides on 29 July. Three
observations inside three days, any of which can move the read. The allocation
above is dated 30 June and is what the Committee would have had in front of it
then. The desk's own view at the report date is the same in name and weaker
underneath.
