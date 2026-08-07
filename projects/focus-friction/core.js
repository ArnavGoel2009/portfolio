(function (root, factory) {
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  else root.FocusCore = api;
})(typeof self !== "undefined" ? self : this, function () {
  "use strict";

  const DEFAULT_CONFIG = Object.freeze({
    blockedSites: ["instagram.com", "reddit.com", "x.com"],
    frictionMode: "intention",
    delaySeconds: 12,
    temporaryUnlockMinutes: 10,
    focusMinutes: 25,
    schedule: {
      enabled: false,
      days: [1,2,3,4,5],
      start: "19:00",
      end: "22:00"
    },
    vocabulary: [
      { prompt: "Translate: aprender", answer: "to learn" },
      { prompt: "Translate: enfoque", answer: "focus" },
      { prompt: "Translate: lograr", answer: "to achieve" }
    ]
  });

  function clone(value) {
    return JSON.parse(JSON.stringify(value));
  }

  function normaliseDomain(input) {
    if (!input || typeof input !== "string") return "";
    let value = input.trim().toLowerCase();
    try {
      if (!value.includes("://")) value = "https://" + value;
      value = new URL(value).hostname;
    } catch {
      value = value.replace(/^https?:\/\//, "").split("/")[0];
    }
    return value.replace(/^www\./, "").replace(/\.$/, "");
  }

  function uniqueDomains(list) {
    return [...new Set((Array.isArray(list) ? list : [])
      .map(normaliseDomain)
      .filter(Boolean))];
  }

  function clamp(number, min, max, fallback) {
    const n = Number(number);
    return Number.isFinite(n) ? Math.min(max, Math.max(min, n)) : fallback;
  }

  function sanitizeConfig(raw) {
    const input = raw || {};
    const scheduleInput = input.schedule || {};
    const cfg = clone(DEFAULT_CONFIG);
    cfg.blockedSites = uniqueDomains(input.blockedSites ?? cfg.blockedSites);
    cfg.frictionMode = ["intention", "delay", "vocabulary"].includes(input.frictionMode)
      ? input.frictionMode : cfg.frictionMode;
    cfg.delaySeconds = clamp(input.delaySeconds, 0, 120, cfg.delaySeconds);
    cfg.temporaryUnlockMinutes = clamp(input.temporaryUnlockMinutes, 1, 120, cfg.temporaryUnlockMinutes);
    cfg.focusMinutes = clamp(input.focusMinutes, 1, 240, cfg.focusMinutes);
    cfg.schedule.enabled = Boolean(scheduleInput.enabled);
    cfg.schedule.days = [...new Set((Array.isArray(scheduleInput.days) ? scheduleInput.days : cfg.schedule.days)
      .map(Number).filter(day => Number.isInteger(day) && day >= 0 && day <= 6))];
    cfg.schedule.start = /^\d{2}:\d{2}$/.test(scheduleInput.start || "") ? scheduleInput.start : cfg.schedule.start;
    cfg.schedule.end = /^\d{2}:\d{2}$/.test(scheduleInput.end || "") ? scheduleInput.end : cfg.schedule.end;
    cfg.vocabulary = Array.isArray(input.vocabulary) && input.vocabulary.length
      ? input.vocabulary
          .filter(item => item && String(item.prompt || "").trim() && String(item.answer || "").trim())
          .map(item => ({prompt: String(item.prompt).trim(), answer: String(item.answer).trim()}))
      : cfg.vocabulary;
    return cfg;
  }

  function startSession(minutes, now = Date.now()) {
    const safe = clamp(minutes, 1, 240, DEFAULT_CONFIG.focusMinutes);
    return {
      active: true,
      startedAt: now,
      endsAt: now + safe * 60_000,
      plannedMinutes: safe
    };
  }

  function isSessionActive(session, now = Date.now()) {
    return Boolean(session && session.active && Number(session.endsAt) > now);
  }

  function remainingSeconds(session, now = Date.now()) {
    return isSessionActive(session, now)
      ? Math.max(0, Math.ceil((session.endsAt - now) / 1000))
      : 0;
  }

  function completedSessionMinutes(session, now = Date.now()) {
    if (!session) return 0;
    const startedAt = Number(session.startedAt);
    const endsAt = Number(session.endsAt);
    if (!Number.isFinite(startedAt) || !Number.isFinite(endsAt) || endsAt <= startedAt) return 0;
    const boundedEnd = Math.min(Number(now), endsAt);
    return Math.max(0, Math.round((boundedEnd - startedAt) / 60_000));
  }

  function timeToMinutes(value) {
    if (!/^\d{2}:\d{2}$/.test(value || "")) return null;
    const [h,m] = value.split(":").map(Number);
    if (h > 23 || m > 59) return null;
    return h * 60 + m;
  }

  function isScheduleActive(schedule, date = new Date()) {
    if (!schedule || !schedule.enabled) return false;
    const days = Array.isArray(schedule.days) ? schedule.days : [];
    const start = timeToMinutes(schedule.start);
    const end = timeToMinutes(schedule.end);
    if (start === null || end === null || start === end) return false;

    const current = date.getHours() * 60 + date.getMinutes();
    const day = date.getDay();

    if (start < end) {
      return days.includes(day) && current >= start && current < end;
    }

    const previousDay = (day + 6) % 7;
    return (days.includes(day) && current >= start) ||
      (days.includes(previousDay) && current < end);
  }

  function isFocusActive(config, state, now = Date.now(), date = new Date(now)) {
    return isSessionActive(state && state.session, now) || isScheduleActive(config.schedule, date);
  }

  function domainMatches(host, candidate) {
    const h = normaliseDomain(host);
    const c = normaliseDomain(candidate);
    return Boolean(h && c && (h === c || h.endsWith("." + c)));
  }

  function isTemporarilyUnlocked(host, unlocks, now = Date.now()) {
    return (Array.isArray(unlocks) ? unlocks : []).some(entry =>
      entry && domainMatches(host, entry.domain) && Number(entry.expiresAt) > now
    );
  }

  function cleanupUnlocks(unlocks, now = Date.now()) {
    return (Array.isArray(unlocks) ? unlocks : []).filter(entry =>
      entry && normaliseDomain(entry.domain) && Number(entry.expiresAt) > now
    );
  }

  function addTemporaryUnlock(unlocks, domain, minutes, now = Date.now()) {
    const host = normaliseDomain(domain);
    if (!host) return cleanupUnlocks(unlocks, now);
    const duration = clamp(minutes, 1, 120, DEFAULT_CONFIG.temporaryUnlockMinutes);
    const cleaned = cleanupUnlocks(unlocks, now).filter(entry => !domainMatches(entry.domain, host));
    return [{domain: host, expiresAt: now + duration * 60_000}, ...cleaned].slice(0, 100);
  }

  function validateIntention(text) {
    const value = String(text || "").trim();
    return value.length >= 12 && value.split(/\s+/).length >= 3;
  }

  function validateVocabulary(input, expected) {
    return String(input || "").trim().toLowerCase() === String(expected || "").trim().toLowerCase();
  }

  function chooseVocabulary(items, random = Math.random) {
    const list = Array.isArray(items) && items.length ? items : DEFAULT_CONFIG.vocabulary;
    const index = Math.min(list.length - 1, Math.max(0, Math.floor(random() * list.length)));
    return list[index];
  }

  function buildDnrRules(config, state, now = Date.now()) {
    const cfg = sanitizeConfig(config);
    const unlocks = cleanupUnlocks(state && state.unlocks, now);
    return cfg.blockedSites
      .filter(domain => !unlocks.some(entry => domainMatches(domain, entry.domain)))
      .map((domain, index) => ({
        id: index + 1,
        priority: 1,
        action: {
          type: "redirect",
          redirect: {
            extensionPath: "/blocked.html?domain=" + encodeURIComponent(domain)
          }
        },
        condition: {
          urlFilter: "||" + domain + "^",
          resourceTypes: ["main_frame"]
        }
      }));
  }

  function appendLocalLog(log, item, max = 100) {
    return [Object.assign({timestamp: new Date().toISOString()}, item),
      ...(Array.isArray(log) ? log : [])].slice(0, max);
  }

  return {
    DEFAULT_CONFIG,
    normaliseDomain,
    uniqueDomains,
    sanitizeConfig,
    startSession,
    isSessionActive,
    remainingSeconds,
    completedSessionMinutes,
    timeToMinutes,
    isScheduleActive,
    isFocusActive,
    domainMatches,
    isTemporarilyUnlocked,
    cleanupUnlocks,
    addTemporaryUnlock,
    validateIntention,
    validateVocabulary,
    chooseVocabulary,
    buildDnrRules,
    appendLocalLog
  };
});
