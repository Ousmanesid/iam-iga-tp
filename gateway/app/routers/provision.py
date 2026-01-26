"""
Router pour les endpoints de provisioning
Gère les opérations CRUD sur les utilisateurs, rôles et permissions de Home App
"""

from fastapi import APIRouter, HTTPException, Query, Depends
from typing import Optional, List
from uuid import UUID
import structlog
import hashlib

from ..models.user import (
    UserCreate, UserUpdate, UserResponse,
    RoleAssignment, PermissionAssignment, UserPermissions
)
from ..services.homeapp_db import homeapp_db
from ..services.n8n import n8n_service

logger = structlog.get_logger()
router = APIRouter(prefix="/provision", tags=["Provisioning"])


# === Endpoints Utilisateurs ===

@router.post("/users", response_model=dict, summary="Créer un utilisateur")
async def create_user(user: UserCreate):
    """
    Créer un nouvel utilisateur dans Home App.
    
    Cette opération:
    - Crée le compte dans PostgreSQL
    - Peut déclencher un workflow post-provisioning si configuré
    """
    try:
        password_hash = None
        if user.password:
            password_hash = hashlib.sha256(user.password.encode("utf-8")).hexdigest()

        user_id = await homeapp_db.create_user(
            login=user.login,
            email=user.email,
            password_hash=password_hash,
            first_name=user.first_name,
            last_name=user.last_name,
            department=user.department,
            job_title=user.job_title,
            employee_number=user.employee_number,
            is_active=user.is_active,
            midpoint_oid=user.midpoint_oid,
            attributes=user.attributes
        )
        
        # Log audit
        await homeapp_db.log_audit_event(
            event_type="user_created",
            action="create",
            target_type="user",
            target_id=user_id,
            target_name=user.login,
            new_value=user.model_dump()
        )

        for role_code in user.roles:
            await homeapp_db.assign_role(
                user_login=user.login,
                role_code=role_code,
                assigned_by="gateway",
                source="workflow"
            )

        for permission_code in user.permissions:
            await homeapp_db.assign_permission(
                user_login=user.login,
                permission_code=permission_code,
                assigned_by="gateway",
                reason="auto_assign_on_create"
            )
        
        return {
            "success": True,
            "user_id": str(user_id),
            "login": user.login,
            "message": f"Utilisateur {user.login} créé avec succès"
        }
    
    except Exception as e:
        logger.error("Failed to create user", login=user.login, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/users/{login}", summary="Obtenir un utilisateur")
async def get_user(login: str):
    """Récupérer les informations d'un utilisateur par son login"""
    user = await homeapp_db.get_user_by_login(login)
    
    if not user:
        raise HTTPException(status_code=404, detail=f"Utilisateur {login} non trouvé")
    
    return user


@router.get("/users", summary="Rechercher des utilisateurs")
async def search_users(
    department: Optional[str] = Query(None, description="Filtrer par département"),
    job_title: Optional[str] = Query(None, description="Filtrer par poste"),
    is_active: Optional[bool] = Query(None, description="Filtrer par statut actif"),
    q: Optional[str] = Query(None, description="Recherche textuelle"),
    limit: int = Query(100, ge=1, le=500)
):
    """Rechercher des utilisateurs avec filtres"""
    users = await homeapp_db.search_users(
        department=department,
        job_title=job_title,
        is_active=is_active,
        search_term=q,
        limit=limit
    )
    
    return {
        "count": len(users),
        "users": users
    }


@router.patch("/users/{login}", summary="Mettre à jour un utilisateur")
async def update_user(login: str, updates: UserUpdate):
    """Mettre à jour les informations d'un utilisateur"""
    # Récupérer l'état actuel pour l'audit
    old_user = await homeapp_db.get_user_by_login(login)
    if not old_user:
        raise HTTPException(status_code=404, detail=f"Utilisateur {login} non trouvé")
    
    # Filtrer les champs non-null
    update_data = {k: v for k, v in updates.model_dump().items() if v is not None}
    
    if not update_data:
        return {"success": True, "message": "Aucune modification"}
    
    success = await homeapp_db.update_user(login, update_data)
    
    if success:
        await homeapp_db.log_audit_event(
            event_type="user_updated",
            action="update",
            target_type="user",
            target_name=login,
            old_value=dict(old_user),
            new_value=update_data
        )
    
    return {
        "success": success,
        "login": login,
        "updated_fields": list(update_data.keys())
    }


@router.post("/users/{login}/disable", summary="Désactiver un utilisateur")
async def disable_user(login: str):
    """Désactiver un compte utilisateur"""
    success = await homeapp_db.disable_user(login)
    
    if not success:
        raise HTTPException(status_code=404, detail=f"Utilisateur {login} non trouvé")
    
    await homeapp_db.log_audit_event(
        event_type="user_disabled",
        action="disable",
        target_type="user",
        target_name=login
    )
    
    return {"success": True, "login": login, "message": "Utilisateur désactivé"}


@router.post("/users/{login}/enable", summary="Activer un utilisateur")
async def enable_user(login: str):
    """Activer un compte utilisateur"""
    success = await homeapp_db.enable_user(login)
    
    if not success:
        raise HTTPException(status_code=404, detail=f"Utilisateur {login} non trouvé")
    
    await homeapp_db.log_audit_event(
        event_type="user_enabled",
        action="enable",
        target_type="user",
        target_name=login
    )
    
    return {"success": True, "login": login, "message": "Utilisateur activé"}


@router.delete("/users/{login}", summary="Supprimer un utilisateur")
async def delete_user(login: str):
    """Supprimer un utilisateur"""
    # Récupérer les infos avant suppression pour l'audit
    old_user = await homeapp_db.get_user_by_login(login)
    
    success = await homeapp_db.delete_user(login)
    
    if not success:
        raise HTTPException(status_code=404, detail=f"Utilisateur {login} non trouvé")
    
    await homeapp_db.log_audit_event(
        event_type="user_deleted",
        action="delete",
        target_type="user",
        target_name=login,
        old_value=dict(old_user) if old_user else None
    )
    
    return {"success": True, "login": login, "message": "Utilisateur supprimé"}


# === Endpoints Rôles ===

@router.post("/roles/assign", summary="Assigner un rôle")
async def assign_role(assignment: RoleAssignment):
    """
    Assigner un rôle à un utilisateur.
    
    Les rôles disponibles: USER, AGENT_COMMERCIAL, RH_MANAGER, IT_ADMIN, etc.
    """
    success = await homeapp_db.assign_role(
        user_login=assignment.user_login,
        role_code=assignment.role_code,
        assigned_by=assignment.assigned_by,
        source=assignment.source,
        valid_until=assignment.valid_until
    )
    
    if not success:
        raise HTTPException(
            status_code=400,
            detail=f"Impossible d'assigner le rôle {assignment.role_code} à {assignment.user_login}"
        )
    
    await homeapp_db.log_audit_event(
        event_type="role_assigned",
        action="assign",
        target_type="user_role",
        target_name=f"{assignment.user_login}:{assignment.role_code}",
        new_value=assignment.model_dump()
    )
    
    return {
        "success": True,
        "user_login": assignment.user_login,
        "role_code": assignment.role_code,
        "message": f"Rôle {assignment.role_code} assigné à {assignment.user_login}"
    }


@router.post("/roles/revoke", summary="Révoquer un rôle")
async def revoke_role(user_login: str, role_code: str):
    """Révoquer un rôle d'un utilisateur"""
    success = await homeapp_db.revoke_role(user_login, role_code)
    
    if not success:
        raise HTTPException(
            status_code=400,
            detail=f"Impossible de révoquer le rôle {role_code} de {user_login}"
        )
    
    await homeapp_db.log_audit_event(
        event_type="role_revoked",
        action="revoke",
        target_type="user_role",
        target_name=f"{user_login}:{role_code}"
    )
    
    return {
        "success": True,
        "user_login": user_login,
        "role_code": role_code,
        "message": f"Rôle {role_code} révoqué de {user_login}"
    }


@router.get("/users/{login}/roles", summary="Obtenir les rôles d'un utilisateur")
async def get_user_roles(login: str):
    """Lister les rôles d'un utilisateur"""
    roles = await homeapp_db.get_user_roles(login)
    
    return {
        "user_login": login,
        "roles": roles,
        "count": len(roles)
    }


# === Endpoints Permissions ===

@router.post("/permissions/assign", summary="Assigner une permission directe")
async def assign_permission(assignment: PermissionAssignment):
    """Assigner une permission directe à un utilisateur (bypass des rôles)"""
    success = await homeapp_db.assign_permission(
        user_login=assignment.user_login,
        permission_code=assignment.permission_code,
        assigned_by=assignment.assigned_by,
        reason=assignment.reason,
        valid_until=assignment.valid_until
    )
    
    if not success:
        raise HTTPException(
            status_code=400,
            detail=f"Impossible d'assigner la permission {assignment.permission_code}"
        )
    
    await homeapp_db.log_audit_event(
        event_type="permission_assigned",
        action="assign",
        target_type="user_permission",
        target_name=f"{assignment.user_login}:{assignment.permission_code}",
        new_value=assignment.model_dump()
    )
    
    return {
        "success": True,
        "user_login": assignment.user_login,
        "permission_code": assignment.permission_code,
        "message": f"Permission {assignment.permission_code} assignée"
    }


@router.post("/permissions/revoke", summary="Révoquer une permission directe")
async def revoke_permission(user_login: str, permission_code: str):
    """Révoquer une permission directe"""
    success = await homeapp_db.revoke_permission(user_login, permission_code)
    
    if not success:
        raise HTTPException(
            status_code=400,
            detail=f"Impossible de révoquer la permission {permission_code}"
        )
    
    return {
        "success": True,
        "user_login": user_login,
        "permission_code": permission_code,
        "message": f"Permission {permission_code} révoquée"
    }


@router.get("/users/{login}/permissions", response_model=UserPermissions, summary="Obtenir les permissions effectives")
async def get_user_permissions(login: str):
    """
    Obtenir toutes les permissions effectives d'un utilisateur.
    Inclut les permissions via les rôles ET les permissions directes.
    """
    permissions = await homeapp_db.get_user_permissions(login)
    
    return UserPermissions(
        user_login=login,
        permissions=permissions
    )


@router.get("/users/{login}/has-permission/{permission_code}", summary="Vérifier une permission")
async def check_user_permission(login: str, permission_code: str):
    """Vérifier si un utilisateur possède une permission spécifique"""
    has_permission = await homeapp_db.user_has_permission(login, permission_code)
    
    return {
        "user_login": login,
        "permission_code": permission_code,
        "has_permission": has_permission
    }


# === Endpoints Sync Odoo ===

@router.post("/sync/odoo", summary="Synchroniser les employés Odoo vers HomeApp")
async def sync_odoo_employees():
    """
    Synchronise tous les employés Odoo vers HomeApp.
    
    - Crée les utilisateurs qui n'existent pas
    - Met à jour les existants
    - Assigne automatiquement les rôles selon le département
    """
    from ..services.odoo import odoo_service, get_roles_for_department
    
    # Récupérer les employés Odoo
    employees = odoo_service.get_employees()
    
    if not employees:
        return {
            "success": False,
            "message": "Aucun employé trouvé ou erreur de connexion Odoo",
            "stats": {"created": 0, "updated": 0, "errors": 0}
        }
    
    stats = {"created": 0, "updated": 0, "errors": 0, "skipped": 0}
    details = []
    
    for emp in employees:
        email = emp.get('email')
        if not email:
            stats['skipped'] += 1
            continue
        
        # Générer le login depuis le nom
        first_name = emp.get('first_name', '')
        last_name = emp.get('last_name', '')
        login = f"{first_name.lower()}.{last_name.lower()}".replace(' ', '') if first_name and last_name else email.split('@')[0]
        
        try:
            # Vérifier si l'utilisateur existe
            existing = await homeapp_db.get_user_by_login(login)
            
            # Déterminer les rôles selon le département
            department = emp.get('department', '')
            roles = get_roles_for_department(department)
            
            if existing:
                # Mise à jour
                await homeapp_db.update_user(login, {
                    'email': email,
                    'first_name': first_name,
                    'last_name': last_name,
                    'department': department,
                    'job_title': emp.get('job_title'),
                    'is_active': emp.get('active', True)
                })
                stats['updated'] += 1
                action = 'updated'
            else:
                # Création
                password_hash = hashlib.sha256(f"Temp{login}123".encode()).hexdigest()
                
                await homeapp_db.create_user(
                    login=login,
                    email=email,
                    password_hash=password_hash,
                    first_name=first_name,
                    last_name=last_name,
                    department=department,
                    job_title=emp.get('job_title'),
                    employee_number=emp.get('employee_id'),
                    is_active=emp.get('active', True)
                )
                stats['created'] += 1
                action = 'created'
            
            # Assigner les rôles
            for role_code in roles:
                await homeapp_db.assign_role(
                    user_login=login,
                    role_code=role_code,
                    assigned_by="odoo_sync",
                    source="odoo"
                )
            
            details.append({
                "login": login,
                "action": action,
                "roles": roles
            })
            
        except Exception as e:
            logger.error("Sync error for employee", email=email, error=str(e))
            stats['errors'] += 1
            details.append({
                "login": login,
                "action": "error",
                "error": str(e)
            })
    
    return {
        "success": True,
        "message": f"Sync terminée: {stats['created']} créés, {stats['updated']} mis à jour, {stats['errors']} erreurs",
        "stats": stats,
        "details": details[:20]  # Limiter les détails
    }


@router.get("/odoo/employees", summary="Lister les employés Odoo")
async def list_odoo_employees():
    """Liste les employés depuis Odoo (lecture seule)"""
    from ..services.odoo import odoo_service, get_roles_for_department
    
    employees = odoo_service.get_employees()
    
    # Enrichir avec les rôles calculés
    for emp in employees:
        emp['calculated_roles'] = get_roles_for_department(emp.get('department', ''))
    
    return {
        "count": len(employees),
        "employees": employees
    }








