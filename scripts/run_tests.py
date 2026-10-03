"""تشغيل الاختبارات داخل مجلد بيانات مؤقت دون تغيير إعدادات الجهاز أو بيانات المستخدم."""

import argparse
import os
import subprocess
import sys
import tempfile
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--language", choices=("ar", "en"), default="ar")
    parser.add_argument("--scale", choices=("1", "1.5", "2"), default="1")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    with tempfile.TemporaryDirectory(prefix="it-console-tests-") as folder:
        env = os.environ.copy()
        env.update(
            IT_TOOLKIT_DATA_DIR=str(Path(folder) / "data"),
            UI_SCREENSHOTS=str(Path(folder) / "screenshots"),
            QT_QPA_PLATFORM="offscreen",
            TEST_LANGUAGE=args.language,
            QT_SCALE_FACTOR=args.scale,
        )
        # نبدأ عملية مستقلة حتى تُقرأ اللغة والمسارات قبل أي استيراد لوحدات التطبيق.
        result = subprocess.run(
            [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"], cwd=root, env=env
        )
        return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
