import os
import runpy
import sys
from pathlib import Path


def _configure_runtime_root() -> None:
    if getattr(sys, "frozen", False):
        exe_path = Path(sys.executable).resolve()
        exe_dir = exe_path.parent
        candidates = [exe_dir, *exe_dir.parents]
        portable_root = next(
            (candidate for candidate in candidates if (candidate / "docs" / "MP2027").is_dir()),
            exe_path.parents[2],
        )
        os.chdir(portable_root)
        for path in (portable_root, exe_dir):
            text = str(path)
            if text not in sys.path:
                sys.path.insert(0, text)
        return

    project_root = Path(__file__).resolve().parents[1]
    os.chdir(project_root)
    text = str(project_root)
    if text not in sys.path:
        sys.path.insert(0, text)


_configure_runtime_root()

if __name__ == "__main__":
    # Legacy reference for previous packaging audits: from scripts.run_e2e import main
    runpy.run_module("scripts.run_e2e", run_name="__main__")
