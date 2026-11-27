"""Offline voice control (runs in background threads).

Command mode   - Vosk, restricted to the command phrases (grammar): instant, and
                 normal talking does not trigger actions.
Dictation mode - Vosk detects where each sentence starts and ends (endpointing) and
                 shows live partial text; the audio of the finished sentence is then
                 transcribed by Whisper (faster-whisper, offline) for accurate text
                 with punctuation and capitals. Falls back to Vosk text if Whisper
                 is unavailable.

Events are delivered to on_event(kind, payload) from the voice threads:
  ("state", "listening"|"off"|"error"), ("partial", text), ("busy", bool),
  ("command", (phrase, action)), ("dictation", text), ("mode", "command"|"dictation"),
  ("error", message)
"""
import json
import os
import queue
import re
import threading

from .paths import MODELS_DIR, USER_DIR

MODEL_DIR = os.path.join(MODELS_DIR, "vosk-model-small-en-us-0.15")
WHISPER_DIR = os.path.join(MODELS_DIR, "whisper-{}")
WHISPER_MODELS = {"base.en": "Standard (fast)", "small.en": "Best accuracy (slower)"}
RATE = 16000
MAX_UTTERANCE_S = 12      # never let one dictation chunk grow longer than this
SILENCE_END_S = 0.8       # this much quiet after speech ends the sentence
LOG_FILE = os.path.join(USER_DIR, "voice.log")


def vlog(msg):
    """Small diagnostic log for dictation timing (kept under ~200 KB)."""
    try:
        os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
        if os.path.exists(LOG_FILE) and os.path.getsize(LOG_FILE) > 200_000:
            os.replace(LOG_FILE, LOG_FILE + ".old")
        import time as _t
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(_t.strftime("%H:%M:%S ") + msg + "\n")
    except Exception:
        pass

# Spoken punctuation in dictation mode (works on Vosk and Whisper output)
# The leading [\s.,!?]* also swallows punctuation Whisper already added ("world. Period.")
_P = r"[\s.,!?]*\b"
PUNCT = [(_P + r"(comma|kama|coma)\b[.,]?", ","), (_P + r"(period|full stop)\b[.,]?", "."),
         (_P + r"question mark\b[.,?]?", "?"), (_P + r"exclamation mark\b[.,!]?", "!"),
         (_P + r"new line\b[.,]?\s*", "\n")]

# Words Whisper should prefer (names it would otherwise misspell, command words)
HOTWORDS = "Ishara, comma, period, question mark, new line"

# Whisper sometimes invents these on noise or silence
HALLUCINATIONS = {"thank you", "thanks for watching", "thank you for watching", "you", "bye"}


def list_microphones():
    """[(index, name)] of input devices (MME host API to avoid duplicates)."""
    try:
        import sounddevice as sd
        apis = sd.query_hostapis()
        mme = next((i for i, a in enumerate(apis) if "MME" in a["name"]), None)
        return [(i, d["name"]) for i, d in enumerate(sd.query_devices())
                if d["max_input_channels"] > 0 and (mme is None or d["hostapi"] == mme)]
    except Exception:
        return []


def whisper_available(name="base.en"):
    try:
        import faster_whisper  # noqa: F401
    except Exception:
        return False
    return os.path.isdir(WHISPER_DIR.format(name))


def match_command(text, commands):
    """Map recognized text to (phrase, action). Exact match first, then the
    longest phrase contained in the text. Returns None if nothing matches."""
    text = text.strip().lower()
    if not text or text == "[unk]":
        return None
    if text in commands:
        return text, commands[text]
    best = None
    for phrase in commands:
        if f" {phrase} " in f" {text} " and (best is None or len(phrase) > len(best)):
            best = phrase
    return (best, commands[best]) if best else None


def apply_punctuation(text):
    for pattern, mark in PUNCT:
        text = re.sub(pattern, mark, text, flags=re.IGNORECASE)
    return text.strip(" ")


def words(text):
    return re.sub(r"[^a-z ]", " ", text.lower()).split()


def split_at_stop(text, stop):
    """('text before the stop phrase', found?) - tolerant of Whisper punctuation/case."""
    stop_words = stop.lower().split()
    tokens = text.split()
    norm = [re.sub(r"[^a-z]", "", t.lower()) for t in tokens]
    for i in range(len(norm) - len(stop_words) + 1):
        if norm[i:i + len(stop_words)] == stop_words:
            return " ".join(tokens[:i]).rstrip(" ,"), True
    return text, False


class WhisperWorker:
    """Transcribes finished sentences in order, in its own thread."""

    def __init__(self, name, on_event, vocabulary=()):
        self.name, self.on_event = name, on_event
        # the user's own names/words are given to Whisper as hints, before the built-ins
        words_ = [w.strip() for w in vocabulary if w and w.strip()]
        self.hotwords = ", ".join(words_ + [HOTWORDS])
        self.jobs = queue.Queue()
        self.model = None
        self.ready = threading.Event()
        self.failed = False
        self.context = ""                 # recent text, helps Whisper with style/punctuation
        threading.Thread(target=self._run, daemon=True, name="whisper").start()

    def submit(self, audio, vosk_text, stop_phrase, stop_found):
        self.jobs.put((audio, vosk_text, stop_phrase, stop_found))

    def _run(self):
        try:
            from faster_whisper import WhisperModel
            threads = max(2, (os.cpu_count() or 4) - 2)
            self.model = WhisperModel(WHISPER_DIR.format(self.name), device="cpu",
                                      compute_type="int8", cpu_threads=threads)
        except Exception as e:
            self.failed = True
            self.on_event("error", f"Whisper unavailable, using basic dictation ({e})")
        self.ready.set()
        import numpy as np
        while True:
            audio, vosk_text, stop_phrase, stop_found = self.jobs.get()
            text = vosk_text
            if self.model is not None:
                self.on_event("busy", True)
                t0 = __import__("time").time()
                try:
                    pcm = np.frombuffer(audio, np.int16).astype(np.float32) / 32768.0
                    segs, _ = self.model.transcribe(
                        pcm, language="en", beam_size=1, vad_filter=True,
                        initial_prompt=self.context[-200:] or None,
                        hotwords=self.hotwords, condition_on_previous_text=False)
                    text = " ".join(s.text.strip() for s in segs).strip()
                except Exception as e:
                    self.on_event("error", f"Whisper failed, using basic text ({e})")
                    vlog(f"whisper error: {e!r}")
                    text = vosk_text
                finally:
                    self.on_event("busy", False)      # always clear "Writing..."
                vlog(f"whisper {len(audio) / (RATE * 2):.1f}s audio -> {__import__('time').time() - t0:.2f}s "
                     f"| vosk={vosk_text!r} | whisper={text!r} | queued={self.jobs.qsize()}")
            if " ".join(words(text)) in HALLUCINATIONS and not vosk_text:
                text = ""
            if stop_found:
                text, _ = split_at_stop(text, stop_phrase)
            text = apply_punctuation(text) if text else ""
            if text:
                self.context = (self.context + " " + text)[-400:]
                self.on_event("dictation", text)
            if stop_found:
                self.on_event("command", (stop_phrase, "dictation_off"))


class VoiceEngine:
    def __init__(self, on_event, commands, device=None, muted=None,
                 dictation_engine="whisper", whisper_model="base.en", vocabulary=()):
        self.on_event = on_event
        self.muted = muted or (lambda: False)   # True while the app itself is speaking
        self.commands = dict(commands)
        self.device = device
        self.mode = "command"
        self.audio = queue.Queue(maxsize=50)
        self.running = False
        self._switch = None
        self.whisper = None
        # Muted by voice ("mute microphone"): keep listening ONLY for the wake phrase,
        # otherwise the user could never turn it back on without hands.
        self.sleeping = False
        self.level = 0.0
        if dictation_engine == "whisper" and whisper_available(whisper_model):
            self.whisper = WhisperWorker(whisper_model, on_event, vocabulary)   # loads in background

    def available(self):
        return os.path.isdir(MODEL_DIR)

    def start(self):
        if self.running:
            return
        self.running = True
        threading.Thread(target=self._run, daemon=True, name="voice").start()

    def stop(self):
        self.running = False

    def set_mode(self, mode):
        self._switch = mode           # applied by the voice thread

    def set_commands(self, commands):
        self.commands = dict(commands)
        self._switch = self.mode      # rebuild grammar

    def _grammar(self):
        return json.dumps(sorted(self.commands.keys()) + ["[unk]"])

    def _stop_phrase(self):
        return next((p for p, a in self.commands.items() if a == "dictation_off"), "stop typing")

    def _run(self):
        try:
            import numpy as np
            import sounddevice as sd
            from vosk import KaldiRecognizer, Model, SetLogLevel
            SetLogLevel(-1)
        except Exception as e:
            self.on_event("error", f"Voice packages missing: {e}")
            self.on_event("state", "error")
            self.running = False
            return
        if not self.available():
            self.on_event("error", "Voice model not found in the models folder")
            self.on_event("state", "error")
            self.running = False
            return
        try:
            model = Model(MODEL_DIR)
            cmd_rec = KaldiRecognizer(model, RATE, self._grammar())
            dict_rec = KaldiRecognizer(model, RATE)

            def callback(indata, frames, t, status):
                try:
                    self.audio.put_nowait(bytes(indata))
                except queue.Full:
                    pass                               # drop audio rather than lag behind

            utter = bytearray()                        # audio of the current sentence
            noise, quiet, spoke = 0.01, 0.0, False     # end-of-speech detector state
            with sd.RawInputStream(samplerate=RATE, blocksize=4000, device=self.device,
                                   dtype="int16", channels=1, callback=callback):
                self.on_event("state", "listening")
                was_muted = False
                while self.running:
                    if self._switch:
                        self.mode, self._switch = self._switch, None
                        cmd_rec = KaldiRecognizer(model, RATE, self._grammar())
                        dict_rec.Reset()
                        utter.clear()
                        self.on_event("mode", self.mode)
                    try:
                        data = self.audio.get(timeout=0.3)
                    except queue.Empty:
                        continue
                    # live input level 0..1 for the waveform in the UI
                    pcm = np.frombuffer(data, np.int16).astype(np.float32)
                    self.level = min(1.0, float(np.sqrt(np.mean(pcm * pcm))) / 6000.0)
                    if self.muted():
                        was_muted = True               # ignore the app's own voice
                        continue
                    if was_muted:
                        was_muted = False
                        cmd_rec.Reset()
                        dict_rec.Reset()
                        utter.clear()

                    if self.sleeping:
                        if self.mode != "command":
                            self.mode = "command"
                        if cmd_rec.AcceptWaveform(data):
                            hit = match_command(json.loads(cmd_rec.Result()).get("text", ""),
                                                self.commands)
                            if hit and hit[1] == "mic_wake":
                                self.on_event("command", hit)
                        continue

                    if self.mode == "dictation":
                        utter.extend(data)
                        # Our own end-of-sentence detector (Vosk alone can miss it in a
                        # noisy room): learn the background level, then end the sentence
                        # after SILENCE_END_S of quiet that follows real speech.
                        lvl = self.level
                        if lvl < noise * 2.5 + 0.01:
                            noise = noise * 0.95 + lvl * 0.05
                            quiet += len(data) / (RATE * 2)
                        else:
                            quiet, spoke = 0.0, True
                        done = dict_rec.AcceptWaveform(data)
                        reason = "vosk"
                        if done:
                            text = json.loads(dict_rec.Result()).get("text", "")
                        elif spoke and quiet >= SILENCE_END_S:
                            done, reason = True, "silence"
                            text = json.loads(dict_rec.FinalResult()).get("text", "")
                        elif len(utter) > MAX_UTTERANCE_S * RATE * 2:
                            done, reason = True, "max-length"   # very long sentence: flush it
                            text = json.loads(dict_rec.FinalResult()).get("text", "")
                        elif not spoke and len(utter) > 3 * RATE * 2:
                            utter.clear()              # only background noise so far: drop it
                        if done:
                            vlog(f"sentence end ({reason}) {len(utter) / (RATE * 2):.1f}s "
                                 f"noise={noise:.3f} vosk={text!r}")
                            if spoke or text:
                                self._dictation_final(text, bytes(utter))
                            utter.clear()
                            quiet, spoke = 0.0, False
                        else:
                            part = json.loads(dict_rec.PartialResult()).get("partial", "")
                            if part:
                                self.on_event("partial", part)
                    else:
                        if cmd_rec.AcceptWaveform(data):
                            hit = match_command(json.loads(cmd_rec.Result()).get("text", ""),
                                                self.commands)
                            if hit:
                                self.on_event("command", hit)
                        else:
                            part = json.loads(cmd_rec.PartialResult()).get("partial", "")
                            if part and part != "[unk]":
                                self.on_event("partial", part)
        except Exception as e:
            self.on_event("error", f"Microphone error: {e}")
            self.on_event("state", "error")
            self.running = False
            return
        self.on_event("state", "off")

    def _dictation_final(self, vosk_text, audio):
        vosk_text = vosk_text.strip()
        if not vosk_text and len(audio) < RATE * 2 * 1.2:
            return                                     # short noise, nothing said
        stop = self._stop_phrase()
        _, stop_found = split_at_stop(vosk_text, stop)
        if stop_found:
            self.mode = "command"                      # stop typing what follows right away
        if self.whisper and not self.whisper.failed:
            self.whisper.submit(audio, vosk_text, stop, stop_found)
            return
        # basic dictation (no Whisper)
        text = vosk_text
        if stop_found:
            text, _ = split_at_stop(text, stop)
        text = apply_punctuation(text)
        if text:
            self.on_event("dictation", text)
        if stop_found:
            self.on_event("command", (stop, "dictation_off"))
