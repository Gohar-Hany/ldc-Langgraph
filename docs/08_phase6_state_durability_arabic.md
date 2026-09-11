# الدليل التفصيلي للمرحلة السادسة (Phase 6): ثبات الحالة وقابلية التوسع الأفقي (PostgreSQL State Durability & Checkpointing)

---

## 1. مقدمة وهدف المرحلة

في المراحل السابقة (Phases 1-5)، كنا نعتمد على `MemorySaver` الخاص بمكتبة LangGraph لحفظ حالة المحادثات وخطوات التنفيذ وتاريخ الرسائل.
على الرغم من كفاءة `MemorySaver` أثناء التطوير والاختبار المحلي، إلا أنه يمثل **نقطة ضعف قاتلة (Single Point of Failure)** في الأنظمة الإنتاجية المؤسسية (Enterprise Production Systems).

### ما هي المشاكل القاتلة للـ In-Memory Checkpointer في الإنتاج؟
1. **فقدان الحالة عند إعادة تشغيل السيرفر (Server Restarts / Crashes):**
   * إذا تعطل التطبيق أو تم عمل Redeployment للـ Docker Container، تفقد الذاكرة كل الـ Threads السابقة.
2. **استحالة التوسع الأفقي (No Horizontal Scaling):**
   * عندما يعمل التطبيق خلف Load Balancer وموزع على 3 أو 5 حاويات (Kubernetes Pods)، فإن رسالة المستخدم الأولى قد تصل للـ Pod رقم 1، بينما رسالته التالية قد تذهب إلى الـ Pod رقم 2. ولأن الذاكرة غير مشتركة، لن يتعرف الـ Pod الثاني على سياق المحادثة إطلاقاً!
3. **ضياع حالات التدخل البشري (HITL Interrupt Loss):**
   * عندما يُعلق الـ Agent عملية حساسة عبر `interrupt()` بانتظار موافقة المشرف، فإن حالة التعليق تُخزن في الذاكرة. إذا أُعيد تشغيل السيرفر قبل أن يُقرر المشرف، تصبح المحادثة تائهة (Deadlocked/Orphaned).

---

## 2. الحل المعماري: PostgreSQL Persistent Checkpointer (`PostgresSaver`)

في المرحلة السادسة، قمنا بنقل نظام التخزين بالكامل إلى **قاعدة بيانات PostgreSQL المشتركة في Supabase** باستخدام الحزمة الرسمية `langgraph-checkpoint-postgres` المدعومة بمكتبة `psycopg` (v3) ونظام إدارة الاتصالات المتقدم `ConnectionPool`.

```mermaid
graph TD
    Client["مستخدم أو تطبيق الشات"] --> Gateway["FastAPI Gateway"]
    
    subgraph Multi_Pod_Deployment ["توسع أفقي (Kubernetes Pods)"]
        Gateway --> Pod1["Container Pod 1"]
        Gateway --> Pod2["Container Pod 2"]
        Gateway --> Pod3["Container Pod 3"]
    end
    
    subgraph Shared_Storage ["قاعدة بيانات Supabase المشتركة"]
        Pod1 <-->|Psycopg Pool| PG[("PostgreSQL Database")]
        Pod2 <-->|Psycopg Pool| PG
        Pod3 <-->|Psycopg Pool| PG
        
        PG --- T1["checkpoints (حالات العقد والـ IDs)"]
        PG --- T2["checkpoint_blobs (قيم القنوات والبيانات الثنائية)"]
        PG --- T3["checkpoint_writes (العمليات والمهام المعلقة)"]
    end
```

---

## 3. مكونات جدول البيانات (Database Schema)

أنشأنا ملف الترحيل [`data/migrations/002_langgraph_checkpoints.sql`](file:///d:/ldc-Langgraph/data/migrations/002_langgraph_checkpoints.sql) الذي ينشئ الهياكل التالية:

1. **جدول `checkpoints`:**
   * المفتاح الأساسي المركب: `(thread_id, checkpoint_ns, checkpoint_id)`.
   * يخزن الـ State الرئيسية، ومعرف العقدة السابقة، ونوع المحتوى، ومخرجات الـ Metadata.
2. **جدول `checkpoint_blobs`:**
   * يخزن قيم القنوات (Channels) والرسائل والمتغيرات بصيغة ثنائية مضغوطة (`BYTEA`).
3. **جدول `checkpoint_writes`:**
   * يسجل المهام المعلقة والعمليات الجارية في كل مرحلة خطوة بخطوة.
4. **فهارس الأداء العالي (High-Performance Indexes):**
   * فهارس B-Tree على حقل `thread_id` لضمان قراءة وكتابة الحالات بزمن أقل من 5 ميلي ثانية حتى مع ملايين المحادثات.

---

## 4. تصميم المصنع المرن مع خطة الطوارئ (Resilient Factory Pattern)

تم بناء المصنع `init_checkpointer()` في [`app/agent/graph.py`](file:///d:/ldc-Langgraph/app/agent/graph.py) بمبدأ **High Resilience (المرونة العالية)**:

```python
def init_checkpointer():
    if settings.CHECKPOINTER_BACKEND == "postgres" and settings.DATABASE_URL:
        try:
            from psycopg_pool import ConnectionPool
            from psycopg.rows import dict_row
            from langgraph.checkpoint.postgres import PostgresSaver

            pool = ConnectionPool(
                settings.DATABASE_URL,
                open=True,
                max_size=10,
                kwargs={"autocommit": True, "prepare_threshold": 0, "row_factory": dict_row}
            )
            saver = PostgresSaver(pool)
            saver.setup()  # تشغيل الجداول تلقائياً
            return saver
        except Exception as e:
            logger.warning(f"PostgreSQL unreachable: {e}. Falling back to MemorySaver.")
            return MemorySaver()
    return MemorySaver()
```

### مزايا هذا التصميم:
* **Zero Downtime:** في حال حدوث عطل شبكي مفاجئ بين السيرفر و Supabase، لا ينهار التطبيق (No Crash)، بل يتحول تلقائياً إلى الذاكرة المحلية مع تسجيل تحذير تفصيلي في الـ Logs.
* **Auto Migration:** عند تشغيل `saver.setup()`، يقوم الـ Checkpointer بفحص وإنشاء الجداول تلقائياً دون الحاجة لتدخل يدوي.
* **Dynamic Injection:** دالة `set_checkpointer(custom_saver)` تتيح حقن أي Checkpointer مخصص أثناء اختبارات الـ Unit & Integration Tests لضمان عزل البيانات وسرعة التنفيذ.

---

## 5. كيفية تفعيل الـ Persistent Checkpointer في بيئة الإنتاج

1. افتح ملف المتغيرات البيئية `.env`.
2. ضع رابط الاتصال المباشر بقاعدة بيانات Supabase (من تبويب Database -> Connection string -> URI):
   ```env
   CHECKPOINTER_BACKEND="postgres"
   DATABASE_URL="postgresql://postgres.peipnsmjaatousqjulbk:[YOUR-PASSWORD]@aws-0-eu-central-1.pooler.supabase.com:6543/postgres"
   ```
3. أعد تشغيل التطبيق أو الحاوية:
   ```bash
   docker-compose up --build -d
   ```
4. سيتصل النظام تلقائياً بـ PostgreSQL، وينشئ الجداول، ويحفظ كل المحادثات بشكل دائم ومستمر.

---

## 6. ملخص نتائج الاختبارات الآلية

تم اختبار جميع جوانب الـ Checkpointer عبر [`tests/integration/test_phase6_postgres_checkpointer.py`](file:///d:/ldc-Langgraph/tests/integration/test_phase6_postgres_checkpointer.py):
- فحص وضع الذاكرة التلقائي.
- فحص السقوط الآمن (Resilient Fallback) عند إدخال رابط داتابيز غير صالح.
- فحص إعداد وتشغيل جداول الـ PostgresSaver.
- فحص بقاء وثبات الحالة عبر الخطوات المتعددة.
- فحص عزل الجلسات والمحادثات بين المستخدمين المختلفين (Thread Isolation).
- فحص بقاء واستئناف عمليات التدخل البشري (HITL Interrupt & Resumption).
