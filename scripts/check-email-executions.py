#!/usr/bin/env python3
"""
Script pour vérifier les exécutions récentes des workflows d'email
"""

import os
import sys
import requests
from datetime import datetime, timedelta
from typing import List, Dict, Any

# Configuration
N8N_URL = os.getenv("N8N_URL", "http://localhost:5678")
N8N_API_KEY = os.getenv("N8N_API_KEY", "")


def get_n8n_headers() -> dict:
    """Retourne les headers pour l'authentification N8N"""
    if not N8N_API_KEY:
        raise ValueError("N8N_API_KEY n'est pas défini")
    return {"X-N8N-API-KEY": N8N_API_KEY}


def get_workflow_executions(workflow_id: str, limit: int = 5) -> List[Dict[str, Any]]:
    """Récupère les exécutions récentes d'un workflow"""
    try:
        # Note: L'API N8N peut varier selon la version
        # On essaie d'abord avec l'endpoint standard
        response = requests.get(
            f"{N8N_URL}/api/v1/executions",
            headers=get_n8n_headers(),
            params={"workflowId": workflow_id, "limit": limit},
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            return data.get("data", [])
        else:
            # Essayer un autre format
            return []
    except Exception as e:
        print(f"⚠️  Erreur lors de la récupération des exécutions: {e}")
        return []


def check_workflow_status(workflow_id: str, workflow_name: str):
    """Vérifie le statut d'un workflow et ses dernières exécutions"""
    print(f"\n📋 {workflow_name} (ID: {workflow_id})")
    
    executions = get_workflow_executions(workflow_id, limit=3)
    
    if not executions:
        print("   ⚠️  Aucune exécution récente trouvée (normal si le workflow vient d'être exécuté)")
        return
    
    print(f"   📊 {len(executions)} exécution(s) récente(s):")
    for exec in executions[:3]:
        status = exec.get("finished", False)
        status_icon = "✅" if status else "⏳"
        print(f"      {status_icon} Status: {exec.get('mode', 'N/A')} - Finished: {status}")


def main():
    """Fonction principale"""
    print("\n" + "=" * 60)
    print("  VÉRIFICATION DES EXÉCUTIONS D'EMAILS")
    print("=" * 60)
    
    if not N8N_API_KEY:
        print("\n❌ N8N_API_KEY n'est pas défini")
        sys.exit(1)
    
    # Workflows avec email
    email_workflows = [
        ("4pdplQ5mM6k1GULp", "pre-provision-simple"),
        ("8Ldn7ERVqQwBVqBG", "post-provision"),
        ("Clrhbmw23vmofy1t", "chatbot-action"),
    ]
    
    print("\n🔍 Vérification des exécutions récentes...\n")
    
    for workflow_id, workflow_name in email_workflows:
        check_workflow_status(workflow_id, workflow_name)
    
    print("\n" + "=" * 60)
    print("💡 Pour voir les logs détaillés:")
    print("   1. Allez sur http://localhost:5678")
    print("   2. Ouvrez chaque workflow")
    print("   3. Vérifiez l'onglet 'Executions'")
    print("   4. Regardez les logs du node 'Envoyer email'")
    print("=" * 60)


if __name__ == "__main__":
    main()







