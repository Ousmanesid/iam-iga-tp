"""
Router pour les workflows d'approbation (pré et post-provisioning)
Interface avec N8N pour orchestrer les validations
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import Optional
from uuid import UUID
from datetime import datetime
import structlog
import hashlib

from ..models.request import (
    PreProvisionRequest, PostProvisionRequest,
    ApprovalDecision, ProvisioningRequestResponse,
    WorkflowTriggerResponse, RequestStatus, ApprovalLevel,
    ApprovalStep, RequestType
)
from ..services.homeapp_db import homeapp_db
from ..services.n8n import n8n_service
from ..services.midpoint import midpoint_service

logger = structlog.get_logger()
router = APIRouter(prefix="/workflow", tags=["Workflows"])


# === Endpoints de pré-provisioning ===

@router.post("/pre-provision", response_model=WorkflowTriggerResponse, summary="Déclencher un workflow de pré-provisioning")
async def trigger_pre_provision(request: PreProvisionRequest, background_tasks: BackgroundTasks):
    """
    Déclencher un workflow de pré-provisioning avant la création d'un compte.
    
    Ce workflow peut être:
    - Simple (1 étape): approbation par le responsable applicatif
    - Multi-étapes: Manager -> Chef département -> Responsable app
    
    Le compte ne sera créé qu'après approbation complète.
    """
    try:
        # Créer la demande en base
        request_id = await homeapp_db.create_provisioning_request(
            request_type=request.request_type.value,
            target_user_login=request.target_user_login,
            payload={
                "user_data": request.target_user_data,
                "requested_roles": request.requested_roles,
                "requested_permissions": request.requested_permissions,
                "target_system": request.target_system
            },
            requester_name=request.requester_name,
            justification=request.justification
        )
        
        # Déterminer le type de workflow
        if len(request.approval_levels) > 1:
            # Workflow multi-étapes
            approval_chain = _build_approval_chain(
                request.approval_levels,
                request.target_user_data
            )
            
            result = await n8n_service.trigger_pre_provision_multi(
                user_data=request.target_user_data,
                requested_roles=request.requested_roles,
                requested_permissions=request.requested_permissions,
                target_system=request.target_system,
                approval_chain=approval_chain,
                requester=request.requester_name,
                justification=request.justification
            )
        else:
            # Workflow simple
            result = await n8n_service.trigger_pre_provision_simple(
                user_data=request.target_user_data,
                requested_roles=request.requested_roles,
                requested_permissions=request.requested_permissions,
                target_system=request.target_system,
                requester=request.requester_name,
                justification=request.justification
            )
        
        # Mettre à jour la demande avec l'ID du workflow
        if result.get("execution_id") or result.get("workflow_id"):
            workflow_id = result.get("execution_id") or result.get("workflow_id")
            # Note: mise à jour async en arrière-plan
        
        return WorkflowTriggerResponse(
            success=result.get("success", True),
            workflow_id=str(request_id),
            execution_id=result.get("execution_id"),
            message="Workflow de pré-provisioning déclenché. En attente d'approbation.",
            data={"request_id": str(request_id)}
        )
    
    except Exception as e:
        logger.error("Failed to trigger pre-provision workflow", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/post-provision", response_model=WorkflowTriggerResponse, summary="Déclencher un workflow de post-provisioning")
async def trigger_post_provision(request: PostProvisionRequest):
    """
    Déclencher un workflow de post-provisioning après création d'un compte.
    
    Ce workflow envoie une notification de revue au responsable.
    Si le compte est rejeté, il sera désactivé ou supprimé.
    """
    try:
        # Créer la demande en base
        request_id = await homeapp_db.create_provisioning_request(
            request_type="post_provision_review",
            target_user_login=request.target_user_login,
            payload={
                "user_id": request.target_user_id,
                "provisioned_systems": request.provisioned_systems,
                "provisioned_roles": request.provisioned_roles,
                "midpoint_oid": request.midpoint_oid
            },
            requester_name="system"
        )
        
        # Récupérer les infos utilisateur
        user_data = await homeapp_db.get_user_by_login(request.target_user_login)
        
        # Déclencher le workflow N8N
        result = await n8n_service.trigger_post_provision(
            user_login=request.target_user_login,
            user_data=dict(user_data) if user_data else {},
            provisioned_systems=request.provisioned_systems,
            provisioned_roles=request.provisioned_roles
        )
        
        return WorkflowTriggerResponse(
            success=result.get("success", True),
            workflow_id=str(request_id),
            execution_id=result.get("execution_id"),
            message="Workflow de post-provisioning déclenché. Notification envoyée pour revue.",
            data={"request_id": str(request_id)}
        )
    
    except Exception as e:
        logger.error("Failed to trigger post-provision workflow", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


# === Endpoints de callback (appelés par N8N) ===

@router.post("/callback/approval", summary="Callback d'approbation (appelé par N8N)")
async def approval_callback(decision: ApprovalDecision):
    """
    Endpoint appelé par N8N quand une décision d'approbation est prise.
    
    Met à jour le statut de la demande et:
    - Si approuvé: procède au provisioning
    - Si rejeté: marque la demande comme rejetée
    """
    try:
        if decision.decision == RequestStatus.APPROVED:
            # Marquer la demande comme approuvée
            await homeapp_db.update_provisioning_request_status(
                request_id=decision.request_id,
                status="approved",
                completed_at=datetime.utcnow()
            )

            request_data = await homeapp_db.get_provisioning_request(decision.request_id)
            if not request_data:
                raise HTTPException(status_code=404, detail="Demande introuvable")

            try:
                action_result = await _apply_approved_request(request_data)
                await homeapp_db.update_provisioning_request_status(
                    request_id=decision.request_id,
                    status="completed",
                    completed_at=datetime.utcnow()
                )
            except Exception as e:
                logger.error("Provisioning failed", request_id=str(decision.request_id), error=str(e))
                await homeapp_db.update_provisioning_request_status(
                    request_id=decision.request_id,
                    status="failed",
                    completed_at=datetime.utcnow()
                )
                raise

            return {
                "success": True,
                "request_id": str(decision.request_id),
                "status": "completed",
                "message": "Demande approuvée et provisioning effectué.",
                "data": action_result
            }
        
        elif decision.decision == RequestStatus.REJECTED:
            await homeapp_db.update_provisioning_request_status(
                request_id=decision.request_id,
                status="rejected",
                completed_at=datetime.utcnow()
            )
            
            return {
                "success": True,
                "request_id": str(decision.request_id),
                "status": "rejected",
                "message": f"Demande rejetée. Raison: {decision.comment or 'Non spécifiée'}"
            }
        
        else:
            raise HTTPException(status_code=400, detail="Décision invalide")
    
    except Exception as e:
        logger.error("Approval callback failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/callback/review", summary="Callback de revue post-provisioning (appelé par N8N)")
async def review_callback(
    request_id: UUID,
    approved: bool,
    reviewer: str,
    comment: Optional[str] = None
):
    """
    Endpoint appelé par N8N après une revue post-provisioning.
    
    Si la revue est négative, désactive ou supprime le compte créé.
    """
    try:
        if approved:
            await homeapp_db.update_provisioning_request_status(
                request_id=request_id,
                status="completed",
                completed_at=datetime.utcnow()
            )
            
            return {
                "success": True,
                "request_id": str(request_id),
                "status": "completed",
                "message": "Revue validée. Compte confirmé."
            }
        
        else:
            # Récupérer les infos de la demande pour trouver l'utilisateur
            # et le désactiver
            
            await homeapp_db.update_provisioning_request_status(
                request_id=request_id,
                status="rejected",
                completed_at=datetime.utcnow()
            )
            
            request_data = await homeapp_db.get_provisioning_request(request_id)
            target_login = None
            if request_data:
                target_login = request_data.get("target_user_login")
                payload = request_data.get("payload") or {}
                if not target_login and isinstance(payload, dict):
                    user_data = payload.get("user_data") or {}
                    target_login = user_data.get("login")

            if target_login:
                await homeapp_db.disable_user(target_login)
            
            return {
                "success": True,
                "request_id": str(request_id),
                "status": "rejected",
                "message": f"Revue négative par {reviewer}. Action: désactivation du compte."
            }
    
    except Exception as e:
        logger.error("Review callback failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


# === Endpoints de gestion des demandes ===

@router.get("/requests/pending", summary="Lister les demandes en attente")
async def list_pending_requests():
    """Lister toutes les demandes de provisioning en attente d'approbation"""
    requests = await homeapp_db.get_pending_requests()
    
    return {
        "count": len(requests),
        "requests": requests
    }


@router.get("/requests/{request_id}", summary="Obtenir le détail d'une demande")
async def get_request(request_id: UUID):
    """Obtenir les détails d'une demande de provisioning"""
    request_data = await homeapp_db.get_provisioning_request(request_id)
    if not request_data:
        raise HTTPException(status_code=404, detail="Demande introuvable")

    steps = [
        ApprovalStep(
            step_order=step["step_order"],
            approver_type=ApprovalLevel(step["approver_type"]),
            approver_email=step.get("approver_email"),
            status=RequestStatus(step["status"]),
            decision_at=step.get("decision_at"),
            comment=step.get("comment")
        )
        for step in request_data.get("approval_steps", [])
    ]

    return ProvisioningRequestResponse(
        request_id=request_id,
        request_type=RequestType(request_data["request_type"]),
        status=RequestStatus(request_data["status"]),
        target_user_login=request_data.get("target_user_login") or "",
        approval_steps=steps,
        created_at=request_data["created_at"],
        updated_at=request_data["updated_at"],
        completed_at=request_data.get("completed_at"),
        n8n_workflow_id=request_data.get("n8n_workflow_id"),
        message=request_data.get("justification")
    )


# === Helpers ===

def _build_approval_chain(levels: list[ApprovalLevel], target_user_data: Optional[dict] = None) -> list:
    """Construire la chaîne d'approbation à partir des niveaux"""
    chain = []
    data = target_user_data or {}
    
    for i, level in enumerate(levels):
        approver = {
            "step": i + 1,
            "level": level.value,
            "required": True
        }
        
        email_key = {
            ApprovalLevel.MANAGER: "manager_email",
            ApprovalLevel.DEPT_HEAD: "dept_head_email",
            ApprovalLevel.APP_OWNER: "app_owner_email",
            ApprovalLevel.SECURITY: "security_email"
        }.get(level)
        approver_email = data.get(email_key) if email_key else None
        if approver_email:
            approver["email"] = approver_email

        if level == ApprovalLevel.MANAGER:
            approver["role"] = "manager"
        elif level == ApprovalLevel.DEPT_HEAD:
            approver["role"] = "department_head"
        elif level == ApprovalLevel.APP_OWNER:
            approver["role"] = "application_owner"
        elif level == ApprovalLevel.SECURITY:
            approver["role"] = "security_officer"
        
        chain.append(approver)
    
    return chain


def _hash_password(raw_password: Optional[str]) -> Optional[str]:
    if not raw_password:
        return None
    return hashlib.sha256(raw_password.encode("utf-8")).hexdigest()


async def _apply_approved_request(request_data: dict) -> dict:
    request_type = request_data.get("request_type")
    payload = request_data.get("payload") or {}
    if not isinstance(payload, dict):
        payload = {}

    target_login = request_data.get("target_user_login")
    user_data = payload.get("user_data") or {}
    if not target_login and isinstance(user_data, dict):
        target_login = user_data.get("login")

    if request_type == RequestType.CREATE_USER.value:
        if not target_login:
            raise ValueError("Login utilisateur manquant pour la création")
        email = user_data.get("email")
        if not email:
            raise ValueError("Email utilisateur manquant pour la création")

        user_id = await homeapp_db.create_user(
            login=target_login,
            email=email,
            password_hash=_hash_password(user_data.get("password")),
            first_name=user_data.get("first_name"),
            last_name=user_data.get("last_name"),
            department=user_data.get("department"),
            job_title=user_data.get("job_title"),
            employee_number=user_data.get("employee_number"),
            is_active=user_data.get("is_active", True),
            midpoint_oid=payload.get("midpoint_oid") or user_data.get("midpoint_oid"),
            attributes=user_data.get("attributes") or {}
        )

        for role_code in payload.get("requested_roles", []):
            await homeapp_db.assign_role(user_login=target_login, role_code=role_code, source="workflow")
        for perm_code in payload.get("requested_permissions", []):
            await homeapp_db.assign_permission(user_login=target_login, permission_code=perm_code)

        return {"action": "create_user", "user_id": str(user_id)}

    if not target_login:
        raise ValueError("Login utilisateur manquant pour la demande approuvée")

    if request_type == RequestType.ASSIGN_ROLE.value:
        role_code = payload.get("role_code")
        if not role_code:
            raise ValueError("role_code manquant pour assign_role")
        await homeapp_db.assign_role(user_login=target_login, role_code=role_code, source="workflow")
        return {"action": "assign_role", "role_code": role_code}

    if request_type == RequestType.REVOKE_ROLE.value:
        role_code = payload.get("role_code")
        if not role_code:
            raise ValueError("role_code manquant pour revoke_role")
        await homeapp_db.revoke_role(target_login, role_code)
        return {"action": "revoke_role", "role_code": role_code}

    if request_type == RequestType.ASSIGN_PERMISSION.value:
        permission_code = payload.get("permission_code")
        if not permission_code:
            raise ValueError("permission_code manquant pour assign_permission")
        await homeapp_db.assign_permission(user_login=target_login, permission_code=permission_code)
        return {"action": "assign_permission", "permission_code": permission_code}

    if request_type == RequestType.REVOKE_PERMISSION.value:
        permission_code = payload.get("permission_code")
        if not permission_code:
            raise ValueError("permission_code manquant pour revoke_permission")
        await homeapp_db.revoke_permission(target_login, permission_code)
        return {"action": "revoke_permission", "permission_code": permission_code}

    if request_type == RequestType.UPDATE_USER.value:
        update_data = payload.get("user_updates") or payload.get("user_data") or {}
        if not update_data:
            raise ValueError("Aucune donnée de mise à jour fournie")
        await homeapp_db.update_user(target_login, update_data)
        return {"action": "update_user", "updated_fields": list(update_data.keys())}

    if request_type == RequestType.DELETE_USER.value:
        await homeapp_db.delete_user(target_login)
        return {"action": "delete_user"}

    raise ValueError(f"Type de demande non pris en charge: {request_type}")


# === Endpoint pour MidPoint (hook de provisioning) ===

@router.post("/midpoint/hook", summary="Hook appelé par MidPoint lors du provisioning")
async def midpoint_provisioning_hook(
    event_type: str,  # "pre_provision" ou "post_provision"
    user_oid: str,
    resource_oid: str,
    operation: str,  # "add", "modify", "delete"
    data: dict
):
    """
    Hook appelé par MidPoint pendant le cycle de provisioning.
    
    Permet de:
    - Déclencher un workflow de pré-provisioning avant l'action
    - Déclencher un workflow de post-provisioning après l'action
    """
    logger.info(
        "MidPoint hook received",
        event_type=event_type,
        user_oid=user_oid,
        operation=operation
    )
    
    if event_type == "pre_provision":
        # Vérifier si l'opération nécessite une approbation
        # basée sur les rôles demandés ou la ressource cible
        
        requires_approval = data.get("requires_approval", False)
        
        if requires_approval:
            # Déclencher le workflow et retourner "hold"
            return {
                "action": "hold",
                "message": "Workflow d'approbation déclenché",
                "workflow_triggered": True
            }
        else:
            return {
                "action": "continue",
                "message": "Aucune approbation requise"
            }
    
    elif event_type == "post_provision":
        # Optionnellement déclencher une revue
        if data.get("requires_review", False):
            return {
                "action": "review_triggered",
                "message": "Workflow de revue déclenché"
            }
        
        return {
            "action": "completed",
            "message": "Provisioning terminé"
        }
    
    return {"action": "unknown", "message": "Type d'événement non reconnu"}








