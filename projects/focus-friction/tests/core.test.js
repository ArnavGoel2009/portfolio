const assert = require("assert");
const core = require("../core.js");

const NOW = Date.parse("2026-08-07T05:00:00Z");

assert.strictEqual(core.normaliseDomain("https://www.YouTube.com/watch?v=1"), "youtube.com");
assert.deepStrictEqual(core.uniqueDomains(["reddit.com","https://www.reddit.com/a","x.com"]), ["reddit.com","x.com"]);

const cfg = core.sanitizeConfig({
  blockedSites:["https://www.instagram.com","reddit.com","reddit.com"],
  focusMinutes:999,
  temporaryUnlockMinutes:0,
  frictionMode:"nonsense",
  schedule:{enabled:true,days:[1,1,9,5],start:"19:00",end:"22:00"}
});
assert.deepStrictEqual(cfg.blockedSites, ["instagram.com","reddit.com"]);
assert.strictEqual(cfg.focusMinutes, 240);
assert.strictEqual(cfg.temporaryUnlockMinutes, 1);
assert.strictEqual(cfg.frictionMode, "intention");
assert.deepStrictEqual(cfg.schedule.days, [1,5]);

const session = core.startSession(25, NOW);
assert.strictEqual(core.isSessionActive(session, NOW + 24*60_000), true);
assert.strictEqual(core.isSessionActive(session, NOW + 26*60_000), false);
assert.strictEqual(core.remainingSeconds(session, NOW + 60_000), 24*60);

const monday1930 = new Date("2026-08-10T19:30:00");
const monday2230 = new Date("2026-08-10T22:30:00");
assert.strictEqual(core.isScheduleActive({enabled:true,days:[1],start:"19:00",end:"22:00"}, monday1930), true);
assert.strictEqual(core.isScheduleActive({enabled:true,days:[1],start:"19:00",end:"22:00"}, monday2230), false);
const overnight = new Date("2026-08-10T23:30:00");
assert.strictEqual(core.isScheduleActive({enabled:true,days:[1],start:"22:00",end:"06:00"}, overnight), true);

assert.strictEqual(core.domainMatches("m.youtube.com","youtube.com"), true);
assert.strictEqual(core.domainMatches("notyoutube.com","youtube.com"), false);

let unlocks = core.addTemporaryUnlock([], "https://reddit.com/r/test", 10, NOW);
assert.strictEqual(unlocks[0].domain, "reddit.com");
assert.strictEqual(core.isTemporarilyUnlocked("www.reddit.com", unlocks, NOW + 9*60_000), true);
assert.strictEqual(core.isTemporarilyUnlocked("www.reddit.com", unlocks, NOW + 11*60_000), false);
assert.deepStrictEqual(core.cleanupUnlocks(unlocks, NOW + 11*60_000), []);

assert.strictEqual(core.validateIntention("I need one tutorial for homework"), true);
assert.strictEqual(core.validateIntention("youtube"), false);
assert.strictEqual(core.validateVocabulary(" Focus ", "focus"), true);

const item = core.chooseVocabulary([{prompt:"a",answer:"b"}], () => 0.2);
assert.strictEqual(item.answer, "b");

const rules = core.buildDnrRules(
  {blockedSites:["youtube.com","reddit.com"]},
  {unlocks:[{domain:"reddit.com",expiresAt:NOW+10000}]},
  NOW
);
assert.strictEqual(rules.length, 1);
assert.strictEqual(rules[0].condition.urlFilter, "||youtube.com^");
assert.strictEqual(rules[0].action.redirect.extensionPath.includes("youtube.com"), true);

const log = core.appendLocalLog([], {domain:"reddit.com",reason:"Need documentation"}, 10);
assert.strictEqual(log.length, 1);
assert.strictEqual(log[0].domain, "reddit.com");

console.log("Focus Friction: all core unit tests passed.");
