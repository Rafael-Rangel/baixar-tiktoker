"""
Serviço de download - stateless
Recebe dados, faz download e salva organizado
"""
import yt_dlp
import os
import logging
from typing import Optional
from app.core.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

class DownloaderService:
    def __init__(self):
        """Serviço stateless - não precisa de sessão de banco"""
        pass

    async def download_video(
        self,
        video_url: str,
        platform: str,
        external_video_id: str,
        group_name: Optional[str] = None,
        source_name: Optional[str] = None
    ):
        """
        Faz download de um vídeo
        Organiza por: downloads/{grupo}/{fonte}/{video_id}.mp4
        """
        # Organizar estrutura de pastas
        if group_name and source_name:
            group_folder = group_name.replace(" ", "_").lower()
            source_folder = source_name.replace(" ", "_").lower()
            download_dir = os.path.join(settings.LOCAL_STORAGE_PATH, group_folder, source_folder)
        else:
            download_dir = os.path.join(settings.LOCAL_STORAGE_PATH, platform)
        
        os.makedirs(download_dir, exist_ok=True)
        output_path = os.path.join(download_dir, f"{external_video_id}.mp4")

        # Configurar opções do yt-dlp para contornar bloqueios do YouTube
        cookies_path = os.path.join(os.path.dirname(__file__), '../../data/cookies.txt')
        cookies_path = os.path.abspath(cookies_path)
        
        # Determinar qual cliente usar baseado na disponibilidade de cookies
        # Na VPS, o YouTube bloqueia android sem cookies mais agressivamente
        # Estratégia: se tiver cookies, usar apenas clientes que suportam cookies
        has_cookies = os.path.exists(cookies_path)
        
        if has_cookies:
            # Com cookies, tentar clientes que suportam cookies
            # tv_embedded funciona bem com cookies e não precisa de JS runtime
            # web_embedded também funciona melhor que web normal
            player_clients = ['tv_embedded', 'web_embedded', 'mweb', 'web']
        else:
            # Sem cookies, tentar android primeiro (funciona localmente)
            # Se falhar na VPS, tentar outros
            player_clients = ['android', 'tv', 'web']
        
        ydl_opts = {
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
            'outtmpl': output_path.replace('.mp4', '.%(ext)s'),
            'quiet': False,
            # Opções para contornar bloqueios do YouTube
            'extractor_args': {
                'youtube': {
                    'player_client': player_clients,
                }
            },
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'referer': 'https://www.youtube.com/',
        }
        
        # Adicionar cookies se o arquivo existir
        if has_cookies:
            ydl_opts['cookiefile'] = cookies_path
            logger.info(f"Using cookies file: {cookies_path} with web client")

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([video_url])
            logger.info(f"Downloaded: {output_path}")
            return {"status": "completed", "path": output_path}
        except Exception as e:
            logger.error(f"Download failed for {external_video_id}: {e}")
            return {"status": "failed", "error": str(e)}
