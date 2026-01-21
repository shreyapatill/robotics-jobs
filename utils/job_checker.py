"""Job link status checker."""

import requests
from concurrent.futures import ThreadPoolExecutor, as_completed


class JobChecker:
    """Check if job posting URLs are still active."""

    CLOSED_PATTERNS = [
        "this job is no longer available",
        "position has been filled",
        "job not found",
        "no longer accepting",
        "this requisition is closed",
        "application deadline has passed",
        "job has expired",
        "page not found",
        "404",
    ]

    DEFAULT_HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }

    def __init__(self, timeout: int = 15, max_workers: int = 5):
        """
        Initialize the job checker.

        Args:
            timeout: Request timeout in seconds
            max_workers: Maximum concurrent requests
        """
        self.timeout = timeout
        self.max_workers = max_workers

    def check_url(self, url: str) -> bool:
        """
        Check if a single URL is still active.

        Args:
            url: The job posting URL

        Returns:
            True if active, False if closed/unavailable
        """
        try:
            response = requests.get(
                url,
                headers=self.DEFAULT_HEADERS,
                timeout=self.timeout,
                allow_redirects=True,
            )

            if response.status_code == 404:
                return False

            if response.status_code != 200:
                return False

            content = response.text.lower()
            for pattern in self.CLOSED_PATTERNS:
                if pattern in content:
                    return False

            return True

        except requests.RequestException:
            return False

    def check_urls(self, urls: list[str]) -> dict[str, bool]:
        """
        Check multiple URLs concurrently.

        Args:
            urls: List of URLs to check

        Returns:
            Dict mapping URL to active status (True/False)
        """
        results = {}

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_url = {executor.submit(self.check_url, url): url for url in urls}

            for future in as_completed(future_to_url):
                url = future_to_url[future]
                try:
                    results[url] = future.result()
                except Exception:
                    results[url] = False

        return results
