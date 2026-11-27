# PyInstaller spec - iShara desktop app (one-folder build).
#   cd desktop
#   .venv\Scripts\pyinstaller packaging\ishara.spec --noconfirm
# Output: desktop\dist\iShara\iShara.exe (+ _internal\). Models are NOT bundled here;
# the Inno Setup script installs them next to the exe ({app}\models).
import os
from PyInstaller.utils.hooks import collect_all, collect_data_files, collect_dynamic_libs, collect_submodules

ROOT = os.path.abspath(os.path.join(SPECPATH, ".."))

datas = [
    (os.path.join(ROOT, "ishara", "web"), os.path.join("ishara", "web")),
    (os.path.join(ROOT, "assets"), "assets"),
]
binaries = []
hiddenimports = []

# Native / data-heavy packages PyInstaller can't fully see on its own
for pkg in ("vosk", "webview", "clr_loader", "pythonnet"):
    d, b, h = collect_all(pkg)
    datas += d; binaries += b; hiddenimports += h

datas += collect_data_files("faster_whisper")            # Silero VAD model (assets/*.onnx)
datas += collect_data_files("_sounddevice_data")         # PortAudio DLL
binaries += collect_dynamic_libs("ctranslate2")          # Whisper inference engine
binaries += collect_dynamic_libs("onnxruntime")          # VAD
hiddenimports += collect_submodules("bleak")             # backend chosen at runtime
hiddenimports += collect_submodules("winrt")             # Windows Bluetooth APIs
hiddenimports += ["ishara.webui", "ishara.ui.main_window", "ishara.ui.practice"]

a = Analysis(
    [os.path.join(ROOT, "ishara_app.py")],
    pathex=[ROOT],
    datas=datas,
    binaries=binaries,
    hiddenimports=hiddenimports,
    excludes=["pytest", "_pytest", "matplotlib", "IPython", "notebook", "PyQt5", "PySide6"],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, [],
    exclude_binaries=True,
    name="iShara",
    icon=os.path.join(ROOT, "assets", "icon.ico"),
    console=False,                       # GUI app, no terminal window
    version=os.path.join(SPECPATH, "version_info.txt"),
)
coll = COLLECT(exe, a.binaries, a.datas, name="iShara")
