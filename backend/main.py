import os
from fastapi import FastAPI, Request
from fastapi.responses import Response
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from dotenv import load_dotenv
from fastapi.staticfiles import StaticFiles
from fastapi.responses import Response, FileResponse

load_dotenv()

from database import engine, Base
import models  # noqa: F401 — ensures tables are registered

from routers import auth_router, people_router, ai_router, settings_router

# Create all DB tables on startup
Base.metadata.create_all(bind=engine)


def ensure_user_columns():
    """Small SQLite-safe migration for new business-specific onboarding fields."""
    from sqlalchemy import text
    columns = {
        "business_description": "TEXT DEFAULT ''",
        "offer": "TEXT DEFAULT ''",
        "target_customer": "TEXT DEFAULT ''",
        "outreach_style": "TEXT DEFAULT ''",
        "personalization_style": "TEXT DEFAULT ''",
        "personalization_examples": "TEXT DEFAULT ''",
        "objection_style": "TEXT DEFAULT ''",
        "step1_script": "TEXT DEFAULT ''",
        "step2_script": "TEXT DEFAULT ''",
        "step3_script": "TEXT DEFAULT ''",
        "step4_script": "TEXT DEFAULT ''",
        "onboarding_complete": "INTEGER DEFAULT 0",
    }
    with engine.connect() as conn:
        existing = [row[1] for row in conn.execute(text("PRAGMA table_info(users)"))]
        for name, ddl in columns.items():
            if name not in existing:
                conn.execute(text(f"ALTER TABLE users ADD COLUMN {name} {ddl}"))
        conn.commit()

ensure_user_columns()


app = FastAPI(title="Outreach Agent API", version="1.0.0")


# Custom CORS middleware that handles null Origin (file:// pages)
class PermissiveCORSMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.method == "OPTIONS":
            response = Response(status_code=200)
        else:
            response = await call_next(request)
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, PATCH, DELETE, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
        return response


app.add_middleware(PermissiveCORSMiddleware)

# Mount all routers under /api
app.include_router(auth_router.router, prefix="/api")
app.include_router(people_router.router, prefix="/api")
app.include_router(ai_router.router, prefix="/api")
app.include_router(settings_router.router, prefix="/api")


@app.get("/api/health")
def health():
    return {"status": "ok"}

FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")

if os.path.isdir(FRONTEND_DIR):
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")

    @app.get("/")
    def serve_frontend():
        return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))