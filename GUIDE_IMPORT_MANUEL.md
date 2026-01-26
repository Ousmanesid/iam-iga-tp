# 📋 GUIDE D'IMPORT MANUEL - MIDPOINT

## ✅ MidPoint est prêt !

**URL:** http://localhost:8080/midpoint  
**Login:** `administrator`  
**Mot de passe:** `5ecr3t`

---

## 📂 ORDRE D'IMPORT (IMPORTANT !)

### 1️⃣ RESSOURCES (6 fichiers)
📁 Dossier: `/root/iam-iga-tp/config/midpoint/resources/`

Importer dans cet ordre :
1. `resource-ldap.xml` ⭐ (Annuaire LDAP)
2. `resource-odoo.xml` (Odoo - provisioning cible)
3. `resource-odoo-hr.xml` (Odoo HR - source d'identités)
4. `resource-homeapp-postgresql.xml` (Home App)
5. `resource-hr-csv.xml` (Import CSV HR)
6. `resource-intranet-csv.xml` (Export Intranet)

### 2️⃣ RÔLES (11 fichiers)
📁 Dossier: `/root/iam-iga-tp/config/midpoint/roles/`

Importer dans cet ordre :
1. `role-employee.xml` ⭐⭐ (Rôle de base - IMPORTANT)
2. `role-odoo-user.xml`
3. `role-odoo-finance.xml`
4. `role-odoo-admin.xml`
5. `role-homeapp-user.xml`
6. `role-homeapp-commercial.xml`
7. `role-homeapp-admin.xml`
8. `role-it-admin.xml`
9. `role-rh-manager.xml`
10. `role-comptable.xml`
11. `role-agent-commercial.xml`

### 3️⃣ OBJECT TEMPLATE (1 fichier)
📁 Dossier: `/root/iam-iga-tp/config/midpoint/object-templates/`

1. `object-template-user.xml` ⭐ (Auto-assignment des rôles)

### 4️⃣ TÂCHES (2 fichiers)
📁 Dossier: `/root/iam-iga-tp/config/midpoint/tasks/`

1. `task-hr-import.xml` (Import depuis HR CSV)
2. `task-odoo-hr-sync.xml` (Synchronisation Odoo HR)

---

## 🔧 PROCÉDURE D'IMPORT

### Étape par étape :

1. **Se connecter à MidPoint**
   - Ouvrir http://localhost:8080/midpoint
   - Login: `administrator` / Mot de passe: `5ecr3t`

2. **Aller dans le menu d'import**
   - Cliquer sur **Configuration** (menu en haut)
   - Cliquer sur **Repository objects**
   - Cliquer sur **Import object**

3. **Importer chaque fichier**
   - Cliquer sur **Choose file** (ou **Parcourir**)
   - Sélectionner le fichier XML
   - **Cocher "Overwrite existing object"** ✅
   - Cliquer sur **Import object**
   - Attendre le message de confirmation ✓

4. **Pause entre imports**
   - Attendre **5 secondes** entre chaque import
   - Cela évite le rate limiting de l'API

---

## ⚠️ POINTS IMPORTANTS

### ⭐ Ressources prioritaires :
- **resource-ldap.xml** : Nécessaire pour tous les rôles
- **resource-odoo.xml** : Cible de provisioning principale

### ⭐⭐ Rôles critiques :
- **role-employee.xml** : Rôle de base attribué à tous les employés
  - Crée automatiquement le compte LDAP
  - Ajoute les groupes : Employee, Internet, Printer, SharePoint
  - Crée le compte Odoo de base

### ⭐ Object Template :
- **object-template-user.xml** : Configuration DÉSACTIVÉE pour l'instant
  - L'auto-assignment du rôle Employee est en commentaire
  - À activer plus tard si nécessaire

---

## 🔍 VÉRIFICATION APRÈS IMPORT

### Vérifier les ressources :
1. Menu **Configuration** → **Repository objects** → **Resources**
2. Vous devez voir **6 ressources** listées

### Vérifier les rôles :
1. Menu **Configuration** → **Repository objects** → **Roles**
2. Vous devez voir **11 rôles** (+ les rôles système par défaut)

### Vérifier les tâches :
1. Menu **Server tasks** → **List tasks**
2. Vous devez voir les 2 tâches importées

### Tester une ressource :
1. Aller dans **Configuration** → **Repository objects** → **Resources**
2. Cliquer sur **LDAP Resource**
3. Onglet **Connector** → Cliquer sur **Test connection**
4. Devrait afficher "Test connection successful" ✓

---

## 📊 COMPTEUR D'IMPORTS

Total à importer : **20 objets**
- ⬜ 6 Ressources
- ⬜ 11 Rôles  
- ⬜ 1 Object Template
- ⬜ 2 Tâches

---

## 🆘 EN CAS DE PROBLÈME

### Erreur "Object already exists"
→ Cocher "Overwrite existing object" et réessayer

### Erreur "Repository reference cannot be resolved"
→ Vérifier que les ressources sont importées avant les rôles

### Erreur "Referenced object not found"
→ Vérifier l'ordre d'import (ressources → rôles → templates → tâches)

### Rate limiting (trop de requêtes)
→ Attendre 2-3 minutes et reprendre

---

## ✅ APRÈS L'IMPORT COMPLET

Une fois tous les objets importés :

1. **Tester le provisioning** :
   - Créer un utilisateur test
   - Lui assigner le rôle "Employee"
   - Vérifier qu'il apparaît dans LDAP

2. **Lancer les tâches de synchronisation** :
   - Aller dans **Server tasks** → **List tasks**
   - Lancer manuellement les tâches d'import

---

**Bon courage pour l'import ! 🚀**
