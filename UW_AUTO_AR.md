# uw-auto: تشغيل وكلاء الذكاء الاصطناعي على الخطة

1. أنشئ خطة عبر `python scripts/workflow.py plan --file plan.json` مع مهام `id`, `paths`, `acceptance`، ويمكن إضافة `agent` لكل مهمة.
2. عدّل `examples/agents.example.json` لتحديد أوامر CLI الحقيقية للمساعدين المثبتين محليًا؛ المثال demo-safe لا يُجري تعديلًا.
3. معاينة بلا تنفيذ: `python scripts/auto_runner.py --run RUN --agent demo-safe`
4. بعد مراجعة الخطة وأوامر الوكلاء: `python scripts/auto_runner.py --run RUN --agent demo-safe --approve-worktrees --approve-agents --max-workers 2`
5. راجع `.ai/runs/RUN/auto/report.md` و`report.json` وسجلات كل وكيل.

**تنبيه:** الموافقة على التنفيذ تسمح لتطبيقات وكلاء خارجية بالعمل؛ لا يوجد sandbox. لا يتم commit/merge/push/deploy تلقائيًا. نتيجة FINISHED_UNVERIFIED لا تعني اجتياز اختبارات القبول.

## V6.9.1: حدّ السياق (مهم جدًا)

**تقسيم الخطة إلى مهام هو تقسيم لملكية الملفات والـ worktrees، وليس تقسيمًا لنافذة السياق.** في وضع المعاينة (PREVIEW) أو عند استخدام الفريق الداخلي، لا يُشغّل أي وكيل خارجي: تبقى كل المهام والأدوار والتقارير ومخرجات الاختبارات داخل **محادثة واحدة**، فيكبر السياق تراكميًا وينتهي رصيد التوكن قبل إكمال التحويل.

قبل كل مهمة/دور:

```powershell
py -3 scripts\uw_context_guard.py --root . check --run RUN --max-tokens 12000
py -3 scripts\uw_context_guard.py --root . brief --run RUN
```

- `brief` هو **البديل الإلزامي** عن `uw_internal_auto.py status`؛ لا تقرأ `internal-auto.json` أو التقارير أو `*.log` كاملة.
- إذا ظهر `over_budget: true` (الخروج برمز 2)، أو بعد إغلاق مهمة واحدة: توقف، ثم
  `py -3 scripts\uw_context_guard.py --root . prompt --run RUN` وافتح **محادثة جديدة** بملف `.ai/runs/RUN/FRESH_PROMPT.md`.
- عند تراكم الأدلة: `py -3 scripts\uw_context_guard.py --root . trim --run RUN --max-chars 800 --apply` (النسخة الكاملة محفوظة في `internal-auto.full.json`).
- وجّه مخرجات البناء/الاختبار إلى ملف، واذكر الأمر + exit code + عدد الاختبارات + آخر 5 أسطر فقط.
- تقديرات `check` هي `bytes/4` لحجوم الملفات، ليست قياس المزود الحقيقي ولا فاتورة.

العزل الحقيقي الوحيد للسياق يكون بأحد أمرين: **محادثة جديدة لكل مهمة**، أو **CLI خارجي مستقل لكل مهمة** عبر `--approve-agents --approve-worktrees` (بتكلفة منفصلة من المزود). راجع [V6_9_1_GUIDE_AR.md](V6_9_1_GUIDE_AR.md).

## V6.10: تكتب `uw-auto` فقط والباقي تلقائي

`uw-auto` صار **نقطة الدخول الوحيدة**؛ لا يسألك عن خطة أو وضع أو معرّف تشغيل أو مهارة. أول أمر ينفّذه المساعد:

```powershell
py -3 scripts\uw_autopilot.py boot
```

يقوم `boot` تلقائيًا بـ: إنشاء `uw-auto.config.json` إن لم يوجد (موافقات مغلقة)، توليد خطة من بنية المستودع إن لم تكن مسجلة، توجيه المهارات المحلية المُراجَعة لكل مهمة، قياس ميزانية السياق، وكتابة `.ai/runs/RUN/MISSION.md` (≤ 450 كلمة). ثم:

- `mode: external` → `py -3 scripts\uw_autopilot.py run --run RUN` — كل مهمة في عملية/سياق/worktree مستقل.
- `mode: inhost` → مهمة واحدة في هذه المحادثة ثم `py -3 scripts\uw_autopilot.py tick --run RUN --task TASK --evidence "..."`.

المهارات **محلية فقط** (مضمنة `uw-*` أو ملفات مثبّتة ببصمة SHA-256 ومراجعة سارية وموافقة صريحة)؛ لا تنزيل ولا تثبيت. التفاصيل: [V6_10_GUIDE_AR.md](V6_10_GUIDE_AR.md).

## V6.11: بلا مساعدات خارجية (الافتراضي الجديد)

كتابة `uw-auto` **لا تعني** إذنًا بتشغيل `codex exec` أو `claude` أو أي CLI/API خارجي. بدلًا من ذلك ينفّذ المساعد:

```powershell
py -3 scripts\uw_autopilot.py boot
py -3 scripts\uw_autopilot.py spawn --run RUN
```

`spawn` يكتب حزمة `SESSION-*.md` مستقلة لكل مهمة (≤ 450 كلمة) وملف `SPAWN.md`. في وضع `self` تُنشأ نسخة من **نفس المساعد** لكل حزمة (سياق مستقل لكل نسخة)، وفي وضع `sessions` تُفتح محادثة جديدة لكل حزمة و`tick` يولّد التالية تلقائيًا. الوضع الخارجي صار يحتاج `external_enabled: true` صريحًا. التفاصيل: [V6_11_GUIDE_AR.md](V6_11_GUIDE_AR.md).
