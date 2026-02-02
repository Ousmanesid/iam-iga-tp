#!/usr/bin/env python3
"""
Force l'import depuis la ressource CSV dans MidPoint
"""
import requests
from requests.auth import HTTPBasicAuth
import time

MIDPOINT_URL = "http://localhost:8080/midpoint"
MIDPOINT_USER = "administrator"
MIDPOINT_PASS = "5ecr3t"
CSV_RESOURCE_OID = "8a83b1a4-be18-11e6-ae84-7301fdab1d7c"  # OID de la ressource HR CSV

def test_resource():
    """Tester la connexion à la ressource"""
    print("🔌 Test de connexion à la ressource HR CSV...")
    
    response = requests.post(
        f"{MIDPOINT_URL}/ws/rest/resources/{CSV_RESOURCE_OID}/test",
        auth=HTTPBasicAuth(MIDPOINT_USER, MIDPOINT_PASS),
        headers={"Content-Type": "application/xml"},
        timeout=30
    )
    
    if response.status_code in [200, 204]:
        print("✅ Test de connexion réussi")
        return True
    else:
        print(f"❌ Test échoué: {response.status_code}")
        print(response.text[:500])
        return False

def import_from_resource():
    """Déclencher l'import depuis la ressource"""
    print("\n📥 Import depuis la ressource HR CSV...")
    
    # Créer une tâche d'import
    task_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<task xmlns="http://midpoint.evolveum.com/xml/ns/public/common/common-3"
      xmlns:q="http://prism.evolveum.com/xml/ns/public/query-3"
      xmlns:c="http://midpoint.evolveum.com/xml/ns/public/common/common-3">
    <name>Manual HR CSV Import</name>
    <extension>
        <mext:objectclass xmlns:mext="http://midpoint.evolveum.com/xml/ns/public/model/extension-3">ri:AccountObjectClass</mext:objectclass>
    </extension>
    <ownerRef oid="00000000-0000-0000-0000-000000000002" type="c:UserType"/>
    <executionStatus>runnable</executionStatus>
    <category>ImportingAccounts</category>
    <handlerUri>http://midpoint.evolveum.com/xml/ns/public/model/synchronization/task/import/handler-3</handlerUri>
    <recurrence>single</recurrence>
    <objectRef oid="{CSV_RESOURCE_OID}" type="c:ResourceType"/>
</task>"""
    
    response = requests.post(
        f"{MIDPOINT_URL}/ws/rest/tasks",
        auth=HTTPBasicAuth(MIDPOINT_USER, MIDPOINT_PASS),
        headers={"Content-Type": "application/xml"},
        data=task_xml,
        timeout=30
    )
    
    if response.status_code in [200, 201]:
        print("✅ Tâche d'import créée et lancée")
        print("\n💡 Allez dans MidPoint pour voir le progrès :")
        print("   http://localhost:8080/midpoint")
        print("   Menu: Server tasks → List tasks")
        return True
    else:
        print(f"❌ Échec création tâche: {response.status_code}")
        print(response.text[:500])
        return False

def main():
    print("=" * 70)
    print("🚀 IMPORT FORCÉ DEPUIS HR CSV")
    print("=" * 70)
    print(f"\nFichier source: /data/hr/hr_raw.csv")
    print(f"Ressource OID: {CSV_RESOURCE_OID}\n")
    
    # Test connexion
    if not test_resource():
        print("\n❌ Le test de ressource a échoué. Vérifiez la configuration.")
        return
    
    # Import
    if import_from_resource():
        print("\n" + "=" * 70)
        print("✅ Import déclenché avec succès !")
        print("=" * 70)
        print("\n📊 Pour suivre l'import :")
        print("   1. Allez sur http://localhost:8080/midpoint")
        print("   2. Menu: Server tasks → List tasks")
        print("   3. Cherchez 'Manual HR CSV Import'")
        print("   4. Ou allez dans Users → List users pour voir les nouveaux")
    else:
        print("\n❌ Échec de l'import. Essayez via l'interface web :")
        print("   http://localhost:8080/midpoint")
        print("   Resources → HR CSV Source → Import")

if __name__ == '__main__':
    main()
