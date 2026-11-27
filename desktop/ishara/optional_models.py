"""Optional speech models, downloaded from inside the app (onboarding or Settings → Voice).

The installer ships what everyone needs (voice commands + standard dictation). The large
best-accuracy dictation model is a separate, versioned GitHub Release asset:

    download -> %TEMP%\\<file>.part   (resumes if interrupted)
    verify   -> SHA-256 must match the catalog below; otherwise the file is deleted
    unpack   -> a temporary folder, then moved into %LOCALAPPDATA%\\Ishara\\models in one step,
                so a half-finished download can never look like an installed model
"""
import hashlib
import os
import shutil
import tempfile
import threading
import urllib.request
import zipfile

from . import __version__
from .paths import MODELS_DIR, USER_MODELS_DIR

# Model versions are pinned here (and listed in release/latest.json) so the app and the
# hosted files always match.
CATALOG = {
    "small.en": dict(
        title="Best accuracy dictation",
        folder="whisper-small.en",
        url="https://github.com/muradahmed23/ishara/releases/download/models-v1/whisper-small.en.zip",
        sha256="cd925ca19ece2202c2dce4dfbeb2b92c92680d9bb9a6d99fd521e5f90944f13c",
        size=486099480,
    ),
}
UA = {"User-Agent": f"iShara/{__version__}"}


def installed(name):
    """Downloaded into the user folder, or already shipped next to the app (developer copy)."""
    folder = CATALOG[name]["folder"]
    return any(os.path.isfile(os.path.join(root, folder, "model.bin")) for root in (USER_MODELS_DIR, MODELS_DIR))


class ModelDownloader:
    """One background download at a time; the UI polls .status."""

    def __init__(self):
        self.status = {name: dict(state="installed" if installed(name) else "available", progress=0.0, error="")
                       for name in CATALOG}
        self._lock = threading.Lock()
        self._busy = False
        self.on_done = None          # callback(name) after a successful install

    def _set(self, name, **kw):
        with self._lock:
            self.status[name] = {**self.status[name], **kw}

    def start(self, name):
        if name not in CATALOG or self._busy or installed(name):
            return False
        self._busy = True
        threading.Thread(target=self._run, args=(name,), daemon=True, name="model-download").start()
        return True

    def _run(self, name):
        item = CATALOG[name]
        part = os.path.join(tempfile.gettempdir(), os.path.basename(item["url"]) + ".part")
        try:
            self._set(name, state="downloading", progress=0.0, error="")
            have = os.path.getsize(part) if os.path.exists(part) else 0
            if have > item["size"]:
                os.remove(part); have = 0
            if have < item["size"]:
                headers = dict(UA, **({"Range": f"bytes={have}-"} if have else {}))
                with urllib.request.urlopen(urllib.request.Request(item["url"], headers=headers), timeout=30) as r:
                    if have and r.status != 206:        # server ignored the range: start over
                        have = 0
                    with open(part, "ab" if have else "wb") as f:
                        done = have
                        for block in iter(lambda: r.read(1 << 20), b""):
                            f.write(block)
                            done += len(block)
                            self._set(name, progress=min(done / item["size"], 1.0))
            self._set(name, state="verifying")
            h = hashlib.sha256()
            with open(part, "rb") as f:
                for block in iter(lambda: f.read(1 << 20), b""):
                    h.update(block)
            if h.hexdigest() != item["sha256"]:
                os.remove(part)
                self._set(name, state="error", error="The download was damaged and has been deleted. Please try again.")
                return
            self._set(name, state="installing")
            os.makedirs(USER_MODELS_DIR, exist_ok=True)
            staging = tempfile.mkdtemp(prefix="ishara-model-", dir=USER_MODELS_DIR)
            try:
                with zipfile.ZipFile(part) as z:
                    for m in z.namelist():                 # refuse paths that escape the folder
                        if m.startswith(("/", "\\")) or ".." in m.replace("\\", "/").split("/"):
                            raise ValueError("unsafe path in archive")
                    z.extractall(staging)
                target = os.path.join(USER_MODELS_DIR, item["folder"])
                if os.path.isdir(target):
                    shutil.rmtree(target)
                os.replace(os.path.join(staging, item["folder"]), target)
            finally:
                shutil.rmtree(staging, ignore_errors=True)
            os.remove(part)
            self._set(name, state="installed", progress=1.0)
            if self.on_done:
                self.on_done(name)
        except Exception as e:
            self._set(name, state="error",
                      error=f"Download interrupted ({type(e).__name__}). Press Download again to continue where it stopped.")
        finally:
            self._busy = False
