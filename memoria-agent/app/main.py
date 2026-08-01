"""FastAPI entrypoint for memoria-agent."""
from fastapi import FastAPI
from app.api.routes import router

app = FastAPI(title="Memoria Agent", version="0.1.0")
app.include_router(router)
