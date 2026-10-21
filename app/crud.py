import os
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func, desc, or_
from datetime import datetime, timedelta
from typing import Optional, List
from app.models import Job
from app.schemas import JobCreate

async def get_jobs(
    db: AsyncSession,
    page: int = 1,
    limit: int = 10,
    domain: Optional[str] = None,
    company: Optional[str] = None,
    search: Optional[str] = None,
    timeframe_months: Optional[int] = None
):
    if timeframe_months is None:
        timeframe_months = int(os.getenv("SCRAPE_TIMEFRAME_MONTHS", 3))

    threshold_date = datetime.utcnow() - timedelta(days=timeframe_months * 30)
    query = select(Job).where(Job.posted_date >= threshold_date)

    if domain:
        query = query.where(Job.domain.ilike(f"%{domain}%"))
    if company:
        query = query.where(Job.company_name.ilike(f"%{company}%"))
    if search:
        query = query.where(
            or_(
                Job.title.ilike(f"%{search}%"),
                Job.professional_req.ilike(f"%{search}%"),
                Job.education_req.ilike(f"%{search}%")
            )
        )

    count_query = select(func.count()).select_from(query.subquery())
    total_res = await db.execute(count_query)
    total = total_res.scalar_one()

    offset = (page - 1) * limit
    query = query.order_by(desc(Job.posted_date)).offset(offset).limit(limit)
    res = await db.execute(query)
    jobs = res.scalars().all()

    total_pages = (total + limit - 1) // limit if total > 0 else 1

    return {
        "total": total,
        "page": page,
        "limit": limit,
        "total_pages": total_pages,
        "data": jobs
    }

async def create_job_bulk(db: AsyncSession, jobs: List[JobCreate]):
    inserted_count = 0
    updated_count = 0

    for job_data in jobs:
        try:
            existing_res = await db.execute(select(Job).where(Job.job_url == job_data.job_url))
            existing = existing_res.scalar_one_or_none()

            if existing:
                existing.title = job_data.title
                existing.company_name = job_data.company_name
                existing.domain = job_data.domain
                existing.location = job_data.location
                existing.education_req = job_data.education_req
                existing.professional_req = job_data.professional_req
                updated_count += 1
            else:
                db_job = Job(**job_data.model_dump())
                db.add(db_job)
                inserted_count += 1
        except Exception as e:
            print(f"Error processing job entry {job_data.title}: {e}")

    await db.commit()
    print(f"Database Sync Result -> Inserted: {inserted_count} | Updated: {updated_count}")

async def get_analytics_summary(db: AsyncSession, timeframe_months: int):
    threshold_date = datetime.utcnow() - timedelta(days=timeframe_months * 30)
    base_query = select(Job).where(Job.posted_date >= threshold_date)

    total_jobs_res = await db.execute(select(func.count()).select_from(base_query.subquery()))
    total_jobs = total_jobs_res.scalar_one()

    total_companies_res = await db.execute(
        select(func.count(func.distinct(Job.company_name))).where(Job.posted_date >= threshold_date)
    )
    total_companies = total_companies_res.scalar_one()

    top_domains_res = await db.execute(
        select(Job.domain, func.count(Job.id).label("count"))
        .where(Job.posted_date >= timeframe_months * 30)
        .group_by(Job.domain)
        .order_by(desc("count"))
        .limit(10)
    )
    top_domains = [{"domain": r[0], "count": r[1]} for r in top_domains_res.all()]

    top_companies_res = await db.execute(
        select(Job.company_name, func.count(Job.id).label("count"))
        .where(Job.posted_date >= timeframe_months * 30)
        .group_by(Job.company_name)
        .order_by(desc("count"))
        .limit(10)
    )
    top_companies = [{"company_name": r[0], "count": r[1]} for r in top_companies_res.all()]

    return {
        "total_jobs": total_jobs,
        "total_companies": total_companies,
        "top_domains": top_domains,
        "top_companies": top_companies
    }