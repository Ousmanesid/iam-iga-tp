#!/usr/bin/env python3
"""
Test de création avec logging détaillé
"""

import xmlrpc.client
import json

url = 'http://localhost:8069'
db = 'odoo'
username = 'midpoint_service'
password = 'midpoint123'

print("🔍 Test de création Alice Doe avec détails\n")

# Authentification
common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common')
uid = common.authenticate(db, username, password, {})
print(f"✅ Authentifié, UID: {uid}\n")

objects = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object')

# Trouver le groupe Internal User
group_ref = objects.execute_kw(db, uid, password,
    'ir.model.data', 'search_read',
    [[['module', '=', 'base'], ['name', '=', 'group_user'], ['model', '=', 'res.groups']]],
    {'fields': ['res_id'], 'limit': 1})

group_id = group_ref[0]['res_id']

# Valeurs EXACTES envoyées
user_values = {
    'login': 'alice.doe',
    'name': 'Alice Doe',
    'email': 'alice.doe@example.com',  # EMAIL COMPLET avec @
    'active': True,
    'groups_id': [[6, 0, [group_id]]],
    'notification_type': 'inbox'
}

print("📤 Valeurs envoyées à Odoo :")
print(json.dumps(user_values, indent=2))
print()

# Créer
new_user_id = objects.execute_kw(db, uid, password,
    'res.users', 'create',
    [[user_values]])

if isinstance(new_user_id, list):
    new_user_id = new_user_id[0]

print(f"✅ Créé avec ID: {new_user_id}\n")

# Relire via l'API pour voir ce que Odoo a stocké
user_data = objects.execute_kw(db, uid, password,
    'res.users', 'read',
    [[new_user_id]],
    {'fields': ['login', 'name', 'email', 'partner_id']})

print("📥 Valeurs lues depuis l'API :")
print(json.dumps(user_data, indent=2))
print()

# Vérifier dans la base SQL
import subprocess
result = subprocess.run([
    'docker', 'exec', '-i', 'odoo-db', 'psql', '-U', 'odoo', '-d', 'odoo', '-c',
    f"SELECT u.id, u.login, u.partner_id, p.name, p.email FROM res_users u LEFT JOIN res_partner p ON u.partner_id = p.id WHERE u.id = {new_user_id};"
], capture_output=True, text=True)

print("📊 Valeurs dans la base SQL :")
print(result.stdout)

print("✅ Test terminé!")
