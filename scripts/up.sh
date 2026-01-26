#!/bin/bash
# Script de démarrage de la stack IGA

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"

echo "🚀 Démarrage de la stack IGA MidPoint + Odoo + OpenLDAP"
echo "📁 Répertoire du projet: $PROJECT_ROOT"

cd "$PROJECT_ROOT/docker"

# Vérifier que docker-compose est disponible
if ! command -v docker-compose &> /dev/null; then
    if ! docker compose version &> /dev/null; then
        echo "❌ Erreur: ni 'docker-compose' ni 'docker compose' ne sont disponibles"
        exit 1
    fi
    DOCKER_COMPOSE="docker compose"
else
    DOCKER_COMPOSE="docker-compose"
fi

echo "🔧 Utilisation de: $DOCKER_COMPOSE"

# Démarrage des conteneurs
echo ""
echo "📦 Création et démarrage des conteneurs..."
$DOCKER_COMPOSE up -d

echo ""
echo "⏳ Attente du démarrage des services (cela peut prendre 2-3 minutes)..."
sleep 10

# Vérification de l'état des services
echo ""
echo "📊 État des services:"
$DOCKER_COMPOSE ps

echo ""
echo "✅ Stack démarrée avec succès!"
echo ""
echo "🌐 URLs d'accès:"
echo "   - MidPoint:   http://localhost:8080/midpoint (administrator / 5ecr3t)"
echo "   - Odoo ERP:   http://localhost:8069 (admin / admin)"
echo "   - LDAP:       ldap://localhost:10389"
echo ""
echo "📝 Logs en temps réel: cd docker && $DOCKER_COMPOSE logs -f"
echo "🛑 Arrêter la stack: ./scripts/down.sh"
echo "🔄 Réinitialiser:    ./scripts/reset.sh"

