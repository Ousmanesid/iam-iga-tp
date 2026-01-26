#!/usr/bin/env python3
"""
Script pour déboguer les problèmes SMTP dans N8N
"""

import os
import sys
import requests
import json
from typing import Dict, Any, List

# Configuration
N8N_URL = os.getenv("N8N_URL", "http://localhost:5678")
N8N_API_KEY = os.getenv("N8N_API_KEY", "")


def get_n8n_headers() -> dict:
    """Retourne les headers pour l'authentification N8N"""
    if not N8N_API_KEY:
        raise ValueError("N8N_API_KEY n'est pas défini")
    return {"X-N8N-API-KEY": N8N_API_KEY}


def get_workflow_details(workflow_id: str) -> Dict[str, Any]:
    """Récupère les détails d'un workflow"""
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


def analyze_email_node(node: Dict[str, Any]) -> Dict[str, Any]:
    """Analyse un node d'envoi d'email"""
    params = node.get("parameters", {})
    credentials = node.get("credentials", {})
    
    return {
        "node_name": node.get("name"),
        "node_id": node.get("id"),
        "has_credentials": "smtp" in credentials,
        "credential_id": credentials.get("smtp", {}).get("id"),
        "credential_name": credentials.get("smtp", {}).get("name"),
        "from_email": params.get("fromEmail"),
        "to_email": params.get("toEmail"),
        "subject": params.get("subject", "")[:50],
        "email_type": params.get("emailType"),
        "has_html": "html" in params,
    }


def get_recent_executions(workflow_id: str, limit: int = 5) -> List[Dict[str, Any]]:
    """Récupère les exécutions récentes"""
    try:
        response = requests.get(
            f"{N8N_URL}/api/v1/executions",
            headers=get_n8n_headers(),
            params={"workflowId": workflow_id, "limit": limit},
            timeout=10
        )
        if response.status_code == 200:
            return response.json().get("data", [])
        return []
    except:
        return []


def get_execution_details(execution_id: str) -> Dict[str, Any]:
    """Récupère les détails d'une exécution"""
    try:
        response = requests.get(
            f"{N8N_URL}/api/v1/executions/{execution_id}",
            headers=get_n8n_headers(),
            timeout=10
        )
        if response.status_code == 200:
            return response.json().get("data", {})
        return {}
    except:
        return {}


def check_execution_for_errors(execution: Dict[str, Any]) -> List[str]:
    """Vérifie une exécution pour des erreurs"""
    errors = []
    
    if execution.get("stoppedAt"):
        errors.append(f"Workflow arrêté à: {execution.get('stoppedAt')}")
    
    # Vérifier les données d'exécution
    execution_data = execution.get("executionData", {})
    node_executions = execution_data.get("resultData", {}).get("runData", {})
    
    for node_id, node_data in node_executions.items():
        if isinstance(node_data, list) and len(node_data) > 0:
            last_run = node_data[-1]
            if last_run.get("error"):
                error_info = last_run.get("error", {})
                errors.append(f"Node {node_id}: {error_info.get('message', 'Erreur inconnue')}")
    
    return errors


def main():
    """Fonction principale"""
    print("\n" + "=" * 60)
    print("  DÉBOGAGE SMTP N8N")
    print("=" * 60 + "\n")
    
    if not N8N_API_KEY:
        print("❌ N8N_API_KEY n'est pas défini")
        sys.exit(1)
    
    # Workflows à vérifier
    workflows_to_check = [
        ("4pdplQ5mM6k1GULp", "pre-provision-simple"),
        ("8Ldn7ERVqQwBVqBG", "post-provision"),
        ("Clrhbmw23vmofy1t", "chatbot-action"),
    ]
    
    print("🔍 Analyse des workflows avec email...\n")
    
    for workflow_id, workflow_name in workflows_to_check:
        print(f"\n{'='*60}")
        print(f"📋 {workflow_name} (ID: {workflow_id})")
        print("="*60)
        
        workflow = get_workflow_details(workflow_id)
        if not workflow:
            print("❌ Impossible de récupérer le workflow")
            continue
        
        # Trouver les nodes email
        nodes = workflow.get("nodes", [])
        email_nodes = [n for n in nodes if n.get("type") == "n8n-nodes-base.emailSend"]
        
        if not email_nodes:
            print("⚠️  Aucun node email trouvé")
            continue
        
        print(f"\n📧 {len(email_nodes)} node(s) email trouvé(s):\n")
        for node in email_nodes:
            analysis = analyze_email_node(node)
            print(f"  Node: {analysis['node_name']}")
            print(f"    Credential: {analysis.get('credential_name', 'NON CONFIGURÉE')} (ID: {analysis.get('credential_id', 'N/A')})")
            print(f"    From: {analysis.get('from_email', 'N/A')}")
            print(f"    To: {analysis.get('to_email', 'N/A')[:60]}...")
            print(f"    Subject: {analysis.get('subject', 'N/A')}...")
            
            if not analysis['has_credentials']:
                print("    ⚠️  PROBLÈME: Pas de credential SMTP configurée!")
            print()
        
        # Vérifier les exécutions récentes
        print("📊 Exécutions récentes:\n")
        executions = get_recent_executions(workflow_id, limit=3)
        
        if not executions:
            print("  ⚠️  Aucune exécution trouvée")
        else:
            for i, exec in enumerate(executions[:3], 1):
                exec_id = exec.get("id", "N/A")
                finished = exec.get("finished", False)
                stopped = exec.get("stoppedAt")
                
                print(f"  Exécution {i}:")
                print(f"    ID: {exec_id}")
                print(f"    Finished: {finished}")
                if stopped:
                    print(f"    Arrêté à: {stopped}")
                
                # Récupérer les détails pour voir les erreurs
                if exec_id != "N/A":
                    details = get_execution_details(exec_id)
                    errors = check_execution_for_errors(details)
                    if errors:
                        print(f"    ❌ Erreurs détectées:")
                        for error in errors:
                            print(f"       - {error}")
                    else:
                        print(f"    ✅ Aucune erreur détectée dans les métadonnées")
                print()
    
    print("\n" + "=" * 60)
    print("💡 RECOMMANDATIONS:")
    print("=" * 60)
    print("1. Vérifiez les logs N8N: docker-compose logs n8n | grep -i smtp")
    print("2. Vérifiez la configuration SMTP dans N8N UI:")
    print("   - Allez sur http://localhost:5678")
    print("   - Settings → Credentials → SMTP account")
    print("   - Vérifiez: host, port, user, password, TLS")
    print("3. Testez manuellement un workflow dans N8N UI")
    print("4. Vérifiez que le serveur SMTP est accessible depuis le conteneur")
    print("=" * 60)


if __name__ == "__main__":
    main()







