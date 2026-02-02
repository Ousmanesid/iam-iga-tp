#!/usr/bin/env python3
"""
Import les employés manquants (1035-1043) dans MidPoint
"""
import requests
from requests.auth import HTTPBasicAuth
import json

MIDPOINT_URL = "http://localhost:8080/midpoint"
MIDPOINT_USER = "administrator"
MIDPOINT_PASS = "5ecr3t"

# Employés à importer (récupérés depuis Odoo)
EMPLOYEES = [
    {"personalNumber": "1035", "givenName": "doue", "familyName": "test", "department": "Unassigned"},
    {"personalNumber": "1036", "givenName": "yamal", "familyName": "test", "department": "Unassigned"},
    {"personalNumber": "1037", "givenName": "marquinos", "familyName": "test barca", "department": "Unassigned"},
    {"personalNumber": "1038", "givenName": "barcola", "familyName": "test", "department": "Unassigned"},
    {"personalNumber": "1039", "givenName": "raphina", "familyName": "test", "department": "Unassigned"},
    {"personalNumber": "1040", "givenName": "debrune", "familyName": "test", "department": "Unassigned"},
    {"personalNumber": "1041", "givenName": "mayulu", "familyName": "", "department": "Unassigned"},
    {"personalNumber": "1042", "givenName": "Gusto", "familyName": "Malori", "department": "Unassigned"},
    {"personalNumber": "1043", "givenName": "mario", "familyName": "senny", "department": "Unassigned"},
]

def check_user_exists(personal_number):
    """Vérifier si un utilisateur existe"""
    try:
        response = requests.get(
            f"{MIDPOINT_URL}/ws/rest/users",
            auth=HTTPBasicAuth(MIDPOINT_USER, MIDPOINT_PASS),
            headers={"Accept": "application/json"},
            params={"query": f"name = '{personal_number}'"},
            timeout=10
        )
        if response.status_code == 200:
            result = response.json()
            return result.get('totalCount', 0) > 0
    except:
        pass
    return False

def create_user(emp):
    """Créer un utilisateur"""
    given_name = emp['givenName'] or "Unknown"
    family_name = emp['familyName'] or "Unknown"
    email = f"{given_name.lower()}.{family_name.lower().replace(' ', '')}@example.com"
    
    user_data = {
        "user": {
            "@xmlns": "http://midpoint.evolveum.com/xml/ns/public/common/common-3",
            "name": emp['personalNumber'],
            "givenName": given_name,
            "familyName": family_name,
            "fullName": f"{given_name} {family_name}".strip(),
            "emailAddress": email,
            "employeeNumber": emp['personalNumber'],
            "organization": emp['department'],
            "activation": {
                "administrativeStatus": "enabled"
            }
        }
    }
    
    try:
        response = requests.post(
            f"{MIDPOINT_URL}/ws/rest/users",
            auth=HTTPBasicAuth(MIDPOINT_USER, MIDPOINT_PASS),
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json"
            },
            data=json.dumps(user_data),
            timeout=30
        )
        
        if response.status_code in [200, 201]:
            user_oid = response.json().get('oid')
            
            # Recompute
            if user_oid:
                requests.post(
                    f"{MIDPOINT_URL}/ws/rest/users/{user_oid}/recompute",
                    auth=HTTPBasicAuth(MIDPOINT_USER, MIDPOINT_PASS),
                    timeout=30
                )
            
            return True, "Créé + recompute"
        else:
            return False, f"HTTP {response.status_code}"
    except Exception as e:
        return False, str(e)

def main():
    print("=" * 70)
    print("🔄 IMPORT DES EMPLOYÉS MANQUANTS (1035-1043)")
    print("=" * 70)
    
    created = 0
    skipped = 0
    errors = 0
    
    for emp in EMPLOYEES:
        personal_number = emp['personalNumber']
        full_name = f"{emp['givenName']} {emp['familyName']}".strip()
        
        print(f"\n📋 {personal_number}: {full_name}")
        
        if check_user_exists(personal_number):
            print(f"   ⏭️  Existe déjà")
            skipped += 1
            continue
        
        success, message = create_user(emp)
        if success:
            print(f"   ✅ {message}")
            created += 1
        else:
            print(f"   ❌ {message}")
            errors += 1
    
    print("\n" + "=" * 70)
    print("📊 RÉSUMÉ")
    print("=" * 70)
    print(f"   Total: {len(EMPLOYEES)}")
    print(f"   ✨ Créés: {created}")
    print(f"   ⏭️  Ignorés: {skipped}")
    print(f"   ❌ Erreurs: {errors}")
    print("=" * 70)

if __name__ == '__main__':
    main()
