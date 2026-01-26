#!/usr/bin/env python3
"""
=============================================================================
LIVESYNC - Import CSV Odoo → Provisioning IGA
=============================================================================

Ce script importe un fichier CSV exporté manuellement depuis Odoo (hr.employee)
et le synchronise vers tous les systèmes cibles.

Flux : CSV Odoo Export → Nettoyage → hr_clean.csv → Provisioning (LDAP, PostgreSQL)

Usage:
    python3 livesync_odoo_csv.py "Employee (hr.employee).csv"
    python3 livesync_odoo_csv.py input.csv --output hr_clean.csv
    python3 livesync_odoo_csv.py input.csv --provision  # Avec provisioning auto

Auteur: Projet IGA - BUT3 Informatique
=============================================================================
"""

import argparse
import csv
import os
import sys
import re
from datetime import datetime
from typing import Dict, List, Optional

# Configuration
DEFAULT_OUTPUT = '/root/iam-iga-tp/data/hr/hr_clean.csv'
SCRIPTS_DIR = '/root/iam-iga-tp/scripts'


# =============================================================================
# UTILITAIRES
# =============================================================================

class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    BOLD = '\033[1m'
    END = '\033[0m'


def print_banner():
    print(f"""
{Colors.CYAN}╔══════════════════════════════════════════════════════════════════════════════╗
║  {Colors.BOLD}🔄 LIVESYNC - Import CSV Odoo → IGA{Colors.END}{Colors.CYAN}                                        ║
║  Nettoyage et provisioning automatique depuis export Odoo                     ║
╚══════════════════════════════════════════════════════════════════════════════╝{Colors.END}
""")


def print_success(msg): print(f"  {Colors.GREEN}✓{Colors.END} {msg}")
def print_error(msg): print(f"  {Colors.RED}✗{Colors.END} {msg}")
def print_warning(msg): print(f"  {Colors.YELLOW}⚠{Colors.END} {msg}")
def print_info(msg): print(f"  {Colors.BLUE}ℹ{Colors.END} {msg}")


def clean_name(name: str) -> tuple:
    """Sépare un nom complet en prénom et nom de famille"""
    if not name or not name.strip():
        return '', ''
    
    parts = name.strip().split(' ', 1)
    first_name = parts[0].strip()
    last_name = parts[1].strip() if len(parts) > 1 else ''
    
    return first_name, last_name


def clean_email(email: str, first_name: str, last_name: str) -> str:
    """Nettoie l'email ou en génère un par défaut"""
    if email and '@' in email and email != 'False':
        return email.strip()
    
    # Générer un email par défaut
    login = f"{first_name.lower()}.{last_name.lower()}"
    login = re.sub(r'[^a-z0-9.]', '', login)
    return f"{login}@example.com"


def clean_department(dept: str) -> str:
    """Nettoie le nom du département"""
    if not dept:
        return ''
    
    # Prendre le dernier niveau si c'est une hiérarchie
    # Ex: "Management / Sales" → "Sales"
    parts = dept.split('/')
    return parts[-1].strip()


def generate_employee_number(index: int, existing_numbers: set) -> str:
    """Génère un numéro d'employé unique"""
    base = 1001 + index
    while str(base) in existing_numbers:
        base += 1
    return str(base)


# =============================================================================
# IMPORT ET NETTOYAGE
# =============================================================================

def import_odoo_csv(input_path: str) -> List[Dict]:
    """Importe et nettoie le CSV exporté depuis Odoo"""
    
    employees = []
    existing_numbers = set()
    seen_emails = set()
    
    print_info(f"Lecture du fichier: {input_path}")
    
    if not os.path.exists(input_path):
        print_error(f"Fichier non trouvé: {input_path}")
        return employees
    
    with open(input_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        
        for i, row in enumerate(reader):
            # Récupérer le nom de l'employé
            name = row.get('Employee Name', row.get('name', '')).strip()
            
            # Ignorer les lignes vides ou les sous-lignes de contrats
            if not name:
                continue
            
            first_name, last_name = clean_name(name)
            
            if not first_name:
                continue
            
            # Email
            email = clean_email(
                row.get('Work Email', row.get('email', '')),
                first_name,
                last_name
            )
            
            # Éviter les doublons d'email
            if email in seen_emails:
                print_warning(f"Email dupliqué ignoré: {email} ({name})")
                continue
            seen_emails.add(email)
            
            # Département
            department = clean_department(row.get('Department', row.get('department', '')))
            
            # Titre/Poste
            title = row.get('Job Position', row.get('job_title', row.get('title', ''))).strip()
            
            # Numéro d'employé
            emp_number = generate_employee_number(i, existing_numbers)
            existing_numbers.add(emp_number)
            
            # Statut (par défaut Active)
            status = 'Active'
            
            employee = {
                'personalNumber': emp_number,
                'givenName': first_name,
                'familyName': last_name,
                'email': email,
                'department': department,
                'title': title,
                'status': status
            }
            
            employees.append(employee)
    
    print_success(f"{len(employees)} employés importés")
    return employees


def export_clean_csv(employees: List[Dict], output_path: str) -> bool:
    """Exporte les employés nettoyés vers hr_clean.csv"""
    
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
        
        print_success(f"CSV nettoyé exporté: {output_path}")
        return True
        
    except Exception as e:
        print_error(f"Erreur d'écriture: {e}")
        return False


def run_provisioning():
    """Lance le script de provisioning"""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'═' * 60}{Colors.END}")
    print(f"{Colors.BOLD}  🚀 PROVISIONING AUTOMATIQUE{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'═' * 60}{Colors.END}\n")
    
    provisioning_script = os.path.join(SCRIPTS_DIR, 'demo_provisioning.py')
    
    if os.path.exists(provisioning_script):
        os.system(f"python3 {provisioning_script} --verify")
    else:
        print_warning("Script de provisioning non trouvé")
        print_info("Exécutez manuellement: python3 scripts/demo_provisioning.py")


# =============================================================================
# MAIN
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description='LiveSync - Import CSV Odoo vers IGA',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemples:
  python3 livesync_odoo_csv.py "Employee (hr.employee).csv"
  python3 livesync_odoo_csv.py input.csv --provision
  python3 livesync_odoo_csv.py input.csv -o /path/to/output.csv
        """
    )
    parser.add_argument('input', help='Fichier CSV exporté depuis Odoo')
    parser.add_argument('-o', '--output', default=DEFAULT_OUTPUT,
                       help=f'Fichier de sortie (défaut: {DEFAULT_OUTPUT})')
    parser.add_argument('--provision', '-p', action='store_true',
                       help='Lancer le provisioning après import')
    parser.add_argument('--dry-run', action='store_true',
                       help='Afficher sans modifier')
    
    args = parser.parse_args()
    
    print_banner()
    
    print(f"{Colors.BOLD}{Colors.BLUE}{'═' * 60}{Colors.END}")
    print(f"{Colors.BOLD}  📥 IMPORT ET NETTOYAGE{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'═' * 60}{Colors.END}\n")
    
    print_info(f"Fichier source : {args.input}")
    print_info(f"Fichier sortie : {args.output}")
    print_info(f"Date/Heure     : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Import et nettoyage
    employees = import_odoo_csv(args.input)
    
    if not employees:
        print_error("Aucun employé valide trouvé")
        sys.exit(1)
    
    # Afficher les employés
    print(f"\n  {'─' * 50}")
    print(f"  {'Prénom':<15} {'Nom':<15} {'Département':<20} {'Poste'}")
    print(f"  {'─' * 50}")
    
    for emp in employees[:15]:
        print(f"  {emp['givenName']:<15} {emp['familyName']:<15} {emp['department']:<20} {emp['title'][:25]}")
    
    if len(employees) > 15:
        print(f"  ... et {len(employees) - 15} autres")
    
    print(f"  {'─' * 50}")
    print(f"  {Colors.BOLD}Total: {len(employees)} employés{Colors.END}")
    print()
    
    # Statistiques par département
    depts = {}
    for emp in employees:
        dept = emp['department'] or 'Non défini'
        depts[dept] = depts.get(dept, 0) + 1
    
    print("  Répartition par département:")
    for dept, count in sorted(depts.items(), key=lambda x: -x[1]):
        print(f"    • {dept}: {count}")
    print()
    
    if args.dry_run:
        print_warning("Mode dry-run: aucune modification")
        return
    
    # Export
    if export_clean_csv(employees, args.output):
        print_success("Import terminé avec succès!")
    else:
        sys.exit(1)
    
    # Provisioning si demandé
    if args.provision:
        run_provisioning()
    else:
        print(f"""
{Colors.CYAN}📌 Prochaines étapes:{Colors.END}
   • Lancer le provisioning: python3 scripts/demo_provisioning.py --verify
   • Ou avec livesync:       python3 scripts/livesync_odoo_csv.py input.csv --provision
""")


if __name__ == '__main__':
    main()






