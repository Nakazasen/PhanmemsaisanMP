"""Điểm vào nhẹ cho ứng dụng MP2027 trên máy tính để bàn đã đóng băng."""

import sys
import os
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _consume_wait_for_pid(argv: list[str]) -> int | None:
    if "--wait-for-pid" not in argv:
        return None
    index = argv.index("--wait-for-pid")
    if index + 1 >= len(argv):
        raise ValueError("Thiếu PID của phiên bản MP2027 cũ.")
    try:
        pid = int(argv[index + 1])
    except ValueError as exc:
        raise ValueError("PID của phiên bản MP2027 cũ không hợp lệ.") from exc
    if pid <= 0 or pid == os.getpid():
        raise ValueError("PID của phiên bản MP2027 cũ không hợp lệ.")
    del argv[index:index + 2]
    return pid


def _process_is_running(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return False
    return True


def _wait_for_process_exit(pid: int, *, timeout_seconds: float = 120.0) -> bool:
    deadline = time.monotonic() + timeout_seconds
    while _process_is_running(pid):
        if time.monotonic() >= deadline:
            return False
        time.sleep(0.1)
    return True


def main() -> int:
    try:
        wait_pid = _consume_wait_for_pid(sys.argv)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    if wait_pid is not None and not _wait_for_process_exit(wait_pid):
        print("Phiên bản MP2027 cũ không thể đóng trong thời gian cho phép.", file=sys.stderr)
        return 2
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
