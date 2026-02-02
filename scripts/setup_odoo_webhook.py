#!/usr/bin/env python3
"""
Setup webhook dans Odoo pour synchroniser automatiquement les employés vers le CSV.

Usage:
  python3 setup_odoo_webhook.py
"""
import xmlrpc.client
import json
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
ODOO_URL = "http://odoo:8069"
ODOO_DB = "odoo"
ODOO_USER = "admin"
ODOO_PASSWORD = "admin"
GATEWAY_URL = "http://gateway:8000/api/v1/odoo/webhook"

def connect_odoo():
    """Connexion à Odoo"""
    try:
        common = xmlrpc.client.ServerProxy(f"{ODOO_URL}/xmlrpc/2/common")
        uid = common.authenticate(ODOO_DB, ODOO_USER, ODOO_PASSWORD, {})
        
        if not uid:
            logger.error("❌ Échec d'authentification Odoo")
            return None, None
        
        models = xmlrpc.client.ServerProxy(f"{ODOO_URL}/xmlrpc/2/object")
        logger.info(f"✅ Connecté à Odoo (uid={uid})")
        return uid, models
    except Exception as e:
        logger.error(f"❌ Erreur connexion Odoo: {e}")
        return None, None

def install_webhooks(uid, models):
    """Installe les webhooks pour hr.employee create/write"""
    try:
        # Vérifier si le module webhook existe
        webhook_module = models.execute_kw(
            ODOO_DB, uid, ODOO_PASSWORD,
            'ir.module.module', 'search_read',
            [[['name', '=', 'webhook']]],
            {'fields': ['name', 'state']}
        )
        
        if webhook_module and webhook_module[0]['state'] == 'installed':
            logger.info("✅ Module 'webhook' trouvé et installé")
            setup_webhook_records(uid, models)
        else:
            logger.info("⚠️ Module 'webhook' non trouvé. Tentative d'utilisation de ir.cron...")
            setup_automated_webhook(uid, models)
            
    except Exception as e:
        logger.error(f"❌ Erreur installation webhooks: {e}")
        return False
    
    return True

def setup_webhook_records(uid, models):
    """Configure les webhooks via le module webhook d'Odoo"""
    try:
        # Créer webhook pour CREATE
        webhook_data = {
            'name': 'Sync Employee to Gateway (Create)',
            'event': 'create',
            'model_id': models.execute_kw(
                ODOO_DB, uid, ODOO_PASSWORD,
                'ir.model', 'search',
                [[['model', '=', 'hr.employee']]],
                {'limit': 1}
            )[0] if models.execute_kw(
                ODOO_DB, uid, ODOO_PASSWORD,
                'ir.model', 'search',
                [[['model', '=', 'hr.employee']]],
                {'limit': 1}
            ) else None,
            'url': GATEWAY_URL,
            'active': True,
        }
        
        webhook_id = models.execute_kw(
            ODOO_DB, uid, ODOO_PASSWORD,
            'webhook', 'create',
            [webhook_data]
        )
        logger.info(f"✅ Webhook CREATE créé (ID: {webhook_id})")
        
        # Créer webhook pour UPDATE
        webhook_data['name'] = 'Sync Employee to Gateway (Update)'
        webhook_data['event'] = 'write'
        
        webhook_id = models.execute_kw(
            ODOO_DB, uid, ODOO_PASSWORD,
            'webhook', 'create',
            [webhook_data]
        )
        logger.info(f"✅ Webhook UPDATE créé (ID: {webhook_id})")
        
    except Exception as e:
        logger.error(f"❌ Erreur création webhooks: {e}")

def setup_automated_webhook(uid, models):
    """Alternative: Configure une tâche cron qui appelle le webhook"""
    try:
        cron_code = """
import requests
import json

odoo = self.env
employees = odoo['hr.employee'].search([('write_date', '>=', datetime.now() - timedelta(minutes=5))])

for emp in employees:
    payload = {
        'event': 'update',
        'employee_id': emp.id,
        'data': {
            'name': emp.name,
            'work_email': emp.work_email,
            'job_title': emp.job_title,
            'department_id': emp.department_id.name if emp.department_id else 'Unknown',
        }
    }
    try:
        requests.post('""" + GATEWAY_URL + """', json=payload, timeout=5)
    except:
        pass
"""
        
        cron_data = {
            'name': 'Sync Employees to Gateway',
            'model_id': models.execute_kw(
                ODOO_DB, uid, ODOO_PASSWORD,
                'ir.model', 'search_read',
                [[['model', '=', 'ir.cron']]],
                {'limit': 1}
            )[0]['id'] if models.execute_kw(
                ODOO_DB, uid, ODOO_PASSWORD,
                'ir.model', 'search_read',
                [[['model', '=', 'ir.cron']]],
                {'limit': 1}
            ) else None,
            'interval_number': 5,
            'interval_type': 'minutes',
            'numbercall': -1,
            'active': True,
            'code': cron_code,
        }
        
        cron_id = models.execute_kw(
            ODOO_DB, uid, ODOO_PASSWORD,
            'ir.cron', 'create',
            [cron_data]
        )
        logger.info(f"✅ Tâche CRON créée pour sync tous les 5 minutes (ID: {cron_id})")
        
    except Exception as e:
        logger.error(f"❌ Erreur création CRON: {e}")

def main():
    logger.info("🔧 Configuration des webhooks Odoo → Gateway...")
    logger.info(f"   Odoo: {ODOO_URL}")
    logger.info(f"   Gateway: {GATEWAY_URL}")
    
    uid, models = connect_odoo()
    if not uid:
        return False
    
    success = install_webhooks(uid, models)
    if success:
        logger.info("✅ Configuration des webhooks réussie!")
        logger.info("""
📝 Webhook configuré pour synchroniser automatiquement:
   - Chaque NOUVEL employé créé dans Odoo
   - Chaque MODIFICATION d'employé
   
Le CSV hr_clean.csv sera mis à jour automatiquement.
        """)
    
    return success

if __name__ == "__main__":
    import sys
    from datetime import datetime, timedelta
    success = main()
    sys.exit(0 if success else 1)
