# Universal AI Workflow V6.9 — الفريق الداخلي

هذه النسخة لا تستدعي نموذج AI آخر ولا تعمل في الخلفية. ينفّذ المساعد الحالي الخطوات بنفسه ويستخدم سكربت الحالة لتحديد الدور التالي.

1. سجّل خطة تشغيل بواسطة `python scripts/workflow.py plan plan.json`.
2. ابدأ `python scripts/uw_internal_auto.py --run RUN_ID init`.
3. اعرف المهمة الجاهزة: `python scripts/uw_internal_auto.py --run RUN_ID next`.
4. نفّذ دور Architect ثم Developer ثم Tester ثم Reviewer داخل بيئة المساعد المتاحة.
5. بعد كل دور سجّل دليلًا محددًا: `python scripts/uw_internal_auto.py --run RUN_ID record TASK_ID architect --evidence "..."`.
6. لإنهاء المهمة: `python scripts/uw_internal_auto.py --run RUN_ID record TASK_ID reviewer --evidence "..." --approve`.
7. عند رفض المراجعة أعد دورة Developer/Tester/Reviewer.
8. للتقرير: `python scripts/uw_internal_auto.py --run RUN_ID report`.

اكتب في الخطة `depends_on: [TASK_ID]` للمهام التابعة. بعد إغلاق المحادثة يستكمل المساعد من ملف `.ai/runs/RUN_ID/internal-auto.json`.

**قيود مهمة:** لا تنفّذ هذه الأوامر كود المشروع ولا تشغّل اختبارات نيابة عن المساعد. الأدلة نصية يكتبها المساعد، وليست تحققًا مستقلًا. لا يسمح السجل بتجاوز الاعتماديات، ولا يربط تلقائيًا حالة `TASKS.md` بحالة المحرك؛ استخدم التقرير المولّد للمزامنة بعد مراجعة المستخدم. لا تعدّل خطة مسجلة أثناء التنفيذ؛ تغيير الاعتماديات أو شروط القبول يُوقف الاستكمال.

**إضافة V6.9.1:** الاستكمال بعد إغلاق المحادثة لا يحل وحده مشكلة نفاد التوكن إذا تابعت نفس الجلسة. استخدم `uw_context_guard.py` (`brief` / `check` / `prompt` / `trim`) واجعل لكل مهمة محادثة جديدة. راجع [V6_9_1_GUIDE_AR.md](V6_9_1_GUIDE_AR.md).
