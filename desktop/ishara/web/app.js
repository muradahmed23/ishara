/* iShara web UI. Reads state from Python (window.pywebview.api.state) ~20x/s
   and sends every action back to Python. No logic lives here. */

const ICONS = {
  home: '<path d="M3.5 10.5 12 3.5l8.5 7"/><path d="M5.5 9v11h13V9"/>',
  target: '<circle cx="12" cy="12" r="8.5"/><circle cx="12" cy="12" r="4.5"/><circle cx="12" cy="12" r="1" fill="currentColor"/>',
  sliders: '<path d="M4 7h9M17 7h3M4 12h3M11 12h9M4 17h11M19 17h1"/><circle cx="15" cy="7" r="2"/><circle cx="9" cy="12" r="2"/><circle cx="17" cy="17" r="2"/>',
  user: '<circle cx="12" cy="8" r="3.8"/><path d="M4.5 20.5c1.2-3.8 4-5.8 7.5-5.8s6.3 2 7.5 5.8"/>',
  info: '<circle cx="12" cy="12" r="8.5"/><path d="M12 11v5.5M12 7.6v.4"/>',
  mic: '<rect x="9" y="3.5" width="6" height="11" rx="3"/><path d="M5.5 11a6.5 6.5 0 0 0 13 0M12 17.5v3"/>',
  micOff: '<rect x="9" y="3.5" width="6" height="11" rx="3"/><path d="M5.5 11a6.5 6.5 0 0 0 13 0M12 17.5v3M4 4l16 16"/>',
  bluetooth: '<path d="M7 7.5 17 16.5 12 20.5V3.5l5 4L7 16.5"/>',
  cursor: '<path d="M5.5 3.5 18.5 11l-5.6 1.4-2.9 5.6z"/>',
  pause: '<path d="M9 5.5v13M15 5.5v13"/>',
  play: '<path d="M8 5.5 18.5 12 8 18.5z"/>',
  check: '<path d="M5 12.5 9.5 17 19 7"/>',
  chevron: '<path d="M9.5 6l6 6-6 6"/>',
  list: '<path d="M9 6.5h11M9 12h11M9 17.5h11M4.5 6.5h.01M4.5 12h.01M4.5 17.5h.01"/>',
};
const svg = (n) => `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round">${ICONS[n] || ""}</svg>`;
function paintIcons(root = document) { root.querySelectorAll("i[data-icon]").forEach((el) => { if (el.dataset.d !== el.dataset.icon) { el.innerHTML = svg(el.dataset.icon); el.dataset.d = el.dataset.icon; } }); }

const $ = (id) => document.getElementById(id);
const api = () => window.pywebview.api;
const set = (el, text) => { if (el.textContent !== text) el.textContent = text; };
const cls = (el, c) => { if (el.className !== c) el.className = c; };
const css = (n) => getComputedStyle(document.documentElement).getPropertyValue(n).trim();

let S = null;              // last state
let page = "home";
let setTab = "movement";
let theme = "light";

/* ---------------- navigation ---------------- */
const TITLES = { home: "Home", training: "Training", settings: "Settings", profiles: "Profiles", about: "About" };
function go(p, tab) {
  if (p === "calibrate") { api().calib_start(); return; }
  page = p;
  document.querySelectorAll("#nav a").forEach((a) => a.classList.toggle("on", a.dataset.page === p));
  document.querySelectorAll(".page").forEach((s) => s.classList.toggle("on", s.id === "page-" + p));
  set($("pageTitle"), TITLES[p]);
  $("scroll").scrollTop = 0;
  if (p === "settings") { if (tab) setTab = tab; renderSettings(); }
  if (p === "profiles") renderProfiles();
}

/* ---------------- canvas plot (shared by Home and Calibration) ---------------- */
function drawPlot(canvas, dot, dz, opts = {}) {
  const dpr = window.devicePixelRatio || 1, W = canvas.clientWidth, H = canvas.clientHeight;
  if (canvas.width !== W * dpr) { canvas.width = W * dpr; canvas.height = H * dpr; }
  const g = canvas.getContext("2d");
  g.setTransform(dpr, 0, 0, dpr, 0, 0);
  g.clearRect(0, 0, W, H);
  const SPAN = 1.3, c = W / 2, P = (v) => c + (v / SPAN) * (c - 8);
  // surface
  g.fillStyle = css("--fill"); roundRect(g, 0, 0, W, H, 18); g.fill();
  // grid
  g.strokeStyle = css("--sep"); g.lineWidth = 1;
  for (let k = -1; k <= 1; k += 0.5) {
    if (k === 0) continue;
    g.globalAlpha = 0.6; line(g, P(k), 10, P(k), H - 10); line(g, 10, P(k), W - 10, P(k)); g.globalAlpha = 1;
  }
  // comfortable range
  const lo = P(-1), hi = P(1);
  g.setLineDash([3, 4]); g.strokeStyle = css("--text-3"); roundRect(g, lo, lo, hi - lo, hi - lo, 10); g.stroke(); g.setLineDash([]);
  // edge highlight when the user reaches the limit
  if (dot && opts.active !== false) {
    g.strokeStyle = css("--orange"); g.lineWidth = 2.5; g.lineCap = "round";
    if (Math.abs(dot[0]) > 1) { const x = dot[0] > 0 ? hi : lo; line(g, x, lo + 8, x, hi - 8); }
    if (Math.abs(dot[1]) > 1) { const y = dot[1] > 0 ? hi : lo; line(g, lo + 8, y, hi - 8, y); }
    g.lineWidth = 1;
  }
  // dead zone + neutral
  const d = P(dz) - c;
  g.fillStyle = css("--surface"); g.beginPath(); g.arc(c, c, d, 0, 7); g.fill();
  g.strokeStyle = css("--sep"); g.stroke();
  g.strokeStyle = css("--text-3"); line(g, c - 5, c, c + 5, c); line(g, c, c - 5, c, c + 5);
  // targets (calibration check)
  (opts.targets || []).forEach(([tx, ty], i) => {
    const hit = (opts.hit || []).includes(i);
    g.beginPath(); g.arc(P(tx), P(ty), 11, 0, 7);
    g.fillStyle = hit ? css("--green") : css("--blue-soft"); g.fill();
    g.strokeStyle = hit ? css("--green") : css("--blue"); g.lineWidth = 1.5; g.stroke(); g.lineWidth = 1;
  });
  if (!dot) return;
  const x = P(Math.max(-SPAN, Math.min(SPAN, dot[0]))), y = P(Math.max(-SPAN, Math.min(SPAN, dot[1])));
  const beyond = Math.abs(dot[0]) > 1 || Math.abs(dot[1]) > 1;
  const col = opts.active === false ? css("--text-3") : (beyond || opts.unstable ? css("--orange") : css("--blue"));
  g.beginPath(); g.arc(x, y, 13, 0, 7); g.fillStyle = col; g.globalAlpha = 0.14; g.fill(); g.globalAlpha = 1;
  g.beginPath(); g.arc(x, y, 6.5, 0, 7); g.fillStyle = col; g.fill();
  g.strokeStyle = "#fff"; g.lineWidth = 2; g.stroke(); g.lineWidth = 1;
}
function line(g, x1, y1, x2, y2) { g.beginPath(); g.moveTo(x1, y1); g.lineTo(x2, y2); g.stroke(); }
function roundRect(g, x, y, w, h, r) { g.beginPath(); g.roundRect(x + .5, y + .5, w - 1, h - 1, r); }

/* ---------------- Home ---------------- */
function tile(icEl, valEl, text, color) { set(valEl, text); cls(icEl, "tile-ic" + (color ? " " + color : "")); }
function renderHome(s) {
  const alive = s.link.alive;
  const conn = alive ? ["Connected", "green"] : (["connecting", "connected"].includes(s.link.state) ? ["Connecting…", "orange"] : ["Not found", ""]);
  tile($("tileHeadband").firstElementChild, $("vHeadband"), conn[0], conn[1]);
  tile($("tileControl").firstElementChild, $("vControl"), s.paused ? "Paused" : (alive ? "Active" : "Waiting"), s.paused ? "orange" : (alive ? "green" : ""));
  const m = micState(s);
  tile($("tileMic").firstElementChild, $("vMic"), m.short, m.color);
  const pb = $("btnPause");
  const want = s.paused ? "play" : "pause";
  if (pb.dataset.st !== want) {
    pb.dataset.st = want;
    pb.innerHTML = `<i data-icon="${want}"></i><span>${s.paused ? "Resume control" : "Pause control"}</span>`;
    paintIcons(pb);
    set($("pauseHint"), s.paused ? "or say “resume”" : "or say “pause”");
  }
  // tracking
  const h = s.head;
  drawPlot($("plot"), h ? [h.nx, h.ny] : null, s.dz, { active: !s.paused && !!h, unstable: h && !h.ok });
  if (h) {
    const dz = s.dz, ax = Math.abs(h.nx), ay = Math.abs(h.ny);
    const dir = ax < dz && ay < dz ? "Centered" : (ax > 1 || ay > 1) ? "At your limit" : ax > ay ? (h.nx > 0 ? "Right" : "Left") : (h.ny > 0 ? "Down" : "Up");
    set($("rDir"), dir); cls($("rDir"), dir === "At your limit" ? "warn" : "");
    set($("rPitch"), (h.pitch > 0 ? "+" : "") + h.pitch.toFixed(1) + "°");
    set($("rRoll"), (h.roll > 0 ? "+" : "") + h.roll.toFixed(1) + "°");
    set($("rCursor"), s.paused ? "Paused" : (h.dx || h.dy ? `${h.dx > 0 ? "+" : ""}${h.dx}, ${h.dy > 0 ? "+" : ""}${h.dy} px` : "Still"));
  } else { ["rDir", "rPitch", "rRoll", "rCursor"].forEach((id) => set($(id), "—")); }
  const r = s.ranges;
  set($("rRange"), `←${r.left}°  →${r.right}°  ↑${r.up}°  ↓${r.down}°`);
  cls($("liveTag"), "tag" + (h && !s.paused ? "" : " hide"));
  // voice
  set($("voiceState"), m.long);
  const bars = $("meter").children, lvl = m.listening ? s.mic.level : 0;
  for (let i = 0; i < bars.length; i++) {
    const center = 1 - Math.abs(i - (bars.length - 1) / 2) / (bars.length / 2);
    const on = lvl > 0.02;
    bars[i].style.height = (on ? 6 + 16 * center * Math.min(1, lvl * 2.2) * (0.75 + 0.25 * Math.sin(Date.now() / 90 + i)) : 6) + "px";
    bars[i].style.background = on ? (s.dictation ? css("--blue") : css("--green")) : "";
  }
  segSet($("modeSeg"), s.dictation ? "dictation" : "command");
  const he = $("heard");
  if (s.partial) { set(he, `“${s.partial}…”`); cls(he, "heard partial"); }
  else if (s.heard) { set(he, (s.heard_kind === "dictation" ? "Typed: " : "") + s.heard); cls(he, "heard" + (s.heard_kind === "error" ? " bad" : "")); }
  else { set(he, "Not sure what to say? Say “help”"); cls(he, "heard dim"); }
  const la = s.last_action, el = $("lastAction");
  if (la) {
    const st = { ok: `✓  ${la.name} · ${ago(la.ago)}`, failed: `✕  ${la.name} failed · ${la.detail}`, pending: `${la.name} · announcing…` }[la.state];
    set(el, st); cls(el, { ok: "ok", failed: "bad", pending: "dim" }[la.state]);
  }
  const mb = $("btnMute"), wantM = s.mic.muted ? "mic" : "micOff";
  if (mb.dataset.st !== wantM) { mb.dataset.st = wantM; mb.innerHTML = `<i data-icon="${wantM}"></i><span>${s.mic.muted ? "Unmute microphone" : "Mute microphone"}</span>`; paintIcons(mb); }
}
function ago(s) { return s < 5 ? "just now" : s < 60 ? s + "s ago" : Math.floor(s / 60) + "m ago"; }
function micState(s) {
  const st = s.mic.state;
  if (st === "error") return { short: "Problem", long: "Microphone problem", color: "red" };
  if (st !== "listening") return { short: "Off", long: "Voice control is off", color: "" };
  if (s.mic.muted) return { short: "Muted", long: "Muted — say “start listening”", color: "red" };
  if (s.transcribing) return { short: "Writing…", long: "Writing your text…", color: "blue", listening: true };
  if (s.dictation) return { short: "Dictating", long: "Dictation — speak to type", color: "blue", listening: true };
  return { short: "Listening", long: "Listening for commands", color: "green", listening: true };
}

/* ---------------- chrome (chips, sidebar, capsule) ---------------- */
function renderChrome(s) {
  const alive = s.link.alive;
  const hb = $("chipHeadband");
  cls(hb.children[0], "led " + (alive ? "green" : ["connecting", "connected"].includes(s.link.state) ? "orange" : ""));
  set(hb.children[1], alive ? "Headband connected" : "Headband not connected");
  const m = micState(s), mc = $("chipMic");
  cls(mc.children[0], "led " + m.color);
  set(mc.children[1], "Microphone " + m.short.toLowerCase());
  set($("profileName"), s.profile); set($("avatar"), (s.profile[0] || "?").toUpperCase());
  set($("calState"), s.calibrated ? "Calibrated" : "Not calibrated");
  const cap = $("capsuleText");
  set(cap, s.status.text || "—");
  cls(cap, { ok: "ok", warn: "warn", error: "bad" }[s.status.kind] || "");
  set($("aboutVersion"), "Version " + s.version);
  const r = s.ranges;
  set($("trainCal"), s.calibrated ? `Your range: left ${r.left}° · right ${r.right}° · up ${r.up}° · down ${r.down}°` : "Not calibrated yet — takes about one minute");
  set($("trainPractice"), `${s.practice.passed} of ${s.practice.total} lessons passed`);
}

/* ---------------- calibration sheet ---------------- */
let calActionsSig = "";
function renderCalib(c) {
  const sheet = $("calSheet");
  if (!c) { sheet.classList.remove("on"); return; }
  if (!sheet.classList.contains("on")) sheet.classList.add("on");
  const ol = $("calSteps"), names = c.steps.concat(["Complete"]);
  if (ol.children.length !== names.length) ol.innerHTML = names.map((n) => `<li>${n}</li>`).join("");
  const cur = c.done ? names.length - 1 : c.step;
  [...ol.children].forEach((li, i) => cls(li, i < cur || (c.done && i === cur) ? "done" : i === cur ? "now" : ""));
  set($("calNo"), c.done ? "Done" : `Step ${c.step + 1} of ${c.steps.length}`);
  set($("calTitle"), c.title); set($("calHint"), c.hint);
  $("calBar").style.width = Math.round(c.progress * 100) + "%";
  let note = c.note;
  if (c.done && c.ranges) note = `Your range — left ${c.ranges.left}°, right ${c.ranges.right}°, up ${c.ranges.up}°, down ${c.ranges.down}°`;
  set($("calNote"), note); cls($("calNote"), "note" + (c.note_kind === "warn" ? " warn" : ""));
  drawPlot($("calPlot"), c.dot, c.dz, { targets: c.targets, hit: c.hit });
  const sig = c.done ? "done" : c.key === "check" ? "check" : "run";
  if (sig !== calActionsSig) {
    calActionsSig = sig;
    const a = $("calActions");
    if (sig === "done") a.innerHTML = `<button class="btn btn-primary" onclick="api().calib_finish()">Done</button>`;
    else if (sig === "check") a.innerHTML = `<button class="btn btn-gray" onclick="api().calib_cancel()">Cancel</button><button class="btn btn-gray" onclick="api().calib_restart()">Start over</button><button class="btn btn-primary" onclick="api().calib_skip()">Looks good</button>`;
    else a.innerHTML = `<button class="btn btn-gray" onclick="api().calib_cancel()">Cancel</button>`;
  }
}

/* ---------------- segmented control ---------------- */
function segSet(seg, v) { [...seg.children].forEach((b) => b.classList.toggle("on", b.dataset.v === v)); }
function segBind(seg, fn) { seg.addEventListener("click", (e) => { const b = e.target.closest("button"); if (b) { segSet(seg, b.dataset.v); fn(b.dataset.v); } }); }

/* ---------------- settings ---------------- */
const esc = (t) => String(t).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
const head = (t) => `<div class="group-head">${t}</div>`;
const gfoot = (t) => `<div class="group-foot">${t}</div>`;
const cell = (title, sub, ctrl) => `<div class="cell"><div class="cell-main"><div class="cell-title">${title}</div>${sub ? `<div class="cell-sub">${sub}</div>` : ""}</div>${ctrl}</div>`;
const sw = (kind, key, on) => `<label class="switch"><input type="checkbox" data-${kind}="${key}" ${on ? "checked" : ""}><span></span></label>`;
const rng = (kind, key, v, lo, hi, step, fmt) => `<div class="range"><input type="range" data-${kind}="${key}" data-fmt="${fmt}" min="${lo}" max="${hi}" step="${step}" value="${v}"><output>${fmtv(v, fmt)}</output></div>`;
const segH = (kind, key, cur, opts) => `<div class="seg" data-${kind}="${key}">${opts.map(([v, t]) => `<button data-v="${v}" class="${String(v) === String(cur) ? "on" : ""}">${t}</button>`).join("")}</div>`;
const btn = (cls, text, onclick) => `<button class="btn ${cls}" onclick="${onclick}">${text}</button>`;
function fmtv(v, f) { v = Number(v); return f === "pct" ? Math.round(v * 100) + "%" : f === "s" ? v.toFixed(1) + " s" : f === "ms" ? Math.round(v) + " ms" : f === "i" ? String(Math.round(v)) : f === "signed" ? (v > 0 ? "+" : "") + Math.round(v) : f === "vol" ? Math.round(v) + "%" : v.toFixed(f === "2" ? 2 : 1); }

async function renderSettings() {
  segSet($("setTabs"), setTab);
  const d = await api().settings();
  const s = d.settings, m = d.model;
  let h = "";
  if (setTab === "movement") {
    h += head("Speed") + `<div class="group">` + cell("Horizontal", "Tilting toward your shoulders", rng("model", "sx", m.sx, 1, 20, 0.5, "1")) + cell("Vertical", "Looking up and down", rng("model", "sy", m.sy, 1, 20, 0.5, "1")) + `</div>` + gfoot("How fast the cursor moves when your head reaches your comfortable limit.");
    h += head("Sensitivity") + `<div class="group">` + cell("Acceleration", "Higher: finer near the centre, faster near your limit", rng("model", "gam", m.gam, 1, 3, 0.1, "1")) + cell("Smoothing", "Lower is steadier, higher reacts faster", rng("model", "alpha", m.alpha, 0.05, 1, 0.01, "2")) + `</div>`;
    h += head("Dead zone") + `<div class="group">` + cell("Size", "Small, unintended movements inside this zone are ignored", rng("model", "dz", m.dz, 0.05, 0.5, 0.01, "pct")) + `</div>`;
    h += head("Direction") + `<div class="group">` + cell("Reverse left and right", "", sw("model", "ix", m.ix)) + cell("Reverse up and down", "", sw("model", "iy", m.iy)) + `</div>` + gfoot("Set automatically during calibration. Change only if a direction feels reversed.");
  } else if (setTab === "voice") {
    const mics = [`<option value="">Windows default</option>`].concat(d.mics.map((x) => `<option value="${x.id}" ${x.id === s.mic_device ? "selected" : ""}>${esc(x.name)}</option>`)).join("");
    h += head("Microphone") + `<div class="group">` + cell("Voice control", "Listen for voice commands", sw("set", "voice_enabled", s.voice_enabled)) + cell("Input device", "", `<select data-set="mic_device">${mics}</select>`) + cell("Repeat protection", "Ignore the same command again within this time", rng("set", "command_cooldown", s.command_cooldown, 0.3, 3, 0.1, "s")) + `</div>`;
    h += head("Dictation") + `<div class="group">` + cell("Accuracy", "Whisper writes punctuation and capitals. Best is slower.", segH("dict", "engine", d.dictation, [["vosk", "Basic"]].concat(d.whisper.map((w) => [w.id, w.name])))) +
      `<div class="cell"><div class="cell-main"><div class="cell-title">Your words</div><div class="cell-sub">Names and words to spell correctly, separated by commas</div></div><input class="input" id="vocab" style="max-width:320px" placeholder="e.g. Murad Ahmed, Bahria, Islamabad" value="${esc(d.vocabulary)}"></div>` +
      `</div>` + gfoot("Say “start typing”, speak, then “stop typing”.");
    h += head("Spoken feedback") + `<div class="group">` + cell("Speak actions", "The computer says what it is doing", sw("set", "speak", s.speak)) + cell("Speaking speed", "", rng("set", "speech_rate", s.speech_rate, -5, 5, 1, "signed")) + cell("Volume", "", rng("set", "speech_volume", s.speech_volume, 0, 100, 5, "vol")) + `</div>`;
  } else if (setTab === "commands") {
    d.commands.forEach((g, gi) => {
      h += head(g.group) + `<div class="group">` + g.items.map((it) => cell(it.text, "", `<div>${it.phrases.map((p) => `<span class="phrase" data-rename="${esc(p)}">“${esc(p)}”</span>`).join("")}</div>`)).join("") + `</div>` +
        (gi === 0 ? gfoot("Don’t remember a command? Say “help” and pick a number from the list next to the cursor.") : g.group === "Mouse" ? gfoot("Click a phrase to rename it.") : "");
    });
    h += head("While dictating") + `<div class="group">` + [["Punctuation", "comma · period · question mark"], ["New line", "new line"], ["Remove the last text", "delete that"], ["Back to commands", "stop typing"]].map(([a, b]) => cell(a, "", `<span class="cell-value">“${b}”</span>`)).join("") + `</div>`;
  } else if (setTab === "access") {
    h += head("Clicking") + `<div class="group">` + cell("Dwell click", "Click automatically when the cursor stays still", sw("set", "dwell_enabled", s.dwell_enabled)) + cell("Dwell time", "", rng("set", "dwell_ms", s.dwell_ms, 500, 3000, 100, "ms")) + `</div>`;
    h += head("Scrolling & screen") + `<div class="group">` + cell("Scroll speed", "Lines per scroll command", rng("set", "scroll_lines", s.scroll_lines, 1, 15, 1, "i")) + cell("Keep cursor on this screen", "Never move to another monitor", sw("set", "lock_to_screen", s.lock_to_screen)) + `</div>`;
    h += head("Cursor status tag") + `<div class="group">` + cell("Show status tag", "A small label next to the cursor", sw("set", "overlay_enabled", s.overlay_enabled)) + cell("Position", "", segH("set", "overlay_position", s.overlay_position, [["cursor", "Cursor"], ["top", "Top"], ["bottom", "Bottom"]])) + cell("Message time", "", rng("set", "overlay_seconds", s.overlay_seconds, 0.8, 4, 0.1, "s")) + `</div>`;
    h += head("Appearance & tools") + `<div class="group">` + cell("Appearance", "", segH("set", "theme", s.theme, [["light", "Light"], ["dark", "Dark"]])) + cell("On-screen keyboard", "Also: say “keyboard”", btn("btn-gray", "Open", "api().action('keyboard')")) + cell("Emergency stop", "Freezes the cursor immediately. Also: say “stop control”", btn("btn-danger", "Stop now", "api().action('stop')")) + `</div>`;
  } else if (setTab === "widget") {
    h += head("Floating bar") + `<div class="group">` + cell("Show floating bar", "Always on top: state, microphone, cursor action and pause", sw("set", "widget_enabled", s.widget_enabled)) + cell("Click-through", "Clicks pass through to the window below; its buttons can’t be pressed", sw("set", "widget_click_through", s.widget_click_through)) + cell("Position", "Back to the bottom centre of the screen", btn("btn-gray", "Reset", "api().widget_reset()")) + `</div>` + gfoot("Drag the bar anywhere. Double-click it to open iShara.");
  } else if (setTab === "calibration") {
    const r = S ? S.ranges : { left: 0, right: 0, up: 0, down: 0 };
    h += head("Your range") + `<div class="group">` + [["Left", r.left], ["Right", r.right], ["Up", r.up], ["Down", r.down]].map(([a, b]) => cell(a, "", `<span class="cell-value">${b}°</span>`)).join("") + `</div>` + gfoot("80% of your maximum reach, so the screen edges are comfortable to reach.");
    h += head("Actions") + `<div class="group">` + cell("Recalibrate", "Guided, about one minute", btn("btn-primary", "Start", "go('calibrate')")) + cell("Re-center only", "Look straight and keep still. Also: say “center”", btn("btn-gray", "Re-center", "api().action('recenter')")) + cell("Reset calibration", "Back to the default range", btn("btn-danger", "Reset", "api().reset_calibration().then(renderSettings)")) + `</div>`;
  }
  const body = $("setBody");
  body.innerHTML = h;
  bindControls(body);
}

function bindControls(root) {
  root.querySelectorAll("input[type=range]").forEach((r) => {
    r.addEventListener("input", () => (r.nextElementSibling.textContent = fmtv(r.value, r.dataset.fmt)));
    r.addEventListener("change", () => (r.dataset.model ? api().set_model(r.dataset.model, r.value) : api().set_setting(r.dataset.set, Number(r.value))));
  });
  root.querySelectorAll(".switch input").forEach((c) => c.addEventListener("change", () => (c.dataset.model ? api().set_model(c.dataset.model, c.checked ? 1 : 0) : api().set_setting(c.dataset.set, c.checked))));
  root.querySelectorAll("select[data-set]").forEach((s) => s.addEventListener("change", () => api().set_setting(s.dataset.set, s.value)));
  root.querySelectorAll(".seg[data-set]").forEach((g) => segBind(g, (v) => { api().set_setting(g.dataset.set, v); if (g.dataset.set === "theme") applyTheme(v); }));
  root.querySelectorAll(".seg[data-dict]").forEach((g) => segBind(g, (v) => api().set_dictation(v)));
  const vocab = root.querySelector("#vocab");
  if (vocab) {
    const save = () => { if (vocab.value !== vocab.dataset.saved) { vocab.dataset.saved = vocab.value; api().set_vocabulary(vocab.value); } };
    vocab.dataset.saved = vocab.value;
    vocab.addEventListener("change", save);
    vocab.addEventListener("keydown", (e) => { if (e.key === "Enter") { save(); vocab.blur(); } });
  }
  root.querySelectorAll("[data-rename]").forEach((p) => p.addEventListener("click", async () => {
    const old = p.dataset.rename, nw = await prompt2(`Rename “${old}”`, old);
    if (nw && nw !== old) { await api().rename_command(old, nw); renderSettings(); }
  }));
}

/* ---------------- profiles ---------------- */
async function renderProfiles() {
  const d = await api().settings();
  $("profileList").innerHTML = d.profiles.map((n) => {
    const on = n === d.profile;
    return `<div class="cell"><div class="avatar">${esc(n[0] || "?").toUpperCase()}</div><div class="cell-main"><div class="cell-title">${esc(n)}</div>${on ? `<div class="cell-sub">Active</div>` : ""}</div>` +
      (on ? `<i data-icon="check" class="check"></i>` : `<button class="btn btn-plain" data-use="${esc(n)}">Switch</button><button class="btn btn-danger" data-del="${esc(n)}">Delete</button>`) + `</div>`;
  }).join("");
  paintIcons($("profileList"));
  $("profileList").querySelectorAll("[data-use]").forEach((b) => b.onclick = async () => { await api().use_profile(b.dataset.use); renderProfiles(); });
  $("profileList").querySelectorAll("[data-del]").forEach((b) => b.onclick = async () => { await api().delete_profile(b.dataset.del); renderProfiles(); });
}

/* ---------------- prompt dialog ---------------- */
function prompt2(title, value) {
  return new Promise((done) => {
    const sh = $("promptSheet"), inp = $("promptInput");
    set($("promptTitle"), title); inp.value = value || ""; sh.classList.add("on"); setTimeout(() => inp.select(), 30);
    const close = (v) => { sh.classList.remove("on"); $("promptOk").onclick = $("promptCancel").onclick = inp.onkeydown = null; done(v); };
    $("promptOk").onclick = () => close(inp.value.trim());
    $("promptCancel").onclick = () => close(null);
    inp.onkeydown = (e) => { if (e.key === "Enter") close(inp.value.trim()); if (e.key === "Escape") close(null); };
  });
}

/* ---------------- theme ---------------- */
function applyTheme(t) { theme = t; document.documentElement.dataset.theme = t; }

/* ---------------- loop ---------------- */
async function poll() {
  try {
    const s = await api().state();
    S = s;
    renderChrome(s);
    if (page === "home") renderHome(s);
    renderCalib(s.calib);
  } catch (e) { console.error(e); }
  setTimeout(poll, 50);
}

async function init() {
  paintIcons();
  $("meter").innerHTML = "<i></i>".repeat(13);
  document.querySelectorAll("#nav a").forEach((a) => (a.onclick = () => go(a.dataset.page)));
  document.addEventListener("click", (e) => { const g = e.target.closest("[data-go]"); if (g) go(g.dataset.go, g.dataset.tab); });
  $("tileControl").onclick = $("btnPause").onclick = () => api().toggle_pause();
  $("tileMic").onclick = $("chipMic").onclick = $("btnMute").onclick = () => api().toggle_mic();
  $("tileHeadband").onclick = $("chipHeadband").onclick = () => go("training");
  $("openPractice").onclick = () => api().open_practice();
  segBind($("modeSeg"), (v) => api().action(v === "dictation" ? "dictation_on" : "dictation_off"));
  segBind($("setTabs"), (v) => { setTab = v; renderSettings(); });
  $("addProfile").onclick = async () => { const n = $("newProfile").value.trim(); if (n) { await api().new_profile(n); $("newProfile").value = ""; renderProfiles(); } };
  const d = await api().settings();
  applyTheme(d.settings.theme);
  go("home");
  poll();
  const s = await api().state();
  if (!s.calibrated) setTimeout(() => go("calibrate"), 600);
}
window.addEventListener("pywebviewready", init);
