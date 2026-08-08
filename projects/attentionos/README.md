# AttentionOS

A local-first attention and productivity system that turns real focus sessions into useful personal patterns.

## Features
- task triage using impact, urgency and effort
- 25/45 minute focus sessions
- one-click interruption logging
- transparent focus score and task ranking
- observed best-hour insight
- local-only browser storage
- JSON export
- responsive dark UI

## Privacy
No account, server, telemetry, browsing-history collection, camera or microphone. Data remains in browser localStorage.

## Important boundary
AttentionOS is a productivity tool, not a medical device. Its focus score is a transparent heuristic, not a diagnosis or measure of ADHD.

## Test
`node tests/core.test.js`

## Status
Core logic is unit-tested. Browser interaction still needs a manual real-browser pass.

## Portfolio description
A privacy-first productivity experiment that ranks tasks, logs interruptions and learns useful time-of-day patterns from local focus-session data without collecting browsing history.