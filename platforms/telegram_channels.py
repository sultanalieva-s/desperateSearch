"""
platforms/telegram_channels.py — Scan Telegram job channels for vacancies.

Uses the Telegram Bot API to read channel messages.
Channels must have added the bot as an admin, OR be public.
Channel usernames/IDs are configured in settings.TG_JOB_CHANNELS.
"""
from __future__ import annotations

import logging
import re
from typing import Any

from config import settings
from platforms.base import BasePlatformAdapter

log = logging.getLogger(__name__)


class TelegramChannelsAdapter(BasePlatformAdapter):

    async def search(self, position: str) -> list[dict[str, Any]]:
        """
        Scan configured Telegram channels for messages matching `position`.
        Requires python-telegram-bot to be available (reuses its bot token).
        """
        import httpx

        channels = settings.TG_JOB_CHANNELS
        if not channels:
            log.info("No TG_JOB_CHANNELS configured — skipping Telegram scan")
            return []

        token   = settings.TELEGRAM_TOKEN
        jobs    = []
        position_pattern = re.compile(re.escape(position), re.IGNORECASE)

        async with httpx.AsyncClient(timeout=15) as client:
            for channel in channels:
                try:
                    channel_jobs = await self._scan_channel(
                        client, token, channel, position_pattern
                    )
                    jobs.extend(channel_jobs)
                except Exception as exc:
                    log.warning("Failed to scan channel %s: %s", channel, exc)

        return jobs

    async def apply(self, job: dict[str, Any], cover_letter: str) -> bool:
        """Telegram jobs require manual application — just notify user."""
        log.info("Telegram job — manual apply required: %s", job["url"])
        return False

    async def _scan_channel(
        self, client, token: str, channel: str, pos_pat: re.Pattern
    ) -> list[dict]:
        """Fetch recent messages from a public channel via getUpdates workaround."""
        # For public channels we can use the public JSON API
        url  = f"https://api.telegram.org/bot{token}/getChat"
        resp = await client.get(url, params={"chat_id": channel})
        chat = resp.json().get("result", {})
        chat_title = chat.get("title", channel)

        # Fetch last 50 messages via forwardable link (public channels only)
        # NOTE: getUpdates only returns messages sent TO the bot.
        # For channel scanning, you need either:
        #   a) Bot added as channel admin (receives channel_post updates)
        #   b) Use Telethon/Pyrogram with user account (MTProto)
        # This stub returns an empty list — implement with Telethon for full support.
        log.info(
            "Channel '%s' (%s): full scanning requires Telethon. "
            "Add bot as admin to receive channel_post updates via webhook.",
            chat_title, channel
        )
        return []

    @staticmethod
    def _parse_job_message(msg: dict, channel: str, chat_title: str) -> dict | None:
        """Parse a Telegram message into a job dict."""
        pass

