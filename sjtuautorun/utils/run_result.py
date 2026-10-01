"""Read result-page text with Windows' installed OCR, without another dependency."""
import json
import os
import subprocess
from pathlib import Path


def read_result_screen(path, timeout=15):
    powershell = Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32/WindowsPowerShell/v1.0/powershell.exe"
    result = subprocess.run(
        [str(powershell), "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(Path(__file__).with_name("read_screen.ps1")),
         "-Path", str(Path(path).resolve())],
        capture_output=True, encoding="utf-8", timeout=timeout, check=True,
        creationflags=subprocess.CREATE_NO_WINDOW)
    lines = json.loads(result.stdout)
    return "\n".join("".join(line.split()) for line in (lines if isinstance(lines, list) else [lines]))


def is_run_result(text):
    # Require result-only labels; mileage on a live map does not prove recording ended.
    compact = "".join(text.split())
    return (any(label in compact for label in ("实际跑步", "跑步结果", "运动数据", "计入成绩"))
            and ("公里" in compact or "km" in compact.lower()))


def is_sports_home(text):
    compact = "".join(text.split())
    return "运动健康" in compact and any(label in compact for label in ("总公里", "达标公里"))
