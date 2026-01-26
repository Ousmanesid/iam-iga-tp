#!/usr/bin/env python3
"""
Script d'import automatique des objets MidPoint via REST API
"""

import requests
import os
import sys
import time
from pathlib import Path
import xml.etree.ElementTree as ET

# Configuration MidPoint
MIDPOINT_URL = "http://localhost:8080/midpoint"
MIDPOINT_USER = "administrator"
MIDPOINT_PASSWORD = "5ecr3t"

# Ordre d'import (important pour les dépendances)
IMPORT_ORDER = [
    "resources",  # Les ressources en premier
    "roles",      # Les rôles ensuite
    "object-templates",  # Templates
    "tasks"       # Tâches en dernier
]

# Dossier de base
BASE_DIR = Path("/root/iam-iga-tp/config/midpoint")


def get_object_type_from_xml(xml_file):
    """Détermine le type d'objet MidPoint depuis le fichier XML"""
    try:
        tree = ET.parse(xml_file)
        root = tree.getroot()
        # Retire le namespace pour obtenir juste le tag
        tag = root.tag.split('}')[-1] if '}' in root.tag else root.tag
        return tag
    except Exception as e:
        print(f"⚠️  Erreur lors de la lecture de {xml_file}: {e}")
        return None


def import_object(xml_file):
    """Importe un objet dans MidPoint via l'API REST"""
    
    # Lire le contenu XML
    with open(xml_file, 'r', encoding='utf-8') as f:
        xml_content = f.read()
    
    # Déterminer le type d'objet
    object_type = get_object_type_from_xml(xml_file)
    if not object_type:
        return False
    
    # Mapping des types d'objets vers les endpoints REST
    type_mapping = {
        'resource': 'resources',
        'role': 'roles',
        'objectTemplate': 'objectTemplates',
        'task': 'tasks',
        'user': 'users'
    }
    
    endpoint = type_mapping.get(object_type, object_type.lower() + 's')
    url = f"{MIDPOINT_URL}/ws/rest/{endpoint}"
    
    headers = {
        'Content-Type': 'application/xml',
        'Accept': 'application/xml'
    }
    
    print(f"  → Import de {xml_file.name}...")
    print(f"     Type: {object_type}, Endpoint: {endpoint}")
    
    # Retries avec backoff exponentiel
    max_retries = 3
    for attempt in range(max_retries):
        try:
            # Créer une nouvelle session pour chaque import
            session = requests.Session()
            session.auth = (MIDPOINT_USER, MIDPOINT_PASSWORD)
            
            # POST pour créer l'objet
            response = session.post(
                url,
                data=xml_content.encode('utf-8'),
                headers=headers,
                timeout=60
            )
            
            if response.status_code in [200, 201, 204]:
                print(f"  ✓ {xml_file.name} importé avec succès")
                session.close()
                return True
            elif response.status_code == 409:
                print(f"  ⚠️  {xml_file.name} existe déjà, tentative de mise à jour...")
                # Si l'objet existe, essayer de le mettre à jour avec PUT
                tree = ET.parse(xml_file)
                root = tree.getroot()
                oid = root.get('oid')
                if oid:
                    put_url = f"{url}/{oid}"
                    response = session.put(
                        put_url,
                        data=xml_content.encode('utf-8'),
                        headers=headers,
                        timeout=60
                    )
                    if response.status_code in [200, 201, 204]:
                        print(f"  ✓ {xml_file.name} mis à jour avec succès")
                        session.close()
                        return True
            elif response.status_code == 401:
                if attempt < max_retries - 1:
                    wait_time = (attempt + 1) * 3
                    print(f"  ⚠️  Erreur 401, nouvelle tentative dans {wait_time}s...")
                    session.close()
                    time.sleep(wait_time)
                    continue
            
            print(f"  ✗ Erreur {response.status_code}: {response.text[:200]}")
            session.close()
            return False
            
        except Exception as e:
            if attempt < max_retries - 1:
                wait_time = (attempt + 1) * 3
                print(f"  ⚠️  Exception: {e}, nouvelle tentative dans {wait_time}s...")
                time.sleep(wait_time)
                continue
            print(f"  ✗ Exception: {e}")
            return False
    
    return False


def main():
    print("=" * 70)
    print("Import des objets MidPoint via REST API")
    print("=" * 70)
    print()
    
    # Vérifier que MidPoint est accessible
    try:
        response = requests.get(
            f"{MIDPOINT_URL}/ws/rest/users/00000000-0000-0000-0000-000000000002",
            auth=(MIDPOINT_USER, MIDPOINT_PASSWORD),
            timeout=10
        )
        if response.status_code == 200:
            print("✓ Connexion à MidPoint OK")
            print()
        else:
            print(f"✗ Impossible de se connecter à MidPoint (code {response.status_code})")
            return 1
    except Exception as e:
        print(f"✗ Erreur de connexion à MidPoint: {e}")
        return 1
    
    # Statistiques
    total = 0
    success = 0
    failed = 0
    
    # Import dans l'ordre défini
    for category in IMPORT_ORDER:
        category_dir = BASE_DIR / category
        
        if not category_dir.exists():
            continue
        
        # Lister tous les fichiers XML (sauf tmp)
        xml_files = sorted(category_dir.glob("*.xml"))
        
        if not xml_files:
            continue
        
        print(f"\n📦 Import des {category}:")
        print("-" * 70)
        
        for xml_file in xml_files:
            total += 1
            if import_object(xml_file):
                success += 1
            else:
                failed += 1
            
            # Pause plus longue pour éviter le rate limiting
            time.sleep(2)
    
    # Résumé
    print()
    print("=" * 70)
    print("Résumé de l'import")
    print("=" * 70)
    print(f"Total: {total} objets")
    print(f"✓ Succès: {success}")
    print(f"✗ Échecs: {failed}")
    print()
    
    if failed == 0:
        print("🎉 Tous les objets ont été importés avec succès!")
        return 0
    else:
        print("⚠️  Certains objets n'ont pas pu être importés.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
