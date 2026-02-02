"""
Base Connector - Phase 2 Core IAM

Interface abstraite pour tous les connectors d'applications.
Chaque connector implémente les opérations CRUD pour son application cible.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional


class BaseConnector(ABC):
    """
    Classe abstraite pour les connectors d'applications.
    
    Tous les connectors (Keycloak, GitLab, Odoo, etc.) doivent hériter de cette classe
    et implémenter les méthodes abstraites.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialise le connector avec sa configuration.
        
        Args:
            config (Dict): Configuration spécifique (URL, credentials, etc.)
        """
        self.config = config or {}
        self.app_name = self.__class__.__name__.replace("Connector", "")
        
    @abstractmethod
    def create_user(self, user_data: Dict[str, str]) -> Dict[str, Any]:
        """
        Crée un utilisateur dans l'application cible.
        
        Args:
            user_data (Dict): Données utilisateur (email, first_name, last_name, etc.)
            
        Returns:
            Dict: Résultat avec au minimum:
                - success (bool): True si succès
                - message (str): Message descriptif
                - details (Dict): Détails supplémentaires (user_id, etc.)
                
        Example:
            >>> connector.create_user({
            ...     "email": "alice@company.com",
            ...     "first_name": "Alice",
            ...     "last_name": "Doe"
            ... })
            {
                "success": True,
                "message": "User created successfully",
                "details": {"user_id": "123", "username": "alice.doe"}
            }
        """
        pass
        
    @abstractmethod
    def update_user(self, user_email: str, user_data: Dict[str, str]) -> Dict[str, Any]:
        """
        Met à jour un utilisateur existant.
        
        Args:
            user_email (str): Email de l'utilisateur
            user_data (Dict): Nouvelles données à mettre à jour
            
        Returns:
            Dict: Résultat avec success, message, details
        """
        pass
        
    @abstractmethod
    def delete_user(self, user_email: str) -> Dict[str, Any]:
        """
        Supprime un utilisateur de l'application.
        
        Args:
            user_email (str): Email de l'utilisateur à supprimer
            
        Returns:
            Dict: Résultat avec success, message, details
        """
        pass
        
    @abstractmethod
    def get_user(self, user_email: str) -> Dict[str, Any]:
        """
        Récupère les informations d'un utilisateur.
        
        Args:
            user_email (str): Email de l'utilisateur
            
        Returns:
            Dict: Résultat avec success, message, et user_data si trouvé
        """
        pass
        
    def test_connection(self) -> Dict[str, Any]:
        """
        Teste la connexion à l'application cible.
        
        Returns:
            Dict: Résultat avec success et message
        """
        return {
            "success": False,
            "message": "test_connection() not implemented for this connector"
        }
        
    def health_check(self) -> Dict[str, Any]:
        """
        Vérifie la santé du connector.
        
        Returns:
            Dict: Statut de santé avec success, message, et métriques
        """
        return {
            "success": True,
            "message": f"{self.app_name} connector is operational",
            "details": {
                "app_name": self.app_name,
                "config_loaded": bool(self.config)
            }
        }


class MockConnector(BaseConnector):
    """
    Connector de test qui simule les opérations sans vraie connexion.
    Utile pour les tests et le développement.
    """
    
    def __init__(self, app_name: str, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.app_name = app_name
        self.users_db = {}  # Base de données en mémoire
        
    def create_user(self, user_data: Dict[str, str]) -> Dict[str, Any]:
        """Simule la création d'utilisateur."""
        email = user_data.get('email')
        
        if email in self.users_db:
            return {
                "success": False,
                "message": f"User {email} already exists in {self.app_name}",
                "details": {}
            }
            
        self.users_db[email] = user_data
        return {
            "success": True,
            "message": f"[MOCK] User created in {self.app_name}",
            "details": {
                "user_id": f"mock-{len(self.users_db)}",
                "username": email.split('@')[0]
            }
        }
        
    def update_user(self, user_email: str, user_data: Dict[str, str]) -> Dict[str, Any]:
        """Simule la mise à jour d'utilisateur."""
        if user_email not in self.users_db:
            return {
                "success": False,
                "message": f"User {user_email} not found in {self.app_name}",
                "details": {}
            }
            
        self.users_db[user_email].update(user_data)
        return {
            "success": True,
            "message": f"[MOCK] User updated in {self.app_name}",
            "details": {}
        }
        
    def delete_user(self, user_email: str) -> Dict[str, Any]:
        """Simule la suppression d'utilisateur."""
        if user_email in self.users_db:
            del self.users_db[user_email]
            return {
                "success": True,
                "message": f"[MOCK] User deleted from {self.app_name}",
                "details": {}
            }
        return {
            "success": False,
            "message": f"User {user_email} not found in {self.app_name}",
            "details": {}
        }
        
    def get_user(self, user_email: str) -> Dict[str, Any]:
        """Simule la récupération d'utilisateur."""
        if user_email in self.users_db:
            return {
                "success": True,
                "message": "User found",
                "user_data": self.users_db[user_email]
            }
        return {
            "success": False,
            "message": f"User {user_email} not found in {self.app_name}",
            "user_data": None
        }
        
    def test_connection(self) -> Dict[str, Any]:
        """Simule le test de connexion."""
        return {
            "success": True,
            "message": f"[MOCK] Connection to {self.app_name} successful"
        }
