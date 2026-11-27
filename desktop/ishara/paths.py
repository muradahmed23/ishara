"""Where iShara's files live, from source and when installed.

From source (python ishara_app.py):
    desktop/ishara/...      code + web UI
    desktop/assets/         fonts
    desktop/models/         speech models

Installed (PyInstaller one-folder build, installed by Inno Setup):
    {app}/iShara.exe
    {app}/_internal/        code, web UI, assets   (sys._MEIPASS)
    {app}/models/           speech models          (installed next to the exe)

User data is never stored in the install folder, so updates cannot overwrite it:
    %APPDATA%/Ishara/       profiles, settings, logs
"""
import os
import sys

FROZEN = getattr(sys, "frozen", False)

if FROZEN:
    RESOURCE_DIR = getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
    INSTALL_DIR = os.path.dirname(sys.executable)
else:
    RESOURCE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    INSTALL_DIR = RESOURCE_DIR

ASSETS_DIR = os.path.join(RESOURCE_DIR, "assets")
# ISHARA_MODELS lets developers and tests point at another model folder.
MODELS_DIR = os.environ.get("ISHARA_MODELS") or os.path.join(INSTALL_DIR, "models")
USER_DIR = os.path.join(os.environ.get("APPDATA", "."), "Ishara")
