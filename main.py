#!/usr/bin/env python3
"""
Robotics Jobs Scraper - Main orchestration script.

Usage:
    python main.py                    # Run all scrapers
    python main.py --dry-run          # Show what would be scraped without saving
    python main.py --check-status     # Also verify existing job links
    python main.py --config path.yaml # Use custom config file
"""

import argparse
import sys
from pathlib import Path

import yaml
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from scrapers import (
    GreenhouseScraper,
    LeverScraper,
    LinkedInScraper,
    WorkdayScraper,
    CustomScraper,
    Job,
)
from utils import READMEGenerator

console = Console()


def load_config(config_path: Path) -> dict:
    """Load configuration from YAML file."""
    if not config_path.exists():
        console.print(f"[red]Config file not found: {config_path}[/red]")
        sys.exit(1)

    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def run_scrapers(config: dict) -> list[Job]:
    """Run all configured scrapers and collect jobs."""
    all_jobs = []
    keywords = config.get("keywords", [])

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:

        # Greenhouse scrapers
        greenhouse_sources = config.get("greenhouse", [])
        if greenhouse_sources:
            task = progress.add_task("[cyan]Scraping Greenhouse...", total=len(greenhouse_sources))
            scraper = GreenhouseScraper()
            for source in greenhouse_sources:
                jobs = scraper.scrape(source, keywords)
                all_jobs.extend(jobs)
                progress.advance(task)

        # Lever scrapers
        lever_sources = config.get("lever", [])
        if lever_sources:
            task = progress.add_task("[cyan]Scraping Lever...", total=len(lever_sources))
            scraper = LeverScraper()
            for source in lever_sources:
                jobs = scraper.scrape(source, keywords)
                all_jobs.extend(jobs)
                progress.advance(task)

        # Workday scrapers
        workday_sources = config.get("workday", [])
        if workday_sources:
            task = progress.add_task("[cyan]Scraping Workday...", total=len(workday_sources))
            scraper = WorkdayScraper()
            for source in workday_sources:
                jobs = scraper.scrape(source, keywords)
                all_jobs.extend(jobs)
                progress.advance(task)

        # LinkedIn scraper
        linkedin_config = config.get("linkedin")
        if linkedin_config:
            task = progress.add_task("[cyan]Scraping LinkedIn...", total=1)
            scraper = LinkedInScraper()
            jobs = scraper.scrape(linkedin_config, keywords)
            all_jobs.extend(jobs)
            progress.advance(task)

        # Custom scrapers
        custom_sources = config.get("custom", [])
        if custom_sources:
            task = progress.add_task("[cyan]Scraping custom pages...", total=len(custom_sources))
            scraper = CustomScraper()
            for source in custom_sources:
                jobs = scraper.scrape(source, keywords)
                all_jobs.extend(jobs)
                progress.advance(task)

    return all_jobs


def display_jobs(jobs: list[Job]) -> None:
    """Display jobs in a formatted table."""
    table = Table(title=f"Found {len(jobs)} Jobs")
    table.add_column("Company", style="cyan")
    table.add_column("Title", style="green")
    table.add_column("Location", style="yellow")

    for job in jobs[:50]:  # Limit display
        table.add_row(job.company, job.title, job.location)

    if len(jobs) > 50:
        table.add_row("...", f"and {len(jobs) - 50} more", "...")

    console.print(table)


def main():
    parser = argparse.ArgumentParser(description="Scrape robotics and autonomy job listings")
    parser.add_argument(
        "--config",
        type=Path,
        default=Path(__file__).parent / "config" / "sources.yaml",
        help="Path to configuration file",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).parent / "README.md",
        help="Path to output README file",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show jobs without saving to README",
    )
    parser.add_argument(
        "--check-status",
        action="store_true",
        help="Check and update status of existing job links",
    )
    args = parser.parse_args()

    console.print("[bold blue]🤖 Robotics Jobs Scraper[/bold blue]\n")

    # Load configuration
    console.print(f"Loading config from: {args.config}")
    config = load_config(args.config)

    keywords = config.get("keywords", [])
    console.print(f"Filtering for keywords: {', '.join(keywords[:5])}...")

    # Run scrapers
    console.print("\n[bold]Starting job scrape...[/bold]\n")
    jobs = run_scrapers(config)

    # Display results
    console.print()
    display_jobs(jobs)

    if args.dry_run:
        console.print("\n[yellow]Dry run - README not updated[/yellow]")
        return

    # Generate and save README
    console.print("\n[bold]Generating README...[/bold]")
    generator = READMEGenerator(args.output)
    content = generator.generate(jobs, update_status=args.check_status)
    generator.save(content)

    console.print(f"\n[bold green]✅ Done! Found {len(jobs)} new jobs.[/bold green]")


if __name__ == "__main__":
    main()
