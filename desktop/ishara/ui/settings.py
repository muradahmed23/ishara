"""Settings and Profiles pages.

Tabs: Movement, Voice, Voice commands, Accessibility, Floating widget, Calibration.
Each tab is a list of rows (title + short description on the left, one control
on the right) separated by hairlines - no nested cards.
"""
import tkinter as tk
from tkinter import simpledialog

from .. import profiles
from ..protocol import DEFAULT_MODEL
from ..voice import WHISPER_MODELS, list_microphones, whisper_available
from .theme import C, F, I
from .widgets import Choice, Pill, Slider, Toggle, label

SECTIONS = ["Movement", "Voice", "Voice commands", "Accessibility", "Floating widget", "Calibration"]

ACTION_TEXT = {
    "left_click": "Left click", "right_click": "Right click", "double_click": "Double click",
    "scroll_up": "Scroll up", "scroll_down": "Scroll down", "drag_start": "Start dragging",
    "drag_release": "Release drag", "click_lock": "Click lock on / off", "pause": "Pause head control",
    "resume": "Resume head control", "stop": "Emergency stop", "dictation_on": "Start dictation",
    "dictation_off": "Stop dictation", "keyboard": "Open on-screen keyboard", "recenter": "Re-center head",
    "find_cursor": "Move cursor to screen center", "mic_sleep": "Mute microphone",
    "mic_wake": "Unmute microphone",
}
ACTION_GROUP = [("Mouse", ["left_click", "double_click", "right_click", "scroll_up", "scroll_down",
                           "drag_start", "drag_release", "click_lock"]),
                ("Control", ["pause", "resume", "stop", "recenter", "find_cursor", "keyboard"]),
                ("Dictation", ["dictation_on", "dictation_off"]),
                ("Microphone", ["mic_sleep", "mic_wake"])]


class SettingsPage(tk.Frame):
    def __init__(self, parent, ctrl, on_change, sections=None, start=None):
        super().__init__(parent, bg=C["bg"])
        self.ctrl, self.on_change = ctrl, on_change
        self.sections = sections or SECTIONS
        self.tabs = {}
        if len(self.sections) > 1:
            bar = tk.Frame(self, bg=C["bg"])
            bar.pack(fill="x", padx=28, pady=(14, 0))
            for name in self.sections:
                cell = tk.Frame(bar, bg=C["bg"])
                cell.pack(side="left", padx=(0, 22))
                lb = tk.Label(cell, text=name, font=F["body"], bg=C["bg"], cursor="hand2", pady=8)
                lb.pack()
                ul = tk.Frame(cell, height=2, bg=C["bg"])
                ul.pack(fill="x")
                lb.bind("<ButtonRelease-1>", lambda e, n=name: self.show(n))
                self.tabs[name] = (lb, ul)
            tk.Frame(self, bg=C["line"], height=1).pack(fill="x", padx=28)
        # scrollable body
        holder = tk.Frame(self, bg=C["bg"])
        holder.pack(fill="both", expand=True, padx=28, pady=(18, 18))
        self.canvas = tk.Canvas(holder, bg=C["bg"], highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        self.inner = tk.Frame(self.canvas, bg=C["bg"])
        self.win_id = self.canvas.create_window(0, 0, window=self.inner, anchor="nw")
        self.inner.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfig(self.win_id, width=e.width))
        self.canvas.bind_all("<MouseWheel>", self._wheel)
        self.bind("<Destroy>", lambda e: self.canvas.unbind_all("<MouseWheel>") if e.widget is self else None)
        self.show(start if start in self.sections else self.sections[0])

    def _wheel(self, e):
        if self.canvas.winfo_exists() and self.inner.winfo_reqheight() > self.canvas.winfo_height():
            self.canvas.yview_scroll(int(-e.delta / 120) * 2, "units")

    # ---------------------------------------------------------------- building blocks
    def show(self, name):
        self.current = name
        for n, (lb, ul) in self.tabs.items():
            on = n == name
            lb.configure(fg=C["text"] if on else C["sub"], font=F["bodyb"] if on else F["body"])
            ul.configure(bg=C["text"] if on else C["bg"])
        for w in self.inner.winfo_children():
            w.destroy()
        self.canvas.yview_moveto(0)
        self.group = None
        getattr(self, "_" + name.lower().replace(" ", "_"))()

    def section(self, title, note=""):
        label(self.inner, title, "h3").pack(anchor="w", pady=(4 if not self.group else 22, 2))
        if note:
            label(self.inner, note, "small", "sub", wraplength=640, justify="left").pack(anchor="w", pady=(0, 6))
        o = tk.Frame(self.inner, bg=C["line"], padx=1, pady=1)
        o.pack(fill="x", pady=(6, 0))
        self.group = tk.Frame(o, bg=C["card"])
        self.group.pack(fill="x")
        self._rows = 0

    def row(self, title, sub=""):
        if self._rows:
            tk.Frame(self.group, bg=C["line2"], height=1).pack(fill="x")
        self._rows += 1
        r = tk.Frame(self.group, bg=C["card"], padx=18, pady=11)
        r.pack(fill="x")
        t = tk.Frame(r, bg=C["card"])
        t.pack(side="left", fill="x", expand=True)
        label(t, title, "body", bg=C["card"]).pack(anchor="w")
        if sub:
            label(t, sub, "small", "sub", bg=C["card"], wraplength=380, justify="left").pack(anchor="w", pady=(1, 0))
        return r

    def mslider(self, title, sub, key, lo, hi, fmt="{:.1f}", step=None):
        r = self.row(title, sub)
        Slider(r, lo, hi, self.ctrl.model[key], lambda v: self.ctrl.set_model({key: v}),
               step=step, fmt=fmt).pack(side="right")

    def stoggle(self, title, sub, key, after=None):
        r = self.row(title, sub)

        def flip(v):
            self.ctrl.settings[key] = v
            self.ctrl.save_profile()
            if after:
                after(v)
        Toggle(r, self.ctrl.settings[key], flip).pack(side="right")

    def sslider(self, title, sub, key, lo, hi, fmt="{:.0f}", step=1, after=None):
        r = self.row(title, sub)

        def set_(v):
            self.ctrl.settings[key] = v
            self.ctrl.save_profile()
            if after:
                after(v)
        Slider(r, lo, hi, self.ctrl.settings[key], set_, step=step, fmt=fmt).pack(side="right")

    def dropdown(self, row, values, current, command):
        var = tk.StringVar(value=current)
        om = tk.OptionMenu(row, var, *values, command=command)
        om.configure(font=F["small"], bg=C["card"], fg=C["text"], relief="flat", highlightthickness=1,
                     highlightbackground=C["line"], activebackground=C["hover"], width=28, anchor="w",
                     indicatoron=True, bd=0, padx=8, pady=3)
        om["menu"].configure(font=F["small"], bg=C["card"], fg=C["text"], activebackground=C["accent_bg"],
                             activeforeground=C["text"], bd=0)
        om.pack(side="right")

    # ---------------------------------------------------------------- tabs
    def _movement(self):
        self.section("Speed", "How fast the cursor moves when your head reaches your comfortable limit.")
        self.mslider("Horizontal", "Tilting toward your shoulders", "sx", 1, 20)
        self.mslider("Vertical", "Looking up and down", "sy", 1, 20)
        self.section("Sensitivity")
        self.mslider("Acceleration", "Higher: finer control near the centre, faster near your limit",
                     "gam", 1.0, 3.0, "{:.1f}", 0.1)
        self.mslider("Smoothing", "Lower is steadier, higher reacts faster", "alpha", 0.05, 1.0, "{:.2f}", 0.01)
        self.section("Dead zone", "Small, unintended head movements inside this zone are ignored.")
        self.mslider("Size", "Part of your range where the cursor stays still", "dz", 0.05, 0.5, "{:.0%}", 0.01)
        self.section("Direction", "Set automatically during calibration. Change only if a direction feels reversed.")
        r = self.row("Reverse left and right")
        Toggle(r, self.ctrl.model["ix"], lambda v: self.ctrl.set_model({"ix": int(v)})).pack(side="right")
        r = self.row("Reverse up and down")
        Toggle(r, self.ctrl.model["iy"], lambda v: self.ctrl.set_model({"iy": int(v)})).pack(side="right")

    def _voice(self):
        s = self.ctrl.settings
        self.section("Microphone")
        self.stoggle("Voice control", "Listen for voice commands", "voice_enabled",
                     after=lambda v: self.ctrl.restart_voice())
        r = self.row("Input device")
        mics = [(None, "Windows default")] + list_microphones()
        cur = next((n for i, n in mics if i == s["mic_device"]), "Windows default")

        def pick(name):
            s["mic_device"] = next(i for i, n in mics if n == name)
            self.ctrl.save_profile()
            self.ctrl.restart_voice()
        self.dropdown(r, [n for _, n in mics], cur, pick)
        self.sslider("Repeat protection", "Ignore the same command again within this time",
                     "command_cooldown", 0.3, 3.0, "{:.1f} s", 0.1)

        self.section("Dictation", "Say “start typing”, speak, then “stop typing”.")
        r = self.row("Accuracy", "Whisper writes punctuation and capitals. Best is slower.")

        def engine(v):
            if v == "vosk":
                s["dictation_engine"] = "vosk"
            else:
                s["dictation_engine"], s["whisper_model"] = "whisper", v
            self.ctrl.save_profile()
            self.ctrl.restart_voice()
        opts = [(m, txt.split(" (")[0]) for m, txt in WHISPER_MODELS.items() if whisper_available(m)]
        cur = "vosk" if s["dictation_engine"] == "vosk" else s["whisper_model"]
        Choice(r, [("vosk", "Basic")] + opts, cur, engine).pack(side="right")

        self.section("Spoken feedback", "The computer says what it is doing through the speaker.")
        self.stoggle("Speak actions", "", "speak", after=lambda v: self.ctrl.apply_speech_settings())

        def speech_set(key):
            def f(v):
                s[key] = int(v)
                self.ctrl.save_profile()
                self.ctrl.apply_speech_settings()
                self.ctrl.say("This is how I sound")
            return f
        r = self.row("Speaking speed")
        Slider(r, -5, 5, s["speech_rate"], speech_set("speech_rate"), step=1, fmt="{:+.0f}").pack(side="right")
        r = self.row("Volume")
        Slider(r, 0, 100, s["speech_volume"], speech_set("speech_volume"), step=5, fmt="{:.0f}%").pack(side="right")

    def _rename(self, phrase):
        new = simpledialog.askstring("Rename command", f"New phrase for “{phrase}”:", parent=self)
        if new and new.strip():
            cmds = self.ctrl.settings["commands"]
            cmds[new.strip().lower()] = cmds.pop(phrase)
            self.ctrl.save_profile()
            self.ctrl.voice.set_commands(cmds)
            self.show("Voice commands")

    def _accessibility(self):
        self.section("Clicking")
        self.stoggle("Dwell click", "Click automatically when the cursor stays still", "dwell_enabled")
        self.sslider("Dwell time", "How long to stay still before clicking", "dwell_ms", 500, 3000, "{:.0f} ms", 100)
        self.section("Scrolling & screen")
        self.sslider("Scroll speed", "Lines per scroll command", "scroll_lines", 1, 15)
        self.stoggle("Keep cursor on this screen", "Never let the cursor move to another monitor", "lock_to_screen")
        self.section("Cursor status tag", "A small label next to the cursor showing what is happening.")
        self.stoggle("Show status tag", "", "overlay_enabled")
        r = self.row("Position")

        def pos(v):
            self.ctrl.settings["overlay_position"] = v
            self.ctrl.save_profile()
        Choice(r, [("cursor", "Next to cursor"), ("top", "Top"), ("bottom", "Bottom")],
               self.ctrl.settings["overlay_position"], pos).pack(side="right")
        self.sslider("Message time", "How long short messages stay", "overlay_seconds", 0.8, 4.0, "{:.1f} s", 0.1)
        self.section("Appearance & tools")
        r = self.row("Theme")

        def theme(v):
            self.ctrl.settings["theme"] = v
            self.ctrl.save_profile()
            self.on_change("theme")
        Choice(r, [("light", "Light"), ("dark", "Dark")], self.ctrl.settings["theme"], theme).pack(side="right")
        r = self.row("On-screen keyboard", "Also: say “keyboard”")
        Pill(r, "Open", lambda: self.ctrl.request("keyboard"), kind="soft").pack(side="right")
        r = self.row("Emergency stop", "Freezes the cursor immediately. Also: say “stop control”")
        Pill(r, "Stop now", lambda: self.ctrl.request("stop"), kind="danger").pack(side="right")

    def _floating_widget(self):
        self.section("Floating bar", "A small always-on-top bar showing state, microphone and cursor action, "
                                     "with a pause button. Drag it anywhere; double-click opens iShara.")
        self.stoggle("Show floating bar", "", "widget_enabled", after=lambda v: self.on_change("widget"))
        self.stoggle("Click-through", "Clicks pass through the bar to the window below. "
                                      "Its buttons can't be pressed while this is on.",
                     "widget_click_through", after=lambda v: self.on_change("widget"))
        r = self.row("Position", "Move it back to the bottom centre of the screen")
        Pill(r, "Reset position", lambda: self.on_change("widget_reset"), kind="soft").pack(side="right")

    def _calibration(self):
        m = self.ctrl.model
        left, right = (m["rL"], m["rR"]) if not m["ix"] else (m["rR"], m["rL"])
        self.section("Your range", "Measured during calibration. 80% of your maximum reach is used, "
                                   "so the screen edges are comfortable to reach.")
        for name, v in (("Left", left), ("Right", right), ("Up", m["rU"]), ("Down", m["rD"])):
            r = self.row(name)
            label(r, f"{v:.0f}°", "bodyb", bg=C["card"]).pack(side="right")
        self.section("Actions")
        r = self.row("Recalibrate", "Guided, about one minute")
        Pill(r, "Start", lambda: self.on_change("calibrate"), kind="primary").pack(side="right")
        r = self.row("Re-center only", "Look straight and keep still. Also: say “center”")
        Pill(r, "Re-center", lambda: self.ctrl.request("recenter"), kind="soft").pack(side="right")
        r = self.row("Reset calibration", "Go back to the default range")
        Pill(r, "Reset", self._reset_cal, kind="danger").pack(side="right")

    def _reset_cal(self):
        self.ctrl.set_model(dict(DEFAULT_MODEL))
        self.ctrl.link.send("CAL")
        self.ctrl.settings["calibrated"] = False
        self.ctrl.save_profile()
        self.show("Calibration")

    def _profiles(self):
        cur = self.ctrl.profile["name"]
        self.section("People", "Each person has their own calibration and settings.")
        for name in profiles.list_profiles():
            r = self.row(name, "Active" if name == cur else "")
            if name != cur:
                Pill(r, "Delete", lambda n=name: (profiles.delete(n), self.show("Profiles")),
                     kind="ghost").pack(side="right", padx=(6, 0))
                Pill(r, "Switch", lambda n=name: self._use(n), kind="soft").pack(side="right")
            else:
                label(r, I["check"], "icon_s", "green", bg=C["card"]).pack(side="right")
        b = tk.Frame(self.inner, bg=C["bg"])
        b.pack(anchor="w", pady=(16, 0))
        Pill(b, "New profile", self._new, kind="primary").pack(side="left")
        Pill(b, "Recalibrate this person", lambda: self.on_change("calibrate"), kind="soft").pack(side="left", padx=8)

    def _use(self, name):
        self.ctrl.load_profile(name)
        self.show("Profiles")
        self.on_change()

    def _new(self):
        name = simpledialog.askstring("New profile", "Name of the person:", parent=self)
        if name and name.strip():
            p = profiles.load(name.strip())
            profiles.save(p)
            self._use(p["name"])


def _voice_commands_tab(self):
    """Voice commands reference (moved here from the home screen)."""
    cmds = self.ctrl.settings["commands"]
    for title, actions in ACTION_GROUP:
        self.section(title, "Click a phrase to rename it." if title == "Mouse" else "")
        for a in actions:
            phrases = [p for p, x in cmds.items() if x == a]
            r = self.row(ACTION_TEXT[a])
            box = tk.Frame(r, bg=C["card"])
            box.pack(side="right")
            for p in phrases:
                lb = tk.Label(box, text=f"“{p}”", font=F["bodyb"], fg=C["text"], bg=C["hover"],
                              padx=8, pady=2, cursor="hand2")
                lb.pack(side="left", padx=(6, 0))
                lb.bind("<ButtonRelease-1>", lambda e, ph=p: self._rename(ph))
    self.section("While dictating")
    for say, what in (("comma · period · question mark", "Punctuation"),
                      ("new line", "Start a new line"), ("delete that", "Remove the last text"),
                      ("stop typing", "Back to commands")):
        r = self.row(what)
        label(r, f"“{say}”", "bodyb", bg=C["card"]).pack(side="right")


SettingsPage._voice_commands = _voice_commands_tab
