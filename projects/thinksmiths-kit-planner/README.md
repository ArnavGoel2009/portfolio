# ThinkSmiths Kit Rollout Planner

Small, transparent scenario calculator for multi-batch STEM-kit planning. It computes variable cost, fixed programme cost, contingency and effective per-kit cost.

## Run
`python kit_planner.py`

## Test
`python -m unittest test_kit_planner.py`

## Evidence
The arithmetic core was independently executed in the JARVIS 2026-08-11 QA runtime with three representative assertions passing. Published tests cover no-contingency, fixed-cost + contingency, and invalid kit count.

## Important limitation
Default ₹300/₹400/₹500 unit-cost scenarios are planning examples, not supplier quotes, actual ThinkSmiths historical costs, or sponsor commitments. Replace them with current BOM and logistics quotes before external use. This tool does not model inventory lead time, volume discounts, taxes, failure-rate distributions or multi-SKU kit mixes yet.
