"""Check for, download and start iShara updates.

The release manifest (release/latest.json in the repository) is the single source of
truth, shared with the website. Updates are full versioned installers:

    check()     -> reads the manifest, compares versions
    download()  -> fetches the installer to %TEMP% (resumes interrupted downloads),
                   verifies SHA-256; a file that doesn't match is deleted, never run
    install()   -> starts the verified installer; Windows shows its normal prompts.
                   The installer upgrades in place and never touches %APPDATA%/Ishara,
                   so profiles and calibration are kept.
"""
import hashlib
import json
import os
import subprocess
import tempfile
import threading
import urllib.request

from . import __version__

MANIFEST_URL = "https://raw.githubusercontent.com/muradahmed23/ishara/main/release/latest.json"
TIMEOUT_S = 8
UA = {"User-Agent": f"iShara/{__version__}"}


def parse_version(v):
    out = []
    for part in str(v).split("."):
        num = "".join(ch for ch in part if ch.isdigit())
        out.append(int(num) if num else 0)
    return tuple(out + [0] * (3 - len(out)))


def is_newer(latest, current=__version__):
    return parse_version(latest) > parse_version(current)


def fetch_manifest(url=MANIFEST_URL):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=TIMEOUT_S) as r:
        return json.loads(r.read().decode("utf-8"))


def evaluate(manifest, current=__version__):
    """Turn a manifest into what the UI shows. Pure function (unit-tested)."""
    inst = manifest.get("installer") or {}
    released = manifest.get("status") == "released" and inst.get("url") and inst.get("sha256")
    latest = manifest.get("version", "0")
    if released and is_newer(latest, current):
        return dict(state="available", current=current, latest=latest, size=inst.get("sizeBytes"),
                    notes=manifest.get("notes", []), url=inst["url"], sha256=inst["sha256"].lower(),
                    file=inst.get("file") or f"iShara-Setup-{latest}.exe")
    return dict(state="current", current=current, latest=latest if released else current)


class Updater:
    """Runs check / download in the background; the UI polls .status."""

    def __init__(self):
        self.status = dict(state="idle", current=__version__)
        self._lock = threading.Lock()
        self.installer_path = None

    def _set(self, **kw):
        with self._lock:
            self.status = {**self.status, **kw}

    def check(self):
        def run():
            self._set(state="checking", error="")
            try:
                self._set(**evaluate(fetch_manifest()))
            except Exception as e:
                self._set(state="error", error=f"Could not check for updates ({type(e).__name__}). Check the internet connection.")
        threading.Thread(target=run, daemon=True, name="update-check").start()

    def download(self):
        st = dict(self.status)
        if st.get("state") != "available":
            return

        def run():
            path = os.path.join(tempfile.gettempdir(), st["file"])
            part = path + ".part"
            try:
                self._set(state="downloading", progress=0.0, error="")
                have = os.path.getsize(part) if os.path.exists(part) else 0
                headers = dict(UA, **({"Range": f"bytes={have}-"} if have else {}))
                req = urllib.request.Request(st["url"], headers=headers)
                with urllib.request.urlopen(req, timeout=30) as r:
                    if have and r.status != 206:       # server ignored the range: start over
                        have = 0
                    total = have + int(r.headers.get("Content-Length") or 0)
                    with open(part, "ab" if have else "wb") as f:
                        done = have
                        for block in iter(lambda: r.read(1 << 20), b""):
                            f.write(block)
                            done += len(block)
                            if total:
                                self._set(progress=done / total)
                self._set(state="verifying")
                h = hashlib.sha256()
                with open(part, "rb") as f:
                    for block in iter(lambda: f.read(1 << 20), b""):
                        h.update(block)
                if h.hexdigest() != st["sha256"]:
                    os.remove(part)
                    self._set(state="error", error="The download was damaged and has been deleted. Please try again.")
                    return
                os.replace(part, path)
                self.installer_path = path
                self._set(state="ready", progress=1.0)
            except Exception as e:
                self._set(state="error", error=f"Download interrupted ({type(e).__name__}). Try again to resume.")
        threading.Thread(target=run, daemon=True, name="update-download").start()

    def install(self):
        """Start the verified installer. It closes iShara, upgrades it and starts it again."""
        if self.status.get("state") != "ready" or not self.installer_path:
            return False
        subprocess.Popen([self.installer_path, "/SP-", "/NOCANCEL"], close_fds=True)
        return True
