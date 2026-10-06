from langchain.agents import create_agent

from app.llm import get_llm
from app.tools.read_tools import search_logs,get_metrics,get_recent_commits

agent = create_agent(
  get_llm(),
  tools = [search_logs,get_metrics,get_recent_commits],
  system_prompt="You are an SRE. Investigate incidents using tools. Cite evidence.", 
)

if __name__ == "__main__":
    out = agent.invoke({"messages": [("user",
        "payment-service returns HTTP 500 after the latest deploy. Investigate.")]})
    print(out["messages"][-1].content)

