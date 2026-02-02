"""
Aegis Gateway - Point d'entrée principal de l'application.

🛡️ Gateway IA pour la gestion des identités et des accès (IAM/IGA)
"""


print("DEBUG: Aegis Gateway Starting Loading...")

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.routes import router as api_router
from app.routers.odoo import router as odoo_router
from app.routers.roles import router as roles_router
from app.routers.audit import router as audit_router
from app.routers.midpoint import router as midpoint_router
from app.routers.connectors import router as connectors_router
from app.routers.notifications import router as notifications_router
from app.database.models import init_db

# Création de l'application FastAPI
app = FastAPI(

    title=settings.PROJECT_NAME,
    description="Gateway IA pour la gestion des identités et des accès",
    version=settings.VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# Configuration CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialisation de la base de données au démarrage
@app.on_event("startup")
async def startup_event():
    """Initialise la base de données au démarrage."""
    init_db()

# Inclusion des routes API
app.include_router(api_router)
app.include_router(odoo_router, prefix="/api/v1")
app.include_router(roles_router, prefix="/api/v1")
app.include_router(audit_router, prefix="/api/v1")
app.include_router(midpoint_router, prefix="/api/v1")
app.include_router(connectors_router, prefix="/api/v1")
app.include_router(notifications_router, prefix="/api/v1")


@app.get("/health", tags=["Health"])
async def health_check():
    """
    🏥 Health Check Endpoint
    
    Vérifie que l'API est opérationnelle.
    """
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
