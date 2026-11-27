"""Optional model download: verify, install atomically, resume, refuse bad archives."""
import hashlib
import io
import os
import tempfile
import time
import unittest
import zipfile
from unittest import mock

from ishara import optional_models as om


def make_zip(files):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        for name, data in files.items():
            z.writestr(name, data)
    return buf.getvalue()


class FakeResp(io.BytesIO):
    def __init__(self, data, status=200):
        super().__init__(data)
        self.status = status
        self.headers = {"Content-Length": str(len(data))}
    def __enter__(self): return self
    def __exit__(self, *a): self.close()


class TestOptionalModels(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.models = os.path.join(self.tmp, "models")
        self.temp = os.path.join(self.tmp, "temp"); os.makedirs(self.temp)
        for p in (mock.patch.object(om, "USER_MODELS_DIR", self.models),
                  mock.patch.object(om, "MODELS_DIR", os.path.join(self.tmp, "bundled")),
                  mock.patch.object(om.tempfile, "gettempdir", lambda: self.temp)):
            p.start(); self.addCleanup(p.stop)

    def catalog(self, data, sha=None):
        item = dict(title="t", folder="whisper-small.en", url="https://x/whisper-small.en.zip",
                    sha256=sha or hashlib.sha256(data).hexdigest(), size=len(data))
        p = mock.patch.dict(om.CATALOG, {"small.en": item}); p.start(); self.addCleanup(p.stop)

    def run_download(self, opener):
        d = om.ModelDownloader()
        with mock.patch.object(om.urllib.request, "urlopen", opener):
            self.assertTrue(d.start("small.en"))
            for _ in range(200):
                if not d._busy: break
                time.sleep(0.02)
        return d.status["small.en"]

    def test_good_download_installs(self):
        data = make_zip({"whisper-small.en/model.bin": b"w" * 5000, "whisper-small.en/config.json": b"{}"})
        self.catalog(data)
        st = self.run_download(lambda req, timeout: FakeResp(data))
        self.assertEqual(st["state"], "installed")
        self.assertTrue(om.installed("small.en"))
        self.assertEqual(os.listdir(self.models), ["whisper-small.en"])         # no staging left behind
        self.assertEqual(os.listdir(self.temp), [])                            # .part removed

    def test_damaged_download_is_deleted_not_installed(self):
        data = make_zip({"whisper-small.en/model.bin": b"w" * 5000})
        self.catalog(data, sha="0" * 64)
        st = self.run_download(lambda req, timeout: FakeResp(data))
        self.assertEqual(st["state"], "error")
        self.assertFalse(om.installed("small.en"))
        self.assertEqual(os.listdir(self.temp), [])

    def test_unsafe_archive_refused(self):
        data = make_zip({"../evil.txt": b"x", "whisper-small.en/model.bin": b"w"})
        self.catalog(data)
        st = self.run_download(lambda req, timeout: FakeResp(data))
        self.assertEqual(st["state"], "error")
        self.assertFalse(os.path.exists(os.path.join(self.tmp, "evil.txt")))
        self.assertFalse(om.installed("small.en"))

    def test_resume_after_interruption(self):
        data = make_zip({"whisper-small.en/model.bin": b"w" * 20000})
        self.catalog(data)
        with open(os.path.join(self.temp, "whisper-small.en.zip.part"), "wb") as f:
            f.write(data[:7000])                                               # earlier attempt stopped here
        seen = {}
        def opener(req, timeout):
            seen["range"] = req.headers.get("Range")
            return FakeResp(data[7000:], status=206)
        st = self.run_download(opener)
        self.assertEqual(seen["range"], "bytes=7000-")
        self.assertEqual(st["state"], "installed")
