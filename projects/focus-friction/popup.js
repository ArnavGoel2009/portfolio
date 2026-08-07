const $ = id => document.getElementById(id);

function formatTime(seconds) {
  if (!seconds) return "—";
  const minutes = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return `${minutes}:${String(secs).padStart(2,"0")}`;
}

function render(status) {
  $("minutes").value = status.config.focusMinutes;
  $("mode").textContent = status.config.frictionMode;
  $("dot").classList.toggle("on", status.active);
  $("status").textContent = status.active ? "Focus protection active" : "Protection idle";
  $("timer").textContent = formatTime(status.remaining);
}

function refresh() {
  chrome.runtime.sendMessage({type:"GET_STATUS"}, response => {
    if (response?.ok) render(response);
  });
}

$("start").addEventListener("click", () => {
  const minutes = Math.max(1, Math.min(240, Number($("minutes").value) || 25));
  chrome.storage.local.get({config: FocusCore.DEFAULT_CONFIG}, data => {
    const config = FocusCore.sanitizeConfig({...data.config, focusMinutes: minutes});
    chrome.storage.local.set({config}, () => {
      chrome.runtime.sendMessage({type:"START_SESSION", minutes}, refresh);
    });
  });
});

$("stop").addEventListener("click", () => {
  chrome.runtime.sendMessage({type:"STOP_SESSION"}, refresh);
});

refresh();
setInterval(refresh, 1000);
