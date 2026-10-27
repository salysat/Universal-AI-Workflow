# Universal AI Workflow V6.9.1 — حارس السياق (إصلاح نفاد التوكن)

## لماذا هذا الإصدار؟

كان يُفترض أن `$uw-auto` «يقسّم المهام ويقلّل التوكن». عمليًا كان التوكن ينتهي قبل إكمال التحويل. السبب ليس في عدد المهام، بل في أن **تقسيم الخطة في هذه الأداة هو تقسيم ملكية ملفات وـ Git worktrees، وليس تقسيم نوافذ السياق**.

أدلة من الكود قبل الإصلاح:

| الملف | الاقتباس |
|---|---|
| `scripts/auto_runner.py:38` | بدون `--approve-agents` يطبع `{'mode':'PREVIEW'}` ويعود بلا تنفيذ ولا تقارير. |
| `commands/registry.json` → `uw-auto` | «the bundled demo agent does not write code». |
| `scripts/uw_internal_auto.py:127` | «The same host assistant performs the next role. No external AI is launched.» |
| `INTERNAL_AI_TEAM_AR.md` | «ليس أربع نسخ مستقلة من النموذج». |
| `.ai/CONTEXT_POLICY.md` | «Never assert numerical token savings without measurement». |
| `V6_6_GUIDE_AR.md` | «لا يمكن للأداة تجاوز حصص Codex/Work أو ضمان خفضها». |

المضاعِفات الداخلية كانت تزيد المشكلة: `uw_internal_auto.py status` يطبع كامل الحالة، و`record` يقبل حتى 50,000 حرف دليل لكل دور، و`report` يطبع حتى 2,000 حرف لكل دور/مهمة، و`uw_internal_team.py next` يُعيد كل الأدلة السابقة، و`workflow.py gate` يخزّن 8,000 حرف من مخرجات كل فحص.

**قياس فعلي على السكربت الأصلي:** 12 مهمة × 4 أدوار × دليل 805 أحرف → `internal-auto.json` بحجم 47,497 بايت؛ مخرجات `status` تكبر من 3,277 إلى 46,584 بايت؛ ومجموع قراءات `status` على 48 خطوة ≈ 1,196,796 بايت ≈ **299,000 توكن تقديري** من قراءة الحالة وحدها، قبل ملفات المصدر ومخرجات `dotnet` والتقارير. (التقدير `bytes/4`.)

## ما الذي تغيّر في 6.9.1

1. **ملف جديد `scripts/uw_context_guard.py`** (مكتبة Python القياسية فقط، بلا شبكة ولا تنفيذ أوامر ولا استدعاء نماذج) بأربعة أوامر: `brief` و`check` و`prompt` و`trim`.
2. **أمر جديد `uw-context`** في `commands/registry.json`، مولّد تلقائيًا للمنصات الست (19 أمرًا إجمالًا).
3. **تحديث `uw-auto` و`uw-team` و`uw-resume`** لفرض `brief` بدل الحالة الكاملة، و`check` قبل كل مهمة/دور، و`prompt` عند تجاوز الميزانية.
4. **قواعد إلزامية في `AGENTS.md`** و`.ai/CONTEXT_POLICY.md` و`.cursor/rules/universal-workflow.mdc` و`.github/copilot-instructions.md` و`UW_AUTO_AR.md` و`INTERNAL_AI_TEAM_AR.md`.
5. **`VERSION` و`scripts/workflow.py`** متزامنان على `6.9.1`؛ و`scripts/install_ai.py` يضيف السكربت إلى `RUNTIME_FILES` ليصل لكل تثبيت جديد.
6. **اختبارات جديدة** `tests/test_uw_context_guard.py` (6 اختبارات).

## الأوامر الأربعة

### `brief` — عرض مضغوط بدل `status`

```powershell
py -3 scripts\uw_context_guard.py --root . brief --run RUN
```

يُرجع: عدّادات الحالات، المهمة الجاهزة الحالية (المعرّف، الدور، شروط القبول، النطاق المملوك، الاعتماديات)، المحظورات، و**مقتطف تحقق واحد محدود بـ 180 حرفًا**. لا يطبع الأدلة ولا السجلات. قياس على نفس المثال: **839 بايت ≈ 191 توكن** مقابل 47,497 بايت ≈ 11,874 توكن لـ `status`.

### `check` — إشارة توقف قبل نفاد السياق

```powershell
py -3 scripts\uw_context_guard.py --root . check --run RUN --max-tokens 12000
```

يجمع أحجام: وثائق السياسة الثابتة، تعريفات المهارات، `commands/registry.json`، كل ما في `.ai/runs/RUN/` عدا `FRESH_PROMPT.md` والنسخ الاحتياطية، و`.ai/reports/`. يُرجع `total_estimate` و`over_budget` وأكبر 10 ملفات. عند `over_budget: true` يكون **exit code = 2** — وهذا مقصود ليوقف الأتمتة، وليس خطأً في السكربت. على المثال السابق: 31,672 توكن تقديري مقابل ميزانية 12,000، وأكبر المصادر `internal-auto.json` (11,875) ثم `internal-auto-report.md` (9,985).

> التقدير هو `UTF-8 bytes ÷ 4` **لأحجام الملفات**، وليس عدّاد المزود ولا فاتورة ولا قياسًا حيًا للسياق. لا توجد طريقة من ملفات المشروع لمعرفة استهلاك Codex/ChatGPT الحقيقي دون بيانات من المزود.

### `prompt` — محادثة جديدة لكل مهمة

```powershell
py -3 scripts\uw_context_guard.py --root . prompt --run RUN
```

يكتب `.ai/runs/RUN/FRESH_PROMPT.md` (≤ 450 كلمة، ≈ 595 توكن في المثال). يحتوي: ما يُقرأ، ما **لا** يُقرأ أبدًا، المهمة الحالية ونطاقها وشروط قبولها، آخر تحقق، المحظورات، الأمر التالي، وخمس قواعد إلزامية. افتح به محادثة جديدة بدل متابعة نفس الجلسة.

### `trim` — تقليص الأدلة المتراكمة

```powershell
py -3 scripts\uw_context_guard.py --root . trim --run RUN --max-chars 800          # معاينة فقط
py -3 scripts\uw_context_guard.py --root . trim --run RUN --max-chars 800 --apply  # بعد المراجعة
```

يحفظ نسخة كاملة في `internal-auto.full.json` ثم يقصّ كل دليل أطول من الحد مع الإشارة إلى مكانه في النسخة الكاملة. على المثال: 48 دليلًا، توفير ≈ 21,360 حرفًا. حالتا `state()` و`plan()` لا تعتمدان على نص الدليل، لذلك يبقى الاستكمال سليمًا. النسخة الكاملة مستبعدة من `check` لأنها أرشيف لا يُقرأ في المحادثة.

## دورة العمل المطلوبة

```
check → brief → مهمة واحدة (أو دورة Architect/Developer/Tester/Reviewer واحدة)
      → دليل ≤ 200 كلمة + مسار السجل → prompt → محادثة جديدة بـ FRESH_PROMPT.md
```

قواعد مرافقة:

- وجّه مخرجات البناء/الاختبار إلى ملف؛ اذكر الأمر + `exit code` + عدد الاختبارات + آخر 5 أسطر فقط.
  ```powershell
  dotnet test ... *> .ai\reports\HEAR-001-test.log
  Get-Content .ai\reports\HEAR-001-test.log -Tail 5
  ```
- لا تقرأ `internal-auto.json` أو `internal-auto-report.md` أو `auto/report.json` أو أي `*.log` كاملًا داخل المحادثة.
- إذا ظهر `over_budget: true`، توقف فورًا ولا تبدأ مهمة جديدة في نفس الجلسة.
- ثبّت منصة واحدة فقط عند التثبيت (`--platforms codex`) لتقليل العبء الثابت.

## العزل الحقيقي للسياق (البديل الاحترافي)

`--approve-agents --approve-worktrees` يشغّل CLI خارجيًا لكل مهمة؛ كل عملية لها نافذة سياق مستقلة، والمضيف يستقبل ملخصًا فقط. لكنها **تكلفة منفصلة** على المزود، وتحتاج CLI مثبتًا ومصادقًا عليه ومراجعة `argv` حسب إصدارك (`examples/agents.codex.unverified.json` موسوم بأنه غير مُختبر). `FINISHED_UNVERIFIED` ليس `DONE`.

```powershell
codex exec --help
Copy-Item examples\agents.codex.unverified.json agents.local.json
py -3 scripts\auto_runner.py --run RUN --agent codex --config agents.local.json
py -3 scripts\auto_runner.py --run RUN --agent codex --config agents.local.json --approve-agents --approve-worktrees --max-workers 2
Get-Content .ai\runs\RUN\auto\report.md -Tail 40
```

## ما لا يصلحه هذا الإصدار

- لا يزيد حصة المزود ولا يضغط سياق محادثة قائم بالفعل؛ يمنع نموه فقط.
- لا يصلح أعطال البيئة مثل `kernel-assets path missing` في المتصفح — تلك مشكلة منفصلة.
- لا يقيس الاستهلاك الحقيقي. `uw_efficiency.py usage-add` يبقى إدخالًا يدويًا لأرقام يقدّمها المستخدم/المزود.
- إذا أصررت على تشغيل كل المهام في محادثة واحدة، فلن ينقذك أي سكربت.

## التحقق قبل النشر

```powershell
py -3 scripts\workflow.py validate
py -3 scripts\generate_commands.py --check
py -3 -m unittest discover -s tests -q
```

النتيجة المتوقعة: `PASS`، `OUT OF SYNC: 0 files`، **85 اختبارًا OK**. راجع [PUBLISH_GITHUB_AR.md](PUBLISH_GITHUB_AR.md) لخطوات الرفع، و[docs/CONTEXT_GUARD.md](docs/CONTEXT_GUARD.md) للتفاصيل التقنية بالإنجليزية.
