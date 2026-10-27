# Universal AI Workflow V6.6 — كفاءة السياق والاستكمال

أضيفت أداة مستقلة آمنة `scripts/uw_efficiency.py` تعمل بدون مكتبات خارجية أو شبكة أو تنفيذ أوامر AI.

```bash
python scripts/workflow.py validate
python -m unittest discover -s tests -v
python scripts/uw_efficiency.py budget AGENTS.md README.md --max-tokens 5000
python scripts/uw_efficiency.py inspect AGENTS.md README.md
python scripts/uw_efficiency.py snapshot AGENTS.md .ai/STATE.md --output .ai/resume-snapshot.json
python scripts/uw_efficiency.py resume-check --snapshot .ai/resume-snapshot.json
python scripts/uw_efficiency.py providers
python scripts/uw_efficiency.py skills "user asks to find a skill"
python scripts/uw_efficiency.py handoff-check
python scripts/uw_efficiency.py usage-add --provider codex --task TASK-1 --input-tokens 1000 --output-tokens 300
```

- `budget`: حساب تقريبي UTF-8 bytes/4 واختيار ما يتسع في الميزانية؛ ليس عدد التوكنات الفعلي.
- `snapshot` / `resume-check`: بصمات SHA-256 للملفات المحددة تكشف التغييرات بعد تسليم السياق؛ لا تكشف تغييرات الملفات غير المدرجة.
- `inspect`: كشف توقيع الملف مع حد قراءة 2MB، وليس تحويلًا أو تحليلًا دلاليًا لكل الصيغ.
- `providers`: يتحقق من وجود CLI على PATH فقط؛ لا يفحص تسجيل الدخول أو API.
- `skills`: ترشيحات فقط ولا تثبيت أو تشغيل.
- `handoff-check`: يتحقق من وجود الملفات وبعض علامات عدم التهيئة، لا يضمن صحة مضمونها.
- `usage-add`: إدخال يدوي لاستهلاك حقيقي مصدره المستخدم/المزود؛ لا يدعي وجود ربط مع API.

**الحدود:** لا يمكن للأداة تجاوز حصص Codex/Work أو ضمان خفضها. ولا تقرأ الملفات الموجودة خارج جذر المشروع.

**V6.9.1:** أضيف `scripts/uw_context_guard.py` (`brief` / `check` / `prompt` / `trim`) لفرض حدّ عملي على نمو السياق أثناء التشغيل؛ راجع [V6_9_1_GUIDE_AR.md](V6_9_1_GUIDE_AR.md). أدوات V6.6 تبقى صالحة للتقدير والبصمات وإدخال الاستهلاك يدويًا.
