#!/usr/bin/env python3
"""
Réapparition d'Alice après import — 100 % via l'API REST MidPoint.

1. Recherche des shadows HR CSV (resourceRef = ressource HR) via POST /shadows/search
2. Supprime les shadows dont le nom (personalNumber) est 1053 (Alice Doe)
3. Lance une tâche d'import depuis la ressource HR CSV

Prérequis : Alice doit être dans data/hr/hr_clean.csv (ligne personalNumber 1053).
"""
import requests
import xml.etree.ElementTree as ET
from requests.auth import HTTPBasicAuth

MIDPOINT_URL = "http://localhost:8080/midpoint"
MIDPOINT_USER = "administrator"
MIDPOINT_PASS = "Test5ecr3t"
HR_CSV_RESOURCE_OID = "8a83b1a4-be18-11e6-ae84-7301fdab1d7c"
ALICE_PERSONAL_NUMBER = "1053"

# Namespaces courants dans les réponses MidPoint
NS = {
    "q": "http://prism.evolveum.com/xml/ns/public/query-3",
    "c": "http://midpoint.evolveum.com/xml/ns/public/common/common-3",
    "t": "http://prism.evolveum.com/xml/ns/public/types-3",
    "apti": "http://midpoint.evolveum.com/xml/ns/public/common/api-types-3",
}


def _local_name(tag):
    return tag.split("}")[-1] if "}" in tag else tag


def search_shadows_hr_csv():
    """POST /ws/rest/shadows/search avec filtre resourceRef = HR CSV. Retourne liste de (oid, name)."""
    url = f"{MIDPOINT_URL}/ws/rest/shadows/search"
    query_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<q:query xmlns:q="http://prism.evolveum.com/xml/ns/public/query-3"
         xmlns:c="http://midpoint.evolveum.com/xml/ns/public/common/common-3">
    <q:filter>
        <q:equal>
            <q:path>resourceRef</q:path>
            <q:value>
                <c:oid>{HR_CSV_RESOURCE_OID}</c:oid>
            </q:value>
        </q:equal>
    </q:filter>
</q:query>"""
    r = requests.post(
        url,
        auth=HTTPBasicAuth(MIDPOINT_USER, MIDPOINT_PASS),
        headers={"Content-Type": "application/xml", "Accept": "application/xml"},
        data=query_xml,
        timeout=60,
    )
    if r.status_code != 200:
        print(f"   ❌ Recherche shadows: HTTP {r.status_code}")
        return []

    root = ET.fromstring(r.content)
    results = []
    # Chercher les éléments "object" (shadow) avec attribut oid (UUID)
    for elem in root.iter():
        tag_local = _local_name(elem.tag)
        if tag_local not in ("object", "ShadowType"):
            continue
        oid = elem.get("oid")
        if not oid or len(oid) != 36 or "-" not in oid:
            continue
        name_el = None
        for child in elem.iter():
            if _local_name(child.tag) == "name" and child.text:
                name_el = child
                break
        if name_el is not None:
            results.append((oid, name_el.text.strip()))
    # Dédupliquer par oid
    seen = set()
    unique = []
    for oid, name in results:
        if oid not in seen:
            seen.add(oid)
            unique.append((oid, name))
    return unique


def delete_shadow(oid):
    """DELETE /ws/rest/shadows/{oid}"""
    r = requests.delete(
        f"{MIDPOINT_URL}/ws/rest/shadows/{oid}",
        auth=HTTPBasicAuth(MIDPOINT_USER, MIDPOINT_PASS),
        timeout=30,
    )
    return r.status_code in (200, 204)


def run_import_task():
    """POST /ws/rest/tasks — crée et lance une tâche d'import HR CSV."""
    # Namespace ri obligatoire pour ri:AccountObjectClass
    task_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<task xmlns="http://midpoint.evolveum.com/xml/ns/public/common/common-3"
      xmlns:c="http://midpoint.evolveum.com/xml/ns/public/common/common-3"
      xmlns:ri="http://midpoint.evolveum.com/xml/ns/public/resource/instance-3"
      xmlns:mext="http://midpoint.evolveum.com/xml/ns/public/model/extension-3">
    <name>Manual HR CSV Import (fix Alice)</name>
    <extension>
        <mext:objectclass>ri:AccountObjectClass</mext:objectclass>
    </extension>
    <ownerRef oid="00000000-0000-0000-0000-000000000002" type="c:UserType"/>
    <executionStatus>runnable</executionStatus>
    <category>ImportingAccounts</category>
    <handlerUri>http://midpoint.evolveum.com/xml/ns/public/model/synchronization/task/import/handler-3</handlerUri>
    <recurrence>single</recurrence>
    <objectRef oid="{HR_CSV_RESOURCE_OID}" type="c:ResourceType"/>
</task>"""
    r = requests.post(
        f"{MIDPOINT_URL}/ws/rest/tasks",
        auth=HTTPBasicAuth(MIDPOINT_USER, MIDPOINT_PASS),
        headers={"Content-Type": "application/xml"},
        data=task_xml,
        timeout=30,
    )
    if r.status_code in (200, 201, 202):
        print("   ✅ Tâche d'import créée et lancée (HTTP %s)." % r.status_code)
        return True
    print(f"   ❌ Création tâche: HTTP {r.status_code}")
    return False


def main():
    print("=" * 60)
    print("🔧 Réapparition d'Alice après import (API REST uniquement)")
    print("=" * 60)
    print()

    print("1. Recherche des shadows HR CSV (POST /shadows/search)...")
    shadows = search_shadows_hr_csv()
    to_delete = [(oid, name) for oid, name in shadows if name == ALICE_PERSONAL_NUMBER]
    if not to_delete:
        print("   Aucun shadow trouvé pour personalNumber 1053 (normal si déjà supprimé).")
    else:
        for oid, name in to_delete:
            print(f"   Suppression du shadow OID {oid} (name={name})...")
            if delete_shadow(oid):
                print("   ✅ Shadow supprimé.")
            else:
                print("   ⚠️ Échec suppression.")

    print()
    print("2. Lancement d'une tâche d'import (POST /tasks)...")
    run_import_task()
    print()
    print("=" * 60)
    print("✅ Terminé. Attendre quelques secondes puis :")
    print("   MidPoint → Users → List users → rechercher Alice ou 1053")
    print("=" * 60)


if __name__ == "__main__":
    main()
