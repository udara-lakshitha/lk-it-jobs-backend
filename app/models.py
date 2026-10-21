from sqlalchemy import Column, Integer, String, Text, DateTime
from app.database import Base
from datetime import datetime

class Job(Base):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True, nullable=False)
    company_name = Column(String, index=True, nullable=False)
    domain = Column(String, index=True, nullable=False)
    location = Column(String, nullable=False)
    education_req = Column(Text, nullable=True)
    professional_req = Column(Text, nullable=True)
    job_url = Column(String, unique=True, index=True, nullable=False)
    posted_date = Column(DateTime, default=datetime.utcnow)
    source = Column(String, nullable=False)