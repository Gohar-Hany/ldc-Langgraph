from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from supabase import create_client, Client

from app.core.config import settings
from app.core.logging import logger
from app.schemas.auth_schema import UserRole
from app.schemas.ticket_schema import (
    TicketCreate,
    TicketUpdate,
    TicketResponse,
    TicketFilter,
    TicketStatus,
    TicketPriority,
    TicketCategory
)
from app.schemas.database_query_schema import DatabaseQuerySpec


class DatabaseService:
    """Enterprise Relational Database Service using Supabase (PostgreSQL)."""

    def __init__(self):
        self.url = settings.SUPABASE_URL
        self.key = settings.SUPABASE_KEY
        self.client: Optional[Client] = None
        self._init_client()

    def _init_client(self):
        if self.url and self.key:
            try:
                self.client = create_client(self.url, self.key)
                logger.info(f"[DatabaseService] Connected to Supabase project at: {self.url[:32]}...")
            except Exception as e:
                logger.error(f"[DatabaseService: Error] Failed to initialize Supabase client: {e}")
                self.client = None
        else:
            logger.warning("[DatabaseService] Supabase URL or Key not set. Running in degraded mode.")

    def ensure_seed_users(self):
        """Ensures test RBAC users exist in Supabase users table."""
        if not self.client:
            return
        default_users = [
            {"id": "user_01", "email": "customer1@enterprise.local", "full_name": "Alice Customer", "role": "customer"},
            {"id": "agent_01", "email": "support1@enterprise.local", "full_name": "Bob Support", "role": "support_agent"},
            {"id": "senior_01", "email": "senior1@enterprise.local", "full_name": "Charlie Senior", "role": "senior_agent"},
            {"id": "admin_01", "email": "admin1@enterprise.local", "full_name": "David Admin", "role": "admin"}
        ]
        try:
            for user in default_users:
                self.client.table("users").upsert(user).execute()
            logger.info("[DatabaseService] Seed users verified in Supabase.")
        except Exception as e:
            logger.warning(f"[DatabaseService] Could not seed users (tables may need creation first): {e}")

    def get_user_tickets(self, user_id: str) -> List[TicketResponse]:
        """Fetch tickets created by or assigned to a specific user (Customer isolation)."""
        if not self.client:
            logger.warning("[DatabaseService] Supabase offline; returning empty ticket list.")
            return []

        try:
            res = self.client.table("tickets").select("*").eq("created_by", user_id).order("created_at", desc=True).execute()
            tickets = []
            for row in res.data or []:
                tickets.append(TicketResponse(**row))
            return tickets
        except Exception as e:
            logger.error(f"[DatabaseService: Error] get_user_tickets for '{user_id}': {e}")
            return []

    def get_ticket_by_id(self, ticket_id: int) -> Optional[TicketResponse]:
        """Fetch single ticket by primary key."""
        if not self.client:
            return None
        try:
            res = self.client.table("tickets").select("*").eq("id", ticket_id).limit(1).execute()
            if res.data and len(res.data) > 0:
                return TicketResponse(**res.data[0])
            return None
        except Exception as e:
            logger.error(f"[DatabaseService: Error] get_ticket_by_id {ticket_id}: {e}")
            return None

    def list_all_tickets(
        self,
        filters: Optional[TicketFilter] = None,
        actor_role: str = "customer",
        actor_id: str = "anonymous"
    ) -> List[TicketResponse]:
        """
        List tickets with RBAC enforcement:
        - Customer: only sees their own tickets.
        - Support Agent, Senior Agent, Admin: see all tickets matching filters.
        """
        if not self.client:
            return []

        try:
            query = self.client.table("tickets").select("*")

            # RBAC restriction
            if actor_role == UserRole.CUSTOMER.value:
                query = query.eq("created_by", actor_id)
            elif filters and filters.created_by:
                query = query.eq("created_by", filters.created_by)

            if filters:
                if filters.status:
                    query = query.eq("status", filters.status.value)
                if filters.priority:
                    query = query.eq("priority", filters.priority.value)
                if filters.category:
                    query = query.eq("category", filters.category.value)
                query = query.range(filters.offset, filters.offset + filters.limit - 1)

            query = query.order("created_at", desc=True)
            res = query.execute()

            return [TicketResponse(**row) for row in res.data or []]
        except Exception as e:
            logger.error(f"[DatabaseService: Error] list_all_tickets: {e}")
            return []

    def create_ticket(self, user_id: str, data: TicketCreate) -> TicketResponse:
        """Create a new support ticket in Supabase."""
        if not self.client:
            raise RuntimeError("Database connection unavailable.")

        payload = {
            "title": data.title,
            "description": data.description,
            "priority": data.priority.value,
            "category": data.category.value,
            "status": TicketStatus.OPEN.value,
            "created_by": user_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }

        try:
            res = self.client.table("tickets").insert(payload).execute()
            if not res.data:
                raise RuntimeError("Failed to insert ticket into database.")
            created = TicketResponse(**res.data[0])
            logger.info(f"[DatabaseService] Ticket #{created.id} created successfully by user '{user_id}'.")
            return created
        except Exception as e:
            logger.error(f"[DatabaseService: Error] create_ticket: {e}")
            raise

    def update_ticket(self, ticket_id: int, data: TicketUpdate, actor_role: str) -> Optional[TicketResponse]:
        """Update ticket lifecycle fields (requires Support Agent, Senior Agent, or Admin)."""
        if not self.client:
            raise RuntimeError("Database connection unavailable.")

        updates: Dict[str, Any] = {
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        if data.status is not None:
            updates["status"] = data.status.value
        if data.priority is not None:
            updates["priority"] = data.priority.value
        if data.category is not None:
            updates["category"] = data.category.value
        if data.assigned_to is not None:
            updates["assigned_to"] = data.assigned_to
        if data.resolution_notes is not None:
            updates["resolution_notes"] = data.resolution_notes

        try:
            res = self.client.table("tickets").update(updates).eq("id", ticket_id).execute()
            if res.data and len(res.data) > 0:
                updated = TicketResponse(**res.data[0])
                logger.info(f"[DatabaseService] Ticket #{ticket_id} updated by role '{actor_role}'.")
                return updated
            return None
        except Exception as e:
            logger.error(f"[DatabaseService: Error] update_ticket #{ticket_id}: {e}")
            raise

    def log_audit(self, user_id: str, action: str, details: dict, ip_address: Optional[str] = None):
        """Record an immutable audit log entry."""
        if not self.client:
            return

        payload = {
            "user_id": user_id,
            "action": action,
            "details": details or {},
            "ip_address": ip_address,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        try:
            self.client.table("audit_logs").insert(payload).execute()
            logger.info(f"[AuditLog] Logged action '{action}' by user '{user_id}'.")
        except Exception as e:
            logger.warning(f"[AuditLog: Warning] Could not record audit log: {e}")

    def execute_schema_aware_query(self, spec: "DatabaseQuerySpec", actor_role: str) -> Dict[str, Any]:
        """
        Execute a dynamically generated, read-only query specification against Supabase.
        Enforces RBAC (Admin only) and strict column whitelisting against SQL/NoSQL injection.
        """
        if actor_role != UserRole.ADMIN.value:
            raise PermissionError("Direct database queries are strictly restricted to Admin role.")

        if not self.client:
            return {
                "table": spec.target_table,
                "records": [],
                "count": 0,
                "explanation_ar": spec.query_explanation_ar,
                "explanation_en": spec.query_explanation_en
            }

        table_name = spec.target_table
        # Column Whitelists per table
        whitelists = {
            "users": {"id", "full_name", "email", "role", "created_at"},
            "tickets": {"id", "title", "description", "priority", "category", "status", "created_by", "assigned_to", "created_at", "updated_at"},
            "audit_logs": {"id", "user_id", "action", "details", "ip_address", "created_at"}
        }
        allowed_cols = whitelists.get(table_name, set())

        # Determine select columns
        if spec.columns:
            valid_cols = [c for c in spec.columns if c.lower() in allowed_cols]
            select_str = ",".join(valid_cols) if valid_cols else "*"
        else:
            select_str = "*"

        try:
            q = self.client.table(table_name).select(select_str)

            # Apply dynamic filters safely
            for flt in spec.filters:
                col = flt.column.strip().lower()
                if col not in allowed_cols:
                    continue

                op = flt.operator.lower()
                val = flt.value

                if op == "eq":
                    q = q.eq(col, val)
                elif op == "neq":
                    q = q.neq(col, val)
                elif op == "like":
                    q = q.like(col, f"%{val}%")
                elif op == "ilike":
                    q = q.ilike(col, f"%{val}%")
                elif op == "gt":
                    q = q.gt(col, val)
                elif op == "lt":
                    q = q.lt(col, val)
                elif op == "gte":
                    q = q.gte(col, val)
                elif op == "lte":
                    q = q.lte(col, val)

            # Apply order
            order_col = (spec.order_by or "created_at").lower()
            if order_col in allowed_cols:
                is_desc = (spec.order_direction == "desc")
                q = q.order(order_col, desc=is_desc)

            # Apply safe limit
            limit_val = max(1, min(spec.limit, 50))
            q = q.limit(limit_val)

            res = q.execute()
            records = res.data or []
            return {
                "table": table_name,
                "records": records,
                "count": len(records),
                "explanation_ar": spec.query_explanation_ar,
                "explanation_en": spec.query_explanation_en
            }
        except Exception as e:
            logger.error(f"[DatabaseService: Error] execute_schema_aware_query: {e}")
            return {
                "table": table_name,
                "records": [],
                "count": 0,
                "error": str(e),
                "explanation_ar": spec.query_explanation_ar,
                "explanation_en": spec.query_explanation_en
            }

    def execute_admin_query(self, query: str, actor_role: str) -> Dict[str, Any]:
        """
        Execute read-only queries or table inspection for Admin role only.
        Fallback keyword-based query inspection.
        """
        if actor_role != UserRole.ADMIN.value:
            raise PermissionError("Direct database queries are strictly restricted to Admin role.")

        if not self.client:
            return {"table": "unknown", "records": [], "count": 0}

        clean_q = query.lower().strip()
        user_keywords = ["user", "users", "يوزر", "يوزرز", "مستخدم", "مستخدمين", "عملاء", "أعضاء", "حسابات", "ناس"]
        ticket_keywords = ["ticket", "tickets", "تذاكر", "تذكرة", "مشاكل", "طلبات"]
        audit_keywords = ["audit", "log", "logs", "سجل", "سجلات", "عمليات"]

        try:
            if any(w in clean_q for w in user_keywords):
                res = self.client.table("users").select("id, full_name, email, role, created_at").limit(20).execute()
                records = res.data or []
                return {"table": "users", "records": records, "count": len(records)}
            elif any(w in clean_q for w in ticket_keywords):
                res = self.client.table("tickets").select("id, title, status, priority, category, created_by, created_at").limit(20).execute()
                records = res.data or []
                return {"table": "tickets", "records": records, "count": len(records)}
            elif any(w in clean_q for w in audit_keywords):
                res = self.client.table("audit_logs").select("*").order("created_at", desc=True).limit(20).execute()
                records = res.data or []
                return {"table": "audit_logs", "records": records, "count": len(records)}
            else:
                res = self.client.table("users").select("id, full_name, email, role, created_at").limit(10).execute()
                records = res.data or []
                return {"table": "users", "records": records, "count": len(records)}
        except Exception as e:
            logger.error(f"[DatabaseService: Error] execute_admin_query: {e}")
            return {"table": "error", "records": [], "count": 0, "error": str(e)}


database_service = DatabaseService()

