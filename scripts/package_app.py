import subprocess
import os
import sys
import shutil


def _add_data_args(source: str, target: str) -> list[str]:
    args: list[str] = []
    if os.path.isdir(source):
        for root, _dirs, files in os.walk(source):
            for filename in files:
                if filename.startswith("~$"):
                    continue
                source_path = os.path.join(root, filename)
                relative_dir = os.path.relpath(root, source)
                target_dir = target if relative_dir == "." else os.path.join(target, relative_dir)
                args.extend(["--add-data", f"{source_path};{target_dir}"])
    elif os.path.exists(source) and not os.path.basename(source).startswith("~$"):
        args.extend(["--add-data", f"{source};{target}"])
    return args


def _copytree_without_excel_locks(source: str, target: str) -> None:
    if os.path.exists(target):
        shutil.rmtree(target)
    shutil.copytree(source, target, ignore=shutil.ignore_patterns("~$*"))


def package():
    print("Bắt đầu đóng gói MP2027 Manager dạng thư mục...")
    
    # Ensure we are at project root
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.chdir(project_root)
    
    icon_path = os.path.join("assets", "app_icon.ico")
    if not os.path.exists(icon_path):
        print(f"Lỗi: không tìm thấy icon tại {icon_path}")
        return

    # PyInstaller command
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--clean",
        "--noconfirm",
        "--noconsole",
        "--hide-console", "minimize-late",
        "--onedir",
        f"--icon={icon_path}",
        "--name", "MP2027_Portable",
        *_add_data_args("assets", "assets"),
        *_add_data_args(os.path.join("docs", "MP2027"), os.path.join("docs", "MP2027")),
        *_add_data_args("raw", "raw"),
        "src/universal_app.py"
    ]
    
    print(f"Đang chạy lệnh: {' '.join(cmd)}")
    
    try:
        subprocess.run(cmd, check=True)
        dist_root = os.path.join(project_root, "dist", "MP2027_Portable")
        dist_docs = os.path.join(dist_root, "docs", "MP2027")
        dist_raw = os.path.join(dist_root, "raw")
        _copytree_without_excel_locks(os.path.join(project_root, "docs", "MP2027"), dist_docs)
        _copytree_without_excel_locks(os.path.join(project_root, "raw"), dist_raw)
        print("\nTHÀNH CÔNG! Đã đóng gói xong.")
        print(f"Thư mục chương trình nằm tại: {dist_root}")
        print(f"Tệp chạy nằm tại: {os.path.join(dist_root, 'MP2027_Portable.exe')}")
        print(f"Dữ liệu runtime có thể chỉnh sửa đã được chép vào: {dist_docs} và {dist_raw}")
    except subprocess.CalledProcessError as e:
        print(f"\nLỗi khi đóng gói: {e}")

if __name__ == "__main__":
    package()
