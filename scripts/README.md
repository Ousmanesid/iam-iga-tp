# Scripts de Provisioning CSV → MidPoint

Ce dossier contient les scripts pour automatiser l'import des données RH depuis CSV vers MidPoint.

## 📋 Scripts disponibles

### 1. `import_hr_csv.py` - Import direct via API REST

Lit le fichier CSV HR et crée/met à jour les utilisateurs directement via l'API REST MidPoint.

**Utilisation:**
```bash
# Import avec configuration par défaut
python import_hr_csv.py

# Spécifier un fichier CSV différent
python import_hr_csv.py --csv-path /path/to/file.csv

# Mode dry-run (simulation sans modification)
python import_hr_csv.py --dry-run

# Avec URL personnalisée
python import_hr_csv.py --midpoint-url http://midpoint:8080/midpoint
```

**Fonctionnalités:**
- ✅ Lecture du CSV hr_raw.csv
- ✅ Création automatique des utilisateurs dans MidPoint
- ✅ Mise à jour des utilisateurs existants (basé sur personalNumber)
- ✅ Recompute automatique pour appliquer les rôles (object template)
- ✅ Statistiques détaillées de l'import

---

### 2. `trigger_import_task.py` - Déclenchement de la task MidPoint

Déclenche manuellement la task d'import CSV configurée dans MidPoint au lieu d'attendre le prochain cycle automatique (60 secondes).

**Utilisation:**
```bash
# Déclencher la task
python trigger_import_task.py

# Déclencher et attendre la fin
python trigger_import_task.py --wait

# Avec timeout personnalisé (défaut: 300s)
python trigger_import_task.py --wait --timeout 600

# Avec OID de task personnalisé
python trigger_import_task.py --task-oid 10000000-0000-0000-5555-000000000001
```

**Fonctionnalités:**
- ✅ Déclenchement immédiat de la task HR CSV Import
- ✅ Attente optionnelle de la fin d'exécution
- ✅ Affichage du statut et des résultats

---

## 🔧 Configuration

### Variables d'environnement (optionnelles)

Les scripts utilisent ces valeurs par défaut, modifiables via arguments:

```bash
MIDPOINT_URL=http://localhost:8080/midpoint
MIDPOINT_USER=administrator
MIDPOINT_PASSWORD=5ecr3t
```

### Format CSV attendu

Le fichier `hr_raw.csv` doit contenir ces colonnes:

```csv
personalNumber,givenName,familyName,email,department,title,manager,status,hireDate,location
1001,Jean,Dupont,jean.dupont@example.com,Commercial,Agent Commercial Senior,1050,Active,2020-03-15,Paris
```

**Colonnes obligatoires:**
- `personalNumber` - Identifiant unique (corrélation MidPoint)
- `givenName` - Prénom
- `familyName` - Nom
- `email` - Adresse email
- `department` - Département (utilisé pour auto-assignment des rôles)
- `title` - Poste/Fonction
- `status` - Statut (Active/Suspended)

**Colonnes optionnelles:**
- `manager` - ID du manager
- `hireDate` - Date d'embauche
- `location` - Localisation

---

## 🚀 Workflow recommandé

### Option 1: Import direct via script (recommandé pour dev/test)

```bash
cd /srv/projet/iam-iga-tp/scripts

# 1. Test en mode dry-run
python import_hr_csv.py --dry-run

# 2. Import réel
python import_hr_csv.py
```

### Option 2: Import via task MidPoint (recommandé pour production)

```bash
cd /srv/projet/iam-iga-tp/scripts

# 1. Déclencher la task et attendre
python trigger_import_task.py --wait

# 2. Vérifier dans MidPoint UI
# → Server Tasks → List Tasks
# → Users → All users
```

---

## 📊 Auto-assignment des rôles

Les rôles sont assignés automatiquement selon le département (voir `object-template-user.xml`):

| Département | Rôles auto-assignés |
|-------------|-------------------|
| Tous | Employee (rôle de base) |
| Informatique | IT Admin |
| Commercial | Agent Commercial |
| RH / Human Resources | RH Manager |

L'auto-assignment se déclenche:
- ✅ Lors de la création d'un utilisateur
- ✅ Lors du recompute (déclenché par les scripts)
- ✅ Lors de la réconciliation automatique (task)

---

## 🔍 Vérification

### Vérifier les utilisateurs créés

```bash
# Via l'API MidPoint
curl -u administrator:5ecr3t \
  http://localhost:8080/midpoint/ws/rest/users
```

### Vérifier les rôles assignés

Connectez-vous à MidPoint:
- URL: http://localhost:8080/midpoint
- User: administrator / Password: 5ecr3t
- Menu: Users → All users
- Cliquer sur un utilisateur → Onglet "Assignments"

---

## ⚙️ Dépendances

Les scripts nécessitent Python 3.8+ et `httpx`:

```bash
pip install httpx
```

---

## 🐛 Dépannage

### Erreur "Cannot connect to MidPoint"
- Vérifier que MidPoint est démarré: `docker ps | grep midpoint`
- Vérifier l'URL: `curl http://localhost:8080/midpoint/`

### Erreur "CSV not found"
- Vérifier le chemin: `/srv/projet/iam-iga-tp/data/hr/hr_raw.csv`
- Utiliser `--csv-path` pour spécifier un autre fichier

### Utilisateurs créés mais sans rôles
- Vérifier que l'object template est importé dans MidPoint
- Exécuter manuellement le recompute dans MidPoint UI
- Ou relancer le script qui force le recompute

### Task ne se déclenche pas
- Vérifier que la ressource HR CSV est configurée dans MidPoint
- Vérifier que la task existe: OID `10000000-0000-0000-5555-000000000001`
- Consulter les logs MidPoint: `docker logs midpoint`
