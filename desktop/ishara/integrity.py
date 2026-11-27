"""Speech-model integrity: SHA-256 of every model file.

Build time:   python -m ishara.integrity --write models     -> models/MODELS.sha256
On the PC:    verify() checks the installed models against MODELS.sha256 once per
              install/update (result cached in %APPDATA%/Ishara), so a damaged or
              incomplete install is detected and reported instead of failing silently.
"""
import hashlib
import json
import os
import sys

from .paths import MODELS_DIR, USER_DIR

MANIFEST = "MODELS.sha256"
CACHE = os.path.join(USER_DIR, "models-verified.json")


def _sha256(path, chunk=1 << 20):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(chunk), b""):
            h.update(block)
    return h.hexdigest()


def _files(root):
    for d, _, names in os.walk(root):
        for n in sorted(names):
            p = os.path.join(d, n)
            rel = os.path.relpath(p, root).replace("\\", "/")
            if rel != MANIFEST and rel.lower() != "readme.md":
                yield rel, p


def write_manifest(root=MODELS_DIR):
    lines = [f"{_sha256(p)}  {rel}" for rel, p in sorted(_files(root))]
    with open(os.path.join(root, MANIFEST), "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + "\n")
    return len(lines)


def read_manifest(root=MODELS_DIR):
    entries = {}
    with open(os.path.join(root, MANIFEST), encoding="utf-8") as f:
        for line in f:
            if line.strip():
                digest, rel = line.rstrip("\n").split("  ", 1)
                entries[rel] = digest
    return entries


def verify(root=MODELS_DIR, use_cache=True, progress=None):
    """Return (ok, problems). problems lists missing or damaged files."""
    path = os.path.join(root, MANIFEST)
    if not os.path.exists(path):
        return True, []                       # running from source without a manifest
    stamp = str(os.path.getmtime(path))
    if use_cache:
        try:
            with open(CACHE, encoding="utf-8") as f:
                c = json.load(f)
            if c.get("root") == os.path.abspath(root) and c.get("stamp") == stamp and c.get("ok"):
                return True, []
        except Exception:
            pass
    entries = read_manifest(root)
    problems = []
    for i, (rel, digest) in enumerate(entries.items()):
        p = os.path.join(root, rel)
        if not os.path.exists(p):
            problems.append(f"missing: {rel}")
        elif _sha256(p) != digest:
            problems.append(f"damaged: {rel}")
        if progress:
            progress((i + 1) / len(entries))
    ok = not problems
    try:
        os.makedirs(USER_DIR, exist_ok=True)
        with open(CACHE, "w", encoding="utf-8") as f:
            json.dump({"root": os.path.abspath(root), "stamp": stamp, "ok": ok}, f)
    except OSError:
        pass
    return ok, problems


if __name__ == "__main__":
    if len(sys.argv) >= 2 and sys.argv[1] == "--write":
        root = sys.argv[2] if len(sys.argv) > 2 else MODELS_DIR
        print(f"{write_manifest(root)} files hashed -> {os.path.join(root, MANIFEST)}")
    else:
        ok, problems = verify(use_cache=False)
        print("models OK" if ok else "\n".join(problems))
        sys.exit(0 if ok else 1)
