"""
GDPR and compliance data factory for creating test data related to data protection.

This module provides factories for creating GDPR compliance records,
data subject requests, and other privacy-related test data.
"""

import uuid
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Optional, Dict, Any, Union
import random

from backend.db.models import (
    ConsentRecord, DataSubjectRequest, DataBreachLog, DataRetentionPolicy
)


class GDPRDataFactory:
    """Factory for creating GDPR and compliance-related test data."""
    
    CONSENT_TYPES = ["marketing", "analytics", "data_processing", "cookies"]
    REQUEST_TYPES = ["access", "rectification", "erasure", "portability", "restriction"]
    REQUEST_STATUSES = ["pending", "in_progress", "completed", "rejected"]
    BREACH_TYPES = ["unauthorized_access", "data_loss", "system_compromise", "human_error"]
    BREACH_SEVERITIES = ["low", "medium", "high", "critical"]
    
    @staticmethod
    def create_consent_record(
        user_id: Union[str, uuid.UUID],
        consent_type: Optional[str] = None,
        granted: Optional[bool] = None,
        **kwargs
    ) -> ConsentRecord:
        """Create consent record with realistic data."""
        if consent_type is None:
            consent_type = random.choice(GDPRDataFactory.CONSENT_TYPES)
        
        if granted is None:
            granted = random.choice([True, False])
        
        return ConsentRecord(
            user_id=user_id,
            consent_type=consent_type,
            granted=granted,
            granted_at=datetime.now() - timedelta(days=random.randint(0, 365)),
            **kwargs
        )
    
    @staticmethod
    def create_data_subject_request(
        user_id: Union[str, uuid.UUID],
        request_type: Optional[str] = None,
        status: Optional[str] = None,
        description: Optional[str] = None,
        **kwargs
    ) -> DataSubjectRequest:
        """Create data subject request with realistic data."""
        if request_type is None:
            request_type = random.choice(GDPRDataFactory.REQUEST_TYPES)
        
        if status is None:
            status = random.choice(GDPRDataFactory.REQUEST_STATUSES)
        
        if description is None:
            descriptions = {
                "access": "Request for access to personal data",
                "rectification": "Request to correct inaccurate personal data",
                "erasure": "Request to delete personal data",
                "portability": "Request for data portability",
                "restriction": "Request to restrict processing of personal data"
            }
            description = descriptions.get(request_type, "Data subject request")
        
        # Set completion date if status is completed
        completed_at = None
        if status == "completed":
            completed_at = datetime.now() - timedelta(days=random.randint(1, 30))
        
        return DataSubjectRequest(
            user_id=user_id,
            request_type=request_type,
            status=status,
            description=description,
            completed_at=completed_at,
            **kwargs
        )
    
    @staticmethod
    def create_data_breach_log(
        organization_id: Union[str, uuid.UUID],
        breach_type: Optional[str] = None,
        severity: Optional[str] = None,
        description: Optional[str] = None,
        affected_records: Optional[int] = None,
        **kwargs
    ) -> DataBreachLog:
        """Create data breach log with realistic data."""
        if breach_type is None:
            breach_type = random.choice(GDPRDataFactory.BREACH_TYPES)
        
        if severity is None:
            severity = random.choice(GDPRDataFactory.BREACH_SEVERITIES)
        
        if description is None:
            descriptions = {
                "unauthorized_access": "Unauthorized access to customer database",
                "data_loss": "Accidental deletion of customer records",
                "system_compromise": "Security breach in customer data system",
                "human_error": "Employee accidentally exposed customer data"
            }
            description = descriptions.get(breach_type, "Data breach incident")
        
        if affected_records is None:
            # Severity affects number of records
            severity_multipliers = {"low": 10, "medium": 100, "high": 1000, "critical": 10000}
            base_count = severity_multipliers.get(severity, 100)
            affected_records = random.randint(1, base_count)
        
        # Set resolution date for some breaches
        resolved_at = None
        if random.choice([True, False]):
            resolved_at = datetime.now() - timedelta(days=random.randint(1, 90))
        
        return DataBreachLog(
            organization_id=organization_id,
            breach_type=breach_type,
            severity=severity,
            description=description,
            affected_records=affected_records,
            resolved_at=resolved_at,
            **kwargs
        )
    
    @staticmethod
    def create_data_retention_policy(
        organization_id: Union[str, uuid.UUID],
        data_type: Optional[str] = None,
        retention_period_days: Optional[int] = None,
        **kwargs
    ) -> DataRetentionPolicy:
        """Create data retention policy with realistic data."""
        if data_type is None:
            data_types = ["user_data", "review_data", "analytics_data", "conversation_data", "log_data"]
            data_type = random.choice(data_types)
        
        if retention_period_days is None:
            # Different retention periods for different data types
            retention_periods = {
                "user_data": 2555,  # 7 years
                "review_data": 1825,  # 5 years
                "analytics_data": 1095,  # 3 years
                "conversation_data": 365,  # 1 year
                "log_data": 90  # 3 months
            }
            retention_period_days = retention_periods.get(data_type, 365)
        
        return DataRetentionPolicy(
            organization_id=organization_id,
            data_type=data_type,
            retention_period_days=retention_period_days,
            **kwargs
        )
    
    @staticmethod
    def create_consent_batch(
        user_ids: List[Union[str, uuid.UUID]],
        consent_types: Optional[List[str]] = None
    ) -> List[ConsentRecord]:
        """Create consent records for multiple users and consent types."""
        if consent_types is None:
            consent_types = GDPRDataFactory.CONSENT_TYPES
        
        consent_records = []
        
        for user_id in user_ids:
            for consent_type in consent_types:
                consent = GDPRDataFactory.create_consent_record(
                    user_id=user_id,
                    consent_type=consent_type
                )
                consent_records.append(consent)
        
        return consent_records
    
    @staticmethod
    def create_gdpr_compliance_dataset(
        organization_id: Union[str, uuid.UUID],
        user_ids: List[Union[str, uuid.UUID]],
        include_breaches: bool = True,
        include_requests: bool = True
    ) -> Dict[str, Any]:
        """Create comprehensive GDPR compliance dataset."""
        # Create consent records for all users
        consent_records = GDPRDataFactory.create_consent_batch(user_ids)
        
        # Create data retention policies
        retention_policies = []
        for data_type in ["user_data", "review_data", "analytics_data", "conversation_data"]:
            policy = GDPRDataFactory.create_data_retention_policy(
                organization_id=organization_id,
                data_type=data_type
            )
            retention_policies.append(policy)
        
        # Create data subject requests if requested
        data_requests = []
        if include_requests:
            for user_id in user_ids[:3]:  # Only some users make requests
                for _ in range(random.randint(1, 3)):
                    request = GDPRDataFactory.create_data_subject_request(user_id=user_id)
                    data_requests.append(request)
        
        # Create breach logs if requested
        breach_logs = []
        if include_breaches:
            for _ in range(random.randint(0, 3)):  # 0-3 breaches
                breach = GDPRDataFactory.create_data_breach_log(
                    organization_id=organization_id
                )
                breach_logs.append(breach)
        
        return {
            "consent_records": consent_records,
            "retention_policies": retention_policies,
            "data_subject_requests": data_requests,
            "data_breach_logs": breach_logs
        }