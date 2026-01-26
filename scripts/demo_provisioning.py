#!/usr/bin/env python3
"""
=============================================================================
DÉMO DE PROVISIONING IGA - Sans N8N
=============================================================================

Ce script démontre le provisioning d'identités depuis un fichier CSV RH
vers plusieurs systèmes cibles :
  1. PostgreSQL Intranet (app legacy)
  2. PostgreSQL HomeApp (nouvelle app)
  3. OpenLDAP (annuaire d'authentification)

Usage:
    python3 demo_provisioning.py                    # Provisioning complet
    python3 demo_provisioning.py --target intranet  # Uniquement vers Intranet
    python3 demo_provisioning.py --target homeapp   # Uniquement vers HomeApp
    python3 demo_provisioning.py --target ldap      # Uniquement vers LDAP
    python3 demo_provisioning.py --dry-run          # Simulation sans modification

Auteur: Projet IGA - BUT3 Informatique
=============================================================================
"""

import argparse
import csv
import os
import sys
import hashlib
import subprocess
from typing import Dict, List, Optional, Any
from datetime import datetime

# Configuration
HR_CSV_PATH = os.getenv('HR_CSV_PATH', '/root/iam-iga-tp/data/hr/hr_clean.csv')

# Configuration PostgreSQL Intranet
INTRANET_DB_HOST = os.getenv('INTRANET_DB_HOST', 'localhost')
INTRANET_DB_PORT = os.getenv('INTRANET_DB_PORT', '5433')
INTRANET_DB_NAME = os.getenv('INTRANET_DB_NAME', 'intranet')
INTRANET_DB_USER = os.getenv('INTRANET_DB_USER', 'intranet')
INTRANET_DB_PASS = os.getenv('INTRANET_DB_PASS', 'intranet123')

# Configuration PostgreSQL HomeApp
HOMEAPP_DB_HOST = os.getenv('HOMEAPP_DB_HOST', 'localhost')
HOMEAPP_DB_PORT = os.getenv('HOMEAPP_DB_PORT', '5434')
HOMEAPP_DB_NAME = os.getenv('HOMEAPP_DB_NAME', 'homeapp')
HOMEAPP_DB_USER = os.getenv('HOMEAPP_DB_USER', 'homeapp')
HOMEAPP_DB_PASS = os.getenv('HOMEAPP_DB_PASS', 'homeapp123')

# Configuration LDAP
LDAP_HOST = os.getenv('LDAP_HOST', 'localhost')
LDAP_PORT = os.getenv('LDAP_PORT', '10389')
LDAP_BASE_DN = os.getenv('LDAP_BASE_DN', 'dc=example,dc=com')
LDAP_ADMIN_DN = os.getenv('LDAP_ADMIN_DN', 'cn=admin,dc=example,dc=com')
LDAP_ADMIN_PASS = os.getenv('LDAP_ADMIN_PASS', 'admin')


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
    UNDERLINE = '\033[4m'
    END = '\033[0m'


def print_banner():
    print(f"""
{Colors.CYAN}╔══════════════════════════════════════════════════════════════════════════════╗
║                                                                                ║
║  {Colors.BOLD}🔐 DÉMO PROVISIONING IGA - Identity Governance & Administration{Colors.END}{Colors.CYAN}             ║
║                                                                                ║
║  Ce script démontre le provisioning automatique d'identités depuis            ║
║  un fichier CSV RH vers plusieurs systèmes cibles.                            ║
║                                                                                ║
╚══════════════════════════════════════════════════════════════════════════════╝{Colors.END}
""")


def print_header(title: str, icon: str = "📋"):
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'═' * 70}{Colors.END}")
    print(f"{Colors.BOLD}  {icon} {title}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'═' * 70}{Colors.END}\n")


def print_section(title: str, icon: str = "→"):
    print(f"\n{Colors.CYAN}{'─' * 50}{Colors.END}")
    print(f"{Colors.BOLD}  {icon} {title}{Colors.END}")
    print(f"{Colors.CYAN}{'─' * 50}{Colors.END}\n")


def print_success(msg: str):
    print(f"  {Colors.GREEN}✓{Colors.END} {msg}")


def print_error(msg: str):
    print(f"  {Colors.RED}✗{Colors.END} {msg}")


def print_warning(msg: str):
    print(f"  {Colors.YELLOW}⚠{Colors.END} {msg}")


def print_info(msg: str):
    print(f"  {Colors.BLUE}ℹ{Colors.END} {msg}")


def print_stats_table(stats: Dict[str, Dict[str, int]]):
    """Affiche un tableau de statistiques"""
    print(f"\n{'─' * 60}")
    print(f"  {'Cible':<20} {'Créés':<10} {'Mis à jour':<12} {'Erreurs':<10}")
    print(f"{'─' * 60}")
    
    total_created = 0
    total_updated = 0
    total_errors = 0
    
    for target, stat in stats.items():
        created = stat.get('created', 0)
        updated = stat.get('updated', 0)
        errors = stat.get('errors', 0)
        
        total_created += created
        total_updated += updated
        total_errors += errors
        
        status = Colors.GREEN + "✓" + Colors.END if errors == 0 else Colors.RED + "✗" + Colors.END
        print(f"  {status} {target:<18} {created:<10} {updated:<12} {errors:<10}")
    
    print(f"{'─' * 60}")
    print(f"  {'TOTAL':<20} {total_created:<10} {total_updated:<12} {total_errors:<10}")
    print(f"{'─' * 60}\n")


# =============================================================================
# LECTURE DES DONNÉES RH
# =============================================================================

def read_hr_data(csv_path: str) -> List[Dict]:
    """Lit les données RH depuis le fichier CSV et calcule les rôles"""
    users = []
    
    if not os.path.exists(csv_path):
        print_error(f"Fichier non trouvé: {csv_path}")
        return users
    
    print_info(f"Lecture du fichier: {csv_path}")
    
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        
        for row in reader:
            first_name = row.get('givenName', '').strip()
            last_name = row.get('familyName', '').strip()
            
            if not first_name or not last_name:
                continue
            
            # Générer le login
            login = f"{first_name.lower()}.{last_name.lower()}"
            # Nettoyer les caractères spéciaux
            login = ''.join(c for c in login if c.isalnum() or c == '.')
            
            department = row.get('department', '').strip()
            title = row.get('title', '').strip()
            status = row.get('status', 'Active').strip()
            
            # Déterminer les rôles en fonction du département et du titre
            roles = ['USER']  # Rôle par défaut
            
            dept_lower = department.lower()
            title_lower = title.lower()
            
            if 'commercial' in dept_lower:
                roles.append('AGENT_COMMERCIAL')
            elif 'rh' in dept_lower or 'ressources humaines' in dept_lower:
                roles.append('RH_ASSISTANT')
            elif 'informatique' in dept_lower or 'it' in dept_lower:
                roles.append('IT_SUPPORT')
            elif 'comptabilité' in dept_lower or 'compta' in dept_lower or 'finance' in dept_lower:
                roles.append('COMPTABLE')
            elif 'marketing' in dept_lower:
                roles.append('USER')  # Marketing garde le rôle USER de base
            
            # Rôles supplémentaires basés sur le titre
            if any(x in title_lower for x in ['responsable', 'manager', 'chef', 'directeur']):
                roles.append('MANAGER')
                if 'rh' in dept_lower or 'ressources humaines' in dept_lower:
                    roles.append('RH_MANAGER')
                elif 'commercial' in dept_lower:
                    roles.append('COMMERCIAL_MANAGER')
                elif 'informatique' in dept_lower:
                    roles.append('IT_ADMIN')
                elif 'comptabilité' in dept_lower or 'finance' in dept_lower:
                    roles.append('FINANCE_MANAGER')
            
            user = {
                'login': login,
                'email': row.get('email', f"{login}@example.com"),
                'first_name': first_name,
                'last_name': last_name,
                'full_name': f"{first_name} {last_name}",
                'department': department,
                'title': title,
                'employee_number': row.get('personalNumber', ''),
                'status': status,
                'is_active': status.lower() == 'active',
                'roles': list(set(roles))  # Dédupliquer
            }
            
            users.append(user)
    
    print_success(f"{len(users)} utilisateurs lus depuis le CSV")
    return users


# =============================================================================
# PROVISIONING POSTGRESQL (INTRANET & HOMEAPP)
# =============================================================================

def provision_to_postgresql(
    users: List[Dict],
    host: str,
    port: str,
    dbname: str,
    db_user: str,
    db_pass: str,
    target_name: str,
    dry_run: bool = False
) -> Dict[str, int]:
    """Provisionne les utilisateurs vers une base PostgreSQL"""
    
    stats = {'created': 0, 'updated': 0, 'errors': 0}
    
    try:
        import psycopg2
        import psycopg2.extras
    except ImportError:
        print_warning("Installation de psycopg2...")
        os.system("pip3 install psycopg2-binary -q")
        import psycopg2
        import psycopg2.extras
    
    print_info(f"Connexion à PostgreSQL {host}:{port}/{dbname}...")
    
    try:
        conn = psycopg2.connect(
            host=host,
            port=port,
            dbname=dbname,
            user=db_user,
            password=db_pass
        )
        conn.autocommit = True
        print_success(f"Connecté à {target_name}")
    except Exception as e:
        print_error(f"Erreur de connexion: {e}")
        stats['errors'] = len(users)
        return stats
    
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            for user in users:
                try:
                    if dry_run:
                        print_info(f"[DRY-RUN] Créerait: {user['login']}")
                        stats['created'] += 1
                        continue
                    
                    # Vérifier si l'utilisateur existe
                    if target_name == 'HomeApp':
                        cur.execute("SELECT id FROM users WHERE login = %s", (user['login'],))
                    else:
                        cur.execute("SELECT id FROM app_users WHERE username = %s", (user['login'],))
                    
                    existing = cur.fetchone()
                    
                    if target_name == 'HomeApp':
                        # Provisioning vers HomeApp
                        cur.execute("""
                            SELECT upsert_user(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """, (
                            user['login'],
                            user['email'],
                            None,  # password_hash
                            user['first_name'],
                            user['last_name'],
                            user['department'],
                            user['title'],
                            user['employee_number'],
                            user['is_active'],
                            None,  # midpoint_oid
                            '{}'   # attributes
                        ))
                        result = cur.fetchone()
                        user_id = result[0] if result else None
                        
                        # Assigner les rôles
                        for role in user['roles']:
                            try:
                                cur.execute("""
                                    SELECT assign_role_to_user(%s, %s, %s, %s, %s)
                                """, (user['login'], role, 'provisioning-script', 'abac', None))
                            except Exception:
                                pass  # Ignorer si le rôle n'existe pas
                    else:
                        # Provisioning vers Intranet
                        cur.execute("""
                            SELECT upsert_user(%s, %s, %s, %s, %s, %s, %s, %s)
                        """, (
                            user['login'],
                            user['email'],
                            user['first_name'],
                            user['last_name'],
                            user['department'],
                            user['title'],
                            user['employee_number'],
                            user['is_active']
                        ))
                        result = cur.fetchone()
                        user_id = result[0] if result else None
                        
                        # Assigner les rôles
                        for role in user['roles']:
                            try:
                                cur.execute("SELECT assign_role(%s, %s)", (user['login'], role))
                            except Exception:
                                pass  # Ignorer si le rôle n'existe pas
                    
                    if user_id:
                        if existing:
                            print_success(f"Mis à jour: {user['login']} ({user['full_name']}) - Rôles: {', '.join(user['roles'])}")
                            stats['updated'] += 1
                        else:
                            print_success(f"Créé: {user['login']} ({user['full_name']}) - Rôles: {', '.join(user['roles'])}")
                            stats['created'] += 1
                    else:
                        print_warning(f"Aucun ID retourné pour {user['login']}, mais peut exister")
                        stats['updated'] += 1
                        
                except Exception as e:
                    print_error(f"Erreur pour {user['login']}: {str(e)}")
                    stats['errors'] += 1
    finally:
        conn.close()
    
    return stats


# =============================================================================
# PROVISIONING LDAP
# =============================================================================

def provision_to_ldap(users: List[Dict], dry_run: bool = False) -> Dict[str, int]:
    """Provisionne les utilisateurs vers OpenLDAP"""
    
    stats = {'created': 0, 'updated': 0, 'errors': 0}
    
    print_info(f"Connexion à LDAP {LDAP_HOST}:{LDAP_PORT}...")
    
    # Vérifier la connectivité LDAP
    test_cmd = f"ldapsearch -x -H ldap://{LDAP_HOST}:{LDAP_PORT} -D '{LDAP_ADMIN_DN}' -w {LDAP_ADMIN_PASS} -b '{LDAP_BASE_DN}' '(objectClass=*)' dn 2>/dev/null | head -5"
    result = subprocess.run(test_cmd, shell=True, capture_output=True, text=True)
    
    if result.returncode != 0:
        print_error(f"Impossible de se connecter à LDAP: {result.stderr}")
        stats['errors'] = len(users)
        return stats
    
    print_success("Connecté à OpenLDAP")
    
    # Créer les OUs si nécessaire
    ous = ['users', 'groups']
    for ou in ous:
        ou_dn = f"ou={ou},{LDAP_BASE_DN}"
        check_cmd = f"ldapsearch -x -H ldap://{LDAP_HOST}:{LDAP_PORT} -D '{LDAP_ADMIN_DN}' -w {LDAP_ADMIN_PASS} -b '{ou_dn}' '(objectClass=organizationalUnit)' dn 2>/dev/null | grep -c 'dn:'"
        result = subprocess.run(check_cmd, shell=True, capture_output=True, text=True)
        
        if result.stdout.strip() == '0':
            print_info(f"Création de l'OU: {ou}")
            ldif = f"""dn: {ou_dn}
objectClass: organizationalUnit
ou: {ou}
"""
            if not dry_run:
                create_cmd = f"echo '{ldif}' | ldapadd -x -H ldap://{LDAP_HOST}:{LDAP_PORT} -D '{LDAP_ADMIN_DN}' -w {LDAP_ADMIN_PASS} 2>/dev/null"
                subprocess.run(create_cmd, shell=True)
    
    # Créer les groupes par département
    departments = set(u['department'] for u in users if u['department'])
    for dept in departments:
        group_cn = dept.lower().replace(' ', '-').replace('é', 'e')
        group_dn = f"cn={group_cn},ou=groups,{LDAP_BASE_DN}"
        
        check_cmd = f"ldapsearch -x -H ldap://{LDAP_HOST}:{LDAP_PORT} -D '{LDAP_ADMIN_DN}' -w {LDAP_ADMIN_PASS} -b '{group_dn}' '(objectClass=groupOfNames)' dn 2>/dev/null | grep -c 'dn:'"
        result = subprocess.run(check_cmd, shell=True, capture_output=True, text=True)
        
        if result.stdout.strip() == '0':
            print_info(f"Création du groupe: {group_cn}")
            # Créer le groupe avec un membre temporaire (admin)
            ldif = f"""dn: {group_dn}
objectClass: groupOfNames
cn: {group_cn}
description: Groupe {dept}
member: {LDAP_ADMIN_DN}
"""
            if not dry_run:
                create_cmd = f"echo '{ldif}' | ldapadd -x -H ldap://{LDAP_HOST}:{LDAP_PORT} -D '{LDAP_ADMIN_DN}' -w {LDAP_ADMIN_PASS} 2>/dev/null"
                subprocess.run(create_cmd, shell=True)
    
    # Provisionner les utilisateurs
    for user in users:
        try:
            user_dn = f"uid={user['login']},ou=users,{LDAP_BASE_DN}"
            
            # Vérifier si l'utilisateur existe
            check_cmd = f"ldapsearch -x -H ldap://{LDAP_HOST}:{LDAP_PORT} -D '{LDAP_ADMIN_DN}' -w {LDAP_ADMIN_PASS} -b '{user_dn}' '(objectClass=inetOrgPerson)' dn 2>/dev/null | grep -c 'dn:'"
            result = subprocess.run(check_cmd, shell=True, capture_output=True, text=True)
            exists = result.stdout.strip() != '0'
            
            if dry_run:
                action = "Mettrait à jour" if exists else "Créerait"
                print_info(f"[DRY-RUN] {action}: {user['login']}")
                if exists:
                    stats['updated'] += 1
                else:
                    stats['created'] += 1
                continue
            
            # Générer un mot de passe hashé (SSHA)
            password = f"{user['login']}123"  # Mot de passe par défaut pour la démo
            
            if exists:
                # Modifier l'utilisateur existant
                ldif = f"""dn: {user_dn}
changetype: modify
replace: cn
cn: {user['full_name']}
-
replace: sn
sn: {user['last_name']}
-
replace: givenName
givenName: {user['first_name']}
-
replace: mail
mail: {user['email']}
"""
                if user['department']:
                    ldif += f"""-
replace: departmentNumber
departmentNumber: {user['department']}
"""
                if user['title']:
                    ldif += f"""-
replace: title
title: {user['title']}
"""
                
                modify_cmd = f"echo '{ldif}' | ldapmodify -x -H ldap://{LDAP_HOST}:{LDAP_PORT} -D '{LDAP_ADMIN_DN}' -w {LDAP_ADMIN_PASS} 2>/dev/null"
                result = subprocess.run(modify_cmd, shell=True, capture_output=True, text=True)
                
                if result.returncode == 0:
                    print_success(f"Mis à jour: {user['login']} ({user['full_name']})")
                    stats['updated'] += 1
                else:
                    print_error(f"Erreur modification {user['login']}: {result.stderr}")
                    stats['errors'] += 1
            else:
                # Créer l'utilisateur
                ldif = f"""dn: {user_dn}
objectClass: inetOrgPerson
objectClass: organizationalPerson
objectClass: person
objectClass: top
uid: {user['login']}
cn: {user['full_name']}
sn: {user['last_name']}
givenName: {user['first_name']}
mail: {user['email']}
userPassword: {password}
"""
                if user['department']:
                    ldif += f"departmentNumber: {user['department']}\n"
                if user['title']:
                    ldif += f"title: {user['title']}\n"
                if user['employee_number']:
                    ldif += f"employeeNumber: {user['employee_number']}\n"
                
                create_cmd = f"echo '{ldif}' | ldapadd -x -H ldap://{LDAP_HOST}:{LDAP_PORT} -D '{LDAP_ADMIN_DN}' -w {LDAP_ADMIN_PASS} 2>/dev/null"
                result = subprocess.run(create_cmd, shell=True, capture_output=True, text=True)
                
                if result.returncode == 0:
                    print_success(f"Créé: {user['login']} ({user['full_name']})")
                    stats['created'] += 1
                    
                    # Ajouter au groupe du département
                    if user['department']:
                        group_cn = user['department'].lower().replace(' ', '-').replace('é', 'e')
                        group_dn = f"cn={group_cn},ou=groups,{LDAP_BASE_DN}"
                        
                        add_member_ldif = f"""dn: {group_dn}
changetype: modify
add: member
member: {user_dn}
"""
                        add_cmd = f"echo '{add_member_ldif}' | ldapmodify -x -H ldap://{LDAP_HOST}:{LDAP_PORT} -D '{LDAP_ADMIN_DN}' -w {LDAP_ADMIN_PASS} 2>/dev/null"
                        subprocess.run(add_cmd, shell=True)
                else:
                    print_error(f"Erreur création {user['login']}: {result.stderr}")
                    stats['errors'] += 1
                    
        except Exception as e:
            print_error(f"Erreur pour {user['login']}: {e}")
            stats['errors'] += 1
    
    return stats


# =============================================================================
# VÉRIFICATION POST-PROVISIONING
# =============================================================================

def verify_provisioning(target: str):
    """Vérifie le résultat du provisioning"""
    
    print_section(f"Vérification {target}", "🔍")
    
    if target == 'intranet':
        cmd = f"PGPASSWORD={INTRANET_DB_PASS} psql -h {INTRANET_DB_HOST} -p {INTRANET_DB_PORT} -U {INTRANET_DB_USER} -d {INTRANET_DB_NAME} -c \"SELECT username, full_name, department, enabled, roles FROM v_users_with_roles ORDER BY username LIMIT 10;\" 2>/dev/null"
    elif target == 'homeapp':
        cmd = f"PGPASSWORD={HOMEAPP_DB_PASS} psql -h {HOMEAPP_DB_HOST} -p {HOMEAPP_DB_PORT} -U {HOMEAPP_DB_USER} -d {HOMEAPP_DB_NAME} -c \"SELECT login, full_name, department, is_active, role_codes FROM v_users_with_roles ORDER BY login LIMIT 10;\" 2>/dev/null"
    elif target == 'ldap':
        cmd = f"ldapsearch -x -H ldap://{LDAP_HOST}:{LDAP_PORT} -D '{LDAP_ADMIN_DN}' -w {LDAP_ADMIN_PASS} -b 'ou=users,{LDAP_BASE_DN}' '(objectClass=inetOrgPerson)' uid cn mail 2>/dev/null | grep -E '^(dn|uid|cn|mail):' | head -40"
    else:
        return
    
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.stdout:
        print(result.stdout)
    else:
        print_warning("Aucun résultat trouvé")


# =============================================================================
# MAIN
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description='Démo de provisioning IGA - Sans N8N',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemples:
  python3 demo_provisioning.py                    # Provisioning complet
  python3 demo_provisioning.py --target intranet  # Uniquement vers Intranet
  python3 demo_provisioning.py --target homeapp   # Uniquement vers HomeApp
  python3 demo_provisioning.py --target ldap      # Uniquement vers LDAP
  python3 demo_provisioning.py --dry-run          # Simulation
        """
    )
    parser.add_argument('--target', default='all',
                       choices=['all', 'intranet', 'homeapp', 'ldap'],
                       help='Cible du provisioning (default: all)')
    parser.add_argument('--csv', default=HR_CSV_PATH,
                       help='Chemin vers le fichier CSV RH')
    parser.add_argument('--dry-run', action='store_true',
                       help='Mode simulation (aucune modification)')
    parser.add_argument('--verify', action='store_true',
                       help='Vérifier le provisioning après exécution')
    parser.add_argument('--quiet', '-q', action='store_true',
                       help='Mode silencieux')
    
    args = parser.parse_args()
    
    if not args.quiet:
        print_banner()
    
    print_header("CONFIGURATION", "⚙️")
    print_info(f"Source CSV     : {args.csv}")
    print_info(f"Cible          : {args.target}")
    print_info(f"Mode dry-run   : {'Oui' if args.dry_run else 'Non'}")
    print_info(f"Date/Heure     : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    if args.dry_run:
        print_warning("\n⚠️  MODE SIMULATION - Aucune modification ne sera effectuée\n")
    
    # Lecture des données RH
    print_header("LECTURE DES DONNÉES RH", "📖")
    users = read_hr_data(args.csv)
    
    if not users:
        print_error("Aucun utilisateur à provisionner")
        sys.exit(1)
    
    # Afficher la répartition
    print("\n  Répartition par département:")
    depts = {}
    for user in users:
        dept = user['department'] or 'Non défini'
        depts[dept] = depts.get(dept, 0) + 1
    
    for dept, count in sorted(depts.items()):
        print(f"    • {dept}: {count} utilisateur(s)")
    
    # Statistiques globales
    global_stats = {}
    
    # Provisioning vers Intranet
    if args.target in ['all', 'intranet']:
        print_header("PROVISIONING VERS INTRANET (PostgreSQL)", "🗄️")
        stats = provision_to_postgresql(
            users,
            INTRANET_DB_HOST, INTRANET_DB_PORT,
            INTRANET_DB_NAME, INTRANET_DB_USER, INTRANET_DB_PASS,
            'Intranet',
            args.dry_run
        )
        global_stats['Intranet'] = stats
    
    # Provisioning vers HomeApp
    if args.target in ['all', 'homeapp']:
        print_header("PROVISIONING VERS HOMEAPP (PostgreSQL)", "🏠")
        stats = provision_to_postgresql(
            users,
            HOMEAPP_DB_HOST, HOMEAPP_DB_PORT,
            HOMEAPP_DB_NAME, HOMEAPP_DB_USER, HOMEAPP_DB_PASS,
            'HomeApp',
            args.dry_run
        )
        global_stats['HomeApp'] = stats
    
    # Provisioning vers LDAP
    if args.target in ['all', 'ldap']:
        print_header("PROVISIONING VERS LDAP (OpenLDAP)", "📁")
        stats = provision_to_ldap(users, args.dry_run)
        global_stats['LDAP'] = stats
    
    # Résumé
    print_header("RÉSUMÉ DU PROVISIONING", "📊")
    print_stats_table(global_stats)
    
    # Calcul du succès global
    total_errors = sum(s.get('errors', 0) for s in global_stats.values())
    total_created = sum(s.get('created', 0) for s in global_stats.values())
    total_updated = sum(s.get('updated', 0) for s in global_stats.values())
    
    if total_errors == 0:
        print(f"{Colors.GREEN}{Colors.BOLD}✅ Provisioning terminé avec succès!{Colors.END}")
        print(f"   {total_created} créé(s), {total_updated} mis à jour")
    else:
        print(f"{Colors.YELLOW}{Colors.BOLD}⚠️  Provisioning terminé avec {total_errors} erreur(s){Colors.END}")
    
    # Vérification si demandée
    if args.verify and not args.dry_run:
        print_header("VÉRIFICATION POST-PROVISIONING", "🔍")
        
        if args.target in ['all', 'intranet']:
            verify_provisioning('intranet')
        if args.target in ['all', 'homeapp']:
            verify_provisioning('homeapp')
        if args.target in ['all', 'ldap']:
            verify_provisioning('ldap')
    
    print("\n")


if __name__ == '__main__':
    main()

