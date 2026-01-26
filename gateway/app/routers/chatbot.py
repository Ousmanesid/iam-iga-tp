"""
Router pour le chatbot IAM
Interface conversationnelle pour la gestion des identités et accès
"""

from fastapi import APIRouter, HTTPException
from typing import Optional, Dict, Any
from datetime import datetime
import structlog
import json

from ..models.request import ChatRequest, ChatResponse, ChatAction
from ..services.llm import llm_service
from ..services.homeapp_db import homeapp_db
from ..services.midpoint import midpoint_service
from ..services.n8n import n8n_service

logger = structlog.get_logger()
router = APIRouter(prefix="/chat", tags=["Chatbot IAM"])


# === Mapping des rôles sensibles nécessitant approbation ===
SENSITIVE_ROLES = {
    "IT_ADMIN": True,
    "RH_MANAGER": True,
    "FINANCE_MANAGER": True,
    "DIRECTOR": True
}


@router.post("/message", response_model=ChatResponse, summary="Envoyer un message au chatbot")
async def send_message(request: ChatRequest):
    """
    Envoyer un message au chatbot IAM et recevoir une réponse.
    
    Le chatbot peut:
    - Rechercher des utilisateurs
    - Assigner/retirer des rôles
    - Assigner/retirer des permissions
    - Lister les rôles et permissions d'un utilisateur
    - Déclencher des workflows d'approbation si nécessaire
    
    Exemples de messages:
    - "Donne le rôle Agent Commercial à Jean Dupont"
    - "Retire les droits admin à tous les employés du département Comptabilité"
    - "Quels sont les rôles de marie.martin?"
    """
    try:
        # Convertir l'historique de conversation au bon format
        conversation_history = []
        for msg in request.conversation_history:
            conversation_history.append({
                "role": msg.role,
                "content": msg.content
            })
        
        # Analyser le message avec le LLM
        parsed_command = await llm_service.parse_iam_command(
            request.message,
            conversation_history
        )
        
        logger.info("Parsed command", command=parsed_command)
        
        # Exécuter l'action correspondante
        result = await _execute_action(parsed_command, request.user_context)
        
        # Générer une réponse en langage naturel
        response_text = await _generate_response(request.message, parsed_command, result)
        
        # Construire l'action pour la réponse
        action = ChatAction(
            action_type=parsed_command.get("action", "unknown"),
            target_type=parsed_command.get("target_type", "user"),
            target_identifier=parsed_command.get("target_identifier"),
            target_filters=parsed_command.get("target_filters"),
            role_or_permission=parsed_command.get("role_or_permission"),
            requires_approval=result.get("requires_approval", False),
            confidence=parsed_command.get("confidence", 0.0)
        )
        
        return ChatResponse(
            response=response_text,
            actions_taken=[action],
            requires_confirmation=result.get("requires_confirmation", False),
            pending_workflow_id=result.get("workflow_id"),
            session_id=request.session_id
        )
    
    except Exception as e:
        logger.error("Chatbot error", error=str(e))
        return ChatResponse(
            response=f"Je suis désolé, une erreur s'est produite: {str(e)}. Pouvez-vous reformuler votre demande?",
            actions_taken=[],
            requires_confirmation=False
        )


@router.get("/health", summary="Vérifier l'état du chatbot")
async def chatbot_health():
    """Vérifier que le chatbot et le LLM sont opérationnels"""
    llm_status = await llm_service.health_check()
    
    return {
        "status": "ok" if llm_status.get("cloud_available") or llm_status.get("local_available") else "degraded",
        "llm": llm_status,
        "timestamp": datetime.utcnow().isoformat()
    }


# === Fonctions d'exécution des actions ===

async def _execute_action(command: Dict[str, Any], user_context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Exécuter l'action IAM identifiée par le LLM"""
    action = command.get("action")
    
    if action == "clarify":
        return {
            "success": True,
            "message": command.get("explanation", "Pourriez-vous préciser votre demande?"),
            "requires_action": False
        }
    
    elif action == "search_user":
        return await _action_search_user(command)
    
    elif action == "get_user_info":
        return await _action_get_user_info(command)
    
    elif action == "assign_role":
        return await _action_assign_role(command, user_context)
    
    elif action == "remove_role":
        return await _action_remove_role(command)
    
    elif action == "assign_permission":
        return await _action_assign_permission(command)
    
    elif action == "remove_permission":
        return await _action_remove_permission(command)
    
    elif action == "list_roles":
        return await _action_list_roles()
    
    elif action == "list_permissions":
        return await _action_list_user_permissions(command)
    
    else:
        return {
            "success": False,
            "message": f"Action '{action}' non reconnue",
            "requires_action": False
        }


async def _action_search_user(command: Dict[str, Any]) -> Dict[str, Any]:
    """Rechercher un utilisateur"""
    target = command.get("target_identifier")
    filters = command.get("target_filters", {})
    
    users = await homeapp_db.search_users(
        department=filters.get("department"),
        job_title=filters.get("job_title"),
        search_term=target,
        limit=10
    )
    
    return {
        "success": True,
        "users": users,
        "count": len(users),
        "message": f"{len(users)} utilisateur(s) trouvé(s)"
    }


async def _action_get_user_info(command: Dict[str, Any]) -> Dict[str, Any]:
    """Obtenir les informations d'un utilisateur"""
    target = command.get("target_identifier")
    
    if not target:
        return {"success": False, "message": "Veuillez spécifier un utilisateur"}
    
    user = await homeapp_db.get_user_by_login(target)
    
    if user:
        permissions = await homeapp_db.get_user_permissions(target)
        roles = await homeapp_db.get_user_roles(target)
        
        return {
            "success": True,
            "user": user,
            "roles": roles,
            "permissions": permissions
        }
    
    return {"success": False, "message": f"Utilisateur '{target}' non trouvé"}


async def _action_assign_role(command: Dict[str, Any], user_context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Assigner un rôle à un utilisateur"""
    target = command.get("target_identifier")
    role_code = command.get("role_or_permission")
    
    if not target or not role_code:
        return {"success": False, "message": "Utilisateur et rôle requis"}
    
    # Vérifier si le rôle nécessite une approbation
    if role_code.upper() in SENSITIVE_ROLES:
        # Déclencher un workflow d'approbation
        result = await n8n_service.trigger_chatbot_action(
            action_type="assign_role",
            target_user=target,
            role_or_permission=role_code,
            requester=user_context.get("requester") if user_context else "chatbot",
            requires_approval=True
        )
        
        return {
            "success": True,
            "requires_approval": True,
            "workflow_id": result.get("execution_id"),
            "message": f"Le rôle {role_code} est sensible. Une demande d'approbation a été envoyée."
        }
    
    # Assignation directe
    success = await homeapp_db.assign_role(
        user_login=target,
        role_code=role_code.upper(),
        assigned_by="chatbot",
        source="chatbot"
    )
    
    if success:
        await homeapp_db.log_audit_event(
            event_type="role_assigned_via_chatbot",
            action="assign",
            target_type="user_role",
            target_name=f"{target}:{role_code}"
        )
    
    return {
        "success": success,
        "message": f"Rôle {role_code} {'assigné' if success else 'non assigné'} à {target}"
    }


async def _action_remove_role(command: Dict[str, Any]) -> Dict[str, Any]:
    """Retirer un rôle à un utilisateur"""
    target = command.get("target_identifier")
    role_code = command.get("role_or_permission")
    
    if not target or not role_code:
        return {"success": False, "message": "Utilisateur et rôle requis"}
    
    success = await homeapp_db.revoke_role(target, role_code.upper())
    
    if success:
        await homeapp_db.log_audit_event(
            event_type="role_revoked_via_chatbot",
            action="revoke",
            target_type="user_role",
            target_name=f"{target}:{role_code}"
        )
    
    return {
        "success": success,
        "message": f"Rôle {role_code} {'retiré' if success else 'non retiré'} de {target}"
    }


async def _action_assign_permission(command: Dict[str, Any]) -> Dict[str, Any]:
    """Assigner une permission directe"""
    target = command.get("target_identifier")
    permission_code = command.get("role_or_permission")
    
    if not target or not permission_code:
        return {"success": False, "message": "Utilisateur et permission requis"}
    
    success = await homeapp_db.assign_permission(
        user_login=target,
        permission_code=permission_code,
        assigned_by="chatbot"
    )
    
    return {
        "success": success,
        "message": f"Permission {permission_code} {'assignée' if success else 'non assignée'} à {target}"
    }


async def _action_remove_permission(command: Dict[str, Any]) -> Dict[str, Any]:
    """Retirer une permission directe"""
    target = command.get("target_identifier")
    permission_code = command.get("role_or_permission")
    
    if not target or not permission_code:
        return {"success": False, "message": "Utilisateur et permission requis"}
    
    success = await homeapp_db.revoke_permission(target, permission_code)
    
    return {
        "success": success,
        "message": f"Permission {permission_code} {'retirée' if success else 'non retirée'} de {target}"
    }


async def _action_list_roles() -> Dict[str, Any]:
    """Lister les rôles disponibles"""
    roles = [
        {"code": "USER", "name": "Utilisateur standard", "sensitive": False},
        {"code": "AGENT_COMMERCIAL", "name": "Agent Commercial", "sensitive": False},
        {"code": "COMMERCIAL_MANAGER", "name": "Responsable Commercial", "sensitive": False},
        {"code": "RH_ASSISTANT", "name": "Assistant RH", "sensitive": False},
        {"code": "RH_MANAGER", "name": "Responsable RH", "sensitive": True},
        {"code": "COMPTABLE", "name": "Comptable", "sensitive": False},
        {"code": "FINANCE_MANAGER", "name": "Responsable Finance", "sensitive": True},
        {"code": "IT_SUPPORT", "name": "Support IT", "sensitive": False},
        {"code": "IT_ADMIN", "name": "Administrateur IT", "sensitive": True},
        {"code": "MANAGER", "name": "Manager", "sensitive": False},
        {"code": "DIRECTOR", "name": "Directeur", "sensitive": True}
    ]
    
    return {
        "success": True,
        "roles": roles,
        "count": len(roles)
    }


async def _action_list_user_permissions(command: Dict[str, Any]) -> Dict[str, Any]:
    """Lister les permissions d'un utilisateur"""
    target = command.get("target_identifier")
    
    if not target:
        return {"success": False, "message": "Veuillez spécifier un utilisateur"}
    
    permissions = await homeapp_db.get_user_permissions(target)
    roles = await homeapp_db.get_user_roles(target)
    
    return {
        "success": True,
        "user_login": target,
        "roles": roles,
        "permissions": permissions,
        "message": f"{target} possède {len(roles)} rôle(s) et {len(permissions)} permission(s)"
    }


async def _generate_response(original_message: str, command: Dict[str, Any], result: Dict[str, Any]) -> str:
    """Générer une réponse en langage naturel"""
    
    # Si le résultat contient déjà un message explicite
    if result.get("message"):
        base_message = result["message"]
    else:
        base_message = "Opération effectuée."
    
    # Enrichir la réponse selon le contexte
    action = command.get("action")
    
    if action == "search_user" and result.get("users"):
        users = result["users"]
        if len(users) == 1:
            u = users[0]
            return f"J'ai trouvé {u.get('full_name', u.get('login'))} ({u.get('email')}), département {u.get('department', 'non spécifié')}."
        elif len(users) > 1:
            names = [u.get('full_name', u.get('login')) for u in users[:5]]
            return f"J'ai trouvé {len(users)} utilisateurs: {', '.join(names)}{'...' if len(users) > 5 else ''}."
        else:
            return "Aucun utilisateur trouvé correspondant à votre recherche."
    
    elif action == "get_user_info" and result.get("user"):
        user = result["user"]
        roles = result.get("roles", [])
        return f"**{user.get('full_name', user.get('login'))}**\n" \
               f"- Email: {user.get('email')}\n" \
               f"- Département: {user.get('department', 'Non spécifié')}\n" \
               f"- Poste: {user.get('job_title', 'Non spécifié')}\n" \
               f"- Rôles: {', '.join(roles) if roles else 'Aucun'}\n" \
               f"- Statut: {'Actif' if user.get('is_active') else 'Inactif'}"
    
    elif action == "list_roles" and result.get("roles"):
        roles_text = "\n".join([
            f"- **{r['code']}**: {r['name']}" + (" ⚠️" if r.get('sensitive') else "")
            for r in result["roles"]
        ])
        return f"Voici les rôles disponibles:\n{roles_text}\n\n⚠️ = nécessite une approbation"
    
    elif result.get("requires_approval"):
        return f"⏳ {base_message}\nUn responsable doit valider cette demande."
    
    elif result.get("success"):
        return f"✅ {base_message}"
    
    else:
        return f"❌ {base_message}"


# === Endpoint de test direct (sans LLM) ===

@router.post("/direct-action", summary="Exécuter une action directement (test)")
async def direct_action(
    action: str,
    target_identifier: Optional[str] = None,
    role_or_permission: Optional[str] = None,
    filters: Optional[Dict[str, Any]] = None
):
    """
    Exécuter une action IAM directement sans passer par le LLM.
    Utile pour les tests et le débogage.
    """
    command = {
        "action": action,
        "target_identifier": target_identifier,
        "role_or_permission": role_or_permission,
        "target_filters": filters,
        "confidence": 1.0
    }
    
    result = await _execute_action(command, None)
    return result








