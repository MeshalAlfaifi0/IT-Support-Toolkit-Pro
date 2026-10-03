# البناء والرفع إلى GitHub

## البناء

```powershell
python -m pip install -r requirements-build.txt
$env:IT_TOOLKIT_BUILD_NAME = "IT-Operations-Console-MyBuild"
.\scripts\build_exe.bat
```

يمكن تحديد مفسر مختلف بمتغير `IT_TOOLKIT_PYTHON` إلى المسار الكامل له. لا تخلط مكتبات pywin32/Pillow الخاصة بإصدار Python آخر. يخرج الملف إلى `dist/`، ويُرفض الاسم الموجود مسبقًا.

الملف الفعلي للبناء `packaging/IT-Operations-Console.spec`. ملف الجذر القديم يستدعيه للتوافق. إعدادات PATH في spec تمنع التقاط DLL من برامج أخرى على الجهاز.

## قائمة التحقق قبل الرفع

1. شغّل `python scripts/check_project.py`.
2. راجع `git status --short` و`git diff --cached --stat`.
3. تحقق من عدم إضافة قواعد بيانات أو سجلات أو نسخ احتياطية أو مفاتيح أو ملفات EXE إلى المصدر.
4. أنشئ حزمة مصدر نظيفة: `python scripts/package_source.py`؛ الملفات المحددة فقط تُضم إلى ZIP.
5. شغّل EXE، وراجع بقاء اللغة والثيم بعد الإغلاق وإعادة التشغيل.

رفع GitHub خطوة لاحقة؛ لا يحتوي المشروع على token أو remote مفترض. بعد إنشاء مستودع فارغ بحسابك، استخدم عنوانه الفعلي:

```powershell
git add app.py src tests scripts packaging docs .github README.md CONTRIBUTING.md SECURITY.md pyproject.toml requirements*.txt .gitignore .gitattributes .editorconfig IT-Support-Toolkit-Pro.spec
git commit -m "Prepare IT Operations Console source and tests"
git remote add origin <YOUR_REPOSITORY_URL>
git push -u origin main
```

إذا كان لديك مستودع Git قائم، راجع حالته بدل إعادة تهيئته أو تغيير remote الحالي. ملف EXE يُنشر لاحقًا كملف Release منفصل؛ لا يدخل تاريخ المصدر.

المشروع دون ترخيص حاليًا حسب اختيار المؤلف. النسخ غير موقعة رقميًا؛ ليست حزمة تثبيت.

يمكن فحص بدء النسخة المجمّعة وحفظ إعدادات تجربة مؤقتة وإعادة تشغيلها:

```powershell
python scripts/smoke_test.py --exe dist/IT-Operations-Console.exe --report artifacts/exe-startup.json
```

استبدل اسم الملف بالاسم الذي بُني فعليًا. هذا اختبار آلي دون عرض نافذة، ويُكمل الفحص المرئي ولا يغني عنه.
