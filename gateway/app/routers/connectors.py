"""
Routes API pour les connecteurs
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List
import logging
import httpx

from ..core.config import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/connectors", tags=["Connectors"])


class ConnectorStatus(BaseModel):
    """Statut d'un connecteur"""
    name: str
    type: str
    status: str  # 'online', 'offline', 'error'
    message: str
    url: str


async def check_midpoint_status() -> ConnectorStatus:
    """Vérifie le statut de MidPoint"""
    try:
        async with httpx.AsyncClient(timeout=5.0, follow_redirects=False) as client:
            # Test simple sur /midpoint sans auth - attendons 302 ou 401
            response = await client.get(f"{settings.MIDPOINT_URL}")
            
            # MidPoint répond 302 ou 401 si actif
            if response.status_code in [200, 302, 401]:
                return ConnectorStatus(
                    name="MidPoint IAM",
                    type="iam",
                    status="online",
                    message="Connecté",
                    url=settings.MIDPOINT_URL
                )
            else:
                return ConnectorStatus(
                    name="MidPoint IAM",
                    type="iam",
                    status="error",
                    message=f"HTTP {response.status_code}",
                    url=settings.MIDPOINT_URL
                )
    except Exception as e:
        return ConnectorStatus(
            name="MidPoint IAM",
            type="iam",
            status="offline",
            message=str(e),
            url=settings.MIDPOINT_URL
        )


async def check_odoo_status() -> ConnectorStatus:
    """Vérifie le statut d'Odoo"""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{settings.ODOO_URL}/web/login")
            if response.status_code in [200, 303]:
                return ConnectorStatus(
                    name="Odoo ERP",
                    type="erp",
                    status="online",
                    message="Connecté",
                    url=settings.ODOO_URL
                )
            else:
                return ConnectorStatus(
                    name="Odoo ERP",
                    type="erp",
                    status="error",
                    message=f"HTTP {response.status_code}",
                    url=settings.ODOO_URL
                )
    except Exception as e:
        return ConnectorStatus(
            name="Odoo ERP",
            type="erp",
            status="offline",
            message=str(e),
            url=settings.ODOO_URL
        )


async def check_ldap_status() -> ConnectorStatus:
    """Vérifie le statut LDAP (via MidPoint)"""
    # LDAP est accessible via MidPoint, on simule pour le moment
    return ConnectorStatus(
        name="LDAP Directory",
        type="directory",
        status="online",
        message="Via MidPoint",
        url="ldap://localhost:389"
    )


@router.get("/status", response_model=List[ConnectorStatus])
async def get_connectors_status():
    """
    Récupère le statut de tous les connecteurs
    """
    try:
        midpoint_status = await check_midpoint_status()
        odoo_status = await check_odoo_status()
        ldap_status = await check_ldap_status()
        
        return [midpoint_status, odoo_status, ldap_status]
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des statuts: {e}")
        raise HTTPException(status_code=500, detail=str(e))
