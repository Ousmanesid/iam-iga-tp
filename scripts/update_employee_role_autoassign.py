#!/usr/bin/env python3
"""
Script pour mettre à jour le rôle Employee avec l'auto-assignation via l'API REST MidPoint.

Ce script:
1. Lit le fichier role-employee.xml
2. L'importe/met à jour dans MidPoint via l'API REST
3. Lance un recompute sur tous les utilisateurs pour activer l'auto-assignation

Usage:
    python3 update_employee_role_autoassign.py
"""

import requests
import xml.etree.ElementTree as ET
from requests.auth import HTTPBasicAuth
import sys

# Configuration MidPoint
MIDPOINT_URL = "http://localhost:8080/midpoint"
MIDPOINT_USER = "administrator"
MIDPOINT_PASSWORD = "5ecr3t"

# OID du rôle Employee
EMPLOYEE_ROLE_OID = "00000000-0000-0000-0000-000000000104"

# Chemin vers le fichier XML du rôle
ROLE_FILE = "/srv/projet/iam-iga-tp/config/midpoint/roles/role-employee.xml"


def read_role_xml():
    """Lit le contenu du fichier XML du rôle Employee."""
    try:
        with open(ROLE_FILE, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        print(f"❌ Fichier non trouvé: {ROLE_FILE}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Erreur lors de la lecture du fichier: {e}")
        sys.exit(1)


def update_role_in_midpoint(role_xml):
    """Met à jour le rôle Employee dans MidPoint via l'API REST."""
    url = f"{MIDPOINT_URL}/ws/rest/roles/{EMPLOYEE_ROLE_OID}"
    
    headers = {
        'Content-Type': 'application/xml',
        'Accept': 'application/xml'
    }
    
    print(f"🔄 Mise à jour du rôle Employee dans MidPoint...")
    print(f"   URL: {url}")
    
    try:
        response = requests.put(
            url,
            data=role_xml.encode('utf-8'),
            headers=headers,
            auth=HTTPBasicAuth(MIDPOINT_USER, MIDPOINT_PASSWORD),
            timeout=30
        )
        
        if response.status_code in [200, 201, 204]:
            print("✅ Rôle Employee mis à jour avec succès!")
            print(f"   Status: {response.status_code}")
            return True
        elif response.status_code == 404:
            # Le rôle n'existe pas, on va le créer
            print("⚠️  Rôle non trouvé, tentative de création...")
            return create_role_in_midpoint(role_xml)
        else:
            print(f"❌ Erreur lors de la mise à jour du rôle")
            print(f"   Status: {response.status_code}")
            print(f"   Réponse: {response.text[:500]}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("❌ Impossible de se connecter à MidPoint")
        print(f"   Vérifiez que MidPoint est démarré sur {MIDPOINT_URL}")
        return False
    except Exception as e:
        print(f"❌ Erreur: {e}")
        return False


def create_role_in_midpoint(role_xml):
    """Crée le rôle Employee dans MidPoint via l'API REST."""
    url = f"{MIDPOINT_URL}/ws/rest/roles"
    
    headers = {
        'Content-Type': 'application/xml',
        'Accept': 'application/xml'
    }
    
    print(f"➕ Création du rôle Employee dans MidPoint...")
    
    try:
        response = requests.post(
            url,
            data=role_xml.encode('utf-8'),
            headers=headers,
            auth=HTTPBasicAuth(MIDPOINT_USER, MIDPOINT_PASSWORD),
            timeout=30
        )
        
        if response.status_code in [200, 201]:
            print("✅ Rôle Employee créé avec succès!")
            print(f"   Status: {response.status_code}")
            return True
        else:
            print(f"❌ Erreur lors de la création du rôle")
            print(f"   Status: {response.status_code}")
            print(f"   Réponse: {response.text[:500]}")
            return False
            
    except Exception as e:
        print(f"❌ Erreur: {e}")
        return False


def get_all_users():
    """Récupère la liste de tous les utilisateurs MidPoint."""
    url = f"{MIDPOINT_URL}/ws/rest/users"
    
    headers = {
        'Accept': 'application/xml'
    }
    
    print(f"📋 Récupération de la liste des utilisateurs...")
    
    try:
        response = requests.get(
            url,
            headers=headers,
            auth=HTTPBasicAuth(MIDPOINT_USER, MIDPOINT_PASSWORD),
            timeout=30
        )
        
        if response.status_code == 200:
            # Parse XML pour extraire les OIDs
            root = ET.fromstring(response.content)
            users = []
            
            # Namespace MidPoint
            ns = {'c': 'http://midpoint.evolveum.com/xml/ns/public/common/common-3'}
            
            for user in root.findall('.//c:object', ns):
                oid = user.get('oid')
                name_elem = user.find('.//c:name', ns)
                name = name_elem.text if name_elem is not None else "Unknown"
                
                if oid and name != 'administrator':  # On exclut l'admin
                    users.append({'oid': oid, 'name': name})
            
            print(f"✅ {len(users)} utilisateurs trouvés (hors administrator)")
            return users
        else:
            print(f"❌ Erreur lors de la récupération des utilisateurs: {response.status_code}")
            return []
            
    except Exception as e:
        print(f"❌ Erreur: {e}")
        return []


def recompute_user(user_oid, user_name):
    """Lance un recompute sur un utilisateur pour appliquer l'auto-assignation."""
    url = f"{MIDPOINT_URL}/ws/rest/users/{user_oid}/recompute"
    
    headers = {
        'Content-Type': 'application/xml'
    }
    
    try:
        response = requests.post(
            url,
            headers=headers,
            auth=HTTPBasicAuth(MIDPOINT_USER, MIDPOINT_PASSWORD),
            timeout=30
        )
        
        if response.status_code in [200, 202, 204]:
            print(f"   ✅ {user_name}")
            return True
        else:
            print(f"   ❌ {user_name} - Erreur {response.status_code}")
            return False
            
    except Exception as e:
        print(f"   ❌ {user_name} - Erreur: {e}")
        return False


def recompute_all_users():
    """Lance un recompute sur tous les utilisateurs pour appliquer l'auto-assignation."""
    print("\n🔄 Lancement du recompute pour tous les utilisateurs...")
    print("   (Ceci va déclencher l'auto-assignation du rôle Employee)")
    
    users = get_all_users()
    
    if not users:
        print("⚠️  Aucun utilisateur à traiter")
        return
    
    success_count = 0
    failed_count = 0
    
    for user in users:
        if recompute_user(user['oid'], user['name']):
            success_count += 1
        else:
            failed_count += 1
    
    print(f"\n📊 Résultat du recompute:")
    print(f"   ✅ Réussis: {success_count}")
    print(f"   ❌ Échoués: {failed_count}")


def main():
    """Fonction principale."""
    print("=" * 70)
    print("🎯 Mise à jour du rôle Employee avec auto-assignation")
    print("=" * 70)
    print()
    
    # Étape 1: Lire le fichier XML
    print("📖 Étape 1: Lecture du fichier role-employee.xml")
    role_xml = read_role_xml()
    print(f"   ✅ Fichier lu ({len(role_xml)} caractères)")
    print()
    
    # Étape 2: Mettre à jour le rôle dans MidPoint
    print("📤 Étape 2: Mise à jour dans MidPoint via API REST")
    if not update_role_in_midpoint(role_xml):
        print("\n❌ Échec de la mise à jour du rôle. Abandon.")
        sys.exit(1)
    print()
    
    # Étape 3: Recompute de tous les utilisateurs
    print("🔄 Étape 3: Recompute des utilisateurs pour appliquer l'auto-assignation")
    recompute_all_users()
    print()
    
    print("=" * 70)
    print("✅ TERMINÉ - Le rôle Employee est maintenant en auto-assignation!")
    print("=" * 70)
    print()
    print("📝 Prochaines étapes:")
    print("   1. Vérifiez dans MidPoint UI que les utilisateurs ont le rôle Employee")
    print("   2. Créez John Malcovitch dans Odoo")
    print("   3. Exportez le CSV avec: python3 sync_odoo_to_csv.py")
    print("   4. La synchronisation se fera automatiquement (tâche toutes les 60s)")
    print("   5. John Malcovitch recevra automatiquement le rôle Employee")
    print()


if __name__ == "__main__":
    main()
