# PyInstaller runtime hook.
# faster-whisper imports PyAV ("av", ~67 MB) at start-up, but only uses it to decode audio
# FILES. iShara always passes microphone samples as a NumPy array, so PyAV is never called
# (faster_whisper/transcribe.py: decode_audio only runs when audio is not an ndarray).
# PyAV is excluded from the build and this empty stand-in satisfies the import.
import sys
import types

if "av" not in sys.modules:
    try:
        import av  # noqa: F401  (present when running from source)
    except ImportError:
        stub = types.ModuleType("av")
        stub.__doc__ = "iShara stub: PyAV is not bundled (audio is never decoded from files)."
        sys.modules["av"] = stub
