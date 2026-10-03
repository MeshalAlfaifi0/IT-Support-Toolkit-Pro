"""قائمة ملفات التسليم المسموح بها؛ البيانات والسجلات والبيئات لا تدخل حزمة المصدر."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ROOT_FILES = (
    "app.py",
    "README.md",
    "CONTRIBUTING.md",
    "SECURITY.md",
    "pyproject.toml",
    "requirements.txt",
    "requirements-lock.txt",
    "requirements-build.txt",
    "requirements-dev.txt",
    ".gitignore",
    ".gitattributes",
    ".editorconfig",
    "IT-Support-Toolkit-Pro.spec",
)
SOURCE_FOLDERS = ("src", "tests", "scripts", "docs", "packaging", ".github")
SUFFIXES = {
    ".py",
    ".json",
    ".md",
    ".toml",
    ".yml",
    ".yaml",
    ".spec",
    ".bat",
    ".ps1",
    ".png",
    ".ico",
}


def source_files():
    files = [ROOT / name for name in ROOT_FILES]
    for folder in SOURCE_FOLDERS:
        for path in (ROOT / folder).rglob("*"):
            if not path.is_file() or "__pycache__" in path.parts or "artifacts" in path.parts:
                continue
            if path.suffix in SUFFIXES:
                files.append(path)
    # الملفات الرمزية قد تشير إلى بيانات خارج المشروع؛ لا تُضم تلقائيًا.
    for path in sorted(set(files)):
        if path.exists():
            if path.is_symlink() or not path.resolve().is_relative_to(ROOT.resolve()):
                raise ValueError(f"Unsafe source path: {path.name}")
            yield path
