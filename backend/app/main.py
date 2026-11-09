from fastapi import FastAPI
from sqlalchemy import create_engine, text

from app.core.config import settings

engine = create_engine(settings.database_url)

app = FastAPI(title="QueueForge")


@app.get("/health")
def health() -> dict[str, str]:
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
    return {"status": "ok", "database": "connected"}
