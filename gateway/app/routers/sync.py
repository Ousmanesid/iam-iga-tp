"""
Routes API pour la synchronisation Odoo → MidPoint
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, Dict
from datetime import datetime

from ..services.sync_service import get_sync_service

router = APIRouter(prefix="/sync", tags=["Synchronization"])


class SyncResponse(BaseModel):
    success: bool
    message: str
    timestamp: str
    details: Optional[Dict] = None


class StatusResponse(BaseModel):
    odoo_connected: bool
    midpoint_connected: bool
    last_sync: Optional[str]
    last_sync_stats: Optional[Dict]


@router.get("/status", response_model=StatusResponse)
async def get_sync_status():
    """
    Retourne le statut de la synchronisation
    
    - Connexion Odoo
    - Connexion MidPoint
    - Dernière synchronisation
    """
    service = get_sync_service()
    return service.get_status()


@router.post("/odoo-to-csv", response_model=SyncResponse)
async def export_odoo_to_csv():
    """
    Exporte les employés Odoo vers le fichier CSV
    
    Étape 1 du pipeline de synchronisation
    """
    service = get_sync_service()
    result = service.export_odoo_to_csv()
    
    return SyncResponse(
        success=result.get("success", False),
        message=f"Export {'réussi' if result.get('success') else 'échoué'}: {result.get('count', 0)} employés",
        timestamp=datetime.now().isoformat(),
        details=result
    )


@router.post("/csv-to-midpoint", response_model=SyncResponse)
async def trigger_midpoint_import():
    """
    Déclenche l'import MidPoint depuis le CSV
    
    Étape 2 du pipeline de synchronisation
    """
    service = get_sync_service()
    result = service.trigger_midpoint_import()
    
    return SyncResponse(
        success=result.get("success", False),
        message=result.get("message", ""),
        timestamp=datetime.now().isoformat(),
        details=result
    )


@router.post("/full", response_model=SyncResponse)
async def full_sync():
    """
    Synchronisation complète Odoo → CSV → MidPoint
    
    Exécute les deux étapes en séquence:
    1. Export Odoo → CSV
    2. Import CSV → MidPoint
    """
    service = get_sync_service()
    result = service.full_sync()
    
    return SyncResponse(
        success=result.get("success", False),
        message=f"Synchronisation {'réussie' if result.get('success') else 'échouée'}",
        timestamp=result.get("timestamp", datetime.now().isoformat()),
        details=result
    )


@router.post("/full/async", response_model=SyncResponse)
async def full_sync_async(background_tasks: BackgroundTasks):
    """
    Synchronisation complète en arrière-plan
    
    Retourne immédiatement, la sync s'exécute en background
    """
    service = get_sync_service()
    background_tasks.add_task(service.full_sync)
    
    return SyncResponse(
        success=True,
        message="Synchronisation démarrée en arrière-plan",
        timestamp=datetime.now().isoformat(),
        details={"async": True}
    )
