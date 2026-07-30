# How this was built

This study was produced by an AI agent working from a single written brief. This
note records how, so a reader can judge the result knowing what produced it.
Nothing here changes a number. `AUDIT.md` is the document that tells you what to
trust; this one tells you where it came from.

---

## The brief

`PROMPT.md` is the brief, unedited. It is the whole of what the agent was told.

It does three things. It appoints a role and an obligation, Chief Investment
Officer owing a recommendation the trustees can audit. It names two governing
documents, `IPS.pdf` and `MANDATE.md`, and says which wins when they disagree.
And it constitutes an office rather than a task list: independent desks, each
one existing only if its work can proceed without waiting on another desk and if
its output can be checked by something other than the desk that produced it.

What the brief deliberately does not contain: the recommendation, the window, the
methods, the file layout, or the tests. Those are the agent's work, which is the
point of the exercise. The brief sets the constraints and the standard of proof
and then gets out of the way.

---

## What the agent produced

Everything in this repository apart from `PROMPT.md`, `IPS.pdf` and `MANDATE.md`.

| | |
|---|---|
| `taa/` | the study itself, about 20 modules |
| `desks/` | six desk papers, 3,883 lines |
| `tests/` | 14 verification scripts |
| `report/`, `outputs/` | the trustee report, the decision record, the dashboard |
| `methods.ipynb` | methods tied to their sources |
| `AUDIT.md` | the pre-publication audit note |
| `README.md` | this repository's front page |

The six desks ran as separate units of work. Two of them, Quantitative and Macro,
were run concurrently and blind to each other on disjoint briefs, writing to
separate output directories. Their pre-reconciliation drafts are preserved
unchanged in the report's evidence appendix. They disagreed by 16.5 percentage
points on Treasury duration. That disagreement is reported rather than smoothed
over, which is the reason for running them blind in the first place.

---

## The order things happened in

1. **Read the governing documents.** `MANDATE.md` is checked against `IPS.pdf` by
   `tests/check_mandate.py`, so the extract cannot silently drift from the
   authority it claims to summarise.
2. **Build the wall first.** `taa/pitdata.py` is the only route to historical
   data and refuses anything published after the as-of date. Everything else is
   written on top of it.
3. **Desks work, each owning a check.** A desk paper is not accepted on its own
   authority. Each has a corresponding script in `tests/` that returns pass or
   fail without a judgement call.
4. **Break the enforcement on purpose.** `tests/mutation_test.py` removes the
   look-ahead protection one piece at a time in a sandbox copy and requires the
   suite to go red. Its first run found three surviving mutations, and two of
   those turned out to be defects in the tests rather than in the code.
5. **Audit before publishing, twice.** `tests/audit.py` asks what is missing.
   `tests/audit2.py` asks what is tilted. Both write JSON that `AUDIT.md` quotes,
   so the audit note can be recomputed rather than believed.

The sequence matters more than any individual step. The tests were written to
fail, then shown failing, then shown passing. A check that has only ever passed
is not evidence of anything, and the repository is arranged so a reader can prove
that for themselves with `--demo-fail`.

---

## The environment it ran in

Stated plainly, because it affects how far the result generalises.

This was **run on my own machine, inside my normal working setup**, not in a
clean room. That environment already had a global instruction file, a set of
installed skills, several MCP servers, and plugins available to the agent. I did
not stand up a fresh sandbox for it, and I am not claiming the result is
reproducible from a bare install of any particular tool.

What that does **not** mean, and what the repository is arranged to prove:

- **No API key is used anywhere in the study.** Every source is public and free.
  Yahoo Finance for prices, FRED for rates and spreads, ALFRED for macro
  vintages, published house forecasts for capital market assumptions, and
  issuer-published spreads for vehicles.
- **Nothing is imported from elsewhere on the machine.** The study runs from this
  folder alone.
- **No paywalled source was consulted.**
- **The output is reproducible from the code here.** Clone, run the commands in
  the README, and the numbers come back the same. The window is a parameter, so
  the whole study also reproduces on a different window with no other edit.

So the honest framing is this. The *study* is reproducible from this folder. The
*process that generated it* ran in a configured environment, and someone
reproducing that part from scratch should expect to do their own configuration.

---

## What a reader should check first

If you have five minutes and want to know whether this is real:

1. `AUDIT.md`, short version table at the top. It states what cannot be trusted
   before it states what can.
2. `py -3 tests/mutation_test.py`. It is the one that proves the tests bite.
3. `py -3 tests/test_lookahead.py --demo-fail`. Watch a planted violation get
   caught.
4. The two blind desk drafts in the evidence appendix, and the 16.5 point
   disagreement between them.

If you have longer, `methods.ipynb` ties every method to the paper it comes from,
and the six desk papers carry the reasoning the report only summarises.

---

## What this is not

It is not a live strategy, not investment advice, and not a claim that an agent
can replace an investment office. It is one attempt at a harder question: whether
an agent given a real mandate, real constraints and an obligation to be audited
produces work that survives being audited. `AUDIT.md` is where that question is
answered honestly, including the places where the answer is no.
