# Ashcroft University Endowment — tactical asset allocation study

Year ended 30 June 2026. Recommendation for the year to 30 June 2027.

Everything here was built in this folder. Nothing is imported from elsewhere on
the machine it was written on, no API key is used anywhere, and no paywalled
source was consulted. Clone the folder, run the commands below, and you get the
same numbers.

> **Built by an AI agent from a single brief.** `PROMPT.md` is that brief,
> unedited, and everything except it, `IPS.pdf` and `MANDATE.md` is the agent's
> work. It ran on my own machine inside my normal working setup, which already
> had a global instruction file, installed skills, MCP servers and plugins
> available. It was not a clean room, and I am not claiming the *process*
> reproduces from a bare install. The *study* does: no keys, no private data, no
> paywalled sources, and the commands below regenerate every number.
> `HOW_THIS_WAS_BUILT.md` records the process, `AUDIT.md` records what to trust.

---

## The recommendation, in one line

**Hold policy weights, take no intentional active risk, and refer two amendment
questions to the Board under IPS 2.3.** The policy portfolio is priced to earn
6.08% against a required 8.10%, the tactical programme's expected alpha is 4.2bps
a year against 6.4bps of cost, and 9 of 40 signal cells beat the historical mean
out of sample. Separately, the Board's own policy portfolio breached its (20.00)%
drawdown limit in this window, reaching (22.46)%.

---

## Read in this order

| | |
|---|---|
| `report/annual_report.html` | The report to trustees. Page one carries the position. |
| `report/decision_record.html` | The five-year record, twenty quarterly entries. |
| `report/dashboard.html` | The record as an interactive tool. Opens from disk. |
| `methods.ipynb` | Every method tied to the paper it comes from. |
| `desks/` | The six desk papers, as tabled. |
| `AUDIT.md` | **Read before publishing.** What in this study can and cannot be trusted. |
| `HOW_THIS_WAS_BUILT.md` | The brief, the order of work, and the environment it ran in. |
| `brief/PROMPT.md` | The brief itself, unedited. |

### What was given and what was produced

`brief/` holds the three documents that were handed to the agent. Everything
outside it is the agent's output. The boundary is kept visible in the file tree
on purpose, so a reader does not have to take my word for where it sits.

| Given | Produced |
|---|---|
| `brief/PROMPT.md` the instruction | `taa/` the study, `tests/` the verification |
| `brief/IPS.pdf` the governing policy | `desks/` six desk papers |
| `brief/MANDATE.md` the working extract | `report/`, `outputs/`, `methods.ipynb` |
| `ds/` the design system | `AUDIT.md`, `README.md` |
| `tests/` | The verification artifacts. |
| `outputs/agent_dynamics.html` | How six concurrent desks behaved as a system, with times. |
| `outputs/top_decisions.html` | The three best decisions by outcome, and how each was reached. Hindsight, labelled. |

---

## Reproducing it

```
pip install -r requirements.txt
py -3 -m taa.datapull        # once. Populates data/raw/ from public sources.
py -3 -m taa.simulate        # the five-year record -> outputs/decision_record.json
py -3 -m taa.report_main     # the report and the decision record
py -3 -m taa.dashboard       # the dashboard
py -3 -m taa.reports_extra   # the two supplementary notes in outputs/
py -3 build_notebook.py      # regenerates methods.ipynb
```

Everything after the first pull runs offline. `data/raw/` ships with the
repository, 438 files, so the study reproduces with no network at all. That cache
is part of the evidence rather than a convenience: the ALFRED macro vintages in
it are what make the point-in-time wall checkable, and they are the one input a
reader cannot easily reconstruct after the fact.

Run the tests one at a time on a machine with limited memory. Several build
covariance matrices, and running the suite back to back on a box with about 2 GB
free produced allocation failures that disappeared on a second run.

### The verification suite

```
py -3 tests/test_lookahead.py     # 12 tests: static, runtime, planted violations
py -3 tests/mutation_test.py      # breaks the wall on purpose, requires it to go red
py -3 tests/check_hindsight.py    # 7 checks across all twenty decision entries
py -3 tests/check_units.py        # the percentage-point / fraction boundary
py -3 tests/check_mandate.py      # MANDATE.md against the IPS
py -3 tests/test_compliance.py    # the compliance test rejecting 13 planted breaches
py -3 tests/check_capital_markets.py
py -3 tests/check_systematic.py
py -3 tests/check_implementation.py
py -3 tests/check_quant.py
py -3 tests/check_macro.py
py -3 tests/check_figures.py    # prose figures against the data they came from
py -3 tests/audit.py            # publication audit, pass 1: what is missing
py -3 tests/audit2.py           # publication audit, pass 2: what is tilted
```

Several accept `--demo-fail`, which plants a violation and shows the check going
red. A test that has only ever passed is not evidence of anything.

---

## The window is a parameter

The study window is defined once, in `taa/config.py`, and every stage reads it
from there. Change it and rerun and the whole study reproduces on the new window
with no other edit:

```
TAA_WINDOW_START=2016-07-01 TAA_WINDOW_END=2026-06-30 py -3 -m taa.simulate
```

or write `outputs/window.json`, or edit the two dates in `config.py`. The
dashboard carries the same control.

This matters more than it sounds. On sixty monthly observations the study's
headline active return is **+22bps a year over five years** and **(6)bps a year
over three**, on the same programme. The report says so rather than quoting
whichever number reads better.

---

## The wall

Every read of historical data goes through `taa/pitdata.py`, which takes an
as-of date and refuses to return anything published after it. It is the only
route to the raw cache, enforced three ways: a runtime guard on the store, the
as-of gate on every value returned, and a static test that walks the import
graph and fails if any analysis module imports the store, imports a network
library, or names the cache by path.

It handles the two ways a look-ahead gets in. **Revision**: macro series are read
from the ALFRED vintage current on the as-of date. **Publication lag**: a figure
released after the trade date is a look-ahead even when the observation is dated
earlier, and the vintage mechanism handles that at source.

The number that justifies it: US real GDP for 2022 Q2 was first published at
**(0.93)% annualised** on 28 July 2022 and reads **+0.63%** today. The sign did
not cross zero until 26 September 2024, **791 days** later. Under this study's
regime rule that flips the reading from *stagflation risk* to *overheat* and
reverses the tilt.

`tests/mutation_test.py` then removes the enforcement on purpose, one piece at a
time, in a sandbox copy, and requires the suite to go red. Its first run found
three surviving mutations and two were defects in the tests rather than the
code.

---

## The office

Six desks, staffed at the outset. Each owned work that could run without waiting
on another desk, tabled a written paper, and owned a check that returns pass or
fail without a judgement call.

| Desk | Paper | Check |
|---|---|---|
| Capital Markets | `desks/capital_markets.md` | 5 of 5 |
| Systematic | `desks/systematic.md` | 26 of 26 |
| Implementation & Operations | `desks/implementation.md` | 53 of 53 |
| Quantitative | `desks/quantitative.md` | look-ahead and range assertions at 20 dates |
| Macro | `desks/macro.md` | 688 assertions |
| Risk | `desks/risk.md` | 13 of 13 mutants died |

The Quantitative and Macro desks ran concurrently and blind to each other, on
disjoint briefs, writing to separate directories. Both pre-reconciliation drafts
are in the report's evidence appendix unchanged. They disagreed by 16.5
percentage points on Treasury duration, which is the finding rather than an
embarrassment.

---

## Code map

```
taa/config.py       the window and every mandate constant. one source of truth
taa/_rawstore.py    PRIVATE. the raw cache. only pitdata may read it
taa/pitdata.py      THE CHOKE POINT. every historical read, with an as-of date
taa/datapull.py     ingestion. the only module that touches the network

taa/costs.py        transaction costs and corridors      (Implementation desk)
taa/signals.py      signal construction                  (Quantitative desk)
taa/evidence.py     R2_oos, Clark-West, vol management   (Quantitative desk)
taa/riskmodel.py    Ledoit-Wolf covariance, ex-ante TE   (Quantitative desk)
taa/optimiser.py    the constrained allocation           (Quantitative desk)
taa/regime.py       point-in-time regime read            (Macro desk)
taa/compliance.py   the pass/fail test. holds a veto     (Risk desk)
taa/exclusions.py   vehicle-level exclusion screening    (Risk desk)

taa/perf.py         GIPS-oriented performance statistics (CIO)
taa/simulate.py     the five-year record, emitted as data (CIO)
taa/charts.py       inline SVG in the house design system (CIO)
taa/render.py       the document shell                    (CIO)
taa/report_*.py     the report and the record             (CIO)
taa/dashboard.py    the interactive record                (CIO)
```

---

## Data sources

All public, all free, no key:

- **Prices** — Yahoo Finance daily adjusted closes, via `yfinance`
- **Market rates and spreads** — FRED `fredgraph.csv`
- **Macro vintages** — ALFRED `alfredgraph.csv?vintage_date=`, which is what
  makes the point-in-time wall real rather than aspirational
- **Capital market assumptions** — seven published house forecasts, each with a
  URL in the evidence appendix
- **Vehicle spreads** — issuer-published 30-day medians under SEC Rule 6c-11

Two limitations are recorded rather than worked around. The ICE BofA
option-adjusted spread series are served for a rolling three-year window only,
so eight of twenty meetings run on three liquidity indicators rather than four.
And the price cache begins July 2009, so the 2008 crisis is outside the stress
replay.

---

## Design

The **Coldbrook Capital** design system shipped in `ds/`. Tokens from
`ds/colors_and_type.css`, components from `ds/preview/`. Three departures are
recorded in the report: the stylesheet's Google Fonts import is dropped so the
documents render identically from disk with no network; the stylesheet's
`--navy` has drifted from the value every preview uses and the tokens file
governs; and the wordmark is Ashcroft's rather than Coldbrook's, since Coldbrook
is the fictional firm the system was authored for.

No red and green anywhere. Direction is carried by navy against clay, by
parentheses on negatives, and by position relative to a zero axis.

---

## Disclaimer

Ashcroft University Endowment, its Investment Policy Statement and its Board are
fictional, written for this exercise. Coldbrook Capital, whose design system is
in `ds/`, is fictional too.

Nothing here is investment advice or a recommendation to buy or sell anything.
The study is a test of whether an agent given a real mandate and an obligation to
be audited produces work that survives auditing. It is published so the process
can be inspected, including the parts `AUDIT.md` says not to trust.

MIT licensed, see `LICENSE`. The cached data under `data/raw/` remains subject to
its originators' terms.
