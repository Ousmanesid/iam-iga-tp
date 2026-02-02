#!/usr/bin/env python3
"""
Test de l'API XML-RPC d'Odoo avec le compte midpoint_service
"""

import xmlrpc.client

# Configuration
url = 'http://localhost:8069'
db = 'odoo'
username = 'midpoint_service'
password = 'midpoint123'

print("🔧 Test de l'API XML-RPC Odoo\n")

# 1. Authentification
print("1️⃣  Authentification...")
common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common')

try:
    uid = common.authenticate(db, username, password, {})
    if uid:
        print(f"✅ Authentifié avec succès, UID: {uid}\n")
    else:
        print("❌ Échec d'authentification")
        exit(1)
except Exception as e:
    print(f"❌ Erreur: {e}")
    exit(1)

# 2. Test de recherche
print("2️⃣  Test de recherche (compte midpoint_service)...")
objects = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object')

try:
    result = objects.execute_kw(db, uid, password,
        'res.users', 'search_read',
        [[['login', '=', username]]],
        {'fields': ['id', 'login', 'name', 'email', 'active'], 'limit': 1})
    
    if result:
        user = result[0]
        print(f"✅ Utilisateur trouvé:")
        print(f"   ID     : {user['id']}")
        print(f"   Login  : {user['login']}")
        print(f"   Nom    : {user['name']}")
        print(f"   Email  : {user['email']}")
        print(f"   Actif  : {user['active']}\n")
    else:
        print("❌ Utilisateur non trouvé")
        
except Exception as e:
    print(f"❌ Erreur lors de la recherche: {e}\n")

# 3. Test de création (utilisateur test)
print("3️⃣  Test de création d'utilisateur...")

test_login = 'test.xmlrpc'

# Vérifier si l'utilisateur existe déjà
existing = objects.execute_kw(db, uid, password,
    'res.users', 'search',
    [[['login', '=', test_login]]],
    {'limit': 1})

if existing:
    print(f"⚠️  L'utilisateur {test_login} existe déjà (ID: {existing[0]})")
    print("   Désactivation pour nettoyer...")
    objects.execute_kw(db, uid, password,
        'res.users', 'write',
        [existing, {'active': False}])
    print("✅ Nettoyage effectué\n")

# Trouver le groupe Internal User
print("4️⃣  Recherche du groupe 'Internal User'...")
group_ref = objects.execute_kw(db, uid, password,
    'ir.model.data', 'search_read',
    [[['module', '=', 'base'], ['name', '=', 'group_user'], ['model', '=', 'res.groups']]],
    {'fields': ['res_id'], 'limit': 1})

if group_ref:
    group_id = group_ref[0]['res_id']
    print(f"✅ Groupe Internal User trouvé: ID {group_id}\n")
    
    # Créer l'utilisateur
    print("5️⃣  Création de l'utilisateur test...")
    try:
        new_user_id = objects.execute_kw(db, uid, password,
            'res.users', 'create',
            [[{
                'login': test_login,
                'name': 'Test XML-RPC User',
                'email': 'test.xmlrpc@example.com',
                'active': True,
                'groups_id': [[6, 0, [group_id]]],
                'notification_type': 'inbox'
            }]])
        
        print(f"✅ Utilisateur créé avec succès, ID: {new_user_id}\n")
        
        # Vérifier la création
        print("6️⃣  Vérification de l'utilisateur créé...")
        created_user = objects.execute_kw(db, uid, password,
            'res.users', 'read',
            [[new_user_id]],
            {'fields': ['login', 'name', 'email', 'partner_id', 'groups_id']})
        
        if created_user:
            user = created_user[0]
            print(f"✅ Utilisateur vérifié:")
            print(f"   Login      : {user['login']}")
            print(f"   Nom        : {user['name']}")
            print(f"   Email      : {user['email']}")
            print(f"   Partner ID : {user['partner_id']}")
            print(f"   Groupes    : {len(user['groups_id'])} groupe(s)\n")
            
    except Exception as e:
        print(f"❌ Erreur lors de la création: {e}")
        
else:
    print("❌ Groupe Internal User non trouvé")

print("✅ Test terminé !")
