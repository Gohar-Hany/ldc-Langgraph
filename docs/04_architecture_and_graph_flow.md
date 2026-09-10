# 04 - المخطط المعماري الكامل للـ LangGraph ومسار التنفيذ
## (Enterprise LangGraph Architecture, Visual Flow & RBAC Intents)

---

## 1. مخطط الجراف الكامل (Mermaid Architecture Diagram)

![Enterprise LangGraph Flow](graph.png)

هذا هو المخطط البياني البرمجي الكامل والمستخرج مباشرة من محرك `enterprise_agent_graph` بعد ربط المرحلة الأولى والثانية:


```mermaid
---
config:
  flowchart:
    curve: linear
---
graph TD;
	__start__([__start__]):::first
	receive_message(receive_message)
	classify_intent(classify_intent)
	router_node(router_node)
	handle_greeting(handle_greeting)
	handle_my_tickets_search(handle_my_tickets_search)
	handle_ticket_create_update(handle_ticket_create_update)
	handle_external_api_search(handle_external_api_search)
	handle_sensitive_operation(handle_sensitive_operation)
	handle_database_query(handle_database_query)
	handle_unauthorized(handle_unauthorized)
	handle_fallback(handle_fallback)
	rag_retrieve(rag_retrieve)
	rag_grade(rag_grade)
	rag_generate(rag_generate)
	rag_rewrite(rag_rewrite)
	rag_fallback(rag_fallback)
	__end__([__end__]):::last

	__start__ --> receive_message;
	receive_message --> classify_intent;
	classify_intent --> router_node;

	router_node -. handle_knowledge_search .-> rag_retrieve;
	router_node -. handle_greeting .-> handle_greeting;
	router_node -. handle_my_tickets_search .-> handle_my_tickets_search;
	router_node -. handle_ticket_create_update .-> handle_ticket_create_update;
	router_node -. handle_external_api_search .-> handle_external_api_search;
	router_node -. handle_sensitive_operation .-> handle_sensitive_operation;
	router_node -. handle_database_query .-> handle_database_query;
	router_node -. handle_unauthorized .-> handle_unauthorized;
	router_node -. handle_fallback .-> handle_fallback;

	rag_retrieve --> rag_grade;
	rag_grade -. generate .-> rag_generate;
	rag_grade -. rewrite .-> rag_rewrite;
	rag_grade -. fallback .-> rag_fallback;
	rag_rewrite --> rag_retrieve;

	handle_database_query --> __end__;
	handle_external_api_search --> __end__;
	handle_fallback --> __end__;
	handle_greeting --> __end__;
	handle_my_tickets_search --> __end__;
	handle_sensitive_operation --> __end__;
	handle_ticket_create_update --> __end__;
	handle_unauthorized --> __end__;
	rag_fallback --> __end__;
	rag_generate --> __end__;

	classDef default fill:#f2f0ff,stroke:#6366f1,stroke-width:1px,line-height:1.2
	classDef first fill:#e0e7ff,stroke:#4338ca,stroke-width:2px
	classDef last fill:#dcfce7,stroke:#15803d,stroke-width:2px
```

---

## 2. جدول النوايا الثمانية ومصفوفة الصلاحيات (The 8 Supported Intents & RBAC Matrix)

| # | النية (Intent) | الوصف والمعنى | الأدوار المصرح لها (Authorized Roles) | أمثلة توضيحية |
| :--- | :--- | :--- | :--- | :--- |
| **1** | `greeting` | التحيات، الترحيب، والاستفسار عن هوية المساعد | **الجميع**<br>(Customer, Support Agent, Senior Agent, Admin) | "Hello, good morning", "السلام عليكم", "Hi, who are you?" |
| **2** | `knowledge_search` | البحث عن سياسات الشركة، أدلة الـ VPN، الواي فاي، كلمات المرور | **الجميع**<br>(Customer, Support Agent, Senior Agent, Admin) | "How to configure VPN on MacOS?", "كود الخطأ 0x80070005", "شروط باسوورد الموظفين" |
| **3** | `my_tickets_search` | الاستعلام عن حالة التذاكر السابقة الخاصة بنفس الموظف | **الجميع**<br>(كل مستخدم لتذاكره الخاصة فقط) | "Check status of my ticket #1042", "وريني تذاكري المفتوحة" |
| **4** | `ticket_create_update` | إنشاء تذكرة دعم فني جديدة أو تعديل أولوية تذكرة قائمة | **Support Agent, Senior Agent, Admin**<br>*(محظور على العميل العادي)* | "Create a new support ticket for email outage", "Update ticket #44 priority to high" |
| **5** | `external_api_search` | الاستعلام من خدمات وواجهات خارجية (Stripe, GitHub, Cloud APIs) | **Support Agent, Senior Agent, Admin**<br>*(محظور على العميل العادي)* | "Query external API for Stripe payment status", "Check GitHub API incident status" |
| **6** | `sensitive_operation` | عمليات عالية الخطورة (تغيير باسوورد مستخدم، ترقية صلاحيات، ريبوت سيرفر) | **Senior Agent, Admin**<br>*(محظور على Customer و Support Agent)* | "Reset password for user John", "Elevate permissions to superuser", "Reboot staging server" |
| **7** | `database_query_operation` | استعلامات SQL المباشرة، فحص الجداول، التعديل على قاعدة البيانات | **Admin فقط**<br>*(محظور على كافة الأدوار الأخرى)* | "Run SQL query on users table", "Select * from audit_logs", "Drop table logs" |
| **8** | `out_of_scope` | أسئلة عامة أو ترفيهية لا علاقة لها بالدعم الفني المؤسسي | **يتم توجيهه لعقدة الاعتذار (Fallback)** | "What is the weather in Tokyo?", "قولي نكتة", "ما هي عاصمة إيطاليا؟" |

---

## 3. كيف يعمل مصنف النوايا (Intent Classifier) بالتفصيل؟

المصنف يعمل عبر **نظام هجين ذكي ثنائي الطبقات (Dual-Layer Robust Architecture)** يضمن دقة خيالية وعدم سقوط السيرفر نهائياً:

### الطبقة الأولى: التصنيف بنموذج الذكاء الاصطناعي مع الـ Structured Output
1. يستلم الموديل (Qwen 2.5 72B عبر OpenRouter أو Aurai-3.0) رسالة المستخدم بالإضافة إلى `CLASSIFIER_SYSTEM_PROMPT` في ملف `classifier_prompt.py`.
2. بدلاً من أن يجيب بنص حر، يتم إجباره برمجياً عبر تقنية **`with_structured_output`** على إرجاع كائن Pydantic مضبوط بالمللي (`IntentClassificationOutput`):
   - `intent`: واحدة من النوايا الثمانية المعتمدة فقط.
   - `confidence`: رقم عشري من 0.0 إلى 1.0 يمثل نسبة التأكد.
   - `reasoning`: سطر يشرح سبب اختياره لهذه النية.
   - `extracted_entities`: الكيانات المستخرجة (رقم التذكرة، اسم المستخدم، اسم السيرفر).

### الطبقة الثانية: صمام الأمان الحتمي (Deterministic Fallback)
لو حدث انقطاع في الإنترنت، أو أرجع مزود الـ LLM خطأ 429 (Rate Limit) أو 500:
1. الـ Try/Except يلتقط الخطأ فوراً في `classify_node.py`.
2. يتم تشغيل الدالة الحتمية `classify_intent_fallback` في `llm_service.py`.
3. الدالة تفحص الكلمات المفتاحية باللغتين (العربية والإنجليزية) ومطابقة التعبيرات القياسية (Regex) وتحدد النية الصحيحة فوراً بدون تأخير وبدون توقف السيرفر!
