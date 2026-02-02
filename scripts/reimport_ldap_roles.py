#!/usr/bin/env python3
"""
Script pour réimporter les rôles LDAP corrigés dans MidPoint
"""

import requests
import os
from requests.auth import HTTPBasicAuth
import xml.etree.ElementTree as ET

# Configuration
MIDPOINT_URL = "http://localhost:8080/midpoint"
MIDPOINT_USER = "administrator"
MIDPOINT_PASSWORD = "Test5ecr3t"
ROLES_DIR = "/srv/projet/iam-iga-tp/config/midpoint/roles"

ROLES = [
    "role-ldap-employee.xml",
    "role-ldap-internet.xml",
    "role-ldap-printer.xml",
    "role-ldap-sharepoint.xml"
]

def extract_oid(xml_file):
    """Extraire l'OID d'un fichier XML de rôle."""
    tree = ET.parse(xml_file)
    root = tree.getroot()
    return root.get('oid')

def import_or_update_role(role_file):
    """Importer ou mettre à jour un rôle dans MidPoint."""
    role_path = os.path.join(ROLES_DIR, role_file)
    
    if not os.path.exists(role_path):
        print(f"   ❌ Fichier non trouvé: {role_path}")
        return False
    
    print(f"➕ Traitement de {role_file}...")
    
    # Lire le contenu XML
    with open(role_path, 'r', encoding='utf-8') as f:
        xml_content = f.read()
    
    # Extraire l'OID
    oid = extract_oid(role_path)
    if not oid:
        print(f"   ❌ Impossible d'extraire l'OID")
        return False
    
    print(f"   📝 OID: {oid}")
    
    # Essayer de mettre à jour (PUT)
    url = f"{MIDPOINT_URL}/ws/rest/roles/{oid}"
    headers = {'Content-Type': 'application/xml'}
    
    try:
        response = requests.put(
            url,
            data=xml_content.encode('utf-8'),
            headers=headers,
            auth=HTTPBasicAuth(MIDPOINT_USER, MIDPOINT_PASSWORD),
            timeout=30
        )
        
        if response.status_code in [200, 201, 204]:
            print(f"   ✅ Mis à jour avec succès (HTTP {response.status_code})")
            return True
        elif response.status_code == 404:
            # Le rôle n'existe pas, essayer de le créer
            print(f"   ⚠️  Rôle non trouvé, création...")
            url = f"{MIDPOINT_URL}/ws/rest/roles"
            response = requests.post(
                url,
                data=xml_content.encode('utf-8'),
                headers=headers,
                auth=HTTPBasicAuth(MIDPOINT_USER, MIDPOINT_PASSWORD),
                timeout=30
            )
            
            if response.status_code in [200, 201]:
                print(f"   ✅ Créé avec succès (HTTP {response.status_code})")
                return True
            else:
                print(f"   ❌ Erreur lors de la création (HTTP {response.status_code})")
                print(f"   {response.text[:500]}")
                return False
        else:
            print(f"   ❌ Erreur lors de la mise à jour (HTTP {response.status_code})")
            print(f"   {response.text[:500]}")
            return False
            
    except requests.exceptions.ConnectionError:
        print(f"   ❌ Impossible de se connecter à MidPoint")
        return False
    except Exception as e:
        print(f"   ❌ Erreur: {e}")
        return False

def main():
    print("=" * 60)
    print("🔄 Réimport des rôles LDAP corrigés dans MidPoint")
    print("=" * 60)
    print()
    
    print(f"📋 Rôles à mettre à jour: {len(ROLES)}")
    for role in ROLES:
        print(f"   - {role}")
    print()
    
    success_count = 0
    fail_count = 0
    
    for role in ROLES:
        if import_or_update_role(role):
            success_count += 1
        else:
            fail_count += 1
        print()
    
    print("=" * 60)
    print("📊 Résumé:")
    print(f"   ✅ Succès: {success_count}")
    print(f"   ❌ Échecs: {fail_count}")
    print("=" * 60)
    print()
    
    if success_count > 0:
        print("🔄 Prochaines étapes:")
        print("   1. Aller dans MidPoint → Users → Alice Doe")
        print("   2. Supprimer l'assignement Employee actuel")
        print("   3. Réassigner le rôle Employee (nouveau)")
        print("   4. Save et attendre le recompute")
        print("   5. Vérifier les groupes LDAP:")
        print("      docker exec -it openldap ldapsearch -x -H ldap://localhost \\")
        print("        -b \"ou=groups,dc=example,dc=com\" \\")
        print("        -D \"cn=admin,dc=example,dc=com\" -w admin \\")
        print("        \"(member=uid=alice.doe,ou=users,dc=example,dc=com)\" dn")
        print()
    
    return 0 if fail_count == 0 else 1

if __name__ == "__main__":
    exit(main())
