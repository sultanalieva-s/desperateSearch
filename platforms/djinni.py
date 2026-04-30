"""
platforms/djinni.py — Djinni.co adapter (scraping, no public API).

Uses httpx + BeautifulSoup. Login is required to apply; search is public.
"""
from __future__ import annotations

import logging
from typing import Any
from urllib.parse import urlencode, quote_plus

from platforms.base import BasePlatformAdapter

log = logging.getLogger(__name__)

BASE_URL = "https://djinni.co"


class DjinniAdapter(BasePlatformAdapter):

    async def search(self, position: str) -> list[dict[str, Any]]:
        try:
            import httpx
            from bs4 import BeautifulSoup
        except ImportError:
            log.error("Install httpx and beautifulsoup4 for Djinni support")
            return []

        query  = quote_plus(position)
        url    = f"{BASE_URL}/jobs/?all-keywords=&any-of-keywords=&exclude-keywords=&primary_keyword={query}"
        headers = {"User-Agent": "Mozilla/5.0 (compatible; JobSearchBot/1.0)"}

        async with httpx.AsyncClient(headers=headers, timeout=20, follow_redirects=True) as client:
            resp = await client.get(url)
            if resp.status_code != 200:
                log.warning("Djinni returned %s", resp.status_code)
                return []

        soup = BeautifulSoup(resp.text, "html.parser")
        jobs = []

        for card in soup.select("li.list-jobs__item")[:20]:
            title_tag = card.select_one("a.job-item__title-link")
            company_tag = card.select_one("a.job-item__company")
            if not title_tag:
                continue

            title   = title_tag.get_text(strip=True)
            company = company_tag.get_text(strip=True) if company_tag else "Unknown"
            href    = title_tag.get("href", "")
            job_url = f"{BASE_URL}{href}" if href.startswith("/") else href

            salary_tag = card.select_one(".public-salary-item")
            salary = salary_tag.get_text(strip=True) if salary_tag else None

            jobs.append({
                "platform":    "Djinni",
                "title":       title,
                "company":     company,
                "url":         job_url,
                "description": "",
                "salary":      salary,
                "location":    None,
            })

        log.info("Djinni: found %d jobs for '%s'", len(jobs), position)
        return jobs

    async def apply(self, job: dict[str, Any], cover_letter: str) -> bool:
        """
        Djinni does not expose an apply API.
        Applying requires browser automation (Playwright).
        Stub left for future implementation.
        """
        log.info("Djinni apply stub — open manually: %s", job["url"])
        return False
