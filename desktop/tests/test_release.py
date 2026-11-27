"""Updater decisions and model integrity checks."""
import json
import os
import tempfile
import unittest
from unittest import mock

from ishara import integrity, updates

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestUpdater(unittest.TestCase):
    def manifest(self, **kw):
        m = {"version": "2.1.0", "status": "released",
             "installer": {"url": "https://x/iShara-Setup-2.1.0.exe", "sha256": "AB" * 32, "sizeBytes": 5}}
        m.update(kw)
        return m

    def test_versions(self):
        self.assertTrue(updates.is_newer("2.1.0", "2.0.9"))
        self.assertTrue(updates.is_newer("10.0", "9.9.9"))
        self.assertFalse(updates.is_newer("2.0.0", "2.0.0"))
        self.assertFalse(updates.is_newer("1.9", "2.0.0"))

    def test_newer_release_is_offered(self):
        r = updates.evaluate(self.manifest(), current="2.0.0")
        self.assertEqual(r["state"], "available")
        self.assertEqual(r["sha256"], "ab" * 32)

    def test_unreleased_or_incomplete_never_offered(self):
        self.assertEqual(updates.evaluate(self.manifest(status="unreleased"), "2.0.0")["state"], "current")
        m = self.manifest(); m["installer"]["sha256"] = None
        self.assertEqual(updates.evaluate(m, "2.0.0")["state"], "current")

    def test_same_version_is_current(self):
        self.assertEqual(updates.evaluate(self.manifest(version="2.0.0"), "2.0.0")["state"], "current")

    def test_repo_manifest_is_valid_and_matches_app_version(self):
        with open(os.path.join(ROOT, "release", "latest.json"), encoding="utf-8") as f:
            m = json.load(f)
        from ishara import __version__
        self.assertEqual(m["version"], __version__)
        self.assertIn(m["status"], ("released", "unreleased"))
        if m["status"] == "released":
            self.assertTrue(m["installer"]["url"].startswith("https://"))
            self.assertEqual(len(m["installer"]["sha256"]), 64)


class TestIntegrity(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        os.makedirs(os.path.join(self.dir, "m"))
        with open(os.path.join(self.dir, "m", "model.bin"), "wb") as f:
            f.write(b"weights" * 100)
        integrity.write_manifest(self.dir)
        p = mock.patch.object(integrity, "CACHE", os.path.join(self.dir, "cache.json"))
        p.start(); self.addCleanup(p.stop)

    def test_intact(self):
        self.assertEqual(integrity.verify(self.dir, use_cache=False), (True, []))

    def test_damaged_and_missing(self):
        with open(os.path.join(self.dir, "m", "model.bin"), "ab") as f:
            f.write(b"x")
        ok, problems = integrity.verify(self.dir, use_cache=False)
        self.assertFalse(ok); self.assertIn("damaged: m/model.bin", problems)
        os.remove(os.path.join(self.dir, "m", "model.bin"))
        ok, problems = integrity.verify(self.dir, use_cache=False)
        self.assertIn("missing: m/model.bin", problems)
