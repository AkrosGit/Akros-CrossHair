#ifndef AppSourceDir
  #error Debe definirse la carpeta de origen de la aplicacion (AppSourceDir).
#endif
#ifndef OutputDir
  #error Debe definirse la carpeta de salida del instalador (OutputDir).
#endif
#ifndef AppIconFile
  #error Debe definirse la ruta del icono de la aplicacion (AppIconFile).
#endif
#ifndef AppLicenseFile
  #error Debe definirse la ruta de la licencia de la aplicacion (AppLicenseFile).
#endif
#ifndef AppNoticeFile
  #error Debe definirse la ruta de los avisos de la aplicacion (AppNoticeFile).
#endif

#define AppName "Akro's CrossHair"
#define AppVersion "1.0.0"

[Setup]
AppId={{F95A1A7B-3C36-481E-AC1E-57E71C9F61B2}
AppName={#AppName}
AppVersion={#AppVersion}
DefaultDirName={localappdata}\Programs\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir={#OutputDir}
OutputBaseFilename=AkrosCrossHair-Setup
UninstallDisplayName={#AppName}
UninstallDisplayIcon={app}\AkrosCrossHair.exe
SetupIconFile={#AppIconFile}
LicenseFile={#AppLicenseFile}
CloseApplications=yes
Uninstallable=yes

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[Tasks]
Name: "desktopicon"; Description: "Crear un acceso directo en el escritorio"; GroupDescription: "Accesos directos adicionales:"; Flags: unchecked

[Files]
Source: "{#AppSourceDir}\AkrosCrossHair.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#AppLicenseFile}"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#AppNoticeFile}"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\AkrosCrossHair.exe"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\AkrosCrossHair.exe"; Tasks: desktopicon

[UninstallDelete]
Type: dirifempty; Name: "{app}"
