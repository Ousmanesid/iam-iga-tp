#!/bin/bash
#
# Import lent des objets MidPoint pour éviter le rate limiting
# Pause de 10 secondes entre chaque import
#

MIDPOINT_URL="http://localhost:8080/midpoint"
USER="administrator"
PASS="5ecr3t"
BASE_DIR="/root/iam-iga-tp/config/midpoint"

# Couleurs
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "=========================================="
echo "Import lent des objets MidPoint"
echo "Pause de 10s entre chaque import"
echo "=========================================="
echo ""

# Attendre que MidPoint soit prêt
echo "Attente de MidPoint..."
for i in {1..40}; do
    STATUS=$(docker inspect --format='{{.State.Health.Status}}' midpoint 2>/dev/null)
    if [ "$STATUS" = "healthy" ]; then
        echo -e "${GREEN}✓ MidPoint est prêt${NC}"
        break
    fi
    echo -n "."
    sleep 5
done
echo ""

# Fonction d'import avec retry
import_file() {
    local FILE=$1
    local TYPE=$2
    local ENDPOINT=$3
    
    echo ""
    echo "→ Import de $(basename $FILE)..."
    
    # Tentative 1
    HTTP_CODE=$(curl -s -o /tmp/response.xml -w "%{http_code}" \
        -X POST \
        -H "Content-Type: application/xml" \
        -u "$USER:$PASS" \
        --data-binary @"$FILE" \
        "$MIDPOINT_URL/ws/rest/$ENDPOINT")
    
    if [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "201" ] || [ "$HTTP_CODE" = "204" ]; then
        echo -e "${GREEN}  ✓ Importé avec succès (HTTP $HTTP_CODE)${NC}"
        return 0
    elif [ "$HTTP_CODE" = "409" ]; then
        echo -e "${YELLOW}  ⚠ Objet existe déjà, tentative de mise à jour...${NC}"
        # Extraire l'OID du fichier XML
        OID=$(grep -oP 'oid="[^"]+' "$FILE" | head -1 | cut -d'"' -f2)
        if [ -n "$OID" ]; then
            HTTP_CODE=$(curl -s -o /tmp/response.xml -w "%{http_code}" \
                -X PUT \
                -H "Content-Type: application/xml" \
                -u "$USER:$PASS" \
                --data-binary @"$FILE" \
                "$MIDPOINT_URL/ws/rest/$ENDPOINT/$OID")
            
            if [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "201" ] || [ "$HTTP_CODE" = "204" ]; then
                echo -e "${GREEN}  ✓ Mis à jour avec succès (HTTP $HTTP_CODE)${NC}"
                return 0
            fi
        fi
    fi
    
    echo -e "${RED}  ✗ Échec (HTTP $HTTP_CODE)${NC}"
    [ -f /tmp/response.xml ] && head -5 /tmp/response.xml | sed 's/^/    /'
    return 1
}

# Compteurs
TOTAL=0
SUCCESS=0
FAILED=0

# 1. Import des ressources
echo ""
echo "====== 1. RESSOURCES ======"
for FILE in "$BASE_DIR/resources"/*.xml; do
    [ -f "$FILE" ] || continue
    TOTAL=$((TOTAL + 1))
    if import_file "$FILE" "resource" "resources"; then
        SUCCESS=$((SUCCESS + 1))
    else
        FAILED=$((FAILED + 1))
    fi
    echo "Pause de 10 secondes..."
    sleep 10
done

# 2. Import des rôles
echo ""
echo "====== 2. RÔLES ======"
for FILE in "$BASE_DIR/roles"/*.xml; do
    [ -f "$FILE" ] || continue
    TOTAL=$((TOTAL + 1))
    if import_file "$FILE" "role" "roles"; then
        SUCCESS=$((SUCCESS + 1))
    else
        FAILED=$((FAILED + 1))
    fi
    echo "Pause de 10 secondes..."
    sleep 10
done

# 3. Import des object templates
echo ""
echo "====== 3. OBJECT TEMPLATES ======"
for FILE in "$BASE_DIR/object-templates"/*.xml; do
    [ -f "$FILE" ] || continue
    TOTAL=$((TOTAL + 1))
    if import_file "$FILE" "objectTemplate" "objectTemplates"; then
        SUCCESS=$((SUCCESS + 1))
    else
        FAILED=$((FAILED + 1))
    fi
    echo "Pause de 10 secondes..."
    sleep 10
done

# 4. Import des tâches
echo ""
echo "====== 4. TÂCHES ======"
for FILE in "$BASE_DIR/tasks"/*.xml; do
    [ -f "$FILE" ] || continue
    TOTAL=$((TOTAL + 1))
    if import_file "$FILE" "task" "tasks"; then
        SUCCESS=$((SUCCESS + 1))
    else
        FAILED=$((FAILED + 1))
    fi
    echo "Pause de 10 secondes..."
    sleep 10
done

# Résumé
echo ""
echo "=========================================="
echo "RÉSUMÉ"
echo "=========================================="
echo -e "Total:   $TOTAL objets"
echo -e "${GREEN}Succès:  $SUCCESS${NC}"
echo -e "${RED}Échecs:  $FAILED${NC}"
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}🎉 Tous les objets ont été importés !${NC}"
    exit 0
else
    echo -e "${YELLOW}⚠️  Certains objets n'ont pas pu être importés${NC}"
    exit 1
fi
