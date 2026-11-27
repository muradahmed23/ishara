/* iShara: Help topics, device panel, updates and the first-run welcome guide.
   Loaded after app.js (uses $, api, set, cls, esc, paintIcons, go, S). */

/* ---------------- Help topics (simple language, read aloud) ---------------- */
const HELP = [
  ["Installing iShara", [
    "Download iShara from the website and open the file.",
    "Press <b>Install</b>. Everything is included: the app and the speech models. No internet is needed afterwards.",
    "iShara starts by itself when installation finishes, and the welcome guide opens."]],
  ["Wearing the headband", [
    "Put the band around your head so the electronics sit on your <b>forehead</b>.",
    "The small blue sensor board should face outwards and sit flat against the foam.",
    "Make it snug. If the band slides, the cursor drifts.",
    "Keep the wires tucked in. If the sensor wire comes loose, the cursor stops."]],
  ["Connecting the headband (Bluetooth)", [
    "Switch the headband on. Charge it first if needed (USB-C on the charger board).",
    "Open Windows <b>Settings → Bluetooth & devices → Add device → Bluetooth</b>.",
    "Choose <b>Ishara Mouse</b>. You only do this once.",
    "The headband <b>beeps once</b> when it connects. The Headband status at the top turns green."]],
  ["How head movement works", [
    "<b>Tilt your head toward a shoulder</b> to move left or right.",
    "<b>Lift or lower your chin</b> to move up or down.",
    "A small tilt moves slowly; a bigger tilt moves faster.",
    "Hold your head straight to keep the cursor still."]],
  ["Calibration", [
    "Calibration learns how the headband sits on your head and how far you can comfortably move.",
    "Go to <b>Training → Calibration</b>, or say nothing and follow the voice.",
    "Look straight, then tilt left, right, up and down. Hold each one until you hear <b>Got it</b>.",
    "Calibrate again if you move the headband or another person uses it."]],
  ["Cursor speed", [
    "Open <b>Settings → Movement → Speed</b>.",
    "Move <b>Horizontal</b> or <b>Vertical</b> to the right for a faster cursor, to the left for a slower one."]],
  ["Smoothing and the dead zone", [
    "<b>Dead zone</b>: small movements inside it are ignored, so a shaky or tired head doesn't move the cursor. Make it bigger if the cursor drifts.",
    "<b>Smoothing</b>: lower is steadier, higher reacts faster.",
    "<b>Acceleration</b>: higher gives finer control near the centre."]],
  ["Left click and right click", [
    "Point at something with your head, then say <b>“click”</b>.",
    "Say <b>“right click”</b> for the menu.",
    "Or turn on <b>Dwell click</b> (Settings → Accessibility): the cursor clicks when you keep it still."]],
  ["Double click and middle click", [
    "Say <b>“double click”</b> to open files.",
    "Say <b>“middle click”</b> to open a link in a new tab.",
    "Say <b>“go back”</b> or <b>“go forward”</b> for the mouse back and forward buttons."]],
  ["Scrolling", [
    "Say <b>“scroll down”</b> or <b>“scroll up”</b>.",
    "Change how far one scroll goes in Settings → Accessibility → Scroll speed."]],
  ["Dragging", [
    "Point at the item and say <b>“start drag”</b>.",
    "Move your head to where it should go.",
    "Say <b>“release”</b> to drop it.",
    "Or say <b>“click lock”</b>: then “click” holds, the next “click” releases."]],
  ["Typing with your voice", [
    "Say <b>“start typing”</b>, then speak your sentence.",
    "Say <b>“comma”</b>, <b>“period”</b>, <b>“question mark”</b> or <b>“new line”</b>.",
    "Say <b>“delete that”</b> to remove the last text.",
    "Say <b>“stop typing”</b> to go back to commands.",
    "You can also say “keyboard” to open the On-Screen Keyboard and click its keys."]],
  ["Pause and resume", [
    "Say <b>“pause”</b> to freeze the cursor, for example when you talk to someone.",
    "Say <b>“resume”</b> to continue.",
    "Say <b>“hand mouse”</b> to use a normal mouse; voice clicks keep working. Say <b>“head mouse”</b> to come back."]],
  ["Emergency stop", [
    "Say <b>“stop control”</b> at any time. The cursor freezes immediately.",
    "There is also a <b>Stop now</b> button in Settings → Accessibility.",
    "Say <b>“resume”</b> when you are ready."]],
  ["Microphone problems", [
    "Check the Microphone status at the top. If it says Muted, say <b>“start listening”</b>.",
    "Choose the right microphone in Settings → Voice → Input device.",
    "In Windows Settings → Privacy → Microphone, allow desktop apps to use the microphone.",
    "Speak normally, about an arm’s length from the microphone. The level bars on Home move when it hears you."]],
  ["Bluetooth disconnections", [
    "Keep the headband within a few metres of the computer.",
    "Check that it is charged and switched on.",
    "If the Headband status stays orange or grey, remove <b>Ishara Mouse</b> in Windows Bluetooth settings and add it again.",
    "If the cursor stops but Bluetooth is connected, the sensor wire may be loose. See <b>Your headband</b> above."]],
  ["Profiles for different people", [
    "Each person has their own calibration and settings.",
    "Open <b>Profiles</b>, type a name and press Add. Press Switch to change person.",
    "After switching, run Calibration for the new person."]],
  ["Updating iShara", [
    "Open <b>About → Check for updates</b>.",
    "If a new version is available, press Download, then Install.",
    "Your profiles, calibration and settings are always kept."]],
];
const strip = (h) => h.replace(/<[^>]+>/g, "").replace(/→/g, ", then");

let helpDrawn = false;
function renderHelpTopics() {
  if (helpDrawn) return;
  helpDrawn = true;
  $("helpTopics").innerHTML = `<div class="group-head">Guides</div><div class="group">` + HELP.map(([t, steps], i) =>
    `<details class="topic"><summary><span class="num">${i + 1}</span><span class="t">${t}</span><i data-icon="chevron" class="chev"></i></summary>
     <div class="topic-body"><ol>${steps.map((s) => `<li>${s}</li>`).join("")}</ol>
     <button class="btn btn-plain" data-say="${i}"><i data-icon="mic"></i><span>Read aloud</span></button></div></details>`).join("") + `</div>`;
  paintIcons($("helpTopics"));
  $("helpTopics").querySelectorAll("[data-say]").forEach((b) => b.onclick = () => {
    const [t, steps] = HELP[Number(b.dataset.say)];
    api().speak(t + ". " + steps.map(strip).join(" "));
  });
  $("openWelcome").onclick = () => welcomeOpen(0);
}

/* ---------------- device panel (Help page) ---------------- */
function renderDevice(s) {
  const d = s.device, m = s.models;
  const rows = [
    ["ESP32 headband", d.alive ? "Connected" : ["connecting", "connected"].includes(d.link) ? "Connecting…" : "Not connected", d.alive ? "green" : ["connecting", "connected"].includes(d.link) ? "orange" : ""],
    ["Connection", d.connection + (d.alive ? " · works as a Bluetooth mouse" : ""), ""],
    ["MPU6050 head sensor", d.sensor_ok === null ? "Unknown until connected" : d.sensor_ok ? "Working" : "Not responding: check the sensor wires", d.sensor_ok === null ? "" : d.sensor_ok ? "green" : "red"],
    ["Battery", "Not measured on this headband", ""],
    ["Speech models", { ok: "Installed and verified", checking: "Checking…", damaged: "Damaged: please reinstall iShara", error: "Could not check" }[m.state] || m.state, { ok: "green", checking: "orange", damaged: "red", error: "orange" }[m.state] || ""],
  ];
  const html = rows.map(([a, b, c]) => `<div class="cell"><span class="led ${c}"></span><div class="cell-main"><div class="cell-title">${a}</div></div><span class="cell-value">${esc(b)}</span></div>`).join("");
  const g = $("deviceGroup");
  if (g.dataset.h !== html) { g.dataset.h = html; g.innerHTML = html; }
}

/* ---------------- updates (About page) ---------------- */
const mb = (b) => b ? Math.round(b / 1048576) + " MB" : "";
function renderUpdate(u) {
  const txt = {
    idle: "Check whether a newer version is available.",
    checking: "Checking…",
    current: `You have the latest version (${u.current}).`,
    available: `Version ${u.latest} is available${u.size ? " · " + mb(u.size) : ""}.`,
    downloading: `Downloading version ${u.latest}… ${Math.round((u.progress || 0) * 100)}%`,
    verifying: "Checking the download is complete and safe…",
    ready: `Version ${u.latest} is ready. iShara will close, update and start again. Your profiles are kept.`,
    error: u.error || "Something went wrong.",
  }[u.state] || "";
  set($("updText"), txt); cls($("updText"), "cell-sub" + (u.state === "error" ? " bad" : ""));
  $("updBarWrap").classList.toggle("hide", u.state !== "downloading");
  $("updBar").style.width = Math.round((u.progress || 0) * 100) + "%";
  const btn = {
    idle: ["btn-gray", "Check for updates", "update_check"], current: ["btn-gray", "Check again", "update_check"],
    error: ["btn-gray", "Try again", u.latest && u.url ? "update_download" : "update_check"],
    available: ["btn-primary", "Download", "update_download"], ready: ["btn-primary", "Install update", "update_install"],
  }[u.state];
  const h = btn ? `<button class="btn ${btn[0]}" onclick="api().${btn[2]}()">${btn[1]}</button>` : "";
  const a = $("updActions");
  if (a.dataset.h !== h) { a.dataset.h = h; a.innerHTML = h; }
}

/* ---------------- welcome guide (first run) ---------------- */
const WELCOME = [
  { name: "Welcome", title: "Welcome to iShara",
    body: "iShara lets you use your computer without your hands. <b>Tilt your head</b> to move the cursor and <b>speak</b> to click, scroll and type.<br><br>This guide takes about five minutes. Press <b>Next</b> when you are ready.",
    say: "Welcome to iShara. iShara lets you use your computer without your hands. Tilt your head to move the cursor, and speak to click, scroll and type. Press next when you are ready." },
  { name: "Microphone", title: "Check your microphone",
    body: "Say anything, for example <b>“hello”</b>. When iShara hears you, the status below turns green.<ul><li>If it says Muted, say “start listening”.</li><li>Wrong microphone? Change it later in Settings → Voice.</li></ul>",
    say: "Let's check your microphone. Say hello.",
    status: (s) => { const heard = !!(s.heard || s.partial) || (s.mic.level || 0) > 0.05;
      return s.mic.state === "error" ? ["red", "Microphone problem. Check Windows microphone privacy settings."]
        : s.mic.muted ? ["orange", "Muted. Say “start listening”."]
        : heard ? ["green", "I can hear you."] : ["orange", "Listening… say “hello”."]; } },
  { name: "Wear the headband", title: "Put on the headband",
    body: "<ol><li>Place the band so the electronics sit on your <b>forehead</b>.</li><li>The blue sensor board faces outwards, flat against the foam.</li><li>Make it snug so it can't slide.</li><li>Switch it on. Charge it first if needed (USB-C on the charger board).</li></ol>",
    say: "Put the headband on, with the electronics on your forehead. Make it snug so it cannot slide, and switch it on." },
  { name: "Bluetooth", title: "Connect the headband",
    body: "<ol><li>Open Windows Bluetooth settings (button below).</li><li>Choose <b>Add device → Bluetooth → Ishara Mouse</b>.</li><li>The headband <b>beeps once</b> when it connects.</li></ol>Already paired? Just switch the headband on.",
    say: "Now connect the headband. In Windows Bluetooth settings, add the device called Ishara Mouse. The headband beeps once when it connects.",
    extra: `<button class="btn btn-gray" onclick="api().open_bluetooth_settings()">Open Bluetooth settings</button>`,
    status: (s) => s.device.alive
      ? (s.device.sensor_ok === false ? ["red", "Connected, but the head sensor is not responding. Check its wires."] : ["green", "Headband connected. Sensor working."])
      : ["orange", "Waiting for the headband…"] },
  { name: "Training", title: "Practise first", skippable: true,
    body: "Seven short lessons teach you to move the cursor with your head and use your voice. Each lesson unlocks the next.<br><br>Press <b>Start training</b>, or <b>Skip for now</b> and practise later from the Training page.",
    say: "First, let's practise. Press start training, or skip for now and practise later.",
    extra: `<button class="btn btn-primary" onclick="api().open_practice()">Start training</button>`,
    status: (s) => s.practice.passed > 0 ? ["green", `${s.practice.passed} of ${s.practice.total} lessons passed`] : ["orange", "Not started yet."] },
  { name: "Calibration", title: "Personal calibration", skippable: true,
    body: "iShara learns how the headband sits on <b>your</b> head and how far you can comfortably move.<br><br>Press <b>Start calibration</b> and follow the voice: look straight, then tilt left, right, up and down. Hold each until you hear “Got it”. You can also <b>skip for now</b> and calibrate later from the Training page.",
    say: "Now let's calibrate, so the cursor fits your head. Press start calibration, or skip for now.",
    extra: `<button class="btn btn-primary" onclick="go('calibrate')">Start calibration</button>`,
    status: (s) => s.calibrated ? ["green", "Calibrated. Your cursor is ready."] : ["orange", s.device.alive ? "Not calibrated yet." : "Connect the headband first."] },
  { name: "Ready", title: "You're ready",
    body: "<ul><li>Say <b>“help”</b> any time to see every command.</li><li>Say <b>“pause”</b> to freeze the cursor, <b>“stop control”</b> in an emergency.</li><li>Guides are in the <b>Help</b> page.</li></ul>",
    say: "You're ready. Say help any time to see every command. Say pause to freeze the cursor." },
];
let wStep = -1, wSig = "";
function welcomeOpen(i) {
  wStep = i; wSig = "";
  $("welcomeSheet").classList.add("on");
  api().speak(WELCOME[i].say);
}
function welcomeGo(d) {
  const n = wStep + d;
  if (n >= WELCOME.length) { $("welcomeSheet").classList.remove("on"); wStep = -1; api().welcome_done(); return; }
  welcomeOpen(Math.max(0, n));
}
function renderWelcome(s) {
  if (wStep < 0 || s.calib) return;           // calibration sheet is on top while it runs
  const w = WELCOME[wStep];
  const ol = $("wSteps");
  if (ol.children.length !== WELCOME.length) ol.innerHTML = WELCOME.map((x) => `<li>${x.name}</li>`).join("");
  [...ol.children].forEach((li, i) => cls(li, i < wStep ? "done" : i === wStep ? "now" : ""));
  set($("wNo"), `Step ${wStep + 1} of ${WELCOME.length}`);
  set($("wTitle"), w.title);
  if ($("wBody").dataset.i !== String(wStep)) { $("wBody").dataset.i = wStep; $("wBody").innerHTML = w.body; }
  const st = w.status ? w.status(s) : null;
  const sh = st ? `<span class="led ${st[0]}"></span><span>${esc(st[1])}</span>` : "";
  if ($("wStatus").dataset.h !== sh) { $("wStatus").dataset.h = sh; $("wStatus").innerHTML = sh; }
  const last = wStep === WELCOME.length - 1;
  const doneStep = !!(st && st[0] === "green");
  const sig = wStep + ":" + doneStep;
  if (sig !== wSig) {
    wSig = sig;
    $("wActions").innerHTML = (wStep > 0 ? `<button class="btn btn-gray" onclick="welcomeGo(-1)">Back</button>` : `<button class="btn btn-gray" onclick="welcomeGo(${WELCOME.length})">Skip guide</button>`) +
      `<button class="btn btn-plain" onclick="api().speak(WELCOME[wStep].say)">Repeat</button>` + (w.extra || "") +
      (w.skippable && !doneStep ? `<button class="btn btn-gray" onclick="welcomeGo(1)">Skip for now</button>` : `<button class="btn btn-primary" onclick="welcomeGo(1)">${last ? "Start using iShara" : "Next"}</button>`);
  }
}

/* ---------------- hook into the main loop ---------------- */
function renderExtras(s) {
  if (page === "help") renderDevice(s);
  if (page === "about") renderUpdate(s.update);
  renderWelcome(s);
}
