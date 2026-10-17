from app.agents.graph import code_agents

out = code_agents.invoke({"messages": [("user", "payment-service returns HTTP 500 after the latest deploy")]})
print(out["messages"][-1].content)