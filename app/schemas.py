from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List

class JobBase(BaseModel):
    title: str
    company_name: str
    domain: str
    location: str
    education_req: Optional[str] = None
    professional_req: Optional[str] = None
    job_url: str
    posted_date: Optional[datetime] = None
    source: str

class JobCreate(JobBase):
    pass

class JobResponse(JobBase):
    id: int

    class Config:
        from_attributes = True

class PaginatedJobsResponse(BaseModel):
    total: int
    page: int
    limit: int
    total_pages: int
    data: List[JobResponse]

class AnalyticsResponse(BaseModel):
    total_jobs: int
    total_companies: int
    top_domains: List[dict]
    top_companies: List[dict]

AnalyticsSummary = AnalyticsResponse