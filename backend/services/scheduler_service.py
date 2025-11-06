"""
Scheduler service for automated review processing and analytics updates.

This service handles automated daily review import, processing, and
real-time dashboard data updates every 4 hours.
"""

import logging
import asyncio
from typing import List, Optional, Dict, Any
from datetime import datetime, time, timedelta, timezone
from uuid import UUID

from backend.services.review.processor import ReviewProcessingService
from backend.services.analytics_service import AnalyticsService
from backend.services.review_import_service import ReviewImportService
from backend.services.backup_service import BackupService
from backend.db.repositories.business import BusinessRepository

logger = logging.getLogger(__name__)


class SchedulerService:
    """Handles automated scheduling of review processing and analytics updates."""

    def __init__(
        self,
        review_processor: ReviewProcessingService,
        analytics_service: AnalyticsService,
        review_import_service: ReviewImportService,
        business_repository: BusinessRepository,
        backup_service: Optional[BackupService] = None,
    ):
        """Initialize scheduler service.

        Args:
            review_processor: Review processing service
            analytics_service: Analytics service for dashboard updates
            review_import_service: Review import service for Google Places integration
            business_repository: Business repository
            backup_service: Optional backup service for automated backups
        """
        self._review_processor = review_processor
        self._analytics_service = analytics_service
        self._review_import_service = review_import_service
        self._business_repo = business_repository
        self._backup_service = backup_service
        self._running = False
        self._tasks: List[asyncio.Task] = []

    async def start(self) -> None:
        """Start the scheduler service."""
        if self._running:
            logger.warning("Scheduler service is already running")
            return

        self._running = True
        logger.info("Starting scheduler service")

        # Start background tasks
        self._tasks = [
            asyncio.create_task(self._daily_review_import_scheduler()),
            asyncio.create_task(self._analytics_refresh_scheduler()),
            asyncio.create_task(self._cache_cleanup_scheduler()),
        ]
        
        # Add backup scheduler if backup service is available
        if self._backup_service:
            self._tasks.append(asyncio.create_task(self._backup_scheduler()))

        task_count = len(self._tasks)
        logger.info(f"Scheduler service started with {task_count} background tasks")

    async def stop(self) -> None:
        """Stop the scheduler service."""
        if not self._running:
            return

        self._running = False
        logger.info("Stopping scheduler service")

        # Cancel all tasks
        for task in self._tasks:
            task.cancel()

        # Wait for tasks to complete
        await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks.clear()

        logger.info("Scheduler service stopped")

    async def trigger_daily_review_processing(self) -> Dict[str, Any]:
        """Manually trigger daily review processing for all businesses.

        Returns:
            Dictionary with processing results
        """
        try:
            logger.info("Starting manual daily review processing")
            
            # Get all businesses
            businesses = await self._business_repo.get_businesses_needing_analysis(limit=1000)
            
            total_processed = 0
            total_errors = 0
            business_results = []

            for business in businesses:
                try:
                    # Import new reviews from Google Places
                    import_result = await self._review_import_service.import_reviews_with_retry(
                        business.id
                    )
                    
                    # Process new reviews
                    processing_result = await self._review_processor.process_new_reviews(
                        business.id
                    )
                    
                    # Update analytics
                    await self._analytics_service.update_business_analytics(business.id)
                    
                    business_results.append({
                        "business_id": str(business.id),
                        "business_name": business.name,
                        "imported_reviews": import_result.imported_count,
                        "duplicate_reviews": import_result.duplicate_count,
                        "import_errors": import_result.error_count,
                        "processed_reviews": processing_result.processed_count,
                        "critical_reviews": processing_result.critical_reviews_found,
                        "processing_errors": processing_result.errors,
                    })
                    
                    total_processed += processing_result.processed_count
                    total_errors += processing_result.error_count + import_result.error_count

                except Exception as e:
                    logger.error(f"Failed to process business {business.id}: {e}")
                    total_errors += 1
                    business_results.append({
                        "business_id": str(business.id),
                        "business_name": business.name,
                        "error": str(e),
                    })

            logger.info(
                f"Daily review processing completed - "
                f"Businesses: {len(businesses)}, "
                f"Reviews processed: {total_processed}, "
                f"Errors: {total_errors}"
            )

            return {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "businesses_processed": len(businesses),
                "total_reviews_processed": total_processed,
                "total_errors": total_errors,
                "business_results": business_results,
            }

        except Exception as e:
            logger.error(f"Failed to execute daily review processing: {e}")
            raise

    async def trigger_analytics_refresh(self) -> Dict[str, Any]:
        """Manually trigger analytics refresh for all businesses.

        Returns:
            Dictionary with refresh results
        """
        try:
            logger.info("Starting manual analytics refresh")
            
            # Refresh cached analytics data
            await self._analytics_service.schedule_cache_refresh()
            
            # Get cache statistics
            cache_stats = await self._analytics_service.get_cache_stats()
            
            return {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "cache_stats": cache_stats,
                "status": "completed",
            }

        except Exception as e:
            logger.error(f"Failed to refresh analytics: {e}")
            raise

    async def trigger_backup(self, backup_type: str = "daily") -> Dict[str, Any]:
        """Manually trigger a database backup.

        Args:
            backup_type: Type of backup to create (daily, weekly, monthly)

        Returns:
            Dictionary with backup results
        """
        if not self._backup_service:
            raise ValueError("Backup service not available")

        try:
            logger.info(f"Starting manual {backup_type} backup")
            
            if backup_type == "daily":
                metadata = await self._backup_service.create_daily_backup()
            elif backup_type == "weekly":
                metadata = await self._backup_service.create_weekly_backup()
            elif backup_type == "monthly":
                metadata = await self._backup_service.create_monthly_backup()
            else:
                raise ValueError(f"Invalid backup type: {backup_type}")
            
            return {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "backup_id": metadata.backup_id,
                "backup_type": metadata.backup_type.value,
                "file_size": metadata.file_size,
                "encrypted": metadata.encrypted,
                "compression_ratio": metadata.compression_ratio,
                "status": metadata.status.value,
            }

        except Exception as e:
            logger.error(f"Failed to create {backup_type} backup: {e}")
            raise

    async def _daily_review_import_scheduler(self) -> None:
        """Background task for daily review import at midnight."""
        while self._running:
            try:
                now = datetime.now()
                
                # Calculate next midnight
                next_midnight = now.replace(
                    hour=0, minute=0, second=0, microsecond=0
                ) + timedelta(days=1)
                
                # Wait until midnight
                sleep_seconds = (next_midnight - now).total_seconds()
                logger.debug(f"Waiting {sleep_seconds} seconds until next daily review import")
                
                await asyncio.sleep(sleep_seconds)
                
                if not self._running:
                    break
                
                # Execute daily review processing
                logger.info("Executing scheduled daily review import and processing")
                await self.trigger_daily_review_processing()

            except asyncio.CancelledError:
                logger.info("Daily review import scheduler cancelled")
                break
            except Exception as e:
                logger.error(f"Error in daily review import scheduler: {e}")
                # Wait 1 hour before retrying
                await asyncio.sleep(3600)

    async def _analytics_refresh_scheduler(self) -> None:
        """Background task for analytics refresh every 4 hours during business hours."""
        while self._running:
            try:
                now = datetime.now()
                current_hour = now.hour
                
                # Business hours: 8:00-22:00 (every 4 hours)
                # Off hours: every 8 hours
                if 8 <= current_hour <= 22:
                    # Business hours - refresh every 4 hours
                    next_refresh_hours = [8, 12, 16, 20]
                    next_hour = min([h for h in next_refresh_hours if h > current_hour], default=8)
                    
                    if next_hour == 8:  # Next day
                        next_refresh = now.replace(
                            hour=8, minute=0, second=0, microsecond=0
                        ) + timedelta(days=1)
                    else:
                        next_refresh = now.replace(
                            hour=next_hour, minute=0, second=0, microsecond=0
                        )
                else:
                    # Off hours - refresh every 8 hours
                    if current_hour < 8:
                        next_refresh = now.replace(
                            hour=8, minute=0, second=0, microsecond=0
                        )
                    else:  # current_hour > 22
                        next_refresh = now.replace(
                            hour=8, minute=0, second=0, microsecond=0
                        ) + timedelta(days=1)
                
                # Wait until next refresh time
                sleep_seconds = (next_refresh - now).total_seconds()
                logger.debug(f"Waiting {sleep_seconds} seconds until next analytics refresh")
                
                await asyncio.sleep(sleep_seconds)
                
                if not self._running:
                    break
                
                # Execute analytics refresh
                logger.info("Executing scheduled analytics refresh")
                await self.trigger_analytics_refresh()

            except asyncio.CancelledError:
                logger.info("Analytics refresh scheduler cancelled")
                break
            except Exception as e:
                logger.error(f"Error in analytics refresh scheduler: {e}")
                # Wait 1 hour before retrying
                await asyncio.sleep(3600)

    async def _cache_cleanup_scheduler(self) -> None:
        """Background task for cache cleanup every hour."""
        while self._running:
            try:
                # Wait 1 hour
                await asyncio.sleep(3600)
                
                if not self._running:
                    break
                
                # Clean up expired cache entries
                removed_count = await self._analytics_service.cleanup_expired_cache()
                
                if removed_count > 0:
                    logger.debug(f"Cleaned up {removed_count} expired cache entries")

            except asyncio.CancelledError:
                logger.info("Cache cleanup scheduler cancelled")
                break
            except Exception as e:
                logger.error(f"Error in cache cleanup scheduler: {e}")
                # Continue with next iteration

    async def _backup_scheduler(self) -> None:
        """Background task for automated database backups."""
        if not self._backup_service:
            return
            
        while self._running:
            try:
                now = datetime.now()
                
                # Daily backup at 2 AM
                if now.hour == 2 and now.minute == 0:
                    logger.info("Executing scheduled daily backup")
                    try:
                        metadata = await self._backup_service.create_daily_backup()
                        logger.info(f"Daily backup completed: {metadata.backup_id}")
                    except Exception as e:
                        logger.error(f"Daily backup failed: {e}")
                
                # Weekly backup on Sunday at 3 AM
                elif now.weekday() == 6 and now.hour == 3 and now.minute == 0:
                    logger.info("Executing scheduled weekly backup")
                    try:
                        metadata = await self._backup_service.create_weekly_backup()
                        logger.info(f"Weekly backup completed: {metadata.backup_id}")
                    except Exception as e:
                        logger.error(f"Weekly backup failed: {e}")
                
                # Monthly backup on 1st day at 4 AM
                elif now.day == 1 and now.hour == 4 and now.minute == 0:
                    logger.info("Executing scheduled monthly backup")
                    try:
                        metadata = await self._backup_service.create_monthly_backup()
                        logger.info(f"Monthly backup completed: {metadata.backup_id}")
                    except Exception as e:
                        logger.error(f"Monthly backup failed: {e}")
                
                # Cleanup old backups daily at 5 AM
                elif now.hour == 5 and now.minute == 0:
                    logger.info("Executing scheduled backup cleanup")
                    try:
                        cleanup_counts = await self._backup_service.cleanup_old_backups()
                        total_cleaned = sum(cleanup_counts.values())
                        logger.info(f"Backup cleanup completed: {total_cleaned} backups removed")
                    except Exception as e:
                        logger.error(f"Backup cleanup failed: {e}")
                
                # Sleep for 1 minute
                await asyncio.sleep(60)
                
            except asyncio.CancelledError:
                logger.info("Backup scheduler cancelled")
                break
            except Exception as e:
                logger.error(f"Error in backup scheduler: {e}")
                await asyncio.sleep(60)  # Continue after error

    async def get_scheduler_status(self) -> Dict[str, Any]:
        """Get current scheduler status.

        Returns:
            Dictionary with scheduler status information
        """
        return {
            "running": self._running,
            "active_tasks": len([task for task in self._tasks if not task.done()]),
            "total_tasks": len(self._tasks),
            "task_status": [
                {
                    "name": task.get_name() if hasattr(task, 'get_name') else f"Task-{i}",
                    "done": task.done(),
                    "cancelled": task.cancelled(),
                }
                for i, task in enumerate(self._tasks)
            ],
        }

    async def health_check(self) -> bool:
        """Check if scheduler service is healthy.

        Returns:
            True if healthy, False otherwise
        """
        if not self._running:
            return False
        
        # Check if all tasks are still running
        active_tasks = [task for task in self._tasks if not task.done()]
        return len(active_tasks) == len(self._tasks)