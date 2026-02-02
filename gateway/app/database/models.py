"""Database Models - Modèles de persistance."""

from datetime import datetime
from typing import Optional
from enum import Enum

from sqlalchemy import (
    create_engine, 
    Column, 
    Integer, 
    String, 
    DateTime, 
    Text, 
    Enum as SQLEnum,
    ForeignKey,
    Boolean,
    JSON,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker

from app.core.config import settings

# Configuration de la base de données
DATABASE_URL = settings.DATABASE_URL

engine = create_engine(
    DATABASE_URL, 
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {},
    echo=settings.DEBUG,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class OperationStatus(str, Enum):
    """Statut d'une opération de provisioning."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    SUCCESS = "success"
    FAILED = "failed"
    PARTIAL = "partial"


class ActionStatus(str, Enum):
    """Statut d'une action."""
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


class ProvisionedUser(Base):
    """Utilisateur provisionné."""
    __tablename__ = "provisioned_users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    job_title = Column(String(200))
    department = Column(String(100))
    role = Column(String(100), nullable=True)  # Rôle métier (Developer, Manager, etc.)
    status = Column(String(50), default=OperationStatus.PENDING.value)
    source = Column(String(50), default="api")  # Source: "api", "odoo_sync", "manual", etc.
    
    created_at = Column(DateTime, default=datetime.utcnow)
    last_modified = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_provisioned_at = Column(DateTime, nullable=True)
    
    # Relations
    operations = relationship("ProvisioningOperation", back_populates="user")


class ProvisioningOperation(Base):
    """Opération de provisioning."""
    __tablename__ = "provisioning_operations"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("provisioned_users.id"), nullable=False)
    
    status = Column(String(50), default=OperationStatus.IN_PROGRESS.value)
    trigger = Column(String(50), default="api")
    
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    
    total_actions = Column(Integer, default=0)
    successful_actions = Column(Integer, default=0)
    failed_actions = Column(Integer, default=0)
    
    # Relations
    user = relationship("ProvisionedUser", back_populates="operations")
    actions = relationship("ProvisioningAction", back_populates="operation")


class ProvisioningAction(Base):
    """Action de provisioning."""
    __tablename__ = "provisioning_actions"
    
    id = Column(Integer, primary_key=True, index=True)
    operation_id = Column(Integer, ForeignKey("provisioning_operations.id"), nullable=False)
    
    action_type = Column(String(100), nullable=False)
    application = Column(String(100), nullable=False)
    target_user = Column(String(255), nullable=False)
    status = Column(String(50), default=ActionStatus.PENDING.value)
    message = Column(Text, nullable=True)
    details = Column(JSON, nullable=True)
    
    executed_at = Column(DateTime, nullable=True)
    
    # Relations
    operation = relationship("ProvisioningOperation", back_populates="actions")


class AuditLog(Base):
    """Log d'audit."""
    __tablename__ = "audit_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    action = Column(String(100), nullable=False)
    actor = Column(String(255), nullable=False)
    target = Column(String(255), nullable=True)
    message = Column(Text, nullable=False)
    level = Column(String(20), default="INFO")
    source_ip = Column(String(50), nullable=True)
    details = Column(JSON, nullable=True)


def init_db():
    """Initialize database."""
    Base.metadata.create_all(bind=engine)


def get_db():
    """Get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
