#define MyAppName "ThermalPulse"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "Tejinder Pal Singh"
#define MyAppURL "https://github.com/Teji007/ThermalPulse"
#define MyAppExeName "ThermalPulse.exe"

[Setup]
AppId={{8D6E4A21-7C3F-4E9B-A54C-91F208C3E1A4}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}/issues
AppUpdatesURL={#MyAppURL}/releases
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
LicenseFile=LICENSE
InfoBeforeFile=Disclaimer.txt
OutputDir=release
OutputBaseFilename=ThermalPulse_Setup_v{#MyAppVersion}
SetupIconFile=assets\app.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
AppMutex=Global\ThermalPulse_SingleInstance_Mutex
CloseApplications=force

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Additional icons:"
Name: "autostart"; Description: "Start {#MyAppName} minimized at Windows logon (Admin, no UAC prompt)"; GroupDescription: "Startup:"

[Files]
Source: "dist\ThermalPulse\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "LICENSE"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\Uninstall {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "powershell.exe"; Parameters: "-NoProfile -ExecutionPolicy Bypass -Command ""$a = New-ScheduledTaskAction -Execute '{app}\{#MyAppExeName}' -Argument '--minimized' -WorkingDirectory '{app}'; $t = New-ScheduledTaskTrigger -AtLogOn; $s = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit (New-TimeSpan -Days 0); $p = New-ScheduledTaskPrincipal -GroupId 'BUILTIN\Administrators' -RunLevel Highest; Register-ScheduledTask -TaskName 'ThermalPulseAutoStart' -Action $a -Trigger $t -Settings $s -Principal $p -Force"""; Flags: runhidden waituntilterminated; Tasks: autostart
Filename: "{app}\{#MyAppExeName}"; Description: "Launch {#MyAppName}"; Flags: nowait postinstall skipifsilent shellexec

[UninstallRun]
Filename: "schtasks.exe"; Parameters: "/Delete /TN ""ThermalPulseAutoStart"" /F"; Flags: runhidden; RunOnceId: "RemoveThermalPulseTask"
Filename: "taskkill.exe"; Parameters: "/IM {#MyAppExeName} /F"; Flags: runhidden; RunOnceId: "KillThermalPulse"

[Code]
procedure KillRunningApp;
var
  ResultCode: Integer;
begin
  Exec('taskkill.exe', '/IM {#MyAppExeName} /F', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
end;

function InitializeSetup(): Boolean;
begin
  KillRunningApp;
  Result := True;
end;

function InitializeUninstall(): Boolean;
begin
  KillRunningApp;
  Result := True;
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  DataDir: String;
begin
  if CurUninstallStep = usPostUninstall then
  begin
    DataDir := ExpandConstant('{localappdata}\{#MyAppName}');
    if DirExists(DataDir) then
    begin
      if MsgBox('Do you also want to delete your saved ThermalPulse settings and telemetry logs?' + #13#10 + DataDir,
                mbConfirmation, MB_YESNO) = IDYES then
      begin
        DelTree(DataDir, True, True, True);
      end;
    end;
  end;
end;