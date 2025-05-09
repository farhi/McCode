; Script generated by the Inno Setup Script Wizard.
; SEE THE DOCUMENTATION FOR DETAILS ON CREATING INNO SETUP SCRIPT FILES!

#define MyAppName "McXtrace Application bundle"
#define MyAppVersion "@VERSION@"
#define MyAppPublisher "McXtrace"
#define MyAppURL "http://www.mcxtrace.org"
#define MyAppExeName "McXtrace-Metapackage-@VERSION@-win64.exe"


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
OutputBaseFilename=McXtrace-Metapackage-@VERSION@-win64
Compression=lzma
SolidCompression=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Files]
Source: "python-install.bat"; DestDir: "{tmp}"
Source: "environment.yml"; DestDir: "{tmp}"
Source: "docupdate.bat"; DestDir: "{tmp}"
Source: "dist\mcxtrace-NSIS64-@VERSION@-mingw64.exe"; DestDir: "{tmp}"
Source: "dist\mcxtrace-comps-NSIS64-@VERSION@-mingw64.exe"; DestDir: "{tmp}"
Source: "dist\mcxtrace-manuals-NSIS64-@VERSION@-mingw64.exe"; DestDir: "{tmp}"
Source: "dist\mcxtrace-tools-python-mxrun-NSIS64-@VERSION@-mingw64.exe"; DestDir: "{tmp}"
Source: "dist\mcxtrace-tools-python-mxtest-NSIS64-@VERSION@-mingw64.exe"; DestDir: "{tmp}"
Source: "dist\mcxtrace-tools-python-mxgui-NSIS64-@VERSION@-mingw64.exe"; DestDir: "{tmp}"
Source: "dist\mcxtrace-tools-python-mccodelib-NSIS64-@VERSION@-mingw64.exe"; DestDir: "{tmp}"
Source: "dist\mcxtrace-tools-python-mxplot-pyqtgraph-NSIS64-@VERSION@-mingw64.exe"; DestDir: "{tmp}"
Source: "dist\mcxtrace-tools-python-mxplot-matplotlib-NSIS64-@VERSION@-mingw64.exe"; DestDir: "{tmp}"
Source: "dist\mcxtrace-tools-python-mxdisplay-webgl-NSIS64-@VERSION@-mingw64.exe"; DestDir: "{tmp}"
Source: "dist\mcxtrace-tools-python-mxdisplay-pyqtgraph-NSIS64-@VERSION@-mingw64.exe"; DestDir: "{tmp}"
Source: "dist\mcxtrace-tools-python-mxdisplay-matplotlib-NSIS64-@VERSION@-mingw64.exe"; DestDir: "{tmp}"
Source: "dist\mcxtrace-tools-python-mxdoc-NSIS64-@VERSION@-mingw64.exe"; DestDir: "{tmp}"
Source: "Support\Miniforge3-Windows-x86_64.exe"; DestDir: "{tmp}"

[Run]
Filename: "{tmp}\python-install.bat"
Filename: "{tmp}\mcxtrace-NSIS64-@VERSION@-mingw64.exe"; Parameters: "/S"
Filename: "{tmp}\mcxtrace-comps-NSIS64-@VERSION@-mingw64.exe"; Parameters: "/S"
Filename: "{tmp}\mcxtrace-manuals-NSIS64-@VERSION@-mingw64.exe"; Parameters: "/S"
Filename: "{tmp}\mcxtrace-tools-python-mxrun-NSIS64-@VERSION@-mingw64.exe"; Parameters: "/S"
Filename: "{tmp}\mcxtrace-tools-python-mxtest-NSIS64-@VERSION@-mingw64.exe"; Parameters: "/S"
Filename: "{tmp}\mcxtrace-tools-python-mxgui-NSIS64-@VERSION@-mingw64.exe"; Parameters: "/S"
Filename: "{tmp}\mcxtrace-tools-python-mccodelib-NSIS64-@VERSION@-mingw64.exe"; Parameters: "/S"
Filename: "{tmp}\mcxtrace-tools-python-mxplot-pyqtgraph-NSIS64-@VERSION@-mingw64.exe"; Parameters: "/S"
Filename: "{tmp}\mcxtrace-tools-python-mxplot-matplotlib-NSIS64-@VERSION@-mingw64.exe"; Parameters: "/S"
Filename: "{tmp}\mcxtrace-tools-python-mxdisplay-webgl-NSIS64-@VERSION@-mingw64.exe"; Parameters: "/S"
Filename: "{tmp}\mcxtrace-tools-python-mxdisplay-pyqtgraph-NSIS64-@VERSION@-mingw64.exe"; Parameters: "/S"
Filename: "{tmp}\mcxtrace-tools-python-mxdisplay-matplotlib-NSIS64-@VERSION@-mingw64.exe"; Parameters: "/S"
Filename: "{tmp}\mcxtrace-tools-python-mxdoc-NSIS64-@VERSION@-mingw64.exe"; Parameters: "/S"
Filename: "{tmp}\docupdate.bat";

; NOTE: Don't use "Flags: ignoreversion" on any shared system files
