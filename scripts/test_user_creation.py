#!/usr/bin/env python3
"""
Test de création d'utilisateur Odoo via XML-RPC comme MidPoint le fera
"""

import xmlrpc.client

# Configuration
url = 'http://localhost:8069'
db = 'odoo'
username = 'midpoint_service'
password = 'midpoint123'

print("🧪 Test de création utilisateur Odoo (simulation MidPoint)\n")

# Authentification
common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common')
uid = common.authenticate(db, username, password, {})
print(f"✅ Authentifié, UID: {uid}\n")

objects = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object')

# Données utilisateur comme MidPoint les enverrait
test_user = {
    'login': 'alice.doe',
    'name': 'Alice Doe',
    'email': 'alice.doe@example.com'
}

print(f"📝 Données à créer:")
print(f"   Login: {test_user['login']}")
print(f"   Name:  {test_user['name']}")
print(f"   Email: {test_user['email']}\n")

# Vérifier si l'utilisateur existe
existing = objects.execute_kw(db, uid, password,
    'res.users', 'search',
    [[['login', '=', test_user['login']]]],
    {'limit': 1})

if existing:
    print(f"⚠️  L'utilisateur existe déjà (ID: {existing[0]}), suppression...\n")
    objects.execute_kw(db, uid, password,
        'res.users', 'write',
        [existing, {'active': False}])

# Trouver le groupe Internal User
group_ref = objects.execute_kw(db, uid, password,
    'ir.model.data', 'search_read',
    [[['module', '=', 'base'], ['name', '=', 'group_user'], ['model', '=', 'res.groups']]],
    {'fields': ['res_id'], 'limit': 1})

group_id = group_ref[0]['res_id']
print(f"✅ Groupe Internal User: {group_id}\n")

# Créer l'utilisateur
user_values = {
    'login': test_user['login'],
    'name': test_user['name'],
    'email': test_user['email'],
    'active': True,
    'groups_id': [[6, 0, [group_id]]],
    'notification_type': 'inbox'
}

print("🚀 Création de l'utilisateur...")
new_user_id = objects.execute_kw(db, uid, password,
    'res.users', 'create',
    [[user_values]])

print(f"✅ Utilisateur créé, ID: {new_user_id}\n")

# Vérifier dans la base
import subprocess
result = subprocess.run([
    'docker', 'exec', '-i', 'odoo-db', 'psql', '-U', 'odoo', '-d', 'odoo', '-c',
    f"SELECT u.id, u.login, p.name as partner_name, p.email, (SELECT COUNT(*) FROM res_groups_users_rel WHERE uid = u.id) as nb_groups FROM res_users u LEFT JOIN res_partner p ON u.partner_id = p.id WHERE u.id = {new_user_id};"
], capture_output=True, text=True)

print("📊 Vérification dans la base:")
print(result.stdout)

# Lister les groupes
groups_result = subprocess.run([
    'docker', 'exec', '-i', 'odoo-db', 'psql', '-U', 'odoo', '-d', 'odoo', '-t', '-c',
    f"SELECT d.module || '.' || d.name FROM res_groups_users_rel r JOIN res_groups g ON r.gid = g.id JOIN ir_model_data d ON d.res_id = g.id AND d.model = 'res.groups' WHERE r.uid = {new_user_id};"
], capture_output=True, text=True)

print("📋 Groupes attribués:")
for group in groups_result.stdout.strip().split('\n'):
    print(f"   - {group.strip()}")

print("\n✅ Test terminé!")
