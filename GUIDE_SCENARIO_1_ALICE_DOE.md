# Guide Vidéo - Scénario 1 : Création et Attribution Manuelle (Alice Doe)

## 📋 Vue d'ensemble
**Objectif** : Créer manuellement l'employée Alice Doe dans Odoo, l'importer dans MidPoint, et lui attribuer manuellement les droits LDAP et Odoo.

**Durée estimée** : 15-20 minutes

---

## 🎬 SÉQUENCE VIDÉO 1 : Création dans Odoo (2-3 min)

### Étape 1.1 : Accéder à Odoo
1. Ouvrir le navigateur
2. Aller sur `http://localhost:8069`
3. Se connecter avec `admin` / `admin`
4. Montrer l'interface Odoo

### Étape 1.2 : Créer l'employée Alice Doe
1. Menu : **Employees** → **Employees**
2. Cliquer sur **Create**
3. Remplir le formulaire :
   - **Name** : `Alice Doe`
   - **Company** : (sélectionner)
   - **Department** : (ex: `Ressources Humaines` ou `Commercial`)
   - **Job Position** : (ex: `Agent Commercial` ou `RH Manager`)
4. Cliquer sur **Save**

### Étape 1.3 : Créer le contrat
1. Dans la fiche d'Alice Doe, onglet **Contracts**
2. Cliquer sur **Create**
3. Remplir :
   - **Employee** : `Alice Doe` (auto-rempli)
   - **Contract Type** : `Permanent`
   - **Start Date** : Date du jour
   - **Wage** : (optionnel)
4. Cliquer sur **Save**
5. **ZOOM** : Montrer que le contrat est créé

**💡 Point à mentionner** : "Nous avons créé Alice Doe dans le SI RH Odoo avec son contrat. Maintenant, nous allons l'importer dans MidPoint."

---

## 🎬 SÉQUENCE VIDÉO 2 : Import dans MidPoint (3-4 min)

### Étape 2.1 : Exporter depuis Odoo (Cas 1 : CSV)
1. Ouvrir un terminal
2. Naviguer vers le projet :
   ```bash
   cd /root/iam-iga-tp
   ```
3. Lancer l'export :
   ```bash
   python3 scripts/export_odoo_hr.py
   ```
4. **ZOOM** : Montrer le fichier `data/hr/hr_clean.csv` généré
5. Vérifier qu'Alice Doe est dans le CSV :
   ```bash
   grep "Alice" data/hr/hr_clean.csv
   ```

**OU** (Cas 2 : Import direct depuis DB)

1. Lancer le script de synchronisation :
   ```bash
   python3 scripts/sync_odoo_to_midpoint.py
   ```
2. **ZOOM** : Montrer les logs de synchronisation

### Étape 2.2 : Vérifier l'import dans MidPoint
1. Ouvrir MidPoint : `http://localhost:8080/midpoint`
2. Se connecter : `administrator` / `5ecr3t`
3. Menu : **Users** → **List users**
4. Rechercher "Alice Doe"
5. **ZOOM** : Montrer la fiche utilisateur
6. Vérifier :
   - ✅ **Name** : Alice Doe
   - ✅ **Lifecycle State** : `ACTIVE` (ou `PROPOSED`)
   - ✅ **Personal Number** : (ID Odoo)
   - ✅ **Organization** : (département)

**💡 Point à mentionner** : "L'identité d'Alice a été créée dans MidPoint. Maintenant, nous allons lui attribuer manuellement les droits."

---

## 🎬 SÉQUENCE VIDÉO 3 : Attribution Manuelle des Droits LDAP (4-5 min)

### Étape 3.1 : Assigner le rôle Employee
1. Dans MidPoint, ouvrir la fiche d'Alice Doe
2. Onglet **Assignments**
3. Cliquer sur **Add assignment**
4. Dans le champ de recherche, taper : `Employee`
5. Sélectionner le rôle **Employee**
6. Cliquer sur **Save**

### Étape 3.2 : Vérifier le provisioning LDAP
1. Attendre quelques secondes (recompute automatique)
2. Onglet **Projections** (ou **Accounts**)
3. **ZOOM** : Montrer les comptes créés :
   - ✅ **LDAP Account** : `uid=alice.doe,ou=people,dc=example,dc=com`
   - ✅ **Status** : `LINKED` ou `PROVISIONED`

### Étape 3.3 : Vérifier les groupes LDAP dans OpenLDAP
1. Ouvrir un terminal
2. Se connecter à OpenLDAP :
   ```bash
   docker exec -it openldap ldapsearch -x -H ldap://localhost -b "dc=example,dc=com" -D "cn=admin,dc=example,dc=com" -w admin
   ```
3. Rechercher Alice Doe :
   ```bash
   docker exec -it openldap ldapsearch -x -H ldap://localhost -b "dc=example,dc=com" -D "cn=admin,dc=example,dc=com" -w admin "cn=alice.doe"
   ```
4. **ZOOM** : Montrer les attributs `memberOf` :
   - ✅ `cn=Employee,ou=groups,dc=example,dc=com`
   - ✅ `cn=Internet,ou=groups,dc=example,dc=com`
   - ✅ `cn=Printer,ou=groups,dc=example,dc=com`
   - ✅ `cn=Public_Share_Folder_SharePoint,ou=groups,dc=example,dc=com`

**💡 Point à mentionner** : "Les 4 groupes LDAP ont été automatiquement attribués grâce au rôle Employee."

---

## 🎬 SÉQUENCE VIDÉO 4 : Attribution Manuelle des Droits Odoo (3-4 min)

### Étape 4.1 : Vérifier le compte Odoo
1. Dans MidPoint, fiche d'Alice Doe
2. Onglet **Projections** (ou **Accounts**)
3. **ZOOM** : Montrer le compte Odoo :
   - ✅ **Odoo Account** : `alice.doe` (ou ID)
   - ✅ **Status** : `LINKED` ou `PROVISIONED`
   - ✅ **Resource** : `Odoo ERP (PostgreSQL)`

**Note** : Le compte Odoo devrait déjà être créé car le rôle Employee inclut Odoo_User.

### Étape 4.2 : Vérifier dans Odoo
1. Retourner dans Odoo
2. Menu : **Settings** → **Users & Companies** → **Users**
3. Rechercher "Alice Doe" ou "alice"
4. **ZOOM** : Montrer :
   - ✅ Utilisateur créé
   - ✅ **Login** : `alice.doe` (ou similaire)
   - ✅ **Groups** : `Internal User` (Odoo_User)

### Étape 4.3 : Tester la connexion (optionnel)
1. Se déconnecter d'Odoo
2. Se connecter avec `alice.doe` / (mot de passe)
3. **ZOOM** : Montrer l'interface utilisateur standard

**💡 Point à mentionner** : "Alice a maintenant tous les droits de base : compte LDAP avec 4 groupes, et compte Odoo avec droits utilisateur standard."

---

## 🎬 SÉQUENCE VIDÉO 5 : Récapitulatif (1-2 min)

### Résumé visuel
1. Dans MidPoint, fiche d'Alice Doe
2. **ZOOM** : Montrer l'onglet **Assignments** :
   - ✅ Rôle **Employee** assigné
3. **ZOOM** : Montrer l'onglet **Projections** :
   - ✅ Compte LDAP avec 4 groupes
   - ✅ Compte Odoo avec rôle User
4. **ZOOM** : Montrer **Lifecycle State** : `ACTIVE`

**💡 Conclusion** : "Nous avons créé manuellement Alice Doe dans Odoo, importé son identité dans MidPoint, et attribué manuellement le rôle Employee qui lui donne automatiquement tous les accès de base."

---

## 📝 Checklist avant l'enregistrement

- [ ] Odoo accessible et fonctionnel
- [ ] MidPoint accessible et fonctionnel
- [ ] OpenLDAP accessible
- [ ] Scripts Python testés
- [ ] Rôle Employee importé dans MidPoint
- [ ] Ressources LDAP Groups et Odoo testées
- [ ] Groupes LDAP créés dans OpenLDAP (Employee, Internet, Printer, Public_Share_Folder_SharePoint)
- [ ] Navigation MidPoint fluide
- [ ] Terminal prêt avec commandes copiées

---

## 🎥 Conseils pour l'enregistrement

1. **Parler lentement** : Expliquer chaque action avant de la faire
2. **Zoomer** : Utiliser Ctrl+Molette pour zoomer sur les éléments importants
3. **Pauses** : Attendre 2-3 secondes après chaque action importante
4. **Erreurs** : Si une erreur survient, l'expliquer et montrer la solution
5. **Transitions** : Utiliser des transitions entre les séquences ("Maintenant, nous allons...")

---

## 🔧 Commandes de référence

```bash
# Export Odoo vers CSV
cd /root/iam-iga-tp
python3 scripts/export_odoo_hr.py

# Vérifier le CSV
grep "Alice" data/hr/hr_clean.csv

# Vérifier LDAP
docker exec -it openldap ldapsearch -x -H ldap://localhost -b "dc=example,dc=com" -D "cn=admin,dc=example,dc=com" -w admin "cn=alice.doe"
```

---

**Durée totale estimée** : 15-20 minutes
**Format recommandé** : 1080p, 30fps
**Audio** : Micro-casque recommandé
