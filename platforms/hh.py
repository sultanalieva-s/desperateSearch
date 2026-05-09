from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx
from aiohttp import web

from config import settings
from platforms.base import BasePlatformAdapter

log = logging.getLogger(__name__)


class HHAdapter(BasePlatformAdapter):
    ACCESS_TOKEN: str
    BASE_URL = "https://api.hh.ru"
    BASE_HEADERS = {"User-Agent": "desperatesearchbot/1.0 (saadatssu@gmail.com)"}

    async def search(self, position: str) -> list[dict[str, Any]]:
        """
            Search HH.ru vacancies by job title. Returns up to 50 results per call.
            Returns list of jobs.
            A job object contains description that will be used for cover letter generation.
        """
        headers = {
            "User-Agent": "desperatesearchbot/1.0 (saadatssu@gmail.com)",
            "HH-User-Agent": "desperatesearchbot/1.0 (saadatssu@gmail.com)",
            "Authorization": f"Bearer {HHAdapter.ACCESS_TOKEN}",
        }
        vacancies_url = f"{self.BASE_URL}/vacancies"
        params = {
            "text":       position,
            "per_page":   50,
            "order_by":   "publication_time",
        }
        log.info(f"Searching HH.ru: {headers}")
        async with httpx.AsyncClient(headers=headers, timeout=15) as client:
            resp = await client.get(vacancies_url, params=params)
            data = resp.json()
            log.info(f"vacancies response: {data}")
            resp.raise_for_status()

        jobs = []
        for item in data.get("items", []):
            jobs.append({
                "platform":    "HH.ru",
                "title":       item["name"],
                "company":     item.get("employer", {}).get("name", "Unknown"),
                "url":         item["alternate_url"],
                "description": item["description"],
                "salary":      item.get("salary"),
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
            **self.BASE_HEADERS,
            "Authorization": f"Bearer {settings.HH_ACCESS_TOKEN}",
        }
        payload = {
            "vacancy_id":   vacancy_id,
            "message":      cover_letter,
        }
        async with httpx.AsyncClient(headers=headers, timeout=15) as client:
            resp = await client.post(f"{self.BASE_URL}/negotiations", json=payload)

        if resp.status_code in (200, 201):
            log.info("Applied to HH vacancy %s", vacancy_id)
            return True

        log.warning("HH apply failed [%s]: %s", resp.status_code, resp.text)
        return False

    async def _get_access_token(self) -> str:
        code = await self._wait_for_authorization_code()
        url = self.BASE_URL + "/token"
        params = {
            "grant_type": "authorization_code",
            "client_id": settings.HH_CLIENT_ID,
            "client_secret": settings.HH_CLIENT_SECRET,
            "redirect_uri": settings.HH_REDIRECT_URI,
            "code": code,
        }
        headers = {
            "User-Agent": "desperatesearchbot/1.0 (saadatssu@gmail.com)",
            "Content-Type": "application/x-www-form-urlencoded",
        }
        async with httpx.AsyncClient(headers=headers, timeout=15) as client:
            response = await client.post(url, params=params)
            log.info("Got access token: %s", response.json())
            response.raise_for_status()
            token = response.json().get("access_token")

        return token


    async def _wait_for_authorization_code(self) -> str:
        code_future: asyncio.Future = asyncio.get_event_loop().create_future()

        async def callback_handler(request: web.Request):
            code = request.rel_url.query.get("code")
            code_future.set_result(code)
            return web.Response(text="✅ Authorization successful! You can close this tab.")

        app = web.Application()
        app.router.add_get("/auth", callback_handler)

        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, "localhost", 8000)
        await site.start()

        code = await code_future  # waits until HH redirects

        await runner.cleanup()  # shut down the server
        return code

    @staticmethod
    def get_auth_url() -> str:
        return (
            f"https://hh.ru/oauth/authorize"
            f"?response_type=code"
            f"&client_id={settings.HH_CLIENT_ID}"
            f"&redirect_uri={settings.HH_REDIRECT_URI}"
        )

    async def __aenter__(self):
        HHAdapter.ACCESS_TOKEN = await self._get_access_token()
        return self

    async def __aexit__(self, *args):
        pass