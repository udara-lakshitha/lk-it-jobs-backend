from abc import ABC, abstractmethod
from typing import List
from app.schemas import JobCreate

class BaseJobParser(ABC):
    source_name: str = "Base"

    @abstractmethod
    async def fetch_jobs(self) -> List[JobCreate]:
        pass