"""
platforms/glassdoor.py — Glassdoor adapter (Playwright-based scraping).

Glassdoor has no public job search API; scraping requires a logged-in session.
"""
from __future__ import annotations

import logging
from typing import Any
from urllib.parse import quote_plus

from platforms.base import BasePlatformAdapter

log = logging.getLogger(__name__)


class GlassdoorAdapter(BasePlatformAdapter):

    async def search(self, position: str) -> list[dict[str, Any]]:
        try:
            from playwright.async_api import async_playwright
        except ImportError:
            log.error("Install playwright for Glassdoor support")
            return []

        jobs: list[dict] = []
        url = (
            f"https://www.glassdoor.com/Job/jobs.htm"
            f"?sc.keyword={quote_plus(position)}&sortBy=date_desc"
        )

        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=True)
            page    = await browser.new_page()
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=30_000)

                # Dismiss sign-in modal if present
                try:
                    close_btn = await page.wait_for_selector(
                        "[data-test='modal-close-btn'], .modal_closeIcon",
                        timeout=4_000
                    )
                    await close_btn.click()
                except Exception:
                    pass

                await page.wait_for_selector("li.react-job-listing", timeout=10_000)
                cards = await page.query_selector_all("li.react-job-listing")

                for card in cards[:20]:
                    try:
                        title_el   = await card.query_selector("[data-test='job-title']")
                        company_el = await card.query_selector("[data-test='employer-name']")
                        link_el    = await card.query_selector("a[data-test='job-link']")
                        salary_el  = await card.query_selector("[data-test='detailSalary']")

                        title   = (await title_el.inner_text()).strip()   if title_el   else ""
                        company = (await company_el.inner_text()).strip() if company_el else ""
                        href    = await link_el.get_attribute("href")     if link_el    else ""
                        salary  = (await salary_el.inner_text()).strip()  if salary_el  else None

                        if title and href:
                            full_url = f"https://www.glassdoor.com{href}" if href.startswith("/") else href
                            jobs.append({
                                "platform":    "Glassdoor",
                                "title":       title,
                                "company":     company,
                                "url":         full_url.split("?")[0],
                                "description": "",
                                "salary":      salary,
                                "location":    None,
                            })
                    except Exception as e:
                        log.debug("Glassdoor card parse error: %s", e)

            except Exception as exc:
                log.warning("Glassdoor search failed: %s", exc)
            finally:
                await browser.close()

        log.info("Glassdoor: found %d jobs for '%s'", len(jobs), position)
        return jobs

    async def apply(self, job: dict[str, Any], cover_letter: str) -> bool:
        log.info("Glassdoor apply — manual required: %s", job["url"])
        return False
