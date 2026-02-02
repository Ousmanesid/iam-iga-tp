#!/usr/bin/env python3
"""
Script pour créer/recréer Alice Doe dans MidPoint
"""

import requests
import xml.etree.ElementTree as ET
from requests.auth import HTTPBasicAuth

# Configuration
MIDPOINT_URL = "http://localhost:8080/midpoint"
MIDPOINT_USER = "administrator"
MIDPOINT_PASSWORD = "Test5ecr3t"

NS = {
    'c': 'http://midpoint.evolveum.com/xml/ns/public/common/common-3',
    't': 'http://prism.evolveum.com/xml/ns/public/types-3'
}

def check_user_exists(name):
    """Vérifier si un utilisateur existe dans MidPoint."""
    url = f"{MIDPOINT_URL}/ws/rest/users"
    headers = {'Accept': 'application/xml'}
    
    print(f"🔍 Recherche de '{name}' dans MidPoint...")
    
    try:
        response = requests.get(
            url,
            headers=headers,
            auth=HTTPBasicAuth(MIDPOINT_USER, MIDPOINT_PASSWORD),
            timeout=60
        )
        
        if response.status_code != 200:
            print(f"❌ Erreur: {response.status_code}")
            return None
        
        root = ET.fromstring(response.content)
        
        for user in root.findall('.//c:object', NS):
            name_elem = user.find('c:name', NS)
            full_name_elem = user.find('.//c:fullName', NS)
            
            if name_elem is not None:
                user_name = name_elem.text
                full_name = full_name_elem.text if full_name_elem is not None else user_name
                
                if name.lower() in user_name.lower() or name.lower() in full_name.lower():
                    oid = user.get('oid')
                    print(f"✅ Utilisateur trouvé: {full_name} (name: {user_name}, OID: {oid})")
                    return {'oid': oid, 'name': user_name, 'fullName': full_name}
        
        print(f"❌ Utilisateur '{name}' non trouvé")
        return None
        
    except Exception as e:
        print(f"❌ Erreur: {e}")
        return None


def create_alice():
    """Créer Alice Doe dans MidPoint."""
    url = f"{MIDPOINT_URL}/ws/rest/users"
    
    user_xml = """<?xml version="1.0" encoding="UTF-8"?>
<user xmlns="http://midpoint.evolveum.com/xml/ns/public/common/common-3"
      xmlns:c="http://midpoint.evolveum.com/xml/ns/public/common/common-3"
      xmlns:t="http://prism.evolveum.com/xml/ns/public/types-3">
    <name>alice.doe</name>
    <fullName>Alice Doe</fullName>
    <givenName>Alice</givenName>
    <familyName>Doe</familyName>
    <emailAddress>Alice.doe@exemple.fr</emailAddress>
    <organizationalUnit>Ressources Humaines</organizationalUnit>
    <employeeNumber>1053</employeeNumber>
    <lifecycleState>active</lifecycleState>
</user>"""
    
    headers = {'Content-Type': 'application/xml'}
    
    print("➕ Création d'Alice Doe dans MidPoint...")
    
    try:
        response = requests.post(
            url,
            data=user_xml.encode('utf-8'),
            headers=headers,
            auth=HTTPBasicAuth(MIDPOINT_USER, MIDPOINT_PASSWORD),
            timeout=30
        )
        
        if response.status_code in [200, 201]:
            print(f"✅ Alice Doe créée avec succès (HTTP {response.status_code})")
            
            # Extraire l'OID de la réponse
            try:
                root = ET.fromstring(response.content)
                oid = root.get('oid')
                print(f"   📝 OID: {oid}")
                return oid
            except:
                print("   ⚠️  OID non trouvé dans la réponse")
                return True
        else:
            print(f"❌ Erreur lors de la création (HTTP {response.status_code})")
            print(f"   {response.text[:500]}")
            return None
            
    except Exception as e:
        print(f"❌ Erreur: {e}")
        return None


def assign_employee_role(user_oid):
    """Assigner le rôle Employee à un utilisateur."""
    url = f"{MIDPOINT_URL}/ws/rest/users/{user_oid}"
    
    # Récupérer l'utilisateur d'abord
    print("📥 Récupération de l'utilisateur...")
    headers = {'Accept': 'application/xml'}
    
    try:
        response = requests.get(
            url,
            headers=headers,
            auth=HTTPBasicAuth(MIDPOINT_USER, MIDPOINT_PASSWORD),
            timeout=30
        )
        
        if response.status_code != 200:
            print(f"❌ Impossible de récupérer l'utilisateur: {response.status_code}")
            return False
        
        # Parser le XML
        root = ET.fromstring(response.content)
        
        # Ajouter l'assignement Employee
        assignment = ET.SubElement(root, '{http://midpoint.evolveum.com/xml/ns/public/common/common-3}assignment')
        target_ref = ET.SubElement(assignment, '{http://midpoint.evolveum.com/xml/ns/public/common/common-3}targetRef')
        target_ref.set('oid', '00000000-0000-0000-0000-000000000104')  # OID du rôle Employee
        target_ref.set('type', 'RoleType')
        
        # Convertir en XML string
        ET.register_namespace('c', 'http://midpoint.evolveum.com/xml/ns/public/common/common-3')
        ET.register_namespace('t', 'http://prism.evolveum.com/xml/ns/public/types-3')
        user_xml = ET.tostring(root, encoding='utf-8', method='xml')
        
        # Mettre à jour l'utilisateur
        print("➕ Assignation du rôle Employee...")
        headers = {'Content-Type': 'application/xml'}
        
        response = requests.put(
            url,
            data=user_xml,
            headers=headers,
            auth=HTTPBasicAuth(MIDPOINT_USER, MIDPOINT_PASSWORD),
            timeout=30
        )
        
        if response.status_code in [200, 201, 204]:
            print(f"✅ Rôle Employee assigné avec succès (HTTP {response.status_code})")
            return True
        else:
            print(f"❌ Erreur lors de l'assignation (HTTP {response.status_code})")
            print(f"   {response.text[:500]}")
            return False
            
    except Exception as e:
        print(f"❌ Erreur: {e}")
        return False


def main():
    print("=" * 60)
    print("🔄 Création/Vérification d'Alice Doe dans MidPoint")
    print("=" * 60)
    print()
    
    # Vérifier si Alice existe
    user = check_user_exists("alice")
    
    if user:
        print()
        print("✅ Alice Doe existe déjà dans MidPoint")
        print(f"   OID: {user['oid']}")
        print(f"   Name: {user['name']}")
        print(f"   Full Name: {user['fullName']}")
        print()
        
        # Demander si on veut réassigner le rôle
        print("💡 Vous pouvez maintenant:")
        print("   1. Aller dans MidPoint → Users → Alice Doe")
        print("   2. Vérifier/Réassigner le rôle Employee")
        return 0
    
    print()
    
    # Créer Alice
    result = create_alice()
    
    if not result:
        print("\n❌ Échec de la création d'Alice")
        return 1
    
    print()
    print("=" * 60)
    print("✅ Alice Doe créée dans MidPoint!")
    print("=" * 60)
    print()
    print("🔄 Prochaines étapes:")
    print("   1. Aller dans MidPoint → Users → Alice Doe")
    print("   2. Assigner le rôle Employee")
    print("   3. Vérifier les projections LDAP et Odoo")
    print("   4. Vérifier les groupes LDAP:")
    print("      docker exec -it openldap ldapsearch -x -H ldap://localhost \\")
    print("        -b \"ou=groups,dc=example,dc=com\" \\")
    print("        -D \"cn=admin,dc=example,dc=com\" -w admin \\")
    print("        \"(member=uid=alice.doe,ou=users,dc=example,dc=com)\" dn")
    print()
    
    return 0

if __name__ == "__main__":
    exit(main())
