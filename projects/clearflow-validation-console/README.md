# ClearFlow Validation Console

A local-first browser tool for recording and summarising **controlled mock prototype tests** for ClearFlow.

The goal is not to make the prototype look more successful. The goal is to make failures, repeats and claim boundaries easier to document.

## Records
Tool head, mock blockage, measured clear time when available, outcome, jam/stall observation, camera usefulness, and failure notes.

## Metrics
Only **real records** count. Demo records are clearly flagged and excluded.
- total real trials
- full-clear success rate
- jam/stall rate
- median measured time among successful trials

## Privacy
All records remain in browser `localStorage`. No server, account, telemetry or cloud analytics.

## Run
Open `index.html` in a modern browser.

## Test
`node tests/core.test.js`

## Claim boundary
This tool does **not** establish real sewer field performance, worker safety outcomes, municipal approval/deployment, or calibrated hazardous-gas accuracy.

## Status
Core data/metrics logic tested. Browser UI still requires a manual visual check in a real browser profile.
