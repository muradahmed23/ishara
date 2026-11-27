"""Cursor status tag (click-through) and the floating control bar."""
import ctypes
import tkinter as tk

from .. import screen
from .theme import C, F, I
from .widgets import icon, rrect

GWL_EXSTYLE = -20
WS_EX_LAYERED, WS_EX_TRANSPARENT = 0x80000, 0x20
WS_EX_TOOLWINDOW, WS_EX_NOACTIVATE = 0x80, 0x8000000
KEY = "#010203"           # transparent colour key


def _hwnd(win):
    return ctypes.windll.user32.GetParent(win.winfo_id())


def _set_style(win, add=0, remove=0):
    h = _hwnd(win)
    style = ctypes.windll.user32.GetWindowLongW(h, GWL_EXSTYLE)
    ctypes.windll.user32.SetWindowLongW(h, GWL_EXSTYLE, (style | add) & ~remove)


def make_click_through(win):
    _set_style(win, WS_EX_LAYERED | WS_EX_TRANSPARENT | WS_EX_TOOLWINDOW | WS_EX_NOACTIVATE)


def make_no_activate(win):
    """Clicks never steal keyboard focus (important while dictating)."""
    _set_style(win, WS_EX_TOOLWINDOW | WS_EX_NOACTIVATE)


def draw_logo(c, x, y, size=22, tags=()):
    """iShara mark: a rounded square with a tilted 'i' - head + signal."""
    rrect(c, x, y, x + size, y + size, size * 0.28, fill=C["text"], outline=C["text"], tags=tags)
    cx = x + size / 2
    c.create_oval(cx - size * 0.09, y + size * 0.2, cx + size * 0.09, y + size * 0.38,
                  fill=C["card"], outline="", tags=tags)
    c.create_line(cx, y + size * 0.5, cx, y + size * 0.8, fill=C["card"], width=max(2, size * 0.14),
                  capstyle="round", tags=tags)


class StatusOverlay(tk.Toplevel):
    """Small charcoal tag next to the cursor. Click-through, never takes focus."""
    H = 28

    def __init__(self, master):
        super().__init__(master)
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.configure(bg=KEY)
        self.attributes("-transparentcolor", KEY)
        self.canvas = tk.Canvas(self, width=260, height=self.H, bg=KEY, highlightthickness=0)
        self.canvas.pack()
        self.text, self.visible, self.alpha, self.w = None, False, 0.0, 120
        self.withdraw()
        self.after(50, lambda: make_click_through(self))

    def show(self, text, kind, position):
        if not text:
            if self.visible:
                self.withdraw()
                self.visible, self.alpha = False, 0.0
            return
        if text != self.text:                       # redraw only on real change
            self.text = text
            c = self.canvas
            c.delete("all")
            t = c.create_text(0, self.H / 2, text=text, anchor="w", fill=C["overlay_fg"], font=F["smallb"])
            tw = c.bbox(t)[2] - c.bbox(t)[0]
            self.w = int(tw + 40)
            c.config(width=self.w)
            c.delete("all")
            rrect(c, 0, 0, self.w, self.H, 7, fill=C["overlay_bg"], outline=C["overlay_bg"])
            ic = {"ok": "check", "warn": "warning", "error": "warning"}.get(kind, "cursor")
            col = {"ok": "#6FD3A0", "warn": "#F2C077", "error": "#F09A97"}.get(kind, C["overlay_fg"])
            icon(c, 15, self.H / 2, ic, "icon_s", fill=col)
            c.create_text(28, self.H / 2, text=text, anchor="w", fill=C["overlay_fg"], font=F["smallb"])
        x, y = screen.cursor_pos()
        rect = screen.monitor_rect(x, y)
        if position == "top":
            px, py = (rect[0] + rect[2] - self.w) // 2, rect[1] + 18
        elif position == "bottom":
            px, py = (rect[0] + rect[2] - self.w) // 2, rect[3] - 120
        else:
            px, py = x + 18, y + 22
            if px + self.w > rect[2]:
                px = x - self.w - 8                  # flip to stay on screen
            if py + self.H > rect[3]:
                py = y - self.H - 8
        px, py = screen.clamp_point(px, py, (rect[0], rect[1], rect[2] - self.w, rect[3] - self.H))
        self.geometry(f"{self.w}x{self.H}+{px}+{py}")
        if not self.visible:
            self.deiconify()
            self.attributes("-topmost", True)
            self.visible, self.alpha = True, 0.35
        if self.alpha < 1.0:                         # subtle fade-in
            self.alpha = min(1.0, self.alpha + 0.22)
            self.attributes("-alpha", self.alpha)


class HelpMenu(tk.Toplevel):
    """Numbered action menu next to the cursor ("show commands" / "help").

    Say a number to choose, "more" / "back" to switch page, "close" to close.
    Rows can also be clicked (move onto a row with the head and say "click").
    Never takes keyboard focus.
    """
    W, ROW, HEAD, FOOT = 248, 34, 40, 34

    def __init__(self, master, ctrl):
        super().__init__(master)
        self.ctrl = ctrl
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.configure(bg=KEY)
        self.attributes("-transparentcolor", KEY)
        self.canvas = tk.Canvas(self, width=self.W, height=200, bg=KEY, highlightthickness=0, cursor="hand2")
        self.canvas.pack()
        self.canvas.bind("<Motion>", self._hover)
        self.canvas.bind("<Leave>", lambda e: self._set_hover(None))
        self.canvas.bind("<ButtonRelease-1>", self._click)
        self.hover, self._sig, self.visible = None, None, False
        self.withdraw()
        self.after(50, lambda: make_no_activate(self))

    def _row_at(self, y):
        i = int((y - self.HEAD) // self.ROW)
        return i if 0 <= i < len(self._items) else None

    def _hover(self, e):
        self._set_hover(self._row_at(e.y))

    def _set_hover(self, i):
        if i != self.hover:
            self.hover = i
            self._sig = None

    def _click(self, e):
        i = self._row_at(e.y)
        if i is not None:
            self.ctrl.request(f"menu_{i + 1}")

    def sync(self):
        from ..controller import MENU_TEXT
        m = self.ctrl.menu
        if not m:
            if self.visible:
                self.withdraw()
                self.visible, self._sig, self.hover = False, None, None
            return
        self._items = m["items"]
        H = self.HEAD + self.ROW * len(self._items) + self.FOOT
        sig = (tuple(self._items), m["page"], self.hover, tuple(m["anchor"]))
        if sig != self._sig:
            self._sig = sig
            c = self.canvas
            c.config(height=H)
            c.delete("all")
            rrect(c, 0, 0, self.W, H, 14, fill=C["line"], outline=C["line"])
            rrect(c, 1, 1, self.W - 1, H - 1, 13, fill=C["card"], outline=C["card"])
            c.create_text(18, self.HEAD / 2 + 2, text="Say a number", anchor="w", fill=C["text"], font=F["smallb"])
            c.create_text(self.W - 18, self.HEAD / 2 + 2, text=f"{m['page'] + 1} / 2", anchor="e",
                          fill=C["faint"], font=F["tiny"])
            for i, a in enumerate(self._items):
                y = self.HEAD + i * self.ROW
                on = i == self.hover
                if on:
                    rrect(c, 6, y + 2, self.W - 6, y + self.ROW - 2, 7, fill=C["accent"], outline=C["accent"])
                rrect(c, 16, y + 8, 34, y + self.ROW - 8, 5, fill="#FFFFFF" if on else C["hover"],
                      outline="")
                c.create_text(25, y + self.ROW / 2, text=str(i + 1), fill=C["accent"] if on else C["sub"],
                              font=F["smallb"])
                c.create_text(46, y + self.ROW / 2, text=MENU_TEXT.get(a, a), anchor="w",
                              fill="#FFFFFF" if on else C["text"], font=F["body"])
            fy = H - self.FOOT
            c.create_line(14, fy, self.W - 14, fy, fill=C["line2"])
            c.create_text(18, fy + self.FOOT / 2, anchor="w", fill=C["sub"], font=F["tiny"],
                          text="Say “close” to close")
            # place next to where the menu was opened, kept fully on screen
            ax, ay = m["anchor"]
            rect = screen.monitor_rect(ax, ay)
            x, y = ax + 18, ay + 18
            if x + self.W > rect[2]:
                x = ax - self.W - 12
            if y + H > rect[3]:
                y = ay - H - 12
            x, y = screen.clamp_point(x, y, (rect[0], rect[1], rect[2] - self.W, rect[3] - H))
            self.geometry(f"{self.W}x{H}+{x}+{y}")
            self.ctrl.menu_rect = (x, y, x + self.W, y + H)
        if not self.visible:
            self.deiconify()
            self.attributes("-topmost", True)
            self.visible = True


class FloatingWidget(tk.Toplevel):
    """Slim always-on-top control bar.

    [state dot + Active]  [mic]  [cursor action ...]  [pause]
    Drag anywhere to move. Mic icon toggles the microphone, the last button
    pauses/resumes. Double-click opens the main window. Optional click-through.
    """
    W, H = 360, 44

    def __init__(self, master, ctrl, open_main):
        super().__init__(master)
        self.ctrl, self.open_main = ctrl, open_main
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.configure(bg=KEY)
        self.attributes("-transparentcolor", KEY)
        self.canvas = tk.Canvas(self, width=self.W, height=self.H, bg=KEY, highlightthickness=0)
        self.canvas.pack()
        self.canvas.bind("<ButtonPress-1>", self._press)
        self.canvas.bind("<B1-Motion>", self._drag)
        self.canvas.bind("<ButtonRelease-1>", self._click)
        self.canvas.bind("<Double-Button-1>", lambda e: self.open_main())
        self.canvas.bind("<Motion>", self._hover)
        self.canvas.bind("<Leave>", lambda e: setattr(self, "hover", None))
        self.reset_position()
        self._moved, self._start, self.hover = False, (0, 0), None
        self._sig = None
        self.click_through = False
        self.after(50, lambda: make_no_activate(self))

    def reset_position(self):
        rect = screen.monitor_rect()
        self.geometry(f"+{(rect[0] + rect[2] - self.W) // 2}+{rect[3] - self.H - 64}")

    def set_click_through(self, on):
        self.click_through = on
        if on:
            _set_style(self, WS_EX_LAYERED | WS_EX_TRANSPARENT)
        else:
            _set_style(self, remove=WS_EX_TRANSPARENT)

    def _zone(self, x):
        if x > self.W - 42:
            return "pause"
        if 102 <= x <= 134:
            return "mic"
        return None

    def _hover(self, e):
        self.hover = self._zone(e.x)
        self.canvas.config(cursor="hand2" if self.hover else "fleur")

    def _press(self, e):
        self._start, self._moved = (e.x_root - self.winfo_x(), e.y_root - self.winfo_y()), False

    def _drag(self, e):
        self._moved = True
        self.geometry(f"+{e.x_root - self._start[0]}+{e.y_root - self._start[1]}")

    def _click(self, e):
        if self._moved:
            return
        z = self._zone(e.x)
        if z == "pause":
            self.ctrl.request("resume" if self.ctrl.paused else "pause")
        elif z == "mic":
            self.ctrl.toggle_mic()

    def _fit(self, text, font, max_px):
        """Cut text to a pixel width with an ellipsis (never overlaps the buttons)."""
        from tkinter import font as tkfont
        f = tkfont.Font(font=font)
        if f.measure(text) <= max_px:
            return text
        while text and f.measure(text + "â€¦") > max_px:
            text = text[:-1]
        return text.rstrip() + "â€¦"

    def refresh(self, text, kind):
        ctrl = self.ctrl
        alive = ctrl.link.data_alive()
        mic_on = ctrl.mic_state == "listening" and not ctrl.mic_muted
        sig = (text, kind, alive, ctrl.paused, mic_on, ctrl.mic_muted, ctrl.dictation, self.hover,
               ctrl.mic_state)
        if sig == self._sig:
            return                                  # nothing changed: no redraw, no flicker
        self._sig = sig
        c, W, H = self.canvas, self.W, self.H
        c.delete("all")
        # capsule with a hairline edge (Apple-style; Tk can't draw real shadows)
        rrect(c, 0, 0, W, H, H / 2, fill=C["line"], outline=C["line"])
        rrect(c, 1, 1, W - 1, H - 1, H / 2 - 1, fill=C["card"], outline=C["card"])
        # 1) state
        if ctrl.paused:
            st, col = "Paused", C["amber"]
        elif alive:
            st, col = "Active", C["green"]
        else:
            st, col = "Offline", C["gray"]
        c.create_oval(16, H / 2 - 4, 24, H / 2 + 4, fill=col, outline="")
        c.create_text(32, H / 2, text=st, anchor="w", fill=C["text"], font=F["smallb"])
        c.create_line(96, 12, 96, H - 12, fill=C["line"])
        # 2) microphone (click to mute / unmute)
        if self.hover == "mic":
            c.create_oval(104, H / 2 - 13, 130, H / 2 + 13, fill=C["hover"], outline="")
        mic_col = C["red"] if ctrl.mic_muted else (C["accent"] if ctrl.dictation else
                                                  (C["text"] if mic_on else C["faint"]))
        c.create_text(117, H / 2, text=I["mic_off" if not mic_on else "mic"], font=F["icon_s"], fill=mic_col)
        c.create_line(140, 12, 140, H - 12, fill=C["line"])
        # 3) what the cursor is doing - fitted to the space left before the button
        if not alive and not ctrl.paused:
            text, kind = "Connect headband", "info"
        tcol = {"ok": C["green"], "warn": C["amber"], "error": C["red"]}.get(kind, C["text"])
        if text == "Connect headband":
            tcol = C["sub"]
        c.create_text(155, H / 2, text=I["cursor"], font=F["icon_s"], fill=C["sub"])
        left, right = 169, W - 48
        c.create_text(left, H / 2, text=self._fit(text, F["small"], right - left), anchor="w",
                      fill=tcol, font=F["small"])
        # 4) pause / resume - round button
        bx = W - 22
        fill = C["accent"] if ctrl.paused else (C["line"] if self.hover == "pause" else C["hover"])
        c.create_oval(bx - 15, H / 2 - 15, bx + 15, H / 2 + 15, fill=fill, outline="")
        c.create_text(bx + (1 if ctrl.paused else 0), H / 2, text=I["play" if ctrl.paused else "pause"],
                      font=F["icon_s"], fill="#FFFFFF" if ctrl.paused else C["text"])
