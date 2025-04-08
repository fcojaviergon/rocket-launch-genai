import logging
from typing import Dict, Any, List
from datetime import datetime, timedelta
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select, and_, text

from database.models.user import User
from database.models.document import Document
from database.models.pipeline import PipelineExecution

logger = logging.getLogger(__name__)

class StatsService:
    """Service layer for calculating and retrieving statistics."""

    def _calculate_percentage_change(self, current: int, previous: int) -> float:
        """Helper to calculate percentage change."""
        if previous == 0:
            return 100.0 if current > 0 else 0.0
        try:
            return ((current - previous) / previous) * 100
        except ZeroDivisionError:
            return 0.0 # Should be covered by previous == 0 check, but defensive

    def _format_time_ago(self, timestamp: datetime) -> str:
         """Helper to format time difference."""
         time_diff = datetime.utcnow() - timestamp
         if time_diff.days > 0:
             return f"{time_diff.days} days ago"
         elif time_diff.seconds >= 3600:
             hours = time_diff.seconds // 3600
             return f"{hours} hours ago"
         else:
             minutes = max(0, time_diff.seconds // 60) # Ensure non-negative
             return f"{minutes} minutes ago"

    async def get_dashboard_data(self, db: AsyncSession) -> Dict[str, Any]:
        """Calculates and returns data for the main dashboard."""
        logger.info("Calculating dashboard statistics...")
        try:
            week_ago = datetime.utcnow() - timedelta(days=7)
            two_weeks_ago = datetime.utcnow() - timedelta(days=14)

            # --- Counts ---
            total_users_fut = db.scalar(select(func.count()).select_from(User))
            new_users_week_fut = db.scalar(select(func.count()).select_from(User).where(User.created_at >= week_ago))
            prev_week_users_fut = db.scalar(select(func.count()).select_from(User).where(and_(User.created_at >= two_weeks_ago, User.created_at < week_ago)))

            total_docs_fut = db.scalar(select(func.count()).select_from(Document))
            new_docs_week_fut = db.scalar(select(func.count()).select_from(Document).where(Document.created_at >= week_ago))
            prev_week_docs_fut = db.scalar(select(func.count()).select_from(Document).where(and_(Document.created_at >= two_weeks_ago, Document.created_at < week_ago)))

            total_executions_fut = db.scalar(select(func.count()).select_from(PipelineExecution))
            new_executions_week_fut = db.scalar(select(func.count()).select_from(PipelineExecution).where(PipelineExecution.created_at >= week_ago))
            prev_week_executions_fut = db.scalar(select(func.count()).select_from(PipelineExecution).where(and_(PipelineExecution.created_at >= two_weeks_ago, PipelineExecution.created_at < week_ago)))

            # --- Recent Activity ---
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
            recent_activity_result_fut = db.execute(recent_activity_query)

            # --- Monthly Stats (Raw SQL - potentially adapt based on DB) ---
            # Note: Using recursive CTE might not be portable. Consider alternatives if needed.
            months_query = text("""
            WITH RECURSIVE months AS (
                SELECT date_trunc('month', now() at time zone 'utc') as month
                UNION ALL
                SELECT date_trunc('month', month - interval '1 month')
                FROM months
                WHERE month > date_trunc('month', now() at time zone 'utc' - interval '6 months')
            )
            SELECT
                months.month,
                COALESCE(COUNT(pe.id), 0) as count
            FROM months
            LEFT JOIN pipeline_executions pe
                ON date_trunc('month', pe.created_at at time zone 'utc') = months.month
            GROUP BY months.month
            ORDER BY months.month DESC;
            """) # Ensure timezone handling is consistent (UTC used here)
            monthly_stats_result_fut = db.execute(months_query)

            # --- Await all futures ---
            (
                total_users, new_users_week, prev_week_users,
                total_docs, new_docs_week, prev_week_docs,
                total_executions, new_executions_week, prev_week_executions,
                recent_activity_result, monthly_stats_result
            ) = await asyncio.gather(
                total_users_fut, new_users_week_fut, prev_week_users_fut,
                total_docs_fut, new_docs_week_fut, prev_week_docs_fut,
                total_executions_fut, new_executions_week_fut, prev_week_executions_fut,
                recent_activity_result_fut, monthly_stats_result_fut
            )

            # --- Process Results ---
            users_change = self._calculate_percentage_change(new_users_week, prev_week_users)
            docs_change = self._calculate_percentage_change(new_docs_week, prev_week_docs)
            executions_change = self._calculate_percentage_change(new_executions_week, prev_week_executions)

            recent_activity = [
                {
                    "id": str(row.id),
                    "document_name": row.document_name,
                    "document_type": row.document_type,
                    "status": row.status.value if hasattr(row.status, 'value') else str(row.status), # Handle enum
                    "time_ago": self._format_time_ago(row.created_at)
                } for row in recent_activity_result
            ]

            # Process monthly stats, ensuring correct month order if needed
            monthly_stats_raw = {row.month.strftime('%Y-%m'): row.count for row in monthly_stats_result}
            # Generate last 6 months keys in order if needed for frontend chart consistency
            monthly_keys_ordered = [(datetime.utcnow() - timedelta(days=30 * i)).strftime('%Y-%m') for i in range(5, -1, -1)]
            monthly_stats_ordered = {key.split('-')[1]: monthly_stats_raw.get(key, 0) for key in monthly_keys_ordered} # Use month number or abbreviation


            dashboard_data = {
                "users": {"total": total_users, "new_week": new_users_week, "change": round(users_change, 1)},
                "documents": {"total": total_docs, "new_week": new_docs_week, "change": round(docs_change, 1)},
                "executions": {"total": total_executions, "new_week": new_executions_week, "change": round(executions_change, 1)},
                "recent_activity": recent_activity,
                "monthly_stats": monthly_stats_ordered # Return ordered dict
            }
            logger.info("Dashboard statistics calculated successfully.")
            return dashboard_data

        except Exception as e:
            logger.error(f"Error calculating dashboard statistics: {e}", exc_info=True)
            # Re-raise a specific service error or the original exception
            raise RuntimeError("Failed to calculate dashboard statistics") from e

    async def get_analytics_data(self, db: AsyncSession) -> Dict[str, Any]:
        """Calculates and returns data for the detailed analytics page."""
        logger.info("Calculating analytics statistics...")
        try:
            year_ago = datetime.utcnow() - timedelta(days=365)

            # --- Monthly Counts ---
            async def fetch_monthly_counts(model_cls, date_column):
                month_trunc = func.date_trunc('month', date_column).label('month') # Define labeled expression
                query = (
                    select(
                        month_trunc, # Use labeled expression
                        func.count().label('count')
                    )
                    .where(date_column >= year_ago)
                    .group_by(month_trunc) # Group by the same labeled expression
                    .order_by('month') # Order by the label
                )
                result = await db.execute(query)
                return {row.month.strftime('%Y-%m'): row.count for row in result}

            users_data_fut = fetch_monthly_counts(User, User.created_at)
            docs_data_fut = fetch_monthly_counts(Document, Document.created_at)
            executions_data_fut = fetch_monthly_counts(PipelineExecution, PipelineExecution.created_at)

            # --- Document Type Distribution ---
            doc_types_query = (
                select(
                    Document.type,
                    func.count().label('count')
                )
                .group_by(Document.type)
            )
            doc_types_result_fut = db.execute(doc_types_query)

            # --- Weekly Data (Last 7 days by day) ---
             # Example for executions (adapt for users/docs if needed)
            # Use DB-specific functions for day of week if possible (e.g., EXTRACT(isodow FROM ...) for postgres)
            # This example uses Python processing after fetching daily counts
            seven_days_ago = datetime.utcnow().date() - timedelta(days=6) # Include today
            day_trunc = func.date(PipelineExecution.created_at.op('at time zone')('utc')).label('day') # Define labeled expression
            daily_executions_query = (\
                select(\
                     day_trunc, # Use labeled expression\
                     func.count().label('count')\
                )\
                .where(PipelineExecution.created_at >= seven_days_ago)\
                .group_by(day_trunc) # Group by the same labeled expression\
                .order_by('day') # Order by the label\
            ) # Added closing parenthesis
            daily_executions_result_fut = db.execute(daily_executions_query)


            # --- Await Futures ---
            (
                users_data, docs_data, executions_data,
                doc_types_result, daily_executions_result
            ) = await asyncio.gather(
                 users_data_fut, docs_data_fut, executions_data_fut,
                 doc_types_result_fut, daily_executions_result_fut
            )

            # --- Process Results ---
            doc_types_data = {row.type or "Unknown": row.count for row in doc_types_result} # Handle null type
            total_docs = sum(doc_types_data.values())
            doc_types_percentage = {
                doc_type: round((count / total_docs) * 100, 1)
                for doc_type, count in doc_types_data.items()
            } if total_docs > 0 else {}

            # Process daily data into weekly counts (Sun=0, Mon=1...)
            weekly_executions = [0] * 7
            for row in daily_executions_result:
                 day_index = row.day.weekday() # Monday is 0, Sunday is 6
                 weekly_executions[day_index] += row.count
            # Shift to Sun=0 if needed by frontend: weekly_executions = weekly_executions[-1:] + weekly_executions[:-1]


            analytics_data = {
                "monthly": {
                    "users": users_data,
                    "documents": docs_data,
                    "executions": executions_data,
                },
                "document_types": {
                    "counts": doc_types_data,
                    "percentages": doc_types_percentage,
                },
                "weekly": {
                    "executions": weekly_executions, # List indexed Sun-Sat or Mon-Sun
                    "users": [0]*7 # TODO: Add actual weekly user calculation
                },
                 # TODO: Add popular_queries data 
            }
            logger.info("Analytics statistics calculated successfully.")
            return analytics_data

        except Exception as e:
            logger.error(f"Error calculating analytics statistics: {e}", exc_info=True)
            raise RuntimeError("Failed to calculate analytics statistics") from e
