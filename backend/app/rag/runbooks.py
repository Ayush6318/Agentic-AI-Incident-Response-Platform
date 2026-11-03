from langchain_text_splitters import RecursiveCharacterTextSplitter
from app.rag.store import db

SHARED = 0
_splitter = RecursiveCharacterTextSplitter(chunk_size=700, chunk_overlap=80)


def _own(user_id: int, name: str) -> dict:
    return {"$and": [{"source": {"$eq": "runbook"}}, {"user_id": {"$eq": user_id}}, {"name": {"$eq": name}}]}


def delete(user_id: int, name: str) -> int:
    old = db.get(where=_own(user_id, name))
    if old["ids"]:
        db.delete(ids=old["ids"])
    return len(old["ids"])


def ingest_text(user_id: int, name: str, text: str) -> int:
    delete(user_id, name)                                    # same name replaces the old version
    chunks = _splitter.split_text(text)[:40]
    db.add_texts(chunks, metadatas=[{"source": "runbook", "user_id": user_id, "name": name}] * len(chunks))
    return len(chunks)


def list_names(user_id: int) -> list[str]:
    got = db.get(where={"$and": [{"source": {"$eq": "runbook"}}, {"user_id": {"$eq": user_id}}]})
    return sorted({m["name"] for m in got["metadatas"]})


def search_runbooks_text(query: str, user_id: int | None, k: int = 3) -> str:
    """Plain retrieval from the user's runbooks and the shared ones. No model call."""
    if not query.strip():
        return ""
    try:
        docs = db.similarity_search(query[:600], k=k, filter={"$and": [
            {"source": {"$eq": "runbook"}}, {"user_id": {"$in": [user_id or SHARED, SHARED]}}]})
    except Exception:
        return ""
    return "\n---\n".join(f"({d.metadata.get('name')}) {d.page_content}" for d in docs)