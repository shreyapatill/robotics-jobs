"""Greenhouse job board scraper."""

from bs4 import BeautifulSoup

from .base import BaseScraper, Job


class GreenhouseScraper(BaseScraper):
    """Scraper for Greenhouse job boards (boards.greenhouse.io)."""

    BASE_URL = "https://boards.greenhouse.io"

    @property
    def platform_name(self) -> str:
        return "Greenhouse"

    def scrape(self, source: str | dict, keywords: list[str]) -> list[Job]:
        """
        Scrape jobs from a Greenhouse job board.

        Args:
            source: Company slug (e.g., 'nuro' for boards.greenhouse.io/nuro)
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
            print(f"[Greenhouse] Error fetching {company_slug}: {e}")
            return []

        soup = BeautifulSoup(response.text, "lxml")
        jobs = []

        # Get company name from page title
        title_tag = soup.find("title")
        company_name = company_slug.replace("-", " ").title()
        if title_tag:
            title_text = title_tag.text.strip()
            if " at " in title_text:
                company_name = title_text.split(" at ")[-1].split(" - ")[0].strip()
            elif "Jobs at " in title_text:
                company_name = title_text.replace("Jobs at ", "").strip()

        # Find all job listings
        job_sections = soup.find_all("div", class_="opening")

        for job_div in job_sections:
            try:
                # Get job title and link
                link_tag = job_div.find("a")
                if not link_tag:
                    continue

                title = link_tag.text.strip()
                job_url = link_tag.get("href", "")

                # Make URL absolute
                if job_url.startswith("/"):
                    job_url = f"{self.BASE_URL}{job_url}"

                # Get location
                location_tag = job_div.find("span", class_="location")
                location = location_tag.text.strip() if location_tag else "Unknown"

                job = Job(
                    company=company_name,
                    company_url=url,
                    title=title,
                    location=location,
                    url=job_url,
                )

                # Filter by keywords
                if job.matches_keywords(keywords):
                    jobs.append(job)

            except Exception as e:
                print(f"[Greenhouse] Error parsing job: {e}")
                continue

        print(f"[Greenhouse] Found {len(jobs)} matching jobs at {company_name}")
        return jobs
