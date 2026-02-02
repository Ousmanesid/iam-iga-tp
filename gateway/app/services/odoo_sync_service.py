"""
Service de synchronisation bidirectionnelle Odoo ↔ Aegis Gateway

Ce service :
1. Récupère les employés d'Odoo
2. Les synchronise dans la base locale d'Aegis Gateway
3. Crée automatiquement les enregistrements ProvisionedUser
4. Log les événements dans le système d'audit

Note: Utilise les rôles de MidPoint via role_mapper
"""
import logging
from typing import List, Dict, Optional
from datetime import datetime
from sqlalchemy.orm import Session

from .odoo_service import get_odoo_service
from .audit_service import get_audit_service
from ..database.models import ProvisionedUser, ProvisioningOperation, OperationStatus as UserStatus
from ..core.role_mapper import get_role_details, get_applications_for_job_title

logger = logging.getLogger(__name__)


class OdooSyncService:
    """Service pour synchroniser les utilisateurs Odoo vers Aegis Gateway"""
    
    def __init__(self, db: Session):
        self.db = db
        self.odoo = get_odoo_service()
        self.audit = get_audit_service(db)
        
    def sync_all_employees(self) -> Dict:
        """
        Synchronise tous les employés d'Odoo vers la base Aegis
        
        Returns:
            Dict: Statistiques de synchronisation
        """
        logger.info("🔄 Début synchronisation Odoo → Aegis Gateway")
        
        # Log audit : début de sync
        self.audit.log_sync_started("Odoo")
        
        # 1. Connexion à Odoo
        if not self.odoo.connect():
            logger.error("❌ Impossible de se connecter à Odoo")
            self.audit.log_sync_failed("Odoo", "Connexion Odoo échouée")
            return {
                "success": False,
                "error": "Connexion Odoo échouée",
                "created": 0,
                "updated": 0,
                "skipped": 0
            }
        
        # 2. Récupérer tous les employés
        employees = self.odoo.get_employees()
        
        if not employees:
            logger.warning("⚠️ Aucun employé trouvé dans Odoo")
            self.audit.log_sync_completed("Odoo", 0, 0, 0)
            return {
                "success": True,
                "created": 0,
                "updated": 0,
                "skipped": 0,
                "message": "Aucun employé dans Odoo"
            }
        
        logger.info(f"📊 {len(employees)} employés récupérés depuis Odoo")
        
        # 3. Synchroniser chaque employé
        stats = {
            "created": 0,
            "updated": 0,
            "skipped": 0,
            "errors": []
        }
        
        for emp in employees:
            try:
                result = self._sync_employee(emp)
                stats[result] += 1
            except Exception as e:
                logger.error(f"❌ Erreur sync {emp.get('email')}: {e}")
                stats["errors"].append({
                    "email": emp.get("email"),
                    "error": str(e)
                })
        
        # 4. Commit final
        self.db.commit()
        
        # Log audit : fin de sync
        self.audit.log_sync_completed(
            "Odoo",
            created=stats['created'],
            updated=stats['updated'],
            skipped=stats['skipped']
        )
        
        logger.info(f"✅ Synchronisation terminée: {stats['created']} créés, "
                   f"{stats['updated']} mis à jour, {stats['skipped']} ignorés")
        
        return {
            "success": True,
            "total": len(employees),
            **stats
        }
        
        return {
            "success": True,
            "total": len(employees),
            **stats
        }
    
    def _sync_employee(self, employee: Dict) -> str:
        """
        Synchronise un employé spécifique
        
        Args:
            employee: Données employé depuis Odoo
            
        Returns:
            str: "created", "updated", ou "skipped"
        """
        email = employee.get("email")
        
        if not email:
            logger.warning(f"⚠️ Employé sans email: {employee.get('givenName')} {employee.get('familyName')}")
            return "skipped"
        
        # Chercher si l'utilisateur existe déjà
        existing_user = self.db.query(ProvisionedUser).filter(
            ProvisionedUser.email == email
        ).first()
        
        if existing_user:
            # Mise à jour si nécessaire
            return self._update_user(existing_user, employee)
        else:
            # Création
            return self._create_user(employee)
    
    def _create_user(self, employee: Dict) -> str:
        """Crée un nouvel utilisateur dans la base Aegis"""
        
        # Récupérer le job_title et chercher le rôle correspondant dans MidPoint
        job_title = employee.get("title", "")
        role_details = get_role_details(job_title) if job_title else None
        
        # Déterminer le statut
        status = UserStatus.SUCCESS if employee.get("status") == "active" else UserStatus.FAILED
        
        # Créer l'utilisateur
        user = ProvisionedUser(
            email=employee["email"],
            first_name=employee.get("givenName", ""),
            last_name=employee.get("familyName", ""),
            job_title=job_title,
            department=employee.get("department", ""),
            role=role_details.get('name') if role_details else job_title,  # Nom du rôle MidPoint ou job_title
            status=status,
            source="odoo_sync",  # Important : marqueur de source
            created_at=datetime.utcnow()
        )
        
        self.db.add(user)
        self.db.flush()  # Pour obtenir l'ID
        
        # Créer une opération de provisioning pour apparaître dans le Dashboard
        operation = ProvisioningOperation(
            user_id=user.id,
            status=UserStatus.SUCCESS.value,
            trigger="odoo_sync",
            started_at=datetime.utcnow(),
            completed_at=datetime.utcnow(),
            total_actions=1,
            successful_actions=1,
            failed_actions=0
        )
        
        self.db.add(operation)
        
        # Log d'audit pour la création
        user_name = f"{employee.get('givenName', '')} {employee.get('familyName', '')}"
        self.audit.log_user_created(
            user_email=employee["email"],
            user_name=user_name.strip(),
            source="Odoo"
        )
        
        logger.info(f"✨ Créé: {employee['email']} ({job_title} → {mapped_role.value if mapped_role else 'N/A'})")
        
        return "created"
    
    def _update_user(self, existing_user: ProvisionedUser, employee: Dict) -> str:
        """Met à jour un utilisateur existant"""
        
        updated = False
        
        # Vérifier les changements
        if existing_user.first_name != employee.get("givenName", ""):
            existing_user.first_name = employee.get("givenName", "")
            updated = True
            
        if existing_user.last_name != employee.get("familyName", ""):
            existing_user.last_name = employee.get("familyName", "")
            updated = True
        
        job_title = employee.get("title", "")
        if existing_user.job_title != job_title:
            existing_user.job_title = job_title
            # Re-mapper le rôle si le titre change - chercher dans MidPoint
            role_details = get_role_details(job_title) if job_title else None
            if role_details:
                existing_user.role = role_details.get('name')
            updated = True
        
        if existing_user.department != employee.get("department", ""):
            existing_user.department = employee.get("department", "")
            updated = True
        
        # Vérifier le statut
        new_status = UserStatus.SUCCESS if employee.get("status") == "active" else UserStatus.FAILED
        if existing_user.status != new_status:
            existing_user.status = new_status
            updated = True
        
        if updated:
            existing_user.last_modified = datetime.utcnow()
            
            # Créer une opération pour la mise à jour
            operation = ProvisioningOperation(
                user_id=existing_user.id,
                status=UserStatus.SUCCESS.value,
                trigger="odoo_sync",
                started_at=datetime.utcnow(),
                completed_at=datetime.utcnow(),
                total_actions=1,
                successful_actions=1,
                failed_actions=0
            )
            
            self.db.add(operation)
            
            # Log d'audit pour la mise à jour
            user_name = f"{employee.get('givenName', '')} {employee.get('familyName', '')}"
            self.audit.log_user_updated(
                user_email=employee['email'],
                user_name=user_name.strip(),
                changes={"updated": True}
            )
            
            logger.info(f"🔄 Mis à jour: {employee['email']}")
            return "updated"
        else:
            return "skipped"
    
    def sync_single_employee(self, employee_id: int) -> Dict:
        """
        Synchronise un seul employé depuis Odoo (pour webhook)
        
        Args:
            employee_id: ID de l'employé dans Odoo
            
        Returns:
            Dict: Résultat de la synchronisation
        """
        logger.info(f"🔄 Synchronisation employé Odoo ID: {employee_id}")
        
        if not self.odoo.connect():
            return {
                "success": False,
                "error": "Connexion Odoo échouée"
            }
        
        # Récupérer l'employé spécifique depuis Odoo
        try:
            employee_data = self.odoo.models.execute_kw(
                self.odoo.db, self.odoo.uid, self.odoo.password,
                'hr.employee', 'read',
                [[employee_id]],
                {'fields': [
                    'id', 'name', 'work_email', 'job_title',
                    'department_id', 'parent_id', 'active'
                ]}
            )
            
            if not employee_data:
                return {
                    "success": False,
                    "error": f"Employé {employee_id} non trouvé"
                }
            
            emp = employee_data[0]
            
            # Transformer au format attendu
            transformed = {
                "personalNumber": str(emp['id']),
                "givenName": emp['name'].split()[0] if emp['name'] else "",
                "familyName": " ".join(emp['name'].split()[1:]) if emp['name'] else "",
                "email": emp.get('work_email', ''),
                "department": emp['department_id'][1] if emp.get('department_id') else "",
                "title": emp.get('job_title', ''),
                "status": "active" if emp.get('active') else "inactive"
            }
            
            # Synchroniser
            result = self._sync_employee(transformed)
            self.db.commit()
            
            return {
                "success": True,
                "action": result,
                "employee": transformed
            }
            
        except Exception as e:
            logger.error(f"❌ Erreur sync employé {employee_id}: {e}")
            return {
                "success": False,
                "error": str(e)
            }


def get_odoo_sync_service(db: Session) -> OdooSyncService:
    """Factory pour créer le service de sync"""
    return OdooSyncService(db)
