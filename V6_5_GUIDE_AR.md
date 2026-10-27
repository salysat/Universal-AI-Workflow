# V6.5 — Audit & Command Registry

- استيراد نتائج فحص SARIF أو JSON وإنشاء **مسودة مهام فقط**:
  `python scripts/uw_audit.py --input audit-report.json --run security01 --output audit-plan.json`
- الفاحص الأصلي غير مرفق. إذا توفرت نسخة `.ps1` فالتشغيل يحتاج `--scanner FILE.ps1 --approve-scanner-execution` وتثبيت PowerShell 7.
- توليد الأوامر: `python scripts/generate_commands.py` ثم `python scripts/generate_commands.py --check`.
- دعم Claude/Cursor/OpenCode/Gemini/Copilot/Codex Skills يتم بنسخ ملفات تعريف داخل المشروع؛ لا يؤكد توفر أي CLI أو توثيقه.
- تستمر اختبارات GitHub Actions على Ubuntu وWindows وmacOS بعد رفع الملف إلى مستودعك؛ لم تنفذ على حسابك هنا.
- `uw-auto` ما زال يتطلب موافقة صريحة لإطلاق الـ CLIs؛ لم يُختبر مزود AI حقيقي هنا.
