"""
Modèles Pydantic pour les requêtes de provisioning et workflows
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID
from enum import Enum


class RequestType(str, Enum):
    """Types de demandes de provisioning"""
    CREATE_USER = "create_user"
    UPDATE_USER = "update_user"
    DELETE_USER = "delete_user"
    ASSIGN_ROLE = "assign_role"
    REVOKE_ROLE = "revoke_role"
    ASSIGN_PERMISSION = "assign_permission"
    REVOKE_PERMISSION = "revoke_permission"


class RequestStatus(str, Enum):
    """Statuts des demandes"""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    FAILED = "failed"


class ApprovalLevel(str, Enum):
    """Niveaux d'approbation"""
    NONE = "none"  # Pas d'approbation nécessaire
    MANAGER = "manager"  # Approbation par le manager
    DEPT_HEAD = "dept_head"  # Approbation par le chef de département
    APP_OWNER = "app_owner"  # Approbation par le responsable applicatif
    SECURITY = "security"  # Approbation par la sécurité


class PreProvisionRequest(BaseModel):
    """Requête de pré-provisioning (avant création du compte)"""
    request_type: RequestType
    target_user_login: str
    target_user_email: Optional[str] = None
    target_user_data: Dict[str, Any] = Field(default_factory=dict)
    requested_roles: List[str] = Field(default_factory=list)
    requested_permissions: List[str] = Field(default_factory=list)
    requester_login: Optional[str] = None
    requester_name: Optional[str] = None
    justification: Optional[str] = None
    target_system: str = "midpoint"  # midpoint, ldap, odoo
    midpoint_oid: Optional[str] = None
    requires_approval: bool = False
    approval_levels: List[ApprovalLevel] = Field(default_factory=list)


class PostProvisionRequest(BaseModel):
    """Requête de post-provisioning (après création du compte)"""
    request_type: RequestType
    target_user_login: str
    target_user_id: Optional[str] = None
    provisioned_systems: List[str] = Field(default_factory=list)
    provisioned_roles: List[str] = Field(default_factory=list)
    provisioned_at: datetime = Field(default_factory=datetime.utcnow)
    midpoint_oid: Optional[str] = None
    requires_review: bool = False


class ApprovalStep(BaseModel):
    """Étape d'approbation dans un workflow"""
    step_order: int
    approver_type: ApprovalLevel
    approver_login: Optional[str] = None
    approver_email: Optional[str] = None
    status: RequestStatus = RequestStatus.PENDING
    decision_at: Optional[datetime] = None
    comment: Optional[str] = None


class ProvisioningRequestResponse(BaseModel):
    """Réponse pour une demande de provisioning"""
    request_id: UUID
    request_type: RequestType
    status: RequestStatus
    target_user_login: str
    approval_steps: List[ApprovalStep] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None
    n8n_workflow_id: Optional[str] = None
    message: Optional[str] = None


class WorkflowTriggerResponse(BaseModel):
    """Réponse après déclenchement d'un workflow N8N"""
    success: bool
    workflow_id: Optional[str] = None
    execution_id: Optional[str] = None
    message: str
    data: Optional[Dict[str, Any]] = None


class ApprovalDecision(BaseModel):
    """Décision d'approbation"""
    request_id: UUID
    step_order: int
    decision: RequestStatus  # approved ou rejected
    approver_login: str
    comment: Optional[str] = None


# === Modèles pour le Chatbot ===

class ChatMessage(BaseModel):
    """Message du chatbot"""
    role: str  # "user" ou "assistant"
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ChatRequest(BaseModel):
    """Requête au chatbot IAM"""
    message: str
    user_context: Optional[Dict[str, Any]] = None
    conversation_history: List[ChatMessage] = Field(default_factory=list)
    session_id: Optional[str] = None


class ChatAction(BaseModel):
    """Action extraite par le chatbot"""
    action_type: str  # search_user, assign_role, remove_role, assign_permission, etc.
    target_type: str  # user, group, department
    target_identifier: Optional[str] = None
    target_filters: Optional[Dict[str, Any]] = None
    role_or_permission: Optional[str] = None
    requires_approval: bool = False
    confidence: float = 0.0


class ChatResponse(BaseModel):
    """Réponse du chatbot IAM"""
    response: str
    actions_taken: List[ChatAction] = Field(default_factory=list)
    requires_confirmation: bool = False
    pending_workflow_id: Optional[str] = None
    session_id: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)








