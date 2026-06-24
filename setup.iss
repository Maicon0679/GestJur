; ============================================================
;  MF System Jur — Script de Instalação (Inno Setup 6.x)
;  Gera: dist\MFSystemJur_Instalador.exe
; ============================================================

[Setup]
AppName=MF System Jur
AppVersion=2.0
AppVerName=MF System Jur 2.0
AppPublisher=MF System Jur
AppPublisherURL=https://
AppSupportURL=https://
AppUpdatesURL=https://
DefaultDirName={autopf}\MF System Jur
DefaultGroupName=MF System Jur
AllowNoIcons=yes
; Saída
OutputDir=dist
OutputBaseFilename=MFSystemJur_Instalador
; Compressão máxima
Compression=lzma2/ultra64
SolidCompression=yes
; Visual moderno
WizardStyle=modern
; Permite instalar sem admin (na pasta do usuário)
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
; Metadados
VersionInfoVersion=2.0.0.0
VersionInfoDescription=MF System Jur — Sistema de Gestão Jurídica
VersionInfoCopyright=2026 MF System Jur
UninstallDisplayName=MF System Jur
UninstallDisplayIcon={app}\MFSystemJur.exe
; Desinstalar versão anterior automaticamente
CloseApplications=yes
RestartApplications=no

[Languages]
Name: "brazilianportuguese"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"

[Tasks]
Name: "desktopicon"; \
    Description: "Criar atalho na Área de Trabalho"; \
    GroupDescription: "Atalhos adicionais:"; \
    Flags: checked
Name: "startmenuicon"; \
    Description: "Criar entrada no Menu Iniciar"; \
    GroupDescription: "Atalhos adicionais:"; \
    Flags: checked

[Files]
Source: "dist\MFSystemJur.exe"; \
    DestDir: "{app}"; \
    DestName: "MFSystemJur.exe"; \
    Flags: ignoreversion

[Icons]
; Menu Iniciar
Name: "{group}\MF System Jur"; \
    Filename: "{app}\MFSystemJur.exe"; \
    Comment: "Sistema de Gestão Jurídica"; \
    Tasks: startmenuicon

Name: "{group}\Desinstalar MF System Jur"; \
    Filename: "{uninstallexe}"; \
    Tasks: startmenuicon

; Área de Trabalho
Name: "{autodesktop}\MF System Jur"; \
    Filename: "{app}\MFSystemJur.exe"; \
    Comment: "Sistema de Gestão Jurídica"; \
    Tasks: desktopicon

[Run]
; Oferecer para iniciar após instalação
Filename: "{app}\MFSystemJur.exe"; \
    Description: "{cm:LaunchProgram,MF System Jur}"; \
    Flags: nowait postinstall skipifsilent

[UninstallRun]
; Garante que o app está fechado antes de desinstalar
Filename: "taskkill.exe"; \
    Parameters: "/f /im MFSystemJur.exe"; \
    Flags: runhidden waituntilterminated

[Code]
function InitializeSetup(): Boolean;
var
  ResultCode: Integer;
begin
  Result := True;
end;
