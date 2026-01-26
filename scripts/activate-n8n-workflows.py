#!/usr/bin/env python3
"""
Script pour activer les workflows N8N
"""

import os
import sys
import requests
from typing import List, Dict, Any

# Configuration
N8N_URL = os.getenv("N8N_URL", "http://localhost:5678")
N8N_API_KEY = os.getenv("N8N_API_KEY", "")

# Workflows à activer
WORKFLOWS_TO_ACTIVATE = [
    "Approval Callback (Simple)",
    "Multi-Approval Callback",
    "Review Callback (Post-Provision)",
    "Chatbot Approval Callback",
]


def get_n8n_headers() -> dict:
    """Retourne les headers pour l'authentification N8N"""
    if not N8N_API_KEY:
        raise ValueError("N8N_API_KEY n'est pas défini")
    return {"X-N8N-API-KEY": N8N_API_KEY}


def get_workflows() -> List[Dict[str, Any]]:
    """Récupère tous les workflows"""
    try:
        response = requests.get(
            f"{N8N_URL}/api/v1/workflows",
            headers=get_n8n_headers(),
            timeout=10
        )
        response.raise_for_status()
        return response.json().get("data", [])
    except Exception as e:
        print(f"❌ Erreur lors de la récupération des workflows: {e}")
        return []


def activate_workflow(workflow_id: str) -> bool:
    """Active un workflow"""
    try:
        response = requests.post(
            f"{N8N_URL}/api/v1/workflows/{workflow_id}/activate",
            headers=get_n8n_headers(),
            timeout=10
        )
        response.raise_for_status()
        return True
    except Exception as e:
        print(f"⚠️  Erreur lors de l'activation: {e}")
        return False


def main():
    """Fonction principale"""
    print("🚀 Activation des workflows N8N\n")
    
    if not N8N_API_KEY:
        print("❌ N8N_API_KEY n'est pas défini")
        sys.exit(1)
    
    workflows = get_workflows()
    workflows_dict = {w["name"]: w for w in workflows}
    
    activated = 0
    already_active = 0
    not_found = 0
    
    for workflow_name in WORKFLOWS_TO_ACTIVATE:
        if workflow_name not in workflows_dict:
            print(f"⚠️  Workflow '{workflow_name}' introuvable")
            not_found += 1
            continue
        
        workflow = workflows_dict[workflow_name]
        workflow_id = workflow["id"]
        
        if workflow.get("active", False):
            print(f"✅ '{workflow_name}' est déjà actif (ID: {workflow_id})")
            already_active += 1
        else:
            print(f"📥 Activation de '{workflow_name}' (ID: {workflow_id})...")
            if activate_workflow(workflow_id):
                print(f"✅ '{workflow_name}' activé")
                activated += 1
            else:
                print(f"❌ Échec de l'activation de '{workflow_name}'")
    
    print("\n" + "=" * 50)
    print(f"✅ Activés: {activated}")
    print(f"✅ Déjà actifs: {already_active}")
    print(f"⚠️  Introuvables: {not_found}")
    print("=" * 50)


if __name__ == "__main__":
    main()







