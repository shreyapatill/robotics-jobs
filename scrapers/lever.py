"""Lever job board scraper."""

from bs4 import BeautifulSoup

from .base import BaseScraper, Job


class LeverScraper(BaseScraper):
    """Scraper for Lever job boards (jobs.lever.co)."""

    BASE_URL = "https://jobs.lever.co"

    @property
    def platform_name(self) -> str:
        return "Lever"

    def scrape(self, source: str | dict, keywords: list[str]) -> list[Job]:
        """
        Scrape jobs from a Lever job board.

        Args:
            source: Company slug (e.g., 'zoox' for jobs.lever.co/zoox)
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
            print(f"[Lever] Error fetching {company_slug}: {e}")
            return []

        soup = BeautifulSoup(response.text, "lxml")
        jobs = []

        # Get company name from page
        company_name = company_slug.replace("-", " ").title()
        header = soup.find("div", class_="main-header-content")
        if header:
            company_tag = header.find("h1")
            if company_tag:
                company_name = company_tag.text.strip()

        # Find all job postings
        postings = soup.find_all("div", class_="posting")

        for posting in postings:
            try:
                # Get job title and link
                title_tag = posting.find("a", class_="posting-title")
                if not title_tag:
                    title_tag = posting.find("h5")

                if not title_tag:
                    continue

                title = title_tag.text.strip()

                # Get job URL
                link_tag = posting.find("a", href=True)
                job_url = link_tag.get("href", "") if link_tag else ""

                if not job_url:
                    continue

                # Get location
                location_tag = posting.find("span", class_="location")
                if not location_tag:
                    location_tag = posting.find("span", class_="sort-by-location")
                location = location_tag.text.strip() if location_tag else "Unknown"

                job = Job(
                    company=company_name,
                    company_url=url,
                    title=title,
                    location=location,
                    url=job_url,
                )

                # Filter by keywords and experience level
                if job.matches_keywords(keywords) and job.is_entry_or_mid_level():
                    jobs.append(job)

            except Exception as e:
                print(f"[Lever] Error parsing job: {e}")
                continue

        print(f"[Lever] Found {len(jobs)} matching jobs at {company_name}")
        return jobs
