"""Bluetooth data link to the headband (runs in its own thread).

The ESP32 is already a Windows Bluetooth mouse. This link opens a second GATT
channel on the same device to receive live head data and send settings.
Reconnects automatically. A simulator is provided for testing without hardware.
"""
import asyncio
import math
import queue
import threading
import time

from . import protocol
from .protocol import Sample

STALE_S = 1.0   # no packet for this long = data lost


class LinkBase:
    def __init__(self):
        self.lock = threading.Lock()
        self.sample = None
        self.last_rx = 0.0
        self.state = "searching"        # searching | connecting | connected | error
        self.error = ""
        self.device_conf = None
        self.on_sample = None            # optional callback(sample), called from link thread

    # ----- read side (UI thread)
    def latest(self):
        with self.lock:
            return self.sample, self.last_rx

    def data_alive(self):
        return self.state == "connected" and time.time() - self.last_rx < STALE_S

    def _push(self, s: Sample):
        with self.lock:
            self.sample = s
            self.last_rx = time.time()
        if self.on_sample:
            self.on_sample(s)

    # ----- commands
    def send(self, cmd: str):
        raise NotImplementedError

    def set_model(self, model: dict, save=True):
        self.send("SET " + protocol.model_to_text(model))
        if save:
            self.send("SAVE")

    def hid(self, action: str) -> bool:
        """Ask the headband to click as a real Bluetooth mouse. Returns False if it
        can't (no headband), so the caller falls back to a software click."""
        return False


class BleLink(LinkBase):
    def __init__(self):
        super().__init__()
        self.cmds = queue.Queue()
        self.stop_flag = False
        self.thread = threading.Thread(target=self._run, daemon=True, name="ble-link")

    def start(self):
        self.thread.start()
        return self

    def stop(self):
        self.stop_flag = True

    def send(self, cmd: str):
        self.cmds.put(cmd)

    def hid(self, action: str) -> bool:
        if self.state != "connected" or not self.data_alive():
            return False
        self.send("HID " + action)
        return True

    def _run(self):
        asyncio.run(self._main())

    async def _main(self):
        try:
            from bleak import BleakClient, BleakScanner
        except Exception as e:                       # package missing
            self.state, self.error = "error", f"bleak not installed: {e}"
            return
        while not self.stop_flag:
            try:
                self.state = "searching"
                dev = await BleakScanner.find_device_by_name(protocol.DEVICE_NAME, timeout=6.0)
                if not dev:
                    await asyncio.sleep(1.5)
                    continue
                self.state = "connecting"
                disconnected = asyncio.Event()
                async with BleakClient(dev, disconnected_callback=lambda c: disconnected.set()) as client:
                    def on_data(_h, data):
                        try:
                            self._push(protocol.unpack_sample(bytes(data)))
                        except ValueError:
                            pass                         # ignore malformed packet
                    await client.start_notify(protocol.DATA_UUID, on_data)
                    try:
                        conf = await client.read_gatt_char(protocol.CONF_UUID)
                        self.device_conf = protocol.text_to_model(bytes(conf).decode(errors="ignore"))
                    except Exception:
                        pass
                    self.state, self.error = "connected", ""
                    while not disconnected.is_set() and not self.stop_flag:
                        try:
                            cmd = self.cmds.get_nowait()
                            await client.write_gatt_char(protocol.CMD_UUID, cmd.encode(), response=True)
                        except queue.Empty:
                            await asyncio.sleep(0.03)
            except Exception as e:
                self.state, self.error = "searching", str(e)
                await asyncio.sleep(2.0)
        self.state = "error"


class SimLink(LinkBase):
    """Fake headband for testing: slow figure-eight head motion."""

    def __init__(self):
        super().__init__()
        self.paused = False
        self.model = dict(protocol.DEFAULT_MODEL)
        self.state = "connected"
        self.device_conf = dict(self.model)

    def start(self):
        threading.Thread(target=self._run, daemon=True, name="sim-link").start()
        return self

    def send(self, cmd: str):
        if cmd == "PAUSE":
            self.paused = True
        elif cmd == "RESUME":
            self.paused = False
        elif cmd.startswith("SET "):
            self.model = protocol.text_to_model(cmd[4:])

    def _run(self):
        from .model import compute_move
        seq, t0 = 0, time.time()
        while True:
            t = time.time() - t0
            pitch = 14 * math.sin(t * 0.7)
            roll = 18 * math.sin(t * 0.45)
            dx, dy = (0, 0) if self.paused else compute_move(pitch, roll, self.model)
            self._push(Sample(pitch, roll, 3.0, dx, dy, self.paused, False, True, seq))
            seq += 1
            time.sleep(1 / 30)
