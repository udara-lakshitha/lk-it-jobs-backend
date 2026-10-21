import random
from datetime import datetime
from typing import List
from playwright.async_api import async_playwright
from scraper.base_parser import BaseJobParser
from app.schemas import JobCreate

class TopJobsParser(BaseJobParser):
    source_name = "topjobs.lk"
    target_url = "https://www.topjobs.lk/applicant/vacancybyfunctionalarea.jsp?FA=HNS"

    def _classify_domain(self, title: str) -> str:
        title_lower = title.lower()
        if "qa" in title_lower or "test" in title_lower or "quality assurance" in title_lower:
            return "Quality Assurance"
        if "data" in title_lower or "analyst" in title_lower or ("engineer" in title_lower and "data" in title_lower):
            return "Data & Analytics"
        if "devops" in title_lower or "cloud" in title_lower or "sysadmin" in title_lower or "infrastructure" in title_lower:
            return "DevOps & Cloud"
        if "ui" in title_lower or "ux" in title_lower or "designer" in title_lower:
            return "UI/UX Design"
        return "Software Engineering"

    async def fetch_jobs(self) -> List[JobCreate]:
        jobs = []
        # Run with headless=False temporarily if you want to watch it run locally in a browser window
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                viewport={"width": 1920, "height": 1080}
            )
            page = await context.new_page()

            try:
                print(f"Navigating to {self.target_url}...")
                await page.goto(self.target_url, timeout=60000)
                await page.wait_for_timeout(5000) # Give time for JS tables to render

                # Take a debug screenshot to verify what the browser actually loaded
                await page.screenshot(path="debug_topjobs.png")

                # Try selecting all rows or table links
                rows = await page.query_selector_all("tr")
                print(f"Found {len(rows)} table rows on the page.")

                for row in rows:
                    cols = await row.query_selector_all("td")
                    if len(cols) >= 3:
                        text_content = await cols[2].inner_text() if len(cols) > 2 else ""
                        if not text_content.strip():
                            continue
                        
                        lines = [l.strip() for l in text_content.split("\n") if l.strip()]
                        title = lines[0] if len(lines) > 0 else "Software Engineer"
                        company = lines[1] if len(lines) > 1 else "Unknown Company"
                        
                        link_elem = await cols[1].query_selector("a") if len(cols) > 1 else None
                        job_url = await link_elem.get_attribute("href") if link_elem else None
                        
                        if job_url:
                            if not job_url.startswith("http"):
                                job_url = f"https://www.topjobs.lk/applicant/{job_url}"
                        else:
                            job_url = f"https://topjobs.lk/job-{random.randint(100000,999999)}"

                        town = await cols[6].inner_text() if len(cols) > 6 else "Colombo"

                        job_item = JobCreate(
                            title=title,
                            company_name=company,
                            domain=self._classify_domain(title),
                            salary_min=None,
                            salary_max=None,
                            currency="LKR",
                            location=town.strip() if town.strip() else "Colombo",
                            education_req="Please refer to original advertisement",
                            professional_req="Please refer to original advertisement",
                            job_url=job_url,
                            posted_date=datetime.utcnow(),
                            source=self.source_name
                        )
                        jobs.append(job_item)

            except Exception as e:
                print(f"Error scraping {self.source_name}: {e}")
            finally:
                await browser.close()

        print(f"Extracted {len(jobs)} valid job items from parser.")
        return jobs