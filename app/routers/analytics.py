import os
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from app.database import get_db
from app.schemas import AnalyticsSummary
import app.crud as crud

router = APIRouter(prefix="/api/analytics", tags=["Analytics"])

@router.get("/summary", response_model=AnalyticsSummary)
async def get_summary(
    timeframe_months: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    if timeframe_months is None:
        timeframe_months = int(os.getenv("SCRAPE_TIMEFRAME_MONTHS", 3))
    return await crud.get_analytics_summary(db=db, timeframe_months=timeframe_months)