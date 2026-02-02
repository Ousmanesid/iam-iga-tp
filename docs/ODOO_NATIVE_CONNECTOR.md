# Guide d'Intégration du Connecteur Odoo Natif (XML-RPC)

## 📋 Vue d'ensemble

Ce guide décrit l'intégration du connecteur Odoo natif pour MidPoint, remplaçant l'ancienne approche d'accès direct PostgreSQL par une connexion via l'API XML-RPC officielle d'Odoo.

### Avantages du Connecteur Natif

| Aspect | Ancien (DatabaseTable) | Nouveau (Odoo Connector) |
|--------|------------------------|--------------------------|
| **Connexion** | Accès direct PostgreSQL | API XML-RPC officielle |
| **Intégrité** | Contourne la logique Odoo | Respecte les workflows |
| **Sécurité** | Accès DB exposé | Authentification API |
| **Groupes** | Nécessite vues custom | Support natif `res.groups` |
| **Maintenance** | Triggers SQL complexes | Configuration déclarative |
| **Compatibilité** | Fragile aux mises à jour | API stable Odoo 10-18 |

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          ARCHITECTURE MODERNISÉE                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   ┌──────────────┐          ┌──────────────────────┐          ┌──────────┐ │
│   │   MidPoint   │ ──────►  │  Connecteur Odoo     │ ──────►  │  Odoo    │ │
│   │   (IGA)      │          │  (lu.lns.connector)  │          │  ERP     │ │
│   └──────────────┘          └──────────────────────┘          └──────────┘ │
│         │                            │                              │       │
│         │                   XML-RPC API                             │       │
│         │                   ─────────────                           │       │
│         │                   • /xmlrpc/2/common                      │       │
│         │                   • /xmlrpc/2/object                      │       │
│         │                                                           │       │
│    Opérations:              Modèles supportés:                Données:     │
│    ───────────              ──────────────────                ─────────    │
│    • Create                 • res.users                       • Utilisateurs│
│    • Update                 • res.partner                     • Partenaires │
│    • Delete                 • res.groups                      • Groupes     │
│    • Search                 • hr.employee                     • Employés    │
│    • Sync                   • hr.department                   • Départements│
│                             • hr.job                          • Postes      │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

## 📦 Fichiers Créés

### Connecteur Java
```
/srv/projet/iam-iga-tp/connectors/
├── idm-connector-odoo/          # Repository cloné depuis GitLab
│   ├── src/                     # Code source Java
│   ├── build.gradle             # Configuration Gradle
│   └── docs/                    # Documentation
└── build/
    └── connector-odoo-1.7.0-SNAPSHOT.jar   # JAR compilé
```

### Configuration MidPoint
```
/srv/projet/iam-iga-tp/config/midpoint/
├── resources/
│   └── resource-odoo-native.xml    # Ressource utilisant le connecteur natif
└── roles/
    ├── role-odoo-user-native.xml   # Rôle pour compte Odoo
    └── role-employee-v2.xml        # Rôle Employee modernisé
```

## 🚀 Installation

### Étape 1 : Vérifier le Connecteur

Le connecteur est déjà déployé dans MidPoint :
```bash
docker exec midpoint ls -la /opt/midpoint/var/icf-connectors/
# connector-odoo-1.7.0-SNAPSHOT.jar
```

### Étape 2 : Importer la Configuration

Les fichiers sont copiés dans `/opt/midpoint/var/import/`. Pour les importer :

1. **Via l'interface MidPoint** :
   - Connectez-vous à http://localhost:8080/midpoint
   - Allez dans **Configuration → Import Objects**
   - Importez les fichiers XML un par un

2. **Via la ligne de commande** (après redémarrage) :
   ```bash
   docker exec midpoint ls /opt/midpoint/var/import/
   # resource-odoo-native.xml
   # role-odoo-user-native.xml
   # role-employee-v2.xml
   ```

### Étape 3 : Tester la Connexion

1. Dans MidPoint, allez dans **Resources**
2. Trouvez **Odoo ERP (Native RPC)**
3. Cliquez sur **Test Connection**
4. Vérifiez le statut de connexion

## 📝 Configuration Détaillée

### Ressource `resource-odoo-native.xml`

```xml
<!-- Connexion -->
<odoo:url>http://odoo:8069</odoo:url>
<odoo:database>odoo</odoo:database>
<odoo:username>admin</odoo:username>
<odoo:password>admin</odoo:password>

<!-- Modèles exposés -->
<odoo:retrieveModels>
    res.users,          <!-- Utilisateurs Odoo -->
    res.partner,        <!-- Partenaires (contacts) -->
    res.groups,         <!-- Groupes/permissions -->
    hr.employee,        <!-- Employés -->
    hr.department,      <!-- Départements -->
    hr.job              <!-- Postes -->
</odoo:retrieveModels>

<!-- Expansion des relations -->
<odoo:expandRelations>
    res.users--partner_id,           <!-- User → Partner (nom, email) -->
    hr.employee--user_id,            <!-- Employee → User -->
    hr.employee--department_id,      <!-- Employee → Department -->
    hr.employee--job_id              <!-- Employee → Job -->
</odoo:expandRelations>
```

### Mapping des Attributs

| Attribut MidPoint | Attribut Odoo | Description |
|------------------|---------------|-------------|
| `name` | `login` (icfs:name) | Identifiant de connexion |
| `fullName` | `partner_id--name` | Nom complet |
| `emailAddress` | `partner_id--email` | Adresse email |
| `activation/status` | `active` | Statut actif/inactif |
| - | `groups_id` | Groupes Odoo assignés |

### Rôle `role-employee-v2.xml`

Ce rôle modernisé attribue :
1. **Compte LDAP** avec 4 groupes (Employee, Internet, Printer, SharePoint)
2. **Compte Odoo** via le connecteur natif XML-RPC

```xml
<!-- Inducement pour Odoo -->
<inducement>
    <construction>
        <resourceRef oid="8a83b1a4-be18-11e6-ae84-7301fdab1d99"/>
        <kind>account</kind>
        <intent>default</intent>
    </construction>
</inducement>
```

## 🧪 Test du Provisioning

### 1. Créer un Utilisateur Test

Dans MidPoint :
1. **Users → New User**
2. Remplir :
   - Name: `test.odoo`
   - Full Name: `Test Odoo User`
   - Email: `test.odoo@example.com`
3. **Assignments → Add → Role → Employee_v2**
4. **Save**

### 2. Vérifier dans Odoo

```bash
# Via XML-RPC Python
python3 << 'EOF'
import xmlrpc.client

url = "http://localhost:8069"
db = "odoo"
username = "admin"
password = "admin"

common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common')
uid = common.authenticate(db, username, password, {})
models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object')

# Rechercher l'utilisateur créé
users = models.execute_kw(db, uid, password, 'res.users', 'search_read', 
    [[('login', 'ilike', 'test')]],
    {'fields': ['login', 'name', 'email', 'active']})

for user in users:
    print(f"Login: {user['login']}, Name: {user['name']}, Email: {user['email']}")
EOF
```

### 3. Vérifier les Logs

```bash
docker exec midpoint grep -i "odoo" /opt/midpoint/var/log/midpoint.log | tail -20
```

## 🔍 Dépannage

### Problème : Connecteur non détecté

```bash
# Vérifier que le JAR est présent
docker exec midpoint ls /opt/midpoint/var/icf-connectors/

# Redémarrer MidPoint
docker restart midpoint

# Vérifier les logs
docker exec midpoint grep "Discovered ICF bundle" /opt/midpoint/var/log/midpoint.log
```

### Problème : Connexion Odoo échoue

1. Vérifier qu'Odoo est accessible :
   ```bash
   curl -v http://localhost:8069/web/database/list
   ```

2. Vérifier les credentials :
   ```bash
   docker exec odoo python3 -c "
   import xmlrpc.client
   common = xmlrpc.client.ServerProxy('http://localhost:8069/xmlrpc/2/common')
   print('UID:', common.authenticate('odoo', 'admin', 'admin', {}))
   "
   ```

### Problème : Schéma vide

- Vérifier que `retrieveModels` contient les bons modèles
- S'assurer que l'utilisateur Odoo a les permissions nécessaires

## 📊 Comparaison des Ressources

| OID | Nom | Type | Usage |
|-----|-----|------|-------|
| `...1d82` | Odoo ERP (PostgreSQL) | DatabaseTable | **Ancien** - Accès direct DB |
| `...1d99` | Odoo ERP (Native RPC) | OdooConnector | **Nouveau** - API XML-RPC |

## 🔄 Migration

Pour migrer de l'ancien vers le nouveau connecteur :

1. **Garder les deux ressources** en parallèle temporairement
2. **Mettre à jour les rôles** pour utiliser la nouvelle ressource (`...1d99`)
3. **Tester** avec quelques utilisateurs
4. **Migrer** progressivement les utilisateurs existants
5. **Désactiver** l'ancienne ressource

## 📚 Références

- [GitLab - idm-connector-odoo](https://gitlab.com/lns-public/idm-connector-odoo)
- [Documentation Odoo XML-RPC](https://www.odoo.com/documentation/14.0/webservices/odoo.html)
- [MidPoint Connector Development](https://docs.evolveum.com/connectors/)

---

**Date de création** : 2 Février 2026
**Version du connecteur** : 1.7.0-SNAPSHOT
**Compatible avec** : Odoo 10.x - 18.x, MidPoint 4.0+
