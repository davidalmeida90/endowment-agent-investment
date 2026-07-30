# Investment Policy Statement — Ashcroft University Endowment

Governing document for this study. Every recommendation cites it. Where an
analysis conflicts with the mandate, the mandate wins.

## The fund

| | |
|---|---|
| Assets | USD 850,000,000 |
| Type | US university endowment, perpetual |
| Governing law | UPMIFA. Prudent investor standard, total-return spending permitted |
| Tax status | Exempt. UBTI applies to debt-financed income |

## Return objective

Spending rate 4.5%, plus higher-education inflation (HEPI, ~3.2%), plus fees
0.4%. **Required long-run nominal return: 8.1%.**

Spending rule: 4.5% of the trailing 3-year average market value, smoothed,
paid quarterly.

## Risk objective

**Ability to bear risk: high.** Perpetual horizon, no debt against the corpus,
no regulatory funding test.

**Willingness: moderate, and binding.** The endowment funds 18% of the
university's operating budget. The board has set a **−20% peak-to-trough**
limit, beyond which the spending draw is cut, which is the outcome the
university is least able to absorb.

These two are in tension by construction. An 8.1% required return implies
substantial equity risk; a −20% drawdown limit with 18% budget dependency
implies less. Any recommendation must say which one it is giving ground on.

## Time horizon

Perpetual, with a near-term leg: a USD 60,000,000 capital campaign inflow is
expected in year 3.

## Liquidity

- Annual draw approximately USD 38,000,000, paid quarterly
- Minimum 15% of NAV in assets liquid within 5 business days
- No new lockups beyond 10% of NAV

## Legal and unique constraints

- Board exclusion: tobacco and thermal coal
- No leverage at the fund level (UBTI)
- Implementation must be daily-liquid: futures, ETFs, index funds

## Policy portfolio and opportunity set

Nine lines. Tactical positions are taken against these weights and must stay
inside the permitted range, which binds independently of the tracking-error
budget.

| Sleeve | Line | Policy | Range | Vehicle |
|---|---|---:|---|---|
| Equity **70%** | US equity | 38% | 28–48% | SPY / VTI |
| | Developed ex-US | 20% | 12–28% | EFA / VEA |
| | Emerging markets | 12% | 5–19% | EEM / VWO |
| Fixed income **25%** | US Treasury duration | 12% | 5–22% | IEF / TLT |
| | US investment grade | 8% | 3–13% | LQD |
| | US high yield | 5% | 0–10% | HYG |
| Real assets **5%** | Commodities | 3% | 0–8% | DBC / GSG |
| | Listed real estate | 2% | 0–6% | VNQ |
| Cash **0%** | T-bills | 0% | 0–10% | BIL / SGOV |

Sleeve totals may move within: equity 60–80%, fixed income 15–35%, real assets
0–10%.

Cash is a real position, not a residual. When the volatility forecast rises,
raising cash is the cheapest way to cut risk, and the range exists so that it
can be used.

**Investable dates bind.** HYG lists from 2007, DBC from 2006, EEM from 2003,
VNQ from 2004. Any historical work either starts each line at its own
investable date, or uses index history for estimation and says plainly that
implementation is assumed. Mixing the two silently is not acceptable.

## Tactical allocation budget

**200bps ex-ante tracking error** against the policy portfolio. Minimum trade
size 50bps; anything smaller is not worth the turnover.

## Constraint hierarchy

Pre-committed, so that a conflict is resolved by the mandate rather than by
whichever analysis argues most confidently in the moment. In order:

1. **Liquidity.** The draw gets funded. Not negotiable.
2. **Legal, UBTI, board exclusions.** Not negotiable.
3. **Drawdown limit, −20%.** Hard.
4. **Tracking error budget, 200bps.** Hard.
5. **Return objective, 8.1%.** Best efforts.

A tactical view that would breach 3 or 4 is truncated to the constraint. It is
not overridden by argument.

## Evidence standard

- **Public data only.** FRED/ALFRED, Philadelphia Fed, Ken French, Shiller,
  Treasury, exchange-published data. Nothing behind a subscription.
- **Point in time.** Any historical analysis uses data as it stood on the date
  in question. Macro series come from ALFRED vintages, never from the current
  revision. `taa/pitdata.py` is the only sanctioned access path and it enforces
  this; a leakage test asserts it.
- **State the falsifier.** Any view that cannot be wrong does not go in.
