import asyncio, json, os, time, argparse
from datetime import datetime
from pathlib import Path
from statistics import mean

from app.agents.graph import build_graph
from app.evals.dataset import INCIDENTS
from app.evals.tracker import Tracker
from app.evals.scoring import (judge_cause, parse_action, tool_selection_ok,
                               service_args_ok, action_outcome)

# USD per 1M tokens. Fill these in from the pricing page for your model.
PRICE_IN, PRICE_OUT = 3.0, 15.0
RESULTS_DIR = Path(__file__).parent / "results"


async def run_one(inc: dict, trial: int) -> dict:
    os.environ["SCENARIO"] = inc["scenario"]      # tools now read this scenario's data
    tracker = Tracker()
    graph = build_graph()                          # fresh graph + fresh MemorySaver
    thread = {"configurable": {"thread_id": f"eval-{inc['id']}-{trial}"}}
    run_cfg = {**thread, "callbacks": [tracker]}

    row = {"id": inc["id"], "trial": trial, "completed": False, "error": None}
    start = time.time()
    try:
        await graph.ainvoke({"incident": inc["text"], "evidence": []}, run_cfg)
        state = graph.get_state(thread)
        row["completed"] = tuple(state.next) == ("approval",)   # paused for human = success
        root_cause = state.values.get("root_cause", "")
        plan = state.values.get("plan", "")
    except Exception as e:
        row["error"] = repr(e)
        root_cause, plan = "", ""
    row["latency_s"] = round(time.time() - start, 2)

    if root_cause:
        v = await judge_cause(root_cause, inc["expected_cause"])
        row["cause_correct"] = v.correct
        row["judge_reason"] = v.reason
    else:
        row["cause_correct"] = False
        row["judge_reason"] = "no root cause produced"

    proposed = parse_action(plan)
    row["proposed_action"] = proposed
    row["action_outcome"] = action_outcome(proposed, inc["expected_action"])
    row["tool_selection_ok"] = tool_selection_ok(tracker.tool_calls, inc["expected_tools"])
    row["service_args_ok"] = service_args_ok(tracker.tool_calls, inc["service"])
    row["tool_calls"] = len(tracker.tool_calls)
    row["tokens"] = tracker.input_tokens + tracker.output_tokens
    row["cost_usd"] = round(tracker.input_tokens / 1e6 * PRICE_IN
                            + tracker.output_tokens / 1e6 * PRICE_OUT, 4)
    return row


def summarize(rows: list[dict]) -> dict:
    n = len(rows)
    pct = lambda key, val=True: round(100 * sum(r[key] == val for r in rows) / n, 1)
    return {
        "runs": n,
        "completion_rate_%": pct("completed"),
        "root_cause_accuracy_%": pct("cause_correct"),
        "action_accuracy_%": pct("action_outcome", "correct"),
        "wrong_action_rate_%": pct("action_outcome", "wrong"),
        "tool_selection_%": pct("tool_selection_ok"),
        "tool_args_%": pct("service_args_ok"),
        "avg_tool_calls": round(mean(r["tool_calls"] for r in rows), 1),
        "avg_latency_s": round(mean(r["latency_s"] for r in rows), 1),
        "avg_tokens": int(mean(r["tokens"] for r in rows)),
        "avg_cost_usd": round(mean(r["cost_usd"] for r in rows), 4),
    }


async def main(trials: int):
    rows = []
    for inc in INCIDENTS:
        for t in range(trials):                    # sequential: SCENARIO env var is global
            row = await run_one(inc, t)
            rows.append(row)
            print(f"{inc['id']:<14} t{t}  cause={row['cause_correct']!s:<5} "
                  f"action={row['action_outcome']:<8} {row['latency_s']}s")

    summary = summarize(rows)
    print("\n=== SUMMARY ===")
    for k, v in summary.items():
        print(f"{k:<24} {v}")

    RESULTS_DIR.mkdir(exist_ok=True)
    out = RESULTS_DIR / f"{datetime.now():%Y%m%d_%H%M%S}.json"
    out.write_text(json.dumps({"summary": summary, "rows": rows}, indent=2))
    print("\nSaved:", out)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--trials", type=int, default=3)
    args = ap.parse_args()
    asyncio.run(main(args.trials))