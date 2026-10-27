# Universal AI Workflow V6.11.0 — النشر على GitHub وأوامر المساعدات

## نشر المستودع (النسخة المحدّثة)

1. هذه الملفات جاهزة للرفع كما هي: راجع `git status` وتأكد من عدم وجود أسرار أو بيانات مشاريع خاصة.
2. من داخل مجلد المستودع (إذا كان مستنسخًا وعليه الـ remote الصحيح):

```powershell
git status
git add -A
git commit -m "Release Universal AI Workflow 6.11.0 - self-instantiating uw-auto"
git branch -M main
git remote -v
# إن لم يكن origin معرّفًا:
# git remote add origin https://github.com/salysat/Universal-AI-Workflow.git
git pull --rebase origin main
git push -u origin main
```

3. لمستودع جديد من الصفر (إن أردت تاريخًا جديدًا):

```powershell
git init
git add .
git commit -m "Release Universal AI Workflow 6.11.0 - self-instantiating uw-auto"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/Universal-AI-Workflow.git
git push -u origin main
```

> لا ترفع `.ai/runs/` (مستبعد في `.gitignore`) ولا أي نسخة احتياطية محلية ولا ملفات تحتوي على توكنات أو كلمات مرور. لا يُنفَّذ `git push` من هذه البيئة؛ نفّذيه أنت بعد مراجعة `git diff --stat`.

## التحقق قبل الرفع (مهم)

```powershell
py -3 scripts\workflow.py validate
py -3 scripts\generate_commands.py --check
py -3 -m unittest discover -s tests -q
py -3 scripts\workflow.py plan --file examples\sample-plan.json
py -3 scripts\uw_context_guard.py --root . brief --run demo
py -3 scripts\uw_context_guard.py --root . check --run demo --max-tokens 12000
py -3 scripts\uw_autopilot.py boot
py -3 scripts\uw_autopilot.py spawn --run auto
```

النتيجة المتوقعة: `PASS`، `OUT OF SYNC: 0 files`، `OK` (101 اختبارًا)، ثم `brief` يعرض المهمة الجاهزة و`check` يُرجع `over_budget: false`، و`boot`/`spawn` يُرجعان JSON مضغوطًا فيه `mode` و`sessions` و`spawn_file` مع ملفات `SESSION-*.md`. ملف `.ai/runs/` و`uw-auto.config.json` و`agents.local.json` مستبعدة في `.gitignore` فلا تُرفع. `check` يعمل حتى بدون خطة مسجلة، أمّا `brief` فيحتاج خطة مسجلة ويعطي خطأً واضحًا إن لم توجد.

## تثبيت من GitHub داخل مشروع

على Windows (يحتاج Git وPython 3، ومساحة المشروع موجودة):

```powershell
git clone https://github.com/YOUR_USERNAME/Universal-AI-Workflow.git "$env:TEMP\universal-ai-workflow"
py -3 "$env:TEMP\universal-ai-workflow\scripts\install_ai.py" --source "$env:TEMP\universal-ai-workflow" --target "D:\MyProject" --platforms all --dry-run
py -3 "$env:TEMP\universal-ai-workflow\scripts\install_ai.py" --source "$env:TEMP\universal-ai-workflow" --target "D:\MyProject" --platforms all
```

**لتقليل العبء الثابت:** استخدم منصة واحدة فقط، مثل `--platforms codex` بدل `all`. التثبيت الكامل ينسخ 19 أمرًا × 6 منصات = 114 ملف تعريف، وبعض المضيفات تحقن وصف المهارات في كل دورة.

### أوامر المحادثة بعد التثبيت

- Claude, Gemini, Cursor, OpenCode: `/uw-init`, `/uw-team`, `/uw-resume`, `/uw-status`, `/uw-context`, `/uw-auto` (إذا دعم الإصدار أوامر المشروع؛ Gemini يحتاج `/commands reload`).
- GitHub Copilot: قد تظهر الأوامر كـ `/uw-team` ضمن prompt files، حسب بيئة VS Code؛ يمكن استدعاء الملف يدويًا.
- Codex: استدعاء Skill من `.agents/skills/<name>/SKILL.md` بحسب واجهة العميل؛ ليس مضمونًا أن `/uw-team` متاح في كل إصدار.
- `@` يستخدم غالبًا للإشارة إلى ملف/أداة/مساعد، وليس بديلًا موحدًا لأوامر slash. مثل `@AGENTS.md نفّذ uw-team`.
- `$` يُستخدم في بعض واجهات Codex لاستدعاء Skills (مثل `$uw-context`)؛ يعتمد ذلك على الواجهة. `$ARGUMENTS` داخل تعريفات الأوامر متغير قالب وليس أمر تشغيل.
- ChatGPT العادي: ارفع الملفات أو استخدم Project/Work بإمكانية الوصول إلى المستودع، واطلب: `اقرأ AGENTS.md و .agents/skills/uw-context/SKILL.md ثم نفّذ المهمة`. النص المكتوب لا يفعّل أوامر مدمجة في واجهة ChatGPT.

**ليس هناك صيغة واحدة تعمل تلقائيًا مع كل AI.** الحزمة تجهّز تعريفات أصلية لكل منصة، والمستخدم يختار الرمز الذي تدعمه الواجهة.

## الاستخدام اليومي لتجنب نفاد التوكن

```powershell
py -3 scripts\uw_context_guard.py --root . check --run RUN --max-tokens 12000
py -3 scripts\uw_context_guard.py --root . brief --run RUN
py -3 scripts\uw_context_guard.py --root . prompt --run RUN
py -3 scripts\uw_context_guard.py --root . trim --run RUN --max-chars 800 --apply
```

قاعدة ذهبية: **مهمة واحدة (أو دورة أدوار واحدة) لكل محادثة** عند غياب وكلاء CLI خارجيين. راجع [V6_9_1_GUIDE_AR.md](V6_9_1_GUIDE_AR.md).

**الأمان:** تثبيت مستودع يعني نسخ ملفاته إلى مشروعك. راجع المصدر والتغييرات، ولا تجعل المساعد ينفذ تثبيتات أو أوامر شبكة دون موافقتك. لا يوجد commit/push تلقائي من أدوات الحزمة.
