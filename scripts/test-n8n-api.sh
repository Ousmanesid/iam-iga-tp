#!/bin/bash
# Script pour tester l'API REST de N8N

N8N_URL="http://localhost:5678"
N8N_USER="admin"
N8N_PASSWORD="admin123"

echo "🔍 Test de l'API REST N8N"
echo "=========================="
echo ""

# 1. Obtenir un token d'authentification
echo "1. Authentification..."
AUTH_RESPONSE=$(curl -s -X POST "$N8N_URL/api/v1/login" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$N8N_USER\",\"password\":\"$N8N_PASSWORD\"}")

echo "Réponse: $AUTH_RESPONSE"
echo ""

# 2. Lister les workflows
echo "2. Liste des workflows..."
curl -s -X GET "$N8N_URL/api/v1/workflows" \
  -u "$N8N_USER:$N8N_PASSWORD" | jq '.' 2>/dev/null || echo "Install jq pour un meilleur affichage"
echo ""

# 3. Tester un webhook
echo "3. Test webhook pre-provision..."
curl -s -X POST "$N8N_URL/webhook/pre-provision" \
  -H "Content-Type: application/json" \
  -d '{
    "user_data": {
      "login": "test.mcp",
      "email": "test@example.com",
      "first_name": "Test",
      "last_name": "MCP"
    },
    "requested_roles": ["USER"],
    "target_system": "homeapp",
    "requires_approval": false
  }' | jq '.' 2>/dev/null || echo "Réponse reçue"
echo ""

echo "✅ Tests terminés"








