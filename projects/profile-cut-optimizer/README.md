# Profile Cut Optimizer

A kerf-aware 1D cutting-stock optimizer for aluminium/uPVC window-profile fabrication. It turns a cut list into stock-bar assignments intended to reduce offcut waste.

## What it does
- keeps profile/SKU types separate;
- accounts for saw kerf between adjacent cuts;
- validates impossible/non-positive inputs;
- exact symmetry-pruned branch-and-bound for modest jobs;
- Best-Fit-Decreasing fallback for larger jobs;
- bar-by-bar JSON cut plan;
- reproducible heuristic benchmarks.

## Run
`python cli.py data/sample_job.csv --stock 6000 --kerf 3 --out cut_plan.json`

`python -m unittest discover -s tests -v`

`python benchmark.py`

## Validation
Seven unit tests cover kerf accounting, exact-fit boundaries, impossible cuts, exact-vs-heuristic bar count, ID preservation, profile separation, and randomized no-overfill invariants.

A seeded synthetic benchmark (`seed=20260810`) compares sequential input-order cutting with FFD and BFD for 20/50/100/250 pieces. BFD/FFD used 1, 2, 5 and 14 fewer 6 m bars respectively on those synthetic cases. These are **not Green Future factory savings**.

## Limitations
Decision-support only. Assumes one-dimensional straight cuts, constant kerf, integer-mm lengths, no remnant inventory, defect zones, paired constraints, minimum reusable offcut, clamp/end-trim allowance, or ERP integration. Real production validation requires actual historical cut lists and machine constraints.

## Next validation
Run one anonymised historical production job with actual stock/kerf/end-trim rules and compare actual issued bars against the suggested plan before operational use.