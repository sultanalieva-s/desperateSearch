from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class BasePlatformAdapter(ABC):
    """
    Every platform adapter must implement:
      - search(position) → list of job dicts
      - apply(job, cover_letter) → bool

    Job dict schema:
    {
        "platform":    str,   # e.g. "HH.ru"
        "title":       str,
        "company":     str,
        "url":         str,   # canonical, unique
        "description": str,
        "salary":      str | None,
        "location":    str | None,
    }
    """

    @abstractmethod
    async def search(self, position: str) -> list[dict[str, Any]]:
        """Search for open vacancies matching `position`."""

    @abstractmethod
    async def apply(self, job: dict[str, Any], cover_letter: str) -> bool:
        """
        Attempt to apply to a job.
        Returns True on success, False if application could not be submitted.
        """
