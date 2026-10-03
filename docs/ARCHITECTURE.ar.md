# البنية وتتبّع الكود

## مسار التنفيذ

`app.py` يهيئ الجداول ويقرأ اللغة ثم ينشئ QApplication والنافذة الرئيسية. `src/ui/main_window.py` يربط الصفحات بالتنقل والثيم ويعالج الإغلاق وإعادة التشغيل. ترتيب `_pages` يطابق ترتيب أزرار الشريط الجانبي؛ لا تغيّر أحدهما منفردًا.

صفحة الواجهة تنشئ خيطًا من `ManagedThread` في `utils/workers.py`. الخيط يجمع البيانات عبر `core` ثم يرسل Signal. دالة استقبال الإشارة تحدّث عناصر الواجهة؛ لا تُعدّل QWidget مباشرة من خيط الفحص.

## أين أعدّل؟

| المطلوب | مكان التعديل |
|---|---|
| اسم التطبيق | `utils/branding.py`؛ عنوان «حول» في `utils/lang.py` |
| القائمة وحجم النافذة والإغلاق | `ui/main_window.py` |
| لوحة التحكم | `ui/dashboard.py` مع `core/system_info.py` |
| التعريفات | `ui/driver_page.py` و`core/system_info.py` |
| فحص الصحة | `ui/health_page.py` و`core/health_checker.py` |
| احتساب الصحة | `core/health_score.py` |
| التوصيات | `core/recommendations.py` |
| IPv4 وDHCP وDNS | `ui/network_page.py` و`core/ip_manager.py` |
| قراءة المحولات وتشخيص الشبكة | `core/network_info.py` و`core/network_tools.py` |
| الأجهزة المتصلة | `ui/connected_devices_page.py` و`core/connected_devices.py` |
| الطابعات والطوابير | `ui/printer_page.py` و`core/printer_tools.py` |
| الصيانة والخدمات | `ui/automation_page.py` و`core/windows_repair.py` و`core/service_manager.py` |
| الدومين | `ui/domain_page.py` و`core/domain_info.py` |
| مؤشرات الأمان | `ui/cybersecurity_page.py` و`core/cybersecurity.py` |
| أوامر الدعم | `ui/cmd_page.py` و`utils/command_runner.py` |
| سجل العمليات | `ui/history_page.py` و`database/init_db.py` |
| اللغة والمظهر ومعلومات المؤلف | `ui/settings_page.py` |
| التقارير المستقلة | `reports/`؛ `ui/reports_page.py` غير مربوط بالتنقل الحالي |
| جداول SQLite | `database/models.py` |
| الاتصال والحفظ | `database/connection.py` و`database/init_db.py` |
| مسارات الملفات والترحيل | `utils/app_paths.py` |
| ترجمة العناصر | `utils/ui_text.py` و`utils/ui_translations*.json` |
| مفاتيح الترجمة | `utils/lang.py` |
| الثيم والبطاقات المرنة | `utils/ui_style.py` و`utils/responsive_grid.py` |
| السجلات والصلاحيات | `utils/logger.py` و`utils/admin_check.py` |
| إعادة تشغيل EXE | `utils/restart.py` |

كل المسارات أعلاه داخل `src/`. ملفات `__init__.py` تعرّف حزم Python؛ لا تحتاج لإعادة تسمية الحزم عند تعديل اسم التطبيق المعروض.

## عقود مهمة

- البيانات الأصلية والفلاتر مفاتيح ثابتة؛ الترجمة تخص العرض فقط. عناصر `ui_text` تغلف Qt لهذا السبب، فلا تستبدلها بعناصر Qt المباشرة دون اختبار اللغتين.
- كلمات مرور الدومين تُرسل عبر stdin إلى سكربت ثابت؛ لا تدخل سطر الأمر أو السجلات. العمليات الحساسة تتجاهل مخرجات الابن التي قد تعيد بيانات الاعتماد.
- حالة الفحص قد تكون True أو False أو None. None تعني مجهولًا، ولا تمنح نقاط نجاح.
- حفظ الفحص والتوصيات معاملة واحدة؛ لا تضف كتابة منفصلة تترك نتيجة جزئية عند الفشل.
- تنسيق حالة الطابعة أعلام bitmask من `win32print`؛ لا تستبدل الثوابت بأرقام ترتيبية.
- ملفات SQLite القديمة تُنسخ عبر API backup ليُحفظ WAL، مع إبقاء المصدر وعدم استبدال البيانات الحالية.
- إبقاء مرجع الخيط يمنع تدميره قبل انتهاء العمل. الإغلاق تعاوني؛ بعض استدعاءات WMI لا تقبل إلغاءً فوريًا.

## ملفات محلية وليست مصدرًا

`backups/` للرجوع، `build/` و`dist/` للبناء، و`database/` و`logs/` و`exports/` قد تحتوي بيانات قديمة قابلة للاستعادة. لا تُحذف ضمن تنظيم الكود، ولا تُرفع إلى GitHub.
