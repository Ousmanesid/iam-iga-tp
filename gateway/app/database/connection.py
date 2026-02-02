"""
Database Connection & Session Management
Gère la connexion SQLAlchemy et fournit les sessions DB
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator

from app.core.config import settings

# Engine SQLite avec check_same_thread=False pour FastAPI
engine = create_engine(
    settings.DATABASE_URL, 
    connect_args={"check_same_thread": False},
    echo=False  # Set to True for SQL debugging
)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """
    Dependency pour obtenir une session DB dans les routes FastAPI.
    
    Usage:
        @router.get("/users")
        def get_users(db: Session = Depends(get_db)):
            return db.query(User).all()
    
    Yields:
        Session: Session SQLAlchemy qui sera fermée automatiquement
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
