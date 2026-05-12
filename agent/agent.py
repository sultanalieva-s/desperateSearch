from typing import Any

from langchain.chat_models import init_chat_model
from langgraph.graph import StateGraph, START, END

from agent.schemas.agent_schemas import State, InputState
from platforms.linkedin import LinkedInAdapter
from platforms.djinni import DjinniAdapter
from platforms.telegram_channels import TelegramChannelsAdapter
from platforms.hh import HHAdapter
from platforms.glassdoor import GlassdoorAdapter
from langchain_core.messages import AIMessage

claude_sonnet = init_chat_model("anthropic:claude-sonnet-4-5-20250929", temperature=0)

platforms_map = {
    "HH": HHAdapter,
    "LinkedIn": LinkedInAdapter,
    "Djinni": DjinniAdapter,
    "Telegram": TelegramChannelsAdapter,
    "Glassdoor": GlassdoorAdapter,
}

async def scrape(state: State) -> dict:
    """
    Scrapes jobs on provided platforms (LinkedIn, Telegram, HH, Djinni).
    """
    platforms: list[str] = state["platforms"]
    jobs: list[dict[str, Any]] = []

    for platform in platforms:
        adapter = platforms_map.get(platform)()
        async with adapter as adapter_manager:
            jobs.extend(await adapter_manager.search(state["job_title"]))
    return {"jobs": jobs}

# call llm -> get cover letter -> update state
async def generate_cover_letter(state: State) -> dict:
    """
    Generates a cover letter based on CV and job description.
    """
    cv: str = state["cv"]
    from agent.prompts.cover_letter_prompt import COVER_LETTER_PROMPT
    jobs = state["jobs"]

    for job in jobs:
        prompt_with_input = COVER_LETTER_PROMPT.format(cv=cv, job=job)
        model_response: AIMessage = await claude_sonnet.ainvoke(prompt_with_input)
        job["cover_letter"] = model_response.content

    return {"jobs": jobs}

async def apply(state: State):
    """
    1. submit on hh job
    2. submit on linkedin job

    3. submit a form on a website
    4. write hr in telegram
    5. write email
    """
    print(f"jobs: {state["jobs"]}")
    for job in state["jobs"]:
        print(f"job: {job["description"]}")
        print(f"cover letter: {job["cover_letter"]}")

workflow = StateGraph(State, input_schema=InputState)

workflow.add_node("scrape", scrape)
workflow.add_node("generate_cover_letter", generate_cover_letter)
workflow.add_node("apply", apply)

workflow.add_edge(START, "scrape")
workflow.add_edge("scrape", "generate_cover_letter")
workflow.add_edge("generate_cover_letter", "apply")
workflow.add_edge("apply", END)

chain = workflow.compile()

__all__ = ["chain"]