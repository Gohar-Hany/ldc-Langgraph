# الدليل الشامل والمفصل للمرحلة الرابعة: الأدوات الخارجية والموافقة البشرية
## (Phase 4: External APIs, Tavily Search & Human-in-the-Loop Workflows)

---

## 1. فكرة المرحلة الرابعة والهدف منها ببساطة

في المراحل السابقة:
* **المرحلة الأولى:** أسسنا عقل الـ Agent، وتصنيف النوايا الثمانية (8 Intents)، ومصفوفة الصلاحيات (RBAC).
* **المرحلة الثانية:** أضفنا استرجاع سياسات الشركة الداخلية من خلال الـ Agentic RAG و Qdrant Cloud.
* **المرحلة الثالثة:** ربطنا النظام بقاعدة بيانات علائقية سحابية (Supabase PostgreSQL) لنظام إدارة التذاكر الحقيقي.

### ما الذي تضيفه المرحلة الرابعة؟ (Enterprise Security & Real-World Telemetry)
في بيئات العمل الحقيقية للشركات الكبرى (Enterprise IT)، يواجه الـ AI Agent نوعين من التحديات الهامة جداً:
1. **معلومات خارج قاعدة المعرفة الداخلية (External World Knowledge):**
   لو مهندس أو موظف سأل: "هل سيرفرات AWS us-east-1 واقعة دلوقتي؟" أو "هل في مشكلة في خدمات GitHub أو Cloudflare؟" هذه البيانات حية وخارج نطاق ملفات الشركة الداخلية، ولا بد من استدعاء **أداة استعلام خارجية حية (External Search Tool)** للوصول لبيانات المزودين ومواقع الحالة التشغيلية (Status Pages).
2. **العمليات الحساسة وعالية الخطورة (High-Privilege Sensitive Operations):**
   لو موظف طلب: "اعمل Reboot لسيرفر الداتابيز الرئيسي" أو "اعمل Reset لباسورد الـ Root والـ Admin"، **مستحيل نترك الذكاء الاصطناعي ينفذ هذا الأمر بمفرده مباشرة مهما كانت درجة دقته!**
   هنا يأتي دور معيار **Human-in-the-Loop (HITL)**:
   يتوقف مسار الـ LangGraph فوراً في حالة انتظار (`Interrupt`)، ويتم إشعار المشرف أو مدير النظام، ولا يُستأنف التنفيذ إلا بقرار بشري معتمد (`Approve` أو `Reject`)، مع تسجيل العملية بالكامل في سجل الرقابة (`audit_logs`).

---

## 2. التقنيات والمفاهيم الجديدة في هذه المرحلة

### 1. محرك البحث الخارجي: `tavily-python>=0.8.1` (Tavily AI Search)
* **ما هو؟** محرك بحث مصمم خصيصاً للـ AI Agents والـ LLMs، يرجع نتائج ملخصة ومفلترة ومباشرة بدون إعلانات أو ضوضاء صفحات الويب العادية.
* **كيف وظفناه في مشروعنا؟**
  * بنينا سيرفيس `ExternalSearchService` في `app/services/external_search_service.py`.
  * إذا كان مفتاح `TAVILY_API_KEY` متوفراً، تقوم باستعلام الـ API وجلب أحدث تقارير الأعطال وروابط المزودين.
  * **المرونة والموثوقية (Resilient Fallback):** إذا لم يتوفر مفتاح API أو انقطع الاتصال، تقوم السيرفيس بالتحول الذاتي السلس إلى محرك فحص حالة الخدمات السحابية (AWS Health, GitHub Status, Cloudflare, Zoom, Slack) لضمان عدم توقف النظام أو الاختبارات أبداً.

### 2. معمارية الـ Human-in-the-Loop (HITL) عبر LangGraph Native Interrupt
* في الإصدارات الحديثة من LangGraph (`langgraph>=1.2`):
  * نستخدم دالة `from langgraph.types import interrupt` داخل العقدة (`handle_sensitive_operation_node`).
  * عند استدعاء `interrupt(payload)`، يتوقف الـ Graph ويحفظ الحالة الحالية في الـ Checkpointer (`MemorySaver`).
  * يرجع الـ API للعميل حالة `approval_required: true` و `approval_status: "PENDING"`.
* **استئناف التنفيذ (Resumption):**
  * يدخل المشرف (Senior Agent أو Admin) عبر الـ Endpoint المخصص:
    `POST /api/v1/chat/approvals/{thread_id}/decide`
  * يتم استئناف الـ Graph باستخدام `Command(resume={"approved": True, ...})`.
  * يستيقظ الـ Graph من نفس النقطة التي توقف عندها، وينفذ الأمر أو يلغيه ويوثق القرار في Supabase.

---

## 3. تفاصيل الـ Endpoints الجديدة في FastAPI

### 1. استعلام البحث الخارجي (External Vendor Telemetry)
* **Endpoint:** `POST /api/v1/chat`
* **الصلاحية المطلوبة:** `Support Agent` فأعلى.
* **جسم الطلب (Body):**
  ```json
  {
    "message": "Is AWS us-east-1 and GitHub experiencing any active service outages?",
    "thread_id": "session_external_01"
  }
  ```
* **الرد (Response):**
  يرجع الرد ملخصاً لحالة الخدمات، وروابط التقارير المرجعية، مع إضافة خطوة `handle_external_api_search` في مصفوفة التتبع `execution_trace`.

### 2. نقطة قرار المشرف البشري (HITL Supervisor Decision)
* **Endpoint:** `POST /api/v1/chat/approvals/{thread_id}/decide`
* **الصلاحية المطلوبة:** `Senior Agent` أو `Admin` فقط (محمية بـ RBAC: العميل العادي يحصل على `403 Forbidden`).
* **جسم الطلب (Body):**
  ```json
  {
    "approved": true,
    "reviewer_notes": "Emergency approved by Enterprise SOC Manager."
  }
  ```
* **الرد (Response):**
  استئناف التنفيذ وإرجاع نتيجة العملية، وتسجيل سجل تدقيق في جدول `audit_logs` في قاعدة بيانات Supabase.

### 3. فحص حالة التعليق (Check Pending Status)
* **Endpoint:** `GET /api/v1/chat/approvals/{thread_id}/status`
* يوضح ما إذا كانت المحادثة معلقة وتنتظر مراجعة بشرية أم أنها مكتملة.

---

## 4. سجل التدقيق الرقابي في Supabase (Audit Logs)

تُسجل كل خطوة في جدول `audit_logs` لضمان الامتثال الأمني:
* `sensitive_operation_request`: لحظة طلب المستخدم للعملية المعلقة.
* `sensitive_operation_approved`: لحظة موافقة المشرف مع تسجيل اسمه وتاريخ وملاحظات الموافقة.
* `sensitive_operation_rejected`: لحظة رفض العملية وسبب الرفض.

---

## 5. سيناريوهات الاختبار في Postman

تمت إضافة مجلد كامل جديد في `postman_collection.json`:
📁 **`09 - External APIs & Human-in-the-Loop (Phase 4)`**

1. **`1. External API - Cloud Vendor Status via Tavily`**: اختبار البحث الخارجي واسترجاع حالة السيرفرات.
2. **`2. HITL - Trigger Sensitive Operation`**: اختبار إيقاف الـ Graph وطلب موافقة المشرف (`PENDING`).
3. **`3. HITL - Check Pending Approval Status`**: فحص حالة الـ Thread والتأكد من أنه في وضع الانتظار.
4. **`4. HITL - Supervisor Approve Sensitive Operation`**: اعتماد العملية واستئناف التنفيذ بنجاح.
5. **`5. HITL - RBAC Guard (403 Forbidden)`**: التحقق من منع العميل العادي من اعتماد العمليات الحساسة.

---

## 6. الاختبارات الآلية (Automated Pytest Suite)

* **`tests/unit/test_external_search.py`**: اختبارات الوحدة لمحرك Tavily ومعالجة الـ Timeout والـ Fallback.
* **`tests/integration/test_hitl_workflow.py`**: اختبارات التكامل الشاملة لدورة حياة الـ Interrupt والـ Resume وحماية الـ RBAC.
