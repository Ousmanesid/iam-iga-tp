"""
Script d'initialisation de la base de données
Crée toutes les tables selon les modèles SQLAlchemy
"""
import sys
from pathlib import Path

# Ajouter le répertoire parent au PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database.models import Base
from sqlalchemy import create_engine
from app.core.config import settings

def init_database():
    """Initialise la base de données avec toutes les tables"""
    print("🔧 Initialisation de la base de données...")
    print(f"📁 Base de données: {settings.DATABASE_URL}")
    
    # Créer l'engine
    engine = create_engine(settings.DATABASE_URL, echo=True)
    
    # Créer toutes les tables
    Base.metadata.create_all(bind=engine)
    
    print("✅ Base de données initialisée avec succès!")
    print("\nTables créées:")
    for table in Base.metadata.sorted_tables:
        print(f"  - {table.name}")

if __name__ == "__main__":
    init_database()
