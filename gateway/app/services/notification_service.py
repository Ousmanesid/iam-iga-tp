"""
Service de notification pour informer les utilisateurs de leurs accès
"""
import logging
from typing import Dict, List, Optional
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

logger = logging.getLogger(__name__)


class NotificationService:
    """Service pour envoyer des notifications aux utilisateurs après provisionnement"""
    
    def __init__(self, smtp_config: Optional[Dict] = None):
        """
        Initialise le service de notification
        
        Args:
            smtp_config: Configuration SMTP (host, port, username, password)
        """
        self.smtp_config = smtp_config or {}
        self.enabled = bool(self.smtp_config.get('host'))
        
    def send_provisioning_notification(
        self,
        user_email: str,
        user_name: str,
        provisioned_apps: List[Dict[str, str]],
        operation_id: Optional[str] = None
    ) -> bool:
        """
        Envoie une notification à l'utilisateur avec ses accès provisionnés
        
        Args:
            user_email: Email de l'utilisateur
            user_name: Nom complet de l'utilisateur
            provisioned_apps: Liste des applications provisionnées avec leurs infos
            operation_id: ID de l'opération de provisionnement
            
        Returns:
            bool: True si envoyé avec succès, False sinon
        """
        try:
            # Construction du message
            subject = "🔐 Vos accès aux applications métiers"
            body = self._build_notification_body(user_name, provisioned_apps, operation_id)
            
            if self.enabled:
                # Envoi par email
                return self._send_email(user_email, subject, body)
            else:
                # Mode simulation - log uniquement
                logger.info(f"📧 Notification (simulation) pour {user_email}:")
                logger.info(f"Subject: {subject}")
                logger.info(f"Body:\n{body}")
                
                # En mode dev, on peut aussi sauvegarder dans un fichier
                self._save_to_file(user_email, subject, body)
                return True
                
        except Exception as e:
            logger.error(f"Erreur envoi notification à {user_email}: {e}")
            return False
    
    def _build_notification_body(
        self,
        user_name: str,
        provisioned_apps: List[Dict[str, str]],
        operation_id: Optional[str] = None
    ) -> str:
        """Construit le corps du message de notification"""
        
        body = f"""Bonjour {user_name},

Vos accès aux applications métiers ont été provisionnés avec succès !

📋 Récapitulatif de vos accès :

"""
        
        for app in provisioned_apps:
            body += f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔹 {app['name']}
   • URL : {app.get('url', 'N/A')}
   • Identifiant : {app.get('username', user_name)}
   • Rôle : {app.get('role', 'Utilisateur')}
   • Permissions : {app.get('permissions', 'Accès standard')}
"""
            
            if app.get('temporary_password'):
                body += f"   ⚠️  Mot de passe temporaire : {app['temporary_password']}\n"
                body += "   📌 Vous devrez le changer à votre première connexion\n"
            else:
                body += "   🔑 Utilisez votre mot de passe d'entreprise (SSO)\n"
        
        body += f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📚 Besoin d'aide ?
   • Documentation : https://docs.aegis.local
   • Support IT : support@aegis.local

⚠️  SÉCURITÉ :
   • Ne partagez jamais vos mots de passe
   • Changez les mots de passe temporaires immédiatement
   • Signalez toute activité suspecte au support

"""
        
        if operation_id:
            body += f"\nRéférence opération : {operation_id}\n"
        
        body += f"""
Date : {datetime.now().strftime('%d/%m/%Y %H:%M')}

Cordialement,
L'équipe Aegis Gateway 🛡️
"""
        
        return body
    
    def _send_email(self, to_email: str, subject: str, body: str) -> bool:
        """Envoie un email via SMTP"""
        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = self.smtp_config.get('from_email', 'noreply@aegis.local')
            msg['To'] = to_email
            
            # Partie texte
            text_part = MIMEText(body, 'plain', 'utf-8')
            msg.attach(text_part)
            
            # Connexion SMTP
            with smtplib.SMTP(
                self.smtp_config['host'],
                self.smtp_config.get('port', 587)
            ) as server:
                if self.smtp_config.get('use_tls', True):
                    server.starttls()
                
                if self.smtp_config.get('username'):
                    server.login(
                        self.smtp_config['username'],
                        self.smtp_config['password']
                    )
                
                server.send_message(msg)
                
            logger.info(f"✅ Email envoyé à {to_email}")
            return True
            
        except Exception as e:
            logger.error(f"Erreur envoi email à {to_email}: {e}")
            return False
    
    def _save_to_file(self, user_email: str, subject: str, body: str):
        """Sauvegarde la notification dans un fichier (mode dev)"""
        try:
            filename = f"/tmp/notification_{user_email.replace('@', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(f"To: {user_email}\n")
                f.write(f"Subject: {subject}\n")
                f.write(f"\n{body}\n")
            logger.info(f"📄 Notification sauvegardée : {filename}")
        except Exception as e:
            logger.warning(f"Impossible de sauvegarder la notification : {e}")


# Instance singleton
_notification_service: Optional[NotificationService] = None


def get_notification_service() -> NotificationService:
    """Retourne l'instance singleton du service de notification"""
    global _notification_service
    if _notification_service is None:
        from ..core.config import settings
        
        # Configuration SMTP depuis les settings
        smtp_config = None
        if hasattr(settings, 'SMTP_HOST') and settings.SMTP_HOST:
            smtp_config = {
                'host': settings.SMTP_HOST,
                'port': getattr(settings, 'SMTP_PORT', 587),
                'username': getattr(settings, 'SMTP_USERNAME', None),
                'password': getattr(settings, 'SMTP_PASSWORD', None),
                'use_tls': getattr(settings, 'SMTP_USE_TLS', True),
                'from_email': getattr(settings, 'SMTP_FROM_EMAIL', 'noreply@aegis.local')
            }
        
        _notification_service = NotificationService(smtp_config)
    
    return _notification_service
