#!/usr/bin/env python3
"""
Script pour vérifier la configuration SMTP dans N8N
"""

import os
import sys
import requests
import json
from typing import List, Dict, Any

# Configuration
N8N_URL = os.getenv("N8N_URL", "http://localhost:5678")
N8N_API_KEY = os.getenv("N8N_API_KEY", "")


def get_n8n_headers() -> dict:
    """Retourne les headers pour l'authentification N8N"""
    if not N8N_API_KEY:
        raise ValueError("N8N_API_KEY n'est pas défini")
    return {"X-N8N-API-KEY": N8N_API_KEY}


def get_credentials() -> List[Dict[str, Any]]:
    """Récupère toutes les credentials"""
    try:
        response = requests.get(
            f"{N8N_URL}/api/v1/credentials",
            headers=get_n8n_headers(),
            timeout=10
        )
        response.raise_for_status()
        return response.json().get("data", [])
    except Exception as e:
        print(f"❌ Erreur lors de la récupération des credentials: {e}")
        return []


def get_smtp_credentials() -> List[Dict[str, Any]]:
    """Récupère uniquement les credentials SMTP"""
    all_credentials = get_credentials()
    smtp_credentials = []
    
    for cred in all_credentials:
        if cred.get("type") == "smtp" or "smtp" in cred.get("name", "").lower():
            smtp_credentials.append(cred)
    
    return smtp_credentials


def get_credential_details(credential_id: str) -> Dict[str, Any]:
    """Récupère les détails d'une credential (sans les secrets)"""
    try:
        response = requests.get(
            f"{N8N_URL}/api/v1/credentials/{credential_id}",
            headers=get_n8n_headers(),
            timeout=10
        )
        response.raise_for_status()
        return response.json().get("data", {})
    except Exception as e:
        print(f"⚠️  Erreur lors de la récupération de la credential {credential_id}: {e}")
        return {}


def check_workflows_smtp_usage() -> Dict[str, Any]:
    """Vérifie quels workflows utilisent des credentials SMTP"""
    try:
        response = requests.get(
            f"{N8N_URL}/api/v1/workflows",
            headers=get_n8n_headers(),
            timeout=10
        )
        response.raise_for_status()
        workflows = response.json().get("data", [])
        
        smtp_workflows = []
        for workflow in workflows:
            nodes = workflow.get("nodes", [])
            for node in nodes:
                if node.get("type") == "n8n-nodes-base.emailSend":
                    credentials = node.get("credentials", {})
                    if "smtp" in credentials:
                        smtp_workflows.append({
                            "workflow_name": workflow.get("name"),
                            "workflow_id": workflow.get("id"),
                            "node_name": node.get("name"),
                            "credential_id": credentials.get("smtp", {}).get("id"),
                            "credential_name": credentials.get("smtp", {}).get("name")
                        })
        
        return smtp_workflows
    except Exception as e:
        print(f"❌ Erreur lors de la vérification des workflows: {e}")
        return []


def main():
    """Fonction principale"""
    print("\n" + "=" * 60)
    print("  VÉRIFICATION DE LA CONFIGURATION SMTP N8N")
    print("=" * 60 + "\n")
    
    if not N8N_API_KEY:
        print("❌ N8N_API_KEY n'est pas défini")
        print("   Utilisez: export N8N_API_KEY='votre_cle_api'")
        sys.exit(1)
    
    # 1. Vérifier les credentials SMTP
    print("📧 Recherche des credentials SMTP...\n")
    smtp_creds = get_smtp_credentials()
    
    if not smtp_creds:
        print("⚠️  Aucune credential SMTP trouvée")
    else:
        print(f"✅ {len(smtp_creds)} credential(s) SMTP trouvée(s):\n")
        for cred in smtp_creds:
            print(f"  📌 {cred.get('name', 'Sans nom')}")
            print(f"     ID: {cred.get('id')}")
            print(f"     Type: {cred.get('type', 'N/A')}")
            print(f"     Créée: {cred.get('createdAt', 'N/A')}")
            print()
    
    # 2. Vérifier l'utilisation dans les workflows
    print("🔍 Vérification de l'utilisation dans les workflows...\n")
    smtp_workflows = check_workflows_smtp_usage()
    
    if not smtp_workflows:
        print("⚠️  Aucun workflow n'utilise de credentials SMTP")
    else:
        print(f"✅ {len(smtp_workflows)} workflow(s) utilisent SMTP:\n")
        for wf in smtp_workflows:
            print(f"  📋 {wf['workflow_name']}")
            print(f"     Node: {wf['node_name']}")
            print(f"     Credential: {wf.get('credential_name', 'N/A')} (ID: {wf.get('credential_id', 'N/A')})")
            print()
    
    # 3. Résumé
    print("=" * 60)
    print("📊 RÉSUMÉ")
    print("=" * 60)
    print(f"Credentials SMTP: {len(smtp_creds)}")
    print(f"Workflows utilisant SMTP: {len(smtp_workflows)}")
    
    if smtp_creds and smtp_workflows:
        print("\n✅ Configuration SMTP OK - Les workflows peuvent envoyer des emails")
        return 0
    elif smtp_creds and not smtp_workflows:
        print("\n⚠️  Credentials SMTP configurées mais non utilisées dans les workflows")
        return 1
    else:
        print("\n❌ Configuration SMTP manquante")
        return 1


if __name__ == "__main__":
    sys.exit(main())







