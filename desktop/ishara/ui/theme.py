"""iShara design system.

Warm off-white surfaces, charcoal text, one blue accent used only for primary
actions and active states. Colour elsewhere only when it carries meaning
(success / warning / error). No gradients, glows or heavy shadows.
Typeface: Inter (bundled, loaded privately for this process only).
"""
import ctypes
import glob
import os
from tkinter import font as tkfont

LIGHT = dict(              # Apple system colours - matches ishara/web/app.css
    bg="#F5F5F7",          # main background
    card="#FFFFFF",        # primary surface
    text="#1D1D1F",        # primary text
    sub="#6E6E73",         # secondary text
    faint="#A1A1A6",       # tertiary text / placeholders
    accent="#007AFF",      # system blue (actions, active states only)
    accent_h="#0062CC",
    accent_bg="#E5F1FF",   # subtle accent background
    line="#E3E3E8",        # borders
    line2="#EFEFF2",       # hairlines inside surfaces
    hover="#EDEDF0",       # neutral hover / selected
    green="#34C759", amber="#FF9500", red="#FF3B30", gray="#C7C7CC",
    overlay_bg="#1D1D1F", overlay_fg="#FFFFFF",
)
DARK = dict(
    bg="#161617", card="#1E1E20", text="#EDEDEF", sub="#9B9EA6", faint="#6B6E76",
    accent="#6B8CF0", accent_h="#7E9BF3", accent_bg="#232A40",
    line="#2C2C2F", line2="#252527", hover="#29292C",
    green="#3DB07A", amber="#E3A94E", red="#E4706C", gray="#4A4B50",
    overlay_bg="#EDEDEF", overlay_fg="#161617",
)
# legacy keys used by the practice lessons
for _p in (LIGHT, DARK):
    _p.update(soft=_p["hover"], soft_h=_p["line"], zone=_p["accent_bg"], dot=_p["text"],
              navy=_p["text"], shadow=_p["line"])

C = dict(LIGHT)
F = {}
ICON_FONT = "Segoe Fluent Icons"
from ..paths import ASSETS_DIR

FONT_DIR = os.path.join(ASSETS_DIR, "fonts")

# Line icons from the Windows 11 icon font
I = dict(home="", training="", settings="", profile="", info="",
         mic="", mic_off="", pause="", play="", check="",
         cursor="", minimize="", close="", keyboard="", warning="",
         chevron="", grip="", bluetooth="", head="", dot="",
         list="", edit="")


def load_private_fonts():
    """Make bundled Inter available to this process only (nothing is installed)."""
    for path in glob.glob(os.path.join(FONT_DIR, "*.ttf")):
        try:
            ctypes.windll.gdi32.AddFontResourceExW(path, 0x10, 0)   # FR_PRIVATE
        except Exception:
            pass


def apply(name):
    C.clear()
    C.update(DARK if name == "dark" else LIGHT)


def init_fonts():
    global ICON_FONT
    fams = set(tkfont.families())
    reg = "Inter" if "Inter" in fams else "Segoe UI Variable Text"
    med = "Inter Medium" if "Inter Medium" in fams else "Segoe UI Variable Text Semibold"
    semi = "Inter SemiBold" if "Inter SemiBold" in fams else "Segoe UI Variable Text Semibold"
    ICON_FONT = next((f for f in ("Segoe Fluent Icons", "Segoe MDL2 Assets") if f in fams), reg)
    F.update(
        # type scale: 18 / 13 / 11 / 10 / 9
        h1=(semi, 16), h2=(semi, 12), h3=(med, 11),
        body=(reg, 10), bodyb=(med, 10), small=(reg, 9), smallb=(med, 9), tiny=(reg, 8),
        btn=(med, 10), big=(med, 11), state=(med, 11), mono=("Cascadia Mono", 9),
        hero=(semi, 18), title=(semi, 12),
        icon=(ICON_FONT, 11), icon_s=(ICON_FONT, 9), icon_m=(ICON_FONT, 12), icon_l=(ICON_FONT, 14))
