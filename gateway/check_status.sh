#!/bin/bash
echo "🔍 Verification de la reconstruction d'Aegis Gateway"
echo "=================================================="
echo ""

echo "📁 Structure Backend:"
ls -la /srv/projet/aegis-gateway/app/api/routes.py 2>/dev/null && echo "✅ Routes API présentes" || echo "❌ Routes manquantes"
ls -la /srv/projet/aegis-gateway/app/database/models.py 2>/dev/null && echo "✅ Models DB présents" || echo "❌ Models manquants"
ls -la /srv/projet/aegis-gateway/app/core/config.py 2>/dev/null && echo "✅ Configuration présente" || echo "❌ Config manquante"

echo ""
echo "📁 Structure Frontend:"
ls -la /srv/projet/aegis-gateway/frontend/src/pages/Dashboard.jsx 2>/dev/null && echo "✅ Dashboard présent" || echo "❌ Dashboard manquant"
ls -la /srv/projet/aegis-gateway/frontend/src/pages/OperationDetail.jsx 2>/dev/null && echo "✅ OperationDetail présent" || echo "❌ OperationDetail manquant"
ls -la /srv/projet/aegis-gateway/frontend/src/components/dashboard/StatCard.jsx 2>/dev/null && echo "✅ StatCard présent" || echo "❌ StatCard manquant"
ls -la /srv/projet/aegis-gateway/frontend/src/layouts/AdminLayout.jsx 2>/dev/null && echo "✅ AdminLayout présent" || echo "❌ AdminLayout manquant"

echo ""
echo "🌐 Services:"
curl -s -o /dev/null -w "Backend (8001): %{http_code}\n" http://localhost:8001/health
curl -s -o /dev/null -w "Frontend (5173): %{http_code}\n" http://localhost:5173/

echo ""
echo "📊 Endpoints API:"
curl -s http://localhost:8001/api/v1/stats 2>/dev/null | python3 -c "import sys,json;d=json.load(sys.stdin);print(f\"✅ /stats - {d['users']} users, {d['operations']} ops\")" 2>/dev/null || echo "⚠️ /stats endpoint à vérifier"

echo ""
echo "✅ Reconstruction terminée ! Accédez à: http://localhost:5173"
