"""
Service de Synchronisation - Orchestre le flux Odoo → CSV → MidPoint
"""
import csv
import os
from typing import Dict, List, Optional
from datetime import datetime
import logging

from .odoo_service import get_odoo_service
from .midpoint_service import get_midpoint_service

logger = logging.getLogger(__name__)

CSV_PATH = "/data/hr/hr_clean.csv"


class SyncService:
    """Service d'orchestration de la synchronisation"""
    
    def __init__(self):
        self.odoo = get_odoo_service()
        self.midpoint = get_midpoint_service()
        self.last_sync: Optional[datetime] = None
        self.sync_stats: Dict = {}
    
    def export_odoo_to_csv(self) -> Dict:
        """Exporte les employés Odoo vers le fichier CSV"""
        logger.info("Début export Odoo → CSV")
        
        # Récupérer les employés depuis Odoo
        employees = self.odoo.get_employees()
        
        if not employees:
            return {
                "success": False,
                "error": "Aucun employé récupéré depuis Odoo",
                "count": 0
            }
        
        # Écrire le CSV
        try:
            os.makedirs(os.path.dirname(CSV_PATH), exist_ok=True)
            
            with open(CSV_PATH, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=[
                    'personalNumber', 'givenName', 'familyName',
                    'email', 'department', 'title', 'status'
                ])
                writer.writeheader()
                writer.writerows(employees)
            
            logger.info(f"CSV exporté: {len(employees)} employés")
            return {
                "success": True,
                "count": len(employees),
                "path": CSV_PATH
            }
            
        except Exception as e:
            logger.error(f"Erreur écriture CSV: {e}")
            return {
                "success": False,
                "error": str(e),
                "count": 0
            }
    
    def trigger_midpoint_import(self) -> Dict:
        """Déclenche l'import MidPoint depuis le CSV"""
        logger.info("Déclenchement import MidPoint")
        
        success = self.midpoint.trigger_hr_import_task()
        
        return {
            "success": success,
            "message": "Tâche d'import déclenchée" if success else "Échec déclenchement"
        }
    
    def full_sync(self) -> Dict:
        """
        Synchronisation complète :
        1. Export Odoo → CSV
        2. Trigger MidPoint Import Task
        """
        logger.info("=== Début synchronisation complète ===")
        start_time = datetime.now()
        
        results = {
            "timestamp": start_time.isoformat(),
            "steps": []
        }
        
        # Étape 1: Export Odoo → CSV
        export_result = self.export_odoo_to_csv()
        results["steps"].append({
            "step": "odoo_export",
            "result": export_result
        })
        
        if not export_result.get("success"):
            results["success"] = False
            results["error"] = "Échec export Odoo"
            return results
        
        # Étape 2: Import MidPoint
        import_result = self.trigger_midpoint_import()
        results["steps"].append({
            "step": "midpoint_import",
            "result": import_result
        })
        
        # Résultat final
        results["success"] = all(
            step["result"].get("success") for step in results["steps"]
        )
        results["duration_seconds"] = (datetime.now() - start_time).total_seconds()
        
        self.last_sync = start_time
        self.sync_stats = results
        
        logger.info(f"=== Synchronisation terminée: {'OK' if results['success'] else 'ÉCHEC'} ===")
        return results
    
    def get_status(self) -> Dict:
        """Retourne le statut du service de synchronisation"""
        return {
            "odoo_connected": self.odoo.connect(),
            "midpoint_connected": self.midpoint.test_connection(),
            "last_sync": self.last_sync.isoformat() if self.last_sync else None,
            "last_sync_stats": self.sync_stats
        }


# Singleton
_sync_service: Optional[SyncService] = None


def get_sync_service() -> SyncService:
    """Retourne l'instance singleton du service de sync"""
    global _sync_service
    if _sync_service is None:
        _sync_service = SyncService()
    return _sync_service
