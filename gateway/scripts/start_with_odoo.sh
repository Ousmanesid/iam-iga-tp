#!/bin/bash
# Script de démarrage d'Aegis Gateway avec chargement des variables d'environnement

set -a  # Auto-export toutes les variables
source /srv/projet/aegis-gateway/.env
set +a

cd /srv/projet/aegis-gateway

# Arrêter les anciens processus
pkill -f "uvicorn.*8001" 2>/dev/null || true
sleep 2

# Démarrer le backend
echo "🚀 Démarrage d'Aegis Gateway avec configuration Odoo..."
echo "   ODOO_URL: $ODOO_URL"
echo "   ODOO_DB: $ODOO_DB"
echo "   ODOO_USERNAME: $ODOO_USERNAME"

nohup python -m uvicorn app.main:app --host 0.0.0.0 --port 8001 > /tmp/aegis_backend.log 2>&1 &
BACKEND_PID=$!

sleep 3

# Vérifier que le backend est démarré
if curl -s http://localhost:8001/health > /dev/null 2>&1; then
    echo "✅ Backend démarré (PID: $BACKEND_PID)"
    echo "📊 API: http://localhost:8001"
    echo "📖 Docs: http://localhost:8001/docs"
else
    echo "❌ Erreur de démarrage, voir les logs:"
    tail -20 /tmp/aegis_backend.log
    exit 1
fi

# Tester la connexion Odoo
echo ""
echo "🔄 Test de connexion Odoo..."
sleep 2

STATUS=$(curl -s http://localhost:8001/api/v1/odoo/sync/status | python3 -c "import sys, json; data = json.load(sys.stdin); print('OK' if data.get('odoo_connected') else 'FAIL')" 2>/dev/null || echo "ERROR")

if [ "$STATUS" = "OK" ]; then
    echo "✅ Odoo connecté avec succès !"
    echo ""
    echo "🎯 Prochaine étape: Synchroniser les employés"
    echo "   curl -X POST http://localhost:8001/api/v1/odoo/sync"
else
    echo "⚠️  Connexion Odoo échouée"
    echo "   Vérifier les credentials dans .env"
    echo "   Status actuel: $STATUS"
fi

echo ""
echo "📝 Logs: tail -f /tmp/aegis_backend.log"
