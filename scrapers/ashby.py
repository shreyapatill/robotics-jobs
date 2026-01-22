"""Ashby HQ job board scraper."""

import json
import re
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

        jobs = []
        company_name = company_slug.replace("-", " ").title()

        # Method 1: Extract from embedded JSON in page
        # Look for jobPostings data structure
        content = response.text

        # Try to find job data - Ashby embeds job data in the HTML
        # Pattern: "id":"<uuid>","title":"<title>" followed by location info
        job_pattern = r'"id"\s*:\s*"([a-f0-9-]{36})"\s*,\s*"title"\s*:\s*"([^"]+)"'
        location_pattern = r'"locationName"\s*:\s*"([^"]+)"'

        job_matches = list(re.finditer(job_pattern, content))
        locations = re.findall(location_pattern, content)

        if job_matches:
            # Try to pair jobs with locations
            for i, match in enumerate(job_matches):
                job_id = match.group(1)
                title = match.group(2)

                # Skip non-job entries (like team IDs or other UUIDs)
                if len(title) < 3 or title.startswith("$"):
                    continue

                # Get location - try to find one near this match
                location = "Unknown"
                if i < len(locations):
                    location = locations[i]
                else:
                    # Search for locationName near this job entry
                    start_pos = match.end()
                    nearby = content[start_pos:start_pos + 500]
                    loc_match = re.search(r'"locationName"\s*:\s*"([^"]+)"', nearby)
                    if loc_match:
                        location = loc_match.group(1)

                job_url = f"{url}/{job_id}"

                job = Job(
                    company=company_name,
                    company_url=url,
                    title=title,
                    location=location,
                    url=job_url,
                )

                if job.matches_keywords(keywords) and job.is_entry_or_mid_level():
                    jobs.append(job)

        # Method 2: Fallback - try parsing the job board API response directly
        if not jobs:
            # Try the GraphQL API
            try:
                gql_url = f"{self.BASE_URL}/api/non-user-graphql"
                query = {
                    "operationName": "ApiJobBoardWithTeams",
                    "variables": {"organizationHostedJobsPageName": company_slug},
                    "query": """query ApiJobBoardWithTeams($organizationHostedJobsPageName: String!) {
                        jobBoard: jobBoardWithTeams(organizationHostedJobsPageName: $organizationHostedJobsPageName) {
                            jobPostings {
                                id
                                title
                                locationName
                            }
                        }
                    }"""
                }
                response = self.session.post(gql_url, json=query)
                if response.status_code == 200:
                    data = response.json()
                    if "data" in data and "jobBoard" in data["data"]:
                        postings = data["data"]["jobBoard"].get("jobPostings", [])
                        for posting in postings:
                            job = Job(
                                company=company_name,
                                company_url=url,
                                title=posting.get("title", ""),
                                location=posting.get("locationName", "Unknown"),
                                url=f"{url}/{posting.get('id', '')}",
                            )
                            if job.matches_keywords(keywords) and job.is_entry_or_mid_level():
                                jobs.append(job)
            except Exception:
                pass

        print(f"[Ashby] Found {len(jobs)} matching jobs at {company_name}")
        return jobs
