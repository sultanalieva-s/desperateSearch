"""
platforms/linkedin.py — LinkedIn adapter.

LinkedIn aggressively blocks scrapers and has no public job API.
The recommended approach is Playwright browser automation.

Install: pip install playwright && playwright install chromium

This module provides a working Playwright-based implementation.
"""
from __future__ import annotations

import logging
from typing import Any

from platforms.base import BasePlatformAdapter

log = logging.getLogger(__name__)

SEARCH_URL = (
    "https://www.linkedin.com/jobs/search/"
    "?keywords={position}&f_TPR=r86400&sortBy=DD"
)


class LinkedInAdapter(BasePlatformAdapter):

    async def search(self, position: str) -> list[dict[str, Any]]:
        """
        Scrape LinkedIn job listings using Playwright (headless Chromium).
        LinkedIn requires cookies / session — log in manually once and
        export cookies to storage/linkedin_cookies.json.
        """
        try:
            from playwright.async_api import async_playwright
        except ImportError:
            log.error("Install playwright: pip install playwright && playwright install chromium")
            return []

        jobs: list[dict] = []
        url  = SEARCH_URL.format(position=position.replace(" ", "%20"))

        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=True)
            ctx     = await browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 Chrome/124.0 Safari/537.36"
                )
            )

            # Load saved session cookies if available
            import json
            from pathlib import Path
            cookies_path = Path("storage/linkedin_cookies.json")
            if cookies_path.exists():
                cookies = json.loads(cookies_path.read_text())
                await ctx.add_cookies(cookies)

            page = await ctx.new_page()
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=30_000)
                await page.wait_for_selector(".jobs-search__results-list", timeout=10_000)

                cards = await page.query_selector_all(".jobs-search__results-list > li")
                for card in cards[:20]:
                    try:
                        title_el   = await card.query_selector("h3.base-search-card__title")
                        company_el = await card.query_selector("h4.base-search-card__subtitle")
                        link_el    = await card.query_selector("a.base-card__full-link")

                        title   = (await title_el.inner_text()).strip()   if title_el   else ""
                        company = (await company_el.inner_text()).strip() if company_el else ""
                        href    = await link_el.get_attribute("href")     if link_el    else ""

                        if title and href:
                            jobs.append({
                                "platform":    "LinkedIn",
                                "title":       title,
                                "company":     company,
                                "url":         href.split("?")[0],
                                "description": "",
                                "salary":      None,
                                "location":    None,
                            })
                    except Exception as e:
                        log.debug("Card parse error: %s", e)

            except Exception as exc:
                log.warning("LinkedIn search failed: %s", exc)
            finally:
                await browser.close()

        log.info("LinkedIn: found %d jobs for '%s'", len(jobs), position)
        return jobs

    async def apply(self, job: dict[str, Any], cover_letter: str) -> bool:
        """
        Easy Apply via Playwright.
        Highly site-specific — LinkedIn changes DOM frequently.
        Stub: returns False, opens job URL for manual application.
        """
        log.info("LinkedIn Easy Apply stub — open manually: %s", job["url"])
        return False
