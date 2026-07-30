# Capital Markets Desk

**Ashcroft University Endowment | 28 July 2026**

Long-horizon capital market assumptions for the nine policy lines, and what the
policy portfolio is priced to earn against the 8.10% required return.

Every factual claim below is tagged `[VERIFIED: url]` if it was fetched during
the preparation of this paper, or `[RECALLED]` if it comes from memory. Recalled
numbers appear only where a judgment input was needed and no free current source
could be opened. They are flagged in place, and their effect is shown as a
sensitivity rather than buried in a point estimate.

---

## 1. Conclusion

On seven independent published house forecasts, normalised to a ten-year nominal
geometric basis in USD, the policy portfolio is priced to earn **6.08%** over the
next decade. The required return is 8.10%. The gap is **−202bp**.

The gap does not close anywhere in the published range.

| Basis | 10y expected return | Gap to 8.10% |
|---|---:|---:|
| Most pessimistic line-by-line combination | 3.99% | −411bp |
| Most pessimistic single house (Vanguard) | 4.85% | −325bp |
| **Median across houses (adopted)** | **6.08%** | **−202bp** |
| Most optimistic single house (BlackRock) | 7.31% | −79bp |
| Most optimistic line-by-line combination | 7.43% | −67bp |

The last row is the load-bearing one. Take the single most favourable published
forecast for every one of the nine lines, from whichever house happens to be most
optimistic on that line, and assemble a portfolio no house actually forecasts.
It still falls **67bp short** of 8.10%. There is no combination of currently
published capital market assumptions under which the Board's policy portfolio
meets its return objective.

Three second-order results that a reader should carry:

1. On a volatility and correlation aware basis, using Invesco's published vols and
   full correlation matrix, the portfolio geometric return is **6.46%**, not 6.08%.
   The naive weighted sum of line-level geometric returns understates the portfolio
   by 39bp because it discards the diversification benefit. Portfolio volatility is
   12.4%. The gap on that basis is −164bp. Both numbers are reported below; the
   6.08% headline is the one the machine-readable file carries because it is the one
   another desk can reproduce from the weights and the adopted line numbers.
2. For the portfolio to earn 8.10% with everything except US equity at its median,
   **US equity would have to return 11.23%** annualised for ten years. That is
   276bp above the highest published baseline forecast of any house and sits outside
   the entire published range.
3. **HEPI is running above the 3.20% the IPS assumes.** Commonfund forecasts 3.4%
   for fiscal 2026 and reports 3.6% actual for fiscal 2025. At 3.40% the required
   return becomes 8.30% and the gap widens to −222bp.

---

## 2. Source register

Seven houses form the primary set. All are free and public, none required a login
or a subscription. The one exception is flagged.

| House | Publication | Vintage / as-of | Nominal or real | Arithmetic or geometric | Horizon | URL |
|---|---|---|---|---|---|---|
| Vanguard | Vanguard Capital Markets Model return forecasts ("Setting realistic expectations") | 30 Jun 2026 (equity); 30 Sep 2025 (fixed income, commodities, REITs) | Nominal | Geometric (annualised median of 10,000 VCMM simulations) | 10y | [corporate.vanguard.com](https://corporate.vanguard.com/content/corporatesite/us/en/corp/vemo/vemo-return-forecasts.html) `[VERIFIED]` |
| J.P. Morgan Asset Management | 2026 Long-Term Capital Market Assumptions, 30th edition (Executive Summary) | 30 Sep 2025 | Nominal | Geometric ("annualized average expected return over our 10- to 15-year time horizon") | 10–15y | [am.jpmorgan.com](https://am.jpmorgan.com/us/en/asset-management/institutional/insights/portfolio-insights/ltcma/) `[VERIFIED]` |
| BlackRock Investment Institute | Capital Market Assumptions, May 2026 update, USD, "Starting point" scenario | 31 Mar 2026 | Nominal | Geometric | 10y (5y to 30y published) | [blackrock.com](https://www.blackrock.com/institutions/en-us/insights/thought-leadership/capital-market-assumptions) `[VERIFIED]` |
| Invesco Solutions | 2026 Capital Market Assumptions, Q1 update, USD (Figure 6) | 31 Dec 2025 | Nominal | Both published; geometric column used | 10y | [invesco.com PDF](https://www.invesco.com/content/dam/invesco/emea/en/pdf/invesco-capital-market-assumption-usd.pdf) `[VERIFIED]` |
| Northern Trust Asset Management | Capital Market Assumptions, 2026 edition, 10-year outlook | 30 Sep 2025 | Nominal | Geometric ("annual returns (geometric basis)") | 10y | [ntam.northerntrust.com PDF](https://ntam.northerntrust.com/content/dam/northerntrust/investment-management/global/en/documents/thought-leadership/2026/cma/2026-capital-market-assumptions-report.pdf) `[VERIFIED]` |
| Charles Schwab Asset Management | Schwab's 2026 Long-Term Capital Market Expectations | 31 Oct 2025 | Nominal | Geometric ("annualized 10-year nominal geometric return") | 10y | [schwab.com](https://www.schwab.com/learn/story/schwabs-long-term-capital-market-expectations) `[VERIFIED]` |
| Research Affiliates | Asset Allocation Interactive | 31 Dec 2025 | Nominal | Geometric | 10y | Reported by [Morningstar](https://www.morningstar.com/markets/experts-forecast-stock-bond-returns-2026-edition) `[VERIFIED]` |
| GMO *(memo only)* | GMO 7-Year Asset Class Forecast | Nov 2025 | **Real** | Geometric | **7y** | Reported by [Morningstar](https://www.morningstar.com/markets/experts-forecast-stock-bond-returns-2026-edition) `[VERIFIED]` |

**Research Affiliates fails the public-data test at source.** Its Asset Allocation
Interactive tool requires a login, which the IPS Section 2.5 evidence standard does
not permit. Its numbers are used here only as republished by Morningstar on a free
page, which is what the desk actually opened. A reader who wants to audit the
primary is told in advance that they will hit a login wall.

**Sources considered and rejected:**

- **Horizon Actuarial Survey of Capital Market Assumptions.** The obvious best
  source for dispersion, because it surveys roughly 40 houses. The current edition
  is behind a download registration form, and the only file reachable without one
  is the 2021 edition. Rejected on both grounds `[VERIFIED: https://www.horizonactuarial.com/survey-of-capital-market-assumptions]`.
- **Fidelity.** Publishes a 20-year horizon, which cannot be stacked against
  ten-year numbers without a term-structure assumption the desk would have to
  invent `[VERIFIED: Morningstar]`.
- **Northern Trust global natural resources (6.4%).** Excluded from the commodities
  line. It is a listed-equity forecast; DBC and GSG hold futures, not equities.

### Market observables used for the bottom-up work

| Series | Value | Date | Source |
|---|---:|---|---|
| 10y Treasury constant maturity (DGS10) | 4.65% | 27 Jul 2026 | FRED `[VERIFIED: https://fred.stlouisfed.org/graph/fredgraph.csv?id=DGS10]` |
| 30y Treasury (DGS30) | 5.12% | 27 Jul 2026 | FRED `[VERIFIED]` |
| 3m Treasury bill (DGS3MO) | 3.96% | 27 Jul 2026 | FRED `[VERIFIED]` |
| 10y breakeven inflation (T10YIE) | 2.21% (2.20% on 28 Jul) | 27 Jul 2026 | FRED `[VERIFIED: https://fred.stlouisfed.org/graph/fredgraph.csv?id=T10YIE]` |
| ICE BofA US Corporate OAS (BAMLC0A0CM) | 0.81% | 27 Jul 2026 | FRED `[VERIFIED]` |
| ICE BofA US High Yield OAS (BAMLH0A0HYM2) | 2.81% | 27 Jul 2026 | FRED `[VERIFIED]` |
| Shiller CAPE (PE10) | 40.47 | 27 Jul 2026 | multpl `[VERIFIED: https://www.multpl.com/shiller-pe]` |
| S&P 500 dividend yield | 1.09% | 27 Jul 2026 | multpl `[VERIFIED: https://www.multpl.com/s-p-500-dividend-yield]` |
| CPI-U year on year | 3.46% (Jun 2026) | Jun 2026 | FRED CPIAUCSL `[VERIFIED]` |
| HEPI forecast, fiscal 2026 | 3.4% | data through 24 Jun 2026 | Commonfund `[VERIFIED: https://www.commonfund.org/index/higher-education-price-index-forecast-june-2026]` |

---

## 3. Normalisation to 10-year nominal geometric

The two places these forecasts get silently mixed are geometric against arithmetic,
and real against nominal. Both were checked at source rather than assumed.

**Geometric against arithmetic.** All seven primary houses publish geometric
(compound, annualised) returns, so no conversion was required for the primary set.
This was verified individually. Schwab states it in terms: "an annualized 10-year
nominal geometric return" `[VERIFIED: schwab.com]`. Northern Trust states
"Forecasted returns are annual returns (geometric basis)" `[VERIFIED: NTAM PDF p.34]`.
J.P. Morgan states "Annualized average expected return over our 10- to 15-year time
horizon" `[VERIFIED: JPM Executive Summary p.2 footnote 5]`. BlackRock's methodology
states its projections use "proprietary capital markets assumptions for risk and
geometric return"
`[VERIFIED: https://www.blackrock.com/us/financial-professionals/tools/expected-returns-analyzer-methodology]`.
Invesco publishes geometric and arithmetic side by side and the geometric column is
the one used `[VERIFIED: Invesco Figure 6]`. Vanguard's ranges are annualised medians
of a simulated distribution `[VERIFIED: corporate.vanguard.com]`.

This distinction is worth 100bp to 200bp on an equity line and it is not cosmetic.
Invesco's own table shows US large cap at 5.0% geometric against 6.6% arithmetic, a
160bp wedge on a single line `[VERIFIED: Invesco Figure 6]`. Any desk that mixed the
two columns would produce a materially different answer.

Three rows of Invesco's Figure 6 print a geometric return above the arithmetic return
for the same asset, which is arithmetically impossible (global ex-US equity 7.1
against 6.4; US broad market 5.1 against 4.8; eurozone equity 8.1 against 7.0). The
geometric column is the one that reconciles to Invesco's own published building-block
decomposition, so the geometric column is used and the arithmetic column is treated
as a typesetting error in those rows. Check: Invesco's US large cap building blocks
are dividend yield 1.34 + buyback yield 1.84 + long-term earnings growth 4.01 +
expected inflation 2.19 + valuation change −4.50 = 4.88%, which rounds to the 5.0%
geometric shown `[VERIFIED: Invesco Figures 4 and 6]`.

**Real against nominal.** Only GMO publishes in real terms. Its conversion is
`nominal = (1 + real)(1 + inflation) − 1` at the 10-year breakeven of 2.21%
(FRED T10YIE, 27 Jul 2026). GMO's −6.0% real US large cap becomes −3.9% nominal.

**Vanguard's split vintage.** Vanguard's June 2026 page publishes the three equity
ranges in narrative form and does not expose the fixed income and real asset table.
The most recent Vanguard table this desk could open in full is the 30 September 2025
edition `[VERIFIED: https://www.vanguardsouthamerica.com/en/home/insights/economic-market-outlook/vanguard-capital-markets-model-forecasts]`.
Vanguard's equity lines are therefore carried at the 30 June 2026 vintage and its
non-equity lines at the 30 September 2025 vintage, and both dates are stated in the
register rather than blended into one. Vanguard's June 2026 commentary says
"U.S. aggregate bond expected returns increased modestly" since March, so the
September 2025 fixed income numbers used here are, if anything, slightly low
`[VERIFIED: corporate.vanguard.com]`.

**Horizon.** Six of the seven are ten-year. J.P. Morgan's is ten to fifteen years
and no adjustment is applied, because J.P. Morgan does not publish a term structure
that would permit one. On a flat-ish path this understates nothing material; on a
mean-reverting path a fifteen-year number is higher than a ten-year number, so
J.P. Morgan's contribution to the median is more likely biased high than low.
GMO is seven-year and is excluded from every median for that reason.

---

## 4. Line by line

All figures are 10-year nominal geometric returns in USD, in percent.

| Line | Weight | Vanguard | J.P. Morgan | BlackRock | Invesco | Northern Trust | Schwab | Research Affiliates | Median | Min | Max | Spread | **Adopted** |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| US equity | 38% | 5.20 | 6.70 | 8.47 | 5.00 | 6.80 | 5.90 | 3.10 | 5.90 | 3.10 | 8.47 | 537bp | **5.90** |
| Developed ex-US equity | 20% | 5.50 | 7.50 | 8.04 | 7.20 | 6.36* | 7.00 | 7.70 | 7.20 | 5.50 | 8.04 | 254bp | **7.20** |
| Emerging markets equity | 12% | 3.00 | 7.80 | 7.27 | 6.10 | 6.90 | — | 7.50 | 7.09 | 3.00 | 7.80 | 480bp | **7.09** |
| US Treasury duration | 12% | 4.20 | 4.60 | 4.63 | 4.00 | 4.60 | — | — | 4.60 | 4.00 | 4.63 | 63bp | **4.60** |
| US investment grade credit | 8% | — | 5.20 | 5.41 | 5.20 | 5.10 | — | — | 5.20 | 5.10 | 5.41 | 31bp | **5.20** |
| US high yield | 5% | 5.00 | 6.10 | 6.46 | 5.40 | 5.50 | — | — | 5.50 | 5.00 | 6.46 | 146bp | **5.50** |
| Commodities | 3% | 5.60 | 4.60 | — | 6.00 | — | — | — | 5.60 | 4.60 | 6.00 | 140bp | **5.60** |
| Listed real estate | 2% | 3.60 | 8.80 | 6.59 | 7.10 | 6.20 | — | — | 6.59 | 3.60 | 8.80 | 520bp | **6.59** |
| Cash / T-bills | 0% | 3.40 | 3.10 | 3.59 | 3.20 | 3.30 | 3.30 | — | 3.30 | 3.10 | 3.59 | 49bp | **3.30** |

\* Northern Trust publishes no EAFE aggregate. 6.36% is a desk construction from
its published regional forecasts at approximate EAFE capitalisation weights:
Europe ex-UK 5.7% at 47%, UK 6.2% at 15%, Japan 7.3% at 23%, Australia 7.7% at 8%,
other 6.5% at 7% `[VERIFIED: NTAM PDF p.35 for the regional numbers; RECALLED for the
capitalisation weights, which are approximate]`. Substituting Northern Trust's
published MSCI World figure of 6.8% instead moves the line median by nothing, because
6.36% is not the median value.

### The adoption rule

**The adopted number for every line is the median across the cited houses, with no
discretionary override.** The rule was fixed before the numbers were assembled. A
desk that adopts a median it likes and overrides a median it does not is a desk
producing a view dressed as a survey. Where the desk disagrees with the median, that
disagreement is expressed as an explicit, quantified sensitivity in sections 8 and 9,
and never by quietly moving the adopted number.

### Index mapping notes

- **US Treasury duration** maps to each house's broad or intermediate Treasury index.
  The policy vehicle is stated as IEF or TLT, and those are different animals. On the
  same houses' long Treasury lines the numbers are 5.20% (J.P. Morgan), 5.33%
  (BlackRock) and 5.80% (Invesco), so a TLT-weighted implementation would sit 60bp to
  180bp above the 4.60% adopted here. That is a live implementation choice worth
  roughly 7bp to 22bp on the total portfolio at a 12% weight, and it belongs to whoever
  owns implementation.
- **Listed real estate** carries a 520bp spread that is mostly a definitional
  disagreement rather than a disagreement about real estate. Vanguard and J.P. Morgan
  quote US REITs; BlackRock, Invesco and Northern Trust quote developed or global
  listed real estate. VNQ is US-only, so the two closest matches to the actual vehicle
  are Vanguard at 3.60% and J.P. Morgan at 8.80%, and they are 520bp apart on the same
  asset. J.P. Morgan's figure is stated leveraged and net of fees
  `[VERIFIED: JPM Executive Summary Exhibit 5]`. At a 2% weight the whole line is worth
  2bp per 100bp, so this is disclosed rather than resolved.
- **US investment grade** has the tightest dispersion of any line at 31bp, which is
  what one should expect: all four houses are building the same starting yield off the
  same curve and the same 81bp index OAS. Where houses agree, they agree because the
  answer is nearly mechanical. Where they disagree, they are disagreeing about equity
  valuation.

---

## 5. Policy portfolio expected return, with dispersion carried through

### Weighted sum on adopted numbers

| Line | Weight | Adopted | Contribution |
|---|---:|---:|---:|
| US equity | 38% | 5.90% | 2.242% |
| Developed ex-US equity | 20% | 7.20% | 1.440% |
| Emerging markets equity | 12% | 7.09% | 0.850% |
| US Treasury duration | 12% | 4.60% | 0.552% |
| US investment grade credit | 8% | 5.20% | 0.416% |
| US high yield | 5% | 5.50% | 0.275% |
| Commodities | 3% | 5.60% | 0.168% |
| Listed real estate | 2% | 6.59% | 0.132% |
| Cash | 0% | 3.30% | 0.000% |
| **Total** | **100%** | | **6.075%** |

### Each house's own portfolio

Applying each house's own numbers to the Board's weights. Where a house does not
cover a line, the median is substituted and the substitution is named.

| House | Policy return | Gap to 8.10% | Own-number coverage | Lines filled from median |
|---|---:|---:|---:|---|
| Vanguard | 4.85% | −325bp | 92% | US IG credit |
| Research Affiliates | 5.16% | −294bp | 70% | Treasuries, IG, HY, commodities, listed RE |
| Invesco | 5.56% | −254bp | 100% | none |
| Schwab | 6.04% | −207bp | 58% | EM, Treasuries, IG, HY, commodities, listed RE |
| Northern Trust | 6.21% | −189bp | 97% | commodities |
| J.P. Morgan | 6.57% | −153bp | 100% | none |
| BlackRock | 7.31% | −79bp | 97% | commodities |

The two houses with complete own-number coverage of all nine lines, Invesco and
J.P. Morgan, bracket the median at 5.56% and 6.57%. That is the honest core range:
**5.6% to 6.6%**, from the two forecasts that require no substitution at all.

### GMO as the tail

GMO's seven-year forecast, converted to nominal at the 2.21% breakeven, gives US
large cap −3.92%, international large cap +1.49% and emerging markets +3.23%
`[VERIFIED: Morningstar; conversion by this desk]`. Applied to the three equity lines
with everything else at the median, the policy portfolio returns **0.74%**, a gap of
−736bp. GMO is excluded from every median because the horizon is seven years, the
published basis is real, and the forecast is explicitly conditional on "a normal
interest rate environment". It is reported because a committee told only about a
−202bp gap and not about a house that thinks the number could be −736bp has not been
told the dispersion.

---

## 6. Volatility and correlation aware calculation

The weighted sum of nine geometric returns is not the geometric return of the
portfolio that holds them. Arithmetic returns are linear in weights; geometric
returns are not. Doing this properly requires vols and correlations, and Invesco is
the one house in the set that publishes both a full volatility column and a full
correlation matrix `[VERIFIED: Invesco Figures 6 and 7]`.

Method. For each line, convert the adopted geometric return to arithmetic using
μ ≈ g + σ²/2. Sum the arithmetic returns at policy weights, which is exact. Compute
portfolio variance as w′Σw from Invesco's published vols and pairwise correlations.
Convert back with g_p ≈ μ_p − σ_p²/2.

Volatilities used (Invesco, 31 Dec 2025): US large cap 16.8%, EAFE 17.6%, EM 18.7%,
intermediate Treasury 3.0%, US IG corporate 5.6%, US high yield 4.1%, S&P GSCI
commodities 18.2%, global REITs 18.0%.

| Quantity | Value |
|---|---:|
| Weighted sum of line-level geometric returns (the headline) | 6.075% |
| Portfolio arithmetic mean | 7.235% |
| Portfolio volatility | 12.41% |
| Weighted average of line volatilities, undiversified | 14.07% |
| **Portfolio geometric return** | **6.464%** |
| Diversification uplift over the naive weighted sum | **+39bp** |
| Arithmetic minus geometric on the portfolio | 77bp |
| Gap to 8.10% on the portfolio-geometric basis | **−164bp** |

Two things follow. First, the honest gap is somewhere between −164bp and −202bp,
and the difference between those two numbers is entirely a question of whether you
credit the portfolio with its own diversification. It should be credited. Second,
the 77bp arithmetic-to-geometric wedge on the portfolio is smaller than the wedge
on any single equity line, which is the diversification benefit showing up in a
second place. A desk quoting arithmetic returns would report 7.24% and a gap of
only −86bp, and would be wrong, because an endowment compounds.

The headline carried in `outputs/cme.json` remains 6.075%, because that is the
number another desk can reproduce from the weights and the adopted line numbers
without needing Invesco's correlation matrix. The 6.464% figure is the better
estimate of what the portfolio actually compounds at, and both are on the record.

---

## 7. The gap, stated plainly

| Scenario | Expected return | Gap to 8.10% |
|---|---:|---:|
| Line-by-line minimum | 3.99% | **−411bp** |
| Vanguard, lowest single house | 4.85% | −325bp |
| **Median, adopted, weighted sum** | **6.08%** | **−202bp** |
| Median, adopted, portfolio-geometric | 6.46% | −164bp |
| BlackRock, highest single house | 7.31% | −79bp |
| Line-by-line maximum | 7.43% | **−67bp** |

What −202bp means in the Board's own units:

- The portfolio supports a spending rate of **2.48%**, against the policy 4.50%
  (6.08% return less 3.20% HEPI less 0.40% fees). At the current HEPI forecast of
  3.40% it supports **2.28%**.
- Spending 4.50% out of a portfolio earning 6.08% while HEPI runs 3.20% and fees
  cost 0.40% erodes the corpus by 2.03% in real terms per year. Compounded over
  ten years that is a **18.5% real loss of purchasing power**, roughly
  **USD 157m** in today's money on an USD 850m corpus.
- The tactical budget is 200bps of ex-ante tracking error (MANDATE, section
  "Tactical allocation budget"). Closing a 202bp gap through tactical allocation
  alone would require an information ratio of about **1.0 sustained for ten
  consecutive years**. The IPS constraint hierarchy already ranks the return
  objective fifth and marks it "best efforts", which is the correct place for it.

---

## 8. What would have to be true

Solving for the input that would make the policy portfolio earn 8.10%.

| Solve for | Required value | Median value | Uplift needed | Inside the published range? |
|---|---:|---:|---:|---|
| US equity alone, all else at median | **11.23%** | 5.90% | +533bp | **No.** 276bp above BlackRock's 8.47%, the highest baseline forecast in the set |
| Whole equity sleeve (70%) | **9.37%** | 6.48% | +289bp | **No.** Above every house's blended equity number |
| Uniform uplift on every one of the nine lines | +202bp on each | | | **No.** Every house would have to be 202bp too low on every line simultaneously |

Translating the 11.23% US equity requirement into valuation terms using the
Grinold-Kroner decomposition in section 9: it requires the CAPE to rise from 40.47
today to **72.7** in ten years. That is 1.80 times today's level and **1.64 times
the December 1999 peak of 44.19**, which is the highest reading in the entire
Shiller series `[VERIFIED: multpl.com]`. It is not a forecast anyone in the set has
made, and it is not one this desk would make.

For completeness, the median US equity forecast of 5.90% itself requires the CAPE to
rise to 43.4 over ten years, which is 1.07 times today and just under the 1999 peak.
Even the consensus embeds no valuation mean reversion whatsoever. BlackRock's 8.47%
requires a CAPE of 55.8, which is 1.26 times the 1999 peak; BlackRock is explicit
that its higher outcomes live in a named "AI productivity boom" scenario, in which
its own US large cap ten-year number is 14.81% `[VERIFIED: BlackRock CMA spreadsheet,
"AI productivity boom" tab]`. The 11.23% this endowment needs sits inside that
scenario and outside every baseline. That is the cleanest possible statement of
what the Board is being asked to underwrite.

---

## 9. Bottom-up cross-check

Built from current observable inputs, independently of the houses.

### US equity, Grinold-Kroner

E[r] = dividend yield + nominal EPS growth + annualised change in the multiple.
Buybacks are folded into per-share EPS growth rather than added separately, to avoid
double counting the repurchase yield.

Inputs: dividend yield 1.09% `[VERIFIED: multpl, 27 Jul 2026]`, expected inflation
2.21% `[VERIFIED: FRED T10YIE, 27 Jul 2026]`, long-run US real EPS growth 1.90%
`[RECALLED]`, CAPE 40.47 `[VERIFIED: multpl, 27 Jul 2026]`.

The 1.90% real EPS growth figure is the one recalled input in this section. The
defensible range is roughly 1.5% to 2.0%, and the sensitivity is one for one: each
10bp of real EPS growth is 10bp of expected return. Nothing below turns on which end
of that range is used.

| Valuation path | Annualised ΔP/E | E[r] nominal |
|---|---:|---:|
| CAPE stays at 40.47 | 0.00% | **5.20%** |
| CAPE reverts to its 1990–2025 average, about 27 `[RECALLED]` | −3.97% | 1.23% |
| CAPE reverts to its full-history mean of 17.40 `[VERIFIED: multpl]` | −8.09% | −2.89% |

A second, cruder anchor with no growth assumption at all: the CAPE earnings yield is
1/40.47 = 2.47% real, which is 4.68% nominal at the current breakeven.

**Where this disagrees with the houses.** The desk's own no-mean-reversion estimate
is 5.20%, which is 70bp below the house median of 5.90% and 327bp below BlackRock.
Only Invesco (5.00%), Vanguard (5.20%) and Research Affiliates (3.10%) sit at or
below the desk's most generous case. The four houses above 5.90% are, arithmetically,
forecasting multiple expansion from the second-highest CAPE in recorded history, or
real earnings growth well above 1.9%, or both. They may be right about AI-driven
margin expansion. The point for the Board is that **the median is the optimistic end
of what current valuations support, not the middle of it**, and the desk's own work
argues the 5.90% adopted for US equity is more likely too high than too low.

### US Treasuries

The standard first-order forecast for a constant-maturity Treasury fund over a
horizon near twice its duration is the starting yield.

| Vehicle | Reference yield, 27 Jul 2026 | House-adopted |
|---|---:|---:|
| IEF, 7–10y | 4.65% (DGS10) | |
| TLT, 20+y | 5.12% (DGS30) | |
| 50/50 IEF/TLT | 4.88% | |
| **Line adopted from houses** | | **4.60%** |

The curve is upward sloping (3m 3.96%, 10y 4.65%, 30y 5.12%), so a rolling ladder
picks up rolldown on top of the starting yield, which pushes the honest estimate
above rather than below 4.65%.

**Where this disagrees with the houses.** The adopted 4.60% is 5bp below the current
10-year yield and 28bp below a 50/50 IEF/TLT blend. The houses are marginally
conservative here, and the direction of the error is in the endowment's favour by 3bp
to 6bp on the total portfolio. This is the one line where the desk would say the
consensus is too low rather than too high. The caveat is that the yield-equals-return
identity holds cleanly for a fund whose duration is roughly half the horizon; for TLT
over ten years the approximation is much weaker and the realised outcome is dominated
by where the long end sits at the end of the period.

### Credit

| | Build | Result | House-adopted |
|---|---|---:|---:|
| Investment grade | 4.65% (10y UST) + 0.81% (index OAS) − 0.15% expected loss `[RECALLED]` | **5.31%** | 5.20% |
| High yield | 4.20% (duration-matched base `[RECALLED]`) + 2.81% (index OAS) − 1.65% expected loss | **5.36%** | 5.50% |

The high yield loss assumption uses Northern Trust's own published long-term default
rate of 2.75% `[VERIFIED: NTAM PDF p.18]` at a 60% loss given default `[RECALLED]`.

**Where this disagrees with the houses.** It does not, materially. Both credit lines
reconcile to within 15bp, which is the expected result: credit forecasts at these
horizons are the starting yield minus a loss assumption, and there is not much room
for houses to differ. Worth noting for the record that both spreads are historically
tight (IG at 81bp, HY at 281bp), so both lines are being forecast off a rich starting
point, and both carry more downside than upside around the point estimate.

---

## 10. Vintage risk, and the emerging markets line specifically

The dispersion the IPS asks about is partly disagreement and partly staleness. Only
two of the seven forecasts are dated inside the last four months: Vanguard at
30 June 2026 and BlackRock at 31 March 2026. Three are dated 30 September 2025,
which is ten months stale.

The emerging markets line makes the problem concrete. Vanguard cut its EM range from
3.6%–5.6% to 2%–4% between 31 March and 30 June 2026, explicitly because "markets
became more expensive as a rally following a Middle East ceasefire agreement
broadened globally" `[VERIFIED: corporate.vanguard.com]`. Vanguard's 3.00% is
therefore the only EM number in the set that has been marked to that rally. The other
five, at 6.10% to 7.80%, predate it by six to ten months. The median of 7.09% is
almost certainly biased high.

Sensitivity. Marking only the three equity lines to Vanguard's 30 June 2026 vintage
(US equity 5.20%, developed ex-US 5.50%, EM 3.00%) and holding all six other lines
at the median gives a policy return of **4.98%** and a gap of **−312bp**. That is
not the same as the Vanguard row in section 5, which is 4.85% because it also uses
Vanguard's older and lower fixed income and REIT numbers. The freshest-vintage
equity marking on its own costs 110bp against the median. The truth is likely
between 4.98% and 6.08%, and closer to the lower end than a naive median implies.

This is a live falsifier. If the September 2025 houses republish in the autumn of
2026 with EM materially unchanged at 6% to 7%, the staleness concern was wrong and
the median should stand. If they republish EM near 4%, the desk's reservation was
right and this paper's headline was too generous.

---

## 11. The inflation assumption

The required return of 8.10% is 4.50% spending plus 3.20% HEPI plus 0.40% fees.
Two problems with that construction.

**HEPI is running above 3.20%.** Commonfund forecasts **3.4%** for fiscal 2026, on
data through 24 June 2026, and reports **3.6%** actual for fiscal 2025
`[VERIFIED: https://www.commonfund.org/index/higher-education-price-index-forecast-june-2026]`.
The IPS assumption of 3.20% is below both the current forecast and the prior year's
outturn.

For context, CPI-U is running at 3.46% year on year as of June 2026
`[VERIFIED: FRED CPIAUCSL]`, while the market prices only 2.21% CPI inflation over
the next ten years `[VERIFIED: FRED T10YIE]`. HEPI has historically run above CPI
because it is weighted toward salaries and benefits `[RECALLED]`. If CPI does
converge to the 2.21% breakeven and the HEPI-CPI wedge holds at roughly 100bp to
120bp, HEPI over the next decade lands at 3.2% to 3.4%, and the IPS assumption is at
the low end of reasonable rather than wrong.

| HEPI assumption | Required return | Gap at 6.08% |
|---|---:|---:|
| 3.20% (IPS) | 8.10% | −202bp |
| 3.40% (Commonfund FY2026 forecast) | 8.30% | −222bp |
| 3.60% (Commonfund FY2025 actual) | 8.50% | −242bp |

**The required return is built additively.** Spending, inflation and fees are summed.
Compounded, the same three requirements are (1.045)(1.032)(1.004) − 1 = **8.28%**,
which is 18bp above the stated 8.10%. The additive construction therefore understates
the requirement, and the gap understates the problem, by about 18bp.

**Recommendation to the Committee.** The 3.20% HEPI assumption is defensible on a
ten-year forward view and is optimistic on a trailing-two-year view. It should be
reviewed against the Commonfund series annually rather than left fixed, and the
Committee should be shown the 8.30% variant alongside the 8.10% whenever the gap is
discussed, because the difference between them is 20bp and the gap itself is only
202bp.

---

## 12. Falsifiers

Every view in this paper can be wrong, and here is how a reader would know.

1. **The gap closes if US equity earns above 11.23%.** That requires the CAPE at
   72.7 in 2036. Watch the CAPE against 44.19.
2. **The staleness argument is wrong if the September 2025 houses republish in
   late 2026 with equity numbers materially unchanged.** Specifically, if EM
   republishes near 7% rather than near 4%.
3. **The bottom-up US equity work is wrong if real EPS growth runs materially
   above 1.9%.** AI-driven margin expansion is the named mechanism, it is the
   explicit basis of BlackRock's 14.81% AI-boom scenario, and it is testable
   against realised S&P 500 real EPS.
4. **The Treasury line is too low, and this paper says so.** If IEF and TLT deliver
   near their starting yields, the fixed income sleeve beats the adopted numbers
   by 5bp to 30bp and the gap narrows by a few basis points. This is the one
   direction in which the desk expects to be pleasantly wrong.
5. **The credit lines assume today's tight spreads persist.** IG at 81bp and HY at
   281bp are both historically rich. If spreads normalise toward long-run averages
   the realised returns land below the adopted numbers, and the gap widens.

---

## 13. Machine-readable output

`outputs/cme.json`, conforming to the agreed schema. Line keys are
`us_equity, dev_ex_us, em_equity, ust_duration, us_ig, us_hy, commodities,
listed_re, cash`. Headline `policy_expected_return.adopted` is 0.06075,
`required_return` is 0.081, `gap_bps` is −202.5.

---

## 14. Check output

`tests/check_capital_markets.py`, standard library only. Run 28 July 2026.

```
CAPITAL MARKETS CHECK  (cme.json, as of 2026-07-28)
===================================================
PASS  1. at least 3 distinct houses per equity line, each with a URL
  us_equity     7 houses, all with URLs: BlackRock, Invesco, J.P. Morgan, Northern Trust, Research Affiliates, Schwab, Vanguard
  dev_ex_us     7 houses, all with URLs: BlackRock, Invesco, J.P. Morgan, Northern Trust, Research Affiliates, Schwab, Vanguard
  em_equity     6 houses, all with URLs: BlackRock, Invesco, J.P. Morgan, Northern Trust, Research Affiliates, Vanguard
PASS  2. every one of the nine lines has >= 2 named sources
  us_equity     7 named sources
  dev_ex_us     7 named sources
  em_equity     6 named sources
  ust_duration  5 named sources
  us_ig         4 named sources
  us_hy         5 named sources
  commodities   3 named sources
  listed_re     5 named sources
  cash          6 named sources
PASS  3. adopted lies within [min, max] of cited sources
  us_equity     adopted   5.90% in [ 3.10%,  8.47%], median   5.90%
  dev_ex_us     adopted   7.20% in [ 5.50%,  8.04%], median   7.20%
  em_equity     adopted   7.08% in [ 3.00%,  7.80%], median   7.08%
  ust_duration  adopted   4.60% in [ 4.00%,  4.63%], median   4.60%
  us_ig         adopted   5.20% in [ 5.10%,  5.41%], median   5.20%
  us_hy         adopted   5.50% in [ 5.00%,  6.46%], median   5.50%
  commodities   adopted   5.60% in [ 4.60%,  6.00%], median   5.60%
  listed_re     adopted   6.59% in [ 3.60%,  8.80%], median   6.59%
  cash          adopted   3.30% in [ 3.10%,  3.59%], median   3.30%
PASS  4. weighted policy return recomputes to within 1bp of headline
  recomputed 6.07500%  stated 6.07500%  difference 0.00bp (tolerance 1.00bp)
PASS  5. policy weights sum to 1.0
  policy weights sum to 1.0000000000
---------------------------------------------------
5 of 5 assertions passed.
EXIT=0
```

And the same harness catching a deliberate corruption, `--demo-fail`, which pushes
the adopted US equity number 200bp above the highest cited house:

```
DEMO-FAIL MUTATION
  us_equity.adopted 0.0590 -> 0.1047 (above the cited max of 0.0847)
  This should break assertion 3, and assertion 4 as a consequence,
  because the headline no longer recomputes from the adopted numbers.

CAPITAL MARKETS CHECK (mutated data)
====================================
PASS  1. at least 3 distinct houses per equity line, each with a URL
  us_equity     7 houses, all with URLs: BlackRock, Invesco, J.P. Morgan, Northern Trust, Research Affiliates, Schwab, Vanguard
  dev_ex_us     7 houses, all with URLs: BlackRock, Invesco, J.P. Morgan, Northern Trust, Research Affiliates, Schwab, Vanguard
  em_equity     6 houses, all with URLs: BlackRock, Invesco, J.P. Morgan, Northern Trust, Research Affiliates, Vanguard
PASS  2. every one of the nine lines has >= 2 named sources
  us_equity     7 named sources
  dev_ex_us     7 named sources
  em_equity     6 named sources
  ust_duration  5 named sources
  us_ig         4 named sources
  us_hy         5 named sources
  commodities   3 named sources
  listed_re     5 named sources
  cash          6 named sources
FAIL  3. adopted lies within [min, max] of cited sources
  us_equity     adopted 0.1047 outside [0.0310, 0.0847]
  dev_ex_us     adopted   7.20% in [ 5.50%,  8.04%], median   7.20%
  em_equity     adopted   7.08% in [ 3.00%,  7.80%], median   7.08%
  ust_duration  adopted   4.60% in [ 4.00%,  4.63%], median   4.60%
  us_ig         adopted   5.20% in [ 5.10%,  5.41%], median   5.20%
  us_hy         adopted   5.50% in [ 5.00%,  6.46%], median   5.50%
  commodities   adopted   5.60% in [ 4.60%,  6.00%], median   5.60%
  listed_re     adopted   6.59% in [ 3.60%,  8.80%], median   6.59%
  cash          adopted   3.30% in [ 3.10%,  3.59%], median   3.30%
FAIL  4. weighted policy return recomputes to within 1bp of headline
  recomputed 7.81160%  stated 6.07500%  difference 173.66bp (tolerance 1.00bp)
PASS  5. policy weights sum to 1.0
  policy weights sum to 1.0000000000
------------------------------------
3 of 5 assertions passed.

DEMO OK: the mutation was caught by 2 assertion(s).
```

The demo exits 0 when the mutation is caught and non-zero when it is not, so the
demonstration itself cannot silently pass. The unmutated run exits 0 with 5 of 5
assertions passing; any real failure exits 1.
