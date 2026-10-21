import asyncio
import os
from dotenv import load_dotenv
from app.database import AsyncSessionLocal
import app.crud as crud
from scraper.sites.itpro import ITProParser

load_dotenv()

async def run_all_scrapers():
    parsers = [
        ITProParser(),
    ]

    total_inserted_count = 0

    for parser in parsers:
        print(f"Starting execution for: {parser.source_name}")
        try:
            jobs = await parser.fetch_jobs()
            print(f"Parser returned {len(jobs)} job objects.")
            
            if jobs:
                async with AsyncSessionLocal() as session:
                    await crud.create_job_bulk(session, jobs)
                print(f"Successfully processed {len(jobs)} jobs from {parser.source_name}")
                total_inserted_count += len(jobs)
            else:
                print(f"Warning: Parser for {parser.source_name} returned 0 jobs!")
        except Exception as e:
            print(f"CRITICAL Error running scraper {parser.source_name}: {e}")

    print(f"Scraping cycle complete. Total entries processed: {total_inserted_count}")

if __name__ == "__main__":
    asyncio.run(run_all_scrapers())