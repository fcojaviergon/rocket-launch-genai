from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select, and_, text
from datetime import datetime, timedelta
from typing import Dict, Any

from core.dependencies import get_current_admin_user, get_db
from database.models.user import User
from database.models.document import Document
from modules.stats.service import StatsService

import logging

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/dashboard")
async def get_dashboard_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
    stats_service: StatsService = Depends()
) -> Dict[str, Any]:
    """Get statistics for the dashboard"""
    try:
        # Delegate to service layer
        dashboard_data = await stats_service.get_dashboard_data(db)
        return dashboard_data
    except Exception as e:
        # Log the error from the endpoint perspective
        logger.error(f"Failed to get dashboard stats: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting statistics: {str(e)}"
        )

@router.get("/analytics")
async def get_analytics_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
    stats_service: StatsService = Depends()
) -> Dict[str, Any]:
    """Get detailed statistics for the analytics page"""
    try:
        # Delegate to service layer
        analytics_data = await stats_service.get_analytics_data(db)
        return analytics_data
    except Exception as e:
        # Log the error from the endpoint perspective
        logger.error(f"Failed to get analytics stats: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting analytics data: {str(e)}"
        ) 