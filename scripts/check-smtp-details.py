#!/usr/bin/env python3
"""
Script pour vérifier les détails SMTP dans les workflows N8N
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


def get_workflow(workflow_id: str) -> Dict[str, Any]:
    """Récupère un workflow par son ID"""
    try:
        response = requests.get(
            f"{N8N_URL}/api/v1/workflows/{workflow_id}",
            headers=get_n8n_headers(),
            timeout=10
        )
        response.raise_for_status()
        return response.json().get("data", {})
    except Exception as e:
        print(f"❌ Erreur: {e}")
        return {}


def get_all_workflows() -> List[Dict[str, Any]]:
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
        print(f"❌ Erreur: {e}")
        return []


def extract_smtp_info(workflow: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Extrait les informations SMTP d'un workflow"""
    smtp_info = []
    nodes = workflow.get("nodes", [])
    
    for node in nodes:
        if node.get("type") == "n8n-nodes-base.emailSend":
            credentials = node.get("credentials", {})
            smtp_cred = credentials.get("smtp", {})
            
            # Extraire les paramètres du node
            params = node.get("parameters", {})
            
            smtp_info.append({
                "workflow_name": workflow.get("name"),
                "workflow_id": workflow.get("id"),
                "node_name": node.get("name"),
                "credential_id": smtp_cred.get("id"),
                "credential_name": smtp_cred.get("name"),
                "from_email": params.get("fromEmail"),
                "to_email_template": params.get("toEmail"),
                "subject_template": params.get("subject"),
            })
    
    return smtp_info


def main():
    """Fonction principale"""
    print("\n" + "=" * 60)
    print("  VÉRIFICATION DÉTAILLÉE SMTP DANS N8N")
    print("=" * 60 + "\n")
    
    if not N8N_API_KEY:
        print("❌ N8N_API_KEY n'est pas défini")
        sys.exit(1)
    
    workflows = get_all_workflows()
    all_smtp_info = []
    
    for workflow in workflows:
        smtp_info = extract_smtp_info(workflow)
        all_smtp_info.extend(smtp_info)
    
    if not all_smtp_info:
        print("⚠️  Aucun workflow n'utilise SMTP")
        return 1
    
    print(f"✅ {len(all_smtp_info)} node(s) email trouvé(s) dans {len(set(s['workflow_name'] for s in all_smtp_info))} workflow(s)\n")
    
    # Grouper par credential
    creds_usage = {}
    for info in all_smtp_info:
        cred_id = info.get("credential_id", "unknown")
        cred_name = info.get("credential_name", "Sans nom")
        key = f"{cred_name} ({cred_id})"
        
        if key not in creds_usage:
            creds_usage[key] = []
        creds_usage[key].append(info)
    
    print("📧 CREDENTIALS SMTP UTILISÉES:\n")
    for cred_key, usages in creds_usage.items():
        print(f"  🔑 {cred_key}")
        print(f"     Utilisée dans {len(usages)} node(s):")
        for usage in usages:
            print(f"       - {usage['workflow_name']} → {usage['node_name']}")
            print(f"         From: {usage.get('from_email', 'N/A')}")
            print(f"         To: {usage.get('to_email_template', 'N/A')[:50]}...")
        print()
    
    # Vérifier la cohérence
    print("🔍 VÉRIFICATION DE COHÉRENCE:\n")
    
    unique_creds = set(info.get("credential_id") for info in all_smtp_info)
    if len(unique_creds) == 1:
        print("✅ Tous les workflows utilisent la même credential SMTP")
    else:
        print(f"⚠️  {len(unique_creds)} credentials SMTP différentes utilisées")
        print("   Cela peut causer des problèmes de configuration")
    
    # Vérifier les templates d'email
    print("\n📝 TEMPLATES D'EMAIL:\n")
    for info in all_smtp_info[:3]:  # Afficher les 3 premiers
        print(f"  📋 {info['workflow_name']} - {info['node_name']}")
        print(f"     Subject: {info.get('subject_template', 'N/A')[:60]}...")
        print()
    
    print("=" * 60)
    print("✅ Configuration SMTP détectée et utilisée dans les workflows")
    print("=" * 60)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())







