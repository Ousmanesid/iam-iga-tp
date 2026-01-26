#!/usr/bin/env python3
"""
Script pour tester directement l'envoi SMTP depuis N8N
en créant un workflow de test simple
"""

import os
import sys
import requests
import json
import time

# Configuration
N8N_URL = os.getenv("N8N_URL", "http://localhost:5678")
N8N_API_KEY = os.getenv("N8N_API_KEY", "")
TEST_EMAIL = os.getenv("TEST_EMAIL", "admin@example.com")


def get_n8n_headers() -> dict:
    """Retourne les headers pour l'authentification N8N"""
    if not N8N_API_KEY:
        raise ValueError("N8N_API_KEY n'est pas défini")
    return {"X-N8N-API-KEY": N8N_API_KEY}


def create_test_workflow() -> str:
    """Crée un workflow de test simple pour tester SMTP"""
    workflow = {
        "name": "Test SMTP Direct",
        "nodes": [
            {
                "parameters": {
                    "httpMethod": "POST",
                    "path": "test-smtp",
                    "responseMode": "responseNode",
                    "options": {}
                },
                "id": "webhook-trigger",
                "name": "Webhook Trigger",
                "type": "n8n-nodes-base.webhook",
                "typeVersion": 1.1,
                "position": [250, 300],
                "webhookId": f"test-smtp-{int(time.time())}"
            },
            {
                "parameters": {
                    "fromEmail": "iam-system@example.com",
                    "toEmail": TEST_EMAIL,
                    "subject": "Test SMTP N8N",
                    "emailType": "text",
                    "text": "Ceci est un test d'envoi d'email depuis N8N.\n\nSi vous recevez cet email, la configuration SMTP fonctionne correctement.",
                    "options": {}
                },
                "id": "send-email",
                "name": "Envoyer Email Test",
                "type": "n8n-nodes-base.emailSend",
                "typeVersion": 2,
                "position": [470, 300],
                "credentials": {
                    "smtp": {
                        "id": "mA4Dc5a8vK6LYplR",
                        "name": "SMTP account"
                    }
                }
            },
            {
                "parameters": {
                    "respondWith": "json",
                    "responseBody": "={{ JSON.stringify({ success: true, message: 'Email envoyé', timestamp: new Date().toISOString() }) }}",
                    "options": {}
                },
                "id": "response",
                "name": "Réponse",
                "type": "n8n-nodes-base.respondToWebhook",
                "typeVersion": 1,
                "position": [690, 300]
            }
        ],
        "connections": {
            "Webhook Trigger": {
                "main": [[{"node": "Envoyer Email Test", "type": "main", "index": 0}]]
            },
            "Envoyer Email Test": {
                "main": [[{"node": "Réponse", "type": "main", "index": 0}]]
            }
        },
        "settings": {
            "executionOrder": "v1"
        }
    }
    
    try:
        response = requests.post(
            f"{N8N_URL}/api/v1/workflows",
            json=workflow,
            headers=get_n8n_headers(),
            timeout=30
        )
        response.raise_for_status()
        result = response.json()
        workflow_id = result.get("id") or result.get("data", {}).get("id")
        return workflow_id
    except Exception as e:
        print(f"❌ Erreur lors de la création: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"   Réponse: {e.response.text[:200]}")
        return None


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


def test_workflow(workflow_id: str) -> bool:
    """Teste le workflow"""
    try:
        # Récupérer le workflow pour obtenir le webhook path
        response = requests.get(
            f"{N8N_URL}/api/v1/workflows/{workflow_id}",
            headers=get_n8n_headers(),
            timeout=10
        )
        response.raise_for_status()
        workflow = response.json().get("data", {})
        
        nodes = workflow.get("nodes", [])
        webhook_node = next((n for n in nodes if n.get("type") == "n8n-nodes-base.webhook"), None)
        
        if not webhook_node:
            print("❌ Node webhook introuvable")
            return False
        
        webhook_path = webhook_node.get("parameters", {}).get("path", "test-smtp")
        
        # Tester le webhook
        print(f"📤 Test du webhook: /webhook/{webhook_path}")
        response = requests.post(
            f"{N8N_URL}/webhook/{webhook_path}",
            json={"test": True},
            timeout=30
        )
        
        if response.status_code in [200, 201]:
            try:
                result = response.json()
                print(f"✅ Réponse: {result}")
            except:
                print(f"✅ Réponse (status {response.status_code})")
            return True
        else:
            print(f"❌ Erreur {response.status_code}: {response.text[:200]}")
            return False
    except Exception as e:
        print(f"❌ Erreur: {e}")
        return False


def main():
    """Fonction principale"""
    print("\n" + "=" * 60)
    print("  TEST DIRECT SMTP N8N")
    print("=" * 60 + "\n")
    
    if not N8N_API_KEY:
        print("❌ N8N_API_KEY n'est pas défini")
        sys.exit(1)
    
    print(f"📧 Email de test: {TEST_EMAIL}\n")
    
    print("1️⃣  Création du workflow de test...")
    workflow_id = create_test_workflow()
    
    if not workflow_id:
        print("❌ Impossible de créer le workflow")
        sys.exit(1)
    
    print(f"✅ Workflow créé (ID: {workflow_id})")
    
    print("\n2️⃣  Activation du workflow...")
    if activate_workflow(workflow_id):
        print("✅ Workflow activé")
    else:
        print("⚠️  Échec de l'activation (peut-être déjà actif)")
    
    print("\n3️⃣  Test d'envoi d'email...")
    if test_workflow(workflow_id):
        print("\n✅ Test envoyé!")
        print(f"\n💡 Vérifiez votre boîte email ({TEST_EMAIL})")
        print(f"   Workflow ID: {workflow_id}")
        print(f"   Vérifiez l'exécution dans N8N UI: http://localhost:5678")
    else:
        print("\n❌ Échec du test")
        sys.exit(1)


if __name__ == "__main__":
    main()







