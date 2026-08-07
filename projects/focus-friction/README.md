# Focus Friction

Focus Friction is a privacy-first Chrome extension that adds a small, configurable pause between an impulse and a distracting website.

Instead of using a punitive all-or-nothing blocker, it asks the user to make access intentional.

## Product idea

During a focus session or scheduled focus window, chosen websites redirect to a local intervention screen. The user can:

- write a specific reason for opening the site,
- wait through a short delay,
- complete an optional vocabulary challenge,
- go back,
- or use a clearly labeled emergency bypass.

Successful access creates only a temporary local unlock. It does not permanently weaken the blocklist.

## Features

- Chrome Manifest V3
- Dynamic browser-level blocking through `declarativeNetRequest`
- Manual focus sessions
- Automatic recurring focus schedule
- Blocklist configuration
- Three friction modes: typed intention, short delay, vocabulary challenge
- Temporary unlocks with expiry
- Non-shaming emergency bypass
- Local intention and bypass logs
- Local-only statistics
- Onboarding page
- Popup status and countdown
- Settings dashboard
- Unit-tested core logic
- No external analytics or server

## Privacy

Focus Friction stores configuration, unlock history, intentions, bypass reasons and counters with `chrome.storage.local`. It does not send browsing history, reasons, statistics, usernames, or website data to a remote service.

## Install locally

1. Download this project.
2. Open `chrome://extensions`.
3. Enable Developer mode.
4. Click Load unpacked.
5. Select the project folder.
6. Configure your blocklist.
7. Start a focus session.

## Automated testing

Run `node tests/core.test.js`.

## Current limitations

- A real Chrome manual integration test is still required after loading the unpacked extension.
- The user can always disable the extension because this is not device-management software.
- Local logs are intentionally simple and do not attempt to infer mental-health outcomes.
- The extension should not be represented as a clinical ADHD treatment.

## Portfolio line

Built a privacy-first Chrome extension that uses temporary, intentional friction rather than hard blocking, with scheduled focus windows, local-only data, configurable unlock modes, expiring access and tested core logic.

## Status

REVIEW FIRST. Core logic is tested. Manual Chrome integration testing remains before public release.
