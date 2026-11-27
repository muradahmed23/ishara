"""Spoken feedback with the built-in Windows voice (System.Speech, offline, no packages).

One PowerShell process stays open and reads lines from stdin, so speaking is fast.
say(text, then=fn) calls fn after the sentence has finished (speak-first-then-act).
While speaking, `speaking` is True so the microphone can ignore the app's own voice.
"""
import queue
import subprocess
import threading
import time

NO_WINDOW = 0x08000000
TAIL_S = 0.35            # keep the mic muted a little after speech ends (room echo)

PS_SCRIPT = r"""
Add-Type -AssemblyName System.Speech
$s = New-Object System.Speech.Synthesis.SpeechSynthesizer
$s.SetOutputToDefaultAudioDevice()
[Console]::Out.WriteLine('READY'); [Console]::Out.Flush()
while ($true) {
  $l = [Console]::In.ReadLine()
  if ($l -eq $null) { break }
  if ($l.StartsWith('!rate ')) { $s.Rate = [int]$l.Substring(6); continue }
  if ($l.StartsWith('!vol '))  { $s.Volume = [int]$l.Substring(5); continue }
  try { $s.Speak($l) } catch {}
  [Console]::Out.WriteLine('DONE'); [Console]::Out.Flush()
}
"""


class Speaker:
    def __init__(self, enabled=True, rate=1, volume=90):
        self.enabled = enabled
        self.rate, self.volume = rate, volume
        self.jobs = queue.Queue()
        self._busy_until = 0.0
        self._speaking = False
        self.proc = None
        self.ok = False
        threading.Thread(target=self._run, daemon=True, name="speech").start()

    @property
    def speaking(self):
        return self._speaking or time.time() < self._busy_until

    def say(self, text, then=None):
        """Speak text. If speech is off or unavailable, `then` runs immediately."""
        if not self.enabled or not text:
            if then:
                then()
            return
        self.jobs.put((text, then))

    def set_voice(self, rate=None, volume=None):
        if rate is not None:
            self.rate = int(rate)
            self.jobs.put(("!rate %d" % self.rate, None))
        if volume is not None:
            self.volume = int(volume)
            self.jobs.put(("!vol %d" % self.volume, None))

    def close(self):
        try:
            if self.proc:
                self.proc.stdin.close()
                self.proc.kill()
        except Exception:
            pass

    def _run(self):
        try:
            self.proc = subprocess.Popen(
                ["powershell", "-NoProfile", "-NoLogo", "-Command", PS_SCRIPT],
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                text=True, bufsize=1, creationflags=NO_WINDOW)
            self.ok = self.proc.stdout.readline().strip() == "READY"
        except Exception:
            self.ok = False
        if self.ok:
            self._write("!rate %d" % self.rate)
            self._write("!vol %d" % self.volume)
        while True:
            text, then = self.jobs.get()
            if not self.ok:
                if then:
                    then()
                continue
            if text.startswith("!"):
                self._write(text)
                continue
            # drop stale queued sentences so feedback never lags far behind
            while self.jobs.qsize() > 2:
                stale_text, stale_then = self.jobs.get_nowait()
                if stale_then:
                    stale_then()
            self._speaking = True
            try:
                self._write(text.replace("\n", " "))
                self.proc.stdout.readline()          # waits for DONE
            except Exception:
                self.ok = False
            self._speaking = False
            self._busy_until = time.time() + TAIL_S
            if then:
                then()

    def _write(self, line):
        self.proc.stdin.write(line + "\n")
        self.proc.stdin.flush()
