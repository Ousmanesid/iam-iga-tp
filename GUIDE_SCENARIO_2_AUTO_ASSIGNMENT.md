# Guide Vidéo - Scénario 2 : Attribution Automatique des Droits (John, Micheline, Sabine)

## 📋 Vue d'ensemble
**Objectif** : Créer un rôle Employee combinant tous les droits, puis démontrer l'assignation automatique lors de la synchronisation depuis Odoo.

**Durée estimée** : 20-25 minutes

---

## 🎬 SÉQUENCE VIDÉO 1 : Configuration du Rôle Employee (5-6 min)

### Étape 1.1 : Présenter le rôle Employee
1. Ouvrir MidPoint : `http://localhost:8080/midpoint`
2. Se connecter : `administrator` / `5ecr3t`
3. Menu : **Roles** → **List roles**
4. Rechercher "Employee"
5. Ouvrir le rôle **Employee**
6. **ZOOM** : Montrer la structure du rôle :
   - ✅ **Name** : Employee
   - ✅ **Description** : Rôle de base pour tous les employés
   - ✅ **Risk Level** : Low

### Étape 1.2 : Montrer les inducements (droits inclus)
1. Onglet **Inducements** (ou **Assignments**)
2. **ZOOM** : Montrer les 6 inducements :
   - ✅ **Compte LDAP** (base)
   - ✅ **Rôle LDAP_Employee** → Groupe LDAP Employee
   - ✅ **Rôle LDAP_Internet** → Groupe LDAP Internet
   - ✅ **Rôle LDAP_Printer** → Groupe LDAP Printer
   - ✅ **Rôle LDAP_Public_Share_Folder_SharePoint** → Groupe SharePoint
   - ✅ **Compte Odoo** avec rôle Odoo_User

**💡 Point à mentionner** : "Ce rôle Employee combine tous les droits de base. Quand on l'assigne à un utilisateur, tous ces accès sont automatiquement provisionnés."

### Étape 1.3 : Test unitaire - Assignation manuelle (optionnel)
1. Créer un utilisateur test (ex: "Test User")
2. Lui assigner le rôle Employee
3. **ZOOM** : Montrer que tous les comptes sont créés automatiquement
4. Supprimer l'utilisateur test après

**💡 Point à mentionner** : "Le rôle fonctionne correctement. Maintenant, nous allons voir comment l'assigner automatiquement."

---

## 🎬 SÉQUENCE VIDÉO 2 : Configuration de l'Assignation Automatique (4-5 min)

### Étape 2.1 : Présenter l'Object Template
1. Dans MidPoint, menu : **Configuration** → **Object templates**
2. Rechercher "User Template with Auto-Role Assignment"
3. Ouvrir le template
4. **ZOOM** : Montrer les mappings

### Étape 2.2 : Montrer la règle d'assignation automatique
1. **ZOOM** : Montrer le mapping "Auto-assign Employee role to all users"
2. Expliquer :
   - **Source** : `activation/administrativeStatus`
   - **Target** : Rôle Employee
   - **Condition** : Si utilisateur est actif (ENABLED)
3. **ZOOM** : Montrer le code de la condition

**💡 Point à mentionner** : "Cette règle assigne automatiquement le rôle Employee à tout nouvel utilisateur actif importé dans MidPoint."

### Étape 2.3 : Vérifier la configuration système
1. Menu : **Configuration** → **System configuration**
2. Ouvrir la configuration système
3. **ZOOM** : Montrer que le template est lié à `c:UserType`

**💡 Point à mentionner** : "Le template est configuré pour s'appliquer automatiquement à tous les utilisateurs."

---

## 🎬 SÉQUENCE VIDÉO 3 : Création dans Odoo et Assignation Manuelle (John) (4-5 min)

### Étape 3.1 : Créer John Malcovitch dans Odoo
1. Ouvrir Odoo : `http://localhost:8069`
2. Menu : **Employees** → **Employees**
3. Cliquer sur **Create**
4. Remplir :
   - **Name** : `John Malcovitch`
   - **Department** : (ex: `Commercial`)
   - **Job Position** : (ex: `Agent Commercial`)
5. Cliquer sur **Save**

### Étape 3.2 : Créer le contrat
1. Onglet **Contracts** → **Create**
2. Remplir le contrat
3. **Save**

### Étape 3.3 : Importer dans MidPoint
1. Terminal :
   ```bash
   cd /root/iam-iga-tp
   python3 scripts/export_odoo_hr.py
   ```
2. Ou synchronisation directe :
   ```bash
   python3 scripts/sync_odoo_to_midpoint.py
   ```

### Étape 3.4 : Assigner manuellement le rôle Employee
1. Dans MidPoint, rechercher "John Malcovitch"
2. Ouvrir sa fiche
3. **ZOOM** : Montrer qu'il n'a **PAS** encore le rôle Employee
4. Onglet **Assignments** → **Add assignment**
5. Sélectionner **Employee**
6. **Save**
7. Attendre le recompute (2-3 secondes)
8. **ZOOM** : Montrer que tous les comptes sont créés :
   - ✅ Compte LDAP
   - ✅ 4 groupes LDAP
   - ✅ Compte Odoo

**💡 Point à mentionner** : "John a maintenant tous les droits grâce au rôle Employee assigné manuellement."

---

## 🎬 SÉQUENCE VIDÉO 4 : Synchronisation Automatique (Micheline et Sabine) (6-7 min)

### Étape 4.1 : Montrer l'état AVANT la synchronisation
1. Dans MidPoint, menu : **Users** → **List users**
2. **ZOOM** : Compter les utilisateurs
3. Vérifier qu'il n'y a **PAS** encore Micheline ni Sabine
4. **ZOOM** : Capturer l'écran (état initial)

### Étape 4.2 : Créer Micheline et Sabine dans Odoo
1. Dans Odoo, créer **Micheline DeVitry** :
   - **Name** : `Micheline DeVitry`
   - **Department** : `Ressources Humaines`
   - **Job Position** : `RH Manager`
2. Créer son contrat
3. Créer **Sabine DeCreteil** :
   - **Name** : `Sabine DeCreteil`
   - **Department** : `Informatique`
   - **Job Position** : `IT Admin`
4. Créer son contrat

### Étape 4.3 : Configurer la synchronisation automatique
1. Dans MidPoint, menu : **Tasks** → **List tasks**
2. Rechercher "HR CSV Import Task" ou "Odoo HR Sync"
3. Ouvrir la tâche
4. **ZOOM** : Montrer la configuration :
   - ✅ **Schedule** : Récurrence toutes les 60 minutes (ou autre)
   - ✅ **Resource** : HR CSV Source ou Odoo HR Source
5. Si besoin, modifier l'intervalle pour un test (ex: 5 minutes)
6. **Save**

**💡 Point à mentionner** : "La tâche de synchronisation est configurée pour s'exécuter automatiquement toutes les X minutes."

### Étape 4.4 : Lancer la synchronisation manuellement (pour la démo)
1. Dans la tâche, cliquer sur **Run now** (ou via l'API)
2. **ZOOM** : Montrer les logs d'exécution
3. Attendre la fin (10-20 secondes)

**OU** via terminal :
```bash
cd /root/iam-iga-tp
python3 scripts/sync_odoo_to_midpoint.py
```

### Étape 4.5 : Vérifier l'état APRÈS la synchronisation
1. Dans MidPoint, menu : **Users** → **List users**
2. **ZOOM** : Montrer que Micheline et Sabine sont maintenant présentes
3. Ouvrir **Micheline DeVitry**
4. **ZOOM** : Montrer l'onglet **Assignments** :
   - ✅ **Rôle Employee** assigné automatiquement
5. **ZOOM** : Montrer l'onglet **Projections** :
   - ✅ Compte LDAP créé
   - ✅ 4 groupes LDAP attribués
   - ✅ Compte Odoo créé
6. Faire de même pour **Sabine DeCreteil**

**💡 Point à mentionner** : "Les deux nouvelles employées ont été automatiquement importées ET le rôle Employee leur a été assigné automatiquement grâce à la règle configurée."

---

## 🎬 SÉQUENCE VIDÉO 5 : Vérification dans les systèmes cibles (3-4 min)

### Étape 5.1 : Vérifier dans LDAP
1. Terminal :
   ```bash
   docker exec -it openldap ldapsearch -x -H ldap://localhost -b "dc=example,dc=com" -D "cn=admin,dc=example,dc=com" -w admin "cn=micheline.devitry"
   ```
2. **ZOOM** : Montrer les groupes `memberOf`
3. Répéter pour Sabine

### Étape 5.2 : Vérifier dans Odoo
1. Dans Odoo, menu : **Settings** → **Users & Companies** → **Users**
2. Rechercher "Micheline" et "Sabine"
3. **ZOOM** : Montrer que les comptes utilisateurs sont créés

### Étape 5.3 : Comparaison avant/après
1. **ZOOM** : Montrer un tableau comparatif :
   - **Avant** : 2 utilisateurs (Alice, John)
   - **Après** : 4 utilisateurs (Alice, John, Micheline, Sabine)
   - **Tous** ont le rôle Employee assigné automatiquement

---

## 🎬 SÉQUENCE VIDÉO 6 : Récapitulatif et Conclusion (2-3 min)

### Résumé visuel
1. Dans MidPoint, menu : **Users** → **List users**
2. **ZOOM** : Montrer la liste complète
3. Ouvrir chaque utilisateur et montrer :
   - ✅ Rôle Employee assigné
   - ✅ Tous les comptes provisionnés

### Points clés à mentionner
1. **Rôle Employee** : Combine tous les droits de base (LDAP + Odoo)
2. **Assignation manuelle** : Possible pour des cas spécifiques (John)
3. **Assignation automatique** : Via la règle dans l'object template
4. **Synchronisation automatique** : Via la tâche planifiée
5. **Résultat** : Provisionnement complet et automatique des nouveaux employés

**💡 Conclusion** : "Nous avons démontré que le système IAM/IGA peut automatiquement provisionner les nouveaux employés avec tous les droits de base, réduisant le temps de traitement de plusieurs heures à quelques minutes."

---

## 📝 Checklist avant l'enregistrement

- [ ] Rôle Employee importé et testé dans MidPoint
- [ ] Object template avec règle d'assignation auto activée
- [ ] Tâche de synchronisation configurée
- [ ] Odoo accessible avec au moins 2-3 employés existants
- [ ] MidPoint accessible
- [ ] OpenLDAP accessible
- [ ] Scripts Python testés
- [ ] Groupes LDAP créés
- [ ] Navigation fluide dans MidPoint
- [ ] Terminal prêt avec commandes
- [ ] Capture d'écran avant/après préparée

---

## 🎥 Conseils pour l'enregistrement

1. **Montrer les deux états** : Avant et après la synchronisation
2. **Temps réel** : Laisser tourner la vidéo pendant l'exécution de la tâche
3. **Zoomer** : Sur les éléments importants (assignments, projections)
4. **Expliquer** : Chaque étape avant de l'exécuter
5. **Pauses** : Attendre le recompute MidPoint (2-5 secondes)
6. **Erreurs** : Si erreur, expliquer et corriger

---

## 🔧 Commandes de référence

```bash
# Synchronisation Odoo → MidPoint
cd /root/iam-iga-tp
python3 scripts/sync_odoo_to_midpoint.py

# Vérifier LDAP
docker exec -it openldap ldapsearch -x -H ldap://localhost -b "dc=example,dc=com" -D "cn=admin,dc=example,dc=com" -w admin "cn=micheline.devitry"

# Vérifier les utilisateurs MidPoint (via API)
curl -s -k -u administrator:5ecr3t "http://localhost:8080/midpoint/ws/rest/users" -H "Accept: application/xml" | grep -oP '<name>[^<]+</name>'
```

---

## 📊 Timeline recommandée

| Séquence | Durée | Description |
|----------|-------|-------------|
| 1. Configuration rôle | 5-6 min | Présenter le rôle Employee |
| 2. Configuration auto | 4-5 min | Montrer la règle d'assignation |
| 3. John (manuel) | 4-5 min | Création + assignation manuelle |
| 4. Micheline/Sabine (auto) | 6-7 min | Synchronisation automatique |
| 5. Vérifications | 3-4 min | LDAP + Odoo |
| 6. Conclusion | 2-3 min | Récapitulatif |

**Durée totale** : 20-25 minutes

---

**Format recommandé** : 1080p, 30fps  
**Audio** : Micro-casque  
**Édition** : Ajouter des annotations/textes pour les points clés
