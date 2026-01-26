# Configuration MidPoint - Ressources

## Vue d'ensemble

Ce document décrit la configuration des ressources MidPoint pour le TP IAM/IGA.

## Ressource 1 : LDAP/Active Directory

**Fichier :** `resource-ldap-groups.xml`  
**OID :** `8a83b1a4-be18-11e6-ae84-7301fdab1d7e`  
**Connecteur :** LDAP Connector

### Groupes gérés par MidPoint

- **Employee** - Groupe de base pour tous les employés
- **Internet** - Accès Internet
- **Printer** - Accès aux imprimantes
- **Public_Share_Folder_SharePoint** - Accès au partage SharePoint public

### Rôles MidPoint correspondants

- `LDAP_Employee` (OID: `12345678-d34d-b33f-f00d-987987987992`)
- `LDAP_Internet` (OID: `12345678-d34d-b33f-f00d-987987987993`)
- `LDAP_Printer` (OID: `12345678-d34d-b33f-f00d-987987987994`)
- `LDAP_Public_Share_Folder_SharePoint` (OID: `12345678-d34d-b33f-f00d-987987987995`)

## Ressource 2 : Odoo

**Fichier :** `resource-odoo-rpc.xml`  
**OID :** `8a83b1a4-be18-11e6-ae84-7301fdab1d83`  
**Connecteur :** REST Connector (API RPC Odoo)

### Rôles applicatifs Odoo

- **Odoo_User** - Utilisateur standard Odoo
- **Odoo_Finance** - Accès au module Finance
- **Odoo_Admin** - Administrateur Odoo (⚠️ **Droit critique**)

### Note importante

MidPoint ne supporte pas nativement l'API RPC Odoo (XML-RPC/JSON-RPC).  
Pour une implémentation complète, il faudrait :
1. Développer un connecteur ICF customisé pour Odoo RPC
2. Ou utiliser un connecteur REST générique avec des scripts de transformation
3. Ou utiliser le connecteur Scripted avec des scripts Python/Java

## Ressource 3 : Application métier PostgreSQL

**Fichier :** `resource-postgresql-app.xml`  
**OID :** `8a83b1a4-be18-11e6-ae84-7301fdab1d84`  
**Connecteur :** DatabaseTable Connector

### Droits base de données

- **app_read** - Droit de lecture
- **app_write** - Droit d'écriture
- **app_admin_db** - Droit d'administration base de données (⚠️ **Droit critique**)

### Rôles MidPoint correspondants

- `App_Read` (OID: `12345678-d34d-b33f-f00d-987987987996`)
- `App_Write` (OID: `12345678-d34d-b33f-f00d-987987987997`)
- `App_Admin_DB` (OID: `12345678-d34d-b33f-f00d-987987987998`)

## Ressource 4 : Application métier multi-base

**Fichier :** `resource-multibase-app.xml`  
**OID :** `8a83b1a4-be18-11e6-ae84-7301fdab1d85`  
**Connecteur :** Multi-Base Connector (customisé)

### Composants

#### 1. LDAP : Groupes

- **AppBiz_CustomGR_User**
- **AppBiz_CustomGR2_Manager**
- **AppBiz_CustomGR2_Admin**
- **AppBiz_CustomGR2_Audit**

#### 2. Base SQL PostgreSQL

**Table `users` :**
```sql
CREATE TABLE users (
    user_id INT PRIMARY KEY AUTO_INCREMENT,
    User_ldap_dn VARCHAR(100) NOT NULL,
    User_ldap_class VARCHAR(100) NOT NULL,
    user_id VARCHAR(100) NOT NULL,
    firstname VARCHAR(50) NOT NULL,
    lastname VARCHAR(50) NOT NULL,
    commonname VARCHAR(50) NOT NULL,
    email VARCHAR(50) NOT NULL,
    brithdate VARCHAR(10) NOT NULL
);
```

**Table `profiles` :**
```sql
CREATE TABLE profiles (
    profile_id INT PRIMARY KEY AUTO_INCREMENT,
    profile_name VARCHAR(50) NOT NULL
);
```

**Table `user_profile_id_permissions` :**
```sql
CREATE TABLE user_profile_id_permissions (
    urp_id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT NOT NULL,
    profile_id INT NOT NULL,
    permission_name VARCHAR(100) NOT NULL,
    is_allowed BOOLEAN DEFAULT TRUE,
    assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (profile_id) REFERENCES profiles(profile_id) ON DELETE CASCADE
);
```

#### 3. Base NoSQL : Supabase/Firebase

**Structure JSON pour la collection `users` :**
```json
{
  "firstName": "Ali",
  "lastName": "Bonalier",
  "email": "alib@gmail.com",
  "user_id": "valeur = la table SQL ou uid ldap",
  "role": "admin",
  "permissions": {
    "createUser": true,
    "deleteUser": false
  },
  "preferences": {
    "language": "fr",
    "theme": "dark"
  },
  "createdAt": "2025-01-10"
}
```

### Note importante

Cette ressource nécessite un **connecteur customisé** qui gère simultanément :
- Provisioning LDAP (groupes)
- Provisioning PostgreSQL (tables users, profiles, permissions)
- Provisioning NoSQL (Supabase/Firebase)

## Droits critiques

Les rôles suivants sont marqués comme **droits critiques** et nécessitent une approbation :

- **Odoo_Admin** - Administration complète Odoo
- **App_Admin_DB** - Administration base de données

## Import des ressources

Pour importer ces ressources dans MidPoint :

```bash
# Importer toutes les ressources
for file in config/midpoint/resources/resource-*.xml; do
    curl -u administrator:5ecr3t -X POST \
      "http://localhost:8080/midpoint/ws/rest/resources" \
      -H "Content-Type: application/xml" \
      -d @"$file"
done

# Importer tous les rôles
for file in config/midpoint/roles/role-*.xml; do
    curl -u administrator:5ecr3t -X POST \
      "http://localhost:8080/midpoint/ws/rest/roles" \
      -H "Content-Type: application/xml" \
      -d @"$file"
done
```

## Prochaines étapes

1. ✅ Configuration LDAP avec groupes
2. ⚠️ Implémentation connecteur Odoo RPC (nécessite développement)
3. ✅ Configuration PostgreSQL application métier
4. ⚠️ Développement connecteur multi-base (nécessite développement)
