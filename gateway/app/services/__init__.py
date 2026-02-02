"""
Services Aegis Gateway
"""
from .odoo_service import OdooService, get_odoo_service
from .midpoint_service import MidPointService, get_midpoint_service
from .sync_service import SyncService, get_sync_service

__all__ = [
    "OdooService", "get_odoo_service",
    "MidPointService", "get_midpoint_service",
    "SyncService", "get_sync_service"
]
