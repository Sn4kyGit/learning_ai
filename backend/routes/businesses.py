"""
Business management API endpoints.

This module provides REST API endpoints for business CRUD operations,
Google Places integration, and business profile management.
"""

import logging
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from backend.db.database import get_db_session
from backend.db.repositories.business import BusinessRepository
from backend.db.schemas import BusinessCreate, BusinessUpdate, BusinessResponse, ErrorResponse
from backend.services.auth_dependencies import get_current_user, RequireAdmin
from backend.services.review_import_service import ReviewImportService
from backend.external.google_places import GooglePlacesClient
from backend.db.models import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/businesses", tags=["businesses"])


# Request/Response models
class ImportReviewsRequest(BaseModel):
    """Request model for importing reviews."""
    max_reviews: int = 500
    force_refresh: bool = False


class ImportReviewsResponse(BaseModel):
    """Response model for review import."""
    business_id: str
    imported_count: int
    skipped_count: int
    total_processed: int
    errors: List[str]


async def get_business_repository(db: AsyncSession = Depends(get_db_session)) -> BusinessRepository:
    """Dependency to get business repository."""
    return BusinessRepository(db)


async def get_review_import_service(db: AsyncSession = Depends(get_db_session)) -> ReviewImportService:
    """Dependency to get review import service."""
    google_places_client = GooglePlacesClient()
    business_repo = BusinessRepository(db)
    return ReviewImportService(google_places_client, business_repo, db)


@router.post(
    "/",
    response_model=BusinessResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"model": ErrorResponse, "description": "Bad Request"},
        409: {"model": ErrorResponse, "description": "Business already exists"},
    },
)
async def create_business(
    business_data: BusinessCreate,
    current_user: User = Depends(get_current_user),
    business_repo: BusinessRepository = Depends(get_business_repository),
) -> BusinessResponse:
    """Create a new business.
    
    Args:
        business_data: Business creation data
        current_user: Current authenticated user
        business_repo: Business repository
        
    Returns:
        BusinessResponse: Created business information
        
    Raises:
        HTTPException: If creation fails
    """
    try:
        # TODO: Add proper authorization check (Admin+ only)
        business = await business_repo.create(business_data)
        
        return BusinessResponse(
            id=business.id,
            name=business.name,
            google_place_id=business.google_place_id,
            category=business.category,
            address=business.address,
            organization_id=business.organization_id,
            avg_rating=business.avg_rating,
            total_reviews=business.total_reviews,
            created_at=business.created_at,
            updated_at=business.updated_at,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Business creation failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Business creation failed"
        )


@router.get(
    "/",
    response_model=List[BusinessResponse],
    responses={
        401: {"model": ErrorResponse, "description": "Authentication required"},
    },
)
async def list_businesses(
    skip: int = Query(0, ge=0, description="Number of businesses to skip"),
    limit: int = Query(100, ge=1, le=500, description="Maximum number of businesses to return"),
    organization_id: Optional[UUID] = Query(None, description="Filter by organization ID"),
    current_user: User = Depends(get_current_user),
    business_repo: BusinessRepository = Depends(get_business_repository),
) -> List[BusinessResponse]:
    """List businesses accessible to current user.
    
    Args:
        skip: Number of businesses to skip
        limit: Maximum number of businesses to return
        organization_id: Optional organization filter
        current_user: Current authenticated user
        business_repo: Business repository
        
    Returns:
        List[BusinessResponse]: List of accessible businesses
    """
    try:
        # Get businesses based on user permissions
        if current_user.role == "super_admin":
            businesses = await business_repo.get_all(skip=skip, limit=limit, organization_id=organization_id)
        else:
            # TODO: Get businesses accessible to current user based on permissions
            businesses = await business_repo.get_by_user_access(current_user.id, skip=skip, limit=limit)
        
        return [
            BusinessResponse(
                id=business.id,
                name=business.name,
                google_place_id=business.google_place_id,
                category=business.category,
                address=business.address,
                organization_id=business.organization_id,
                avg_rating=business.avg_rating,
                total_reviews=business.total_reviews,
                created_at=business.created_at,
                updated_at=business.updated_at,
            )
            for business in businesses
        ]
        
    except Exception as e:
        logger.error(f"Failed to list businesses: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve businesses"
        )


@router.get(
    "/{business_id}",
    response_model=BusinessResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Business not found"},
    },
)
async def get_business(
    business_id: UUID,
    current_user: User = Depends(get_current_user),
    business_repo: BusinessRepository = Depends(get_business_repository),
) -> BusinessResponse:
    """Get business by ID.
    
    Args:
        business_id: Business ID
        current_user: Current authenticated user
        business_repo: Business repository
        
    Returns:
        BusinessResponse: Business information
        
    Raises:
        HTTPException: If business not found or access denied
    """
    try:
        # TODO: Add business access validation
        business = await business_repo.get_by_id(business_id)
        
        if not business:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Business not found"
            )
        
        return BusinessResponse(
            id=business.id,
            name=business.name,
            google_place_id=business.google_place_id,
            category=business.category,
            address=business.address,
            organization_id=business.organization_id,
            avg_rating=business.avg_rating,
            total_reviews=business.total_reviews,
            created_at=business.created_at,
            updated_at=business.updated_at,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get business {business_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve business"
        )


@router.put(
    "/{business_id}",
    response_model=BusinessResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Business not found"},
        400: {"model": ErrorResponse, "description": "Bad Request"},
    },
)
async def update_business(
    business_id: UUID,
    business_data: BusinessUpdate,
    current_user: User = Depends(get_current_user),
    business_repo: BusinessRepository = Depends(get_business_repository),
) -> BusinessResponse:
    """Update business information.
    
    Args:
        business_id: Business ID
        business_data: Business update data
        current_user: Current authenticated user
        business_repo: Business repository
        
    Returns:
        BusinessResponse: Updated business information
        
    Raises:
        HTTPException: If business not found or update fails
    """
    try:
        # TODO: Add business access validation (Admin+ only)
        business = await business_repo.update(business_id, business_data)
        
        if not business:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Business not found"
            )
        
        return BusinessResponse(
            id=business.id,
            name=business.name,
            google_place_id=business.google_place_id,
            category=business.category,
            address=business.address,
            organization_id=business.organization_id,
            avg_rating=business.avg_rating,
            total_reviews=business.total_reviews,
            created_at=business.created_at,
            updated_at=business.updated_at,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update business {business_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Business update failed"
        )


@router.delete(
    "/{business_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        404: {"model": ErrorResponse, "description": "Business not found"},
        403: {"model": ErrorResponse, "description": "Insufficient permissions"},
    },
)
async def delete_business(
    business_id: UUID,
    current_user: RequireAdmin,
    business_repo: BusinessRepository = Depends(get_business_repository),
) -> None:
    """Delete business (Admin+ only).
    
    Args:
        business_id: Business ID
        current_user: Current authenticated admin user
        business_repo: Business repository
        
    Raises:
        HTTPException: If business not found or deletion fails
    """
    try:
        # TODO: Add business access validation
        deleted = await business_repo.delete(business_id)
        
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Business not found"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete business {business_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Business deletion failed"
        )


@router.post(
    "/{business_id}/import-reviews",
    response_model=ImportReviewsResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Business not found"},
        400: {"model": ErrorResponse, "description": "Bad Request"},
    },
)
async def import_reviews(
    business_id: UUID,
    import_request: ImportReviewsRequest,
    current_user: User = Depends(get_current_user),
    import_service: ReviewImportService = Depends(get_review_import_service),
) -> ImportReviewsResponse:
    """Import reviews from Google Places for a business.
    
    Args:
        business_id: Business ID
        import_request: Import configuration
        current_user: Current authenticated user
        import_service: Review import service
        
    Returns:
        ImportReviewsResponse: Import results
        
    Raises:
        HTTPException: If import fails
    """
    try:
        # TODO: Add business access validation
        result = await import_service.import_reviews_for_business(
            business_id,
            max_reviews=import_request.max_reviews,
            force_refresh=import_request.force_refresh
        )
        
        return ImportReviewsResponse(
            business_id=str(business_id),
            imported_count=result.imported_count,
            skipped_count=result.skipped_count,
            total_processed=result.total_processed,
            errors=result.errors,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to import reviews for business {business_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Review import failed"
        )


@router.get(
    "/{business_id}/google-places-info",
    responses={
        404: {"model": ErrorResponse, "description": "Business not found"},
    },
)
async def get_google_places_info(
    business_id: UUID,
    current_user: User = Depends(get_current_user),
    business_repo: BusinessRepository = Depends(get_business_repository),
    import_service: ReviewImportService = Depends(get_review_import_service),
):
    """Get Google Places information for a business.
    
    Args:
        business_id: Business ID
        current_user: Current authenticated user
        business_repo: Business repository
        import_service: Review import service
        
    Returns:
        dict: Google Places information
        
    Raises:
        HTTPException: If business not found or API call fails
    """
    try:
        # TODO: Add business access validation
        business = await business_repo.get_by_id(business_id)
        
        if not business:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Business not found"
            )
        
        places_info = await import_service.get_google_places_info(business.google_place_id)
        
        return {
            "business_id": str(business_id),
            "google_place_id": business.google_place_id,
            "places_info": places_info,
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get Google Places info for business {business_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve Google Places information"
        )


@router.get(
    "/{business_id}/import-status",
    responses={
        404: {"model": ErrorResponse, "description": "Business not found"},
    },
)
async def get_import_status(
    business_id: UUID,
    current_user: User = Depends(get_current_user),
    import_service: ReviewImportService = Depends(get_review_import_service),
):
    """Get review import status for a business.
    
    Args:
        business_id: Business ID
        current_user: Current authenticated user
        import_service: Review import service
        
    Returns:
        dict: Import status information
        
    Raises:
        HTTPException: If business not found
    """
    try:
        # TODO: Add business access validation
        status_info = await import_service.get_import_status(business_id)
        return status_info
        
    except Exception as e:
        logger.error(f"Failed to get import status for business {business_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve import status"
        )


@router.get(
    "/{business_id}/import-status/real-time",
    responses={
        404: {"model": ErrorResponse, "description": "Business not found"},
    },
)
async def get_real_time_import_status(
    business_id: UUID,
    current_user: User = Depends(get_current_user),
    import_service: ReviewImportService = Depends(get_review_import_service),
):
    """Get real-time import status for active imports.
    
    Args:
        business_id: Business ID
        current_user: Current authenticated user
        import_service: Review import service
        
    Returns:
        dict: Real-time import status
    """
    try:
        # TODO: Add business access validation
        status_info = await import_service.get_real_time_status(business_id)
        return status_info
        
    except Exception as e:
        logger.error(f"Failed to get real-time import status for business {business_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve real-time import status"
        )


@router.get(
    "/{business_id}/import-history",
    responses={
        404: {"model": ErrorResponse, "description": "Business not found"},
    },
)
async def get_import_history(
    business_id: UUID,
    limit: int = Query(10, ge=1, le=50, description="Maximum number of history entries"),
    current_user: User = Depends(get_current_user),
    import_service: ReviewImportService = Depends(get_review_import_service),
):
    """Get import history for a business.
    
    Args:
        business_id: Business ID
        limit: Maximum number of history entries
        current_user: Current authenticated user
        import_service: Review import service
        
    Returns:
        dict: Import history
    """
    try:
        # TODO: Add business access validation
        history = await import_service.get_import_history(business_id, limit)
        
        return {
            "business_id": str(business_id),
            "import_history": history,
            "total_entries": len(history)
        }
        
    except Exception as e:
        logger.error(f"Failed to get import history for business {business_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve import history"
        )


@router.post(
    "/{business_id}/import-reviews/manual",
    response_model=ImportReviewsResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Business not found"},
        400: {"model": ErrorResponse, "description": "Bad Request"},
        409: {"model": ErrorResponse, "description": "Import already in progress"},
    },
)
async def start_manual_import(
    business_id: UUID,
    import_request: ImportReviewsRequest,
    current_user: User = Depends(get_current_user),
    import_service: ReviewImportService = Depends(get_review_import_service),
) -> ImportReviewsResponse:
    """Start manual review import with progress tracking.
    
    Args:
        business_id: Business ID
        import_request: Import configuration
        current_user: Current authenticated user
        import_service: Review import service
        
    Returns:
        ImportReviewsResponse: Import results
        
    Raises:
        HTTPException: If import fails or already in progress
    """
    try:
        # TODO: Add business access validation
        
        # Check if import is already in progress
        current_status = await import_service.get_real_time_status(business_id)
        if current_status.get("is_active", False):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Import already in progress for this business"
            )
        
        result = await import_service.start_manual_import(
            business_id,
            max_reviews=import_request.max_reviews
        )
        
        return ImportReviewsResponse(
            business_id=str(business_id),
            imported_count=result.imported_count,
            skipped_count=result.duplicate_count,
            total_processed=result.total_found,
            errors=result.errors,
        )
        
    except HTTPException:
        raise
    except ValueError as e:
        if "already in progress" in str(e):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=str(e)
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to start manual import for business {business_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Manual import failed"
        )


@router.get(
    "/search/google-places",
    responses={
        400: {"model": ErrorResponse, "description": "Bad Request"},
    },
)
async def search_google_places(
    query: str = Query(..., description="Search query for places"),
    location: Optional[str] = Query(None, description="Location bias (lat,lng format)"),
    radius: int = Query(5000, ge=100, le=50000, description="Search radius in meters"),
    current_user: User = Depends(get_current_user),
):
    """Search Google Places for businesses.
    
    Args:
        query: Search query (e.g., "Italian restaurant")
        location: Optional location bias (lat,lng format)
        radius: Search radius in meters
        current_user: Current authenticated user
        
    Returns:
        dict: Search results from Google Places
        
    Raises:
        HTTPException: If search fails
    """
    try:
        google_places_client = GooglePlacesClient()
        results = await google_places_client.search_places(
            query=query,
            location=location,
            radius=radius
        )
        
        # Format results for frontend consumption
        formatted_results = []
        for place in results:
            formatted_results.append({
                "place_id": place.get("place_id"),
                "name": place.get("name"),
                "address": place.get("formatted_address"),
                "rating": place.get("rating"),
                "user_ratings_total": place.get("user_ratings_total"),
                "types": place.get("types", []),
                "geometry": place.get("geometry", {}),
                "photos": place.get("photos", []),
                "price_level": place.get("price_level"),
                "business_status": place.get("business_status"),
            })
        
        return {
            "results": formatted_results,
            "query": query,
            "location": location,
            "radius": radius,
        }
        
    except Exception as e:
        logger.error(f"Failed to search Google Places: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Google Places search failed"
        )


@router.get(
    "/google-places/{place_id}/details",
    responses={
        400: {"model": ErrorResponse, "description": "Bad Request"},
        404: {"model": ErrorResponse, "description": "Place not found"},
    },
)
async def get_google_place_details(
    place_id: str,
    current_user: User = Depends(get_current_user),
):
    """Get detailed information for a Google Place.
    
    Args:
        place_id: Google Place ID
        current_user: Current authenticated user
        
    Returns:
        dict: Detailed place information
        
    Raises:
        HTTPException: If place not found or API call fails
    """
    try:
        google_places_client = GooglePlacesClient()
        place_details = await google_places_client.get_place_details(place_id)
        
        if not place_details:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Place not found"
            )
        
        # Format details for frontend consumption
        formatted_details = {
            "place_id": place_details.get("place_id"),
            "name": place_details.get("name"),
            "formatted_address": place_details.get("formatted_address"),
            "formatted_phone_number": place_details.get("formatted_phone_number"),
            "international_phone_number": place_details.get("international_phone_number"),
            "website": place_details.get("website"),
            "rating": place_details.get("rating"),
            "user_ratings_total": place_details.get("user_ratings_total"),
            "types": place_details.get("types", []),
            "geometry": place_details.get("geometry", {}),
            "photos": place_details.get("photos", []),
            "price_level": place_details.get("price_level"),
            "business_status": place_details.get("business_status"),
            "opening_hours": place_details.get("opening_hours", {}),
            "reviews": place_details.get("reviews", []),
        }
        
        return {
            "place_details": formatted_details,
            "place_id": place_id,
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get Google Place details for {place_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve place details"
        )