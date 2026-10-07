from langgraph.graph import StateGraph,START,END
from langchain.agents import create_agent
from langgraph.checkpoint.memory import MemorySaver
from app.llm import get_llm
from app.agents.state import IncidentState
from app.tools.read_tools import search_logs,get_recent_commits,get_metrics
import re
from langgraph.types import interrupt,Command
from app.tools.write_tools import execute_action

llm = get_llm()

log_agents = create_agent(
  llm,[search_logs],system_prompt = "You are a log analyst. Report only facts found in logs."
)

metrics_agent = create_agent(
  llm,[get_metrics],system_prompt = "You are a metrics analyst. Check db_connection_usage and error_rate."
)

code_agents = create_agent(
  llm,[get_recent_commits],system_prompt = "You are a code analyst. Find recent commits that could cause the incident."
)

def make_node(agent, label):
    def node(state: IncidentState):
        out = agent.invoke({"messages": [("user", state["incident"])]})
        return {"evidence": [f"[{label}] {out['messages'][-1].content}"]}
    return node


def root_cause_node(state : IncidentState):
  evidence = "\n".join(state["evidence"])
  msg = llm.invoke(
        f"Incident: {state['incident']}\nEvidence:\n{evidence}\n\n"
        "State the most likely root cause, a confidence %, and the evidence list.")
  return {"root_cause": msg.content}


def planner_node(state : IncidentState):
  msg = llm.invoke(
        f"Root cause:\n{state['root_cause']}\n\n"
        "Propose a remediation plan. Start with the safest action. "
        "End with a line 'ACTION: rollback <sha>' or 'ACTION: none'.")
  return {"plan": msg.content}


def approval_node(state : IncidentState):
  decision = interrupt({"question" :  "Approve this plan ?","plan":state["plan"]})
  return {"approved":decision["approve"]}

def remediation_node(state: IncidentState):
    if not state["approved"]:
        return {"result": "Rejected by human. No action taken."}
    m = re.search(r"ACTION:\s*rollback\s+(\w+)", state["plan"])
    if not m:
        return {"result": "No executable action in plan."}
    return {"result": execute_action("rollback", m.group(1), "sre", True)}



def build_graph(checkpointer = None):
  g = StateGraph(IncidentState)
  
  g.add_node("logs",make_node(log_agents,"logs"))
  g.add_node("metrics",make_node(metrics_agent,"metrics"))
  g.add_node("code",make_node(code_agents,"code"))
  g.add_node("root_cause",root_cause_node)
  g.add_node("planner",planner_node)
  g.add_node("approval",approval_node)
  g.add_node("remediation",remediation_node)
  
  
  for n in ("logs","metrics","code"):
    g.add_edge(START,n)
    g.add_edge(n,"root_cause")
  g.add_edge("root_cause","planner")
  g.add_edge("planner","approval")
  g.add_edge("approval","remediation")
  g.add_edge("remediation",END)
  
  
  return g.compile(checkpointer=MemorySaver())

graph = build_graph()


cfg = {"configurable": {"thread_id": "t2"}}
graph.invoke({"incident": "payment-service 500 after deploy", "evidence": []}, cfg)
print(graph.get_state(cfg).next)                       # ('approval',) = paused
out = graph.invoke(Command(resume={"approve": True}), cfg)
print(out["result"])
  
    
    
  
  
  






