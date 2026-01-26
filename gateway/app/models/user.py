"""
Modèles Pydantic pour les utilisateurs
"""

from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID
from enum import Enum


class UserStatus(str, Enum):
    """Statut d'un utilisateur"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    PENDING = "pending"


class UserCreate(BaseModel):
    """Modèle pour la création d'un utilisateur"""
    login: str = Field(..., min_length=3, max_length=100)
    email: EmailStr
    password: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    department: Optional[str] = None
    job_title: Optional[str] = None
    employee_number: Optional[str] = None
    manager_login: Optional[str] = None
    is_active: bool = True
    midpoint_oid: Optional[str] = None
    attributes: Dict[str, Any] = Field(default_factory=dict)
    roles: List[str] = Field(default_factory=list)
    permissions: List[str] = Field(default_factory=list)


class UserUpdate(BaseModel):
    """Modèle pour la mise à jour d'un utilisateur"""
    email: Optional[EmailStr] = None
    password: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    department: Optional[str] = None
    job_title: Optional[str] = None
    employee_number: Optional[str] = None
    manager_login: Optional[str] = None
    is_active: Optional[bool] = None
    is_locked: Optional[bool] = None
    attributes: Optional[Dict[str, Any]] = None


class UserResponse(BaseModel):
    """Modèle de réponse pour un utilisateur"""
    id: UUID
    login: str
    email: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    full_name: Optional[str] = None
    department: Optional[str] = None
    job_title: Optional[str] = None
    employee_number: Optional[str] = None
    is_active: bool
    is_locked: bool = False
    midpoint_oid: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    roles: List[str] = Field(default_factory=list)
    permissions: List[str] = Field(default_factory=list)
    
    class Config:
        from_attributes = True


class RoleAssignment(BaseModel):
    """Modèle pour l'assignation de rôle"""
    user_login: str
    role_code: str
    assigned_by: str = "gateway"
    source: str = "manual"
    valid_until: Optional[datetime] = None


class PermissionAssignment(BaseModel):
    """Modèle pour l'assignation de permission directe"""
    user_login: str
    permission_code: str
    assigned_by: str = "gateway"
    reason: Optional[str] = None
    valid_until: Optional[datetime] = None


class UserPermissions(BaseModel):
    """Modèle pour les permissions effectives d'un utilisateur"""
    user_login: str
    permissions: List[Dict[str, str]]
    computed_at: datetime = Field(default_factory=datetime.utcnow)








