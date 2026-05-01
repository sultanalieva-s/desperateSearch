from typing import TypedDict, Annotated, Optional
from langgraph.graph import add_messages

# ── Input (what the user provides at the start) ──────────────────────────────

class InputState(TypedDict):
    cv: str                      # raw CV/resume text
    job_urls: list[str]          # list of job posting URLs to apply to
    preferences: dict            # e.g. {"min_salary": 80000, "skip_if": ["contractor"]}

# ── Configuration (static, injected at runtime, not part of graph flow) ───────

class Configuration(TypedDict):
    max_applications: int        # hard cap per run
    dry_run: bool                # if True, skip actual submission
    platform_credentials: dict   # {"linkedin": {...}, "greenhouse": {...}}

# ── Core State (evolves as the graph runs) ────────────────────────────────────

class JobApplication(TypedDict):
    job_id: str
    url: str
    platform: str                # "linkedin" | "greenhouse" | "lever" | ...
    job_details: dict            # title, company, description, requirements
    cover_letter: Optional[str]
    status: str                  # "pending" | "submitted" | "failed" | "skipped"
    error: Optional[str]         # reason if failed/skipped

class State(InputState):
    # discovery
    jobs: list[JobApplication]           # populated after scraping URLs
    current_job_index: int               # pointer for the apply loop

    # generation
    messages: Annotated[list, add_messages]  # LLM conversation history

    # results
    applied: list[str]           # job_ids successfully submitted
    failed: list[str]            # job_ids that errored
    skipped: list[str]           # job_ids filtered by preferences