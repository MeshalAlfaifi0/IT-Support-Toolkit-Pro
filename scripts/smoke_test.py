"""اختبار بدء المصدر أو EXE مرتين واستعادة اللغة والثيم داخل بيانات مؤقتة."""

import argparse
import json
import os
import sqlite3
import subprocess
import sys
import tempfile
from contextlib import closing
from pathlib import Path


def run_once(command, root, folder):
    (folder / "smoke-result.json").unlink(missing_ok=True)
    env = os.environ.copy()
    env.update(IT_TOOLKIT_DATA_DIR=str(folder), QT_QPA_PLATFORM="offscreen")
    process = subprocess.Popen(
        [*command, "--smoke-test"],
        cwd=root,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        errors="replace",
    )
    try:
        output, errors = process.communicate(timeout=90)
    except subprocess.TimeoutExpired:
        # نوقف شجرة عملية الاختبار فقط، بما فيها طفل PyInstaller إن وُجد.
        subprocess.run(
            ["taskkill", "/PID", str(process.pid), "/T", "/F"], capture_output=True, timeout=10
        )
        process.communicate(timeout=10)
        raise RuntimeError("Startup smoke test timed out") from None
    if process.returncode:
        raise RuntimeError(f"Startup exited {process.returncode}: {output[-500:]} {errors[-500:]}")
    result = json.loads((folder / "smoke-result.json").read_text(encoding="utf-8"))
    if result.get("pages") != 13 or result.get("exit_code") != 0:
        raise RuntimeError("Startup did not construct all application pages")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--exe", type=Path)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    if args.exe and not args.exe.is_file():
        parser.error("EXE file does not exist")
    command = [str(args.exe.resolve())] if args.exe else [sys.executable, str(root / "app.py")]
    with tempfile.TemporaryDirectory(prefix="it-console-startup-") as temp:
        data = Path(temp) / "data"
        # وجود قاعدة فارغة يمنع ترحيل قاعدة المشروع القديمة إلى تجربة البدء.
        database = data / "database/app.db"
        database.parent.mkdir(parents=True)
        with closing(sqlite3.connect(database)) as connection:
            connection.execute("PRAGMA user_version=0")
        first = run_once(command, root, data)
        if first.get("language") != "ar" or first.get("theme") != "dark":
            raise RuntimeError("Fresh settings did not use the expected defaults")
        # نغيّر إعدادات قاعدة الاختبار فقط ثم نبدأ عملية جديدة لقياس الاستعادة.
        with closing(sqlite3.connect(data / "database/app.db")) as connection:
            connection.execute(
                "INSERT INTO settings (setting_key, setting_value) VALUES ('theme', 'light') "
                "ON CONFLICT(setting_key) DO UPDATE SET setting_value=excluded.setting_value"
            )
            connection.execute(
                "INSERT INTO settings (setting_key, setting_value) VALUES ('lang', 'en') "
                "ON CONFLICT(setting_key) DO UPDATE SET setting_value=excluded.setting_value"
            )
            connection.commit()
        second = run_once(command, root, data)
        if second.get("language") != "en" or second.get("theme") != "light":
            raise RuntimeError("Saved settings were not restored after restart")
        result = {"kind": "exe" if args.exe else "source", "first": first, "second": second}
        if args.report:
            args.report.parent.mkdir(parents=True, exist_ok=True)
            args.report.write_text(
                json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
            )
        print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
