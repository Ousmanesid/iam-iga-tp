"""
Gateway IAM - Point d'entrée de l'application
Interface HTTP entre MidPoint, N8N, PostgreSQL (Home App) et Supabase
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import structlog
import logging
from datetime import datetime

from app.config import settings
from app.services.homeapp_db import homeapp_db
from app.services.n8n import n8n_service
from app.services.midpoint import midpoint_service
from app.services.llm import llm_service
from app.routers import provision_router, workflow_router, chatbot_router

# Configuration du logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logging.basicConfig(
    format="%(message)s",
    level=logging.INFO if not settings.app_debug else logging.DEBUG
)

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gestion du cycle de vie de l'application"""
    # Démarrage
    logger.info("Starting Gateway IAM", env=settings.app_env, debug=settings.app_debug)
    
    # Connexion à la base de données Home App
    try:
        await homeapp_db.connect()
        logger.info("Connected to HomeApp database")
    except Exception as e:
        logger.error("Failed to connect to HomeApp database", error=str(e))
    
    yield
    
    # Arrêt
    logger.info("Shutting down Gateway IAM")
    await homeapp_db.disconnect()


# Création de l'application FastAPI
app = FastAPI(
    title=settings.app_title,
    description="""
## Gateway IAM - Interface de gestion des identités et accès

Cette API sert d'interface entre:
- **MidPoint**: Plateforme IAM centrale
- **N8N**: Orchestration des workflows d'approbation
- **Home App PostgreSQL**: Application métier cible
- **Supabase**: Alternative cloud (optionnel)

### Fonctionnalités principales:

#### Provisioning
- Création, modification, suppression d'utilisateurs
- Assignation et révocation de rôles
- Gestion des permissions directes

#### Workflows
- Pré-provisioning avec approbation
- Post-provisioning avec revue
- Workflows multi-étapes

#### Chatbot IAM
- Interface conversationnelle
- Support LLM cloud (OpenAI/Claude) et local (Ollama)
- Exécution automatique des actions IAM
    """,
    version=settings.app_version,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configuration CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En production, restreindre les origines
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# === Gestion des erreurs ===

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error("Unhandled exception", error=str(exc), path=request.url.path)
    return JSONResponse(
        status_code=500,
        content={
            "error": "internal_server_error",
            "message": str(exc) if settings.app_debug else "Une erreur interne s'est produite",
            "timestamp": datetime.utcnow().isoformat()
        }
    )


# === Routes principales ===

@app.get("/", summary="Accueil")
async def root():
    """Page d'accueil de la Gateway IAM"""
    return {
        "name": settings.app_title,
        "version": settings.app_version,
        "status": "running",
        "documentation": "/docs",
        "endpoints": {
            "provisioning": "/provision",
            "workflows": "/workflow",
            "chatbot": "/chat"
        }
    }


@app.get("/health", summary="Health check")
async def health_check():
    """
    Vérifier l'état de santé de la Gateway et de ses dépendances
    """
    health = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "services": {}
    }
    
    # Vérifier Home App DB
    try:
        await homeapp_db.ensure_connected()
        health["services"]["homeapp_db"] = {"status": "up"}
    except Exception as e:
        health["services"]["homeapp_db"] = {"status": "down", "error": str(e)}
        health["status"] = "degraded"
    
    # Vérifier N8N
    try:
        n8n_healthy = await n8n_service.health_check()
        health["services"]["n8n"] = {"status": "up" if n8n_healthy else "down"}
        if not n8n_healthy:
            health["status"] = "degraded"
    except Exception as e:
        health["services"]["n8n"] = {"status": "down", "error": str(e)}
        health["status"] = "degraded"
    
    # Vérifier MidPoint
    try:
        mp_healthy = await midpoint_service.health_check()
        health["services"]["midpoint"] = {"status": "up" if mp_healthy else "down"}
        if not mp_healthy:
            health["status"] = "degraded"
    except Exception as e:
        health["services"]["midpoint"] = {"status": "down", "error": str(e)}
        health["status"] = "degraded"
    
    # Vérifier LLM
    try:
        llm_status = await llm_service.health_check()
        health["services"]["llm"] = {
            "status": "up" if (llm_status.get("cloud_available") or llm_status.get("local_available")) else "down",
            "provider": settings.llm_provider,
            "cloud_available": llm_status.get("cloud_available", False),
            "local_available": llm_status.get("local_available", False)
        }
    except Exception as e:
        health["services"]["llm"] = {"status": "down", "error": str(e)}
    
    return health


@app.get("/config", summary="Configuration (debug)")
async def get_config():
    """
    Afficher la configuration actuelle (en mode debug uniquement)
    """
    if not settings.app_debug:
        return {"message": "Configuration masquée en production"}
    
    return {
        "app_env": settings.app_env,
        "homeapp_db_host": settings.homeapp_db_host,
        "midpoint_url": settings.midpoint_url,
        "n8n_url": settings.n8n_url,
        "llm_provider": settings.llm_provider,
        "supabase_enabled": settings.supabase_enabled
    }


# === Inclusion des routers ===

app.include_router(provision_router)
app.include_router(workflow_router)
app.include_router(chatbot_router)


# === Point d'entrée pour uvicorn ===

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.app_port,
        reload=settings.app_debug
    )








