from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from app.database import get_db
from app.schemas import PaginatedJobsResponse
import app.crud as crud

router = APIRouter(prefix="/api/jobs", tags=["Jobs"])

@router.get("/", response_model=PaginatedJobsResponse)
async def list_jobs(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    domain: Optional[str] = Query(None),
    company: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    timeframe_months: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    return await crud.get_jobs(
        db=db,
        page=page,
        limit=limit,
        domain=domain,
        company=company,
        search=search,
        timeframe_months=timeframe_months
    )