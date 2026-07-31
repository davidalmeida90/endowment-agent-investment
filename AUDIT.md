# Audit note

**Ashcroft University Endowment: tactical asset allocation study**
Prepared before publication. Nothing in this note changes a result. It records
what a reader should and should not trust, and why.

Every mechanical figure below is produced by `tests/audit.py` and written to
`outputs/audit.json`, so this note can be checked:

```
py -3 tests/audit.py     # first pass: what is missing
py -3 tests/audit2.py    # second pass: what is tilted
```

The findings the script **cannot** produce are marked **[judgement]**. Those are
the ones that matter most, because a check that could detect them would already
have been written.

---

## Short version

| | |
|---|---|
| Can you trust that no decision used future data? | **Yes**, within the limits at §1. Enforced, tested, and the enforcement was broken on purpose to prove the tests fire. |
| Can you trust the five-year track record? | **It is not a track record.** It is a simulation of a rule. See §2. |
| Can you trust that the programme added +34bps a year? | **No.** Indistinguishable from zero, the sign flips with the window, and §9.1 shows the benchmark it was measured against was about 30bps a year too easy. |
| Can you trust the recommendation? | **Yes, but on a narrower base than the report first implied.** It rests on the 202bps valuation gap and the drawdown incompatibility. The cost argument is weaker than presented; see §9.3. |
| Can you trust the committee minutes? | **The reasoning, yes. The meeting, no.** No committee met. See §4. |

---

## 1. Look-ahead: what was enforced and what could not be

### What was enforced, and verified

Every historical read passes through `taa/pitdata.py`, which takes an as-of date
and refuses anything published after it. Verified this run:

| Check | Result |
|---|---|
| Decision fields referencing a date later than that meeting | **0** |
| Point-in-time access log entries | **over 9,000** (the audit's own reads append to it, so the exact count rises each run) |
| Reads returning an observation after their as-of date | **0** |
| Meeting/series reads not using that meeting's own ALFRED vintage | **0 of 140** |
| Current-vintage (anachronistic) inputs admitted to a historical decision | **0** |
| Deliberate mutations of the enforcement caught by the test suite | **7 of 7** |

The macro series are read from the ALFRED vintage current on each meeting date,
so a decision in September 2022 sees the September 2022 vintage and nothing
later. This is not cosmetic: 2022 Q2 real GDP printed **(0.93)%** and now reads
**+0.63%**, and the sign did not cross zero until **791 days** after the print.

The Macro desk added six BEA release dates to the ingestion layer. A reader
might reasonably ask whether choosing *which* extra vintages to fetch, knowing
where the interesting revision was, leaks anything into the decisions. It does
not, and this was tested rather than argued: all 140 meeting-and-series reads
resolve to that meeting's own dated vintage file, so an extra vintage sitting
between two meetings can never be served to one. The extra vintages are used
only for the published-print demonstration.

### What could not be enforced **[judgement]**

**The specification of the study was chosen in 2026, with knowledge of what
2021 to 2026 contained.** No point-in-time layer can fix this. Specifically:

- which five signals to build, and their lookbacks and standardisation
- the regime classification rule, its indicators and its thresholds
- the 50/50 reconciliation rule between the two desks
- the corridor formula and the choice of stress episodes
- the decision to run quarterly rather than monthly or annually

This is the residual look-ahead in every backtest of a rule designed after the
fact, and it is present here. Three things reduce how much it should worry you,
and one thing should:

- The **opportunity set is not mine**. The nine lines, their weights, ranges and
  vehicles are fixed by the Investment Policy Statement.
- The signals are taken from published literature rather than fitted to this
  window, and the parameter count is stated in `taa/signals.py`.
- **The direction of the bias runs against the conclusion.** Specification
  choices made with hindsight generally make a strategy look *better*. This
  study concludes the signals do not work, on a composite out-of-sample R² of
  **(1.61)%**. A bias that flatters, applied to a result this poor, means the
  honest result is poorer still. The conclusion is robust to the bias; a
  positive conclusion would not have been.
- **But**: if you are reading the five-year record as evidence that this
  *particular* rule is good, that reading is not supported, for exactly this
  reason.

**Prices are back-adjusted.** Yahoo Finance adjusted closes are restated
retroactively when a distribution is paid, so the *level* of a past adjusted
close is not what a screen showed that day. Returns between two past dates are
correct, and no return in this study is computed across the as-of boundary, so
no look-ahead is introduced. It is recorded here because it is a real property of
the data, and not because it causes a problem.

---

## 2. The five-year record is a simulation, not a track record

This is the most important thing in this note.

| | |
|---|---|
| Committee meetings actually held | **0** |
| Historical decisions that involved deliberation | **0 of 20** |
| Live decisions that involved deliberation | **1** (the FY2027 recommendation) |
| Transaction costs | **modelled**, static per-line vector |
| Execution, slippage, market impact beyond that vector | **not modelled** |

No office ran. No money was managed. The twenty quarterly entries are a
pre-committed rule applied to point-in-time inputs, and the report and record
both say so at the top rather than in a footnote. The reasons attached to each
decision are the readings that drove the rule, not an account of a discussion.

Returns are **net of modelled trading costs and gross of the 0.40% cost load**
in the IPS 3.2 return requirement, which is an office and custody cost rather
than a trading cost. A GIPS-compliant net-of-fees presentation for a real
composite would deduct it.

The benchmark is the policy portfolio **rebalanced monthly**. That is a
modelling choice and a GIPS 24.C.27 disclosure item. It works against the fund
rather than for it, since a monthly-rebalanced blend is harder to beat than a
drifting one.

---

## 3. The performance numbers are indistinguishable from zero

| Statistic | Value | Interval |
|---|---:|---|
| Monthly observations | 60 | five years, one or two regimes |
| Sharpe ratio | 0.762 | 95%: **[(0.13), +1.65]**, contains zero |
| Information ratio | 0.266 | 95%: **[(0.61), +1.14]**, contains zero |

**Active return a year, same programme, different window:**

| Window | 12m | 24m | 36m | 48m | 60m |
|---|---:|---:|---:|---:|---:|
| Active return a year, bps | **+27** | **(22)** | **+2** | **(16)** | **+34** |

The sign flips four times. Any headline drawn from this record is a statement
about the window it was measured on, and for that reason the report quotes the
five-year and three-year figures side by side.

**Do not quote the +34bps as a result.** If you quote anything, quote the
interval.

The out-of-sample evidence is on roughly 130 monthly observations per line
against the 900 in the studies it is compared to, so every R² here carries a
standard error several times theirs.

---

## 4. Judgement calls with a large presentational effect **[judgement]**

These changed how the study reads. Each is defensible and each is a call a
reader is entitled to disagree with.

### 4.1 Reclassifying two compliance failures as fund state rather than allocation defects

**Effect: the headline moved from "20 of 20 allocations failed" to "0 of 20
failed, 17 of 20 quarters with the fund in breach".**

A realised drawdown beyond the (20.00)% limit cannot be remedied by choosing
different weights, because it has already happened; IPS 3.3 answers it by
reducing the distribution and IPS 2.3 escalates it. The same applies to an
ex-ante drawdown failure at or below policy-equivalent risk, because the Board's
own policy portfolio reads (21.60)% against the (20.00)% limit, so the gate sits
on top of policy.

Treating either as a rejected allocation would report twenty rejections for one
event in October 2022 and would blame the desks for the mandate. That is the
argument. The counter-argument is that it is a reclassification that turns a
failing control into a passing one, and it is implemented in `taa/simulate.py`
where a reader can see it.

### 4.2 The risk desk's ex-ante drawdown gate

The gate is set at the **looser** of the mandate limit and the policy
portfolio's own ex-ante figure. Without that, the policy portfolio fails at
every meeting and the test gates nothing. The Risk desk names this as the most
questionable choice in its module and the office did not overrule it. It means
**the office can never take a risk-increasing position**, which is a strong
constraint arrived at by calibration rather than by the Statement.

### 4.3 The committee is a construct

Seven members, a quorum, a chair who does not vote, and a recorded dissent. **No
such body met.** The dissent recorded in the minutes is a real and sourced
counter-argument, Sneddon (2020) on whether correlation across bets raises or
lowers the achievable information ratio, which appears in the Systematic desk's
own paper. Its attribution to "a member with professional investment experience"
is fiction. The reasoning is genuine; the meeting is not.

If you publish the minutes, say this. They read as a record of a deliberation.

### 4.4 The top-decisions note is selected on outcome

`outputs/top_decisions.html` sorts twenty decisions by what they earned and
keeps three. That is hindsight applied deliberately, and the note says so in its
first paragraph. Selecting the best three from twenty coin flips produces three
impressive coin flips.

---

## 5. Data limitations

| Limitation | Extent | What was done |
|---|---|---|
| ICE BofA option-adjusted spreads served for a rolling three-year window only, from 31 July 2023 | **8 of 20** meetings ran on three liquidity indicators rather than four | Four public-domain long-history substitutes added (BAA10Y, AAA10Y, T10Y2Y, T10Y3M). Nothing interpolated, nothing carried backwards. The dashboard shows which quarters. |
| Price cache begins 1 July 2009 | The **2008 crisis is outside** the stress replay | Not worked around. The desk did not reach past the point-in-time layer to obtain it, so the worst episode the risk model can see is not the worst that occurred, and the ex-ante drawdown estimate is optimistic by an unknown margin. |
| Shiller CAPE has no vintage history | Excluded from all historical work | A dividend-yield construction from price data is used instead, which is point-in-time clean and weaker. |
| Yahoo Finance is an unofficial interface | All price data | No paid vendor was used. Data is not guaranteed and adjusted closes are vendor-computed. |
| Six agents appending to one log concurrently | 2 lines corrupted during the desk phase, since removed | The current log shows 0 corrupted, but that is after cleaning. The failure mode is real: shared mutable state, no locking. |
| Months with a missing line return | **0** | All nine lines have a complete series across the window and every vehicle was investable throughout, so nothing is spliced. |

---

## 6. What was independently verified, and what was taken on trust **[judgement]**

Six desks produced roughly 11,000 lines of code and six papers. The coordinating
office did not re-derive all of it.

**Independently verified by the office:**

- the 2022 Q2 GDP vintage claim, recomputed from ALFRED rather than accepted
- the compliance module's behaviour on the case IPS 4.1 names, run directly
- the unit boundary between `costs.py` and the rest of the study
- the look-ahead enforcement, including under deliberate mutation
- the Capital Markets check, run and shown failing under `--demo-fail`
- that MANDATE.md agrees with the IPS on all 9 weights, 9 ranges, 3 sleeve
  ranges and 11 scalar limits

**Taken on trust, checked only by the desk's own tests:**

- the 688 Macro desk assertions
- the 53 Implementation desk assertions
- the Ledoit-Wolf shrinkage implementation and its Monte Carlo validation
- every individual cell of the out-of-sample R² table
- the vehicle-level exclusion holdings, said to be from SEC N-PORT filings
- the transaction cost vector's derivation from quoted spreads

**Marked by the desks themselves as recalled rather than verified:**

- **8 of 40** Systematic desk claims (20%)
- two Capital Markets inputs, including the long-run real earnings growth
  assumption in the bottom-up equity cross-check
- Research Affiliates figures, taken from Morningstar because the primary tool
  requires a login

All 8 capital-market houses carry an openable URL. No paywalled source was used
anywhere and no credential was required.

---

## 7. Errors found during the build, and what that implies

Recorded because the ones found suggest the rate, and the rate is not zero.

| Found | What it was | How it was found |
|---|---|---|
| Unit mismatch at the cost interface | Would have made **all twenty decisions holds** | A two-line smoke test |
| Publication-lag test dated on Good Friday | Test passed regardless of the code | The mutation test |
| Anachronism test failing on a missing file | Passed without reaching its check | The mutation test |
| Prose saying 16.3pp where the files said 16.5pp | Four sentences across three documents | **By hand** |
| A wrong causal claim about the Dec-2025 EM sale | Called a view reversal; it was drift correction | **By hand**, while writing this audit |
| The benchmark claim, stated backwards | Report said the benchmark was harder to beat; it is **29.7bps a year easier** | **The second audit pass**, testing a claim never tested |
| “Three independent findings” | Two of the three share a prior; the honest count is two | **The second audit pass** |
| A check too blunt to tell prose from code | The static guard failed on a *sentence about* config.RAW in the audit script | **The suite itself**, third instance of this class |
| `trades_pp` serialised in set order | The record came back byte-different from a clean rerun. **No value moved**, only key order | **Reproducing the study from a fresh clone**, after publication |
| The README's own window example could not run | It asked for 2016, the shipped vintage cache starts 2021-09-30, so the documented command failed on a clean clone | **The same fresh-clone run** |

### 7.1 Two corrections made after publication, by the author

Both rows above were found by cloning the published repository and following the
README, which is the one test the office never ran on itself: it verified its
work in the folder it built it in. Recorded here in full because they are the
first changes to this repository **not made by the agent**, and the repository's
boundary claim is worth more than the appearance of one.

**`taa/costs.py`, `trades_pp` now iterates `sorted(keys)`.** Python randomises
string hashing per process, so a dict built by iterating a set serialises in a
different order every run. Every value was identical across runs; only the order
moved. The effect was that `git diff` on `outputs/decision_record.json` after a
clean rerun showed 66 changed lines, so a reader following the reproduce
instructions saw what looked like a failed reproduction and had no easy way to
tell it was cosmetic. `tests/check_determinism.py` now runs the simulation twice
under different hash seeds and requires byte-identical output, so this class
cannot return silently.

The fix reached one sentence of prose. The dashboard names the trades in a
quarter in order of size, and one quarter moved 1.21pp between two lines in
opposite directions. Equal magnitudes, so the sort tie used to break on whatever
order the set produced, and that sentence could flip between runs on its own.
It now reads the same way every time. No figure changed.

**The README's window example now starts 2023-07-01, and the cache boundary is
stated.** The old example asked for a ten-year window. The shipped ALFRED
vintages begin 2021-09-30, so it raised `FileNotFoundError` on a clean clone.
The point-in-time layer was behaving correctly by refusing to guess; the
documentation was wrong about what it shipped with, and it sat one screen below
a sentence promising the study reproduces with no network at all.

Neither correction moves a number in the study. The recommendation, the record
and every figure in the report are unchanged.

**A pattern worth naming.** Three separate checks in this study were written too
bluntly and failed clean work: a hindsight check matching "0.1" inside an unrelated
signal reading, a figure-drift check reading a table cell as a prose claim, and a
static guard reading a sentence *about* `config.RAW` as an access to it. Each was
tightened rather than loosened, and each took a real failure to notice. A check that
fires on correct work is not merely noisy: it is the thing that gets a guard switched
off by someone who is right to switch it off.

Two of the errors in the table above were found by reading rather than by a test,
which means the detection rate for that class is unknown. A check for the
first now exists (`tests/check_figures.py`, 9 assertions, goes red on demand).
**No check exists for the second class**: a hand-written causal interpretation
of the record that is wrong. Some of the interpretive prose has been spot-checked
against the data. Not all of it has.

---

## 8. If you publish this, say these six things

1. **The five-year record is a simulation of a rule, not a track record.** No
   office ran and no committee met.
2. **The performance numbers cannot be separated from zero**, the sign of the
   active return flips depending on the measurement window, and the benchmark
   they were measured against is about **30bps a year too easy** (§9.1). Against
   a drifting benchmark the programme's active return is negative.
3. **The recommendation does not depend on either of those.** It rests on a
   202bps gap between what the policy portfolio is priced to earn and what the
   spending rule requires. That finding is forward-looking, independent of the
   record, and is the strongest thing in the study.
4. **The claim that the tactical programme fails to clear its costs is true
   ex ante and false on the realised numbers** for this window (§9.3).
   Preferring the ex-ante figure is a defensible judgement, not a fact.
5. **The committee minutes are a construct.** The reasoning and the dissent are
   genuine and sourced; the meeting and its members are not.
6. **The point-in-time discipline is real and was tested to destruction**, but
   it cannot cover the fact that the study's own specification was chosen in
   2026 with knowledge of the period it is applied to.

The one conclusion that strengthened under audit is the **drawdown
incompatibility**: 32% of rolling five-year windows since 2009 breach the
Board's (20)% limit on policy weights alone (§9.4).

---

## 9. Second pass: bias, and claims this office asserted without testing

Run by `tests/audit2.py` into `outputs/audit2.json`. The first pass asked what
was missing. This one asked what was tilted, and it tested five claims the
report made in prose and had never checked. **Two of them were wrong.** Both are
now corrected in the report and both are recorded here rather than quietly
fixed.

### 9.1 The benchmark choice flatters the fund. The report said the opposite.

The report asserted, twice, that a monthly-rebalanced blend is harder to beat
than a drifting one, and that the choice therefore worked against the fund. That
was never tested. It is wrong:

| Benchmark construction | Annualised, five years |
|---|---:|
| Policy portfolio, rebalanced monthly (the one used) | **8.262%** |
| Policy portfolio, never rebalanced | **8.558%** |

The benchmark this study uses is **29.7bps a year easier to beat**. Every active
return in the report is flattered by roughly that amount, which is larger than
the +21.8bps a year the programme is credited with. Measured against the harder
benchmark, the active return is negative.

The benchmark was not changed, because it is the IPS 4.1 blend and the choice
was made before the comparison was run. The report now discloses the direction
and the size of the effect.

### 9.2 The 50/50 reconciliation rule gave one desk roughly twice the weight

Equal weight on two *active vectors* is not equal weight on two *opinions*.

| | Quantitative | Macro |
|---|---:|---:|
| Mean size of the active vector | **14.1pp** | **7.7pp** |
| Quarters it was the larger view | **20 of 20** | 0 of 20 |
| Mean cosine similarity to the adopted allocation | **+0.911** | +0.659 |

The adopted allocation resembles the model desk far more closely than the macro
desk, by a factor of about 1.8 to 1 in position size. The rule was pre-committed
and has not been changed, because altering it after seeing the record is the
failure the pre-commitment exists to prevent. But **the report describing it as
equal weighting was misleading**, and it now says so.

### 9.3 The cost argument: ex ante says no, realised says yes

| | |
|---|---:|
| Systematic desk assumed turnover cost | 6.4bps/yr |
| **Realised turnover cost in the simulation** | **2.6bps/yr** |
| Ratio, assumed to realised | 2.5x |
| Systematic desk expected alpha | 4.2bps/yr |
| **Realised active return** | **+21.8bps/yr** |
| Clears its costs, ex ante | **NO** |
| Clears its costs, realised on this window | **YES** |

The recommendation leads with the ex-ante arithmetic, which is the unfavourable
one. The realised experience over these five years says the opposite. Leading
with the number that supports the conclusion while the other one exists is
exactly the selective presentation an audit should catch, so it is now stated in
the report beside the fundamental-law section.

The office still prefers the ex-ante number, because +21.8bps sits inside a
noise band of roughly plus or minus 45bps, and the same programme returns
(22)bps a year measured over two years. **That preference is a judgement and not
a fact.**

### 9.4 The drawdown finding is robust, and it is the one that survived

The second amendment question rests on the policy portfolio breaching its own
(20)% limit. That would be weak if it depended on the chosen window. It does
not:

| | |
|---|---:|
| Policy portfolio worst drawdown, full cache from 2009 | **(22.46)%** |
| Rolling five-year windows breaching the (20)% limit | **46 of 144, 32%** |
| Worst twelve-month loss | (18.57)% |

Caveat: those 144 windows overlap heavily and the breaches cluster on two
episodes, 2020 and 2022, so this is not 46 independent observations. The honest
statement is that **any five-year window containing either episode breaches the
limit**, and two such episodes occurred in fifteen years.

### 9.5 Three independent findings is really two

The report said three findings, each from a different desk working
independently. The Systematic and Quantitative desks both update from the same
replication literature, so the second corroborates the first rather than
standing apart from it. The genuinely disjoint pair is Capital Markets against
Systematic: a valuation gap and a breadth-and-cost arithmetic share no input.
Corrected in the report.

### 9.6 Coordinator anchoring: four diagnoses sent, four adopted, zero pushback

| Desk | What the office sent | What it contained |
|---|---|---|
| Quantitative | `config.RAW` in signals.py | the diagnosis **and** the fix |
| Implementation | unit contract | the diagnosis **and** the adapter |
| Risk | `range_breach_inside_te` | the root cause, the fix, **and** the forbidden fixes |
| Macro | credit series limitation | the problem **and** the substitute series |

**Every diagnosis the office sent was adopted as sent. No desk pushed back on
one.** In each case the office supplied the answer alongside the problem, which
is efficient and is also the shape of an anchoring effect. Where the office was
right this is invisible. Had it been wrong, nothing in the process would have
surfaced it, because each desk received the conclusion at the same moment as the
question.

The one place the office deliberately guarded against this is the instruction to
the Macro desk to report a disagreement with the office own GDP computation
rather than reconcile to it. That instruction was given once, to one desk, about
one number.

### 9.7 Self-written, self-passed desk checks

| Desk | Assertions | Written by | Reviewed line by line by the office |
|---|---:|---|---|
| Macro | 688 | the desk | no |
| Implementation | 53 | the desk | no |
| Systematic | 26 | the desk | no |
| Capital Markets | 5 | the desk | no |
| Risk | 13 mutants killed | the desk | no |

Every check was re-run by the office and every one passes. **None had its
assertions reviewed.** A desk that writes 688 assertions and passes 688 of them
has demonstrated internal consistency, not correctness. The Risk desk mutation
harness is the strongest of the five, because killing a mutant requires a check
to detect a deliberate break rather than merely to agree with its author.

---

## 10. Revised summary after the second pass

Two claims in the report were wrong and are corrected. One material tension was
under-reported and is now stated. One finding got stronger.

| | |
|---|---|
| Active returns in the report | **Flattered by about 30bps a year** by the benchmark construction. Against a drifting benchmark the active return is negative. |
| The 50/50 rule | Gave the Quantitative desk about 1.8x the influence. Disclosed, not changed. |
| The programme does not clear its costs | True ex ante, **false on realised experience over this window**. Both now in the report. |
| The policy portfolio breaches its drawdown limit | **Robust.** 32% of rolling five-year windows since 2009 breach it. |
| Three independent findings | **Two.** Corrected. |
| Desk work | Internally consistent; not independently re-derived. |

**The recommendation is unchanged**, and after this pass it rests on a narrower
base than the report originally implied: the 202bps valuation gap, which is the
strongest single finding and is independent of everything else here, and the
drawdown incompatibility, which survives the window test.

The evidence that the tactical programme is worthless is **weaker than the report
first presented it**, because the realised numbers on this window are positive
and the benchmark that produced them was the easy one. What carries the
recommendation is the forward-looking arithmetic, not the record.

---

## What would change this note

- An error found in a desk's work that its own tests passed
- Any interpretive claim in the report shown to be wrong, as two already were
- A rerun on a different window producing a materially different conclusion,
  which for the *performance* numbers it already does and for the
  *recommendation* it should not

Re-run `py -3 tests/audit.py` after any change. It writes `outputs/audit.json`
and takes about a minute.
