from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.db import get_cursor
from app.api.routes import ensure_admin_tables, router
from app.services.auto_replay import auto_replay_engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Startup ──────────────────────────────────────────────────────────────
    # Ensure admin tables exist
    conn, cur = get_cursor()
    try:
        ensure_admin_tables(cur)
        conn.commit()
    finally:
        cur.close()
        conn.close()

    # Start the autonomous event generator
    await auto_replay_engine.start()

    yield  # server is running

    # ── Shutdown ─────────────────────────────────────────────────────────────
    await auto_replay_engine.stop()


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/")
def root():
    return {"message": "BehaviorGuard-AI backend running"}
