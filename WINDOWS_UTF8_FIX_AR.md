# إصلاح Windows UTF-8

السبب: عملية Python الفرعية على Windows كانت تحول النص العربي في stdout إلى علامات استفهام عند استخدام ترميز وحدة التحكم الافتراضي.

التعديل: `scripts/uw_v6.py` يستخدم UTF-8 للـ stdin/stdout/stderr ويضبط PYTHONIOENCODING في بيئة العملية الفرعية. لا يلغى أي اختبار أو فحص أمن.

التحقق: `python -m unittest discover -s tests -v`، ثم تحقق GitHub Actions من جميع الأنظمة.

> الإصلاح يعالج عمليات Python الفرعية التي تحترم PYTHONIOENCODING. أدوات CLI التي تخرج ترميزات أخرى تحتاج مهايئًا مخصصًا.
