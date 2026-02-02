"""
Service MidPoint - Gestion des utilisateurs via API REST
"""
import httpx
from typing import List, Dict, Optional, Any
import logging
import xml.etree.ElementTree as ET

logger = logging.getLogger(__name__)


class MidPointService:
    """Service pour interagir avec l'API REST MidPoint"""
    
    def __init__(
        self,
        url: str = "http://midpoint:8080/midpoint",
        username: str = "administrator",
        password: str = "5ecr3t"
    ):
        self.url = url
        self.username = username
        self.password = password
        self.auth = (username, password)
    
    def _get_client(self) -> httpx.Client:
        """Crée un client HTTP configuré"""
        return httpx.Client(
            base_url=self.url,
            auth=self.auth,
            headers={"Content-Type": "application/xml"},
            timeout=30.0
        )
    
    def test_connection(self) -> bool:
        """Teste la connexion à MidPoint"""
        try:
            with self._get_client() as client:
                response = client.get("/ws/rest/self")
                return response.status_code == 200
        except Exception as e:
            logger.error(f"Erreur connexion MidPoint: {e}")
            return False
    
    def get_user_by_personal_number(self, personal_number: str) -> Optional[Dict]:
        """Recherche un utilisateur par personalNumber"""
        query = f"""<?xml version="1.0" encoding="UTF-8"?>
        <q:query xmlns:q="http://prism.evolveum.com/xml/ns/public/query-3">
            <q:filter>
                <q:equal>
                    <q:path>personalNumber</q:path>
                    <q:value>{personal_number}</q:value>
                </q:equal>
            </q:filter>
        </q:query>"""
        
        try:
            with self._get_client() as client:
                response = client.post(
                    "/ws/rest/users/search",
                    content=query
                )
                if response.status_code == 200 and "<user" in response.text:
                    return {"exists": True, "data": response.text}
                return None
        except Exception as e:
            logger.error(f"Erreur recherche utilisateur: {e}")
            return None
    
    def create_user(self, user_data: Dict) -> bool:
        """Crée un utilisateur dans MidPoint"""
        user_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
        <user xmlns="http://midpoint.evolveum.com/xml/ns/public/common/common-3">
            <name>{user_data.get('email', '').split('@')[0]}</name>
            <givenName>{user_data.get('givenName', '')}</givenName>
            <familyName>{user_data.get('familyName', '')}</familyName>
            <emailAddress>{user_data.get('email', '')}</emailAddress>
            <personalNumber>{user_data.get('personalNumber', '')}</personalNumber>
            <title>{user_data.get('title', '')}</title>
            <organization>{user_data.get('department', '')}</organization>
            <activation>
                <administrativeStatus>{'enabled' if user_data.get('status') == 'Active' else 'disabled'}</administrativeStatus>
            </activation>
        </user>"""
        
        try:
            with self._get_client() as client:
                response = client.post("/ws/rest/users", content=user_xml)
                if response.status_code in [200, 201, 202]:
                    logger.info(f"Utilisateur créé: {user_data.get('email')}")
                    return True
                else:
                    logger.error(f"Erreur création: {response.status_code} - {response.text}")
                    return False
        except Exception as e:
            logger.error(f"Erreur création utilisateur: {e}")
            return False
    
    def update_user(self, oid: str, user_data: Dict) -> bool:
        """Met à jour un utilisateur existant"""
        # ... implémentation existante ou TODO ...
        return True

    def _find_role_oid_by_name(self, role_name: str) -> Optional[str]:
        """Cherche l'OID d'un rôle par son nom"""
        query = f"""<q:query xmlns:q="http://prism.evolveum.com/xml/ns/public/query-3">
            <q:filter>
                <q:equal>
                    <q:path>name</q:path>
                    <q:value>{role_name}</q:value>
                </q:equal>
            </q:filter>
        </q:query>"""
        
        try:
            with self._get_client() as client:
                response = client.post("/ws/rest/roles/search", content=query)
                if response.status_code == 200:
                    root = ET.fromstring(response.text)
                    # Namespace map
                    ns = {'c': 'http://midpoint.evolveum.com/xml/ns/public/common/common-3'}
                    role = root.find(".//c:role", ns)
                    if role is not None:
                        return role.get('oid')
        except Exception as e:
            logger.error(f"Erreur recherche rôle {role_name}: {e}")
        return None

    def provision_user_with_assignments(self, user_data: Dict, assignments: List[str]) -> Dict[str, Any]:
        """
        Orchestration complète : Crée/Update User + Assigne les rôles.
        Remplace les appels directs aux APIs finales.
        
        Args:
            user_data: Données utilisateur (email, nom, etc.)
            assignments: Liste des noms de rôles/apps (ex: 'Mattermost', 'Role-Developer')
        """
        results = {
            "success": True, 
            "actions": [], 
            "midpoint_oid": None
        }
        
        # 1. Gestion de l'identité (User)
        existing_user = self.get_user_by_personal_number(user_data.get('personalNumber', ''))
        user_oid = None
        
        if existing_user:
            # Récupérer l'OID depuis le XML (parsing rapide)
            try:
                root = ET.fromstring(existing_user['data'])
                # L'objet retourné par search est une liste d'objets, ou l'objet lui-même selon setup
                # Souvent <object><user oid="...">...</object>
                user_node = root.find(".//{http://midpoint.evolveum.com/xml/ns/public/common/common-3}user")
                if user_node is not None:
                    user_oid = user_node.get('oid')
            except:
                pass
            results['actions'].append("User check: Found")
        else:
            # Créer l'utilisateur
            # Note: create_user actuel retourne bool, on va l'utiliser tel quel, 
            # mais idéalement il faudrait l'OID. On refait une recherche après.
            if self.create_user(user_data):
                results['actions'].append("User creation: Success")
                # Récupérer l'OID nouvellement créé
                new_user = self.get_user_by_personal_number(user_data.get('personalNumber', ''))
                if new_user:
                     root = ET.fromstring(new_user['data'])
                     user_node = root.find(".//{http://midpoint.evolveum.com/xml/ns/public/common/common-3}user")
                     if user_node is not None:
                        user_oid = user_node.get('oid')
            else:
                results['success'] = False
                results['actions'].append("User creation: Failed")
                return results

        results['midpoint_oid'] = user_oid

        if not user_oid:
            results['success'] = False
            results['actions'].append("Error: Could not retrieve User OID")
            return results

        # 2. Assignation des rôles
        modifications_xml = """<objectModification xmlns="http://prism.evolveum.com/xml/ns/public/types-3" 
                                   xmlns:c="http://midpoint.evolveum.com/xml/ns/public/common/common-3">"""
        
        has_assignments = False
        for app_name in assignments:
            # Mapping Simple: On suppose que le Role MidPoint s'appelle comme l'App ou a un préfixe
            # Pour ce projet, on va standardiser sur le nom de l'app si pas de prefix trouvé
            # ou essayer de trouver "Role-{app_name}"
            
            # Stratégie de recherche de rôle
            role_candidates = [f"Role - {app_name}", f"App - {app_name}", app_name]
            role_oid = None
            
            for candidate in role_candidates:
                role_oid = self._find_role_oid_by_name(candidate)
                if role_oid:
                    break
            
            if role_oid:
                modifications_xml += f"""
                <itemDelta>
                    <t:modificationType>add</t:modificationType>
                    <t:path>assignment</t:path>
                    <t:value>
                        <c:assignment>
                            <c:targetRef oid="{role_oid}" type="c:RoleType"/>
                        </c:assignment>
                    </t:value>
                </itemDelta>"""
                has_assignments = True
                results['actions'].append(f"Prepared assignment: {app_name} (OID: {role_oid})")
            else:
                # Log mais ne pas bloquer tout
                logger.warning(f"Rôle pour '{app_name}' introuvable dans MidPoint. Candidats testés: {role_candidates}")
                results['actions'].append(f"Warning: Role not found for {app_name}")

        modifications_xml += "</objectModification>"

        # 3. Envoyer la modification
        if has_assignments:
            try:
                with self._get_client() as client:
                    resp = client.post(f"/ws/rest/users/{user_oid}", content=modifications_xml)
                    if resp.status_code in [200, 204]:
                         results['actions'].append("Assignments execution: Success")
                    else:
                         results['success'] = False
                         logger.error(f"MidPoint Error: {resp.text}")
                         results['actions'].append(f"Assignments execution: Failed ({resp.status_code})")
            except Exception as e:
                results['success'] = False
                results['actions'].append(f"Assignments exception: {str(e)}")
        
        return results
        # TODO: Implémenter la mise à jour via PATCH
        return True
    
    def trigger_recompute(self, user_oid: str) -> bool:
        """Déclenche le recompute d'un utilisateur pour appliquer les rôles"""
        try:
            with self._get_client() as client:
                response = client.post(f"/ws/rest/users/{user_oid}/recompute")
                return response.status_code in [200, 202, 204]
        except Exception as e:
            logger.error(f"Erreur recompute: {e}")
            return False
    
    def trigger_hr_import_task(self) -> bool:
        """Déclenche la tâche d'import HR CSV"""
        task_oid = "10000000-0000-0000-5555-000000000001"
        try:
            with self._get_client() as client:
                response = client.post(f"/ws/rest/tasks/{task_oid}/run")
                if response.status_code in [200, 202]:
                    logger.info("Tâche HR Import déclenchée")
                    return True
                return False
        except Exception as e:
            logger.error(f"Erreur déclenchement tâche: {e}")
            return False
    
    def get_all_users(self) -> List[Dict]:
        """Récupère tous les utilisateurs depuis MidPoint (via PostgreSQL en fallback)"""
        try:
            # Essayer l'API REST d'abord
            with self._get_client() as client:
                response = client.get("/ws/rest/users")
                if response.status_code == 200:
                    return self._parse_users_xml(response.text)
        except Exception as e:
            logger.warning(f"API REST MidPoint inaccessible: {e}, fallback vers PostgreSQL")
        
        # Fallback: Charger directement depuis PostgreSQL
        return self._get_users_from_db()
    
    def _get_users_from_db(self) -> List[Dict]:
        """Charge les utilisateurs directement depuis la base PostgreSQL de MidPoint"""
        import subprocess
        import json
        
        try:
            # Récupérer les users depuis PostgreSQL via docker exec
            cmd = [
                'docker', 'exec', 'docker_midpoint_data_1',
                'psql', '-U', 'midpoint', '-t', '-A', '-F', '|',
                '-c', """
                    SELECT 
                        oid, 
                        nameorig, 
                        COALESCE(emailaddress, ''),
                        COALESCE(givennameorig, ''),
                        COALESCE(familynameorig, ''),
                        COALESCE(fullnameorig, '')
                    FROM m_user 
                    WHERE nameorig != 'administrator' 
                    ORDER BY nameorig
                """
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                users = []
                for line in result.stdout.strip().split('\n'):
                    if line and '|' in line:
                        parts = line.split('|')
                        if len(parts) >= 6:
                            users.append({
                                'oid': parts[0].strip(),
                                'name': parts[1].strip(),
                                'email': parts[2].strip() or None,
                                'givenName': parts[3].strip(),
                                'familyName': parts[4].strip(),
                                'fullName': parts[5].strip(),
                                'title': None,
                                'status': 'enabled'
                            })
                
                logger.info(f"Chargé {len(users)} utilisateurs depuis PostgreSQL")
                return users
            else:
                logger.error(f"Erreur PostgreSQL: {result.stderr}")
                return []
                
        except Exception as e:
            logger.error(f"Erreur chargement PostgreSQL: {e}")
            return []
    
    def _parse_users_xml(self, xml_text: str) -> List[Dict]:
        """Parse la réponse XML pour extraire les utilisateurs"""
        users = []
        try:
            # Supprimer le namespace pour faciliter le parsing
            xml_text_clean = xml_text.replace(' xmlns="http://midpoint.evolveum.com/xml/ns/public/common/common-3"', '')
            root = ET.fromstring(xml_text_clean)
            
            for user_elem in root.findall('.//user'):
                oid = user_elem.get('oid', '')
                name_elem = user_elem.find('name')
                email_elem = user_elem.find('emailAddress')
                given_elem = user_elem.find('givenName')
                family_elem = user_elem.find('familyName')
                title_elem = user_elem.find('title')
                status_elem = user_elem.find('.//administrativeStatus')
                
                user = {
                    'oid': oid,
                    'name': name_elem.text if name_elem is not None else '',
                    'email': email_elem.text if email_elem is not None else None,
                    'givenName': given_elem.text if given_elem is not None else '',
                    'familyName': family_elem.text if family_elem is not None else '',
                    'title': title_elem.text if title_elem is not None else None,
                    'status': status_elem.text if status_elem is not None else 'unknown'
                }
                
                # Skip superuser et administrator
                if user['name'] not in ['administrator', 'superuser']:
                    users.append(user)
                    
        except ET.ParseError as e:
            logger.error(f"Erreur parsing XML: {e}")
        except Exception as e:
            logger.error(f"Erreur parsing utilisateurs: {e}")
        
        return users


# Singleton
_midpoint_service: Optional[MidPointService] = None


def get_midpoint_service() -> MidPointService:
    """Retourne l'instance singleton du service MidPoint"""
    global _midpoint_service
    if _midpoint_service is None:
        from ..core.config import settings
        _midpoint_service = MidPointService(
            url=getattr(settings, 'MIDPOINT_URL', 'http://midpoint:8080/midpoint'),
            username=getattr(settings, 'MIDPOINT_USERNAME', 'administrator'),
            password=getattr(settings, 'MIDPOINT_PASSWORD', 'Test5ecr3t')
        )
    return _midpoint_service
