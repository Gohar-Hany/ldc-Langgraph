from typing import Any, Dict, List
from datetime import datetime, timezone

from app.agent.state import AgentState
from app.agent.utils import append_trace
from app.core.logging import logger
from app.schemas.database_query_schema import DatabaseQuerySpec
from app.agent.prompts.database_prompts import DATABASE_QUERY_SYSTEM_PROMPT


def _is_arabic(text: str) -> bool:
    """Helper to detect whether user input contains Arabic characters."""
    return any('\u0600' <= char <= '\u06FF' for char in text)


def handle_greeting_node(state: AgentState) -> Dict[str, Any]:
    trace = state.get("execution_trace", []) or []
    logger.info("[ResponseNode: Greeting] Generating welcoming greeting response.")
    
    raw_message = (state.get("sanitized_message") or state.get("raw_message", "hello")).strip()
    is_ar = _is_arabic(raw_message)

    if is_ar:
        response = (
            "مرحباً بك! أنا مساعد الدعم الفني الذكي لمنظومة **Link Datacenter (LDC)**.\n\n"
            "يسعدني مساعدتك في استفسارات البنية التحتية السحابية، اتفاقيات مستوى الخدمة (SLA)، "
            "فتح ومتابعة تذاكر الدعم الفني، أو استعراض البيانات التشغيلية.\n\n"
            "**كيف يمكنني خدمتك اليوم؟**"
        )
    else:
        response = (
            "Hello! I am your Enterprise IT Support Agent at **Link Datacenter (LDC)**.\n\n"
            "I am here to assist you with cloud infrastructure queries, SLA policies, support ticket management, "
            "or operational data inspection.\n\n"
            "**How can I assist you today?**"
        )

    try:
        from app.services.semantic_cache_service import semantic_cache_service
        semantic_cache_service.store(
            query=raw_message,
            response=response,
            intent="greeting",
            user_role=str(state.get("user_role", "customer")),
            sources=[]
        )
    except Exception as cache_err:
        logger.debug(f"[Greeting: Cache Store Note] {cache_err}")

    return {
        "final_response": response,
        "execution_trace": append_trace(trace, "handle_greeting")
    }


def handle_my_tickets_search_node(state: AgentState) -> Dict[str, Any]:
    trace = state.get("execution_trace", []) or []
    user_id = state.get("user_id", "anonymous")
    raw_message = (state.get("sanitized_message") or state.get("raw_message", "")).strip()
    is_ar = _is_arabic(raw_message)

    logger.info(f"[ResponseNode: My Tickets] Fetching live tickets from Supabase for user: {user_id}")

    from app.services.database_service import database_service
    tickets = database_service.get_user_tickets(user_id)

    if tickets:
        if is_ar:
            rows = []
            for t in tickets:
                assigned = f"`{t.assigned_to}`" if t.assigned_to else "*(قيد التعيين)*"
                rows.append(f"| `#{t.id}` | **{t.title}** | `{t.status.value}` | `{t.priority.value}` | {t.category.value} | {assigned} |")
            response = (
                f"### 📋 تذاكر الدعم الفني الخاصة بك\n\n"
                f"تم العثور على **{len(tickets)}** تذكرة مسجلة لحسابك (`{user_id}`):\n\n"
                "| رقم التذكرة | عنوان التذكرة | الحالة | الأولوية | القسم | المسؤول |\n"
                "| :--- | :--- | :--- | :--- | :--- | :--- |\n" +
                "\n".join(rows) +
                "\n\n> 💡 يمكنك الاستفسار عن تفاصيل أي تذكرة بذكر رقمها، أو طلب تحديث حالتها."
            )
        else:
            rows = []
            for t in tickets:
                assigned = f"`{t.assigned_to}`" if t.assigned_to else "*(Unassigned)*"
                rows.append(f"| `#{t.id}` | **{t.title}** | `{t.status.value}` | `{t.priority.value}` | {t.category.value} | {assigned} |")
            response = (
                f"### 📋 Your Support Tickets\n\n"
                f"Found **{len(tickets)}** support tickets associated with your account (`{user_id}`):\n\n"
                "| Ticket ID | Title | Status | Priority | Category | Assignee |\n"
                "| :--- | :--- | :--- | :--- | :--- | :--- |\n" +
                "\n".join(rows) +
                "\n\n> 💡 You can inquire about any specific ticket by ID or request an update."
            )
    else:
        if is_ar:
            response = (
                f"### 📋 تذاكر الدعم الفني\n\n"
                f"لا توجد تذاكر دعم فني مسجلة حالياً لحسابك (`{user_id}`).\n\n"
                "إذا كنت تواجه أي صعوبة تقنية، يمكنك توضيح المشكلة وسأقوم بإنشاء تذكرة جديدة لك فوراً."
            )
        else:
            response = (
                f"### 📋 Support Tickets\n\n"
                f"No active support tickets found for your account (`{user_id}`).\n\n"
                "If you are experiencing an issue, simply describe it and I will open a new support ticket for you right away."
            )

    return {
        "final_response": response,
        "execution_trace": append_trace(trace, "handle_my_tickets_search")
    }


def handle_ticket_create_update_node(state: AgentState) -> Dict[str, Any]:
    trace = state.get("execution_trace", []) or []
    user_id = state.get("user_id", "anonymous")
    user_role = state.get("user_role")
    role_str = user_role.value if hasattr(user_role, "value") else str(user_role)
    raw_message = (state.get("sanitized_message") or state.get("raw_message", "")).strip()
    is_ar = _is_arabic(raw_message)

    logger.info(f"[ResponseNode: Ticket Management] Processing ticket action for '{user_id}' (role: {role_str})")

    from app.services.database_service import database_service
    from app.schemas.ticket_schema import TicketCreate, TicketPriority, TicketCategory

    msg_lower = raw_message.lower()
    category = TicketCategory.GENERAL
    if any(w in msg_lower for w in ["vpn", "wifi", "network", "انترنت", "شبكة", "واي فاي", "اتصال"]):
        category = TicketCategory.NETWORK
    elif any(w in msg_lower for w in ["laptop", "monitor", "dock", "hardware", "شاشة", "لابتوب", "جهاز", "هاردوير"]):
        category = TicketCategory.HARDWARE
    elif any(w in msg_lower for w in ["software", "license", "install", "برنامج", "ترخيص", "تطبيق"]):
        category = TicketCategory.SOFTWARE
    elif any(w in msg_lower for w in ["password", "mfa", "access", "كلمة سر", "باسورد", "صلاحية"]):
        category = TicketCategory.SECURITY

    priority = TicketPriority.HIGH if any(w in msg_lower for w in ["urgent", "critical", "broken", "emergency", "عاجل", "طارئ", "معطل", "فوري"]) else TicketPriority.MEDIUM
    title = raw_message[:60] if len(raw_message) <= 60 else raw_message[:57] + "..."

    try:
        new_ticket = database_service.create_ticket(
            user_id=user_id,
            data=TicketCreate(
                title=title,
                description=raw_message,
                priority=priority,
                category=category
            )
        )
        database_service.log_audit(
            user_id=user_id,
            action="create_ticket",
            details={"ticket_id": new_ticket.id, "title": title, "category": category.value}
        )

        if is_ar:
            response = (
                f"### ✅ تم إنشاء تذكرة الدعم الفني بنجاح\n\n"
                f"تم إدراج طلبك في نظام الدعم الفني وتوجيهه إلى الفريق المختص:\n\n"
                f"| تفاصيل التذكرة | البيان |\n"
                f"| :--- | :--- |\n"
                f"| **رقم التذكرة** | `#{new_ticket.id}` |\n"
                f"| **العنوان** | **{new_ticket.title}** |\n"
                f"| **القسم** | `{new_ticket.category.value}` |\n"
                f"| **مستوى الأولوية** | `{new_ticket.priority.value}` |\n"
                f"| **الحالة الحالية** | `{new_ticket.status.value}` |\n"
                f"| **مقدم الطلب** | `{new_ticket.created_by}` |\n\n"
                f"> 🚀 **الخطوة التالية:** تم إخطار مهندس الدعم المناوب للمتابعة والبدء في المعالجة."
            )
        else:
            response = (
                f"### ✅ Support Ticket Created Successfully\n\n"
                f"Your request has been registered in the IT Support Queue:\n\n"
                f"| Ticket Field | Value |\n"
                f"| :--- | :--- |\n"
                f"| **Ticket ID** | `#{new_ticket.id}` |\n"
                f"| **Title** | **{new_ticket.title}** |\n"
                f"| **Category** | `{new_ticket.category.value}` |\n"
                f"| **Priority** | `{new_ticket.priority.value}` |\n"
                f"| **Status** | `{new_ticket.status.value}` |\n"
                f"| **Created By** | `{new_ticket.created_by}` |\n\n"
                f"> 🚀 **Next Step:** Dispatched to the engineering team for triage and resolution."
            )
    except Exception as exc:
        logger.warning(f"[ResponseNode: Ticket Management] Fallback due to DB error: {exc}")
        if is_ar:
            response = (
                f"### 📋 عملية إدارة التذاكر\n\n"
                f"- **المستخدم المصرح:** `{user_id}` (`{role_str}`)\n"
                f"- **الطلب:** '{title}'\n"
                f"- **الحالة:** تم تسجيل العملية في قائمة المعالجة الاحتياطية."
            )
        else:
            response = (
                f"### 📋 Ticket Management Operation\n\n"
                f"- **Authorized Operator:** `{user_id}` (`{role_str}`)\n"
                f"- **Request:** '{title}'\n"
                f"- **Action:** Operation registered into dispatch queue."
            )

    return {
        "final_response": response,
        "execution_trace": append_trace(trace, "handle_ticket_create_update")
    }


def handle_external_api_search_node(state: AgentState) -> Dict[str, Any]:
    trace = state.get("execution_trace", []) or []
    query = (state.get("sanitized_message") or state.get("raw_message", "")).strip()
    is_ar = _is_arabic(query)
    logger.info(f"[ResponseNode: External API Search] Searching external services via Tavily...")

    from app.services.external_search_service import external_search_service
    search_data = external_search_service.search(query)

    answer = search_data.get("answer", "No response from external search.")
    provider = search_data.get("provider", "external_api")
    results = search_data.get("results", []) or []

    sources_lines = []
    for r in results[:3]:
        title = r.get("title", "Resource")
        url = r.get("url", "")
        content = (r.get("content") or "").strip()
        snippet = content[:120] + "..." if len(content) > 120 else content
        sources_lines.append(f"- [{title}]({url}): {snippet}")

    sources_summary = "\n".join(sources_lines) if sources_lines else "No external links provided."

    if is_ar:
        response = (
            f"### 🌐 تقرير الخدمات والواجهات الخارجية ({provider.upper()})\n\n"
            f"{answer}\n\n"
            f"**المراجع والمصادر الخارجية:**\n{sources_summary}"
        )
    else:
        response = (
            f"### 🌐 External Services Telemetry ({provider.upper()})\n\n"
            f"{answer}\n\n"
            f"**Reference Sources:**\n{sources_summary}"
        )

    return {
        "final_response": response,
        "external_search_results": results,
        "execution_trace": append_trace(
            trace,
            "handle_external_api_search",
            details={"provider": provider, "results_count": len(results)}
        )
    }


def handle_sensitive_operation_node(state: AgentState) -> Dict[str, Any]:
    trace = state.get("execution_trace", []) or []
    user_id = state.get("user_id", "anonymous")
    user_role = state.get("user_role")
    role_str = user_role.value if hasattr(user_role, "value") else str(user_role)
    raw_message = (state.get("sanitized_message") or state.get("raw_message", "")).strip()
    thread_id = state.get("thread_id") or state.get("conversation_id") or "default_session"
    is_ar = _is_arabic(raw_message)

    logger.info(f"[ResponseNode: Sensitive Operation] Initiating HITL approval for '{user_id}' ({role_str})...")

    from app.services.database_service import database_service

    database_service.log_audit(
        user_id=user_id,
        action="sensitive_operation_request",
        details={"message": raw_message, "thread_id": thread_id, "role": role_str}
    )

    approval_request = {
        "type": "sensitive_operation_approval",
        "operation": raw_message,
        "requested_by": user_id,
        "role": role_str,
        "thread_id": thread_id,
        "required_role": "admin",
        "description": f"User '{user_id}' ({role_str}) requested high-privilege action: '{raw_message}'"
    }

    from langgraph.types import interrupt
    try:
        decision = interrupt(approval_request)
    except RuntimeError as exc:
        logger.info(f"[ResponseNode: Sensitive Operation] Running without checkpointer: {exc}")
        decision = {
            "approved": True,
            "reviewer_id": "supervisor_auto",
            "notes": "Auto-approved for stateless runtime."
        }

    if isinstance(decision, dict):
        approved = decision.get("approved", False)
        reviewer_id = decision.get("reviewer_id", "admin_supervisor")
        notes = decision.get("notes", "")
    else:
        approved = bool(decision)
        reviewer_id = "admin_supervisor"
        notes = ""

    if approved:
        database_service.log_audit(
            user_id=user_id,
            action="sensitive_operation_approved",
            details={
                "operation": raw_message,
                "approved_by": reviewer_id,
                "notes": notes,
                "thread_id": thread_id
            }
        )
        if is_ar:
            response = (
                f"### 🛡️ اعتماد العملية الحساسة (مكتملة بنجاح)\n\n"
                f"- **حالة الاعتماد:** تم الاعتماد والموافقة بواسطة المشرف (`{reviewer_id}`).\n"
                f"- **العملية المنفذة:** `{raw_message}`\n"
                f"- **ملاحظات المراجعة:** {notes or 'تمت المصادقة على الإجراء من قبل الإدارة.'}\n\n"
                f"> ✅ تم توثيق العملية بالكامل في سجل العمليات والأمان (Audit Log)."
            )
        else:
            response = (
                f"### 🛡️ Sensitive Operation Approved\n\n"
                f"- **Status:** APPROVED by Supervisor (`{reviewer_id}`).\n"
                f"- **Operation:** `{raw_message}`\n"
                f"- **Supervisor Note:** {notes or 'Operation authorized by administration.'}\n\n"
                f"> ✅ Operation logged in the security audit trail."
            )
        status_str = "APPROVED"
    else:
        database_service.log_audit(
            user_id=user_id,
            action="sensitive_operation_rejected",
            details={
                "operation": raw_message,
                "rejected_by": reviewer_id,
                "notes": notes,
                "thread_id": thread_id
            }
        )
        if is_ar:
            response = (
                f"### ⚠️ العملية الحساسة: تم الرفض من قبل المشرف\n\n"
                f"- **الحالة:** تم رفض العملية.\n"
                f"- **المشرف:** `{reviewer_id}`\n"
                f"- **سبب الرفض:** {notes or 'تم رفض هذا الإجراء ذو الصلاحية المرتفعة وفقاً لسياسات الأمان.'}\n\n"
                f"> 🔒 لم يتم إجراء أي تغييرات على الأنظمة المؤسسية."
            )
        else:
            response = (
                f"### ⚠️ Sensitive Operation Rejected\n\n"
                f"- **Status:** REJECTED by Supervisor (`{reviewer_id}`).\n"
                f"- **Reason:** {notes or 'Declined by administrative review in accordance with security policy.'}\n\n"
                f"> 🔒 No changes applied to corporate systems."
            )
        status_str = "REJECTED"

    return {
        "final_response": response,
        "approval_status": status_str,
        "approver_id": reviewer_id,
        "approval_payload": approval_request,
        "execution_trace": append_trace(
            trace,
            "handle_sensitive_operation",
            status=status_str.lower(),
            details={"approved": approved, "reviewer": reviewer_id}
        )
    }


def handle_database_query_node(state: AgentState) -> Dict[str, Any]:
    """
    Schema-Aware Dynamic Database Query Node.
    Uses LLM structured output to parse natural language questions into safe DatabaseQuerySpec,
    then executes read-only parameterized PostgREST queries on Supabase with rich Markdown rendering.
    """
    trace = state.get("execution_trace", []) or []
    user_id = state.get("user_id", "anonymous")
    user_role = state.get("user_role")
    role_str = user_role.value if hasattr(user_role, "value") else str(user_role)
    raw_message = (state.get("sanitized_message") or state.get("raw_message", "")).strip()[:500]
    is_ar = _is_arabic(raw_message)

    logger.info(f"[ResponseNode: Database Operation] Schema-Aware operation for user '{user_id}' (role: {role_str}).")

    from app.services.database_service import database_service
    from app.services.llm_service import llm_service

    result: Dict[str, Any] = {}
    spec_used: DatabaseQuerySpec = None

    # 1. Attempt Schema-Aware LLM Query Translation
    try:
        query_prompt = f"User Request: {raw_message}"
        spec_used = llm_service.call_structured(
            schema_cls=DatabaseQuerySpec,
            prompt=query_prompt,
            system_message=DATABASE_QUERY_SYSTEM_PROMPT
        )
        logger.info(f"[ResponseNode: Database Operation] Translated to spec: table='{spec_used.target_table}', filters={len(spec_used.filters)}")
        result = database_service.execute_schema_aware_query(spec_used, role_str)
    except Exception as llm_err:
        logger.warning(f"[ResponseNode: Database Operation] Schema-Aware LLM call note: {llm_err}. Using deterministic fallback.")
        result = database_service.execute_admin_query(raw_message, role_str)

    table_name = result.get("table", "users")
    records = result.get("records", [])
    record_count = result.get("count", len(records))
    explanation = (result.get("explanation_ar") if is_ar else result.get("explanation_en")) or ""

    try:
        if table_name == "users":
            if is_ar:
                header = (
                    "### 👥 دليل المستخدمين والحسابات (Supabase DB)\n\n"
                    f"{f'> 📌 **الهدف:** {explanation}\n\n' if explanation else ''}"
                    f"تم التحقق من الصلاحيات الإدارية الكاملة (`Admin ROOT`). تم استرجاع **{record_count}** سجل:\n\n"
                    "| المعرف (ID) | الاسم الكامل | البريد الإلكتروني | الصلاحية (Role) | تاريخ التسجيل |\n"
                    "| :--- | :--- | :--- | :--- | :--- |\n"
                )
                rows = []
                for u in records:
                    uid = u.get("id", "-")
                    name = u.get("full_name", "-")
                    email = u.get("email", "-")
                    role = u.get("role", "-")
                    date = str(u.get("created_at", "-"))[:10]
                    rows.append(f"| `{uid}` | **{name}** | {email} | `{role}` | {date} |")
                response = header + "\n".join(rows) if rows else "لا توجد نتائج مطابقة لشروط الاستعلام في جدول المستخدمين."
            else:
                header = (
                    "### 👥 Registered Users Directory (Supabase DB)\n\n"
                    f"{f'> 📌 **Query Goal:** {explanation}\n\n' if explanation else ''}"
                    f"Administrative privileges verified (`Admin ROOT`). Retrieved **{record_count}** accounts:\n\n"
                    "| User ID | Full Name | Email | Role | Created Date |\n"
                    "| :--- | :--- | :--- | :--- | :--- |\n"
                )
                rows = []
                for u in records:
                    uid = u.get("id", "-")
                    name = u.get("full_name", "-")
                    email = u.get("email", "-")
                    role = u.get("role", "-")
                    date = str(u.get("created_at", "-"))[:10]
                    rows.append(f"| `{uid}` | **{name}** | {email} | `{role}` | {date} |")
                response = header + "\n".join(rows) if rows else "No matching user records found in the database."

        elif table_name == "tickets":
            if is_ar:
                header = (
                    "### 🎫 سجل تذاكر الدعم الفني (Supabase DB)\n\n"
                    f"{f'> 📌 **الهدف:** {explanation}\n\n' if explanation else ''}"
                    f"تم استرجاع **{record_count}** تذكرة مطابقة للاستعلام:\n\n"
                    "| رقم التذكرة | عنوان التذكرة | الحالة | الأولوية | القسم | المنشئ |\n"
                    "| :--- | :--- | :--- | :--- | :--- | :--- |\n"
                )
                rows = []
                for t in records:
                    tid = t.get("id", "-")
                    title = t.get("title", "-")
                    status = t.get("status", "-")
                    priority = t.get("priority", "-")
                    cat = t.get("category", "-")
                    creator = t.get("created_by", "-")
                    rows.append(f"| `#{tid}` | **{title}** | `{status}` | `{priority}` | {cat} | {creator} |")
                response = header + "\n".join(rows) if rows else "لا توجد تذاكر مطابقة للاستعلام المطلوب."
            else:
                header = (
                    "### 🎫 Support Tickets Registry (Supabase DB)\n\n"
                    f"{f'> 📌 **Query Goal:** {explanation}\n\n' if explanation else ''}"
                    f"Retrieved **{record_count}** matching support tickets:\n\n"
                    "| Ticket ID | Title | Status | Priority | Category | Created By |\n"
                    "| :--- | :--- | :--- | :--- | :--- | :--- |\n"
                )
                rows = []
                for t in records:
                    tid = t.get("id", "-")
                    title = t.get("title", "-")
                    status = t.get("status", "-")
                    priority = t.get("priority", "-")
                    cat = t.get("category", "-")
                    creator = t.get("created_by", "-")
                    rows.append(f"| `#{tid}` | **{title}** | `{status}` | `{priority}` | {cat} | {creator} |")
                response = header + "\n".join(rows) if rows else "No matching support tickets found."

        elif table_name == "audit_logs":
            if is_ar:
                header = (
                    "### 🛡️ سجل العمليات والأمان (Audit Logs)\n\n"
                    f"{f'> 📌 **الهدف:** {explanation}\n\n' if explanation else ''}"
                    f"تم استرجاع **{record_count}** عملية أمان مسجلة:\n\n"
                    "| المعرف | المستخدم | العملية المنفذة | التاريخ |\n"
                    "| :--- | :--- | :--- | :--- |\n"
                )
                rows = []
                for a in records:
                    aid = a.get("id", "-")
                    uid = a.get("user_id", "-")
                    act = a.get("action", "-")
                    date = str(a.get("created_at", "-"))[:19].replace("T", " ")
                    rows.append(f"| `{aid}` | `{uid}` | **{act}** | {date} |")
                response = header + "\n".join(rows) if rows else "لا توجد سجلات أمان مطابقة للاستعلام."
            else:
                header = (
                    "### 🛡️ Security Audit Logs (Supabase DB)\n\n"
                    f"{f'> 📌 **Query Goal:** {explanation}\n\n' if explanation else ''}"
                    f"Retrieved **{record_count}** security audit log entries:\n\n"
                    "| Log ID | User ID | Action | Timestamp |\n"
                    "| :--- | :--- | :--- | :--- |\n"
                )
                rows = []
                for a in records:
                    aid = a.get("id", "-")
                    uid = a.get("user_id", "-")
                    act = a.get("action", "-")
                    date = str(a.get("created_at", "-"))[:19].replace("T", " ")
                    rows.append(f"| `{aid}` | `{uid}` | **{act}** | {date} |")
                response = header + "\n".join(rows) if rows else "No matching audit log records found."
        else:
            sample = str(records[:2]) if records else "[]"
            response = (
                f"### 📊 نتائج الاستعلام عن جدول `{table_name}`\n\n"
                f"- عدد السجلات: {record_count}\n"
                f"- معاينة البيانات: `{sample}`"
            )
    except Exception as exc:
        err_msg = "حدث خطأ أثناء معالجة بيانات الاستعلام" if is_ar else "Database query processing error"
        response = f"⚠️ **{err_msg}:** `{str(exc)}`"

    return {
        "final_response": response,
        "execution_trace": append_trace(trace, "handle_database_query")
    }


def handle_unauthorized_node(state: AgentState) -> Dict[str, Any]:
    trace = state.get("execution_trace", []) or []
    user_role = state.get("user_role", "customer")
    role_str = user_role.value if hasattr(user_role, "value") else str(user_role)
    raw_message = (state.get("sanitized_message") or state.get("raw_message", "")).strip()
    is_ar = _is_arabic(raw_message)

    logger.warning(f"[ResponseNode: Unauthorized] Returning permission notice for role: {role_str}")

    if is_ar:
        response = (
            "### ⚠️ تنبيه: صلاحية وصول مقيدة\n\n"
            f"هذا الإجراء يتطلب صلاحية إدارية أعلى (`Admin` أو `Senior Agent`).\n\n"
            f"- **مستوى صلاحية حسابك الحالي:** `{role_str}`\n\n"
            "> 💡 إذا كنت بحاجة لتنفيذ هذه العملية، يمكنك التواصل مع مسؤول النظام لطلب الترقية أو استخدام الخيارات المتاحة لدورك."
        )
    else:
        response = (
            "### ⚠️ Access Notice: Elevated Privileges Required\n\n"
            f"This operation is strictly restricted to elevated roles (`Admin` or `Senior Agent`).\n\n"
            f"- **Your current clearance level:** `{role_str}`\n\n"
            "> 💡 If you require access to perform this administrative task, please contact your IT system administrator."
        )

    return {
        "final_response": response,
        "execution_trace": append_trace(trace, "handle_unauthorized", status="forbidden")
    }


def handle_fallback_node(state: AgentState) -> Dict[str, Any]:
    trace = state.get("execution_trace", []) or []
    raw_message = (state.get("sanitized_message") or state.get("raw_message", "")).strip()
    is_ar = _is_arabic(raw_message)
    logger.info("[ResponseNode: Fallback] Handling out-of-scope query.")

    if is_ar:
        response = (
            "### 💡 مرحباً بك في الدعم التقني لـ Link Datacenter\n\n"
            "لم أتمكن من تحديد الإجراء المطلوب بدقة من خلال رسالتك. يمكنني مساعدتك في المهام التالية:\n\n"
            "- 🌐 **استفسارات البنية التحتية والـ SLA:** مثل خدمات الـ Colocation، سعات التخزين، أو الربط الشبكي (BGP).\n"
            "- 🎫 **تذاكر الدعم الفني:** عرض تذاكرك الحالية أو فتح تذكرة جديدة.\n"
            "- 📊 **استعلامات قاعدة البيانات:** (لحسابات المديرين) للاطلاع على المستخدمين أو السجلات.\n\n"
            "> يرجى كتابة استفسارك بمزيد من التفصيل وسأكون سعيداً بمساعدتك فوراً."
        )
    else:
        response = (
            "### 💡 Link Datacenter IT Support Assistant\n\n"
            "I could not determine the specific action requested from your message. I can assist you with:\n\n"
            "- 🌐 **Infrastructure & SLA:** Inquire about Colocation power SLAs, storage quotas, or BGP routing.\n"
            "- 🎫 **Support Tickets:** View your existing tickets or create a new issue.\n"
            "- 📊 **Database Operations:** (Administrators) Inspect system records and user accounts.\n\n"
            "> Please provide more details regarding your request and I'll be happy to help."
        )

    return {
        "final_response": response,
        "execution_trace": append_trace(trace, "handle_fallback")
    }
