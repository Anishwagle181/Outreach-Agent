import os
from fastapi import FastAPI, Request
from fastapi.responses import Response
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from dotenv import load_dotenv

load_dotenv()

from database import engine, Base
import models  # noqa: F401 — ensures tables are registered

from routers import auth_router, people_router, ai_router, settings_router

# Create all DB tables on startup
Base.metadata.create_all(bind=engine)

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

