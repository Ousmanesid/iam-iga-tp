""""""

Keycloak Connector - Phase 2 Core IAMKeycloak Connector - Connecteur vers Keycloak (IAM).



Connector pour Keycloak (SSO Identity Provider).🎯 Ce connecteur encapsule toutes les interactions avec Keycloak :

Utilise l'API REST de Keycloak Admin pour gérer les utilisateurs.   - Création d'utilisateurs

"""   - Gestion des groupes

import requests   - Attribution des rôles

from typing import Dict, Any, Optional

from app.connectors.base import BaseConnector⚠️ Phase 2 : Mode simulation (logs + mock)

   Phase 3+ : Vraies API Keycloak

"""

class KeycloakConnector(BaseConnector):

    """from typing import Dict, Any, List, Optional

    Connector pour Keycloak Identity Provider.from datetime import datetime

    import logging

    Gère la création, mise à jour, et suppression d'utilisateurs via l'API Admin.

    """logger = logging.getLogger(__name__)

    

    def __init__(self, config: Optional[Dict[str, Any]] = None):

        """class KeycloakConnector:

        Initialise le connector Keycloak.    """

            Connecteur pour Keycloak.

        Args:    

            config (Dict): Configuration avec:    Gère la création et la gestion des utilisateurs dans Keycloak.

                - server_url (str): URL du serveur Keycloak (ex: "http://keycloak:8080")    En Phase 2, les actions sont simulées (logs).

                - realm (str): Nom du realm (ex: "master")    """

                - admin_username (str): Username admin    

                - admin_password (str): Password admin    def __init__(

                - client_id (str): Client ID (défaut: "admin-cli")        self,

        """        url: Optional[str] = None,

        super().__init__(config)        realm: str = "aegis",

        self.server_url = config.get('server_url', 'http://localhost:8080')        client_id: Optional[str] = None,

        self.realm = config.get('realm', 'master')        client_secret: Optional[str] = None,

        self.admin_username = config.get('admin_username', 'admin')    ):

        self.admin_password = config.get('admin_password', 'admin')        """

        self.client_id = config.get('client_id', 'admin-cli')        Initialise le connecteur Keycloak.

        self._access_token = None        

                Args:

    def _get_access_token(self) -> Optional[str]:            url: URL du serveur Keycloak (ex: http://localhost:8080)

        """            realm: Nom du realm Keycloak

        Obtient un token d'accès admin via OAuth2 password grant.            client_id: ID du client pour l'authentification

                    client_secret: Secret du client

        Returns:        """

            Optional[str]: Access token ou None si échec        self.url = url

        """        self.realm = realm

        token_url = f"{self.server_url}/realms/{self.realm}/protocol/openid-connect/token"        self.client_id = client_id

                self.client_secret = client_secret

        payload = {        self._connected = False

            'grant_type': 'password',        self._simulation_mode = url is None

            'client_id': self.client_id,        

            'username': self.admin_username,        # Stockage simulé des utilisateurs (Phase 2)

            'password': self.admin_password        self._mock_users: Dict[str, Dict[str, Any]] = {}

        }        self._mock_groups: Dict[str, List[str]] = {}

                

        try:        if self._simulation_mode:

            response = requests.post(token_url, data=payload, timeout=10)            logger.info("KeycloakConnector initialized in SIMULATION mode")

            response.raise_for_status()        else:

            self._access_token = response.json()['access_token']            logger.info(f"KeycloakConnector initialized for {url}/{realm}")

            return self._access_token    

        except Exception as e:    def _log_action(self, action: str, details: Dict[str, Any]) -> None:

            print(f"❌ Failed to get Keycloak access token: {e}")        """Log une action pour traçabilité."""

            return None        logger.info(f"[KEYCLOAK] {action}: {details}")

                

    def _get_headers(self) -> Dict[str, str]:    def connect(self) -> bool:

        """Retourne les headers HTTP avec le token d'authentification."""        """

        if not self._access_token:        Établit la connexion à Keycloak.

            self._get_access_token()        

                    Returns:

        return {            True si connexion réussie

            'Authorization': f'Bearer {self._access_token}',        """

            'Content-Type': 'application/json'        if self._simulation_mode:

        }            self._log_action("CONNECT", {"mode": "simulation", "status": "ok"})

                    self._connected = True

    def create_user(self, user_data: Dict[str, str]) -> Dict[str, Any]:            return True

        """        

        Crée un utilisateur dans Keycloak.        # TODO Phase 3: Vraie connexion OAuth2

                try:

        Args:            # Simulation de connexion

            user_data (Dict): Données avec email, first_name, last_name            self._connected = True

                        self._log_action("CONNECT", {"url": self.url, "realm": self.realm, "status": "ok"})

        Returns:            return True

            Dict: Résultat avec success, message, details        except Exception as e:

        """            logger.error(f"Keycloak connection failed: {e}")

        users_url = f"{self.server_url}/admin/realms/{self.realm}/users"            return False

            

        # Payload Keycloak    def create_user(self, user_data: Dict[str, Any]) -> Dict[str, Any]:

        payload = {        """

            'username': user_data['email'].split('@')[0],        Crée un utilisateur dans Keycloak.

            'email': user_data['email'],        

            'firstName': user_data.get('first_name', ''),        Args:

            'lastName': user_data.get('last_name', ''),            user_data: Données de l'utilisateur contenant:

            'enabled': True,                - email (requis)

            'emailVerified': True,                - first_name (requis)

            'credentials': [{                - last_name (requis)

                'type': 'password',                - groups (optionnel)

                'value': user_data.get('password', 'ChangeMe123!'),  # Mot de passe temporaire                - access_level (optionnel)

                'temporary': True                

            }]        Returns:

        }            Résultat de l'opération avec success et message

                """

        try:        email = user_data.get("email")

            response = requests.post(        first_name = user_data.get("first_name", "")

                users_url,        last_name = user_data.get("last_name", "")

                json=payload,        groups = user_data.get("groups", [])

                headers=self._get_headers(),        

                timeout=10        if not email:

            )            return {

                            "success": False,

            if response.status_code == 201:                "message": "Email is required",

                # Succès - récupérer l'ID utilisateur depuis Location header            }

                location = response.headers.get('Location', '')        

                user_id = location.split('/')[-1] if location else 'unknown'        # Vérifier si l'utilisateur existe déjà

                        if email in self._mock_users:

                return {            return {

                    "success": True,                "success": False,

                    "message": f"User created in Keycloak realm '{self.realm}'",                "message": f"User {email} already exists in Keycloak",

                    "details": {            }

                        "user_id": user_id,        

                        "username": payload['username'],        # Créer l'utilisateur (simulation)

                        "realm": self.realm        keycloak_user = {

                    }            "id": f"kc-{len(self._mock_users) + 1:04d}",

                }            "username": email.split("@")[0],

            elif response.status_code == 409:            "email": email,

                return {            "firstName": first_name,

                    "success": False,            "lastName": last_name,

                    "message": f"User {user_data['email']} already exists in Keycloak",            "enabled": True,

                    "details": {"error_code": 409}            "emailVerified": False,

                }            "createdTimestamp": datetime.now().isoformat(),

            else:            "attributes": {

                return {                "job_title": user_data.get("job_title", ""),

                    "success": False,                "department": user_data.get("department", ""),

                    "message": f"Keycloak API error: {response.status_code}",                "access_level": user_data.get("access_level", "read"),

                    "details": {"error": response.text}            }

                }        }

                        

        except requests.exceptions.Timeout:        self._mock_users[email] = keycloak_user

            return {        

                "success": False,        # Ajouter aux groupes si spécifiés

                "message": "Keycloak connection timeout after 10s",        for group in groups:

                "details": {"error": "timeout"}            if group not in self._mock_groups:

            }                self._mock_groups[group] = []

        except Exception as e:            self._mock_groups[group].append(email)

            return {        

                "success": False,        self._log_action("CREATE_USER", {

                "message": f"Keycloak connector error: {str(e)}",            "email": email,

                "details": {"error": str(e)}            "name": f"{first_name} {last_name}",

            }            "groups": groups,

                        "keycloak_id": keycloak_user["id"],

    def get_user(self, user_email: str) -> Dict[str, Any]:        })

        """        

        Récupère un utilisateur par email dans Keycloak.        return {

                    "success": True,

        Args:            "message": f"User {email} created in Keycloak",

            user_email (str): Email de l'utilisateur            "keycloak_id": keycloak_user["id"],

                        "username": keycloak_user["username"],

        Returns:        }

            Dict: Résultat avec user_data si trouvé    

        """    def update_user(self, email: str, user_data: Dict[str, Any]) -> Dict[str, Any]:

        users_url = f"{self.server_url}/admin/realms/{self.realm}/users"        """

        params = {'email': user_email, 'exact': 'true'}        Met à jour un utilisateur dans Keycloak.

                

        try:        Args:

            response = requests.get(            email: Email de l'utilisateur à mettre à jour

                users_url,            user_data: Nouvelles données

                params=params,            

                headers=self._get_headers(),        Returns:

                timeout=10            Résultat de l'opération

            )        """

            response.raise_for_status()        if email not in self._mock_users:

                        return {

            users = response.json()                "success": False,

            if users:                "message": f"User {email} not found in Keycloak",

                user = users[0]            }

                return {        

                    "success": True,        # Mettre à jour les champs

                    "message": "User found in Keycloak",        user = self._mock_users[email]

                    "user_data": {        if "first_name" in user_data:

                        "id": user.get('id'),            user["firstName"] = user_data["first_name"]

                        "username": user.get('username'),        if "last_name" in user_data:

                        "email": user.get('email'),            user["lastName"] = user_data["last_name"]

                        "firstName": user.get('firstName'),        if "enabled" in user_data:

                        "lastName": user.get('lastName'),            user["enabled"] = user_data["enabled"]

                        "enabled": user.get('enabled')        

                    }        self._log_action("UPDATE_USER", {"email": email, "updated_fields": list(user_data.keys())})

                }        

            else:        return {

                return {            "success": True,

                    "success": False,            "message": f"User {email} updated in Keycloak",

                    "message": f"User {user_email} not found in Keycloak",        }

                    "user_data": None    

                }    def delete_user(self, email: str) -> Dict[str, Any]:

                        """

        except Exception as e:        Supprime un utilisateur de Keycloak.

            return {        

                "success": False,        Args:

                "message": f"Error retrieving user: {str(e)}",            email: Email de l'utilisateur à supprimer

                "user_data": None            

            }        Returns:

                        Résultat de l'opération

    def update_user(self, user_email: str, user_data: Dict[str, str]) -> Dict[str, Any]:        """

        """        if email not in self._mock_users:

        Met à jour un utilisateur dans Keycloak.            return {

                        "success": False,

        Args:                "message": f"User {email} not found in Keycloak",

            user_email (str): Email de l'utilisateur            }

            user_data (Dict): Nouvelles données        

                    del self._mock_users[email]

        Returns:        

            Dict: Résultat de la mise à jour        # Retirer des groupes

        """        for group_members in self._mock_groups.values():

        # 1. Récupérer l'ID utilisateur            if email in group_members:

        user_info = self.get_user(user_email)                group_members.remove(email)

        if not user_info['success']:        

            return user_info        self._log_action("DELETE_USER", {"email": email})

                    

        user_id = user_info['user_data']['id']        return {

        user_url = f"{self.server_url}/admin/realms/{self.realm}/users/{user_id}"            "success": True,

                    "message": f"User {email} deleted from Keycloak",

        # 2. Construire le payload de mise à jour        }

        payload = {}    

        if 'first_name' in user_data:    def get_user(self, email: str) -> Optional[Dict[str, Any]]:

            payload['firstName'] = user_data['first_name']        """

        if 'last_name' in user_data:        Récupère un utilisateur par email.

            payload['lastName'] = user_data['last_name']        

        if 'enabled' in user_data:        Args:

            payload['enabled'] = user_data['enabled']            email: Email de l'utilisateur

                        

        try:        Returns:

            response = requests.put(            Données de l'utilisateur ou None

                user_url,        """

                json=payload,        return self._mock_users.get(email)

                headers=self._get_headers(),    

                timeout=10    def add_to_group(self, email: str, group: str) -> Dict[str, Any]:

            )        """

                    Ajoute un utilisateur à un groupe.

            if response.status_code == 204:        

                return {        Args:

                    "success": True,            email: Email de l'utilisateur

                    "message": "User updated in Keycloak",            group: Nom du groupe

                    "details": {"user_id": user_id}            

                }        Returns:

            else:            Résultat de l'opération

                return {        """

                    "success": False,        if email not in self._mock_users:

                    "message": f"Keycloak update failed: {response.status_code}",            return {

                    "details": {"error": response.text}                "success": False,

                }                "message": f"User {email} not found in Keycloak",

                            }

        except Exception as e:        

            return {        if group not in self._mock_groups:

                "success": False,            self._mock_groups[group] = []

                "message": f"Error updating user: {str(e)}",        

                "details": {}        if email not in self._mock_groups[group]:

            }            self._mock_groups[group].append(email)

                        self._log_action("ADD_TO_GROUP", {"email": email, "group": group})

    def delete_user(self, user_email: str) -> Dict[str, Any]:            

        """            return {

        Supprime un utilisateur de Keycloak.                "success": True,

                        "message": f"User {email} added to group {group}",

        Args:            }

            user_email (str): Email de l'utilisateur        else:

                        return {

        Returns:                "success": True,

            Dict: Résultat de la suppression                "message": f"User {email} already in group {group}",

        """            }

        # 1. Récupérer l'ID utilisateur    

        user_info = self.get_user(user_email)    def remove_from_group(self, email: str, group: str) -> Dict[str, Any]:

        if not user_info['success']:        """

            return {        Retire un utilisateur d'un groupe.

                "success": True,  # Idempotent - déjà supprimé        

                "message": f"User {user_email} not found (already deleted)",        Args:

                "details": {}            email: Email de l'utilisateur

            }            group: Nom du groupe

                        

        user_id = user_info['user_data']['id']        Returns:

        user_url = f"{self.server_url}/admin/realms/{self.realm}/users/{user_id}"            Résultat de l'opération

                """

        try:        if group not in self._mock_groups:

            response = requests.delete(            return {

                user_url,                "success": False,

                headers=self._get_headers(),                "message": f"Group {group} not found",

                timeout=10            }

            )        

                    if email in self._mock_groups[group]:

            if response.status_code == 204:            self._mock_groups[group].remove(email)

                return {            self._log_action("REMOVE_FROM_GROUP", {"email": email, "group": group})

                    "success": True,            

                    "message": "User deleted from Keycloak",            return {

                    "details": {"user_id": user_id}                "success": True,

                }                "message": f"User {email} removed from group {group}",

            else:            }

                return {        else:

                    "success": False,            return {

                    "message": f"Keycloak delete failed: {response.status_code}",                "success": False,

                    "details": {"error": response.text}                "message": f"User {email} not in group {group}",

                }            }

                    

        except Exception as e:    def list_users(self) -> List[Dict[str, Any]]:

            return {        """Retourne la liste de tous les utilisateurs."""

                "success": False,        return list(self._mock_users.values())

                "message": f"Error deleting user: {str(e)}",    

                "details": {}    def list_groups(self) -> Dict[str, List[str]]:

            }        """Retourne tous les groupes et leurs membres."""

                    return self._mock_groups.copy()

    def test_connection(self) -> Dict[str, Any]:    

        """    def get_stats(self) -> Dict[str, Any]:

        Teste la connexion au serveur Keycloak.        """Retourne les statistiques du connecteur."""

                return {

        Returns:            "mode": "simulation" if self._simulation_mode else "production",

            Dict: Résultat du test            "connected": self._connected,

        """            "realm": self.realm,

        try:            "total_users": len(self._mock_users),

            token = self._get_access_token()            "total_groups": len(self._mock_groups),

            if token:        }

                return {
                    "success": True,
                    "message": f"Connected to Keycloak realm '{self.realm}'",
                    "details": {
                        "server_url": self.server_url,
                        "realm": self.realm
                    }
                }
            else:
                return {
                    "success": False,
                    "message": "Failed to authenticate with Keycloak",
                    "details": {}
                }
        except Exception as e:
            return {
                "success": False,
                "message": f"Connection test failed: {str(e)}",
                "details": {}
            }
