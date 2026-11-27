# Speech models

Not stored in git (≈ 670 MB). Download them with:

```powershell
.\scripts\setup.ps1          # from the repository root
```

| Folder | Used for | Source |
|---|---|---|
| `vosk-model-small-en-us-0.15/` | voice commands (offline, fast grammar) | [alphacephei.com/vosk/models](https://alphacephei.com/vosk/models) |
| `whisper-base.en/` | dictation (default) | faster-whisper `base.en` |
| `whisper-small.en/` | dictation (best accuracy, optional) | faster-whisper `small.en` |
