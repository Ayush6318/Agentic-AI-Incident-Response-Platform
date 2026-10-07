from pathlib import Path
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.tools import tool

RUNBOOKS = Path(__file__).resolve().parents[2] / "data" / "runbooks"

emb = HuggingFaceEmbeddings(model_name = "all-MiniLM-L6-v2")
db = Chroma(collection_name="runbooks",embedding_function=emb,persist_directory="./chroma")

def ingest():
  splitter = RecursiveCharacterTextSplitter(chunk_size = 500,chunk_overlap = 5)
  for f in RUNBOOKS.glob(".*md"):    
   chunks = splitter.split_text(f.read_text())
   db.add_texts(chunks,metadatas=[{"source":f.name}]* len(chunks))
  
@tool
def search_runbooks(query: str) -> str:
    """Search internal runbooks for how to handle an issue."""
    docs = db.similarity_search(query, k=3)
    return "\n---\n".join(f"({d.metadata['source']}) {d.page_content}" for d in docs)
  

if __name__ == "__main__":
    ingest(); print(search_runbooks.invoke({"query": "connection pool exhausted"}))
