from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.db import get_cursor
from app.api.routes import ensure_admin_tables, router


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.on_event("startup")
def startup():
    conn, cur = get_cursor()
    try:
        ensure_admin_tables(cur)
        conn.commit()
    finally:
        cur.close()
        conn.close()


@app.get("/")
def root():
    return {"message": "BehaviorGuard-AI backend running"}
