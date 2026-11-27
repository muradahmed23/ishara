"""Reusable UI components (all drawn on Tk canvases)."""
import tkinter as tk

from .theme import C, F, I


def rrect(c, x1, y1, x2, y2, r, **kw):
    """Rounded rectangle. Small radii only - this design avoids pill shapes."""
    r = max(0, min(r, (x2 - x1) / 2, (y2 - y1) / 2))
    pts = [x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r, x2, y2 - r, x2, y2,
           x2 - r, y2, x1 + r, y2, x1, y2, x1, y2 - r, x1, y1 + r, x1, y1]
    return c.create_polygon(pts, smooth=True, **kw)


def label(parent, text, font="body", fg="text", bg=None, **kw):
    return tk.Label(parent, text=text, font=F[font], fg=C[fg], bg=bg or parent.cget("bg"), **kw)


def icon(c, x, y, name, size="icon", fill=None, tags=(), anchor="center"):
    return c.create_text(x, y, text=I[name], font=F[size], fill=fill or C["text"], tags=tags, anchor=anchor)


def card(c, x1, y1, x2, y2, r=8, fill=None, tags=()):
    """Flat surface with a 1px border (no shadow)."""
    rrect(c, x1, y1, x2, y2, r, fill=fill or C["card"], outline=C["line"], tags=tags)


def centered_status(c, cx, cy, text, font="bodyb", dot=None, icon_name=None, color=None, tags=(), gap=7):
    t = c.create_text(0, cy, text=text, anchor="w", fill=C["text"], font=F[font], tags=tags)
    x1, _, x2, _ = c.bbox(t)
    lead = 8 if dot else (14 if icon_name else 0)
    total = (x2 - x1) + (lead + gap if lead else 0)
    left = cx - total / 2
    if dot:
        c.create_oval(left, cy - 4, left + 8, cy + 4, fill=dot, outline="", tags=tags)
    elif icon_name:
        icon(c, left + 7, cy, icon_name, "icon_s", fill=color, tags=tags)
    c.move(t, left + (lead + gap if lead else 0), 0)
    return t


class Pill(tk.Canvas):
    """Button. kind: primary (blue) | soft (white, bordered) | ghost | danger."""

    def __init__(self, parent, text, command, kind="primary", width=None, height=32, font="btn", icon_name=None):
        self.f = F[font]
        tmp = tk.Label(parent, text=text, font=self.f)
        tw = tmp.winfo_reqwidth()
        tmp.destroy()
        width = width or tw + (44 if icon_name else 28)
        super().__init__(parent, width=width, height=height, bg=parent.cget("bg"),
                         highlightthickness=0, cursor="hand2")
        self.command, self.kind, self.enabled = command, kind, True
        self.w, self.h, self.text, self.icon_name = width, height, text, icon_name
        self._draw(False)
        self.bind("<Enter>", lambda e: self._draw(True))
        self.bind("<Leave>", lambda e: self._draw(False))
        self.bind("<ButtonRelease-1>", self._click)

    def set_text(self, text, kind=None, icon_name=None):
        if (text, kind or self.kind, icon_name or self.icon_name) == (self.text, self.kind, self.icon_name):
            return
        self.text = text
        self.kind = kind or self.kind
        self.icon_name = icon_name or self.icon_name
        self._draw(False)

    def set_enabled(self, on):
        self.enabled = on
        self._draw(False)

    def _draw(self, hover):
        self.delete("all")
        k = self.kind
        if not self.enabled:
            fill, border, fg = C["hover"], C["line"], C["faint"]
        elif k in ("primary", "accent"):
            fill = border = C["accent_h"] if hover else C["accent"]
            fg = "#FFFFFF"
        elif k == "danger":
            fill, border, fg = (C["hover"] if hover else C["card"]), C["line"], C["red"]
        elif k == "ghost":
            fill = border = C["hover"] if hover else self.cget("bg")
            fg = C["text"]
        else:
            fill, border, fg = (C["hover"] if hover else C["card"]), C["line"], C["text"]
        rrect(self, 1, 1, self.w - 1, self.h - 1, 6, fill=fill, outline=border)
        if self.icon_name:
            t = self.create_text(0, self.h / 2, text=self.text, fill=fg, font=self.f, anchor="w")
            tw = self.bbox(t)[2] - self.bbox(t)[0]
            left = (self.w - tw - 18) / 2
            self.create_text(left + 6, self.h / 2, text=I[self.icon_name], fill=fg, font=F["icon_s"])
            self.move(t, left + 18, 0)
        else:
            self.create_text(self.w / 2, self.h / 2, text=self.text, fill=fg, font=self.f)

    def _click(self, _e):
        if self.enabled and self.command:
            self.command()


class Toggle(tk.Canvas):
    def __init__(self, parent, value, command):
        super().__init__(parent, width=34, height=20, bg=parent.cget("bg"),
                         highlightthickness=0, cursor="hand2")
        self.value, self.command = bool(value), command
        self._draw()
        self.bind("<ButtonRelease-1>", self._flip)

    def _draw(self):
        self.delete("all")
        col = C["accent"] if self.value else C["gray"]
        rrect(self, 1, 2, 33, 18, 8, fill=col, outline=col)
        x = 25 if self.value else 9
        self.create_oval(x - 6, 4, x + 6, 16, fill="#FFFFFF", outline="")

    def _flip(self, _e):
        self.value = not self.value
        self._draw()
        self.command(self.value)


class Slider(tk.Canvas):
    def __init__(self, parent, lo, hi, value, command, width=220, step=None, fmt="{:.1f}"):
        super().__init__(parent, width=width + 54, height=24, bg=parent.cget("bg"),
                         highlightthickness=0, cursor="hand2")
        self.lo, self.hi, self.value, self.command = lo, hi, value, command
        self.wid, self.step, self.fmt = width, step, fmt
        self._draw()
        self.bind("<B1-Motion>", self._drag)
        self.bind("<Button-1>", self._drag)
        self.bind("<ButtonRelease-1>", lambda e: self.command(self.value))

    def _draw(self):
        self.delete("all")
        x = 8 + (self.value - self.lo) / (self.hi - self.lo) * (self.wid - 16)
        self.create_line(8, 12, self.wid - 8, 12, fill=C["line"], width=3, capstyle="round")
        self.create_line(8, 12, x, 12, fill=C["accent"], width=3, capstyle="round")
        self.create_oval(x - 7, 5, x + 7, 19, fill="#FFFFFF", outline=C["gray"])
        self.create_text(self.wid + 46, 12, text=self.fmt.format(self.value), anchor="e",
                         fill=C["sub"], font=F["small"])

    def _drag(self, e):
        f = min(max((e.x - 8) / (self.wid - 16), 0), 1)
        v = self.lo + f * (self.hi - self.lo)
        if self.step:
            v = round(v / self.step) * self.step
        self.value = v
        self._draw()


class Choice(tk.Frame):
    """Segmented control."""

    def __init__(self, parent, options, value, command):
        super().__init__(parent, bg=C["line"], padx=1, pady=1)
        inner = tk.Frame(self, bg=C["bg"], padx=2, pady=2)
        inner.pack()
        self.command, self.value, self.btns = command, value, {}
        for key, text in options:
            b = tk.Label(inner, text=text, font=F["small"], padx=10, pady=3, cursor="hand2")
            b.pack(side="left", padx=1)
            b.bind("<ButtonRelease-1>", lambda e, k=key: self.set(k, True))
            self.btns[key] = b
        self.set(value, False)

    def set(self, key, fire):
        self.value = key
        for k, b in self.btns.items():
            on = k == key
            b.configure(bg=C["card"] if on else C["bg"], fg=C["text"] if on else C["sub"],
                        font=F["smallb"] if on else F["small"])
        if fire:
            self.command(key)


class TrackingView(tk.Canvas):
    """Functional head-tracking plot.

    Coordinates are the personal-model normalised values (model.normalized):
    0 = neutral, +-1 = the user's comfortable limit. Shows grid, neutral cross,
    dead zone, comfortable range, live dot with a short trail, and edge
    highlights when a limit is reached.
    """
    SPAN = 1.25          # plot shows +-1.25 so 'beyond limit' is visible

    def __init__(self, parent, size=200, bg=None):
        super().__init__(parent, width=size, height=size, bg=bg or parent.cget("bg"), highlightthickness=0)
        self.size = size
        self.trail = []

    def _p(self, v):
        s = self.size
        return s / 2 + v / self.SPAN * (s / 2 - 6)

    def show(self, nx, ny, dz, active=True, unstable=False, targets=(), hit=()):
        s = self.size
        self.delete("all")
        rrect(self, 1, 1, s - 1, s - 1, 6, fill=C["card"], outline=C["line"])
        for i in range(1, 8):                                  # fine grid
            v = -self.SPAN + i * self.SPAN * 2 / 8
            p = self._p(v)
            self.create_line(p, 6, p, s - 6, fill=C["line2"])
            self.create_line(6, p, s - 6, p, fill=C["line2"])
        c = s / 2
        self.create_line(c, 6, c, s - 6, fill=C["line"])          # axes
        self.create_line(6, c, s - 6, c, fill=C["line"])
        lo, hi = self._p(-1), self._p(1)                          # comfortable range
        beyond_x, beyond_y = abs(nx) > 1, abs(ny) > 1
        self.create_rectangle(lo, hi, hi, lo, outline=C["gray"], dash=(2, 3))
        # highlight the edge being touched
        if active:
            if beyond_x:
                x = hi if nx > 0 else lo
                self.create_line(x, lo, x, hi, fill=C["amber"], width=2)
            if beyond_y:
                y = hi if ny > 0 else lo
                self.create_line(lo, y, hi, y, fill=C["amber"], width=2)
        d = self._p(dz) - c                                       # dead zone
        self.create_oval(c - d, c - d, c + d, c + d, outline=C["gray"], dash=(1, 3))
        self.create_line(c - 4, c, c + 5, c, fill=C["sub"])        # neutral mark
        self.create_line(c, c - 4, c, c + 5, fill=C["sub"])
        for i, (tx, ty) in enumerate(targets):
            px, py = self._p(tx), self._p(ty)
            col = C["green"] if i in hit else C["accent"]
            self.create_oval(px - 8, py - 8, px + 8, py + 8, outline=col, width=2,
                             fill=C["accent_bg"] if i not in hit else col)
        x = self._p(max(-self.SPAN, min(self.SPAN, nx)))
        y = self._p(max(-self.SPAN, min(self.SPAN, ny)))
        if active:
            self.trail = (self.trail + [(x, y)])[-8:]
            for tx, ty in self.trail[:-1]:
                self.create_oval(tx - 2, ty - 2, tx + 2, ty + 2, fill=C["gray"], outline="")
        col = C["gray"] if not active else (C["amber"] if (unstable or beyond_x or beyond_y) else C["text"])
        self.create_oval(x - 5, y - 5, x + 5, y + 5, fill=col, outline=C["card"], width=2)


# kept for older imports
HeadIndicator = TrackingView
