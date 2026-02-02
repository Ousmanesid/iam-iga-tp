# Configuration de l'Intégration MidPoint → Odoo via API XML-RPC

## ✅ Configuration terminée

L'intégration utilise maintenant l'**API XML-RPC d'Odoo** au lieu d'une connexion SQL directe.

### Architecture

```
MidPoint (Groovy Scripts)
    ↓ XML-RPC
Odoo API (/xmlrpc/2/object)
    ↓
Odoo ORM (res.users, res.partner)
    ↓
PostgreSQL
```

## 🔑 Compte Technique

Un compte de service dédié a été créé dans Odoo :

- **Login** : `midpoint_service`
- **Mot de passe** : `midpoint123`
- **Email** : `midpoint@example.com`
- **Groupes** : Administration/Settings (group_system)
- **Objectif** : Provisioning automatique via MidPoint

## 📁 Fichiers Créés

### Scripts Groovy (dans `/opt/midpoint/var/scripts/odoo/`)

1. **OdooHelper.groovy** : Classe helper pour l'API XML-RPC Odoo
   - Utilise `org.apache.xmlrpc.client.XmlRpcClient`
   - Endpoints : `/xmlrpc/2/common` (auth) et `/xmlrpc/2/object` (operations)
2. **TestScript.groovy** : Test de connexion
3. **SchemaScript.groovy** : Définition du schéma (login, name, email, active, groups_id)
4. **CreateScript.groovy** : Création d'utilisateur via XML-RPC
   - Appelle `res.users.create()` via `execute_kw`
   - Attribue automatiquement le groupe "Internal User"
   - Pas de mot de passe (authentification LDAP)
5. **SearchScript.groovy** : Recherche d'utilisateurs via `search_read`
6. **UpdateScript.groovy** : Mise à jour via `write`
7. **DeleteScript.groovy** : Désactivation (pas de suppression réelle)

### Configuration MidPoint

1. **resource-odoo-api.xml** : Nouvelle ressource avec OID `a1b2c3d4-e5f6-7890-abcd-ef1234567890`
   - Utilise le connecteur ScriptedREST avec XML-RPC
   - Mappings : login, name, email, active
   - Groupe "Internal User" attribué automatiquement via `execute_kw`

2. **role-odoo-user.xml** : Rôle mis à jour
   - Référence la nouvelle ressource API
   - Simplifié (le script CreateScript gère le groupe)

## 🔄 Processus de Provisioning

Quand un utilisateur se voit attribuer le rôle `Odoo_User` dans MidPoint :

1. MidPoint appelle **CreateScript.groovy**
2. Le script construit les valeurs :
   ```json
   {
     "login": "prenom.nom",
     "name": "Prénom Nom",
     "email": "prenom.nom@example.com",
     "active": true,
     "groups_id": [[6, 0, [ID_DU_GROUPE_INTERNAL_USER]]],
     "notification_type": "inbox"
   }
   ```
3. Appel à l'API Odoo via XML-RPC : 
   ```python
   execute_kw(
       db="odoo", uid=14, password="midpoint123",
       model="res.users", method="create",
       args=[[values]]
   )
   ```
4. Odoo crée automatiquement :
   - L'enregistrement `res_users`
   - L'enregistrement `res_partner` lié (avec email et nom)
   - L'appartenance au groupe "Internal User"

## 🎯 Avantages de cette Solution

✅ **Respect des règles métier Odoo** : L'API gère automatiquement :
   - Création du partner lié
   - Validation des données
   - Triggers Odoo natifs
   - Audit logs

✅ **Pas de mot de passe** : Les utilisateurs s'authentifient via LDAP

✅ **Groupe automatique** : "Internal User" attribué par le script

✅ **Réversible** : Le DeleteScript désactive au lieu de supprimer

✅ **Maintenable** : Pas de triggers SQL custom à maintenir

## 🚀 Étapes Suivantes

### 1. Importer la ressource dans MidPoint

Via l'interface Web :
```
http://localhost:8080/midpoint
→ Configuration → Repository objects → Import object
→ Coller le contenu de resource-odoo-api.xml
```

### 2. Tester la connexion

```
Resources → Odoo ERP (API)
→ Test connection
```

### 3. Réimporter le rôle Odoo_User

```
Configuration → Repository objects → Import object
→ Coller le contenu de role-odoo-user.xml
```

### 4. Tester avec un utilisateur

1. Créer un utilisateur test dans MidPoint
2. Lui attribuer le rôle `Odoo_User`
3. Vérifier dans Odoo :
   - Utilisateur créé avec le bon email
   - Groupe "Internal User" attribué
   - Peut se connecter (si LDAP configuré)

## 🐛 Dépannage

### Erreur "Authentication failed"

Vérifier :
```bash
docker exec -it odoo-db psql -U odoo -d odoo -c \
  "SELECT login, active FROM res_users WHERE login = 'midpoint_service';"
```

### Logs MidPoint

```bash
docker exec midpoint tail -f /opt/midpoint/var/log/midpoint.log
```

### Test manuel de l'API Odoo XML-RPC

```python
import xmlrpc.client

# Connexion
common = xmlrpc.client.ServerProxy('http://localhost:8069/xmlrpc/2/common')
uid = common.authenticate('odoo', 'midpoint_service', 'midpoint123', {})
print(f"Authenticated, UID: {uid}")

# Appel
objects = xmlrpc.client.ServerProxy('http://localhost:8069/xmlrpc/2/object')
result = objects.execute_kw('odoo', uid, 'midpoint123',
    'res.users', 'search_read',
    [[['login', '=', 'midpoint_service']]],
    {'fields': ['login', 'name', 'email'], 'limit': 1})
print(result)
```

## 📊 Comparaison Ancien vs Nouveau

| Aspect | Ancienne Solution (SQL) | Nouvelle Solution (XML-RPC) |
|--------|------------------------|----------------------------|
| Connexion | DatabaseTable connector | ScriptedREST + XML-RPC |
| Cible | Vue SQL custom | API Odoo XML-RPC native |
| Email | Trigger SQL | API Odoo (partner) |
| Groupes | Trigger SQL | API Odoo (groups_id) |
| Validation | Manuelle (SQL) | Automatique (ORM Odoo) |
| Audit | Limité | Complet (logs Odoo) |
| Maintenance | Triggers à maintenir | Scripts Groovy simples |
| Protocole | JDBC/PostgreSQL | XML-RPC standard |

## ✅ Résultat Final

**Provisioning complet MidPoint → Odoo** :
- ✅ Login créé
- ✅ Email synchronisé
- ✅ Nom complet renseigné
- ✅ Groupe "Internal User" attribué
- ✅ Compte actif
- ✅ Pas de mot de passe (authentification LDAP)
- ✅ Respect des règles métier Odoo
