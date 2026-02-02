# 🚀 GUIDE PROVISIONING CSV → MIDPOINT

## Vue d'ensemble

Ce guide décrit le processus complet d'import des données RH depuis un fichier CSV vers MidPoint avec auto-assignment automatique des rôles.

---

## 📋 Architecture

```
┌─────────────────┐
│   hr_raw.csv    │  ← Source de données RH (15 employés)
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────────────┐
│  2 Options d'import:                    │
│                                         │
│  A) Script Python (import_hr_csv.py)   │
│     → API REST directe                  │
│                                         │
│  B) Task MidPoint (task-hr-import.xml) │
│     → Via ressource CSV connector       │
└─────────────────┬───────────────────────┘
                  │
                  ▼
         ┌────────────────┐
         │    MidPoint    │
         │   - Utilisateurs créés
         │   - Object Template appliqué
         │   - Rôles auto-assignés
         └────────────────┘
```

---

## 🗂️ Fichiers impliqués

### 1. Configuration MidPoint

| Fichier | Description | Status |
|---------|-------------|--------|
| [resource-hr-csv.xml](config/midpoint/resources/resource-hr-csv.xml) | Ressource CSV avec connecteur | ✅ Configuré pour hr_raw.csv |
| [task-hr-import.xml](config/midpoint/tasks/task-hr-import.xml) | Task de réconciliation périodique | ✅ Corrigé (mode reconciliation) |
| [object-template-user.xml](config/midpoint/object-templates/object-template-user.xml) | Template avec auto-assignment | ✅ Rôles par département |

### 2. Données

| Fichier | Description | Format |
|---------|-------------|--------|
| [hr_raw.csv](data/hr/hr_raw.csv) | Données RH (15 employés) | personalNumber, givenName, familyName, email, department, title, status |
| ~~hr_clean.csv~~ | ❌ **SUPPRIMÉ** (ancien format) | - |

### 3. Scripts d'automatisation

| Fichier | Description | Usage |
|---------|-------------|-------|
| [import_hr_csv.py](scripts/import_hr_csv.py) | Import direct via API REST | `python3 import_hr_csv.py` |
| [trigger_import_task.py](scripts/trigger_import_task.py) | Déclenchement manuel de la task | `python3 trigger_import_task.py --wait` |

---

## 🔧 Prérequis

### 1. MidPoint configuré

```bash
# Vérifier que MidPoint est démarré
docker ps | grep midpoint

# Accès: http://localhost:8080/midpoint
# Login: administrator / 5ecr3t
```

### 2. Objets MidPoint importés

Dans MidPoint, importer dans cet ordre (voir [GUIDE_IMPORT_MANUEL.md](GUIDE_IMPORT_MANUEL.md)):
1. ✅ Ressources (6 fichiers) - dont `resource-hr-csv.xml`
2. ✅ Rôles (11 fichiers) - Employee, IT Admin, Agent Commercial, RH Manager, etc.
3. ✅ Object Template (1 fichier) - `object-template-user.xml`
4. ✅ Tâches (1 fichier) - `task-hr-import.xml`

### 3. Dépendances Python

```bash
pip3 install httpx
```

---

## 🚀 Méthodes d'import

### Méthode A: Script Python (Recommandé pour dev/test)

**Avantages:**
- ✅ Contrôle total sur l'import
- ✅ Feedback immédiat et détaillé
- ✅ Mode dry-run pour tester
- ✅ Recompute forcé après chaque utilisateur

**Usage:**

```bash
cd /srv/projet/iam-iga-tp/scripts

# 1. Test en simulation (aucune modification)
python3 import_hr_csv.py --dry-run

# 2. Import réel
python3 import_hr_csv.py

# 3. Avec options
python3 import_hr_csv.py \
  --csv-path /chemin/custom.csv \
  --midpoint-url http://midpoint:8080/midpoint
```

**Output exemple:**
```
============================================================
🚀 HR CSV Import Script
============================================================
🔗 Testing connection to http://localhost:8080/midpoint...
✅ Connected to MidPoint
📂 Reading CSV from /srv/projet/iam-iga-tp/data/hr/hr_raw.csv...
✅ 15 employés lus depuis /srv/projet/iam-iga-tp/data/hr/hr_raw.csv
📥 Importing 15 employees...
📋 Processing: Jean Dupont (1001)
   ✨ Creating new user...
   ✅ Created user Jean Dupont (OID: abc123...)
   🔄 Recomputed roles for Jean Dupont
============================================================
📊 Import Results:
   Total employees: 15
   ✨ Created: 15
   ♻️  Updated: 0
   ❌ Errors: 0
============================================================
✅ Import completed successfully!
```

---

### Méthode B: Task MidPoint (Recommandé pour production)

**Avantages:**
- ✅ Intégré à MidPoint (réconciliation périodique)
- ✅ Automatique (toutes les 60 secondes)
- ✅ Logs MidPoint natifs

**Usage:**

```bash
cd /srv/projet/iam-iga-tp/scripts

# Déclencher manuellement et attendre le résultat
python3 trigger_import_task.py --wait

# Ou juste déclencher (sans attendre)
python3 trigger_import_task.py
```

**Vérification dans MidPoint UI:**
- Menu: **Server Tasks** → **List Tasks**
- Chercher: "HR CSV Import Task"
- Statut: Running → Closed
- Cliquer sur la task → Voir les statistiques

---

## 🎯 Auto-assignment des rôles

Les rôles sont assignés **automatiquement** selon le département (configuré dans `object-template-user.xml`):

### Mapping département → rôles

| Département (CSV) | Rôles MidPoint assignés |
|------------------|------------------------|
| **Tous** | Employee (rôle de base) |
| Commercial | Employee + **Agent Commercial** |
| Informatique | Employee + **IT Admin** |
| Ressources Humaines | Employee + **RH Manager** |
| Comptabilité | Employee + **Comptable** |

### Exemple avec hr_raw.csv

| Employé | Département | Rôles assignés |
|---------|-------------|----------------|
| Jean Dupont | Commercial | Employee + Agent Commercial |
| Sophie Dubois | Informatique | Employee + IT Admin |
| Marie Martin | Ressources Humaines | Employee + RH Manager |
| Luc Thomas | Comptabilité | Employee + Comptable |

### Déclenchement de l'auto-assignment

L'auto-assignment se déclenche automatiquement:
1. ✅ Lors de la création d'un utilisateur (via script ou task)
2. ✅ Lors du **recompute** (forcé par `import_hr_csv.py`)
3. ✅ Lors de la réconciliation périodique (task MidPoint)

---

## 📊 Données CSV

### Format hr_raw.csv

```csv
personalNumber,givenName,familyName,email,department,title,manager,status,hireDate,location
1001,Jean,Dupont,jean.dupont@example.com,Commercial,Agent Commercial Senior,1050,Active,2020-03-15,Paris
1002,Marie,Martin,marie.martin@example.com,Ressources Humaines,Responsable RH,1050,Active,2019-06-01,Lyon
1004,Sophie,Dubois,sophie.dubois@example.com,Informatique,Développeur Senior,1040,Active,2018-11-20,Paris
```

### Champs obligatoires

| Champ | Description | Exemple |
|-------|-------------|---------|
| `personalNumber` | ID unique (corrélation MidPoint) | 1001 |
| `givenName` | Prénom | Jean |
| `familyName` | Nom | Dupont |
| `email` | Email professionnel | jean.dupont@example.com |
| `department` | Département (pour auto-assignment) | Commercial |
| `title` | Poste/Fonction | Agent Commercial Senior |
| `status` | Statut (Active/Suspended) | Active |

### Champs optionnels

- `manager` - ID du manager
- `hireDate` - Date d'embauche
- `location` - Localisation géographique

---

## ✅ Vérification après import

### 1. Via MidPoint UI

```
http://localhost:8080/midpoint
Login: administrator / 5ecr3t

→ Menu: Users → All users
→ Filtrer: Status = Enabled
→ Nombre d'utilisateurs: 15 (+ administrator)
```

### 2. Vérifier les rôles d'un utilisateur

```
→ Users → All users
→ Cliquer sur "Jean Dupont" (1001)
→ Onglet: Assignments
→ Devrait voir:
   - Role: Employee
   - Role: Agent Commercial
```

### 3. Vérifier via API REST

```bash
# Lister tous les utilisateurs
curl -u administrator:5ecr3t \
  http://localhost:8080/midpoint/ws/rest/users | jq

# Récupérer un utilisateur spécifique
curl -u administrator:5ecr3t \
  http://localhost:8080/midpoint/ws/rest/users/1001
```

---

## 🔍 Corrélation et mises à jour

### Principe de corrélation

MidPoint utilise le champ **`personalNumber`** pour identifier les utilisateurs:

```xml
<correlation>
    <q:equal>
        <q:path>personalNumber</q:path>
        <expression>
            <path>$account/attributes/personalNumber</path>
        </expression>
    </q:equal>
</correlation>
```

### Comportement

| Situation | Action MidPoint |
|-----------|----------------|
| personalNumber n'existe pas | ✨ **Création** d'un nouvel utilisateur |
| personalNumber existe déjà | ♻️ **Mise à jour** de l'utilisateur existant |
| Status = Suspended | 🔒 Désactivation du compte |
| Changement de département | 🔄 Recalcul des rôles (si recompute) |

---

## 🛠️ Workflow complet

### Scénario: Nouvel employé

```bash
# 1. Ajouter la ligne dans hr_raw.csv
echo "1016,Alice,Doe,alice.doe@example.com,Informatique,Développeur,1040,Active,2026-01-28,Paris" >> data/hr/hr_raw.csv

# 2. Lancer l'import
cd scripts
python3 import_hr_csv.py

# 3. Vérifier dans MidPoint
# → User "Alice Doe" créé
# → Rôles: Employee + IT Admin (car Informatique)
```

### Scénario: Mutation d'un employé

```bash
# 1. Modifier le département dans hr_raw.csv
# Exemple: Jean Dupont (1001) passe de Commercial → Informatique

# 2. Relancer l'import
python3 import_hr_csv.py

# 3. Résultat:
# → Jean Dupont est mis à jour
# → Recompute déclenché automatiquement
# → Anciens rôles: Employee + Agent Commercial
# → Nouveaux rôles: Employee + IT Admin
```

### Scénario: Départ d'un employé

```bash
# 1. Modifier le status dans hr_raw.csv
# Exemple: Léa Simon (1012) → status = Suspended

# 2. Relancer l'import
python3 import_hr_csv.py

# 3. Résultat:
# → Compte désactivé (administrativeStatus = disabled)
# → Les rôles restent assignés mais inactifs
```

---

## 🐛 Dépannage

### Erreur: "Cannot connect to MidPoint"

```bash
# Vérifier que MidPoint est démarré
docker ps | grep midpoint

# Vérifier les logs
docker logs midpoint | tail -50

# Tester l'accès
curl http://localhost:8080/midpoint/
```

### Erreur: "CSV not found"

```bash
# Vérifier le fichier
ls -la /srv/projet/iam-iga-tp/data/hr/hr_raw.csv

# Utiliser un chemin absolu
python3 import_hr_csv.py --csv-path /srv/projet/iam-iga-tp/data/hr/hr_raw.csv
```

### Utilisateurs créés mais sans rôles

```bash
# 1. Vérifier que l'object template est importé
# Dans MidPoint UI: Configuration → Repository objects → Object templates
# Devrait voir: "User Template with Auto-Role Assignment"

# 2. Forcer le recompute via script
python3 import_hr_csv.py  # Le script force le recompute automatiquement

# 3. Ou via MidPoint UI
# Users → Cliquer sur l'utilisateur → Menu Actions → Recompute
```

### Task ne se déclenche pas

```bash
# 1. Vérifier que la ressource CSV existe
# MidPoint UI: Configuration → Resources → "HR CSV Source"

# 2. Tester la connexion à la ressource
# Cliquer sur la ressource → Onglet Connector → Test Connection

# 3. Vérifier la task
# Server Tasks → List Tasks → "HR CSV Import Task"
# Status doit être: Runnable (pas Suspended)

# 4. Consulter les logs
docker logs midpoint | grep -i "hr csv"
```

---

## 📚 Références

- [GUIDE_IMPORT_MANUEL.md](GUIDE_IMPORT_MANUEL.md) - Import des objets MidPoint
- [scripts/README.md](scripts/README.md) - Documentation des scripts Python
- [config/midpoint/CONFIGURATION_RESSOURCES.md](config/midpoint/CONFIGURATION_RESSOURCES.md) - Configuration des ressources

---

## ✅ Checklist de déploiement

- [ ] MidPoint démarré et accessible
- [ ] Ressources MidPoint importées (6 fichiers)
- [ ] Rôles MidPoint importés (11 fichiers)
- [ ] Object Template importé (auto-assignment activé)
- [ ] Task HR Import importée
- [ ] Fichier hr_raw.csv présent et valide
- [ ] Dépendance Python `httpx` installée
- [ ] Test du script en mode dry-run réussi
- [ ] Import réel exécuté avec succès
- [ ] Utilisateurs vérifiés dans MidPoint UI
- [ ] Rôles auto-assignés vérifiés

---

**Status:** ✅ Configuration complète et testée  
**Date:** 2026-01-28  
**Employés RH:** 15 (hr_raw.csv)  
**Tasks obsolètes supprimées:** task-odoo-hr-sync.xml
