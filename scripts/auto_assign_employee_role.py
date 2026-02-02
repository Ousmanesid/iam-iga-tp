#!/usr/bin/env python3
"""
Script d'assignation automatique du rôle Employee à tous les utilisateurs MidPoint.

Ce script:
1. Récupère tous les utilisateurs depuis MidPoint
2. Vérifie s'ils ont déjà le rôle Employee
3. Assigne le rôle Employee à ceux qui ne l'ont pas

Usage:
    python3 auto_assign_employee_role.py [--dry-run]
"""

import requests
import xml.etree.ElementTree as ET
from requests.auth import HTTPBasicAuth
import sys
import argparse

# Configuration MidPoint
MIDPOINT_URL = "http://localhost:8080/midpoint"
MIDPOINT_USER = "administrator"
MIDPOINT_PASSWORD = "Test5ecr3t"

# OID du rôle Employee
EMPLOYEE_ROLE_OID = "00000000-0000-0000-0000-000000000104"
EMPLOYEE_ROLE_NAME = "Employee"

# Namespace MidPoint
NS = {
    'c': 'http://midpoint.evolveum.com/xml/ns/public/common/common-3',
    't': 'http://prism.evolveum.com/xml/ns/public/types-3'
}


def get_all_users():
    """Récupère la liste de tous les utilisateurs MidPoint avec leurs détails."""
    url = f"{MIDPOINT_URL}/ws/rest/users"
    
    headers = {
        'Accept': 'application/xml'
    }
    
    print("📋 Récupération de la liste des utilisateurs...")
    
    try:
        response = requests.get(
            url,
            headers=headers,
            auth=HTTPBasicAuth(MIDPOINT_USER, MIDPOINT_PASSWORD),
            timeout=60
        )
        
        if response.status_code == 200:
            root = ET.fromstring(response.content)
            users = []
            
            for user in root.findall('.//c:object', NS):
                oid = user.get('oid')
                name_elem = user.find('c:name', NS)
                name = name_elem.text if name_elem is not None else "Unknown"
                
                # Exclure l'administrateur
                if oid and name.lower() != 'administrator':
                    users.append({'oid': oid, 'name': name})
            
            print(f"✅ {len(users)} utilisateurs trouvés (hors administrator)")
            return users
        else:
            print(f"❌ Erreur lors de la récupération: {response.status_code}")
            print(response.text[:500])
            return []
            
    except requests.exceptions.ConnectionError:
        print("❌ Impossible de se connecter à MidPoint")
        print(f"   Vérifiez que MidPoint est démarré sur {MIDPOINT_URL}")
        return []
    except Exception as e:
        print(f"❌ Erreur: {e}")
        return []


def get_user_roles(user_oid):
    """Récupère les rôles assignés à un utilisateur."""
    url = f"{MIDPOINT_URL}/ws/rest/users/{user_oid}"
    
    headers = {
        'Accept': 'application/xml'
    }
    
    try:
        response = requests.get(
            url,
            headers=headers,
            auth=HTTPBasicAuth(MIDPOINT_USER, MIDPOINT_PASSWORD),
            timeout=30
        )
        
        if response.status_code == 200:
            root = ET.fromstring(response.content)
            roles = []
            
            # Chercher les assignments de type Role
            for assignment in root.findall('.//c:assignment', NS):
                target_ref = assignment.find('c:targetRef', NS)
                if target_ref is not None:
                    ref_type = target_ref.get('type', '')
                    ref_oid = target_ref.get('oid', '')
                    if 'RoleType' in ref_type:
                        roles.append(ref_oid)
            
            return roles
        else:
            return []
            
    except Exception as e:
        return []


def assign_employee_role(user_oid, user_name, dry_run=False):
    """Assigne le rôle Employee à un utilisateur via l'API REST."""
    
    if dry_run:
        print(f"   [DRY-RUN] Assignerait Employee à {user_name}")
        return True
    
    url = f"{MIDPOINT_URL}/ws/rest/users/{user_oid}"
    
    # XML pour ajouter l'assignment du rôle Employee
    modification_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<objectModification
    xmlns="http://midpoint.evolveum.com/xml/ns/public/common/api-types-3"
    xmlns:c="http://midpoint.evolveum.com/xml/ns/public/common/common-3"
    xmlns:t="http://prism.evolveum.com/xml/ns/public/types-3">
    <itemDelta>
        <t:modificationType>add</t:modificationType>
        <t:path>c:assignment</t:path>
        <t:value>
            <c:targetRef oid="{EMPLOYEE_ROLE_OID}" type="c:RoleType"/>
        </t:value>
    </itemDelta>
</objectModification>"""

    headers = {
        'Content-Type': 'application/xml',
        'Accept': 'application/xml'
    }
    
    try:
        response = requests.patch(
            url,
            data=modification_xml.encode('utf-8'),
            headers=headers,
            auth=HTTPBasicAuth(MIDPOINT_USER, MIDPOINT_PASSWORD),
            timeout=30
        )
        
        if response.status_code in [200, 204]:
            print(f"   ✅ {user_name} - Rôle Employee assigné")
            return True
        elif response.status_code == 409:
            # Conflit - probablement déjà assigné
            print(f"   ⚠️  {user_name} - Déjà assigné ou conflit")
            return True
        else:
            print(f"   ❌ {user_name} - Erreur {response.status_code}")
            if response.text:
                # Extraire le message d'erreur
                try:
                    error_root = ET.fromstring(response.content)
                    message = error_root.find('.//message')
                    if message is not None:
                        print(f"      Message: {message.text[:100]}")
                except:
                    pass
            return False
            
    except Exception as e:
        print(f"   ❌ {user_name} - Erreur: {e}")
        return False


def recompute_user(user_oid, user_name):
    """Lance un recompute sur un utilisateur."""
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
        
        return response.status_code in [200, 202, 204]
    except:
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Assigner automatiquement le rôle Employee aux utilisateurs MidPoint"
    )
    parser.add_argument(
        '--dry-run', '-d',
        action='store_true',
        help="Affiche les changements sans les appliquer"
    )
    parser.add_argument(
        '--recompute', '-r',
        action='store_true',
        help="Lance aussi un recompute sur chaque utilisateur"
    )
    
    args = parser.parse_args()
    
    print("=" * 70)
    print("🎯 ASSIGNATION AUTOMATIQUE DU RÔLE EMPLOYEE")
    print("=" * 70)
    
    if args.dry_run:
        print("⚠️  Mode DRY-RUN : aucun changement ne sera effectué\n")
    
    # Récupérer tous les utilisateurs
    users = get_all_users()
    
    if not users:
        print("\n❌ Aucun utilisateur trouvé ou erreur de connexion")
        sys.exit(1)
    
    print(f"\n🔄 Traitement des utilisateurs...\n")
    
    stats = {
        'already_has_role': 0,
        'role_assigned': 0,
        'errors': 0
    }
    
    for user in users:
        user_oid = user['oid']
        user_name = user['name']
        
        # Vérifier si l'utilisateur a déjà le rôle
        current_roles = get_user_roles(user_oid)
        
        if EMPLOYEE_ROLE_OID in current_roles:
            print(f"   ✓ {user_name} - A déjà le rôle Employee")
            stats['already_has_role'] += 1
        else:
            # Assigner le rôle
            if assign_employee_role(user_oid, user_name, dry_run=args.dry_run):
                stats['role_assigned'] += 1
                
                # Recompute si demandé
                if args.recompute and not args.dry_run:
                    recompute_user(user_oid, user_name)
            else:
                stats['errors'] += 1
    
    # Résumé
    print("\n" + "=" * 70)
    print("📊 RÉSUMÉ")
    print("=" * 70)
    print(f"   Utilisateurs traités : {len(users)}")
    print(f"   Avaient déjà le rôle : {stats['already_has_role']}")
    print(f"   Rôles assignés       : {stats['role_assigned']}")
    print(f"   Erreurs              : {stats['errors']}")
    print("=" * 70)
    
    if not args.dry_run and stats['role_assigned'] > 0:
        print("\n✅ Les rôles ont été assignés avec succès!")
        print("   Vérifiez dans MidPoint: http://localhost:8080/midpoint")
        print("   Menu: Users → List users → Cliquez sur un utilisateur → Assignments")


if __name__ == '__main__':
    main()
