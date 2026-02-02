#!/bin/bash
#
# Alice n'apparaît plus après l'import task car le shadow (projection) HR CSV
# reste orphelin après suppression du focus. Ce script :
# 1. Supprime tous les shadows de la ressource HR CSV (pour permettre la recréation)
# 2. Déclenche une tâche d'import pour que MidPoint recrée Alice depuis le CSV.
#
# Prérequis : Alice doit être dans data/hr/hr_clean.csv (ligne avec personalNumber 1053).
#

set -e

HR_CSV_RESOURCE_OID="8a83b1a4-be18-11e6-ae84-7301fdab1d7c"
MIDPOINT_URL="${MIDPOINT_URL:-http://localhost:8080/midpoint}"
MIDPOINT_USER="${MIDPOINT_USER:-administrator}"
MIDPOINT_PASS="${MIDPOINT_PASS:-Test5ecr3t}"

echo "============================================================"
echo "🔧 Réapparition d'Alice après import"
echo "============================================================"
echo

# 1. Supprimer les shadows HR CSV (en base MidPoint)
echo "1. Suppression des shadows de la ressource HR CSV (pour recréation à l'import)..."
PG_CONTAINER=$(docker ps --format '{{.Names}}' | grep -E 'midpoint_data|midpoint-data' | head -1)
if [ -z "$PG_CONTAINER" ]; then
    echo "   ⚠️  Conteneur Postgres MidPoint non trouvé. Tentative avec 'midpoint_data'..."
    PG_CONTAINER="midpoint_data"
fi

# Mot de passe Postgres MidPoint (docker-compose)
MP_DB_PASS="${MP_DB_PASSWORD:-db.secret.pw.007}"
if docker exec -e PGPASSWORD="$MP_DB_PASS" "$PG_CONTAINER" psql -U midpoint -d midpoint -t -c \
    "DELETE FROM m_shadow WHERE resourceRef_targetOid = '$HR_CSV_RESOURCE_OID';" 2>/dev/null; then
    echo "   ✅ Shadows HR CSV supprimés en base."
else
    echo "   ⚠️  Erreur SQL (vérifier que le conteneur Postgres MidPoint tourne et que la table m_shadow existe)."
    echo "   Vous pouvez lancer l'import manuellement dans MidPoint (Resources → HR CSV Source → Import)."
fi
echo

# 2. Lancer une tâche d'import
echo "2. Lancement d'une tâche d'import depuis HR CSV..."
TASK_XML="<?xml version=\"1.0\" encoding=\"UTF-8\"?>
<task xmlns=\"http://midpoint.evolveum.com/xml/ns/public/common/common-3\"
      xmlns:c=\"http://midpoint.evolveum.com/xml/ns/public/common/common-3\">
    <name>Manual HR CSV Import (fix Alice)</name>
    <extension>
        <mext:objectclass xmlns:mext=\"http://midpoint.evolveum.com/xml/ns/public/model/extension-3\">ri:AccountObjectClass</mext:objectclass>
    </extension>
    <ownerRef oid=\"00000000-0000-0000-0000-000000000002\" type=\"c:UserType\"/>
    <executionStatus>runnable</executionStatus>
    <category>ImportingAccounts</category>
    <handlerUri>http://midpoint.evolveum.com/xml/ns/public/model/synchronization/task/import/handler-3</handlerUri>
    <recurrence>single</recurrence>
    <objectRef oid=\"$HR_CSV_RESOURCE_OID\" type=\"c:ResourceType\"/>
</task>"

HTTP=$(curl -s -o /dev/null -w "%{http_code}" -u "${MIDPOINT_USER}:${MIDPOINT_PASS}" \
    -X POST \
    -H "Content-Type: application/xml" \
    -d "$TASK_XML" \
    "${MIDPOINT_URL}/ws/rest/tasks" 2>/dev/null || echo "000")

if [ "$HTTP" = "200" ] || [ "$HTTP" = "201" ]; then
    echo "   ✅ Tâche d'import créée et lancée."
else
    echo "   ⚠️  Réponse HTTP $HTTP. Lancez l'import manuellement :"
    echo "      MidPoint → Resources → HR CSV Source → Import"
fi
echo
echo "============================================================"
echo "✅ Terminé. Attendre quelques secondes puis :"
echo "   MidPoint → Users → List users → rechercher Alice ou 1053"
echo "============================================================"
