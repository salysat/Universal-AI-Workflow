# دليل الاستخدام العربي — Universal AI Workflow V4

## المتطلبات
Python 3.10 أو أحدث، Git، وبيئة الذكاء الاصطناعي التي تختارها إذا أردت التنفيذ الفعلي. السكربت يدير المهام والفروع والتوثيق، **لكنه لا يشغّل نموذج ذكاء اصطناعي بنفسه**.

## تشغيل سريع على Windows
افتح PowerShell داخل مجلد الحزمة بعد فك ZIP:
```powershell
py -3 scripts\workflow.py validate
py -3 -m unittest discover -s tests -v
py -3 scripts\workflow.py init --project "MyProject"
py -3 scripts\workflow.py status
```

## كيف تستخدمها مع مشروعك
1. احتفظ بنسخة من ملفات مشروعك أولًا. انقل `AGENTS.md` وملفات `.ai` وأدوات `scripts` مع دمج أي تعليمات موجودة بدل محوها.
2. افتح المشروع في Claude Code أو Codex أو Cursor أو Gemini أو OpenCode، واطلب قراءة `AGENTS.md` و`.ai/HANDOFF.md`.
3. استخدم `plan` مع ملف JSON لوصف مهام مستقلة ومسارات ملكيتها. لا تضع مهمتين تعدّلان الملف نفسه.
4. استخدم `worktree` لإنشاء مجلد وفرع Git مستقل لكل مهمة، ثم شغّل أداة الوكيل المتوافقة يدويًا داخل كل مجلد.
5. شغّل البناء والاختبارات وسجّل الأدلة؛ بعدها راجع الفروع واستخدم `integrate` بموافقة صريحة، ثم اختبر مجددًا.

## مهم
الملفات الإرشادية لا تمنح الوكيل صلاحيات جديدة. أوامر التثبيت والحذف والدفع إلى GitHub ونشر الإنتاج لا تُشغّل تلقائيًا. يفضّل إبقاء المستودع خاصًا حتى فحص التراخيص والأسرار.

## الرفع إلى GitHub
أنشئ Repository فارغًا من GitHub دون README إضافي، ثم:
```powershell
git init
git add .
git commit -m "Initial V4"
git branch -M main
git remote add origin https://github.com/USERNAME/Universal-AI-Workflow.git
git push -u origin main
```
استبدل `USERNAME` باسم المستخدم الخاص بك. للمزيد راجع `docs/OPERATIONS.md`.
