#!/usr/bin/env python3
"""
Importe un workflow n8n et l'active automatiquement.

Usage:
  python3 setup_n8n_workflow.py <workflow.json>
  python3 setup_n8n_workflow.py ../config/n8n/workflows/sync-odoo-simple.json
"""
import json
import requests
import sys
import time
import logging

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

N8N_URL = "http://localhost:5678"
API_ENDPOINT = f"{N8N_URL}/api/v1"
N8N_USER = "admin"
N8N_PASSWORD = "admin123"

def get_auth():
    """Retourne les credentials pour authentification"""
    from requests.auth import HTTPBasicAuth
    return HTTPBasicAuth(N8N_USER, N8N_PASSWORD)

def wait_for_n8n():
    """Attend que n8n soit disponible"""
    max_retries = 30
    for i in range(max_retries):
        try:
            response = requests.get(f"{N8N_URL}/index.html", timeout=5)
            if response.status_code == 200:
                logger.info("✅ n8n is available")
                return True
        except:
            pass
        logger.info(f"⏳ Waiting for n8n... ({i+1}/{max_retries})")
        time.sleep(2)
    
    return False

def import_workflow(workflow_file):
    """Importe un workflow dans n8n"""
    try:
        with open(workflow_file, 'r') as f:
            workflow = json.load(f)
        
        logger.info(f"📥 Importing workflow: {workflow['name']}")
        
        # Créer le workflow
        response = requests.post(
            f"{API_ENDPOINT}/workflows",
            json=workflow,
            auth=get_auth(),
            timeout=10
        )
        
        if response.status_code == 201:
            workflow_id = response.json()['id']
            logger.info(f"✅ Workflow created with ID: {workflow_id}")
            
            # Activer le workflow
            activate_response = requests.patch(
                f"{API_ENDPOINT}/workflows/{workflow_id}",
                json={"active": True},
                auth=get_auth(),
                timeout=10
            )
            
            if activate_response.status_code == 200:
                logger.info(f"✅ Workflow activated!")
                logger.info(f"📊 Workflow URL: {N8N_URL}/workflow/{workflow_id}")
                return True
            else:
                logger.warning(f"⚠️ Could not activate workflow: {activate_response.text}")
                return False
        else:
            logger.error(f"❌ Failed to create workflow: {response.text}")
            return False
    
    except FileNotFoundError:
        logger.error(f"❌ File not found: {workflow_file}")
        return False
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        return False

def main():
    if len(sys.argv) < 2:
        workflow_file = "/srv/projet/iam-iga-tp/config/n8n/workflows/sync-odoo-simple.json"
        logger.info(f"Usage: python3 {sys.argv[0]} <workflow.json>")
        logger.info(f"Using default: {workflow_file}")
    else:
        workflow_file = sys.argv[1]
    
    logger.info(f"🔧 Setting up n8n workflow...")
    logger.info(f"   n8n URL: {N8N_URL}")
    
    if not wait_for_n8n():
        logger.error("❌ n8n is not available")
        return False
    
    if import_workflow(workflow_file):
        logger.info("""
✅ Workflow setup complete!

La synchronisation Odoo → Gateway se fera automatiquement:
  • Toutes les 5 minutes
  • Récupère les employés depuis Odoo
  • Envoie les changements à la Gateway
  • Met à jour le CSV hr_clean.csv

Vous pouvez suivre l'exécution dans l'interface n8n.
        """)
        return True
    
    return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
