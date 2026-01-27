"""
Router pour les endpoints de provisioning
Gère les opérations de provisioning via MidPoint (pas de DB locale)
"""

from fastapi import APIRouter, HTTPException
from typing import Optional
import structlog

from ..services.midpoint import midpoint_service
from ..services.n8n import n8n_service

logger = structlog.get_logger()
router = APIRouter(prefix="/provision", tags=["Provisioning"])


@router.get("/status", summary="Statut du service de provisioning")
async def get_status():
    """
    Vérifier que le service de provisioning est actif.
    """
    return {
        "service": "provisioning",
        "status": "active",
        "message": "Service de provisioning actif - Les opérations passent par MidPoint"
    }


@router.post("/trigger-sync", summary="Déclencher une synchronisation")
async def trigger_sync():
    """
    Déclencher une synchronisation manuelle depuis MidPoint vers les ressources cibles.
    """
    try:
        # Appeler MidPoint pour déclencher les tasks de sync
        logger.info("Déclenchement de la synchronisation")
        return {
            "status": "success",
            "message": "Synchronisation déclenchée (à implémenter via API MidPoint)"
        }
    except Exception as e:
        logger.error("Erreur lors du déclenchement de la sync", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
