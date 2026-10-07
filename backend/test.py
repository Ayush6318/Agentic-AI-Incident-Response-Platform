from app.agents.graph import graph
cfg = {"configurable": {"thread_id": "t1"}}
out = graph.invoke({"incident": "payment-service HTTP 500 after deploy", "evidence": []}, cfg)
print(out["root_cause"]); print(out["plan"])