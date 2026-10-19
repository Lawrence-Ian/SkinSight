"""
SKINSIGHT v2 — FastAPI Backend
Live camera scan only. No file upload permitted.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import analysis, auth, history, chat, locations
from app.database import init_db

app = FastAPI(title="SKINSIGHT API v2", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup():
    init_db()

app.include_router(auth.router,      prefix="/api/auth",      tags=["Auth"])
app.include_router(analysis.router,  prefix="/api/analysis",  tags=["Analysis"])
app.include_router(history.router,   prefix="/api/history",   tags=["History"])
app.include_router(chat.router,      prefix="/api/chat",      tags=["Chat"])
app.include_router(locations.router, prefix="/api/locations", tags=["Locations"])

@app.get("/health")
async def health():
    return {"status": "ok", "version": "2.0.0"}
