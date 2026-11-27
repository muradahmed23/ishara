"""Practice lessons (from the original Ishara Trainer), now using the app's own voice engine.
Each lesson unlocks when the previous one is passed. Opens full screen."""
import difflib
import random
import re
import time
import tkinter as tk

from .theme import C, F
from .widgets import Pill, label, rrect

LESSONS = [
    dict(id="move", title="Look around", sub="Move the cursor in four directions",
         steps=["Keep your head straight. The cursor stays still.",
                "Tilt your head toward each blue circle.",
                "Hold the cursor inside the circle until it fills."],
         rule="Reach all 4 circles within 90 seconds.", limit=90),
    dict(id="aim", title="Aim", sub="Stop exactly on smaller targets",
         steps=["Targets appear one by one and get smaller.",
                "Use small tilts to move slowly and stop on them.",
                "Hold the cursor inside until the circle fills."],
         rule="Reach 8 targets within 2 minutes.", limit=120),
    dict(id="click", title="Click", sub="Click with your voice",
         steps=["Move the cursor onto the blue circle.", "Say “click”.",
                "Clicking outside the circle counts as a miss."],
         rule="5 clicks on target with fewer than 6 misses, within 2 minutes.", limit=120),
    dict(id="double", title="Double click", sub="Open files and folders",
         steps=["Move the cursor onto the folder.", "Say “double click”."],
         rule="Open 3 folders within 2 minutes.", limit=120),
    dict(id="right", title="Right click", sub="Open menus with your voice",
         steps=["Move the cursor onto the target.", "Say “right click”."],
         rule="3 right clicks on target within 2 minutes.", limit=120),
    dict(id="scroll", title="Scroll", sub="Move through long pages",
         steps=["Put the cursor over the list.", "Say “scroll down” until you see the blue row.",
                "Move onto it and say “click”."],
         rule="Click the blue row at the bottom within 2 minutes.", limit=120),
    dict(id="type", title="Type", sub="Write with your voice",
         steps=["Move onto the text box and say “click”.",
                "Say “start typing”, read the sentence, then “stop typing”.",
                "Say “delete that” to remove a mistake."],
         rule="Type the sentence (at least 85% correct) within 3 minutes.", limit=180),
]
SENTENCES = ["hello my name is ishara", "i can use the computer without my hands",
             "today is a good day to learn", "please open my email"]


def normalize(s):
    s = re.sub(r"[^a-z0-9 ]", " ", s.lower())
    return re.sub(r"\s+", " ", s).strip()


class Lesson:
    def __init__(self, win, spec):
        self.win, self.spec = win, spec
        self.done = False
        self.t0 = self.last = time.time()
        self.mx = self.my = -1000
        bar = tk.Frame(win.root_frame, bg=C["bg"])
        bar.pack(fill="x", padx=32, pady=(20, 8))
        label(bar, spec["title"], "h2").pack(side="left")
        Pill(bar, "Exit", self.exit, kind="soft", width=100, height=36).pack(side="right")
        self.timer = label(bar, "", "body", "sub")
        self.timer.pack(side="right", padx=20)
        self.status = label(bar, "", "body", "sub")
        self.status.pack(side="right", padx=20)
        self.body = tk.Frame(win.root_frame, bg=C["bg"])
        self.body.pack(fill="both", expand=True, padx=32, pady=(0, 32))
        self.build()
        win.after(150, self._start)

    def build(self):
        self.canvas = tk.Canvas(self.body, bg=C["card"], highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        self.canvas.bind("<Motion>", lambda e: setattr(self, "mx", e.x) or setattr(self, "my", e.y))

    def _start(self):
        if self.done:
            return
        if hasattr(self, "canvas"):
            self.W = max(self.canvas.winfo_width(), 600)
            self.H = max(self.canvas.winfo_height(), 400)
        self.start()
        self._tick()

    def _tick(self):
        if self.done:
            return
        now = time.time()
        dt, self.last = now - self.last, now
        left = self.spec["limit"] - (now - self.t0)
        if left <= 0:
            return self.finish(False, "Time is up. Take a short break and try again.")
        self.timer.config(text=f"{int(left) // 60}:{int(left) % 60:02d}")
        self.update(dt)
        self.win.after(30, self._tick)

    def start(self):
        pass

    def update(self, dt):
        pass

    def cleanup(self):
        pass

    def exit(self):
        self.done = True
        self.cleanup()
        self.win.show_home()

    def finish(self, passed, detail):
        if self.done:
            return
        self.done = True
        self.cleanup()
        self.win.after(400, lambda: self.win.show_result(self.spec, passed, detail))


class HoverLesson(Lesson):
    HOLD = 0.8

    def start(self):
        self.targets, self.idx, self.held = self.make_targets(), 0, 0.0
        self.draw()

    def draw(self):
        c = self.canvas
        c.delete("all")
        if self.idx >= len(self.targets):
            return
        x, y, r = self.targets[self.idx]
        c.create_oval(x - r, y - r, x + r, y + r, fill=C["zone"], outline=C["accent"], width=3)
        if self.held > 0:
            c.create_arc(x - r, y - r, x + r, y + r, start=90, extent=-359.9 * min(self.held / self.HOLD, 1),
                         fill=C["accent"], outline=C["accent"])
        self.status.config(text=f"{self.idx} of {len(self.targets)}")

    def update(self, dt):
        if self.idx >= len(self.targets):
            return
        x, y, r = self.targets[self.idx]
        if (self.mx - x) ** 2 + (self.my - y) ** 2 <= r * r:
            self.held += dt
            if self.held >= self.HOLD:
                self.idx, self.held = self.idx + 1, 0
                if self.idx >= len(self.targets):
                    return self.finish(True, "Great control. You can move the cursor where you want.")
        else:
            self.held = 0
        self.draw()


class MoveLesson(HoverLesson):
    def make_targets(self):
        W, H, r = self.W, self.H, 60
        pts = [(W / 2, r + 30, r), (W - r - 30, H / 2, r), (W / 2, H - r - 30, r), (r + 30, H / 2, r)]
        random.shuffle(pts)
        return pts


class AimLesson(HoverLesson):
    def make_targets(self):
        return [(random.randint(r + 20, self.W - r - 20), random.randint(r + 20, self.H - r - 20), r)
                for r in (int(60 - i * 5) for i in range(8))]


class ClickLesson(Lesson):
    NEED, EVENT, MAX_MISS = 5, "<Button-1>", 6
    LABEL = "Say “click”"

    def start(self):
        self.hits = self.miss = 0
        self.canvas.bind(self.EVENT, self.on_click)
        self.place()

    def place(self):
        self.r = 70
        self.x = random.randint(self.r + 30, self.W - self.r - 30)
        self.y = random.randint(self.r + 30, self.H - self.r - 30)
        self.draw()

    def draw(self, flash=None):
        c = self.canvas
        c.delete("all")
        col = flash or C["accent"]
        c.create_oval(self.x - self.r, self.y - self.r, self.x + self.r, self.y + self.r, fill=col, outline=col)
        c.create_text(self.x, self.y, text=self.LABEL, fill="#FFFFFF", font=F["btn"])
        self.status.config(text=f"{self.hits} of {self.NEED}   ·   misses {self.miss}")

    def on_click(self, e):
        if self.done:
            return
        if (e.x - self.x) ** 2 + (e.y - self.y) ** 2 <= self.r ** 2:
            self.hits += 1
            self.draw(C["green"])
            if self.hits >= self.NEED:
                self.finish(True, "Well done. Clicking by voice works.")
            else:
                self.win.after(300, self.place)
        else:
            self.miss += 1
            self.draw()
            if self.miss >= self.MAX_MISS:
                self.finish(False, "Too many clicks outside the target. Stop on the circle first, then speak.")


class DoubleLesson(ClickLesson):
    NEED, EVENT, MAX_MISS = 3, "<Double-Button-1>", 99

    def draw(self, flash=None):
        c = self.canvas
        c.delete("all")
        x, y = self.x, self.y
        col = flash or "#FFCC00"
        rrect(c, x - 70, y - 40, x - 10, y - 25, 6, fill=col, outline=col)
        rrect(c, x - 70, y - 30, x + 70, y + 50, 12, fill=col, outline=col)
        c.create_text(x, y + 75, text="Say “double click”", fill=C["text"], font=F["body"])
        self.status.config(text=f"{self.hits} of {self.NEED} opened")

    def on_click(self, e):
        if self.done:
            return
        if self.x - 70 <= e.x <= self.x + 70 and self.y - 45 <= e.y <= self.y + 50:
            self.hits += 1
            self.draw(C["green"])
            if self.hits >= self.NEED:
                self.finish(True, "You can open files and folders.")
            else:
                self.win.after(400, self.place)


class RightLesson(ClickLesson):
    NEED, EVENT, MAX_MISS = 3, "<Button-3>", 6
    LABEL = "Say “right click”"


class ScrollLesson(Lesson):
    ROWS = 40

    def start(self):
        c, rowh = self.canvas, 64
        for i in range(self.ROWS):
            y = i * rowh
            if i == self.ROWS - 1:
                rrect(c, 20, y + 6, self.W - 20, y + rowh - 6, 14, fill=C["accent"], outline=C["accent"], tags="goal")
                c.create_text(self.W / 2, y + rowh / 2, text="Click me", fill="#FFFFFF", font=F["btn"], tags="goal")
            else:
                c.create_text(40, y + rowh / 2, text=f"Row {i + 1}", anchor="w", fill=C["text"], font=F["body"])
                c.create_line(20, y + rowh, self.W - 20, y + rowh, fill=C["line"])
        c.configure(scrollregion=(0, 0, self.W, self.ROWS * rowh))
        c.tag_bind("goal", "<Button-1>", lambda e: self.finish(True, "Scrolling works. You can read long pages."))
        self.win.bind_all("<MouseWheel>", self.wheel)
        self.status.config(text="Find the blue row")

    def wheel(self, e):
        self.canvas.yview_scroll(int(-e.delta / 120) * 2, "units")

    def cleanup(self):
        self.win.unbind_all("<MouseWheel>")


class TypeLesson(Lesson):
    def build(self):
        card = tk.Frame(self.body, bg=C["card"])
        card.pack(fill="both", expand=True)
        self.target = random.choice(SENTENCES)
        label(card, "Say this sentence", "small", "sub").pack(pady=(60, 6))
        label(card, f"“{self.target.capitalize()}”", "h1", wraplength=900).pack(pady=(0, 40))
        box = tk.Frame(card, bg=C["line"], padx=2, pady=2)
        box.pack(padx=80, fill="x")
        self.text = tk.Text(box, height=4, font=F["h3"], bg=C["card"], fg=C["text"], relief="flat",
                            padx=16, pady=14, wrap="word", insertbackground=C["accent"])
        self.text.pack(fill="x")
        self.score = label(card, "Match 0%", "body", "sub")
        self.score.pack(pady=24)

    def update(self, dt):
        typed = normalize(self.text.get("1.0", "end"))
        ratio = difflib.SequenceMatcher(None, typed, self.target).ratio()
        self.score.config(text=f"Match {int(ratio * 100)}%")
        self.status.config(text="Click the box, then speak")
        if ratio >= 0.85:
            self.finish(True, "You can type with your voice.")


CLASSES = dict(move=MoveLesson, aim=AimLesson, click=ClickLesson, double=DoubleLesson,
               right=RightLesson, scroll=ScrollLesson, type=TypeLesson)


class PracticeWindow(tk.Toplevel):
    def __init__(self, master, ctrl):
        super().__init__(master)
        self.ctrl = ctrl
        self.title("Ishara Practice")
        self.configure(bg=C["bg"])
        self.geometry("1100x760")
        try:
            self.state("zoomed")
        except tk.TclError:
            pass
        self.root_frame, self.lesson = None, None
        self.show_home()

    @property
    def passed(self):
        return self.ctrl.settings.setdefault("practice_passed", [])

    def clear(self):
        if self.lesson and not self.lesson.done:
            self.lesson.done = True
            self.lesson.cleanup()
        self.lesson = None
        if self.root_frame:
            self.root_frame.destroy()
        self.root_frame = tk.Frame(self, bg=C["bg"])
        self.root_frame.pack(fill="both", expand=True)

    def centered(self):
        box = tk.Frame(self.root_frame, bg=C["bg"])
        box.place(relx=0.5, rely=0.5, anchor="center")
        return box

    def show_home(self):
        self.clear()
        box = self.centered()
        label(box, "Practice", "hero").pack()
        label(box, "Pass each lesson to unlock the next one.", "body", "sub").pack(pady=(6, 24))
        card = tk.Frame(box, bg=C["card"])
        card.pack(fill="x")
        unlocked = next((i + 1 for i, s in enumerate(LESSONS) if s["id"] not in self.passed), len(LESSONS))
        for i, spec in enumerate(LESSONS):
            done, open_ = spec["id"] in self.passed, i < unlocked
            row = tk.Frame(card, bg=C["card"], padx=24, pady=12, cursor="hand2" if open_ else "arrow")
            row.pack(fill="x")
            num = tk.Canvas(row, width=32, height=32, bg=C["card"], highlightthickness=0)
            num.pack(side="left", padx=(0, 16))
            col = C["green"] if done else (C["accent"] if open_ else C["gray"])
            num.create_oval(1, 1, 31, 31, fill=col, outline="")
            num.create_text(16, 16, text="✓" if done else str(i + 1), fill="#FFFFFF", font=F["btn"])
            txt = tk.Frame(row, bg=C["card"])
            txt.pack(side="left", fill="x", expand=True)
            label(txt, spec["title"], "h3", "text" if open_ else "sub", anchor="w").pack(fill="x")
            label(txt, spec["sub"], "small", "sub", anchor="w").pack(fill="x")
            st = label(row, "Passed" if done else ("Start ›" if open_ else "Locked"), "body",
                       "accent" if open_ and not done else "sub")
            st.pack(side="right")
            if open_:
                for w in (row, num, txt, st, *txt.winfo_children()):
                    w.bind("<ButtonRelease-1>", lambda e, s=spec: self.show_intro(s))
        b = tk.Frame(box, bg=C["bg"])
        b.pack(pady=(24, 0))
        Pill(b, "Reset progress", self._reset, kind="soft", width=170, height=38).pack(side="left", padx=6)
        Pill(b, "Close", self.destroy, kind="soft", width=120, height=38).pack(side="left", padx=6)

    def _reset(self):
        self.passed.clear()
        self.ctrl.save_profile()
        self.show_home()

    def show_intro(self, spec):
        self.clear()
        box = self.centered()
        label(box, f"Lesson {LESSONS.index(spec) + 1}", "body", "sub").pack()
        label(box, spec["title"], "hero").pack(pady=(4, 24))
        card = tk.Frame(box, bg=C["card"], padx=32, pady=24)
        card.pack(fill="x")
        for i, s in enumerate(spec["steps"], 1):
            label(card, f"{i}.  {s}", "h3", anchor="w", justify="left").pack(fill="x", pady=4)
        label(box, spec["rule"], "body", "sub").pack(pady=(18, 28))
        b = tk.Frame(box, bg=C["bg"])
        b.pack()
        Pill(b, "Start", lambda: self.run_lesson(spec), width=180, height=42).pack(side="left", padx=8)
        Pill(b, "Back", self.show_home, kind="soft", width=180, height=42).pack(side="left", padx=8)

    def run_lesson(self, spec):
        self.clear()
        self.lesson = CLASSES[spec["id"]](self, spec)

    def show_result(self, spec, passed, detail):
        if passed and spec["id"] not in self.passed:
            self.passed.append(spec["id"])
            self.ctrl.save_profile()
        self.clear()
        box = self.centered()
        c = tk.Canvas(box, width=96, height=96, bg=C["bg"], highlightthickness=0)
        c.pack()
        c.create_oval(2, 2, 94, 94, fill=C["green"] if passed else C["red"], outline="")
        c.create_text(48, 48, text="✓" if passed else "✕", fill="#FFFFFF", font=(F["h1"][0], 34, "bold"))
        label(box, "Passed" if passed else "Not yet", "hero").pack(pady=(20, 6))
        label(box, detail, "body", "sub", wraplength=560).pack(pady=(0, 32))
        b = tk.Frame(box, bg=C["bg"])
        b.pack()
        i = LESSONS.index(spec)
        if passed and i + 1 < len(LESSONS):
            Pill(b, "Next lesson", lambda: self.show_intro(LESSONS[i + 1]), width=180, height=42).pack(side="left", padx=8)
        elif not passed:
            Pill(b, "Try again", lambda: self.run_lesson(spec), width=180, height=42).pack(side="left", padx=8)
        Pill(b, "All lessons", self.show_home, kind="soft", width=180, height=42).pack(side="left", padx=8)
