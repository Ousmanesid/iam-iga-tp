#!/usr/bin/env python3
"""
Script pour forcer le recompute d'Alice Doe via l'API REST MidPoint
"""

import requests
import xml.etree.ElementTree as ET
from requests.auth import HTTPBasicAuth

# Configuration MidPoint
MIDPOINT_URL = "http://localhost:8080/midpoint"
MIDPOINT_USER = "administrator"
MIDPOINT_PASSWORD = "Test5ecr3t"

NS = {
    'c': 'http://midpoint.evolveum.com/xml/ns/public/common/common-3',
    't': 'http://prism.evolveum.com/xml/ns/public/types-3'
}

def find_user_by_name(name):
    """Trouve un utilisateur par son nom."""
    url = f"{MIDPOINT_URL}/ws/rest/users"
    headers = {'Accept': 'application/xml'}
    
    print(f"🔍 Recherche de l'utilisateur '{name}'...")
    
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
        if name_elem is not None and name.lower() in name_elem.text.lower():
            oid = user.get('oid')
            full_name_elem = user.find('.//c:fullName', NS)
            full_name = full_name_elem.text if full_name_elem is not None else name_elem.text
            print(f"✅ Utilisateur trouvé: {full_name} (OID: {oid})")
            return oid
    
    print(f"❌ Utilisateur '{name}' non trouvé")
    return None


def recompute_user(oid):
    """Lance un recompute pour un utilisateur."""
    url = f"{MIDPOINT_URL}/ws/rest/users/{oid}"
    
    # Payload pour le recompute
    payload = """<?xml version="1.0" encoding="UTF-8"?>
<executeScript xmlns="http://midpoint.evolveum.com/xml/ns/public/common/api-types-3"
               xmlns:c="http://midpoint.evolveum.com/xml/ns/public/common/common-3">
    <script>
        <code>
            import com.evolveum.midpoint.xml.ns._public.common.common_3.UserType;
            midpoint.recompute(UserType.class, '{oid}')
        </code>
    </script>
</executeScript>"""
    
    payload = payload.format(oid=oid)
    
    headers = {
        'Content-Type': 'application/xml'
    }
    
    print(f"⚙️  Lancement du recompute...")
    
    # Utiliser l'endpoint de tâches
    task_url = f"{MIDPOINT_URL}/ws/rest/tasks"
    
    task_payload = f"""<?xml version="1.0" encoding="UTF-8"?>
<task xmlns="http://midpoint.evolveum.com/xml/ns/public/common/common-3"
      xmlns:c="http://midpoint.evolveum.com/xml/ns/public/common/common-3"
      xmlns:q="http://prism.evolveum.com/xml/ns/public/query-3">
    <name>Recompute Alice Doe</name>
    <extension>
        <mext:objectType xmlns:mext="http://midpoint.evolveum.com/xml/ns/public/model/extension-3">UserType</mext:objectType>
    </extension>
    <objectRef oid="{oid}" type="UserType"/>
    <ownerRef oid="00000000-0000-0000-0000-000000000002" type="UserType"/>
    <executionStatus>runnable</executionStatus>
    <category>Recomputation</category>
    <handlerUri>http://midpoint.evolveum.com/xml/ns/public/model/synchronization/task/recompute/handler-3</handlerUri>
    <recurrence>single</recurrence>
</task>"""
    
    response = requests.post(
        task_url,
        data=task_payload,
        headers=headers,
        auth=HTTPBasicAuth(MIDPOINT_USER, MIDPOINT_PASSWORD),
        timeout=60
    )
    
    if response.status_code in [200, 201, 202]:
        print(f"✅ Recompute lancé avec succès!")
        return True
    else:
        print(f"❌ Erreur lors du recompute: {response.status_code}")
        print(response.text[:1000])
        return False


def reconcile_user(oid):
    """Alternative: Utiliser reconcile au lieu de recompute."""
    url = f"{MIDPOINT_URL}/ws/rest/users/{oid}/operations/reconcile"
    
    headers = {
        'Content-Type': 'application/xml'
    }
    
    print(f"⚙️  Lancement de la réconciliation...")
    
    response = requests.post(
        url,
        headers=headers,
        auth=HTTPBasicAuth(MIDPOINT_USER, MIDPOINT_PASSWORD),
        timeout=60
    )
    
    if response.status_code in [200, 201, 202, 204]:
        print(f"✅ Réconciliation lancée avec succès!")
        return True
    else:
        print(f"❌ Erreur: {response.status_code}")
        print(response.text[:1000])
        return False


if __name__ == "__main__":
    print("=" * 60)
    print("🔄 Recompute Alice Doe via API REST MidPoint")
    print("=" * 60)
    print()
    
    # Trouver Alice
    oid = find_user_by_name("alice")
    
    if not oid:
        print("\n❌ Impossible de continuer sans l'OID d'Alice")
        exit(1)
    
    print()
    
    # Essayer la réconciliation (plus simple)
    success = reconcile_user(oid)
    
    if not success:
        print("\n⚠️  Tentative avec recompute...")
        success = recompute_user(oid)
    
    if success:
        print("\n" + "=" * 60)
        print("✅ Opération terminée! Vérifiez maintenant les groupes LDAP:")
        print("   docker exec -it openldap ldapsearch -x -H ldap://localhost \\")
        print("     -b \"ou=groups,dc=example,dc=com\" \\")
        print("     -D \"cn=admin,dc=example,dc=com\" -w admin \\")
        print("     \"(member=uid=alice.doe,ou=users,dc=example,dc=com)\" dn")
        print("=" * 60)
    else:
        print("\n❌ Échec du recompute")
        exit(1)
