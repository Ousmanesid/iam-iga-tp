"""
Service pour interagir avec les LLM (mode cloud ou local)
Abstraction permettant de basculer entre OpenAI/Anthropic (cloud) et Ollama (local)
"""

import httpx
from typing import Optional, Dict, Any, List
from abc import ABC, abstractmethod
import structlog
import json

from ..config import settings

logger = structlog.get_logger()


# === Prompt système pour l'extraction de commandes IAM ===

IAM_SYSTEM_PROMPT = """Tu es un assistant IAM (Identity and Access Management) intelligent.
Tu aides les utilisateurs à gérer les identités et les accès dans un système d'entreprise.

Tu dois analyser les demandes en langage naturel et extraire les actions IAM à effectuer.

Les actions possibles sont:
- search_user: Rechercher un utilisateur
- assign_role: Assigner un rôle à un utilisateur
- remove_role: Retirer un rôle à un utilisateur
- assign_permission: Assigner une permission directe
- remove_permission: Retirer une permission directe
- list_roles: Lister les rôles disponibles
- list_permissions: Lister les permissions d'un utilisateur
- get_user_info: Obtenir les informations d'un utilisateur

Les rôles disponibles dans Home App sont:
- USER: Utilisateur standard
- AGENT_COMMERCIAL: Agent commercial avec accès CRM
- COMMERCIAL_MANAGER: Responsable commercial
- RH_ASSISTANT: Assistant RH
- RH_MANAGER: Responsable RH
- COMPTABLE: Comptable
- FINANCE_MANAGER: Responsable Finance
- IT_SUPPORT: Support IT
- IT_ADMIN: Administrateur IT
- MANAGER: Manager
- DIRECTOR: Directeur

Pour chaque demande, tu dois:
1. Identifier l'action à effectuer
2. Identifier la cible (utilisateur spécifique, groupe, département)
3. Identifier le rôle ou la permission concernée si applicable
4. Déterminer si une approbation est nécessaire

Tu dois répondre en JSON avec le format suivant:
{
    "action": "nom_action",
    "target_type": "user|group|department",
    "target_identifier": "login ou nom ou null",
    "target_filters": {"department": "...", "job_title": "..."} ou null,
    "role_or_permission": "code du rôle/permission ou null",
    "requires_approval": true|false,
    "confidence": 0.0-1.0,
    "explanation": "Explication de ce que tu vas faire"
}

Si tu ne comprends pas la demande ou si elle est ambiguë, demande des précisions.
"""


class BaseLLMProvider(ABC):
    """Classe abstraite pour les providers LLM"""
    
    @abstractmethod
    async def chat(
        self,
        message: str,
        system_prompt: str = IAM_SYSTEM_PROMPT,
        conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> str:
        """Envoyer un message au LLM et obtenir une réponse"""
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """Vérifier si le provider est disponible"""
        pass


class OpenAIProvider(BaseLLMProvider):
    """Provider OpenAI (GPT-4, GPT-3.5, etc.)"""
    
    def __init__(self):
        self.api_key = settings.openai_api_key
        self.model = settings.openai_model
        self.api_url = "https://api.openai.com/v1/chat/completions"
    
    async def chat(
        self,
        message: str,
        system_prompt: str = IAM_SYSTEM_PROMPT,
        conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> str:
        if not self.api_key:
            raise ValueError("OpenAI API key not configured")
        
        messages = [{"role": "system", "content": system_prompt}]
        
        if conversation_history:
            messages.extend(conversation_history)
        
        messages.append({"role": "user", "content": message})
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                self.api_url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": self.model,
                    "messages": messages,
                    "temperature": 0.3,
                    "response_format": {"type": "json_object"}
                }
            )
            response.raise_for_status()
            
            result = response.json()
            return result["choices"][0]["message"]["content"]
    
    async def health_check(self) -> bool:
        if not self.api_key:
            return False
        try:
            async with httpx.AsyncClient(timeout=10.0, verify=True, follow_redirects=True) as client:
                response = await client.get(
                    "https://api.openai.com/v1/models",
                    headers={"Authorization": f"Bearer {self.api_key}"}
                )
                return response.status_code == 200
        except (httpx.HTTPError, Exception) as e:
            # Ignorer silencieusement les erreurs SSL/HTTP si pas de clé API
            return False


class AnthropicProvider(BaseLLMProvider):
    """Provider Anthropic (Claude)"""
    
    def __init__(self):
        self.api_key = settings.anthropic_api_key
        self.model = settings.anthropic_model
        self.api_url = "https://api.anthropic.com/v1/messages"
    
    async def chat(
        self,
        message: str,
        system_prompt: str = IAM_SYSTEM_PROMPT,
        conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> str:
        if not self.api_key:
            raise ValueError("Anthropic API key not configured")
        
        messages = []
        
        if conversation_history:
            messages.extend(conversation_history)
        
        messages.append({"role": "user", "content": message})
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                self.api_url,
                headers={
                    "x-api-key": self.api_key,
                    "anthropic-version": "2023-06-01",
                    "Content-Type": "application/json"
                },
                json={
                    "model": self.model,
                    "max_tokens": 1024,
                    "system": system_prompt,
                    "messages": messages
                }
            )
            response.raise_for_status()
            
            result = response.json()
            return result["content"][0]["text"]
    
    async def health_check(self) -> bool:
        # Anthropic n'a pas d'endpoint de health check simple
        return bool(self.api_key)


class OllamaProvider(BaseLLMProvider):
    """Provider Ollama (LLM local)"""
    
    def __init__(self):
        self.base_url = settings.llm_local_url
        self.model = settings.llm_local_model
    
    async def chat(
        self,
        message: str,
        system_prompt: str = IAM_SYSTEM_PROMPT,
        conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> str:
        messages = [{"role": "system", "content": system_prompt}]
        
        if conversation_history:
            messages.extend(conversation_history)
        
        messages.append({"role": "user", "content": message})
        
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self.base_url}/api/chat",
                json={
                    "model": self.model,
                    "messages": messages,
                    "stream": False,
                    "format": "json",
                    "options": {
                        "temperature": 0.3
                    }
                }
            )
            response.raise_for_status()
            
            result = response.json()
            return result["message"]["content"]
    
    async def health_check(self) -> bool:
        try:
            # Ollama utilise HTTP, pas HTTPS
            url = self.base_url
            if url.startswith("https://"):
                url = url.replace("https://", "http://", 1)
            
            async with httpx.AsyncClient(timeout=5.0, verify=False, follow_redirects=True) as client:
                response = await client.get(f"{url}/api/tags")
                return response.status_code == 200
        except (httpx.HTTPError, Exception):
            return False


class LLMService:
    """
    Service principal pour le LLM avec abstraction du provider
    Supporte le basculement entre mode cloud et local via configuration
    """
    
    def __init__(self):
        self._cloud_provider: Optional[BaseLLMProvider] = None
        self._local_provider: Optional[BaseLLMProvider] = None
        self._initialize_providers()
    
    def _initialize_providers(self):
        """Initialiser les providers configurés"""
        # Provider cloud (OpenAI ou Anthropic)
        if settings.openai_api_key:
            self._cloud_provider = OpenAIProvider()
            logger.info("OpenAI provider initialized")
        elif settings.anthropic_api_key:
            self._cloud_provider = AnthropicProvider()
            logger.info("Anthropic provider initialized")
        
        # Provider local (Ollama) - toujours disponible si configuré
        self._local_provider = OllamaProvider()
        logger.info("Ollama provider initialized (may not be running)")
    
    @property
    def current_provider(self) -> str:
        """Obtenir le provider actuel"""
        return settings.llm_provider
    
    def _get_provider(self) -> BaseLLMProvider:
        """Obtenir le provider actif selon la configuration"""
        if settings.llm_provider == "local":
            if self._local_provider:
                return self._local_provider
            raise ValueError("Local LLM provider not available")
        else:  # cloud
            if self._cloud_provider:
                return self._cloud_provider
            raise ValueError("Cloud LLM provider not configured (missing API key)")
    
    async def chat(
        self,
        message: str,
        system_prompt: str = IAM_SYSTEM_PROMPT,
        conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> str:
        """
        Envoyer un message au LLM et obtenir une réponse
        Utilise le provider configuré (cloud ou local)
        """
        provider = self._get_provider()
        
        logger.info(
            "Sending message to LLM",
            provider=settings.llm_provider,
            message_length=len(message)
        )
        
        try:
            response = await provider.chat(message, system_prompt, conversation_history)
            logger.info("LLM response received", response_length=len(response))
            return response
        except Exception as e:
            logger.error("LLM chat failed", error=str(e))
            raise
    
    async def parse_iam_command(
        self,
        user_message: str,
        conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> Dict[str, Any]:
        """
        Parser un message utilisateur pour extraire une commande IAM
        Retourne un dictionnaire avec l'action et les paramètres
        """
        response = await self.chat(
            user_message,
            IAM_SYSTEM_PROMPT,
            conversation_history
        )
        
        try:
            # Parser la réponse JSON
            parsed = json.loads(response)
            logger.info("IAM command parsed", action=parsed.get("action"))
            return parsed
        except json.JSONDecodeError:
            logger.warning("Failed to parse LLM response as JSON", response=response)
            # Retourner une réponse d'erreur structurée
            return {
                "action": "clarify",
                "explanation": response,
                "confidence": 0.0
            }
    
    async def generate_response(
        self,
        context: str,
        result: Dict[str, Any]
    ) -> str:
        """
        Générer une réponse en langage naturel basée sur le résultat d'une action
        """
        prompt = f"""Génère une réponse courte et claire en français pour l'utilisateur.

Contexte de la demande: {context}

Résultat de l'action: {json.dumps(result, ensure_ascii=False)}

Réponds de manière naturelle et professionnelle. Si l'action a réussi, confirme-le.
Si elle a échoué ou nécessite une approbation, explique pourquoi.

Réponse:"""
        
        response = await self.chat(
            prompt,
            system_prompt="Tu es un assistant IAM. Réponds de manière concise en français.",
            conversation_history=None
        )
        
        # Nettoyer la réponse si elle est en JSON
        try:
            parsed = json.loads(response)
            if "response" in parsed:
                return parsed["response"]
            if "explanation" in parsed:
                return parsed["explanation"]
        except json.JSONDecodeError:
            pass
        
        return response
    
    async def health_check(self) -> Dict[str, Any]:
        """Vérifier l'état des providers LLM"""
        status = {
            "current_provider": settings.llm_provider,
            "cloud_available": False,
            "local_available": False
        }
        
        if self._cloud_provider:
            status["cloud_available"] = await self._cloud_provider.health_check()
        
        if self._local_provider:
            status["local_available"] = await self._local_provider.health_check()
        
        return status


# Instance singleton
llm_service = LLMService()


