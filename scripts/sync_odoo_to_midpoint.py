#!/usr/bin/env python3
"""
=============================================================================
SYNCHRONISATION ODOO → MIDPOINT
=============================================================================

Ce script synchronise les employés d'Odoo vers MidPoint :
1. Exporte les employés d'Odoo (module HR) vers un fichier CSV
2. Déclenche l'import dans MidPoint via l'API REST
3. Vérifie le résultat de la synchronisation

Flux : Odoo (HR) → CSV → MidPoint → (LDAP, Intranet, HomeApp)

Usage:
    python3 sync_odoo_to_midpoint.py                # Sync complète
    python3 sync_odoo_to_midpoint.py --export-only  # Export CSV uniquement
    python3 sync_odoo_to_midpoint.py --import-only  # Import MidPoint uniquement
    python3 sync_odoo_to_midpoint.py --dry-run      # Simulation

Auteur: Projet IGA - BUT3 Informatique
=============================================================================
"""

import argparse
import csv
import json
import os
import sys
import time
import xmlrpc.client
from datetime import datetime
from typing import Dict, List, Optional, Any

try:
    import requests
except ImportError:
    print("Installation de requests...")
    os.system("pip3 install requests -q")
    import requests

# =============================================================================
# CONFIGURATION
# =============================================================================

# Odoo
ODOO_URL = os.getenv('ODOO_URL', 'http://localhost:8069')
ODOO_DB = os.getenv('ODOO_DB', 'odoo')
ODOO_USER = os.getenv('ODOO_USER', 'admin')
ODOO_PASSWORD = os.getenv('ODOO_PASSWORD', 'admin')

# MidPoint
MIDPOINT_URL = os.getenv('MIDPOINT_URL', 'http://localhost:8080/midpoint')
MIDPOINT_USER = os.getenv('MIDPOINT_USER', 'administrator')
MIDPOINT_PASSWORD = os.getenv('MIDPOINT_PASSWORD', '5ecr3t')

# Fichier CSV intermédiaire
CSV_PATH = os.getenv('HR_CSV_PATH', '/root/iam-iga-tp/data/hr/hr_clean.csv')


# =============================================================================
# UTILITAIRES D'AFFICHAGE
# =============================================================================

class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    END = '\033[0m'


def print_banner():
    print(f"""
{Colors.CYAN}╔══════════════════════════════════════════════════════════════════════════════╗
║                                                                                ║
║  {Colors.BOLD}🔄 SYNCHRONISATION ODOO → MIDPOINT{Colors.END}{Colors.CYAN}                                         ║
║                                                                                ║
║  Flux : Odoo (HR) → CSV → MidPoint → (LDAP, Intranet, HomeApp)               ║
║                                                                                ║
╚══════════════════════════════════════════════════════════════════════════════╝{Colors.END}
""")


def print_header(title: str, icon: str = "📋"):
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'═' * 70}{Colors.END}")
    print(f"{Colors.BOLD}  {icon} {title}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'═' * 70}{Colors.END}\n")


def print_success(msg: str):
    print(f"  {Colors.GREEN}✓{Colors.END} {msg}")


def print_error(msg: str):
    print(f"  {Colors.RED}✗{Colors.END} {msg}")


def print_warning(msg: str):
    print(f"  {Colors.YELLOW}⚠{Colors.END} {msg}")


def print_info(msg: str):
    print(f"  {Colors.BLUE}ℹ{Colors.END} {msg}")


# =============================================================================
# EXPORT ODOO → CSV
# =============================================================================

class OdooExporter:
    """Exporte les employés d'Odoo vers CSV"""
    
    def __init__(self, url: str, db: str, username: str, password: str):
        self.url = url
        self.db = db
        self.username = username
        self.password = password
        self.uid = None
        self.models = None
    
    def connect(self) -> bool:
        """Connexion à Odoo"""
        try:
            common = xmlrpc.client.ServerProxy(f'{self.url}/xmlrpc/2/common')
            version = common.version()
            print_info(f"Odoo version: {version.get('server_version', 'unknown')}")
            
            self.uid = common.authenticate(self.db, self.username, self.password, {})
            if not self.uid:
                print_error("Échec de l'authentification Odoo")
                return False
            
            self.models = xmlrpc.client.ServerProxy(f'{self.url}/xmlrpc/2/object')
            print_success(f"Connecté à Odoo (UID: {self.uid})")
            return True
            
        except Exception as e:
            print_error(f"Erreur de connexion Odoo: {e}")
            return False
    
    def get_employees(self) -> List[Dict]:
        """Récupère les employés depuis Odoo"""
        employees = []
        
        # Vérifier si le module HR est installé
        hr_installed = self.models.execute_kw(
            self.db, self.uid, self.password,
            'ir.module.module', 'search_count',
            [[('name', '=', 'hr'), ('state', '=', 'installed')]]
        )
        
        if hr_installed:
            print_info("Module HR détecté, extraction depuis hr.employee...")
            
            emp_ids = self.models.execute_kw(
                self.db, self.uid, self.password,
                'hr.employee', 'search', [[('active', '=', True)]]
            )
            
            if emp_ids:
                emp_data = self.models.execute_kw(
                    self.db, self.uid, self.password,
                    'hr.employee', 'read', [emp_ids],
                    {'fields': ['name', 'work_email', 'department_id', 'job_title', 
                               'identification_id', 'active', 'parent_id']}
                )
                
                for emp in emp_data:
                    # Séparer prénom et nom
                    name_parts = emp['name'].split(' ', 1)
                    first_name = name_parts[0]
                    last_name = name_parts[1] if len(name_parts) > 1 else ''
                    
                    # Nettoyer l'email
                    email = emp.get('work_email')
                    if not email or email == 'False':
                        email = f"{first_name.lower()}.{last_name.lower()}@example.com"
                        email = email.replace(' ', '')
                    
                    employees.append({
                        'personalNumber': emp.get('identification_id') or str(emp['id'] + 1000),
                        'givenName': first_name,
                        'familyName': last_name,
                        'email': email,
                        'department': emp['department_id'][1] if emp.get('department_id') else '',
                        'title': emp.get('job_title') or '',
                        'status': 'Active' if emp.get('active', True) else 'Suspended'
                    })
                
                print_success(f"{len(employees)} employés extraits depuis hr.employee")
        
        else:
            print_warning("Module HR non installé, extraction depuis res.users...")
            
            user_ids = self.models.execute_kw(
                self.db, self.uid, self.password,
                'res.users', 'search',
                [[('login', 'not in', ['admin', 'portal', 'public', 'demo']), ('active', '=', True)]]
            )
            
            if user_ids:
                user_data = self.models.execute_kw(
                    self.db, self.uid, self.password,
                    'res.users', 'read', [user_ids],
                    {'fields': ['login', 'name', 'email', 'active']}
                )
                
                for i, user in enumerate(user_data):
                    login = user['login']
                    if '.' in login:
                        parts = login.split('.', 1)
                        first_name = parts[0].capitalize()
                        last_name = parts[1].capitalize()
                    else:
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
                
                print_success(f"{len(employees)} utilisateurs extraits depuis res.users")
        
        return employees
    
    def export_to_csv(self, employees: List[Dict], output_path: str) -> bool:
        """Exporte vers CSV"""
        if not employees:
            print_error("Aucun employé à exporter")
            return False
        
        fieldnames = ['personalNumber', 'givenName', 'familyName', 'email', 
                      'department', 'title', 'status']
        
        try:
            with open(output_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(employees)
            
            print_success(f"CSV exporté: {output_path}")
            return True
            
        except Exception as e:
            print_error(f"Erreur d'écriture CSV: {e}")
            return False


# =============================================================================
# IMPORT MIDPOINT
# =============================================================================

class MidPointImporter:
    """Gère l'import dans MidPoint via API REST"""
    
    def __init__(self, url: str, username: str, password: str):
        self.base_url = url
        self.auth = (username, password)
        self.session = requests.Session()
        self.session.auth = self.auth
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })
    
    def test_connection(self) -> bool:
        """Teste la connexion à MidPoint"""
        try:
            response = self.session.get(f"{self.base_url}/ws/rest/self", timeout=10)
            if response.status_code == 200:
                print_success("Connecté à MidPoint")
                return True
            else:
                print_error(f"Erreur MidPoint: {response.status_code}")
                return False
        except Exception as e:
            print_error(f"Erreur de connexion MidPoint: {e}")
            return False
    
    def get_users(self) -> List[Dict]:
        """Liste les utilisateurs dans MidPoint"""
        try:
            response = self.session.get(
                f"{self.base_url}/ws/rest/users",
                params={'options': 'raw'},
                timeout=30
            )
            if response.status_code == 200:
                data = response.json()
                users = data.get('object', [])
                return users
            return []
        except Exception as e:
            print_error(f"Erreur lors de la récupération des utilisateurs: {e}")
            return []
    
    def get_user_count(self) -> int:
        """Compte les utilisateurs dans MidPoint"""
        users = self.get_users()
        return len(users)
    
    def trigger_reconciliation(self, resource_oid: str = None) -> bool:
        """Déclenche une réconciliation MidPoint"""
        print_info("Déclenchement de la réconciliation MidPoint...")
        
        # Pour une vraie réconciliation, il faudrait l'OID de la ressource CSV
        # Ici on peut utiliser l'API MidPoint pour lancer une tâche
        
        print_warning("La réconciliation automatique nécessite la configuration MidPoint")
        print_info("Utilisez l'interface MidPoint pour lancer la tâche 'HR CSV Import Task'")
        return True
    
    def create_user(self, user_data: Dict) -> Optional[str]:
        """Crée un utilisateur dans MidPoint via API REST"""
        
        # Construire l'objet UserType pour MidPoint
        user_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<user xmlns="http://midpoint.evolveum.com/xml/ns/public/common/common-3">
    <name>{user_data['login']}</name>
    <givenName>{user_data['first_name']}</givenName>
    <familyName>{user_data['last_name']}</familyName>
    <fullName>{user_data['full_name']}</fullName>
    <emailAddress>{user_data['email']}</emailAddress>
    <employeeNumber>{user_data.get('employee_number', '')}</employeeNumber>
    <organization>{user_data.get('department', '')}</organization>
    <title>{user_data.get('title', '')}</title>
</user>"""
        
        try:
            response = self.session.post(
                f"{self.base_url}/ws/rest/users",
                data=user_xml,
                headers={'Content-Type': 'application/xml'},
                timeout=30
            )
            
            if response.status_code in [200, 201]:
                print_success(f"Utilisateur créé dans MidPoint: {user_data['login']}")
                return response.headers.get('Location', '')
            elif response.status_code == 409:
                print_warning(f"Utilisateur existe déjà: {user_data['login']}")
                return 'exists'
            else:
                print_error(f"Erreur création MidPoint: {response.status_code} - {response.text[:200]}")
                return None
                
        except Exception as e:
            print_error(f"Erreur: {e}")
            return None


# =============================================================================
# SYNCHRONISATION COMPLÈTE
# =============================================================================

def sync_odoo_to_midpoint(
    csv_path: str,
    export_only: bool = False,
    import_only: bool = False,
    dry_run: bool = False
) -> Dict[str, Any]:
    """Synchronisation complète Odoo → CSV → MidPoint"""
    
    results = {
        'odoo_employees': 0,
        'csv_exported': False,
        'midpoint_users_before': 0,
        'midpoint_users_after': 0,
        'created': 0,
        'errors': 0
    }
    
    # Étape 1: Export depuis Odoo
    if not import_only:
        print_header("ÉTAPE 1: EXPORT ODOO → CSV", "📤")
        
        exporter = OdooExporter(ODOO_URL, ODOO_DB, ODOO_USER, ODOO_PASSWORD)
        
        if not exporter.connect():
            return results
        
        employees = exporter.get_employees()
        results['odoo_employees'] = len(employees)
        
        if employees:
            print(f"\n  Employés trouvés dans Odoo:")
            for emp in employees[:10]:
                status = "✓" if emp['status'] == 'Active' else "✗"
                print(f"    {status} {emp['givenName']} {emp['familyName']} - {emp['department']} - {emp['title']}")
            if len(employees) > 10:
                print(f"    ... et {len(employees) - 10} autres")
        
        if dry_run:
            print_warning("\n[DRY-RUN] Export CSV simulé")
            results['csv_exported'] = True
        else:
            results['csv_exported'] = exporter.export_to_csv(employees, csv_path)
        
        if export_only:
            return results
    
    # Étape 2: Import dans MidPoint
    print_header("ÉTAPE 2: IMPORT CSV → MIDPOINT", "📥")
    
    importer = MidPointImporter(MIDPOINT_URL, MIDPOINT_USER, MIDPOINT_PASSWORD)
    
    if not importer.test_connection():
        print_error("Impossible de se connecter à MidPoint")
        print_info(f"Vérifiez que MidPoint est accessible sur {MIDPOINT_URL}")
        return results
    
    results['midpoint_users_before'] = importer.get_user_count()
    print_info(f"Utilisateurs MidPoint avant import: {results['midpoint_users_before']}")
    
    # Lire le CSV et importer dans MidPoint
    if os.path.exists(csv_path):
        print_info(f"Lecture du CSV: {csv_path}")
        
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            for row in reader:
                first_name = row.get('givenName', '')
                last_name = row.get('familyName', '')
                
                if not first_name or not last_name:
                    continue
                
                login = f"{first_name.lower()}.{last_name.lower()}".replace(' ', '')
                
                user_data = {
                    'login': login,
                    'first_name': first_name,
                    'last_name': last_name,
                    'full_name': f"{first_name} {last_name}",
                    'email': row.get('email', f"{login}@example.com"),
                    'employee_number': row.get('personalNumber', ''),
                    'department': row.get('department', ''),
                    'title': row.get('title', ''),
                }
                
                if dry_run:
                    print_info(f"[DRY-RUN] Créerait: {login}")
                    results['created'] += 1
                else:
                    result = importer.create_user(user_data)
                    if result:
                        if result != 'exists':
                            results['created'] += 1
                    else:
                        results['errors'] += 1
    
    if not dry_run:
        results['midpoint_users_after'] = importer.get_user_count()
        print_info(f"Utilisateurs MidPoint après import: {results['midpoint_users_after']}")
    
    return results


# =============================================================================
# MAIN
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description='Synchronisation Odoo → MidPoint',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemples:
  python3 sync_odoo_to_midpoint.py                # Sync complète
  python3 sync_odoo_to_midpoint.py --export-only  # Export CSV uniquement
  python3 sync_odoo_to_midpoint.py --import-only  # Import MidPoint uniquement
  python3 sync_odoo_to_midpoint.py --dry-run      # Simulation
        """
    )
    parser.add_argument('--csv', default=CSV_PATH, help='Chemin du fichier CSV')
    parser.add_argument('--export-only', action='store_true', help='Export CSV uniquement')
    parser.add_argument('--import-only', action='store_true', help='Import MidPoint uniquement')
    parser.add_argument('--dry-run', action='store_true', help='Mode simulation')
    
    args = parser.parse_args()
    
    print_banner()
    
    print_header("CONFIGURATION", "⚙️")
    print_info(f"Odoo URL     : {ODOO_URL}")
    print_info(f"MidPoint URL : {MIDPOINT_URL}")
    print_info(f"CSV Path     : {args.csv}")
    print_info(f"Date/Heure   : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    if args.dry_run:
        print_warning("\n⚠️  MODE SIMULATION - Aucune modification\n")
    
    # Lancer la synchronisation
    results = sync_odoo_to_midpoint(
        csv_path=args.csv,
        export_only=args.export_only,
        import_only=args.import_only,
        dry_run=args.dry_run
    )
    
    # Résumé
    print_header("RÉSUMÉ DE LA SYNCHRONISATION", "📊")
    print(f"  {'─' * 40}")
    print(f"  Employés Odoo       : {results['odoo_employees']}")
    print(f"  CSV exporté         : {'✓' if results['csv_exported'] else '✗'}")
    print(f"  MidPoint (avant)    : {results['midpoint_users_before']}")
    print(f"  MidPoint (après)    : {results['midpoint_users_after']}")
    print(f"  Créés               : {results['created']}")
    print(f"  Erreurs             : {results['errors']}")
    print(f"  {'─' * 40}")
    
    if results['errors'] == 0 and (results['csv_exported'] or results['created'] > 0):
        print(f"\n{Colors.GREEN}{Colors.BOLD}✅ Synchronisation terminée avec succès!{Colors.END}")
    else:
        print(f"\n{Colors.YELLOW}{Colors.BOLD}⚠️  Synchronisation terminée avec des avertissements{Colors.END}")
    
    print(f"""
{Colors.CYAN}📌 Prochaines étapes:{Colors.END}
   1. Ouvrir MidPoint: {MIDPOINT_URL}
   2. Aller dans Users → All users
   3. Vérifier les utilisateurs importés
   4. Lancer la tâche 'HR CSV Import Task' si nécessaire
""")


if __name__ == '__main__':
    main()

