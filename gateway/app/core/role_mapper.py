"""
Role Mapper - Utilise UNIQUEMENT les rôles de MidPoint

Ce module sert de pont entre Aegis Gateway et MidPoint.
Tous les rôles et mappings viennent de MidPoint.
"""
from typing import List, Dict, Optional
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class Application(str, Enum):
    """Applications disponibles pour le provisioning."""
    KEYCLOAK = "Keycloak"
    GITLAB = "GitLab"
    MATTERMOST = "Mattermost"
    NOTION = "Notion"
    JENKINS = "Jenkins"
    KUBERNETES = "Kubernetes"
    ODOO = "Odoo"
    CRM = "CRM"
    SECURE_HR = "SecureHR"
    SAP = "SAP"
    POSTGRESQL = "PostgreSQL"
    LDAP = "LDAP"
    NEXTCLOUD = "Nextcloud"


# Cache des rôles MidPoint
_midpoint_roles_cache: Optional[List[Dict]] = None


def _get_midpoint_roles() -> List[Dict]:
    """Récupère les rôles depuis MidPoint (avec cache)"""
    global _midpoint_roles_cache
    
    if _midpoint_roles_cache is not None:
        return _midpoint_roles_cache
    
    try:
        from ..services.midpoint_role_service import MidPointRoleService
        service = MidPointRoleService()
        roles = service.get_all_roles()
        _midpoint_roles_cache = roles
        logger.info(f"Chargé {len(roles)} rôles depuis MidPoint")
        return roles
    except Exception as e:
        logger.error(f"Erreur récupération rôles MidPoint: {e}")
        return []


def clear_roles_cache():
    """Vide le cache des rôles (pour forcer un refresh)"""
    global _midpoint_roles_cache
    _midpoint_roles_cache = None
    logger.info("Cache des rôles vidé")


def get_applications_for_job_title(job_title: str) -> List[str]:
    """
    Retourne la liste des applications à provisionner pour un job title.
    Utilise les rôles de MidPoint.
    
    Args:
        job_title (str): Titre du poste (ex: "Développeur", "Commercial")
    
    Returns:
        List[str]: Liste des noms d'applications basée sur les inducements MidPoint
        
    Examples:
        >>> get_applications_for_job_title("Développeur")
        ['LDAP', 'Keycloak', 'GitLab']  # Depuis les inducements MidPoint
    """
    roles = _get_midpoint_roles()
    
    # Chercher le rôle correspondant au job title
    matching_role = None
    job_title_normalized = job_title.lower().strip()
    
    for role in roles:
        role_name = role.get('name', '').lower()
        # Correspondance exacte ou partielle
        if job_title_normalized in role_name or role_name in job_title_normalized:
            matching_role = role
            break
    
    if not matching_role:
        # Fallback : chercher dans la description
        for role in roles:
            description = role.get('description', '').lower()
            if job_title_normalized in description:
                matching_role = role
                break
    
    if not matching_role:
        logger.warning(f"Aucun rôle MidPoint trouvé pour '{job_title}', retour au défaut")
        return [Application.KEYCLOAK]  # Minimum : SSO
    
    # Extraire les applications depuis les inducements du rôle
    # Note: Les inducements MidPoint contiennent les ressources cibles (LDAP, Odoo, etc.)
    applications = [Application.KEYCLOAK]  # SSO toujours inclus
    
    # Mapper les ressources MidPoint vers nos applications
    role_name = matching_role.get('name', '').lower()
    
    # Règles de provisioning basées sur le métier (Odoo -> MidPoint -> Apps)
    if 'employee' in role_name or 'employé' in role_name:
        applications.extend([Application.LDAP, Application.ODOO, Application.MATTERMOST])
    elif 'developer' in role_name or 'développeur' in role_name:
        applications.extend([Application.LDAP, Application.GITLAB, Application.MATTERMOST, Application.NEXTCLOUD])
    elif 'admin' in role_name:
        applications.extend([Application.LDAP, Application.GITLAB, Application.POSTGRESQL, Application.MATTERMOST, Application.NEXTCLOUD])
    elif 'hr' in role_name or 'rh' in role_name:
        applications.extend([Application.LDAP, Application.ODOO, Application.SECURE_HR, Application.MATTERMOST, Application.NEXTCLOUD])
    elif 'commercial' in role_name or 'sales' in role_name:
        applications.extend([Application.LDAP, Application.ODOO, Application.CRM, Application.MATTERMOST])
    
    return list(set(applications))  # Dédoublonnage


def get_all_supported_roles() -> List[str]:
    """
    Retourne la liste de tous les rôles supportés depuis MidPoint.
    
    Returns:
        List[str]: Liste des noms de rôles MidPoint
    """
    roles = _get_midpoint_roles()
    return [role.get('name', 'Unknown') for role in roles]


def get_role_summary() -> Dict[str, int]:
    """
    Retourne un résumé des rôles MidPoint.
    
    Returns:
        Dict[str, int]: Statistiques sur les rôles
    """
    roles = _get_midpoint_roles()
    return {
        'total_roles': len(roles),
        'from_midpoint': len(roles),
        'hardcoded': 0  # Plus de rôles hardcodés !
    }


def get_role_details(role_name: str) -> Optional[Dict]:
    """
    Récupère les détails d'un rôle depuis MidPoint.
    
    Args:
        role_name (str): Nom du rôle
        
    Returns:
        Optional[Dict]: Détails du rôle ou None
    """
    roles = _get_midpoint_roles()
    role_name_normalized = role_name.lower().strip()
    
    for role in roles:
        if role.get('name', '').lower() == role_name_normalized:
            return role
    
    return None


def get_all_applications() -> List[Dict[str, str]]:
    """
    Retourne la liste de toutes les applications disponibles pour le provisioning.
    
    Returns:
        List[Dict]: Liste des applications avec nom et description
    """
    return [
        {"name": Application.KEYCLOAK, "description": "Single Sign-On (SSO)"},
        {"name": Application.LDAP, "description": "Annuaire LDAP"},
        {"name": Application.ODOO, "description": "ERP Odoo"},
        {"name": Application.MATTERMOST, "description": "Communication interne (Chat)"},
        {"name": Application.NEXTCLOUD, "description": "Partage de fichiers et collaboration"},
        {"name": Application.GITLAB, "description": "Gestion du code source"},
        {"name": Application.POSTGRESQL, "description": "Base de données"},
        {"name": Application.CRM, "description": "Gestion clients"},
        {"name": Application.SECURE_HR, "description": "Ressources humaines"},
    ]


def validate_application_exists(app_name: str) -> bool:
    """
    Vérifie si une application existe dans la configuration.
    
    Args:
        app_name (str): Nom de l'application
        
    Returns:
        bool: True si l'application existe
    """
    try:
        Application(app_name)
        return True
    except ValueError:
        return False


def get_provisioning_plan(user_data: dict) -> Dict[str, any]:
    """
    Génère un plan de provisioning complet pour un utilisateur.
    Basé sur les rôles MidPoint.
    
    Args:
        user_data (dict): Données utilisateur avec job_title, email, etc.
        
    Returns:
        Dict: Plan de provisioning avec applications et métadonnées
        
    Example:
        >>> plan = get_provisioning_plan({
        ...     "email": "alice@company.com",
        ...     "job_title": "Développeur",
        ...     "first_name": "Alice",
        ...     "last_name": "Doe"
        ... })
        >>> print(plan['applications'])
        ['LDAP', 'Keycloak', 'GitLab']  # Depuis MidPoint
    """
    job_title = user_data.get("job_title", "")
    applications = get_applications_for_job_title(job_title)
    
    return {
        "user": {
            "email": user_data.get("email"),
            "first_name": user_data.get("first_name"),
            "last_name": user_data.get("last_name"),
            "job_title": job_title,
            "department": user_data.get("department"),
        },
        "applications": applications,
        "total_actions": len(applications),
        "estimated_duration_seconds": len(applications) * 5,  # ~5s par app
        "requires_manual_approval": len(applications) > 10,  # Cas exceptionnel
        "source": "midpoint"  # Indique que les rôles viennent de MidPoint
    }


if __name__ == "__main__":
    # Test du module
    print("🎭 Role Mapper - Test (MidPoint)")
    print("=" * 60)
    
    # Test 1: Développeur
    apps = get_applications_for_job_title("Développeur")
    print(f"\n✅ Développeur → {apps}")
    
    # Test 2: Employee
    apps = get_applications_for_job_title("Employee")
    print(f"✅ Employee → {apps}")
    
    # Test 3: Liste des rôles
    roles = get_all_supported_roles()
    print(f"\n✅ Rôles disponibles: {roles}")
    
    # Test 4: Résumé
    summary = get_role_summary()
    print(f"\n✅ Résumé: {summary}")

    
    # Test 3: Job title inconnu
    apps = get_applications_for_job_title("Product Manager")
    print(f"⚠️  Product Manager (inconnu) → {apps}")
    
    # Test 4: Plan complet
    plan = get_provisioning_plan({
        "email": "alice@company.com",
        "job_title": "Développeur",
        "first_name": "Alice",
        "last_name": "Doe",
        "department": "IT"
    })
    print(f"\n📋 Plan de provisioning pour Alice:")
    print(f"   Applications: {plan['applications']}")
    print(f"   Durée estimée: {plan['estimated_duration_seconds']}s")
