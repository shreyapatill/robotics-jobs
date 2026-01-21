"""Base scraper class and Job dataclass for all scrapers."""

import time
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


@dataclass
class Job:
    """Represents a job posting."""

    company: str
    company_url: str
    title: str
    location: str
    url: str
    date_added: datetime = field(default_factory=datetime.now)
    visa_info: str = "-"
    is_active: bool = True

    def to_table_row(self) -> str:
        """Convert job to markdown table row."""
        status = "✅" if self.is_active else "🔒"
        date_str = self.date_added.strftime("%m/%d/%Y")
        role_link = f"{status} [{self.title}]({self.url})"
        return f"| [{self.company}]({self.company_url}) | {self.location} | {role_link} | {date_str} |\n"

    def matches_keywords(self, keywords: list[str]) -> bool:
        """Check if job title matches any keywords (case-insensitive)."""
        title_lower = self.title.lower()
        return any(kw.lower() in title_lower for kw in keywords)

    def is_entry_or_mid_level(self) -> bool:
        """
        Check if job is entry/mid level (not requiring 8+ years).
        Returns False for senior/principal/staff/director level roles.
        """
        title_lower = self.title.lower()
        senior_patterns = [
            "senior", "sr.", "sr ", "principal", "staff", "lead",
            "director", "head of", "vp ", "vice president",
            "manager", "architect", "distinguished", "fellow",
            "iii", "iv", "v", "level 3", "level 4", "level 5",
            "l3", "l4", "l5", "l6", "l7",
        ]
        # Allow "team lead" type roles that might be ok
        if "team lead" in title_lower:
            return True
        return not any(pattern in title_lower for pattern in senior_patterns)


class BaseScraper(ABC):
    """Abstract base class for all job scrapers."""

    # Default headers to mimic a browser
    DEFAULT_HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
    }

    def __init__(self, rate_limit_delay: float = 1.0):
        """
        Initialize the scraper.

        Args:
            rate_limit_delay: Seconds to wait between requests
        """
        self.rate_limit_delay = rate_limit_delay
        self.session = self._create_session()
        self._last_request_time = 0

    def _create_session(self) -> requests.Session:
        """Create a requests session with retry logic."""
        session = requests.Session()
        session.headers.update(self.DEFAULT_HEADERS)

        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)

        return session

    def _rate_limit(self) -> None:
        """Enforce rate limiting between requests."""
        elapsed = time.time() - self._last_request_time
        if elapsed < self.rate_limit_delay:
            time.sleep(self.rate_limit_delay - elapsed)
        self._last_request_time = time.time()

    def get(self, url: str, **kwargs) -> requests.Response:
        """Make a rate-limited GET request."""
        self._rate_limit()
        return self.session.get(url, timeout=30, **kwargs)

    def check_status(self, url: str) -> bool:
        """
        Check if a job posting is still active.

        Args:
            url: The job posting URL

        Returns:
            True if job is active, False if closed/not found
        """
        try:
            response = self.get(url)
            if response.status_code == 200:
                # Additional checks for common "job closed" patterns
                content = response.text.lower()
                closed_patterns = [
                    "this job is no longer available",
                    "position has been filled",
                    "job not found",
                    "this requisition is closed",
                    "no longer accepting applications",
                ]
                if any(pattern in content for pattern in closed_patterns):
                    return False
                return True
            return False
        except requests.RequestException:
            return False

    @abstractmethod
    def scrape(self, source: str | dict, keywords: list[str]) -> list[Job]:
        """
        Scrape jobs from the source.

        Args:
            source: The source identifier (company slug, URL, or config dict)
            keywords: List of keywords to filter jobs

        Returns:
            List of Job objects matching the keywords
        """
        pass

    @property
    @abstractmethod
    def platform_name(self) -> str:
        """Return the name of the platform this scraper handles."""
        pass
