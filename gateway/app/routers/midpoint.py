"""
Routes API pour MidPoint
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Dict
from sqlalchemy.orm import Session
import logging

from ..services.midpoint_service import get_midpoint_service
from ..services.provisioning_service import ProvisioningService
from ..database.connection import get_db

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/midpoint", tags=["MidPoint"])


class ProvisionFromMidPointRequest(BaseModel):
    """Requête pour provisionner depuis MidPoint"""
    user_oid: str
    applications: List[str] = []  # Liste des apps à provisionner (vide = toutes)


@router.get("/applications")
async def get_available_applications():
    """
    Récupère la liste des applications métiers disponibles pour le provisioning.
    """
    from ..core.role_mapper import get_all_applications
    
    try:
        applications = get_all_applications()
        return {
            "status": "success",
            "applications": applications
        }
    except Exception as e:
        logger.error(f"Erreur récupération applications: {e}")
        # Retour par défaut si erreur
        return {
            "status": "success",
            "applications": [
                {"name": "Keycloak", "description": "SSO et authentification"},
                {"name": "LDAP", "description": "Annuaire d'entreprise"},
                {"name": "Odoo", "description": "ERP - Applications métiers"},
            ]
        }


@router.get("/users")
async def get_midpoint_users():
    """
    Récupère tous les utilisateurs de MidPoint.
    
    Ces utilisateurs peuvent être provisionnés vers les applications métiers.
    """
    try:
        service = get_midpoint_service()
        users = service.get_all_users()
        
        return {
            "status": "success",
            "count": len(users),
            "users": users
        }
        
    except Exception as e:
        logger.error(f"Erreur récupération utilisateurs MidPoint: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de la récupération des utilisateurs: {str(e)}"
        )


@router.post("/provision")
async def provision_from_midpoint(
    request: ProvisionFromMidPointRequest,
    db: Session = Depends(get_db)
):
    """
    Provisionne un utilisateur MidPoint vers les applications métiers.
    
    L'utilisateur doit déjà exister dans MidPoint avec ses informations complètes.
    """
    try:
        # Récupérer l'utilisateur depuis MidPoint
        midpoint_service = get_midpoint_service()
        
        # Pour l'instant, on récupère tous les users et on filtre
        all_users = midpoint_service.get_all_users()
        user = next((u for u in all_users if u['oid'] == request.user_oid), None)
        
        if not user:
            raise HTTPException(
                status_code=404,
                detail=f"Utilisateur {request.user_oid} introuvable dans MidPoint"
            )
        
        # Préparer les données pour le provisioning
        # Déterminer le job_title (title, fullName ou role par défaut)
        job_title = user.get('title') or user.get('fullName') or 'Employee'
        if not job_title or job_title.strip() == '':
            job_title = 'Employee'
        
        user_data = {
            "email": user.get('email') or f"{user['name']}@company.local",
            "first_name": user.get('givenName', user['name']),
            "last_name": user.get('familyName', user['name']),
            "job_title": job_title,
            "department": user.get('department', 'General'),
        }
        
        # Provisionner via le service avec session DB
        provisioning_service = ProvisioningService(db)
        operation = provisioning_service.provision_user(
            user_data=user_data,
            trigger="midpoint",
            dry_run=False,
            selected_applications=request.applications if request.applications else None
        )
        
        return {
            "status": "success",
            "message": f"Utilisateur {user['name']} provisionné avec succès",
            "user_oid": request.user_oid,
            "user_email": user_data['email'],
            "operation_id": operation.id,
            "total_actions": operation.total_actions,
            "successful_actions": operation.successful_actions,
            "failed_actions": operation.failed_actions
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur provisioning depuis MidPoint: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors du provisioning: {str(e)}"
        )


@router.get("/health")
async def check_midpoint_health():
    """Vérifie la connexion à MidPoint"""
    try:
        service = get_midpoint_service()
        is_connected = service.test_connection()
        
        return {
            "status": "healthy" if is_connected else "unhealthy",
            "connected": is_connected,
            "url": service.url
        }
        
    except Exception as e:
        return {
            "status": "unhealthy",
            "connected": False,
            "error": str(e)
        }
