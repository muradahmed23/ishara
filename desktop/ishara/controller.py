"""Central controller: one source of truth for state, actions and status.

Threads (link, voice) only post events into a queue; everything is applied in
tick(), called from the UI thread every ~30 ms. This keeps the indicator, the
real cursor and the status text synchronized with the same state.
"""
import os
import queue
import subprocess
import time

from . import profiles, screen
from .link import BleLink, SimLink
from .speech import Speaker
from .voice import VoiceEngine

# Spoken feedback.
# SPEAK_FIRST: announce, then act (mode changes the user should be warned about).
# Everything else acts immediately and then confirms; pause/stop are never delayed.
SPEAK_FIRST = {
    "resume": "Resuming control",
    "dictation_on": "Typing mode. Start speaking.",
    "dictation_off": "Command mode",
    "recenter": "Look straight and keep still",
    "keyboard": "Opening keyboard",
    "find_cursor": "Cursor to the center",
    "click_lock": None,                      # text depends on state, see _speak_first_text
    "mic_sleep": "Microphone muted. Say start listening to turn it back on.",
}
SPOKEN_AFTER = {
    "left_click": "Click", "right_click": "Right click", "double_click": "Double click",
    "middle_click": "Middle click", "go_back": "Back", "go_forward": "Forward",
    "scroll_up": "Scrolling up", "scroll_down": "Scrolling down",
    "drag_start": "Dragging", "drag_release": "Released",
    "pause": "Paused", "hand_mouse": "Hand mouse. Say head mouse to go back.",
    "stop": "Control stopped. Say resume to continue.",
    "mic_wake": "Listening",
}

ACTION_LABELS = {
    "left_click": "Left Click", "right_click": "Right Click", "double_click": "Double Click",
    "middle_click": "Middle Click", "go_back": "Back", "go_forward": "Forward",
    "scroll_up": "Scrolling Up", "scroll_down": "Scrolling Down",
    "drag_start": "Dragging", "drag_release": "Released", "pause": "Mouse Paused",
    "resume": "Resumed", "stop": "Control Stopped", "dictation_on": "Dictation Mode Active",
    "dictation_off": "Command Mode", "click_lock": "Click Lock", "keyboard": "On-Screen Keyboard",
    "recenter": "Re-centering", "find_cursor": "Cursor to Center",
    "mic_sleep": "Microphone Muted", "mic_wake": "Microphone On",
    "hand_mouse": "Hand Mouse", "help_menu": "Help", "more": "More…", "back": "Back",
}

# Help menu ("show commands" / "what can I say" / "help"). Say the number to choose.
# Every voice action is listed. "more" / "back" move one page forward / back.
MENU_PAGES = [
    ["left_click", "double_click", "right_click", "middle_click", "scroll_up", "scroll_down",
     "drag_start", "more"],
    ["go_back", "go_forward", "click_lock", "drag_release", "dictation_on", "dictation_off",
     "back", "more"],
    ["hand_mouse", "pause", "stop", "keyboard", "recenter", "find_cursor", "mic_sleep", "back"],
]
MENU_ALL = {a for page in MENU_PAGES for a in page} | {"resume", "mic_wake"}
MENU_TIMEOUT_S = 30
MENU_TEXT = {
    "left_click": "Click", "double_click": "Double click", "right_click": "Right click",
    "scroll_up": "Scroll up", "scroll_down": "Scroll down", "drag_start": "Start dragging",
    "drag_release": "Release drag", "dictation_on": "Start typing", "more": "More…",
    "pause": "Pause control", "resume": "Resume control", "mic_sleep": "Mute microphone",
    "mic_wake": "Unmute microphone", "keyboard": "Keyboard", "recenter": "Re-center head",
    "find_cursor": "Cursor to center", "click_lock": "Click lock", "back": "Back",
    "hand_mouse": "Use hand mouse", "middle_click": "Middle click", "go_back": "Back button",
    "go_forward": "Forward button", "dictation_off": "Stop typing", "stop": "Stop control",
}


class Status:
    """Persistent states + one temporary message. Avoids redundant updates."""

    def __init__(self):
        self.temp, self.temp_kind, self.temp_until = "", "info", 0.0
        self.movement = "Cursor Stationary"
        self.still_since = time.time()

    def flash(self, text, kind="info", seconds=1.6):
        self.temp, self.temp_kind, self.temp_until = text, kind, time.time() + seconds


class Controller:
    def __init__(self, simulate=False):
        self.events = queue.Queue()
        self.profile = profiles.load(profiles.current_name())
        self.link = (SimLink() if simulate else BleLink()).start()
        self.status = Status()

        self.paused = False
        self.hand_mode = False          # head movement off, real mouse free, voice clicks on
        self.dictation = False
        self.dragging = False
        self.click_lock = False
        self.mic_state = "off"          # off | listening | error
        self.partial = ""
        self.last_heard = ""
        self.last_heard_kind = ""       # command | dictation | error
        self._last_cmd = {}
        self._last_typed = ""
        self._pushed_model = False
        self._last_clip = 0.0
        self._prev_pos = screen.cursor_pos()
        self._dwell_anchor = self._prev_pos
        self._dwell_since = time.time()
        self._dwell_armed = False
        self.dwell_progress = 0.0
        self._was_alive = False
        self._recenter_done_at = 0.0
        self.transcribing = False
        self.last_action = None         # (label, "ok"|"failed"|"pending", detail, time)
        self.menu = None                # help menu state while it is open
        self.menu_rect = None           # its screen rectangle (set by the popup)

        s = self.settings
        self.speech = Speaker(s["speak"], s["speech_rate"], s["speech_volume"])
        self.voice = self._new_voice()
        if s["voice_enabled"]:
            self.voice.start()

    def _new_voice(self):
        s = self.settings
        return VoiceEngine(self._voice_event, s["commands"], s["mic_device"],
                           muted=lambda: self.speech.speaking,
                           dictation_engine=s["dictation_engine"], whisper_model=s["whisper_model"],
                           vocabulary=s.get("vocabulary", []))

    # ---------------------------------------------------------- shortcuts
    @property
    def settings(self):
        return self.profile["settings"]

    @property
    def model(self):
        return self.profile["model"]

    @property
    def mic_muted(self):
        return bool(getattr(self.voice, "sleeping", False))

    def toggle_mic(self):
        self.request("mic_wake" if self.mic_muted else "mic_sleep")

    def save_profile(self):
        profiles.save(self.profile)

    def say(self, text, then=None):
        """Speak through the laptop speaker. `then` runs after speaking (on the
        speech thread, so it only posts to the event queue / link queue)."""
        self.speech.enabled = bool(self.settings.get("speak", True))
        self.speech.say(text, then)

    def apply_speech_settings(self):
        s = self.settings
        self.speech.enabled = bool(s["speak"])
        self.speech.set_voice(s["speech_rate"], s["speech_volume"])

    # ---------------------------------------------------------- voice thread -> queue
    def _voice_event(self, kind, payload):
        self.events.put((kind, payload))

    # ---------------------------------------------------------- public actions
    def request(self, action, source="ui"):
        """Run an action (from UI buttons or voice). Always on the UI thread."""
        self.events.put(("action", (action, source)))

    def set_model(self, changes, save=True):
        self.model.update(changes)
        from .protocol import clamp_model
        self.profile["model"] = clamp_model(self.model)
        self.link.set_model(self.model, save=save)
        self.save_profile()

    def restart_voice(self):
        self.voice.stop()
        time.sleep(0.4)
        self.voice = self._new_voice()
        self.mic_state = "off"
        if self.settings["voice_enabled"]:
            self.voice.start()

    def load_profile(self, name):
        self.profile = profiles.load(name)
        profiles.set_current(name)
        self._pushed_model = False
        self.apply_speech_settings()
        self.restart_voice()

    # ---------------------------------------------------------- action executor
    # ---------------------------------------------------------- help menu
    def _menu_items(self, page):
        items = list(MENU_PAGES[page])
        if self.dragging:
            items = ["drag_release" if a == "drag_start" else a for a in items]
        if self.paused:
            items = ["resume" if a == "pause" else a for a in items]
        if self.mic_muted:
            items = ["mic_wake" if a == "mic_sleep" else a for a in items]
        if self.hand_mode:
            items = ["resume" if a == "hand_mouse" else a for a in items]
        return items

    def open_menu(self, page=0, anchor=None):
        self.menu = dict(page=page, items=self._menu_items(page), until=time.time() + MENU_TIMEOUT_S,
                         anchor=anchor or screen.cursor_pos())
        self.menu_rect = None

    def close_menu(self):
        self.menu = None
        self.menu_rect = None

    def _cursor_on_menu(self):
        r = self.menu_rect
        if not r:
            return False
        x, y = screen.cursor_pos()
        return r[0] <= x < r[2] and r[1] <= y < r[3]

    def _menu_action(self, action):
        """help_menu opens the menu; menu_* only work while it is open."""
        st = self.status
        if action == "help_menu":
            self.open_menu(0, self.menu["anchor"] if self.menu else None)
            st.flash("Help — say a number", "info", 2)
            self.say("Say a number, or close.")
            return
        if not self.menu:
            return                                   # "one", "close"... mean nothing without the menu
        self.menu["until"] = time.time() + MENU_TIMEOUT_S
        if action == "menu_close":
            self.close_menu()
            st.flash("Help closed", "info", 1.2)
            self.say("Closed")
            return
        if action in ("menu_more", "menu_back"):
            return self._menu_page(self.menu["page"] + (1 if action == "menu_more" else -1))
        i = int(action.split("_")[1]) - 1
        items = self.menu["items"]
        if i >= len(items):
            return
        self._menu_choose(items[i])

    def _menu_page(self, page):
        page = max(0, min(page, len(MENU_PAGES) - 1))
        if page == self.menu["page"]:
            return
        forward = page > self.menu["page"]
        self.menu.update(page=page, items=self._menu_items(page))
        self.say(f"Page {page + 1} of {len(MENU_PAGES)}" if forward else "Back")

    def _menu_choose(self, item):
        """Run a menu item at the place where the menu was opened, then close the menu."""
        if item in ("more", "back"):
            return self._menu_page(self.menu["page"] + (1 if item == "more" else -1))
        anchor = self.menu["anchor"]
        self.close_menu()
        try:
            screen.set_cursor(*anchor)
        except Exception:
            pass
        self._execute(item, "menu", announced=True)

    def _execute(self, action, source, announced=False):
        st = self.status
        label = ACTION_LABELS.get(action, action)
        if action == "help_menu" or action.startswith("menu_"):
            return self._menu_action(action)
        if self.menu and source != "menu":
            if action == "left_click" and self._cursor_on_menu():
                pass                                 # clicking a menu row with the head: plain click
            elif action in MENU_ALL:
                # a normal command said while the menu is open acts at the menu's spot
                return self._menu_choose(action)
        if self.paused and action not in ("resume", "pause", "stop", "hand_mouse", "dictation_off",
                                          "mic_sleep", "mic_wake"):
            st.flash("Paused \u2014 say \u201cresume\u201d", "warn")
            self.say("Paused. Say resume.")
            self.last_action = (label, "failed", "mouse is paused", time.time())
            return
        # speak first, then act (the action runs when the sentence has finished)
        if action in SPEAK_FIRST and not announced:
            text = SPEAK_FIRST[action] or ("Click lock off" if self.click_lock else "Click lock on")
            st.flash(label, "info", 2.5)
            self.last_action = (label, "pending", "", time.time())
            self.say(text, then=lambda: self.events.put(("announced", (action, source))))
            return
        try:
            if action == "left_click":
                if self.click_lock:
                    self._toggle_lock_hold()
                    return
                self._click("L", screen.left_click)
            elif action == "right_click":
                self._click("R", screen.right_click)
            elif action == "double_click":
                self._click("D", screen.double_click)
            elif action == "middle_click":
                self._click("M", screen.middle_click)
            elif action == "go_back":
                self._click("B", screen.back_click)
            elif action == "go_forward":
                self._click("F", screen.forward_click)
            elif action == "scroll_up":
                self._click(f"WHEEL {self.settings['scroll_lines']}", lambda: screen.scroll(self.settings["scroll_lines"]))
            elif action == "scroll_down":
                self._click(f"WHEEL {-self.settings['scroll_lines']}", lambda: screen.scroll(-self.settings["scroll_lines"]))
            elif action == "drag_start":
                self._click("DOWN", screen.left_down)
                self.dragging = True
            elif action == "drag_release":
                self._release()
                self.dragging = False
            elif action == "pause":
                self.pause()
            elif action == "hand_mouse":
                self.hand_mouse()
            elif action == "resume":
                self.resume()
            elif action == "stop":
                self.pause()
                st.flash("Control stopped \u2014 say \u201cresume\u201d", "warn", 3)
                self.say(SPOKEN_AFTER["stop"])
                self.last_action = (label, "ok", "", time.time())
                return
            elif action == "dictation_on":
                self.dictation = True
                self.voice.set_mode("dictation")
            elif action == "dictation_off":
                self.dictation = False
                self.voice.set_mode("command")
            elif action == "click_lock":
                self.click_lock = not self.click_lock
                if not self.click_lock and self.dragging:
                    self._release()
                    self.dragging = False
                label = "Click Lock On" if self.click_lock else "Click Lock Off"
            elif action == "keyboard":
                subprocess.Popen(os.path.join(os.environ.get("WINDIR", r"C:\Windows"),
                                              "System32", "osk.exe"), shell=True)
            elif action == "recenter":
                if not self.link.data_alive():
                    raise RuntimeError("headband not connected")
                self.link.send("CAL")
                self._recenter_done_at = time.time() + 3.2     # headband averages ~3 s
            elif action == "find_cursor":
                screen.center_cursor()
            elif action == "mic_sleep":
                if self.dictation:
                    self.dictation = False
                    self.voice.set_mode("command")
                self.voice.sleeping = True
                self.partial = ""
            elif action == "mic_wake":
                self.voice.sleeping = False
            else:
                raise ValueError(f"unknown action {action}")
        except Exception as e:
            st.flash(f"{label} failed: {e}", "error", 3)
            self.say(f"Sorry, {label.lower()} failed")
            self.last_action = (label, "failed", str(e), time.time())
            return
        self.last_action = (label, "ok", "", time.time())
        done = label if action in ("dictation_on", "pause", "stop") else \
            (f"{label} Executed" if action in ("left_click", "right_click", "double_click", "middle_click") else label)
        st.flash(done, "ok")
        if action in SPOKEN_AFTER and source != "dwell":
            self.say(SPOKEN_AFTER[action])
        elif source == "dwell":
            self.say("Click")

    def _click(self, hid_action, software):
        """Click through the headband (a real Bluetooth mouse: works on protected
        windows like the On-Screen Keyboard); software click if no headband."""
        if not self.link.hid(hid_action):
            software()

    def _release(self):
        """Release the button on BOTH paths, so a drag can never stay stuck."""
        self.link.hid("UP")
        screen.left_up()

    def _toggle_lock_hold(self):
        self.last_action = ("Release" if self.dragging else "Hold (Click Lock)", "ok", "", time.time())
        if self.dragging:
            self._release()
            self.dragging = False
            self.status.flash("Released", "ok")
            self.say("Released")
        else:
            self._click("DOWN", screen.left_down)
            self.dragging = True
            self.status.flash("Holding (Click Lock)", "ok")
            self.say("Holding")

    def hand_mouse(self):
        """Hand control to the real mouse: head movement stops, the cursor is NOT
        frozen, and voice clicks still work where the real mouse points."""
        self.paused, self.hand_mode = False, True
        self.link.send("PAUSE")
        screen.clip_to(None)
        self._last_clip = 0

    def pause(self):
        self.hand_mode = False
        self.paused = True
        if self.dragging:
            self._release()
            self.dragging = False
        self.link.send("PAUSE")
        screen.freeze_cursor()          # immediate, works even if the link is down

    def resume(self):
        self.paused = self.hand_mode = False
        self.link.send("RESUME")
        screen.clip_to(None)
        self._last_clip = 0

    def shutdown(self):
        try:
            if self.dragging:
                self._release()
            screen.clip_to(None)
            self.voice.stop()
            self.speech.close()
            if hasattr(self.link, "stop"):
                self.link.stop()
        except Exception:
            pass

    # ---------------------------------------------------------- main tick (UI thread)
    def tick(self):
        self._drain_events()
        now = time.time()

        # push the saved personal model to the headband once per connection
        if self.link.data_alive() and not self._pushed_model:
            self.link.set_model(self.model, save=True)
            self._pushed_model = True
        if self.link.state != "connected":
            self._pushed_model = False

        # announce connection changes and the end of a re-center
        alive = self.link.data_alive()
        if alive != self._was_alive:
            self._was_alive = alive
            self.say("Headband connected" if alive else "Headband disconnected")
        if self.menu and now > self.menu["until"]:        # safety: never leave it open forever
            self.close_menu()
            self.status.flash("Help closed", "info", 1.2)
        if self._recenter_done_at and now > self._recenter_done_at:
            self._recenter_done_at = 0
            self.status.flash("Centered", "ok")
            self.say("Centered")

        # strict boundary: lock to the active monitor (re-applied every second)
        if not self.paused and not self.hand_mode and self.settings["lock_to_screen"] and now - self._last_clip > 1.0:
            screen.clip_to(screen.monitor_rect())
            self._last_clip = now
        elif not self.paused and not self.settings["lock_to_screen"] and self._last_clip:
            screen.clip_to(None)
            self._last_clip = 0

        self._update_movement()
        self._dwell(now)

    def _drain_events(self):
        while True:
            try:
                kind, payload = self.events.get_nowait()
            except queue.Empty:
                return
            if kind == "action":
                self._execute(*payload)
            elif kind == "announced":
                self._execute(*payload, announced=True)
            elif kind == "state":
                self.mic_state = payload
            elif kind == "partial":
                self.partial = payload
            elif kind == "busy":
                self.transcribing = payload
            elif kind == "mode":
                self.dictation = payload == "dictation"
            elif kind == "error":
                self.last_heard, self.last_heard_kind = payload, "error"
                self.status.flash(payload, "error", 3)
            elif kind == "command":
                phrase, action = payload
                self.partial = ""
                now = time.time()
                if action.startswith("menu_") and not self.menu:
                    continue                         # menu words mean nothing while it is closed
                # debounce: continuous recognition must not repeat a click
                if now - self._last_cmd.get(action, 0) < self.settings["command_cooldown"]:
                    continue
                self._last_cmd[action] = now
                self.last_heard, self.last_heard_kind = phrase, "command"
                if not action.startswith("menu_"):
                    self.status.flash(f"Command Recognized: {ACTION_LABELS.get(action, phrase)}", "info", 0.6)
                self._execute(action, "voice")
            elif kind == "dictation":
                self.partial = ""
                self.last_heard, self.last_heard_kind = payload, "dictation"
                try:
                    said = " ".join(payload.lower().replace(".", " ").replace(",", " ").split())
                    if said == "delete that" and self._last_typed:
                        for _ in self._last_typed:
                            screen.key_press(screen.VK_BACK)
                        self._last_typed = ""
                        self.status.flash("Deleted", "ok")
                    else:
                        text = payload + ("" if payload.endswith("\n") else " ")
                        screen.type_text(text)
                        self._last_typed = text
                        self.status.flash("Typed", "ok", 0.8)
                except Exception as e:
                    self.status.flash(f"Typing failed: {e}", "error", 3)

    def _update_movement(self):
        """Status from the ACTUAL cursor motion, plus the headband's intent."""
        pos = screen.cursor_pos()
        mx, my = pos[0] - self._prev_pos[0], pos[1] - self._prev_pos[1]
        self._prev_pos = pos
        sample, _ = self.link.latest()
        want_x = sample.dx if sample and self.link.data_alive() else 0
        want_y = sample.dy if sample and self.link.data_alive() else 0
        edges = screen.at_edge(pos[0], pos[1], screen.monitor_rect(*pos))
        blocked = (want_x < 0 and "left" in edges) or (want_x > 0 and "right" in edges) or \
                  (want_y < 0 and "top" in edges) or (want_y > 0 and "bottom" in edges)
        st = self.status
        if blocked and abs(mx) + abs(my) == 0:
            text = "At Screen Boundary"
        elif abs(mx) + abs(my) < 1:
            text = "Cursor Stationary"
        else:
            horiz = "Right" if mx > 0 else "Left"
            vert = "Down" if my > 0 else "Up"
            if abs(mx) > 2 * abs(my):
                text = f"Moving {horiz}"
            elif abs(my) > 2 * abs(mx):
                text = f"Moving {vert}"
            else:
                text = "Moving Diagonally"
        if text != st.movement:
            st.movement = text
            st.still_since = time.time()

    def _dwell(self, now):
        s = self.settings
        self.dwell_progress = 0.0
        if not s["dwell_enabled"] or self.paused or self.hand_mode or self.dictation:
            self._dwell_armed = False
            return
        pos = screen.cursor_pos()
        ax, ay = self._dwell_anchor
        if (pos[0] - ax) ** 2 + (pos[1] - ay) ** 2 > s["dwell_radius"] ** 2:
            self._dwell_anchor, self._dwell_since, self._dwell_armed = pos, now, True
            return
        if self._dwell_armed:              # one click per stop, never repeats
            held = (now - self._dwell_since) * 1000
            self.dwell_progress = min(held / s["dwell_ms"], 1.0)
            if held >= s["dwell_ms"]:
                self._dwell_armed = False
                self._execute("left_click", "dwell")

    # ---------------------------------------------------------- view model
    def status_line(self):
        """(text, kind, persistent) shown by the main window, widget and overlay."""
        st = self.status
        if time.time() < st.temp_until:
            return st.temp, st.temp_kind, False
        if self.menu:
            return "Help — say a number", "info", True
        if self.paused:
            return "Mouse Paused", "warn", True
        if self.hand_mode:
            return "Hand Mouse — say “head mouse”", "info", True
        if self.link.state != "connected":
            return "Headband not connected", "warn", True
        if self.dragging:
            return "Dragging", "info", True
        if self.transcribing:
            return "Writing…", "info", True
        if self.dictation:
            return "Dictation Mode Active", "info", True
        if self.dwell_progress > 0.15:
            return f"Clicking\u2026 {int(self.dwell_progress * 100)}%", "info", False
        if self.partial and self.mic_state == "listening":
            return "Listening\u2026", "info", False
        return st.movement, "info", False
