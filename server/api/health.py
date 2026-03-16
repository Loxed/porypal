"""
server/api/health.py

Routes: /api/health
"""

from fastapi import APIRouter
from server.state import state

router = APIRouter(prefix="/api", tags=["health"])


@router.get("/health")
def health():
    return {"status": "ok", "palettes_loaded": len(state.palette_manager.get_palettes())}