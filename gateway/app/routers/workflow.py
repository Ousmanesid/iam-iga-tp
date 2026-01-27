"""
Router pour les endpoints de workflows N8N
Gère les déclenchements et le suivi des workflows d'approbation
"""

from fastapi import APIRouter, HTTPException
import structlog

from ..services.n8n import n8n_service
from ..services.midpoint import midpoint_service

logger = structlog.get_logger()
router = APIRouter(prefix="/workflow", tags=["Workflows"])


@router.get("/status", summary="Statut du service workflows")
async def get_status():
    """
    Vérifier que le service de workflows est actif.
    """
    return {
        "service": "workflows",
        "status": "active",
        "message": "Service de workflows N8N actif"
    }


@router.post("/trigger/{workflow_name}", summary="Déclencher un workflow")
async def trigger_workflow(workflow_name: str):
    """
    Déclencher un workflow N8N par son nom.
    """
    try:
        logger.info(f"Déclenchement du workflow: {workflow_name}")
        # À implémenter : appel à N8N
        return {
            "status": "success",
            "workflow": workflow_name,
            "message": "Workflow déclenché (à implémenter)"
        }
    except Exception as e:
        logger.error(f"Erreur lors du déclenchement du workflow {workflow_name}", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
