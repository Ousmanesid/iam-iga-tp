#!/bin/bash
# Script de démarrage du backend Aegis Gateway avec chargement des variables d'environnement

cd /srv/projet/aegis-gateway

# Activer le virtualenv
source venv/bin/activate

# Charger les variables d'environnement depuis .env
export $(cat .env | grep -v '^#' | xargs)

# Afficher les variables Odoo pour vérification
echo "🔧 Configuration Odoo:"
echo "   URL: $ODOO_URL"
echo "   DB: $ODOO_DB"
echo "   User: $ODOO_USERNAME"

# Tuer l'ancien processus s'il existe
pkill -f "uvicorn app.main:app" 2>/dev/null

# Attendre que le port soit libéré
sleep 2

# Démarrer le backend
echo "🚀 Démarrage du backend..."
python -m uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload > backend.log 2>&1 &

# Attendre le démarrage
sleep 3

# Vérifier que ça fonctionne
if curl -s http://localhost:8001/health > /dev/null 2>&1; then
    echo "✅ Backend démarré avec succès !"
    echo "   Health check: OK"
    echo "   Logs: tail -f backend.log"
else
    echo "❌ Erreur de démarrage"
    echo "   Voir les logs: tail -f backend.log"
    exit 1
fi
