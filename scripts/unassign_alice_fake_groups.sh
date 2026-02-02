#!/bin/bash
#
# Désassigne des faux groupes LDAP (cn numérique).
# Supprime tous les groupes à cn numérique (créés par MidPoint).
# À lancer EN SECOND après assign_alice_real_groups.sh.
# Utilisable pour tout utilisateur (Alice, John Doe, etc.) : même commande.
#

set -e

ADMIN_DN="cn=admin,dc=example,dc=com"
ADMIN_PASS="admin"
BASE_GROUPS="ou=groups,dc=example,dc=com"

echo "============================================================"
echo "➖ Supprimer les faux groupes LDAP (cn numérique)"
echo "============================================================"
echo

echo "🔍 Recherche des groupes à cn numérique..."
FAKE_CNS=$(docker exec openldap ldapsearch -x -H ldap://localhost \
    -b "$BASE_GROUPS" \
    -D "$ADMIN_DN" -w "$ADMIN_PASS" \
    -LLL "(objectClass=groupOfNames)" cn 2>/dev/null | \
    sed -n 's/^cn: *\([0-9][0-9]*\)$/\1/p' | sort -u)

if [ -z "$FAKE_CNS" ]; then
    echo "   Aucun faux groupe (cn numérique) trouvé."
    echo "============================================================"
    exit 0
fi

COUNT=$(echo "$FAKE_CNS" | wc -l)
echo "   Trouvé $COUNT faux groupe(s) à supprimer."
echo

for cn in $FAKE_CNS; do
    dn="cn=${cn},${BASE_GROUPS}"
    echo "➖ Suppression de $dn ..."
    if docker exec openldap ldapdelete -x -H ldap://localhost \
        -D "$ADMIN_DN" -w "$ADMIN_PASS" "$dn" 2>/dev/null; then
        echo "   ✅ Supprimé"
    else
        echo "   ⚠️  Échec ou déjà supprimé"
    fi
done

echo
echo "============================================================"
echo "✅ Faux groupes supprimés."
echo "============================================================"
echo "Ordre pour un nouvel utilisateur (ex. John Doe) :"
echo "  1. ./scripts/assign_alice_real_groups.sh john.doe   (assigner aux vrais groupes)"
echo "  2. ./scripts/unassign_alice_fake_groups.sh         (supprimer les faux groupes)"
echo
