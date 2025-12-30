"""
Serviço de busca de conteúdo - stateless
Recebe dados, processa e retorna resultados
"""
import yt_dlp
import logging
from typing import List, Dict, Optional
from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

class FetcherService:
    def __init__(self):
        """Serviço stateless - não precisa de sessão de banco"""
        pass

    def _construct_url(self, platform: str, external_id: str) -> Optional[str]:
        """Constrói URL baseado na plataforma"""
        if platform == "youtube":
            return f"https://www.youtube.com/channel/{external_id}/videos"
        elif platform == "instagram":
            return f"https://www.instagram.com/{external_id}/"
        elif platform == "tiktok":
            return f"https://www.tiktok.com/@{external_id}"
        return None

    async def fetch_from_source_data(
        self,
        platform: str,
        external_id: str,
        group_name: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[Dict]:
        """
        Busca vídeos de uma fonte específica
        Retorna lista de vídeos encontrados
        """
        logger.info(f"Fetching from {platform}: {external_id} (limit: {limit})")
        
        url = self._construct_url(platform, external_id)
        if not url:
            logger.warning(f"Could not construct URL for {platform}: {external_id}")
            return []

        ydl_opts = {
            'quiet': True,
            'extract_flat': True,
            'force_generic_extractor': False,
        }
        
        # Limitar quantidade de vídeos se fornecido
        if limit and limit > 0:
            ydl_opts['playlistend'] = limit

        videos = []
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                
            if 'entries' in info:
                entries = info['entries']
            else:
                entries = [info]

            # Limitar resultados se ainda não foi limitado pelo yt-dlp
            if limit and limit > 0 and len(entries) > limit:
                entries = entries[:limit]

            for entry in entries:
                    if not entry:
                        continue
                    
                    video_data = {
                        "platform": platform,
                        "external_id": external_id,
                        "external_video_id": entry.get('id'),
                        "title": entry.get('title'),
                        "url": entry.get('url') or entry.get('webpage_url'),
                        "duration": entry.get('duration'),
                        "view_count": entry.get('view_count'),
                        "group_name": group_name,
                        "fetched_at": entry.get('upload_date') or entry.get('timestamp')
                    }
                    videos.append(video_data)

        except Exception as e:
            logger.error(f"Error fetching from {platform}: {external_id} - {e}")
            return []

        logger.info(f"Found {len(videos)} videos from {platform}: {external_id}")
        return videos
