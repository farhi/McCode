; Script generated by the Inno Setup Script Wizard.
; SEE THE DOCUMENTATION FOR DETAILS ON CREATING INNO SETUP SCRIPT FILES!

#define MyAppName "McXtrace CONDA Application bundle"
#define MyAppVersion "@VERSION@"
#define MyAppPublisher "McXtrace"
#define MyAppURL "http://www.mcxtrace.org"
#define MyAppExeName "McXtrace-Metapackage-@VERSION@-CONDA-win64.exe"


[Setup]
; NOTE: The value of AppId uniquely identifies this application.
; Do not use the same AppId value in installers for other applications.
; (To generate a new GUID, click Tools | Generate GUID inside the IDE.)
AppId={{9EB3C862-0C7C-489E-841F-76B6555E580A}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
CreateAppDir=no
LicenseFile=license_mcx\COPYING.txt
InfoBeforeFile=license_mcx\Welcome.txt
InfoAfterFile=license_mcx\Description.txt
OutputBaseFilename=McXtrace-Metapackage-@VERSION@-CONDA-win64
Compression=lzma
SolidCompression=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Files]
Source: "python-install.bat"; DestDir: "{tmp}"
Source: "mcxtrace-environment.yml"; DestDir: "{tmp}"
Source: "docupdate.bat"; DestDir: "{tmp}"
Source: "Support\Miniforge3-Windows-x86_64.exe"; DestDir: "{tmp}"

[Run]
Filename: "{tmp}\python-install.bat"
Filename: "{tmp}\docupdate.bat";

; NOTE: Don't use "Flags: ignoreversion" on any shared system files
