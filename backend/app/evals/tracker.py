from langchain_core.callbacks import BaseCallbackHandler

class Tracker(BaseCallbackHandler):
    def __init__(self):
        self.tool_calls = []         
        self.input_tokens = 0
        self.output_tokens = 0

    def on_tool_start(self, serialized, input_str, **kwargs):
        self.tool_calls.append({
            "name": (serialized or {}).get("name"),
            "input": kwargs.get("inputs") or input_str,
        })

    def on_llm_end(self, response, **kwargs):
        for gens in response.generations:
            for g in gens:
                usage = getattr(getattr(g, "message", None), "usage_metadata", None)
                if usage:
                    self.input_tokens += usage.get("input_tokens", 0)
                    self.output_tokens += usage.get("output_tokens", 0)