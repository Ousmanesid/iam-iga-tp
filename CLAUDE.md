# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**IAM-IGA-TP** is a comprehensive Identity and Access Management (IAM) / Identity Governance and Administration (IGA) training platform. It demonstrates modern IAM practices using industry-standard tools and integrations.

### Technology Stack

- **IGA Core**: Evolveum MidPoint 4.8
- **Directory**: OpenLDAP
- **ERP/HR System**: Odoo 16 (HR module)
- **Workflow Automation**: n8n
- **API Gateway**: FastAPI (Python)
- **Database**: PostgreSQL (for Odoo, MidPoint, Intranet)
- **Container Orchestration**: Docker Compose

### Key Features

1. **User Lifecycle Management**: Automated provisioning from HR (Odoo) to downstream systems
2. **Role-Based Access Control (RBAC)**: Hierarchical role structure with automatic assignments
3. **LDAP Integration**: Group management and authentication
4. **Odoo HR Integration**: Dual connectivity (PostgreSQL direct + XML-RPC native connector)
5. **CSV-based Provisioning**: Import users from HR exports
6. **Workflow Automation**: n8n workflows for synchronization and notifications

## Project Structure

```
iam-iga-tp/
├── config/
│   ├── ldap/                    # OpenLDAP configuration
│   │   └── bootstrap.ldif       # Initial LDAP structure
│   ├── midpoint/
│   │   ├── resources/           # MidPoint resource definitions
│   │   │   ├── resource-ldap.xml              # LDAP connector
│   │   │   ├── resource-ldap-groups.xml       # LDAP groups
│   │   │   ├── resource-odoo.xml              # Odoo (PostgreSQL - legacy)
│   │   │   ├── resource-odoo-native.xml       # Odoo (XML-RPC - NEW)
│   │   │   ├── resource-hr-csv.xml            # CSV import
│   │   │   └── resource-*.xml                 # Other resources
│   │   ├── roles/               # MidPoint roles
│   │   │   ├── role-employee.xml              # Legacy Employee role
│   │   │   ├── role-employee-v2.xml           # Modern Employee role (uses native Odoo)
│   │   │   ├── role-ldap-*.xml                # LDAP group roles
│   │   │   └── role-odoo-user-native.xml      # Odoo user role (native)
│   │   ├── object-templates/    # User templates for auto-assignment
│   │   ├── tasks/               # Import/sync tasks
│   │   └── scripts/             # Groovy scripts (Odoo connector helpers)
│   ├── n8n/                     # n8n workflow definitions
│   ├── postgresql/              # PostgreSQL init scripts
│   └── rabbitmq/                # RabbitMQ config (planned)
├── data/
│   ├── hr/                      # HR CSV data
│   │   ├── hr_clean.csv         # Cleaned employee data
│   │   └── hr_raw.csv           # Raw Odoo exports
│   └── intranet/                # Intranet user data
├── scripts/
│   ├── export_odoo_to_csv.py                  # Export Odoo HR to CSV
│   ├── install-odoo-native-connector.sh       # Install native Odoo connector
│   ├── auto_assign_employee_role.py           # Auto-assign Employee role
│   └── *.py, *.sh                             # Various utility scripts
├── docker/
│   └── docker-compose.yml       # Main orchestration file
├── gateway/                     # AEGIS Gateway (FastAPI)
│   ├── app/
│   │   ├── services/            # Business logic
│   │   ├── routers/             # API endpoints
│   │   └── connectors/          # External system connectors
│   └── requirements.txt
├── connectors/                  # Custom MidPoint connectors
│   └── build/
│       └── connector-odoo-1.7.0-SNAPSHOT.jar  # Native Odoo connector
└── docs/
    ├── ODOO_NATIVE_CONNECTOR.md               # Odoo connector documentation
    ├── FIX_LDAP_GROUPS_PROBLEM.md             # LDAP troubleshooting
    └── N8N_WORKFLOW_SETUP.md                  # n8n setup guide
```

## Key Components

### MidPoint Configuration

**Resources** define how MidPoint connects to target systems:
- `resource-ldap.xml`: Main LDAP connector for user accounts
- `resource-ldap-groups.xml`: LDAP group management
- `resource-odoo-native.xml`: **NEW** - Native Odoo connector using XML-RPC API
- `resource-odoo.xml`: **LEGACY** - Direct PostgreSQL access (being replaced)
- `resource-hr-csv.xml`: CSV file import for HR data

**Roles** define access patterns:
- `role-employee-v2.xml`: **MODERN** - Uses native Odoo connector
- `role-employee.xml`: **LEGACY** - Uses PostgreSQL connector
- `role-ldap-employee.xml`, `role-ldap-internet.xml`, etc.: LDAP group assignments
- `role-odoo-user-native.xml`: Odoo account via XML-RPC

**Object Templates**:
- `user-template-auto-employee.xml`: Automatically assigns Employee role to new users

### Odoo Integration - Dual Approach

#### Legacy Approach (DatabaseTable Connector)
- **Resource**: `resource-odoo.xml` (OID: `...1d82`)
- **Method**: Direct PostgreSQL access via `DatabaseTableConnector`
- **Issues**:
  - Bypasses Odoo business logic
  - Requires SQL views and triggers
  - Fragile to Odoo updates
  - Limited group management

#### Modern Approach (Native Odoo Connector)
- **Resource**: `resource-odoo-native.xml` (OID: `...1d99`)
- **Method**: XML-RPC API via `lu.lns.connector.odoo.OdooConnector`
- **Advantages**:
  - Uses official Odoo API
  - Respects Odoo workflows
  - Native `res.groups` support
  - Compatible Odoo 10-18
  - Relation expansion (`partner_id`, `department_id`, etc.)

**Migration Strategy**: Keep both resources temporarily, migrate roles progressively to v2

### LDAP Structure

```
dc=example,dc=com
├── ou=users                 # User accounts
│   └── uid=alice.doe        # User entries (inetOrgPerson)
└── ou=groups                # Groups
    ├── cn=Employee          # Employee group
    ├── cn=Internet          # Internet access
    ├── cn=Printer           # Printer access
    └── cn=Public_Share_Folder_SharePoint  # SharePoint access
```

### Gateway (AEGIS)

FastAPI-based REST API providing:
- MidPoint API abstraction
- Odoo integration endpoints
- User provisioning workflows
- Audit logging
- Synchronization services

**Key Services**:
- `midpoint_service.py`: MidPoint REST API client
- `odoo_service.py`: Odoo XML-RPC client
- `sync_service.py`: Cross-system synchronization
- `provisioning_service.py`: Automated provisioning logic

## Development Workflow

### Container Management

```bash
# Start all services
cd docker/
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f midpoint
docker-compose logs -f odoo

# Restart a service
docker restart midpoint

# Stop all
docker-compose down
```

### MidPoint Operations

```bash
# Import MidPoint objects
curl -X POST \
  -H "Content-Type: application/xml" \
  -u administrator:5ecr3t \
  --data-binary @config/midpoint/resources/resource-odoo-native.xml \
  http://localhost:8080/midpoint/ws/rest/resources

# Test resource connection
curl -X POST \
  -u administrator:5ecr3t \
  http://localhost:8080/midpoint/ws/rest/resources/{oid}/test

# Recompute user
curl -X POST \
  -u administrator:5ecr3t \
  http://localhost:8080/midpoint/ws/rest/users/{oid}/recompute
```

### Common Tasks

**Export Odoo HR to CSV**:
```bash
python3 scripts/export_odoo_to_csv.py
```

**Auto-assign Employee Role**:
```bash
python3 scripts/auto_assign_employee_role.py
```

**Verify LDAP Groups**:
```bash
docker exec -it openldap ldapsearch -x \
  -H ldap://localhost \
  -b "ou=groups,dc=example,dc=com" \
  -D "cn=admin,dc=example,dc=com" \
  -w admin \
  "(objectClass=groupOfNames)"
```

**Check Odoo Users**:
```bash
docker exec odoo-db psql -U odoo -d odoo -c "SELECT login, name, active FROM res_users WHERE login != 'admin';"
```

## Important Notes

### User Creation Flow

1. **HR Source** (Odoo): Employee created with contract
2. **Export**: CSV export or direct sync
3. **MidPoint Import**: User created with `lifecycleState=active`
4. **Role Assignment**: 
   - Manual: Admin assigns `Employee_v2` role
   - Automatic: Object template triggers if conditions met
5. **Provisioning**:
   - LDAP account created
   - LDAP groups assigned (Employee, Internet, Printer, SharePoint)
   - Odoo user account created via XML-RPC

### Credentials

- **MidPoint**: `administrator` / `5ecr3t`
- **Odoo**: `admin` / `admin`
- **OpenLDAP**: `cn=admin,dc=example,dc=com` / `admin`
- **PostgreSQL** (Odoo): `odoo` / `odoo`
- **n8n**: Web interface at http://localhost:5678

### Known Issues

1. **LDAP Group Creation**: Groups must be pre-created in LDAP before role assignment
2. **MidPoint LDAP Integration**: Use `ou=users` not `ou=people` for user DN
3. **Odoo Password**: Set via MidPoint doesn't work for legacy connector (use native connector)
4. **CSV Import**: Ensure UTF-8 encoding and proper field mapping

### Recent Changes (February 2026)

- ✅ Added native Odoo connector (`connector-odoo-1.7.0-SNAPSHOT.jar`)
- ✅ Created `resource-odoo-native.xml` with XML-RPC configuration
- ✅ Created `role-employee-v2.xml` using native connector
- ✅ Fixed LDAP group provisioning (Employee, Internet, Printer, SharePoint)
- ✅ Implemented CSV-based HR import
- ✅ Added object template for automatic Employee role assignment

## Testing Scenarios

### Scenario 1: Alice Doe (Manual Creation)
See: [GUIDE_SCENARIO_1_ALICE_DOE.md](GUIDE_SCENARIO_1_ALICE_DOE.md)

1. Create employee in Odoo
2. Export to CSV
3. Import to MidPoint
4. Manually assign Employee role
5. Verify LDAP and Odoo accounts created

### Scenario 2: Auto-Assignment
See: [GUIDE_SCENARIO_2_AUTO_ASSIGNMENT.md](GUIDE_SCENARIO_2_AUTO_ASSIGNMENT.md)

1. Import HR CSV
2. Object template auto-assigns Employee role
3. Automatic provisioning to LDAP and Odoo

### Scenario 3: CSV Provisioning
See: [GUIDE_PROVISIONING_CSV.md](GUIDE_PROVISIONING_CSV.md)

1. Export Odoo HR to CSV
2. Clean and format CSV
3. Import via MidPoint task
4. Verify provisioning

## Troubleshooting

### MidPoint Logs
```bash
docker exec midpoint tail -f /opt/midpoint/var/log/midpoint.log
```

### LDAP Debug
```bash
docker exec -it openldap ldapsearch -x -LLL \
  -H ldap://localhost \
  -b "dc=example,dc=com" \
  -D "cn=admin,dc=example,dc=com" \
  -w admin \
  "(uid=alice.doe)"
```

### Odoo API Test
```python
import xmlrpc.client

url = "http://localhost:8069"
db = "odoo"
username = "admin"
password = "admin"

common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common')
uid = common.authenticate(db, username, password, {})
print(f"Authenticated as UID: {uid}")

models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object')
users = models.execute_kw(db, uid, password, 'res.users', 'search_read',
    [[('login', '!=', 'admin')]],
    {'fields': ['login', 'name', 'email']})
print(f"Users: {users}")
```

### Gateway Health Check
```bash
curl http://localhost:8000/health
```

## Development Guidelines

### Adding a New Resource

1. Create XML file in `config/midpoint/resources/`
2. Define connector configuration
3. Configure schema handling
4. Set up synchronization rules
5. Test connection
6. Import into MidPoint

### Creating a New Role

1. Create XML file in `config/midpoint/roles/`
2. Define inducements (constructions for accounts)
3. Set requestable and risk level
4. Import into MidPoint
5. Test assignment

### Modifying LDAP Schema

1. Update `config/ldap/bootstrap.ldif`
2. Rebuild LDAP container: `docker-compose up -d --force-recreate openldap`
3. Update MidPoint LDAP resource if needed

### Adding a Script

1. Create script in `scripts/`
2. Make executable: `chmod +x script.sh`
3. Document in README or guide
4. Test in isolation first

## References

- [MidPoint Documentation](https://docs.evolveum.com/midpoint/)
- [Odoo XML-RPC API](https://www.odoo.com/documentation/16.0/developer/reference/external_api.html)
- [OpenLDAP Admin Guide](https://www.openldap.org/doc/admin24/)
- [ConnId Framework](https://connid.tirasa.net/)
- [Odoo Connector GitLab](https://gitlab.com/lns-public/idm-connector-odoo)

## Quick Start

```bash
# Clone the repository
git clone https://github.com/Ousmanesid/iam-iga-tp.git
cd iam-iga-tp

# Start all services
cd docker
docker-compose up -d

# Wait for services to be ready (2-3 minutes)
docker-compose ps

# Access interfaces
# MidPoint: http://localhost:8080/midpoint (administrator/5ecr3t)
# Odoo: http://localhost:8069 (admin/admin)
# Gateway: http://localhost:8000/docs
# n8n: http://localhost:5678

# Install native Odoo connector
./scripts/install-odoo-native-connector.sh

# Import sample data
python3 scripts/export_odoo_to_csv.py
# Then import via MidPoint UI: Resources → HR CSV → Import task
```

---

**Last Updated**: February 2, 2026  
**Project Status**: Active Development  
**Primary Maintainer**: Ousmanesid
