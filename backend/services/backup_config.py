"""
Backup configuration management for Local Business Intelligence Bot.

This module provides configuration classes and factory functions
for setting up backup services with proper encryption and storage settings.
"""

import os
from dataclasses import dataclass
from typing import List
from cryptography.fernet import Fernet

from backend.config import get_settings


@dataclass
class BackupStorageConfig:
    """Configuration for backup storage locations."""
    
    # Local storage
    local_backup_dir: str
    
    # Remote storage locations (AWS S3, Google Cloud Storage, etc.)
    remote_locations: List[str]
    
    # Storage limits
    max_local_storage_gb: int = 50
    max_remote_storage_gb: int = 500


@dataclass
class BackupRetentionConfig:
    """Configuration for backup retention policies."""
    
    # Retention periods
    daily_retention_days: int = 30
    weekly_retention_weeks: int = 12
    monthly_retention_months: int = 12
    
    # Cleanup settings
    auto_cleanup_enabled: bool = True
    cleanup_check_interval_hours: int = 24


@dataclass
class BackupSecurityConfig:
    """Configuration for backup security and encryption."""
    
    # Encryption
    encryption_key: str
    encryption_algorithm: str = "Fernet"
    
    # Compression
    compression_enabled: bool = True
    compression_level: int = 6  # 1-9, higher = better compression but slower
    
    # Integrity checking
    checksum_algorithm: str = "SHA-256"
    verify_after_backup: bool = True


@dataclass
class BackupPerformanceConfig:
    """Configuration for backup performance settings."""
    
    # Timeouts
    backup_timeout_minutes: int = 60
    upload_timeout_minutes: int = 120
    
    # Concurrency
    max_concurrent_uploads: int = 3
    chunk_size_mb: int = 10
    
    # Resource limits
    max_backup_size_mb: int = 1000
    max_memory_usage_mb: int = 500


@dataclass
class BackupMonitoringConfig:
    """Configuration for backup monitoring and alerting."""
    
    # Health checks
    health_check_interval_minutes: int = 60
    max_consecutive_failures: int = 3
    
    # Alerting
    alert_on_failure: bool = True
    alert_on_size_threshold: bool = True
    size_threshold_mb: int = 800
    
    # Metrics
    collect_metrics: bool = True
    metrics_retention_days: int = 90


class BackupConfigFactory:
    """Factory for creating backup configurations."""
    
    @staticmethod
    def create_default_config() -> dict:
        """Create default backup configuration.
        
        Returns:
            dict: Complete backup configuration
        """
        settings = get_settings()
        
        # Generate or load encryption key
        encryption_key = BackupConfigFactory._get_or_create_encryption_key()
        
        # Determine backup directory
        backup_dir = os.path.join(os.getcwd(), "backups")
        
        # Remote storage locations (would be configured per deployment)
        remote_locations = [
            # "s3://my-backup-bucket/businessbot/",
            # "gs://my-backup-bucket/businessbot/",
        ]
        
        return {
            "storage": BackupStorageConfig(
                local_backup_dir=backup_dir,
                remote_locations=remote_locations,
                max_local_storage_gb=50,
                max_remote_storage_gb=500
            ),
            "retention": BackupRetentionConfig(
                daily_retention_days=30,
                weekly_retention_weeks=12,
                monthly_retention_months=12,
                auto_cleanup_enabled=True,
                cleanup_check_interval_hours=24
            ),
            "security": BackupSecurityConfig(
                encryption_key=encryption_key,
                encryption_algorithm="Fernet",
                compression_enabled=True,
                compression_level=6,
                checksum_algorithm="SHA-256",
                verify_after_backup=True
            ),
            "performance": BackupPerformanceConfig(
                backup_timeout_minutes=60,
                upload_timeout_minutes=120,
                max_concurrent_uploads=3,
                chunk_size_mb=10,
                max_backup_size_mb=1000,
                max_memory_usage_mb=500
            ),
            "monitoring": BackupMonitoringConfig(
                health_check_interval_minutes=60,
                max_consecutive_failures=3,
                alert_on_failure=True,
                alert_on_size_threshold=True,
                size_threshold_mb=800,
                collect_metrics=True,
                metrics_retention_days=90
            )
        }
    
    @staticmethod
    def create_production_config() -> dict:
        """Create production-optimized backup configuration.
        
        Returns:
            dict: Production backup configuration
        """
        config = BackupConfigFactory.create_default_config()
        
        # Production-specific overrides
        config["storage"].max_local_storage_gb = 100
        config["storage"].max_remote_storage_gb = 1000
        
        config["retention"].daily_retention_days = 30
        config["retention"].weekly_retention_weeks = 12
        config["retention"].monthly_retention_months = 24  # Keep monthly backups longer
        
        config["performance"].backup_timeout_minutes = 120
        config["performance"].max_concurrent_uploads = 5
        config["performance"].max_backup_size_mb = 5000
        
        config["monitoring"].health_check_interval_minutes = 30
        config["monitoring"].max_consecutive_failures = 2
        
        return config
    
    @staticmethod
    def create_development_config() -> dict:
        """Create development-friendly backup configuration.
        
        Returns:
            dict: Development backup configuration
        """
        config = BackupConfigFactory.create_default_config()
        
        # Development-specific overrides
        config["storage"].max_local_storage_gb = 10
        config["storage"].remote_locations = []  # No remote storage in dev
        
        config["retention"].daily_retention_days = 7
        config["retention"].weekly_retention_weeks = 4
        config["retention"].monthly_retention_months = 3
        
        config["performance"].backup_timeout_minutes = 30
        config["performance"].max_backup_size_mb = 100
        
        config["monitoring"].health_check_interval_minutes = 120
        config["monitoring"].alert_on_failure = False  # No alerts in dev
        
        return config
    
    @staticmethod
    def _get_or_create_encryption_key() -> str:
        """Get existing encryption key or create a new one.
        
        Returns:
            str: Base64-encoded encryption key
        """
        key_file = os.path.join(os.getcwd(), ".backup_key")
        
        try:
            # Try to load existing key
            if os.path.exists(key_file):
                with open(key_file, 'rb') as f:
                    return f.read().decode()
            
            # Create new key
            key = Fernet.generate_key()
            
            # Save key to file (in production, use secure key management)
            with open(key_file, 'wb') as f:
                f.write(key)
            
            # Set restrictive permissions
            os.chmod(key_file, 0o600)
            
            return key.decode()
            
        except Exception as e:
            # Fallback to environment variable or default
            return os.getenv("BACKUP_ENCRYPTION_KEY", Fernet.generate_key().decode())
    
    @staticmethod
    def validate_config(config: dict) -> List[str]:
        """Validate backup configuration.
        
        Args:
            config: Backup configuration dictionary
            
        Returns:
            List[str]: List of validation errors (empty if valid)
        """
        errors = []
        
        try:
            # Validate storage config
            storage = config.get("storage")
            if not storage:
                errors.append("Missing storage configuration")
            else:
                if not storage.local_backup_dir:
                    errors.append("Local backup directory not specified")
                
                if storage.max_local_storage_gb <= 0:
                    errors.append("Invalid local storage limit")
            
            # Validate security config
            security = config.get("security")
            if not security:
                errors.append("Missing security configuration")
            else:
                if not security.encryption_key:
                    errors.append("Encryption key not specified")
                
                try:
                    # Test encryption key validity
                    Fernet(security.encryption_key.encode())
                except Exception:
                    errors.append("Invalid encryption key format")
            
            # Validate retention config
            retention = config.get("retention")
            if not retention:
                errors.append("Missing retention configuration")
            else:
                if retention.daily_retention_days <= 0:
                    errors.append("Invalid daily retention period")
                
                if retention.weekly_retention_weeks <= 0:
                    errors.append("Invalid weekly retention period")
                
                if retention.monthly_retention_months <= 0:
                    errors.append("Invalid monthly retention period")
            
            # Validate performance config
            performance = config.get("performance")
            if not performance:
                errors.append("Missing performance configuration")
            else:
                if performance.backup_timeout_minutes <= 0:
                    errors.append("Invalid backup timeout")
                
                if performance.max_backup_size_mb <= 0:
                    errors.append("Invalid maximum backup size")
            
        except Exception as e:
            errors.append(f"Configuration validation error: {e}")
        
        return errors


def get_backup_config() -> dict:
    """Get backup configuration based on environment.
    
    Returns:
        dict: Backup configuration
    """
    settings = get_settings()
    
    if settings.environment == "production":
        return BackupConfigFactory.create_production_config()
    elif settings.environment == "development":
        return BackupConfigFactory.create_development_config()
    else:
        return BackupConfigFactory.create_default_config()


def validate_backup_environment() -> List[str]:
    """Validate that the environment is properly configured for backups.
    
    Returns:
        List[str]: List of environment issues (empty if valid)
    """
    issues = []
    
    try:
        # Check backup directory permissions
        config = get_backup_config()
        backup_dir = config["storage"].local_backup_dir
        
        if not os.path.exists(backup_dir):
            try:
                os.makedirs(backup_dir, exist_ok=True)
            except Exception as e:
                issues.append(f"Cannot create backup directory: {e}")
        
        # Check write permissions
        if os.path.exists(backup_dir):
            if not os.access(backup_dir, os.W_OK):
                issues.append("No write permission to backup directory")
        
        # Check available disk space
        try:
            import shutil
            total, used, free = shutil.disk_usage(backup_dir)
            free_gb = free / (1024**3)
            required_gb = config["storage"].max_local_storage_gb
            
            if free_gb < required_gb:
                issues.append(
                    f"Insufficient disk space: {free_gb:.1f}GB available, "
                    f"{required_gb}GB required"
                )
        except Exception as e:
            issues.append(f"Cannot check disk space: {e}")
        
        # Validate encryption key
        try:
            key = config["security"].encryption_key
            Fernet(key.encode())
        except Exception as e:
            issues.append(f"Invalid encryption key: {e}")
        
    except Exception as e:
        issues.append(f"Environment validation error: {e}")
    
    return issues