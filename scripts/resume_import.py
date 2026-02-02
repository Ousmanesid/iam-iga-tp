#!/usr/bin/env python3
"""
Reprendre l'import MidPoint depuis le dernier utilisateur
"""
import requests
from requests.auth import HTTPBasicAuth
import json
import subprocess

MIDPOINT_URL = "http://localhost:8080/midpoint"
MIDPOINT_USER = "administrator"
MIDPOINT_PASS = "5ecr3t"

def get_odoo_employees_from_db(start_personal_number=None):
    """Récupérer les employés depuis la base Odoo"""
    where_clause = f"WHERE e.name IS NOT NULL AND (e.id + 1000) >= {start_personal_number}" if start_personal_number else "WHERE e.name IS NOT NULL"
    
    cmd = f"""docker exec odoo-db psql -U odoo -d odoo -t -A -F'|' -c "
SELECT 
    (e.id + 1000) AS personalNumber,
    SPLIT_PART(e.name, ' ', 1) AS givenName,
    CASE 
        WHEN POSITION(' ' IN e.name) > 0 
        THEN SUBSTRING(e.name FROM POSITION(' ' IN e.name) + 1)
        ELSE e.name
    END AS familyName,
    COALESCE(e.work_email, '') AS email,
    COALESCE(
        CASE 
            WHEN d.name LIKE '{{%' THEN 
                TRIM(BOTH '\\\"' FROM (regexp_match(d.name::text, '\\\"en_US\\\":\\\\s*\\\"([^\\\"]+)\\\"'))[1])
            ELSE d.name
        END,
        'Unassigned'
    ) AS department,
    COALESCE(e.job_title, 'Employee') AS title,
    CASE 
        WHEN e.active = true THEN 'Active'
        ELSE 'Suspended'
    END AS status
FROM hr_employee e
LEFT JOIN hr_department d ON e.department_id = d.id
{where_clause}
ORDER BY e.id
"
"""
    
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    
    employees = []
    for line in result.stdout.strip().split('\n'):
        if line.strip():
            parts = line.split('|')
            if len(parts) >= 7:
                employees.append({
                    'personalNumber': parts[0].strip(),
                    'givenName': parts[1].strip(),
                    'familyName': parts[2].strip(),
                    'email': parts[3].strip(),
                    'department': parts[4].strip() if parts[4].strip() else 'Unassigned',
                    'title': parts[5].strip(),
                    'status': parts[6].strip()
                })
    
    return employees

def check_user_exists(personal_number):
    """Vérifier si un utilisateur existe dans MidPoint"""
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
    """Créer un utilisateur dans MidPoint"""
    email = emp['email'] if emp['email'] else f"{emp['givenName'].lower()}.{emp['familyName'].lower()}@example.com"
    
    user_data = {
        "user": {
            "@xmlns": "http://midpoint.evolveum.com/xml/ns/public/common/common-3",
            "name": emp['personalNumber'],
            "givenName": emp['givenName'],
            "familyName": emp['familyName'],
            "fullName": f"{emp['givenName']} {emp['familyName']}",
            "emailAddress": email,
            "employeeNumber": emp['personalNumber'],
            "organization": emp['department'],
            "organizationalUnit": emp['department'],
            "additionalName": emp['title'],
            "activation": {
                "administrativeStatus": "enabled" if emp['status'] == 'Active' else "disabled"
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
            
            # Recompute pour auto-assignment des rôles
            if user_oid:
                recompute_response = requests.post(
                    f"{MIDPOINT_URL}/ws/rest/users/{user_oid}/recompute",
                    auth=HTTPBasicAuth(MIDPOINT_USER, MIDPOINT_PASS),
                    timeout=30
                )
            
            return True, "Créé"
        else:
            return False, f"HTTP {response.status_code}: {response.text[:200]}"
    except Exception as e:
        return False, str(e)

def main():
    print("=" * 70)
    print("🔄 REPRISE DE L'IMPORT MIDPOINT")
    print("=" * 70)
    
    # Récupérer tous les employés depuis 1035
    print("\n📋 Récupération des employés depuis Odoo (à partir de 1035)...")
    employees = get_odoo_employees_from_db(start_personal_number=1035)
    print(f"   → {len(employees)} employés trouvés")
    
    created = 0
    skipped = 0
    errors = 0
    
    for emp in employees:
        personal_number = emp['personalNumber']
        full_name = f"{emp['givenName']} {emp['familyName']}"
        
        print(f"\n📋 {personal_number}: {full_name}")
        
        # Vérifier si existe déjà
        if check_user_exists(personal_number):
            print(f"   ⏭️  Existe déjà")
            skipped += 1
            continue
        
        # Créer
        success, message = create_user(emp)
        if success:
            print(f"   ✅ {message}")
            created += 1
        else:
            print(f"   ❌ {message}")
            errors += 1
    
    # Résumé
    print("\n" + "=" * 70)
    print("📊 RÉSUMÉ")
    print("=" * 70)
    print(f"   Total traité: {len(employees)}")
    print(f"   ✨ Créés: {created}")
    print(f"   ⏭️  Ignorés: {skipped}")
    print(f"   ❌ Erreurs: {errors}")
    print("=" * 70)

if __name__ == '__main__':
    main()
