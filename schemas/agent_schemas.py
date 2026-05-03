from typing import TypedDict, Annotated, Optional, Any
from langgraph.graph import add_messages

class InputState(TypedDict):
    cv: str
    job_title: str            # CV/resume text
    platforms: list[str]
    preferences: dict         # e.g. {"min_salary": 80000, "skip_if": ["contractor"]}


class Configuration(TypedDict):
    max_applications: int        # hard cap per run
    dry_run: bool                # if True, skip actual submission
    platform_credentials: dict   # {"linkedin": {...}, "greenhouse": {...}}

class JobApplication(TypedDict):
    job_id: str
    url: str
    platform: str                # "linkedin" | "greenhouse" | "lever"
    job_details: dict            # title, company, description, requirements
    cover_letter: Optional[str]
    status: str                 # "pending" | "submitted" | "failed" | "skipped"

class State(InputState):
    jobs: list[dict[str, Any]]
    current_job_index: int

    messages: Annotated[list, add_messages]

    applied: list[str]
    failed: list[str]
    skipped: list[str]