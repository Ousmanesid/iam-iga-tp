#!/bin/bash
#
# Script pour ajouter manuellement Alice Doe aux groupes LDAP
# et corriger le groupe 1053
#

echo "============================================================"
echo "🔧 Correction des groupes LDAP pour Alice Doe"
echo "============================================================"
echo

# Variables
ALICE_DN="uid=alice.doe,ou=users,dc=example,dc=com"
ADMIN_DN="cn=admin,dc=example,dc=com"
ADMIN_PASS="admin"

# Groupes à ajouter (ne pas utiliser GROUPS = variable réservée shell)
LDAP_GROUPS=(
    "Employee"
    "Internet"
    "Printer"
    "Public_Share_Folder_SharePoint"
)

echo "👤 Utilisateur: $ALICE_DN"
echo "📋 Groupes à attribuer: ${LDAP_GROUPS[@]}"
echo

# Fonction pour ajouter Alice à un groupe
add_to_group() {
    local group_name=$1
    local group_dn="cn=${group_name},ou=groups,dc=example,dc=com"
    
    echo "➕ Ajout d'Alice au groupe ${group_name}..."
    
    # Vérifier si le groupe existe
    docker exec -i openldap ldapsearch -x -H ldap://localhost \
        -b "ou=groups,dc=example,dc=com" \
        -D "$ADMIN_DN" -w "$ADMIN_PASS" \
        "(cn=${group_name})" dn 2>/dev/null | grep -q "^dn:"
    
    if [ $? -ne 0 ]; then
        echo "   ⚠️  Groupe $group_name n'existe pas, création..."
        
        # Créer le groupe
        docker exec -i openldap ldapadd -x -H ldap://localhost \
            -D "$ADMIN_DN" -w "$ADMIN_PASS" <<EOF
dn: $group_dn
objectClass: groupOfNames
cn: $group_name
member: $ALICE_DN
EOF
        echo "   ✅ Groupe créé avec Alice comme membre"
    else
        # Vérifier si Alice est déjà membre
        docker exec -i openldap ldapsearch -x -H ldap://localhost \
            -b "$group_dn" \
            -D "$ADMIN_DN" -w "$ADMIN_PASS" \
            "(member=$ALICE_DN)" 2>/dev/null | grep -q "numEntries: 1"
        
        if [ $? -eq 0 ]; then
            echo "   ✅ Alice est déjà membre"
        else
            # Ajouter Alice au groupe
            docker exec -i openldap ldapmodify -x -H ldap://localhost \
                -D "$ADMIN_DN" -w "$ADMIN_PASS" <<EOF
dn: $group_dn
changetype: modify
add: member
member: $ALICE_DN
EOF
            if [ $? -eq 0 ]; then
                echo "   ✅ Alice ajoutée au groupe"
            else
                echo "   ❌ Erreur lors de l'ajout"
            fi
        fi
    fi
    echo
}

# Corriger le groupe 1053 (remplacer cn=dummy par Alice)
echo "🔄 Correction du groupe cn=1053..."
docker exec -i openldap ldapmodify -x -H ldap://localhost \
    -D "$ADMIN_DN" -w "$ADMIN_PASS" <<EOF
dn: cn=1053,ou=groups,dc=example,dc=com
changetype: modify
delete: member
member: cn=dummy,ou=users,dc=example,dc=com
-
add: member
member: $ALICE_DN
EOF

if [ $? -eq 0 ]; then
    echo "✅ Groupe 1053 corrigé"
else
    echo "⚠️  Erreur lors de la modification du groupe 1053 (peut-être déjà corrigé)"
fi
echo

# Ajouter Alice à chaque groupe
for group in "${LDAP_GROUPS[@]}"; do
    add_to_group "$group"
done

echo "============================================================"
echo "✅ Opération terminée!"
echo "============================================================"
echo
echo "🔍 Vérification - Lister les groupes d'Alice:"
echo "   docker exec -it openldap ldapsearch -x -H ldap://localhost \\"
echo "     -b \"ou=groups,dc=example,dc=com\" \\"
echo "     -D \"cn=admin,dc=example,dc=com\" -w admin \\"
echo "     \"(member=uid=alice.doe,ou=users,dc=example,dc=com)\" dn"
echo
