# 02 - معمارية المشروع وخريطة التنفيذ المعتمدة
## (Enterprise Architecture & Implementation Roadmap)

---

## 1. سيناريو المشروع وأهدافه (Scenario & Objectives)

بناء **Role-Based Enterprise AI Support Agent** باستخدام **LangGraph** ومربوط بـ **FastAPI REST API**.

### مصفوفة الأدوار والصلاحيات (RBAC Matrix):
1. **Customer:** RAG Search + البحث في تذاكره الخاصة فقط.
2. **Support Agent:** الصلاحيات السابقة + إنشاء وتعديل التذاكر + البحث في External APIs.
3. **Senior Agent:** الصلاحيات السابقة + العمليات الحساسة (Sensitive Operations) بموافقة بشرية.
4. **Admin:** جميع الصلاحيات + استعلامات وعمليات قواعد البيانات (Database Operations).

---

## 2. المعمارية المعتمدة للمشروع (Modular Layered Architecture)

```text
ldc-Langgraph/
│
├── app/                           # الكود الأساسي للمشروع
│   ├── api/                       # [1] طبقة الـ API والـ Endpoints
│   │   ├── v1/
│   │   │   ├── endpoints/
│   │   │   │   ├── auth.py        # تسجيل الدخول وتوليد الـ Tokens
│   │   │   │   └── chat.py        # استقبال الرسائل وتشغيل الـ Agent
│   │   │   └── router.py          # تجميع مسارات v1
│   │   ├── middlewares/
│   │   │   ├── auth_middleware.py # فحص الـ JWT ومراقبة الريكويستات
│   │   │   └── error_handler.py   # معالجة الأخطاء وتوحيد الاستجابة
│   │   └── dependencies.py        # حارس الصلاحيات (RBAC Guards)
│   │
│   ├── agent/                     # [2] عقل ومنطق الـ LangGraph
│   │   ├── state.py               # الـ Agent State الموحدة
│   │   ├── prompts/               # ملفات الـ Prompts الموحدة
│   │   │   └── classifier_prompt.py
│   │   ├── nodes/                 # العقد الأساسية
│   │   │   ├── receive_node.py    # استقبال المدخلات وتجهيز الحالة
│   │   │   ├── classify_node.py   # تصنيف النوايا (Structured Output)
│   │   │   ├── router_node.py     # فحص الصلاحيات وتوجيه الفلو
│   │   │   └── response_nodes.py  # توليد الردود الخاصة بكل Intent
│   │   ├── edges/                 # قواعد التوجيه الشرطي
│   │   │   └── routing_rules.py
│   │   └── graph.py               # بناء وتجميع الـ StateGraph
│   │
│   ├── core/                      # [3] البنية التحتية والإعدادات
│   │   ├── config.py              # إدارة الإعدادات بـ Pydantic Settings
│   │   ├── security.py            # تشفير وفك الـ JWT وتشفير الباسووردات
│   │   └── logging.py             # السجلات المؤسسية (Structured Logging)
│   │
│   ├── schemas/                   # [4] العقود ونماذج البيانات (Pydantic Contracts)
│   │   ├── auth_schema.py         # نماذج الأدوار والمستخدمين والتوكنز
│   │   ├── chat_schema.py         # نماذج ريكويست وريسبونس الشات
│   │   └── intent_schema.py       # نموذج تصنيف الـ 7 Intents
│   │
│   ├── services/                  # [5] الخدمات الخارجية والـ LLM
│   │   └── llm_service.py         # إعداد واستدعاء الموديل
│   │
│   └── main.py                    # نقطة انطلاق تطبيق FastAPI
│
├── tests/                         # [6] الاختبارات الشاملة (Pytest)
│   ├── unit/
│   │   ├── test_intent_classifier.py
│   │   ├── test_rbac_router.py
│   │   └── test_auth.py
│   └── integration/
│       └── test_api_chat.py
│
├── docs/                          # [7] التوثيق وملاحظات المذاكرة
├── .env.example                   # المتغيرات البيئية النموذجية
├── requirements.txt               # المكتبات والاعتماديات
└── README.md
```

---

## 3. الترتيب المنطقي للبناء (Execution Order)

1. **الخطوة 1: ملف الاعتماديات (`requirements.txt`)**
   - فحص واختيار أحدث وأدق نسخ مستقرة للمكتبات على PyPI.
2. **الخطوة 2: الإعدادات والأمان الأساسي (`app/core/`)**
   - `config.py` لقراءة الإعدادات.
   - `security.py` لتشفير وفك الـ JWT.
3. **الخطوة 3: العقود والـ Schemas (`app/schemas/`)**
   - `auth_schema.py` (تعريف الـ 4 Roles).
   - `intent_schema.py` (تعريف الـ 7 Intents كـ Structured Output).
   - `chat_schema.py` (مدخلات ومخرجات الشات).
4. **الخطوة 4: منطق الـ Agent والـ LangGraph (`app/agent/`)**
   - `state.py` ⬅️ `prompts/` ⬅️ `nodes/` ⬅️ `edges/` ⬅️ `graph.py`.
5. **الخطوة 5: الـ Middleware والـ API Layer (`app/api/`)**
   - `auth_middleware.py` ⬅️ `dependencies.py` ⬅️ `endpoints/` ⬅️ `main.py`.
6. **الخطوة 6: الاختبارات الشاملة (`tests/`) والتوثيق**.
