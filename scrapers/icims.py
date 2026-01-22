"""iCIMS job board scraper."""

import re
from bs4 import BeautifulSoup

from .base import BaseScraper, Job


class ICIMSScraper(BaseScraper):
    """Scraper for iCIMS job boards (careers-{company}.icims.com)."""

    @property
    def platform_name(self) -> str:
        return "iCIMS"

    def scrape(self, source: dict, keywords: list[str]) -> list[Job]:
        """
        Scrape jobs from an iCIMS job board.

        Args:
            source: Dict with 'name' and 'url' (e.g., careers-company.icims.com)
            keywords: List of keywords to filter jobs

        Returns:
            List of matching Job objects
        """
        company_name = source.get("name", "Unknown")
        base_url = source.get("url", "")

        if not base_url:
            print(f"[iCIMS] Missing URL for {company_name}")
            return []

        # Ensure URL has protocol
        if not base_url.startswith("http"):
            base_url = f"https://{base_url}"

        try:
            response = self.get(base_url)
            response.raise_for_status()
        except Exception as e:
            print(f"[iCIMS] Error fetching {company_name}: {e}")
            return []

        soup = BeautifulSoup(response.text, "lxml")
        jobs = []

        # iCIMS uses various structures, try common patterns
        job_containers = (
            soup.find_all("div", class_=re.compile(r"iCIMS_JobsTable|job-?listing|job-?row", re.I)) or
            soup.find_all("tr", class_=re.compile(r"job", re.I)) or
            soup.find_all("li", class_=re.compile(r"job", re.I)) or
            soup.find_all("article", class_=re.compile(r"job", re.I))
        )

        for container in job_containers:
            try:
                # Get job title and link
                title_link = container.find("a", href=re.compile(r"job|position|requisition", re.I))
                if not title_link:
                    title_link = container.find("a", class_=re.compile(r"title", re.I))
                if not title_link:
                    title_link = container.find("a", href=True)

                if not title_link:
                    continue

                title = title_link.text.strip()
                if not title or len(title) < 3:
                    continue

                job_url = title_link.get("href", "")
                if job_url and not job_url.startswith("http"):
                    # Handle relative URLs
                    from urllib.parse import urljoin
                    job_url = urljoin(base_url, job_url)

                # Get location
                location = "Unknown"
                loc_elem = container.find(class_=re.compile(r"location|city", re.I))
                if not loc_elem:
                    loc_elem = container.find("span", string=re.compile(r"[A-Z]{2}$|\w+,\s*\w+"))
                if loc_elem:
                    location = loc_elem.text.strip()

                job = Job(
                    company=company_name,
                    company_url=base_url,
                    title=title,
                    location=location,
                    url=job_url,
                )

                if job.matches_keywords(keywords) and job.is_entry_or_mid_level():
                    jobs.append(job)

            except Exception:
                continue

        # Fallback: Look for job links directly
        if not jobs:
            all_links = soup.find_all("a", href=re.compile(r"/jobs/|/job/|requisition", re.I))
            seen_urls = set()

            for link in all_links:
                try:
                    title = link.text.strip()
                    if not title or len(title) < 5:
                        continue

                    job_url = link.get("href", "")
                    if job_url in seen_urls:
                        continue
                    seen_urls.add(job_url)

                    if not job_url.startswith("http"):
                        from urllib.parse import urljoin
                        job_url = urljoin(base_url, job_url)

                    job = Job(
                        company=company_name,
                        company_url=base_url,
                        title=title,
                        location="Unknown",
                        url=job_url,
                    )

                    if job.matches_keywords(keywords) and job.is_entry_or_mid_level():
                        jobs.append(job)

                except Exception:
                    continue

        print(f"[iCIMS] Found {len(jobs)} matching jobs at {company_name}")
        return jobs
