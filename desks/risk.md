# Risk function

**Compliance testing of proposed allocations**
Ashcroft University Endowment · 28 July 2026 · IPS Version 7.2

---

## What this desk is for

IPS Section 2.1 gives the risk function nothing to determine and no allocation
authority. It executes compliance testing of every proposed allocation and it
monitors every proposal and the portfolio continuously. The Statement is
explicit about why:

> "The separation is deliberate. The risk function does not advise on allocation
> and does not compete with the Chief Investment Officer for influence over it.
> It applies the constraints in this Statement and returns a pass or a fail. An
> allocation that fails does not proceed to the Committee. The remedy is a
> different allocation or an amendment to this Statement, and never an
> adjustment to the test."

This paper therefore contains no view on weights. It documents a test, shows the
test rejecting thirteen allocations, shows it passing the Board's own policy
portfolio, and says what it does not catch.

The test is `taa/compliance.py`. Its assertions are `tests/test_compliance.py`.
Its output on every case is `outputs/compliance_demo.json`.

Every limit is imported from `taa/config.py`, which transcribes the Statement.
No limit is written down twice, because a limit that appears twice is a limit
that can disagree with itself. Historical data is read through `taa/pitdata.py`
with an as-of date, which is the only sanctioned path under IPS 4.4.

---

## 1. The constraint set

Seventeen checks. The rank column is the pre-committed hierarchy at IPS 3.6.
Checks without a rank are not absent from the Statement; they sit outside the
hierarchy because the hierarchy exists to resolve conflicts between the five
constraints it names, and a permitted range does not conflict with anything, it
simply binds.

| # | Check | IPS | Rank | Standing | What it tests |
|---|---|---|---|---|---|
| 1 | `structural_keys` | 4.1 | . | structural | All nine mandate lines present, nothing outside the opportunity set |
| 2 | `structural_finite` | 4.1 | . | structural | No NaN, no infinity |
| 3 | `structural_sum` | 4.1 | . | structural | Weights sum to one |
| 4 | `liquidity_floor` | 3.4 | **1** | not negotiable | 15% of NAV realisable within five business days |
| 5 | `liquidity_distribution` | 3.4 | **1** | not negotiable | The quarterly draw funds without a forced sale |
| 6 | `leverage_gross` | 3.5 | **2** | not negotiable | Gross exposure does not exceed NAV |
| 7 | `leverage_short` | 3.5 | **2** | not negotiable | No negative weight, since a short is leverage at fund level |
| 8 | `board_exclusions` | 3.5 | **2** | not negotiable | Tobacco and thermal coal, assessed at the vehicle level |
| 9 | `drawdown_realised` | 3.3 | **3** | hard | Worst realised peak to trough against (20.00%) |
| 10 | `drawdown_ex_ante` | 3.3 | **3** | hard | Modelled maximum drawdown of the proposal |
| 11 | `drawdown_stress` | 3.3 | **3** | hard, advisory | Replay through named historical episodes |
| 12 | `tracking_error` | 4.2 | **4** | hard | 200bps ex ante against the policy portfolio |
| 13 | `line_range` | 4.1 | . | binds | Every line inside its permitted range |
| 14 | `sleeve_range` | 4.1 | . | binds | Equity 60 to 80, fixed income 15 to 35, real assets 0 to 10 |
| 15 | `min_trade` | 4.2 | . | binds | No proposed change strictly between zero and 50bps |
| 16 | `corridor_width` | 4.5 | . | advisory | No corridor narrower than the minimum trade |
| 17 | `investable_date` | 4.1 | . | binds | No weight on a line before its vehicle existed |

### Five outcomes, not two

A pass and a fail are not sufficient, because IPS 3.5 asks for a third thing by
name and honest bookkeeping asks for two more.

**PASS-WITH-DISCLOSURE** exists because IPS 3.5 says a broad index vehicle
carrying incidental excluded exposure is "disclosed rather than deemed compliant
by silence". Silence is not one of the permitted answers, so the test carries an
outcome that is a pass and still obliges text to appear in the report.

**NOT ASSESSED** is recorded when a required input was withheld. On a gating
check it counts as a failure. A risk function that cannot measure the
tracking-error budget must not certify compliance with it. Absence of evidence
is not evidence of compliance, and the alternative, treating an untested
constraint as satisfied, is the single most common way a compliance system comes
to mean nothing.

**NOT APPLICABLE** is recorded when the input does not exist for this class of
proposal. A forward-looking allocation has no realised NAV path. This counts as
a pass.

### Gating and advisory

A check gates the verdict when it tests a property of the allocation, because
IPS 2.1 says the remedy for a failure is a different allocation. A check is
advisory when it tests the machinery around the allocation, since no different
allocation could cure it and a veto would therefore be a veto of every
allocation equally. Two checks are advisory, `corridor_width` and
`drawdown_stress`, and both are argued below. An advisory result never becomes a
silent pass: it prints in the table with its own status and repeats under
QUALIFICATIONS, so every certificate carries the list of what was tested weakly
or not at all.

---

## 2. The ex-ante drawdown method

IPS 3.3 sets a (20.00%) peak-to-trough limit. That limit is on realised drawdown, on
"the value of the pool". An ex-ante number is a model output and this paper
treats it as one throughout.

### The two estimates

**Parametric, and this is the gating one.** Portfolio volatility is
`sqrt(w' Σ w)` from the supplied annualised covariance. The maximum drawdown of
the log price path is then modelled as that of a driftless Brownian motion over
one year, and the test reads the **95th percentile**, not the mean, because the
mandate limit is a ceiling on an outcome and a portfolio whose average drawdown
sits inside the limit can breach it routinely. The expected maximum drawdown is
reported alongside from the closed form `sqrt(pi/2) · σ · sqrt(T)` of
Magdon-Ismail, Atiya, Pratap and Abu-Mostafa (2004). Both are converted from the
log measure to a price fraction by `1 - exp(-d)`.

Three choices, each defensible and each arguable:

- **Horizon one year**, from IPS 4.5, which resets the portfolio to policy at
  least annually, and IPS 4.3, which reports to the Board annually.
- **Zero drift**, which is conservative and deliberate. Adding the mandate's
  8.10% required return moves the policy portfolio's figure from (21.60%) to
  (15.52%), which is a very large effect and exactly the direction an optimistic
  model would push. The figure is reported in the check detail so that the cost
  of the choice is visible rather than assumed away.
- **Fixed seed**, 20260728, with 20,000 paths. Driftlessness makes the log path
  scale exactly in sigma, so one simulation serves every portfolio and the answer
  does not move between runs. A compliance test that returns a different verdict
  on a different seed is not a compliance test.

**Historical stress replay.** The proposed weights are held unchanged, buy and
hold, through named episodes dated on the peak and trough of the S&P 500, using
daily total-return prices read point in time. Buy and hold rather than daily
rebalancing, because that is what holding the allocation through the episode
means, and rebalancing would credit the portfolio with a policy the proposal
does not contain.

### The weakness, stated plainly

The parametric estimate assumes Gaussian, independent, identically distributed
returns with a stable covariance. Real returns are none of those things. They
are fat-tailed, they cluster in volatility, and correlations rise toward one in
exactly the episodes the limit exists to survive. The estimate therefore
**understates** the tail it is meant to bound. It also inherits every weakness
of Σ, which the Quantitative desk supplies and this desk does not audit, so the
rank 3 constraint is only as good as the rank 4 input.

The stress replay has the opposite weakness. It is an empirical read of five
specific paths, which gives enormous weight to path-specific accident, and one
episode is missing. It is reported and it does not veto.

### The gate, and why it is not the mandate limit

Under this model the policy portfolio reads **(21.60%)** at the 95th percentile
over one year, against a mandate limit of (20.00%). The Board's own benchmark is
beyond the Board's own limit.

That is not a modelling failure. IPS 3.3 says so in advance:

> "These two are in tension by construction, and the tension is not an oversight.
> An 8.10% required return implies substantial equity risk. A −20% drawdown limit
> alongside an 18% budget dependency implies materially less."

An absolute gate at (20.00%) would therefore reject the policy portfolio, and a
test that rejects the benchmark the same Statement requires the portfolio to be
measured against rejects everything and tests nothing. The gate is therefore the
**more permissive of the mandate limit and the same model's reading of
`config.POLICY`**. No constant is introduced; both terms are mandate objects. The
check names which term is binding, and when the policy term binds it raises the
finding as an IPS 2.3 amendment question rather than absorbing it in the
portfolio.

**This is the most questionable design decision in the module and it is stated
here rather than buried.** When the policy term binds, the effective gate becomes
"no more drawdown exposure than the policy portfolio", which is stricter than the
Statement's words and which duplicates, in one direction, the rank 4
tracking-error budget the Board granted so that the Chief Investment Officer
could take active risk. A risk function that vetoes any increase in total
portfolio volatility has quietly awarded itself an allocation authority IPS 2.1
denies it. The alternative, an absolute gate, vetoes the mandate. Both readings
are defensible and this one was chosen because the control case must pass. A
Committee that disagrees should amend IPS 3.3 rather than ask for the gate to be
adjusted.

---

## 3. Board exclusions: what the vehicles actually hold

Evidence sits in `taa/exclusions.py`, separately from the test, so it can be
re-sourced and challenged without touching the code. Every weight was read from
the fund's own SEC Form N-PORT schedule on EDGAR, which is public and free
(IPS 4.4). Issuer sites and the commercial aggregators were blocked or
truncated, so N-PORT is the sole holdings authority.

**The policy portfolio raises nine disclosures.** Not one of them is a breach.

| Vehicle | Line | Exclusion | Of vehicle | Of NAV | Evidence |
|---|---|---|---:|---:|---|
| SPY | US equity | tobacco | 0.66% | 0.250% | verified |
| SPY | US equity | thermal coal | n/e | n/e | holding verified, materiality not |
| EFA | Developed ex-US | tobacco | 0.93% | 0.186% | verified |
| EFA | Developed ex-US | thermal coal | n/e | n/e | verified |
| EEM | Emerging markets | tobacco | 0.18% | 0.021% | verified |
| EEM | Emerging markets | thermal coal | 0.42% | 0.050% | verified |
| LQD | US investment grade | tobacco | **1.44%** | 0.115% | verified |
| LQD | US investment grade | thermal coal | n/e | n/e | holding verified, materiality not |
| HYG | US high yield | thermal coal | 1.25% | 0.063% | holding verified, materiality not |

Three things a trustee should take from this table.

**The Board's own policy portfolio cannot be certified as silently compliant
with the tobacco and thermal coal exclusions.** Every broad index vehicle in the
opportunity set except the Treasury, T-bill, commodity and real estate lines
carries incidental exposure. IPS 3.5 anticipated exactly this and requires
disclosure rather than a silent pass, which is why the control result is
PASS-WITH-DISCLOSURE and not PASS. This is a finding, not a footnote.

**The largest tobacco weight in the opportunity set is in a bond fund.** LQD
carries 1.44% across 51 bonds of Philip Morris International, BAT Capital,
Altria and Reynolds American, against 0.66% in SPY. A bond index screens on
issuance rather than on market capitalisation, and tobacco issuers are heavy
users of the USD investment grade market. This is the exposure least likely to
be anticipated by anyone looking only at equity sleeves. HYG, by contrast, holds
no tobacco paper at all, which was checked by scanning every issuer name and is
worth recording because the expectation running into the work was the opposite.

**Generation is not extraction, and the mandate does not say which it means.**
SPY holds no coal producer of any kind. It holds seventeen utilities that still
burn thermal coal. LQD holds roughly 1.2% in utility obligors in the same
position, and HYG holds 1.25% in NRG Energy and Talen Energy Supply. Whether the
Board's exclusion reaches a generator that burns coal or only an extractor that
mines it is a question about the Board's intent, and the risk function does not
decide it. Those rows are disclosed with the question attached and marked
`materiality not verified`, because what was not established is the share of
each utility's generation that is actually coal, and that is the fact that would
make the holding relevant. Resolving this is an IPS 2.3 amendment question.

Three candidates were examined and **rejected**: Anglo American and Teck, held in
EFA and VEA, are metallurgical coal rather than thermal, and Anglo agreed to sell
that business in May 2026; Vale is iron ore; Reynolds Consumer Products makes
food wrap and is unrelated to Reynolds American. Naming what was looked at and
rejected matters as much as naming what was found, because a screen that only
ever adds names is a screen nobody has audited.

---

## 4. The rejection table

Fourteen cases. One control, thirteen planted defects. Full output in
`outputs/compliance_demo.json`; reproduce with `py -3 -m tests.test_compliance`.

Covariance: `taa.pitdata` monthly returns, 203 months to 30 June 2026,
annualised. Not synthetic.

| Case | What was planted | Verdict | Rank | What the test returned |
|---|---|---|---|---|
| `policy_control` | Nothing. The Board's policy portfolio | **PASS-WITH-DISCLOSURE** | . | No breach. 9 disclosures under IPS 3.5 |
| `range_breach_inside_te` | US IG cut to 2.50% against a 3% floor, into cash | **FAIL** | . | `line_range` (0.50pp) outside. **TE 39.8bps of 200bps, PASS** |
| `te_breach_ranges_ok` | Every line at an end of its own range at once | **FAIL** | 4 | `tracking_error` 237.6bps against 200bps. Ranges and sleeves PASS |
| `negative_weight_leverage` | Cash at (5.00%), US equity 43% | **FAIL** | 2 | `leverage_gross` 1.10x against 1.00x; `leverage_short` (5.00%) |
| `liquidity_floor_breach` | Custodian reports only the T-bill line clearing same week; cash 1% | **FAIL** | 1 | `liquidity_floor` 1.00% against 15.00%; `liquidity_distribution` 1.00% against 1.12% |
| `dust_trade_30bp` | A 30bps shift from EM into US equity | **FAIL** | . | `min_trade` 0.30pp against 0.50pp. Every other constraint PASS |
| `sleeve_breach_lines_ok` | Equity sleeve 82%, every line inside its own range | **FAIL** | 3 | `sleeve_range` 2.00pp over. **`line_range` PASS** |
| `drawdown_breach` | Most drawdown-exposed allocation the ranges permit | **FAIL** | 3 | `drawdown_ex_ante` (23.78%) against a (21.60%) gate. Ranges and sleeves PASS |
| `realised_drawdown_breach` | A NAV path that fell 26% peak to trough | **FAIL** | 3 | `drawdown_realised` (26.00%) against (20.00%) |
| `direct_exclusion_breach` | Commodities line with direct thermal coal exposure | **FAIL** | 2 | `board_exclusions`, 1 direct breach against a limit of zero |
| `investable_date_breach` | Policy weights proposed as at 30 June 2005 | **FAIL** | . | `investable_date`, 2 lines held before their vehicles listed |
| `malformed_nan` | US equity set to NaN | **FAIL** | 1 | `structural_finite`, and every downstream check NOT ASSESSED |
| `weights_do_not_sum` | Weights summing to 102% | **FAIL** | 2 | `structural_sum` 102.00%; `leverage_gross` 1.02x |
| `covariance_withheld` | Policy weights, no covariance supplied | **FAIL** | 3 | `tracking_error` and `drawdown_ex_ante` NOT ASSESSED |

### The case IPS 4.1 names

> "A position inside the tracking-error budget but outside its range is a
> breach."

`range_breach_inside_te` is that case and it is planted on the **defensive**
side deliberately, so that no other constraint can be credited with the
rejection. Cutting investment grade to 2.50% and holding the proceeds in cash
lowers portfolio volatility, so both drawdown checks pass. Tracking error comes
in at **39.8bps, leaving 160.2bps of the budget unused**, and the check passes.
The range check fails on its own, and the allocation does not proceed. Had the
range been folded into the tracking-error budget, as it commonly is, this
portfolio would have been approved.

`te_breach_ranges_ok` is the mirror. Every line is legal in isolation and the
combination runs 237.6bps of tracking error. Neither check subsumes the other,
which is why the Statement sets both.

### Every check is load bearing

A suite that passes proves the code agrees with the suite. It does not prove the
suite would notice if the code stopped working. `py -3 -m tests.test_compliance
--mutate` disables one check at a time in a sandbox copy and asserts the suite
fails. **All 13 mutants died.** A surviving mutant would be a check nothing is
testing.

---

## 5. Control: the policy portfolio

**Verdict: PASS-WITH-DISCLOSURE. No gating check failed.**

The test does not reject the Board's own benchmark, which is the minimum
condition for it to be a test of proposals rather than a test of the mandate.

Binding constraints, meaning at or within a hair of their limit:

| Constraint | Slack | Why |
|---|---|---|
| `leverage_gross` | 0.00x | A fully invested long-only portfolio is always exactly at the gross exposure cap |
| `leverage_short` | 0.00% | Cash sits at zero, so the smallest weight is exactly the floor |
| `drawdown_ex_ante` | 0.00% | The policy portfolio defines its own gate, so slack is zero by construction |
| `drawdown_stress` | 0.00% | Same |
| `line_range[cash]` | 0.00pp | Policy holds no cash and cash rests on the zero floor of its 0 to 10% range |

The `line_range` entry is qualified by the line that actually binds. Reporting a
bare `line_range` would put the same word on the dashboard's which-constraint-
bound chart every quarter and mean nothing by it, since the policy portfolio
permanently rests cash on its floor. A reader should also note that a line
resting on a bound because policy puts it there is not the same event as a
constraint truncating a tactical view, and the dashboard should not count them
together.

One qualification: `corridor_width` is NOT ASSESSED because `taa.costs` does not
yet publish a corridor table. The documented fallback sets every corridor equal
to the minimum trade, which makes the comparison vacuous by construction. That
default was chosen precisely so that it cannot manufacture a meaningful pass.

### The finding the Committee should see

Under the stress replay, the **policy portfolio itself** breached the (20.00%)
mandate limit in two of the five episodes that could be run:

| Episode | Policy portfolio, peak to trough |
|---|---|
| Global financial crisis, 2007 to 2009 | **not available** |
| Euro crisis and US downgrade, 2011 | (15.35%) |
| China devaluation and EM selloff, 2015 to 2016 | (14.31%) |
| Fourth quarter 2018 | (12.52%) |
| COVID-19 crash, 2020 | **(25.94%)** |
| 2022 inflation and rates | **(22.73%)** |

The Board's (20.00%) limit has been exceeded by the Board's own policy portfolio
twice in the fifteen years this study can observe, and the worst episode in the
modern record is not among them. Combined with the parametric reading of
(21.60%), the evidence is that the limit at IPS 3.3 is not attainable by the
policy portfolio at IPS 4.1. Under IPS 2.3 that is escalated to the Board as an
amendment question. It is not resolved inside the portfolio and it is not
resolved by adjusting this test.

---

## 6. What this test does not catch

The section that decides whether the rest of the paper is worth anything.

**1. The 2008 crisis is invisible to it.** `taa/datapull.py` pulls prices from
`WINDOW_START` less `ESTIMATION_PREFIX_YEARS`, which is 1 July 2009. The
worst equity drawdown of the modern era sits outside the sanctioned cache and
the replay cannot run it. The episode is left declared in the code so that every
run reports it as unavailable rather than quietly dropping it. **The worst
episode this test can measure is not the worst episode that has occurred.** The
remedy is to lengthen the estimation prefix and repull, not to reach around the
choke point at IPS 4.4.

**2. The liquidity floor cannot bind on the shipped opportunity set.** Every
line in `config.LIQUID_WITHIN_5D` is a daily-liquid ETF marked same-week
realisable, so weights summing to one always produce 100% liquid. The check only
fires when the custodian reports a vehicle has stopped clearing, supplied
through `context`. It is a tripwire for a change in the opportunity set or a
market event, not a live constraint on weights. The demonstration of it is
therefore a demonstration of the code, and a reader should not conclude the rank
1 constraint has been stress-tested against anything real. It also takes the
custodian's classification on trust and does not model market impact, so "liquid
within five business days" is tested as a label rather than as a capacity.

**3. It tests one allocation at one moment.** It says nothing about the path
between two allocations, about turnover accumulated across quarters, about
whether a sequence of individually compliant proposals drifts somewhere the
Board would not have gone, or about implementation shortfall between the
decision and the fill. `min_trade` sizes a trade; it does not cost one.

**4. It does not audit the covariance matrix.** Σ arrives from the Quantitative
desk and is used as given. Tracking error and the gating ex-ante drawdown both
rest entirely on it. A covariance estimated on 203 months of a period containing
one short crash and one long bull market will understate the correlation
breakdown that matters, and this desk has not checked whether it is shrunk,
conditioned, or estimated on overlapping windows. **The rank 3 and rank 4
constraints are only as reliable as an input this test does not verify.**

**5. Ex-ante drawdown is a model output and the mandate's limit is realised.**
Repeated because it is the point most likely to be forgotten between here and a
Committee paper. A pass on `drawdown_ex_ante` is a statement about a Gaussian
model of a portfolio, not a promise about the pool.

**6. The exclusion screen is bounded by what N-PORT shows.** Holdings below
roughly 0.001% can be missed, so every weight in section 3 is a floor. The
generation-versus-extraction question is unresolved and the fuel mix of every
utility named is unverified. A `PASS-WITH-DISCLOSURE` on `board_exclusions` means
no direct exposure was reported and the incidental exposure that was found has
been written down. It does not mean the fund is free of tobacco or coal, and it
does not mean the list is complete. It also depends on the Implementation desk
reporting direct exposure truthfully through `context`, which this test cannot
verify.

**7. Vehicle substitution is only partly modelled.** The exclusion table keys on
the vehicle actually used. Swapping SPY for VTI changes the disclosure and the
test will follow, but `INVESTABLE_FROM` and the liquidity classification are
keyed to the primary vehicle in `config.VEHICLE`, so a substitution into an
alternate vehicle with a later listing date or worse liquidity would not be
caught.

**8. Corridor widths were never tested.** See section 5.

**9. A constraint absent from `config.py` is absent from the test.** The test
enforces the transcription, not the Statement. `MAX_NEW_LOCKUPS` at IPS 3.4 and
the daily-liquidity implementation requirement at IPS 3.5 are both in the
mandate and neither is checked here, because neither is expressible as a
function of a weight vector alone. If the transcription in `config.py` diverges
from the Statement, this test will enforce the error faithfully and report a
pass.

---

## What would prove this test wrong

An allocation that passes every check here and then breaches a constraint the
Statement actually imposes, or the policy portfolio failing a check whose limit
the Board did not set.

---

*Risk function. This desk holds a veto and no opinion on allocation (IPS 2.1).*
*Code: `taa/compliance.py`, `taa/exclusions.py`. Assertions:
`tests/test_compliance.py`. Output: `outputs/compliance_demo.json`.*
