# AttentionOS

A local-first attention and productivity system that turns real focus sessions into useful personal patterns.

## Features
- task triage using impact, urgency and effort
- 25/45 minute focus sessions
- explicit stop-and-save control for interrupted sessions
- active-session recovery after page reload
- one-click interruption logging
- transparent focus score and deterministic task ranking
- adaptive duration recommendation only after at least 3 real sessions
- observed best-hour insight with invalid timestamps ignored
- seven-day focus/session/interruption trend
- JSON export and validated JSON restore
- local-only browser storage
- responsive dark UI

## Privacy
No account, server, telemetry, browsing-history collection, camera or microphone. Data remains in browser localStorage.

## Important boundary
AttentionOS is a productivity tool, not a medical device. Its focus score is a transparent heuristic, not a diagnosis or measure of ADHD. Early data is treated cautiously: the UI does not present an adaptive duration as meaningful until at least three sessions exist.

## Test
`node tests/core.test.js`

QA coverage includes task ranking, focus scoring, summaries, invalid timestamps, recommendation gating, seven-day aggregation and backup validation.

## Status
Core logic is unit-tested. Browser interaction still needs a manual real-browser pass; that limitation is intentionally not hidden.

## Portfolio description
A privacy-first productivity experiment that ranks tasks, survives interrupted focus sessions, logs interruptions and learns useful time-of-day patterns from local focus-session data without collecting browsing history.