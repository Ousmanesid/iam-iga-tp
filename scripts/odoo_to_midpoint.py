#!/usr/bin/env python3
"""
Import complet : Odoo → CSV → MidPoint
Étapes:
1. Exporter les employés depuis Odoo via XML-RPC
2. Écrire dans hr_raw.csv (format propre)
3. Importer dans MidPoint via API REST
"""

import csv
import xmlrpc.client
import requests
from requests.auth import HTTPBasicAuth
import json

# ============================================================================
# CONFIGURATION
# ============================================================================
ODOO_URL = "http://localhost:8069"
ODOO_DB = "odoo"
ODOO_USERNAME = "midpoint_service"
ODOO_PASSWORD = "midpoint123"

MIDPOINT_URL = "http://localhost:8080/midpoint"
MIDPOINT_USER = "administrator"
MIDPOINT_PASS = "5ecr3t"

CSV_OUTPUT = "/srv/projet/iam-iga-tp/data/hr/hr_raw.csv"

# ============================================================================
# ÉTAPE 1: EXPORT DEPUIS ODOO
# ============================================================================
def export_from_odoo():
    """Exporter les employés depuis Odoo"""
    print("\n" + "="*70)
    print("📥 ÉTAPE 1: Export depuis Odoo")
    print("="*70)
    
    print(f"🔗 Connexion à Odoo: {ODOO_URL}...")
    common = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/common')
    uid = common.authenticate(ODOO_DB, ODOO_USERNAME, ODOO_PASSWORD, {})
    
    if not uid:
        raise Exception("❌ Échec d'authentification Odoo")
    
    print(f"✅ Connecté (UID: {uid})")
    
    models = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/object')
    
    # Récupérer les employés
    print("📋 Récupération des employés...")
    employee_ids = models.execute_kw(
        ODOO_DB, uid, ODOO_PASSWORD,
        'hr.employee', 'search',
        [[]]
    )
    
    print(f"   → {len(employee_ids)} employés trouvés")
    
    if len(employee_ids) == 0:
        print("⚠️  Aucun employé dans Odoo!")
        print("   Créez des employés dans Odoo d'abord:")
        print("   http://localhost:8069 → Menu Employees → Create")
        return []
    
    employees = models.execute_kw(
        ODOO_DB, uid, ODOO_PASSWORD,
        'hr.employee', 'read',
        [employee_ids],
        {'fields': ['id', 'name', 'work_email', 'department_id', 'job_title', 'active']}
    )
    
    return employees

# ============================================================================
# ÉTAPE 2: NETTOYER ET ÉCRIRE CSV
# ============================================================================
def write_to_csv(employees):
    """Écrire les employés dans hr_raw.csv (format propre)"""
    print("\n" + "="*70)
    print("📝 ÉTAPE 2: Nettoyage et écriture CSV")
    print("="*70)
    
    print(f"💾 Écriture dans: {CSV_OUTPUT}")
    
    with open(CSV_OUTPUT, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = [
            'personalNumber', 'givenName', 'familyName', 'email', 
            'department', 'title', 'manager', 'status', 'hireDate', 'location'
        ]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        
        for emp in employees:
            # Split name
            name_parts = emp['name'].split(' ', 1)
            given_name = name_parts[0] if name_parts else 'Unknown'
            family_name = name_parts[1] if len(name_parts) > 1 else 'Unknown'
            
            # Department
            department = emp['department_id'][1] if emp['department_id'] else 'Unassigned'
            
            # Generate email if missing
            email = emp['work_email']
            if not email:
                email = f"{given_name.lower()}.{family_name.lower()}@example.com"
            
            row = {
                'personalNumber': str(1000 + emp['id']),
                'givenName': given_name,
                'familyName': family_name,
                'email': email,
                'department': department,
                'title': emp['job_title'] or 'Employee',
                'manager': '',  # Odoo ne fournit pas facilement le manager
                'status': 'Active' if emp['active'] else 'Suspended',
                'hireDate': '',
                'location': ''
            }
            
            writer.writerow(row)
            print(f"   ✓ {emp['name']} → {row['personalNumber']}")
    
    print(f"\n✅ {len(employees)} employés écrits dans {CSV_OUTPUT}")
    return len(employees)

# ============================================================================
# ÉTAPE 3: IMPORT DANS MIDPOINT
# ============================================================================
def import_to_midpoint(num_employees):
    """Importer les employés dans MidPoint"""
    print("\n" + "="*70)
    print("📤 ÉTAPE 3: Import dans MidPoint")
    print("="*70)
    
    print(f"🔗 Connexion à MidPoint: {MIDPOINT_URL}...")
    
    # Test connexion
    try:
        response = requests.get(
            f"{MIDPOINT_URL}/ws/rest/users",
            auth=HTTPBasicAuth(MIDPOINT_USER, MIDPOINT_PASS),
            headers={"Accept": "application/json"},
            timeout=5
        )
        if response.status_code == 200:
            print("✅ Connexion MidPoint OK")
        else:
            raise Exception(f"Status code: {response.status_code}")
    except Exception as e:
        print(f"❌ Échec connexion MidPoint: {e}")
        return
    
    # Lire le CSV
    print(f"📂 Lecture de {CSV_OUTPUT}...")
    with open(CSV_OUTPUT, 'r', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        employees = list(reader)
    
    print(f"   → {len(employees)} employés à importer")
    
    # Importer chaque employé
    created = 0
    updated = 0
    errors = 0
    
    for emp in employees:
        personal_number = emp['personalNumber']
        full_name = f"{emp['givenName']} {emp['familyName']}"
        
        print(f"\n📋 Traitement: {full_name} ({personal_number})")
        
        # Vérifier si l'utilisateur existe
        search_response = requests.get(
            f"{MIDPOINT_URL}/ws/rest/users",
            auth=HTTPBasicAuth(MIDPOINT_USER, MIDPOINT_PASS),
            headers={"Accept": "application/json"},
            params={"query": f"name = '{personal_number}'"},
            timeout=10
        )
        
        user_exists = False
        if search_response.status_code == 200:
            result = search_response.json()
            if result.get('totalCount', 0) > 0:
                user_exists = True
                print(f"   ℹ️  Utilisateur existe déjà")
        
        # Créer l'utilisateur MidPoint
        user_data = {
            "user": {
                "@xmlns": "http://midpoint.evolveum.com/xml/ns/public/common/common-3",
                "name": personal_number,
                "givenName": emp['givenName'],
                "familyName": emp['familyName'],
                "emailAddress": emp['email'],
                "employeeNumber": personal_number,
                "organization": emp['department'],
                "organizationalUnit": emp['department'],
                "additionalName": emp['title'],
                "activation": {
                    "administrativeStatus": "enabled" if emp['status'] == 'Active' else "disabled"
                }
            }
        }
        
        if not user_exists:
            # Créer
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
                    print(f"   ✅ Créé")
                    created += 1
                    
                    # Recompute pour activer les rôles automatiques
                    user_oid = response.json().get('oid')
                    if user_oid:
                        recompute_response = requests.post(
                            f"{MIDPOINT_URL}/ws/rest/users/{user_oid}/recompute",
                            auth=HTTPBasicAuth(MIDPOINT_USER, MIDPOINT_PASS),
                            timeout=30
                        )
                        if recompute_response.status_code == 204:
                            print(f"   🔄 Rôles auto-assignés")
                else:
                    print(f"   ❌ Erreur création: {response.status_code}")
                    print(f"      {response.text[:200]}")
                    errors += 1
            except Exception as e:
                print(f"   ❌ Exception: {e}")
                errors += 1
        else:
            print(f"   ⏭️  Ignoré (existe déjà)")
            updated += 1
    
    # Résumé
    print("\n" + "="*70)
    print("📊 RÉSUMÉ")
    print("="*70)
    print(f"   Total: {len(employees)}")
    print(f"   ✨ Créés: {created}")
    print(f"   ♻️  Existants: {updated}")
    print(f"   ❌ Erreurs: {errors}")
    print("="*70)

# ============================================================================
# MAIN
# ============================================================================
def main():
    print("\n" + "="*70)
    print("🚀 IMPORT COMPLET : ODOO → CSV → MIDPOINT")
    print("="*70)
    
    try:
        # Étape 1: Export Odoo
        employees = export_from_odoo()
        
        if len(employees) == 0:
            print("\n❌ Aucun employé à traiter. Arrêt.")
            return
        
        # Étape 2: Clean CSV
        num_employees = write_to_csv(employees)
        
        # Étape 3: Import MidPoint
        import_to_midpoint(num_employees)
        
        print("\n✅ Import complet terminé!")
        
    except Exception as e:
        print(f"\n❌ ERREUR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()
