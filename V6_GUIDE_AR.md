# Universal AI Workflow V6 — القدرات الجديدة

## قبل التشغيل

الوظائف التي تستخدم الذكاء الاصطناعي تحتاج CLI حقيقيًا مثبتًا ومصادقًا عليه وتكوين `examples/agents.roles.json` لأدوار `architect`, `developer`, `reviewer`. لا تتضمن الحزمة أي نموذج أو مفاتيح API. جميع استدعاءات LLM تتطلب `--approve-llm`. ملف المثال الافتراضي يستخدم `python -c` كتجربة وهمية، وليس LLM.

## 1. التخطيط الفعلي عبر LLM

```powershell
python scripts/uw_v6.py --config examples/agents.roles.json --approve-llm plan --run lawfirm --description "أنشئ وحدة إدارة الجلسات لنظام محاماة ASP.NET Core وSQL Server" --output draft_llm.json
```

يفحص المحرك صيغة JSON والملكية والتبعيات، ويكتب مسودة تتطلب مراجعة واعتمادًا قبل تطبيقها:

```powershell
python scripts/workflow.py plan --file draft_llm.json
```

## 2. حلقة إصلاح/اختبار

يُشترط إعداد Git worktree للمهمة قبل التشغيل. نفذ فقط اختبارات موثوقة بالمسارات/الأوامر المسموحة.

```powershell
python scripts/uw_v6.py --config examples/agents.roles.json --approve-llm repair --run lawfirm --task 02_developer --test-argv '["dotnet","test","--no-restore"]' --allow-test dotnet --attempts 3
```

تتوقف المحاولة عند النجاح أو عدد المحاولات المحدد أو فشل الوكيل أو تعديل ملفات غير مملوكة. النجاح في الاختبار لا يعني قبول التغييرات دون مراجعة بشرية.

## 3. Reviewer مستقل

```powershell
python scripts/uw_v6.py --config examples/agents.roles.json --approve-llm review --run lawfirm --task 02_developer
```

يشغل جلسة أخرى في دور Reviewer مع تعليمات عدم تعديل الملفات. يفحص `git diff` للتغييرات المتتبعة، ولا يشمل الملفات غير المتتبعة بعد، ويُوقف العملية عند تغير حالة الملفات أثناء المراجعة. نتيجة المراجعة استشارية ولا تعني السماح بالدمج.

## 4. لوحة حية

```powershell
python scripts/uw_dashboard.py --port 8787
```

افتح `http://127.0.0.1:8787`. لوحة محلية للقراءة فقط، تعرض المهام وحالتها والتقارير الموجودة كل 3 ثوانٍ.

## 5. التوكن والتكلفة

`uw_v6.py` يتعرف على `usage.input_tokens` و`usage.output_tokens` من JSON صادر عن CLI، أو سجلات الأحداث بصيغة JSON Lines (عند استخدام موضع القراءة المخصص). إذا أعاد المزود `total_cost_usd` يسجله كقيمة مباشرة. يمكن حساب تقدير عبر أسعار مدخلة يدويًا لكنه **ليس فاتورة فعلية**. إذا كانت المخرجات نصية فقط أو بدون عدادات يضع `null`، ولا يختلق بيانات.

## القيود

- وظيفة Planner وReviewer والإصلاح تعتمد على CLI صالح ذي صلاحيات ملائمة، ولا توجد تجربة تكاملية مع حساب مزود حي داخل هذه البيئة.
- تقارير `repair` و`review` تحفظ في `.ai/runs/<run>/v6/`.
- لا يوجد دمج أو رفع أو نشر تلقائي، ولا ضمان لإصلاح كل الأخطاء حتى النجاح.
- المراجعة المستقلة هنا جلسة مميزة، وقد تكون باستخدام نفس النموذج؛ ليست ضمانًا لاستقلال الحكم.
