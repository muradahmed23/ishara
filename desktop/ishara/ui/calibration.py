"""Guided calibration: Look Straight -> Left -> Right -> Up -> Down -> Check -> Complete.

Neutral is measured ON the ESP32 (CAL command, 2 s average). The movement range
is captured here from the live stream, turned into a personal model
(model.ranges_from_capture) and sent back to the headband, which saves it.
Mouse movement is paused for the whole flow.
"""
import statistics
import time
import tkinter as tk

from .. import model as pm
from .theme import C, F
from .widgets import HeadIndicator, Pill, label, rrect

CAPTURE_S = 3.5
START_DEG = 4.0          # movement must exceed this before capture starts
WAIT_S = 12.0            # give up waiting for movement after this

STEPS = [
    ("neutral", "Look straight", "Look at the middle of the screen and keep still."),
    ("left", "Move left", "Slowly tilt your head toward your LEFT shoulder, as far as is comfortable. Hold it."),
    ("right", "Move right", "Now tilt toward your RIGHT shoulder, as far as is comfortable. Hold it."),
    ("up", "Look up", "Lift your chin and look up, as far as is comfortable. Hold it."),
    ("down", "Look down", "Lower your chin and look down, as far as is comfortable. Hold it."),
    ("check", "Check", "Move the dot into each circle. This is how your cursor will feel."),
]
TARGETS = [(0, -0.75), (0.75, 0), (0, 0.75), (-0.75, 0)]
SPOKEN = {
    "left": "Tilt your head to your left shoulder, and hold.",
    "right": "Now tilt to your right shoulder, and hold.",
    "up": "Look up, and hold.",
    "down": "Look down, and hold.",
    "check": "Now move the dot into each circle.",
}


class CalibrationPage(tk.Frame):
    def __init__(self, parent, ctrl, on_done):
        super().__init__(parent, bg=C["bg"])
        self.ctrl, self.on_done = ctrl, on_done
        self.prev_model = dict(ctrl.model)
        self.capture = {}
        self.step = -1
        self.closed = False
        self.key, self.hit, self.started, self.extreme = "", set(), None, 0.0
        self.samples, self.t0, self.cal_sent = [], time.time(), time.time()

        # Left: step list (guided onboarding).  Right: instruction + live tracking.
        left = tk.Frame(self, bg=C["bg"], width=240)
        left.pack(side="left", fill="y", padx=(28, 0), pady=24)
        left.pack_propagate(False)
        label(left, "Calibration", "h1").pack(anchor="w")
        label(left, "About one minute. Mouse movement is paused until you finish.", "small", "sub",
              wraplength=210, justify="left").pack(anchor="w", pady=(4, 18))
        self.dots = tk.Canvas(left, width=230, height=40 * (len(STEPS) + 1), bg=C["bg"], highlightthickness=0)
        self.dots.pack(anchor="w")
        Pill(left, "Cancel", self.cancel, kind="ghost").pack(anchor="w", pady=(14, 0))
        tk.Frame(self, bg=C["line"], width=1).pack(side="left", fill="y", pady=24, padx=(0, 0))

        right = tk.Frame(self, bg=C["bg"])
        right.pack(side="left", fill="both", expand=True, padx=40, pady=24)
        self.stepno = label(right, "", "small", "sub")
        self.stepno.pack(anchor="w")
        self.title = label(right, "", "h1")
        self.title.pack(anchor="w", pady=(2, 4))
        self.hint = label(right, "", "body", "sub", wraplength=460, justify="left")
        self.hint.pack(anchor="w")
        self.ind = HeadIndicator(right, 236)
        self.ind.pack(anchor="w", pady=(20, 14))
        self.bar = tk.Canvas(right, width=236, height=4, bg=C["bg"], highlightthickness=0)
        self.bar.pack(anchor="w")
        self.note = label(right, "", "small", "sub", wraplength=460, justify="left")
        self.note.pack(anchor="w", pady=(10, 0))
        self.btns = tk.Frame(right, bg=C["bg"])
        self.btns.pack(anchor="w", pady=14)

        ctrl.link.send("PAUSE")
        self.after(200, self.next_step)
        self._loop()

    # ---------------------------------------------------------------- flow
    def next_step(self):
        self.step += 1
        for w in self.btns.winfo_children():
            w.destroy()
        self.note.config(text="", fg=C["sub"])
        if self.step >= len(STEPS):
            return self.complete()
        key, title, hint = STEPS[self.step]
        self.stepno.config(text=f"Step {self.step + 1} of {len(STEPS)}")
        self.title.config(text=title)
        self.hint.config(text=hint)
        self.key, self.t0, self.started, self.extreme, self.hit = key, time.time(), None, 0.0, set()
        self.samples = []
        if key == "neutral":
            self.note.config(text="Follow the spoken instructions.")
            self._start_neutral("Look straight at the screen and keep still.")
        else:
            self.ctrl.say(SPOKEN[key])
        if key == "check":
            m = pm.ranges_from_capture(self.capture["left"], self.capture["right"],
                                       self.capture["up"], self.capture["down"], self.ctrl.model)
            self.new_model = m
            self.ctrl.link.set_model(m, save=False)      # try it before saving
            issues = pm.capture_quality(self.capture["left"], self.capture["right"],
                                        self.capture["up"], self.capture["down"])
            if issues:
                self.note.config(text=" ".join(issues), fg=C["amber"])
            Pill(self.btns, "Start over", self.restart, kind="soft").pack(side="left")
            Pill(self.btns, "Skip check", self.next_step, kind="ghost").pack(side="left", padx=8)

    def _start_neutral(self, sentence):
        """Speak first, THEN measure, so the user is already still when the headband
        starts averaging. Until the sentence ends, cal_sent = inf keeps the step waiting."""
        self.cal_sent = float("inf")

        def go():
            self.ctrl.link.send("CAL")
            self.cal_sent = time.time()
        self.ctrl.say(sentence, then=go)

    def restart(self):
        self.capture, self.step = {}, -1
        self.ctrl.link.set_model(self.prev_model, save=False)
        self.next_step()

    def complete(self):
        self.stepno.config(text="Done")
        self.title.config(text="Calibration complete")
        self.hint.config(text="Your personal settings are saved on the headband and in your profile.")
        self.ctrl.set_model(self.new_model, save=True)
        self.ctrl.settings["calibrated"] = True
        self.ctrl.save_profile()
        self.ctrl.link.send("RESUME")
        self.ctrl.say("Calibration complete. You can use the mouse now.")
        r = self.new_model
        self.note.config(text=f"Range  left {r['rL'] if not r['ix'] else r['rR']:.0f}° · "
                              f"right {r['rR'] if not r['ix'] else r['rL']:.0f}° · "
                              f"up {r['rU']:.0f}° · down {r['rD']:.0f}°")
        Pill(self.btns, "Finish", self.finish, kind="primary").pack(side="left")
        self.step = len(STEPS) + 1

    def finish(self):
        self.closed = True
        self.on_done()

    def cancel(self):
        self.closed = True
        self.ctrl.link.set_model(self.prev_model, save=False)
        self.ctrl.link.send("RESUME")
        self.on_done()

    # ---------------------------------------------------------------- live loop
    def _loop(self):
        if self.closed or not self.winfo_exists():
            return
        self._draw_dots()
        sample, _ = self.ctrl.link.latest()
        alive = self.ctrl.link.data_alive()
        if not alive:
            self.note.config(text="Waiting for the headband… make sure it is on and connected.",
                             fg=C["amber"])
            self.ind.show(0, 0, self.ctrl.model["dz"], active=False)
            self.after(100, self._loop)
            return
        mdl = getattr(self, "new_model", None) if self.key == "check" else None
        nx, ny = pm.normalized(sample.pitch, sample.roll, mdl or self.ctrl.model)
        if self.step < len(STEPS):
            self._step_logic(sample, nx, ny)
        tgts = TARGETS if self.step < len(STEPS) and self.key == "check" else ()
        self.ind.show(nx, ny, self.ctrl.model["dz"], active=True,
                      unstable=not sample.sensor_ok, targets=tgts, hit=self.hit)
        self.after(33, self._loop)

    def _progress(self, f):
        self.bar.delete("all")
        self.bar.create_rectangle(0, 0, 236, 4, fill=C["line"], outline="")
        if f > 0:
            self.bar.create_rectangle(0, 0, 236 * min(f, 1), 4, fill=C["accent"], outline="")

    def _draw_dots(self):
        """Vertical step list: done (check), current (accent), upcoming (grey)."""
        sig = self.step
        if getattr(self, "_dots_sig", None) == sig:
            return
        self._dots_sig = sig
        c = self.dots
        c.delete("all")
        names = [s[1] for s in STEPS] + ["Complete"]
        for i, name in enumerate(names):
            y = 14 + i * 40
            if i < len(names) - 1:
                c.create_line(10, y + 10, 10, y + 30, fill=C["line"])
            if i < self.step:
                c.create_oval(2, y - 8, 18, y + 8, fill=C["green"], outline="")
                c.create_text(10, y, text="", font=("Segoe Fluent Icons", 7), fill="#FFFFFF")
                fg, fnt = C["sub"], F["body"]
            elif i == self.step:
                c.create_oval(2, y - 8, 18, y + 8, fill=C["card"], outline=C["accent"], width=2)
                c.create_oval(7, y - 3, 13, y + 3, fill=C["accent"], outline="")
                fg, fnt = C["text"], F["bodyb"]
            else:
                c.create_oval(2, y - 8, 18, y + 8, fill=C["bg"], outline=C["gray"])
                fg, fnt = C["faint"], F["body"]
            c.create_text(30, y, text=name, anchor="w", fill=fg, font=fnt)

    def _step_logic(self, s, nx, ny):
        now = time.time()
        if self.key == "neutral":
            # The headband blocks ~2.5 s while it averages and sends no data.
            # Wait for that to finish, then measure stability on FRESH samples only.
            if s.calibrating or now - self.cal_sent < 3.2:
                self._progress(min((now - self.cal_sent) / 3.2, 0.95))
                return
            if s.seq == getattr(self, "last_seq", None):
                return                                   # same packet again, not new data
            self.last_seq = s.seq
            self.samples.append((s.pitch, s.roll))
            self._progress(1.0)
            if len(self.samples) >= 30:
                noise = max(statistics.pstdev(p for p, _ in self.samples),
                            statistics.pstdev(r for _, r in self.samples))
                if noise > 1.5:
                    self.note.config(text="Readings are unstable. Tighten the headband and keep still.",
                                     fg=C["amber"])
                    self.samples = []
                    self._start_neutral("Readings are unstable. Please keep completely still.")
                else:
                    self.next_step()
            return

        if self.key in ("left", "right", "up", "down"):
            if s.seq == getattr(self, "last_seq", None):
                return                                   # only count fresh samples
            self.last_seq = s.seq
            value = s.roll if self.key in ("left", "right") else s.pitch
            if self.started is None:
                self._progress(0)
                if abs(value) > START_DEG:
                    self.started = now
                elif now - self.t0 > WAIT_S:
                    self.note.config(text="No movement detected. Move a little further.", fg=C["amber"])
                return
            if abs(value) > abs(self.extreme):
                self.extreme = value
            f = (now - self.started) / CAPTURE_S
            self._progress(f)
            if f >= 1:
                self.capture[self.key] = self.extreme
                self.ctrl.say("Got it. Back to straight.")
                self.note.config(text=f"Captured {abs(self.extreme):.0f}°. Back to straight.")
                self.after(900, self.next_step)
                self.started = float("inf")      # freeze until next step
            return

        if self.key == "check":
            for i, (tx, ty) in enumerate(TARGETS):
                if (nx - tx) ** 2 + (ny - ty) ** 2 < 0.25 ** 2 and i not in self.hit:
                    self.hit.add(i)
                    self.ctrl.say("Good")
            self._progress(len(self.hit) / len(TARGETS))
            if len(self.hit) == len(TARGETS):
                self.key = "done"
                self.after(500, self.next_step)
