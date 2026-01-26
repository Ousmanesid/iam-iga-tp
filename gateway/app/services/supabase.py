"""
Service pour interagir avec Supabase (alternative cloud à PostgreSQL local)
Utilise l'API REST de Supabase pour les opérations CRUD
"""

import httpx
from typing import Optional, List, Dict, Any
from datetime import datetime
import structlog

from ..config import settings

logger = structlog.get_logger()


class SupabaseService:
    """
    Service pour les opérations vers Supabase
    Miroir du service HomeAppDB mais utilisant l'API REST Supabase
    """
    
    def __init__(self):
        self.enabled = settings.supabase_enabled
        self.url = settings.supabase_url
        self.service_key = settings.supabase_service_key
        self._headers = None
    
    @property
    def headers(self) -> Dict[str, str]:
        """Headers pour les requêtes API Supabase"""
        if self._headers is None:
            self._headers = {
                "apikey": self.service_key or "",
                "Authorization": f"Bearer {self.service_key or ''}",
                "Content-Type": "application/json",
                "Prefer": "return=representation"
            }
        return self._headers
    
    def _check_enabled(self):
        """Vérifier que Supabase est configuré"""
        if not self.enabled:
            raise ValueError("Supabase n'est pas activé. Définir SUPABASE_ENABLED=true")
        if not self.url or not self.service_key:
            raise ValueError("Configuration Supabase incomplète (URL ou clé manquante)")
    
    async def _request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Faire une requête vers l'API REST Supabase"""
        self._check_enabled()
        
        url = f"{self.url}/rest/v1/{endpoint}"
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                if method.upper() == "GET":
                    response = await client.get(url, headers=self.headers, params=params)
                elif method.upper() == "POST":
                    response = await client.post(url, headers=self.headers, json=data, params=params)
                elif method.upper() == "PATCH":
                    response = await client.patch(url, headers=self.headers, json=data, params=params)
                elif method.upper() == "DELETE":
                    response = await client.delete(url, headers=self.headers, params=params)
                else:
                    raise ValueError(f"Method {method} not supported")
                
                response.raise_for_status()
                
                if response.text:
                    return response.json()
                return {"success": True}
                
            except httpx.HTTPError as e:
                logger.error("Supabase request failed", url=url, error=str(e))
                raise
    
    async def _rpc(self, function_name: str, params: Dict[str, Any]) -> Any:
        """Appeler une fonction RPC Supabase"""
        self._check_enabled()
        
        url = f"{self.url}/rest/v1/rpc/{function_name}"
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, headers=self.headers, json=params)
            response.raise_for_status()
            
            if response.text:
                return response.json()
            return None
    
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
    ) -> Optional[str]:
        """Créer ou mettre à jour un utilisateur via RPC upsert"""
        try:
            result = await self._rpc("upsert_user", {
                "p_login": login,
                "p_email": email,
                "p_password_hash": password_hash,
                "p_first_name": first_name,
                "p_last_name": last_name,
                "p_department": department,
                "p_job_title": job_title,
                "p_employee_number": employee_number,
                "p_is_active": is_active,
                "p_midpoint_oid": midpoint_oid,
                "p_attributes": attributes or {}
            })
            
            logger.info("User created/updated in Supabase", login=login, user_id=result)
            return result
            
        except Exception as e:
            logger.error("Failed to create user in Supabase", login=login, error=str(e))
            raise
    
    async def get_user_by_login(self, login: str) -> Optional[Dict[str, Any]]:
        """Récupérer un utilisateur par son login"""
        try:
            result = await self._request(
                "GET",
                "users",
                params={"login": f"eq.{login}", "select": "*"}
            )
            
            if result and isinstance(result, list) and len(result) > 0:
                return result[0]
            return None
            
        except Exception as e:
            logger.error("Failed to get user from Supabase", login=login, error=str(e))
            return None
    
    async def search_users(
        self,
        department: Optional[str] = None,
        job_title: Optional[str] = None,
        is_active: Optional[bool] = None,
        search_term: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Rechercher des utilisateurs"""
        params = {"select": "*", "limit": str(limit)}
        
        # Construction des filtres
        filters = []
        if department:
            filters.append(f"department.ilike.*{department}*")
        if job_title:
            filters.append(f"job_title.ilike.*{job_title}*")
        if is_active is not None:
            filters.append(f"is_active.eq.{str(is_active).lower()}")
        if search_term:
            # Recherche sur plusieurs colonnes avec or
            params["or"] = f"(login.ilike.*{search_term}*,email.ilike.*{search_term}*,full_name.ilike.*{search_term}*)"
        
        if filters:
            params["and"] = f"({','.join(filters)})"
        
        try:
            result = await self._request("GET", "users", params=params)
            return result if isinstance(result, list) else []
        except Exception as e:
            logger.error("Failed to search users in Supabase", error=str(e))
            return []
    
    async def update_user(self, login: str, updates: Dict[str, Any]) -> bool:
        """Mettre à jour un utilisateur"""
        try:
            await self._request(
                "PATCH",
                "users",
                data=updates,
                params={"login": f"eq.{login}"}
            )
            logger.info("User updated in Supabase", login=login)
            return True
        except Exception as e:
            logger.error("Failed to update user in Supabase", login=login, error=str(e))
            return False
    
    async def disable_user(self, login: str) -> bool:
        """Désactiver un utilisateur"""
        return await self.update_user(login, {"is_active": False})
    
    async def enable_user(self, login: str) -> bool:
        """Activer un utilisateur"""
        return await self.update_user(login, {"is_active": True})
    
    async def delete_user(self, login: str) -> bool:
        """Supprimer un utilisateur"""
        try:
            await self._request(
                "DELETE",
                "users",
                params={"login": f"eq.{login}"}
            )
            logger.info("User deleted from Supabase", login=login)
            return True
        except Exception as e:
            logger.error("Failed to delete user from Supabase", login=login, error=str(e))
            return False
    
    # === Opérations Rôles ===
    
    async def assign_role(
        self,
        user_login: str,
        role_code: str,
        assigned_by: str = "gateway",
        source: str = "manual"
    ) -> bool:
        """Assigner un rôle via RPC"""
        try:
            result = await self._rpc("assign_role_to_user", {
                "p_user_login": user_login,
                "p_role_code": role_code,
                "p_assigned_by": assigned_by,
                "p_source": source
            })
            logger.info("Role assigned in Supabase", user=user_login, role=role_code)
            return result is True
        except Exception as e:
            logger.error("Failed to assign role in Supabase", error=str(e))
            return False
    
    async def revoke_role(self, user_login: str, role_code: str) -> bool:
        """Révoquer un rôle via RPC"""
        try:
            result = await self._rpc("revoke_role_from_user", {
                "p_user_login": user_login,
                "p_role_code": role_code
            })
            logger.info("Role revoked in Supabase", user=user_login, role=role_code)
            return result is True
        except Exception as e:
            logger.error("Failed to revoke role in Supabase", error=str(e))
            return False
    
    async def get_user_roles(self, user_login: str) -> List[str]:
        """Obtenir les rôles d'un utilisateur"""
        try:
            # Requête avec jointure
            result = await self._request(
                "GET",
                "user_roles",
                params={
                    "select": "roles(code)",
                    "user_id": f"eq.{await self._get_user_id(user_login)}"
                }
            )
            
            if result and isinstance(result, list):
                return [r["roles"]["code"] for r in result if r.get("roles")]
            return []
        except Exception as e:
            logger.error("Failed to get user roles from Supabase", error=str(e))
            return []
    
    async def _get_user_id(self, login: str) -> Optional[str]:
        """Obtenir l'ID d'un utilisateur par son login"""
        user = await self.get_user_by_login(login)
        return user.get("id") if user else None
    
    # === Opérations Permissions ===
    
    async def get_user_permissions(self, user_login: str) -> List[Dict[str, str]]:
        """Obtenir les permissions effectives via RPC"""
        try:
            result = await self._rpc("get_user_effective_permissions", {
                "p_user_login": user_login
            })
            return result if isinstance(result, list) else []
        except Exception as e:
            logger.error("Failed to get user permissions from Supabase", error=str(e))
            return []
    
    # === Health Check ===
    
    async def health_check(self) -> bool:
        """Vérifier si Supabase est accessible"""
        if not self.enabled:
            return False
        
        try:
            async with httpx.AsyncClient(timeout=5.0, verify=True, follow_redirects=True) as client:
                response = await client.get(
                    f"{self.url}/rest/v1/",
                    headers=self.headers
                )
                return response.status_code in [200, 404]  # 404 = pas de table par défaut, mais API accessible
        except (httpx.HTTPError, Exception):
            return False


# Instance singleton
supabase_service = SupabaseService()


# === Service combiné pour le provisioning dual (PostgreSQL + Supabase) ===

class DualProvisioningService:
    """
    Service de provisioning qui peut écrire vers PostgreSQL local ET Supabase
    Permet une synchronisation entre les deux systèmes
    """
    
    def __init__(self, homeapp_db, supabase_svc):
        self.homeapp = homeapp_db
        self.supabase = supabase_svc
    
    async def provision_user(
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
        attributes: Dict[str, Any] = None,
        sync_to_supabase: bool = True
    ) -> Dict[str, Any]:
        """
        Provisionner un utilisateur vers PostgreSQL et optionnellement vers Supabase
        
        Returns:
            Dict avec les résultats pour chaque système
        """
        results = {
            "postgresql": {"success": False, "user_id": None},
            "supabase": {"success": False, "user_id": None, "skipped": False}
        }
        
        # 1. Provisioning PostgreSQL (toujours)
        try:
            user_id = await self.homeapp.create_user(
                login=login,
                email=email,
                password_hash=password_hash,
                first_name=first_name,
                last_name=last_name,
                department=department,
                job_title=job_title,
                employee_number=employee_number,
                is_active=is_active,
                midpoint_oid=midpoint_oid,
                attributes=attributes
            )
            results["postgresql"] = {"success": True, "user_id": str(user_id)}
        except Exception as e:
            results["postgresql"] = {"success": False, "error": str(e)}
        
        # 2. Provisioning Supabase (si activé et demandé)
        if sync_to_supabase and self.supabase.enabled:
            try:
                sb_user_id = await self.supabase.create_user(
                    login=login,
                    email=email,
                    password_hash=password_hash,
                    first_name=first_name,
                    last_name=last_name,
                    department=department,
                    job_title=job_title,
                    employee_number=employee_number,
                    is_active=is_active,
                    midpoint_oid=midpoint_oid,
                    attributes=attributes
                )
                results["supabase"] = {"success": True, "user_id": sb_user_id}
            except Exception as e:
                results["supabase"] = {"success": False, "error": str(e)}
        else:
            results["supabase"]["skipped"] = True
        
        return results
    
    async def assign_role_dual(
        self,
        user_login: str,
        role_code: str,
        assigned_by: str = "gateway",
        sync_to_supabase: bool = True
    ) -> Dict[str, Any]:
        """Assigner un rôle dans les deux systèmes"""
        results = {
            "postgresql": {"success": False},
            "supabase": {"success": False, "skipped": False}
        }
        
        # PostgreSQL
        try:
            pg_result = await self.homeapp.assign_role(
                user_login=user_login,
                role_code=role_code,
                assigned_by=assigned_by,
                source="gateway"
            )
            results["postgresql"] = {"success": pg_result}
        except Exception as e:
            results["postgresql"] = {"success": False, "error": str(e)}
        
        # Supabase
        if sync_to_supabase and self.supabase.enabled:
            try:
                sb_result = await self.supabase.assign_role(
                    user_login=user_login,
                    role_code=role_code,
                    assigned_by=assigned_by,
                    source="gateway"
                )
                results["supabase"] = {"success": sb_result}
            except Exception as e:
                results["supabase"] = {"success": False, "error": str(e)}
        else:
            results["supabase"]["skipped"] = True
        
        return results


