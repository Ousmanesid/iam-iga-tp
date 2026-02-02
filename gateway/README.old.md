# Aegis Gateway

Gateway d'orchestration IAM pour synchroniser les identités entre Odoo HR, MidPoint et LDAP.

## Architecture

```
Odoo HR → Aegis Gateway → CSV → MidPoint → LDAP/Odoo
```

## Endpoints

- `GET /health` - Health check
- `GET /sync/status` - Statut synchronisation
- `POST /sync/odoo-to-csv` - Export Odoo → CSV
- `POST /sync/csv-to-midpoint` - Import CSV → MidPoint
- `POST /sync/full` - Synchronisation complète
- `POST /sync/full/async` - Sync en arrière-plan

## Démarrage

```bash
docker-compose build aegis-gateway
docker-compose up -d aegis-gateway
```

## Utilisation

```bash
# Sync complète
curl -X POST http://localhost:8000/sync/full

# Statut
curl http://localhost:8000/sync/status

# Documentation
open http://localhost:8000/docs
```
