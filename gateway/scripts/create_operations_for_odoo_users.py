#!/usr/bin/env python3
"""
Script de migration : Créer des opérations de provisioning pour tous les utilisateurs Odoo existants

Ce script parcourt tous les utilisateurs avec source="odoo_sync" et crée une opération
de provisioning pour chacun s'ils n'en ont pas déjà une.

Cela permettra de les voir dans le Dashboard "Opérations Récentes".
"""
import sys
import os
from datetime import datetime

# Ajouter le chemin parent pour importer les modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database.models import ProvisionedUser, ProvisioningOperation, OperationStatus


def main():
    """Créer des opérations pour tous les utilisateurs Odoo"""
    
    # Connexion à la base de données
    DATABASE_URL = "sqlite:///aegis.db"
    engine = create_engine(DATABASE_URL)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    
    print("🔍 Recherche des utilisateurs Odoo sans opération...")
    
    # Trouver tous les utilisateurs Odoo
    odoo_users = db.query(ProvisionedUser).filter(
        ProvisionedUser.source == "odoo_sync"
    ).all()
    
    print(f"📊 Trouvé {len(odoo_users)} utilisateurs Odoo au total")
    
    created_count = 0
    skipped_count = 0
    
    for user in odoo_users:
        # Vérifier s'il a déjà une opération
        existing_op = db.query(ProvisioningOperation).filter(
            ProvisioningOperation.user_id == user.id
        ).first()
        
        if existing_op:
            skipped_count += 1
            continue
        
        # Créer une opération
        operation = ProvisioningOperation(
            user_id=user.id,
            status=OperationStatus.SUCCESS.value,
            trigger="odoo_sync",
            started_at=user.created_at or datetime.utcnow(),
            completed_at=user.created_at or datetime.utcnow(),
            total_actions=1,
            successful_actions=1,
            failed_actions=0
        )
        
        db.add(operation)
        created_count += 1
        
        print(f"✅ Opération créée pour: {user.first_name} {user.last_name} ({user.email})")
    
    # Commit
    db.commit()
    
    print("\n" + "=" * 70)
    print(f"✅ Migration terminée !")
    print(f"   - {created_count} opération(s) créée(s)")
    print(f"   - {skipped_count} utilisateur(s) ignoré(s) (ont déjà une opération)")
    print("=" * 70)
    
    print("\n💡 Rafraîchissez le Dashboard pour voir tous les utilisateurs Odoo !")
    
    db.close()


if __name__ == "__main__":
    main()
