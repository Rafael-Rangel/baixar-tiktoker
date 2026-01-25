"""
Endpoints específicos para integração com n8n
API stateless - recebe dados do n8n, processa e retorna resultados
Dados gerenciados via Google Sheets no n8n
"""
from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Optional
from app.services.fetcher.service import FetcherService

router = APIRouter()

class SourceData(BaseModel):
    """Dados de uma fonte vinda do n8n/Google Sheets"""
    platform: str  # youtube, instagram, tiktok
    external_id: str  # ID do canal/perfil
    group_name: Optional[str] = None
    video_type: Optional[str] = "videos"  # "videos" ou "shorts" para YouTube

class ProcessRequest(BaseModel):
    """Request para processar fontes"""
    sources: List[SourceData]
    limit: Optional[int] = None  # Limite de vídeos por fonte (opcional)

@router.post("/process-sources")
async def process_sources(request: ProcessRequest):
    """
    Processa fontes recebidas do n8n. Aguarda conclusão e retorna vídeos.
    n8n envia: sources[], limit. Retorna: status, videos_found, videos[], errors[].
    """
    fetcher = FetcherService()
    videos: List[dict] = []
    errors: List[dict] = []

    for source_data in request.sources:
        try:
            items = await fetcher.fetch_from_source_data(
                platform=source_data.platform,
                external_id=source_data.external_id,
                group_name=source_data.group_name,
                limit=request.limit,
                video_type=source_data.video_type or "videos",
            )
            videos.extend(items)
        except Exception as e:
            errors.append({
                "error": str(e),
                "source": source_data.external_id,
                "platform": source_data.platform,
            })

    return {
        "status": "completed",
        "videos_found": len(videos),
        "videos": videos,
        "errors": errors,
    }

@router.get("/health")
async def health_check():
    """Health check simples"""
    return {"status": "ok", "message": "n8n integration ready"}
