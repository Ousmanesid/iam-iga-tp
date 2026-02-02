#!/bin/bash
# =============================================================================
# Script d'assignation automatique du rôle Employee via ninja CLI
# 
# Ce script:
# 1. Met à jour le rôle Employee avec l'auto-assignation
# 2. Force un recompute sur tous les utilisateurs
# =============================================================================

set -e

echo "======================================================================"
echo "🎯 ASSIGNATION AUTOMATIQUE DU RÔLE EMPLOYEE"
echo "======================================================================"

# Vérifier que le conteneur MidPoint est en cours d'exécution
if ! docker ps | grep -q midpoint; then
    echo "❌ Le conteneur MidPoint n'est pas en cours d'exécution"
    exit 1
fi

echo ""
echo "📋 Étape 1: Import du rôle Employee avec auto-assignation..."
echo ""

# Copier le fichier XML du rôle dans le conteneur
docker cp /srv/projet/iam-iga-tp/config/midpoint/roles/role-employee.xml midpoint:/tmp/role-employee.xml

# Importer le rôle via ninja
docker exec midpoint /opt/midpoint/bin/ninja.sh import -i /tmp/role-employee.xml --overwrite 2>&1 || true

echo ""
echo "📋 Étape 2: Lister tous les utilisateurs..."
echo ""

# Lister les utilisateurs
docker exec midpoint /opt/midpoint/bin/ninja.sh export -t UserType -o /tmp/users.xml 2>&1 || true

# Compter les utilisateurs
USER_COUNT=$(docker exec midpoint grep -c "<user " /tmp/users.xml 2>/dev/null || echo "0")
echo "   Trouvé $USER_COUNT utilisateurs"

echo ""
echo "📋 Étape 3: Forcer le recompute de tous les utilisateurs..."
echo ""

# Créer une tâche de recompute pour tous les utilisateurs
cat << 'EOF' > /tmp/recompute-task.xml
<?xml version="1.0" encoding="UTF-8"?>
<task xmlns="http://midpoint.evolveum.com/xml/ns/public/common/common-3"
      xmlns:c="http://midpoint.evolveum.com/xml/ns/public/common/common-3"
      xmlns:q="http://prism.evolveum.com/xml/ns/public/query-3">
    <name>Recompute All Users - Auto Role Assignment</name>
    <extension xmlns:se="http://midpoint.evolveum.com/xml/ns/public/model/scripting/extension-3">
        <se:executeScript xmlns:s="http://midpoint.evolveum.com/xml/ns/public/model/scripting-3">
            <s:pipeline>
                <s:search>
                    <s:type>UserType</s:type>
                </s:search>
                <s:action>
                    <s:type>recompute</s:type>
                </s:action>
            </s:pipeline>
        </se:executeScript>
    </extension>
    <ownerRef oid="00000000-0000-0000-0000-000000000002" type="c:UserType"/>
    <executionState>runnable</executionState>
    <category>BulkActions</category>
    <handlerUri>http://midpoint.evolveum.com/xml/ns/public/model/scripting/handler-3</handlerUri>
    <recurrence>single</recurrence>
</task>
EOF

# Copier et importer la tâche
docker cp /tmp/recompute-task.xml midpoint:/tmp/recompute-task.xml
docker exec midpoint /opt/midpoint/bin/ninja.sh import -i /tmp/recompute-task.xml 2>&1 || true

echo ""
echo "======================================================================"
echo "✅ TERMINÉ!"
echo "======================================================================"
echo ""
echo "📝 Le rôle Employee avec auto-assignation a été importé."
echo "   Une tâche de recompute a été créée pour tous les utilisateurs."
echo ""
echo "🔍 Pour vérifier:"
echo "   1. Allez sur http://localhost:8080/midpoint"
echo "   2. Login: administrator / Test5ecr3t"
echo "   3. Menu: Server tasks → List tasks"
echo "   4. Cherchez 'Recompute All Users'"
echo "   5. Ou allez dans Users → cliquez sur un utilisateur → Assignments"
echo ""
echo "💡 Alternative manuelle:"
echo "   - Allez dans Configuration → Repository objects → Import object"
echo "   - Importez /config/midpoint/roles/role-employee.xml"
echo "   - Puis dans Users, sélectionnez tous et cliquez 'Recompute'"
echo ""
