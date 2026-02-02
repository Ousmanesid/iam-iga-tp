# Correction du Problème d'Attribution des Groupes LDAP

## 🔴 Problème Identifié

Lorsque le rôle **Employee** était attribué à un utilisateur (Alice Doe), MidPoint créait bien les groupes LDAP mais ne liait pas correctement l'utilisateur à ces groupes. À la place, les groupes contenaient un membre fictif `cn=dummy,ou=users,dc=example,dc=com`.

### Symptômes

```bash
# Alice existe dans LDAP
uid=alice.doe,ou=users,dc=example,dc=com ✅

# Les groupes existent
cn=Employee,ou=groups,dc=example,dc=com ✅
cn=Internet,ou=groups,dc=example,dc=com ✅
cn=Printer,ou=groups,dc=example,dc=com ✅
cn=Public_Share_Folder_SharePoint,ou=groups,dc=example,dc=com ✅

# Mais Alice n'est pas membre des groupes ❌
# Recherche: (member=uid=alice.doe,ou=users,dc=example,dc=com)
# Résultat: 0 groupes trouvés

# Les groupes contiennent un membre dummy
member: cn=dummy,ou=users,dc=example,dc=com ❌
```

---

## 🔧 Cause Racine

### Architecture Incorrecte

**Avant** : Les rôles LDAP utilisaient une ressource séparée `resource-ldap-groups.xml` (OID: `8a83b1a4-be18-11e6-ae84-7301fdab1d86`) qui créait les groupes avec un membre dummy hardcodé :

```xml
<!-- ❌ INCORRECT -->
<attribute>
    <ref>ri:member</ref>
    <outbound>
        <strength>weak</strength>
        <expression>
            <value>cn=dummy,ou=users,dc=example,dc=com</value>
        </expression>
    </outbound>
</attribute>
```

Les rôles faisaient uniquement un `inducement` vers cette ressource :

```xml
<!-- ❌ INCORRECT -->
<inducement>
    <construction>
        <resourceRef oid="8a83b1a4-be18-11e6-ae84-7301fdab1d86"/> <!-- resource-ldap-groups -->
        <kind>entitlement</kind>
        <intent>group</intent>
    </construction>
</inducement>
```

### Problème

Cette approche :
- ✅ Créait bien les groupes LDAP
- ✅ Ajoutait les noms de groupes (cn) corrects
- ❌ **Mais ne liait jamais les utilisateurs aux groupes**
- ❌ Laissait `cn=dummy` comme seul membre

---

## ✅ Solution Implémentée

### 1. Utilisation de l'Association LDAP

La ressource `resource-ldap.xml` (OID: `8a83b1a4-be18-11e6-ae84-7301fdab1d7d`) contient déjà la configuration correcte avec **association** :

```xml
<!-- ✅ CORRECT - Dans resource-ldap.xml -->
<objectType>
    <kind>account</kind>
    <intent>default</intent>
    
    <!-- Association aux groupes LDAP -->
    <association>
        <ref>ri:group</ref>
        <displayName>LDAP Group Membership</displayName>
        <kind>entitlement</kind>
        <intent>group</intent>
        <direction>objectToSubject</direction>
        <associationAttribute>ri:member</associationAttribute>
        <valueAttribute>ri:dn</valueAttribute>
    </association>
</objectType>
```

### 2. Correction des Rôles LDAP

Chaque rôle (Employee, Internet, Printer, SharePoint) a été modifié pour :

**a) Créer/lier au groupe LDAP** (entitlement)

```xml
<inducement>
    <construction>
        <resourceRef oid="8a83b1a4-be18-11e6-ae84-7301fdab1d7d"/> <!-- resource-ldap -->
        <kind>entitlement</kind>
        <intent>group</intent>
        <attribute>
            <ref>ri:cn</ref>
            <outbound>
                <expression>
                    <value>Employee</value>
                </expression>
            </outbound>
        </attribute>
    </construction>
</inducement>
```

**b) Associer l'utilisateur au groupe** (association)

```xml
<inducement>
    <construction>
        <resourceRef oid="8a83b1a4-be18-11e6-ae84-7301fdab1d7d"/> <!-- resource-ldap -->
        <kind>account</kind>
        <intent>default</intent>
        
        <!-- Association automatique via le lien -->
        <association>
            <ref>ri:group</ref>
            <outbound>
                <expression>
                    <associationFromLink>
                        <projectionDiscriminator>
                            <kind>entitlement</kind>
                            <intent>group</intent>
                        </projectionDiscriminator>
                    </associationFromLink>
                </expression>
            </outbound>
        </association>
    </construction>
</inducement>
```

---

## 📋 Fichiers Modifiés

1. **`config/midpoint/roles/role-ldap-employee.xml`**
2. **`config/midpoint/roles/role-ldap-internet.xml`**
3. **`config/midpoint/roles/role-ldap-printer.xml`**
4. **`config/midpoint/roles/role-ldap-sharepoint.xml`**

Tous ont été corrigés pour utiliser :
- ✅ `resourceRef` vers `resource-ldap.xml` (OID: 8a83b1a4-be18-11e6-ae84-7301fdab1d7d)
- ✅ Double `inducement` : un pour le groupe (entitlement) + un pour l'association (account)
- ✅ Utilisation de `associationFromLink` pour lier automatiquement

---

## 🔄 Procédure de Migration

### 1. Réimporter les Rôles

```bash
cd /srv/projet/iam-iga-tp
python3 scripts/reimport_ldap_roles.py
```

### 2. Pour Chaque Utilisateur Existant

#### Via l'Interface MidPoint

1. Ouvrir MidPoint → **Users** → Sélectionner l'utilisateur (ex: Alice Doe)
2. Onglet **Assignments**
3. **Supprimer** l'assignement Employee actuel
4. Cliquer sur **Save**
5. **Ajouter** à nouveau le rôle Employee
6. Cliquer sur **Save**
7. Attendre quelques secondes (recompute automatique)

#### Vérification LDAP

```bash
# Vérifier que l'utilisateur est maintenant membre des groupes
docker exec -it openldap ldapsearch -x -H ldap://localhost \
  -b "ou=groups,dc=example,dc=com" \
  -D "cn=admin,dc=example,dc=com" -w admin \
  "(member=uid=alice.doe,ou=users,dc=example,dc=com)" dn
```

**Résultat attendu :**
```
dn: cn=Employee,ou=groups,dc=example,dc=com
dn: cn=Internet,ou=groups,dc=example,dc=com
dn: cn=Printer,ou=groups,dc=example,dc=com
dn: cn=Public_Share_Folder_SharePoint,ou=groups,dc=example,dc=com
```

---

## 🚀 Pour les Nouveaux Utilisateurs

Les nouveaux utilisateurs qui recevront le rôle **Employee** seront automatiquement :
- ✅ Créés dans LDAP (`uid=prenom.nom,ou=users,dc=example,dc=com`)
- ✅ Ajoutés aux 4 groupes LDAP avec leur DN correct
- ✅ Sans membre `dummy`

---

## 📚 Ressources Supplémentaires

### Scripts Créés

1. **`scripts/reimport_ldap_roles.py`** : Réimporte les rôles corrigés dans MidPoint
2. **`scripts/fix_alice_ldap_groups.sh`** : Correction manuelle LDAP (workaround temporaire)
3. **`scripts/recompute_alice.py`** : Force un recompute via API REST (optionnel)

### Documentation MidPoint

- [Associations](https://docs.evolveum.com/midpoint/reference/resources/resource-configuration/schema-handling/associations/)
- [Entitlements](https://docs.evolveum.com/midpoint/reference/resources/entitlements/)
- [LDAP Connector](https://docs.evolveum.com/connectors/connectors/com.evolveum.polygon.connector.ldap.LdapConnector/)

---

## ✅ Validation

Pour confirmer que le problème est résolu :

1. **Créer un nouvel utilisateur** dans Odoo
2. **Importer** dans MidPoint
3. **Assigner** le rôle Employee
4. **Vérifier** dans LDAP que l'utilisateur est membre des 4 groupes
5. **Confirmer** que `cn=dummy` n'apparaît plus

---

**Date de correction** : 29 janvier 2026  
**Testé sur** : MidPoint 4.x + OpenLDAP  
**Status** : ✅ Résolu
