"""Lightweight entrypoint for the frozen MP2027 desktop application."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def main() -> int:
    if "--health-check" in sys.argv[1:]:
        from src.services.runtime_health import (
            ensure_external_runtime_data,
            print_health_report,
        )

        frozen = bool(getattr(sys, "frozen", False))
        app_dir = Path(sys.executable).resolve().parent if frozen else ROOT
        bundled_root = Path(sys._MEIPASS) if frozen and hasattr(sys, "_MEIPASS") else ROOT
        runtime_root = ensure_external_runtime_data(
            app_dir,
            bundled_root,
            frozen=frozen,
        )
        return print_health_report(runtime_root)

    from src.universal_app import main as app_main

    return app_main()


if __name__ == "__main__":
    raise SystemExit(main())
