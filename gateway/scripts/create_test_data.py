"""
Script pour créer des données de test dans Aegis Gateway
"""
import sys
import os
sys.path.insert(0, os.path.abspath('.'))

from datetime import datetime, timedelta
from app.database.models import SessionLocal, ProvisionedUser, ProvisioningOperation, ProvisioningAction, OperationStatus, ActionStatus

def create_test_data():
    db = SessionLocal()
    
    print("🎭 Création de données de test pour Aegis Gateway...")
    print("=" * 60)
    
    # Créer des utilisateurs
    users_data = [
        {"email": "sophie.martin@aegis.local", "first_name": "Sophie", "last_name": "Martin", 
         "job_title": "Développeuse Full-Stack", "department": "IT"},
        {"email": "lucas.dubois@aegis.local", "first_name": "Lucas", "last_name": "Dubois", 
         "job_title": "Commercial Senior", "department": "Ventes"},
        {"email": "emma.bernard@aegis.local", "first_name": "Emma", "last_name": "Bernard", 
         "job_title": "RH Manager", "department": "Ressources Humaines"},
        {"email": "thomas.petit@aegis.local", "first_name": "Thomas", "last_name": "Petit", 
         "job_title": "DevOps Engineer", "department": "IT"},
        {"email": "marie.roux@aegis.local", "first_name": "Marie", "last_name": "Roux", 
         "job_title": "Comptable", "department": "Finance"},
    ]
    
    users = []
    for user_data in users_data:
        user = ProvisionedUser(**user_data, status=OperationStatus.SUCCESS.value)
        db.add(user)
        users.append(user)
    
    db.commit()
    print(f"✅ {len(users)} utilisateurs créés")
    
    # Créer des opérations
    operations_config = [
        # Opération 1 : Succès complet
        {
            "user": users[0],
            "status": OperationStatus.SUCCESS.value,
            "time_offset": -2,  # il y a 2 heures
            "actions": [
                {"app": "Keycloak", "type": "create_user", "status": ActionStatus.SUCCESS.value, 
                 "message": "User created successfully"},
                {"app": "GitLab", "type": "create_user", "status": ActionStatus.SUCCESS.value, 
                 "message": "User added to developers group"},
                {"app": "Mattermost", "type": "create_user", "status": ActionStatus.SUCCESS.value, 
                 "message": "User invited to #dev-team channel"},
                {"app": "Notion", "type": "grant_access", "status": ActionStatus.SUCCESS.value, 
                 "message": "Access granted to Engineering workspace"},
            ]
        },
        # Opération 2 : Échec critique
        {
            "user": users[1],
            "status": OperationStatus.FAILED.value,
            "time_offset": -5,  # il y a 5 heures
            "actions": [
                {"app": "Keycloak", "type": "create_user", "status": ActionStatus.SUCCESS.value, 
                 "message": "User created successfully"},
                {"app": "Odoo", "type": "create_user", "status": ActionStatus.FAILED.value, 
                 "message": "ERROR: Database connection timeout after 30s"},
                {"app": "CRM", "type": "create_user", "status": ActionStatus.SKIPPED.value, 
                 "message": "Skipped due to previous failure"},
            ]
        },
        # Opération 3 : Partiel
        {
            "user": users[2],
            "status": OperationStatus.PARTIAL.value,
            "time_offset": -24,  # hier
            "actions": [
                {"app": "Keycloak", "type": "create_user", "status": ActionStatus.SUCCESS.value, 
                 "message": "User created successfully"},
                {"app": "Odoo", "type": "create_user", "status": ActionStatus.SUCCESS.value, 
                 "message": "HR employee record created"},
                {"app": "SecureHR", "type": "grant_access", "status": ActionStatus.FAILED.value, 
                 "message": "ERROR: User already exists with different email"},
            ]
        },
        # Opération 4 : Succès récent
        {
            "user": users[3],
            "status": OperationStatus.SUCCESS.value,
            "time_offset": -0.5,  # il y a 30 minutes
            "actions": [
                {"app": "Keycloak", "type": "create_user", "status": ActionStatus.SUCCESS.value, 
                 "message": "User created successfully"},
                {"app": "GitLab", "type": "create_user", "status": ActionStatus.SUCCESS.value, 
                 "message": "Admin rights granted"},
                {"app": "Jenkins", "type": "grant_access", "status": ActionStatus.SUCCESS.value, 
                 "message": "Added to CI/CD administrators"},
                {"app": "Kubernetes", "type": "grant_access", "status": ActionStatus.SUCCESS.value, 
                 "message": "Cluster access configured"},
            ]
        },
        # Opération 5 : Échec complet
        {
            "user": users[4],
            "status": OperationStatus.FAILED.value,
            "time_offset": -72,  # il y a 3 jours
            "actions": [
                {"app": "Keycloak", "type": "create_user", "status": ActionStatus.FAILED.value, 
                 "message": "ERROR: Email validation failed - invalid domain"},
                {"app": "Odoo", "type": "create_user", "status": ActionStatus.SKIPPED.value, 
                 "message": "Skipped due to previous failure"},
            ]
        },
    ]
    
    for config in operations_config:
        # Créer l'opération
        started_at = datetime.utcnow() + timedelta(hours=config["time_offset"])
        operation = ProvisioningOperation(
            user_id=config["user"].id,
            status=config["status"],
            trigger="api",
            started_at=started_at,
            completed_at=started_at + timedelta(seconds=15),
        )
        db.add(operation)
        db.flush()
        
        # Créer les actions
        total = len(config["actions"])
        success = sum(1 for a in config["actions"] if a["status"] == ActionStatus.SUCCESS.value)
        failed = sum(1 for a in config["actions"] if a["status"] == ActionStatus.FAILED.value)
        
        operation.total_actions = total
        operation.successful_actions = success
        operation.failed_actions = failed
        
        for i, action_data in enumerate(config["actions"]):
            action = ProvisioningAction(
                operation_id=operation.id,
                action_type=action_data["type"],
                application=action_data["app"],
                target_user=config["user"].email,
                status=action_data["status"],
                message=action_data["message"],
                executed_at=started_at + timedelta(seconds=i*3),
            )
            db.add(action)
    
    db.commit()
    print(f"✅ {len(operations_config)} opérations créées avec leurs actions")
    print("")
    print("=" * 60)
    print("🎉 Données de test créées avec succès !")
    print("")
    print("📊 Statistiques :")
    print(f"   • {len(users)} utilisateurs")
    print(f"   • {len(operations_config)} opérations")
    print(f"   • Succès: 2 | Échecs: 2 | Partiels: 1")
    print("")
    print("🌐 Accédez au Dashboard pour voir les données :")
    print("   → http://136.119.23.158:5174")
    print("=" * 60)
    
    db.close()

if __name__ == "__main__":
    create_test_data()
