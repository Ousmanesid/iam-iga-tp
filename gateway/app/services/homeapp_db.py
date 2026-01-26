"""
Service pour interagir avec la base de données Home App (PostgreSQL)
"""

import asyncpg
from typing import Optional, List, Dict, Any
from datetime import datetime
import structlog
from uuid import UUID

from ..config import settings

logger = structlog.get_logger()


class HomeAppDBService:
    """Service pour les opérations CRUD sur Home App PostgreSQL"""
    
    def __init__(self):
        self.pool: Optional[asyncpg.Pool] = None
    
    async def connect(self):
        """Établir la connexion à la base de données"""
        if self.pool is None:
            self.pool = await asyncpg.create_pool(
                host=settings.homeapp_db_host,
                port=settings.homeapp_db_port,
                database=settings.homeapp_db_name,
                user=settings.homeapp_db_user,
                password=settings.homeapp_db_password,
                min_size=2,
                max_size=10
            )
            logger.info("Connected to HomeApp database")
    
    async def disconnect(self):
        """Fermer la connexion"""
        if self.pool:
            await self.pool.close()
            self.pool = None
            logger.info("Disconnected from HomeApp database")
    
    async def ensure_connected(self):
        """S'assurer que la connexion est établie"""
        if self.pool is None:
            await self.connect()
    
    # === Opérations Utilisateurs ===
    
    async def create_user(
        self,
        login: str,
        email: str,
        password_hash: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        department: Optional[str] = None,
        job_title: Optional[str] = None,
        employee_number: Optional[str] = None,
        is_active: bool = True,
        midpoint_oid: Optional[str] = None,
        attributes: Dict[str, Any] = None
    ) -> Optional[UUID]:
        """Créer ou mettre à jour un utilisateur (upsert)"""
        await self.ensure_connected()
        
        import json as json_lib
        
        try:
            # Convertir le dict en JSON string pour PostgreSQL
            attributes_json = json_lib.dumps(attributes) if attributes else '{}'
            
            result = await self.pool.fetchval(
                """
                SELECT upsert_user($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                """,
                login, email, password_hash, first_name, last_name,
                department, job_title, employee_number, is_active,
                midpoint_oid, attributes_json
            )
            logger.info("User created/updated", login=login, user_id=str(result))
            return result
        except Exception as e:
            logger.error("Failed to create user", login=login, error=str(e))
            raise
    
    async def get_user_by_login(self, login: str) -> Optional[Dict[str, Any]]:
        """Récupérer un utilisateur par son login"""
        await self.ensure_connected()
        
        row = await self.pool.fetchrow(
            """
            SELECT * FROM v_users_with_roles WHERE login = $1
            """,
            login
        )
        
        if row:
            return dict(row)
        return None
    
    async def get_user_by_id(self, user_id: UUID) -> Optional[Dict[str, Any]]:
        """Récupérer un utilisateur par son ID"""
        await self.ensure_connected()
        
        row = await self.pool.fetchrow(
            """
            SELECT * FROM v_users_with_roles WHERE id = $1
            """,
            user_id
        )
        
        if row:
            return dict(row)
        return None
    
    async def search_users(
        self,
        department: Optional[str] = None,
        job_title: Optional[str] = None,
        is_active: Optional[bool] = None,
        search_term: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Rechercher des utilisateurs avec filtres"""
        await self.ensure_connected()
        
        query = "SELECT * FROM v_users_with_roles WHERE 1=1"
        params = []
        param_idx = 1
        
        if department:
            query += f" AND department ILIKE ${param_idx}"
            params.append(f"%{department}%")
            param_idx += 1
        
        if job_title:
            query += f" AND job_title ILIKE ${param_idx}"
            params.append(f"%{job_title}%")
            param_idx += 1
        
        if is_active is not None:
            query += f" AND is_active = ${param_idx}"
            params.append(is_active)
            param_idx += 1
        
        if search_term:
            query += f" AND (login ILIKE ${param_idx} OR full_name ILIKE ${param_idx} OR email ILIKE ${param_idx})"
            params.append(f"%{search_term}%")
            param_idx += 1
        
        query += f" ORDER BY login LIMIT ${param_idx}"
        params.append(limit)
        
        rows = await self.pool.fetch(query, *params)
        return [dict(row) for row in rows]
    
    async def update_user(self, login: str, updates: Dict[str, Any]) -> bool:
        """Mettre à jour un utilisateur"""
        await self.ensure_connected()
        
        if not updates:
            return False
        
        # Construire la requête de mise à jour dynamique
        set_clauses = []
        params = []
        param_idx = 1
        
        for key, value in updates.items():
            if key in ['email', 'first_name', 'last_name', 'department', 
                       'job_title', 'employee_number', 'is_active', 'is_locked',
                       'password_hash', 'midpoint_oid']:
                set_clauses.append(f"{key} = ${param_idx}")
                params.append(value)
                param_idx += 1
        
        if not set_clauses:
            return False
        
        params.append(login)
        query = f"UPDATE users SET {', '.join(set_clauses)} WHERE login = ${param_idx}"
        
        try:
            result = await self.pool.execute(query, *params)
            updated = result.split()[-1] != '0'
            logger.info("User updated", login=login, updated=updated)
            return updated
        except Exception as e:
            logger.error("Failed to update user", login=login, error=str(e))
            raise
    
    async def disable_user(self, login: str) -> bool:
        """Désactiver un utilisateur"""
        await self.ensure_connected()
        
        result = await self.pool.fetchval(
            "SELECT disable_user($1)", login
        )
        logger.info("User disabled", login=login, success=result)
        return result
    
    async def enable_user(self, login: str) -> bool:
        """Activer un utilisateur"""
        await self.ensure_connected()
        
        result = await self.pool.fetchval(
            "SELECT enable_user($1)", login
        )
        logger.info("User enabled", login=login, success=result)
        return result
    
    async def delete_user(self, login: str) -> bool:
        """Supprimer un utilisateur"""
        await self.ensure_connected()
        
        result = await self.pool.fetchval(
            "SELECT delete_user($1)", login
        )
        logger.info("User deleted", login=login, success=result)
        return result
    
    # === Opérations Rôles ===
    
    async def assign_role(
        self,
        user_login: str,
        role_code: str,
        assigned_by: str = "gateway",
        source: str = "manual",
        valid_until: Optional[datetime] = None
    ) -> bool:
        """Assigner un rôle à un utilisateur"""
        await self.ensure_connected()
        
        result = await self.pool.fetchval(
            "SELECT assign_role_to_user($1, $2, $3, $4, $5)",
            user_login, role_code, assigned_by, source, valid_until
        )
        logger.info("Role assigned", user=user_login, role=role_code, success=result)
        return result
    
    async def revoke_role(self, user_login: str, role_code: str) -> bool:
        """Révoquer un rôle d'un utilisateur"""
        await self.ensure_connected()
        
        result = await self.pool.fetchval(
            "SELECT revoke_role_from_user($1, $2)",
            user_login, role_code
        )
        logger.info("Role revoked", user=user_login, role=role_code, success=result)
        return result
    
    async def get_user_roles(self, user_login: str) -> List[str]:
        """Obtenir les rôles d'un utilisateur"""
        await self.ensure_connected()
        
        rows = await self.pool.fetch(
            """
            SELECT r.code FROM roles r
            JOIN user_roles ur ON r.id = ur.role_id
            JOIN users u ON ur.user_id = u.id
            WHERE u.login = $1
            AND (ur.valid_until IS NULL OR ur.valid_until > NOW())
            """,
            user_login
        )
        return [row['code'] for row in rows]
    
    # === Opérations Permissions ===
    
    async def assign_permission(
        self,
        user_login: str,
        permission_code: str,
        assigned_by: str = "gateway",
        reason: Optional[str] = None,
        valid_until: Optional[datetime] = None
    ) -> bool:
        """Assigner une permission directe à un utilisateur"""
        await self.ensure_connected()
        
        result = await self.pool.fetchval(
            "SELECT assign_permission_to_user($1, $2, $3, $4, $5)",
            user_login, permission_code, assigned_by, reason, valid_until
        )
        logger.info("Permission assigned", user=user_login, permission=permission_code, success=result)
        return result
    
    async def revoke_permission(self, user_login: str, permission_code: str) -> bool:
        """Révoquer une permission directe"""
        await self.ensure_connected()
        
        result = await self.pool.fetchval(
            "SELECT revoke_permission_from_user($1, $2)",
            user_login, permission_code
        )
        logger.info("Permission revoked", user=user_login, permission=permission_code, success=result)
        return result
    
    async def get_user_permissions(self, user_login: str) -> List[Dict[str, str]]:
        """Obtenir toutes les permissions effectives d'un utilisateur"""
        await self.ensure_connected()
        
        rows = await self.pool.fetch(
            "SELECT * FROM get_user_effective_permissions($1)",
            user_login
        )
        return [dict(row) for row in rows]
    
    async def user_has_permission(self, user_login: str, permission_code: str) -> bool:
        """Vérifier si un utilisateur a une permission"""
        await self.ensure_connected()
        
        result = await self.pool.fetchval(
            "SELECT user_has_permission($1, $2)",
            user_login, permission_code
        )
        return result
    
    # === Opérations sur les demandes de provisioning ===
    
    async def create_provisioning_request(
        self,
        request_type: str,
        target_user_login: str,
        payload: Dict[str, Any],
        requester_name: Optional[str] = None,
        justification: Optional[str] = None,
        n8n_workflow_id: Optional[str] = None
    ) -> UUID:
        """Créer une demande de provisioning"""
        await self.ensure_connected()
        
        import json
        
        result = await self.pool.fetchval(
            """
            INSERT INTO provisioning_requests 
            (request_type, target_user_login, payload, requester_name, justification, n8n_workflow_id)
            VALUES ($1, $2, $3, $4, $5, $6)
            RETURNING id
            """,
            request_type, target_user_login, json.dumps(payload),
            requester_name, justification, n8n_workflow_id
        )
        logger.info("Provisioning request created", request_id=str(result), type=request_type)
        return result
    
    async def update_provisioning_request_status(
        self,
        request_id: UUID,
        status: str,
        completed_at: Optional[datetime] = None
    ) -> bool:
        """Mettre à jour le statut d'une demande"""
        await self.ensure_connected()
        
        if completed_at:
            result = await self.pool.execute(
                """
                UPDATE provisioning_requests 
                SET status = $2, completed_at = $3
                WHERE id = $1
                """,
                request_id, status, completed_at
            )
        else:
            result = await self.pool.execute(
                """
                UPDATE provisioning_requests SET status = $2 WHERE id = $1
                """,
                request_id, status
            )
        
        return result.split()[-1] != '0'
    
    async def get_pending_requests(self) -> List[Dict[str, Any]]:
        """Obtenir les demandes en attente"""
        await self.ensure_connected()
        
        rows = await self.pool.fetch(
            "SELECT * FROM v_pending_requests ORDER BY created_at"
        )
        return [dict(row) for row in rows]

    async def get_provisioning_request(self, request_id: UUID) -> Optional[Dict[str, Any]]:
        """Obtenir une demande de provisioning avec ses étapes"""
        await self.ensure_connected()

        row = await self.pool.fetchrow(
            "SELECT * FROM provisioning_requests WHERE id = $1",
            request_id
        )
        if not row:
            return None

        steps = await self.pool.fetch(
            """
            SELECT step_order, approver_type, approver_email, status, decision_at, comment
            FROM approval_steps
            WHERE request_id = $1
            ORDER BY step_order
            """,
            request_id
        )

        data = dict(row)
        payload = data.get("payload") or {}
        data["payload"] = dict(payload) if isinstance(payload, dict) else payload
        data["approval_steps"] = [dict(step) for step in steps]
        return data
    
    # === Audit ===
    
    async def log_audit_event(
        self,
        event_type: str,
        action: str,
        actor_name: Optional[str] = None,
        target_type: Optional[str] = None,
        target_id: Optional[UUID] = None,
        target_name: Optional[str] = None,
        old_value: Optional[Dict] = None,
        new_value: Optional[Dict] = None,
        source: str = "gateway"
    ):
        """Enregistrer un événement d'audit"""
        await self.ensure_connected()
        
        import json
        
        await self.pool.execute(
            """
            INSERT INTO audit_log 
            (event_type, action, actor_name, target_type, target_id, target_name, 
             old_value, new_value, source)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            """,
            event_type, action, actor_name, target_type, target_id, target_name,
            json.dumps(old_value) if old_value else None,
            json.dumps(new_value) if new_value else None,
            source
        )


# Instance singleton
homeapp_db = HomeAppDBService()

