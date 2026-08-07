# START HERE

## WHAT THIS IS

Focus Friction is a Chrome Manifest V3 productivity extension built around one idea: distracting websites should require a deliberate decision during focus time, not be permanently forbidden.

## WHY IT MATTERS

The project turns an attention-management problem into a product and engineering problem: how much friction is useful, when does it become annoying, how do you preserve an emergency exit, and how do you keep browsing data private?

## WHAT WAS COMPLETED TODAY

- Rebuilt the extension as inspectable source code
- Added browser-level dynamic redirect rules
- Added timed focus sessions
- Added recurring focus schedules
- Added intention, delay and vocabulary modes
- Added expiring temporary unlocks
- Added non-shaming emergency bypass
- Added local statistics and logs
- Added onboarding and settings UI
- Added automated unit tests
- Added documentation, privacy boundaries and limitations

## HOW TO USE IT

Load the folder as an unpacked Chrome extension, configure blocked domains and start a focus session.

## TESTING

Run `node tests/core.test.js`.

## WHAT ARNAV NEEDS TO DO

One short manual Chrome test:

1. Load the extension unpacked.
2. Block one harmless website.
3. Start a five-minute session.
4. Confirm redirect.
5. Test one intentional unlock.
6. Confirm the site re-blocks after the temporary unlock expires.

## RECOMMENDATION

REVIEW FIRST, then pilot. Do not claim users or outcomes until they actually exist.
