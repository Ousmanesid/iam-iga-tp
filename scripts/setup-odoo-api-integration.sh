#!/bin/bash
# Script pour préparer Odoo à l'intégration MidPoint via API XML-RPC

set -e

echo "🔧 Préparation d'Odoo pour l'intégration MidPoint via API XML-RPC"
echo ""

# 1. Nettoyer les vues et triggers SQL (ancienne solution)
echo "1️⃣  Nettoyage des vues et triggers SQL..."
docker exec -i odoo-db psql -U odoo -d odoo <<EOF
DROP VIEW IF EXISTS midpoint_users_view CASCADE;
DROP FUNCTION IF EXISTS midpoint_users_insert() CASCADE;
DROP FUNCTION IF EXISTS midpoint_users_update() CASCADE;
DROP FUNCTION IF EXISTS midpoint_users_delete() CASCADE;
DROP FUNCTION IF EXISTS sync_user_email_from_hr() CASCADE;
DROP TRIGGER IF EXISTS trg_sync_user_email_insert ON res_users;
DROP TRIGGER IF EXISTS trg_sync_user_email_update ON res_users;
SELECT 'Triggers et vues nettoyés' AS status;
EOF

echo "✅ Nettoyage terminé"
echo ""

# 2. Créer le compte technique midpoint_service dans Odoo
echo "2️⃣  Création du compte technique midpoint_service..."

# Vérifier si le compte existe déjà
EXISTING_USER=$(docker exec -i odoo-db psql -U odoo -d odoo -t -c "SELECT login FROM res_users WHERE login = 'midpoint_service';")

if [[ -z "${EXISTING_USER// }" ]]; then
    echo "Création du compte..."
    
    docker exec -i odoo-db psql -U odoo -d odoo <<EOF
-- 1. Créer le partner
INSERT INTO res_partner (name, email, company_id, active, is_company, create_date, write_date)
VALUES ('MidPoint Service Account', 'midpoint@example.com', 1, true, false, NOW(), NOW())
RETURNING id;

-- 2. Créer l'utilisateur avec le partner_id
WITH new_partner AS (
    SELECT id FROM res_partner WHERE email = 'midpoint@example.com' ORDER BY id DESC LIMIT 1
)
INSERT INTO res_users (login, partner_id, active, company_id, notification_type, password, create_date, write_date)
SELECT 'midpoint_service', id, true, 1, 'inbox', 'midpoint123', NOW(), NOW()
FROM new_partner
RETURNING id;

-- 3. Attribuer les groupes nécessaires (Settings + Access Rights)
WITH service_user AS (
    SELECT id FROM res_users WHERE login = 'midpoint_service' LIMIT 1
),
admin_group AS (
    SELECT g.id FROM res_groups g
    JOIN ir_model_data d ON d.res_id = g.id AND d.model = 'res.groups'
    WHERE d.name = 'group_system' AND d.module = 'base'
    LIMIT 1
)
INSERT INTO res_groups_users_rel (gid, uid)
SELECT admin_group.id, service_user.id
FROM service_user, admin_group
ON CONFLICT DO NOTHING;

SELECT 'Compte midpoint_service créé avec succès' AS status;
EOF

    echo "✅ Compte créé"
else
    echo "⚠️  Le compte midpoint_service existe déjà"
fi

echo ""

# 3. Copier les scripts Groovy dans le conteneur MidPoint
echo "3️⃣  Copie des scripts Groovy dans MidPoint..."

# Créer le répertoire dans le conteneur
docker exec midpoint mkdir -p /opt/midpoint/var/scripts/odoo

# Copier chaque script
for script in OdooHelper TestScript SchemaScript CreateScript UpdateScript DeleteScript SearchScript; do
    echo "  Copie de ${script}.groovy..."
    docker cp "$(pwd)/config/midpoint/scripts/odoo/${script}.groovy" midpoint:/opt/midpoint/var/scripts/odoo/
done

echo "✅ Scripts copiés"
echo ""

echo "✅ Configuration terminée !"
echo ""
echo "📝 Informations du compte technique :"
echo "   Login    : midpoint_service"
echo "   Password : midpoint123"
echo "   Groupes  : Administration/Settings"
echo ""
echo "🚀 Prochaines étapes :"
echo "   1. Importer la ressource resource-odoo-api.xml dans MidPoint"
echo "   2. Tester la connexion"
echo "   3. Réimporter le rôle Odoo_User"
echo "   4. Tester l'assignation du rôle à un utilisateur"
