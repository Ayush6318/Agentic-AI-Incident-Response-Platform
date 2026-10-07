from app.rag.store import db

def remember(incident : str,root_cause:str):
  db.add_texts([f"Incident : {incident}\n Root cause : {root_cause}"],metadatas=[{"source":"past_incident"}])
  
def recall(incident:str)->str:
  docs = db.similarity_search(incident,k=2,filter={"source":"past_incident"})
  return "\n".join(d.page_content for d in docs)
  