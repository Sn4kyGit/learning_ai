"""
Unit tests for backup service functionality.

Tests backup creation, encryption, compression, recovery procedures,
and retention policy enforcement.
"""

import asyncio
import os
import tempfile
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock
import pytest
from cryptography.fernet import Fernet

from backend.services.backup_service import (
    BackupService,
    BackupConfig,
    BackupType,
    BackupStatus,
    BackupMetadata,
    BackupException,
    BackupScheduler
)


class TestBackupService:
    """Test suite for BackupService class."""

    @pytest.fixture
    def temp_backup_dir(self):
        """Create temporary directory for backup tests."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)

    @pytest.fixture
    def backup_config(self, temp_backup_dir):
        """Create test backup configuration."""
        encryption_key = Fernet.generate_key().decode()
        
        return BackupConfig(
            local_backup_dir=temp_backup_dir,
            remote_backup_locations=[],
            encryption_key=encryption_key,
            retention_days_daily=7,
            retention_weeks_weekly=4,
            retention_months_monthly=3,
            compression_enabled=True,
            max_backup_size_mb=100,
            backup_timeout_minutes=30
        )

    @pytest.fixture
    def backup_service(self, backup_config):
        """Create BackupService instance for testing."""
        return BackupService(backup_config)

    @pytest.fixture
    def sample_backup_metadata(self, temp_backup_dir):
        """Create sample backup metadata for testing."""
        return BackupMetadata(
            backup_id="test_backup_20231201_120000",
            backup_type=BackupType.DAILY,
            created_at=datetime.now(),
            file_path=os.path.join(temp_backup_dir, "test_backup.sql.gz.enc"),
            file_size=1024,
            checksum="abc123def456",
            encrypted=True,
            compression_ratio=0.7,
            status=BackupStatus.COMPLETED
        )

    async def test_backup_service_initialization(self, backup_config):
        """Test backup service initialization."""
        service = BackupService(backup_config)
        
        assert service.config == backup_config
        assert service._backup_history == []
        assert os.path.exists(backup_config.local_backup_dir)

    @patch('backend.services.backup_service.get_db_session_context')
    async def test_create_daily_backup_success(self, mock_db_context, backup_service, temp_backup_dir):
        """Test successful daily backup creation."""
        # Mock database session
        mock_session = AsyncMock()
        mock_db_context.return_value.__aenter__.return_value = mock_session
        
        # Mock database query results
        mock_result = Mock()
        mock_result.fetchall.return_value = []
        mock_result.keys.return_value = []
        mock_session.execute.return_value = mock_result
        
        # Create a test database file to backup
        test_db_path = os.path.join(temp_backup_dir, "test.db")
        with open(test_db_path, 'w') as f:
            f.write("test database content")
        
        with patch('backend.config.get_settings') as mock_settings:
            mock_settings.return_value.database_url = f"sqlite+aiosqlite:///{test_db_path}"
            
            metadata = await backup_service.create_daily_backup()
            
            assert metadata.backup_type == BackupType.DAILY
            assert metadata.status == BackupStatus.COMPLETED
            assert metadata.encrypted is True
            assert metadata.file_size > 0
            assert metadata.checksum != ""
            assert os.path.exists(metadata.file_path)

    async def test_backup_encryption_decryption(self, backup_service, temp_backup_dir):
        """Test backup encryption and decryption."""
        # Create test file
        test_file = os.path.join(temp_backup_dir, "test_data.txt")
        test_content = "This is test backup data"
        
        with open(test_file, 'w') as f:
            f.write(test_content)
        
        # Encrypt the file
        encrypted_file = await backup_service._encrypt_backup(test_file)
        
        assert encrypted_file.endswith('.enc')
        assert os.path.exists(encrypted_file)
        assert os.path.getsize(encrypted_file) > 0
        
        # Decrypt the file
        decrypted_file = await backup_service._decrypt_backup(encrypted_file)
        
        assert os.path.exists(decrypted_file)
        
        with open(decrypted_file, 'r') as f:
            decrypted_content = f.read()
        
        assert decrypted_content == test_content

    async def test_backup_compression_decompression(self, backup_service, temp_backup_dir):
        """Test backup compression and decompression."""
        # Create test file with compressible content
        test_file = os.path.join(temp_backup_dir, "test_data.txt")
        test_content = "A" * 1000  # Highly compressible content
        
        with open(test_file, 'w') as f:
            f.write(test_content)
        
        original_size = os.path.getsize(test_file)
        
        # Compress the file
        compressed_file = await backup_service._compress_backup(test_file)
        
        assert compressed_file.endswith('.gz')
        assert os.path.exists(compressed_file)
        
        compressed_size = os.path.getsize(compressed_file)
        assert compressed_size < original_size  # Should be smaller
        
        # Decompress the file
        decompressed_file = await backup_service._decompress_backup(compressed_file)
        
        assert os.path.exists(decompressed_file)
        
        with open(decompressed_file, 'r') as f:
            decompressed_content = f.read()
        
        assert decompressed_content == test_content

    async def test_checksum_calculation(self, backup_service, temp_backup_dir):
        """Test checksum calculation for backup files."""
        # Create test file
        test_file = os.path.join(temp_backup_dir, "test_data.txt")
        test_content = "Test content for checksum"
        
        with open(test_file, 'w') as f:
            f.write(test_content)
        
        # Calculate checksum
        checksum1 = await backup_service._calculate_checksum(test_file)
        checksum2 = await backup_service._calculate_checksum(test_file)
        
        assert checksum1 == checksum2  # Should be consistent
        assert len(checksum1) == 64  # SHA-256 hex length
        
        # Modify file and verify checksum changes
        with open(test_file, 'a') as f:
            f.write(" modified")
        
        checksum3 = await backup_service._calculate_checksum(test_file)
        assert checksum3 != checksum1

    async def test_backup_integrity_verification(self, backup_service, sample_backup_metadata, temp_backup_dir):
        """Test backup integrity verification."""
        # Create a test backup file
        test_content = "Test backup content"
        
        # Create unencrypted file first
        temp_file = os.path.join(temp_backup_dir, "temp_backup.txt")
        with open(temp_file, 'w') as f:
            f.write(test_content)
        
        # Encrypt it
        encrypted_file = await backup_service._encrypt_backup(temp_file)
        
        # Update metadata with correct path and checksum
        sample_backup_metadata.file_path = encrypted_file
        sample_backup_metadata.checksum = await backup_service._calculate_checksum(encrypted_file)
        
        # Add to backup history
        backup_service._backup_history.append(sample_backup_metadata)
        
        # Verify integrity
        is_valid = await backup_service.verify_backup_integrity(sample_backup_metadata.backup_id)
        assert is_valid is True
        
        # Corrupt the file and verify it fails
        with open(encrypted_file, 'ab') as f:
            f.write(b"corrupted data")
        
        is_valid = await backup_service.verify_backup_integrity(sample_backup_metadata.backup_id)
        assert is_valid is False

    async def test_cleanup_old_backups(self, backup_service, temp_backup_dir):
        """Test cleanup of old backups according to retention policy."""
        # Create mock old backups
        old_daily = BackupMetadata(
            backup_id="old_daily",
            backup_type=BackupType.DAILY,
            created_at=datetime.now() - timedelta(days=10),  # Older than 7 days
            file_path=os.path.join(temp_backup_dir, "old_daily.enc"),
            file_size=100,
            checksum="abc123",
            encrypted=True,
            compression_ratio=0.8,
            status=BackupStatus.COMPLETED
        )
        
        recent_daily = BackupMetadata(
            backup_id="recent_daily",
            backup_type=BackupType.DAILY,
            created_at=datetime.now() - timedelta(days=3),  # Within 7 days
            file_path=os.path.join(temp_backup_dir, "recent_daily.enc"),
            file_size=100,
            checksum="def456",
            encrypted=True,
            compression_ratio=0.8,
            status=BackupStatus.COMPLETED
        )
        
        # Create actual files
        for metadata in [old_daily, recent_daily]:
            with open(metadata.file_path, 'w') as f:
                f.write("test backup data")
        
        # Add to backup history
        backup_service._backup_history = [old_daily, recent_daily]
        
        # Run cleanup
        cleanup_counts = await backup_service.cleanup_old_backups()
        
        assert cleanup_counts[BackupType.DAILY] == 1  # Should clean up old_daily
        assert len(backup_service._backup_history) == 1  # Should have only recent_daily
        assert backup_service._backup_history[0].backup_id == "recent_daily"
        assert not os.path.exists(old_daily.file_path)  # File should be deleted
        assert os.path.exists(recent_daily.file_path)  # File should remain

    @patch('backend.services.backup_service.get_db_session_context')
    async def test_restore_from_backup(self, mock_db_context, backup_service, temp_backup_dir):
        """Test database restoration from backup."""
        # Mock database session
        mock_session = AsyncMock()
        mock_db_context.return_value.__aenter__.return_value = mock_session
        
        # Create test backup file with SQL content
        backup_content = """
        -- Test backup
        BEGIN TRANSACTION;
        INSERT INTO test_table (id, name) VALUES (1, 'test');
        COMMIT;
        """
        
        # Create backup file (unencrypted for simplicity)
        backup_file = os.path.join(temp_backup_dir, "test_backup.sql")
        with open(backup_file, 'w') as f:
            f.write(backup_content)
        
        # Encrypt the backup
        encrypted_file = await backup_service._encrypt_backup(backup_file)
        
        # Create backup metadata
        metadata = BackupMetadata(
            backup_id="test_restore",
            backup_type=BackupType.DAILY,
            created_at=datetime.now(),
            file_path=encrypted_file,
            file_size=len(backup_content),
            checksum="test_checksum",
            encrypted=True,
            compression_ratio=1.0,
            status=BackupStatus.COMPLETED
        )
        
        backup_service._backup_history.append(metadata)
        
        with patch('backend.config.get_settings') as mock_settings:
            mock_settings.return_value.database_url = "postgresql://test:test@localhost/test"
            
            # Perform restoration
            success = await backup_service.restore_from_backup("test_restore")
            
            assert success is True
            # Verify that SQL was executed
            assert mock_session.execute.called

    async def test_backup_failure_handling(self, backup_service):
        """Test backup failure handling and error reporting."""
        with patch.object(backup_service, '_create_database_dump', side_effect=Exception("Database error")):
            with pytest.raises(BackupException) as exc_info:
                await backup_service.create_daily_backup()
            
            assert "Daily backup failed" in str(exc_info.value)

    async def test_get_backup_status(self, backup_service, sample_backup_metadata):
        """Test backup status reporting."""
        # Add sample backup to history
        backup_service._backup_history.append(sample_backup_metadata)
        
        status = await backup_service.get_backup_status()
        
        assert status["total_backups"] == 1
        assert "last_backup" in status
        assert "backup_directory" in status
        assert status["encryption_enabled"] is True


class TestBackupScheduler:
    """Test suite for BackupScheduler class."""

    @pytest.fixture
    def mock_backup_service(self):
        """Create mock backup service for scheduler tests."""
        service = Mock(spec=BackupService)
        service.create_daily_backup = AsyncMock()
        service.create_weekly_backup = AsyncMock()
        service.create_monthly_backup = AsyncMock()
        service.cleanup_old_backups = AsyncMock()
        return service

    @pytest.fixture
    def backup_scheduler(self, mock_backup_service):
        """Create BackupScheduler instance for testing."""
        return BackupScheduler(mock_backup_service)

    async def test_scheduler_initialization(self, backup_scheduler, mock_backup_service):
        """Test backup scheduler initialization."""
        assert backup_scheduler.backup_service == mock_backup_service
        assert backup_scheduler._running is False
        assert backup_scheduler._task is None

    async def test_scheduler_start_stop(self, backup_scheduler):
        """Test scheduler start and stop functionality."""
        # Start scheduler
        await backup_scheduler.start()
        assert backup_scheduler._running is True
        assert backup_scheduler._task is not None
        
        # Stop scheduler
        await backup_scheduler.stop()
        assert backup_scheduler._running is False

    @patch('backend.services.backup_service.datetime')
    async def test_scheduler_daily_backup_trigger(self, mock_datetime, backup_scheduler, mock_backup_service):
        """Test that scheduler triggers daily backup at correct time."""
        # Mock current time to 2 AM
        mock_now = Mock()
        mock_now.hour = 2
        mock_now.minute = 0
        mock_now.weekday.return_value = 1  # Tuesday
        mock_now.day = 15
        mock_datetime.now.return_value = mock_now
        
        # Start scheduler
        await backup_scheduler.start()
        
        # Give it a moment to process
        await asyncio.sleep(0.1)
        
        # Stop scheduler
        await backup_scheduler.stop()
        
        # Verify daily backup was called
        mock_backup_service.create_daily_backup.assert_called()

    @patch('backend.services.backup_service.datetime')
    async def test_scheduler_weekly_backup_trigger(self, mock_datetime, backup_scheduler, mock_backup_service):
        """Test that scheduler triggers weekly backup at correct time."""
        # Mock current time to Sunday 3 AM
        mock_now = Mock()
        mock_now.hour = 3
        mock_now.minute = 0
        mock_now.weekday.return_value = 6  # Sunday
        mock_now.day = 15
        mock_datetime.now.return_value = mock_now
        
        # Start scheduler
        await backup_scheduler.start()
        
        # Give it a moment to process
        await asyncio.sleep(0.1)
        
        # Stop scheduler
        await backup_scheduler.stop()
        
        # Verify weekly backup was called
        mock_backup_service.create_weekly_backup.assert_called()

    @patch('backend.services.backup_service.datetime')
    async def test_scheduler_monthly_backup_trigger(self, mock_datetime, backup_scheduler, mock_backup_service):
        """Test that scheduler triggers monthly backup at correct time."""
        # Mock current time to 1st day 4 AM
        mock_now = Mock()
        mock_now.hour = 4
        mock_now.minute = 0
        mock_now.weekday.return_value = 1  # Tuesday
        mock_now.day = 1  # First day of month
        mock_datetime.now.return_value = mock_now
        
        # Start scheduler
        await backup_scheduler.start()
        
        # Give it a moment to process
        await asyncio.sleep(0.1)
        
        # Stop scheduler
        await backup_scheduler.stop()
        
        # Verify monthly backup was called
        mock_backup_service.create_monthly_backup.assert_called()

    @patch('backend.services.backup_service.datetime')
    async def test_scheduler_cleanup_trigger(self, mock_datetime, backup_scheduler, mock_backup_service):
        """Test that scheduler triggers cleanup at correct time."""
        # Mock current time to 5 AM
        mock_now = Mock()
        mock_now.hour = 5
        mock_now.minute = 0
        mock_now.weekday.return_value = 1  # Tuesday
        mock_now.day = 15
        mock_datetime.now.return_value = mock_now
        
        # Start scheduler
        await backup_scheduler.start()
        
        # Give it a moment to process
        await asyncio.sleep(0.1)
        
        # Stop scheduler
        await backup_scheduler.stop()
        
        # Verify cleanup was called
        mock_backup_service.cleanup_old_backups.assert_called()

    async def test_scheduler_error_handling(self, backup_scheduler, mock_backup_service):
        """Test scheduler error handling."""
        # Make backup service raise an exception
        mock_backup_service.create_daily_backup.side_effect = Exception("Backup failed")
        
        with patch('backend.services.backup_service.datetime') as mock_datetime:
            # Mock current time to trigger daily backup
            mock_now = Mock()
            mock_now.hour = 2
            mock_now.minute = 0
            mock_now.weekday.return_value = 1
            mock_now.day = 15
            mock_datetime.now.return_value = mock_now
            
            # Start scheduler
            await backup_scheduler.start()
            
            # Give it a moment to process
            await asyncio.sleep(0.1)
            
            # Stop scheduler
            await backup_scheduler.stop()
            
            # Scheduler should continue running despite the error
            assert backup_scheduler._running is False  # Stopped by us, not by error