import json

MAX_CHARS = 6000


def clip(text: str, limit: int = MAX_CHARS) -> str:
    return text if len(text) <= limit else text[:limit] + f"\n...[truncated {len(text) - limit} chars]"


def as_tool_output(source: str, payload) -> str:
    body = payload if isinstance(payload, str) else json.dumps(payload, default=str)
    body = clip(body).replace("</tool_output", "<\\/tool_output")
    return f'<tool_output source="{source}">\n{body}\n</tool_output>'