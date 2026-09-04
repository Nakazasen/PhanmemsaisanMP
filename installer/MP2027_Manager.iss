; Trình cài đặt Windows ban đầu cho MP2027 Manager
; Biên dịch bằng Inno Setup 6 sau khi chạy: py scripts/package_app.py
; Cài bộ ứng dụng onedir theo phiên bản; máy đích không cần cài Python.

#define AppName "MP2027 Manager"
#define AppVersion "0.1.8"
#define AppPublisher "MP2027"
#define LauncherExe "MP2027_Launcher.exe"
#define BundleDir "..\\release_artifacts\\install_bundle"

[Setup]
AppId={{9E4E0A87-1D0C-4A12-9F5C-93F65E4B2027}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
; Cài theo người dùng vì apps/<version>, current.json và .staging là trạng thái cập nhật
; có thể thay đổi, thuộc quyền sở hữu của người dùng thông thường.
DefaultDirName={localappdata}\\MP2027 Manager
DefaultGroupName={#AppName}
OutputDir=..\\release_artifacts
OutputBaseFilename=MP2027_Manager_Setup_{#AppVersion}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=lowest
UninstallDisplayName={#AppName}

[Languages]
; Bản dịch được ghim và kiểm tra đủ key so với Default.isl của Inno Setup 6.7.3.
Name: "vietnamese"; MessagesFile: "languages\Vietnamese.isl"

[Files]
Source: "{#BundleDir}\\*"; DestDir: "{app}"; Flags: recursesubdirs ignoreversion createallsubdirs

[Icons]
Name: "{autoprograms}\\{#AppName}"; Filename: "{app}\\{#LauncherExe}"
Name: "{autodesktop}\\{#AppName}"; Filename: "{app}\\{#LauncherExe}"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Tạo lối tắt trên màn hình nền"; GroupDescription: "Lối tắt bổ sung:"

[Run]
Filename: "{app}\\{#LauncherExe}"; Description: "Khởi chạy {#AppName}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Dữ liệu vận hành/dự án trong LocalAppData không bao giờ bị xóa tại đây.
Type: filesandordirs; Name: "{app}\\.staging"
