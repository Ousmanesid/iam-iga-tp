#!/usr/bin/env python3
"""
Script pour tester l'envoi d'emails SMTP via les workflows N8N
"""

import os
import sys
import requests
import json
import time
from datetime import datetime
from typing import Dict, Any

# Configuration
N8N_URL = os.getenv("N8N_URL", "http://localhost:5678")
N8N_API_KEY = os.getenv("N8N_API_KEY", "")
N8N_WEBHOOK_URL = os.getenv("N8N_WEBHOOK_URL", "http://localhost:5678/webhook")
TEST_EMAIL = os.getenv("TEST_EMAIL", "admin@example.com")


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


def test_pre_provision_email() -> bool:
    """Teste l'envoi d'email via le workflow pre-provision-simple"""
    print_section("Test 1: Email Pre-Provision Simple")
    
    test_data = {
        "workflow_type": "pre_provision_simple",
        "timestamp": datetime.utcnow().isoformat(),
        "user_data": {
            "login": "test_smtp_user",
            "email": f"test.smtp.{int(time.time())}@example.com",
            "first_name": "Test",
            "last_name": "SMTP",
            "department": "IT",
            "job_title": "Developer"
        },
        "requested_roles": ["HOMEAPP_USER"],
        "requested_permissions": [],
        "target_system": "homeapp",
        "requester": "test_script",
        "justification": "Test d'envoi d'email SMTP",
        "requires_approval": True,
        "approver_email": TEST_EMAIL,
        "request_id": f"test-{int(time.time())}"
    }
    
    try:
        print(f"📤 Envoi de la requête au webhook pre-provision...")
        print(f"📧 Email destinataire: {TEST_EMAIL}")
        
        response = requests.post(
            f"{N8N_WEBHOOK_URL}/pre-provision",
            json=test_data,
            timeout=30
        )
        
        if response.status_code in [200, 201]:
            try:
                result = response.json()
                print_result(True, f"Workflow exécuté: {result.get('message', 'OK')}")
                print(f"   Execution ID: {result.get('execution_id', 'N/A')}")
            except:
                print_result(True, f"Workflow exécuté (status {response.status_code})")
            
            print(f"\n💡 Vérifiez votre boîte email ({TEST_EMAIL}) pour confirmer la réception")
            return True
        else:
            print_result(False, f"Erreur {response.status_code}: {response.text[:200]}")
            return False
    except Exception as e:
        print_result(False, f"Erreur: {e}")
        return False


def test_chatbot_email() -> bool:
    """Teste l'envoi d'email via le workflow chatbot"""
    print_section("Test 2: Email Chatbot")
    
    test_data = {
        "action_type": "assign_role",
        "target_user": "test_user_001",
        "role_or_permission": "HOMEAPP_ADMIN",
        "requester": "test_script",
        "requires_approval": True,
        "timestamp": datetime.utcnow().isoformat()
    }
    
    try:
        print(f"📤 Envoi de la requête au webhook chatbot...")
        print(f"📧 Email destinataire: {TEST_EMAIL}")
        
        response = requests.post(
            f"{N8N_WEBHOOK_URL}/chatbot",
            json=test_data,
            timeout=30
        )
        
        if response.status_code in [200, 201]:
            try:
                result = response.json()
                print_result(True, f"Workflow exécuté: {result.get('message', 'OK')}")
            except:
                print_result(True, f"Workflow exécuté (status {response.status_code})")
            
            print(f"\n💡 Vérifiez votre boîte email ({TEST_EMAIL}) pour confirmer la réception")
            return True
        else:
            print_result(False, f"Erreur {response.status_code}: {response.text[:200]}")
            return False
    except Exception as e:
        print_result(False, f"Erreur: {e}")
        return False


def test_post_provision_email() -> bool:
    """Teste l'envoi d'email via le workflow post-provision"""
    print_section("Test 3: Email Post-Provision")
    
    test_data = {
        "workflow_type": "post_provision",
        "timestamp": datetime.utcnow().isoformat(),
        "user_login": "test_provisioned_user",
        "user_data": {
            "login": "test_provisioned_user",
            "email": f"test.provisioned.{int(time.time())}@example.com",
            "first_name": "Test",
            "last_name": "Provisioned",
            "department": "IT",
            "full_name": "Test Provisioned"
        },
        "provisioned_systems": ["homeapp"],
        "provisioned_roles": ["HOMEAPP_USER"],
        "reviewer_email": TEST_EMAIL,
        "request_id": f"test-review-{int(time.time())}"
    }
    
    try:
        print(f"📤 Envoi de la requête au webhook post-provision...")
        print(f"📧 Email destinataire: {TEST_EMAIL}")
        
        response = requests.post(
            f"{N8N_WEBHOOK_URL}/post-provision",
            json=test_data,
            timeout=30
        )
        
        if response.status_code in [200, 201]:
            try:
                result = response.json()
                print_result(True, f"Workflow exécuté: {result.get('message', 'OK')}")
            except:
                print_result(True, f"Workflow exécuté (status {response.status_code})")
            
            print(f"\n💡 Vérifiez votre boîte email ({TEST_EMAIL}) pour confirmer la réception")
            return True
        else:
            print_result(False, f"Erreur {response.status_code}: {response.text[:200]}")
            return False
    except Exception as e:
        print_result(False, f"Erreur: {e}")
        return False


def check_workflow_executions() -> bool:
    """Vérifie les exécutions récentes des workflows"""
    print_section("Vérification des Exécutions")
    
    try:
        # Récupérer les workflows
        response = requests.get(
            f"{N8N_URL}/api/v1/workflows",
            headers=get_n8n_headers(),
            timeout=10
        )
        response.raise_for_status()
        workflows = response.json().get("data", [])
        
        email_workflows = [w for w in workflows if any(
            n.get("type") == "n8n-nodes-base.emailSend" 
            for n in w.get("nodes", [])
        )]
        
        print(f"📊 {len(email_workflows)} workflow(s) avec envoi d'email trouvé(s)\n")
        
        for workflow in email_workflows[:3]:  # Afficher les 3 premiers
            print(f"  📋 {workflow.get('name')}")
            print(f"     ID: {workflow.get('id')}")
            print(f"     Actif: {'✅' if workflow.get('active') else '❌'}")
            print()
        
        return True
    except Exception as e:
        print_result(False, f"Erreur: {e}")
        return False


def main():
    """Fonction principale"""
    print("\n" + "=" * 60)
    print("  TEST D'ENVOI D'EMAILS SMTP VIA N8N")
    print("=" * 60)
    
    if not N8N_API_KEY:
        print("\n❌ N8N_API_KEY n'est pas défini")
        print("   Utilisez: export N8N_API_KEY='votre_cle_api'")
        sys.exit(1)
    
    print(f"\n📧 Email de test: {TEST_EMAIL}")
    print("   (Modifiez avec: export TEST_EMAIL='votre@email.com')\n")
    
    results = []
    
    # Vérification préalable
    results.append(("Vérification workflows", check_workflow_executions()))
    
    # Tests d'envoi
    results.append(("Email Pre-Provision", test_pre_provision_email()))
    time.sleep(2)  # Petite pause entre les tests
    
    results.append(("Email Chatbot", test_chatbot_email()))
    time.sleep(2)
    
    results.append(("Email Post-Provision", test_post_provision_email()))
    
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
        print(f"\n📬 Vérifiez votre boîte email ({TEST_EMAIL}) pour confirmer la réception des emails")
        print("   Si vous n'avez pas reçu d'emails, vérifiez:")
        print("   - La configuration SMTP dans N8N")
        print("   - Les logs N8N pour les erreurs")
        print("   - Que l'adresse email de test est correcte")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) ont échoué")
        return 1


if __name__ == "__main__":
    sys.exit(main())







