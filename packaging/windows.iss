#define AppVersion GetEnv("HORAS_VERSION")
[Setup]
AppId={{D3F66A80-7019-46D8-8353-80B95565D9F0}
AppName=HorasJogadas
AppVersion={#AppVersion}
AppPublisher=JoaoPPolli
AppPublisherURL=https://github.com/JoaoPPolli/HorasJogadas
AppSupportURL=https://github.com/JoaoPPolli/HorasJogadas
AppUpdatesURL=https://github.com/JoaoPPolli/HorasJogadas/releases/latest
DefaultDirName={localappdata}\Programs\HorasJogadas
DefaultGroupName=HorasJogadas
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=..\release
OutputBaseFilename=HorasJogadas-Windows-Setup
SetupIconFile=..\icon.ico
UninstallDisplayIcon={app}\HorasJogadas.exe
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
CloseApplications=yes
RestartApplications=no
[Languages]
Name: "brazilianportuguese"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"
[Tasks]
Name: "desktopicon"; Description: "Criar atalho na área de trabalho"; Flags: unchecked
[Files]
Source: "..\dist\HorasJogadas\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
[Icons]
Name: "{group}\HorasJogadas"; Filename: "{app}\HorasJogadas.exe"
Name: "{autodesktop}\HorasJogadas"; Filename: "{app}\HorasJogadas.exe"; Tasks: desktopicon
[Run]
Filename: "{app}\HorasJogadas.exe"; Description: "Abrir HorasJogadas"; Flags: nowait postinstall skipifsilent

Filename: "{app}\HorasJogadas.exe"; Flags: nowait skipifnotsilent; Check: RestartRequested
[Code]
function RestartRequested: Boolean;
var I: Integer;
begin
  Result := False;
  for I := 1 to ParamCount do
    if CompareText(ParamStr(I), '/RESTARTAPP') = 0 then Result := True;
end;
