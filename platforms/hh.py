"""
platforms/hh.py — HH.ru adapter using the official public REST API.

Docs: https://api.hh.ru/openapi/redoc
No auth required for search; OAuth token required for apply.
"""
from __future__ import annotations

import logging
from typing import Any

import httpx

from config import settings
from platforms.base import BasePlatformAdapter

log = logging.getLogger(__name__)

BASE_URL = "https://api.hh.ru"
HEADERS  = {"User-Agent": "JobSearchBot/1.0 (your@email.com)"}   # HH requires UA


class HHAdapter(BasePlatformAdapter):

    async def search(self, position: str) -> list[dict[str, Any]]:
        """
            Search HH.ru vacancies by job title. Returns up to 50 results per call.
            Returns list of jobs. Job contains description that will be used for cover letter.
        """

        params = {
            "text":       position,
            "area":       113,      # Russia; remove or change for other regions
            "per_page":   50,
            "order_by":   "publication_time",
        }
        async with httpx.AsyncClient(headers=HEADERS, timeout=15) as client:
            resp = await client.get(f"{BASE_URL}/vacancies", params=params)
            resp.raise_for_status()
            data = resp.json()

        jobs = []
        for item in data.get("items", []):
            salary = self._fmt_salary(item.get("salary"))
            jobs.append({
                "platform":    "HH.ru",
                "title":       item["name"],
                "company":     item.get("employer", {}).get("name", "Unknown"),
                "url":         item["alternate_url"],
                "description": "",        # fetched lazily if needed
                "salary":      salary,
                "location":    item.get("area", {}).get("name"),
            })
        return jobs

    async def apply(self, job: dict[str, Any], cover_letter: str) -> bool:
        """
        Apply via HH.ru Negotiations API (requires OAuth token).
        https://api.hh.ru/openapi/redoc#tag/Otklikipredlozheniya-rabotodatelya
        """
        if not settings.HH_ACCESS_TOKEN:
            log.warning("HH_ACCESS_TOKEN not set — cannot apply on HH.ru")
            return False

        # Extract vacancy ID from URL: https://hh.ru/vacancy/12345678
        vacancy_id = job["url"].rstrip("/").split("/")[-1]
        headers = {
            **HEADERS,
            "Authorization": f"Bearer {settings.HH_ACCESS_TOKEN}",
        }
        payload = {
            "vacancy_id":   vacancy_id,
            "message":      cover_letter,
        }
        async with httpx.AsyncClient(headers=headers, timeout=15) as client:
            resp = await client.post(f"{BASE_URL}/negotiations", json=payload)

        if resp.status_code in (200, 201):
            log.info("Applied to HH vacancy %s", vacancy_id)
            return True

        log.warning("HH apply failed [%s]: %s", resp.status_code, resp.text)
        return False

    # ── helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _fmt_salary(s: dict | None) -> str | None:
        if not s:
            return None
        lo, hi, cur = s.get("from"), s.get("to"), s.get("currency", "")
        if lo and hi:
            return f"{lo:,}–{hi:,} {cur}"
        if lo:
            return f"from {lo:,} {cur}"
        if hi:
            return f"up to {hi:,} {cur}"
        return None
