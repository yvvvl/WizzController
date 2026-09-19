; Per-user installer: no administrator privileges or code-signing certificate
; are required.  The installer intentionally keeps user settings in LocalAppData.
#define AppName "WizZ Desktop"
#define AppVersion GetEnv("WIZZ_INSTALLER_VERSION")
#define AppSource GetEnv("WIZZ_INSTALLER_SOURCE")
#define AppOutput GetEnv("WIZZ_INSTALLER_OUTPUT")

[Setup]
AppId={{A2F17A3E-B90A-4A1A-9AB2-D1036E0DA77E}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher=yvvvl
DefaultDirName={localappdata}\Programs\WizZ Desktop
DefaultGroupName=WizZ Desktop
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
OutputDir={#AppOutput}
OutputBaseFilename=WizZDesktop-v{#AppVersion}-windows-x64-setup
SetupIconFile=..\assets\icon_windows.ico
UninstallDisplayIcon={app}\WizZDesktop.exe
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
CloseApplications=yes
RestartApplications=no

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "launchafterinstall"; Description: "Launch WizZ Desktop after installation"; Flags: unchecked

[Files]
Source: "{#AppSource}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\WizZ Desktop"; Filename: "{app}\WizZDesktop.exe"; WorkingDir: "{app}"
Name: "{autodesktop}\WizZ Desktop"; Filename: "{app}\WizZDesktop.exe"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{app}\WizZDesktop.exe"; Description: "{cm:LaunchProgram,WizZ Desktop}"; Flags: nowait postinstall skipifsilent; Tasks: launchafterinstall
