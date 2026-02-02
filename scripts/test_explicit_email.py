#!/usr/bin/env python3
"""
Test ultra-explicite : créer un user Charlie avec email séparé du login
et vérifier que le partner a bien le bon email
"""

import xmlrpc.client

url = 'http://localhost:8069'
db = 'odoo'
username = 'midpoint_service'
password = 'midpoint123'

print("🧪 Test création user avec email explicite\n")

# Auth
common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common')
uid = common.authenticate(db, username, password, {})
print(f"✅ Auth OK, UID: {uid}\n")

objects = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object')

# Supprimer Charlie s'il existe
existing = objects.execute_kw(db, uid, password,
    'res.users', 'search',
    [[['login', '=', 'charlie.test']]])
if existing:
    objects.execute_kw(db, uid, password,
        'res.users', 'unlink', [existing])
    print("🗑️  Charlie existant supprimé\n")

# Trouver Internal User group
group_ref = objects.execute_kw(db, uid, password,
    'ir.model.data', 'search_read',
    [[['module', '=', 'base'], ['name', '=', 'group_user']]],
    {'fields': ['res_id'], 'limit': 1})
group_id = group_ref[0]['res_id']

# Créer Charlie avec des valeurs TRÈS DIFFÉRENTES
user_data = {
    'login': 'charlie.test',              # Login court
    'name': 'Charlie Testing Person',     # Nom complet
    'email': 'charlie.testing@company.fr', # Email totalement différent du login !
    'active': True,
    'groups_id': [[6, 0, [group_id]]],
    'notification_type': 'inbox'
}

print("📝 Création de Charlie avec :")
print(f"   login: {user_data['login']}")
print(f"   name:  {user_data['name']}")
print(f"   email: {user_data['email']}")
print()

charlie_id = objects.execute_kw(db, uid, password,
    'res.users', 'create',
    [[user_data]])

if isinstance(charlie_id, list):
    charlie_id = charlie_id[0]

print(f"✅ Charlie créé, ID: {charlie_id}\n")

# Lire via API pour vérifier
charlie_read = objects.execute_kw(db, uid, password,
    'res.users', 'read',
    [[charlie_id]],
    {'fields': ['login', 'name', 'email', 'partner_id']})

print("📖 Lecture via API res.users :")
print(f"   login: {charlie_read[0]['login']}")
print(f"   name:  {charlie_read[0]['name']}")
print(f"   email: {charlie_read[0]['email']}")
print(f"   partner_id: {charlie_read[0]['partner_id']}")
print()

# Lire le partner directement
partner_id = charlie_read[0]['partner_id'][0]
partner_read = objects.execute_kw(db, uid, password,
    'res.partner', 'read',
    [[partner_id]],
    {'fields': ['name', 'email']})

print("📖 Lecture via API res.partner :")
print(f"   name:  {partner_read[0]['name']}")
print(f"   email: {partner_read[0]['email']}")
print()

# Vérif BDD
import subprocess
result = subprocess.run([
    'docker', 'exec', '-i', 'odoo-db', 'psql', '-U', 'odoo', '-d', 'odoo', '-c',
    f"""
    SELECT 
        u.id as user_id,
        u.login,
        u.partner_id,
        p.name as partner_name,
        p.email as partner_email
    FROM res_users u
    LEFT JOIN res_partner p ON u.partner_id = p.id
    WHERE u.login = 'charlie.test';
    """
], capture_output=True, text=True)

print("🗄️  Vérification PostgreSQL :")
print(result.stdout)

print("\n✅ Test terminé !")
print("🌐 Vérifier dans Odoo : http://localhost:8069")
print("   → Settings → Users → Charlie Testing Person")
print("   → Le champ Email doit afficher : charlie.testing@company.fr")
