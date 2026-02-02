"""
Routes API pour la gestion des rôles MidPoint
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import logging

from ..services.midpoint_role_service import get_role_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/roles", tags=["Roles"])


class RoleResponse(BaseModel):
    """Réponse pour un rôle"""
    id: str
    oid: str
    name: str
    displayName: str
    description: str
    riskLevel: str
    requestable: bool
    source: str
    memberCount: Optional[int] = 0


class RoleMember(BaseModel):
    """Membre d'un rôle"""
    oid: str
    name: str
    email: str


class AssignRoleRequest(BaseModel):
    """Requête d'assignation de rôle"""
    user_oid: str
    role_oid: str


# Rôles par défaut si MidPoint non disponible
DEFAULT_ROLES = [
    {
        "id": "00000000-0000-0000-0000-000000000104",
        "oid": "00000000-0000-0000-0000-000000000104",
        "name": "Employee",
        "displayName": "Employé - Accès de base",
        "description": "Rôle de base pour tous les employés. Compte LDAP + groupes de base + Odoo utilisateur.",
        "riskLevel": "low",
        "requestable": True,
        "source": "midpoint",
        "memberCount": 156,
        "permissions": ["Compte LDAP", "Groupe Employee", "Groupe Internet", "Groupe Printer", "SharePoint", "Odoo User"]
    },
    {
        "id": "00000000-0000-0000-0000-000000000105",
        "oid": "00000000-0000-0000-0000-000000000105",
        "name": "IT_Admin",
        "displayName": "Administrateur IT",
        "description": "Accès administrateur complet aux systèmes IT.",
        "riskLevel": "high",
        "requestable": False,
        "source": "midpoint",
        "memberCount": 5,
        "permissions": ["Tous droits Employee", "Admin LDAP", "Admin Odoo", "Config système", "Logs audit"]
    },
    {
        "id": "00000000-0000-0000-0000-000000000106",
        "oid": "00000000-0000-0000-0000-000000000106",
        "name": "RH_Manager",
        "displayName": "Manager RH",
        "description": "Gestion des ressources humaines dans Odoo.",
        "riskLevel": "medium",
        "requestable": True,
        "source": "midpoint",
        "memberCount": 8,
        "permissions": ["Tous droits Employee", "Module RH Odoo", "Recrutement", "Formation", "Documents confidentiels RH"]
    },
    {
        "id": "00000000-0000-0000-0000-000000000107",
        "oid": "00000000-0000-0000-0000-000000000107",
        "name": "Agent_Commercial",
        "displayName": "Agent Commercial",
        "description": "Accès CRM et outils commerciaux Odoo.",
        "riskLevel": "low",
        "requestable": True,
        "source": "midpoint",
        "memberCount": 32,
        "permissions": ["Tous droits Employee", "CRM Odoo", "Gestion leads", "Contrats", "Reporting commercial"]
    },
    {
        "id": "00000000-0000-0000-0000-000000000108",
        "oid": "00000000-0000-0000-0000-000000000108",
        "name": "Comptable",
        "displayName": "Comptable",
        "description": "Accès aux modules financiers Odoo.",
        "riskLevel": "medium",
        "requestable": True,
        "source": "midpoint",
        "memberCount": 12,
        "permissions": ["Tous droits Employee", "Odoo Finance", "Facturation", "Comptabilité", "Rapports financiers"]
    },
    {
        "id": "00000000-0000-0000-0000-000000000109",
        "oid": "00000000-0000-0000-0000-000000000109",
        "name": "Developer",
        "displayName": "Développeur",
        "description": "Accès aux outils de développement.",
        "riskLevel": "medium",
        "requestable": True,
        "source": "midpoint",
        "memberCount": 18,
        "permissions": ["Tous droits Employee", "Git/GitLab", "Serveurs DEV", "CI/CD", "API Documentation", "Logs serveur"]
    }
]


@router.get("", response_model=List[dict])
async def list_roles():
    """
    Liste tous les rôles disponibles.
    
    Tente de récupérer depuis MidPoint, sinon retourne les rôles par défaut.
    """
    try:
        service = get_role_service()
        roles = service.get_all_roles()
        
        if roles:
            # Enrichir avec le nombre de membres
            for role in roles:
                members = service.get_role_members(role.get('oid', ''))
                role['memberCount'] = len(members)
            
            logger.info(f"Récupéré {len(roles)} rôles depuis MidPoint")
            return roles
        else:
            logger.warning("MidPoint non disponible, utilisation des rôles par défaut")
            return DEFAULT_ROLES
            
    except Exception as e:
        logger.error(f"Erreur récupération rôles: {e}")
        return DEFAULT_ROLES


@router.get("/{role_oid}")
async def get_role(role_oid: str):
    """Récupère un rôle par son OID"""
    try:
        service = get_role_service()
        role = service.get_role_by_oid(role_oid)
        
        if role:
            members = service.get_role_members(role_oid)
            role['memberCount'] = len(members)
            role['members'] = members
            return role
        
        # Fallback sur les rôles par défaut
        for default_role in DEFAULT_ROLES:
            if default_role['oid'] == role_oid:
                return default_role
        
        raise HTTPException(status_code=404, detail="Rôle non trouvé")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur récupération rôle: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{role_oid}/members", response_model=List[RoleMember])
async def get_role_members(role_oid: str):
    """Récupère les membres d'un rôle"""
    try:
        service = get_role_service()
        members = service.get_role_members(role_oid)
        return members
        
    except Exception as e:
        logger.error(f"Erreur récupération membres: {e}")
        return []


@router.post("/assign")
async def assign_role(request: AssignRoleRequest):
    """Assigne un rôle à un utilisateur"""
    try:
        service = get_role_service()
        success = service.assign_role_to_user(request.user_oid, request.role_oid)
        
        if success:
            return {
                "status": "success",
                "message": f"Rôle {request.role_oid} assigné à l'utilisateur {request.user_oid}"
            }
        else:
            raise HTTPException(status_code=500, detail="Échec de l'assignation")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur assignation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/unassign")
async def unassign_role(request: AssignRoleRequest):
    """Retire un rôle d'un utilisateur"""
    try:
        service = get_role_service()
        success = service.unassign_role_from_user(request.user_oid, request.role_oid)
        
        if success:
            return {
                "status": "success",
                "message": f"Rôle {request.role_oid} retiré de l'utilisateur {request.user_oid}"
            }
        else:
            raise HTTPException(status_code=500, detail="Échec du retrait")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur retrait: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/permissions/all")
async def get_all_permissions():
    """
    Retourne toutes les permissions/inducements possibles.
    Ces permissions correspondent aux inducements MidPoint.
    """
    permissions = [
        # LDAP
        {"id": "ldap_account", "name": "Compte LDAP", "category": "LDAP", "description": "Compte utilisateur LDAP de base"},
        {"id": "ldap_employee", "name": "Groupe Employee", "category": "LDAP", "description": "Appartenance au groupe Employee"},
        {"id": "ldap_internet", "name": "Groupe Internet", "category": "LDAP", "description": "Accès Internet via proxy"},
        {"id": "ldap_printer", "name": "Groupe Printer", "category": "LDAP", "description": "Accès aux imprimantes réseau"},
        {"id": "ldap_sharepoint", "name": "SharePoint", "category": "LDAP", "description": "Accès aux dossiers partagés SharePoint"},
        {"id": "ldap_admin", "name": "Admin LDAP", "category": "LDAP", "description": "Droits administrateur LDAP"},
        
        # Odoo
        {"id": "odoo_user", "name": "Odoo User", "category": "Odoo", "description": "Compte utilisateur Odoo standard"},
        {"id": "odoo_hr", "name": "Module RH Odoo", "category": "Odoo", "description": "Accès au module Ressources Humaines"},
        {"id": "odoo_crm", "name": "CRM Odoo", "category": "Odoo", "description": "Accès au module CRM"},
        {"id": "odoo_finance", "name": "Odoo Finance", "category": "Odoo", "description": "Accès aux modules financiers"},
        {"id": "odoo_admin", "name": "Admin Odoo", "category": "Odoo", "description": "Droits administrateur Odoo"},
        
        # Développement
        {"id": "git", "name": "Git/GitLab", "category": "Dev", "description": "Accès aux dépôts Git"},
        {"id": "dev_servers", "name": "Serveurs DEV", "category": "Dev", "description": "Accès aux serveurs de développement"},
        {"id": "cicd", "name": "CI/CD", "category": "Dev", "description": "Pipelines CI/CD"},
        {"id": "api_docs", "name": "API Documentation", "category": "Dev", "description": "Documentation API interne"},
        {"id": "prod_deploy", "name": "Déploiement PROD", "category": "Dev", "description": "Droits de déploiement production"},
        
        # Admin
        {"id": "audit_logs", "name": "Logs audit", "category": "Admin", "description": "Consultation des logs d'audit"},
        {"id": "sys_config", "name": "Config système", "category": "Admin", "description": "Configuration système"},
        {"id": "user_mgmt", "name": "Gestion utilisateurs", "category": "Admin", "description": "Création/modification utilisateurs"},
        {"id": "role_mgmt", "name": "Gestion rôles", "category": "Admin", "description": "Création/modification rôles"},
    ]
    
    return permissions


@router.post("/refresh")
async def refresh_roles_from_midpoint():
    """
    Force le rechargement des rôles depuis MidPoint.
    Vide le cache et récupère les rôles à jour.
    """
    try:
        # Vider le cache du role_mapper
        from ..core.role_mapper import clear_roles_cache
        clear_roles_cache()
        
        # Récupérer les nouveaux rôles
        service = get_role_service()
        roles = service.get_all_roles()
        
        logger.info(f"Rôles rechargés depuis MidPoint: {len(roles)} rôles")
        
        return {
            "status": "success",
            "message": "Rôles rechargés depuis MidPoint",
            "count": len(roles),
            "source": "midpoint",
            "roles": [{"oid": r.get("oid"), "name": r.get("name")} for r in roles]
        }
        
    except Exception as e:
        logger.error(f"Erreur refresh rôles: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Impossible de recharger les rôles depuis MidPoint: {str(e)}"
        )
