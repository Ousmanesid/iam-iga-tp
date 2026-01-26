#!/bin/bash
#
# Script d'import automatique des ressources et rôles dans MidPoint
# Utilise l'API REST de MidPoint
#

MIDPOINT_URL="http://localhost:8080/midpoint"
MIDPOINT_USER="administrator"
MIDPOINT_PASS="5ecr3t"
CONFIG_DIR="/root/iam-iga-tp/config/midpoint"

# Couleurs pour les messages
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "=============================================="
echo "  Import automatique MidPoint via API REST"
echo "=============================================="

# Fonction pour attendre que MidPoint soit prêt
wait_for_midpoint() {
    echo -e "${YELLOW}Attente du démarrage de MidPoint...${NC}"
    max_attempts=60
    attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        response=$(curl -s -o /dev/null -w "%{http_code}" \
            -u "$MIDPOINT_USER:$MIDPOINT_PASS" \
            "$MIDPOINT_URL/ws/rest/self")
        
        if [ "$response" = "200" ]; then
            echo -e "${GREEN}✓ MidPoint est prêt!${NC}"
            return 0
        fi
        
        echo "  Tentative $attempt/$max_attempts (HTTP: $response)..."
        sleep 5
        attempt=$((attempt + 1))
    done
    
    echo -e "${RED}✗ MidPoint n'est pas accessible après $max_attempts tentatives${NC}"
    return 1
}

# Fonction pour importer un objet XML
import_object() {
    local file="$1"
    local name=$(basename "$file" .xml)
    
    if [ ! -f "$file" ]; then
        echo -e "${RED}  ✗ Fichier non trouvé: $file${NC}"
        return 1
    fi
    
    # Import avec option overwrite
    response=$(curl -s -w "\n%{http_code}" \
        -u "$MIDPOINT_USER:$MIDPOINT_PASS" \
        -H "Content-Type: application/xml" \
        -X POST \
        --data-binary "@$file" \
        "$MIDPOINT_URL/ws/rest/rpc/executeScript" \
        -d '<?xml version="1.0"?>
<s:executeScript xmlns:s="http://midpoint.evolveum.com/xml/ns/public/model/scripting-3">
    <s:expression>
        <s:action>
            <s:type>execute-script</s:type>
        </s:action>
    </s:expression>
</s:executeScript>')
    
    # Méthode alternative: import direct via l'endpoint objects
    response=$(curl -s -w "\n%{http_code}" \
        -u "$MIDPOINT_USER:$MIDPOINT_PASS" \
        -H "Content-Type: application/xml" \
        -X POST \
        --data-binary "@$file" \
        "$MIDPOINT_URL/ws/rest/objects?options=overwrite")
    
    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | sed '$d')
    
    if [ "$http_code" = "200" ] || [ "$http_code" = "201" ] || [ "$http_code" = "204" ]; then
        echo -e "${GREEN}  ✓ $name importé avec succès${NC}"
        return 0
    elif [ "$http_code" = "409" ]; then
        echo -e "${YELLOW}  ~ $name existe déjà, mise à jour...${NC}"
        # Essayer avec PUT pour mise à jour
        return 0
    else
        echo -e "${RED}  ✗ $name échec (HTTP $http_code)${NC}"
        echo "    Réponse: $body"
        return 1
    fi
}

# Fonction pour importer via le endpoint /rpc/importFromResource
import_xml_file() {
    local file="$1"
    local name=$(basename "$file" .xml)
    
    if [ ! -f "$file" ]; then
        echo -e "${RED}  ✗ Fichier non trouvé: $file${NC}"
        return 1
    fi
    
    # Utiliser l'API d'import avec overwrite
    response=$(curl -s -w "\n%{http_code}" \
        -u "$MIDPOINT_USER:$MIDPOINT_PASS" \
        -H "Content-Type: application/xml" \
        -X POST \
        --data-binary "@$file" \
        "$MIDPOINT_URL/api/model/objects?options=overwrite,raw")
    
    http_code=$(echo "$response" | tail -n1)
    
    if [ "$http_code" = "200" ] || [ "$http_code" = "201" ] || [ "$http_code" = "204" ] || [ "$http_code" = "409" ]; then
        echo -e "${GREEN}  ✓ $name${NC}"
        return 0
    else
        # Essayer avec l'ancien endpoint
        response=$(curl -s -w "\n%{http_code}" \
            -u "$MIDPOINT_USER:$MIDPOINT_PASS" \
            -H "Content-Type: application/xml" \
            -X POST \
            --data-binary "@$file" \
            "$MIDPOINT_URL/ws/rest/objects?options=overwrite")
        
        http_code=$(echo "$response" | tail -n1)
        
        if [ "$http_code" = "200" ] || [ "$http_code" = "201" ] || [ "$http_code" = "204" ] || [ "$http_code" = "409" ]; then
            echo -e "${GREEN}  ✓ $name${NC}"
            return 0
        else
            echo -e "${RED}  ✗ $name (HTTP $http_code)${NC}"
            return 1
        fi
    fi
}

# Attendre MidPoint
wait_for_midpoint || exit 1

echo ""
echo "=============================================="
echo "  Import des ressources"
echo "=============================================="

# Liste des ressources à importer (dans l'ordre)
RESOURCES=(
    "resources/resource-ldap.xml"
    "resources/resource-odoo.xml"
    "resources/resource-odoo-hr.xml"
    "resources/resource-hr-csv.xml"
    "resources/resource-homeapp-postgresql.xml"
    "resources/resource-intranet-csv.xml"
)

for res in "${RESOURCES[@]}"; do
    import_xml_file "$CONFIG_DIR/$res"
done

echo ""
echo "=============================================="
echo "  Import des rôles"
echo "=============================================="

# Liste des rôles à importer (dans l'ordre)
ROLES=(
    "roles/role-odoo-user.xml"
    "roles/role-odoo-finance.xml"
    "roles/role-odoo-admin.xml"
    "roles/role-employee.xml"
    "roles/role-agent-commercial.xml"
    "roles/role-comptable.xml"
    "roles/role-it-admin.xml"
    "roles/role-rh-manager.xml"
    "roles/role-homeapp-user.xml"
    "roles/role-homeapp-commercial.xml"
    "roles/role-homeapp-admin.xml"
)

for role in "${ROLES[@]}"; do
    import_xml_file "$CONFIG_DIR/$role"
done

echo ""
echo "=============================================="
echo "  Import de l'Object Template"
echo "=============================================="

import_xml_file "$CONFIG_DIR/object-templates/object-template-user.xml"

echo ""
echo "=============================================="
echo "  Import des tâches"
echo "=============================================="

TASKS=(
    "tasks/task-hr-import.xml"
    "tasks/task-odoo-hr-sync.xml"
)

for task in "${TASKS[@]}"; do
    import_xml_file "$CONFIG_DIR/$task"
done

echo ""
echo "=============================================="
echo "  Import terminé!"
echo "=============================================="
echo ""
echo "Accédez à MidPoint: $MIDPOINT_URL"
echo "Login: $MIDPOINT_USER / Mot de passe: $MIDPOINT_PASS"
echo ""
