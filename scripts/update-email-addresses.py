#!/usr/bin/env python3
"""
Script pour mettre à jour les adresses email dans les workflows N8N existants
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

# Workflows à mettre à jour
WORKFLOWS_TO_UPDATE = [
    "4pdplQ5mM6k1GULp",  # pre-provision-simple
    "8Ldn7ERVqQwBVqBG",  # post-provision
    "Clrhbmw23vmofy1t",  # chatbot-action
    "tlR3A5daKY6qNUZr",  # pre-provision-multi.json
]


def get_n8n_headers() -> dict:
    """Retourne les headers pour l'authentification N8N"""
    if not N8N_API_KEY:
        raise ValueError("N8N_API_KEY n'est pas défini")
    return {"X-N8N-API-KEY": N8N_API_KEY}


def update_workflow_emails(workflow_id: str) -> bool:
    """Met à jour les adresses email dans un workflow"""
    try:
        # Récupérer le workflow
        response = requests.get(
            f"{N8N_URL}/api/v1/workflows/{workflow_id}",
            headers=get_n8n_headers(),
            timeout=10
        )
        response.raise_for_status()
        workflow = response.json().get("data", {})
        
        # Mettre à jour les nodes email
        nodes = workflow.get("nodes", [])
        updated = False
        
        for node in nodes:
            if node.get("type") == "n8n-nodes-base.emailSend":
                params = node.get("parameters", {})
                old_from = params.get("fromEmail", "")
                old_to = params.get("toEmail", "")
                
                # Mettre à jour fromEmail
                if old_from and old_from != FROM_EMAIL:
                    params["fromEmail"] = FROM_EMAIL
                    updated = True
                    print(f"  📧 From: {old_from} → {FROM_EMAIL}")
                
                # Mettre à jour toEmail (seulement si c'est une adresse fixe)
                if old_to and "@example.com" in old_to and old_to != TO_EMAIL:
                    # Remplacer les adresses example.com par défaut
                    if "admin@example.com" in old_to:
                        params["toEmail"] = old_to.replace("admin@example.com", TO_EMAIL)
                        updated = True
                        print(f"  📧 To: {old_to} → {params['toEmail']}")
                    elif old_to == "admin@example.com":
                        params["toEmail"] = TO_EMAIL
                        updated = True
                        print(f"  📧 To: {old_to} → {TO_EMAIL}")
        
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
        else:
            print("  ℹ️  Aucune mise à jour nécessaire")
            return True
            
    except Exception as e:
        print(f"  ❌ Erreur: {e}")
        return False


def main():
    """Fonction principale"""
    print("\n" + "=" * 60)
    print("  MISE À JOUR DES ADRESSES EMAIL")
    print("=" * 60 + "\n")
    print(f"📧 Email expéditeur: {FROM_EMAIL}")
    print(f"📧 Email destinataire par défaut: {TO_EMAIL}\n")
    
    if not N8N_API_KEY:
        print("❌ N8N_API_KEY n'est pas défini")
        sys.exit(1)
    
    success_count = 0
    
    for workflow_id in WORKFLOWS_TO_UPDATE:
        print(f"📋 Mise à jour du workflow {workflow_id}...")
        if update_workflow_emails(workflow_id):
            print("  ✅ Mis à jour\n")
            success_count += 1
        else:
            print("  ❌ Échec\n")
    
    print("=" * 60)
    print(f"✅ {success_count}/{len(WORKFLOWS_TO_UPDATE)} workflows mis à jour")
    print("=" * 60)


if __name__ == "__main__":
    main()







