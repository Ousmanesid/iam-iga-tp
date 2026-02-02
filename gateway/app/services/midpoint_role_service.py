"""
Service MidPoint Roles - Gestion des rôles via API REST
"""
import httpx
from typing import List, Dict, Optional
import logging
import xml.etree.ElementTree as ET
from ..core.config import settings

logger = logging.getLogger(__name__)

# Namespace MidPoint
NS = {
    'c': 'http://midpoint.evolveum.com/xml/ns/public/common/common-3',
    't': 'http://prism.evolveum.com/xml/ns/public/types-3',
    'q': 'http://prism.evolveum.com/xml/ns/public/query-3'
}


class MidPointRoleService:
    """Service pour gérer les rôles MidPoint"""
    
    def __init__(self):
        self.url = getattr(settings, 'MIDPOINT_URL', 'http://midpoint:8080/midpoint')
        self.username = getattr(settings, 'MIDPOINT_USERNAME', 'administrator')
        self.password = getattr(settings, 'MIDPOINT_PASSWORD', 'Test5ecr3t')
        self.auth = (self.username, self.password)
    
    def _get_client(self) -> httpx.Client:
        """Crée un client HTTP configuré"""
        return httpx.Client(
            base_url=self.url,
            auth=self.auth,
            headers={
                "Content-Type": "application/xml",
                "Accept": "application/xml"
            },
            timeout=30.0
        )
    
    def get_all_roles(self) -> List[Dict]:
        """Récupère tous les rôles depuis MidPoint"""
        try:
            with self._get_client() as client:
                response = client.get("/ws/rest/roles")
                
                if response.status_code != 200:
                    logger.error(f"Erreur récupération rôles: {response.status_code}")
                    return []
                
                return self._parse_roles_xml(response.text)
                
        except Exception as e:
            logger.error(f"Erreur connexion MidPoint: {e}")
            return []
    
    def _parse_roles_xml(self, xml_text: str) -> List[Dict]:
        """Parse la réponse XML MidPoint pour extraire les rôles"""
        roles = []
        try:
            root = ET.fromstring(xml_text)
            
            # Chercher tous les éléments role
            for role_elem in root.findall('.//c:role', NS) or root.findall('.//role', NS):
                role = self._parse_single_role(role_elem)
                if role:
                    roles.append(role)
            
            # Si pas trouvé avec namespace, essayer sans
            if not roles:
                for role_elem in root.iter():
                    if role_elem.tag.endswith('role'):
                        role = self._parse_single_role(role_elem)
                        if role:
                            roles.append(role)
                            
        except ET.ParseError as e:
            logger.error(f"Erreur parsing XML: {e}")
        
        return roles
    
    def _parse_single_role(self, role_elem) -> Optional[Dict]:
        """Parse un élément role XML"""
        try:
            # Extraire OID
            oid = role_elem.get('oid', '')
            
            # Helper pour trouver un élément avec ou sans namespace
            def find_text(elem, tag):
                for ns_prefix in ['c:', '']:
                    found = elem.find(f'.//{ns_prefix}{tag}', NS if ns_prefix else {})
                    if found is not None and found.text:
                        return found.text
                # Chercher sans namespace
                for child in elem.iter():
                    if child.tag.endswith(tag) and child.text:
                        return child.text
                return None
            
            name = find_text(role_elem, 'name') or 'Unknown'
            
            # Skip les rôles système
            if name.startswith('Superuser') or name.startswith('End user'):
                return None
            
            return {
                'id': oid,
                'oid': oid,
                'name': name,
                'displayName': find_text(role_elem, 'displayName') or name,
                'description': find_text(role_elem, 'description') or '',
                'riskLevel': find_text(role_elem, 'riskLevel') or 'low',
                'requestable': find_text(role_elem, 'requestable') == 'true',
                'source': 'midpoint'
            }
        except Exception as e:
            logger.error(f"Erreur parsing role: {e}")
            return None
    
    def get_role_by_oid(self, oid: str) -> Optional[Dict]:
        """Récupère un rôle spécifique par son OID"""
        try:
            with self._get_client() as client:
                response = client.get(f"/ws/rest/roles/{oid}")
                
                if response.status_code != 200:
                    return None
                
                root = ET.fromstring(response.text)
                return self._parse_single_role(root)
                
        except Exception as e:
            logger.error(f"Erreur récupération rôle {oid}: {e}")
            return None
    
    def get_role_members(self, role_oid: str) -> List[Dict]:
        """Récupère les utilisateurs ayant ce rôle"""
        query = f"""<?xml version="1.0" encoding="UTF-8"?>
        <q:query xmlns:q="http://prism.evolveum.com/xml/ns/public/query-3"
                 xmlns:c="http://midpoint.evolveum.com/xml/ns/public/common/common-3">
            <q:filter>
                <q:ref>
                    <q:path>assignment/targetRef</q:path>
                    <q:value oid="{role_oid}" type="c:RoleType"/>
                </q:ref>
            </q:filter>
        </q:query>"""
        
        try:
            with self._get_client() as client:
                response = client.post("/ws/rest/users/search", content=query)
                
                if response.status_code != 200:
                    return []
                
                return self._parse_users_xml(response.text)
                
        except Exception as e:
            logger.error(f"Erreur recherche membres: {e}")
            return []
    
    def _parse_users_xml(self, xml_text: str) -> List[Dict]:
        """Parse la réponse XML pour extraire les utilisateurs"""
        users = []
        try:
            root = ET.fromstring(xml_text)
            
            for user_elem in root.iter():
                if user_elem.tag.endswith('user'):
                    oid = user_elem.get('oid', '')
                    name = None
                    email = None
                    
                    for child in user_elem.iter():
                        if child.tag.endswith('name') and child.text:
                            name = child.text
                        if child.tag.endswith('emailAddress') and child.text:
                            email = child.text
                    
                    if name:
                        users.append({
                            'oid': oid,
                            'name': name,
                            'email': email or ''
                        })
                        
        except ET.ParseError:
            pass
        
        return users
    
    def assign_role_to_user(self, user_oid: str, role_oid: str) -> bool:
        """Assigne un rôle à un utilisateur"""
        assignment_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
        <objectModification xmlns="http://midpoint.evolveum.com/xml/ns/public/common/api-types-3"
                           xmlns:c="http://midpoint.evolveum.com/xml/ns/public/common/common-3"
                           xmlns:t="http://prism.evolveum.com/xml/ns/public/types-3">
            <itemDelta>
                <t:modificationType>add</t:modificationType>
                <t:path>c:assignment</t:path>
                <t:value>
                    <c:targetRef oid="{role_oid}" type="c:RoleType"/>
                </t:value>
            </itemDelta>
        </objectModification>"""
        
        try:
            with self._get_client() as client:
                response = client.patch(
                    f"/ws/rest/users/{user_oid}",
                    content=assignment_xml
                )
                
                if response.status_code in [200, 204]:
                    logger.info(f"Rôle {role_oid} assigné à {user_oid}")
                    return True
                else:
                    logger.error(f"Erreur assignation: {response.status_code}")
                    return False
                    
        except Exception as e:
            logger.error(f"Erreur assignation rôle: {e}")
            return False
    
    def unassign_role_from_user(self, user_oid: str, role_oid: str) -> bool:
        """Retire un rôle d'un utilisateur"""
        unassignment_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
        <objectModification xmlns="http://midpoint.evolveum.com/xml/ns/public/common/api-types-3"
                           xmlns:c="http://midpoint.evolveum.com/xml/ns/public/common/common-3"
                           xmlns:t="http://prism.evolveum.com/xml/ns/public/types-3">
            <itemDelta>
                <t:modificationType>delete</t:modificationType>
                <t:path>c:assignment</t:path>
                <t:value>
                    <c:targetRef oid="{role_oid}" type="c:RoleType"/>
                </t:value>
            </itemDelta>
        </objectModification>"""
        
        try:
            with self._get_client() as client:
                response = client.patch(
                    f"/ws/rest/users/{user_oid}",
                    content=unassignment_xml
                )
                return response.status_code in [200, 204]
                
        except Exception as e:
            logger.error(f"Erreur retrait rôle: {e}")
            return False


# Singleton
_role_service: Optional[MidPointRoleService] = None


def get_role_service() -> MidPointRoleService:
    """Retourne l'instance singleton du service"""
    global _role_service
    if _role_service is None:
        _role_service = MidPointRoleService()
    return _role_service
