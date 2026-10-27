# أوامر ومهارات V6.11.0

الحزمة توفّر **19 أمرًا** (كانت 12 في V4.2) بتعريفات أصلية لكل منصة. يمكنك استخدام `/uw-plan` و`/uw-review` و`/uw-build` و`/uw-test` و`/uw-context` وغيرها في التطبيقات التي تدعم أوامر المشروع. وفي Codex اختر المهارة عبر `$uw-plan` أو `/skills`، وفي ChatGPT عبر `@` بعد استيراد المهارة في واجهة تدعم المهارات. **لا يظهر الأمر في كل التطبيقات لمجرد رفع المستودع على GitHub.**

## تثبيتها داخل مشروع آخر

```powershell
py -3 scripts\install_commands.py --target "E:\Projects\MyApp" --platforms all --dry-run
py -3 scripts\install_commands.py --target "E:\Projects\MyApp" --platforms all
```

يمكن اختيار تطبيق محدد: `--platforms claude cursor gemini opencode copilot codex`. النسخ يتجاوز الملفات الموجودة افتراضيًا. لتثبيت `scripts/uw_context_guard.py` وبقية وقت التشغيل استخدم `scripts/install_ai.py`. يلزم دمج `AGENTS.md` وأي بروتوكول ذاكرة تريده للمشروع بصورة منفصلة بعد المراجعة.

**نصيحة لتقليل الاستهلاك:** ثبّت منصة واحدة فقط (`--platforms codex`) بدل `all`؛ التثبيت الكامل ينسخ 19 تعريفًا × 6 منصات = 114 ملفًا، وبعض المضيفات تحقن وصف المهارات في كل دورة.

أمثلة: `/uw-recon` لتحليل المشروع دون تعديل، `/uw-plan` لوضع خطة، `/uw-build` للتنفيذ، `/uw-review` للمراجعة، `/uw-handoff` لتسليم السياق، `/uw-agents` لوضع خطة لتوزيع العمل على عدة وكلاء، `/uw-context` لضبط ميزانية السياق والتسليم لمحادثة جديدة.

## الأمر الجديد `uw-context` (V6.9.1)

تقسيم المهام هو تقسيم **ملكية ملفات** وليس تقسيم **نافذة السياق**. عند العمل داخل نفس المساعد تبقى كل المهام والأدوار والتقارير في محادثة واحدة. الحل:

```powershell
py -3 scripts\uw_context_guard.py --root . brief  --run RUN
py -3 scripts\uw_context_guard.py --root . check  --run RUN --max-tokens 12000
py -3 scripts\uw_context_guard.py --root . prompt --run RUN
py -3 scripts\uw_context_guard.py --root . trim   --run RUN --max-chars 800 --apply
```

التفاصيل: [V6_9_1_GUIDE_AR.md](../V6_9_1_GUIDE_AR.md) و[CONTEXT_GUARD.md](CONTEXT_GUARD.md).

## `uw-auto` صار الطيار الآلي (V6.10)

كتابة `uw-auto` وحدها تشغّل `scripts/uw_autopilot.py boot`: ينشئ إعدادًا آمنًا، يولّد خطة من بنية المستودع، يوجّه مهارات محلية مُراجَعة عبر `scripts/uw_skill_router.py`، يقيس ميزانية السياق، ويكتب `MISSION.md` (≤ 450 كلمة). في الوضع **external** (اختياري صريح منذ V6.11) كل مهمة في عملية/سياق/worktree مستقل، وفي **self** تُستنسخ نسخ أصلية من نفس المساعد، وفي **sessions** محادثات جديدة متسلسلة. لا أسئلة عن خطة أو وضع أو مهارة. راجع [AUTOPILOT.md](AUTOPILOT.md) و[SELF_SESSIONS.md](SELF_SESSIONS.md).

**ملاحظة:** هذه الأوامر تعرّف خطوات للمساعد وليست ضمانًا بتشغيل الأوامر أو الوكلاء تلقائيًا. يعتمد التنفيذ الفعلي على أدوات وصلاحيات التطبيق. جميع تعريفات الأوامر مصدرها `commands/registry.json`؛ بعد تعديله شغّل `python scripts/generate_commands.py` ثم `--check` قبل النشر.
