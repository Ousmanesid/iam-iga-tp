#!/usr/bin/env python3
"""
Script de test pour les workflows N8N
"""

import os
import sys
import json
import requests
import time
from typing import Dict, Any, Optional
from datetime import datetime

# Configuration
N8N_URL = os.getenv("N8N_URL", "http://localhost:5678")
N8N_API_KEY = os.getenv("N8N_API_KEY", "")
GATEWAY_URL = os.getenv("GATEWAY_URL", "http://localhost:8000")
N8N_WEBHOOK_URL = os.getenv("N8N_WEBHOOK_URL", "http://localhost:5678/webhook")


def get_n8n_headers() -> dict:
    """Retourne les headers pour l'authentification N8N"""
    if not N8N_API_KEY:
        raise ValueError("N8N_API_KEY n'est pas défini")
    return {"X-N8N-API-KEY": N8N_API_KEY}


def print_section(title: str):
    """Affiche une section"""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def print_result(success: bool, message: str):
    """Affiche un résultat"""
    icon = "✅" if success else "❌"
    print(f"{icon} {message}")


def test_gateway_health() -> bool:
    """Teste la santé du Gateway"""
    print_section("Test 1: Santé du Gateway")
    try:
        response = requests.get(f"{GATEWAY_URL}/health", timeout=5)
        if response.status_code == 200:
            print_result(True, f"Gateway accessible: {response.json()}")
            return True
        else:
            print_result(False, f"Gateway retourne {response.status_code}")
            return False
    except Exception as e:
        print_result(False, f"Erreur de connexion: {e}")
        return False


def test_n8n_health() -> bool:
    """Teste la santé de N8N"""
    print_section("Test 2: Santé de N8N")
    try:
        response = requests.get(
            f"{N8N_URL}/api/v1/workflows",
            headers=get_n8n_headers(),
            timeout=5
        )
        if response.status_code == 200:
            workflows = response.json().get("data", [])
            active_workflows = [w for w in workflows if w.get("active", False)]
            print_result(True, f"N8N accessible - {len(active_workflows)} workflows actifs")
            return True
        else:
            print_result(False, f"N8N retourne {response.status_code}")
            return False
    except Exception as e:
        print_result(False, f"Erreur de connexion: {e}")
        return False


def test_workflow_exists(workflow_name: str) -> Optional[Dict[str, Any]]:
    """Vérifie qu'un workflow existe et est actif"""
    try:
        response = requests.get(
            f"{N8N_URL}/api/v1/workflows",
            headers=get_n8n_headers(),
            timeout=5
        )
        response.raise_for_status()
        workflows = response.json().get("data", [])
        
        for workflow in workflows:
            if workflow["name"] == workflow_name:
                return workflow
        return None
    except Exception as e:
        print(f"⚠️  Erreur: {e}")
        return None


def test_pre_provision_simple() -> bool:
    """Teste le workflow de pré-provisioning simple"""
    print_section("Test 3: Workflow Pre-Provision Simple")
    
    workflow = test_workflow_exists("pre-provision-simple")
    if not workflow:
        print_result(False, "Workflow 'pre-provision-simple' introuvable")
        return False
    
    if not workflow.get("active", False):
        print_result(False, "Workflow 'pre-provision-simple' n'est pas actif")
        return False
    
    print_result(True, f"Workflow trouvé et actif (ID: {workflow['id']})")
    
    # Test du webhook
    test_data = {
        "workflow_type": "pre_provision_simple",
        "timestamp": datetime.utcnow().isoformat(),
        "user_data": {
            "login": "test_user_001",
            "email": "test.user@example.com",
            "first_name": "Test",
            "last_name": "User",
            "department": "IT",
            "job_title": "Developer"
        },
        "requested_roles": ["HOMEAPP_USER"],
        "requested_permissions": [],
        "target_system": "homeapp",
        "requester": "test_script",
        "justification": "Test automatique",
        "requires_approval": True,
        "approver_email": "admin@example.com"
    }
    
    try:
        print(f"📤 Envoi de la requête au webhook...")
        response = requests.post(
            f"{N8N_WEBHOOK_URL}/pre-provision",
            json=test_data,
            timeout=10
        )
        
        if response.status_code in [200, 201]:
            try:
                if response.text:
                    result = response.json()
                    print_result(True, f"Webhook répond: {result.get('message', 'OK')}")
                else:
                    print_result(True, f"Webhook répond (vide): {response.status_code}")
            except:
                # Peut être une réponse HTML ou autre format
                print_result(True, f"Webhook répond (format non-JSON): {response.status_code}")
            return True
        else:
            print_result(False, f"Webhook retourne {response.status_code}: {response.text[:200]}")
            return False
    except Exception as e:
        print_result(False, f"Erreur lors de l'appel: {e}")
        return False


def test_approval_callback() -> bool:
    """Teste le workflow de callback d'approbation"""
    print_section("Test 4: Workflow Approval Callback")
    
    workflow = test_workflow_exists("Approval Callback (Simple)")
    if not workflow:
        print_result(False, "Workflow 'Approval Callback (Simple)' introuvable")
        return False
    
    if not workflow.get("active", False):
        print_result(False, "Workflow n'est pas actif")
        return False
    
    print_result(True, f"Workflow trouvé et actif (ID: {workflow['id']})")
    
    # Test du webhook (simulation d'un clic sur le lien d'approbation)
    test_params = {
        "request_id": "00000000-0000-0000-0000-000000000001",
        "decision": "approved",
        "comment": "Test automatique"
    }
    
    try:
        print(f"📤 Test du callback d'approbation...")
        response = requests.get(
            f"{N8N_WEBHOOK_URL}/approval-callback",
            params=test_params,
            timeout=10
        )
        
        if response.status_code == 200:
            print_result(True, "Callback répond correctement")
            return True
        else:
            print_result(False, f"Callback retourne {response.status_code}: {response.text[:200]}")
            return False
    except Exception as e:
        print_result(False, f"Erreur lors de l'appel: {e}")
        return False


def test_chatbot_workflow() -> bool:
    """Teste le workflow chatbot"""
    print_section("Test 5: Workflow Chatbot")
    
    workflow = test_workflow_exists("chatbot-action")
    if not workflow:
        print_result(False, "Workflow 'chatbot-action' introuvable")
        return False
    
    if not workflow.get("active", False):
        print_result(False, "Workflow n'est pas actif")
        return False
    
    print_result(True, f"Workflow trouvé et actif (ID: {workflow['id']})")
    
    # Test du webhook
    test_data = {
        "action_type": "assign_role",
        "target_user": "test_user_001",
        "role_or_permission": "HOMEAPP_USER",
        "requester": "test_script",
        "requires_approval": False
    }
    
    try:
        print(f"📤 Test du webhook chatbot...")
        response = requests.post(
            f"{N8N_WEBHOOK_URL}/chatbot",
            json=test_data,
            timeout=10
        )
        
        if response.status_code in [200, 201]:
            try:
                result = response.json()
                print_result(True, f"Webhook répond: {result.get('message', 'OK')}")
            except:
                # Peut être une réponse HTML (page de confirmation)
                print_result(True, f"Webhook répond (HTML): {response.status_code}")
            return True
        else:
            print_result(False, f"Webhook retourne {response.status_code}: {response.text[:200]}")
            return False
    except Exception as e:
        print_result(False, f"Erreur lors de l'appel: {e}")
        return False


def test_all_callbacks() -> bool:
    """Teste tous les workflows de callback"""
    print_section("Test 6: Workflows de Callback")
    
    callbacks = [
        ("Approval Callback (Simple)", "approval-callback"),
        ("Multi-Approval Callback", "multi-approval-callback"),
        ("Review Callback (Post-Provision)", "review-callback"),
        ("Chatbot Approval Callback", "chatbot-approval"),
    ]
    
    all_ok = True
    for name, webhook_path in callbacks:
        workflow = test_workflow_exists(name)
        if not workflow:
            print_result(False, f"Workflow '{name}' introuvable")
            all_ok = False
            continue
        
        if not workflow.get("active", False):
            print_result(False, f"Workflow '{name}' n'est pas actif")
            all_ok = False
        else:
            print_result(True, f"✅ '{name}' actif (ID: {workflow['id']})")
    
    return all_ok


def main():
    """Fonction principale"""
    print("\n" + "=" * 60)
    print("  TESTS DES WORKFLOWS N8N")
    print("=" * 60)
    
    if not N8N_API_KEY:
        print("\n❌ N8N_API_KEY n'est pas défini")
        print("   Utilisez: export N8N_API_KEY='votre_cle_api'")
        sys.exit(1)
    
    results = []
    
    # Tests de base
    results.append(("Gateway Health", test_gateway_health()))
    results.append(("N8N Health", test_n8n_health()))
    
    # Tests des workflows
    results.append(("Pre-Provision Simple", test_pre_provision_simple()))
    results.append(("Approval Callback", test_approval_callback()))
    results.append(("Chatbot Workflow", test_chatbot_workflow()))
    results.append(("All Callbacks", test_all_callbacks()))
    
    # Résumé
    print_section("RÉSUMÉ DES TESTS")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        icon = "✅" if result else "❌"
        print(f"{icon} {name}")
    
    print(f"\n📊 Résultat: {passed}/{total} tests réussis")
    
    if passed == total:
        print("\n🎉 Tous les tests sont passés !")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) ont échoué")
        return 1


if __name__ == "__main__":
    sys.exit(main())

