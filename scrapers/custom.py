"""Custom company career page scraper."""

import re
from bs4 import BeautifulSoup

from .base import BaseScraper, Job


class CustomScraper(BaseScraper):
    """Scraper for custom company career pages with configurable selectors."""

    @property
    def platform_name(self) -> str:
        return "Custom"

    def scrape(self, source: dict, keywords: list[str]) -> list[Job]:
        """
        Scrape jobs from a custom career page.

        Args:
            source: Dict with 'name', 'url', 'type', and optionally 'selectors'
            keywords: List of keywords to filter jobs

        Returns:
            List of matching Job objects
        """
        company_name = source.get("name", "Unknown")
        url = source.get("url", "")
        source_type = source.get("type", "custom")
        selectors = source.get("selectors", {})

        if not url:
            print(f"[Custom] Missing URL for {company_name}")
            return []

        # If it's actually a workday site, delegate
        if source_type == "workday":
            from .workday import WorkdayScraper
            workday_scraper = WorkdayScraper(rate_limit_delay=self.rate_limit_delay)
            return workday_scraper.scrape({"tenant": company_name, "subdomain": url}, keywords)

        try:
            response = self.get(url)
            response.raise_for_status()
        except Exception as e:
            print(f"[Custom] Error fetching {company_name}: {e}")
            return []

        soup = BeautifulSoup(response.text, "lxml")
        jobs = []

        # Use configured selectors or try common patterns
        job_card_selector = selectors.get("job_card", None)
        title_selector = selectors.get("title", None)
        location_selector = selectors.get("location", None)
        link_selector = selectors.get("link", "a")

        # Find job cards
        if job_card_selector:
            job_cards = soup.select(job_card_selector)
        else:
            # Try common patterns
            job_cards = (
                soup.find_all(class_=re.compile(r"job[-_]?(card|listing|item|post)", re.I)) or
                soup.find_all(class_=re.compile(r"opening|position|vacancy", re.I)) or
                soup.find_all("article", class_=re.compile(r"job", re.I)) or
                []
            )

        for card in job_cards:
            try:
                # Get title
                if title_selector:
                    title_elem = card.select_one(title_selector)
                else:
                    title_elem = (
                        card.find(class_=re.compile(r"title|name", re.I)) or
                        card.find(["h2", "h3", "h4", "h5"])
                    )

                if not title_elem:
                    continue

                title = title_elem.text.strip()
                if not title or len(title) < 3:
                    continue

                # Get link
                link_elem = card.select_one(link_selector) if link_selector else card.find("a", href=True)
                if not link_elem:
                    link_elem = title_elem.find_parent("a") or title_elem.find("a")

                job_url = ""
                if link_elem and link_elem.get("href"):
                    job_url = link_elem.get("href")
                    if job_url.startswith("/"):
                        # Make absolute URL
                        from urllib.parse import urljoin
                        job_url = urljoin(url, job_url)

                if not job_url:
                    continue

                # Get location
                location = "Unknown"
                if location_selector:
                    loc_elem = card.select_one(location_selector)
                else:
                    loc_elem = card.find(class_=re.compile(r"location|place|city", re.I))

                if loc_elem:
                    location = loc_elem.text.strip()

                job = Job(
                    company=company_name,
                    company_url=url,
                    title=title,
                    location=location,
                    url=job_url,
                )

                if job.matches_keywords(keywords) and job.is_entry_or_mid_level():
                    jobs.append(job)

            except Exception as e:
                continue

        print(f"[Custom] Found {len(jobs)} matching jobs at {company_name}")
        return jobs
