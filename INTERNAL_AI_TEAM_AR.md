# فريق ذكاء اصطناعي داخل نفس الجلسة — V6.7

الهدف: نفس AI يتولى أربعة أدوار متسلسلة (Architect → Developer → Tester → Reviewer)، دون استدعاء أدوات AI خارجية أو الحاجة لحسابات جديدة.

**تمييز مهم:** هذا تنفيذ لأدوار منطقية داخل نفس المساعد وليس أربع نسخ مستقلة من النموذج؛ وقد لا يكون تقييم Reviewer مستقلاً معرفيًا. عند توفر دعم رسمي لوكلاء فرعيين داخل المنصة يمكن للمساعد استخدامه، وإلا يعمل بالتسلسل ولا يدّعي التوازي.

## التشغيل

```bash
python scripts/uw_internal_team.py start T001 "إصلاح شاشة الجلسات" --files src/Sessions.cs
python scripts/uw_internal_team.py next T001
python scripts/uw_internal_team.py record T001 architect --report "خطة وفحوص" --evidence "فحص الملفات"
python scripts/uw_internal_team.py next T001
python scripts/uw_internal_team.py record T001 developer --report "تم تعديل الملفات" --evidence "git diff"
python scripts/uw_internal_team.py record T001 tester --report "اختبارات" --evidence "اسم الأمر ومخرجاته وexit code"
python scripts/uw_internal_team.py record T001 reviewer --report "مراجعة" --evidence "diff + test results" --approve
```

لا يتم تطبيق أي تغييرات بواسطة أداة الفريق نفسها. يقوم المساعد المضيف بالعمل والتوثيق؛ ويتولى Git workflow القديم العزل والدمج والموافقة.

## الملفات

`uw_file_edit.py` يدعم فقط استبدال نص UTF-8 بشكل فريد وتعديل مفتاح JSON موجود أو CSV أحادي الصف (وضع المعاينة افتراضيًا، ثم `--apply` مع نسخة احتياطية). أنواع Office وPDF والصور تحتاج أدوات متخصصة فعلية؛ الاكتشاف لا يعني تحريرها.

## التوكنات

`uw_efficiency.py usage-add` يقبل أرقام استخدام موثقة من المضيف فقط. لا يمكن معرفة استهلاك ChatGPT/Work الحقيقي تلقائيًا من ملفات المشروع أو من نموذج داخلي ما لم تعرض المنصة القياسات. تجنب تسمية التقديرات أرقامًا فعلية.

**V6.9.1 — حدّ السياق:** الأدوار الأربعة داخل نفس المساعد تعني أن `next` يُعيد `prior_evidence` السابقة وأن `status` يطبع كل الأدلة؛ أي أن السياق يكبر مع كل دور. استخدم `scripts/uw_context_guard.py brief` بدل الحالة الكاملة، و`check` قبل كل دور، و`prompt` للتسليم إلى محادثة جديدة عند `over_budget`. راجع [V6_9_1_GUIDE_AR.md](V6_9_1_GUIDE_AR.md).

## المهارات

يجوز للمساعد قراءة Skill مُراجَعة واستخدام إرشاداتها ضمن قدراته؛ لا تنزيل أو تنفيذ سكربتات من الإنترنت أو تثبيت تلقائي دون موافقة المستخدم والتحقق من المصدر والصلاحيات. لا يعد العثور على مهارة إذنًا بالتنفيذ.
