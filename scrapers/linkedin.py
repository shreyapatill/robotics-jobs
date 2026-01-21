"""LinkedIn jobs scraper."""

import urllib.parse
from bs4 import BeautifulSoup

from .base import BaseScraper, Job


class LinkedInScraper(BaseScraper):
    """
    Scraper for LinkedIn job listings.
    
    Note: LinkedIn actively blocks scrapers. This uses public job search pages
    which may have limited reliability. For production use, consider LinkedIn's
    official API.
    """

    BASE_URL = "https://www.linkedin.com/jobs/search"

    @property
    def platform_name(self) -> str:
        return "LinkedIn"

    def scrape(self, source: dict, keywords: list[str]) -> list[Job]:
        """
        Scrape jobs from LinkedIn job search.

        Args:
            source: Dict with 'keywords' and optionally 'location', 'posted_within_days'
            keywords: List of additional keywords to filter jobs (from config)

        Returns:
            List of matching Job objects
        """
        jobs = []
        search_keywords = source.get("keywords", [])
        location = source.get("location", "United States")
        posted_within = source.get("posted_within_days", 7)

        # Map days to LinkedIn's time filter
        time_filter_map = {1: "r86400", 7: "r604800", 30: "r2592000"}
        time_filter = time_filter_map.get(posted_within, "r604800")

        for search_term in search_keywords:
            try:
                params = {
                    "keywords": search_term,
                    "location": location,
                    "f_TPR": time_filter,
                    "position": 1,
                    "pageNum": 0,
                }
                url = f"{self.BASE_URL}?{urllib.parse.urlencode(params)}"

                response = self.get(url)
                response.raise_for_status()

                soup = BeautifulSoup(response.text, "lxml")

                # Find job cards
                job_cards = soup.find_all("div", class_="base-card")

                for card in job_cards:
                    try:
                        # Get title
                        title_tag = card.find("h3", class_="base-search-card__title")
                        if not title_tag:
                            continue
                        title = title_tag.text.strip()

                        # Get company
                        company_tag = card.find("h4", class_="base-search-card__subtitle")
                        company = company_tag.text.strip() if company_tag else "Unknown"

                        # Get location
                        location_tag = card.find("span", class_="job-search-card__location")
                        job_location = location_tag.text.strip() if location_tag else "Unknown"

                        # Get job URL
                        link_tag = card.find("a", class_="base-card__full-link")
                        job_url = link_tag.get("href", "") if link_tag else ""

                        if not job_url:
                            continue

                        job = Job(
                            company=company,
                            company_url=f"https://www.linkedin.com/company/{urllib.parse.quote(company.lower().replace(' ', '-'))}",
                            title=title,
                            location=job_location,
                            url=job_url.split("?")[0],  # Remove tracking params
                        )

                        # Filter by config keywords if any additionally specified
                        if not keywords or job.matches_keywords(keywords):
                            jobs.append(job)

                    except Exception as e:
                        print(f"[LinkedIn] Error parsing job card: {e}")
                        continue

            except Exception as e:
                print(f"[LinkedIn] Error searching '{search_term}': {e}")
                continue

        # Deduplicate by URL
        seen_urls = set()
        unique_jobs = []
        for job in jobs:
            if job.url not in seen_urls:
                seen_urls.add(job.url)
                unique_jobs.append(job)

        print(f"[LinkedIn] Found {len(unique_jobs)} matching jobs")
        return unique_jobs
