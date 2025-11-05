"""
GDPR compliance API endpoints.

This module provides REST API endpoints for GDPR compliance features including
consent management, data subject rights, privacy notices, and data breach reporting.
"""

from typing import List, Optional
from uuid import UUID
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.database import get_db_session
from backend.db.schemas import (
    ConsentRecordCreate,
    ConsentRecordResponse,
    DataSubjectRequestCreate,
    DataSubjectRequestResponse,
    DataBreachLogCreate,
    DataBreachLogResponse,
    PrivacyNoticeResponse,
    DataMinimizationReport,
    DataCleanupReport,
    DataRetentionPolicyCreate,
    DataRetentionPolicyResponse,
)
from backend.services.gdpr_compliance_service import (
    GDPRComplianceService,
    ConsentType,
    DataSubjectRightType,
    DataBreachSeverity,
)
from backend.services.auth_dependencies import get_current_user
from backend.db.models import User

router = APIRouter(prefix="/api/gdpr", tags=["GDPR Compliance"])


@router.post("/consent", response_model=dict)
async def record_consent(
    consent_data: ConsentRecordCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Record user consent for data processing activities.
    
    This endpoint allows users to grant or withdraw consent for various
    data processing activities as required by GDPR Article 7.
    """
    service = GDPRComplianceService(db)
    
    consent_record = await service.record_consent(
        user_id=current_user.id,
        consent_type=ConsentType(consent_data.consent_type),
        granted=consent_data.granted,
        purpose=consent_data.purpose,
        legal_basis=consent_data.legal_basis,
        ip_address=consent_data.ip_address,
        user_agent=consent_data.user_agent,
    )
    
    return consent_record


@router.get("/consent", response_model=List[dict])
async def get_user_consents(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Get all consent records for the current user.
    
    This endpoint allows users to view their consent history
    as required by GDPR transparency obligations.
    """
    service = GDPRComplianceService(db)
    consents = await service.get_user_consents(current_user.id)
    return consents


@router.post("/data-subject-request", response_model=dict)
async def create_data_subject_request(
    request_data: DataSubjectRequestCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Create a data subject rights request.
    
    This endpoint allows users to exercise their GDPR rights including:
    - Right to access (Article 15)
    - Right to rectification (Article 16)
    - Right to erasure/be forgotten (Article 17)
    - Right to data portability (Article 20)
    - Right to restrict processing (Article 18)
    - Right to object (Article 21)
    """
    service = GDPRComplianceService(db)
    
    result = await service.process_data_subject_request(
        user_id=current_user.id,
        request_type=DataSubjectRightType(request_data.request_type),
        details=request_data.request_details,
    )
    
    return result


@router.get("/privacy-notice", response_model=PrivacyNoticeResponse)
async def get_privacy_notice(
    language: str = Query(default="en", regex="^(en|de|tr|ar)$"),
    db: AsyncSession = Depends(get_db_session),
):
    """Get the privacy notice for GDPR compliance.
    
    This endpoint provides the privacy notice as required by
    GDPR Article 13 (information to be provided when personal
    data are collected from the data subject).
    """
    service = GDPRComplianceService(db)
    privacy_notice = await service.get_privacy_notice(language)
    return PrivacyNoticeResponse(**privacy_notice)


@router.post("/data-breach", response_model=dict)
async def log_data_breach(
    breach_data: DataBreachLogCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Log a data breach incident.
    
    This endpoint is for system administrators to log data breaches
    as required by GDPR Article 33 (notification of a personal data
    breach to the supervisory authority).
    
    Requires super_admin role.
    """
    if current_user.role != "super_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only super administrators can log data breaches"
        )
    
    service = GDPRComplianceService(db)
    
    breach_record = await service.log_data_breach(
        severity=DataBreachSeverity(breach_data.severity),
        description=breach_data.description,
        affected_data_types=breach_data.affected_data_types,
        affected_users_count=breach_data.affected_users_count,
        discovered_at=breach_data.discovered_at,
        contained_at=breach_data.contained_at,
        root_cause=breach_data.root_cause,
        mitigation_steps=breach_data.mitigation_steps,
    )
    
    return breach_record


@router.get("/data-minimization/{business_id}", response_model=DataMinimizationReport)
async def validate_data_minimization(
    business_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Validate data minimization compliance for a business.
    
    This endpoint checks that data collection and retention
    follows GDPR data minimization principles (Article 5(1)(c)).
    
    Requires admin or super_admin role.
    """
    if current_user.role not in ["admin", "super_admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to validate data minimization"
        )
    
    service = GDPRComplianceService(db)
    validation_result = await service.validate_data_minimization(business_id)
    
    return DataMinimizationReport(**validation_result)


@router.post("/cleanup-expired-data", response_model=DataCleanupReport)
async def cleanup_expired_data(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Clean up expired data according to retention policies.
    
    This endpoint triggers cleanup of data that has exceeded
    its retention period as required by GDPR storage limitation
    principle (Article 5(1)(e)).
    
    Requires super_admin role.
    """
    if current_user.role != "super_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only super administrators can trigger data cleanup"
        )
    
    service = GDPRComplianceService(db)
    cleanup_stats = await service.cleanup_expired_data()
    
    return DataCleanupReport(
        conversations_deleted=cleanup_stats["conversations_deleted"],
        messages_deleted=cleanup_stats["messages_deleted"],
        old_analytics_deleted=cleanup_stats["old_analytics_deleted"],
        cleanup_completed_at=datetime.utcnow(),
    )


@router.get("/my-data", response_model=dict)
async def get_my_data(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Get all data associated with the current user.
    
    This endpoint provides users with access to all their personal
    data as required by GDPR Right to Access (Article 15).
    """
    service = GDPRComplianceService(db)
    
    user_data = await service.process_data_subject_request(
        user_id=current_user.id,
        request_type=DataSubjectRightType.ACCESS,
    )
    
    return user_data


@router.delete("/delete-my-data", response_model=dict)
async def delete_my_data(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Delete all data associated with the current user.
    
    This endpoint allows users to exercise their Right to Erasure
    (Right to be Forgotten) as required by GDPR Article 17.
    
    WARNING: This action is irreversible and will delete all user data.
    """
    service = GDPRComplianceService(db)
    
    deletion_result = await service.process_data_subject_request(
        user_id=current_user.id,
        request_type=DataSubjectRightType.ERASURE,
    )
    
    return deletion_result


@router.get("/export-my-data", response_model=dict)
async def export_my_data(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Export all data associated with the current user.
    
    This endpoint allows users to exercise their Right to Data
    Portability as required by GDPR Article 20.
    """
    service = GDPRComplianceService(db)
    
    export_data = await service.process_data_subject_request(
        user_id=current_user.id,
        request_type=DataSubjectRightType.PORTABILITY,
    )
    
    return export_data