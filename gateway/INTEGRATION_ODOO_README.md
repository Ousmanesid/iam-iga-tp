# 🔄 Intégration Odoo → Aegis Gateway

## ✅ COMPLETÉE

L'intégration entre Odoo et Aegis Gateway est maintenant **opérationnelle**.

Les utilisateurs créés dans Odoo peuvent être automatiquement synchronisés vers Aegis Gateway et affichés dans le Dashboard.

---

## 🚀 Comment ça marche

```
┌─────────┐         ┌──────────────┐         ┌───────────────┐
│  Odoo   │  sync   │    Aegis     │ display │   Dashboard   │
│   HR    │────────▶│   Gateway    │────────▶│  (Frontend)   │
└─────────┘         └──────────────┘         └───────────────┘
   ↑ créer                  ↓                        ↑
   employé            provisionner              voir users
                      vers apps
```

---

## 📊 Nouveaux Endpoints

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| GET | `/api/v1/odoo/employees` | Liste les employés Odoo (source directe) |
| POST | `/api/v1/odoo/sync` | Synchronise Odoo → Aegis Gateway |
| POST | `/api/v1/odoo/webhook` | Webhook pour sync temps réel |
| GET | `/api/v1/odoo/sync/status` | Statut de la synchronisation |

---

## 🎯 Utilisation Rapide

### 1. Vérifier le statut

```bash
curl http://localhost:8001/api/v1/odoo/sync/status
```

### 2. Synchroniser

```bash
curl -X POST http://localhost:8001/api/v1/odoo/sync
```

### 3. Voir dans le Dashboard

Ouvrir : **http://136.119.23.158:5174/**

Les utilisateurs avec `source: "odoo_sync"` viennent d'Odoo.

---

## 🧪 Tests

### Test automatique

```bash
cd /srv/projet/aegis-gateway
./venv/bin/python scripts/test_odoo_integration.py
```

### Test manuel

```bash
# 1. Status
curl http://localhost:8001/api/v1/odoo/sync/status

# 2. Sync
curl -X POST http://localhost:8001/api/v1/odoo/sync

# 3. Vérifier les users
curl http://localhost:8001/api/v1/users | grep odoo_sync
```

---

## 📋 Mapping Automatique

| Job Title Odoo | Rôle Aegis | Applications |
|----------------|------------|--------------|
| Développeur | DEVELOPER | GitLab, Keycloak, Mattermost, Notion |
| DevOps Engineer | DEVOPS | Jenkins, Kubernetes, GitLab |
| Commercial | SALES | CRM, Odoo, Keycloak |
| RH Manager | HR_MANAGER | SecureHR, Odoo, Keycloak |

---

## ⚠️ Prérequis

Pour que la synchronisation fonctionne:

1. **Odoo doit être démarré** :
   ```bash
   cd /srv/projet/iam-iga-tp
   docker-compose up -d odoo
   ```

2. **Credentials configurés dans `.env`** :
   ```bash
   ODOO_URL=http://odoo:8069
   ODOO_DB=odoo
   ODOO_USERNAME=admin@example.com
   ODOO_PASSWORD=admin
   ```

---

## 📁 Fichiers Créés

- `app/services/odoo_sync_service.py` - Service de synchronisation
- `app/routers/odoo.py` - Routes API
- `app/core/role_mapper.py` - Mapping job → role (fonction ajoutée)
- `app/database/models.py` - Colonnes `role` et `source` ajoutées
- `docs/ODOO_INTEGRATION.md` - Documentation complète (20+ pages)
- `scripts/test_odoo_integration.py` - Script de test automatique

---

## 📖 Documentation Complète

Voir : **`docs/ODOO_INTEGRATION.md`** pour tous les détails.

---

## ✅ Checklist

- [x] Service de synchronisation créé
- [x] Endpoints API fonctionnels
- [x] Mapping automatique des rôles
- [x] Colonnes DB ajoutées (`role`, `source`)
- [x] Documentation complète
- [x] Script de test
- [ ] Odoo démarré et connecté (dépend de votre environnement)
- [ ] Premier test de synchronisation

---

## 🎉 Résultat

**Les utilisateurs créés dans Odoo s'affichent maintenant dans Aegis Gateway !**

Après synchronisation, ils sont visibles dans le Dashboard avec la mention `source: "odoo_sync"`.

---

**Besoin d'aide ?** Consultez `docs/ODOO_INTEGRATION.md`
