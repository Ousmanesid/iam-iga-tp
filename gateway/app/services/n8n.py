"""
Service pour interagir avec N8N (orchestration des workflows)
"""

import httpx
from typing import Optional, Dict, Any
import structlog
from datetime import datetime

from ..config import settings

logger = structlog.get_logger()


class N8NService:
    """Service pour déclencher et gérer les workflows N8N"""
    
    def __init__(self):
        self.base_url = settings.n8n_url
        self.webhook_base = settings.n8n_webhook_base
        self.auth = (settings.n8n_user, settings.n8n_password)
    
    async def _make_request(
        self,
        method: str,
        url: str,
        data: Optional[Dict[str, Any]] = None,
        timeout: float = 30.0
    ) -> Dict[str, Any]:
        """Faire une requête HTTP vers N8N"""
        async with httpx.AsyncClient(timeout=timeout) as client:
            try:
                if method.upper() == "GET":
                    response = await client.get(url, auth=self.auth)
                elif method.upper() == "POST":
                    response = await client.post(url, json=data, auth=self.auth)
                else:
                    raise ValueError(f"Method {method} not supported")
                
                response.raise_for_status()
                return response.json() if response.text else {}
            
            except httpx.HTTPError as e:
                logger.error("N8N request failed", url=url, error=str(e))
                raise
    
    async def trigger_webhook(
        self,
        webhook_path: str,
        data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Déclencher un webhook N8N"""
        url = f"{self.webhook_base}{webhook_path}"
        
        logger.info("Triggering N8N webhook", webhook=webhook_path)
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                response = await client.post(url, json=data)
                response.raise_for_status()
                
                result = response.json() if response.text else {"success": True}
                logger.info("Webhook triggered successfully", webhook=webhook_path)
                return result
            
            except httpx.HTTPError as e:
                logger.error("Webhook trigger failed", webhook=webhook_path, error=str(e))
                return {"success": False, "error": str(e)}
    
    # === Workflows de pré-provisioning ===
    
    async def trigger_pre_provision_simple(
        self,
        user_data: Dict[str, Any],
        requested_roles: list,
        requested_permissions: list,
        target_system: str,
        requester: Optional[str] = None,
        justification: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Déclencher le workflow de pré-provisioning simple (1 étape)
        Attend l'approbation du responsable applicatif
        """
        payload = {
            "workflow_type": "pre_provision_simple",
            "timestamp": datetime.utcnow().isoformat(),
            "user_data": user_data,
            "requested_roles": requested_roles,
            "requested_permissions": requested_permissions,
            "target_system": target_system,
            "requester": requester,
            "justification": justification,
            "callback_url": f"{settings.n8n_url}/webhook/approval-callback"
        }
        
        return await self.trigger_webhook(settings.webhook_pre_provision, payload)
    
    async def trigger_pre_provision_multi(
        self,
        user_data: Dict[str, Any],
        requested_roles: list,
        requested_permissions: list,
        target_system: str,
        approval_chain: list,  # Liste des approbateurs ordonnés
        requester: Optional[str] = None,
        justification: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Déclencher le workflow de pré-provisioning multi-étapes
        Passe par: Manager -> Chef de département -> Responsable applicatif
        """
        payload = {
            "workflow_type": "pre_provision_multi",
            "timestamp": datetime.utcnow().isoformat(),
            "user_data": user_data,
            "requested_roles": requested_roles,
            "requested_permissions": requested_permissions,
            "target_system": target_system,
            "approval_chain": approval_chain,
            "current_step": 0,
            "requester": requester,
            "justification": justification,
            "callback_url": f"{settings.n8n_url}/webhook/approval-callback"
        }
        
        return await self.trigger_webhook(settings.webhook_pre_provision, payload)
    
    # === Workflows de post-provisioning ===
    
    async def trigger_post_provision(
        self,
        user_login: str,
        user_data: Dict[str, Any],
        provisioned_systems: list,
        provisioned_roles: list,
        reviewer_email: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Déclencher le workflow de post-provisioning (revue après création)
        Envoie une notification au responsable pour validation
        """
        payload = {
            "workflow_type": "post_provision",
            "timestamp": datetime.utcnow().isoformat(),
            "user_login": user_login,
            "user_data": user_data,
            "provisioned_systems": provisioned_systems,
            "provisioned_roles": provisioned_roles,
            "reviewer_email": reviewer_email,
            "callback_url": f"{settings.n8n_url}/webhook/review-callback"
        }
        
        return await self.trigger_webhook(settings.webhook_post_provision, payload)
    
    # === Workflow Chatbot ===
    
    async def trigger_chatbot_action(
        self,
        action_type: str,
        target_user: Optional[str] = None,
        target_filters: Optional[Dict[str, Any]] = None,
        role_or_permission: Optional[str] = None,
        requester: Optional[str] = None,
        requires_approval: bool = False
    ) -> Dict[str, Any]:
        """
        Déclencher une action depuis le chatbot
        Peut déclencher directement l'action ou un workflow d'approbation
        """
        payload = {
            "workflow_type": "chatbot_action",
            "timestamp": datetime.utcnow().isoformat(),
            "action_type": action_type,
            "target_user": target_user,
            "target_filters": target_filters,
            "role_or_permission": role_or_permission,
            "requester": requester,
            "requires_approval": requires_approval
        }
        
        return await self.trigger_webhook(settings.webhook_chatbot, payload)
    
    # === Gestion des exécutions ===
    
    async def get_execution_status(self, execution_id: str) -> Dict[str, Any]:
        """Obtenir le statut d'une exécution de workflow"""
        url = f"{self.base_url}/api/v1/executions/{execution_id}"
        return await self._make_request("GET", url)
    
    async def get_workflow_executions(
        self,
        workflow_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 20
    ) -> list:
        """Lister les exécutions de workflows"""
        url = f"{self.base_url}/api/v1/executions"
        params = {"limit": limit}
        
        if workflow_id:
            params["workflowId"] = workflow_id
        if status:
            params["status"] = status
        
        # Note: L'API N8N peut nécessiter des ajustements selon la version
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, params=params, auth=self.auth)
                response.raise_for_status()
                return response.json().get("data", [])
        except Exception as e:
            logger.warning("Could not fetch executions", error=str(e))
            return []
    
    # === Helpers ===
    
    async def health_check(self) -> bool:
        """Vérifier si N8N est accessible"""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.base_url}/healthz")
                return response.status_code == 200
        except Exception:
            return False
    
    def build_approval_chain(
        self,
        manager_email: Optional[str] = None,
        dept_head_email: Optional[str] = None,
        app_owner_email: Optional[str] = None,
        security_email: Optional[str] = None
    ) -> list:
        """Construire une chaîne d'approbation"""
        chain = []
        
        if manager_email:
            chain.append({
                "level": "manager",
                "email": manager_email,
                "required": True
            })
        
        if dept_head_email:
            chain.append({
                "level": "dept_head",
                "email": dept_head_email,
                "required": True
            })
        
        if app_owner_email:
            chain.append({
                "level": "app_owner",
                "email": app_owner_email,
                "required": True
            })
        
        if security_email:
            chain.append({
                "level": "security",
                "email": security_email,
                "required": False  # Optionnel selon les cas
            })
        
        return chain


# Instance singleton
n8n_service = N8NService()








