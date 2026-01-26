#!/bin/bash
# Script de démarrage de la stack IGA COMPLÈTE
# Inclut: MidPoint, Odoo, OpenLDAP, Home App, N8N, Gateway

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"

echo "🚀 Démarrage de la stack IGA COMPLÈTE"
echo "   MidPoint + Odoo + OpenLDAP + Home App + N8N + Gateway"
echo "📁 Répertoire du projet: $PROJECT_ROOT"
echo ""

cd "$PROJECT_ROOT/docker"

# Vérifier docker-compose
if ! command -v docker-compose &> /dev/null; then
    if ! docker compose version &> /dev/null; then
        echo "❌ Erreur: Docker Compose non disponible"
        exit 1
    fi
    DOCKER_COMPOSE="docker compose"
else
    DOCKER_COMPOSE="docker-compose"
fi

echo "🔧 Utilisation de: $DOCKER_COMPOSE"
echo ""

# Construire l'image de la Gateway si nécessaire
echo "🏗️  Construction de l'image Gateway..."
$DOCKER_COMPOSE build gateway 2>/dev/null || echo "⚠️  Build gateway ignoré (image existante ou erreur)"

# Démarrage des conteneurs
echo ""
echo "📦 Démarrage de tous les conteneurs..."
$DOCKER_COMPOSE up -d

echo ""
echo "⏳ Attente du démarrage des services..."
echo "   (MidPoint peut prendre 2-3 minutes)"

# Attendre que les services soient prêts
sleep 15

# Afficher l'état
echo ""
echo "📊 État des services:"
$DOCKER_COMPOSE ps

echo ""
echo "═══════════════════════════════════════════════════════════════════"
echo "✅ Stack IGA COMPLÈTE démarrée!"
echo "═══════════════════════════════════════════════════════════════════"
echo ""
echo "🌐 URLs d'accès:"
echo ""
echo "   📋 MidPoint IAM:     http://localhost:8080/midpoint"
echo "      └─ Login: administrator / 5ecr3t"
echo ""
echo "   🏢 Odoo ERP:         http://localhost:8069"
echo "      └─ Login: admin / admin"
echo ""
echo "   🔌 Gateway API:      http://localhost:8000"
echo "      └─ Documentation: http://localhost:8000/docs"
echo ""
echo "   ⚙️  N8N Workflows:    http://localhost:5678"
echo "      └─ Login: admin / admin123"
echo ""
echo "   📂 LDAP:             ldap://localhost:10389"
echo "      └─ Bind DN: cn=admin,dc=example,dc=com / admin"
echo ""
echo "   🗄️  Home App DB:      localhost:5434"
echo "      └─ Base: homeapp / homeapp / homeapp123"
echo ""
echo "═══════════════════════════════════════════════════════════════════"
echo ""
echo "📝 Commandes utiles:"
echo "   Logs Gateway:    cd docker && $DOCKER_COMPOSE logs -f gateway"
echo "   Logs N8N:        cd docker && $DOCKER_COMPOSE logs -f n8n"
echo "   Logs MidPoint:   cd docker && $DOCKER_COMPOSE logs -f midpoint"
echo "   Arrêter:         ./scripts/down.sh"
echo ""
echo "📖 Prochaines étapes:"
echo "   1. Initialiser LDAP:     ./scripts/init-ldap.sh"
echo "   2. Importer données RH:  python3 scripts/clean_hr_csv.py"
echo "   3. Importer workflows N8N via l'interface N8N"
echo "   4. Configurer les ressources MidPoint"
echo ""








