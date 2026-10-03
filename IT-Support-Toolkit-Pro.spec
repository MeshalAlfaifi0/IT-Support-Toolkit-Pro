# مدخل توافق للأوامر القديمة؛ إعدادات البناء الفعلية داخل packaging.
from pathlib import Path

spec_path = Path(SPECPATH) / "packaging" / "IT-Operations-Console.spec"
exec(compile(spec_path.read_text(encoding="utf-8"), str(spec_path), "exec"))
