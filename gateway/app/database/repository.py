"""Repository - Couche d'accès aux données.""""""

Repository - Couche d'accès aux données.

from typing import Optional, List

from datetime import datetime🎯 Ce module fournit des méthodes CRUD pour :

from sqlalchemy.orm import Session   - Utilisateurs provisionnés

   - Opérations de provisioning

from app.database.models import (   - Logs d'audit

    ProvisionedUser,"""

    ProvisioningOperation,

    ProvisioningAction,from typing import Optional, List

    AuditLog,from datetime import datetime

    OperationStatus,from sqlalchemy.orm import Session

    ActionStatus,

)from app.database.models import (

    ProvisionedUser,

    ProvisioningOperation,

class UserRepository:    ProvisioningAction,

    """Repository pour les utilisateurs provisionnés."""    AuditLog,

        OperationStatus,

    def __init__(self, db: Session):    ActionStatus,

        self.db = db)

    

    def get_by_email(self, email: str) -> Optional[ProvisionedUser]:

        """Récupère un utilisateur par email."""class UserRepository:

        return self.db.query(ProvisionedUser).filter(    """Repository pour les utilisateurs provisionnés."""

            ProvisionedUser.email == email    

        ).first()    def __init__(self, db: Session):

            self.db = db

    def get_by_id(self, user_id: int) -> Optional[ProvisionedUser]:    

        """Récupère un utilisateur par ID."""    def get_by_email(self, email: str) -> Optional[ProvisionedUser]:

        return self.db.query(ProvisionedUser).filter(        """Récupère un utilisateur par email."""

            ProvisionedUser.id == user_id        return self.db.query(ProvisionedUser).filter(

        ).first()            ProvisionedUser.email == email

            ).first()

    def list_all(self, skip: int = 0, limit: int = 100) -> List[ProvisionedUser]:    

        """Liste tous les utilisateurs."""    def get_by_id(self, user_id: int) -> Optional[ProvisionedUser]:

        return self.db.query(ProvisionedUser).offset(skip).limit(limit).all()        """Récupère un utilisateur par ID."""

            return self.db.query(ProvisionedUser).filter(

    def create(            ProvisionedUser.id == user_id

        self,        ).first()

        email: str,    

        first_name: str,    def list_all(self, skip: int = 0, limit: int = 100) -> List[ProvisionedUser]:

        last_name: str,        """Liste tous les utilisateurs."""

        job_title: Optional[str] = None,        return self.db.query(ProvisionedUser).offset(skip).limit(limit).all()

        department: Optional[str] = None,    

    ) -> ProvisionedUser:    def create(

        """Crée un nouvel utilisateur."""        self,

        user = ProvisionedUser(        email: str,

            email=email,        first_name: str,

            first_name=first_name,        last_name: str,

            last_name=last_name,        job_title: Optional[str] = None,

            job_title=job_title,        department: Optional[str] = None,

            department=department,    ) -> ProvisionedUser:

            status=OperationStatus.PENDING.value,        """Crée un nouvel utilisateur."""

        )        user = ProvisionedUser(

        self.db.add(user)            email=email,

        self.db.commit()            first_name=first_name,

        self.db.refresh(user)            last_name=last_name,

        return user            job_title=job_title,

                department=department,

    def update_status(self, user: ProvisionedUser, status: str) -> ProvisionedUser:            status=OperationStatus.PENDING.value,

        """Met à jour le statut d'un utilisateur."""        )

        user.status = status        self.db.add(user)

        user.updated_at = datetime.utcnow()        self.db.commit()

        self.db.commit()        self.db.refresh(user)

        self.db.refresh(user)        return user

        return user    

    def get_or_create(

        self,

class OperationRepository:        email: str,

    """Repository pour les opérations de provisioning."""        first_name: str,

            last_name: str,

    def __init__(self, db: Session):        job_title: Optional[str] = None,

        self.db = db        department: Optional[str] = None,

        ) -> tuple[ProvisionedUser, bool]:

    def create(        """Récupère ou crée un utilisateur. Retourne (user, created)."""

        self,        existing = self.get_by_email(email)

        user_id: int,        if existing:

        trigger: str = "api",            return existing, False

    ) -> ProvisioningOperation:        

        """Crée une nouvelle opération."""        user = self.create(email, first_name, last_name, job_title, department)

        operation = ProvisioningOperation(        return user, True

            user_id=user_id,    

            trigger=trigger,    def update_status(self, user: ProvisionedUser, status: str) -> ProvisionedUser:

            status=OperationStatus.IN_PROGRESS.value,        """Met à jour le statut d'un utilisateur."""

        )        user.status = status

        self.db.add(operation)        user.updated_at = datetime.utcnow()

        self.db.commit()        self.db.commit()

        self.db.refresh(operation)        self.db.refresh(user)

        return operation        return user

        

    def add_action(    def mark_provisioned(self, user: ProvisionedUser, status: str) -> ProvisionedUser:

        self,        """Marque un utilisateur comme provisionné."""

        operation: ProvisioningOperation,        user.status = status

        action_type: str,        user.last_provisioned_at = datetime.utcnow()

        application: str,        user.updated_at = datetime.utcnow()

        target_user: str,        self.db.commit()

        details: dict = None,        self.db.refresh(user)

    ) -> ProvisioningAction:        return user

        """Ajoute une action à une opération."""

        action = ProvisioningAction(

            operation_id=operation.id,class OperationRepository:

            action_type=action_type,    """Repository pour les opérations de provisioning."""

            application=application,    

            target_user=target_user,    def __init__(self, db: Session):

            status=ActionStatus.PENDING.value,        self.db = db

        )    

        if details:    def create(

            action.details = details        self,

                user_id: int,

        self.db.add(action)        trigger: str = "api",

        self.db.commit()    ) -> ProvisioningOperation:

        self.db.refresh(action)        """Crée une nouvelle opération."""

        return action        operation = ProvisioningOperation(

                user_id=user_id,

    def update_action(            trigger=trigger,

        self,            status=OperationStatus.IN_PROGRESS.value,

        action: ProvisioningAction,        )

        status: str,        self.db.add(operation)

        message: Optional[str] = None,        self.db.commit()

    ) -> ProvisioningAction:        self.db.refresh(operation)

        """Met à jour une action."""        return operation

        action.status = status    

        action.message = message    def add_action(

        action.executed_at = datetime.utcnow()        self,

        self.db.commit()        operation: ProvisioningOperation,

        self.db.refresh(action)        action_type: str,

        return action        application: str,

            target_user: str,

    def complete_operation(        details: dict = None,

        self,    ) -> ProvisioningAction:

        operation: ProvisioningOperation,        """Ajoute une action à une opération."""

        total: int,        action = ProvisioningAction(

        success: int,            operation_id=operation.id,

        failed: int,            action_type=action_type,

    ) -> ProvisioningOperation:            application=application,

        """Termine une opération."""            target_user=target_user,

        operation.total_actions = total            status=ActionStatus.PENDING.value,

        operation.successful_actions = success        )

        operation.failed_actions = failed        if details:

        operation.completed_at = datetime.utcnow()            action.details = details

                

        # Déterminer le statut        self.db.add(action)

        if failed == 0 and success > 0:        self.db.commit()

            operation.status = OperationStatus.SUCCESS.value        self.db.refresh(action)

        elif failed > 0 and success > 0:        return action

            operation.status = OperationStatus.PARTIAL.value    

        elif failed == total:    def update_action(

            operation.status = OperationStatus.FAILED.value        self,

                action: ProvisioningAction,

        self.db.commit()        status: str,

        self.db.refresh(operation)        message: Optional[str] = None,

        return operation    ) -> ProvisioningAction:

            """Met à jour une action."""

    def get_by_id(self, operation_id: int) -> Optional[ProvisioningOperation]:        action.status = status

        """Récupère une opération par son ID."""        action.message = message

        return self.db.query(ProvisioningOperation).filter(        action.executed_at = datetime.utcnow()

            ProvisioningOperation.id == operation_id        self.db.commit()

        ).first()        self.db.refresh(action)

            return action

    def get_recent(self, limit: int = 50) -> List[ProvisioningOperation]:    

        """Récupère les opérations récentes."""    def complete_operation(

        return self.db.query(ProvisioningOperation).order_by(        self,

            ProvisioningOperation.started_at.desc()        operation: ProvisioningOperation,

        ).limit(limit).all()        total: int,

        success: int,

        failed: int,

class AuditRepository:    ) -> ProvisioningOperation:

    """Repository pour les logs d'audit."""        """Termine une opération."""

            operation.total_actions = total

    def __init__(self, db: Session):        operation.successful_actions = success

        self.db = db        operation.failed_actions = failed

            operation.completed_at = datetime.utcnow()

    def log(        

        self,        # Déterminer le statut

        action: str,        if failed == 0 and success > 0:

        message: str,            operation.status = OperationStatus.SUCCESS.value

        actor: Optional[str] = None,        elif failed > 0 and success > 0:

        target: Optional[str] = None,            operation.status = OperationStatus.PARTIAL.value

        level: str = "INFO",        elif failed == total:

        details: dict = None,            operation.status = OperationStatus.FAILED.value

        source_ip: Optional[str] = None,        

    ) -> AuditLog:        self.db.commit()

        """Crée une entrée d'audit."""        self.db.refresh(operation)

        log_entry = AuditLog(        return operation

            action=action,    

            message=message,    def get_by_user(self, user_id: int) -> List[ProvisioningOperation]:

            actor=actor or "system",        """Récupère les opérations d'un utilisateur."""

            target=target,        return self.db.query(ProvisioningOperation).filter(

            level=level,            ProvisioningOperation.user_id == user_id

            source_ip=source_ip,        ).order_by(ProvisioningOperation.started_at.desc()).all()

        )    

        if details:    def get_recent(self, limit: int = 50) -> List[ProvisioningOperation]:

            log_entry.details = details        """Récupère les opérations récentes."""

                return self.db.query(ProvisioningOperation).order_by(

        self.db.add(log_entry)            ProvisioningOperation.started_at.desc()

        self.db.commit()        ).limit(limit).all()

        self.db.refresh(log_entry)

        return log_entry    def get_by_id(self, operation_id: int) -> Optional[ProvisioningOperation]:

        """Récupère une opération par son ID."""
        return self.db.query(ProvisioningOperation).filter(
            ProvisioningOperation.id == operation_id
        ).first()


class AuditRepository:
    """Repository pour les logs d'audit."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def log(
        self,
        action: str,
        message: str,
        actor: Optional[str] = None,
        target: Optional[str] = None,
        level: str = "INFO",
        details: dict = None,
        source_ip: Optional[str] = None,
    ) -> AuditLog:
        """Crée une entrée d'audit."""
        log_entry = AuditLog(
            action=action,
            message=message,
            actor=actor or "system",
            target=target,
            level=level,
            source_ip=source_ip,
        )
        if details:
            log_entry.details = details
        
        self.db.add(log_entry)
        self.db.commit()
        self.db.refresh(log_entry)
        return log_entry
    
    def get_recent(self, limit: int = 100) -> List[AuditLog]:
        """Récupère les logs récents."""
        return self.db.query(AuditLog).order_by(
            AuditLog.timestamp.desc()
        ).limit(limit).all()
    
    def get_by_target(self, target: str, limit: int = 50) -> List[AuditLog]:
        """Récupère les logs pour une cible."""
        return self.db.query(AuditLog).filter(
            AuditLog.target == target
        ).order_by(AuditLog.timestamp.desc()).limit(limit).all()
