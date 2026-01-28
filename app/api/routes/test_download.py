"""
Rota de teste - testa todas as estratégias de download em ordem
Útil para identificar qual estratégia funciona melhor
"""
import time
import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict
from app.services.downloader.service import DownloaderService

router = APIRouter()
logger = logging.getLogger(__name__)


class TestDownloadRequest(BaseModel):
    """Request para teste de download"""
    video_url: str
    external_video_id: str
    platform: str = "youtube"


@router.post("")
async def test_download(request: TestDownloadRequest):
    """
    Testa TODAS as estratégias de download em ordem (rápido → lento)
    Retorna qual estratégia funcionou e estatísticas de cada tentativa
    """
    downloader = DownloaderService()
    attempts: List[Dict] = []
    start_time = time.time()
    
    # Criar caminho temporário para teste
    import os
    from app.core.config import get_settings
    settings = get_settings()
    test_dir = os.path.join(settings.LOCAL_STORAGE_PATH, "test_downloads")
    os.makedirs(test_dir, exist_ok=True)
    test_output = os.path.join(test_dir, f"{request.external_video_id}_test.mp4")
    
    # Limpar arquivo de teste anterior se existir
    if os.path.exists(test_output):
        try:
            os.remove(test_output)
        except:
            pass
    
    # ESTRATÉGIA 1: yt-dlp format 18 (mais rápido)
    logger.info("Test: Trying yt-dlp format 18")
    strategy_start = time.time()
    try:
        import yt_dlp
        opts = {
            "format": "18",
            "outtmpl": test_output.replace(".mp4", ".%(ext)s"),
            "noplaylist": True,
            "quiet": True,
            "no_warnings": True,
        }
        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([request.video_url])
        
        if os.path.exists(test_output) and os.path.getsize(test_output) > 1000:
            elapsed = time.time() - strategy_start
            attempts.append({
                "strategy": "yt-dlp-format18",
                "status": "success",
                "time": round(elapsed, 2),
                "file_size": os.path.getsize(test_output)
            })
            return {
                "status": "success",
                "strategy_used": "yt-dlp-format18",
                "time_taken": round(time.time() - start_time, 2),
                "file_path": test_output,
                "attempts": attempts
            }
        else:
            elapsed = time.time() - strategy_start
            attempts.append({
                "strategy": "yt-dlp-format18",
                "status": "failed",
                "time": round(elapsed, 2),
                "error": "File not created or too small"
            })
    except Exception as e:
        elapsed = time.time() - strategy_start
        attempts.append({
            "strategy": "yt-dlp-format18",
            "status": "failed",
            "time": round(elapsed, 2),
            "error": str(e)[:200]
        })
    
    # ESTRATÉGIA 2: yt-dlp best
    logger.info("Test: Trying yt-dlp best")
    strategy_start = time.time()
    try:
        import yt_dlp
        opts = {
            "format": "best",
            "outtmpl": test_output.replace(".mp4", ".%(ext)s"),
            "noplaylist": True,
            "quiet": True,
            "no_warnings": True,
        }
        cookies_path = downloader._resolve_cookies_path()
        if cookies_path:
            opts["cookiefile"] = cookies_path
        
        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([request.video_url])
        
        # Verificar extensões alternativas
        base = test_output.replace(".mp4", "")
        for ext in [".mp4", ".webm", ".mkv"]:
            p = base + ext
            if os.path.exists(p) and os.path.getsize(p) > 1000:
                if ext != ".mp4":
                    os.rename(p, test_output)
                elapsed = time.time() - strategy_start
                attempts.append({
                    "strategy": "yt-dlp-best",
                    "status": "success",
                    "time": round(elapsed, 2),
                    "file_size": os.path.getsize(test_output)
                })
                return {
                    "status": "success",
                    "strategy_used": "yt-dlp-best",
                    "time_taken": round(time.time() - start_time, 2),
                    "file_path": test_output,
                    "attempts": attempts
                }
        
        elapsed = time.time() - strategy_start
        attempts.append({
            "strategy": "yt-dlp-best",
            "status": "failed",
            "time": round(elapsed, 2),
            "error": "File not created or too small"
        })
    except Exception as e:
        elapsed = time.time() - strategy_start
        attempts.append({
            "strategy": "yt-dlp-best",
            "status": "failed",
            "time": round(elapsed, 2),
            "error": str(e)[:200]
        })
    
    # ESTRATÉGIA 3: pytubefix
    logger.info("Test: Trying pytubefix")
    strategy_start = time.time()
    try:
        from app.services.downloader.pytubefix_service import PytubefixDownloaderService
        pytubefix_service = PytubefixDownloaderService()
        result = await pytubefix_service.download_video(
            request.video_url, test_output, request.external_video_id
        )
        
        elapsed = time.time() - strategy_start
        if result.get('status') == 'completed':
            attempts.append({
                "strategy": "pytubefix",
                "status": "success",
                "time": round(elapsed, 2),
                "file_size": os.path.getsize(result['path']) if os.path.exists(result['path']) else 0
            })
            return {
                "status": "success",
                "strategy_used": "pytubefix",
                "time_taken": round(time.time() - start_time, 2),
                "file_path": result['path'],
                "attempts": attempts
            }
        else:
            attempts.append({
                "strategy": "pytubefix",
                "status": "failed",
                "time": round(elapsed, 2),
                "error": result.get('error', 'Unknown error')[:200]
            })
    except Exception as e:
        elapsed = time.time() - strategy_start
        attempts.append({
            "strategy": "pytubefix",
            "status": "failed",
            "time": round(elapsed, 2),
            "error": str(e)[:200]
        })
    
    # ESTRATÉGIA 4: YouTube Player API direto
    logger.info("Test: Trying YouTube Player API direct")
    strategy_start = time.time()
    try:
        from app.services.downloader.youtube_api_service import YouTubeAPIDownloaderService
        api_service = YouTubeAPIDownloaderService()
        result = await api_service.download_video(
            request.video_url, test_output, request.external_video_id
        )
        
        elapsed = time.time() - strategy_start
        if result.get('status') == 'completed':
            attempts.append({
                "strategy": "youtube-api-direct",
                "status": "success",
                "time": round(elapsed, 2),
                "file_size": os.path.getsize(result['path']) if os.path.exists(result['path']) else 0
            })
            return {
                "status": "success",
                "strategy_used": "youtube-api-direct",
                "time_taken": round(time.time() - start_time, 2),
                "file_path": result['path'],
                "attempts": attempts
            }
        else:
            attempts.append({
                "strategy": "youtube-api-direct",
                "status": "failed",
                "time": round(elapsed, 2),
                "error": result.get('error', 'Unknown error')[:200]
            })
    except Exception as e:
        elapsed = time.time() - strategy_start
        attempts.append({
            "strategy": "youtube-api-direct",
            "status": "failed",
            "time": round(elapsed, 2),
            "error": str(e)[:200]
        })
    
    # ESTRATÉGIA 5: Selenium download direto (se implementado)
    # Por enquanto, pular para Selenium + yt-dlp
    
    # ESTRATÉGIA 6: Selenium + yt-dlp
    logger.info("Test: Trying Selenium + yt-dlp")
    strategy_start = time.time()
    try:
        from app.services.downloader.selenium_service import SeleniumDownloaderService
        selenium_service = SeleniumDownloaderService()
        result = await selenium_service.download_video(
            request.video_url, test_output, request.external_video_id
        )
        
        elapsed = time.time() - strategy_start
        if result.get('status') == 'completed':
            attempts.append({
                "strategy": "selenium-ytdlp",
                "status": "success",
                "time": round(elapsed, 2),
                "file_size": os.path.getsize(result['path']) if os.path.exists(result['path']) else 0
            })
            return {
                "status": "success",
                "strategy_used": "selenium-ytdlp",
                "time_taken": round(time.time() - start_time, 2),
                "file_path": result['path'],
                "attempts": attempts
            }
        else:
            attempts.append({
                "strategy": "selenium-ytdlp",
                "status": "failed",
                "time": round(elapsed, 2),
                "error": result.get('error', 'Unknown error')[:200]
            })
    except Exception as e:
        elapsed = time.time() - strategy_start
        attempts.append({
            "strategy": "selenium-ytdlp",
            "status": "failed",
            "time": round(elapsed, 2),
            "error": str(e)[:200]
        })
    
    # Todas as estratégias falharam
    total_time = time.time() - start_time
    return {
        "status": "failed",
        "strategy_used": None,
        "time_taken": round(total_time, 2),
        "file_path": None,
        "attempts": attempts,
        "error": "All strategies failed"
    }
