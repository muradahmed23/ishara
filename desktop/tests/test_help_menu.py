"""Help menu ("help" -> numbered actions next to the cursor). Mouse, voice and speech are faked."""
import os
import sys
import time
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ishara import controller as ctl            # noqa: E402
from ishara.profiles import DEFAULT_COMMANDS    # noqa: E402
from ishara.voice import match_command          # noqa: E402


class FakeLink:
    state = "connected"
    def __init__(self, *a): pass
    def start(self): return self
    def data_alive(self): return True
    def latest(self): return None, 0
    def send(self, c): pass
    def set_model(self, *a, **k): pass
    def hid(self, a): return False


class Fake:
    def __init__(self, *a, **k):
        self.enabled, self.speaking, self.sleeping, self.level = True, False, False, 0.0
    def start(self): pass
    def stop(self): pass
    def set_mode(self, m): pass
    def set_commands(self, c): pass
    def say(self, text, then=None):
        if then:
            then()
    def set_voice(self, *a): pass
    def close(self): pass


class TestHelpMenu(unittest.TestCase):
    def setUp(self):
        self.calls = []
        self.cursor = [500, 400]
        scr = mock.MagicMock()
        scr.cursor_pos.side_effect = lambda: tuple(self.cursor)
        scr.monitor_rect.return_value = (0, 0, 1920, 1080)
        scr.at_edge.return_value = set()
        scr.set_cursor.side_effect = lambda x, y, r=None: self.calls.append(("move", x, y))
        for name in ("left_click", "right_click", "double_click", "left_down", "left_up"):
            getattr(scr, name).side_effect = (lambda n: lambda *a: self.calls.append((n, tuple(self.cursor))))(name)
        scr.scroll.side_effect = lambda n: self.calls.append(("scroll", n))
        patches = [mock.patch.object(ctl, "screen", scr), mock.patch.object(ctl, "BleLink", FakeLink),
                   mock.patch.object(ctl, "SimLink", FakeLink), mock.patch.object(ctl, "VoiceEngine", Fake),
                   mock.patch.object(ctl, "Speaker", Fake),
                   mock.patch.object(ctl.profiles, "save", lambda p: None)]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)
        self.c = ctl.Controller(simulate=True)
        self.c.settings["command_cooldown"] = 0.0
        self.c.settings["dwell_enabled"] = False
        self.c.paused = False

    def say(self, phrase):
        hit = match_command(phrase, self.c.settings["commands"])
        self.assertIsNotNone(hit, phrase)
        self.c.events.put(("command", hit))
        self.c._drain_events()

    def test_phrases_recognised(self):
        for p in ("help", "show commands", "what can i say", "three", "close", "more", "back"):
            self.assertIsNotNone(match_command(p, DEFAULT_COMMANDS), p)

    def test_open_and_choose_by_number(self):
        self.say("help")
        self.assertIsNotNone(self.c.menu)
        self.assertEqual(self.c.menu["anchor"], (500, 400))
        self.cursor[:] = [900, 900]                     # head moves away while reading the menu
        self.say("three")                                # 3 = right click
        self.assertIsNone(self.c.menu)                   # closes itself after choosing
        self.assertIn(("move", 500, 400), self.calls)    # back to where help was asked
        self.assertTrue(any(c[0] == "right_click" for c in self.calls))

    def test_close_by_voice(self):
        self.say("show commands")
        self.say("close")
        self.assertIsNone(self.c.menu)
        self.assertFalse(any(c[0] in ("left_click", "right_click") for c in self.calls))

    def test_menu_words_ignored_when_closed(self):
        self.say("three")
        self.say("close")
        self.assertEqual(self.calls, [])
        self.assertIsNone(self.c.last_action)

    def test_more_and_back(self):
        self.say("help")
        self.say("more")
        self.assertEqual(self.c.menu["page"], 1)
        self.assertEqual(self.c.menu["items"][0], "go_back")
        self.say("more")
        self.assertEqual(self.c.menu["page"], 2)
        self.say("more")                                  # last page: stays
        self.assertEqual(self.c.menu["page"], 2)
        self.say("back")
        self.assertEqual(self.c.menu["page"], 1)
        self.say("back")
        self.assertEqual(self.c.menu["page"], 0)

    def test_every_voice_action_is_in_help(self):
        from ishara import controller as ctl
        from ishara.profiles import DEFAULT_COMMANDS
        actions = {a for a in DEFAULT_COMMANDS.values()
                   if a != "help_menu" and not a.startswith("menu_")}
        self.assertEqual(actions - ctl.MENU_ALL, set())
        for page in ctl.MENU_PAGES:
            self.assertLessEqual(len(page), 8)            # numbers go to "eight"
            for a in page:
                self.assertIn(a, ctl.MENU_TEXT)

    def test_normal_command_acts_at_menu_spot(self):
        self.say("help")
        self.cursor[:] = [10, 10]
        self.say("double click")
        self.assertIsNone(self.c.menu)
        self.assertIn(("move", 500, 400), self.calls)

    def test_click_on_a_menu_row_is_a_plain_click(self):
        self.say("help")
        self.c.menu_rect = (518, 418, 766, 760)
        self.cursor[:] = [600, 500]                      # head moved onto a menu row
        self.say("click")
        self.assertIsNotNone(self.c.menu)                # the row's own handler decides
        self.assertNotIn(("move", 500, 400), self.calls)

    def test_timeout_closes(self):
        self.say("help")
        self.c.menu["until"] = time.time() - 1
        self.c.tick()
        self.assertIsNone(self.c.menu)

    def test_context_items(self):
        self.c.dragging = True
        self.say("help")
        self.assertIn("drag_release", self.c.menu["items"])
        self.assertNotIn("drag_start", self.c.menu["items"])


if __name__ == "__main__":
    unittest.main()
