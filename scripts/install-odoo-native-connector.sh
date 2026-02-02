#!/bin/bash
#
# Script d'installation et test du connecteur Odoo natif pour MidPoint
#
set -e

echo "╔══════════════════════════════════════════════════════════════════════════════╗"
echo "║     Installation du Connecteur Odoo Natif (XML-RPC) pour MidPoint           ║"
echo "╚══════════════════════════════════════════════════════════════════════════════╝"

MIDPOINT_URL="http://localhost:8080/midpoint"
MIDPOINT_USER="administrator"
MIDPOINT_PASS="5ecr3t"
CONFIG_DIR="/srv/projet/iam-iga-tp/config/midpoint"

# Fonction pour importer un objet XML dans MidPoint
import_object() {
    local file=$1
    local type=$2
    local name=$(basename "$file" .xml)
    
    echo "  → Importing $type: $name"
    
    response=$(curl -s -w "\n%{http_code}" \
        -X POST \
        -H "Content-Type: application/xml" \
        -u "$MIDPOINT_USER:$MIDPOINT_PASS" \
        --data-binary "@$file" \
        "$MIDPOINT_URL/ws/rest/$type")
    
    http_code=$(echo "$response" | tail -1)
    body=$(echo "$response" | sed '$d')
    
    if [ "$http_code" = "200" ] || [ "$http_code" = "201" ] || [ "$http_code" = "409" ]; then
        echo "    ✅ Success (HTTP $http_code)"
        return 0
    else
        echo "    ⚠️  HTTP $http_code - Trying via add endpoint..."
        # Essayer avec l'endpoint alternatif
        response2=$(curl -s -w "\n%{http_code}" \
            -X POST \
            -H "Content-Type: application/xml" \
            -u "$MIDPOINT_USER:$MIDPOINT_PASS" \
            --data-binary "@$file" \
            "$MIDPOINT_URL/api/objects/$type")
        
        http_code2=$(echo "$response2" | tail -1)
        if [ "$http_code2" = "200" ] || [ "$http_code2" = "201" ] || [ "$http_code2" = "204" ]; then
            echo "    ✅ Success via API (HTTP $http_code2)"
            return 0
        else
            echo "    ❌ Failed (HTTP $http_code2)"
            return 1
        fi
    fi
}

# Vérifier que MidPoint est accessible
echo ""
echo "📡 Vérification de la connexion à MidPoint..."
if curl -s -o /dev/null -w "%{http_code}" -u "$MIDPOINT_USER:$MIDPOINT_PASS" "$MIDPOINT_URL/ws/rest/self" | grep -q "200\|302"; then
    echo "  ✅ MidPoint est accessible"
else
    echo "  ❌ MidPoint n'est pas accessible"
    exit 1
fi

# Vérifier que le connecteur Odoo est chargé
echo ""
echo "🔌 Vérification du connecteur Odoo..."
if docker exec midpoint grep -q "lu.lns.connector.odoo" /opt/midpoint/var/log/midpoint.log 2>/dev/null; then
    echo "  ✅ Connecteur Odoo natif détecté"
else
    echo "  ⚠️  Connecteur Odoo non trouvé dans les logs"
fi

# Importer la ressource Odoo Native
echo ""
echo "📦 Import de la ressource Odoo Native..."
if [ -f "$CONFIG_DIR/resources/resource-odoo-native.xml" ]; then
    import_object "$CONFIG_DIR/resources/resource-odoo-native.xml" "resources"
else
    echo "  ❌ Fichier resource-odoo-native.xml non trouvé"
fi

# Importer le rôle Odoo_User_Native
echo ""
echo "👤 Import du rôle Odoo_User_Native..."
if [ -f "$CONFIG_DIR/roles/role-odoo-user-native.xml" ]; then
    import_object "$CONFIG_DIR/roles/role-odoo-user-native.xml" "roles"
else
    echo "  ❌ Fichier role-odoo-user-native.xml non trouvé"
fi

# Importer le rôle Employee_v2
echo ""
echo "👥 Import du rôle Employee_v2..."
if [ -f "$CONFIG_DIR/roles/role-employee-v2.xml" ]; then
    import_object "$CONFIG_DIR/roles/role-employee-v2.xml" "roles"
else
    echo "  ❌ Fichier role-employee-v2.xml non trouvé"
fi

# Test de connexion à la ressource Odoo
echo ""
echo "🧪 Test de connexion à la ressource Odoo Native..."
test_result=$(curl -s \
    -X POST \
    -H "Content-Type: application/xml" \
    -u "$MIDPOINT_USER:$MIDPOINT_PASS" \
    "$MIDPOINT_URL/ws/rest/resources/8a83b1a4-be18-11e6-ae84-7301fdab1d99/test" 2>/dev/null || echo "FAILED")

if echo "$test_result" | grep -qi "success\|ok"; then
    echo "  ✅ Connexion à Odoo réussie!"
else
    echo "  ⚠️  Test de connexion - Vérifiez dans l'interface MidPoint"
    echo "     URL: $MIDPOINT_URL"
    echo "     Resource: Odoo ERP (Native RPC)"
fi

echo ""
echo "╔══════════════════════════════════════════════════════════════════════════════╗"
echo "║  Installation terminée                                                        ║"
echo "╠══════════════════════════════════════════════════════════════════════════════╣"
echo "║                                                                               ║"
echo "║  Prochaines étapes:                                                           ║"
echo "║  1. Ouvrir MidPoint: http://localhost:8080/midpoint                          ║"
echo "║  2. Aller dans Resources → Odoo ERP (Native RPC) → Test Connection           ║"
echo "║  3. Si OK, vérifier Schema pour voir les modèles Odoo                        ║"
echo "║  4. Créer un utilisateur et lui assigner le rôle Employee_v2                 ║"
echo "║  5. Vérifier que le compte est créé dans Odoo                                ║"
echo "║                                                                               ║"
echo "╚══════════════════════════════════════════════════════════════════════════════╝"
