"""README generator and organizer for job listings."""

import os
import re
from datetime import datetime
from pathlib import Path

from scrapers.base import Job


class READMEGenerator:
    """Generate and manage the jobs README file."""

    TABLE_HEADER = """| Company | Location | Role | Date Added |
| ------- | -------- | ---- | ---------- |
"""

    README_TEMPLATE = """# 🤖 Robotics & Autonomy Jobs

A curated list of entry-level robotics and autonomy job openings, automatically updated daily.

---

## 💼 All Jobs

{jobs_table}

[⬆️ Back to Top](#-robotics--autonomy-jobs)

---

## 🗽 NYC Jobs

{nyc_jobs_table}

[⬆️ Back to Top](#-robotics--autonomy-jobs)

---

### Legend

- ✅ = Position is open/available
- 🔒 = Position is closed/filled

---

*Last updated: {last_updated}*
"""

    def __init__(self, readme_path: str | Path):
        """
        Initialize the README generator.

        Args:
            readme_path: Path to the README.md file
        """
        self.readme_path = Path(readme_path)

    def load_existing_jobs(self) -> list[dict]:
        """
        Load existing jobs from the README.

        Returns:
            List of job dicts with keys: company, location, role, visa, date, url, is_active
        """
        if not self.readme_path.exists():
            return []

        try:
            content = self.readme_path.read_text(encoding="utf-8")
        except Exception:
            return []

        jobs = []

        # Find the jobs table
        table_match = re.search(
            r"\|\s*Company\s*\|.*?\n\|[-\s|]+\|\n((?:\|.*\|\n)*)",
            content,
            re.IGNORECASE,
        )

        if not table_match:
            return []

        table_rows = table_match.group(1).strip().split("\n")

        for row in table_rows:
            if not row.strip() or row.strip() == "|":
                continue

            try:
                # Parse table row: | Company | Location | Role | Visa | Date |
                cells = [c.strip() for c in row.split("|")[1:-1]]
                if len(cells) < 5:
                    continue

                company_cell, location, role_cell, visa, date = cells[:5]

                # Extract company name and URL
                company_match = re.search(r"\[(.+?)\]\((.+?)\)", company_cell)
                company = company_match.group(1) if company_match else company_cell
                company_url = company_match.group(2) if company_match else ""

                # Extract role status, name and URL
                is_active = "✅" in role_cell
                role_match = re.search(r"\[(.+?)\]\((.+?)\)", role_cell)
                role = role_match.group(1) if role_match else role_cell.replace("✅", "").replace("🔒", "").strip()
                role_url = role_match.group(2) if role_match else ""

                jobs.append({
                    "company": company,
                    "company_url": company_url,
                    "location": location,
                    "role": role,
                    "role_url": role_url,
                    "visa": visa,
                    "date": date,
                    "is_active": is_active,
                })

            except Exception:
                continue

        return jobs

    def merge_jobs(self, existing: list[dict], new_jobs: list[Job]) -> list[dict]:
        """
        Merge new jobs with existing ones, avoiding duplicates.

        Args:
            existing: List of existing job dicts
            new_jobs: List of new Job objects

        Returns:
            Merged list of job dicts
        """
        # Create lookup by URL for deduplication
        seen_urls = {job.get("role_url", ""): job for job in existing if job.get("role_url")}

        for job in new_jobs:
            if job.url not in seen_urls:
                seen_urls[job.url] = {
                    "company": job.company,
                    "company_url": job.company_url,
                    "location": job.location,
                    "role": job.title,
                    "role_url": job.url,
                    "visa": job.visa_info,
                    "date": job.date_added.strftime("%m/%d/%Y"),
                    "is_active": job.is_active,
                }

        return list(seen_urls.values())

    def sort_jobs(self, jobs: list[dict]) -> list[dict]:
        """
        Sort jobs by date (newest first).

        Args:
            jobs: List of job dicts

        Returns:
            Sorted list
        """
        def get_date(job):
            try:
                return datetime.strptime(job.get("date", "01/01/2000"), "%m/%d/%Y")
            except ValueError:
                return datetime(2000, 1, 1)

        return sorted(jobs, key=get_date, reverse=True)

    def format_table(self, jobs: list[dict]) -> str:
        """
        Format jobs as a markdown table.

        Args:
            jobs: List of job dicts

        Returns:
            Markdown table string
        """
        rows = []
        for job in jobs:
            status = "✅" if job.get("is_active", True) else "🔒"
            company_link = f"[{job['company']}]({job['company_url']})" if job.get("company_url") else job["company"]
            role_link = f"{status} [{job['role']}]({job['role_url']})" if job.get("role_url") else f"{status} {job['role']}"

            row = f"| {company_link} | {job['location']} | {role_link} | {job['date']} |"
            rows.append(row)

        return self.TABLE_HEADER + "\n".join(rows)

    def is_canada_job(self, location: str) -> bool:
        """Check if location is in Canada."""
        location_lower = location.lower()
        canada_indicators = [
            "canada", "toronto", "vancouver", "montreal", "ottawa",
            "calgary", "edmonton", "winnipeg", ", ca", "ontario",
            "british columbia", "quebec", "alberta", ", on", ", bc", ", qc"
        ]
        return any(ind in location_lower for ind in canada_indicators)

    def is_nyc_job(self, location: str) -> bool:
        """Check if location is in NYC area."""
        location_lower = location.lower()
        nyc_indicators = [
            "new york", "nyc", "brooklyn", "manhattan", "queens",
            "bronx", "staten island", ", ny", "new york city"
        ]
        return any(ind in location_lower for ind in nyc_indicators)

    def generate(self, new_jobs: list[Job], update_status: bool = False) -> str:
        """
        Generate the README content.

        Args:
            new_jobs: List of new Job objects to add
            update_status: Whether to check and update job statuses

        Returns:
            Generated README content
        """
        existing = self.load_existing_jobs()
        merged = self.merge_jobs(existing, new_jobs)
        sorted_jobs = self.sort_jobs(merged)

        # Filter out Canada jobs
        sorted_jobs = [job for job in sorted_jobs if not self.is_canada_job(job.get("location", ""))]

        if update_status:
            from utils.job_checker import JobChecker
            checker = JobChecker()
            urls = [job.get("role_url", "") for job in sorted_jobs if job.get("role_url")]
            statuses = checker.check_urls(urls)
            for job in sorted_jobs:
                url = job.get("role_url", "")
                if url in statuses:
                    job["is_active"] = statuses[url]

        # Split into NYC jobs and all jobs
        nyc_jobs = [job for job in sorted_jobs if self.is_nyc_job(job.get("location", ""))]

        jobs_table = self.format_table(sorted_jobs)
        nyc_jobs_table = self.format_table(nyc_jobs) if nyc_jobs else "No NYC jobs found yet."
        last_updated = datetime.now().strftime("%Y-%m-%d %H:%M UTC")

        return self.README_TEMPLATE.format(
            jobs_table=jobs_table,
            nyc_jobs_table=nyc_jobs_table,
            last_updated=last_updated
        )

    def save(self, content: str) -> None:
        """
        Save content to the README file.

        Args:
            content: README content to save
        """
        self.readme_path.write_text(content, encoding="utf-8")
        print(f"README saved to {self.readme_path}")
