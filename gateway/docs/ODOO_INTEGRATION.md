# 🔄 Intégration Odoo ↔ Aegis Gateway

## Vue d'ensemble

Cette intégration permet de **synchroniser automatiquement** les employés créés dans Odoo vers la base de données d'Aegis Gateway.

```
Odoo (hr.employee) → Aegis Gateway (provisioned_users) → Provisioning automatique
```

---

## 📊 Endpoints API

### 1. **GET `/api/v1/odoo/employees`**

Liste tous les employés depuis Odoo (source directe, sans passer par la base locale).

```bash
curl http://136.119.23.158:8001/api/v1/odoo/employees
```

**Réponse :**
```json
[
  {
    "personalNumber": "1",
    "givenName": "Alice",
    "familyName": "Doe",
    "email": "alice.doe@company.com",
    "department": "IT",
    "title": "Développeur",
    "status": "active"
  }
]
```

---

### 2. **POST `/api/v1/odoo/sync`**

Synchronise **tous** les employés d'Odoo vers la base Aegis Gateway.

```bash
# Synchronisation immédiate (bloquante)
curl -X POST http://136.119.23.158:8001/api/v1/odoo/sync

# Synchronisation en arrière-plan (non-bloquante)
curl -X POST "http://136.119.23.158:8001/api/v1/odoo/sync?background=true"
```

**Réponse :**
```json
{
  "success": true,
  "message": "Synchronisation réussie: 12 créés, 3 mis à jour",
  "timestamp": "2026-01-29T00:00:00",
  "stats": {
    "success": true,
    "total": 15,
    "created": 12,
    "updated": 3,
    "skipped": 0,
    "errors": []
  }
}
```

---

### 3. **POST `/api/v1/odoo/webhook`**

Webhook pour synchronisation **temps réel** depuis Odoo.

**Payload :**
```json
{
  "event": "create",
  "employee_id": 42,
  "data": null
}
```

**Événements supportés :**
- `create` : Nouvel employé
- `update` : Employé modifié
- `delete` : Employé désactivé

**Configuration dans n8n :**
1. Créer un workflow qui écoute les créations dans Odoo
2. Envoyer un POST vers `/api/v1/odoo/webhook`

---

### 4. **GET `/api/v1/odoo/sync/status`**

Affiche le statut de la synchronisation.

```bash
curl http://136.119.23.158:8001/api/v1/odoo/sync/status
```

**Réponse :**
```json
{
  "odoo_connected": true,
  "local_users_from_odoo": 15,
  "last_check": "2026-01-29T00:03:18.542342"
}
```

---

## 🎯 Workflow de Synchronisation

### Scénario 1 : Synchronisation Manuelle

1. **Créer un employé dans Odoo** (interface web ou API)
2. **Lancer la synchronisation** :
   ```bash
   curl -X POST http://localhost:8001/api/v1/odoo/sync
   ```
3. **Vérifier dans le Dashboard** :
   - Ouvrir http://136.119.23.158:5174/
   - L'utilisateur apparaît dans la liste avec `source: odoo_sync`

### Scénario 2 : Webhook Temps Réel (n8n)

```
Odoo → Webhook n8n → API Aegis /odoo/webhook → Base Aegis
```

**Workflow n8n :**
```
1. Trigger: Odoo - On Employee Created
2. HTTP Request: POST /api/v1/odoo/webhook
   Body: 
   {
     "event": "create",
     "employee_id": {{$node.Trigger.json.id}}
   }
```

### Scénario 3 : Synchronisation Programmée (Cron)

```bash
# Ajouter dans crontab
0 * * * * curl -X POST http://localhost:8001/api/v1/odoo/sync?background=true
```

Synchronise toutes les heures en arrière-plan.

---

## 📋 Mapping des Données

### Odoo → Aegis Gateway

| Champ Odoo (hr.employee) | Champ Aegis (provisioned_users) | Transformation |
|--------------------------|----------------------------------|----------------|
| `id` | `source_id` | String |
| `name` | `first_name` + `last_name` | Split sur espace |
| `work_email` | `email` | Direct |
| `job_title` | `job_title` | Direct |
| `job_title` | `role` | Mapping via `map_job_to_role()` |
| `department_id` | `department` | Extraction du nom |
| `active` | `status` | `active` → SUCCESS, sinon FAILED |

### Mapping Automatique des Rôles

La fonction `map_job_to_role()` mappe les titres de poste vers des rôles standardisés :

| Titre Odoo | Rôle Aegis | Applications Provisionnées |
|------------|------------|----------------------------|
| Développeur | DEVELOPER | Keycloak, GitLab, Mattermost, Notion |
| DevOps Engineer | DEVOPS | Keycloak, GitLab, Jenkins, Kubernetes |
| Commercial | SALES | Keycloak, CRM, Odoo |
| RH Manager | HR_MANAGER | Keycloak, SecureHR, Odoo |

**Exemple :**
- Employé créé dans Odoo : `job_title="Développeur"`
- Synchronisé dans Aegis : `role="DEVELOPER"`
- Provisioning automatique vers : GitLab, Keycloak, Mattermost, Notion

---

## 🔐 Configuration

### Variables d'environnement (.env)

```bash
# Configuration Odoo
ODOO_URL=http://odoo:8069
ODOO_DB=odoo
ODOO_USERNAME=admin@example.com
ODOO_PASSWORD=admin
```

### Vérifier la connexion Odoo

```bash
curl http://localhost:8001/api/v1/odoo/sync/status
```

Si `odoo_connected: false`, vérifier :
1. Odoo est démarré : `docker ps | grep odoo`
2. Les credentials sont corrects dans `.env`
3. Le réseau Docker permet la communication

---

## 🧪 Tests

### Test 1 : Créer un employé dans Odoo

```python
# Via Python (si Odoo est accessible)
import xmlrpc.client

url = "http://localhost:8069"
db = "odoo"
username = "admin@example.com"
password = "admin"

common = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/common")
uid = common.authenticate(db, username, password, {})

models = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/object")

# Créer un employé
employee_id = models.execute_kw(db, uid, password,
    'hr.employee', 'create',
    [{
        'name': 'Bob Test',
        'work_email': 'bob.test@company.com',
        'job_title': 'Développeur',
        'department_id': 1,
        'active': True
    }]
)

print(f"✅ Employé créé : ID {employee_id}")
```

### Test 2 : Synchroniser vers Aegis

```bash
curl -X POST http://localhost:8001/api/v1/odoo/sync
```

### Test 3 : Vérifier dans la base Aegis

```bash
curl http://localhost:8001/api/v1/users | grep "bob.test"
```

---

## 🚀 Utilisation Complète

### Workflow Complet : Odoo → Aegis → Applications

```bash
# 1. Créer un employé dans Odoo (via interface ou API)
#    Titre : "Développeur"
#    Email : alice.new@company.com

# 2. Synchroniser vers Aegis
curl -X POST http://localhost:8001/api/v1/odoo/sync

# 3. L'utilisateur apparaît dans Aegis avec :
#    - source: "odoo_sync"
#    - role: "DEVELOPER"
#    - status: "SUCCESS"

# 4. Lancer le provisioning automatique (optionnel)
curl -X POST http://localhost:8001/api/v1/provision \
  -H "Content-Type: application/json" \
  -d '{
    "email": "alice.new@company.com",
    "first_name": "Alice",
    "last_name": "New",
    "job_title": "Développeur",
    "department": "IT"
  }'

# 5. Vérifier les applications provisionnées
curl http://localhost:8001/api/v1/users/alice.new@company.com
```

---

## 📊 Monitoring

### Dashboard Aegis Gateway

1. Ouvrir http://136.119.23.158:5174/
2. Voir la section "Users from Odoo"
3. Filtrer par `source: odoo_sync`

### Logs

```bash
# Logs backend
tail -f /tmp/aegis_backend.log | grep -i odoo

# Logs de synchronisation
tail -f /tmp/aegis_backend.log | grep "🔄\|✨\|❌"
```

### Métriques

```bash
# Nombre d'utilisateurs synchronisés depuis Odoo
curl http://localhost:8001/api/v1/odoo/sync/status | jq '.local_users_from_odoo'

# Statistiques globales
curl http://localhost:8001/api/v1/stats
```

---

## 🔧 Troubleshooting

### Erreur : "Connexion Odoo échouée"

**Cause :** Odoo n'est pas accessible ou credentials incorrects.

**Solution :**
```bash
# Vérifier qu'Odoo est démarré
docker ps | grep odoo

# Tester la connexion manuellement
curl http://localhost:8069/web/database/selector

# Vérifier les credentials dans .env
cat .env | grep ODOO
```

### Erreur : "Aucun employé récupéré"

**Cause :** Aucun employé actif dans Odoo.

**Solution :**
```bash
# Créer un employé de test dans Odoo
# Ou vérifier le filtre active=True
```

### Les utilisateurs ne s'affichent pas dans le Dashboard

**Cause :** Le frontend ne filtre pas les sources correctement.

**Solution :**
```bash
# Vérifier dans l'API
curl http://localhost:8001/api/v1/users | grep odoo_sync

# Recharger le frontend
# Ctrl+Shift+R dans le navigateur
```

---

## 📚 Ressources

- **Code source** : `/srv/projet/aegis-gateway/app/services/odoo_sync_service.py`
- **Routes API** : `/srv/projet/aegis-gateway/app/routers/odoo.py`
- **Mapping des rôles** : `/srv/projet/aegis-gateway/app/core/role_mapper.py`
- **Tests** : `scripts/test_odoo_sync.py` (à créer)

---

## ✅ Checklist de Mise en Production

- [ ] Odoo démarré et accessible
- [ ] Credentials Odoo configurés dans `.env`
- [ ] Test de connexion : `GET /odoo/sync/status` → `odoo_connected: true`
- [ ] Test de synchronisation manuelle : `POST /odoo/sync`
- [ ] Vérification des utilisateurs dans le Dashboard
- [ ] Configuration du webhook n8n (optionnel)
- [ ] Configuration du cron de synchronisation (optionnel)
- [ ] Monitoring des logs activé

---

**🎉 Votre intégration Odoo ↔ Aegis Gateway est prête !**

Les utilisateurs créés dans Odoo apparaîtront automatiquement dans Aegis Gateway après synchronisation.
