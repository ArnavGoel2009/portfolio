const $ = id => document.getElementById(id);
const dayNames = ["Sun","Mon","Tue","Wed","Thu","Fri","Sat"];

function parseLines(value) {
  return value.split(/\n|,/).map(x => x.trim()).filter(Boolean);
}

function renderDays(selected) {
  $("days").innerHTML = "";
  dayNames.forEach((name, index) => {
    const label = document.createElement("label");
    label.innerHTML = `<input type="checkbox" value="${index}" ${selected.includes(index) ? "checked" : ""}> ${name}`;
    $("days").appendChild(label);
  });
}

function load() {
  chrome.storage.local.get({
    config: FocusCore.DEFAULT_CONFIG,
    stats: {blockedAttempts:0,intentionalUnlocks:0,emergencyBypasses:0,focusMinutes:0}
  }, data => {
    const c = FocusCore.sanitizeConfig(data.config);
    $("blocked").value = c.blockedSites.join("\n");
    $("focusMinutes").value = c.focusMinutes;
    $("unlockMinutes").value = c.temporaryUnlockMinutes;
    $("mode").value = c.frictionMode;
    $("delaySeconds").value = c.delaySeconds;
    $("scheduleEnabled").checked = c.schedule.enabled;
    $("scheduleStart").value = c.schedule.start;
    $("scheduleEnd").value = c.schedule.end;
    renderDays(c.schedule.days);
    $("blocks").textContent = data.stats.blockedAttempts || 0;
    $("unlocks").textContent = data.stats.intentionalUnlocks || 0;
    $("bypasses").textContent = data.stats.emergencyBypasses || 0;
    $("minutes").textContent = data.stats.focusMinutes || 0;
  });
}

$("save").addEventListener("click", () => {
  const days = [...$("days").querySelectorAll("input:checked")].map(el => Number(el.value));
  const config = FocusCore.sanitizeConfig({
    blockedSites: parseLines($("blocked").value),
    focusMinutes: Number($("focusMinutes").value),
    temporaryUnlockMinutes: Number($("unlockMinutes").value),
    frictionMode: $("mode").value,
    delaySeconds: Number($("delaySeconds").value),
    schedule: {
      enabled: $("scheduleEnabled").checked,
      days,
      start: $("scheduleStart").value,
      end: $("scheduleEnd").value
    }
  });
  chrome.storage.local.set({config}, () => {
    $("message").textContent = "Saved locally.";
    setTimeout(() => $("message").textContent = "", 1800);
  });
});

load();
