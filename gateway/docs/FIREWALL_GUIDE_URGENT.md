# 🚨 GUIDE URGENT : Configuration Pare-feu Google Cloud

## ❌ Problème Actuel
Le site charge à l'infini sur http://136.119.23.158:5174/

**Cause** : Le pare-feu Google Cloud bloque les ports 5174 et 8001

## ✅ Solution : 5 Minutes de Configuration

### Étape 1 : Ouvrir Google Cloud Console
1. Allez sur : **https://console.cloud.google.com/**
2. Connectez-vous avec votre compte Google Cloud

### Étape 2 : Accéder aux Règles de Pare-feu
1. Cliquez sur le **menu hamburger** (☰) en haut à gauche
2. Dans le menu, cherchez **"VPC Network"** (ou "Réseau VPC")
3. Cliquez sur **"Firewall"** (ou "Pare-feu")

OU plus rapide :
- Cliquez sur la barre de recherche en haut
- Tapez **"firewall"**
- Cliquez sur **"Firewall - VPC Network"**

### Étape 3 : Créer la Règle pour le Frontend (Port 5174)

1. Cliquez sur le bouton **"CREATE FIREWALL RULE"** en haut
2. Remplissez le formulaire :

   **Section "Details"** :
   - **Name** : `allow-aegis-frontend`
   - **Description** : `Allow access to Aegis Gateway Frontend`
   - **Logs** : Off (laissez par défaut)

   **Section "Network"** :
   - **Network** : `default` (ou votre réseau)
   - **Priority** : `1000` (laissez par défaut)
   - **Direction of traffic** : `Ingress` (sélectionnez)
   - **Action on match** : `Allow` (sélectionnez)

   **Section "Targets"** :
   - **Targets** : `All instances in the network` (sélectionnez)

   **Section "Source filter"** :
   - **Source filter** : `IPv4 ranges` (sélectionnez)
   - **Source IPv4 ranges** : `0.0.0.0/0`

   **Section "Protocols and ports"** :
   - Cochez **"Specified protocols and ports"**
   - **TCP** : cochez la case et entrez `5174`

3. Cliquez sur **"CREATE"** en bas

### Étape 4 : Créer la Règle pour le Backend (Port 8001)

1. Cliquez à nouveau sur **"CREATE FIREWALL RULE"**
2. Remplissez le formulaire :

   **Section "Details"** :
   - **Name** : `allow-aegis-backend`
   - **Description** : `Allow access to Aegis Gateway Backend API`
   - **Logs** : Off

   **Section "Network"** :
   - **Network** : `default`
   - **Priority** : `1000`
   - **Direction of traffic** : `Ingress`
   - **Action on match** : `Allow`

   **Section "Targets"** :
   - **Targets** : `All instances in the network`

   **Section "Source filter"** :
   - **Source filter** : `IPv4 ranges`
   - **Source IPv4 ranges** : `0.0.0.0/0`

   **Section "Protocols and ports"** :
   - Cochez **"Specified protocols and ports"**
   - **TCP** : cochez la case et entrez `8001`

3. Cliquez sur **"CREATE"**

### Étape 5 : Vérification

Une fois les 2 règles créées, attendez **30 secondes** puis :

1. **Rafraîchissez** votre navigateur sur http://136.119.23.158:5174/
2. Le dashboard devrait apparaître immédiatement avec :
   - 6 utilisateurs
   - 4 opérations aujourd'hui
   - 50% de taux de succès
   - 2 échecs critiques

## 🧪 Tests Après Configuration

### Test 1 : Backend API
Ouvrez dans votre navigateur :
```
http://136.119.23.158:8001/api/v1/stats
```

Vous devriez voir :
```json
{
  "total_users": 6,
  "today_operations": 4,
  "success_rate": 50.0,
  "critical_failures": 2
}
```

### Test 2 : Frontend Dashboard
Ouvrez dans votre navigateur :
```
http://136.119.23.158:5174/
```

Vous devriez voir le dashboard avec :
- 4 cartes KPI en haut
- Un tableau avec 6 opérations
- Des badges colorés (vert=SUCCESS, rouge=FAILED, orange=PARTIAL)

## 🔒 Note de Sécurité

Pour l'instant, nous avons ouvert les ports à tout le monde (`0.0.0.0/0`).

**En production**, vous devriez restreindre à votre IP :
1. Trouvez votre IP publique : https://ifconfig.me/
2. Dans les règles de pare-feu, remplacez `0.0.0.0/0` par `VOTRE_IP/32`
   - Exemple : `203.0.113.45/32`

## ❓ Si Ça Ne Marche Toujours Pas

### Vérifiez les Règles Créées
1. Dans Google Cloud Console → Firewall
2. Vous devriez voir 2 nouvelles règles :
   - ✅ `allow-aegis-frontend` (Priority: 1000, TCP: 5174)
   - ✅ `allow-aegis-backend` (Priority: 1000, TCP: 8001)
3. Les deux doivent avoir l'icône verte (enabled)

### Vérifiez le Network Tag de votre VM
Si les règles ne fonctionnent pas :

1. Allez dans **Compute Engine** → **VM instances**
2. Cliquez sur votre VM `instance-20260127-222802`
3. Cliquez sur **EDIT**
4. Regardez la section **Network tags**
5. Si elle contient un tag (ex: `http-server`), retournez modifier les règles :
   - Dans **Targets**, changez pour **Specified target tags**
   - Entrez le tag de votre VM

### Commandes CLI (Alternative depuis votre PC)

Si vous préférez utiliser la ligne de commande :

```bash
# Frontend
gcloud compute firewall-rules create allow-aegis-frontend \
    --direction=INGRESS \
    --priority=1000 \
    --network=default \
    --action=ALLOW \
    --rules=tcp:5174 \
    --source-ranges=0.0.0.0/0 \
    --description="Allow access to Aegis Gateway Frontend"

# Backend
gcloud compute firewall-rules create allow-aegis-backend \
    --direction=INGRESS \
    --priority=1000 \
    --network=default \
    --action=ALLOW \
    --rules=tcp:8001 \
    --source-ranges=0.0.0.0/0 \
    --description="Allow access to Aegis Gateway Backend API"
```

**⚠️ Important** : Ces commandes doivent être exécutées **depuis votre PC local**, pas depuis la VM.

## 📊 Ce Qui Vous Attend Après Configuration

### Dashboard Visible
- **4 KPI Cards** :
  - 👥 Total Users: 6
  - 📅 Today's Operations: 4
  - ✅ Success Rate: 50%
  - ❌ Critical Failures: 2

### Tableau des Opérations
| Utilisateur | Statut | Applications | Actions |
|-------------|--------|--------------|---------|
| Alice Test | SUCCESS | 4 | 4/0 |
| Thomas Petit | SUCCESS | 4 | 4/0 |
| Sophie Martin | SUCCESS | 4 | 4/0 |
| Emma Bernard | PARTIAL | 3 | 2/1 |
| Lucas Dubois | FAILED | 3 | 1/1 |
| Marie Roux | FAILED | 2 | 0/1 |

### Fonctionnalités Disponibles
- ✅ Cliquez sur une opération → voir le détail avec timeline
- ✅ API REST complète sur `/api/v1/*`
- ✅ Provisioning POST pour créer de nouveaux utilisateurs
- ✅ Documentation interactive sur http://136.119.23.158:8001/docs

---

## 🎯 Récapitulatif

1. ✅ **Services opérationnels** : Frontend (5174) + Backend (8001)
2. ✅ **Configuration correcte** : API pointe vers 136.119.23.158:8001
3. ❌ **Pare-feu bloqué** : Il faut créer 2 règles dans Google Cloud Console

**Temps estimé** : 5 minutes  
**Difficulté** : Facile (cliquer sur CREATE et remplir un formulaire)

Une fois configuré, le site fonctionnera immédiatement ! 🚀
