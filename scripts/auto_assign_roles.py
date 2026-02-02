#!/usr/bin/env python3
"""
Script d'assignation automatique des rôles basé sur le département.

Ce script:
1. Lit les utilisateurs existants depuis la base Intranet
2. Détermine les rôles appropriés selon leur département/titre
3. Assigne automatiquement les rôles sans créer de nouveaux utilisateurs

Usage:
    python3 auto_assign_roles.py [--dry-run] [--verbose]
    
Options:
    --dry-run   : Affiche les changements sans les appliquer
    --verbose   : Affiche plus de détails
"""

import psycopg2
import argparse
import sys
from typing import Dict, List, Tuple

# Configuration de la base de données Intranet
DB_CONFIG = {
    'host': 'localhost',
    'port': 5435,
    'dbname': 'intranet',
    'user': 'intranet',
    'password': 'intranet123'
}

# Mapping département → rôles
DEPARTMENT_ROLE_MAPPING = {
    # Commercial / Ventes
    'commercial': ['AGENT_COMMERCIAL', 'USER'],
    'sales': ['AGENT_COMMERCIAL', 'USER'],
    'vente': ['AGENT_COMMERCIAL', 'USER'],
    
    # RH / Administration
    'rh': ['RH_MANAGER', 'USER'],
    'ressources humaines': ['RH_MANAGER', 'USER'],
    'human resources': ['RH_MANAGER', 'USER'],
    'administration': ['RH_MANAGER', 'USER'],
    
    # IT / Informatique
    'it': ['IT_ADMIN', 'USER'],
    'informatique': ['IT_ADMIN', 'USER'],
    'r&d': ['IT_ADMIN', 'USER'],
    'research': ['IT_ADMIN', 'USER'],
    'research & development': ['IT_ADMIN', 'USER'],
    'r&d usa': ['IT_ADMIN', 'USER'],
    
    # Finance / Comptabilité
    'comptabilité': ['COMPTABLE', 'USER'],
    'compta': ['COMPTABLE', 'USER'],
    'finance': ['COMPTABLE', 'USER'],
    'accounting': ['COMPTABLE', 'USER'],
    
    # Management
    'management': ['MANAGER', 'USER'],
    'direction': ['MANAGER', 'USER'],
    
    # Services professionnels
    'professional services': ['USER'],
    'services': ['USER'],
    
    # Projets
    'long term projects': ['USER'],
    'projects': ['USER'],
}

# Mapping titre → rôles additionnels
TITLE_ROLE_MAPPING = {
    'manager': ['MANAGER'],
    'responsable': ['MANAGER'],
    'directeur': ['MANAGER'],
    'director': ['MANAGER'],
    'chief': ['MANAGER'],
    'ceo': ['MANAGER'],
    'cto': ['IT_ADMIN', 'MANAGER'],
    'cfo': ['COMPTABLE', 'MANAGER'],
    'team leader': ['MANAGER'],
    'rh': ['RH_MANAGER'],
    'human resources': ['RH_MANAGER'],
    'commercial': ['AGENT_COMMERCIAL'],
    'consultant': ['USER'],
    'developer': ['USER'],
    'développeur': ['USER'],
}


def get_roles_for_user(department: str, title: str) -> List[str]:
    """
    Détermine les rôles à assigner selon le département et le titre.
    """
    roles = set()
    roles.add('USER')  # Rôle de base pour tous
    
    if department:
        dept_lower = department.lower().strip()
        
        # Recherche exacte d'abord
        if dept_lower in DEPARTMENT_ROLE_MAPPING:
            roles.update(DEPARTMENT_ROLE_MAPPING[dept_lower])
        else:
            # Recherche partielle
            for key, dept_roles in DEPARTMENT_ROLE_MAPPING.items():
                if key in dept_lower or dept_lower in key:
                    roles.update(dept_roles)
                    break
    
    if title:
        title_lower = title.lower().strip()
        
        for key, title_roles in TITLE_ROLE_MAPPING.items():
            if key in title_lower:
                roles.update(title_roles)
    
    return list(roles)


def connect_db() -> psycopg2.extensions.connection:
    """Établit la connexion à la base de données."""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        return conn
    except psycopg2.Error as e:
        print(f"❌ Erreur de connexion à la base de données: {e}")
        sys.exit(1)


def get_all_users(conn) -> List[Dict]:
    """Récupère tous les utilisateurs de la base."""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT id, username, email, first_name, last_name, 
                   department, title, enabled
            FROM app_users
            ORDER BY username
        """)
        
        columns = ['id', 'username', 'email', 'first_name', 'last_name', 
                   'department', 'title', 'enabled']
        return [dict(zip(columns, row)) for row in cur.fetchall()]


def get_user_roles(conn, user_id: int) -> List[str]:
    """Récupère les rôles actuels d'un utilisateur."""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT r.role_name 
            FROM user_roles ur
            JOIN app_roles r ON ur.role_id = r.id
            WHERE ur.user_id = %s
        """, (user_id,))
        return [row[0] for row in cur.fetchall()]


def assign_role(conn, username: str, role_name: str) -> bool:
    """Assigne un rôle à un utilisateur."""
    with conn.cursor() as cur:
        try:
            cur.execute("SELECT assign_role(%s, %s)", (username, role_name))
            return True
        except psycopg2.Error as e:
            print(f"  ⚠️  Erreur assignation {role_name} à {username}: {e}")
            return False


def revoke_role(conn, username: str, role_name: str) -> bool:
    """Révoque un rôle d'un utilisateur."""
    with conn.cursor() as cur:
        try:
            cur.execute("SELECT revoke_role(%s, %s)", (username, role_name))
            return True
        except psycopg2.Error as e:
            print(f"  ⚠️  Erreur révocation {role_name} de {username}: {e}")
            return False


def auto_assign_roles(dry_run: bool = False, verbose: bool = False) -> Dict:
    """
    Fonction principale d'assignation automatique des rôles.
    
    Returns:
        Dictionnaire avec les statistiques
    """
    stats = {
        'users_processed': 0,
        'roles_assigned': 0,
        'roles_revoked': 0,
        'users_updated': 0,
        'errors': 0
    }
    
    print("=" * 70)
    print("🔄 ASSIGNATION AUTOMATIQUE DES RÔLES")
    print("=" * 70)
    
    if dry_run:
        print("⚠️  Mode DRY-RUN : aucun changement ne sera effectué\n")
    
    conn = connect_db()
    print("✅ Connecté à la base de données Intranet\n")
    
    try:
        users = get_all_users(conn)
        print(f"📋 {len(users)} utilisateurs trouvés\n")
        
        for user in users:
            stats['users_processed'] += 1
            
            username = user['username']
            department = user['department'] or ''
            title = user['title'] or ''
            
            # Calculer les rôles appropriés
            expected_roles = set(get_roles_for_user(department, title))
            current_roles = set(get_user_roles(conn, user['id']))
            
            # Rôles à ajouter
            roles_to_add = expected_roles - current_roles
            
            # Rôles à retirer (optionnel - désactivé par défaut pour éviter la révocation accidentelle)
            # roles_to_remove = current_roles - expected_roles
            roles_to_remove = set()  # Ne pas révoquer automatiquement
            
            if roles_to_add or roles_to_remove:
                stats['users_updated'] += 1
                
                if verbose or roles_to_add:
                    print(f"👤 {username}")
                    print(f"   Département: {department or 'Non défini'}")
                    print(f"   Titre: {title or 'Non défini'}")
                    print(f"   Rôles actuels: {', '.join(current_roles) or 'Aucun'}")
                    print(f"   Rôles calculés: {', '.join(expected_roles)}")
                
                # Ajouter les nouveaux rôles
                for role in roles_to_add:
                    if dry_run:
                        print(f"   ➕ [DRY-RUN] Assignerait: {role}")
                        stats['roles_assigned'] += 1
                    else:
                        if assign_role(conn, username, role):
                            print(f"   ✅ Assigné: {role}")
                            stats['roles_assigned'] += 1
                        else:
                            stats['errors'] += 1
                
                # Révoquer les rôles obsolètes (si activé)
                for role in roles_to_remove:
                    if dry_run:
                        print(f"   ➖ [DRY-RUN] Révoquerait: {role}")
                        stats['roles_revoked'] += 1
                    else:
                        if revoke_role(conn, username, role):
                            print(f"   🔴 Révoqué: {role}")
                            stats['roles_revoked'] += 1
                        else:
                            stats['errors'] += 1
                
                if verbose or roles_to_add:
                    print()
            
            elif verbose:
                print(f"👤 {username} - OK (rôles déjà corrects: {', '.join(current_roles)})")
        
        if not dry_run:
            conn.commit()
            print("💾 Changements sauvegardés")
        
    except Exception as e:
        print(f"❌ Erreur: {e}")
        conn.rollback()
        stats['errors'] += 1
    finally:
        conn.close()
    
    # Afficher le résumé
    print("\n" + "=" * 70)
    print("📊 RÉSUMÉ")
    print("=" * 70)
    print(f"   Utilisateurs traités : {stats['users_processed']}")
    print(f"   Utilisateurs mis à jour : {stats['users_updated']}")
    print(f"   Rôles assignés : {stats['roles_assigned']}")
    print(f"   Rôles révoqués : {stats['roles_revoked']}")
    print(f"   Erreurs : {stats['errors']}")
    print("=" * 70)
    
    return stats


def show_current_status():
    """Affiche l'état actuel des utilisateurs et leurs rôles."""
    print("=" * 70)
    print("📋 ÉTAT ACTUEL DES UTILISATEURS ET RÔLES")
    print("=" * 70)
    
    conn = connect_db()
    
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT u.username, u.department, u.title, 
                       COALESCE(STRING_AGG(r.role_name, ', ' ORDER BY r.role_name), 'Aucun') as roles
                FROM app_users u
                LEFT JOIN user_roles ur ON u.id = ur.user_id
                LEFT JOIN app_roles r ON ur.role_id = r.id
                WHERE u.enabled = true
                GROUP BY u.id, u.username, u.department, u.title
                ORDER BY u.username
            """)
            
            print(f"\n{'Username':<25} {'Département':<25} {'Rôles':<30}")
            print("-" * 80)
            
            for row in cur.fetchall():
                username, department, title, roles = row
                dept = (department or 'N/A')[:24]
                print(f"{username:<25} {dept:<25} {roles:<30}")
            
            print()
    
    finally:
        conn.close()


def main():
    parser = argparse.ArgumentParser(
        description="Assignation automatique des rôles selon le département"
    )
    parser.add_argument(
        '--dry-run', '-d',
        action='store_true',
        help="Affiche les changements sans les appliquer"
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help="Affiche plus de détails"
    )
    parser.add_argument(
        '--status', '-s',
        action='store_true',
        help="Affiche l'état actuel des rôles"
    )
    
    args = parser.parse_args()
    
    if args.status:
        show_current_status()
    else:
        auto_assign_roles(dry_run=args.dry_run, verbose=args.verbose)


if __name__ == '__main__':
    main()
