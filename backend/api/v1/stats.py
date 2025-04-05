from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select, and_, text
from datetime import datetime, timedelta
from typing import Dict, Any

from core.deps import get_current_user, get_db
from database.models.user import User
from database.models.document import Document
from database.models.pipeline import PipelineExecution

router = APIRouter()

@router.get("/dashboard")
async def get_dashboard_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get statistics for the dashboard"""
    try:
        # Get date from a week ago
        week_ago = datetime.utcnow() - timedelta(days=7)
        
        # Total users and new ones this week
        total_users = await db.scalar(select(func.count()).select_from(User))
        new_users_week = await db.scalar(
            select(func.count())
            .select_from(User)
            .where(User.created_at >= week_ago)
        )
        
        # Total documents and processed this week
        total_docs = await db.scalar(select(func.count()).select_from(Document))
        new_docs_week = await db.scalar(
            select(func.count())
            .select_from(Document)
            .where(Document.created_at >= week_ago)
        )
        
        # Total executions and new ones this week
        total_executions = await db.scalar(select(func.count()).select_from(PipelineExecution))
        new_executions_week = await db.scalar(
            select(func.count())
            .select_from(PipelineExecution)
            .where(PipelineExecution.created_at >= week_ago)
        )
        
        # Calculate percentage changes
        two_weeks_ago = datetime.utcnow() - timedelta(days=14)
        
        prev_week_users = await db.scalar(
            select(func.count())
            .select_from(User)
            .where(and_(
                User.created_at >= two_weeks_ago,
                User.created_at < week_ago
            ))
        )
        
        prev_week_docs = await db.scalar(
            select(func.count())
            .select_from(Document)
            .where(and_(
                Document.created_at >= two_weeks_ago,
                Document.created_at < week_ago
            ))
        )
        
        prev_week_executions = await db.scalar(
            select(func.count())
            .select_from(PipelineExecution)
            .where(and_(
                PipelineExecution.created_at >= two_weeks_ago,
                PipelineExecution.created_at < week_ago
            ))
        )
        
        # Calculate percentage changes
        def calculate_change(current: int, previous: int) -> float:
            if previous == 0:
                return 100.0 if current > 0 else 0.0
            return ((current - previous) / previous) * 100

        users_change = calculate_change(new_users_week, prev_week_users)
        docs_change = calculate_change(new_docs_week, prev_week_docs)
        executions_change = calculate_change(new_executions_week, prev_week_executions)

        # Get recent activity (last 5 executions)
        recent_activity_query = (
            select(
                PipelineExecution.id,
                PipelineExecution.status,
                PipelineExecution.created_at,
                Document.title.label('document_name'),
                Document.type.label('document_type')
            )
            .join(Document, PipelineExecution.document_id == Document.id)
            .order_by(PipelineExecution.created_at.desc())
            .limit(5)
        )
        recent_activity_result = await db.execute(recent_activity_query)
        recent_activity = []
        for row in recent_activity_result:
            time_diff = datetime.utcnow() - row.created_at
            if time_diff.days > 0:
                time_ago = f"{time_diff.days} days ago"
            elif time_diff.seconds >= 3600:
                hours = time_diff.seconds // 3600
                time_ago = f"{hours} hours ago"
            else:
                minutes = time_diff.seconds // 60
                time_ago = f"{minutes} minutes ago"
            
            recent_activity.append({
                "id": str(row.id),
                "document_name": row.document_name,
                "document_type": row.document_type,
                "status": row.status,
                "time_ago": time_ago
            })

        # Get monthly performance (last 6 months)
        six_months_ago = datetime.utcnow() - timedelta(days=180)

        # Generate month series
        months_query = """
        WITH RECURSIVE months AS (
            SELECT date_trunc('month', now()) as month
            UNION ALL
            SELECT date_trunc('month', month - interval '1 month')
            FROM months
            WHERE month > date_trunc('month', now() - interval '6 months')
        )
        SELECT 
            months.month,
            COALESCE(COUNT(pe.id), 0) as count
        FROM months
        LEFT JOIN pipeline_executions pe 
            ON date_trunc('month', pe.created_at) = months.month
        GROUP BY months.month
        ORDER BY months.month DESC;
        """

        monthly_stats_result = await db.execute(text(months_query))
        monthly_stats = {}
        for row in monthly_stats_result:
            month_name = row.month.strftime('%b')  # Month abbreviation
            monthly_stats[month_name] = row.count
        
        return {
            "users": {
                "total": total_users,
                "new_week": new_users_week,
                "change": round(users_change, 1)
            },
            "documents": {
                "total": total_docs,
                "new_week": new_docs_week,
                "change": round(docs_change, 1)
            },
            "executions": {
                "total": total_executions,
                "new_week": new_executions_week,
                "change": round(executions_change, 1)
            },
            "recent_activity": recent_activity,
            "monthly_stats": monthly_stats
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting statistics: {str(e)}"
        )

@router.get("/analytics")
async def get_analytics_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get detailed statistics for the analytics page"""
    try:
        # Get data from the last 12 months
        year_ago = datetime.utcnow() - timedelta(days=365)
        
        # Queries to get monthly data
        monthly_users = await db.execute(
            select(
                func.date_trunc('month', User.created_at).label('month'),
                func.count().label('count')
            )
            .where(User.created_at >= year_ago)
            .group_by(text('month'))
            .order_by(text('month'))
        )
        
        monthly_docs = await db.execute(
            select(
                func.date_trunc('month', Document.created_at).label('month'),
                func.count().label('count')
            )
            .where(Document.created_at >= year_ago)
            .group_by(text('month'))
            .order_by(text('month'))
        )
        
        monthly_executions = await db.execute(
            select(
                func.date_trunc('month', PipelineExecution.created_at).label('month'),
                func.count().label('count')
            )
            .where(PipelineExecution.created_at >= year_ago)
            .group_by(text('month'))
            .order_by(text('month'))
        )
        
        # Process results
        def process_monthly_data(results):
            data = {}
            for row in results:
                month = row.month.strftime('%Y-%m')
                data[month] = row.count
            return data
        
        users_data = process_monthly_data(monthly_users)
        docs_data = process_monthly_data(monthly_docs)
        executions_data = process_monthly_data(monthly_executions)
        
        # Get document type distribution
        doc_types = await db.execute(
            select(
                Document.type,
                func.count().label('count')
            )
            .group_by(Document.type)
        )
        
        doc_types_data = {row.type: row.count for row in doc_types}
        total_docs = sum(doc_types_data.values())
        doc_types_percentage = {
            doc_type: round((count / total_docs) * 100, 1) 
            for doc_type, count in doc_types_data.items()
        } if total_docs > 0 else {}
        
        # Weekly data (last 7 days, grouped by day of the week)
        week_ago = datetime.utcnow() - timedelta(days=7)
        
        # Query for weekly user data (0-6, where 0 is Monday)
        weekly_users_query = """
        SELECT 
            EXTRACT(DOW FROM created_at) as dow,
            COUNT(*) as count
        FROM users
        WHERE created_at >= :week_ago
        GROUP BY dow
        ORDER BY dow
        """
        weekly_users_result = await db.execute(
            text(weekly_users_query),
            {"week_ago": week_ago}
        )
        
        # Query for weekly execution data (0-6, where 0 is Monday)
        weekly_executions_query = """
        SELECT 
            EXTRACT(DOW FROM created_at) as dow,
            COUNT(*) as count
        FROM pipeline_executions
        WHERE created_at >= :week_ago
        GROUP BY dow
        ORDER BY dow
        """
        weekly_executions_result = await db.execute(
            text(weekly_executions_query),
            {"week_ago": week_ago}
        )
        
        # Process weekly data
        def process_weekly_data(results):
            # Initialize with zeros for the 7 days (0-6)
            data = [0, 0, 0, 0, 0, 0, 0]
            for row in results:
                # PostgreSQL uses 0 for Sunday, adjust for Monday to be 0
                dow = (int(row.dow) - 1) % 7
                data[dow] = row.count
            return data
            
        weekly_users = process_weekly_data(weekly_users_result)
        weekly_executions = process_weekly_data(weekly_executions_result)
        
        # Popular queries (simulated for now)
        # In a real implementation, this would likely come from a query log
        popular_queries = [
            {"query": "how to implement authentication", "count": 145},
            {"query": "Integrate with external APIs", "count": 132},
            {"query": "Process PDF documents", "count": 98},
            {"query": "Configure security", "count": 76}, 
            {"query": "Optimize database", "count": 63}
        ]
        
        return {
            "monthly": {
                "users": users_data,
                "documents": docs_data,
                "executions": executions_data
            },
            "weekly": {
                "users": weekly_users,
                "executions": weekly_executions
            },
            "document_types": {
                "counts": doc_types_data,
                "percentages": doc_types_percentage
            },
            "popular_queries": popular_queries
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting detailed statistics: {str(e)}"
        ) 