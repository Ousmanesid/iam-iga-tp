#!/bin/bash
# Script pour déclencher le webhook manuellement
# Usage: ./trigger_webhook.sh <event> <employee_id> <name> <email> <job_title>

EVENT="${1:-create}"
EMPLOYEE_ID="${2:-99}"
NAME="${3:-Jean Dupont}"
EMAIL="${4:-jean.dupont@example.com}"
JOB_TITLE="${5:-Employee}"
GATEWAY_URL="${GATEWAY_URL:-http://localhost:8000/api/v1/odoo/webhook}"

echo "🔔 Webhook Event: $EVENT"
echo "👤 Employee ID: $EMPLOYEE_ID"
echo "📧 Name: $NAME"
echo "💼 Email: $EMAIL"
echo ""

curl -X POST "$GATEWAY_URL" \
  -H "Content-Type: application/json" \
  -d "{
    \"event\": \"$EVENT\",
    \"employee_id\": $EMPLOYEE_ID,
    \"data\": {
      \"name\": \"$NAME\",
      \"work_email\": \"$EMAIL\",
      \"job_title\": \"$JOB_TITLE\"
    }
  }"

echo ""
echo "✅ CSV updated. Last line:"
tail -1 /srv/projet/iam-iga-tp/data/hr/hr_clean.csv || echo "File not found"
