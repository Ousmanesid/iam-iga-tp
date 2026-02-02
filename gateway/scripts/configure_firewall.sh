#!/bin/bash
# Script de configuration automatique du pare-feu Google Cloud
# À exécuter depuis votre PC LOCAL (pas la VM)

set -e

echo "🔥 Configuration du pare-feu Google Cloud pour Aegis Gateway"
echo "============================================================"

# Variables
PROJECT_ID=$(gcloud config get-value project)
NETWORK="default"

echo "📋 Projet détecté: $PROJECT_ID"
echo ""

# Règle Frontend (Port 5174)
echo "⏳ Création de la règle pour le Frontend (port 5174)..."
gcloud compute firewall-rules create allow-aegis-frontend \
    --project=$PROJECT_ID \
    --direction=INGRESS \
    --priority=1000 \
    --network=$NETWORK \
    --action=ALLOW \
    --rules=tcp:5174 \
    --source-ranges=0.0.0.0/0 \
    --description="Allow access to Aegis Gateway Frontend" \
    --quiet

echo "✅ Règle Frontend créée"
echo ""

# Règle Backend (Port 8001)
echo "⏳ Création de la règle pour le Backend (port 8001)..."
gcloud compute firewall-rules create allow-aegis-backend \
    --project=$PROJECT_ID \
    --direction=INGRESS \
    --priority=1000 \
    --network=$NETWORK \
    --action=ALLOW \
    --rules=tcp:8001 \
    --source-ranges=0.0.0.0/0 \
    --description="Allow access to Aegis Gateway Backend API" \
    --quiet

echo "✅ Règle Backend créée"
echo ""

# Vérification
echo "📊 Vérification des règles créées:"
gcloud compute firewall-rules list --filter="name~'allow-aegis-'" --format="table(name,direction,sourceRanges,allowed)"

echo ""
echo "🎉 Configuration terminée !"
echo ""
echo "🧪 Testez maintenant:"
echo "   Frontend: http://136.119.23.158:5174/"
echo "   Backend:  http://136.119.23.158:8001/api/v1/stats"
