importScripts("core.js");

const STORAGE_DEFAULTS = {
  config: FocusCore.DEFAULT_CONFIG,
  session: null,
  unlocks: [],
  intentionLog: [],
  bypassLog: [],
  stats: {
    blockedAttempts: 0,
    intentionalUnlocks: 0,
    emergencyBypasses: 0,
    focusMinutes: 0
  }
};

function getState() {
  return new Promise(resolve => chrome.storage.local.get(STORAGE_DEFAULTS, resolve));
}

function setState(values) {
  return new Promise(resolve => chrome.storage.local.set(values, resolve));
}

async function finalizeExpiredSession(state, now = Date.now()) {
  const session = state.session;
  if (!session || FocusCore.isSessionActive(session, now) || Number(session.endsAt) > now) {
    return state;
  }

  const elapsed = FocusCore.completedSessionMinutes(session, now);
  const stats = {
    ...state.stats,
    focusMinutes: (state.stats.focusMinutes || 0) + elapsed
  };
  await setState({session: null, stats});
  return {...state, session: null, stats};
}

async function refreshRules() {
  let state = await getState();
  const now = Date.now();
  state = await finalizeExpiredSession(state, now);

  const config = FocusCore.sanitizeConfig(state.config);
  const unlocks = FocusCore.cleanupUnlocks(state.unlocks, now);
  const active = FocusCore.isFocusActive(config, {session: state.session}, now);

  const existing = await chrome.declarativeNetRequest.getDynamicRules();
  const removeRuleIds = existing.map(rule => rule.id);
  const addRules = active ? FocusCore.buildDnrRules(config, {unlocks}, now) : [];

  await chrome.declarativeNetRequest.updateDynamicRules({
    removeRuleIds,
    addRules
  });

  if (unlocks.length !== (state.unlocks || []).length) {
    await setState({unlocks});
  }

  const remaining = FocusCore.remainingSeconds(state.session, now);
  const badge = remaining ? String(Math.ceil(remaining / 60)) : (active ? "ON" : "");
  await chrome.action.setBadgeText({text: badge});
  return {active, remaining, ruleCount: addRules.length};
}

chrome.runtime.onInstalled.addListener(async details => {
  const current = await getState();
  await setState({
    config: FocusCore.sanitizeConfig(current.config),
    stats: current.stats || STORAGE_DEFAULTS.stats
  });
  await refreshRules();
  if (details.reason === "install") {
    chrome.tabs.create({url: chrome.runtime.getURL("onboarding.html")});
  }
});

chrome.runtime.onStartup.addListener(refreshRules);
chrome.alarms.create("focus-friction-tick", {periodInMinutes: 1});
chrome.alarms.onAlarm.addListener(refreshRules);
chrome.storage.onChanged.addListener((changes, area) => {
  if (area === "local" && (changes.config || changes.session || changes.unlocks)) {
    refreshRules();
  }
});

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  (async () => {
    let state = await getState();
    const now = Date.now();
    state = await finalizeExpiredSession(state, now);
    const config = FocusCore.sanitizeConfig(state.config);

    if (message.type === "GET_STATUS") {
      sendResponse({
        ok: true,
        config,
        session: state.session,
        active: FocusCore.isFocusActive(config, state, now),
        remaining: FocusCore.remainingSeconds(state.session, now),
        stats: state.stats
      });
      return;
    }

    if (message.type === "START_SESSION") {
      const session = FocusCore.startSession(message.minutes || config.focusMinutes, now);
      await setState({session});
      await refreshRules();
      sendResponse({ok: true, session});
      return;
    }

    if (message.type === "STOP_SESSION") {
      const elapsed = FocusCore.completedSessionMinutes(state.session, now);
      const stats = {
        ...state.stats,
        focusMinutes: (state.stats.focusMinutes || 0) + elapsed
      };
      await setState({session: null, stats});
      await refreshRules();
      sendResponse({ok: true, elapsed});
      return;
    }

    if (message.type === "RECORD_BLOCK") {
      const stats = {
        ...state.stats,
        blockedAttempts: (state.stats.blockedAttempts || 0) + 1
      };
      await setState({stats});
      sendResponse({ok: true});
      return;
    }

    if (message.type === "INTENTIONAL_UNLOCK") {
      const domain = FocusCore.normaliseDomain(message.domain);
      const unlocks = FocusCore.addTemporaryUnlock(
        state.unlocks, domain, config.temporaryUnlockMinutes, now
      );
      const intentionLog = FocusCore.appendLocalLog(state.intentionLog, {
        domain,
        intention: String(message.intention || "").trim().slice(0, 280),
        mode: String(message.mode || config.frictionMode)
      });
      const stats = {
        ...state.stats,
        intentionalUnlocks: (state.stats.intentionalUnlocks || 0) + 1
      };
      await setState({unlocks, intentionLog, stats});
      await refreshRules();
      sendResponse({ok: true, expiresAt: unlocks[0]?.expiresAt || null});
      return;
    }

    if (message.type === "EMERGENCY_BYPASS") {
      const domain = FocusCore.normaliseDomain(message.domain);
      const unlocks = FocusCore.addTemporaryUnlock(
        state.unlocks, domain, config.temporaryUnlockMinutes, now
      );
      const bypassLog = FocusCore.appendLocalLog(state.bypassLog, {
        domain,
        reason: String(message.reason || "").trim().slice(0, 280)
      });
      const stats = {
        ...state.stats,
        emergencyBypasses: (state.stats.emergencyBypasses || 0) + 1
      };
      await setState({unlocks, bypassLog, stats});
      await refreshRules();
      sendResponse({ok: true, expiresAt: unlocks[0]?.expiresAt || null});
      return;
    }

    sendResponse({ok:false, error:"Unknown message type"});
  })().catch(error => sendResponse({ok:false, error:error.message}));
  return true;
});
