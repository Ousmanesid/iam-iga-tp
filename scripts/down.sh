#!/bin/bash
# Script d'arrêt de la stack IGA

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"

echo ""
echo "🛑 Arrêt de la stack IGA..."
echo ""

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

# Arrêter le conteneur intranet-app s'il a été lancé manuellement
if docker ps -q -f name=intranet-app &> /dev/null; then
    echo "  → Arrêt de intranet-app..."
    docker stop intranet-app 2>/dev/null || true
    docker rm intranet-app 2>/dev/null || true
fi

# Arrêt des conteneurs docker-compose
echo "  → Arrêt des services Docker Compose..."
$DOCKER_COMPOSE down 2>/dev/null || true

# Nettoyer le réseau si nécessaire
docker network rm iam_net 2>/dev/null || true

echo ""
echo "✅ Stack arrêtée avec succès"
echo ""
echo "💡 Les volumes (données) sont préservés."
echo "   Pour supprimer également les volumes: $0 --volumes"

# Option pour supprimer les volumes
if [[ "$1" == "--volumes" || "$1" == "-v" ]]; then
    echo ""
    echo "🗑️  Suppression des volumes..."
    cd "$PROJECT_ROOT/docker"
    $DOCKER_COMPOSE down -v 2>/dev/null || true
    echo "✅ Volumes supprimés"
fi

