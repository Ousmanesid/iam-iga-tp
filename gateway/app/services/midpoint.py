"""
Service pour interagir avec l'API MidPoint
"""

import httpx
from typing import Optional, Dict, Any, List
import structlog
from xml.etree import ElementTree as ET
import json

from ..config import settings

logger = structlog.get_logger()


class MidPointService:
    """Service pour les opérations via l'API REST MidPoint"""
    
    def __init__(self):
        self.base_url = settings.midpoint_url
        self.auth = (settings.midpoint_user, settings.midpoint_password)
        self.api_url = f"{self.base_url}/ws/rest"
    
    def _get_headers(self, accept: str = "application/json") -> Dict[str, str]:
        """Headers pour les requêtes API"""
        return {
            "Accept": accept,
            "Content-Type": "application/json"
        }
    
    async def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        timeout: float = 30.0
    ) -> Dict[str, Any]:
        """Faire une requête HTTP vers l'API MidPoint"""
        url = f"{self.api_url}/{endpoint}"
        
        async with httpx.AsyncClient(timeout=timeout) as client:
            try:
                if method.upper() == "GET":
                    response = await client.get(
                        url, 
                        headers=self._get_headers(),
                        auth=self.auth,
                        params=params
                    )
                elif method.upper() == "POST":
                    response = await client.post(
                        url,
                        headers=self._get_headers(),
                        auth=self.auth,
                        json=data
                    )
                elif method.upper() == "PUT":
                    response = await client.put(
                        url,
                        headers=self._get_headers(),
                        auth=self.auth,
                        json=data
                    )
                elif method.upper() == "PATCH":
                    response = await client.patch(
                        url,
                        headers=self._get_headers(),
                        auth=self.auth,
                        json=data
                    )
                elif method.upper() == "DELETE":
                    response = await client.delete(
                        url,
                        headers=self._get_headers(),
                        auth=self.auth
                    )
                else:
                    raise ValueError(f"Method {method} not supported")
                
                response.raise_for_status()
                
                if response.text:
                    return response.json()
                return {"success": True}
                
            except httpx.HTTPError as e:
                logger.error("MidPoint request failed", url=url, error=str(e))
                raise
    
    # === Opérations sur les utilisateurs ===
    
    async def search_users(
        self,
        query: Optional[str] = None,
        department: Optional[str] = None,
        name: Optional[str] = None,
        max_size: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Rechercher des utilisateurs dans MidPoint
        
        Utilise l'API de recherche MidPoint avec un filtre
        """
        # Construction du filtre de recherche
        search_filter = {}
        
        if query:
            # Recherche full-text
            search_filter = {
                "query": {
                    "filter": {
                        "or": {
                            "filter": [
                                {"equal": {"path": "name", "value": query}},
                                {"substring": {"path": "givenName", "value": query}},
                                {"substring": {"path": "familyName", "value": query}},
                                {"equal": {"path": "emailAddress", "value": query}}
                            ]
                        }
                    }
                }
            }
        elif department:
            search_filter = {
                "query": {
                    "filter": {
                        "equal": {
                            "path": "organization",
                            "value": department
                        }
                    }
                }
            }
        elif name:
            search_filter = {
                "query": {
                    "filter": {
                        "or": {
                            "filter": [
                                {"substring": {"path": "givenName", "value": name}},
                                {"substring": {"path": "familyName", "value": name}},
                                {"substring": {"path": "fullName", "value": name}}
                            ]
                        }
                    }
                }
            }
        
        try:
            result = await self._make_request(
                "POST",
                "users/search",
                data=search_filter,
                params={"options": f"maxSize={max_size}"}
            )
            
            # Parser le résultat
            users = result.get("object", [])
            if isinstance(users, dict):
                users = [users]
            
            return [self._parse_user(u) for u in users]
            
        except Exception as e:
            logger.error("Failed to search users", error=str(e))
            return []
    
    async def get_user_by_oid(self, oid: str) -> Optional[Dict[str, Any]]:
        """Récupérer un utilisateur par son OID"""
        try:
            result = await self._make_request("GET", f"users/{oid}")
            return self._parse_user(result)
        except Exception as e:
            logger.error("Failed to get user", oid=oid, error=str(e))
            return None
    
    async def get_user_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Récupérer un utilisateur par son name (login)"""
        users = await self.search_users(query=name, max_size=1)
        return users[0] if users else None
    
    def _parse_user(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Parser les données utilisateur MidPoint"""
        user = user_data.get("user", user_data)
        
        return {
            "oid": user.get("oid"),
            "name": user.get("name"),
            "givenName": user.get("givenName"),
            "familyName": user.get("familyName"),
            "fullName": user.get("fullName"),
            "emailAddress": user.get("emailAddress"),
            "organization": user.get("organization"),
            "title": user.get("title"),
            "personalNumber": user.get("personalNumber"),
            "activation": user.get("activation", {}),
            "assignment": user.get("assignment", [])
        }
    
    # === Opérations sur les rôles ===
    
    async def get_roles(self) -> List[Dict[str, Any]]:
        """Lister tous les rôles disponibles"""
        try:
            result = await self._make_request("POST", "roles/search", data={})
            roles = result.get("object", [])
            if isinstance(roles, dict):
                roles = [roles]
            
            return [self._parse_role(r) for r in roles]
        except Exception as e:
            logger.error("Failed to get roles", error=str(e))
            return []
    
    async def get_role_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Récupérer un rôle par son nom"""
        search_filter = {
            "query": {
                "filter": {
                    "equal": {
                        "path": "name",
                        "value": name
                    }
                }
            }
        }
        
        try:
            result = await self._make_request("POST", "roles/search", data=search_filter)
            roles = result.get("object", [])
            if roles:
                return self._parse_role(roles[0] if isinstance(roles, list) else roles)
            return None
        except Exception as e:
            logger.error("Failed to get role", name=name, error=str(e))
            return None
    
    def _parse_role(self, role_data: Dict[str, Any]) -> Dict[str, Any]:
        """Parser les données de rôle MidPoint"""
        role = role_data.get("role", role_data)
        
        return {
            "oid": role.get("oid"),
            "name": role.get("name"),
            "displayName": role.get("displayName"),
            "description": role.get("description"),
            "requestable": role.get("requestable", False),
            "riskLevel": role.get("riskLevel")
        }
    
    # === Assignation de rôles ===
    
    async def assign_role_to_user(
        self,
        user_oid: str,
        role_oid: str
    ) -> bool:
        """Assigner un rôle à un utilisateur"""
        # Modification delta pour ajouter un assignment
        modification = {
            "objectModification": {
                "@type": "c:ObjectModificationType",
                "itemDelta": {
                    "modificationType": "add",
                    "path": "assignment",
                    "value": {
                        "targetRef": {
                            "oid": role_oid,
                            "type": "RoleType"
                        }
                    }
                }
            }
        }
        
        try:
            await self._make_request("PATCH", f"users/{user_oid}", data=modification)
            logger.info("Role assigned via MidPoint", user_oid=user_oid, role_oid=role_oid)
            return True
        except Exception as e:
            logger.error("Failed to assign role", user_oid=user_oid, role_oid=role_oid, error=str(e))
            return False
    
    async def remove_role_from_user(
        self,
        user_oid: str,
        role_oid: str
    ) -> bool:
        """Retirer un rôle d'un utilisateur"""
        modification = {
            "objectModification": {
                "@type": "c:ObjectModificationType",
                "itemDelta": {
                    "modificationType": "delete",
                    "path": "assignment",
                    "value": {
                        "targetRef": {
                            "oid": role_oid,
                            "type": "RoleType"
                        }
                    }
                }
            }
        }
        
        try:
            await self._make_request("PATCH", f"users/{user_oid}", data=modification)
            logger.info("Role removed via MidPoint", user_oid=user_oid, role_oid=role_oid)
            return True
        except Exception as e:
            logger.error("Failed to remove role", user_oid=user_oid, role_oid=role_oid, error=str(e))
            return False
    
    async def get_user_assignments(self, user_oid: str) -> List[Dict[str, Any]]:
        """Obtenir les assignments (rôles) d'un utilisateur"""
        user = await self.get_user_by_oid(user_oid)
        if user:
            assignments = user.get("assignment", [])
            if isinstance(assignments, dict):
                assignments = [assignments]
            return assignments
        return []
    
    # === Recompute / Synchronisation ===
    
    async def recompute_user(self, user_oid: str) -> bool:
        """Forcer le recalcul des droits d'un utilisateur"""
        try:
            await self._make_request(
                "POST",
                f"users/{user_oid}/recompute",
                data={}
            )
            logger.info("User recomputed", user_oid=user_oid)
            return True
        except Exception as e:
            logger.error("Failed to recompute user", user_oid=user_oid, error=str(e))
            return False
    
    # === Health Check ===
    
    async def health_check(self) -> bool:
        """Vérifier si MidPoint est accessible"""
        try:
            # S'assurer que l'URL est en HTTP (pas HTTPS)
            url = self.base_url
            if url.startswith("https://"):
                url = url.replace("https://", "http://", 1)
            
            async with httpx.AsyncClient(timeout=10.0, verify=False, follow_redirects=True) as client:
                response = await client.get(
                    f"{url}/",
                    auth=self.auth
                )
                return response.status_code in [200, 302]
        except (httpx.HTTPError, Exception):
            return False


# Instance singleton
midpoint_service = MidPointService()


