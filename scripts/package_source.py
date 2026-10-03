"""إنشاء ZIP نظيف من ملفات المصدر المحددة، مع رفض استبدال ملف تسليم سابق."""

import argparse
import zipfile
from datetime import datetime
from pathlib import Path

from source_files import ROOT, source_files


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    output = (
        args.output
        or ROOT / "dist" / f"IT-Operations-Console-source-{datetime.now():%Y%m%d-%H%M%S}.zip"
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    # الوضع x يمنع الكتابة فوق حزمة موجودة حتى لو تكرر الاسم.
    with zipfile.ZipFile(output, "x", zipfile.ZIP_DEFLATED) as archive:
        for path in source_files():
            archive.write(path, path.relative_to(ROOT).as_posix())
    with zipfile.ZipFile(output) as archive:
        if archive.testzip():
            raise RuntimeError("Source archive integrity check failed")
        print(f"Packaged {len(archive.namelist())} source files: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
