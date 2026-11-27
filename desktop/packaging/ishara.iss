; Inno Setup script - iShara Windows installer (complete offline installer).
; Built by packaging\build.ps1, which passes /DAppVersion=x.y.z.
;
; Installs:  {app}\iShara.exe + _internal\   (PyInstaller one-folder build)
;            {app}\models\                    (Vosk + Whisper speech models)
; Never touches %APPDATA%\Ishara (profiles, calibration, settings), so updates keep them.

#ifndef AppVersion
  #define AppVersion "0.0.0"
#endif
#define AppName "iShara"
#define AppExe "iShara.exe"
#define Root ".."

[Setup]
; Fixed AppId: every version upgrades the same installation in place.
AppId={{6F1B7C2E-3A4D-4E8F-9B21-1C5D7A9E3F40}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher=iShara
AppPublisherURL=https://github.com/muradahmed23/ishara
AppSupportURL=https://github.com/muradahmed23/ishara/issues
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
; Per-user install by default: no administrator prompt. Users may choose "all users" (UAC).
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0.17763
OutputDir={#Root}\dist\installer
OutputBaseFilename=iShara-Setup-{#AppVersion}
SetupIconFile={#Root}\assets\icon.ico
UninstallDisplayIcon={app}\{#AppExe}
; Model weights are already dense; strong LZMA settings only cost memory (ISCC is 32-bit).
Compression=lzma2/normal
SolidCompression=no
LZMAUseSeparateProcess=yes
WizardStyle=modern
DisableProgramGroupPage=yes
DisableReadyPage=yes
DisableWelcomePage=no
CloseApplications=yes
RestartApplications=no
VersionInfoVersion={#AppVersion}

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Shortcuts:"

[InstallDelete]
; Remove the previous program files on upgrade (models and user data are kept).
Type: filesandordirs; Name: "{app}\_internal"

[Files]
Source: "{#Root}\dist\iShara\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "{#Root}\models\vosk-model-small-en-us-0.15\*"; DestDir: "{app}\models\vosk-model-small-en-us-0.15"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "{#Root}\models\whisper-base.en\*"; DestDir: "{app}\models\whisper-base.en"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "{#Root}\models\whisper-small.en\*"; DestDir: "{app}\models\whisper-small.en"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "{#Root}\models\MODELS.sha256"; DestDir: "{app}\models"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\{#AppExe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExe}"; Tasks: desktopicon

[Run]
; Start iShara when setup finishes (first-run welcome opens automatically).
Filename: "{app}\{#AppExe}"; Description: "Start iShara"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}\_internal"
