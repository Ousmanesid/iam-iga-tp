#!/bin/bash
# Script pour importer les ressources et rôles MidPoint

MIDPOINT_URL="${MIDPOINT_URL:-http://localhost:8080/midpoint/ws/rest}"
MIDPOINT_USER="${MIDPOINT_USER:-administrator}"
MIDPOINT_PASSWORD="${MIDPOINT_PASSWORD:-5ecr3t}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "============================================================"
echo "  Import MidPoint Resources and Roles"
echo "============================================================"
echo ""

# Fonction pour importer un fichier XML
import_xml() {
    local file=$1
    local type=$2
    
    if [ ! -f "$file" ]; then
        echo "✗ Fichier non trouvé: $file"
        return 1
    fi
    
    echo "→ Import: $(basename $file)"
    
    response=$(curl -s -w "\n%{http_code}" -u "$MIDPOINT_USER:$MIDPOINT_PASSWORD" \
        -X POST \
        "$MIDPOINT_URL/$type" \
        -H "Content-Type: application/xml" \
        -d @"$file" 2>/dev/null)
    
    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | sed '$d')
    
    if [ "$http_code" = "200" ] || [ "$http_code" = "201" ] || [ "$http_code" = "204" ]; then
        echo "  ✓ Import réussi"
        return 0
    elif echo "$body" | grep -q "already exists"; then
        echo "  → Déjà existant, mise à jour..."
        # Essayer de mettre à jour
        oid=$(grep -oP 'oid="[^"]+"' "$file" | head -1 | cut -d'"' -f2)
        if [ -n "$oid" ]; then
            update_response=$(curl -s -w "\n%{http_code}" -u "$MIDPOINT_USER:$MIDPOINT_PASSWORD" \
                -X PUT \
                "$MIDPOINT_URL/$type/$oid" \
                -H "Content-Type: application/xml" \
                -d @"$file" 2>/dev/null)
            update_code=$(echo "$update_response" | tail -n1)
            if [ "$update_code" = "200" ] || [ "$update_code" = "204" ]; then
                echo "  ✓ Mise à jour réussie"
                return 0
            fi
        fi
        echo "  → Existe déjà (ignoré)"
        return 0
    else
        echo "  ✗ Erreur HTTP $http_code"
        echo "$body" | head -20
        return 1
    fi
}

# Importer les ressources
echo "=== Import des ressources ==="
RESOURCES_DIR="$PROJECT_ROOT/config/midpoint/resources"
for file in "$RESOURCES_DIR"/resource-*.xml; do
    if [ -f "$file" ]; then
        import_xml "$file" "resources"
    fi
done

echo ""
echo "=== Import des rôles ==="
ROLES_DIR="$PROJECT_ROOT/config/midpoint/roles"
for file in "$ROLES_DIR"/role-*.xml; do
    if [ -f "$file" ]; then
        import_xml "$file" "roles"
    fi
done

echo ""
echo "============================================================"
echo "  Import terminé"
echo "============================================================"
