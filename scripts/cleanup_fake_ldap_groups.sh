#!/bin/bash
#
# Supprime les "faux" groupes LDAP (cn numérique) créés par erreur
# à cause de la variable shell réservée GROUPS (GID).
# Garde uniquement les vrais groupes : Employee, Internet, Printer, etc.
#

set -e

ADMIN_DN="cn=admin,dc=example,dc=com"
ADMIN_PASS="admin"
BASE="ou=groups,dc=example,dc=com"

# Groupes légitimes à ne jamais supprimer
KEEP_GROUPS="Employee|Internet|Printer|Public_Share_Folder_SharePoint|crm-agents|rh-team|it-team|compta-team|marketing-team|AppBiz_"

echo "============================================================"
echo "🧹 Nettoyage des faux groupes LDAP (cn numérique)"
echo "============================================================"
echo

# Lister tous les groupes dont le cn est uniquement numérique
echo "🔍 Recherche des groupes à cn numérique..."
FAKE_CNS=$(docker exec openldap ldapsearch -x -H ldap://localhost \
    -b "$BASE" \
    -D "$ADMIN_DN" -w "$ADMIN_PASS" \
    -LLL "(objectClass=groupOfNames)" cn 2>/dev/null | \
    sed -n 's/^cn: *\([0-9][0-9]*\)$/\1/p' | sort -u)

if [ -z "$FAKE_CNS" ]; then
    echo "   Aucun faux groupe (cn numérique) trouvé."
    echo "============================================================"
    exit 0
fi

COUNT=$(echo "$FAKE_CNS" | wc -l)
echo "   Trouvé $COUNT groupe(s) à supprimer: $(echo $FAKE_CNS | tr '\n' ' ')"
echo

for cn in $FAKE_CNS; do
    dn="cn=${cn},${BASE}"
    echo "🗑️  Suppression de $dn ..."
    docker exec -i openldap ldapdelete -x -H ldap://localhost \
        -D "$ADMIN_DN" -w "$ADMIN_PASS" "$dn" 2>/dev/null && echo "   ✅ Supprimé" || echo "   ⚠️  Échec ou déjà supprimé"
done

echo
echo "============================================================"
echo "✅ Nettoyage terminé."
echo "   Groupes restants = vrais groupes (Employee, Internet, Printer, etc.)"
echo "============================================================"
echo
echo "🔍 Vérifier les groupes d'Alice (doit lister seulement les 4 vrais si elle y est):"
echo "   docker exec openldap ldapsearch -x -H ldap://localhost -b \"$BASE\" -D \"$ADMIN_DN\" -w admin \"(member=uid=alice.doe,ou=users,dc=example,dc=com)\" dn"
echo
