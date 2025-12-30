"""
Endpoint de fetch - simplificado
"""
from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Optional
from app.services.fetcher.service import FetcherService

router = APIRouter()

class SourceRequest(BaseModel):
    platform: str
    external_id: str
    group_name: Optional[str] = None
    limit: Optional[int] = None  # Limite de vídeos (opcional)
    video_type: Optional[str] = "videos"  # "videos" ou "shorts" para YouTube

@router.post("/run")
async def run_fetch(request: SourceRequest):
    """
    Busca vídeos de uma fonte
    Retorna lista de vídeos encontrados
    """
    fetcher = FetcherService()
    videos = await fetcher.fetch_from_source_data(
        platform=request.platform,
        external_id=request.external_id,
        group_name=request.group_name,
        limit=request.limit,
        video_type=request.video_type or "videos"
    )
    
    return {
        "status": "completed",
        "videos_found": len(videos),
        "videos": videos
    }
