#!/bin/bash
# Script de démarrage complet pour Aegis Gateway sur Google Cloud
# Usage: ./start_aegis.sh

set -e

PROJECT_DIR="/srv/projet/aegis-gateway"
FRONTEND_DIR="$PROJECT_DIR/frontend"

echo "🚀 Démarrage d'Aegis Gateway"
echo "============================"
echo ""

# 1. Arrêter les anciens processus
echo "⏹️  Arrêt des anciens processus..."
pkill -9 -f "uvicorn.*8001" 2>/dev/null || true
pkill -9 -f "vite.*5174" 2>/dev/null || true
sleep 2

# 2. Vérifier la base de données
echo "📊 Vérification de la base de données..."
if [ ! -f "$PROJECT_DIR/aegis.db" ]; then
    echo "⚠️  Base de données non initialisée, création en cours..."
    cd "$PROJECT_DIR"
    source venv/bin/activate
    python scripts/init_db.py
    python scripts/create_test_data.py
    echo "✅ Base de données initialisée"
fi

# 3. Démarrer le Backend
echo ""
echo "🔧 Démarrage du Backend FastAPI (port 8001)..."
cd "$PROJECT_DIR"
source venv/bin/activate
nohup uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload \
    > /tmp/aegis_backend.log 2>&1 &
BACKEND_PID=$!
echo "✅ Backend démarré (PID: $BACKEND_PID)"

# Attendre que le backend soit prêt
echo "⏳ Attente du démarrage du backend..."
for i in {1..30}; do
    if curl -s http://localhost:8001/health > /dev/null 2>&1; then
        echo "✅ Backend opérationnel"
        break
    fi
    sleep 1
done

# 4. Démarrer le Frontend
echo ""
echo "🎨 Démarrage du Frontend React (port 5174)..."
cd "$FRONTEND_DIR"
nohup npm run dev -- --host 0.0.0.0 --port 5174 \
    > /tmp/aegis_frontend.log 2>&1 &
FRONTEND_PID=$!
echo "✅ Frontend démarré (PID: $FRONTEND_PID)"

# Attendre que le frontend soit prêt
echo "⏳ Attente du démarrage du frontend..."
for i in {1..30}; do
    if ss -tlnp 2>/dev/null | grep -q ":5174"; then
        echo "✅ Frontend opérationnel"
        break
    fi
    sleep 1
done

# 5. Récapitulatif
echo ""
echo "=========================================="
echo "✅ Aegis Gateway démarré avec succès !"
echo "=========================================="
echo ""
echo "📊 Services:"
echo "   Backend:  http://localhost:8001"
echo "   Frontend: http://localhost:5174"
echo ""
echo "🌐 Accès externe (après config pare-feu):"
echo "   Dashboard: http://136.119.23.158:5174/"
echo "   API:       http://136.119.23.158:8001/api/v1/stats"
echo "   API Docs:  http://136.119.23.158:8001/docs"
echo ""
echo "📝 Logs:"
echo "   Backend:  tail -f /tmp/aegis_backend.log"
echo "   Frontend: tail -f /tmp/aegis_frontend.log"
echo ""
echo "🔥 Configuration Pare-feu Requise:"
echo "   Voir: docs/FIREWALL_GUIDE_URGENT.md"
echo ""
echo "🛑 Pour arrêter:"
echo "   pkill -f 'uvicorn.*8001'"
echo "   pkill -f 'vite.*5174'"
echo ""

# Vérification finale
echo "🧪 Tests de connectivité..."
sleep 3

if curl -s http://localhost:8001/health > /dev/null; then
    echo "✅ Backend accessible"
    curl -s http://localhost:8001/api/v1/stats | head -c 100
    echo "..."
else
    echo "❌ Backend non accessible"
fi

echo ""
echo "✨ Démarrage terminé !"
