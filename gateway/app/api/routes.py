from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Dict
from datetime import datetime, timedelta
from pydantic import BaseModel, EmailStr

from app.database.connection import get_db
from app.database.models import (
    ProvisionedUser, 
    ProvisioningOperation, 
    ProvisioningAction,
    OperationStatus,
    ActionStatus
)
from app.services.provisioning_service import ProvisioningService
from app.connectors.base import MockConnector

router = APIRouter(prefix="/api/v1", tags=["provisioning"])


# ========== Pydantic Models ==========

class UserProvisionRequest(BaseModel):
    """Modèle de requête pour le provisioning d'un utilisateur."""
    email: EmailStr
    first_name: str
    last_name: str
    job_title: str
    department: str | None = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "email": "alice.doe@company.com",
                "first_name": "Alice",
                "last_name": "Doe",
                "job_title": "Développeur",
                "department": "IT"
            }
        }


# ========== Endpoints ==========

@router.get("/ping")
async def ping():
    """
    🏓 Ping Endpoint
    
    Test de connectivité simple.
    
    Returns:
        dict: Réponse pong avec timestamp
    """
    return {"status": "pong", "timestamp": datetime.utcnow().isoformat()}


@router.get("/stats")
async def get_provisioning_stats(db: Session = Depends(get_db)):
    """
    📊 Dashboard Statistics
    
    Retourne les KPIs principaux du dashboard :
    - Nombre total d'utilisateurs provisionnés
    - Nombre d'opérations aujourd'hui
    - Taux de succès global
    - Nombre d'échecs critiques
    
    Returns:
        dict: Dictionnaire avec les 4 métriques principales
    """
    # 1. Total Users
    total_users = db.query(ProvisionedUser).count()
    
    # 2. Today's Operations
    today = datetime.utcnow().date()
    today_ops = db.query(ProvisioningOperation).filter(
        ProvisioningOperation.started_at >= datetime.combine(today, datetime.min.time())
    ).count()
    
    # 3. Success Rate & Failures
    completed_ops = db.query(ProvisioningOperation).filter(
        ProvisioningOperation.status.in_([
            OperationStatus.SUCCESS.value,
            OperationStatus.PARTIAL.value,
            OperationStatus.FAILED.value
        ])
    ).all()
    
    failures = db.query(ProvisioningOperation).filter(
        ProvisioningOperation.status == OperationStatus.FAILED.value
    ).count()
    
    if completed_ops:
        success_ops = [op for op in completed_ops if op.status == OperationStatus.SUCCESS.value]
        success_rate = round((len(success_ops) / len(completed_ops)) * 100, 1)
    else:
        success_rate = 100.0
    
    return {
        "total_users": total_users,
        "today_operations": today_ops,
        "success_rate": success_rate,
        "critical_failures": failures
    }


@router.get("/users")
async def get_all_users(
    source: str = None,
    department: str = None,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """
    👥 List All Users
    
    Retourne la liste de tous les utilisateurs avec filtres optionnels.
    
    Args:
        source (str): Filtrer par source (ex: "odoo_sync", "api")
        department (str): Filtrer par département
        limit (int): Nombre maximum d'utilisateurs (défaut: 100)
        
    Returns:
        list: Liste des utilisateurs avec leurs informations
    """
    query = db.query(ProvisionedUser)
    
    # Appliquer les filtres
    if source:
        query = query.filter(ProvisionedUser.source == source)
    
    if department:
        query = query.filter(ProvisionedUser.department == department)
    
    users = query.limit(limit).all()
    
    return [
        {
            "id": user.id,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "job_title": user.job_title,
            "department": user.department,
            "role": user.role,
            "status": user.status,
            "source": user.source,
            "created_at": user.created_at.isoformat() if user.created_at else None,
            "last_provisioned_at": user.last_provisioned_at.isoformat() if user.last_provisioned_at else None
        }
        for user in users
    ]


@router.get("/operations/recent")
async def get_recent_operations(limit: int = 10, db: Session = Depends(get_db)):
    """
    📋 Recent Operations
    
    Retourne les N dernières opérations de provisioning avec leurs détails.
    
    Args:
        limit (int): Nombre maximum d'opérations à retourner (défaut: 10)
        
    Returns:
        list: Liste des opérations avec user, statut, et compteurs d'actions
    """
    operations = db.query(ProvisioningOperation).order_by(
        ProvisioningOperation.started_at.desc()
    ).limit(limit).all()
    
    results = []
    for op in operations:
        user = db.query(ProvisionedUser).filter(ProvisionedUser.id == op.user_id).first()
        
        # Récupérer les actions associées
        actions = db.query(ProvisioningAction).filter(
            ProvisioningAction.operation_id == op.id
        ).order_by(ProvisioningAction.executed_at.asc()).all()
        
        results.append({
            "id": op.id,
            "user": {
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "job_title": user.job_title
            },
            "status": op.status,
            "trigger": op.trigger,
            "started_at": op.started_at.isoformat() if op.started_at else None,
            "completed_at": op.completed_at.isoformat() if op.completed_at else None,
            "total_actions": op.total_actions,
            "successful_actions": op.successful_actions,
            "failed_actions": op.failed_actions,
            "actions": [
                {
                    "application": action.application,
                    "status": action.status,
                    "message": action.message,
                }
                for action in actions
            ]
        })
    
    return results


@router.get("/operations/{operation_id}")
async def get_operation_detail(operation_id: int, db: Session = Depends(get_db)):
    """
    🔍 Operation Detail
    
    Retourne le détail complet d'une opération avec toutes ses actions.
    Utilisé pour la page de détail avec timeline.
    
    Args:
        operation_id (int): ID de l'opération
        
    Returns:
        dict: Opération complète avec user, actions, et métadonnées
        
    Raises:
        HTTPException: 404 si l'opération n'existe pas
    """
    operation = db.query(ProvisioningOperation).filter(
        ProvisioningOperation.id == operation_id
    ).first()
    
    if not operation:
        raise HTTPException(status_code=404, detail="Operation not found")
    
    user = db.query(ProvisionedUser).filter(ProvisionedUser.id == operation.user_id).first()
    actions = db.query(ProvisioningAction).filter(
        ProvisioningAction.operation_id == operation_id
    ).order_by(ProvisioningAction.executed_at.asc()).all()
    
    return {
        "id": operation.id,
        "user": {
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "job_title": user.job_title,
            "department": user.department
        },
        "status": operation.status,
        "trigger": operation.trigger,
        "started_at": operation.started_at.isoformat() if operation.started_at else None,
        "completed_at": operation.completed_at.isoformat() if operation.completed_at else None,
        "total_actions": operation.total_actions,
        "successful_actions": operation.successful_actions,
        "failed_actions": operation.failed_actions,
        "actions": [
            {
                "id": action.id,
                "action_type": action.action_type,
                "application": action.application,
                "target_user": action.target_user,
                "status": action.status,
                "message": action.message,
                "details": action.details,
                "executed_at": action.executed_at.isoformat() if action.executed_at else None
            }
            for action in actions
        ]
    }


# ========== DÉSACTIVÉ: Création d'utilisateur ==========
# La création d'identités se fait uniquement sur Odoo/MidPoint
# Le Gateway ne sert qu'à provisionner les identités existantes

# @router.post("/provision", status_code=201)
# async def provision_user(
#     request: UserProvisionRequest,
#     dry_run: bool = False,
#     db: Session = Depends(get_db)
# ):
#     """
#     🚀 Provision User [DÉSACTIVÉ]
#     
#     ⚠️ Cette route est désactivée. 
#     La création d'utilisateurs doit se faire via Odoo ou MidPoint uniquement.
#     Utilisez POST /api/v1/midpoint/provision pour provisionner des identités existantes.
#     """
#     raise HTTPException(
#         status_code=403, 
#         detail="Création directe désactivée. Utilisez Odoo/MidPoint puis /api/v1/midpoint/provision"
#     )
