import subprocess
import os
import sys

def package():
    print("Starting packaging process for MP2027 Manager...")
    
    # Ensure we are at project root
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.chdir(project_root)
    
    icon_path = os.path.join("assets", "app_icon.ico")
    if not os.path.exists(icon_path):
        print(f"Error: Icon not found at {icon_path}")
        return

    # PyInstaller command
    cmd = [
        "pyinstaller",
        "--noconsole",
        "--hide-console", "minimize-late",
        "--onefile",
        f"--icon={icon_path}",
        "--add-data", "assets;assets",
        "--add-data", "FORM.xlsx;.",
        "--name", "MP2027_Manager",
        "src/universal_app.py"
    ]
    
    print(f"Running command: {' '.join(cmd)}")
    
    try:
        subprocess.run(cmd, check=True)
        print("\nSUCCESS! Packaging complete.")
        print(f"Executable is located at: {os.path.join(project_root, 'dist', 'MP2027_Manager.exe')}")
    except subprocess.CalledProcessError as e:
        print(f"\nERROR during packaging: {e}")

if __name__ == "__main__":
    package()
