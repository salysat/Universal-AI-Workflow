# تثبيت Universal AI Workflow داخل مساعد البرمجة

> المستودع خاص: يلزم أن يستطيع جهازك أو بيئة المساعد الوصول إلى GitHub بتسجيل دخول Git Credential Manager أو SSH. إرسال رابط خاص في محادثة لا يمنح المساعد حق الوصول. لا تلصق GitHub PAT في المحادثة أو الرابط.

## انسخ هذه الرسالة إلى مساعد البرمجة

```
ثبّت Universal AI Workflow من https://github.com/salysat/Universal-AI-Workflow
في جذر المشروع الحالي. استخدم صلاحيات Git التي أعددتها مسبقًا، ولا تطلب مني كشف التوكن أو أي أسرار.
افحص README وINSTALL_FOR_AI_AR.md وscripts/install_ai.py قبل التنفيذ.
اعرض الملفات التي ستضاف، وحافظ على AGENTS.md وملفات المشروع الحالية، ولا تستخدم --overwrite.
بعد الموافقة، نفّذ التثبيت ثم اختبر python scripts/workflow.py validate
وpython -m unittest discover -s tests -v من نسخة المصدر إن كانت متوفرة.
اذكر الأوامر المتاحة بحسب المساعد ولا تدّعي ظهور @ أو $ أو / إن لم تدعمها واجهته.
```

## التثبيت المحلي من ملف ZIP (Windows PowerShell)

```powershell
# فك ضغط الحزمة، ثم افتح المجلد المستخرج
py -3 scripts\install_ai.py --source . --target "C:\Path\To\MyProject" --platforms all --dry-run
py -3 scripts\install_ai.py --source . --target "C:\Path\To\MyProject" --platforms all
```

## تثبيت النسخة المنشورة من GitHub (إذا كانت مُتاحة لحسابك)

```powershell
# بعد تثبيت Git وضبط تسجيل الدخول، نفّذ من أي مجلد:
git clone https://github.com/salysat/Universal-AI-Workflow.git
cd Universal-AI-Workflow
py -3 scripts\install_ai.py --source . --target "C:\Path\To\MyProject" --platforms all
```

## واجهات الأوامر

| المساعد | أمر مثال | ملاحظات |
| --- | --- | --- |
| Claude Code | `/uw-plan` | ملفات `.claude/commands` |
| Gemini CLI | `/uw-plan` | ملفات `.gemini/commands`، استخدم `/commands reload` |
| Codex CLI / IDE | `$uw-plan` | ملفات `.agents/skills/uw-plan/SKILL.md`؛ استخدم `/skills` إن لزم |
| ChatGPT Work مع Skills | `@uw-plan` | يحتاج تثبيت Skill بطريقة يدعمها المنتج؛ نسخ الملفات على جهازك **لا** يثبّتها تلقائيًا في ChatGPT |
| GitHub Copilot VS Code | `/uw-plan` | ملفات `.github/prompts/uw-plan.prompt.md`؛ مع جلسات Local الداعمة |
| Cursor | `/uw-plan` | حسب دعم نسخة Cursor للأوامر المخصصة |
| OpenCode | `/uw-plan` | ملفات `.opencode/commands` |

الأوامر الأخرى: `uw-help`, `uw-build`, `uw-review`, `uw-test`, `uw-security`, `uw-status`, `uw-agents`, `uw-handoff`, `uw-resume`, `uw-ship`, `uw-recon`, `uw-audit`, `uw-auto`, `uw-auto-v5`, `uw-team`, `uw-v6`, `uw-init`، و**`uw-context`** (جديد في 6.9.1: ميزانية السياق والتسليم لمحادثة جديدة).

**لتقليل العبء الثابت:** استخدم `--platforms codex` (أو المنصة التي تستعملها فعلًا) بدل `all`. التثبيت الكامل ينسخ 19 أمرًا × 6 منصات = 114 ملف تعريف. بعد التثبيت جرّب:

```powershell
py -3 scripts\uw_context_guard.py --root . check --run RUN --max-tokens 12000
py -3 scripts\uw_context_guard.py --root . brief --run RUN
```

**الاستخدام اليومي (V6.11):** اكتب `$uw-auto` فقط. سيشغّل المساعد `boot` ثم `spawn` الذي يولّد حزم `SESSION-*.md` — أي نسخ متعددة من **نفس المساعد**، لكل نسخة سياق مستقل، بلا أي مساعد خارجي. الملفات `uw_autopilot.py` و`uw_skill_router.py` و`uw_context_guard.py` تُنسخ ضمن `RUNTIME_FILES`. لا تحتاج أي إعداد؛ وإن أردت وكلاء فرعيين أصليين اضبط `host_subagents: true` في `uw-auto.config.json`.التفاصيل: [V6_11_GUIDE_AR.md](V6_11_GUIDE_AR.md).

## حدود مهمة

- لا توجد طريقة تفرض كتابة `/` أو `@` أو `$` في **كل** واجهة محادثة. تلك الاختصارات ملك للمنصة نفسها.
- هذه المهارات نصوص تعليمات؛ تنفيذ ملفات Python يحتاج بيئة ملفات وتشغيل أوامر متاحة للمساعد.
- لا تُمكّن الأداة تلقائيًا من الوصول إلى مشروع محلي من ChatGPT العادي.
- ملفات `.ai/STATE.md` وغيرها تُنسخ عند الإنشاء فقط. ملف `AGENTS.md` القائم لا يُستبدل أبدًا بواسطة المثبت.
