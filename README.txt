================================================================================
    PROJET IGA - GESTION DES IDENTITÉS ET DES ACCÈS
    Identity and Access Governance avec MidPoint
================================================================================

INFORMATIONS GÉNÉRALES
================================================================================

Auteur(s)     : Équipe TP IGA (BUT3 Informatique)
Co-auteur     : achibani@gmail.com
Date          : Novembre 2024
Formation     : BUT3 Informatique - SAE Gestion des Identités
Version       : 2.0

DESCRIPTION DU PROJET
================================================================================

Ce projet implémente une solution complète de gouvernance des identités et des
accès (IGA) utilisant :

- Evolveum MidPoint 4.8 (plateforme IAM open-source)
- OpenLDAP (serveur LDAP/Active Directory)
- Odoo ERP 17.0 (source RH et provisioning utilisateurs)
- PostgreSQL (applications métier)
- N8N (workflow d'approbation)
- Gateway HTTP (orchestration)
- Docker / docker-compose (déploiement conteneurisé)

L'architecture met en œuvre :
  - Import automatique des identités depuis Odoo HR / CSV
  - Provisioning vers LDAP (authentification, groupes)
  - Provisioning vers Odoo ERP (utilisateurs et rôles)
  - Provisioning vers applications PostgreSQL
  - Politique RBAC (Role-Based Access Control)
  - Politique ABAC (Attribute-Based Access Control)
  - Auto-assignation de rôles basée sur les attributs métier
  - Workflows d'approbation pour droits critiques

================================================================================
RESSOURCES CONFIGURÉES (MidPoint)
================================================================================

RESSOURCE 1 : Apache DS/LDAP / Active Directory
-----------------------------------------------
Connecteur : LDAP (com.evolveum.polygon.connector.ldap.LdapConnector)
Fichiers   : config/midpoint/resources/resource-ldap.xml (comptes utilisateurs)
             config/midpoint/resources/resource-ldap-groups.xml (groupes)

Groupes gérés par MidPoint :
  - Employee                       (tous les employés)
  - Internet                       (accès Internet autorisé)
  - Printer                        (accès imprimantes)
  - Public_Share_Folder_SharePoint (partage SharePoint)

Rôles MidPoint correspondants :
  - LDAP_Employee (OID: 12345678-d34d-b33f-f00d-987987987992)
  - LDAP_Internet (OID: 12345678-d34d-b33f-f00d-987987987993)
  - LDAP_Printer (OID: 12345678-d34d-b33f-f00d-987987987994)
  - LDAP_Public_Share_Folder_SharePoint (OID: 12345678-d34d-b33f-f00d-987987987995)

RESSOURCE 2 : Odoo ERP
----------------------
Connecteur : REST Connector (API RPC Odoo) - Note: nécessite connecteur customisé
Fichiers   : config/midpoint/resources/resource-odoo-rpc.xml (API RPC)
             config/midpoint/resources/resource-odoo.xml (PostgreSQL direct - alternatif)
             config/midpoint/resources/resource-odoo-hr.xml (source HR)

Rôles applicatifs :
  - Odoo_User    : Utilisateur standard ERP
  - Odoo_Finance : Accès module Finance
  - Odoo_Admin   : Administrateur (DROIT CRITIQUE - nécessite approbation)

Note: L'API RPC Odoo nécessite un connecteur customisé. En attendant,
      on peut utiliser resource-odoo.xml (PostgreSQL direct) comme alternative.

RESSOURCE 3 : Application Métier (PostgreSQL)
--------------------------------------------------------
Connecteur : DatabaseTable (org.identityconnectors.databasetable)
Fichier    : config/midpoint/resources/resource-postgresql-app.xml

Droits base de données :
  - app_read     : Lecture seule
  - app_write    : Lecture/écriture
  - app_admin_db : Administration BDD (DROIT CRITIQUE)

Rôles MidPoint correspondants :
  - App_Read (OID: 12345678-d34d-b33f-f00d-987987987996)
  - App_Write (OID: 12345678-d34d-b33f-f00d-987987997)
  - App_Admin_DB (OID: 12345678-d34d-b33f-f00d-987987987998)

RESSOURCE 4 : Application Multi-base
----------------------------------------------
Connecteur : Multi-Base Connector (customisé - À DÉVELOPPER)
Fichier    : config/midpoint/resources/resource-multibase-app.xml

Composants :
  - LDAP : Groupes AppBiz_CustomGR_User, AppBiz_CustomGR2_Manager,
           AppBiz_CustomGR2_Admin, AppBiz_CustomGR2_Audit
  - PostgreSQL : Tables users, profiles, user_profile_id_permissions
                 (Schéma: config/postgresql/appbiz-schema.sql)
  - NoSQL : Supabase/Firebase (collection users avec structure JSON)

Note: Cette ressource nécessite un connecteur customisé qui gère
      simultanément LDAP, PostgreSQL et NoSQL.

================================================================================
ARCHITECTURE DU PROJET
================================================================================

/iam-iga-tp/
  |
  +-- docker/
  |   +-- docker-compose.yml           # Orchestration des conteneurs
  |
  +-- scripts/
  |   +-- up.sh                        # Démarrage de la stack
  |   +-- down.sh                      # Arrêt de la stack
  |   +-- reset.sh                     # Réinitialisation complète
  |   +-- init-ldap.sh                 # Initialisation LDAP
  |   +-- sync_all.py                  # Synchronisation complète
  |   +-- ...                          # Autres scripts utilitaires
  |
  +-- config/
  |   +-- midpoint/
  |   |   +-- resources/
  |   |   |   +-- resource-ldap.xml           # Ressource 1: LDAP
  |   |   |   +-- resource-odoo.xml           # Ressource 2: Odoo
  |   |   |   +-- resource-odoo-hr.xml        # Source HR Odoo
  |   |   |   +-- resource-homeapp-postgresql.xml # Ressource 3: PostgreSQL
  |   |   |   +-- resource-hr-csv.xml         # Source CSV RH
  |   |   |   +-- resource-intranet-csv.xml   # Cible Intranet
  |   |   +-- roles/
  |   |   |   +-- role-odoo-user.xml          # Rôle Odoo User
  |   |   |   +-- role-odoo-finance.xml       # Rôle Odoo Finance
  |   |   |   +-- role-odoo-admin.xml         # Rôle Odoo Admin (critique)
  |   |   |   +-- role-agent-commercial.xml   # Rôle ABAC
  |   |   |   +-- role-homeapp-*.xml          # Rôles Home App
  |   |   |   +-- ...
  |   |   +-- tasks/
  |   |       +-- task-hr-import.xml          # Import périodique
  |   |       +-- task-odoo-hr-sync.xml       # Sync Odoo HR
  |   +-- ldap/
  |   |   +-- bootstrap.ldif           # Structure LDAP + groupes
  |   +-- homeapp/
  |   |   +-- init.sql                 # Schéma PostgreSQL Home App
  |   +-- n8n/
  |       +-- workflows/               # Workflows d'approbation
  |
  +-- gateway/                         # API Gateway Python
  |
  +-- data/
  |   +-- hr/                          # Données RH
  |   +-- intranet/                    # Comptes Intranet
  |
  +-- docs/                            # Documentation
  +-- reports/                         # Rapports et livrables
  +-- README.txt                       # Ce fichier

DÉMARRAGE RAPIDE
================================================================================

PRÉREQUIS
---------
- Docker installé (version 20.10+)
- Docker Compose installé (version 2.0+)
- Python 3.8+ (pour les scripts)
- 8 Go de RAM minimum
- Ports disponibles : 8080, 8069, 8090, 8000, 5678, 10389, 5433, 5434

ÉTAPE 1 : Démarrer la stack Docker
-----------------------------------
cd /root/iam-iga-tp
./scripts/up.sh

Le démarrage prend environ 3-5 minutes (MidPoint est lent à démarrer).

ÉTAPE 2 : Initialiser le serveur LDAP
--------------------------------------
./scripts/init-ldap.sh

ÉTAPE 3 : Accéder aux interfaces
---------------------------------
MidPoint IAM    : http://localhost:8080/midpoint
                  Login: administrator / Mot de passe: 5ecr3t

Odoo ERP        : http://localhost:8069
                  Login: admin / Mot de passe: admin

Gateway API     : http://localhost:8000
                  (API REST pour provisioning)

N8N Workflows   : http://localhost:5678
                  Login: admin / Mot de passe: admin123

Intranet App    : http://localhost:8090
                  (Application PHP de test)

LDAP Server     : ldap://localhost:10389
                  Bind DN: cn=admin,dc=example,dc=com
                  Password: admin

PostgreSQL (Intranet)  : localhost:5433
PostgreSQL (Home App)  : localhost:5434

CONFIGURATION MIDPOINT
================================================================================

ÉTAPE 1 : Importer les ressources
----------------------------------
Option A - Via script automatique (recommandé) :
   ./scripts/import-midpoint-resources.sh

Option B - Via interface MidPoint :
1. Se connecter à MidPoint (administrator / 5ecr3t)
2. Aller dans Configuration > Repository objects > Import object
3. Importer les fichiers dans cet ordre :

   a) config/midpoint/resources/resource-ldap.xml        (Ressource 1: LDAP comptes)
   b) config/midpoint/resources/resource-ldap-groups.xml (Ressource 1: LDAP groupes)
   c) config/midpoint/resources/resource-odoo-rpc.xml    (Ressource 2: Odoo RPC)
   d) config/midpoint/resources/resource-odoo.xml        (Ressource 2: Odoo PostgreSQL - alternatif)
   e) config/midpoint/resources/resource-odoo-hr.xml     (Source HR Odoo)
   f) config/midpoint/resources/resource-postgresql-app.xml (Ressource 3: PostgreSQL App)
   g) config/midpoint/resources/resource-multibase-app.xml  (Ressource 4: Multi-base)
   h) config/midpoint/resources/resource-hr-csv.xml      (Source CSV - optionnel)
   i) config/midpoint/resources/resource-intranet-csv.xml (Cible Intranet)

4. Pour chaque ressource :
   - Resources > [Nom de la ressource] > Test connection
   - Vérifier que le test réussit (Success)

ÉTAPE 2 : Importer les rôles
-----------------------------
1. Configuration > Repository objects > Import object
2. Importer tous les rôles :

   Rôles LDAP (Ressource 1):
   a) config/midpoint/roles/role-ldap-employee.xml
   b) config/midpoint/roles/role-ldap-internet.xml
   c) config/midpoint/roles/role-ldap-printer.xml
   d) config/midpoint/roles/role-ldap-sharepoint.xml

   Rôles Odoo (Ressource 2):
   e) config/midpoint/roles/role-odoo-user.xml
   f) config/midpoint/roles/role-odoo-finance.xml
   g) config/midpoint/roles/role-odoo-admin.xml          [CRITIQUE]

   Rôles PostgreSQL App (Ressource 3):
   h) config/midpoint/roles/role-app-read.xml
   i) config/midpoint/roles/role-app-write.xml
   j) config/midpoint/roles/role-app-admin-db.xml        [CRITIQUE]

   Rôles Home App (optionnel):
   k) config/midpoint/roles/role-homeapp-user.xml
   l) config/midpoint/roles/role-homeapp-commercial.xml
   m) config/midpoint/roles/role-homeapp-admin.xml       [CRITIQUE]

   Autres rôles métier:
   n) config/midpoint/roles/role-agent-commercial.xml    (ABAC)
   o) config/midpoint/roles/role-comptable.xml
   p) config/midpoint/roles/role-it-admin.xml
   q) config/midpoint/roles/role-rh-manager.xml

ÉTAPE 3 : Importer les tâches
------------------------------
1. Configuration > Repository objects > Import object
2. Importer :
   - config/midpoint/tasks/task-hr-import.xml
   - config/midpoint/tasks/task-odoo-hr-sync.xml

3. Lancer manuellement : Server Tasks > [Tâche] > Run now

ÉTAPE 4 : Vérifier le provisioning
-----------------------------------
1. Users > All users : vérifier les utilisateurs importés
2. Pour chaque utilisateur, vérifier les projections (onglet Projections):
   - Compte LDAP créé
   - Compte Odoo créé (si rôle Odoo assigné)
   - Compte Home App créé (si rôle Home App assigné)

ÉTAPE 5 : Tester l'auto-assignation ABAC
-----------------------------------------
1. Sélectionner un utilisateur du département "Commercial"
2. Cliquer sur "Recompute" (forcer l'évaluation des règles)
3. Vérifier dans l'onglet "Assignments" la présence du rôle auto-assigné

TESTS ET VALIDATION
================================================================================

SCÉNARIOS COUVERTS :
--------------------
[x] Scénario 1 : Import initial des identités RH (Odoo ou CSV)
[x] Scénario 2 : Provisioning LDAP (groupes Employee, Internet, etc.)
[x] Scénario 3 : Auto-assignation du rôle (ABAC - département Commercial)
[x] Scénario 4 : Provisioning vers Odoo (Ressource 2)
[x] Scénario 5 : Provisioning vers Home App PostgreSQL (Ressource 3)
[x] Scénario 6 : Changement de département -> révocation/assignation rôle
[x] Scénario 7 : Suspension d'un utilisateur
[x] Scénario 8 : Demande de droit critique -> workflow d'approbation

COMMANDES DE VÉRIFICATION :
---------------------------

# Vérifier les utilisateurs dans LDAP
ldapsearch -x -H ldap://localhost:10389 \
  -D "cn=admin,dc=example,dc=com" -w admin \
  -b "ou=users,dc=example,dc=com"

# Vérifier les groupes LDAP (incluant les nouveaux)
ldapsearch -x -H ldap://localhost:10389 \
  -D "cn=admin,dc=example,dc=com" -w admin \
  -b "ou=groups,dc=example,dc=com" "(cn=*)"

# Vérifier les utilisateurs Odoo
docker exec -it odoo-db psql -U odoo -d odoo -c "SELECT id, login, active FROM res_users;"

# Vérifier les utilisateurs Home App
docker exec -it homeapp-db psql -U homeapp -d homeapp -c "SELECT login, email, is_active FROM users;"

# Vérifier les permissions Home App
docker exec -it homeapp-db psql -U homeapp -d homeapp -c "SELECT * FROM permissions;"

# Voir les logs MidPoint
cd docker && docker-compose logs -f midpoint

# Tester la Gateway API
curl http://localhost:8000/health

POLITIQUE IAM IMPLÉMENTÉE
================================================================================

MODÈLE HYBRIDE : RBAC + ABAC
-----------------------------

RBAC (Role-Based Access Control)
----------------------------------
Rôles définis avec hiérarchie de permissions :

  Ressource 2 - Odoo ERP:
  - Odoo_User    : Accès de base ERP
  - Odoo_Finance : Module Finance (inclut Odoo_User)
  - Odoo_Admin   : Administration complète [CRITIQUE]

  Ressource 3 - Application Métier:
  - app_read     : Lecture seule base de données
  - app_write    : Lecture/écriture
  - app_admin_db : Administration BDD [CRITIQUE]

  Autres rôles métier:
  - Agent Commercial, Comptable, RH Manager, IT Admin...

ABAC (Attribute-Based Access Control)
--------------------------------------
  Condition d'auto-assignation : department = "Commercial"
  Évaluation dynamique :
     - Si un utilisateur rejoint le département Commercial
       -> Le rôle est automatiquement assigné
     - Si un utilisateur quitte le département Commercial
       -> Le rôle est automatiquement révoqué

DROITS CRITIQUES (nécessitent approbation)
------------------------------------------
  - Odoo_Admin      : Administration Odoo ERP
  - app_admin_db    : Administration base de données
  - IT_ADMIN        : Administration système

PROVISIONING :
---------------
  Sources :
    - Odoo HR (table hr_employee)
    - CSV RH (hr_clean.csv) - alternatif
         |
         v
  MidPoint (base centrale d'identités)
         |
         +---> LDAP (Ressource 1)
         |       - Authentification
         |       - Groupes: Employee, Internet, Printer, SharePoint
         |
         +---> Odoo ERP (Ressource 2)
         |       - Comptes utilisateurs res_users
         |       - Rôles: User, Finance, Admin
         |
         +---> PostgreSQL Home App (Ressource 3)
         |       - Comptes et permissions granulaires
         |       - Droits: app_read, app_write, app_admin_db
         |
         +---> (Futur) Multi-base (Ressource 4)
                 - LDAP + PostgreSQL + NoSQL

DONNÉES DE TEST
================================================================================

FICHIER : data/hr/hr_raw.csv
  - 15 employés fictifs
  - Départements : Commercial, RH, IT, Comptabilité, Marketing
  - Statuts : Active, Suspended

DÉPARTEMENTS ET EFFECTIFS :
  - Commercial        : 6 employés (dont 1 suspendu)
  - Informatique      : 3 employés
  - Marketing         : 2 employés
  - Ressources Humaines : 2 employés
  - Comptabilité      : 2 employés

COMMANDES UTILES
================================================================================

GESTION DE LA STACK :
----------------------
./scripts/up.sh         # Démarrer tous les services
./scripts/down.sh       # Arrêter tous les services
./scripts/reset.sh      # Réinitialisation complète (ATTENTION: supprime les données)

GESTION DES DONNÉES :
---------------------
python3 scripts/clean_hr_csv.py    # Nettoyer le CSV RH
./scripts/init-ldap.sh             # Réinitialiser la structure LDAP
python3 scripts/sync_all.py        # Synchronisation complète

LOGS :
------
cd docker
docker-compose logs -f             # Tous les logs
docker-compose logs -f midpoint    # Logs MidPoint uniquement
docker-compose logs -f openldap    # Logs LDAP uniquement
docker-compose logs -f gateway     # Logs Gateway uniquement

ÉTAT DES SERVICES :
-------------------
cd docker
docker-compose ps                  # Liste des conteneurs

DÉBOGAGE
================================================================================

PROBLÈME : MidPoint ne démarre pas
-> Vérifier les logs : docker-compose logs midpoint
-> Augmenter la mémoire Docker (minimum 4 Go)

PROBLÈME : Connexion LDAP échoue
-> Vérifier qu'OpenLDAP est démarré : docker-compose ps
-> Tester la connexion : ldapsearch -x -H ldap://localhost:10389 -D "cn=admin,dc=example,dc=com" -w admin -b "dc=example,dc=com"
-> Réinitialiser : ./scripts/init-ldap.sh

PROBLÈME : Connexion Odoo échoue
-> Vérifier que odoo-db est démarré : docker-compose ps
-> Tester : docker exec -it odoo-db psql -U odoo -d odoo -c "SELECT 1;"

PROBLÈME : Connexion Home App échoue
-> Vérifier que homeapp-db est démarré : docker-compose ps
-> Tester : docker exec -it homeapp-db psql -U homeapp -d homeapp -c "SELECT 1;"

PROBLÈME : Import CSV RH échoue
-> Vérifier que le fichier hr_clean.csv existe
-> Vérifier le format du CSV (encoding UTF-8, délimiteur virgule)
-> Relancer : python3 scripts/clean_hr_csv.py

PROBLÈME : Rôle pas auto-assigné
-> Forcer le recalcul : dans MidPoint, sélectionner l'utilisateur > Recompute
-> Vérifier la condition ABAC dans le rôle
-> Vérifier que l'utilisateur a bien organization = "Commercial"

PROBLÈME : Droit critique non approuvé
-> Vérifier dans N8N (http://localhost:5678) les workflows en attente
-> Vérifier les logs de la Gateway

RESSOURCES ET DOCUMENTATION
================================================================================

Documentation MidPoint : https://docs.evolveum.com/midpoint/
Apache Directory       : https://directory.apache.org/
Odoo Documentation     : https://www.odoo.com/documentation
N8N Documentation      : https://docs.n8n.io/

LIVRABLES DU TP
================================================================================

[x] README.txt (ce fichier)
[x] docker-compose.yml et scripts d'automatisation

[x] Fichiers de configuration MidPoint (XML)
    Ressources :
    - resource-ldap.xml               (Ressource 1: LDAP)
    - resource-odoo.xml               (Ressource 2: Odoo)
    - resource-odoo-hr.xml            (Source HR)
    - resource-homeapp-postgresql.xml (Ressource 3: PostgreSQL)
    - resource-hr-csv.xml             (Source CSV)
    - resource-intranet-csv.xml       (Cible Intranet)

    Rôles :
    - role-odoo-user.xml              (Odoo User)
    - role-odoo-finance.xml           (Odoo Finance)
    - role-odoo-admin.xml             (Odoo Admin - CRITIQUE)
    - role-homeapp-user.xml           (Home App User)
    - role-homeapp-commercial.xml     (Home App Commercial)
    - role-homeapp-admin.xml          (Home App Admin - CRITIQUE)
    - role-agent-commercial.xml       (ABAC)
    - role-comptable.xml
    - role-it-admin.xml
    - role-rh-manager.xml

    Tâches :
    - task-hr-import.xml
    - task-odoo-hr-sync.xml

[x] Structure LDAP (bootstrap.ldif)
    - Groupes TP: Employee, Internet, Printer, Public_Share_Folder_SharePoint
    - Groupes multi-base: AppBiz_CustomGR_*

[x] Schéma PostgreSQL (config/homeapp/init.sql)
    - Permissions: app_read, app_write, app_admin_db
    - Permissions: odoo.access, odoo.finance, odoo.admin
    - Rôles: APP_READ, APP_WRITE, APP_ADMIN_DB, ODOO_USER, ODOO_FINANCE, ODOO_ADMIN

[x] Gateway HTTP (gateway/)
[x] Workflows N8N (config/n8n/workflows/)

[ ] Ressource 4 - Multi-base (À FAIRE)
[ ] Rapport technique [À compléter dans reports/]

CONTACT
================================================================================

Pour toute question concernant ce projet :
-> Co-auteur : achibani@gmail.com

================================================================================
                            FIN DU README
================================================================================

