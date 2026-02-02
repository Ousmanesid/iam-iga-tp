#!/bin/bash
#
# Supprime Alice Doe de LDAP et de MidPoint.
# 1. LDAP : retire Alice de tous les groupes puis supprime l'entrée utilisateur.
# 2. MidPoint : trouve l'utilisateur (fullName/nom) et le supprime via l'API REST.
#

set -e

ALICE_DN="uid=alice.doe,ou=users,dc=example,dc=com"
DUMMY_DN="cn=dummy,ou=users,dc=example,dc=com"
ADMIN_DN="cn=admin,dc=example,dc=com"
ADMIN_PASS="admin"
BASE_GROUPS="ou=groups,dc=example,dc=com"

MIDPOINT_URL="${MIDPOINT_URL:-http://localhost:8080/midpoint}"
MIDPOINT_USER="${MIDPOINT_USER:-administrator}"
MIDPOINT_PASS="${MIDPOINT_PASS:-Test5ecr3t}"

echo "============================================================"
echo "🗑️  Suppression d'Alice Doe (LDAP + MidPoint)"
echo "============================================================"
echo

# ---------- 1. LDAP : groupes dont Alice est membre ----------
echo "🔍 LDAP : recherche des groupes dont Alice est membre..."
GROUP_DNS=$(docker exec openldap ldapsearch -x -H ldap://localhost \
    -b "$BASE_GROUPS" \
    -D "$ADMIN_DN" -w "$ADMIN_PASS" \
    -LLL "(member=$ALICE_DN)" dn 2>/dev/null | sed -n 's/^dn: *//p' || true)

if [ -n "$GROUP_DNS" ]; then
    echo "$GROUP_DNS" | while IFS= read -r group_dn; do
        [ -z "$group_dn" ] && continue
        echo "   ➖ Retrait d'Alice du groupe $group_dn ..."
        # Compter les membres : si seul Alice, ajouter dummy puis retirer Alice
        MEMBER_COUNT=$(docker exec openldap ldapsearch -x -H ldap://localhost \
            -b "$group_dn" -D "$ADMIN_DN" -w "$ADMIN_PASS" -LLL member 2>/dev/null | grep -c "^member:" || echo 0)
        if [ "$MEMBER_COUNT" -le 1 ]; then
            # groupOfNames exige au moins 1 membre : ajouter cn=dummy (doit exister dans ou=users)
            docker exec -i openldap ldapmodify -x -H ldap://localhost \
                -D "$ADMIN_DN" -w "$ADMIN_PASS" <<EOF 2>/dev/null || true
dn: $group_dn
changetype: modify
add: member
member: $DUMMY_DN
EOF
        fi
        docker exec -i openldap ldapmodify -x -H ldap://localhost \
            -D "$ADMIN_DN" -w "$ADMIN_PASS" <<EOF 2>/dev/null || true
dn: $group_dn
changetype: modify
delete: member
member: $ALICE_DN
EOF
        echo "   ✅ Alice retirée de $group_dn"
    done
else
    echo "   Aucun groupe trouvé avec Alice comme membre."
fi
echo

# ---------- 2. LDAP : suppression de l'entrée utilisateur ----------
echo "🗑️  LDAP : suppression de l'entrée $ALICE_DN ..."
if docker exec openldap ldapdelete -x -H ldap://localhost \
    -D "$ADMIN_DN" -w "$ADMIN_PASS" "$ALICE_DN" 2>/dev/null; then
    echo "   ✅ Alice supprimée de LDAP."
else
    echo "   ⚠️  Entrée déjà absente ou erreur (vérifier que cn=dummy existe si des groupes la référençaient)."
fi
echo

# ---------- 3. MidPoint : trouver et supprimer l'utilisateur ----------
echo "🔍 MidPoint : recherche d'Alice (search=alice)..."
RESPONSE=$(curl -s -u "${MIDPOINT_USER}:${MIDPOINT_PASS}" \
    -H "Accept: application/xml" \
    "${MIDPOINT_URL}/ws/rest/users?search=alice" 2>/dev/null || true)

# OID du premier apti:object (utilisateur) dans la réponse, pas les refs
OID=$(echo "$RESPONSE" | grep -E 'apti:object oid=|object oid=.*UserType' | head -1 | grep -oP 'oid="[a-f0-9-]+"' | sed 's/oid="//;s/"//')
if [ -z "$OID" ]; then
    OID=$(echo "$RESPONSE" | grep -oP 'oid="[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}"' | head -1 | sed 's/oid="//;s/"//')
fi

if [ -n "$OID" ]; then
    echo "   Utilisateur trouvé (OID: $OID). Suppression..."
    HTTP=$(curl -s -o /dev/null -w "%{http_code}" -u "${MIDPOINT_USER}:${MIDPOINT_PASS}" \
        -X DELETE "${MIDPOINT_URL}/ws/rest/users/${OID}" 2>/dev/null || echo "000")
    if [ "$HTTP" = "204" ] || [ "$HTTP" = "200" ]; then
        echo "   ✅ Alice supprimée de MidPoint."
    else
        echo "   ⚠️  MidPoint a répondu HTTP $HTTP pour DELETE /users/$OID"
    fi
else
    echo "   ⚠️  Aucun utilisateur 'Alice' trouvé dans MidPoint. Suppression manuelle si besoin."
fi

echo
echo "============================================================"
echo "✅ Terminé. Alice supprimée de LDAP et (si trouvée) de MidPoint."
echo "============================================================"
