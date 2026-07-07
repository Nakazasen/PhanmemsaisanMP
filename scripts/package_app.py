import subprocess
import os
import sys
import shutil

def package():
    print("Bắt đầu đóng gói MP2027 Manager...")
    
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
        "--noconsole",
        "--hide-console", "minimize-late",
        "--onefile",
        f"--icon={icon_path}",
        "--add-data", "assets;assets",
        "--add-data", "docs\\MP2027;docs\\MP2027",
        "--name", "MP2027_Manager",
        "src/universal_app.py"
    ]
    
    print(f"Đang chạy lệnh: {' '.join(cmd)}")
    
    try:
        subprocess.run(cmd, check=True)
        dist_docs = os.path.join(project_root, "dist", "docs", "MP2027")
        if os.path.exists(dist_docs):
            shutil.rmtree(dist_docs)
        shutil.copytree(os.path.join(project_root, "docs", "MP2027"), dist_docs)
        print("\nTHÀNH CÔNG! Đã đóng gói xong.")
        print(f"Tệp chạy nằm tại: {os.path.join(project_root, 'dist', 'MP2027_Manager.exe')}")
        print(f"Dữ liệu runtime có thể chỉnh sửa đã được chép vào: {dist_docs}")
    except subprocess.CalledProcessError as e:
        print(f"\nLỗi khi đóng gói: {e}")

if __name__ == "__main__":
    package()
