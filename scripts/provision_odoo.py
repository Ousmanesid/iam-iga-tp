#!/usr/bin/env python3
"""
Script de provisionnement Odoo
Crée et gère les utilisateurs dans Odoo via l'API XML-RPC

Ce script peut être utilisé :
- Manuellement pour provisionner des utilisateurs
- Intégré avec MidPoint via un connecteur Scripted
- En mode batch pour synchroniser depuis un fichier CSV

Usage:
    python3 provision_odoo.py --action create --username jean.dupont --email jean@example.com
    python3 provision_odoo.py --action sync --csv /path/to/users.csv
    python3 provision_odoo.py --action list
"""

import argparse
import csv
import xmlrpc.client
import sys
import os
from typing import Optional, Dict, List, Any

# Configuration Odoo
ODOO_URL = os.getenv('ODOO_URL', 'http://odoo:8069')
ODOO_DB = os.getenv('ODOO_DB', 'odoo')
ODOO_USER = os.getenv('ODOO_USER', 'admin')
ODOO_PASSWORD = os.getenv('ODOO_PASSWORD', 'admin')

class OdooProvisioner:
    """Classe pour gérer le provisionnement des utilisateurs Odoo"""
    
    def __init__(self, url: str, db: str, username: str, password: str):
        self.url = url
        self.db = db
        self.username = username
        self.password = password
        self.uid = None
        self.common = None
        self.models = None
        
    def connect(self) -> bool:
        """Établit la connexion avec Odoo"""
        try:
            self.common = xmlrpc.client.ServerProxy(f'{self.url}/xmlrpc/2/common')
            
            # Vérifier la version d'Odoo
            version = self.common.version()
            print(f"✓ Connecté à Odoo {version.get('server_version', 'unknown')}")
            
            # Authentification
            self.uid = self.common.authenticate(self.db, self.username, self.password, {})
            
            if not self.uid:
                print("✗ Échec de l'authentification")
                return False
                
            print(f"✓ Authentifié avec UID: {self.uid}")
            
            # Connexion au modèle
            self.models = xmlrpc.client.ServerProxy(f'{self.url}/xmlrpc/2/object')
            return True
            
        except Exception as e:
            print(f"✗ Erreur de connexion: {e}")
            return False
    
    def _execute(self, model: str, method: str, *args, **kwargs) -> Any:
        """Exécute une méthode sur un modèle Odoo"""
        return self.models.execute_kw(
            self.db, self.uid, self.password,
            model, method, args, kwargs
        )
    
    def list_users(self) -> List[Dict]:
        """Liste tous les utilisateurs Odoo"""
        user_ids = self._execute('res.users', 'search', [])
        users = self._execute('res.users', 'read', user_ids, 
                             {'fields': ['id', 'login', 'name', 'email', 'active', 'groups_id']})
        return users
    
    def get_user(self, login: str) -> Optional[Dict]:
        """Récupère un utilisateur par son login"""
        user_ids = self._execute('res.users', 'search', [('login', '=', login)])
        if not user_ids:
            return None
        users = self._execute('res.users', 'read', user_ids, 
                             {'fields': ['id', 'login', 'name', 'email', 'active', 'groups_id']})
        return users[0] if users else None
    
    def create_user(self, login: str, name: str, email: str, 
                   password: str = None, groups: List[int] = None) -> Optional[int]:
        """Crée un nouvel utilisateur"""
        try:
            # Vérifier si l'utilisateur existe déjà
            existing = self.get_user(login)
            if existing:
                print(f"  → L'utilisateur '{login}' existe déjà (ID: {existing['id']})")
                return existing['id']
            
            # Données de l'utilisateur
            user_data = {
                'login': login,
                'name': name,
                'email': email or f"{login}@example.com",
            }
            
            # Mot de passe (si fourni)
            if password:
                user_data['password'] = password
            
            # Groupes (si fournis)
            if groups:
                user_data['groups_id'] = [(6, 0, groups)]
            
            # Création
            user_id = self._execute('res.users', 'create', user_data)
            print(f"  ✓ Utilisateur créé: {login} (ID: {user_id})")
            return user_id
            
        except Exception as e:
            print(f"  ✗ Erreur création utilisateur {login}: {e}")
            return None
    
    def update_user(self, login: str, **kwargs) -> bool:
        """Met à jour un utilisateur existant"""
        try:
            user = self.get_user(login)
            if not user:
                print(f"  ✗ Utilisateur '{login}' non trouvé")
                return False
            
            # Filtrer les champs valides
            valid_fields = ['name', 'email', 'active', 'password']
            update_data = {k: v for k, v in kwargs.items() if k in valid_fields and v is not None}
            
            if update_data:
                self._execute('res.users', 'write', [user['id']], update_data)
                print(f"  ✓ Utilisateur mis à jour: {login}")
            
            return True
            
        except Exception as e:
            print(f"  ✗ Erreur mise à jour {login}: {e}")
            return False
    
    def delete_user(self, login: str) -> bool:
        """Supprime (désactive) un utilisateur"""
        try:
            user = self.get_user(login)
            if not user:
                print(f"  → Utilisateur '{login}' non trouvé")
                return True
            
            # Désactiver plutôt que supprimer
            self._execute('res.users', 'write', [user['id']], {'active': False})
            print(f"  ✓ Utilisateur désactivé: {login}")
            return True
            
        except Exception as e:
            print(f"  ✗ Erreur suppression {login}: {e}")
            return False
    
    def get_group_id(self, group_name: str) -> Optional[int]:
        """Récupère l'ID d'un groupe par son nom"""
        try:
            group_ids = self._execute('res.groups', 'search', [('name', 'ilike', group_name)])
            return group_ids[0] if group_ids else None
        except:
            return None
    
    def assign_group(self, login: str, group_name: str) -> bool:
        """Assigne un groupe à un utilisateur"""
        try:
            user = self.get_user(login)
            if not user:
                print(f"  ✗ Utilisateur '{login}' non trouvé")
                return False
            
            group_id = self.get_group_id(group_name)
            if not group_id:
                print(f"  ✗ Groupe '{group_name}' non trouvé")
                return False
            
            # Ajouter le groupe
            self._execute('res.users', 'write', [user['id']], 
                         {'groups_id': [(4, group_id)]})
            print(f"  ✓ Groupe '{group_name}' assigné à {login}")
            return True
            
        except Exception as e:
            print(f"  ✗ Erreur assignation groupe: {e}")
            return False
    
    def sync_from_csv(self, csv_path: str) -> Dict[str, int]:
        """Synchronise les utilisateurs depuis un fichier CSV"""
        stats = {'created': 0, 'updated': 0, 'errors': 0}
        
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            for row in reader:
                # Construire le login à partir du prénom et nom
                first_name = row.get('givenName', row.get('first_name', ''))
                last_name = row.get('familyName', row.get('last_name', ''))
                
                if not first_name or not last_name:
                    continue
                
                login = f"{first_name.lower()}.{last_name.lower()}".replace(' ', '')
                name = f"{first_name} {last_name}"
                email = row.get('email', f"{login}@example.com")
                status = row.get('status', 'Active').lower()
                
                # Vérifier si l'utilisateur existe
                existing = self.get_user(login)
                
                if existing:
                    # Mise à jour
                    if self.update_user(login, name=name, email=email, 
                                       active=(status == 'active')):
                        stats['updated'] += 1
                    else:
                        stats['errors'] += 1
                else:
                    # Création
                    if self.create_user(login, name, email):
                        stats['created'] += 1
                        
                        # Désactiver si nécessaire
                        if status != 'active':
                            self.update_user(login, active=False)
                    else:
                        stats['errors'] += 1
        
        return stats


def main():
    parser = argparse.ArgumentParser(description='Provisionnement Odoo')
    parser.add_argument('--action', required=True, 
                       choices=['list', 'create', 'update', 'delete', 'sync', 'test'],
                       help='Action à effectuer')
    parser.add_argument('--username', help='Login de l\'utilisateur')
    parser.add_argument('--name', help='Nom complet')
    parser.add_argument('--email', help='Adresse email')
    parser.add_argument('--password', help='Mot de passe')
    parser.add_argument('--csv', help='Chemin vers le fichier CSV')
    parser.add_argument('--group', help='Nom du groupe à assigner')
    parser.add_argument('--url', default=ODOO_URL, help='URL Odoo')
    parser.add_argument('--db', default=ODOO_DB, help='Nom de la base Odoo')
    parser.add_argument('--user', default=ODOO_USER, help='Utilisateur admin Odoo')
    parser.add_argument('--pwd', default=ODOO_PASSWORD, help='Mot de passe admin')
    
    args = parser.parse_args()
    
    print(f"\n{'='*60}")
    print(f"  Provisionnement Odoo - {args.action.upper()}")
    print(f"{'='*60}\n")
    
    # Connexion
    provisioner = OdooProvisioner(args.url, args.db, args.user, args.pwd)
    
    if not provisioner.connect():
        print("\n✗ Impossible de se connecter à Odoo")
        sys.exit(1)
    
    print()
    
    # Exécuter l'action
    if args.action == 'test':
        print("✓ Connexion réussie!")
        
    elif args.action == 'list':
        users = provisioner.list_users()
        print(f"{'ID':<6} {'Login':<25} {'Nom':<30} {'Email':<35} {'Actif'}")
        print('-' * 100)
        for user in users:
            print(f"{user['id']:<6} {user['login']:<25} {user['name']:<30} {user.get('email', '-'):<35} {'✓' if user['active'] else '✗'}")
        print(f"\nTotal: {len(users)} utilisateurs")
        
    elif args.action == 'create':
        if not args.username:
            print("✗ --username requis pour create")
            sys.exit(1)
        name = args.name or args.username
        email = args.email or f"{args.username}@example.com"
        provisioner.create_user(args.username, name, email, args.password)
        
    elif args.action == 'update':
        if not args.username:
            print("✗ --username requis pour update")
            sys.exit(1)
        provisioner.update_user(args.username, name=args.name, email=args.email)
        
    elif args.action == 'delete':
        if not args.username:
            print("✗ --username requis pour delete")
            sys.exit(1)
        provisioner.delete_user(args.username)
        
    elif args.action == 'sync':
        if not args.csv:
            print("✗ --csv requis pour sync")
            sys.exit(1)
        stats = provisioner.sync_from_csv(args.csv)
        print(f"\n{'='*40}")
        print(f"  Résumé de la synchronisation")
        print(f"{'='*40}")
        print(f"  Créés    : {stats['created']}")
        print(f"  Mis à jour: {stats['updated']}")
        print(f"  Erreurs  : {stats['errors']}")
    
    print(f"\n{'='*60}\n")


if __name__ == '__main__':
    main()








