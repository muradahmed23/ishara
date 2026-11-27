"""Calibration session - the guided flow as pure logic (no UI).

Look straight -> Left -> Right -> Up -> Down -> Check -> Complete.
Neutral is averaged ON the headband (CAL command). The movement range is
captured from the live stream, turned into a personal model
(model.ranges_from_capture), tried during "Check", then saved on the headband
and in the profile. Mouse movement is paused for the whole flow.

tick() is called ~30x per second; state() is what the UI displays.
"""
import statistics
import time

from . import model as pm

HOLD_S = 1.0             # hold still at your limit this long to capture
MIN_DEG = 6.0            # a movement must reach at least this far
CENTER_DEG = 3.5         # "back to straight" = within this of neutral
STEADY_DEG = 1.5         # held still = moves less than this during HOLD_S
DISTINCT_COS = 0.5       # new direction must be > 60 deg from earlier ones
WAIT_S = 12.0            # hint after this long without movement
NEUTRAL_WAIT_S = 3.2     # headband averages ~2.5 s and sends nothing meanwhile

STEPS = [
    ("neutral", "Look straight", "Look at the middle of the screen and keep still."),
    ("left", "Tilt left", "Slowly tilt your head toward your left shoulder, as far as is comfortable, and hold."),
    ("right", "Tilt right", "Now tilt toward your right shoulder, as far as is comfortable, and hold."),
    ("up", "Look up", "Lift your chin and look up, as far as is comfortable, and hold."),
    ("down", "Look down", "Lower your chin and look down, as far as is comfortable, and hold."),
    ("check", "Try it", "Move the dot into each circle. This is how your cursor will feel."),
]
SPOKEN = {
    "left": "Tilt your head to your left shoulder, and hold.",
    "right": "Now tilt to your right shoulder, and hold.",
    "up": "Look up, and hold.",
    "down": "Look down, and hold.",
    "check": "Now move the dot into each circle.",
}
TARGETS = [(0, -0.75), (0.75, 0), (0, 0.75), (-0.75, 0)]


class CalibrationSession:
    def __init__(self, ctrl):
        self.ctrl = ctrl
        self.prev_model = dict(ctrl.model)
        self.active = True
        self.done = False
        self.capture = {}
        self.new_model = None
        self.step = -1
        self.note, self.note_kind = "", "info"
        self.progress = 0.0
        self.issues = []
        self._later = None                  # (time, fn) - small scheduler
        ctrl.link.send("PAUSE")
        self._raw_stream()
        self._next()

    def _raw_stream(self):
        """Measure with no swap/invert so the real mounting can be detected."""
        raw = dict(self.prev_model, ix=0, iy=0, sw=0)
        self.raw_model = raw
        self.ctrl.link.set_model(raw, save=False)

    # ------------------------------------------------------------ flow
    def _next(self):
        self.step += 1
        self.note, self.note_kind, self.progress = "", "info", 0.0
        if self.step >= len(STEPS):
            return self._complete()
        self.key = STEPS[self.step][0]
        self.t0, self.started, self.extreme, self.hit = time.time(), None, 0.0, set()
        self.extreme_pr = (0.0, 0.0)
        self.centered = False            # must return to straight before each step
        self.hold = []                   # (time, pitch, roll) while holding
        self.samples, self.last_seq = [], None
        if self.key == "neutral":
            self.note = "Follow the spoken instructions."
            self._start_neutral("Look straight at the screen and keep still.")
        else:
            self.ctrl.say(SPOKEN[self.key])
        if self.key == "check":
            sw, left, right, up, down = pm.axes_from_capture(self.capture)
            m = pm.ranges_from_capture(left, right, up, down, self.prev_model)
            m["sw"] = sw
            self.new_model = pm.clamp_model(m)
            self.ctrl.link.set_model(self.new_model, save=False)          # try before saving
            self.issues = pm.axes_quality(self.capture, sw) + pm.capture_quality(left, right, up, down)
            if self.issues:
                self.note, self.note_kind = " ".join(self.issues), "warn"

    def _start_neutral(self, sentence):
        """Speak first, THEN measure, so the user is already still."""
        self.cal_sent = float("inf")

        def go():
            if not self.active or self.done:          # cancelled while speaking
                return
            self.ctrl.link.send("CAL")
            self.cal_sent = time.time()
        self.ctrl.say(sentence, then=go)

    def _complete(self):
        self.key, self.done, self.progress = "complete", True, 1.0
        self.ctrl.set_model(self.new_model, save=True)
        self.ctrl.settings["calibrated"] = True
        self.ctrl.save_profile()
        self.ctrl.link.send("RESUME")
        self.ctrl.say("Calibration complete. You can use the mouse now.")

    def restart(self):
        self._later = None
        self._raw_stream()
        self.capture, self.step, self.done = {}, -1, False
        self._next()

    def skip_check(self):
        if self.key == "check":
            self._next()

    def cancel(self):
        self._later = None
        if not self.done:
            self.ctrl.link.set_model(self.prev_model, save=False)
            self.ctrl.link.send("RESUME")
        self.active = False

    def finish(self):
        self.active = False

    # ------------------------------------------------------------ live
    def view(self):
        """(nx, ny) of the dot, using the model being tried during Check."""
        s, _ = self.ctrl.link.latest()
        if not s or not self.ctrl.link.data_alive():
            return None
        m = self.new_model if self.key in ("check", "complete") and self.new_model else self.raw_model
        return pm.normalized(s.pitch, s.roll, m)

    def tick(self):
        if not self.active:
            return
        now = time.time()
        if self._later and now >= self._later[0]:
            fn, self._later = self._later[1], None
            fn()
        if self.done:
            return
        s, _ = self.ctrl.link.latest()
        if not s or not self.ctrl.link.data_alive():
            self.note, self.note_kind = "Waiting for the headband — make sure it is on and connected.", "warn"
            return
        if self.note.startswith("Waiting for the headband"):
            self.note, self.note_kind = "", "info"
        v = self.view()
        nx, ny = v if v else (0, 0)

        if self.key == "neutral":
            if s.calibrating or now - self.cal_sent < NEUTRAL_WAIT_S:
                self.progress = max(0.0, min((now - self.cal_sent) / NEUTRAL_WAIT_S, 0.95))
                return
            if s.seq == self.last_seq:
                return                                     # same packet again
            self.last_seq = s.seq
            self.samples.append((s.pitch, s.roll))
            self.progress = 1.0
            if len(self.samples) >= 30:
                noise = max(statistics.pstdev(p for p, _ in self.samples),
                            statistics.pstdev(r for _, r in self.samples))
                if noise > 1.5:
                    self.note, self.note_kind = "Readings are unstable. Tighten the headband and keep still.", "warn"
                    self.samples = []
                    self._start_neutral("Readings are unstable. Please keep completely still.")
                else:
                    self._next()
            return

        if self.key in ("left", "right", "up", "down"):
            if s.seq == self.last_seq:
                return
            self.last_seq = s.seq
            # record BOTH axes: the mounting decides which one this movement uses
            value = (s.pitch ** 2 + s.roll ** 2) ** 0.5
            if self.started == float("inf"):
                return                                     # captured, waiting for next step
            # 1) wait until the head is back to straight
            if not self.centered:
                self.progress = 0.0
                if value < CENTER_DEG:
                    self.centered = True
                    self.note, self.note_kind = "", "info"
                elif now - self.t0 > 2.0:
                    self.note, self.note_kind = "First come back to straight.", "info"
                return
            # 2) movement must be big enough and in a NEW direction
            new_dir = value >= MIN_DEG and self._distinct(s.pitch, s.roll)
            if value > self.extreme and new_dir:
                self.extreme, self.extreme_pr = value, (s.pitch, s.roll)
            if not new_dir:
                self.hold = []
                self.progress = min(value / MIN_DEG, 1.0) * 0.3 if value < MIN_DEG else 0.0
                if value >= MIN_DEG:
                    self.note, self.note_kind = "That looks like an earlier direction. Follow the instruction.", "warn"
                elif now - self.t0 > WAIT_S:
                    self.note, self.note_kind = "No movement yet. Move a little further.", "warn"
                return
            self.note, self.note_kind = "Hold it there...", "info"
            # 3) capture only after holding still at the limit
            # self.hold = [start_time, anchor_pitch, anchor_roll]
            if not self.hold or ((s.pitch - self.hold[1]) ** 2 + (s.roll - self.hold[2]) ** 2) ** 0.5 > STEADY_DEG:
                self.hold = [now, s.pitch, s.roll]         # (re)start: still moving
            span = now - self.hold[0]
            self.progress = 0.3 + 0.7 * min(span / HOLD_S, 1.0)
            if span >= HOLD_S:
                self.capture[self.key] = self.extreme_pr
                self.ctrl.say("Got it. Back to straight.")
                self.note = f"Captured {self.extreme:.0f}°. Back to straight."
                self.started = float("inf")
                self._later = (now + 0.9, self._next)
            return

        if self.key == "check":
            for i, (tx, ty) in enumerate(TARGETS):
                if (nx - tx) ** 2 + (ny - ty) ** 2 < 0.25 ** 2 and i not in self.hit:
                    self.hit.add(i)
                    self.ctrl.say("Good")
            self.progress = len(self.hit) / len(TARGETS)
            if len(self.hit) == len(TARGETS) and not self._later:
                self._later = (now + 0.5, self._next)

    def _distinct(self, pitch, roll):
        """True if (pitch, roll) points away from every earlier captured direction."""
        n = (pitch ** 2 + roll ** 2) ** 0.5
        for cp, cr in self.capture.values():
            m = (cp ** 2 + cr ** 2) ** 0.5
            if m > 0 and (pitch * cp + roll * cr) / (n * m) > DISTINCT_COS:
                return False
        return True

    def state(self):
        r = self.new_model
        ranges = None
        if r:
            left, right = (r["rL"], r["rR"]) if not r["ix"] else (r["rR"], r["rL"])
            ranges = dict(left=round(left), right=round(right), up=round(r["rU"]), down=round(r["rD"]))
        title, hint = (("Calibration complete", "Your settings are saved on the headband and in this profile.")
                       if self.done else STEPS[self.step][1:])
        v = self.view()
        return dict(active=self.active, done=self.done, step=self.step, steps=[s[1] for s in STEPS],
                    key=self.key, title=title, hint=hint, progress=round(self.progress, 3),
                    note=self.note, note_kind=self.note_kind, ranges=ranges,
                    targets=TARGETS if self.key == "check" else [], hit=sorted(self.hit),
                    dot=list(v) if v else None,
                    dz=(self.new_model or self.ctrl.model)["dz"])
