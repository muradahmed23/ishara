"""Web UI host.

Threads
  main thread   : pywebview window (the iShara app, HTML/CSS in ishara/web/)
  native thread : hidden Tk root that runs the controller tick (~30 Hz), the
                  click-through cursor tag, the floating bar and the practice
                  lessons. These must stay native: click-through, no focus.
  link / voice / speech threads : unchanged.

The page polls Api.state() and calls Api methods for every action, so the UI
never touches the controller directly.
"""
import os
import queue
import threading
import time

from . import __version__, profiles
from . import model as pm
from .calib import CalibrationSession
from . import integrity
from .updates import Updater
from .protocol import DEFAULT_MODEL
from .voice import WHISPER_MODELS, list_microphones, whisper_available

WEB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "web")

ACTION_TEXT = {
    "left_click": "Left click", "right_click": "Right click", "double_click": "Double click",
    "middle_click": "Middle (wheel) click", "go_back": "Back button", "go_forward": "Forward button",
    "scroll_up": "Scroll up", "scroll_down": "Scroll down", "drag_start": "Start dragging",
    "drag_release": "Release drag", "click_lock": "Click lock", "pause": "Pause head control",
    "resume": "Resume head control", "hand_mouse": "Use the hand mouse (head off, voice clicks on)", "stop": "Emergency stop", "dictation_on": "Start dictation",
    "dictation_off": "Stop dictation", "keyboard": "On-screen keyboard", "recenter": "Re-center head",
    "find_cursor": "Cursor to screen center", "mic_sleep": "Mute microphone", "mic_wake": "Unmute microphone",
    "help_menu": "Show all actions next to the cursor",
    "menu_1": "Choose 1", "menu_2": "Choose 2", "menu_3": "Choose 3", "menu_4": "Choose 4",
    "menu_5": "Choose 5", "menu_6": "Choose 6", "menu_7": "Choose 7", "menu_8": "Choose 8",
    "menu_more": "Next page", "menu_back": "Previous page", "menu_close": "Close the menu",
}
COMMAND_GROUPS = [
                  ("Help", ["help_menu"]),
                  ("Inside the help menu", ["menu_1", "menu_2", "menu_3", "menu_4", "menu_5", "menu_6",
                                            "menu_7", "menu_8", "menu_more", "menu_back", "menu_close"]),("Mouse", ["left_click", "double_click", "right_click", "middle_click", "go_back", "go_forward", "scroll_up", "scroll_down",
                             "drag_start", "drag_release", "click_lock"]),
                  ("Control", ["hand_mouse", "pause", "resume", "stop", "recenter", "find_cursor", "keyboard"]),
                  ("Dictation", ["dictation_on", "dictation_off"]),
                  ("Microphone", ["mic_sleep", "mic_wake"])]

# settings the page may change, with their type
SETTING_TYPES = dict(voice_enabled=bool, mic_device=lambda v: None if v in (None, "", "null") else int(v),
                     command_cooldown=float, speak=bool, speech_rate=int, speech_volume=int,
                     dwell_enabled=bool, dwell_ms=int, scroll_lines=int, overlay_enabled=bool,
                     overlay_position=str, overlay_seconds=float, lock_to_screen=bool, theme=str,
                     widget_enabled=bool, widget_click_through=bool)
MODEL_KEYS = {"sx", "sy", "dz", "alpha", "gam", "ix", "iy"}


class NativeLayer(threading.Thread):
    """Hidden Tk root: controller tick + cursor tag + floating bar + practice."""

    def __init__(self, ctrl, api):
        super().__init__(daemon=True, name="native-ui")
        self.ctrl, self.api = ctrl, api
        self.jobs = queue.Queue()
        self.ready = threading.Event()
        self.stopping = False

    def call(self, fn):
        self.jobs.put(fn)

    def run(self):
        import ctypes
        import tkinter as tk
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            pass
        from .ui import theme
        from .ui.overlay import FloatingWidget, HelpMenu, StatusOverlay
        theme.load_private_fonts()
        self.root = tk.Tk()
        self.root.withdraw()
        theme.init_fonts()
        theme.apply(self.ctrl.settings["theme"])
        self.overlay = StatusOverlay(self.root)
        self.help_menu = HelpMenu(self.root, self.ctrl)
        self.widget = FloatingWidget(self.root, self.ctrl, self.api.bring_front)
        self.practice = None
        self.root.after(80, self.apply_widget)
        self.ready.set()
        self._loop()
        self.root.mainloop()

    def apply_widget(self):
        s = self.ctrl.settings
        (self.widget.deiconify if s.get("widget_enabled", True) else self.widget.withdraw)()
        self.widget.set_click_through(bool(s.get("widget_click_through")))

    def retheme(self):
        from .ui import theme
        theme.apply(self.ctrl.settings["theme"])
        self.widget._sig = None
        self.overlay.text = None

    def open_practice(self):
        from .ui.practice import PracticeWindow
        if self.practice and self.practice.winfo_exists():
            self.practice.deiconify()
            self.practice.lift()
            return
        self.practice = PracticeWindow(self.root, self.ctrl)

    def _loop(self):
        if self.stopping:
            self.root.quit()
            return
        try:
            while True:
                try:
                    self.jobs.get_nowait()()
                except queue.Empty:
                    break
            ctrl = self.ctrl
            ctrl.tick()
            if self.api._calib:
                self.api._calib.tick()
            text, kind, _ = ctrl.status_line()
            self.api._status = (text, kind)
            self.widget.refresh(text, kind)
            self.help_menu.sync()
            show = ctrl.settings["overlay_enabled"] and ctrl.link.state == "connected" and not ctrl.menu
            if text == "Cursor Stationary" and time.time() - ctrl.status.still_since > 1.0:
                show = False
            self.overlay.show(text if show else "", kind, ctrl.settings["overlay_position"])
            raw = getattr(ctrl.voice, "level", 0.0) if ctrl.mic_state == "listening" and not ctrl.mic_muted else 0.0
            self.api._level = max(raw, self.api._level * 0.85)
        except Exception as e:                           # never let the tick die
            print("native loop error:", e)
        self.root.after(30, self._loop)


class Api:
    """Methods callable from JavaScript as window.pywebview.api.<name>()."""

    def __init__(self, ctrl):
        self._ctrl = ctrl
        self._calib = None
        self._status = ("", "info")
        self._level = 0.0
        self._window = None
        self._native = NativeLayer(ctrl, self)
        self._updater = Updater()
        self._models = dict(state="checking", problems=[])
        threading.Thread(target=self._verify_models, daemon=True, name="model-check").start()

    def _verify_models(self):
        try:
            ok, problems = integrity.verify()
            self._models = dict(state="ok" if ok else "damaged", problems=problems[:5])
        except Exception as e:
            self._models = dict(state="error", problems=[str(e)])

    # ---------------------------------------------------------- window helpers
    def bring_front(self):
        if self._window:
            try:
                self._window.restore()
                self._window.show()
            except Exception:
                pass

    # ---------------------------------------------------------- read
    def state(self):
        c = self._ctrl
        s, m = c.settings, c.model
        sample, _ = c.link.latest()
        alive = c.link.data_alive()
        head = None
        if sample and alive:
            nx, ny = pm.normalized(sample.pitch, sample.roll, m)
            head = dict(pitch=round(sample.pitch, 1), roll=round(sample.roll, 1), nx=round(nx, 3),
                        ny=round(ny, 3), dx=sample.dx, dy=sample.dy, ok=sample.sensor_ok)
        left, right = (m["rL"], m["rR"]) if not m["ix"] else (m["rR"], m["rL"])
        la = c.last_action
        return dict(
            version=__version__,
            link=dict(state=c.link.state, alive=alive),
            paused=c.paused, dictation=c.dictation, transcribing=c.transcribing,
            mic=dict(state=c.mic_state, muted=c.mic_muted, level=round(self._level, 3)),
            partial=c.partial, heard=c.last_heard, heard_kind=c.last_heard_kind,
            last_action=dict(name=la[0], state=la[1], detail=la[2], ago=round(time.time() - la[3])) if la else None,
            status=dict(text=self._status[0], kind=self._status[1]),
            head=head, dz=m["dz"],
            ranges=dict(left=round(left), right=round(right), up=round(m["rU"]), down=round(m["rD"])),
            calibrated=bool(s.get("calibrated")),
            profile=c.profile["name"],
            practice=dict(passed=len(s.get("practice_passed", [])), total=7),
            calib=self._calib.state() if self._calib and self._calib.active else None,
            device=dict(
                connection="Bluetooth LE",
                link=c.link.state,
                alive=alive,
                # flag bit 4 of every live packet: the ESP32 can read the MPU6050
                sensor_ok=bool(sample.sensor_ok) if sample and alive else None,
                battery=None,          # this headband has no battery measurement
            ),
            models=self._models,
            update=dict(self._updater.status),
            welcome=not s.get("welcome_done", False),
        )

    def settings(self):
        c = self._ctrl
        s = c.settings
        whisper = [dict(id=k, name=v.split(" (")[0]) for k, v in WHISPER_MODELS.items() if whisper_available(k)]
        return dict(
            settings={k: s.get(k) for k in SETTING_TYPES},
            dictation=("vosk" if s["dictation_engine"] == "vosk" else s["whisper_model"]),
            vocabulary=", ".join(s.get("vocabulary", [])),
            whisper=whisper,
            model={k: c.model[k] for k in MODEL_KEYS},
            mics=[dict(id=i, name=n) for i, n in list_microphones()],
            commands=[dict(group=g, items=[dict(action=a, text=ACTION_TEXT[a],
                                                phrases=[p for p, x in s["commands"].items() if x == a])
                                           for a in acts]) for g, acts in COMMAND_GROUPS],
            profiles=profiles.list_profiles(), profile=c.profile["name"],
        )

    # ---------------------------------------------------------- actions
    def action(self, name):
        self._ctrl.request(name)
        return True

    def toggle_pause(self):
        self._ctrl.request("resume" if self._ctrl.paused else "pause")

    def toggle_mic(self):
        self._ctrl.toggle_mic()

    def set_setting(self, key, value):
        if key not in SETTING_TYPES:
            return False
        c = self._ctrl
        c.settings[key] = SETTING_TYPES[key](value)
        c.save_profile()
        if key in ("voice_enabled", "mic_device"):
            threading.Thread(target=c.restart_voice, daemon=True).start()
        elif key in ("speak", "speech_rate", "speech_volume"):
            c.apply_speech_settings()
            if key != "speak":
                c.say("This is how I sound")
        elif key in ("widget_enabled", "widget_click_through"):
            self._native.call(self._native.apply_widget)
        elif key == "theme":
            self._native.call(self._native.retheme)
        return True

    def set_dictation(self, value):
        c = self._ctrl
        if value == "vosk":
            c.settings["dictation_engine"] = "vosk"
        else:
            c.settings["dictation_engine"], c.settings["whisper_model"] = "whisper", value
        c.save_profile()
        threading.Thread(target=c.restart_voice, daemon=True).start()
        return True

    def set_vocabulary(self, text):
        """Comma-separated names/words that dictation should prefer."""
        c = self._ctrl
        words = [w.strip() for w in (text or "").split(",") if w.strip()][:50]
        c.settings["vocabulary"] = words
        c.save_profile()
        threading.Thread(target=c.restart_voice, daemon=True).start()
        return words

    def set_model(self, key, value):
        if key in MODEL_KEYS:
            self._ctrl.set_model({key: float(value)})
            return True
        return False

    def rename_command(self, old, new):
        new = (new or "").strip().lower()
        cmds = self._ctrl.settings["commands"]
        if not new or old not in cmds or (new in cmds and new != old):
            return False
        cmds[new] = cmds.pop(old)
        self._ctrl.save_profile()
        self._ctrl.voice.set_commands(cmds)
        return True

    def use_profile(self, name):
        self._ctrl.load_profile(name)
        return True

    def new_profile(self, name):
        name = (name or "").strip()
        if not name:
            return False
        p = profiles.load(name)
        profiles.save(p)
        self._ctrl.load_profile(p["name"])
        return True

    def delete_profile(self, name):
        if name != self._ctrl.profile["name"]:
            profiles.delete(name)
        return True

    def reset_calibration(self):
        c = self._ctrl
        c.set_model(dict(DEFAULT_MODEL))
        c.link.send("CAL")
        c.settings["calibrated"] = False
        c.save_profile()
        return True

    def widget_reset(self):
        self._native.call(self._native.widget.reset_position)

    def open_practice(self):
        self._native.call(self._native.open_practice)

    # ---------------------------------------------------------- welcome, help, updates
    def speak(self, text):
        """Read text aloud (welcome steps, help topics)."""
        self._ctrl.say(str(text)[:600])
        return True

    def open_bluetooth_settings(self):
        os.startfile("ms-settings:bluetooth")
        return True

    def welcome_done(self):
        c = self._ctrl
        c.settings["welcome_done"] = True
        c.save_profile()
        return True

    def update_check(self):
        self._updater.check()

    def update_download(self):
        self._updater.download()

    def update_install(self):
        if self._updater.install():
            self._native.stopping = True              # the installer replaces the app
            if self._window:
                self._window.destroy()
            return True
        return False

    # ---------------------------------------------------------- calibration
    def calib_start(self):
        if self._calib and self._calib.active:
            self._calib.cancel()
        self._calib = CalibrationSession(self._ctrl)

    def calib_cancel(self):
        if self._calib:
            self._calib.cancel()

    def calib_restart(self):
        if self._calib:
            self._calib.restart()

    def calib_skip(self):
        if self._calib:
            self._calib.skip_check()

    def calib_finish(self):
        if self._calib:
            self._calib.finish()


def run(ctrl):
    import webview
    api = Api(ctrl)
    api._native.start()
    api._native.ready.wait(10)
    window = webview.create_window(
        "iShara", url=os.path.join(WEB_DIR, "index.html"), js_api=api,
        width=1140, height=760, min_size=(940, 640), background_color="#F5F5F7")
    api._window = window
    try:
        webview.start(gui="edgechromium", http_server=True, private_mode=False,
                      storage_path=os.path.join(profiles.APPDIR, "webview"))
    finally:
        api._native.stopping = True
        ctrl.shutdown()
