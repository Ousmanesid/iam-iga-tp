#!/bin/bash
#
# Assigne un utilisateur aux 4 vrais groupes LDAP :
# Employee, Internet, Printer, Public_Share_Folder_SharePoint
# Usage : ./assign_alice_real_groups.sh [uid]
#   sans arg = alice.doe
#   ex. ./assign_alice_real_groups.sh john.doe  pour John Doe
# À lancer EN PREMIER, puis unassign_alice_fake_groups.sh
#

set -e

USER_UID="${1:-${USER_UID:-alice.doe}}"
USER_DN="uid=${USER_UID},ou=users,dc=example,dc=com"
ADMIN_DN="cn=admin,dc=example,dc=com"
ADMIN_PASS="admin"
BASE_GROUPS="ou=groups,dc=example,dc=com"

# Les 4 vrais groupes (ne pas utiliser la variable GROUPS = réservée shell)
REAL_GROUPS=(
    "Employee"
    "Internet"
    "Printer"
    "Public_Share_Folder_SharePoint"
)

echo "============================================================"
echo "➕ Assigner $USER_UID aux vrais groupes LDAP"
echo "============================================================"
echo "   Utilisateur : $USER_DN"
echo "   Groupes    : ${REAL_GROUPS[*]}"
echo "============================================================"
echo

for cn in "${REAL_GROUPS[@]}"; do
    group_dn="cn=${cn},${BASE_GROUPS}"
    echo "➕ Groupe $cn ..."

    if ! docker exec openldap ldapsearch -x -H ldap://localhost -b "$BASE_GROUPS" \
        -D "$ADMIN_DN" -w "$ADMIN_PASS" "(cn=${cn})" dn 2>/dev/null | grep -q "^dn:"; then
        echo "   Création du groupe puis ajout de $USER_UID..."
        docker exec -i openldap ldapadd -x -H ldap://localhost \
            -D "$ADMIN_DN" -w "$ADMIN_PASS" <<EOF
dn: $group_dn
objectClass: groupOfNames
cn: $cn
member: $USER_DN
EOF
        echo "   ✅ Groupe créé avec $USER_UID comme membre"
    else
        if docker exec openldap ldapsearch -x -H ldap://localhost -b "$group_dn" \
            -D "$ADMIN_DN" -w "$ADMIN_PASS" "(member=$USER_DN)" dn 2>/dev/null | grep -q "^dn:"; then
            echo "   ✅ $USER_UID est déjà membre"
        else
            docker exec -i openldap ldapmodify -x -H ldap://localhost \
                -D "$ADMIN_DN" -w "$ADMIN_PASS" <<EOF
dn: $group_dn
changetype: modify
add: member
member: $USER_DN
EOF
            echo "   ✅ $USER_UID ajouté au groupe"
        fi
    fi
done

echo
echo "============================================================"
echo "✅ $USER_UID est assigné aux 4 vrais groupes."
echo "============================================================"
echo "Ensuite : ./scripts/unassign_alice_fake_groups.sh (supprimer les faux groupes)"
echo "Vérification :"
echo "  docker exec openldap ldapsearch -x -H ldap://localhost -b \"$BASE_GROUPS\" -D \"$ADMIN_DN\" -w admin \"(member=$USER_DN)\" dn"
echo
