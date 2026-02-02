"""
Service d'Audit - Enregistrement des événements système

Ce service centralise tous les logs d'audit de l'application.
"""
import logging
from datetime import datetime
from typing import Optional, List, Dict
from sqlalchemy.orm import Session

from ..database.models import AuditLog

logger = logging.getLogger(__name__)


class AuditService:
    """Service pour gérer les logs d'audit"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def log(
        self,
        action: str,
        actor: str,
        message: str,
        target: Optional[str] = None,
        level: str = "INFO",
        source_ip: Optional[str] = None,
        details: Optional[Dict] = None
    ) -> AuditLog:
        """
        Enregistre un événement d'audit.
        
        Args:
            action: Type d'action (USER_CREATED, USER_UPDATED, SYNC_COMPLETED, etc.)
            actor: Qui a effectué l'action (email, system, etc.)
            message: Description de l'action
            target: Cible de l'action (email utilisateur, nom du système, etc.)
            level: Niveau (INFO, WARNING, ERROR, CRITICAL)
            source_ip: Adresse IP source
            details: Détails supplémentaires en JSON
            
        Returns:
            AuditLog créé
        """
        audit_log = AuditLog(
            timestamp=datetime.utcnow(),
            action=action,
            actor=actor,
            target=target,
            message=message,
            level=level,
            source_ip=source_ip,
            details=details
        )
        
        self.db.add(audit_log)
        self.db.commit()
        self.db.refresh(audit_log)
        
        # Log aussi dans les logs Python pour debug
        log_msg = f"[AUDIT] {action} | {actor} → {target} | {message}"
        if level == "ERROR" or level == "CRITICAL":
            logger.error(log_msg)
        elif level == "WARNING":
            logger.warning(log_msg)
        else:
            logger.info(log_msg)
        
        return audit_log
    
    def log_user_created(
        self, 
        user_email: str, 
        user_name: str, 
        source: str,
        actor: str = "system",
        source_ip: Optional[str] = None
    ) -> AuditLog:
        """Log création d'utilisateur"""
        return self.log(
            action="USER_CREATED",
            actor=actor,
            target=f"{user_name} ({user_email})",
            message=f"Nouvel utilisateur créé via {source}",
            level="INFO",
            source_ip=source_ip,
            details={"email": user_email, "source": source}
        )
    
    def log_user_updated(
        self,
        user_email: str,
        user_name: str,
        changes: Dict,
        actor: str = "system",
        source_ip: Optional[str] = None
    ) -> AuditLog:
        """Log mise à jour d'utilisateur"""
        return self.log(
            action="USER_UPDATED",
            actor=actor,
            target=f"{user_name} ({user_email})",
            message=f"Utilisateur mis à jour: {', '.join(changes.keys())}",
            level="INFO",
            source_ip=source_ip,
            details={"email": user_email, "changes": changes}
        )
    
    def log_sync_started(
        self,
        source: str,
        actor: str = "system",
        source_ip: Optional[str] = None
    ) -> AuditLog:
        """Log début de synchronisation"""
        return self.log(
            action="SYNC_STARTED",
            actor=actor,
            target=source,
            message=f"Synchronisation {source} démarrée",
            level="INFO",
            source_ip=source_ip
        )
    
    def log_sync_completed(
        self,
        source: str,
        created: int,
        updated: int,
        skipped: int,
        actor: str = "system",
        source_ip: Optional[str] = None
    ) -> AuditLog:
        """Log fin de synchronisation"""
        return self.log(
            action="SYNC_COMPLETED",
            actor=actor,
            target=source,
            message=f"Synchronisation terminée: {created} créés, {updated} mis à jour, {skipped} ignorés",
            level="INFO",
            source_ip=source_ip,
            details={"created": created, "updated": updated, "skipped": skipped}
        )
    
    def log_sync_failed(
        self,
        source: str,
        error: str,
        actor: str = "system",
        source_ip: Optional[str] = None
    ) -> AuditLog:
        """Log échec de synchronisation"""
        return self.log(
            action="SYNC_FAILED",
            actor=actor,
            target=source,
            message=f"Échec de synchronisation: {error}",
            level="ERROR",
            source_ip=source_ip,
            details={"error": error}
        )
    
    def log_role_assigned(
        self,
        user_email: str,
        role_name: str,
        actor: str = "system",
        source_ip: Optional[str] = None
    ) -> AuditLog:
        """Log assignation de rôle"""
        return self.log(
            action="ROLE_ASSIGNED",
            actor=actor,
            target=user_email,
            message=f"Rôle '{role_name}' assigné",
            level="INFO",
            source_ip=source_ip,
            details={"role": role_name}
        )
    
    def log_provisioning_success(
        self,
        user_email: str,
        applications: List[str],
        actor: str = "system",
        source_ip: Optional[str] = None
    ) -> AuditLog:
        """Log provisioning réussi"""
        return self.log(
            action="USER_PROVISIONED",
            actor=actor,
            target=user_email,
            message=f"Provisioning réussi vers {len(applications)} application(s)",
            level="INFO",
            source_ip=source_ip,
            details={"applications": applications}
        )
    
    def log_provisioning_failed(
        self,
        user_email: str,
        application: str,
        error: str,
        actor: str = "system",
        source_ip: Optional[str] = None
    ) -> AuditLog:
        """Log échec de provisioning"""
        return self.log(
            action="PROVISIONING_FAILED",
            actor=actor,
            target=user_email,
            message=f"Échec provisioning vers {application}: {error}",
            level="ERROR",
            source_ip=source_ip,
            details={"application": application, "error": error}
        )
    
    def get_recent_logs(
        self,
        limit: int = 50,
        level: Optional[str] = None,
        action: Optional[str] = None
    ) -> List[AuditLog]:
        """
        Récupère les logs récents.
        
        Args:
            limit: Nombre max de logs
            level: Filtrer par niveau (INFO, WARNING, ERROR, CRITICAL)
            action: Filtrer par type d'action
            
        Returns:
            Liste de logs ordonnés par date décroissante
        """
        query = self.db.query(AuditLog)
        
        if level and level != "all":
            query = query.filter(AuditLog.level == level)
        
        if action:
            query = query.filter(AuditLog.action == action)
        
        return query.order_by(AuditLog.timestamp.desc()).limit(limit).all()
    
    def get_logs_count_by_level(self) -> Dict[str, int]:
        """Compte les logs par niveau"""
        from sqlalchemy import func
        
        result = self.db.query(
            AuditLog.level,
            func.count(AuditLog.id)
        ).group_by(AuditLog.level).all()
        
        return {level: count for level, count in result}


def get_audit_service(db: Session) -> AuditService:
    """Factory pour créer le service d'audit"""
    return AuditService(db)
