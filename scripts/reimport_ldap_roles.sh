#!/bin/bash
#
# Script pour réimporter les rôles LDAP corrigés dans MidPoint
#

echo "============================================================"
echo "🔄 Réimport des rôles LDAP corrigés dans MidPoint"
echo "============================================================"
echo

MIDPOINT_URL="http://localhost:8080/midpoint"
MIDPOINT_USER="administrator"
MIDPOINT_PASS="Test5ecr3t"

ROLES_DIR="/srv/projet/iam-iga-tp/config/midpoint/roles"

# Liste des rôles à réimporter
ROLES=(
    "role-ldap-employee.xml"
    "role-ldap-internet.xml"
    "role-ldap-printer.xml"
    "role-ldap-sharepoint.xml"
)

echo "📋 Rôles à mettre à jour:"
for role in "${ROLES[@]}"; do
    echo "   - $role"
done
echo

# Fonction pour importer un rôle
import_role() {
    local role_file=$1
    local role_path="${ROLES_DIR}/${role_file}"
    
    if [ ! -f "$role_path" ]; then
        echo "   ❌ Fichier non trouvé: $role_path"
        return 1
    fi
    
    echo "➕ Import de $role_file..."
    
    # Utiliser curl pour uploader le XML
    response=$(curl -s -w "\n%{http_code}" -u "${MIDPOINT_USER}:${MIDPOINT_PASS}" \
        -X POST \
        -H "Content-Type: application/xml" \
        --data-binary "@${role_path}" \
        "${MIDPOINT_URL}/ws/rest/roles" 2>&1)
    
    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | head -n-1)
    
    if [ "$http_code" = "201" ] || [ "$http_code" = "200" ]; then
        echo "   ✅ Importé avec succès (HTTP $http_code)"
    elif [ "$http_code" = "409" ]; then
        echo "   ⚠️  Rôle existe déjà, mise à jour..."
        
        # Extraire l'OID du fichier XML
        oid=$(grep -oP 'oid="[^"]+"' "$role_path" | head -1 | cut -d'"' -f2)
        
        if [ -z "$oid" ]; then
            echo "   ❌ Impossible de trouver l'OID dans $role_file"
            return 1
        fi
        
        # Mettre à jour le rôle existant
        response=$(curl -s -w "\n%{http_code}" -u "${MIDPOINT_USER}:${MIDPOINT_PASS}" \
            -X PUT \
            -H "Content-Type: application/xml" \
            --data-binary "@${role_path}" \
            "${MIDPOINT_URL}/ws/rest/roles/${oid}" 2>&1)
        
        http_code=$(echo "$response" | tail -n1)
        
        if [ "$http_code" = "204" ] || [ "$http_code" = "200" ]; then
            echo "   ✅ Mis à jour avec succès (HTTP $http_code)"
        else
            echo "   ❌ Erreur lors de la mise à jour (HTTP $http_code)"
            echo "$response" | head -n-1 | head -20
            return 1
        fi
    else
        echo "   ❌ Erreur lors de l'import (HTTP $http_code)"
        echo "$body" | head -20
        return 1
    fi
    
    echo
}

# Importer tous les rôles
success_count=0
fail_count=0

for role in "${ROLES[@]}"; do
    if import_role "$role"; then
        ((success_count++))
    else
        ((fail_count++))
    fi
done

echo "============================================================"
echo "📊 Résumé:"
echo "   ✅ Succès: $success_count"
echo "   ❌ Échecs: $fail_count"
echo "============================================================"
echo
echo "🔄 Prochaines étapes:"
echo "   1. Aller dans MidPoint → Users → Alice Doe"
echo "   2. Supprimer l'assignement Employee actuel"
echo "   3. Réassigner le rôle Employee (nouveau)"
echo "   4. Save et attendre le recompute"
echo "   5. Vérifier les groupes LDAP:"
echo "      docker exec -it openldap ldapsearch -x -H ldap://localhost \\"
echo "        -b \"ou=groups,dc=example,dc=com\" \\"
echo "        -D \"cn=admin,dc=example,dc=com\" -w admin \\"
echo "        \"(member=uid=alice.doe,ou=users,dc=example,dc=com)\" dn"
echo

if [ $fail_count -eq 0 ]; then
    exit 0
else
    exit 1
fi
