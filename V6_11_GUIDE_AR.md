# Universal AI Workflow V6.11 — بلا مساعدات خارجية: نفس المساعد يتكرر

## طلبك

> «لا أريد مساعدات خارجية… فقط يتشكّل نفسه أكثر من مرة.»

تم. الإعداد الافتراضي في هذا الإصدار **لا يستدعي أي CLI خارجي** (`codex exec`, `claude`, `gemini`، ولا أي API). بدلًا من ذلك، يكتب الطيار الآلي **حزم جلسات مستقلة**، وتُنشأ من **نفس المساعد** نسخ متعددة لكل منها سياقها الخاص.

## الفكرة بوضوح

| ما تريده | كيف تحقّقه الأداة |
|---|---|
| نفس المساعد، أكثر من مرة | ملف `SESSION-01-….md` لكل مهمة = برومبت كامل ومكتفي بذاته لنسخة جديدة منك. |
| بلا مساعدات خارجية | `external_enabled: false` افتراضيًا. الوضع الخارجي يحتاج أربع موافقات صريحة ولا يُستدعى بكتابة `uw-auto`. |
| ما ينفد التوكن | كل نسخة/محادثة تبدأ بسياق نظيف (≤ 450 كلمة) بدل تراكم كل المهام في محادثة واحدة. |
| يحمل سكيل لو احتاجها | كل حزمة جلسة تحتوي مسارات المهارات المحلية المُراجَعة المناسبة لتلك المهمة. |

## الوضعان (يُكتشفان تلقائيًا)

### 1) `self` — وكلاء فرعيون أصليون (native subagents)

فعّله مرة واحدة في `uw-auto.config.json`:

```json
{ "version": 1, "host_subagents": true, "parallel_sessions": 2 }
```

ثم اكتب `$uw-auto`. المساعد ينفّذ:

```powershell
py -3 scripts\uw_autopilot.py boot
py -3 scripts\uw_autopilot.py spawn --run auto
```

`spawn` يُرجع JSON مضغوطًا بقائمة الجلسات ويكتب `.ai/runs/auto/SPAWN.md`. المساعد المضيف:

1. ينشئ **نسخة من نفسه** لكل ملف جلسة (حتى `parallel_sessions`).
2. يعطي كل نسخة **محتوى ملفها فقط** — لا سجل المحادثة، لا التقارير، لا الـ logs.
3. كل نسخة تنفّذ مهمة واحدة وتُرجع ≤ 10 أسطر (الأمر + exit code + الملفات + الدليل).
4. بعد عودة النسخ يُسجّل `tick` لكل مهمة، ثم `spawn` مرة أخرى للموجة التالية.

> هذا هو التجسيد الحرفي لـ«يتشكّل نفسه أكثر من مرة»: نفس النموذج، عدة سياقات مستقلة، بلا أي مزود خارجي.

### 2) `sessions` — محادثات جديدة متسلسلة (الافتراضي إن لم تدعم المنصة الوكلاء الفرعيين)

```powershell
py -3 scripts\uw_autopilot.py boot
py -3 scripts\uw_autopilot.py spawn --run auto
```

1. افتح محادثة جديدة والصق محتوى `SESSION-01-….md`.
2. النسخة الجديدة تنفّذ مهمة واحدة، ثم تسجّل:
   ```powershell
   py -3 scripts\uw_autopilot.py tick --run auto --task T01 --evidence "build ok; log .ai/reports/x.log"
   ```
3. `tick` يولّد **تلقائيًا** ملف الجلسة التالية ويعيد `spawn_again: true`.
4. افتح محادثة جديدة بالملف التالي — أو اكتب `uw-auto` فيها وسيختار الجلسة التالية بلا أسئلة.

## شكل حزمة الجلسة

كل ملف (≤ 450 كلمة) يحتوي:

- المعرّف والدور والهدف.
- **النطاق المملوك** (لا تعدّل خارجه) وشروط القبول.
- مسارات المهارات المحلية المُراجَعة — تُقرأ فقط.
- ما يُقرأ: `AGENTS.md`, `.ai/HANDOFF.md`, هذا الملف، و1–10 ملفات مصدر.
- ما **لا** يُقرأ: `autopilot.json`, `internal-auto.json`, التقارير، `*.log`، مخرجات الاختبارات الكاملة.
- أمر `tick` الدقيق، ثم «توقف، لا تبدأ مهمة أخرى في هذه الجلسة».
- ممنوعات: لا CLI خارجي، لا تنزيل/تثبيت مهارات، لا commit/push، لا ادعاء اختبارات لم تُرَ.

## الإعداد الكامل (كل شيء اختياري عدا كلمة `uw-auto`)

```json
{
  "version": 1,
  "run_id": "auto",
  "description": "حوّل المشروع بالكامل وأصلح الأخطاء",
  "max_tasks": 6,
  "max_tokens": 12000,
  "auto_plan": true,
  "auto_skills": true,
  "host_subagents": false,
  "parallel_sessions": 2,
  "external_enabled": false
}
```

| المفتاح | المعنى |
|---|---|
| `host_subagents` | `true` → وضع `self` (نسخ native). `false` → وضع `sessions` (محادثات جديدة). |
| `parallel_sessions` | عدد النسخ التي تُنشأ في الموجة الواحدة (1–8). |
| `external_enabled` | إن أردت CLI خارجيًا يومًا ما؛ يجب أن يجتمع مع `approve_agents` و`approve_worktrees` و`agents_config`. **لا يُفعّل افتراضيًا.** |
| `mode_override` | `self` / `sessions` / `external` لفرض وضع يدويًا للاختبار. |

## الأوامر

```powershell
py -3 scripts\uw_autopilot.py boot                      # ما ينفّذه $uw-auto أولًا
py -3 scripts\uw_autopilot.py spawn --run RUN           # يولّد حزم الجلسات + SPAWN.md
py -3 scripts\uw_autopilot.py tick --run RUN --task T01 --evidence "..."
py -3 scripts\uw_autopilot.py status --run RUN
py -3 scripts\uw_autopilot.py init-config
```

`run` ما زال موجودًا لكنه للمسار الخارجي فقط؛ في الوضعين الجديدين يُرجع توجيهًا إلى `spawn` ولا يشغّل أي شيء خارجي.

## التحقق الفعلي على هذا الإصدار

- `python scripts/workflow.py validate` → PASS
- `python scripts/generate_commands.py --check` → 0 ملفات غير متزامنة
- `python -m unittest discover -s tests -q` → **101 اختبارًا OK** (6 اختبارات جديدة للجلسات)
- اختبار `self`: `boot` أنشأ حزمتي جلسة مستقلتين، كل ≤ 450 كلمة، و`SPAWN.md` يحوي تعليمات النسخ.
- اختبار `sessions`: `boot` → `tick` أعاد `spawn_again: true` وولّد الجلسة التالية تلقائيًا.
- اختبار أن `approve_agents=True` **لا** يفعّل الوضع الخارجي ما دام `external_enabled=False`.

## حدود يجب أن تعرفها بصراحة

- **المنصة تقرر عدد السياقات.** ملفات السكربت لا تستطيع فتح محادثات جديدة داخل واجهة ChatGPT/Codex ويب، ولا تُجبر المنصة على إنشاء وكلاء فرعيين. إن كانت المنصة تدعم أداة الوكلاء الفرعيين → وضع `self` يعمل فورًا. وإن كانت تسمح بمحادثات جديدة → وضع `sessions` يعمل (بضغطة منك لكل محادثة). وإن لم تدعم أيًا منهما → لا توجد طريقة صادقة لإنشاء سياقات مستقلة، وسيقول المساعد ذلك بدل الادعاء.
- لا توجد أداة تزيد حصة المزود؛ هذا يمنع **تراكم** السياق داخل المحادثة الواحدة.
- لا تنزيل/تثبيت مهارات، لا شبكة، لا commit/merge/push تلقائي.
- `FINISHED_UNVERIFIED` في المسار الخارجي لا يعني قبولًا مُتحققًا منه.

التفاصيل التقنية: [docs/SELF_SESSIONS.md](docs/SELF_SESSIONS.md) · الطيار الآلي: [V6_10_GUIDE_AR.md](V6_10_GUIDE_AR.md) · النشر: [PUBLISH_GITHUB_AR.md](PUBLISH_GITHUB_AR.md).
