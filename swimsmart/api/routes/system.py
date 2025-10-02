from __future__ import annotations
from fastapi import APIRouter, Depends
from pydantic import BaseModel
import os

router = APIRouter()

APP_VERSION = os.getenv("SWIMSMART_VERSION", "0.20.0")
APP_ENV = os.getenv("SWIMSMART_ENV", "development")

class HealthResponse(BaseModel):
    status: str = "ok"

class VersionResponse(BaseModel):
    version: str
    env: str

@router.get("/health", response_model= HealthResponse)
def health() -> dict:
    return {"status": "ok"}

@router.get("/version", response_model=VersionResponse)
def version() -> dict:
    return {"version": APP_VERSION, "env": APP_ENV}