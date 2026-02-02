# 🔄 Guide : Synchronisation Odoo → Aegis Gateway

## ✅ **BOUTON DE SYNCHRONISATION CRÉÉ !**

Un bouton **"Synchroniser Odoo"** a été ajouté au Dashboard pour synchroniser en un clic.

---

## 🎯 Comment ça marche

### Scénario : Ajouter un nouvel employé

#### Étape 1 : Créer l'employé dans Odoo
1. Ouvrir Odoo : http://localhost:8069
2. Aller dans **Employés** (module HR)
3. Cliquer sur **Créer**
4. Remplir les informations :
   - **Nom** : Bob Test
   - **Email** : bob.test@company.com
   - **Poste** : Développeur
   - **Département** : IT
5. Cliquer sur **Enregistrer**

#### Étape 2 : Synchroniser vers Aegis
**Option A : Via le Dashboard (NOUVEAU !)** ✨
1. Ouvrir le Dashboard : http://136.119.23.158:5174/
2. Cliquer sur le bouton **"Synchroniser Odoo"** 🔄 (en haut à droite)
3. Attendre 1-2 secondes
4. Un message apparaît : "✅ X employé(s) créé(s), Y mis à jour"
5. Le nouvel employé apparaît dans la liste !

**Option B : Via l'API**
```bash
curl -X POST http://localhost:8001/api/v1/odoo/sync
```

#### Étape 3 : Vérifier dans le Dashboard
- Le nouvel employé **Bob Test** apparaît dans la table
- Son email : `bob.test@company.com`
- Source : `odoo_sync` ✨
- Rôle : `DEVELOPER` (mapping automatique)

---

## 🔄 Les 3 Modes de Synchronisation

### 1. **MANUEL (Bouton Dashboard)** ⭐ RECOMMANDÉ
**Quand** : Après avoir créé des employés dans Odoo  
**Comment** : Cliquer sur "Synchroniser Odoo" dans le Dashboard  
**Avantages** :
- ✅ Visuel et intuitif
- ✅ Feedback immédiat
- ✅ Pas de configuration

**Utilisation** :
```
1. Créer employés dans Odoo
2. Ouvrir Dashboard Aegis
3. Cliquer "Synchroniser Odoo"
4. Voir les résultats s'afficher
```

---

### 2. **AUTOMATIQUE (Cron)** 🤖
**Quand** : Pour une synchronisation régulière sans intervention  
**Comment** : Configurer un cron job sur le serveur  
**Avantages** :
- ✅ Totalement automatique
- ✅ Pas besoin de cliquer
- ✅ Synchronisation en arrière-plan

**Configuration** :
```bash
# Éditer le crontab
crontab -e

# Ajouter une ligne :

# Toutes les 15 minutes
*/15 * * * * curl -X POST http://localhost:8001/api/v1/odoo/sync?background=true

# OU toutes les heures
0 * * * * curl -X POST http://localhost:8001/api/v1/odoo/sync?background=true

# OU tous les jours à 8h du matin
0 8 * * * curl -X POST http://localhost:8001/api/v1/odoo/sync?background=true
```

**Vérifier le cron** :
```bash
# Voir les tâches programmées
crontab -l

# Voir les logs du cron
grep CRON /var/log/syslog | tail -20
```

---

### 3. **TEMPS RÉEL (Webhook n8n)** ⚡ AVANCÉ
**Quand** : Pour une synchronisation instantanée à chaque création  
**Comment** : Configurer un workflow n8n  
**Avantages** :
- ✅ Synchronisation instantanée
- ✅ Pas de délai
- ✅ Réactif

**Workflow n8n** :
```
1. Trigger : Odoo Webhook - Employee Created
   └─> URL: http://n8n:5678/webhook/odoo-employee

2. HTTP Request : POST to Aegis
   └─> URL: http://localhost:8001/api/v1/odoo/webhook
   └─> Body: 
       {
         "event": "create",
         "employee_id": {{$json.id}}
       }

3. Slack Notification (optionnel)
   └─> Message: "Nouvel employé synchronisé : {{$json.name}}"
```

---

## 🎨 Interface du Bouton

### Apparence
```
┌─────────────────────────────────────────┐
│  Dashboard                [🔄 Synchroniser Odoo] │
└─────────────────────────────────────────┘
```

### États du bouton
1. **Normal** : `🔄 Synchroniser Odoo` (violet)
2. **En cours** : `🔄 Synchronisation...` (icône tourne, bouton désactivé)
3. **Succès** : Message vert "✅ 2 employé(s) créé(s), 1 mis à jour"
4. **Erreur** : Message rouge "❌ Erreur: connexion Odoo échouée"

### Animation
- L'icône tourne pendant la synchronisation
- Le message apparaît avec une animation de slide
- Le message disparaît après 5 secondes
- La liste se rafraîchit automatiquement

---

## 📊 Résultats de Synchronisation

### Messages possibles

#### Succès
```
✅ 5 employé(s) créé(s), 0 mis à jour
✅ 0 employé(s) créé(s), 3 mis à jour
✅ 10 employé(s) créé(s), 2 mis à jour
```

#### Aucun changement
```
✅ 0 employé(s) créé(s), 0 mis à jour
(Tous les employés sont déjà synchronisés)
```

#### Erreur
```
❌ Erreur: Connexion Odoo échouée
❌ Erreur: Impossible de synchroniser
❌ Erreur: Timeout
```

---

## 🧪 Test Complet

### Test 1 : Créer un employé et synchroniser

```bash
# 1. Créer un employé dans Odoo (via interface web)
#    Nom: Test User
#    Email: test.user@company.com

# 2. Vérifier qu'il n'est pas encore dans Aegis
curl http://localhost:8001/api/v1/users | grep test.user
# → Aucun résultat

# 3. Synchroniser via le bouton Dashboard
#    → Cliquer sur "Synchroniser Odoo"

# 4. Vérifier qu'il est maintenant dans Aegis
curl http://localhost:8001/api/v1/users | grep test.user
# → Résultat : { "email": "test.user@company.com", ... }
```

### Test 2 : Synchronisation multiple

```bash
# 1. Créer 5 employés dans Odoo

# 2. Cliquer "Synchroniser Odoo"

# 3. Message attendu :
#    ✅ 5 employé(s) créé(s), 0 mis à jour

# 4. Re-cliquer "Synchroniser Odoo"

# 5. Message attendu :
#    ✅ 0 employé(s) créé(s), 0 mis à jour
#    (car déjà synchronisés)
```

---

## 🔧 Troubleshooting

### Le bouton ne fait rien
**Cause** : Erreur JavaScript  
**Solution** :
```bash
# Vérifier les logs du navigateur (F12 → Console)
# Redémarrer le frontend
cd /srv/projet/aegis-gateway/frontend
npm run dev
```

### Message d'erreur "Connexion Odoo échouée"
**Cause** : Odoo n'est pas accessible  
**Solution** :
```bash
# Vérifier qu'Odoo est démarré
docker ps | grep odoo

# Tester la connexion
curl http://localhost:8069

# Vérifier les credentials dans .env
cat /srv/projet/aegis-gateway/.env | grep ODOO
```

### La liste ne se rafraîchit pas
**Cause** : Cache du navigateur  
**Solution** :
```bash
# Recharger la page (Ctrl+R ou Cmd+R)
# Ou vider le cache (Ctrl+Shift+R)
```

---

## 📋 Commandes Utiles

```bash
# Voir le statut de sync Odoo
curl http://localhost:8001/api/v1/odoo/sync/status

# Synchroniser manuellement via API
curl -X POST http://localhost:8001/api/v1/odoo/sync

# Voir les employés Odoo (source)
curl http://localhost:8001/api/v1/odoo/employees

# Voir les users Aegis depuis Odoo
curl "http://localhost:8001/api/v1/users?source=odoo_sync"

# Compter les users Odoo
curl "http://localhost:8001/api/v1/users?source=odoo_sync" | jq 'length'

# Redémarrer le backend
bash /srv/projet/aegis-gateway/scripts/start_with_odoo.sh
```

---

## ✅ Checklist de Déploiement

- [x] Bouton créé dans le Dashboard
- [x] API `/odoo/sync` fonctionnelle
- [x] Messages de feedback affichés
- [x] Animation de chargement
- [x] Rafraîchissement automatique
- [ ] Tester avec un nouvel employé
- [ ] Configurer le cron (optionnel)
- [ ] Configurer le webhook n8n (optionnel)

---

## 🎉 Résumé

**Maintenant, quand vous créez un employé dans Odoo :**

1. ✅ Ouvrir le Dashboard Aegis
2. ✅ Cliquer sur **"Synchroniser Odoo"** 🔄
3. ✅ Attendre 1-2 secondes
4. ✅ Le nouvel employé apparaît immédiatement !

**Plus besoin de ligne de commande !** 🚀

---

**Pour plus d'automatisation**, configurez un cron qui synchronise toutes les 15 minutes, et vous n'aurez même plus besoin de cliquer !
