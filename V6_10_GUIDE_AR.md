# Universal AI Workflow V6.10 — تكتب `uw-auto` فقط والباقي تلقائي

## الهدف

تكتب أمرًا واحدًا — `$uw-auto` — فيتولى المساعد:

1. اكتشاف المشروع وتوليد خطة تشغيل تلقائيًا إن لم توجد خطة مسجلة.
2. توجيه **المهارات المناسبة** لكل مهمة (محلية، مُراجَعة، بلا تنزيل).
3. قياس ميزانية السياق ومنع نفاد التوكن.
4. تنفيذ المهام تلقائيًا — كل مهمة في عملية ونافذة سياق وـ Git worktree مستقلة عند توفر CLI.
5. التحقق، كتابة تقرير مضغوط، والتسليم لمحادثة جديدة عند الحاجة.

لا يُسأل المستخدم عن: اسم الخطة، معرّف التشغيل، الوضع، المهارة، أو عدد العمال.

## ما الذي نفّذه المساعد عند كتابة `uw-auto`

```powershell
py -3 scripts\uw_autopilot.py boot
```

مخرجات `boot` عبارة عن JSON مضغوط (أقل من 2.5KB) يحتوي: `mode`، عدد المهام، المهمة الحالية، المسارات المملوكة، المهارات الموجّهة، ميزانية السياق، ومسار `MISSION.md`. المساعد يقرأ هذا الـ JSON و`MISSION.md` فقط — لا يقرأ الحالة الكاملة ولا السجلات.

`boot` ينفّذ تلقائيًا:

- إنشاء `uw-auto.config.json` إن لم يوجد (كل الموافقات `false` افتراضيًا، والملف مستبعد من Git).
- توليد خطة عبر مسح مجلدات المستودع ذات ملفات الكود: مهمة لكل مجلد (بحد `max_tasks`) بملكية ملفات غير متداخلة + مهمة `VERIFY` نهائية تعتمد على كل المهام. الخطة قابلة للمراجعة في `.ai/runs/RUN/plan.md`.
- توجيه المهارات لكل مهمة عبر `scripts/uw_skill_router.py`.
- قياس السياق عبر `uw_context_guard.py check`.
- كتابة `.ai/runs/RUN/MISSION.md` (≤ 450 كلمة).

## الوضعان (يُكتشفان تلقائيًا)

### 1) `external` — التشغيل غير المراقب الحقيقي

```powershell
py -3 scripts\uw_autopilot.py run --run RUN
```

- كل مهمة: `git worktree` مستقل + عملية CLI مستقلة + **نافذة سياق مستقلة**.
- المضيف لا يستقبل إلا سطرًا واحدًا لكل مهمة (المعرّف، الحالة، exit code، عدد الملفات، نتيجة التحقق).
- التحقق: أمر من القائمة الموثوقة `workflow.SAFE_COMMANDS` عبر `validation_command_id` (مثل `dotnet-test` أو `python-unittest`)؛ يُخزّن exit code وآخر 5 أسطر فقط.
- فحص ملكية الملفات: أي تعديل خارج `paths` يُوقف المهمة كـ `BLOCKED`.
- تقرير مضغوط في `.ai/runs/RUN/autopilot-report.md`؛ السجلات الكاملة في `.ai/runs/RUN/agents/<task>/`.

**اختبار فعلي أُجري على هذا الإصدار بوكيل تجريبي محلي:** 3/3 مهام، ثلاث worktrees منفصلة، exit code 0، صفر انتهاكات ملكية، وأمر تحقق ناجح — مع بقاء مخرجات المضيف JSON نقيًا.

> `FINISHED_UNVERIFIED` تعني: الوكيل خرج برمز 0 بلا انتهاكات ملكية. **لا تعني** أن شروط القبول تحققت independently. راجع الـ diffs وشغّل بوابة المشروع قبل أي commit.

### 2) `inhost` — مساعد المحادثة فقط

عند غياب CLI خارجي مُصادَق عليه:

1. نفّذ مهمة واحدة (أو دورة Architect→Developer→Tester→Reviewer واحدة) في هذه المحادثة.
2. سجّل:
   ```powershell
   py -3 scripts\uw_autopilot.py tick --run RUN --task T01 --evidence "build ok; log .ai/reports/x.log"
   ```
3. إن ظهر `next_chat_required: true`، افتح **محادثة جديدة** بملف `.ai/runs/RUN/FRESH_PROMPT.md`.

**حدّ صريح:** لا يمكن لأي سكربت أن يجعل محادثة ويب واحدة تُشغّل عدة نوافذ سياق مستقلة. هذا حدّ في المنصة نفسها، وليس إعدادًا ناقصًا. الحل إمّا محادثة جديدة لكل مهمة، أو CLI خارجي.

## المهارات: «يحمل سكيل لو محتاجها» بأمان

`scripts/uw_skill_router.py` يوجّه **مسارات ملفات محلية** فقط:

| النوع | الشرط |
|---|---|
| أوامر `uw-*` المضمنة | ملفات المستودع نفسها (`.agents/skills/...` أو أي منصة مثبّتة). موثوقة، تُقرأ فقط. |
| مهارات الطرف الثالث | ملف موجود محليًا + `approved_for_execution: true` + `review_status: approved` + `review_expires` سارٍ + **بصمة SHA-256 مطابقة** في `.ai/skills/REGISTRY.json`. |
| مهارات يضيفها المستخدم | في `uw-auto.config.json` → `extra_skills` مع `approved: true` و`sha256` مطابق ومسار داخل المشروع. |

يُمنع: التنزيل، التثبيت، `npx skills add`، تنفيذ السكربتات، والخروج من جذر المشروع. التحميل هنا = «أخبر الوكيل أن يقرأ هذا الملف المراجَع»، وليس «الصق محتواه في سياق المضيف». الناتج دائمًا `network_used: false` و`auto_install: false`.

## الإعداد لمرة واحدة (للتشغيل غير المراقب)

```powershell
py -3 scripts\uw_autopilot.py init-config
```

ثم عدّل `uw-auto.config.json`:

```json
{
  "version": 1,
  "run_id": "auto",
  "description": "حوّل المشروع بالكامل وأصلح الأخطاء",
  "agent": "codex",
  "agents_config": "agents.local.json",
  "max_tasks": 6,
  "max_tokens": 12000,
  "validation_command_id": "dotnet-test",
  "approve_agents": true,
  "approve_worktrees": true,
  "auto_integrate": false
}
```

وأنشئ `agents.local.json` (مستبعد من Git) بعد التأكد من صيغة إصدارك عبر `codex exec --help`:

```json
{
  "version": 1,
  "agents": {
    "codex": {
      "argv": ["codex", "exec", "-"],
      "prompt_transport": "stdin",
      "timeout_seconds": 600
    }
  }
}
```

> اكتشاف الملف التنفيذي ≠ تسجيل دخول. صلاحيات الـ CLI والتكلفة على المزود مسؤوليتك. كل مهمة عملية مستقلة = تكلفة منفصلة.

### خيارات إضافية

| المفتاح | المعنى |
|---|---|
| `auto_plan` | تعطيله يمنع توليد خطة تلقائيًا ويطلب خطة مسجلة. |
| `auto_skills` | تعطيل توجيه المهارات. |
| `max_tasks_per_run` | عدد المهام في الاستدعاء الواحد (افتراضي 4) — يمنع الاستدعاءات الطويلة. |
| `validation_command_id` | أمر من `workflow.SAFE_COMMANDS` يُشغّل بعد كل مهمة. |
| `auto_integrate` + `approve_integrate` | تطبيق تغييرات الـ worktree على الشجرة الرئيسية عبر `git apply --check` ثم `git apply`. **خطير: يتطلب موافقتين صريحتين.** |
| `extra_skills` | مهارات محلية إضافية ببصمة وموافقة. |

## الأوامر الكاملة

```powershell
py -3 scripts\uw_autopilot.py init-config                 # مرة واحدة (اختياري؛ boot ينشئه تلقائيًا)
py -3 scripts\uw_autopilot.py boot                       # ما ينفّذه $uw-auto أولًا
py -3 scripts\uw_autopilot.py run --run RUN              # external
py -3 scripts\uw_autopilot.py tick --run RUN --task T01 --evidence "..." --status done
py -3 scripts\uw_autopilot.py status --run RUN
```

## التحقق قبل النشر

```powershell
py -3 scripts\workflow.py validate
py -3 scripts\generate_commands.py --check
py -3 -m unittest discover -s tests -q
py -3 scripts\uw_autopilot.py boot
```

النتيجة المتوقعة: `PASS`، `OUT OF SYNC: 0 files`، **95 اختبارًا OK**، و`boot` يُرجع JSON مضغوطًا بـ `mode` و`current` و`skills`.

## ما لا يفعله هذا الإصدار

- لا يزيد حصة المزود ولا يضغط سياق محادثة قائمًا.
- لا يُشغّل CLI غير مُصادَق عليه، ولا يخمّن كلمات المرور.
- لا ينزّل أو يثبّت مهارات، ولا ينفّذ سكربتاتها.
- لا يعمل commit/merge/push/deploy تلقائيًا.
- لا يدّعي أن `FINISHED_UNVERIFIED` تعني «تم التحقق».
- لا يصلح أعطال البيئة (مثل `kernel-assets path missing` في المتصفح).

التفاصيل التقنية: [docs/AUTOPILOT.md](docs/AUTOPILOT.md) · حدّ السياق: [V6_9_1_GUIDE_AR.md](V6_9_1_GUIDE_AR.md) · النشر: [PUBLISH_GITHUB_AR.md](PUBLISH_GITHUB_AR.md).
