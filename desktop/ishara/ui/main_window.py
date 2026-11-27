"""iShara main window.

Layout
  sidebar | top bar (page title + headband / microphone status + settings)
          | page content
          | status bar (live cursor status)

Home answers three questions at a glance - headband connected? head control
active? microphone listening? - then shows the live head tracking and the voice
activity. Everything reads the controller's single state every tick, so this
window, the floating bar, the cursor tag and the real cursor always agree.
"""
import time
import tkinter as tk

from .. import __version__
from .. import model as pm
from . import theme
from .calibration import CalibrationPage
from .overlay import FloatingWidget, HelpMenu, StatusOverlay, draw_logo
from .practice import LESSONS, PracticeWindow
from .settings import SettingsPage
from .theme import C, F, I
from .widgets import Choice, Pill, TrackingView, label, rrect

TICK_MS = 30
NAV = [("home", "Home", "home"), ("training", "Training", "training"),
       ("settings", "Settings", "settings"), ("profiles", "Profiles", "profile"),
       ("about", "About", "info")]
TITLES = {"home": "Home", "training": "Training", "calibrate": "Calibration", "settings": "Settings",
          "profiles": "Profiles", "about": "About"}


def ago(t):
    s = int(time.time() - t)
    return "just now" if s < 5 else (f"{s}s ago" if s < 60 else f"{s // 60}m ago")


class MainWindow(tk.Tk):
    def __init__(self, ctrl):
        try:
            import ctypes
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            pass
        theme.load_private_fonts()
        super().__init__()
        self.ctrl = ctrl
        theme.init_fonts()
        theme.apply(ctrl.settings["theme"])
        self.title("iShara")
        self.geometry("1120x740")
        self.minsize(920, 620)
        self.protocol("WM_DELETE_WINDOW", self.quit_app)
        self.overlay = StatusOverlay(self)
        self.help_menu = HelpMenu(self, ctrl)
        self.widget = FloatingWidget(self, ctrl, self.bring_front)
        self.after(80, self.apply_widget_settings)
        self.practice_win = None
        self.current = "home"
        self.phase = 0
        self.level = 0.0
        self.page_view = None
        self.build()
        if not ctrl.settings.get("calibrated"):
            self.after(700, lambda: self.show("calibrate"))
        self.after(TICK_MS, self.loop)

    # ================================================================ layout
    def build(self):
        for w in self.winfo_children():
            if not isinstance(w, tk.Toplevel):
                w.destroy()
        self.configure(bg=C["bg"])
        self.side = tk.Canvas(self, width=216, bg=C["bg"], highlightthickness=0)
        self.side.pack(side="left", fill="y")
        self.side.bind("<Configure>", lambda e: self.draw_side())
        self.side.bind("<Motion>", lambda e: self.draw_side(self._nav_at(e.y)))
        self.side.bind("<Leave>", lambda e: self.draw_side())
        self.side.bind("<ButtonRelease-1>", self.side_click)
        tk.Frame(self, bg=C["line"], width=1).pack(side="left", fill="y")
        main = tk.Frame(self, bg=C["bg"])
        main.pack(side="left", fill="both", expand=True)
        self.top = tk.Canvas(main, height=52, bg=C["bg"], highlightthickness=0)
        self.top.pack(fill="x")
        self.top.bind("<Configure>", lambda e: self.draw_top())
        self.top.bind("<ButtonRelease-1>", self.top_click)
        tk.Frame(main, bg=C["line"], height=1).pack(fill="x")
        self.statusbar = tk.Canvas(main, height=30, bg=C["bg"], highlightthickness=0)
        self.statusbar.pack(side="bottom", fill="x")
        tk.Frame(main, bg=C["line"], height=1).pack(side="bottom", fill="x")
        self.content = tk.Frame(main, bg=C["bg"])
        self.content.pack(fill="both", expand=True)
        self.show(self.current if self.current != "calibrate" else "home")

    def show(self, page, tab=None):
        self.current = page
        for w in self.content.winfo_children():
            w.destroy()
        self.page_view = None
        if page == "home":
            self.page_view = HomePage(self.content, self)
            self.page_view.pack(fill="both", expand=True)
        elif page == "training":
            self.build_training()
        elif page == "calibrate":
            CalibrationPage(self.content, self.ctrl, lambda: self.show("training")).pack(fill="both", expand=True)
        elif page == "settings":
            SettingsPage(self.content, self.ctrl, self.on_settings_change, start=tab).pack(fill="both", expand=True)
        elif page == "profiles":
            SettingsPage(self.content, self.ctrl, self.on_settings_change,
                         sections=["Profiles"]).pack(fill="both", expand=True)
        elif page == "about":
            self.build_about()
        if hasattr(self, "side"):
            self.draw_side()
            self.draw_top()

    # ================================================================ sidebar
    def draw_side(self, hover=None):
        c = self.side
        c.delete("all")
        h = c.winfo_height()
        draw_logo(c, 22, 18, 22)
        c.create_text(54, 29, text="iShara", anchor="w", fill=C["text"], font=F["h2"])
        cur = "training" if self.current == "calibrate" else self.current
        for i, (key, text, ic) in enumerate(NAV):
            y = 68 + i * 36
            if key == cur:
                rrect(c, 12, y, 204, y + 32, 6, fill=C["hover"], outline=C["hover"])
            elif key == hover:
                rrect(c, 12, y, 204, y + 32, 6, fill=C["line2"], outline=C["line2"])
            active = key == cur
            c.create_text(34, y + 16, text=I[ic], font=F["icon_s"], fill=C["text"] if active else C["sub"])
            c.create_text(54, y + 16, text=text, anchor="w", fill=C["text"] if active else C["sub"],
                          font=F["bodyb"] if active else F["body"])
        c.create_text(22, h - 24, text=self.ctrl.profile["name"], anchor="w", fill=C["sub"], font=F["small"])
        c.create_text(204, h - 24, text=f"v{__version__}", anchor="e", fill=C["faint"], font=F["tiny"])

    def _nav_at(self, y):
        i = int((y - 68) // 36)
        if 0 <= i < len(NAV) and (y - 68) % 36 <= 32:
            return NAV[i][0]
        return None

    def side_click(self, e):
        key = self._nav_at(e.y)
        if key:
            self.show(key)

    # ================================================================ top bar
    def draw_top(self):
        c, ctrl = self.top, self.ctrl
        c.delete("all")
        w = c.winfo_width()
        c.create_text(28, 26, text=TITLES.get(self.current, ""), anchor="w", fill=C["text"], font=F["h2"])
        c.create_text(w - 28, 26, text=I["settings"], font=F["icon_m"], fill=C["sub"], tags="gear")
        x = w - 58
        for txt, col, tag in reversed(self._chips()):
            t = c.create_text(x, 26, text=txt, anchor="e", fill=C["sub"], font=F["small"], tags=tag)
            x1 = c.bbox(t)[0]
            c.create_oval(x1 - 13, 22, x1 - 5, 30, fill=col, outline="", tags=tag)
            x = x1 - 30

    def _chips(self):
        ctrl = self.ctrl
        alive = ctrl.link.data_alive()
        hb = ("Headband connected", C["green"]) if alive else \
             (("Headband connecting", C["amber"]) if ctrl.link.state in ("connecting", "connected")
              else ("Headband not found", C["gray"]))
        if ctrl.mic_state == "error":
            mic = ("Microphone problem", C["red"])
        elif ctrl.mic_state != "listening":
            mic = ("Microphone off", C["gray"])
        elif ctrl.mic_muted:
            mic = ("Microphone muted", C["red"])
        else:
            mic = ("Microphone listening", C["green"])
        return [(hb[0], hb[1], "hb"), (mic[0], mic[1], "micchip")]

    def top_click(self, e):
        items = self.top.find_overlapping(e.x - 2, e.y - 2, e.x + 2, e.y + 2)
        tags = {t for i in items for t in self.top.gettags(i)}
        if "gear" in tags:
            self.show("settings")
        elif "micchip" in tags:
            self.ctrl.toggle_mic()

    # ================================================================ status bar
    def draw_status(self, text, kind):
        c, ctrl = self.statusbar, self.ctrl
        sig = (text, kind, ctrl.profile["name"], ctrl.settings.get("calibrated"), c.winfo_width())
        if sig == getattr(self, "_status_sig", None):
            return
        self._status_sig = sig
        c.delete("all")
        w = c.winfo_width()
        col = {"ok": C["green"], "warn": C["amber"], "error": C["red"]}.get(kind, C["text"])
        c.create_text(28, 15, text=I["cursor"], font=F["icon_s"], fill=C["sub"])
        c.create_text(44, 15, text=text, anchor="w", fill=col, font=F["small"])
        right = f"{ctrl.profile['name']}  ·  " + ("Calibrated" if ctrl.settings.get("calibrated") else "Not calibrated")
        c.create_text(w - 20, 15, text=right, anchor="e", fill=C["faint"], font=F["tiny"])

    # ================================================================ pages
    def page_header(self, parent, title, sub):
        label(parent, title, "h1").pack(anchor="w", padx=28, pady=(24, 2))
        label(parent, sub, "body", "sub").pack(anchor="w", padx=28, pady=(0, 18))

    def list_panel(self, parent):
        outer = tk.Frame(parent, bg=C["line"], padx=1, pady=1)
        outer.pack(fill="x", padx=28)
        inner = tk.Frame(outer, bg=C["card"])
        inner.pack(fill="both")
        return inner

    def list_row(self, panel, title, desc, meta, btn, cmd, first=False, kind="soft"):
        if not first:
            tk.Frame(panel, bg=C["line2"], height=1).pack(fill="x")
        r = tk.Frame(panel, bg=C["card"], padx=20, pady=16)
        r.pack(fill="x")
        Pill(r, btn, cmd, kind=kind).pack(side="right")
        t = tk.Frame(r, bg=C["card"])
        t.pack(side="left", fill="x", expand=True)
        label(t, title, "h3", bg=C["card"]).pack(anchor="w")
        label(t, desc, "small", "sub", bg=C["card"], wraplength=560, justify="left").pack(anchor="w", pady=(2, 0))
        if meta:
            label(t, meta, "small", "text", bg=C["card"]).pack(anchor="w", pady=(6, 0))

    def build_training(self):
        p = tk.Frame(self.content, bg=C["bg"])
        p.pack(fill="both", expand=True)
        self.page_header(p, "Get set up", "Calibrate once for each person, then practise until it feels natural.")
        panel = self.list_panel(p)
        m = self.ctrl.model
        cal = self.ctrl.settings.get("calibrated")
        left, right = (m["rL"], m["rR"]) if not m["ix"] else (m["rR"], m["rL"])
        meta = (f"Range  left {left:.0f}° · right {right:.0f}° · up {m['rU']:.0f}° "
                f"· down {m['rD']:.0f}°") if cal else "Not calibrated yet"
        self.list_row(panel, "1   Calibration",
                      "Look straight, then tilt left, right, up and down. iShara learns your comfortable "
                      "range so every corner of the screen is easy to reach.",
                      meta, "Recalibrate" if cal else "Start calibration", lambda: self.show("calibrate"),
                      first=True, kind="soft" if cal else "primary")
        done = len(self.ctrl.settings.get("practice_passed", []))
        self.list_row(panel, "2   Practice",
                      "Seven short lessons: moving, aiming, click, double click, right click, scrolling "
                      "and typing. Each lesson unlocks the next.",
                      f"{done} of {len(LESSONS)} lessons passed", "Open practice", self.open_practice,
                      kind="primary" if cal and done < len(LESSONS) else "soft")

    def build_about(self):
        p = tk.Frame(self.content, bg=C["bg"])
        p.pack(fill="both", expand=True)
        self.page_header(p, "iShara", f"Head & voice mouse · version {__version__}")
        panel = self.list_panel(p)
        for i, (title, text) in enumerate([
            ("What it does", "A low-cost head-controlled mouse for people with upper limb disability. "
                             "Tilt your head to move the cursor; speak to click, scroll and type."),
            ("How it works", "ESP32 + MPU6050 headband acting as a Bluetooth mouse with a personal movement "
                             "model. Offline voice: Vosk for commands, Whisper for typing. "
                             "The Windows voice reads out feedback."),
            ("Privacy", "Everything runs on this computer. No internet connection is needed and nothing is uploaded."),
            ("Project", "Embedded Systems Design (CEN-440), Bahria University. "
                        "Typeface: Inter, SIL Open Font License."),
        ]):
            if i:
                tk.Frame(panel, bg=C["line2"], height=1).pack(fill="x")
            r = tk.Frame(panel, bg=C["card"], padx=20, pady=14)
            r.pack(fill="x")
            label(r, title, "bodyb", bg=C["card"], width=16, anchor="nw").pack(side="left", anchor="n")
            label(r, text, "body", "sub", bg=C["card"], wraplength=600, justify="left").pack(side="left", fill="x")

    # ================================================================ actions
    def open_practice(self):
        if self.practice_win and self.practice_win.winfo_exists():
            self.practice_win.lift()
            return
        self.practice_win = PracticeWindow(self, self.ctrl)

    def apply_widget_settings(self):
        s = self.ctrl.settings
        if s.get("widget_enabled", True):
            self.widget.deiconify()
        else:
            self.widget.withdraw()
        self.widget.set_click_through(bool(s.get("widget_click_through")))

    def on_settings_change(self, what=None):
        if what == "theme":
            theme.apply(self.ctrl.settings["theme"])
            self.current = "settings"
            self.build()
            self.widget._sig = None
            self.overlay.text = None
        elif what == "calibrate":
            self.show("calibrate")
        elif what == "widget":
            self.apply_widget_settings()
        elif what == "widget_reset":
            self.widget.reset_position()
        else:
            self.draw_side()

    def bring_front(self):
        self.deiconify()
        self.lift()
        self.focus_force()

    def quit_app(self):
        self.ctrl.shutdown()
        self.destroy()

    # ================================================================ live loop
    def loop(self):
        try:
            self.ctrl.tick()
            self.refresh()
        finally:
            self.after(TICK_MS, self.loop)

    def refresh(self):
        ctrl = self.ctrl
        self.phase += 1
        text, kind, persistent = ctrl.status_line()
        self.widget.refresh(text, kind)
        self.help_menu.sync()
        show = ctrl.settings["overlay_enabled"] and ctrl.link.state == "connected" and not ctrl.menu
        if text == "Cursor Stationary" and time.time() - ctrl.status.still_since > 1.0:
            show = False                     # stay out of the way when nothing is happening
        self.overlay.show(text if show else "", kind, ctrl.settings["overlay_position"])
        self.draw_status(text, kind)
        if self.phase % 10 == 0:
            self.draw_top()
        raw = getattr(ctrl.voice, "level", 0.0) if ctrl.mic_state == "listening" and not ctrl.mic_muted else 0.0
        self.level = max(raw, self.level * 0.85)
        if self.page_view and self.page_view.winfo_exists():
            self.page_view.update_dynamic()


class HomePage(tk.Frame):
    def __init__(self, parent, win):
        super().__init__(parent, bg=C["bg"])
        self.win, self.ctrl = win, win.ctrl
        self._sig = {}

        # ---------- control strip: three answers + the pause control
        strip_o = tk.Frame(self, bg=C["line"], padx=1, pady=1)
        strip_o.pack(fill="x", padx=28, pady=(24, 16))
        strip = tk.Frame(strip_o, bg=C["card"])
        strip.pack(fill="x")
        self.cells = {}
        for i, (key, title) in enumerate([("hb", "Headband"), ("ctl", "Head control"), ("mic", "Microphone")]):
            if i:
                tk.Frame(strip, bg=C["line2"], width=1).pack(side="left", fill="y", pady=12)
            cell = tk.Frame(strip, bg=C["card"], padx=20, pady=12)
            cell.pack(side="left")
            label(cell, title, "small", "sub", bg=C["card"]).pack(anchor="w")
            row = tk.Frame(cell, bg=C["card"])
            row.pack(anchor="w", pady=(3, 0))
            dot = tk.Canvas(row, width=10, height=10, bg=C["card"], highlightthickness=0)
            dot.pack(side="left", padx=(0, 7))
            val = label(row, "", "bodyb", bg=C["card"])
            val.pack(side="left")
            self.cells[key] = (dot, val)
        self.toggle_btn = Pill(strip, "Pause control", self._toggle, kind="soft", width=150, icon_name="pause")
        self.toggle_btn.pack(side="right", padx=16)

        # ---------- two panels
        row = tk.Frame(self, bg=C["bg"])
        row.pack(fill="both", expand=True, padx=28, pady=(0, 20))
        row.columnconfigure(0, weight=1, uniform="p")
        row.columnconfigure(1, weight=1, uniform="p")
        row.rowconfigure(0, weight=1)
        self.track_panel(row).grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        self.voice_panel(row).grid(row=0, column=1, sticky="nsew", padx=(8, 0))

    # ---------------------------------------------------------------- panels
    def panel(self, parent, title, meta=""):
        o = tk.Frame(parent, bg=C["line"], padx=1, pady=1)
        p = tk.Frame(o, bg=C["card"])
        p.pack(fill="both", expand=True)
        h = tk.Frame(p, bg=C["card"], padx=20, pady=14)
        h.pack(fill="x")
        label(h, title, "h3", bg=C["card"]).pack(side="left")
        m = label(h, meta, "small", "faint", bg=C["card"])
        m.pack(side="right")
        tk.Frame(p, bg=C["line2"], height=1).pack(fill="x")
        body = tk.Frame(p, bg=C["card"], padx=20, pady=18)
        body.pack(fill="both", expand=True)
        return o, body, m

    def readout(self, parent, name):
        r = tk.Frame(parent, bg=C["card"])
        r.pack(fill="x", pady=4)
        label(r, name, "small", "sub", bg=C["card"], width=11, anchor="w").pack(side="left")
        v = label(r, "—", "bodyb", bg=C["card"], anchor="w")
        v.pack(side="left")
        return v

    def track_panel(self, parent):
        o, body, self.track_meta = self.panel(parent, "Head tracking", "")
        self.plot = TrackingView(body, 208, bg=C["card"])
        self.plot.pack(side="left", anchor="n")
        info = tk.Frame(body, bg=C["card"], padx=22)
        info.pack(side="left", fill="both", expand=True, anchor="n")
        self.r_dir = self.readout(info, "Direction")
        self.r_pitch = self.readout(info, "Up / down")
        self.r_roll = self.readout(info, "Left / right")
        self.r_speed = self.readout(info, "Cursor")
        self.r_range = self.readout(info, "Your range")
        tk.Frame(info, bg=C["card"], height=10).pack()
        Pill(info, "Recalibrate", lambda: self.win.show("calibrate"), kind="soft").pack(anchor="w")
        return o

    def voice_panel(self, parent):
        o, body, self.voice_meta = self.panel(parent, "Voice", "")
        # microphone + level meter
        r = tk.Frame(body, bg=C["card"])
        r.pack(fill="x")
        self.mic_lbl = label(r, "", "bodyb", bg=C["card"])
        self.mic_lbl.pack(side="left")
        self.meter = tk.Canvas(r, width=104, height=14, bg=C["card"], highlightthickness=0)
        self.meter.pack(side="right")
        # mode
        r = tk.Frame(body, bg=C["card"])
        r.pack(fill="x", pady=(16, 0))
        label(r, "Mode", "small", "sub", bg=C["card"], width=11, anchor="w").pack(side="left")
        self.mode = Choice(r, [("command", "Commands"), ("dictation", "Dictation")],
                           "dictation" if self.ctrl.dictation else "command", self._mode)
        self.mode.pack(side="left")
        # heard / last command
        tk.Frame(body, bg=C["line2"], height=1).pack(fill="x", pady=16)
        self.heard = self.readout(body, "Heard")
        self.heard.config(font=F["body"], wraplength=300, justify="left")
        r = tk.Frame(body, bg=C["card"])
        r.pack(fill="x", pady=4)
        label(r, "Last action", "small", "sub", bg=C["card"], width=11, anchor="w").pack(side="left")
        self.last_lbl = label(r, "—", "bodyb", bg=C["card"])
        self.last_lbl.pack(side="left")
        self.last_state = label(r, "", "small", bg=C["card"])
        self.last_state.pack(side="left", padx=(8, 0))
        tk.Frame(body, bg=C["card"], height=10).pack()
        foot = tk.Frame(body, bg=C["card"])
        foot.pack(fill="x", side="bottom")
        self.mute_btn = Pill(foot, "Mute microphone", self.ctrl.toggle_mic, kind="soft", icon_name="mic_off",
                             width=172)
        self.mute_btn.pack(side="left")
        Pill(foot, "All voice commands", lambda: self.win.show("settings", "Voice commands"),
             kind="ghost", icon_name="list").pack(side="left", padx=8)
        return o

    # ---------------------------------------------------------------- actions
    def _toggle(self):
        self.ctrl.request("resume" if self.ctrl.paused else "pause")

    def _mode(self, v):
        if (v == "dictation") != self.ctrl.dictation:
            self.ctrl.request("dictation_on" if v == "dictation" else "dictation_off")

    def _set(self, key, widget, **kw):
        """Only touch Tk when the value changed (keeps the UI cheap and flicker-free)."""
        sig = tuple(sorted(kw.items()))
        if self._sig.get(key) != sig:
            self._sig[key] = sig
            widget.config(**kw)

    def _cell(self, key, text, col):
        dot, val = self.cells[key]
        if self._sig.get(key) != (text, col):
            self._sig[key] = (text, col)
            dot.delete("all")
            dot.create_oval(1, 1, 9, 9, fill=col, outline="")
            val.config(text=text)

    # ---------------------------------------------------------------- live
    def update_dynamic(self):
        ctrl = self.ctrl
        alive = ctrl.link.data_alive()
        st = ctrl.link.state
        self._cell("hb", "Connected" if alive else ("Connecting…" if st in ("connecting", "connected")
                                                    else "Not found"),
                   C["green"] if alive else (C["amber"] if st in ("connecting", "connected") else C["gray"]))
        self._cell("ctl", "Paused" if ctrl.paused else ("Active" if alive else "Waiting for headband"),
                   C["amber"] if ctrl.paused else (C["green"] if alive else C["gray"]))
        listening = ctrl.mic_state == "listening"
        mic_txt = ("Problem" if ctrl.mic_state == "error" else "Off" if not listening else
                   "Muted" if ctrl.mic_muted else "Writing…" if ctrl.transcribing else
                   "Dictating" if ctrl.dictation else "Listening")
        mic_col = (C["red"] if ctrl.mic_state == "error" or ctrl.mic_muted else
                   C["gray"] if not listening else C["accent"] if ctrl.dictation else C["green"])
        self._cell("mic", mic_txt, mic_col)
        if ctrl.paused:
            self.toggle_btn.set_text("Resume control", "primary", "play")
        else:
            self.toggle_btn.set_text("Pause control", "soft", "pause")

        # head tracking
        sample, _ = ctrl.link.latest()
        m = ctrl.model
        if sample and alive:
            nx, ny = pm.normalized(sample.pitch, sample.roll, m)
            self.plot.show(nx, ny, m["dz"], active=not ctrl.paused, unstable=not sample.sensor_ok)
            if abs(nx) < m["dz"] and abs(ny) < m["dz"]:
                d = "Centered"
            elif abs(nx) > 1 or abs(ny) > 1:
                d = "At your limit"
            else:
                d = ("Right" if nx > 0 else "Left") if abs(nx) > abs(ny) else ("Down" if ny > 0 else "Up")
            self._set("dir", self.r_dir, text=d, fg=C["amber"] if d == "At your limit" else C["text"])
            self._set("p", self.r_pitch, text=f"{sample.pitch:+.1f}°")
            self._set("r", self.r_roll, text=f"{sample.roll:+.1f}°")
            mv = "Paused" if ctrl.paused else (f"{sample.dx:+d}, {sample.dy:+d} px" if sample.dx or sample.dy else "Still")
            self._set("sp", self.r_speed, text=mv)
        else:
            self.plot.show(0, 0, m["dz"], active=False)
            for k, wdg in (("dir", self.r_dir), ("p", self.r_pitch), ("r", self.r_roll), ("sp", self.r_speed)):
                self._set(k, wdg, text="—", fg=C["text"])
        lr = (m["rL"], m["rR"]) if not m["ix"] else (m["rR"], m["rL"])
        self._set("rng", self.r_range, text=f"←{lr[0]:.0f}° →{lr[1]:.0f}°  "
                                            f"↑{m['rU']:.0f}° ↓{m['rD']:.0f}°")
        self._set("tm", self.track_meta, text="Live" if alive and not ctrl.paused else "")

        # voice
        self._set("mic", self.mic_lbl, text={"Listening": "Listening for commands",
                                             "Dictating": "Dictation — speak to type",
                                             "Muted": "Muted — say “start listening”",
                                             "Off": "Voice control is off",
                                             "Problem": "Microphone problem",
                                             "Writing…": "Writing your text…"}[mic_txt])
        c = self.meter
        c.delete("all")
        lvl = self.win.level if listening and not ctrl.mic_muted else 0
        for i in range(10):
            on = lvl * 2.4 > (i + 0.5) / 10
            c.create_rectangle(i * 10 + 2, 3, i * 10 + 8, 11, outline="",
                               fill=(C["accent"] if ctrl.dictation else C["green"]) if on else C["line"])
        mode = "dictation" if ctrl.dictation else "command"
        if self.mode.value != mode:
            self.mode.set(mode, False)
        if ctrl.partial:
            self._set("heard", self.heard, text=f"“{ctrl.partial}…”", fg=C["sub"])
        elif ctrl.last_heard:
            pre = {"command": "", "dictation": "Typed: ", "error": ""}.get(ctrl.last_heard_kind, "")
            self._set("heard", self.heard, text=pre + ctrl.last_heard,
                      fg=C["red"] if ctrl.last_heard_kind == "error" else C["text"])
        else:
            self._set("heard", self.heard, text="Say “click”, “scroll down” or “start typing”",
                      fg=C["faint"])
        if ctrl.last_action:
            name, state, detail, t = ctrl.last_action
            self._set("la", self.last_lbl, text=name)
            st_txt = {"ok": f"✓ Done · {ago(t)}", "failed": f"✕ Failed · {detail}"[:40],
                      "pending": "Announcing…"}[state]
            self._set("ls", self.last_state, text=st_txt,
                      fg={"ok": C["green"], "failed": C["red"], "pending": C["sub"]}[state])
        if ctrl.mic_muted:
            self.mute_btn.set_text("Unmute microphone", "primary", "mic")
        else:
            self.mute_btn.set_text("Mute microphone", "soft", "mic_off")
        self._set("vm", self.voice_meta, text="Offline")
