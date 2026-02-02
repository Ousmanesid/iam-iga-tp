"""
Provisioning Service - Phase 2 Core IAM

Orchestre le provisioning multi-applications avec gestion d'erreur et rollback.
Ce service coordonne les connectors et enregistre toutes les opérations dans la DB.
"""
from datetime import datetime
from typing import List, Dict, Optional, Any
from sqlalchemy.orm import Session
import logging

from app.database.models import (
    ProvisionedUser,
    ProvisioningOperation,
    ProvisioningAction,
    OperationStatus,
    ActionStatus
)
from app.core.role_mapper import get_provisioning_plan
from app.services.midpoint_service import MidPointService

logger = logging.getLogger(__name__)


class ProvisioningService:
    """
    Service de provisioning centralisé (Orchestrateur).
    
    Nouvelle Architecture (Phase 3):
    - Calcule le plan de provisioning (Rôles & Applications)
    - Délègue l'exécution technique UNIQUEMENT à MidPoint
    - N'appelle plus directement les connecteurs applicatifs
    """
    
    def __init__(self, db: Session):
        """
        Initialise le service de provisioning.
        """
        self.db = db
        # Les connecteurs directs sont obsolètes. On utilise MidPointService.
        self.midpoint_service = MidPointService()
        
    def register_connector(self, app_name: str, connector: Any):
        """DEPRECATED: Les connecteurs ne sont plus utilisés par Aegis."""
        logger.warning(f"Register connector {app_name} ignored (Architecture Change: All provisioning goes via MidPoint)")
        pass
        
    def provision_user(
        self, 
        user_data: Dict[str, str], 
        trigger: str = "api",
        dry_run: bool = False,
        selected_applications: Optional[List[str]] = None
    ) -> ProvisioningOperation:
        """
        Orchestre le provisioning d'un utilisateur via MidPoint.
        """
        # 1. Validation des données
        self._validate_user_data(user_data)
        
        # 2. Création ou récupération de l'utilisateur (Local DB)
        user = self._get_or_create_user(user_data)
        
        # 3. Génération du plan de provisioning
        plan = get_provisioning_plan(user_data)
        
        # 4. Filtrage des applications
        if selected_applications:
            plan['applications'] = [
                app for app in plan['applications'] 
                if app in selected_applications
            ]
            plan['total_actions'] = len(plan['applications'])
        
        # 5. Création de l'opération (Pending)
        operation = ProvisioningOperation(
            user_id=user.id,
            status=OperationStatus.PENDING.value,
            trigger=trigger,
            started_at=datetime.utcnow(),
            total_actions=plan['total_actions'],
            successful_actions=0,
            failed_actions=0
        )
        self.db.add(operation)
        self.db.commit()
        self.db.refresh(operation)
        
        if dry_run:
            logger.info(f"[DRY RUN] Plan for {user_data['email']}: {plan['applications']}")
            operation.status = OperationStatus.SUCCESS.value
            operation.completed_at = datetime.utcnow()
            self.db.commit()
            return operation

        # 6. Exécution via MidPoint (Seul point de sortie)
        try:
            # Envoi du plan complet à MidPoint
            target_apps = plan['applications']
            logger.info(f"Delegating provisioning for {user_data['email']} to MidPoint. Targets: {target_apps}")
            
            mp_result = self.midpoint_service.provision_user_with_assignments(
                user_data=user_data,
                assignments=target_apps
            )
            
            # 7. Enregistrement des résultats (Audit)
            for action_desc in mp_result['actions']:
                action = ProvisioningAction(
                    operation_id=operation.id,
                    action_type="midpoint_delegation",
                    application="MidPoint",
                    target_user=user_data['email'],
                    status=ActionStatus.SUCCESS.value if "Success" in action_desc else ActionStatus.FAILED.value,
                    executed_at=datetime.utcnow(),
                    message=action_desc,
                    details={"midpoint_oid": mp_result.get('midpoint_oid')}
                )
                self.db.add(action)
                
                # Mise à jour des compteurs
                if "Success" in action_desc:
                    operation.successful_actions += 1 # Estimation
                # Note: MidPoint fait tout en une requête ou quelques 'unes. 
                # On map 1-to-1 les actions MidPoint aux actions Aegis pour la visibilité

            if mp_result['success']:
                operation.status = OperationStatus.SUCCESS.value
                user.status = "synced"
            else:
                operation.status = OperationStatus.FAILED.value
                operation.failed_actions += 1 # Mark global failure
                
        except Exception as e:
            logger.error(f"Critical Error calling MidPoint: {e}")
            operation.status = OperationStatus.FAILED.value
            operation.failed_actions += 1
            
            # Log error action
            error_action = ProvisioningAction(
                operation_id=operation.id,
                action_type="midpoint_error",
                application="MidPoint",
                target_user=user_data['email'],
                status=ActionStatus.FAILED.value,
                executed_at=datetime.utcnow(),
                message=str(e)
            )
            self.db.add(error_action)

        operation.completed_at = datetime.utcnow()
        user.last_provisioned_at = datetime.utcnow()
        self.db.commit()
        
        return operation
        
    def _validate_user_data(self, user_data: Dict[str, str]):
        """Valide les données utilisateur minimales."""
        required_fields = ['email', 'first_name', 'last_name', 'job_title']
        for field in required_fields:
            if not user_data.get(field):
                raise ValueError(f"Missing required field: {field}")
                
        # Validation email basique
        email = user_data['email']
        if '@' not in email or '.' not in email:
            raise ValueError(f"Invalid email format: {email}")
            
    def _get_or_create_user(self, user_data: Dict[str, str]) -> ProvisionedUser:
        """Crée ou récupère un utilisateur existant."""
        email = user_data['email']
        user = self.db.query(ProvisionedUser).filter(
            ProvisionedUser.email == email
        ).first()
        
        if not user:
            user = ProvisionedUser(
                email=email,
                first_name=user_data['first_name'],
                last_name=user_data['last_name'],
                job_title=user_data['job_title'],
                department=user_data.get('department'),
                status='pending'
            )
            self.db.add(user)
            self.db.commit()
            self.db.refresh(user)
            
        return user
        
    def _provision_to_application(
        self,
        operation: ProvisioningOperation,
        user_data: Dict[str, str],
        app_name: str,
        dry_run: bool = False
    ) -> ProvisioningAction:
        """
        DEPRECATED: Cette méthode ne doit plus être utilisée directement pour provisionner.
        Tout passe par MidPoint en une seule opération groupée.
        
        Gardée temporairement pour compatibilité si nécessaire, mais renvoie maintenant une erreur
        pour forcer l'usage du nouveau flux.
        """
        raise NotImplementedError("This method is deprecated. Use provision_user() which delegates to MidPoint.")

        
    def rollback_operation(self, operation_id: int) -> Dict[str, any]:
        """
        Tente de rollback une opération partiellement réussie.
        
        Args:
            operation_id (int): ID de l'opération à rollback
            
        Returns:
            Dict: Résultat du rollback avec détails
        """
        operation = self.db.query(ProvisioningOperation).filter(
            ProvisioningOperation.id == operation_id
        ).first()
        
        if not operation:
            return {"success": False, "message": "Operation not found"}
            
        # Récupérer toutes les actions réussies
        successful_actions = self.db.query(ProvisioningAction).filter(
            ProvisioningAction.operation_id == operation_id,
            ProvisioningAction.status == ActionStatus.SUCCESS.value
        ).all()
        
        rollback_results = []
        for action in successful_actions:
            app_name = action.application
            if app_name in self.connectors:
                try:
                    connector = self.connectors[app_name]
                    result = connector.delete_user(action.target_user)
                    rollback_results.append({
                        "app": app_name,
                        "success": result['success'],
                        "message": result['message']
                    })
                except Exception as e:
                    rollback_results.append({
                        "app": app_name,
                        "success": False,
                        "message": f"Rollback failed: {str(e)}"
                    })
                    
        return {
            "success": True,
            "rollback_count": len(rollback_results),
            "results": rollback_results
        }
        
    def get_provisioning_status(self, operation_id: int) -> Optional[ProvisioningOperation]:
        """
        Récupère le statut d'une opération de provisioning.
        
        Args:
            operation_id (int): ID de l'opération
            
        Returns:
            Optional[ProvisioningOperation]: Opération avec ses actions
        """
        return self.db.query(ProvisioningOperation).filter(
            ProvisioningOperation.id == operation_id
        ).first()
    
    def _send_user_notification(
        self,
        user_data: Dict[str, str],
        actions_results: List[ProvisioningAction],
        operation_id: int
    ):
        """
        Envoie une notification à l'utilisateur avec ses accès provisionnés
        
        Args:
            user_data: Données de l'utilisateur
            actions_results: Liste des actions de provisionnement
            operation_id: ID de l'opération
        """
        try:
            from .notification_service import get_notification_service
            
            # Construire la liste des applications provisionnées avec succès
            provisioned_apps = []
            for action in actions_results:
                if action.status == ActionStatus.SUCCESS.value:
                    app_info = {
                        'name': action.application,
                        'username': user_data.get('email'),
                        'role': user_data.get('job_title', 'Utilisateur'),
                        'permissions': 'Accès standard',
                        'url': self._get_app_url(action.application)
                    }
                    
                    # Ajouter le mot de passe temporaire si disponible
                    if action.details and 'password' in action.details:
                        app_info['temporary_password'] = action.details['password']
                    
                    provisioned_apps.append(app_info)
            
            if provisioned_apps:
                notification_service = get_notification_service()
                user_name = f"{user_data.get('first_name', '')} {user_data.get('last_name', '')}".strip()
                
                notification_service.send_provisioning_notification(
                    user_email=user_data['email'],
                    user_name=user_name or user_data['email'],
                    provisioned_apps=provisioned_apps,
                    operation_id=str(operation_id)
                )
                
                logger.info(f"📧 Notification envoyée à {user_data['email']} pour {len(provisioned_apps)} applications")
            
        except Exception as e:
            # Ne pas faire échouer le provisionnement si la notification échoue
            logger.error(f"Erreur envoi notification : {e}")
    
    def _get_app_url(self, app_name: str) -> str:
        """Retourne l'URL d'accès à une application"""
        app_urls = {
            'Keycloak': 'http://localhost:8180',
            'GitLab': 'http://localhost:8080/gitlab',
            'MidPoint': 'http://localhost:8080/midpoint',
            'Odoo': 'http://localhost:8069',
            'LDAP': 'ldap://localhost:389'
        }
        return app_urls.get(app_name, 'https://apps.aegis.local')
