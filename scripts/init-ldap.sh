#!/bin/bash
# Script d'initialisation de la structure LDAP
# À exécuter après le démarrage d'OpenLDAP

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"
LDIF_FILE="$PROJECT_ROOT/config/ldap/bootstrap.ldif"

echo "🔧 Initialisation de la structure LDAP..."

# Attendre qu'OpenLDAP soit disponible
echo "⏳ Attente d'OpenLDAP sur localhost:10389..."
timeout=60
elapsed=0
while ! nc -z localhost 10389 > /dev/null 2>&1; do
    if [ $elapsed -ge $timeout ]; then
        echo "❌ Timeout: OpenLDAP n'est pas disponible"
        exit 1
    fi
    sleep 2
    elapsed=$((elapsed + 2))
done

echo "✅ OpenLDAP est disponible"
echo ""

# Vérifier si la structure existe déjà
if ldapsearch -x -H ldap://localhost:10389 -D "cn=admin,dc=example,dc=com" -w admin -b "ou=users,dc=example,dc=com" "(objectClass=*)" dn 2>/dev/null | grep -q "ou=users"; then
    echo "ℹ️  La structure LDAP existe déjà"
    echo "📋 Contenu actuel:"
    ldapsearch -x -H ldap://localhost:10389 -D "cn=admin,dc=example,dc=com" -w admin -b "dc=example,dc=com" "(objectClass=*)" dn
    exit 0
fi

echo "📝 Injection du fichier LDIF: $LDIF_FILE"
echo ""

# Injecter la structure de base
if ldapadd -x -H ldap://localhost:10389 -D "cn=admin,dc=example,dc=com" -w admin -f "$LDIF_FILE"; then
    echo ""
    echo "✅ Structure LDAP initialisée avec succès"
    echo ""
    echo "📋 Groupes créés:"
    ldapsearch -x -H ldap://localhost:10389 -D "cn=admin,dc=example,dc=com" -w admin -b "ou=groups,dc=example,dc=com" "(objectClass=groupOfNames)" cn
else
    echo ""
    echo "❌ Erreur lors de l'injection LDIF"
    exit 1
fi

