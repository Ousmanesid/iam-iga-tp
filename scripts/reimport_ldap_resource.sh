#!/bin/bash
#
# Réimporte la ressource OpenLDAP dans MidPoint via l'API REST (Pi REST).
# Utilise le fichier resource-ldap.xml mis à jour (attribut member pour groupOfNames).
#

set -e

MIDPOINT_URL="${MIDPOINT_URL:-http://localhost:8080/midpoint}"
MIDPOINT_USER="${MIDPOINT_USER:-administrator}"
MIDPOINT_PASS="${MIDPOINT_PASS:-Test5ecr3t}"

RESOURCE_FILE="/srv/projet/iam-iga-tp/config/midpoint/resources/resource-ldap.xml"
RESOURCE_OID="8a83b1a4-be18-11e6-ae84-7301fdab1d7d"

echo "============================================================"
echo "🔄 Réimport ressource OpenLDAP dans MidPoint (REST)"
echo "============================================================"
echo "   URL  : $MIDPOINT_URL"
echo "   User : $MIDPOINT_USER"
echo "   Fichier : $RESOURCE_FILE"
echo "============================================================"
echo

if [ ! -f "$RESOURCE_FILE" ]; then
    echo "❌ Fichier non trouvé: $RESOURCE_FILE"
    exit 1
fi

echo "📤 Mise à jour de la ressource OpenLDAP (PUT /ws/rest/resources/${RESOURCE_OID})..."

response=$(curl -s -w "\n%{http_code}" -u "${MIDPOINT_USER}:${MIDPOINT_PASS}" \
    -X PUT \
    -H "Content-Type: application/xml" \
    --data-binary "@${RESOURCE_FILE}" \
    "${MIDPOINT_URL}/ws/rest/resources/${RESOURCE_OID}" 2>&1)

http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | head -n-1)

if [ "$http_code" = "204" ] || [ "$http_code" = "200" ] || [ "$http_code" = "201" ]; then
    echo "   ✅ Ressource mise à jour / créée avec succès (HTTP $http_code)"
else
    echo "   ❌ Erreur (HTTP $http_code)"
    echo "$body" | head -40
    exit 1
fi

echo
echo "============================================================"
echo "✅ Terminé. La ressource OpenLDAP a le schéma à jour (member pour groupOfNames)."
echo "   Vous pouvez réessayer d’ajouter un assignement dans MidPoint."
echo "============================================================"
