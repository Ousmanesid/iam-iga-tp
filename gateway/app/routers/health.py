"""
Routes de santé et monitoring
"""
from fastapi import APIRouter
from pydantic import BaseModel
from datetime import datetime

from ..services.odoo_service import get_odoo_service
from ..services.midpoint_service import get_midpoint_service

router = APIRouter(tags=["Health"])


class HealthCheck(BaseModel):
    status: str
    timestamp: str
    services: dict


@router.get("/health", response_model=HealthCheck)
async def health_check():
    """
    Health check complet de la gateway et ses dépendances
    """
    odoo = get_odoo_service()
    midpoint = get_midpoint_service()
    
    odoo_ok = odoo.connect()
    midpoint_ok = midpoint.test_connection()
    
    all_ok = odoo_ok and midpoint_ok
    
    return HealthCheck(
        status="healthy" if all_ok else "degraded",
        timestamp=datetime.now().isoformat(),
        services={
            "aegis_gateway": "up",
            "odoo": "up" if odoo_ok else "down",
            "midpoint": "up" if midpoint_ok else "down"
        }
    )


@router.get("/ready")
async def readiness():
    """
    Readiness probe pour Kubernetes/Docker
    """
    return {"ready": True}


@router.get("/live")
async def liveness():
    """
    Liveness probe pour Kubernetes/Docker
    """
    return {"alive": True}
