"""Configuration centrale de l'application."""
from pydantic_settings import BaseSettings
from typing import List, Optional
import secrets


class Settings(BaseSettings):
    """Configuration de l'application."""
    
    PROJECT_NAME: str = "Aegis Gateway"
    VERSION: str = "1.0.0"
    DEBUG: bool = True
    API_V1_PREFIX: str = "/api/v1"
    
    # Database
    DATABASE_URL: str = "sqlite:///./aegis.db"
    
    # CORS - En production, listez explicitement les origins autorisées
    CORS_ORIGINS: List[str] = [
        "http://localhost:5173", 
        "http://localhost:5174",
        "http://136.119.23.158:5173",
        "http://136.119.23.158:5174"
    ]
    
    # Security - IMPORTANT: Changez la SECRET_KEY en production !
    SECRET_KEY: str = secrets.token_urlsafe(32)  # Génération automatique par défaut
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Demo Mode
    DEMO_MODE: bool = True
    DEMO_TOKEN: str = "aegis-demo-2024"
    
    # Odoo Configuration
    ODOO_URL: str = "http://localhost:8069"
    ODOO_DB: str = "odoo"
    ODOO_USERNAME: str = "admin"
    ODOO_PASSWORD: str = "admin"
    
    # MidPoint Configuration (optional)
    MIDPOINT_URL: str = "http://localhost:8080/midpoint"
    MIDPOINT_USERNAME: str = "administrator"
    MIDPOINT_PASSWORD: str = "Test5ecr3t"
    
    # Keycloak Configuration (optional)
    KEYCLOAK_URL: str = "http://localhost:8180"
    KEYCLOAK_ADMIN: str = "admin"
    KEYCLOAK_PASSWORD: str = "admin"
    
    # SMTP Configuration (pour notifications)
    SMTP_HOST: Optional[str] = None  # Ex: "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USERNAME: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    SMTP_USE_TLS: bool = True
    SMTP_FROM_EMAIL: str = "noreply@aegis.local"
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "allow"  # Permettre des champs extra pour flexibilité


settings = Settings()


settings = Settings()
