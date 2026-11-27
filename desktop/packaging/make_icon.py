"""Render the iShara logo mark (same shape as the .mark element in web/app.css)
to icon.ico (exe, installer, shortcuts) and icon-512.png (website)."""
import os
from PIL import Image, ImageDraw

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets")


def mark(size):
    s = size * 4                                   # draw large, downsample = smooth edges
    im = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, s - 1, s - 1], radius=int(s * 0.25), fill="#1D1D1F")
    dot, bar_w, bar_h = s * 0.125, s * 0.125, s * 0.34
    cx, top = s / 2, s * 0.22
    d.ellipse([cx - dot / 2, top, cx + dot / 2, top + dot], fill="white")
    by = top + dot + s * 0.07
    d.rounded_rectangle([cx - bar_w / 2, by, cx + bar_w / 2, by + bar_h], radius=int(bar_w / 2), fill="white")
    return im.resize((size, size), Image.LANCZOS)


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    big = mark(256)
    big.save(os.path.join(OUT, "icon.ico"), sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    mark(512).save(os.path.join(OUT, "icon-512.png"))
    print("written to", os.path.abspath(OUT))
