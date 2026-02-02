"""
Routes API pour l'intégration Odoo ↔ Aegis Gateway

Endpoints:
- GET /odoo/employees : Liste les employés Odoo
- POST /odoo/sync : Synchronise tous les employés vers la base locale
- POST /odoo/webhook : Webhook pour synchronisation temps réel
"""
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, Dict, List
from datetime import datetime
from sqlalchemy.orm import Session
import logging

logger = logging.getLogger(__name__)

from ..services.odoo_sync_service import get_odoo_sync_service
from ..services.odoo_service import get_odoo_service
from ..database.models import get_db

router = APIRouter(prefix="/odoo", tags=["Odoo Integration"])


class OdooEmployee(BaseModel):
    """Modèle d'employé Odoo"""
    personalNumber: str
    givenName: str
    familyName: str
    email: str
    department: Optional[str] = None
    title: Optional[str] = None
    status: str


class SyncResponse(BaseModel):
    """Réponse de synchronisation"""
    success: bool
    message: str
    timestamp: str
    stats: Optional[Dict] = None


class WebhookPayload(BaseModel):
    """Payload du webhook Odoo"""
    event: str  # "create", "update", "delete"
    employee_id: int
    data: Optional[Dict] = None


@router.get("/employees", response_model=List[OdooEmployee])
async def get_odoo_employees():
    """
    Récupère la liste des employés depuis Odoo
    
    Cette route interroge directement Odoo sans passer par la base locale.
    Utile pour voir les données sources.
    """
    odoo = get_odoo_service()
    
    if not odoo.connect():
        raise HTTPException(status_code=503, detail="Impossible de se connecter à Odoo")
    
    employees = odoo.get_employees()
    
    if not employees:
        return []
    
    return employees


@router.post("/sync", response_model=SyncResponse)
async def sync_odoo_employees(
    background: bool = False,
    background_tasks: BackgroundTasks = None,
    db: Session = Depends(get_db)
):
    """
    Synchronise tous les employés Odoo vers la base Aegis Gateway
    
    Args:
        background: Si True, exécute la sync en arrière-plan
        
    Returns:
        Statistiques de synchronisation (créés, mis à jour, ignorés)
        
    Usage:
        POST /api/v1/odoo/sync
        POST /api/v1/odoo/sync?background=true
    """
    sync_service = get_odoo_sync_service(db)
    
    if background and background_tasks:
        # Exécution asynchrone
        background_tasks.add_task(sync_service.sync_all_employees)
        
        return SyncResponse(
            success=True,
            message="Synchronisation lancée en arrière-plan",
            timestamp=datetime.now().isoformat(),
            stats={"status": "running"}
        )
    else:
        # Exécution synchrone
        result = sync_service.sync_all_employees()
        
        if not result.get("success"):
            raise HTTPException(
                status_code=500,
                detail=result.get("error", "Erreur de synchronisation")
            )
        
        return SyncResponse(
            success=True,
            message=f"Synchronisation réussie: {result.get('created', 0)} créés, "
                   f"{result.get('updated', 0)} mis à jour",
            timestamp=datetime.now().isoformat(),
            stats=result
        )


@router.post("/sync-csv")
async def sync_odoo_to_csv_endpoint(background_tasks: BackgroundTasks):
    """
    Déclenche manuellement la mise à jour du fichier hr_clean.csv depuis Odoo.
    Met à jour le fichier utilisé par MidPoint pour la réconciliation.
    """
    odoo = get_odoo_service()
    
    # On exécute en background
    background_tasks.add_task(odoo.update_csv)
    
    return {
        "success": True,
        "message": "Mise à jour du fichier hr_clean.csv lancée en arrière-plan",
        "timestamp": datetime.now().isoformat()
    }


@router.post("/webhook")
async def odoo_webhook(
    payload: WebhookPayload,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Webhook pour synchronisation temps réel depuis Odoo
    
    À configurer dans Odoo avec un module "webhook" ou via n8n.
    
    Événements supportés:
    - create: Nouvel employé créé dans Odoo
    - update: Employé modifié dans Odoo
    - delete: Employé désactivé dans Odoo
    
    Usage depuis Odoo/n8n:
        POST /api/v1/odoo/webhook
        {
            "event": "create",
            "employee_id": 42,
            "data": {...}
        }
    """
    sync_service = get_odoo_sync_service(db)
    
    # 🔄 Mise à jour du CSV partagé à chaque changement
    odoo = get_odoo_service()
    background_tasks.add_task(odoo.update_csv)
    
    if payload.event in ["create", "update"]:
        # Synchroniser l'employé spécifique (best-effort)
        try:
            result = sync_service.sync_single_employee(payload.employee_id)
            sync_success = result.get("success", False)
            action = result.get("action", "synced")
        except Exception as e:
            logger.warning(f"Sync failed for employee {payload.employee_id}: {e}")
            sync_success = False
            action = "csv_updated_only"
        
        return {
            "success": True,
            "message": f"Employé {payload.employee_id}: CSV mis à jour",
            "action": action,
            "sync_success": sync_success,
            "timestamp": datetime.now().isoformat()
        }
    
    elif payload.event == "delete":
        # Marquer l'utilisateur comme inactif
        return {
            "success": True,
            "message": f"Employé {payload.employee_id}: Marqué inactif, CSV mis à jour",
            "action": "deactivated_csv_updated",
            "timestamp": datetime.now().isoformat()
        }
    
    else:
        raise HTTPException(
            status_code=400,
            detail=f"Événement non supporté: {payload.event}"
        )


@router.get("/sync/status")
async def get_sync_status(db: Session = Depends(get_db)):
    """
    Retourne le statut de la dernière synchronisation
    
    Affiche:
    - Nombre d'utilisateurs dans la base locale provenant d'Odoo
    - Dernière synchronisation
    - Connexion Odoo
    """
    from ..database.models import ProvisionedUser
    
    # Compter les utilisateurs provenant d'Odoo
    odoo_users_count = db.query(ProvisionedUser).filter(
        ProvisionedUser.source == "odoo_sync"
    ).count()
    
    # Tester la connexion Odoo
    odoo = get_odoo_service()
    odoo_connected = odoo.connect()
    
    return {
        "odoo_connected": odoo_connected,
        "local_users_from_odoo": odoo_users_count,
        "last_check": datetime.now().isoformat()
    }
