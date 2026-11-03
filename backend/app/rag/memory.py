from app.rag.store import db


def remember(incident: str, root_cause: str, user_id: int | None = None, service: str = "") -> None:
    db.add_texts([f"Incident: {incident}\nRoot cause: {root_cause[:1500]}"],
                 metadatas=[{"source": "past_incident", "user_id": user_id or 0, "service": service}])


def recall(incident: str, user_id: int | None = None, k: int = 2) -> str:
    try:
        docs = db.similarity_search(incident, k=k, filter={"$and": [
            {"source": {"$eq": "past_incident"}}, {"user_id": {"$eq": user_id or 0}}]})
    except Exception:
        return ""
    return "\n".join(d.page_content for d in docs)