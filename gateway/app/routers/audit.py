"""
API Router pour les logs d'audit

Endpoints:
- GET /api/v1/audit - Liste des logs d'audit avec filtres
- GET /api/v1/audit/stats - Statistiques des logs
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime

from ..database.models import get_db
from ..services.audit_service import get_audit_service
from pydantic import BaseModel


router = APIRouter(prefix="/audit", tags=["Audit"])


# ============ Schémas de réponse ============

class AuditLogResponse(BaseModel):
    """Schéma de réponse pour un log d'audit"""
    id: int
    timestamp: datetime
    action: str
    actor: str
    target: Optional[str]
    message: str
    level: str
    source_ip: Optional[str]
    details: Optional[dict]
    
    class Config:
        from_attributes = True


class AuditStatsResponse(BaseModel):
    """Statistiques des logs d'audit"""
    total: int
    by_level: dict
    

class AuditListResponse(BaseModel):
    """Réponse liste des logs"""
    logs: List[AuditLogResponse]
    total: int


# ============ Endpoints ============

@router.get("", response_model=AuditListResponse)
def get_audit_logs(
    limit: int = Query(50, ge=1, le=500),
    level: Optional[str] = Query(None, description="Filtrer par niveau (INFO, WARNING, ERROR, CRITICAL)"),
    action: Optional[str] = Query(None, description="Filtrer par type d'action"),
    db: Session = Depends(get_db)
):
    """
    Récupère les logs d'audit.
    
    - **limit**: Nombre maximum de logs à retourner (1-500)
    - **level**: Filtrer par niveau (INFO, WARNING, ERROR, CRITICAL)
    - **action**: Filtrer par type d'action (USER_CREATED, SYNC_COMPLETED, etc.)
    """
    audit_service = get_audit_service(db)
    logs = audit_service.get_recent_logs(limit=limit, level=level, action=action)
    
    return AuditListResponse(
        logs=[AuditLogResponse.from_orm(log) for log in logs],
        total=len(logs)
    )


@router.get("/stats", response_model=AuditStatsResponse)
def get_audit_stats(db: Session = Depends(get_db)):
    """
    Récupère les statistiques des logs d'audit.
    """
    audit_service = get_audit_service(db)
    by_level = audit_service.get_logs_count_by_level()
    total = sum(by_level.values())
    
    return AuditStatsResponse(
        total=total,
        by_level=by_level
    )


@router.get("/actions")
def get_available_actions(db: Session = Depends(get_db)):
    """
    Récupère la liste des types d'actions disponibles.
    """
    from ..database.models import AuditLog
    from sqlalchemy import distinct
    
    actions = db.query(distinct(AuditLog.action)).all()
    return {"actions": [a[0] for a in actions if a[0]]}
