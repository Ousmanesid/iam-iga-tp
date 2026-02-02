# Nouvelles Fonctionnalités - 30 Janvier 2026

## 🎯 Résumé

Implémentation de deux fonctionnalités majeures :
1. **Sélection d'applications lors du provisioning** - L'utilisateur peut choisir quelles applications métiers provisionner
2. **Affichage de l'avancement du provisioning** - Le dashboard affiche maintenant les 5 dernières opérations avec détails des applications provisionnées

---

## 1. Sélection d'Applications pour le Provisioning

### 🔧 Modifications Backend

#### `/app/core/role_mapper.py`
**Nouvelle fonction :**
```python
def get_all_applications() -> List[Dict[str, str]]:
    """
    Retourne la liste de toutes les applications disponibles pour le provisioning.
    """
    return [
        {"name": Application.KEYCLOAK, "description": "Single Sign-On (SSO)"},
        {"name": Application.LDAP, "description": "Annuaire LDAP"},
        {"name": Application.ODOO, "description": "ERP Odoo"},
        {"name": Application.GITLAB, "description": "Gestion du code source"},
        {"name": Application.POSTGRESQL, "description": "Base de données"},
        {"name": Application.MATTERMOST, "description": "Communication"},
        {"name": Application.CRM, "description": "Gestion clients"},
        {"name": Application.SECURE_HR, "description": "Ressources humaines"},
    ]
```

#### `/app/services/provisioning_service.py`
**Modification de `provision_user()` :**
- Ajout du paramètre `selected_applications: Optional[List[str]] = None`
- Logique de filtrage des applications si une sélection est fournie :
  ```python
  if selected_applications:
      plan['applications'] = [
          app for app in plan['applications'] 
          if app in selected_applications
      ]
  ```

#### `/app/routers/midpoint.py`
**Modifications :**
1. Ajout du champ `applications` au modèle Pydantic :
   ```python
   class ProvisionFromMidPointRequest(BaseModel):
       user_oid: str
       applications: List[str] = []  # Liste des apps à provisionner
   ```

2. Nouvel endpoint `/midpoint/applications` :
   ```python
   @router.get("/applications")
   async def get_available_applications():
       """Récupère la liste des applications métiers disponibles"""
   ```

3. Passage des applications sélectionnées au service :
   ```python
   operation = provisioning_service.provision_user(
       user_data=user_data,
       trigger="midpoint",
       selected_applications=request.applications if request.applications else None
   )
   ```

4. **Correction du bug job_title** :
   - Fallback robuste : `user.get('title') or user.get('fullName') or 'Employee'`
   - Validation pour éviter les chaînes vides

### 🎨 Modifications Frontend

#### `/frontend/src/pages/Provisioning.jsx`
**Nouveaux états :**
```javascript
const [availableApplications, setAvailableApplications] = useState([]);
const [selectedApplications, setSelectedApplications] = useState([]);
const [showAppSelector, setShowAppSelector] = useState(false);
const [currentUserOid, setCurrentUserOid] = useState(null);
```

**Nouvelles fonctions :**
- `loadAvailableApplications()` - Charge les applications au montage
- `toggleApplication(appName)` - Gère la sélection/désélection
- `confirmProvisioning()` - Envoie la requête avec les apps sélectionnées

**Nouveau composant modal :**
```jsx
{showAppSelector && (
  <div className="modal-overlay">
    <div className="modal-content">
      {/* Liste des applications avec checkboxes */}
      {availableApplications.map((app) => (
        <label className="app-checkbox-item">
          <input type="checkbox" />
          <div className="app-info">
            <strong>{app.name}</strong>
            <span>{app.description}</span>
          </div>
        </label>
      ))}
    </div>
  </div>
)}
```

#### `/frontend/src/pages/Provisioning.css`
**Nouveaux styles (~150 lignes) :**
- `.modal-overlay` - Fond semi-transparent avec animations
- `.modal-content` - Boîte modale centrée
- `.app-checkbox-item` - Éléments sélectionnables avec hover
- `.btn-primary` - Bouton de confirmation stylisé

---

## 2. Affichage de l'Avancement du Provisioning

### 🔧 Modifications Backend

#### `/app/api/routes.py`
**Modification de l'endpoint `/operations/recent` :**
```python
@router.get("/operations/recent")
async def get_recent_operations(limit: int = 10, db: Session = Depends(get_db)):
    # ... code existant ...
    
    # NOUVEAU : Récupérer les actions associées
    actions = db.query(ProvisioningAction).filter(
        ProvisioningAction.operation_id == op.id
    ).order_by(ProvisioningAction.executed_at.asc()).all()
    
    results.append({
        # ... autres champs ...
        "actions": [
            {
                "application": action.application,
                "status": action.status,
                "message": action.message,
            }
            for action in actions
        ]
    })
```

**Format de réponse :**
```json
[
  {
    "id": 59,
    "user": {
      "email": "jeffrey.kelly72@example.com",
      "first_name": "Jeffrey",
      "last_name": "Kelly",
      "job_title": "Marketing and Community Manager"
    },
    "status": "success",
    "trigger": "midpoint",
    "started_at": "2026-01-30T11:07:39.288465",
    "completed_at": "2026-01-30T11:07:39.303277",
    "total_actions": 1,
    "successful_actions": 1,
    "failed_actions": 0,
    "actions": [
      {
        "application": "Keycloak",
        "status": "success",
        "message": "[MOCK] User created in Keycloak (no connector)"
      }
    ]
  }
]
```

### 🎨 Modifications Frontend

#### `/frontend/src/components/dashboard/RecentOperations.jsx`
**Refonte complète pour adapter au nouveau format :**

1. **Nouvelle fonction `getInitials()` :**
   ```javascript
   const getInitials = (firstName, lastName) => {
     return `${firstName?.[0] || ''}${lastName?.[0] || ''}`.toUpperCase() || '?';
   };
   ```

2. **Extraction des applications depuis les actions :**
   ```javascript
   const apps = op.actions?.map(a => a.application) || [];
   ```

3. **Nouvelle colonne "Applications" :**
   ```jsx
   <td>
     <div className="apps-list">
       {apps.slice(0, 3).map((app, index) => (
         <span key={index} className="app-tag">{app}</span>
       ))}
       {apps.length > 3 && (
         <span className="app-tag more">+{apps.length - 3}</span>
       )}
     </div>
   </td>
   ```

4. **Affichage du job title au lieu de "Source → Cible" :**
   ```jsx
   <th>Job Title</th>
   ...
   <td>
     <span className="role-badge">{op.user.job_title || 'N/A'}</span>
   </td>
   ```

---

## 📋 Workflow Complet

### Provisioning avec Sélection d'Applications

1. **Utilisateur charge les utilisateurs MidPoint** (bouton "Charger les utilisateurs MidPoint")
2. **Clic sur "Provisionner"** pour un utilisateur spécifique
3. **Modal s'ouvre** avec la liste des 8 applications disponibles (toutes cochées par défaut)
4. **Utilisateur décoche les applications non désirées** (ex: garde uniquement Keycloak + LDAP)
5. **Clic sur "Provisionner (2 apps)"** pour confirmer
6. **Backend filtre les applications** et provisionne uniquement Keycloak et LDAP
7. **Message de succès** : "✅ Utilisateur provisionné avec succès vers 2 application(s)"

### Visualisation dans le Dashboard

1. **Accès au Dashboard** (`/`)
2. **Section "Dernières Opérations de Provisioning"** affiche les 5 dernières opérations
3. **Pour chaque opération** :
   - Avatar avec initiales de l'utilisateur
   - Nom complet + email
   - Job title (rôle)
   - **Liste des applications provisionnées** (max 3 visibles, "+X" si plus)
   - Date de completion
   - Badge de statut (Succès/Échec/Partiel/En cours)

---

## 🧪 Tests

### Test Backend - Applications Disponibles
```bash
curl http://localhost:8001/api/v1/midpoint/applications
```
**Résultat attendu :**
```json
{
  "status": "success",
  "applications": [
    {"name": "Keycloak", "description": "Single Sign-On (SSO)"},
    {"name": "LDAP", "description": "Annuaire LDAP"},
    ...
  ]
}
```

### Test Backend - Provisioning avec Sélection
```bash
curl -X POST http://localhost:8001/api/v1/midpoint/provision \
  -H "Content-Type: application/json" \
  -d '{
    "user_oid": "0f29757d-a3f6-4dcb-8757-91fda4d6e9a4",
    "applications": ["Keycloak", "LDAP"]
  }'
```
**Résultat attendu :**
```json
{
  "status": "success",
  "message": "Utilisateur 1001 provisionné avec succès",
  "total_actions": 2,  // Seulement 2 au lieu de toutes
  "successful_actions": 2
}
```

### Test Backend - Opérations Récentes avec Actions
```bash
curl 'http://localhost:8001/api/v1/operations/recent?limit=1'
```
**Résultat attendu :**
```json
[
  {
    "id": 59,
    "user": {...},
    "actions": [
      {"application": "Keycloak", "status": "success", ...}
    ],
    ...
  }
]
```

---

## 🐛 Bugs Corrigés

### 1. Erreur "Missing required field: job_title"
**Problème :** Les utilisateurs MidPoint sans champ `title` causaient une erreur de validation

**Solution :**
```python
job_title = user.get('title') or user.get('fullName') or 'Employee'
if not job_title or job_title.strip() == '':
    job_title = 'Employee'
```

### 2. Endpoint operations en double
**Problème :** Création d'un nouveau fichier `/app/routers/operations.py` alors qu'un endpoint existait déjà dans `/app/api/routes.py`

**Solution :** Suppression du fichier doublon et amélioration de l'endpoint existant avec les actions

---

## 📦 Fichiers Modifiés

### Backend (6 fichiers)
1. ✅ `/app/core/role_mapper.py` - Ajout `get_all_applications()`
2. ✅ `/app/services/provisioning_service.py` - Paramètre `selected_applications`
3. ✅ `/app/routers/midpoint.py` - Endpoint `/applications` + bug fix job_title
4. ✅ `/app/api/routes.py` - Endpoint `/operations/recent` avec actions
5. ✅ `/app/main.py` - Import nettoyé (pas de doublon operations)

### Frontend (3 fichiers)
1. ✅ `/frontend/src/pages/Provisioning.jsx` - Modal de sélection d'applications
2. ✅ `/frontend/src/pages/Provisioning.css` - Styles du modal (~150 lignes)
3. ✅ `/frontend/src/components/dashboard/RecentOperations.jsx` - Refonte pour nouveau format

---

## 🚀 Commandes de Déploiement

Les serveurs sont déjà en cours d'exécution avec auto-reload :

```bash
# Backend (port 8001)
cd /srv/projet/aegis-gateway
source venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload

# Frontend (port 5173)
cd /srv/projet/aegis-gateway/frontend
npm run dev
```

**Rechargement automatique :** Les modifications sont prises en compte sans redémarrage manuel.

---

## ✨ Fonctionnalités Additionnelles

### Sélection par défaut
- **Toutes les applications cochées par défaut** lors de l'ouverture du modal
- Permet de désélectionner rapidement ce qui n'est pas nécessaire

### Compteur dynamique
- Le bouton "Provisionner" affiche le nombre d'apps sélectionnées : `Provisionner (3 apps)`
- Désactivé si aucune application n'est sélectionnée

### Animations
- Modal avec effet de fondu et slide-up
- Hover effects sur les checkboxes
- Spinning loader pendant le provisioning

### Messages utilisateur
- Message de succès avec nombre exact d'applications : "✅ Utilisateur provisionné avec succès vers 2 application(s)"
- Message d'erreur détaillé en cas d'échec

---

## 📚 Documentation API

### Nouveaux endpoints

#### `GET /api/v1/midpoint/applications`
**Description :** Récupère la liste des applications métiers disponibles

**Réponse :**
```json
{
  "status": "success",
  "applications": [
    {"name": "Keycloak", "description": "Single Sign-On (SSO)"},
    {"name": "LDAP", "description": "Annuaire LDAP"}
  ]
}
```

#### `POST /api/v1/midpoint/provision` (modifié)
**Description :** Provisionne un utilisateur MidPoint vers des applications sélectionnées

**Body :**
```json
{
  "user_oid": "0f29757d-a3f6-4dcb-8757-91fda4d6e9a4",
  "applications": ["Keycloak", "LDAP"]  // NOUVEAU : vide = toutes
}
```

**Réponse :**
```json
{
  "status": "success",
  "message": "Utilisateur 1001 provisionné avec succès",
  "operation_id": 58,
  "total_actions": 2,
  "successful_actions": 2,
  "failed_actions": 0
}
```

#### `GET /api/v1/operations/recent?limit=5` (modifié)
**Description :** Récupère les dernières opérations avec détails des actions

**Nouveau champ dans la réponse :**
```json
{
  "actions": [
    {
      "application": "Keycloak",
      "status": "success",
      "message": "[MOCK] User created in Keycloak (no connector)"
    }
  ]
}
```

---

## 🎨 Captures d'écran

### Modal de Sélection d'Applications
```
┌─────────────────────────────────────────────────────┐
│ Sélectionner les applications à provisionner    ×  │
├─────────────────────────────────────────────────────┤
│ Choisissez les applications métiers pour cet       │
│ utilisateur. Les applications cochées seront       │
│ provisionnées.                                      │
│                                                     │
│ ☑ Keycloak        Single Sign-On (SSO)            │
│ ☑ LDAP            Annuaire LDAP                   │
│ ☑ Odoo            ERP Odoo                        │
│ ☐ GitLab          Gestion du code source         │
│ ☐ PostgreSQL      Base de données                │
│ ☐ Mattermost      Communication                  │
│ ☐ CRM             Gestion clients                │
│ ☐ SecureHR        Ressources humaines            │
│                                                     │
│              [Annuler]  [👤 Provisionner (3 apps)]  │
└─────────────────────────────────────────────────────┘
```

### Dashboard - Dernières Opérations
```
┌─────────────────────────────────────────────────────────────────────────┐
│ Dernières Opérations de Provisioning                      [Voir tout]   │
├─────────────────────────────────────────────────────────────────────────┤
│ Utilisateur         Job Title     Applications    Date       Statut     │
├─────────────────────────────────────────────────────────────────────────┤
│ 🔵 Jeffrey Kelly    Marketing     [Keycloak]     30 jan.    ✅ Succès  │
│    jeffrey.kel...   Manager                      11:07                  │
│                                                                          │
│ 🔵 Mitchell Admin   CEO           [LDAP]         30 jan.    ✅ Succès  │
│    admin@yourco...                [Keycloak]     11:07                  │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 🔮 Améliorations Futures

1. **Auto-refresh du dashboard** - Rafraîchissement automatique toutes les 5 secondes
2. **Progress bar en temps réel** - Barre de progression pendant le provisioning multi-applications
3. **Notifications push** - WebSocket pour notifier la fin du provisioning
4. **Historique détaillé** - Page dédiée avec timeline pour chaque opération
5. **Filtres avancés** - Filtrer les opérations par statut, utilisateur, date, application
6. **Export CSV** - Télécharger l'historique des opérations

---

## 📞 Support

Pour toute question ou problème :
- Vérifier les logs backend : `tail -f /srv/projet/aegis-gateway/logs/app.log`
- Vérifier les logs frontend : Console navigateur (F12)
- Tester les endpoints avec `curl` comme montré ci-dessus

---

**Dernière mise à jour :** 30 Janvier 2026, 12:15 UTC
**Version Backend :** 0.2.0
**Version Frontend :** 0.2.0
