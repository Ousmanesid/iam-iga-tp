#!/bin/bash
# Script de réinitialisation complète de la stack IGA
# ⚠️  ATTENTION: supprime toutes les données (volumes)

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"

echo "⚠️  RÉINITIALISATION COMPLÈTE DE LA STACK IGA"
echo "Ceci va supprimer tous les conteneurs et volumes (données perdues)."
echo ""
read -p "Confirmer la réinitialisation? (oui/non): " -r
echo

if [[ ! $REPLY =~ ^[Oo][Uu][Ii]$ ]]; then
    echo "❌ Annulé"
    exit 1
fi

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

echo "🗑️  Suppression des conteneurs et volumes..."
$DOCKER_COMPOSE down -v

echo ""
echo "🧹 Nettoyage des fichiers CSV générés..."
rm -f "$PROJECT_ROOT/data/hr/hr_clean.csv"
echo "" > "$PROJECT_ROOT/data/intranet/accounts.csv"
echo "username,full_name,email,department,enabled,roles" >> "$PROJECT_ROOT/data/intranet/accounts.csv"

echo ""
echo "✅ Réinitialisation terminée"
echo "🚀 Redémarrer: ./scripts/up.sh"

