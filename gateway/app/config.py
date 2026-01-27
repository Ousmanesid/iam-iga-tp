"""
Configuration de la Gateway IAM
Gestion centralisée des paramètres via variables d'environnement
"""

from pydantic_settings import BaseSettings
from typing import Optional
from functools import lru_cache


class Settings(BaseSettings):
    """Configuration de l'application Gateway"""
    
    # Application
    app_env: str = "development"
    app_debug: bool = True
    app_port: int = 8000
    app_title: str = "IAM Gateway"
    app_version: str = "1.0.0"
    
    # MidPoint
    midpoint_url: str = "http://midpoint:8080/midpoint"
    midpoint_user: str = "administrator"
    midpoint_password: str = "5ecr3t"
    
    # N8N
    n8n_url: str = "http://n8n:5678"
    n8n_user: str = "admin"
    n8n_password: str = "admin123"
    n8n_webhook_base: str = "http://n8n:5678/webhook"
    
    # Odoo
    odoo_url: str = "http://odoo:8069"
    odoo_db: str = "odoo"
    odoo_user: str = "admin"
    odoo_password: str = "admin"
    
    # LLM Configuration
    llm_provider: str = "cloud"  # "cloud" ou "local"
    llm_local_url: str = "http://host.docker.internal:11434"
    llm_local_model: str = "mistral:7b"
    
    # OpenAI (pour le mode cloud)
    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-4-turbo-preview"
    
    # Anthropic (alternative cloud)
    anthropic_api_key: Optional[str] = None
    anthropic_model: str = "claude-3-sonnet-20240229"
    
    # Webhooks N8N (endpoints pour déclencher les workflows)
    webhook_pre_provision: str = "/webhook/pre-provision"
    webhook_post_provision: str = "/webhook/post-provision"
    webhook_chatbot: str = "/webhook/chatbot"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Singleton pour les settings"""
    return Settings()


# Export des settings
settings = get_settings()








