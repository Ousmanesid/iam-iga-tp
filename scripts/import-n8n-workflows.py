#!/usr/bin/env python3
"""
Script pour importer les workflows N8N via l'API REST
"""

import json
import os
import sys
import requests
from pathlib import Path
from typing import Dict, Any

# Configuration
N8N_URL = os.getenv("N8N_URL", "http://localhost:5678")
N8N_API_KEY = os.getenv("N8N_API_KEY", "")
N8N_USER = os.getenv("N8N_USER", "admin")
N8N_PASSWORD = os.getenv("N8N_PASSWORD", "admin123")
WORKFLOWS_DIR = Path(__file__).parent.parent / "config" / "n8n" / "workflows"

# Workflows à importer (dans l'ordre)
WORKFLOWS_TO_IMPORT = [
    "pre-provision-simple.json",
    "pre-provision-multi.json",
    "post-provision.json",
    "chatbot-action.json",
    "approval-callback.json",
    "multi-approval-callback.json",
    "review-callback.json",
    "chatbot-approval.json",
]


def get_n8n_auth():
    """Retourne headers/auth pour l'authentification N8N"""
    if N8N_API_KEY:
        return {"X-N8N-API-KEY": N8N_API_KEY}, None
    return {}, (N8N_USER, N8N_PASSWORD)


def check_n8n_connection() -> bool:
    """Vérifie que N8N est accessible"""
    try:
        headers, auth = get_n8n_auth()
        response = requests.get(
            f"{N8N_URL}/api/v1/workflows",
            headers=headers,
            auth=auth,
            timeout=5
        )
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Erreur de connexion à N8N: {e}")
        return False


def get_existing_workflows() -> Dict[str, Any]:
    """Récupère la liste des workflows existants"""
    try:
        headers, auth = get_n8n_auth()
        response = requests.get(
            f"{N8N_URL}/api/v1/workflows",
            headers=headers,
            auth=auth,
            timeout=10
        )
        response.raise_for_status()
        return {w["name"]: w for w in response.json().get("data", [])}
    except Exception as e:
        print(f"⚠️  Erreur lors de la récupération des workflows: {e}")
        return {}


def import_workflow(workflow_path: Path, update_if_exists: bool = True) -> bool:
    """Importe un workflow dans N8N"""
    try:
        # Lire le fichier workflow
        with open(workflow_path, "r", encoding="utf-8") as f:
            workflow_data = json.load(f)
        
        workflow_name = workflow_data.get("name", workflow_path.stem)
        
        # Vérifier si le workflow existe déjà
        existing_workflows = get_existing_workflows()
        
        if workflow_name in existing_workflows:
            if not update_if_exists:
                print(f"⏭️  Workflow '{workflow_name}' existe déjà, ignoré")
                return True
            
            # Mettre à jour le workflow existant
            workflow_id = existing_workflows[workflow_name]["id"]
            
            # Préparer les données pour la mise à jour
            # Note: 'tags' est en lecture seule, on ne peut pas le mettre à jour via l'API
            update_data = {
                "name": workflow_name,
                "nodes": workflow_data.get("nodes", []),
                "connections": workflow_data.get("connections", {}),
                "settings": workflow_data.get("settings", {}),
                "staticData": workflow_data.get("staticData"),
            }
            
            headers, auth = get_n8n_auth()
            response = requests.put(
                f"{N8N_URL}/api/v1/workflows/{workflow_id}",
                json=update_data,
                headers=headers,
                auth=auth,
                timeout=30
            )
            response.raise_for_status()
            print(f"✅ Workflow '{workflow_name}' mis à jour (ID: {workflow_id})")
            return True
        else:
            # Créer un nouveau workflow
            # N8N attend un format spécifique pour la création
            # Note: 'active' et 'tags' sont en lecture seule, on ne peut pas les définir à la création
            create_data = {
                "name": workflow_name,
                "nodes": workflow_data.get("nodes", []),
                "connections": workflow_data.get("connections", {}),
                "settings": workflow_data.get("settings", {}),
                "staticData": workflow_data.get("staticData"),
            }
            
            headers, auth = get_n8n_auth()
            response = requests.post(
                f"{N8N_URL}/api/v1/workflows",
                json=create_data,
                headers=headers,
                auth=auth,
                timeout=30
            )
            response.raise_for_status()
            result = response.json()
            workflow_id = result.get("id") or result.get("data", {}).get("id")
            print(f"✅ Workflow '{workflow_name}' créé (ID: {workflow_id})")
            return True
            
    except requests.exceptions.HTTPError as e:
        print(f"❌ Erreur HTTP lors de l'import de '{workflow_path.name}': {e}")
        if e.response is not None:
            try:
                error_detail = e.response.json()
                print(f"   Détails: {json.dumps(error_detail, indent=2)}")
            except:
                print(f"   Réponse: {e.response.text}")
        return False
    except Exception as e:
        print(f"❌ Erreur lors de l'import de '{workflow_path.name}': {e}")
        return False


def main():
    """Fonction principale"""
    print("🚀 Import des workflows N8N\n")
    print(f"📡 URL N8N: {N8N_URL}")
    print(f"📁 Dossier workflows: {WORKFLOWS_DIR}\n")
    
    if not N8N_API_KEY:
        print("ℹ️  N8N_API_KEY non défini, utilisation de l'auth basique.")
        print(f"   Utilisateur: {N8N_USER}")
    
    # Vérifier la connexion
    if not check_n8n_connection():
        print("\n❌ Impossible de se connecter à N8N. Vérifiez:")
        print(f"   - Que N8N est démarré sur {N8N_URL}")
        print(f"   - Que la clé API est valide")
        sys.exit(1)
    
    print("✅ Connexion à N8N réussie\n")
    
    # Vérifier que le dossier existe
    if not WORKFLOWS_DIR.exists():
        print(f"❌ Dossier workflows introuvable: {WORKFLOWS_DIR}")
        sys.exit(1)
    
    # Importer les workflows
    success_count = 0
    failed_count = 0
    
    for workflow_file in WORKFLOWS_TO_IMPORT:
        workflow_path = WORKFLOWS_DIR / workflow_file
        
        if not workflow_path.exists():
            print(f"⚠️  Fichier introuvable: {workflow_file}")
            failed_count += 1
            continue
        
        print(f"📥 Import de {workflow_file}...")
        if import_workflow(workflow_path):
            success_count += 1
        else:
            failed_count += 1
        print()
    
    # Résumé
    print("=" * 50)
    print(f"✅ Succès: {success_count}")
    print(f"❌ Échecs: {failed_count}")
    print("=" * 50)
    
    if failed_count > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()

