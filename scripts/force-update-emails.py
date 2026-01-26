#!/usr/bin/env python3
"""
Script pour forcer la mise à jour des adresses email dans tous les workflows
"""

import os
import sys
import requests
import json

# Configuration
N8N_URL = os.getenv("N8N_URL", "http://localhost:5678")
N8N_API_KEY = os.getenv("N8N_API_KEY", "")
FROM_EMAIL = "sidibe.osm@gmail.com"
TO_EMAIL = "sidibeousmane2005@gmail.com"


def get_n8n_headers() -> dict:
    """Retourne les headers pour l'authentification N8N"""
    if not N8N_API_KEY:
        raise ValueError("N8N_API_KEY n'est pas défini")
    return {"X-N8N-API-KEY": N8N_API_KEY}


def update_workflow(workflow_id: str, workflow_name: str) -> bool:
    """Met à jour un workflow"""
    try:
        # Récupérer le workflow
        response = requests.get(
            f"{N8N_URL}/api/v1/workflows/{workflow_id}",
            headers=get_n8n_headers(),
            timeout=10
        )
        response.raise_for_status()
        workflow = response.json().get("data", {})
        
        nodes = workflow.get("nodes", [])
        updated = False
        
        for node in nodes:
            if node.get("type") == "n8n-nodes-base.emailSend":
                params = node.get("parameters", {})
                
                # Mettre à jour fromEmail
                if params.get("fromEmail"):
                    old_from = params.get("fromEmail")
                    if old_from != FROM_EMAIL:
                        params["fromEmail"] = FROM_EMAIL
                        updated = True
                        print(f"    From: {old_from} → {FROM_EMAIL}")
                
                # Mettre à jour toEmail
                if params.get("toEmail"):
                    old_to = params.get("toEmail")
                    # Remplacer les adresses par défaut
                    if "admin@example.com" in old_to:
                        new_to = old_to.replace("admin@example.com", TO_EMAIL)
                        params["toEmail"] = new_to
                        updated = True
                        print(f"    To: {old_to} → {new_to}")
                    elif old_to == "admin@example.com":
                        params["toEmail"] = TO_EMAIL
                        updated = True
                        print(f"    To: {old_to} → {TO_EMAIL}")
        
        if updated:
            # Mettre à jour le workflow
            update_data = {
                "name": workflow.get("name"),
                "nodes": nodes,
                "connections": workflow.get("connections", {}),
                "settings": workflow.get("settings", {}),
                "staticData": workflow.get("staticData"),
            }
            
            response = requests.put(
                f"{N8N_URL}/api/v1/workflows/{workflow_id}",
                json=update_data,
                headers=get_n8n_headers(),
                timeout=30
            )
            response.raise_for_status()
            return True
        return False
        
    except Exception as e:
        print(f"    ❌ Erreur: {e}")
        return False


def main():
    """Fonction principale"""
    print("\n" + "=" * 60)
    print("  MISE À JOUR FORCÉE DES ADRESSES EMAIL")
    print("=" * 60 + "\n")
    
    # Récupérer tous les workflows
    try:
        response = requests.get(
            f"{N8N_URL}/api/v1/workflows",
            headers=get_n8n_headers(),
            timeout=10
        )
        response.raise_for_status()
        workflows = response.json().get("data", [])
    except Exception as e:
        print(f"❌ Erreur: {e}")
        sys.exit(1)
    
    # Filtrer les workflows avec email
    email_workflows = []
    for wf in workflows:
        nodes = wf.get("nodes", [])
        if any(n.get("type") == "n8n-nodes-base.emailSend" for n in nodes):
            email_workflows.append((wf.get("id"), wf.get("name")))
    
    print(f"📋 {len(email_workflows)} workflow(s) avec email trouvé(s)\n")
    
    updated_count = 0
    for workflow_id, workflow_name in email_workflows:
        print(f"📧 {workflow_name} ({workflow_id})")
        if update_workflow(workflow_id, workflow_name):
            print("  ✅ Mis à jour\n")
            updated_count += 1
        else:
            print("  ℹ️  Déjà à jour\n")
    
    print("=" * 60)
    print(f"✅ {updated_count} workflow(s) mis à jour")
    print("=" * 60)


if __name__ == "__main__":
    main()







