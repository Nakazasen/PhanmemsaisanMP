import subprocess
import os
import sys
import shutil

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
    
    print(f"Running command: {' '.join(cmd)}")
    
    try:
        subprocess.run(cmd, check=True)
        dist_docs = os.path.join(project_root, "dist", "docs", "MP2027")
        if os.path.exists(dist_docs):
            shutil.rmtree(dist_docs)
        shutil.copytree(os.path.join(project_root, "docs", "MP2027"), dist_docs)
        print("\nSUCCESS! Packaging complete.")
        print(f"Executable is located at: {os.path.join(project_root, 'dist', 'MP2027_Manager.exe')}")
        print(f"Editable runtime data copied to: {dist_docs}")
    except subprocess.CalledProcessError as e:
        print(f"\nERROR during packaging: {e}")

if __name__ == "__main__":
    package()
