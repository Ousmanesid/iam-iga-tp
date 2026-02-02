#!/bin/bash
# ==============================================================================
# Odoo HR Export - Export des employés Odoo vers CSV normalisé pour MidPoint
# Usage: ./odoo_hr_export.sh [--docker] [--output FILE]
# ==============================================================================

set -e

# Détecter si on est en mode Docker ou local
USE_DOCKER=false
OUTPUT_FILE="/srv/projet/iam-iga-tp/data/hr/hr_clean.csv"

while [[ $# -gt 0 ]]; do
    case $1 in
        --docker) USE_DOCKER=true; shift ;;
        --output) OUTPUT_FILE="$2"; shift 2 ;;
        *) shift ;;
    esac
done

echo "🚀 Export HR Odoo → CSV"
echo "   Mode: $([ "$USE_DOCKER" = true ] && echo 'Docker' || echo 'Local')"
echo "   Output: $OUTPUT_FILE"

# Requête SQL pour extraire les employés avec format normalisé
SQL_QUERY="
SELECT 
    (e.id + 1000)::text AS \"personalNumber\",
    SPLIT_PART(e.name, ' ', 1) AS \"givenName\",
    CASE 
        WHEN POSITION(' ' IN e.name) > 0 
        THEN SUBSTRING(e.name FROM POSITION(' ' IN e.name) + 1)
        ELSE e.name
    END AS \"familyName\",
    COALESCE(e.work_email, '') AS \"email\",
    COALESCE(
        CASE 
            WHEN d.name LIKE '{%' THEN 
                TRIM(BOTH '\"' FROM (regexp_match(d.name::text, '\"en_US\":\\s*\"([^\"]+)\"'))[1])
            ELSE d.name
        END,
        'Unassigned'
    ) AS \"department\",
    COALESCE(e.job_title, 'Employee') AS \"title\",
    CASE 
        WHEN e.active = true THEN 'Active'
        ELSE 'Suspended'
    END AS \"status\"
FROM hr_employee e
LEFT JOIN hr_department d ON e.department_id = d.id
WHERE e.name IS NOT NULL AND e.name != ''
ORDER BY e.id;
"

# Créer le répertoire de sortie
mkdir -p "$(dirname "$OUTPUT_FILE")"

# Exécuter l'export selon le mode
if [ "$USE_DOCKER" = true ]; then
    # Via Docker exec
    docker exec odoo-db psql -U odoo -d odoo -t -A -F',' -c "
SELECT 
    (e.id + 1000)::text AS personalNumber,
    SPLIT_PART(e.name, ' ', 1) AS givenName,
    CASE 
        WHEN POSITION(' ' IN e.name) > 0 
        THEN SUBSTRING(e.name FROM POSITION(' ' IN e.name) + 1)
        ELSE e.name
    END AS familyName,
    COALESCE(e.work_email, '') AS email,
    COALESCE(d.name->>'en_US', 'Unassigned') AS department,
    COALESCE(e.job_title, 'Employee') AS title,
    CASE 
        WHEN e.active = true THEN 'Active'
        ELSE 'Suspended'
    END AS status
FROM hr_employee e
LEFT JOIN hr_department d ON e.department_id = d.id
WHERE e.name IS NOT NULL AND e.name != ''
ORDER BY e.id
" > "$OUTPUT_FILE.tmp"
    # Ajouter l'en-tête
    sed -i '1i personalNumber,givenName,familyName,email,department,title,status' "$OUTPUT_FILE.tmp"
else
    # Connexion directe (port exposé 5433)
    PGPASSWORD=odoo psql -h localhost -p 5433 -U odoo -d odoo -t -A -F',' -c "
SELECT 
    (e.id + 1000)::text AS personalNumber,
    SPLIT_PART(e.name, ' ', 1) AS givenName,
    CASE 
        WHEN POSITION(' ' IN e.name) > 0 
        THEN SUBSTRING(e.name FROM POSITION(' ' IN e.name) + 1)
        ELSE e.name
    END AS familyName,
    COALESCE(e.work_email, '') AS email,
    COALESCE(d.name->>'en_US', 'Unassigned') AS department,
    COALESCE(e.job_title, 'Employee') AS title,
    CASE 
        WHEN e.active = true THEN 'Active'
        ELSE 'Suspended'
    END AS status
FROM hr_employee e
LEFT JOIN hr_department d ON e.department_id = d.id
WHERE e.name IS NOT NULL AND e.name != ''
ORDER BY e.id
" > "$OUTPUT_FILE.tmp"
    # Ajouter l'en-tête
    sed -i '1i personalNumber,givenName,familyName,email,department,title,status' "$OUTPUT_FILE.tmp"
fi

# Vérifier et finaliser
if [ -s "$OUTPUT_FILE.tmp" ]; then
    mv "$OUTPUT_FILE.tmp" "$OUTPUT_FILE"
    EMPLOYEE_COUNT=$(($(wc -l < "$OUTPUT_FILE") - 1))
    echo "✅ Export réussi: $EMPLOYEE_COUNT employés"
    echo ""
    echo "📋 Aperçu du fichier:"
    head -5 "$OUTPUT_FILE"
else
    echo "❌ Erreur: Export vide"
    rm -f "$OUTPUT_FILE.tmp"
    exit 1
fi
