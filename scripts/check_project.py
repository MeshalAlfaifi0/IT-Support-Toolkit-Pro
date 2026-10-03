"""فحص جودة الكود وصيغته ثم تشغيل اختبارات العربية والإنجليزية في بيئة بيانات معزولة."""

import ast
import re
import subprocess
import sys

from source_files import ROOT, source_files


def check_shareable_source():
    """كشف أنماط مفاتيح معروفة دون طباعة قيمة المفتاح في نتيجة الفحص."""
    patterns = [
        re.compile(r"\bAKIA[A-Z0-9]{16}\b"),
        re.compile(r"\bgh[pousr]_[A-Za-z0-9]{36,255}\b"),
        re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    ]
    for path in source_files():
        if path.suffix in {".png", ".ico"}:
            continue
        content = path.read_text(encoding="utf-8-sig")
        if any(pattern.search(content) for pattern in patterns):
            raise RuntimeError(f"Possible private key/token in {path.relative_to(ROOT)}")
        if path.suffix in {".py", ".spec"}:
            ast.parse(content, filename=str(path))


def main():
    check_shareable_source()
    commands = [
        ["-m", "ruff", "check", "app.py", "src", "tests", "scripts"],
        ["-m", "ruff", "format", "--check", "app.py", "src", "tests", "scripts"],
        ["-m", "compileall", "-q", "app.py", "src", "tests", "scripts"],
        ["scripts/run_tests.py", "--language", "ar"],
        ["scripts/run_tests.py", "--language", "en", "--scale", "1.5"],
    ]
    for command in commands:
        # نفشل فورًا عند فشل أي مرحلة؛ لا نعلن نجاح الاختبارات من كود خروج مهمل.
        result = subprocess.run([sys.executable, *command], cwd=ROOT)
        if result.returncode:
            return result.returncode
    print("All project checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
