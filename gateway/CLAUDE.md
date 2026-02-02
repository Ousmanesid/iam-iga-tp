# CLAUDE.md — Mémoire Projet AEGIS Gateway

> **Document de contexte permanent pour IA**  
> Version: 2.0 | Dernière mise à jour: 30 Janvier 2026  
> Projet académique BUT Informatique 3ème année

---

## 📋 Table des matières

1. [Project Overview](#-project-overview)
2. [Global Architecture](#-global-architecture)
3. [Tech Stack](#-tech-stack)
4. [Backend Structure](#-backend-structure)
5. [Frontend Structure](#-frontend-structure)
6. [Database Schema](#-database-schema)
7. [Core Features Implémentées](#-core-features-implémentées)
8. [Intégrations Externes](#-intégrations-externes)
9. [Système de Notification](#-système-de-notification)
10. [Fonctionnalités Hors Scope](#-fonctionnalités-hors-scope)
11. [Règles pour l'IA](#-règles-pour-lia)
12. [Conventions de Code](#-conventions-de-code)
13. [Commandes Utiles](#-commandes-utiles)
14. [Dernières Modifications](#-dernières-modifications)

---

## 🎯 Project Overview

### Qu'est-ce qu'AEGIS Gateway ?

**AEGIS Gateway** est une plateforme de gestion des identités et des accès (IAM/IGA) développée dans un cadre académique. Elle automatise le cycle de vie des comptes employés au sein d'une organisation.

### Objectif Principal

Automatiser le **provisioning** (création de comptes) et le **deprovisioning** (suppression de comptes) des employés à partir d'une source RH (Odoo), avec :
- Synchronisation automatique depuis Odoo (source RH)
- Attribution automatique des rôles basée sur MidPoint (IAM central)
- Provisioning vers les systèmes cibles (LDAP, Odoo, Keycloak)
- Notifications automatiques aux utilisateurs avec leurs accès
- Tableau de bord de supervision en temps réel
- Historique et audit des opérations
- **Chargement des identités depuis PostgreSQL MidPoint** (fallback si API REST indisponible)

### Ce que fait AEGIS

| Fonctionnalité | Description |
|----------------|-------------|
| **Onboarding automatique** | Un nouvel employé dans Odoo → synchronisé vers MidPoint → provisionné vers applications |
| **Role Mapping dynamique** | Rôles chargés depuis MidPoint via API (pas de mappings hardcodés) |
| **Dashboard temps réel** | Vue des opérations, statistiques, alertes |
| **Audit Trail** | Historique complet de toutes les actions |
| **Intégration MidPoint** | Connexion au moteur IAM MidPoint pour la gestion centralisée des rôles |
| **Notifications utilisateurs** | Email automatique avec accès, credentials et instructions |
| **Statut des connecteurs** | Monitoring en temps réel (MidPoint, Odoo, LDAP) |
| **Provisioning MidPoint** | Charge 53+ identités depuis PostgreSQL et provisionne vers apps métiers |

### Ce que le projet NE CHERCHE PAS à faire

- ❌ Remplacer un IAM enterprise complet (SailPoint, Saviynt)
- ❌ Gérer la réconciliation avancée des comptes
- ❌ Implémenter une sécurité de niveau production
- ❌ Supporter le multi-tenant
- ❌ Gérer des workflows d'approbation complexes
- ❌ **Créer des identités directement** (création uniquement via Odoo/MidPoint)

> **Note importante** : C'est un MVP pédagogique, pas un produit enterprise.
> **Workflow de création** : Odoo (RH) → MidPoint (IAM) → Gateway (Provisioning vers apps)

---

## 🏗 Global Architecture

### Vue d'ensemble des flux

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            SOURCES DE DONNÉES                                │
│  ┌─────────────┐     ┌─────────────┐     ┌─────────────┐                    │
│  │    Odoo     │     │  MidPoint   │     │   CSV/API   │                    │
│  │   (RH)      │     │   (IAM)     │     │  (Import)   │                    │
│  └──────┬──────┘     └──────┬──────┘     └──────┬──────┘                    │
│         │                   │                   │                            │
└─────────┼───────────────────┼───────────────────┼────────────────────────────┘
          │                   │                   │
          ▼                   ▼                   ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         AEGIS GATEWAY (Backend)                              │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                           FastAPI Server                             │   │
│  │                         (Port 8001)                                  │   │
│  ├─────────────────────────────────────────────────────────────────────┤   │
│  │                                                                       │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐ │   │
│  │  │   Routers   │  │  Services   │  │ Connectors  │  │    Core     │ │   │
│  │  │ (API REST)  │  │ (Logique)   │  │ (Intégr.)   │  │  (Config)   │ │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘ │   │
│  │                                                                       │   │
│  │  ┌───────────────────────────────────────────────────────────────┐   │   │
│  │  │                    SQLite Database                             │   │   │
│  │  │  (ProvisionedUser, ProvisioningOperation, ProvisioningAction)  │   │   │
│  │  └───────────────────────────────────────────────────────────────┘   │   │
│  │                                                                       │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
└──────────────────────────────────┬───────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         FRONTEND (React + Vite)                              │
│                              (Port 5174)                                     │
│                                                                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │  Dashboard  │  │ Operations  │  │   Roles     │  │   Audit     │        │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘        │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         SYSTÈMES CIBLES                                      │
│  ┌─────────────┐     ┌─────────────┐     ┌─────────────┐                    │
│  │    LDAP     │     │  Keycloak   │     │    Odoo     │                    │
│  │  (Comptes)  │     │   (SSO)     │     │  (Accès)    │                    │
│  └─────────────┘     └─────────────┘     └─────────────┘                    │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Responsabilités par couche

| Couche | Responsabilité |
|--------|----------------|
| **Frontend** | Interface utilisateur, visualisation, formulaires |
| **Routers** | Points d'entrée API REST, validation des requêtes |
| **Services** | Logique métier, orchestration, synchronisation |
| **Connectors** | Communication avec les systèmes externes |
| **Database** | Persistance, historique, état des utilisateurs |

---

## 🛠 Tech Stack

### Stack imposée (NE PAS MODIFIER)

| Composant | Technologie | Version | Justification |
|-----------|-------------|---------|---------------|
| **Backend** | FastAPI (Python) | 3.11+ | Framework async moderne, documentation auto |
| **Frontend** | React + Vite | React 18, Vite 5.4 | SPA moderne, hot reload rapide |
| **Base de données** | SQLite | 3.x | Développement simple, pas de serveur |
| **ORM** | SQLAlchemy | 2.x | Mapping objet-relationnel standard |
| **HTTP Client** | httpx | 0.x | Client HTTP async pour Python |
| **Auth** | JWT simple | - | Authentification stateless basique |
| **Icônes** | Lucide React | - | Pack d'icônes moderne et léger |

### Dépendances Backend (`requirements.txt`)

```
fastapi>=0.109.0
uvicorn[standard]>=0.27.0
sqlalchemy>=2.0.0
pydantic>=2.0.0
pydantic-settings>=2.0.0
python-jose[cryptography]>=3.3.0
passlib[bcrypt]>=1.7.4
python-multipart>=0.0.6
httpx>=0.26.0
```

### Dépendances Frontend (`package.json`)

```json
{
  "dependencies": {
    "react": "^18.3.1",
    "react-dom": "^18.3.1",
    "react-router-dom": "^7.1.1",
    "axios": "^1.7.9",
    "lucide-react": "^0.469.0"
  }
}
```

---

## 📁 Backend Structure

```
app/
├── main.py                    # Point d'entrée FastAPI
├── __init__.py
│
├── api/
│   └── routes.py              # Routes API principales (/api/v1/*)
│
├── routers/                   # Routes spécialisées
│   ├── health.py              # Health checks
│   ├── odoo.py                # Endpoints Odoo (/api/v1/odoo/*)
│   ├── roles.py               # Gestion des rôles MidPoint
│   └── sync.py                # Synchronisation
│
├── services/                  # Logique métier
│   ├── odoo_service.py        # Client Odoo XML-RPC
│   ├── odoo_sync_service.py   # Sync Odoo → Aegis
│   ├── midpoint_service.py    # Client MidPoint REST
│   ├── midpoint_role_service.py  # Gestion rôles MidPoint
│   ├── provisioning_service.py   # Orchestration provisioning
│   └── sync_service.py        # Service de synchronisation
│
├── connectors/                # Intégrations externes
│   ├── base.py                # Classe abstraite + MockConnector
│   └── keycloak.py            # Connecteur Keycloak
│
├── core/                      # Configuration centrale
│   ├── config.py              # Settings (Pydantic)
│   ├── role_mapper.py         # Mapping Job Title → Applications
│   └── security.py            # JWT, auth
│
├── database/                  # Persistance
│   ├── models.py              # Modèles SQLAlchemy
│   └── connection.py          # Session factory
│
└── models/                    # Modèles Pydantic (schemas)
```

### Fichiers clés et leur rôle

| Fichier | Rôle |
|---------|------|
| `main.py` | Bootstrap FastAPI, CORS, routes |
| `api/routes.py` | Endpoints principaux : `/stats`, `/operations`, `/users` |
| `services/odoo_sync_service.py` | Synchronise employés Odoo → base locale |
| `core/role_mapper.py` | Mappe "Développeur" → [GitLab, Keycloak, etc.] |
| `core/config.py` | Variables d'environnement, settings |
| `database/models.py` | Schémas BDD : ProvisionedUser, ProvisioningOperation |

---

## 🎨 Frontend Structure

```
frontend/src/
├── main.jsx                   # Point d'entrée React
├── App.jsx                    # Routing principal
├── theme.css                  # Variables CSS globales
│
├── api/                       # Services API
│   ├── axiosClient.js         # Client Axios configuré
│   ├── provisioningService.js # Appels API provisioning
│   └── rolesService.js        # Appels API rôles MidPoint
│
├── layouts/                   # Layouts
│   ├── AdminLayout.jsx        # Layout admin (sidebar + header)
│   └── AdminLayout.css
│
├── pages/                     # Pages principales
│   ├── Dashboard.jsx          # Page d'accueil avec stats
│   ├── Operations.jsx         # Liste des opérations
│   ├── OperationDetail.jsx    # Détail d'une opération
│   ├── Provisioning.jsx       # Formulaire création utilisateur
│   ├── Roles.jsx              # Gestion des rôles MidPoint
│   └── Audit.jsx              # Logs d'audit
│
├── components/
│   ├── layout/
│   │   ├── Sidebar.jsx        # Navigation latérale
│   │   └── Header.jsx         # Barre supérieure
│   │
│   └── dashboard/             # Composants Dashboard
│       ├── StatCard.jsx       # Carte de statistique
│       ├── RecentOperations.jsx  # Liste opérations récentes
│       ├── OperationTimeline.jsx # Timeline visuelle
│       └── OperationSummary.jsx  # Résumé opération
```

### Pages principales

| Page | Route | Description |
|------|-------|-------------|
| **Dashboard** | `/` | KPIs, opérations récentes, bouton sync Odoo |
| **Operations** | `/operations` | Liste filtrable de toutes les opérations |
| **OperationDetail** | `/operations/:id` | Détail complet d'une opération |
| **Provisioning** | `/provisioning` | Formulaire de création manuelle |
| **Roles** | `/roles` | Gestion des rôles MidPoint |
| **Audit** | `/audit` | Historique des actions système |

---

## 🗃 Database Schema

### Tables principales

```
┌─────────────────────────────────────────────────────────────────┐
│                      provisioned_users                           │
├─────────────────────────────────────────────────────────────────┤
│ id              │ INTEGER PRIMARY KEY                           │
│ email           │ VARCHAR(255) UNIQUE NOT NULL                  │
│ first_name      │ VARCHAR(100) NOT NULL                         │
│ last_name       │ VARCHAR(100) NOT NULL                         │
│ job_title       │ VARCHAR(200)                                  │
│ department      │ VARCHAR(100)                                  │
│ role            │ VARCHAR(100)        # Rôle mappé              │
│ status          │ VARCHAR(50)         # pending/success/failed  │
│ source          │ VARCHAR(50)         # api/odoo_sync/manual    │
│ created_at      │ DATETIME                                      │
│ updated_at      │ DATETIME                                      │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ 1:N
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                   provisioning_operations                        │
├─────────────────────────────────────────────────────────────────┤
│ id              │ INTEGER PRIMARY KEY                           │
│ user_id         │ INTEGER FOREIGN KEY → provisioned_users       │
│ status          │ VARCHAR(50)         # in_progress/success/... │
│ trigger         │ VARCHAR(50)         # api/odoo_sync/manual    │
│ started_at      │ DATETIME                                      │
│ completed_at    │ DATETIME                                      │
│ total_actions   │ INTEGER                                       │
│ successful_actions │ INTEGER                                    │
│ failed_actions  │ INTEGER                                       │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ 1:N
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    provisioning_actions                          │
├─────────────────────────────────────────────────────────────────┤
│ id              │ INTEGER PRIMARY KEY                           │
│ operation_id    │ INTEGER FOREIGN KEY → provisioning_operations │
│ application     │ VARCHAR(100)        # Keycloak, GitLab, etc.  │
│ action          │ VARCHAR(50)         # create_account, etc.    │
│ status          │ VARCHAR(50)         # pending/success/failed  │
│ started_at      │ DATETIME                                      │
│ completed_at    │ DATETIME                                      │
│ error_message   │ TEXT                                          │
└─────────────────────────────────────────────────────────────────┘
```

### Enum Status

```python
class OperationStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    SUCCESS = "success"
    FAILED = "failed"
    PARTIAL = "partial"  # Certaines actions OK, d'autres KO
```

---

## ✅ Core Features Implémentées

### 1. Synchronisation Odoo (Onboarding)

**Flux** : Odoo → Aegis Gateway → Base locale

```
1. Utilisateur clique "Synchroniser Odoo" dans Dashboard
2. Backend appelle Odoo XML-RPC (hr.employee)
3. Pour chaque employé :
   a. Vérifie si existe dans provisioned_users
   b. Si non → Crée l'utilisateur + ProvisioningOperation
   c. Si oui → Met à jour si modifié
4. Dashboard affiche "X créés, Y mis à jour"
```

**Endpoint** : `POST /api/v1/odoo/sync`

### 2. Role Mapping

**Logique** : Job Title → Liste d'applications

```python
ROLE_MAPPINGS = {
    "Développeur": [Keycloak, GitLab, Mattermost, Notion],
    "Commercial": [Keycloak, Odoo, CRM],
    "RH Manager": [Keycloak, Odoo, SecureHR],
    # ...
}
```

Le mapping se fait automatiquement lors de la synchronisation ou du provisioning manuel.

### 3. Dashboard

**KPIs affichés** :
- Total utilisateurs provisionnés
- Opérations aujourd'hui
- Taux de succès (%)
- Échecs critiques

**Fonctionnalités** :
- Bouton "Synchroniser Odoo" avec feedback immédiat
- Liste des opérations récentes
- Navigation vers détails

### 4. Gestion des Opérations

**Liste** (`/operations`) :
- Filtres : Tous, Succès, Échecs, Partiels, En cours
- Recherche par nom/email
- Pagination

**Détail** (`/operations/:id`) :
- Timeline des actions
- Statut par application
- Messages d'erreur

### 5. Gestion des Rôles (MidPoint)

**Interface** (`/roles`) :
- Liste des rôles avec niveau de risque
- Visualisation des inducements (permissions)
- Mode édition avec recherche de permissions
- Connexion API MidPoint (avec fallback local)

### 6. Audit

**Logs affichés** :
- Timestamp, Acteur, Action, Cible
- Niveau : INFO, WARNING, ERROR, CRITICAL
- Filtres par niveau et période

---

## 🔌 Intégrations Externes

### Odoo (Source RH)

| Paramètre | Valeur par défaut |
|-----------|-------------------|
| URL | `http://localhost:8069` |
| Database | `odoo` |
| Protocol | XML-RPC |
| Modèle | `hr.employee` |

**Champs récupérés** : `name`, `work_email`, `job_title`, `department_id`

### MidPoint (IAM Engine)

| Paramètre | Valeur par défaut |
|-----------|-------------------|
| URL | `http://localhost:8080/midpoint` |
| Protocol | REST API |
| Auth | Basic (administrator/5ecr3t) |

**Fonctionnalités** :
- Récupération des rôles
- Assignation/retrait de rôles
- Déclenchement de tasks

### Keycloak (SSO) - Optionnel

| Paramètre | Valeur par défaut |
|-----------|-------------------|
| URL | `http://localhost:8180` |
| Protocol | REST Admin API |

---

## 🚫 Fonctionnalités Hors Scope

Ces fonctionnalités ne doivent **PAS** être proposées :

| Fonctionnalité | Raison |
|----------------|--------|
| **Réconciliation avancée** | Trop complexe pour un MVP |
| **Workflows d'approbation** | Hors périmètre académique |
| **Multi-tenant** | Architecture single-tenant |
| **Sécurité enterprise** | Mode démo avec auth simple |
| **Audit SOX/GDPR** | Conformité hors scope |
| **Intégration SCIM** | Protocole trop avancé |
| **Connecteurs custom** | Architecture fixée |
| **HA / Clustering** | Environnement de dev |

---

## 🤖 Règles pour l'IA

### TOUJOURS

1. **Respecter la stack existante** : FastAPI, React, SQLite
2. **Suivre l'architecture en couches** : Routers → Services → Connectors
3. **Utiliser les modèles existants** : ProvisionedUser, ProvisioningOperation
4. **Maintenir la compatibilité API** : Ne pas casser les endpoints existants
5. **Préférer des solutions simples** : Pas d'over-engineering
6. **Documenter les changements** : Docstrings, commentaires
7. **Gérer les erreurs** : Try/except, logging approprié

### JAMAIS

1. **Changer la stack** : Pas de migration vers Django, GraphQL, etc.
2. **Proposer du hors scope** : Pas de multi-tenant, Kubernetes, etc.
3. **Refactorer sans demande** : Pas de restructuration globale
4. **Ajouter des dépendances lourdes** : Pas de Celery, Redis, Kafka
5. **Complexifier l'auth** : JWT simple suffit
6. **Ignorer le contexte pédagogique** : C'est un projet BUT3

### Priorités

```
1. Fonctionnel > Performant
2. Simple > Élégant  
3. Explicite > Implicite
4. Pédagogique > Optimal
```

---

## 📝 Conventions de Code

### Python (Backend)

```python
# Imports groupés
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

# Docstrings françaises
def sync_employees(db: Session) -> Dict:
    """
    Synchronise les employés depuis Odoo.
    
    Args:
        db: Session SQLAlchemy
        
    Returns:
        Dict avec statistiques de sync
    """
    pass

# Logging systématique
logger.info(f"✅ Synchronisation terminée: {count} employés")
logger.error(f"❌ Erreur: {e}")

# Emoji dans les logs pour lisibilité
# ✅ Succès | ❌ Erreur | ⚠️ Warning | 🔄 En cours | 📊 Stats
```

### React (Frontend)

```jsx
// Composants fonctionnels avec hooks
export default function Dashboard() {
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(true);
  
  useEffect(() => {
    loadData();
  }, []);
  
  return (
    <div className="dashboard">
      {/* JSX */}
    </div>
  );
}

// CSS modules par composant
// Dashboard.jsx → Dashboard.css
```

### API Endpoints

```
GET    /api/v1/stats              # KPIs dashboard
GET    /api/v1/operations         # Liste opérations
GET    /api/v1/operations/{id}    # Détail opération
POST   /api/v1/users              # Créer utilisateur
POST   /api/v1/odoo/sync          # Sync Odoo
GET    /api/v1/roles              # Liste rôles MidPoint
GET    /health                    # Health check
```

---

## 🚀 Commandes Utiles

### Démarrage

```bash
# Backend
cd /srv/projet/aegis-gateway
source venv/bin/activate
./start_backend.sh
# ou: uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload

# Frontend
cd frontend
npm run dev -- --host --port 5174
```

### Vérification

```bash
# Health check
curl http://localhost:8001/health

# Stats dashboard
curl http://localhost:8001/api/v1/stats

# Sync Odoo
curl -X POST http://localhost:8001/api/v1/odoo/sync

# Liste rôles
curl http://localhost:8001/api/v1/roles
```

### Base de données

```bash
# Voir les utilisateurs
sqlite3 aegis.db "SELECT email, first_name, source FROM provisioned_users LIMIT 10;"

# Compter les opérations
sqlite3 aegis.db "SELECT status, COUNT(*) FROM provisioning_operations GROUP BY status;"
```

### Logs

```bash
# Backend logs
tail -f /srv/projet/aegis-gateway/backend.log

# Frontend (dans le terminal npm)
# Affiche automatiquement les erreurs
```

---

## 📊 État Actuel du Projet

### Fonctionnel ✅

- [x] Dashboard avec KPIs temps réel
- [x] Synchronisation Odoo → Aegis
- [x] Liste et détail des opérations
- [x] Page Provisioning depuis MidPoint (53 utilisateurs)
- [x] Page Roles (intégration MidPoint dynamique)
- [x] Page Audit (logs)
- [x] Role Mapping automatique depuis MidPoint
- [x] API REST complète
- [x] **Système de notification par email** (SMTP + fichiers /tmp en dev)
- [x] **Statut des connecteurs en temps réel** (MidPoint, Odoo, LDAP)
- [x] **Chargement depuis PostgreSQL MidPoint** (fallback API)
- [x] **Formulaire de création désactivé** (création uniquement Odoo/MidPoint)

### En développement 🟡

- [ ] Assistant IA explicatif (page placeholder)
- [ ] Provisioning réel vers Keycloak
- [ ] Provisioning réel vers LDAP

### Non prévu ❌

- [ ] Multi-tenant
- [ ] Workflows d'approbation
- [ ] Réconciliation avancée
- [ ] Création directe d'utilisateurs (désactivé volontairement)

---

## 🔐 Variables d'Environnement

Fichier `.env` à la racine du backend :

```env
# Database
DATABASE_URL=sqlite:///./aegis.db

# Odoo
ODOO_URL=http://localhost:8069
ODOO_DB=odoo
ODOO_USERNAME=admin
ODOO_PASSWORD=admin

# MidPoint (optionnel)
MIDPOINT_URL=http://localhost:8080/midpoint
MIDPOINT_USERNAME=administrator


MIDPOINT_PASSWORD=Test5ecr3t

# Keycloak (optionnel)
KEYCLOAK_URL=http://localhost:8180
KEYCLOAK_ADMIN=admin
KEYCLOAK_PASSWORD=admin

# SMTP pour notifications (optionnel)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_FROM_EMAIL=noreply@aegis.local

# Security
SECRET_KEY=your-secret-key-here
DEMO_MODE=true
DEMO_TOKEN=aegis-demo-2024
```

---

## 📚 Ressources Associées

| Ressource | Emplacement |
|-----------|-------------|
| Config MidPoint | `/srv/projet/iam-iga-tp/config/midpoint/` |
| Rôles MidPoint XML | `/srv/projet/iam-iga-tp/config/midpoint/roles/` |
| Docker Compose | `/srv/projet/iam-iga-tp/docker/docker-compose.yml` |
| Scripts utilitaires | `/srv/projet/aegis-gateway/scripts/` |

---

## 🎓 Contexte Académique

**Formation** : BUT Informatique 3ème année  
**Module** : IAM / IGA (Identity & Access Management)  
**Objectif pédagogique** : Comprendre les concepts IAM à travers l'implémentation

Ce projet doit rester :
- **Compréhensible** par un étudiant BUT3
- **Explicable** lors d'une soutenance
- **Fonctionnel** comme MVP démontrable
- **Simple** dans son architecture

---

## 🔄 Dernières Modifications (30 Janvier 2026)

### 1. Système de Notification ✉️

**Fichiers créés:**
- `app/services/notification_service.py`
- `app/routers/notifications.py`

**Fonctionnalités:**
- Email automatique après provisionnement avec détails des accès
- Modes: Production (SMTP) / Dev (fichiers /tmp)
- Template avec credentials, URLs, rôles par application
- Endpoints: `/notifications/test`, `/notifications/status`

### 2. Monitoring Connecteurs 🔌

**Fichier créé:** `app/routers/connectors.py`

**Fonctionnalités:**
- Statut temps réel: MidPoint IAM, Odoo ERP, LDAP
- Endpoint: `GET /api/v1/connectors/status`
- Affichage frontend avec cartes visuelles

### 3. Chargement PostgreSQL MidPoint 🗄

**Problème:** API REST MidPoint retourne 401

**Solution:** Fallback automatique vers PostgreSQL
- Connexion directe `docker_midpoint_data_1`
- SQL sur table `m_user`
- **53 utilisateurs** chargés avec succès
- Modifié: `app/services/midpoint_service.py`

### 4. Rôles Dynamiques 🎭

**Changement majeur:** Suppression mappings hardcodés

**Modifications:**
- `app/core/role_mapper.py` - Rôles depuis MidPoint API
- Cache 5 minutes, endpoint `/roles/refresh`
- Plus de `JobTitle` enum hardcodé

### 5. Désactivation Création Directe 🚫

**Philosophie:** Création UNIQUEMENT Odoo/MidPoint

**Modifications:**
- Endpoint `POST /api/v1/provision` → 404
- Frontend: Formulaire masqué
- Nouveau titre: "Provisioning depuis MidPoint"
- Workflow: Odoo → MidPoint → Gateway → Apps

### 6. Frontend Page Provisioning 🎨

**Sections ajoutées:**
- Statut des connecteurs (3 cartes)
- Table 53 utilisateurs MidPoint
- Boutons provisionnement par user
- +200 lignes CSS

### 7. Corrections ⚙️

- Password MidPoint: `Test5ecr3t` (partout)
- Import `Optional` dans config.py
- Tests Accept headers MidPoint API

### 8. Refonte UI/UX (Réagencement) 🎨
- **Sidebar** : Support thème sombre/pro, meilleur UX
- **Layout Provisioning** : 
  - Nouvelle structure "Dashboard Grid" (Main + Sidebar)
  - Promotion de la table utilisateurs en contenu principal
  - Widgets latéraux pour l'état et l'aide
  - Nettoyage du formulaire obsolète

---

## 🎯 Points d'Attention pour l'IA

### Règles Strictes

1. **JAMAIS créer endpoint de création utilisateur**
   - Création UNIQUEMENT via Odoo/MidPoint

2. **TOUJOURS utiliser rôles MidPoint**
   - Ne JAMAIS hardcoder mappings
   - Appeler `_get_midpoint_roles()`

3. **Password MidPoint = `Test5ecr3t`**

4. **Fallback PostgreSQL obligatoire**
   - API MidPoint peut échouer

5. **Notifications = optionnel**
   - Ne JAMAIS bloquer provisionnement

---

> **Pour toute modification, vérifier la cohérence avec ce document.**  
> **En cas de doute, demander clarification plutôt que deviner.**

