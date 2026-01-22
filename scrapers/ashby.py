"""Ashby HQ job board scraper."""

import json
from bs4 import BeautifulSoup

from .base import BaseScraper, Job


class AshbyScraper(BaseScraper):
    """Scraper for Ashby job boards (jobs.ashbyhq.com)."""

    BASE_URL = "https://jobs.ashbyhq.com"

    @property
    def platform_name(self) -> str:
        return "Ashby"

    def scrape(self, source: str | dict, keywords: list[str]) -> list[Job]:
        """
        Scrape jobs from an Ashby job board.

        Args:
            source: Company slug (e.g., 'cruise' for jobs.ashbyhq.com/cruise)
            keywords: List of keywords to filter jobs

        Returns:
            List of matching Job objects
        """
        company_slug = source if isinstance(source, str) else source.get("slug", source)
        url = f"{self.BASE_URL}/{company_slug}"

        try:
            response = self.get(url)
            response.raise_for_status()
        except Exception as e:
            print(f"[Ashby] Error fetching {company_slug}: {e}")
            return []

        soup = BeautifulSoup(response.text, "lxml")
        jobs = []

        # Get company name
        company_name = company_slug.replace("-", " ").title()
        title_tag = soup.find("title")
        if title_tag:
            title_text = title_tag.text.strip()
            if " - " in title_text:
                company_name = title_text.split(" - ")[0].strip()

        # Try to find job data in script tags (Ashby often uses JSON)
        scripts = soup.find_all("script")
        for script in scripts:
            if script.string and "jobPostings" in script.string:
                try:
                    # Extract JSON from script
                    import re
                    json_match = re.search(r'jobPostings["\']?\s*:\s*(\[.*?\])', script.string, re.DOTALL)
                    if json_match:
                        job_data = json.loads(json_match.group(1))
                        for item in job_data:
                            title = item.get("title", "")
                            location = item.get("location", {}).get("name", "Unknown")
                            job_id = item.get("id", "")
                            job_url = f"{url}/{job_id}" if job_id else url

                            job = Job(
                                company=company_name,
                                company_url=url,
                                title=title,
                                location=location,
                                url=job_url,
                            )

                            if job.matches_keywords(keywords) and job.is_entry_or_mid_level():
                                jobs.append(job)
                except (json.JSONDecodeError, AttributeError):
                    pass

        # Fallback: Parse HTML job listings
        if not jobs:
            job_cards = soup.find_all("a", href=True, class_=lambda x: x and "job" in x.lower() if x else False)
            if not job_cards:
                job_cards = soup.find_all("div", class_=lambda x: x and ("posting" in x.lower() or "job" in x.lower()) if x else False)

            for card in job_cards:
                try:
                    # Get title
                    title_elem = card.find(["h2", "h3", "h4", "span"], class_=lambda x: x and "title" in x.lower() if x else False)
                    if not title_elem:
                        title_elem = card.find(["h2", "h3", "h4"])
                    
                    if not title_elem:
                        continue

                    title = title_elem.text.strip()
                    if not title:
                        continue

                    # Get URL
                    if card.name == "a":
                        job_url = card.get("href", "")
                    else:
                        link = card.find("a", href=True)
                        job_url = link.get("href", "") if link else ""

                    if job_url and not job_url.startswith("http"):
                        job_url = f"{self.BASE_URL}{job_url}"

                    # Get location
                    location = "Unknown"
                    loc_elem = card.find(class_=lambda x: x and "location" in x.lower() if x else False)
                    if loc_elem:
                        location = loc_elem.text.strip()

                    job = Job(
                        company=company_name,
                        company_url=url,
                        title=title,
                        location=location,
                        url=job_url if job_url else url,
                    )

                    if job.matches_keywords(keywords) and job.is_entry_or_mid_level():
                        jobs.append(job)

                except Exception:
                    continue

        print(f"[Ashby] Found {len(jobs)} matching jobs at {company_name}")
        return jobs
