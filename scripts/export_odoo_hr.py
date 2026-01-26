#!/usr/bin/env python3
"""
Export des données RH depuis Odoo vers CSV
Ce script extrait les employés du module RH d'Odoo et génère
le fichier hr_clean.csv utilisé par MidPoint.

Usage:
    python3 export_odoo_hr.py
    python3 export_odoo_hr.py --output /path/to/output.csv
"""

import argparse
import csv
import xmlrpc.client
import sys
import os

# Configuration Odoo
ODOO_URL = os.getenv('ODOO_URL', 'http://localhost:8069')
ODOO_DB = os.getenv('ODOO_DB', 'odoo')
ODOO_USER = os.getenv('ODOO_USER', 'admin')
ODOO_PASSWORD = os.getenv('ODOO_PASSWORD', 'admin')

# Chemin de sortie par défaut
DEFAULT_OUTPUT = '/root/iam-iga-tp/data/hr/hr_clean.csv'


def connect_odoo(url, db, username, password):
    """Connexion à Odoo via XML-RPC"""
    try:
        common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common')
        uid = common.authenticate(db, username, password, {})
        
        if not uid:
            print("✗ Échec de l'authentification Odoo")
            return None, None
        
        models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object')
        print(f"✓ Connecté à Odoo (UID: {uid})")
        return uid, models
    
    except Exception as e:
        print(f"✗ Erreur de connexion: {e}")
        return None, None


def get_employees_from_odoo(uid, models, db, password):
    """Récupère les employés depuis le module RH d'Odoo"""
    employees = []
    
    try:
        # Vérifier si le module hr est installé
        module_ids = models.execute_kw(
            db, uid, password,
            'ir.module.module', 'search',
            [[('name', '=', 'hr'), ('state', '=', 'installed')]]
        )
        
        if module_ids:
            print("✓ Module HR détecté, extraction des employés...")
            
            # Récupérer les employés depuis hr.employee
            emp_ids = models.execute_kw(
                db, uid, password,
                'hr.employee', 'search', [[]]
            )
            
            if emp_ids:
                emp_data = models.execute_kw(
                    db, uid, password,
                    'hr.employee', 'read', [emp_ids],
                    {'fields': ['name', 'work_email', 'department_id', 'job_title', 
                               'identification_id', 'active']}
                )
                
                for emp in emp_data:
                    # Séparer prénom et nom
                    name_parts = emp['name'].split(' ', 1)
                    first_name = name_parts[0]
                    last_name = name_parts[1] if len(name_parts) > 1 else ''
                    
                    employees.append({
                        'personalNumber': emp.get('identification_id') or str(emp['id'] + 1000),
                        'givenName': first_name,
                        'familyName': last_name,
                        'email': emp.get('work_email') or f"{first_name.lower()}.{last_name.lower()}@example.com",
                        'department': emp['department_id'][1] if emp.get('department_id') else '',
                        'title': emp.get('job_title') or '',
                        'status': 'Active' if emp.get('active', True) else 'Suspended'
                    })
                
                print(f"  → {len(employees)} employés trouvés dans hr.employee")
        
        # Si pas de module HR ou pas d'employés, utiliser res.users
        if not employees:
            print("ℹ️  Pas de module HR ou pas d'employés, extraction depuis res.users...")
            
            user_ids = models.execute_kw(
                db, uid, password,
                'res.users', 'search',
                [[('login', 'not in', ['admin', 'portal', 'public', 'demo'])]]
            )
            
            if user_ids:
                user_data = models.execute_kw(
                    db, uid, password,
                    'res.users', 'read', [user_ids],
                    {'fields': ['login', 'name', 'email', 'active']}
                )
                
                for i, user in enumerate(user_data):
                    # Utiliser le login Odoo pour générer prénom/nom (plus fiable)
                    login = user['login']
                    if '.' in login:
                        login_parts = login.split('.', 1)
                        first_name = login_parts[0].capitalize()
                        last_name = login_parts[1].capitalize()
                    else:
                        # Fallback sur le nom complet
                        name_parts = user['name'].split(' ', 1)
                        first_name = name_parts[0]
                        last_name = name_parts[1] if len(name_parts) > 1 else ''
                    
                    employees.append({
                        'personalNumber': str(1001 + i),
                        'givenName': first_name,
                        'familyName': last_name,
                        'email': user.get('email') or f"{login}@example.com",
                        'department': '',
                        'title': '',
                        'status': 'Active' if user.get('active', True) else 'Suspended'
                    })
                
                print(f"  → {len(employees)} utilisateurs trouvés dans res.users")
    
    except Exception as e:
        print(f"✗ Erreur lors de l'extraction: {e}")
    
    return employees


def export_to_csv(employees, output_path):
    """Exporte les employés vers un fichier CSV"""
    if not employees:
        print("✗ Aucun employé à exporter")
        return False
    
    fieldnames = ['personalNumber', 'givenName', 'familyName', 'email', 
                  'department', 'title', 'status']
    
    try:
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(employees)
        
        print(f"✓ Export réussi: {output_path}")
        print(f"  → {len(employees)} employés exportés")
        return True
    
    except Exception as e:
        print(f"✗ Erreur d'écriture: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description='Export RH Odoo vers CSV')
    parser.add_argument('--url', default=ODOO_URL, help='URL Odoo')
    parser.add_argument('--db', default=ODOO_DB, help='Base de données')
    parser.add_argument('--user', default=ODOO_USER, help='Utilisateur')
    parser.add_argument('--password', default=ODOO_PASSWORD, help='Mot de passe')
    parser.add_argument('--output', '-o', default=DEFAULT_OUTPUT, help='Fichier de sortie')
    
    args = parser.parse_args()
    
    print(f"\n{'='*60}")
    print(f"  Export RH Odoo → CSV")
    print(f"{'='*60}\n")
    
    # Connexion
    uid, models = connect_odoo(args.url, args.db, args.user, args.password)
    if not uid:
        sys.exit(1)
    
    # Extraction
    employees = get_employees_from_odoo(uid, models, args.db, args.password)
    
    # Export
    if export_to_csv(employees, args.output):
        print(f"\n✅ Export terminé!")
        print(f"\nProchaine étape:")
        print(f"  → Lancer l'import MidPoint pour synchroniser les identités")
    else:
        print(f"\n❌ Export échoué")
        sys.exit(1)
    
    print(f"\n{'='*60}\n")


if __name__ == '__main__':
    main()

