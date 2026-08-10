# Independent QA — 2026-08-10

Recovery independently inspected the published optimizer source rather than relying on the overnight status report.

## Validation added

The test suite now includes an independent brute-force oracle for small cutting-stock instances. With a fixed seed, 25 random cases containing 3–8 pieces are solved both by the production branch-and-bound solver and by a deliberately simple exhaustive assignment search. The required bar counts must match exactly.

The updated 8-test suite was reconstructed from the published `optimizer.py` plus updated test file and executed in the QA runtime. Result: **8 tests passed**. The pre-existing tests also cover kerf arithmetic, exact-fit boundaries, impossible pieces, exact-vs-heuristic ordering, ID preservation, profile separation, and 100-piece no-overfill stress checks.

## Reviewer findings

- The solver's primary objective is minimising number of stock bars. For a fixed piece set, stock length and kerf model, this also fixes aggregate offcut/waste for a given bar count because the total piece length is fixed and total internal cut count is `pieces - bars`.
- The branch-and-bound lower bound is optimistic because it ignores additional future kerf in the remaining-length bound; that makes pruning weaker, not unsafe.
- Profile types are optimised separately, avoiding invalid mixing of incompatible extrusion profiles.
- Real-factory claims remain **unvalidated** until actual Green Future stock length, saw kerf, end-trim/clamp allowance, remnant policy and anonymised historical cut lists are supplied.

## Evidence classification

- Algorithm correctness: unit/stress/oracle-tested in software.
- Benchmark data: synthetic unless explicitly labelled otherwise.
- Factory savings: **not claimed**.
- Physical cutting validation: pending.
