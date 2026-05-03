from typing import Any

from langchain.chat_models import init_chat_model
from langgraph.graph import StateGraph, START, END

from schemas.agent_schemas import State, InputState
from platforms.linkedin import LinkedInAdapter
from platforms.djinni import DjinniAdapter
from platforms.telegram_channels import TelegramChannelsAdapter
from platforms.hh import HHAdapter
from platforms.glassdoor import GlassdoorAdapter

claude_sonnet = init_chat_model("anthropic:claude-sonnet-4-5-20250929", temperature=0)

platforms_map = {
    "hh": HHAdapter,
    "linkedin": LinkedInAdapter,
    "djinni": DjinniAdapter,
    "telegram": TelegramChannelsAdapter,
    "glassdoor": GlassdoorAdapter,
}

async def scrape_node(state: State) -> dict:
    """
    Scrapes jobs on provided platforms (LinkedIn, Telegram, HH, Djinni).
    """
    platforms: list[str] = state.platforms
    jobs: list[dict[str, Any]] = []

    for platform in platforms:
        adapter = platforms_map.get(platform)()
        jobs.extend(await adapter.search(state.job_title))
    return {"jobs": jobs}

# call llm -> get cover letter
def write_cover_letter_node(state: State) -> str:
    """
    Generates a cover letter based on CV and job description.
    """
    pass


def apply_node(State):
    pass


workflow = StateGraph(State, input_schema=InputState)
