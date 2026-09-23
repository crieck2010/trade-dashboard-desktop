; Inno Setup installer for TradeDashboardDesktop.
; 1. Run build_exe.bat on your Windows PC to produce dist\TradeDashboardDesktop.exe
; 2. Open this file in Inno Setup and Compile -> installer lands in installer-output\

#define MyAppName "TradeDashboardDesktop"
#define MyAppVersion "0.1.0"
#define MyAppPublisher "crieck2010"
#define MyAppURL "https://github.com/crieck2010/trade-dashboard-desktop"
#define MyAppExeName "TradeDashboardDesktop.exe"

[Setup]
AppId={{9F2C4A1B-7D3E-4F8A-9C2B-1A5E6D7C8B9A}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
OutputDir=installer-output
OutputBaseFilename=TradeDashboardDesktop-Setup-{#MyAppVersion}
Compression=lzma
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; \
    GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; \
    Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; \
    Flags: nowait postinstall skipifsilent
