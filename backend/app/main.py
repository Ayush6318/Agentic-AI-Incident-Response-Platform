from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from langgraph.checkpoint.postgres import PostgresSaver

from app.api import auth, incidents
from app.config import settings
from app.db.database import pool, checkpoint_pool
from app.db.migrate import run as run_migrations
from app.agents.graph import build_graph

@asynccontextmanager
async def lifespan(app: FastAPI):
    run_migrations()                       # keep the schema up to date
    pool.open(); pool.wait()
    checkpoint_pool.open(); checkpoint_pool.wait()
    checkpointer = PostgresSaver(checkpoint_pool)
    checkpointer.setup()                   # creates LangGraph's own tables (safe to repeat)
    app.state.graph = build_graph(checkpointer)
    yield
    checkpoint_pool.close()
    pool.close()

app = FastAPI(title="Incident Agent", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=settings.CORS_ORIGINS.split(","),
                   allow_methods=["*"], allow_headers=["*"])
app.include_router(auth.router)
app.include_router(incidents.router)

@app.get("/health")
def health():
    return {"ok": True}