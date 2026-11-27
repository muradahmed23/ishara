"""Unit tests for the parts that must be exactly right. Run:  python -m unittest -v"""
import os
import random
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ishara import model as pm                                    # noqa: E402
from ishara import protocol, screen                               # noqa: E402
from ishara.protocol import DEFAULT_MODEL, Sample                 # noqa: E402
from ishara.profiles import DEFAULT_COMMANDS                      # noqa: E402
from ishara.voice import apply_punctuation, match_command         # noqa: E402

RESOLUTIONS = [(1366, 768), (1920, 1080), (2560, 1440), (3840, 2160), (1280, 1024)]


class TestBoundary(unittest.TestCase):
    def test_clamp_never_leaves_screen(self):
        for w, h in RESOLUTIONS:
            rect = (0, 0, w, h)
            for _ in range(2000):
                x = random.uniform(-1e6, 1e6)
                y = random.uniform(-1e6, 1e6)
                cx, cy = screen.clamp_point(x, y, rect)
                self.assertTrue(0 <= cx <= w - 1 and 0 <= cy <= h - 1)

    def test_corners_reachable(self):
        rect = (0, 0, 1920, 1080)
        self.assertEqual(screen.clamp_point(-50, -50, rect), (0, 0))
        self.assertEqual(screen.clamp_point(5000, -1, rect), (1919, 0))
        self.assertEqual(screen.clamp_point(-1, 5000, rect), (0, 1079))
        self.assertEqual(screen.clamp_point(1e9, 1e9, rect), (1919, 1079))

    def test_second_monitor_offsets(self):
        rect = (-1920, 0, 0, 1080)               # monitor left of the primary
        self.assertEqual(screen.clamp_point(100, 500, rect), (-1, 500))
        self.assertEqual(screen.clamp_point(-5000, -5, rect), (-1920, 0))

    def test_edges(self):
        rect = (0, 0, 1920, 1080)
        self.assertEqual(screen.at_edge(0, 0, rect), {"left", "top"})
        self.assertEqual(screen.at_edge(1919, 1079, rect), {"right", "bottom"})
        self.assertEqual(screen.at_edge(500, 500, rect), set())


class TestModel(unittest.TestCase):
    m = dict(DEFAULT_MODEL)

    def test_dead_zone(self):
        # each side has its own range, so the dead zone is per side
        m = self.m
        self.assertEqual(pm.compute_move(0, m["rR"] * m["dz"] * 0.9, m), (0, 0))
        self.assertEqual(pm.compute_move(0, -m["rL"] * m["dz"] * 0.9, m), (0, 0))
        self.assertEqual(pm.compute_move(m["rU"] * m["dz"] * 0.9, 0, m), (0, 0))
        self.assertEqual(pm.compute_move(-m["rD"] * m["dz"] * 0.9, 0, m), (0, 0))
        self.assertNotEqual(pm.compute_move(-m["rD"] * m["dz"] * 1.2, 0, m), (0, 0))

    def test_directions(self):
        dx, _ = pm.compute_move(0, 12, self.m)
        self.assertGreater(dx, 0)                 # right tilt -> right
        _, dy = pm.compute_move(12, 0, self.m)
        self.assertLess(dy, 0)                    # chin up -> screen up
        dx, dy = pm.compute_move(10, -10, self.m)
        self.assertTrue(dx < 0 and dy < 0)        # diagonal

    def test_speed_capped_for_extreme_values(self):
        for tilt in (30, 60, 179, 1e6):
            dx, dy = pm.compute_move(tilt, tilt, self.m)
            self.assertLessEqual(abs(dx), self.m["sx"])
            self.assertLessEqual(abs(dy), self.m["sy"])

    def test_monotonic(self):
        prev = 0
        for t in range(0, 40):
            dx, _ = pm.compute_move(0, t, self.m)
            self.assertGreaterEqual(dx, prev)
            prev = dx

    def test_indicator_matches_cursor(self):
        """The dot and the cursor must agree on direction, for every mounting."""
        for ix in (0, 1):
            for iy in (0, 1):
                m = dict(self.m, ix=ix, iy=iy)
                for p, r in [(14, 0), (-14, 0), (0, 14), (0, -14), (10, 10)]:
                    dx, dy = pm.compute_move(p, r, m)
                    nx, ny = pm.normalized(p, r, m)
                    if dx:
                        self.assertEqual(dx > 0, nx > 0)
                    if dy:
                        self.assertEqual(dy > 0, ny > 0)

    def test_capture_personal_ranges(self):
        m = pm.ranges_from_capture(left=-20, right=25, up=18, down=-10, model=self.m)
        self.assertEqual((m["ix"], m["iy"]), (0, 0))
        self.assertAlmostEqual(m["rR"], 25 * pm.COMFORT)
        self.assertAlmostEqual(m["rL"], 20 * pm.COMFORT)
        self.assertAlmostEqual(m["rD"], 10 * pm.COMFORT)

    def test_capture_detects_reversed_mounting(self):
        m = pm.ranges_from_capture(left=20, right=-20, up=-15, down=12, model=self.m)
        self.assertEqual((m["ix"], m["iy"]), (1, 1))
        # after calibration, tilting LEFT (positive roll here) must move the cursor left
        dx, _ = pm.compute_move(0, 18, m)
        self.assertLess(dx, 0)
        _, dy = pm.compute_move(-14, 0, m)        # looking up gives negative pitch here
        self.assertLess(dy, 0)

    def test_full_range_reaches_max_speed(self):
        m = pm.ranges_from_capture(-20, 20, 15, -15, self.m)
        dx, _ = pm.compute_move(0, m["rR"], m)
        self.assertEqual(dx, round(m["sx"]))

    def test_tiny_capture_is_limited_and_reported(self):
        m = pm.ranges_from_capture(-1, 1, 1, -1, self.m)
        self.assertGreaterEqual(m["rL"], pm.MIN_RANGE)
        self.assertTrue(pm.capture_quality(-1, 1, 1, -1))


class TestProtocol(unittest.TestCase):
    def test_roundtrip(self):
        s = Sample(-12.34, 56.78, 12.3, -5, 7, True, False, True, 200)
        t = protocol.unpack_sample(protocol.pack_sample(s))
        self.assertAlmostEqual(t.pitch, -12.34, places=2)
        self.assertAlmostEqual(t.roll, 56.78, places=2)
        self.assertEqual((t.dx, t.dy, t.paused, t.calibrating, t.sensor_ok, t.seq), (-5, 7, True, False, True, 200))

    def test_bad_packet(self):
        with self.assertRaises(ValueError):
            protocol.unpack_sample(b"\x00\x01")

    def test_neutral_never_sent_by_default(self):
        # regression: the app overwrote the headband's neutral with 0/0
        text = protocol.model_to_text(dict(DEFAULT_MODEL, p0=-40, r0=29))
        self.assertNotIn("p0=", text)
        self.assertNotIn("r0=", text)
        self.assertIn("p0=", protocol.model_to_text(DEFAULT_MODEL, include_neutral=True))

    def test_model_text_clamps(self):
        m = protocol.text_to_model("rL=999,dz=-1,sx=abc,ix=1,junk")
        self.assertEqual(m["rL"], 60)
        self.assertEqual(m["dz"], 0.05)
        self.assertEqual(m["sx"], DEFAULT_MODEL["sx"])
        self.assertEqual(m["ix"], 1)
        self.assertEqual(protocol.text_to_model(protocol.model_to_text(m)), m)


class TestVoice(unittest.TestCase):
    def test_commands(self):
        self.assertEqual(match_command("right click", DEFAULT_COMMANDS), ("right click", "right_click"))
        self.assertEqual(match_command("click", DEFAULT_COMMANDS)[1], "left_click")
        self.assertEqual(match_command("please double click", DEFAULT_COMMANDS)[1], "double_click")
        self.assertIsNone(match_command("[unk]", DEFAULT_COMMANDS))
        self.assertIsNone(match_command("hello there", DEFAULT_COMMANDS))
        # microphone on/off by voice
        self.assertEqual(match_command("mute microphone", DEFAULT_COMMANDS)[1], "mic_sleep")
        self.assertEqual(match_command("stop listening", DEFAULT_COMMANDS)[1], "mic_sleep")
        self.assertEqual(match_command("start listening", DEFAULT_COMMANDS)[1], "mic_wake")
        self.assertEqual(match_command("unmute microphone", DEFAULT_COMMANDS)[1], "mic_wake")
        # "start typing" must not be confused with "start listening" or "start drag"
        self.assertEqual(match_command("start typing", DEFAULT_COMMANDS)[1], "dictation_on")

    def test_punctuation(self):
        self.assertEqual(apply_punctuation("hello comma world period"), "hello, world.")
        # Whisper style output (capitals + its own punctuation)
        self.assertEqual(apply_punctuation("Hello comma world. Period."), "Hello, world.")
        self.assertEqual(apply_punctuation("first line new line second"), "first line\nsecond")

    def test_stop_phrase_tolerant(self):
        from ishara.voice import split_at_stop
        self.assertEqual(split_at_stop("I am done. Stop typing.", "stop typing"), ("I am done.", True))
        self.assertEqual(split_at_stop("stop typing", "stop typing"), ("", True))
        self.assertEqual(split_at_stop("keep going", "stop typing"), ("keep going", False))


class TestWhisperDictation(unittest.TestCase):
    """End-to-end: real audio -> Whisper -> typed text, then leaves dictation mode."""

    @unittest.skipUnless(__import__("ishara.voice", fromlist=["x"]).whisper_available("base.en"),
                         "Whisper model not installed")
    def test_sentence_then_stop(self):
        import queue as q
        import subprocess
        import tempfile
        import wave
        from ishara.voice import WhisperWorker
        wav = os.path.join(tempfile.gettempdir(), "ishara_test.wav")
        ps = ("Add-Type -AssemblyName System.Speech;"
              "$s=New-Object System.Speech.Synthesis.SpeechSynthesizer;"
              "$f=New-Object System.Speech.AudioFormat.SpeechAudioFormatInfo 16000,"
              "([System.Speech.AudioFormat.AudioBitsPerSample]::Sixteen),"
              "([System.Speech.AudioFormat.AudioChannel]::Mono);"
              f"$s.SetOutputToWaveFile('{wav}',$f);"
              "$s.Speak('My name is Ishara, comma, and I can type. Stop typing.');$s.Dispose()")
        subprocess.run(["powershell", "-NoProfile", "-Command", ps], check=True, timeout=60)
        with wave.open(wav) as w:
            audio = w.readframes(w.getnframes())
        events = q.Queue()
        worker = WhisperWorker("base.en", lambda k, p: events.put((k, p)))
        self.assertTrue(worker.ready.wait(60))
        worker.submit(audio, "my name is ishara comma and i can type stop typing", "stop typing", True)
        got = {}
        while "command" not in got:
            k, p = events.get(timeout=60)
            got[k] = p
        typed = got.get("dictation", "")
        self.assertIn("ishara", typed.lower())
        self.assertNotIn("stop", typed.lower())          # stop phrase never typed
        self.assertEqual(got["command"][1], "dictation_off")


if __name__ == "__main__":
    unittest.main()


class TestAxisDetection(unittest.TestCase):
    def test_swapped_and_reversed_mount(self):
        from ishara import model as pm
        from ishara.protocol import DEFAULT_MODEL
        # forehead mount: side tilt shows on PITCH (reversed), nod on ROLL (reversed)
        cap = {"left": (18, 2), "right": (-20, -1), "up": (1, -15), "down": (-2, 12)}
        sw, l, r, u, d = pm.axes_from_capture(cap)
        self.assertEqual(sw, 1)
        m = pm.ranges_from_capture(l, r, u, d, DEFAULT_MODEL)
        m["sw"] = sw
        # firmware swaps first, then the user's real movements must go the right way
        def move(pitch_raw, roll_raw):
            p, rr = (roll_raw, pitch_raw) if m["sw"] else (pitch_raw, roll_raw)
            return pm.compute_move(p, rr, m)
        self.assertLess(move(*cap["left"])[0], 0)    # tilt left  -> cursor left
        self.assertGreater(move(*cap["right"])[0], 0)
        self.assertLess(move(*cap["up"])[1], 0)      # look up    -> cursor up
        self.assertGreater(move(*cap["down"])[1], 0)
        self.assertEqual(pm.axes_quality(cap, sw), [])

    def test_normal_mount(self):
        from ishara import model as pm
        cap = {"left": (1, -18), "right": (0, 20), "up": (15, 1), "down": (-12, 0)}
        self.assertEqual(pm.axes_from_capture(cap)[0], 0)


class TestCalibrationCancel(unittest.TestCase):
    def test_cancel_stops_pending_actions(self):
        from ishara.calib import CalibrationSession
        sent, spoken = [], []

        class Link:
            def send(self, c): sent.append(c)
            def set_model(self, m, save=True): sent.append("SET")
            def latest(self): return None, None
            def data_alive(self): return False

        class Ctrl:
            model = {"ix": 0, "iy": 0, "sw": 0, "dz": 0.22}
            link = Link()
            def say(self, text, then=None): spoken.append(then)

        s = CalibrationSession(Ctrl())
        s.cancel()
        for fn in spoken:          # speech finishes after the cancel
            if fn: fn()
        self.assertNotIn("CAL", sent)
        self.assertFalse(s.active)


class TestCalibrationSteps(unittest.TestCase):
    def _session(self):
        from unittest import mock
        from ishara import calib
        from ishara.protocol import Sample
        st = {"t": 1000.0, "s": None, "seq": 0}
        said = []

        class Link:
            def send(self, c): pass
            def set_model(self, m, save=True): pass
            def latest(self): return st["s"], None
            def data_alive(self): return True

        class Ctrl:
            model = {"ix": 0, "iy": 0, "sw": 0, "dz": 0.22, "rU": 15, "rD": 12, "rL": 15, "rR": 15}
            link = Link()
            def say(self, text, then=None): said.append(text)

        patcher = mock.patch.object(calib.time, "time", lambda: st["t"])
        patcher.start()
        self.addCleanup(patcher.stop)
        s = calib.CalibrationSession(Ctrl())
        s.step, s.key = 0, "neutral"
        s._next()                                   # -> "left"

        def feed(pitch, roll, secs):
            for _ in range(int(secs * 30)):
                st["t"] += 1 / 30
                st["seq"] = (st["seq"] + 1) % 256
                st["s"] = Sample(pitch, roll, 0, 0, 0, True, False, True, st["seq"])
                s.tick()
        return s, feed, said

    def test_waits_for_center_and_new_direction(self):
        s, feed, said = self._session()
        feed(0, -15, 2.0)               # left step: user is not centered yet...
        self.assertEqual(s.key, "left")
        feed(0, 0, 0.5)                 # back to straight
        feed(0, -15, 2.0)               # tilt left and hold
        feed(0, 0, 1.0)                 # (scheduled move to next step)
        self.assertEqual(s.key, "right")
        self.assertIn("left", s.capture)
        feed(0, -15, 3.0)               # still tilted LEFT during the RIGHT step
        self.assertNotIn("right", s.capture)   # must NOT say "got it"
        feed(0, 0, 0.5)
        feed(0, 5, 0.3); feed(0, 10, 0.3); feed(0, 14, 0.3)   # still moving: no capture
        self.assertNotIn("right", s.capture)
        feed(0, 14, 1.5)                # hold at the limit
        self.assertAlmostEqual(s.capture["right"][1], 14)
