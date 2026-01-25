"""
Endpoint de download - stateless
Recebe dados do vídeo e faz download. Aguarda conclusão antes de retornar.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from app.services.downloader.service import DownloaderService

router = APIRouter()

class DownloadRequest(BaseModel):
    """Request para download"""
    video_url: str
    platform: str
    external_video_id: str
    group_name: Optional[str] = None
    source_name: Optional[str] = None

@router.post("")
async def download_content(request: DownloadRequest):
    """
    Faz download de um vídeo. Aguarda o término do download antes de retornar.
    Retorna sucesso com path do arquivo ou erro se o download falhar.
    """
    downloader = DownloaderService()
    result = await downloader.download_video(
        video_url=request.video_url,
        platform=request.platform,
        external_video_id=request.external_video_id,
        group_name=request.group_name,
        source_name=request.source_name,
    )

    if result["status"] == "completed":
        return {
            "status": "completed",
            "path": result["path"],
            "external_video_id": request.external_video_id,
            "message": "Vídeo baixado com sucesso",
        }

    raise HTTPException(
        status_code=422,
        detail=result.get("error", "Falha ao baixar o vídeo"),
    )
