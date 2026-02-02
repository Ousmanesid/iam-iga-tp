"""User models.""""""

from typing import OptionalModèle User - Représentation d'un utilisateur.

from pydantic import BaseModel, EmailStr

⚠️ Phase 1: Modèle logique uniquement, pas de base de données.

   La persistance sera ajoutée en Phase 2.

class UserBase(BaseModel):"""

    """Base user model."""

    email: EmailStrfrom typing import Optional, Annotated

    first_name: strfrom enum import Enum

    last_name: strfrom datetime import datetime

    job_title: Optional[str] = Nonefrom pydantic import BaseModel, EmailStr, Field, ConfigDict, field_validator

    department: Optional[str] = Noneimport re





class UserCreate(UserBase):class UserStatus(str, Enum):

    """User creation model."""    """Statuts possibles d'un utilisateur."""

    pass    ACTIVE = "active"

    INACTIVE = "inactive"

    PENDING = "pending"

class User(UserBase):    SUSPENDED = "suspended"

    """User model."""

    id: int

    class UserBase(BaseModel):

    class Config:    """

        from_attributes = True    Attributs de base d'un utilisateur.

    

    Utilisé comme base pour les autres schémas.

class UserResponse(BaseModel):    """

    """User response model."""    first_name: str = Field(..., min_length=1, max_length=100, description="Prénom")

    id: int    last_name: str = Field(..., min_length=1, max_length=100, description="Nom")

    email: str    email: str = Field(..., description="Adresse email")

    first_name: str    job_title: Optional[str] = Field(None, max_length=200, description="Métier/Poste")

    last_name: str    department: Optional[str] = Field(None, max_length=100, description="Département")

    full_name: str    

    job_title: Optional[str]    @field_validator('email')

    department: Optional[str]    @classmethod

        def validate_email(cls, v: str) -> str:

    @classmethod        """Validate email with a relaxed pattern that accepts test domains."""

    def from_user(cls, user: User):        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'

        """Create response from user."""        if not re.match(pattern, v):

        return cls(            raise ValueError('Format email invalide (ex: user@domain.com)')

            id=user.id,        return v.lower()

            email=user.email,

            first_name=user.first_name,

            last_name=user.last_name,class UserCreate(UserBase):

            full_name=f"{user.first_name} {user.last_name}",    """

            job_title=user.job_title,    Schéma pour la création d'un utilisateur.

            department=user.department,    

        )    Hérite de UserBase avec des champs optionnels supplémentaires.

    """
    status: UserStatus = Field(default=UserStatus.PENDING, description="Statut")


class User(UserBase):
    """
    Modèle complet d'un utilisateur.
    
    Représentation interne avec tous les champs.
    """
    id: int = Field(..., description="Identifiant unique")
    status: UserStatus = Field(default=UserStatus.PENDING, description="Statut")
    created_at: datetime = Field(default_factory=datetime.now, description="Date de création")
    updated_at: Optional[datetime] = Field(None, description="Date de mise à jour")
    
    # === Future: Relations ===
    # roles: List[str] = Field(default_factory=list, description="Rôles attribués")
    # odoo_id: Optional[int] = Field(None, description="ID Odoo")
    # midpoint_oid: Optional[str] = Field(None, description="OID MidPoint")
    
    @property
    def full_name(self) -> str:
        """Retourne le nom complet de l'utilisateur."""
        return f"{self.first_name} {self.last_name}"
    
    @property
    def is_active(self) -> bool:
        """Vérifie si l'utilisateur est actif."""
        return self.status == UserStatus.ACTIVE


class UserResponse(BaseModel):
    """
    Schéma de réponse pour un utilisateur.
    
    Utilisé pour sérialiser les réponses API.
    """
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    first_name: str
    last_name: str
    full_name: str
    email: str
    job_title: Optional[str] = None
    department: Optional[str] = None
    status: UserStatus
    created_at: datetime
    
    @classmethod
    def from_user(cls, user: User) -> "UserResponse":
        """Crée une réponse à partir d'un User."""
        return cls(
            id=user.id,
            first_name=user.first_name,
            last_name=user.last_name,
            full_name=user.full_name,
            email=user.email,
            job_title=user.job_title,
            department=user.department,
            status=user.status,
            created_at=user.created_at,
        )
