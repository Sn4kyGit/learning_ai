"""
Backup and recovery API endpoints for Local Business Intelligence Bot.

This module provides REST API endpoints for backup management,
recovery operations, and system monitoring.
"""

from datetime import datetime
from typing import Dict, List, Optional
import logging

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.database import get_db_session
from backend.services.auth_dependencies import get_current_user, require_role
from backend.services.backup_service import (
    BackupService, 
    BackupType, 
    BackupStatus, 
    BackupMetadata,
    BackupException
)
from backend.services.backup_config import get_backup_config, validate_backup_environment
from backend.db.schemas import UserResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/backup", tags=["backup"])


# Pydantic models for API requests/responses

class BackupCreateRequest(BaseModel):
    """Request model for creating backups."""
    backup_type: BackupType = Field(default=BackupType.DAILY, description="Type of backup to create")
    force: bool = Field(default=False, description="Force backup even if recent backup exists")


class BackupMetadataResponse(BaseModel):
    """Response model for backup metadata."""
    backup_id: str
    backup_type: BackupType
    created_at: datetime
    file_size: int
    checksum: str
    encrypted: bool
    compression_ratio: float
    status: BackupStatus
    error_message: Optional[str] = None


class BackupListResponse(BaseModel):
    """Response model for backup list."""
    backups: List[BackupMetadataResponse]
    total_count: int
    total_size_mb: float


class BackupStatusResponse(BaseModel):
    """Response model for backup system status."""
    total_backups: int
    recent_backups: int
    failed_backups: int
    total_backup_size_mb: float
    last_backup: Optional[str]
    backup_directory: str
    encryption_enabled: bool
    compression_enabled: bool


class RestoreRequest(BaseModel):
    """Request model for database restoration."""
    backup_id: str = Field(description="ID of backup to restore from")
    target_database_url: Optional[str] = Field(default=None, description="Target database URL (optional)")
    confirm: bool = Field(description="Confirmation flag for destructive operation")


class RestoreResponse(BaseModel):
    """Response model for restoration operations."""
    success: bool
    backup_id: str
    restored_at: datetime
    message: str


class BackupConfigResponse(BaseModel):
    """Response model for backup configuration."""
    local_backup_dir: str
    retention_days_daily: int
    retention_weeks_weekly: int
    retention_months_monthly: int
    encryption_enabled: bool
    compression_enabled: bool
    max_backup_size_mb: int


class BackupHealthResponse(BaseModel):
    """Response model for backup system health check."""
    healthy: bool
    issues: List[str]
    last_check: datetime


# Global backup service instance (would be dependency injected in production)
_backup_service: Optional[BackupService] = None


def get_backup_service() -> BackupService:
    """Get or create backup service instance."""
    global _backup_service
    
    if _backup_service is None:
        from backend.services.backup_service import BackupConfig
        from backend.services.notification.alert_service import AlertService
        
        config_dict = get_backup_config()
        
        # Convert config dict to BackupConfig dataclass
        backup_config = BackupConfig(
            local_backup_dir=config_dict["storage"].local_backup_dir,
            remote_backup_locations=config_dict["storage"].remote_locations,
            encryption_key=config_dict["security"].encryption_key,
            retention_days_daily=config_dict["retention"].daily_retention_days,
            retention_weeks_weekly=config_dict["retention"].weekly_retention_weeks,
            retention_months_monthly=config_dict["retention"].monthly_retention_months,
            compression_enabled=config_dict["security"].compression_enabled,
            max_backup_size_mb=config_dict["performance"].max_backup_size_mb,
            backup_timeout_minutes=config_dict["performance"].backup_timeout_minutes
        )
        
        # Initialize alert service (optional)
        alert_service = None  # Would be injected in production
        
        _backup_service = BackupService(backup_config, alert_service)
    
    return _backup_service


@router.post("/create", response_model=BackupMetadataResponse)
async def create_backup(
    request: BackupCreateRequest,
    background_tasks: BackgroundTasks,
    current_user: UserResponse = Depends(require_role("super_admin")),
    backup_service: BackupService = Depends(get_backup_service)
):
    """Create a new database backup.
    
    This endpoint creates a backup of the entire database with encryption
    and compression. Only super-admin users can create backups.
    """
    try:
        logger.info(f"Creating {request.backup_type.value} backup requested by user {current_user.id}")
        
        # Create backup based on type
        if request.backup_type == BackupType.DAILY:
            metadata = await backup_service.create_daily_backup()
        elif request.backup_type == BackupType.WEEKLY:
            metadata = await backup_service.create_weekly_backup()
        elif request.backup_type == BackupType.MONTHLY:
            metadata = await backup_service.create_monthly_backup()
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported backup type: {request.backup_type}"
            )
        
        return BackupMetadataResponse(
            backup_id=metadata.backup_id,
            backup_type=metadata.backup_type,
            created_at=metadata.created_at,
            file_size=metadata.file_size,
            checksum=metadata.checksum,
            encrypted=metadata.encrypted,
            compression_ratio=metadata.compression_ratio,
            status=metadata.status,
            error_message=metadata.error_message
        )
        
    except BackupException as e:
        logger.error(f"Backup creation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Backup creation failed: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Unexpected error during backup creation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during backup creation"
        )


@router.get("/list", response_model=BackupListResponse)
async def list_backups(
    backup_type: Optional[BackupType] = None,
    limit: int = 50,
    offset: int = 0,
    current_user: UserResponse = Depends(require_role("super_admin")),
    backup_service: BackupService = Depends(get_backup_service)
):
    """List available backups with optional filtering.
    
    Returns a list of all available backups with metadata.
    Only super-admin users can access backup information.
    """
    try:
        # Get backup status (includes backup list)
        status_info = await backup_service.get_backup_status()
        
        # In a real implementation, this would filter and paginate properly
        # For now, return basic status information
        return BackupListResponse(
            backups=[],  # Would be populated with actual backup metadata
            total_count=status_info.get("total_backups", 0),
            total_size_mb=status_info.get("total_backup_size_mb", 0.0)
        )
        
    except Exception as e:
        logger.error(f"Failed to list backups: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve backup list"
        )


@router.get("/status", response_model=BackupStatusResponse)
async def get_backup_status(
    current_user: UserResponse = Depends(require_role("super_admin")),
    backup_service: BackupService = Depends(get_backup_service)
):
    """Get backup system status and statistics.
    
    Returns comprehensive information about the backup system including
    recent backups, failures, and storage usage.
    """
    try:
        status_info = await backup_service.get_backup_status()
        
        return BackupStatusResponse(
            total_backups=status_info.get("total_backups", 0),
            recent_backups=status_info.get("recent_backups", 0),
            failed_backups=status_info.get("failed_backups", 0),
            total_backup_size_mb=status_info.get("total_backup_size_mb", 0.0),
            last_backup=status_info.get("last_backup"),
            backup_directory=status_info.get("backup_directory", ""),
            encryption_enabled=status_info.get("encryption_enabled", False),
            compression_enabled=status_info.get("compression_enabled", False)
        )
        
    except Exception as e:
        logger.error(f"Failed to get backup status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve backup status"
        )


@router.post("/restore", response_model=RestoreResponse)
async def restore_database(
    request: RestoreRequest,
    current_user: UserResponse = Depends(require_role("super_admin")),
    backup_service: BackupService = Depends(get_backup_service)
):
    """Restore database from a backup.
    
    This is a destructive operation that replaces the current database
    with data from the specified backup. Requires explicit confirmation.
    """
    try:
        if not request.confirm:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Database restoration requires explicit confirmation"
            )
        
        logger.warning(
            f"Database restoration initiated by user {current_user.id} "
            f"from backup {request.backup_id}"
        )
        
        # Perform restoration
        success = await backup_service.restore_from_backup(
            request.backup_id,
            request.target_database_url
        )
        
        if success:
            message = f"Database successfully restored from backup {request.backup_id}"
            logger.info(message)
        else:
            message = f"Database restoration failed for backup {request.backup_id}"
            logger.error(message)
        
        return RestoreResponse(
            success=success,
            backup_id=request.backup_id,
            restored_at=datetime.now(),
            message=message
        )
        
    except BackupException as e:
        logger.error(f"Database restoration failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database restoration failed: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Unexpected error during database restoration: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during database restoration"
        )


@router.post("/verify/{backup_id}")
async def verify_backup(
    backup_id: str,
    current_user: UserResponse = Depends(require_role("super_admin")),
    backup_service: BackupService = Depends(get_backup_service)
):
    """Verify the integrity of a backup file.
    
    Checks that the backup file exists, is not corrupted, and can be decrypted.
    """
    try:
        is_valid = await backup_service.verify_backup_integrity(backup_id)
        
        return {
            "backup_id": backup_id,
            "valid": is_valid,
            "verified_at": datetime.now(),
            "message": "Backup integrity verified" if is_valid else "Backup integrity check failed"
        }
        
    except Exception as e:
        logger.error(f"Backup verification failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Backup verification failed: {str(e)}"
        )


@router.post("/cleanup")
async def cleanup_old_backups(
    current_user: UserResponse = Depends(require_role("super_admin")),
    backup_service: BackupService = Depends(get_backup_service)
):
    """Clean up old backups according to retention policy.
    
    Removes backups that exceed the configured retention periods.
    """
    try:
        cleanup_counts = await backup_service.cleanup_old_backups()
        
        return {
            "cleanup_completed": True,
            "cleaned_up": cleanup_counts,
            "cleaned_at": datetime.now(),
            "message": f"Cleaned up {sum(cleanup_counts.values())} old backups"
        }
        
    except Exception as e:
        logger.error(f"Backup cleanup failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Backup cleanup failed: {str(e)}"
        )


@router.get("/config", response_model=BackupConfigResponse)
async def get_backup_configuration(
    current_user: UserResponse = Depends(require_role("super_admin"))
):
    """Get current backup configuration.
    
    Returns the current backup system configuration including
    retention policies and storage settings.
    """
    try:
        config = get_backup_config()
        
        return BackupConfigResponse(
            local_backup_dir=config["storage"].local_backup_dir,
            retention_days_daily=config["retention"].daily_retention_days,
            retention_weeks_weekly=config["retention"].weekly_retention_weeks,
            retention_months_monthly=config["retention"].monthly_retention_months,
            encryption_enabled=True,  # Always enabled
            compression_enabled=config["security"].compression_enabled,
            max_backup_size_mb=config["performance"].max_backup_size_mb
        )
        
    except Exception as e:
        logger.error(f"Failed to get backup configuration: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve backup configuration"
        )


@router.get("/health", response_model=BackupHealthResponse)
async def check_backup_health(
    current_user: UserResponse = Depends(require_role("super_admin"))
):
    """Check backup system health.
    
    Validates that the backup system is properly configured and operational.
    """
    try:
        issues = validate_backup_environment()
        
        return BackupHealthResponse(
            healthy=len(issues) == 0,
            issues=issues,
            last_check=datetime.now()
        )
        
    except Exception as e:
        logger.error(f"Backup health check failed: {e}")
        return BackupHealthResponse(
            healthy=False,
            issues=[f"Health check failed: {str(e)}"],
            last_check=datetime.now()
        )