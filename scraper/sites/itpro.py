from datetime import datetime
import re
import httpx
from bs4 import BeautifulSoup
from scraper.base_parser import BaseJobParser
from app.schemas import JobCreate

class ITProParser(BaseJobParser):
    source_name = "itpro.lk"
    target_url = "https://itpro.lk/jobs/"

    def _classify_domain(self, title: str) -> str:
        title_lower = title.lower()
        if "qa" in title_lower or "test" in title_lower or "quality" in title_lower:
            return "Quality Assurance"
        if "data" in title_lower or "analyst" in title_lower or "ai" in title_lower:
            return "Data & Analytics"
        if "devops" in title_lower or "cloud" in title_lower or "sysadmin" in title_lower:
            return "DevOps & Cloud"
        if "ui" in title_lower or "ux" in title_lower or "designer" in title_lower:
            return "UI/UX Design"
        if "marketing" in title_lower or "growth" in title_lower:
            return "Digital Marketing"
        return "Software Engineering"

    def _sanitize_company_name(self, raw_name: str, title: str) -> str:
        if not raw_name:
            return "Sri Lankan Tech Employer"
        
        # Remove trailing attached locations/types like "CodimiteColombo" -> "Codimite", "Kangaro TechRemote" -> "Kangaro Tech"
        unwanted_suffixes = [
            "colombo", "remote", "hybrid", "kandy", "gampaha", "kurunegala", 
            "jaffna", "galle", "negombo", "malabe", "nugegoda", "biyagama", 
            "full-time", "internship", "part-time", "contract"
        ]
        
        cleaned = raw_name.strip()
        cleaned_lower = cleaned.lower()
        
        for suffix in unwanted_suffixes:
            if cleaned_lower.endswith(suffix):
                # Cut off the suffix
                cleaned = cleaned[:-len(suffix)].strip()
                cleaned_lower = cleaned.lower()
                
        if not cleaned or cleaned.lower() == "tech company" or cleaned == title:
            return "Sri Lankan Tech Employer"
            
        return cleaned

    def _extract_company_name(self, card_soup, detail_soup, full_text: str, title: str) -> str:
        raw_name = ""

        # 1. Search card elements
        for tag in card_soup.select("span, div, a, p, small, h4, h5"):
            cls = " ".join(tag.get("class", []))
            if any(k in cls.lower() for k in ["company", "employer", "badge", "subtitle", "author"]):
                txt = tag.get_text(strip=True)
                if txt and txt.lower() != "tech company" and txt != title and len(txt) > 1:
                    raw_name = txt
                    break

        # 2. Check detail page header metadata
        if not raw_name and detail_soup:
            for tag in detail_soup.select(".company-name, .employer-name, .job-company, .employer, .company-title, h4"):
                txt = tag.get_text(strip=True)
                if txt and txt.lower() != "tech company" and txt != title and len(txt) > 1:
                    raw_name = txt
                    break

        # 3. Fallback to text line analysis
        if not raw_name:
            lines = [line.strip() for line in full_text.split("\n") if line.strip()]
            for line in lines[:10]:
                line_lower = line.lower()
                if line_lower.startswith("company:") or line_lower.startswith("employer:"):
                    parts = line.split(":", 1)
                    if len(parts) > 1 and len(parts[1].strip()) > 1:
                        raw_name = parts[1].strip()
                        break

                match = re.match(r"^([A-Z0-9a-zA-Z\s&.,-]+?)\s+(?:is looking for|is seeking|is a|seeks|hiring)", line)
                if match:
                    comp = match.group(1).strip()
                    if comp.lower() not in ["we", "our client", "company", "the company", title.lower()]:
                        raw_name = comp
                        break

        return self._sanitize_company_name(raw_name, title)

    def _extract_section(self, text: str, keywords: list) -> str:
        lines = text.split("\n")
        extracted_lines = []
        capturing = False

        for line in lines:
            line_lower = line.lower().strip()
            if any(kw in line_lower for kw in keywords):
                capturing = True
                continue
            elif capturing:
                if any(header in line_lower for header in ["about", "responsibilities", "how to apply", "what you'll gain", "benefits", "contact"]):
                    break
                if line.strip():
                    extracted_lines.append(line.strip())

        return "\n".join(extracted_lines[:10]) if extracted_lines else "Refer to original listing"

    async def fetch_jobs(self) -> list[JobCreate]:
        jobs = []
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        }

        print(f"Fetching job listings from {self.target_url}...")
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            try:
                response = await client.get(self.target_url, headers=headers)
                if response.status_code != 200:
                    print(f"Failed to fetch {self.target_url}, status code: {response.status_code}")
                    return jobs

                soup = BeautifulSoup(response.text, "html.parser")
                job_cards = soup.select(".job-listing, article, .card, .views-row, div.job")
                if not job_cards:
                    job_cards = soup.find_all("div", class_=lambda x: x and ("job" in x.lower() or "card" in x.lower()))

                print(f"Found {len(job_cards)} listings. Parsing structured fields...")

                for card in job_cards:
                    title_elem = card.select_one("h2, h3, a.job-title, .title, h5")
                    location_elem = card.select_one(".location, .job-location, .fa-map-marker")
                    link_elem = card.select_one("a")

                    if title_elem and link_elem:
                        title = title_elem.get_text(strip=True)
                        location = location_elem.get_text(strip=True) if location_elem else "Colombo"
                        job_url = link_elem.get("href", "")
                        
                        if job_url and not job_url.startswith("http"):
                            job_url = f"https://itpro.lk{job_url}"

                        full_text = ""
                        detail_soup = None
                        if job_url:
                            try:
                                detail_res = await client.get(job_url, headers=headers)
                                if detail_res.status_code == 200:
                                    detail_soup = BeautifulSoup(detail_res.text, "html.parser")
                                    content_box = detail_soup.select_one(".job-description, .content-body, .node__content, .job-details, article")
                                    if content_box:
                                        full_text = content_box.get_text(separator="\n", strip=True)
                            except Exception:
                                pass

                        company = self._extract_company_name(card, detail_soup, full_text, title)
                        
                        education_req = self._extract_section(full_text, ["education", "qualification", "degree", "undergraduate", "bachelor"])
                        if education_req == "Refer to original listing":
                            for line in full_text.split("\n"):
                                if any(term in line.lower() for term in ["bsc", "b.sc", "degree", "diploma", "undergraduate", "graduate"]):
                                    education_req = line.strip()
                                    break

                        professional_req = self._extract_section(full_text, ["requirements", "skills", "experience", "key responsibilities", "profile"])
                        if professional_req == "Refer to original listing" and full_text:
                            professional_req = full_text[:1200]

                        job_item = JobCreate(
                            title=title,
                            company_name=company,
                            domain=self._classify_domain(title),
                            location=location if location else "Colombo",
                            education_req=education_req,
                            professional_req=professional_req,
                            job_url=job_url,
                            posted_date=datetime.utcnow(),
                            source=self.source_name
                        )
                        jobs.append(job_item)

            except Exception as e:
                print(f"Error scraping {self.source_name}: {e}")

        print(f"Successfully processed and normalized {len(jobs)} jobs.")
        return jobs