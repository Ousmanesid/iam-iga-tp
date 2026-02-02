"""
Routes API pour les notifications
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr
from typing import List, Optional
import logging

from ..services.notification_service import get_notification_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/notifications", tags=["Notifications"])


class TestNotificationRequest(BaseModel):
    """Requête pour tester l'envoi d'une notification"""
    user_email: EmailStr
    user_name: str
    apps: Optional[List[dict]] = None


@router.post("/test")
async def test_notification(request: TestNotificationRequest):
    """
    Envoie une notification de test
    
    Utile pour vérifier la configuration SMTP
    """
    try:
        notification_service = get_notification_service()
        
        # Apps de test si non fourni
        apps = request.apps or [
            {
                'name': 'Keycloak SSO',
                'url': 'http://localhost:8180',
                'username': request.user_email,
                'role': 'Développeur',
                'permissions': 'Accès complet API',
                'temporary_password': 'Test123!'
            },
            {
                'name': 'GitLab',
                'url': 'http://localhost:8080/gitlab',
                'username': request.user_email,
                'role': 'Developer',
                'permissions': 'Repository access'
            }
        ]
        
        success = notification_service.send_provisioning_notification(
            user_email=request.user_email,
            user_name=request.user_name,
            provisioned_apps=apps,
            operation_id="TEST-12345"
        )
        
        if success:
            return {
                "status": "success",
                "message": f"Notification envoyée à {request.user_email}",
                "smtp_enabled": notification_service.enabled,
                "note": "En mode dev, vérifiez /tmp/notification_*.txt" if not notification_service.enabled else None
            }
        else:
            raise HTTPException(status_code=500, detail="Échec de l'envoi")
            
    except Exception as e:
        logger.error(f"Erreur test notification: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status")
async def get_notification_status():
    """
    Vérifie l'état du service de notification
    """
    notification_service = get_notification_service()
    
    return {
        "enabled": notification_service.enabled,
        "smtp_configured": bool(notification_service.smtp_config.get('host')),
        "smtp_host": notification_service.smtp_config.get('host', 'Not configured'),
        "mode": "Production (SMTP)" if notification_service.enabled else "Développement (fichiers /tmp)"
    }
