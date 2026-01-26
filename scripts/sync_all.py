#!/usr/bin/env python3
"""
Script de synchronisation globale
Provisionne tous les utilisateurs vers les systèmes cibles :
- Odoo ERP
- Application Intranet (PostgreSQL)
- Export vers LDAP (via MidPoint)

Ce script lit le fichier hr_clean.csv et provisionne vers toutes les cibles.

Usage:
    python3 sync_all.py
    python3 sync_all.py --target odoo
    python3 sync_all.py --target intranet
    python3 sync_all.py --target all
"""

import argparse
import csv
import os
import sys
import time

# Ajouter le répertoire scripts au path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import des modules de provisionnement
try:
    from provision_odoo import OdooProvisioner
except ImportError:
    OdooProvisioner = None

try:
    from provision_intranet import IntranetProvisioner
except ImportError:
    IntranetProvisioner = None

# Configuration
HR_CSV_PATH = os.getenv('HR_CSV_PATH', '/root/iam-iga-tp/data/hr/hr_clean.csv')

# Configuration Odoo
ODOO_URL = os.getenv('ODOO_URL', 'http://localhost:8069')
ODOO_DB = os.getenv('ODOO_DB', 'odoo')
ODOO_USER = os.getenv('ODOO_USER', 'admin')
ODOO_PASSWORD = os.getenv('ODOO_PASSWORD', 'admin')

# Configuration Intranet PostgreSQL
INTRANET_DB_HOST = os.getenv('INTRANET_DB_HOST', 'localhost')
INTRANET_DB_PORT = os.getenv('INTRANET_DB_PORT', '5433')
INTRANET_DB_NAME = os.getenv('INTRANET_DB_NAME', 'intranet')
INTRANET_DB_USER = os.getenv('INTRANET_DB_USER', 'intranet')
INTRANET_DB_PASS = os.getenv('INTRANET_DB_PASS', 'intranet123')


def print_header(title: str):
    """Affiche un en-tête formaté"""
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}\n")


def print_section(title: str):
    """Affiche une section"""
    print(f"\n{'─'*50}")
    print(f"  {title}")
    print(f"{'─'*50}\n")


def read_hr_data(csv_path: str) -> list:
    """Lit les données RH depuis le fichier CSV"""
    users = []
    
    if not os.path.exists(csv_path):
        print(f"✗ Fichier non trouvé: {csv_path}")
        return users
    
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            first_name = row.get('givenName', row.get('first_name', ''))
            last_name = row.get('familyName', row.get('last_name', ''))
            
            if not first_name or not last_name:
                continue
            
            # Nettoyer le username
            username = f"{first_name.lower()}.{last_name.lower()}"
            username = ''.join(c for c in username if c.isalnum() or c == '.')
            
            user = {
                'username': username,
                'email': row.get('email', f"{username}@example.com"),
                'first_name': first_name,
                'last_name': last_name,
                'full_name': f"{first_name} {last_name}",
                'department': row.get('department', ''),
                'title': row.get('title', ''),
                'employee_number': row.get('personalNumber', ''),
                'status': row.get('status', 'Active'),
                'enabled': row.get('status', 'Active').lower() == 'active'
            }
            
            # Déterminer les rôles
            roles = ['USER']
            dept = user['department'].lower()
            title = user['title'].lower()
            
            if 'commercial' in dept:
                roles.append('AGENT_COMMERCIAL')
            elif 'rh' in dept or 'ressources' in dept:
                roles.append('RH_MANAGER')
            elif 'informatique' in dept or 'it' in dept:
                roles.append('IT_ADMIN')
            elif 'comptabilité' in dept or 'compta' in dept:
                roles.append('COMPTABLE')
            
            if 'responsable' in title or 'manager' in title or 'chef' in title:
                roles.append('MANAGER')
            
            user['roles'] = roles
            users.append(user)
    
    return users


def sync_to_odoo(users: list, url: str, db: str, username: str, password: str) -> dict:
    """Synchronise les utilisateurs vers Odoo"""
    stats = {'success': 0, 'errors': 0, 'skipped': 0}
    
    if OdooProvisioner is None:
        print("  ✗ Module provision_odoo non disponible")
        return stats
    
    provisioner = OdooProvisioner(url, db, username, password)
    
    if not provisioner.connect():
        print("  ✗ Impossible de se connecter à Odoo")
        stats['errors'] = len(users)
        return stats
    
    for user in users:
        try:
            result = provisioner.create_user(
                login=user['username'],
                name=user['full_name'],
                email=user['email']
            )
            
            if result:
                # Désactiver si nécessaire
                if not user['enabled']:
                    provisioner.update_user(user['username'], active=False)
                stats['success'] += 1
            else:
                stats['errors'] += 1
                
        except Exception as e:
            print(f"  ✗ Erreur pour {user['username']}: {e}")
            stats['errors'] += 1
    
    return stats


def sync_to_intranet(users: list, host: str, port: str, dbname: str, 
                     db_user: str, db_pass: str) -> dict:
    """Synchronise les utilisateurs vers l'Intranet PostgreSQL"""
    stats = {'success': 0, 'errors': 0, 'skipped': 0}
    
    if IntranetProvisioner is None:
        print("  ✗ Module provision_intranet non disponible")
        return stats
    
    provisioner = IntranetProvisioner(host, port, dbname, db_user, db_pass)
    
    if not provisioner.connect():
        print("  ✗ Impossible de se connecter à PostgreSQL")
        stats['errors'] = len(users)
        return stats
    
    try:
        for user in users:
            try:
                result = provisioner.create_user(
                    username=user['username'],
                    email=user['email'],
                    first_name=user['first_name'],
                    last_name=user['last_name'],
                    department=user['department'],
                    title=user['title'],
                    employee_number=user['employee_number'],
                    enabled=user['enabled'],
                    roles=user['roles']
                )
                
                if result:
                    stats['success'] += 1
                else:
                    stats['errors'] += 1
                    
            except Exception as e:
                print(f"  ✗ Erreur pour {user['username']}: {e}")
                stats['errors'] += 1
    finally:
        provisioner.close()
    
    return stats


def main():
    parser = argparse.ArgumentParser(description='Synchronisation globale IGA')
    parser.add_argument('--target', default='all', 
                       choices=['all', 'odoo', 'intranet'],
                       help='Cible de synchronisation')
    parser.add_argument('--csv', default=HR_CSV_PATH, 
                       help='Chemin vers le fichier CSV RH')
    parser.add_argument('--dry-run', action='store_true',
                       help='Afficher les actions sans les exécuter')
    
    args = parser.parse_args()
    
    print_header("🔄 SYNCHRONISATION GLOBALE IGA")
    print(f"  Source CSV   : {args.csv}")
    print(f"  Cible        : {args.target}")
    print(f"  Mode dry-run : {'Oui' if args.dry_run else 'Non'}")
    
    # Lire les données RH
    print_section("📖 Lecture des données RH")
    users = read_hr_data(args.csv)
    
    if not users:
        print("✗ Aucun utilisateur trouvé dans le CSV")
        sys.exit(1)
    
    print(f"✓ {len(users)} utilisateurs lus depuis le CSV")
    
    # Statistiques par département
    depts = {}
    for user in users:
        dept = user['department'] or 'Non défini'
        depts[dept] = depts.get(dept, 0) + 1
    
    print("\n  Répartition par département:")
    for dept, count in sorted(depts.items()):
        print(f"    - {dept}: {count}")
    
    if args.dry_run:
        print("\n⚠️  Mode dry-run: aucune modification effectuée")
        print("\nUtilisateurs qui seraient provisionnés:")
        for user in users:
            status = "✓" if user['enabled'] else "✗"
            print(f"  {status} {user['username']:<25} {user['full_name']:<25} {user['department']}")
        return
    
    global_stats = {}
    
    # Synchronisation vers Odoo
    if args.target in ['all', 'odoo']:
        print_section("📦 Synchronisation vers Odoo ERP")
        try:
            stats = sync_to_odoo(users, ODOO_URL, ODOO_DB, ODOO_USER, ODOO_PASSWORD)
            global_stats['odoo'] = stats
            print(f"\n  Résultat: {stats['success']} réussis, {stats['errors']} erreurs")
        except Exception as e:
            print(f"  ✗ Erreur Odoo: {e}")
            global_stats['odoo'] = {'success': 0, 'errors': len(users)}
    
    # Synchronisation vers Intranet
    if args.target in ['all', 'intranet']:
        print_section("🏢 Synchronisation vers Intranet PostgreSQL")
        try:
            stats = sync_to_intranet(
                users, 
                INTRANET_DB_HOST, INTRANET_DB_PORT, 
                INTRANET_DB_NAME, INTRANET_DB_USER, INTRANET_DB_PASS
            )
            global_stats['intranet'] = stats
            print(f"\n  Résultat: {stats['success']} réussis, {stats['errors']} erreurs")
        except Exception as e:
            print(f"  ✗ Erreur Intranet: {e}")
            global_stats['intranet'] = {'success': 0, 'errors': len(users)}
    
    # Résumé final
    print_header("📊 RÉSUMÉ DE LA SYNCHRONISATION")
    
    total_success = 0
    total_errors = 0
    
    for target, stats in global_stats.items():
        print(f"  {target.upper():<15} : {stats['success']:>3} réussis, {stats['errors']:>3} erreurs")
        total_success += stats['success']
        total_errors += stats['errors']
    
    print(f"\n  {'TOTAL':<15} : {total_success:>3} réussis, {total_errors:>3} erreurs")
    
    if total_errors == 0:
        print("\n✅ Synchronisation terminée avec succès!")
    else:
        print(f"\n⚠️  Synchronisation terminée avec {total_errors} erreur(s)")
    
    print()


if __name__ == '__main__':
    main()








