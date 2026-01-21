"""Workday job board scraper."""

import json
import re
from bs4 import BeautifulSoup

from .base import BaseScraper, Job


class WorkdayScraper(BaseScraper):
    """Scraper for Workday job boards ({tenant}.wd{n}.myworkdayjobs.com)."""

    @property
    def platform_name(self) -> str:
        return "Workday"

    def scrape(self, source: dict, keywords: list[str]) -> list[Job]:
        """
        Scrape jobs from a Workday job board.

        Args:
            source: Dict with 'tenant' and 'subdomain' keys
            keywords: List of keywords to filter jobs

        Returns:
            List of matching Job objects
        """
        tenant = source.get("tenant", "")
        subdomain = source.get("subdomain", "")

        if not subdomain:
            print(f"[Workday] Missing subdomain for {tenant}")
            return []

        # Construct base URL
        if not subdomain.startswith("http"):
            base_url = f"https://{subdomain}"
        else:
            base_url = subdomain

        jobs = []

        try:
            response = self.get(base_url)
            response.raise_for_status()
        except Exception as e:
            print(f"[Workday] Error fetching {tenant}: {e}")
            return []

        soup = BeautifulSoup(response.text, "lxml")

        # Get company name
        company_name = tenant.replace("-", " ").title()
        title_tag = soup.find("title")
        if title_tag:
            company_name = title_tag.text.split(" - ")[0].split(" | ")[0].strip()
            if "Career" in company_name or "Job" in company_name:
                company_name = tenant.replace("-", " ").title()

        # Try to find job listings - Workday uses various structures

        # Method 1: Look for job data in script tags (common API pattern)
        scripts = soup.find_all("script", type="application/ld+json")
        for script in scripts:
            try:
                data = json.loads(script.string)
                if isinstance(data, dict) and data.get("@type") == "JobPosting":
                    job = self._parse_json_ld_job(data, company_name, base_url, keywords)
                    if job:
                        jobs.append(job)
                elif isinstance(data, list):
                    for item in data:
                        if isinstance(item, dict) and item.get("@type") == "JobPosting":
                            job = self._parse_json_ld_job(item, company_name, base_url, keywords)
                            if job:
                                jobs.append(job)
            except (json.JSONDecodeError, TypeError):
                continue

        # Method 2: Parse HTML job listings
        job_elements = soup.find_all(["li", "div", "article"], class_=re.compile(r"job|posting|position", re.I))

        for element in job_elements:
            try:
                # Look for title link
                title_link = element.find("a", href=re.compile(r"job|position|career", re.I))
                if not title_link:
                    continue

                title = title_link.text.strip()
                if not title or len(title) < 3:
                    continue

                job_url = title_link.get("href", "")
                if job_url.startswith("/"):
                    job_url = f"{base_url.rstrip('/')}{job_url}"

                # Get location
                location = "Unknown"
                location_elem = element.find(class_=re.compile(r"location", re.I))
                if location_elem:
                    location = location_elem.text.strip()

                job = Job(
                    company=company_name,
                    company_url=base_url,
                    title=title,
                    location=location,
                    url=job_url,
                )

                if job.matches_keywords(keywords):
                    jobs.append(job)

            except Exception as e:
                continue

        # Deduplicate
        seen = set()
        unique_jobs = []
        for job in jobs:
            if job.url not in seen:
                seen.add(job.url)
                unique_jobs.append(job)

        print(f"[Workday] Found {len(unique_jobs)} matching jobs at {company_name}")
        return unique_jobs

    def _parse_json_ld_job(
        self, data: dict, company_name: str, base_url: str, keywords: list[str]
    ) -> Job | None:
        """Parse a JSON-LD JobPosting object."""
        try:
            title = data.get("title", "")
            if not title:
                return None

            job_url = data.get("url", base_url)

            # Get location
            location = "Unknown"
            job_location = data.get("jobLocation", {})
            if isinstance(job_location, dict):
                address = job_location.get("address", {})
                if isinstance(address, dict):
                    city = address.get("addressLocality", "")
                    state = address.get("addressRegion", "")
                    location = f"{city}, {state}".strip(", ")
            elif isinstance(job_location, list) and job_location:
                first_loc = job_location[0]
                if isinstance(first_loc, dict):
                    address = first_loc.get("address", {})
                    city = address.get("addressLocality", "")
                    state = address.get("addressRegion", "")
                    location = f"{city}, {state}".strip(", ")

            job = Job(
                company=data.get("hiringOrganization", {}).get("name", company_name),
                company_url=base_url,
                title=title,
                location=location if location else "Unknown",
                url=job_url,
            )

            if job.matches_keywords(keywords):
                return job

        except Exception:
            pass

        return None
