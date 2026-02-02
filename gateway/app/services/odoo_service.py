"""
Service Odoo - Récupération des employés via XML-RPC API
"""
import xmlrpc.client
from typing import List, Dict, Optional
import logging
import os

# Charger .env manuellement pour les variables d'environnement
from dotenv import load_dotenv
load_dotenv()

logger = logging.getLogger(__name__)


class OdooService:
    """Service pour interagir avec l'API Odoo"""
    
    def __init__(
        self,
        url: str = None,
        db: str = None,
        username: str = None,
        password: str = None
    ):
        # Utiliser les variables d'environnement ou les valeurs par défaut
        self.url = url or os.getenv("ODOO_URL", "http://localhost:8069")
        self.db = db or os.getenv("ODOO_DB", "odoo")
        self.username = username or os.getenv("ODOO_USERNAME", "admin")
        self.password = password or os.getenv("ODOO_PASSWORD", "admin")
        self.uid: Optional[int] = None
        self.common = None
        self.models = None
    
    def connect(self) -> bool:
        """Établit la connexion à Odoo"""
        try:
            self.common = xmlrpc.client.ServerProxy(f"{self.url}/xmlrpc/2/common")
            self.uid = self.common.authenticate(self.db, self.username, self.password, {})
            
            if not self.uid:
                logger.error("Échec d'authentification Odoo")
                return False
            
            self.models = xmlrpc.client.ServerProxy(f"{self.url}/xmlrpc/2/object")
            logger.info(f"Connecté à Odoo (uid={self.uid})")
            return True
        except Exception as e:
            logger.error(f"Erreur connexion Odoo: {e}")
            return False
    
    def get_employees(self) -> List[Dict]:
        """Récupère tous les employés actifs depuis Odoo"""
        if not self.models:
            if not self.connect():
                return []
        
        try:
            # Recherche des employés
            employee_ids = self.models.execute_kw(
                self.db, self.uid, self.password,
                'hr.employee', 'search',
                [[['active', '=', True]]]
            )
            
            # Lecture des données
            employees = self.models.execute_kw(
                self.db, self.uid, self.password,
                'hr.employee', 'read',
                [employee_ids],
                {'fields': [
                    'id', 'name', 'work_email', 'job_title',
                    'department_id', 'parent_id', 'active'
                ]}
            )
            
            # Transformation au format attendu
            result = []
            for emp in employees:
                # Séparer prénom/nom
                name_parts = emp.get('name', '').split(' ', 1)
                first_name = name_parts[0] if name_parts else ''
                last_name = name_parts[1] if len(name_parts) > 1 else ''
                
                # Département
                dept = emp.get('department_id')
                dept_name = dept[1] if dept else 'Unknown'
                
                result.append({
                    'personalNumber': 1000 + emp['id'],
                    'givenName': first_name,
                    'familyName': last_name,
                    'email': emp.get('work_email') or f"{first_name.lower()}.{last_name.lower()}@example.com",
                    'department': dept_name,
                    'title': emp.get('job_title') or 'Employee',
                    'status': 'Active' if emp.get('active') else 'Inactive'
                })
            
            logger.info(f"Récupéré {len(result)} employés depuis Odoo")
            return result
            
        except Exception as e:
            logger.error(f"Erreur récupération employés: {e}")
            return []

    def update_csv(self, file_path: str = "/data/hr/hr_clean.csv") -> Dict:
        """Met à jour le fichier CSV avec les données d'Odoo"""
        employees = self.get_employees()
        if not employees:
            # Si on échoue, on renvoie une erreur mais on ne vide pas le CSV
            return {"success": False, "message": "Aucun employé récupéré d'Odoo ou erreur de connexion"}
            
        import csv
        from pathlib import Path
        
        try:
            # Essayer de créer le dossier si nécessaire
            path = Path(file_path)
            if not path.parent.exists():
                try:
                    path.parent.mkdir(parents=True, exist_ok=True)
                except PermissionError:
                    logger.warning(f"Impossible de créer le dossier pour {file_path}, tentative d'écriture directe.")

            fieldnames = ["personalNumber", "givenName", "familyName", "email", "department", "title", "status"]
            
            # Écriture du fichier (Écrasement complet car Odoo est la source de vérité)
            with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                for emp in employees:
                    # Filtrer les clés pour correspondre aux colonnes du CSV
                    row = {k: emp.get(k) for k in fieldnames}
                    writer.writerow(row)
            
            logger.info(f"Mise à jour réussie de {file_path} avec {len(employees)} employés")
            return {"success": True, "count": len(employees), "message": f"Fichier {file_path} mis à jour avec succès"}
            
        except Exception as e:
            logger.error(f"Erreur écriture CSV: {e}")
            return {"success": False, "message": str(e)}


# Singleton
_odoo_service: Optional[OdooService] = None


def get_odoo_service() -> OdooService:
    """Retourne l'instance singleton du service Odoo"""
    global _odoo_service
    if _odoo_service is None:
        _odoo_service = OdooService()
    return _odoo_service
