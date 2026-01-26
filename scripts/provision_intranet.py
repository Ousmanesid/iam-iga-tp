#!/usr/bin/env python3
"""
Script de provisionnement Intranet (PostgreSQL)
Crée et gère les utilisateurs dans l'application Intranet

Ce script peut être utilisé :
- Manuellement pour provisionner des utilisateurs
- Intégré avec MidPoint via un connecteur Scripted
- En mode batch pour synchroniser depuis un fichier CSV

Usage:
    python3 provision_intranet.py --action create --username jean.dupont --email jean@example.com
    python3 provision_intranet.py --action sync --csv /path/to/users.csv
    python3 provision_intranet.py --action list
"""

import argparse
import csv
import sys
import os
from typing import Optional, Dict, List, Any

try:
    import psycopg2
    import psycopg2.extras
except ImportError:
    print("Installation de psycopg2...")
    os.system("pip3 install psycopg2-binary")
    import psycopg2
    import psycopg2.extras

# Configuration base de données
DB_HOST = os.getenv('INTRANET_DB_HOST', 'localhost')
DB_PORT = os.getenv('INTRANET_DB_PORT', '5433')
DB_NAME = os.getenv('INTRANET_DB_NAME', 'intranet')
DB_USER = os.getenv('INTRANET_DB_USER', 'intranet')
DB_PASS = os.getenv('INTRANET_DB_PASS', 'intranet123')


class IntranetProvisioner:
    """Classe pour gérer le provisionnement des utilisateurs Intranet"""
    
    def __init__(self, host: str, port: str, dbname: str, user: str, password: str):
        self.conn_params = {
            'host': host,
            'port': port,
            'dbname': dbname,
            'user': user,
            'password': password
        }
        self.conn = None
        
    def connect(self) -> bool:
        """Établit la connexion avec PostgreSQL"""
        try:
            self.conn = psycopg2.connect(**self.conn_params)
            self.conn.autocommit = True
            print(f"✓ Connecté à PostgreSQL ({self.conn_params['host']}:{self.conn_params['port']})")
            return True
        except Exception as e:
            print(f"✗ Erreur de connexion: {e}")
            return False
    
    def close(self):
        """Ferme la connexion"""
        if self.conn:
            self.conn.close()
    
    def list_users(self) -> List[Dict]:
        """Liste tous les utilisateurs"""
        with self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT * FROM v_users_with_roles ORDER BY username")
            return cur.fetchall()
    
    def get_user(self, username: str) -> Optional[Dict]:
        """Récupère un utilisateur par son username"""
        with self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT * FROM v_users_with_roles WHERE username = %s", (username,))
            return cur.fetchone()
    
    def create_user(self, username: str, email: str, first_name: str = None,
                   last_name: str = None, department: str = None, 
                   title: str = None, employee_number: str = None,
                   enabled: bool = True, roles: List[str] = None) -> Optional[int]:
        """Crée un nouvel utilisateur"""
        try:
            with self.conn.cursor() as cur:
                # Upsert utilisateur
                cur.execute("""
                    SELECT upsert_user(%s, %s, %s, %s, %s, %s, %s, %s)
                """, (username, email, first_name, last_name, department, 
                      title, employee_number, enabled))
                user_id = cur.fetchone()[0]
                
                print(f"  ✓ Utilisateur créé/mis à jour: {username} (ID: {user_id})")
                
                # Assigner les rôles
                if roles:
                    for role in roles:
                        self.assign_role(username, role)
                
                return user_id
                
        except Exception as e:
            print(f"  ✗ Erreur création utilisateur {username}: {e}")
            return None
    
    def update_user(self, username: str, **kwargs) -> bool:
        """Met à jour un utilisateur existant"""
        try:
            user = self.get_user(username)
            if not user:
                print(f"  ✗ Utilisateur '{username}' non trouvé")
                return False
            
            # Construire la requête de mise à jour
            updates = []
            values = []
            
            field_mapping = {
                'email': 'email',
                'first_name': 'first_name',
                'last_name': 'last_name',
                'department': 'department',
                'title': 'title',
                'enabled': 'enabled'
            }
            
            for key, col in field_mapping.items():
                if key in kwargs and kwargs[key] is not None:
                    updates.append(f"{col} = %s")
                    values.append(kwargs[key])
            
            if updates:
                # Ajouter full_name si prénom ou nom changé
                if 'first_name' in kwargs or 'last_name' in kwargs:
                    fn = kwargs.get('first_name', user.get('first_name', ''))
                    ln = kwargs.get('last_name', user.get('last_name', ''))
                    updates.append("full_name = %s")
                    values.append(f"{fn} {ln}".strip())
                
                values.append(username)
                
                with self.conn.cursor() as cur:
                    cur.execute(f"""
                        UPDATE app_users SET {', '.join(updates)}
                        WHERE username = %s
                    """, values)
                
                print(f"  ✓ Utilisateur mis à jour: {username}")
            
            return True
            
        except Exception as e:
            print(f"  ✗ Erreur mise à jour {username}: {e}")
            return False
    
    def delete_user(self, username: str) -> bool:
        """Supprime un utilisateur"""
        try:
            with self.conn.cursor() as cur:
                cur.execute("DELETE FROM app_users WHERE username = %s", (username,))
                if cur.rowcount > 0:
                    print(f"  ✓ Utilisateur supprimé: {username}")
                else:
                    print(f"  → Utilisateur '{username}' non trouvé")
            return True
            
        except Exception as e:
            print(f"  ✗ Erreur suppression {username}: {e}")
            return False
    
    def disable_user(self, username: str) -> bool:
        """Désactive un utilisateur"""
        return self.update_user(username, enabled=False)
    
    def assign_role(self, username: str, role_name: str) -> bool:
        """Assigne un rôle à un utilisateur"""
        try:
            with self.conn.cursor() as cur:
                cur.execute("SELECT assign_role(%s, %s)", (username, role_name))
            print(f"  ✓ Rôle '{role_name}' assigné à {username}")
            return True
        except Exception as e:
            print(f"  ✗ Erreur assignation rôle: {e}")
            return False
    
    def revoke_role(self, username: str, role_name: str) -> bool:
        """Révoque un rôle d'un utilisateur"""
        try:
            with self.conn.cursor() as cur:
                cur.execute("SELECT revoke_role(%s, %s)", (username, role_name))
            print(f"  ✓ Rôle '{role_name}' révoqué de {username}")
            return True
        except Exception as e:
            print(f"  ✗ Erreur révocation rôle: {e}")
            return False
    
    def sync_from_csv(self, csv_path: str) -> Dict[str, int]:
        """Synchronise les utilisateurs depuis un fichier CSV"""
        stats = {'created': 0, 'updated': 0, 'errors': 0}
        
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            for row in reader:
                # Construire les données utilisateur
                first_name = row.get('givenName', row.get('first_name', ''))
                last_name = row.get('familyName', row.get('last_name', ''))
                
                if not first_name or not last_name:
                    continue
                
                username = f"{first_name.lower()}.{last_name.lower()}".replace(' ', '').replace("'", '')
                email = row.get('email', f"{username}@example.com")
                department = row.get('department', '')
                title = row.get('title', '')
                employee_number = row.get('personalNumber', row.get('employee_number', ''))
                status = row.get('status', 'Active').lower()
                enabled = (status == 'active')
                
                # Déterminer les rôles en fonction du département
                roles = ['USER']
                if department.lower() == 'commercial':
                    roles.append('AGENT_COMMERCIAL')
                elif 'rh' in department.lower() or 'ressources' in department.lower():
                    roles.append('RH_MANAGER')
                elif 'informatique' in department.lower() or 'it' in department.lower():
                    roles.append('IT_ADMIN')
                elif 'comptabilité' in department.lower() or 'compta' in department.lower():
                    roles.append('COMPTABLE')
                
                # Ajouter rôle MANAGER si titre contient responsable/manager
                if 'responsable' in title.lower() or 'manager' in title.lower() or 'chef' in title.lower():
                    roles.append('MANAGER')
                
                # Vérifier si l'utilisateur existe
                existing = self.get_user(username)
                
                if existing:
                    # Mise à jour
                    if self.update_user(username, email=email, first_name=first_name,
                                       last_name=last_name, department=department,
                                       title=title, enabled=enabled):
                        stats['updated'] += 1
                    else:
                        stats['errors'] += 1
                else:
                    # Création
                    if self.create_user(username, email, first_name, last_name,
                                       department, title, employee_number, enabled, roles):
                        stats['created'] += 1
                    else:
                        stats['errors'] += 1
        
        return stats


def main():
    parser = argparse.ArgumentParser(description='Provisionnement Intranet PostgreSQL')
    parser.add_argument('--action', required=True, 
                       choices=['list', 'create', 'update', 'delete', 'disable', 
                               'sync', 'assign-role', 'revoke-role', 'test'],
                       help='Action à effectuer')
    parser.add_argument('--username', help='Username')
    parser.add_argument('--email', help='Adresse email')
    parser.add_argument('--first-name', help='Prénom')
    parser.add_argument('--last-name', help='Nom')
    parser.add_argument('--department', help='Département')
    parser.add_argument('--title', help='Titre/Poste')
    parser.add_argument('--role', help='Nom du rôle')
    parser.add_argument('--csv', help='Chemin vers le fichier CSV')
    parser.add_argument('--host', default=DB_HOST, help='Hôte PostgreSQL')
    parser.add_argument('--port', default=DB_PORT, help='Port PostgreSQL')
    parser.add_argument('--dbname', default=DB_NAME, help='Nom de la base')
    parser.add_argument('--user', default=DB_USER, help='Utilisateur PostgreSQL')
    parser.add_argument('--password', default=DB_PASS, help='Mot de passe')
    
    args = parser.parse_args()
    
    print(f"\n{'='*60}")
    print(f"  Provisionnement Intranet - {args.action.upper()}")
    print(f"{'='*60}\n")
    
    # Connexion
    provisioner = IntranetProvisioner(args.host, args.port, args.dbname, 
                                      args.user, args.password)
    
    if not provisioner.connect():
        print("\n✗ Impossible de se connecter à PostgreSQL")
        sys.exit(1)
    
    print()
    
    try:
        # Exécuter l'action
        if args.action == 'test':
            print("✓ Connexion réussie!")
            
        elif args.action == 'list':
            users = provisioner.list_users()
            print(f"{'Username':<20} {'Nom complet':<25} {'Département':<20} {'Rôles':<30} {'Actif'}")
            print('-' * 100)
            for user in users:
                print(f"{user['username']:<20} {(user['full_name'] or '-'):<25} {(user['department'] or '-'):<20} {(user['roles'] or 'USER'):<30} {'✓' if user['enabled'] else '✗'}")
            print(f"\nTotal: {len(users)} utilisateurs")
            
        elif args.action == 'create':
            if not args.username or not args.email:
                print("✗ --username et --email requis pour create")
                sys.exit(1)
            provisioner.create_user(
                args.username, args.email, 
                args.first_name, args.last_name,
                args.department, args.title
            )
            
        elif args.action == 'update':
            if not args.username:
                print("✗ --username requis pour update")
                sys.exit(1)
            provisioner.update_user(
                args.username, 
                email=args.email,
                first_name=args.first_name,
                last_name=args.last_name,
                department=args.department,
                title=args.title
            )
            
        elif args.action == 'delete':
            if not args.username:
                print("✗ --username requis pour delete")
                sys.exit(1)
            provisioner.delete_user(args.username)
            
        elif args.action == 'disable':
            if not args.username:
                print("✗ --username requis pour disable")
                sys.exit(1)
            provisioner.disable_user(args.username)
            
        elif args.action == 'sync':
            if not args.csv:
                print("✗ --csv requis pour sync")
                sys.exit(1)
            stats = provisioner.sync_from_csv(args.csv)
            print(f"\n{'='*40}")
            print(f"  Résumé de la synchronisation")
            print(f"{'='*40}")
            print(f"  Créés     : {stats['created']}")
            print(f"  Mis à jour: {stats['updated']}")
            print(f"  Erreurs   : {stats['errors']}")
            
        elif args.action == 'assign-role':
            if not args.username or not args.role:
                print("✗ --username et --role requis pour assign-role")
                sys.exit(1)
            provisioner.assign_role(args.username, args.role)
            
        elif args.action == 'revoke-role':
            if not args.username or not args.role:
                print("✗ --username et --role requis pour revoke-role")
                sys.exit(1)
            provisioner.revoke_role(args.username, args.role)
    
    finally:
        provisioner.close()
    
    print(f"\n{'='*60}\n")


if __name__ == '__main__':
    main()








