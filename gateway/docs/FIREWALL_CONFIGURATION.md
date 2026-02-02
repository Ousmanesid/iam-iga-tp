# 🔥 Configuration du Pare-feu Google Cloud

## 📋 Résumé
Pour accéder à Aegis Gateway depuis votre PC externe (IP: 136.119.23.158), vous devez ouvrir les ports suivants dans le pare-feu Google Cloud :

- **Port 5174** : Frontend React (Dashboard)
- **Port 8001** : Backend FastAPI (API REST)

---

## ✅ État Actuel des Services

Les services sont **opérationnels** et écoutent sur toutes les interfaces :

```bash
✓ Backend  : http://0.0.0.0:8001 (API Ready)
✓ Frontend : http://0.0.0.0:5174 (React Dashboard)
✓ Database : SQLite with 5 test users & 5 operations
```

**Problème** : Le pare-feu Google Cloud bloque les connexions externes.

---

## 🛠️ Solution : Règles de Pare-feu via Console Web

### Méthode 1 : Google Cloud Console (Recommandée)

1. **Accédez à Google Cloud Console** :
   - Ouvrez https://console.cloud.google.com/
   - Connectez-vous avec votre compte

2. **Naviguez vers les Règles de Pare-feu** :
   - Menu hamburger (☰) → **VPC Network** → **Firewall**
   - Ou recherchez "Firewall" dans la barre de recherche

3. **Créez la Règle pour le Frontend (Port 5174)** :
   - Cliquez sur **CREATE FIREWALL RULE**
   - **Nom** : `allow-aegis-frontend`
   - **Description** : Allow external access to Aegis Gateway Frontend
   - **Direction** : `Ingress`
   - **Action on match** : `Allow`
   - **Targets** : `All instances in the network` (ou spécifiez votre instance)
   - **Source filter** : `IPv4 ranges`
   - **Source IPv4 ranges** : `0.0.0.0/0` (tout le monde) ou votre IP personnelle
   - **Protocols and ports** :
     - Cochez **Specified protocols and ports**
     - **tcp** : `5174`
   - Cliquez sur **CREATE**

4. **Créez la Règle pour le Backend (Port 8001)** :
   - Cliquez sur **CREATE FIREWALL RULE**
   - **Nom** : `allow-aegis-backend`
   - **Description** : Allow external access to Aegis Gateway Backend
   - **Direction** : `Ingress`
   - **Action on match** : `Allow`
   - **Targets** : `All instances in the network`
   - **Source filter** : `IPv4 ranges`
   - **Source IPv4 ranges** : `0.0.0.0/0` ou votre IP personnelle
   - **Protocols and ports** :
     - Cochez **Specified protocols and ports**
     - **tcp** : `8001`
   - Cliquez sur **CREATE**

---

### Méthode 2 : gcloud CLI (Si Disponible)

**⚠️ Note** : Ces commandes doivent être exécutées **depuis votre PC local**, pas depuis la VM.
La VM n'a pas les scopes nécessaires pour modifier les règles de pare-feu.

```bash
# Frontend (Port 5174)
gcloud compute firewall-rules create allow-aegis-frontend \
    --direction=INGRESS \
    --priority=1000 \
    --network=default \
    --action=ALLOW \
    --rules=tcp:5174 \
    --source-ranges=0.0.0.0/0 \
    --description="Allow external access to Aegis Gateway Frontend"

# Backend (Port 8001)
gcloud compute firewall-rules create allow-aegis-backend \
    --direction=INGRESS \
    --priority=1000 \
    --network=default \
    --action=ALLOW \
    --rules=tcp:8001 \
    --source-ranges=0.0.0.0/0 \
    --description="Allow external access to Aegis Gateway Backend"
```

---

## 🔒 Sécurité : Restreindre par IP Source

Pour plus de sécurité, remplacez `0.0.0.0/0` par **votre IP publique** :

1. Trouvez votre IP publique :
   - Google : "what is my ip"
   - Ou visitez : https://ifconfig.me/

2. Utilisez cette IP dans **Source IPv4 ranges** :
   ```
   <VOTRE_IP>/32
   ```
   Exemple : `203.0.113.45/32`

---

## ✅ Vérification Post-Configuration

Après avoir créé les règles, testez l'accès depuis votre PC :

### 1. Backend API
```bash
curl http://136.119.23.158:8001/api/v1/stats
```

**Réponse attendue** :
```json
{
  "total_users": 5,
  "today_operations": 3,
  "success_rate": 40.0,
  "critical_failures": 2
}
```

### 2. Frontend Dashboard
Ouvrez dans votre navigateur :
```
http://136.119.23.158:5174
```

Vous devriez voir :
- **Dashboard** avec 4 KPI cards (5 users, 3 ops today, 40% success, 2 failures)
- **Tableau des opérations** : Sophie Martin, Lucas Dubois, Emma Bernard, Thomas Petit, Marie Roux
- **Badges de statut** : SUCCESS (vert), FAILED (rouge), PARTIAL (orange)

---

## 🐛 Dépannage

### Les règles ne fonctionnent pas ?

1. **Vérifiez le Network Tag de votre VM** :
   ```bash
   gcloud compute instances describe instance-20260127-222802 --zone=<ZONE> --format="value(tags.items)"
   ```

2. **Appliquez les règles à ce tag spécifique** :
   - Retournez dans la console
   - Éditez la règle de pare-feu
   - Dans **Targets**, choisissez `Specified target tags`
   - Entrez le tag de votre VM

3. **Vérifiez les Priorités** :
   - Les règles avec priorité 1000 sont généralement bonnes
   - Si vous avez une règle `deny` avec priorité < 1000, elle bloquera le trafic

### Toujours bloqué ?

```bash
# Testez depuis la VM (doit fonctionner)
curl http://localhost:8001/api/v1/stats

# Si ça fonctionne en local mais pas depuis l'extérieur,
# c'est bien un problème de pare-feu
```

---

## 📊 Données de Test Disponibles

La base de données contient actuellement :

### Utilisateurs (5)
1. **Sophie Martin** - Développeuse Full-Stack (IT)
2. **Lucas Dubois** - Commercial Senior (Ventes)
3. **Emma Bernard** - RH Manager (RH)
4. **Thomas Petit** - DevOps Engineer (IT)
5. **Marie Roux** - Comptable (Finance)

### Opérations (5)
- **2 Success** : Sophie Martin (Keycloak, GitLab, Mattermost, Notion), Thomas Petit (Keycloak, GitLab, Jenkins, Kubernetes)
- **2 Failed** : Lucas Dubois (Odoo timeout), Marie Roux (email validation)
- **1 Partial** : Emma Bernard (SecureHR conflict)

---

## 🎯 Prochaine Étape : Phase 2

Une fois le pare-feu configuré et l'interface accessible, nous allons implémenter :

1. **role_mapper.py** : Mapping Job Title → Applications
2. **provisioning_service.py** : Orchestration multi-app
3. **Connectors** : Keycloak, GitLab, Odoo, etc.
4. **POST /api/v1/provision** : Endpoint de provisioning réel

---

**Questions ou problèmes ?** N'hésitez pas à demander !
