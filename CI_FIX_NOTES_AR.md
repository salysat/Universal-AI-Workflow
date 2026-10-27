# إصلاح CI لإصدار V6.9

- دعم Python 3.10 عبر مكتبة tomli عندما لا تتوفر tomllib.
- تثبيت tomli في وظائف Python 3.10 فقط.
- تثبيت نهايات الأسطر LF عبر .gitattributes للمحافظة على SHA-256 لمهارة find-skills على Windows.
- لم تُعطّل اختبارات أو فحوص أمنية.
- شغّل `python scripts/workflow.py validate` ثم `python -m unittest discover -s tests -v` ثم `python scripts/generate_commands.py --check`.
- نجاح GitHub Actions على Windows وPython 3.10 يحتاج التحقق بعد الرفع.
