# Implementation and Operations

**Ashcroft University Endowment · USD 850,000,000 · 28 July 2026**
Desk paper for the Investment Committee. Governing document: Investment Policy Statement v7.2, effective 1 July 2026.

Deliverables: `taa/costs.py` (importable cost and corridor module), `outputs/implementation.json` (machine-readable, every figure sourced), `tests/check_implementation.py` (53 assertions, output at Section 4).

---

## 0. What the desk asks the Committee to adopt

Three things.

**One.** A one-way transaction cost vector, in basis points of traded notional, for the nine policy lines. Fixed income and commodity lines cost several times what US equity costs. Commodities cost sixteen times what US equity costs.

| Line | Primary vehicle | One-way cost |
|---|---|---:|
| US equity | VTI (SPY for size) | **1.5bp** |
| Developed ex-US | VEA (EFA for size) | **4.0bp** |
| Emerging markets | VWO (EEM for size) | **8.0bp** |
| US Treasury duration | IEF (TLT for long end) | **3.0bp** |
| US investment grade | LQD | **6.0bp** |
| US high yield | HYG | **12.0bp** |
| Commodities | DBC (GSG to split size) | **25.0bp** |
| Listed real estate | VNQ | **5.0bp** |
| Cash | SGOV (BIL) | **1.0bp** |

> ### Unit contract, for anyone lifting these numbers
>
> **`taa/costs.py` works in percentage points of NAV, not fractions.** A 38% policy weight is `38.0` in this module and in every table in this paper. It is **not** `0.38`. The minimum trade `MIN_TRADE_PP` is `0.50`, meaning 50bp of NAV, meaning USD 4,250,000.
>
> The rest of the investment office works in fractions. Both conventions are defensible; holding both at once without saying so is how a study produces a confident wrong number. The conversion lives in one place, an adapter at the top of `taa/simulate.py`, with boundary assertions in `tests/check_units.py`. Do not convert at call sites.
>
> The costs themselves are in a **third** unit and this is the easiest thing in the paper to misread. **`ONE_WAY_BPS` is basis points of the traded notional, not basis points of NAV.** A 25bp cost on a 3pp commodity trade is 25bp of USD 25.5m, which is 0.75bp of NAV. `round_trip_cost` does that conversion for you: it **takes percentage points of NAV and returns basis points of NAV**. So does `drift_te_bps`. Everything named `*_pp` is percentage points on both sides; everything named `*_bps` returns basis points.
>
> The failure this guards against is live rather than theoretical. Called with fractional weights, `apply_min_trade` reads a 60bp trade as `0.006`, compares it against a `0.50` minimum, suppresses it, and returns a hold. The allocation is internally valid before and after, so neither a look-ahead test nor a compliance test flags it, and a five-year record would carry twenty reasoned entries explaining an inactivity that was an arithmetic error.

**Two.** A corridor table in which no corridor is narrower than the 50bp minimum trade at IPS Section 4.2, every band sits inside the IPS Section 4.1 range, and the whole set consumes 26.7bp of the 200bp tracking-error budget at its worst.

**Three.** A trustee reporting checklist built on the **GIPS Standards for Asset Owners, 2020 edition**, which is the chapter of the Global Investment Performance Standards that applies to this fund. The requirement most often missed is the one the IPS already gestures at: the **three-year annualised ex post standard deviation, using monthly returns, must be presented for the benchmark as well as for the total fund, as of each annual period end** (provision 24.A.1.j).

The desk gives ground on the return objective rather than the risk objective, per IPS Section 3.3. Every choice below (tighter corridors than the practitioner default, a cheaper primary vehicle over a more liquid one, a hard cap on commodity order size) trades a small amount of expected return for control.

---

## 1. Real transaction costs on the actual vehicles

### 1.1 What is published, and under what rule

SEC Rule 6c-11(c)(1)(v) requires an ETF to post on its website the **median bid-ask spread over the most recent 30 calendar days**, computed from the national best bid and offer sampled at the end of each ten-second interval and divided by the NBBO midpoint ([SEC ADI 2025-15, website posting requirements](https://www.sec.gov/about/divisions-offices/division-investment-management/accounting-disclosure-information/adi-2025-15-website-posting-requirements)). Every figure in the table below is that statistic, pulled from the issuer on 28 July 2026 with an issuer as-of date of 27 July 2026.

Two precision caveats matter and the desk states them rather than hiding them. iShares and Invesco round to two decimal places in percent, so a published `0.01%` means the true median lies somewhere near 0.5bp to 1.5bp. Vanguard publishes to eight decimal places, which is why the Vanguard vehicles carry sub-basis-point figures. SPY's published figure is `0.00%`, meaning below 0.005%; the one-cent minimum price increment on a USD 739.09 share is 0.135bp, which is the tightest the tick regime permits and is what the desk records.

### 1.2 The vehicle table

Dollar ADV is the median of close times volume over the 60 US trading sessions ended 28 July 2026, from the [Yahoo Finance public chart endpoint](https://query1.finance.yahoo.com/v8/finance/chart/SPY?range=3y&interval=1d). "100bp move" is USD 8,500,000 expressed as a share of that ADV.

| Ticker | Line | Role | Expense | 30d median spread | Dollar ADV | 100bp move as % of ADV | Prem/disc | AUM | Source |
|---|---|---|---:|---:|---:|---:|---:|---:|---|
| SPY | US equity | size | 0.0945% | 0.00% (0.14bp) | $35,899m | 0.02% | +0.02% | $785.2bn | [SPDR product data](https://www.ssga.com/library-content/products/fund-data/etfs/us/spdr-product-data-us-en.xlsx) |
| VTI | US equity | **primary** | 0.03% | **0.0055%** | $1,163m | 0.73% | +0.03% | $657.3bn | [Vanguard 30-day median bid/ask](https://advisors.vanguard.com/investments/bidaskspread) |
| EFA | Dev ex-US | size | 0.32% | 0.01% | $1,351m | 0.63% | +0.22% | $76.6bn | [iShares MSCI EAFE](https://www.ishares.com/us/products/239623/ishares-msci-eafe-etf) |
| VEA | Dev ex-US | **primary** | 0.03% | **0.0142%** | $734m | 1.16% | +0.16% | $226.7bn | [Vanguard](https://advisors.vanguard.com/investments/bidaskspread) |
| EEM | EM equity | size | 0.72% | 0.02% | $1,804m | 0.47% | 0.00% | $28.6bn | [iShares MSCI EM](https://www.ishares.com/us/products/239637/ishares-msci-emerging-markets-etf) |
| VWO | EM equity | **primary** | 0.06% | **0.0170%** | $452m | 1.88% | +0.16% | $120.9bn | [Vanguard](https://advisors.vanguard.com/investments/bidaskspread) |
| IEF | UST duration | **primary** | 0.15% | 0.01% | $553m | 1.54% | +0.03% | $47.3bn | [iShares 7-10y Treasury](https://www.ishares.com/us/products/239456/ishares-7-10-year-treasury-bond-etf) |
| TLT | UST duration | long end | 0.15% | 0.01% | $2,006m | 0.42% | +0.03% | $43.0bn | [iShares 20+y Treasury](https://www.ishares.com/us/products/239454/ishares-20-year-treasury-bond-etf) |
| LQD | US IG | **primary** | 0.14% | 0.01% | $2,895m | 0.29% | +0.01% | $33.8bn | [iShares iBoxx IG](https://www.ishares.com/us/products/239566/ishares-iboxx-investment-grade-corporate-bond-etf) |
| HYG | US HY | **primary** | 0.49% | 0.01% | $2,445m | 0.35% | +0.07% | $15.9bn | [iShares iBoxx HY](https://www.ishares.com/us/products/239565/ishares-iboxx-high-yield-corporate-bond-etf) |
| DBC | Commodities | **primary** | 0.89% total | **0.04%** | **$27.3m** | **31.1%** | **−0.44%** | $1.70bn | [Invesco DBC](https://www.invesco.com/us/financial-products/etfs/product-detail?audienceType=Investor&ticker=DBC) |
| GSG | Commodities | split | 0.75% | 0.03% | **$20.7m** | **41.1%** | **−0.50%** | $0.93bn | [iShares GSCI trust](https://www.ishares.com/us/products/239757/ishares-sp-gsci-commodityindexed-trust-fund) |
| VNQ | Listed RE | **primary** | 0.13% | **0.0102%** | $305m | 2.79% | +0.05% | $39.1bn | [Vanguard](https://advisors.vanguard.com/investments/bidaskspread) |
| BIL | Cash | alternate | 0.1353% | 0.01% | $847m | 1.00% | 0.00% | $47.2bn | [SPDR product data](https://www.ssga.com/library-content/products/fund-data/etfs/us/spdr-product-data-us-en.xlsx) |
| SGOV | Cash | **primary** | 0.09% | 0.01% | $1,891m | 0.45% | 0.00% | $99.7bn | [iShares 0-3m Treasury](https://www.ishares.com/us/products/314116/ishares-0-3-month-treasury-bond-etf) |

DBC's expense figure decomposes as a 0.85% management fee plus a 0.04% estimated futures brokerage fee, giving 0.89% total and 0.82% net of the current waiver, all from the Invesco product data service.

### 1.3 Vehicle selection, and where the desk departs from habit

Where the IPS names two vehicles, the desk designates the **cheaper one to hold** as primary and the **deeper one** as the size vehicle. A perpetual fund pays the expense ratio every year and pays the spread only on turnover, so the arithmetic is one-sided.

| Line | Primary over alternate | Annual saving on the policy weight |
|---|---|---:|
| US equity | VTI 0.03% over SPY 0.0945% | 6.45bp on 38% = **USD 2.08m/yr** |
| Developed ex-US | VEA 0.03% over EFA 0.32% | 29bp on 20% = **USD 4.93m/yr** |
| EM equity | VWO 0.06% over EEM 0.72% | 66bp on 12% = **USD 6.73m/yr** |
| Cash | SGOV 0.09% over BIL 0.1353% | 4.53bp on the balance held |

Total identified fee saving: **USD 13.7m a year**, or 16bp of NAV, against a spread differential measured in tenths of a basis point paid only on turnover. That is more than a fifth of the 0.40% fee assumption in the IPS Section 3.2 return requirement. The Committee should note that VWO tracks FTSE rather than MSCI, so it includes onshore China A-shares and excludes South Korea. That is an index decision for the Committee, and the desk flags it rather than making it silently.

### 1.4 Why institutional single-stock cost models do not apply here

The Committee will have seen 10bp to 30bp quoted for equity portfolio transitions, and will have seen Kissell-style or Almgren-Chriss market-impact estimates quoted for institutional single-stock trading. **Neither applies to this fund, and using either would overstate the cost of the tactical programme by an order of magnitude on the cheap lines.** Three reasons.

**The impact function has the wrong argument.** Almgren-Chriss and its descendants model the price concession from consuming a fraction of a security's own daily volume, because a single stock has one order book and that book is the entire supply of liquidity. An ETF has two markets. When secondary liquidity is exhausted, an authorised participant creates or redeems shares in kind against the underlying basket, so the relevant capacity is the **underlying market's** capacity rather than the wrapper's. DBC's USD 27.3m of secondary ADV understates its true capacity by a wide margin, because its underlying is a basket of WTI, Brent, gold, copper and grain futures, each of which trades billions of dollars a day.

**The cost is bounded above by arbitrage, not by impact.** An ETF's trading price cannot stray far from the cost of assembling its basket plus the creation fee, because that gap is exactly the arbitrage. Single-stock impact has no such ceiling.

**The transition-management numbers price a different problem.** The 10bp to 30bp range quoted for portfolio transitions covers the liquidation of a legacy segregated portfolio of individual securities, including its illiquid tail, its sector concentration and the information leakage from a known forced seller. This fund never holds individual securities. It holds nine exchange-traded wrappers, and its trades are anonymous, small relative to the wrappers, and free of any legacy tail.

What does apply is the ETF-specific evidence, and it cuts the other way on the expensive lines.

### 1.5 The published evidence on ETF transaction costs

**Angel, James J., Todd J. Broms and Gary L. Gastineau (2016), "ETF Transaction Costs Are Often Higher Than Investors Realize", *Journal of Portfolio Management* 42(3), Spring 2016, pp. 65–75.** [Free PDF.](https://centerforfinancialstability.org/etfs/ETFAnalysis/etf-trans-costs-are-often-higher-than-inv-realize-spring2016.pdf) The single most useful paper for this desk. Their finding, taking EEM as the worked example: the fund "generally shows a one or two cent bid–ask spread, or about 3 basis points", while during 2014 "the closing price deviated from the NAV by an average of 48 basis points, nearly one half of one per cent". The median deviation was 15bp, and on 5% of observations, "nearly 75,000 observations", the deviation was "136 basis points (1.36%) or more". On their worked date the closing-price discount was 61bp, and they conclude that "the average investor's trading cost for this fund is likely to be over 50 basis points". Their general verdict: "the cost to trade most index ETFs is more than a few basis points."

Their Exhibits 4 and 5 make the structural point directly, comparing the weighted bid-ask spread of the **underlying basket** against the spread of the **fund shares**. For the equity funds the fund spread is the smaller of the two by a wide margin. That gap is the wrapper's benefit in normal conditions and its liability in stress, when the wrapper reprices before the basket does.

**Petajisto, Antti (2011), "The index premium and its hidden cost for index funds", *Journal of Empirical Finance* 18(2), pp. 271–288.** [Author copy.](https://www.petajisto.net/papers/petajisto%202011%20jef%20-%20hidden%20cost%20for%20index%20funds.pdf) The reference for index-fund rebalancing costs as distinct from investor trading costs. Price impact from announcement to effective day averaged +8.8% for S&P 500 additions and −15.1% for deletions over 1990 to 2005, and the resulting recurring "index turnover cost" borne by a mechanical indexer is **0.21% to 0.28% a year for the S&P 500 and 0.38% to 0.77% for other indices**. This is a cost the fund pays inside the tracking difference of every vehicle it holds, whether or not the desk trades, and it is one reason the desk does not treat the expense ratio as the full holding cost.

**Bond ETF primary-market frictions.** Research on custom creation baskets finds US-listed corporate bond ETFs pay on the order of **48bp a year in costs embedded in the basket-selection process**, and that investors face roughly 1.3bp wider effective spreads on redemption days ([ETF Stream summary of the underlying academic work](https://www.etfstream.com/articles/hidden-costs-for-bond-etf-investors-revealed-in-academic-study); see also [Journal of Financial and Quantitative Analysis, "ETFs, Creation and Redemption Processes, and Bond Liquidity"](https://www.cambridge.org/core/journals/journal-of-financial-and-quantitative-analysis/article/abs/etfs-creation-and-redemption-processes-and-bond-liquidity/1044758A6030F7EF31F502994E1F07AB)). This is why the adopted LQD and HYG costs sit at twelve and twenty-four times the published half-spread rather than at the half-spread.

### 1.6 Building the adopted vector

The rule the desk applies: **the half-spread is a floor and never the answer.** Adopted cost equals half the quoted spread, plus the market maker's premium for exposure the wrapper cannot hedge cleanly during US hours, plus the primary-market frictions that bind at USD 8.5m and above.

| Line | Primary | Quoted spread | Half-spread | **Adopted one-way** | Multiple | What the multiple buys |
|---|---|---:|---:|---:|---:|---|
| us_equity | VTI | 0.55bp | 0.275bp | **1.50bp** | 5.5x | Nothing structural. Deliberately conservative so the vector never flatters the cheapest trade. |
| dev_ex_us | VEA | 1.42bp | 0.710bp | **4.00bp** | 5.6x | Europe and Japan are shut when the US trades. The maker carries overnight beta and FX. EFA's +0.22% premium is the same mechanism. |
| em_equity | VWO | 1.70bp | 0.850bp | **8.00bp** | 9.4x | The above plus emerging FX, settlement frictions and a basket that cannot be hedged intraday. Angel et al. put EEM's realised NAV deviation at 48bp average; the desk has no evidence it trades inside a sixth of that at size. |
| ust_duration | IEF | 1.00bp | 0.500bp | **3.00bp** | 6.0x | Thirteen holdings, all Treasuries, deepest cash bond market there is. Allows for the creation fee and a wider screen on an FOMC day. |
| us_ig | LQD | 1.00bp | 0.500bp | **6.00bp** | 12.0x | 3,144 corporate bonds, most of which do not trade on a given day. The 1bp screen is the wrapper's spread, not the basket's. |
| us_hy | HYG | 1.00bp | 0.500bp | **12.00bp** | 24.0x | 1,328 high yield bonds. In stress the ETF becomes the price-discovery instrument for the asset class and its own spread widens by a multiple, which is exactly when a risk-reducing trade is wanted. Desk assumes 3x in a stressed tape. |
| commodities | DBC | 4.00bp | 2.000bp | **25.00bp** | 12.5x | The only line where secondary capacity binds. Closed at a 43.5bp discount to NAV on 27 July 2026, GSG at 50bp, on a day the index fell 3.02%. Creation against futures is the release valve and carries the creation fee and the roll. |
| listed_re | VNQ | 1.02bp | 0.510bp | **5.00bp** | 9.8x | Roughly 160 listed US REITs, ordinary liquid equities. A 2% weight, not the vehicle, is what makes this line awkward. |
| cash | SGOV | 1.00bp | 0.500bp | **1.00bp** | 2.0x | Zero-to-three-month bills, effectively frictionless. Held above zero so that no optimiser treats cash as a free place to park risk. |

`tests/check_implementation.py` asserts each of these against the published half-spread, so the vector cannot silently drift below the evidence.

### 1.7 The asymmetry, stated plainly

**A 100bp allocation move is USD 8,500,000.** As a share of a day's trading in each vehicle:

```
SPY    0.02%  |
LQD    0.29%  |
HYG    0.35%  |
TLT    0.42%  |
SGOV   0.45%  |
EEM    0.47%  |
EFA    0.63%  |
VTI    0.73%  |
BIL    1.00%  |
VEA    1.16%  |
IEF    1.54%  |
VWO    1.88%  |
VNQ    2.79%  ||
DBC   31.10%  |||||||||||||||||||||||||||||||
GSG   41.06%  |||||||||||||||||||||||||||||||||||||||||
```

Eight of the nine lines absorb a full 100bp tactical move inside the first hour of trading and cost less than 12bp one-way. The ninth does not. **A 3pp exit from commodities is USD 25,500,000, which is 93% of DBC's entire median daily volume**, and the IPS range allows commodities to run to 8%, so a full traverse of the range is USD 42,500,000, or roughly 1.6 days of DBC and 0.9 days of DBC and GSG combined.

The desk therefore imposes an operating rule, which the Committee is asked to ratify:

> **Commodity orders above USD 8,500,000 are worked over a minimum of two sessions, split across DBC and GSG, with a participation cap of 15% of each vehicle's trailing 20-day volume. Orders above USD 20,000,000 are pre-negotiated with an authorised participant as a risk price against the futures basket rather than worked on screen.**

Which lines carry the turnover depends on which signals fire, and the two cases are not symmetric.

- **A risk-off signal that raises cash** sells across all eight risk lines pro rata. On a 5pp de-risking, the weighted cost is roughly 4.4bp one-way on the sale plus 1bp on the bill purchase, about **0.27bp of NAV, USD 23,000**. Cheap, because most of the turnover falls on the cheap equity lines.
- **A commodity or credit signal** concentrates the turnover on the expensive lines. A 3pp commodity exit costs 25bp on the way out and 1bp into bills, **0.78bp of NAV, USD 66,300**, on a position worth USD 25.5m. That is 2.6% of the position's value in round-trip terms if the desk reverses within the year.

The practical consequence for the tactical programme: **a commodity view must be worth more than 50bp of the commodity line to survive its own round trip, while a US equity view need only be worth 3bp.** The desk recommends that any tactical proposal touching commodities or high yield carry its round-trip cost against its expected value explicitly, which IPS Section 4.3 already requires in reporting and which this desk asks be required at the proposal stage as well.

### 1.8 The futures alternative, and why it is constrained

The IPS Section 1.2 and 3.5 permit exchange-traded futures. The desk examined them and recommends against a cash-equitised overlay, for reasons of mandate rather than economics.

**Where a clean futures proxy exists.** CME E-mini S&P 500 (ES) is the deepest equity index contract in the world, with a USD 50 multiplier and a 0.25-index-point minimum tick worth USD 12.50 per contract, and average daily volume of 1.81 million contracts in 2023 ([CME Group](https://www.cmegroup.com/markets/equities/sp/micro-e-mini-sandp-500.html); volume figure via [NinjaTrader contract specs](https://ninjatrader.com/futures/futures-contracts/equity-index/e-mini-s-p-500/), `[RECALLED]` as to the exact 2026 figure). Executing US equity exposure through ES costs well under a basis point one-way in commission and half-tick. Treasury duration has ZN and ZB. Developed ex-US has liquid contracts on the individual index families rather than one clean EAFE contract, and EM has a listed MSCI EM contract of much thinner depth.

**Where no clean proxy exists.** There is no exchange-traded futures contract on US investment grade credit, on US high yield, or on listed real estate that is deep enough to carry a USD 68m or USD 42m position. Credit exposure would have to be taken through CDX index swaps, which are over-the-counter derivatives and outside the "exchange-traded futures" permission at IPS Section 3.5. Broad commodity exposure would require a basket of two dozen individual contracts and their rolls, replacing one vehicle with a standing operational burden.

**Why the mandate constrains it anyway.** The desk is obliged to be precise about the legal position rather than to repeat the IPS's own shorthand. Gains and losses on commodity and financial futures held by a tax-exempt organisation are **excluded from unrelated business taxable income under IRC §512(b)(5)** as gains from the sale or exchange of property, and a long futures position does not constitute acquisition indebtedness under §514, because it involves no borrowing in the traditional sense ([IRS EO technical topic on IRC 514](https://www.irs.gov/pub/irs-tege/eotopicn86.pdf); [IRS, unrelated business income from debt-financed property](https://www.irs.gov/charities-non-profits/unrelated-business-income-from-debt-financed-property-under-irc-section-514)). The Treasury regulations similarly exclude income and gain from notional principal contracts from UBTI.

**So the tax reason the IPS gives for the leverage prohibition does not, on its own, reach a fully cash-collateralised futures overlay.** What does reach it is the operative sentence of IPS Section 3.5: *"Gross exposure does not exceed net asset value."* An overlay that adds ES notional on top of a fully invested physical portfolio raises gross exposure above NAV and breaches that sentence, and Section 3.5 states that the constraint "is not a risk preference that analysis may trade against". It sits at rank 2 of the constraint hierarchy, alongside legal and board exclusions, and rank 2 is not negotiable.

The desk's conclusion, and it is a narrow one: **futures may be used only as a substitute for physical exposure, never as an addition to it.** A permitted use is holding ES against bills in place of holding VTI, where gross exposure is unchanged. A prohibited use is equitising a cash balance that the desk has deliberately raised to cut risk, because that both raises gross exposure and defeats the purpose of the cash. Given that the substitution saves perhaps 1bp on a line that already costs 1.5bp, and introduces roll risk, margin operations, basis risk against the S&P 500 rather than the total market, and a quarterly roll the fund does not currently run, **the desk recommends no futures use at present** and asks that any future proposal be brought as a change to this paper rather than as a trade. The Committee should also note that the tax analysis above is a desk reading of published IRS material and should be confirmed with counsel before any first use.

---

## 2. Rebalancing rule design

### 2.1 What sets the corridor width, and which way each determinant pushes

The canonical practitioner reference is **Masters, Seth J. (2003), "Rebalancing", *Journal of Portfolio Management* 29(3), Spring 2003, pp. 52–57** ([publisher page](https://jpm.pm-research.com/content/29/3/52)). Its abstract sets out the aim: "Most rebalancing policies use arbitrary 'one size fits all' rules... The author's simpler methodology allows investors to tailor their rebalancing policies to their risk tolerance, the cost of rebalancing, and the risk characteristics of each asset class in the portfolio. This approach addresses not only when to rebalance, but also how far back to rebalance."

The paper itself is paywalled at pm-research, ProQuest and ResearchGate. The desk was unable to read it directly and flags that. The formulation that actually circulates, and which the desk adopts, is the CFA Institute curriculum's, which is open and explicit ([Principles of Asset Allocation, CFA Institute refresher reading](https://www.cfainstitute.org/insights/professional-learning/refresher-readings/2026/principles-asset-allocation)). There are **five** determinants, not four, and two of the directions are commonly stated backwards.

| Determinant | Direction on corridor width | Reason |
|---|---|---|
| **Transaction cost** | **Positive.** Higher cost, wider corridor. | High costs set a high hurdle for the benefit of rebalancing to clear. |
| **Risk tolerance** | **Positive.** More tolerant, wider corridor. | Lower sensitivity to straying from target. |
| **Correlation with the rest of the portfolio** | **Positive.** Higher correlation, wider corridor. | When asset classes move together, further divergence from target is less likely. |
| **Asset-class volatility** | **Inverse.** Higher volatility, narrower corridor. | A given move away from target is more costly for a volatile line, because further divergence becomes more likely. |
| **Volatility of the rest of the portfolio** | **Inverse.** | Same mechanism, from the other side. |

The direction on **transaction cost is positive**, and it is the one determinant where the theory and the practitioner literature agree without qualification. **Leland, Hayne E. (December 1999), "Optimal Portfolio Management with Transactions Costs and Capital Gains Taxes", Haas School of Business working paper RPF-290** ([free full PDF at eScholarship](https://escholarship.org/uc/item/0fw6k0hm); [SSRN 206871](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=206871)) gives the sharp form. From his comparative statics at page 26:

> "(i) The size of the optimal no-trade interval (w_max − w_min) is **proportional to the cube root of transactions costs**."

and, in his own gloss, "doubling transactions costs will increase the no-trade interval by a factor of about 2^(1/3) = 1.26." The same cube-root exponent falls out of **Constantinides, George M. (1986), "Capital Market Equilibrium with Transaction Costs", *Journal of Political Economy* 94(4), pp. 842–862** ([DOI 10.1086/261410](https://www.journals.uchicago.edu/doi/abs/10.1086/261410)) and **Davis, M.H.A. and A.R. Norman (1990), "Portfolio Selection with Transaction Costs", *Mathematics of Operations Research* 15(4), pp. 676–713** ([INFORMS](https://pubsonline.informs.org/doi/10.1287/moor.15.4.676)), where the no-trade region width is O(ε^(1/3)) in the proportional cost ε and the welfare loss is O(ε^(2/3)). The clearest open restatement is Guasoni and Muhle-Karbe (2012), [*Portfolio Choice with Transaction Costs: a User's Guide*](https://arxiv.org/abs/1207.7330): "optimal portfolios entail a no-trade region... trading should merely take place at its boundaries. The no-trade region is wide, even for small transaction costs."

**On volatility the two frameworks disagree, and the desk resolves the disagreement in favour of the mandate.** In the utility-maximisation literature the target weight itself moves with volatility, and the dependence of band width on σ is non-monotone: Guasoni and Muhle-Karbe show the half-width scales as [π\*²(1−π\*)²]^(1/3), which peaks at a 50% weight and vanishes as the weight approaches zero or one. In the CFA and Masters tracking-error framework the target is **exogenous**, set by the Board at IPS Section 4.1, and the loss function is λ(w−w\*)′V(w−w\*), so higher V unambiguously raises the cost of any given deviation and tightens the band. This fund's target is exogenous and its tracking-error budget is a rank-4 hard constraint, so **the tracking-error framework governs and higher volatility means a narrower corridor here.**

### 2.2 Trade to the edge, not to the target

**Leland (1999)**, verbatim from his abstract and page 3:

> "We show that the optimal policy involves a no-trade region about the target stock proportions... When proportions are outside the region, trading should be undertaken to move the ratio to the region's boundary... Compared to the current practice of periodic rebalancing of all assets to their target proportions, **the optimal strategy will reduce turnover by almost 50%**."

> "When the risky asset ratio moves outside the no-trade interval, it should be adjusted back to **the nearest edge of the interval, not to the target proportion**."

His footnote 1 carries the reason in one sentence: the loss from diverging from the optimal ratio is approximately U-shaped and flat at the bottom, so moving the last small distance to the target gains a **second-order** amount of utility and costs a **first-order** amount in trading. **Donohue, Christopher and Kenneth Yip (2003), "Optimal Portfolio Rebalancing with Transaction Costs", *Journal of Portfolio Management* 29(4), Summer 2003, pp. 49–63** ([publisher page](https://jpm.pm-research.com/content/29/4/49)) confirm Leland's result, characterise the shape and size of the no-trade region, and reach the same conclusion on destination.

### 2.3 Should corridors be uniform across lines? No

The CFA curriculum's own critique of a fixed uniform corridor gives three grounds, and all three apply to this fund. A uniform band takes no account of differences in transaction cost across lines, so "private equity has much higher transaction costs than inflation-protected bonds and should have a wider corridor, all else equal". It takes no account of differences in volatility, so "rebalancing is most likely to be triggered by the highest volatility asset class". And it takes no account of correlations.

The mechanism that handles small weights is the distinction between **absolute** corridors, stated in percentage points of NAV, and **relative** corridors, stated as a percentage of the line's own policy weight. The practitioner standard is the **5/25 rule**: rebalance when a line moves 5 percentage points absolute **or** 25% relative, whichever triggers first ([White Coat Investor write-up](https://www.whitecoatinvestor.com/rebalancing-the-525-rule/); attribution to Larry Swedroe is `[RECALLED]` and the source gives none). A 5% line with a ±5pp absolute corridor could go to zero or double before triggering, which is absurd. Expressed relatively its band is ±1.25pp, **narrower in absolute terms and wider in relative terms**, which is precisely the shape the small lines need. **Daryanani, Gobind (2008), "Opportunistic Rebalancing", *Journal of Financial Planning* 21(1), pp. 48–61** ([FPA](https://www.financialplanningassociation.org/article/journal/JAN08-opportunistic-rebalancing-new-paradigm-wealth-managers)) finds a **20% relative** band optimal over rolling five-year periods 1992 to 2004, with 10% to 15% and 25% both worse, and coins the slogan "rebalance less frequently, but look more frequently".

So the answer to the question is no, and the reason is that a 2% policy weight in listed real estate and a 38% weight in US equity differ on every one of the five determinants at once. Uniform corridors would either strangle the small lines or abandon the large ones.

### 2.4 Threshold versus calendar, and by how much

The honest answer from the evidence is **the difference is small, and the point of any rebalancing discipline is risk control rather than return.**

**Vanguard, Jaconetti, Kinniry and Zilbering (2010), "Best practices for portfolio rebalancing"** ([free PDF](https://static.squarespace.com/static/53068354e4b083d9ce6ab0da/53d2f42ae4b05818c5593360/53d2f42be4b05818c5593de5/1326929360787/01_2012_Rebalancing_Vanguard.pdf)). 60/40 US, 1926 to 2009, before costs and taxes:

| Monitoring | Threshold | Avg equity | Turnover | Events | Return | Volatility |
|---|---:|---:|---:|---:|---:|---:|
| Monthly | 0% | 60.1% | 2.7% | 1,008 | 8.5% | 12.1% |
| Monthly | 5% | 61.2% | 1.7% | 58 | 8.6% | 12.2% |
| Quarterly | 5% | 60.9% | 1.7% | 50 | 8.8% | 12.1% |
| Annually | 5% | 60.7% | 1.6% | 28 | 8.6% | 11.8% |
| Annually | 10% | 63.0% | 1.4% | 15 | 8.7% | 12.1% |
| **Never** | — | **84.1%** | 0.0% | 0 | **9.1%** | **14.4%** |

Verbatim: *"The primary goal of a rebalancing strategy is to minimize risk relative to a target asset allocation, rather than to maximize returns,"* and *"annual or semiannual monitoring, with rebalancing at 5% thresholds, produces a reasonable balance between risk control and cost minimization."*

The 2019 update, **McNamee, Paradise and Bruno, "Getting back on track: A guide to smart rebalancing"** ([free PDF](https://www.vanguardsouthamerica.com/content/dam/intl/americas/documents/latam/en/sa-2123766-getting-back-on-track.pdf)), extends to 1926 to 2018 on a tax-adjusted basis. Across strategies ranging from 1,116 rebalancing events to 14, tax-adjusted returns span **8.19% to 8.39%** and Sharpe ratios span 0.50 to 0.51. Their sentence is the one to put in front of trustees: *"What's remarkable is that starkly different strategies were equally successful in controlling risk."* Never rebalancing returned 8.74% at 14.0% volatility with an 85% average equity weight, which is a different portfolio rather than a better one.

Two later strands qualify the "no difference" verdict without overturning it. **Sun, Fan, Chen, Schouwenaars and Albota (2006), "Optimal Rebalancing for Institutional Portfolios", *Journal of Portfolio Management* 32(2), Winter 2006, pp. 33–43** ([free PDF](https://people.csail.mit.edu/fan/papers/JPM_Winter2006_opt_rebalancing.pdf)) put tracking error and trading cost in common certainty-equivalent units and solve by dynamic programming. Their Exhibit 9, five risky assets, 20 years, 10,000 paths, annualised aggregate cost in bp:

| Strategy | Quadratic | Power | Log wealth |
|---|---:|---:|---:|
| **Optimal DP** | **5.47** | **4.54** | **6.72** |
| 5% tolerance | 7.99 | 6.01 | 12.38 |
| Annual | 8.39 | 6.84 | 10.22 |
| Quarterly | 13.96 | 11.78 | 16.67 |
| Monthly | 23.67 | 20.05 | 28.15 |
| No trading | 30.18 | 25.99 | 30.52 |

Searching over parameters under quadratic utility, the best calendar interval is **18 months at 7.53bp** and the best tolerance band is **9% at 6.25bp**, against 5.47bp for the optimum. Two findings matter for this desk. Tolerance bands beat calendars at every utility specification. And "in most cases, **partial rebalancing** can provide nearly the same utility as full rebalancing while saving on transaction costs". Their headline improvement over annual rebalancing is **35 percent** of the expected loss under log-wealth utility, which is frequently misquoted as 35 basis points; it is not.

**Vanguard, "The rebalancing edge" (December 2024)** ([free PDF](https://corporate.vanguard.com/content/dam/corp/research/pdf/the_rebalancing_edge_optimizing_target_date_fund_rebalancing_through_threshold_based_strategies.pdf)) quantifies the destination question in production terms. Their "200/175" rule sets a 200bp threshold with a **175bp destination**, so a 60/40 portfolio breaching 62% equity rebalances to 61.75% rather than to 60%: *"Selecting a destination closer to the threshold can help reduce the size of rebalancing trades and lower the associated transaction costs."* Expected annual benefit of threshold-based over monthly is **15bp to 22bp** in accumulation.

**Does the destination matter empirically? Barely.** **Meketa Investment Group, "Rebalancing" (June 2018)** ([free PDF](https://meketa.com/wp-content/uploads/2020/03/Rebalancing.pdf)) tested target, midpoint and endpoint destinations on a 60/40 global portfolio from January 1979 to March 2018. At a ±5% band the cost-adjusted returns were **9.21% to target, 9.28% to midpoint, 9.25% to endpoint**, and they found "little difference between target, midpoint, and endpoint rebalancing from a performance standpoint". What differs is the **number of trades**, which is what makes the choice a transaction-cost-structure decision rather than a return decision.

Vanguard (2010) states the structural rule precisely: *"When trading costs are mainly **fixed**... rebalancing to the target allocation is optimal... However, when trading costs are mainly **proportional** to the size of the trade... rebalancing to the closest rebalancing boundary is optimal... If both fixed and proportional costs exist, the optimal strategy is to rebalance to some intermediate point."*

**This fund's costs are almost entirely proportional.** ETF commissions are negligible at institutional scale and the cost is the spread and the creation friction, both proportional. Theory therefore points to trading to the near edge. **The desk nevertheless recommends rebalancing to target**, for one reason that overrides it: the IPS minimum trade size is 50bp, every corridor is set at or above 50bp, and trading to the edge would generate a trade of approximately zero, which the mandate forbids outright. Trading to the edge only works when the band is many multiples of the minimum trade. It is not, here, by construction. The desk records this as a live trade-off and would revisit it if the minimum trade were relaxed.

### 2.5 Rebalancing is a short straddle, and the Committee should know it

**Granger, Greenig, Harvey, Rattray and Zou (2014), "Rebalancing Risk"** ([SSRN 2488552](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2488552)), restated verbatim in **Rattray, Granger, Harvey and Van Hemert (2020), "Strategic Rebalancing", *Journal of Portfolio Management*, Multi-Asset Special Issue 2020, pp. 10–31** ([free PDF](https://people.duke.edu/~charvey/Research/Published_Papers/P145_Strategic_rebalancing.pdf)):

> "Granger et al. (2014) formally showed that rebalancing is similar to starting with a buy-and-hold portfolio and adding a **short straddle** (selling both a call and a put option) on the relative value of the portfolio assets. The option-like payoff to rebalancing induces **negative convexity** by magnifying drawdowns when there are pronounced divergences in asset returns."

Their two-period result is R_rebal − R_hold = −w_S·w_B·κ₁·κ₂ in the stock-minus-bond return κ, which is negative when relative performance trends. Empirically the gap over October 2007 to February 2009 was about 5.3 percentage points, with the monthly-rebalanced portfolio's maximum drawdown roughly 5pp worse. The origin of the argument is **Perold and Sharpe (1988), "Dynamic Strategies for Asset Allocation", *Financial Analysts Journal* 44(1), pp. 16–27** ([free mirror](https://docslib.org/doc/7623938/dynamic-strategies-for-asset-allocation)): constant-mix is concave, buy-and-hold is linear, CPPI is convex.

**This matters directly for the IPS Section 3.3 drawdown limit.** The Board has set a hard −20% peak-to-trough limit, and a disciplined rebalancing policy makes the tail worse in a sustained trending decline by buying the falling asset all the way down. The desk raises this because the constraint hierarchy puts the drawdown limit at rank 3, above the tracking-error budget and above the return objective, and a rebalancing rule that quietly worsens the thing at rank 3 should be adopted with eyes open. The desk's mitigation is **not** to abandon rebalancing. It is the corridor set below, which is tighter on the high-volatility lines so that the short-straddle position is written on smaller notional, plus the cash line, which IPS Section 4.1 explicitly makes available as a risk-reduction lever and which is the cheapest one on this cost vector at 1bp.

### 2.6 The 50bp minimum trade, and which lines it bites on

IPS Section 4.2 sets a minimum trade of 50bp of NAV, USD 4,250,000, and Section 4.5 closes the loop: *"a corridor narrower than the minimum trade cannot be acted on."* This is arithmetic rather than judgement. If the corridor half-width is c and the desk rebalances to target on breach, the trade is exactly c. If c is below 0.50pp the trade is below the minimum and the mandate forbids it, so the corridor is decorative.

**Which lines does it bite on?** The desk answers it two ways, because the two answers differ and the difference is the point.

**On pure risk grounds.** Equalising each line's contribution to drift-induced tracking error at 7bp gives a corridor of 7 / (active volatility). Using the three-year active volatilities computed at Section 2.7:

| Line | Active vol | Equal-risk corridor | Below 50bp? |
|---|---:|---:|---|
| Commodities | 18.70% | **0.37pp** | **Yes** |
| Listed real estate | 13.17% | **0.53pp** | At the floor |
| UST duration | 11.10% | 0.63pp | No |
| Cash | 11.11% | 0.63pp | No, but structurally floored |
| US IG | 9.51% | 0.74pp | No |
| EM equity | 9.26% | 0.76pp | No |
| US HY | 7.39% | 0.95pp | No |
| Developed ex-US | 6.90% | 1.01pp | No |
| US equity | 6.26% | 1.12pp | No |

**On the relative-corridor ground.** A 25% relative corridor, which is the relative leg of the 5/25 rule and the cap the desk applies, gives 0.50pp on the 2% listed real estate weight and 0.75pp on the 3% commodity weight. The listed real estate cap and the minimum trade coincide exactly at 0.50pp.

**So the minimum trade bites on three lines, and for three different reasons.**

1. **Commodities.** Risk wants 0.37pp. The minimum trade forbids anything under 0.50pp. Cost, via Leland's cube root on a 25bp line, pushes it back out to 0.75pp. The mandate's own minimum trade overrides the risk analysis here, and the Committee should understand that commodities carry a wider band than the risk numbers justify because the mandate will not permit a narrower one.
2. **Listed real estate.** The equal-risk corridor of 0.53pp, the 25%-relative cap of 0.50pp, and the 50bp minimum all land on top of each other. The floor is exactly binding. A ±0.50pp corridor on a 2% weight is a **±25% relative corridor**, which is very wide in relative terms and very narrow in absolute terms. The resolution is to accept it and say so: this line may drift from 1.5% to 2.5% of NAV, a 50% swing in the position, without triggering anything, because the alternative is trades that cost more in turnover than the risk they remove. On a 5bp one-way cost, a 0.50pp trade costs 0.025bp of NAV, USD 2,125, which is real money spent on a position worth USD 17m.
3. **Cash.** The policy weight is 0% and the range floor is 0%, so a symmetric band is impossible and the floor binds by construction. The desk resolves this with a **one-sided upward band of 0.50pp**: cash may accumulate to 0.50% of NAV from dividends and coupons without any action, and any deliberate cash holding above that is a tactical position governed by the 200bp tracking-error budget rather than by this table. The code and the check both handle this explicitly rather than silently.

By the same arithmetic, the minimum trade would bite on **any line with a policy weight below 2%**, since 25% of 2% is exactly 50bp. Listed real estate is the smallest non-zero weight in the policy portfolio and is therefore the boundary case. If the Committee ever adds a line at 1% or 1.5%, that line cannot be corridor-managed at all and must be run as a discretionary position or dropped.

### 2.7 The adopted corridor table

The rule, applied mechanically and then rounded to the nearest 0.25pp:

```
c_i = clip( 5 · (one_way_bps_i)^(1/3) / active_vol_i ,
            floor = 0.50pp                                  (IPS 4.2 minimum trade)
            cap   = min( 25% of policy weight ,             (5/25 relative leg)
                         80% of distance to the nearer IPS range edge ) )
```

The cube root on cost is Leland's exponent, taken from the source rather than chosen for convenience. **Active volatility** is the annualised standard deviation of the line's daily log return minus the policy portfolio's daily log return, over the 750 common sessions from 31 July 2023 to 28 July 2026, computed on the primary vehicles from Yahoo Finance adjusted closes with the policy portfolio built at the IPS Section 4.1 weights. The policy portfolio's own realised volatility over that window was **11.10%**.

That single statistic carries three of the five determinants and carries each in the direction the curriculum requires. Higher asset-class volatility raises active volatility and narrows the corridor. Higher volatility of the rest of the portfolio raises active volatility and narrows the corridor. Higher correlation with the rest of the portfolio **lowers** active volatility and widens the corridor. Transaction cost enters separately through the cube root, and risk tolerance enters through the constant 5, which was set so that the whole corridor set consumes about one seventh of the tracking-error budget at its worst.

| Line | Policy | IPS range | Active vol | Cost | **Corridor ±pp** | Relative | **Band** | Trade on breach | Drift TE at edge |
|---|---:|---|---:|---:|---:|---:|---|---:|---:|
| US equity | 38% | 28–48 | 6.26% | 1.5bp | **±1.00** | ±2.6% | 37.00–39.00 | USD 8.50m | 6.3bp |
| Developed ex-US | 20% | 12–28 | 6.90% | 4.0bp | **±1.25** | ±6.3% | 18.75–21.25 | USD 10.63m | 8.6bp |
| EM equity | 12% | 5–19 | 9.26% | 8.0bp | **±1.00** | ±8.3% | 11.00–13.00 | USD 8.50m | 9.3bp |
| UST duration | 12% | 5–22 | 11.10% | 3.0bp | **±0.75** | ±6.3% | 11.25–12.75 | USD 6.38m | 8.3bp |
| US IG | 8% | 3–13 | 9.51% | 6.0bp | **±1.00** | ±12.5% | 7.00–9.00 | USD 8.50m | 9.5bp |
| US HY | 5% | 0–10 | 7.39% | 12.0bp | **±1.25** | ±25.0% | 3.75–6.25 | USD 10.63m | 9.2bp |
| Commodities | 3% | 0–8 | 18.70% | 25.0bp | **±0.75** | ±25.0% | 2.25–3.75 | USD 6.38m | 14.0bp |
| Listed real estate | 2% | 0–6 | 13.17% | 5.0bp | **±0.50** | ±25.0% | 1.50–2.50 | USD 4.25m | 6.6bp |
| Cash | 0% | 0–10 | 11.11% | 1.0bp | **+0.50** one-sided | n/a | 0.00–0.50 | USD 4.25m | 5.6bp |

**Every corridor is at least 50bp wide, so every breach generates an actionable trade.** Every band sits strictly inside its IPS range, with a minimum of 1.50pp of headroom on the tightest line. With every line simultaneously at its corridor edge, drift-induced tracking error is **26.7bp against the 200bp budget**, which leaves 87% of the budget for deliberate views rather than for drift the desk chose not to fix. That figure is an upper bound, since the drifts are negatively correlated by construction because the weights sum to one.

The cost of the discipline is negligible. A full reset from every corridor edge at once costs **0.595bp of NAV, USD 50,575**, which is 0.13% of the annual distribution.

Note what the cost scaling does and does not do. US equity, the largest line, carries the **narrowest** corridor in relative terms at ±2.6%, because it is the cheapest line to trade and the least volatile against the portfolio. High yield carries the widest at ±25% relative, because at 12bp it is the second most expensive line to trade. That inversion of the usual instinct, where the big line gets the wide band, is the whole content of Leland's result.

### 2.8 The rest of the rebalancing policy

**Monitoring.** Monthly, per IPS Section 4.5, tested against the table above and against the IPS Section 4.1 ranges independently. The desk also runs the range test daily on a lights-out basis, because a range breach is a compliance event under Section 4.1 whether or not it is a monitoring day.

**Destination.** To target, per Section 2.4. Recorded as a deliberate departure from the Leland and Donohue-Yip result, forced by the 50bp minimum trade.

**Annual reset.** IPS Section 4.5 requires a reset to policy at least annually. The desk proposes **30 June**, aligned to the fiscal year end and the IPS review cycle, executed over the five sessions ending 30 June with the commodity leg worked over the full five per the Section 1.7 rule. Cost of a full reset from the corridor edges is under USD 51,000, so the annual reset is not a material cost item and there is no case for skipping it.

**The USD 60,000,000 campaign inflow in year three.** This is 7.06% of current NAV and IPS Section 3.4 states it "is staged into policy weights over a defined window. It is not timed against a market view." The desk proposes:

| Line | Policy | Inflow allocation | One-way cost | Cost of leg | Days of ADV |
|---|---:|---:|---:|---:|---:|
| US equity | 38% | USD 22.80m | 1.5bp | USD 3,420 | 0.02 (SPY) |
| Developed ex-US | 20% | USD 12.00m | 4.0bp | USD 4,800 | 0.89 (EFA+VEA) |
| EM equity | 12% | USD 7.20m | 8.0bp | USD 5,760 | 0.32 (EEM+VWO) |
| UST duration | 12% | USD 7.20m | 3.0bp | USD 2,160 | 0.28 (IEF+TLT) |
| US IG | 8% | USD 4.80m | 6.0bp | USD 2,880 | 0.002 |
| US HY | 5% | USD 3.00m | 12.0bp | USD 3,600 | 0.001 |
| Commodities | 3% | USD 1.80m | 25.0bp | USD 4,500 | **0.04 (DBC+GSG)** |
| Listed real estate | 2% | USD 1.20m | 5.0bp | USD 600 | 0.004 |
| **Total** | **100%** | **USD 60.00m** | **4.6bp wtd** | **USD 27,720** | |

Staged in **four equal weekly tranches of USD 15,000,000** over the twenty sessions following receipt, each tranche allocated at policy weights, with cash held in SGOV between tranches. Four tranches rather than one because a single USD 1.8m commodity clip is fine but the desk prefers not to run any leg above 10% of a vehicle's daily volume, and four rather than twelve because the drag from holding equity risk in bills for a quarter dominates the execution saving. The entire exercise costs **USD 27,720, 0.33bp of the inflow**, which the desk notes is roughly one twentieth of a single month of the annual distribution and should not be a subject of debate.

---

## 3. The reporting standard

### 3.1 What it is, which edition, and why this chapter

The standard is the **Global Investment Performance Standards (GIPS)**, maintained by **CFA Institute**. The current edition is the **2020 edition**, issued 30 June 2019, effective **1 January 2020**, with reports covering periods ending on or after **31 December 2020** required to be prepared under it. No newer edition exists as at July 2026 and no exposure draft for a new edition of either chapter is in process. Primary source, and the document every clause below is read out of: [**GIPS Standards for Asset Owners, 2020 edition**](https://www.gipsstandards.org/wp-content/uploads/2021/02/2020_gips_standards_asset_owners.pdf).

The 2020 edition has three chapters: GIPS Standards for Firms, GIPS Standards for Asset Owners, and GIPS Standards for Verifiers.

**This endowment is an asset owner, and the Asset Owners chapter applies.** The Introduction at page xiii is explicit: *"The GIPS Standards for Asset Owners are for asset owners that do not compete for business and that report their performance to an oversight body. Asset owners that compete for business must comply with the GIPS Standards for Firms."* Provision **21.A.2** names the entity type directly, listing "public and private pension funds, **endowments**, foundations, family offices..." and **21.A.3** requires discretion over total fund assets "either by managing assets directly or by having the discretion to hire and fire external managers", which an in-house CIO office satisfies. **21.A.24** is the escape hatch in the other direction: *"If an asset owner competes for business, the asset owner must follow all sections of the GIPS Standards for Firms."*

**This distinction is not cosmetic and the CIO must not work from a Firms-chapter checklist.** Four things differ materially.

| | Firms chapter | **Asset Owners chapter** |
|---|---|---|
| Provision numbering | Sections 1–8 | **Sections 21–26** |
| Reporting unit | Composite or pooled fund | **Total fund**, plus optional composites |
| Audience | Prospective client | **Oversight body** |
| Deliverable | GIPS Composite Report | **GIPS Asset Owner Report** |
| Minimum track record | 5 years building to 10 (4.A.1.a) | **1 year building to 10 (24.A.1.a)** |
| Return basis | Gross or net, firm's choice | **Time-weighted and net-of-fees, mandatory** |

There is **no Section 4** in the Asset Owners chapter. Presentation, reporting and disclosure live in **Section 24**.

Two adjacent documents are live and binding on this fund: the [**Guidance Statement on Benchmarks for Asset Owners**](https://www.gipsstandards.org/wp-content/uploads/2023/04/guidance-statement-benchmarks-asset-owners.pdf), effective 30 June 2023, and the [**errata of November 2020**](https://www.gipsstandards.org/wp-content/uploads/2021/03/errata_november_2020_gips_standards_for_asset_owners.pdf), ten items. The [**GIPS Standards for Verifiers When Verifying Asset Owners**](https://www.gipsstandards.org/wp-content/uploads/2025/09/2020-gips-standards-verifier-when-verifying-asset-owners.pdf) took effect 1 January 2026 and governs the independent performance auditor the Committee engages under IPS Section 2.4.

### 3.2 The required benchmark risk statistic

**Provision 24.A.1.j**, verbatim:

> "24.A.1 The asset owner must present in each GIPS ASSET OWNER REPORT: ... j. For TOTAL FUNDS or COMPOSITES for which monthly TOTAL FUND or COMPOSITE returns are available, the **three-year annualized EX POST STANDARD DEVIATION (using monthly returns) of the TOTAL FUND or COMPOSITE and the BENCHMARK as of each annual period end**."

Footnote 29: *"Required for periods ending on or after 1 January 2011."*

So: **three years, annualised, ex post, monthly returns, for the benchmark as well as for the fund, at every annual period end.** The Firms equivalents are 4.A.1.j for composites and 6.A.1.h for pooled funds. Money-weighted-return reports do not require standard deviation at all.

Two operational points. The Guidance Statement at page 25 requires that *"Standard deviation for both the total fund or composite and the benchmark must be calculated using 36 monthly returns. The same formula must be used to calculate standard deviation for the total fund or composite and the benchmark."* And where 36 monthly returns are unavailable, **24.C.30** requires a disclosure to that effect rather than a substitute statistic. Provision **24.C.35** requires disclosure of whether the risk measures were computed from gross-of-fees, net-of-external-costs-only or net-of-fees returns, because the three series give different numbers.

The 2010 edition's requirement to present an alternative risk measure where the firm judged standard deviation not relevant or appropriate is **absent from the 2020 edition**. Additional risk measures are recommended (24.B.7) rather than required, and if presented they trigger 24.C.34 (describe the measure, name the risk-free rate if used) and 22.A.15 (matching periodicity and methodology for fund and benchmark).

### 3.3 The blended benchmark

The IPS Section 4.2 benchmark is *"the policy portfolio, blended at the weights in Section 4.1"*, which is precisely the case the Asset Owners chapter has a dedicated provision for.

**24.C.27**, the general custom-benchmark provision:

> "If a CUSTOM BENCHMARK or combination of multiple BENCHMARKS is used, the asset owner must: a. Disclose the BENCHMARK **components, weights, and rebalancing process**, if applicable. b. Disclose the **calculation methodology**. c. **Clearly label** the BENCHMARK to indicate that it is a custom benchmark."

**24.C.28**, which exists only in the Asset Owners chapter and fits this fund exactly:

> "If the TOTAL FUND BENCHMARK is a blend of asset class benchmarks based on the policy weights of the respective asset classes, the asset owner must disclose: a. The BENCHMARKS used by each asset class along with their **weights as of the most recent annual period end**. b. **General information regarding the investments, structure, and/or characteristics** of the BENCHMARKS."

The Guidance Statement at page 8 supplies model wording the CIO can adapt directly: *"The Total Fund blended benchmark is calculated monthly using a blend of the asset class benchmarks based on the Total Fund's benchmark policy weights for the respective asset classes. Each asset class uses a total return benchmark. The benchmark policy weights listed in the following table are as of 31 December 2022. Benchmark policy weights and asset class weights for prior periods are available upon request."*

One carve-out saves the fund a great deal of unnecessary disclosure. Per the Guidance Statement at page 23, *"If an asset owner uses a custom benchmark that is a blend of one or more benchmarks, a change in the weights of the constituent benchmarks is **not** considered a benchmark change within the scope of this required disclosure."* Tactical drift and rebalancing inside the policy weights do not trigger the benchmark-change disclosure. A change to the policy weights themselves, adopted by the Board under IPS Section 2.1, does.

Provision **21.A.15** also constrains the benchmark itself: it *"must reflect the investment mandate, objective, or strategy"* and *"must not use a PRICE-ONLY BENCHMARK"*, so every constituent index must be a total return index.

### 3.4 Net versus gross, track record, and part-years

**Net is mandatory for the total fund, and net means something harder for an asset owner than it does for a firm.**

**21.A.25**: *"The asset owner must present TIME-WEIGHTED RETURNS for all TOTAL FUNDS."* **24.A.1.b**: the report must present *"For TOTAL FUNDS, TOTAL FUND returns that are NET-OF-FEES"*, required for periods beginning on or after 1 January 2015.

The Asset Owners glossary defines **net-of-fees** as the return reflecting deduction of transaction costs, all fees and expenses of externally managed pooled funds, investment management fees for externally managed segregated accounts, **and investment management costs**. That last term is asset-owner-only, and it is defined to include *"All internal costs... they may also involve overhead and other related costs and fees, including data valuation fees, investment research services, CUSTODY FEES, pro rata share of overhead (such as building and utilities), allocation of non-investment-department expenses (such as human resources, communications, and technology), and performance measurement and compliance services."*

**The practical consequence for this fund: the reported net return must absorb the cost of running the CIO office itself, including a pro rata share of University overhead.** A firm's net-of-fees never has to do that. The IPS Section 3.2 fee assumption of 0.40% is the right order of magnitude for what this figure must capture, and the desk asks that the finance office establish the overhead allocation methodology before the first report rather than at the first audit. The standard's own worked example is a university endowment ("Genius University Endowment", Appendix A Sample 1, pages 45 to 56) whose note 9 reads: *"Total investment management costs to arrive at the net return have averaged roughly 15 bps annually since 2000."*

Supporting provisions: **24.A.3.b** (label the return type), **24.A.4** (full gross-of-fees returns must be identified as supplemental information), **24.C.6/7/8** (disclose any fees deducted beyond the definition), **22.A.10** (all returns after transaction costs), **22.A.12** (all required returns net of leverage), **22.A.14** (returns reflect fees charged at the underlying pooled fund level, which for this fund means the ETF expense ratios).

**Track record. 24.A.1.a**: at least **one year** of GIPS-compliant performance, or since inception if shorter, *"building up to a minimum of 10 years"*. The five-year opening requirement is the Firms rule at 4.A.1.a and does not apply here. **24.B.8** recommends presenting more than ten years. Only GIPS-compliant performance may appear in the report; linking to non-compliant history must be done outside it (Introduction, page ix).

**Part-years. 22.A.9**, without qualification: *"Returns for periods of less than one year must not be annualized."* **24.A.1.d** requires the return from inception through the first annual period end where the initial period is a stub, and **24.A.1.e** the return from the last annual period end to a termination date.

### 3.5 Benchmark changes

**24.C.26**, verbatim:

> "If the asset owner changes the BENCHMARK, the asset owner must disclose: a. For a **prospective** BENCHMARK change, the **date and description** of the change. Changes must be disclosed for **as long as returns for the prior BENCHMARK are included** in the GIPS ASSET OWNER REPORT. b. For a **retroactive** BENCHMARK change, the **date and description** of the change. Changes must be disclosed for a **minimum of one year** and for as long as they are relevant to interpreting the track record."

The provision requires date and description. It does not use the word "reason", and the desk flags that so the CIO does not cite a clause that says something it does not. Reason is treated as expected practice in the Guidance Statement, which at pages 23 and 24 adds three interpretive rules worth putting in front of the Committee: *"In most cases, the asset owner should change the benchmark going forward only and should not change it retroactively"*; *"When an asset owner changes a benchmark retroactively, the asset owner is encouraged to continue to also present the old benchmark"*; and, bluntly, *"Changes to the benchmark primarily intended to make performance look better by lowering the benchmark return violate the spirit of the GIPS standards."*

Two triggers that are easy to miss. Re-designating a primary benchmark as secondary, or the reverse, **counts as a benchmark change** (Guidance Statement page 26), as does removing a benchmark from the report. And switching from a benchmark not reduced by transaction costs to one that is qualifies as a prospective change (page 11).

Adjacent: **24.C.25** (disclose why, if no benchmark is presented), **24.A.5** (if more than one benchmark is shown, all required information and disclosures apply to all of them), **24.C.21** (disclose if benchmark returns are net of withholding taxes), **24.C.5** (disclose the benchmark description, and the periodicity if calculated less frequently than monthly).

### 3.6 The annual trustee report checklist

To be followed literally. Each item cites the provision that requires it.

**Identity and scope**

- [ ] Head the document **"GIPS Asset Owner Report"** and identify the reporting unit as the **Total Fund**, Ashcroft University Endowment. *(23, glossary)*
- [ ] Carry the GIPS compliance claim in the form the standard prescribes, and present **no non-compliant performance anywhere in the report**. *(21.A.23)*
- [ ] Provide the report to the oversight body, meaning the Investment Committee and the Board, **at least once every 12 months**, updated through the most recent annual period end **within 12 months of that period end**, and retain evidence of how it was provided. *(21.A.11, 21.A.13, 21.A.14)*
- [ ] File the **GIPS Compliance Notification Form** with CFA Institute on initial claim and annually thereafter **by 30 June**, as of the preceding 31 December. *(21.A.27)*

**Returns**

- [ ] **Time-weighted total fund returns, net of fees**, for each annual period. Net must include investment management costs, meaning external manager and vehicle fees, transaction costs, **and the internal cost of the CIO office with its pro rata share of University overhead**. *(21.A.25, 24.A.1.b, glossary)*
- [ ] **Label the return basis explicitly** on the table. *(24.A.3.b)*
- [ ] If gross or net-of-external-costs-only returns are also shown, present them alongside and label them; any **full gross-of-fees** return must be marked **supplemental information**. *(24.B.1, 24.A.4)*
- [ ] **At least one year**, adding a year annually, building to **ten**. Present more than ten once available. *(24.A.1.a, 24.B.8)*
- [ ] **Do not annualise any period shorter than one year.** Show a stub period from inception to the first annual period end as a stub. *(22.A.9, 24.A.1.d)*
- [ ] Disclose the investment management fees and costs incurred in the most recent annual period. *(24.D.7, recommended, and the desk recommends complying)*

**Benchmark**

- [ ] Present the **blended policy benchmark return alongside the fund return for every period shown**, and never the fund return in isolation. *(24.A.1, IPS 4.3)*
- [ ] **The required risk statistic: the three-year annualised ex post standard deviation, computed from monthly returns, for the Total Fund AND for the benchmark, as of each annual period end.** Same formula for both. *(24.A.1.j; Guidance Statement p. 25)*
- [ ] If 36 monthly returns are not available for either, **disclose that as the reason it is not presented**. *(24.C.30)*
- [ ] Disclose which return basis was used to compute the risk statistics. *(24.C.35)*
- [ ] Label the benchmark **clearly as a custom benchmark**, and disclose its **components, weights and rebalancing process**, plus the **calculation methodology**. *(24.C.27)*
- [ ] Table the **nine asset-class benchmarks with their policy weights as of the most recent annual period end** (38 / 20 / 12 / 12 / 8 / 5 / 3 / 2 / 0), and give **general information on the investments, structure and characteristics** of each constituent index. State that prior-period weights are available on request. *(24.C.28)*
- [ ] State the **blend's rebalancing frequency**. The desk recommends **monthly**, matching the IPS Section 4.5 monitoring cycle, and asks the Committee to fix it explicitly, because it must be disclosed and cannot be left implicit. *(24.C.27a)*
- [ ] Confirm every constituent is a **total return index**, never price-only. *(21.A.15)*
- [ ] Disclose whether benchmark returns are net of withholding taxes, where known. *(24.C.21)*
- [ ] On any **benchmark change**, disclose the **date and description**. Prospective changes stay disclosed for as long as prior-benchmark returns appear; retroactive changes for at least one year and for as long as they matter. Treat a primary-to-secondary re-designation or a removal as a change. *(24.C.26; Guidance Statement p. 26)*
- [ ] Note that a change in the **weights** of the blend's constituents is not itself a benchmark change, so ordinary rebalancing does not trigger the disclosure. *(Guidance Statement p. 23)*

**IPS Section 4.3 additions, which GIPS does not require and the mandate does**

- [ ] Return against benchmark **for the period and since inception**.
- [ ] **Ex-ante and realised tracking error** against the 200bp budget.
- [ ] **Peak-to-trough drawdown** against the −20% Section 3.3 limit.
- [ ] **Position of every line against policy and against its range**, per the table at Section 2.7 of this paper.
- [ ] **Compliance status on every constraint in Section 3.6**, with any truncation minuted.
- [ ] **Turnover and its cost in basis points, against the value it was intended to add**, priced off `taa/costs.py`.

---

## 4. The check

`tests/check_implementation.py`, standard library only, 53 assertions, non-zero exit on any failure.

```
==============================================================================
Ashcroft University Endowment -- Implementation & Operations desk
check_implementation.py                                 28 Jul 2026
==============================================================================

1. Every vehicle carries a sourced, statused bid-ask spread
-----------------------------------------------------------
[PASS] outputs/implementation.json lists at least the nine primary vehicles
         15 vehicles present
[PASS] BIL   spread_bps sourced and statused
         1.0bp  status=VERIFIED  https://www.ssga.com/library-content/products/fund-data/etfs/us/spdr-pro
[PASS] DBC   spread_bps sourced and statused
         4.0bp  status=VERIFIED  https://www.invesco.com/us/financial-products/etfs/product-detail?audien
[PASS] EEM   spread_bps sourced and statused
         2.0bp  status=VERIFIED  https://www.ishares.com/us/products/239637/ishares-msci-emerging-markets
[PASS] EFA   spread_bps sourced and statused
         1.0bp  status=VERIFIED  https://www.ishares.com/us/products/239623/ishares-msci-eafe-etf
[PASS] GSG   spread_bps sourced and statused
         3.0bp  status=VERIFIED  https://www.ishares.com/us/products/239757/ishares-sp-gsci-commodityinde
[PASS] HYG   spread_bps sourced and statused
         1.0bp  status=VERIFIED  https://www.ishares.com/us/products/239565/ishares-iboxx-high-yield-corp
[PASS] IEF   spread_bps sourced and statused
         1.0bp  status=VERIFIED  https://www.ishares.com/us/products/239456/ishares-7-10-year-treasury-bo
[PASS] LQD   spread_bps sourced and statused
         1.0bp  status=VERIFIED  https://www.ishares.com/us/products/239566/ishares-iboxx-investment-grad
[PASS] SGOV  spread_bps sourced and statused
         1.0bp  status=VERIFIED  https://www.ishares.com/us/products/314116/ishares-0-3-month-treasury-bo
[PASS] SPY   spread_bps sourced and statused
         0.14bp  status=VERIFIED  https://www.ssga.com/library-content/products/fund-data/etfs/us/spdr-pro
[PASS] TLT   spread_bps sourced and statused
         1.0bp  status=VERIFIED  https://www.ishares.com/us/products/239454/ishares-20-year-treasury-bond
[PASS] VEA   spread_bps sourced and statused
         1.42bp  status=VERIFIED  https://advisors.vanguard.com/investments/bidaskspread
[PASS] VNQ   spread_bps sourced and statused
         1.02bp  status=VERIFIED  https://advisors.vanguard.com/investments/bidaskspread
[PASS] VTI   spread_bps sourced and statused
         0.55bp  status=VERIFIED  https://advisors.vanguard.com/investments/bidaskspread
[PASS] VWO   spread_bps sourced and statused
         1.7bp  status=VERIFIED  https://advisors.vanguard.com/investments/bidaskspread

2. Adopted one-way cost >= half-spread of the primary vehicle
-------------------------------------------------------------
[PASS] us_equity      1.50bp >= half-spread of VTI
         quoted 0.5500bp, half 0.2750bp, adopted is 5.5x the half-spread
[PASS] dev_ex_us      4.00bp >= half-spread of VEA
         quoted 1.4200bp, half 0.7100bp, adopted is 5.6x the half-spread
[PASS] em_equity      8.00bp >= half-spread of VWO
         quoted 1.7000bp, half 0.8500bp, adopted is 9.4x the half-spread
[PASS] ust_duration   3.00bp >= half-spread of IEF
         quoted 1.0000bp, half 0.5000bp, adopted is 6.0x the half-spread
[PASS] us_ig          6.00bp >= half-spread of LQD
         quoted 1.0000bp, half 0.5000bp, adopted is 12.0x the half-spread
[PASS] us_hy         12.00bp >= half-spread of HYG
         quoted 1.0000bp, half 0.5000bp, adopted is 24.0x the half-spread
[PASS] commodities   25.00bp >= half-spread of DBC
         quoted 4.0000bp, half 2.0000bp, adopted is 12.5x the half-spread
[PASS] listed_re      5.00bp >= half-spread of VNQ
         quoted 1.0200bp, half 0.5100bp, adopted is 9.8x the half-spread
[PASS] cash           1.00bp >= half-spread of SGOV
         quoted 1.0000bp, half 0.5000bp, adopted is 2.0x the half-spread

3. Cost vector has the right shape
----------------------------------
[PASS] SPY line cost < DBC line cost
         us_equity 1.50bp < commodities 25.00bp
[PASS] SPY line cost < HYG line cost
         us_equity 1.50bp < us_hy 12.00bp
[PASS] every line has a strictly positive one-way cost
         no line is free to trade

4. Every corridor is at least one minimum trade wide
----------------------------------------------------
[PASS] us_equity     corridor 1.00pp >= minimum trade 0.50pp
         a breach trades 1.00pp = USD 8,500,000
[PASS] dev_ex_us     corridor 1.25pp >= minimum trade 0.50pp
         a breach trades 1.25pp = USD 10,625,000
[PASS] em_equity     corridor 1.00pp >= minimum trade 0.50pp
         a breach trades 1.00pp = USD 8,500,000
[PASS] ust_duration  corridor 0.75pp >= minimum trade 0.50pp
         a breach trades 0.75pp = USD 6,375,000
[PASS] us_ig         corridor 1.00pp >= minimum trade 0.50pp
         a breach trades 1.00pp = USD 8,500,000
[PASS] us_hy         corridor 1.25pp >= minimum trade 0.50pp
         a breach trades 1.25pp = USD 10,625,000
[PASS] commodities   corridor 0.75pp >= minimum trade 0.50pp
         a breach trades 0.75pp = USD 6,375,000
[PASS] listed_re     corridor 0.50pp >= minimum trade 0.50pp
         a breach trades 0.50pp = USD 4,250,000
[PASS] cash          corridor 0.50pp >= minimum trade 0.50pp
         a breach trades 0.50pp = USD 4,250,000

5. Every corridor keeps its line inside the IPS range
-----------------------------------------------------
[PASS] us_equity     band [37.00, 39.00] inside range [28, 48]
         headroom 9.00pp below, 9.00pp above
[PASS] dev_ex_us     band [18.75, 21.25] inside range [12, 28]
         headroom 6.75pp below, 6.75pp above
[PASS] em_equity     band [11.00, 13.00] inside range [5, 19]
         headroom 6.00pp below, 6.00pp above
[PASS] ust_duration  band [11.25, 12.75] inside range [5, 22]
         headroom 6.25pp below, 9.25pp above
[PASS] us_ig         band [7.00, 9.00] inside range [3, 13]
         headroom 4.00pp below, 4.00pp above
[PASS] us_hy         band [3.75, 6.25] inside range [0, 10]
         headroom 3.75pp below, 3.75pp above
[PASS] commodities   band [2.25, 3.75] inside range [0, 8]
         headroom 2.25pp below, 4.25pp above
[PASS] listed_re     band [1.50, 2.50] inside range [0, 6]
         headroom 1.50pp below, 3.50pp above
[PASS] cash          band [0.00, 0.50] inside range [0, 10]
         headroom 0.00pp below, 9.50pp above (one-sided: policy weight sits on the range floor)

6. apply_min_trade honours the IPS Section 4.2 minimum
------------------------------------------------------
[PASS] 30bp proposed trade is suppressed
         us_equity stays at 38.00%, below the 0.50pp minimum
[PASS] 60bp proposed trade passes
         us_equity moves to 38.60%, at or above the 0.50pp minimum
[PASS] a trade of exactly 50bp passes
         the minimum is inclusive, per 'anything smaller' at IPS 4.2
[PASS] suppression reconciles into cash so weights still sum
         total 38.0000%, cash absorbs 0.00pp

Cross-checks the desk uses to sanity-test itself
------------------------------------------------
[PASS] corridor set consumes less than a quarter of the TE budget
         26.7bp of drift TE with every line at its edge, against a 200bp budget
[PASS] a full reset from every corridor edge costs under 1bp of NAV
         0.595bp of NAV = USD 50,575
[PASS] module reports the JSON's one-way vector unchanged
         taa/costs.py and outputs/implementation.json agree

==============================================================================
53 passed, 0 failed, 53 assertions
==============================================================================
```

`--demo-fail` plants a violation, narrowing the listed real estate corridor from 0.50pp to 0.30pp, which is below the IPS Section 4.2 minimum trade:

```
*** --demo-fail: planting a violation before running the check.
*** listed_re corridor 0.50pp -> 0.30pp, which is narrower than
*** the IPS Section 4.2 minimum trade of 50bp, so a breach of
*** that corridor would generate a trade the mandate forbids.

...

[FAIL] listed_re     corridor 0.30pp >= minimum trade 0.50pp
         a breach would trade 0.30pp = USD 2,550,000, below the IPS Section 4.2
         minimum, so it could not be acted on

==============================================================================
52 passed, 1 failed, 53 assertions

  FAILED: listed_re     corridor 0.30pp >= minimum trade 0.50pp
==============================================================================
```

Exit code 1. Note that the planted corridor still passes the range-containment assertion, which is correct: a corridor can be perfectly compliant with the IPS range and still be unusable. Two separate tests, two separate failure modes.

---

## 5. What would refute this

Per IPS Section 4.4, every view carries what would show it wrong and a date by which that would be known.

| Claim | Falsifier | Known by |
|---|---|---|
| Commodities cost 25bp one-way | Three executed commodity trades of USD 5m or more averaging under 12bp of realised slippage against arrival midpoint | After the third commodity trade, or one year, whichever is sooner |
| DBC liquidity is the binding constraint | DBC's 60-session median dollar ADV exceeds USD 85m, making an 8.5m clip under 10% of a day | Monitored monthly |
| The corridor set consumes about 27bp of TE | Realised tracking error attributable to drift, measured as the difference between the actual portfolio and a continuously rebalanced policy portfolio, exceeds 60bp over any rolling twelve months | 30 June 2027 |
| VTI over SPY is the right primary | A twelve-month period in which realised slippage on VTI trades exceeds SPY's by more than 6.45bp, which would erase the fee saving | 30 June 2027 |
| Futures add nothing worth the mandate risk | An ES-versus-VTI cost study showing more than 5bp a year of net saving after roll, margin and basis | On any Committee request |
| Trading to target beats trading to the edge here | Relaxation of the 50bp minimum trade at IPS Section 4.2, which would immediately reverse the recommendation at Section 2.4 | On any IPS amendment |

**Where the desk is uncertain, stated rather than buried.** The Masters (2003) paper is paywalled at pm-research, ProQuest and ResearchGate and the desk could not read it; the corridor determinants at Section 2.1 come from the open CFA Institute formulation and are corroborated across four independent secondary sources, but the desk has not verified them against Masters' own text. The widely repeated claim that Masters recommends rebalancing half-way back to target could not be traced to any openable source and is **not** relied on anywhere in this paper. The UBTI analysis at Section 1.8 is a desk reading of published IRS material and needs counsel's confirmation before any first futures use. The exact 2026 ES average daily volume figure is `[RECALLED]`; the 1.81 million contract figure cited is 2023. Attribution of the 5/25 rule to Larry Swedroe is `[RECALLED]` and the cited source gives no attribution.

---

## Appendix: importing the module

**Units, once more, because this is where callers get it wrong.** Percentage points of NAV throughout. `38.0`, never `0.38`. `ONE_WAY_BPS` is basis points of traded notional; `round_trip_cost` takes pp of NAV and returns bps of NAV.

```python
from taa import costs

costs.ONE_WAY_BPS["commodities"]        # 25.0
costs.CORRIDOR_PP["listed_re"]          # 0.5
costs.MIN_TRADE_PP                      # 0.5

# price a proposed rebalance, in bps of NAV
costs.round_trip_cost({"commodities": 3.0, "cash": 3.0})    # 0.78

# one-way turnover between two weight vectors, in pp of NAV
costs.turnover_pp({"us_equity": 38.0, "cash": 0.0},
                  {"us_equity": 36.0, "cash": 2.0})          # 2.0

# suppress anything the mandate will not let you trade
costs.apply_min_trade(current_weights, proposed_weights)

# which lines have breached their corridor, and the trade back to policy
costs.breaches(current_weights)

# which lines have breached their IPS range, which is a compliance event
costs.range_breaches(current_weights)
```

Running `py -3 taa/costs.py` prints the corridor table and the tracking-error budget consumption. Standard library only, no third-party imports, Python 3.8 and later.
