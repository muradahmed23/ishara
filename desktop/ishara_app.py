"""iShara - start the app.

    pythonw ishara_app.py            normal use (headband over Bluetooth)
    python  ishara_app.py --sim      test without the headband (simulated head motion)
    python  ishara_app.py --classic  previous built-in (tkinter) interface
"""
import atexit
import ctypes
import sys

from ishara import screen


def single_instance():
    """Only one iShara may control the mouse at a time."""
    ctypes.windll.kernel32.CreateMutexW(None, False, "Local\\Ishara.MouseControl")
    if ctypes.windll.kernel32.GetLastError() == 183:            # ERROR_ALREADY_EXISTS
        ctypes.windll.user32.MessageBoxW(None, "iShara is already running.", "iShara", 0x40)
        sys.exit(0)


def main():
    single_instance()
    atexit.register(lambda: screen.clip_to(None))               # never leave the cursor locked
    from ishara.controller import Controller
    ctrl = Controller(simulate="--sim" in sys.argv)
    if "--classic" in sys.argv:
        from ishara.ui.main_window import MainWindow
        MainWindow(ctrl).mainloop()
        ctrl.shutdown()
        return
    try:
        from ishara import webui
    except Exception as e:                                      # web UI unavailable: fall back
        ctypes.windll.user32.MessageBoxW(None, f"Web interface unavailable ({e}). Using classic UI.", "iShara", 0x30)
        from ishara.ui.main_window import MainWindow
        MainWindow(ctrl).mainloop()
        ctrl.shutdown()
        return
    webui.run(ctrl)


if __name__ == "__main__":
    main()
