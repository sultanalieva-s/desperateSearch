from langchain.chat_models import init_chat_model
from langgraph.graph import StateGraph, START, END

from schemas.agent_schemas import State, InputState

claude_sonnet = init_chat_model("anthropic:claude-sonnet-4-5-20250929", temperature=0)


# call llm -> get cover letter
def write_cover_letter_node(job: dict, cv: str) -> str:
    pass
workflow = StateGraph(State, input_schema=InputState)
