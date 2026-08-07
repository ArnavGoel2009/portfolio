const $ = id => document.getElementById(id);
const params = new URLSearchParams(location.search);
const domain = FocusCore.normaliseDomain(params.get("domain") || "blocked site");
$("domain").textContent = domain;

chrome.runtime.sendMessage({type:"RECORD_BLOCK"});

function unlock(payload) {
  chrome.runtime.sendMessage({type:"INTENTIONAL_UNLOCK", domain, ...payload}, response => {
    if (!response?.ok) {
      $("message").textContent = response?.error || "Could not unlock this site.";
      return;
    }
    location.replace("https://" + domain);
  });
}

chrome.storage.local.get({config: FocusCore.DEFAULT_CONFIG}, data => {
  const config = FocusCore.sanitizeConfig(data.config);
  if (config.frictionMode === "delay") {
    $("delaySection").classList.remove("hidden");
    let remaining = config.delaySeconds;
    $("countdown").textContent = remaining;
    const tick = setInterval(() => {
      remaining -= 1;
      $("countdown").textContent = Math.max(0, remaining);
      if (remaining <= 0) {
        clearInterval(tick);
        $("delayContinue").classList.remove("hidden");
      }
    }, 1000);
    $("delayContinue").addEventListener("click", () => unlock({mode:"delay", intention:"waited before continuing"}));
    return;
  }
  if (config.frictionMode === "vocabulary") {
    $("vocabSection").classList.remove("hidden");
    const item = FocusCore.chooseVocabulary(config.vocabulary);
    $("vocabPrompt").textContent = item.prompt;
    $("vocabContinue").addEventListener("click", () => {
      if (!FocusCore.validateVocabulary($("vocabAnswer").value, item.answer)) {
        $("message").textContent = "Not quite. Try again, or go back.";
        return;
      }
      unlock({mode:"vocabulary", intention:"completed challenge"});
    });
    return;
  }
  $("intentionSection").classList.remove("hidden");
  $("intentContinue").addEventListener("click", () => {
    const value = $("intention").value;
    if (!FocusCore.validateIntention(value)) {
      $("message").textContent = "Write a short, specific intention first.";
      return;
    }
    unlock({mode:"intention", intention:value});
  });
});

$("back").addEventListener("click", () => history.length > 1 ? history.back() : location.replace("about:blank"));

$("bypass").addEventListener("click", () => {
  const reason = $("reason").value.trim();
  if (reason.length < 5) {
    $("message").textContent = "Add a short reason first.";
    return;
  }
  chrome.runtime.sendMessage({type:"EMERGENCY_BYPASS", domain, reason}, response => {
    if (!response?.ok) {
      $("message").textContent = response?.error || "Bypass failed.";
      return;
    }
    location.replace("https://" + domain);
  });
});
