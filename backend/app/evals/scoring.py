import re
from pydantic import BaseModel
from app.llm import get_llm
from langchain_google_genai import ChatGoogleGenerativeAI
from app.config import settings
import os

judge_llm= ChatGoogleGenerativeAI(
    model="gemini-2.5-flash-lite",
    temperature=0,
    google_api_key=settings.GOOGLE_API_KEY
)

class Verdict(BaseModel):
  correct:bool
  reason:str
  
_judge = judge_llm.with_structured_output(Verdict)

async def judge_cause(predicted:str,expected:str)->Verdict:
  return await _judge.ainvoke(
        "You are grading an incident root-cause analysis.\n"
        f"EXPECTED root cause: {expected}\n"
        f"PREDICTED analysis: {predicted}\n\n"
        "Mark correct=true only if the predicted analysis identifies the same underlying "
        "cause as expected (wording may differ, details may be extra). If it blames something "
        "different, or is vague, mark correct=false. Give a one-sentence reason."
    )
  
def parse_action(plan: str) -> str:
    """Return e.g. 'rollback abc123', 'none', or 'missing'."""
    found = re.findall(r"ACTION:\s*(rollback\s+\w+|none)", plan, flags=re.I)
    return " ".join(found[-1].lower().split()) if found else "missing"

  
def tool_selection_ok(calls: list[dict], expected: set[str]) -> bool:
    return expected.issubset({c["name"] for c in calls})
  

def service_args_ok(calls: list[dict], service: str) -> bool:
    log_calls = [c for c in calls if c["name"] == "search_logs"]
    if not log_calls:
        return False
    return all(
        (c["input"].get("service") if isinstance(c["input"], dict) else service in str(c["input"])) == service
        or service in str(c["input"])
        for c in log_calls
    )


def action_outcome(proposed: str, expected: str) -> str:
    if proposed == expected:
        return "correct"
    if proposed == "missing":
        return "missing"
    return "wrong"  
  

  
