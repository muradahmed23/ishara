# Release manifest

`latest.json` is the **single source of truth** for the current release. It is read by:

- the **website** (download button, version, size, requirements, release notes),
- the **desktop app** (Settings → About → Check for updates).

Both read it from
`https://raw.githubusercontent.com/muradahmed23/ishara/main/release/latest.json`,
so publishing a release is: build → upload → edit this file → push. No redeploy, no hard-coded links.

| Field | Meaning |
|---|---|
| `version` | app version (must equal `desktop/ishara/__init__.py`) |
| `status` | `unreleased` → website shows **Coming soon**; `released` → download enabled |
| `installer.url` | GitHub Release asset URL |
| `installer.sha256` / `sizeBytes` | integrity + size shown to users and checked by the updater |
| `models` | speech models shipped inside the installer |

## Publishing a release

```powershell
cd desktop
.\packaging\build.ps1                                   # -> dist\installer\iShara-Setup-<v>.exe + release-draft.json
gh release create v<v> dist\installer\iShara-Setup-<v>.exe --title "iShara <v>" --notes-file ..\release\notes.md
```

Then copy `url`, `sha256`, `sizeBytes` from `release-draft.json` into `latest.json`,
set `"status": "released"` and `releaseDate`, commit and push.
GitHub Release assets may be up to 2 GB, so the complete offline installer (~700 MB) fits.
