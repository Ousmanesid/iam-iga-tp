"""
Service pour interagir avec Odoo via XML-RPC
"""

import xmlrpc.client
from typing import Optional, List, Dict, Any
import structlog

from ..config import settings

logger = structlog.get_logger()


class OdooService:
    """Service pour les opérations Odoo"""
    
    def __init__(self):
        self.url = settings.odoo_url
        self.db = settings.odoo_db
        self.username = settings.odoo_user
        self.password = settings.odoo_password
        self.uid = None
        self.common = None
        self.models = None
    
    def connect(self) -> bool:
        """Établit la connexion avec Odoo"""
        try:
            self.common = xmlrpc.client.ServerProxy(f'{self.url}/xmlrpc/2/common')
            self.uid = self.common.authenticate(self.db, self.username, self.password, {})
            
            if not self.uid:
                logger.error("Odoo authentication failed")
                return False
            
            self.models = xmlrpc.client.ServerProxy(f'{self.url}/xmlrpc/2/object')
            logger.info("Connected to Odoo", uid=self.uid)
            return True
            
        except Exception as e:
            logger.error("Odoo connection failed", error=str(e))
            return False
    
    def _execute(self, model: str, method: str, *args, **kwargs) -> Any:
        """Exécute une méthode sur un modèle Odoo"""
        if not self.uid:
            self.connect()
        return self.models.execute_kw(
            self.db, self.uid, self.password,
            model, method, args, kwargs
        )
    
    def get_employees(self) -> List[Dict[str, Any]]:
        """Récupère tous les employés actifs depuis Odoo"""
        try:
            if not self.uid:
                self.connect()
            
            # Récupérer les employés
            employee_ids = self._execute('hr.employee', 'search', [('active', '=', True)])
            
            employees = self._execute('hr.employee', 'read', employee_ids, 
                ['id', 'name', 'work_email', 'department_id', 'job_title', 'active'])
            
            result = []
            for emp in employees:
                dept = emp.get('department_id')
                dept_name = dept[1] if isinstance(dept, (list, tuple)) and len(dept) > 1 else str(dept) if dept else None
                
                # Parser prénom/nom depuis le nom complet
                name_parts = emp.get('name', '').split(' ', 1)
                first_name = name_parts[0] if name_parts else ''
                last_name = name_parts[1] if len(name_parts) > 1 else ''
                
                result.append({
                    'employee_id': str(emp.get('id')),
                    'name': emp.get('name'),
                    'first_name': first_name,
                    'last_name': last_name,
                    'email': emp.get('work_email'),
                    'department': dept_name,
                    'job_title': emp.get('job_title'),
                    'active': emp.get('active', True)
                })
            
            logger.info("Fetched employees from Odoo", count=len(result))
            return result
            
        except Exception as e:
            logger.error("Failed to get Odoo employees", error=str(e))
            return []
    
    def get_employee_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Récupère un employé par son email"""
        employees = self.get_employees()
        for emp in employees:
            if emp.get('email') == email:
                return emp
        return None


# Mapping département → rôle
DEPARTMENT_ROLE_MAPPING = {
    'commercial': ['AGENT_COMMERCIAL'],
    'sales': ['AGENT_COMMERCIAL'],
    'ventes': ['AGENT_COMMERCIAL'],
    'rh': ['RH_ASSISTANT'],
    'ressources humaines': ['RH_ASSISTANT'],
    'human resources': ['RH_ASSISTANT'],
    'hr': ['RH_ASSISTANT'],
    'comptabilité': ['COMPTABLE'],
    'finance': ['COMPTABLE'],
    'accounting': ['COMPTABLE'],
    'it': ['IT_SUPPORT'],
    'informatique': ['IT_SUPPORT'],
    'r&d': ['USER'],
    'research': ['USER'],
    'management': ['MANAGER'],
    'direction': ['DIRECTOR'],
}


def get_roles_for_department(department: str) -> List[str]:
    """Détermine les rôles à assigner selon le département"""
    if not department:
        return ['USER']
    
    dept_lower = department.lower()
    
    for key, roles in DEPARTMENT_ROLE_MAPPING.items():
        if key in dept_lower:
            return roles + ['USER']  # Toujours ajouter le rôle de base
    
    return ['USER']


# Instance singleton
odoo_service = OdooService()
