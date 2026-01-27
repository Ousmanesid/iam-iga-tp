"""
Router pour le chatbot IA
Gère les interactions en langage naturel avec le système IAM
"""

from fastapi import APIRouter, HTTPException
import structlog

from ..services.llm import llm_service
from ..services.midpoint import midpoint_service

logger = structlog.get_logger()
router = APIRouter(prefix="/chat", tags=["Chatbot"])


@router.get("/status", summary="Statut du chatbot")
async def get_status():
    """
    Vérifier que le service chatbot est actif.
    """
    return {
        "service": "chatbot",
        "status": "active",
        "message": "Service chatbot IA actif"
    }


@router.post("/message", summary="Envoyer un message au chatbot")
async def send_message(message: dict):
    """
    Envoyer un message au chatbot et recevoir une réponse.
    """
    try:
        user_message = message.get("message", "")
        logger.info(f"Message reçu: {user_message}")
        
        # À implémenter : traitement via LLM
        return {
            "status": "success",
            "response": "Chatbot en cours d'implémentation",
            "message": user_message
        }
    except Exception as e:
        logger.error("Erreur lors du traitement du message", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
