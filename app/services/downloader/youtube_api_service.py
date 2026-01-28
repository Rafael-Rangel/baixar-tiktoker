"""
Serviço de download direto via YouTube Player API
Contorna yt-dlp completamente, acessando diretamente a API do YouTube
"""
import os
import logging
import httpx
import subprocess
import json
import re
from typing import Optional

logger = logging.getLogger(__name__)


class YouTubeAPIDownloaderService:
    """Serviço para download direto via YouTube Player API"""
    
    def __init__(self):
        """Inicializa serviço stateless"""
        self.timeout = 60.0
        # API key do YouTube (pode ser qualquer uma, não precisa ser válida para player API)
        self.api_key = "AIzaSyAO_FJ2SlqU8Q4STEHLGCilw_Y9_11qW8U"  # Chave pública comum
    
    def _extract_video_id(self, url: str) -> Optional[str]:
        """Extrai video ID da URL"""
        patterns = [
            r'(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/shorts\/)([a-zA-Z0-9_-]{11})',
            r'youtube\.com\/embed\/([a-zA-Z0-9_-]{11})',
        ]
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None
    
    async def download_video(
        self,
        video_url: str,
        output_path: str,
        external_video_id: Optional[str] = None
    ) -> dict:
        """
        Faz download direto via YouTube Player API
        """
        try:
            logger.info(f"YouTube API: Starting direct download for {external_video_id or video_url}")
            
            video_id = external_video_id or self._extract_video_id(video_url)
            if not video_id:
                return {"status": "failed", "error": "Could not extract video ID"}
            
            output_path_abs = os.path.abspath(output_path)
            output_dir = os.path.dirname(output_path_abs)
            os.makedirs(output_dir, exist_ok=True)
            
            # Fazer requisição para YouTube Player API
            # Usar contexto do cliente web (navegador)
            context = {
                "client": {
                    "clientName": "WEB",
                    "clientVersion": "2.20240101.00.00",
                    "hl": "en",
                    "gl": "US"
                }
            }
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                # Tentar obter informações do player
                player_url = "https://www.youtube.com/youtubei/v1/player"
                
                payload = {
                    "context": context,
                    "videoId": video_id,
                    "params": "8AEB"  # Parâmetro para obter URLs de download
                }
                
                headers = {
                    "Content-Type": "application/json",
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
                    "Accept": "*/*",
                    "Origin": "https://www.youtube.com",
                    "Referer": f"https://www.youtube.com/watch?v={video_id}"
                }
                
                try:
                    response = await client.post(
                        player_url,
                        json=payload,
                        headers=headers,
                        params={"key": self.api_key}
                    )
                    
                    if response.status_code != 200:
                        logger.warning(f"YouTube API: Player API returned {response.status_code}")
                        # Tentar método alternativo: extrair da página HTML
                        return await self._download_from_page(client, video_url, output_path_abs, video_id)
                    
                    data = response.json()
                    
                    # Extrair URLs de streaming da resposta
                    streaming_data = data.get("streamingData", {})
                    formats = streaming_data.get("formats", [])
                    adaptive_formats = streaming_data.get("adaptiveFormats", [])
                    
                    if not formats and not adaptive_formats:
                        logger.warning("YouTube API: No streaming data found, trying page extraction")
                        return await self._download_from_page(client, video_url, output_path_abs, video_id)
                    
                    # Encontrar melhor formato disponível
                    best_video = None
                    best_audio = None
                    
                    # Procurar vídeo progressivo (vídeo+áudio juntos)
                    for fmt in formats:
                        if fmt.get("mimeType", "").startswith("video/"):
                            if not best_video or int(fmt.get("width", 0)) > int(best_video.get("width", 0)):
                                best_video = fmt
                    
                    # Se não houver progressivo, procurar adaptativo
                    if not best_video:
                        for fmt in adaptive_formats:
                            mime = fmt.get("mimeType", "")
                            if mime.startswith("video/"):
                                if not best_video or int(fmt.get("width", 0)) > int(best_video.get("width", 0)):
                                    best_video = fmt
                            elif mime.startswith("audio/"):
                                if not best_audio or int(fmt.get("bitrate", 0)) > int(best_audio.get("bitrate", 0)):
                                    best_audio = fmt
                    
                    # Baixar vídeo
                    if best_video:
                        video_url_download = best_video.get("url") or best_video.get("signatureCipher", "")
                        if not video_url_download:
                            return {"status": "failed", "error": "No video URL found"}
                        
                        # Se tiver signatureCipher, precisa decodificar (complexo, pular por enquanto)
                        if "signatureCipher" in str(best_video):
                            logger.warning("YouTube API: Signature cipher detected, trying page extraction")
                            return await self._download_from_page(client, video_url, output_path_abs, video_id)
                        
                        # Baixar vídeo
                        if best_audio:
                            # Baixar vídeo e áudio separadamente e fazer merge
                            video_path = os.path.join(output_dir, f"{video_id}_video.mp4")
                            audio_path = os.path.join(output_dir, f"{video_id}_audio.m4a")
                            
                            logger.info("YouTube API: Downloading video and audio separately")
                            async with httpx.AsyncClient(timeout=300.0) as dl_client:
                                async with dl_client.stream("GET", video_url_download) as resp:
                                    if resp.status_code == 200:
                                        with open(video_path, "wb") as f:
                                            async for chunk in resp.aiter_bytes():
                                                f.write(chunk)
                                
                                audio_url = best_audio.get("url")
                                if audio_url:
                                    async with dl_client.stream("GET", audio_url) as resp:
                                        if resp.status_code == 200:
                                            with open(audio_path, "wb") as f:
                                                async for chunk in resp.aiter_bytes():
                                                    f.write(chunk)
                            
                            # Fazer merge
                            logger.info("YouTube API: Merging video and audio")
                            merge_cmd = [
                                "ffmpeg", "-y", "-i", video_path, "-i", audio_path,
                                "-c:v", "copy", "-c:a", "copy", output_path_abs
                            ]
                            result = subprocess.run(merge_cmd, capture_output=True, text=True, timeout=300)
                            
                            # Limpar temporários
                            for p in [video_path, audio_path]:
                                try:
                                    if os.path.exists(p):
                                        os.remove(p)
                                except:
                                    pass
                            
                            if result.returncode == 0 and os.path.exists(output_path_abs) and os.path.getsize(output_path_abs) > 1000:
                                logger.info(f"YouTube API: Download successful! File size: {os.path.getsize(output_path_abs)} bytes")
                                return {"status": "completed", "path": output_path_abs}
                        else:
                            # Apenas vídeo (pode não ter áudio)
                            async with httpx.AsyncClient(timeout=300.0) as dl_client:
                                async with dl_client.stream("GET", video_url_download) as resp:
                                    if resp.status_code == 200:
                                        with open(output_path_abs, "wb") as f:
                                            async for chunk in resp.aiter_bytes():
                                                f.write(chunk)
                                        
                                        if os.path.exists(output_path_abs) and os.path.getsize(output_path_abs) > 1000:
                                            logger.info(f"YouTube API: Download successful! File size: {os.path.getsize(output_path_abs)} bytes")
                                            return {"status": "completed", "path": output_path_abs}
                    
                    return {"status": "failed", "error": "Could not extract video/audio URLs"}
                    
                except httpx.TimeoutException:
                    logger.error("YouTube API: Request timeout")
                    return await self._download_from_page(client, video_url, output_path_abs, video_id)
                except Exception as e:
                    logger.warning(f"YouTube API: Player API failed, trying page extraction: {e}")
                    return await self._download_from_page(client, video_url, output_path_abs, video_id)
            
        except Exception as e:
            logger.error(f"YouTube API: Download failed: {e}")
            import traceback
            logger.error(f"YouTube API: Traceback: {traceback.format_exc()}")
            return {"status": "failed", "error": f"YouTube API download failed: {str(e)}"}
    
    async def _download_from_page(self, client: httpx.AsyncClient, video_url: str, output_path: str, video_id: str) -> dict:
        """Método alternativo: extrair URL da página HTML e fazer download direto"""
        try:
            logger.info("YouTube API: Trying to extract from page HTML")
            
            # Baixar página HTML com headers completos
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "Accept-Encoding": "gzip, deflate",
                "Referer": "https://www.youtube.com/",
                "DNT": "1",
                "Connection": "keep-alive",
            }
            
            response = await client.get(video_url, headers=headers)
            
            if response.status_code != 200:
                return {"status": "failed", "error": f"Page request failed: {response.status_code}"}
            
            # Procurar por player_response no HTML (múltiplos padrões)
            html = response.text
            
            player_data = None
            patterns = [
                r'var ytInitialPlayerResponse = ({.+?});',
                r'ytInitialPlayerResponse\s*=\s*({.+?});',
                r'"playerResponse":\s*({.+?})',
                r'ytInitialPlayerResponse\s*=\s*({.+?});\s*var',
            ]
            
            for pattern in patterns:
                match = re.search(pattern, html, re.DOTALL)
                if match:
                    try:
                        player_data = json.loads(match.group(1))
                        logger.info("YouTube API: Found player_response in HTML")
                        break
                    except json.JSONDecodeError:
                        continue
            
            if not player_data:
                return {"status": "failed", "error": "Could not extract player data from page"}
            
            # Extrair streamingData
            streaming_data = player_data.get("streamingData", {})
            formats = streaming_data.get("formats", [])
            adaptive_formats = streaming_data.get("adaptiveFormats", [])
            
            if not formats and not adaptive_formats:
                return {"status": "failed", "error": "No streaming data in player_response"}
            
            # Encontrar melhor formato
            best_video = None
            best_audio = None
            
            # Procurar vídeo progressivo
            for fmt in formats:
                if fmt.get("mimeType", "").startswith("video/"):
                    if not best_video or int(fmt.get("width", 0)) > int(best_video.get("width", 0)):
                        best_video = fmt
            
            # Se não houver progressivo, procurar adaptativo
            if not best_video:
                for fmt in adaptive_formats:
                    mime = fmt.get("mimeType", "")
                    if mime.startswith("video/"):
                        if not best_video or int(fmt.get("width", 0)) > int(best_video.get("width", 0)):
                            best_video = fmt
                    elif mime.startswith("audio/"):
                        if not best_audio or int(fmt.get("bitrate", 0)) > int(best_audio.get("bitrate", 0)):
                            best_audio = fmt
            
            if not best_video:
                return {"status": "failed", "error": "No video format found"}
            
            video_url_download = best_video.get("url")
            if not video_url_download:
                # Se tiver signatureCipher, não podemos decodificar facilmente
                if "signatureCipher" in str(best_video):
                    return {"status": "failed", "error": "Signature cipher detected, use CDP or Selenium"}
                return {"status": "failed", "error": "No video URL found"}
            
            # Baixar vídeo
            output_path_abs = os.path.abspath(output_path)
            output_dir = os.path.dirname(output_path_abs)
            os.makedirs(output_dir, exist_ok=True)
            
            if best_audio:
                # Baixar vídeo e áudio separadamente
                video_path = os.path.join(output_dir, f"{video_id}_video.mp4")
                audio_path = os.path.join(output_dir, f"{video_id}_audio.m4a")
                
                logger.info("YouTube API: Downloading video and audio separately from HTML")
                
                # Baixar vídeo
                async with client.stream("GET", video_url_download, headers=headers) as resp:
                    if resp.status_code == 200:
                        with open(video_path, "wb") as f:
                            async for chunk in resp.aiter_bytes():
                                f.write(chunk)
                
                # Baixar áudio
                audio_url = best_audio.get("url")
                if audio_url:
                    async with client.stream("GET", audio_url, headers=headers) as resp:
                        if resp.status_code == 200:
                            with open(audio_path, "wb") as f:
                                async for chunk in resp.aiter_bytes():
                                    f.write(chunk)
                
                # Fazer merge
                logger.info("YouTube API: Merging video and audio")
                merge_cmd = [
                    "ffmpeg", "-y", "-i", video_path, "-i", audio_path,
                    "-c:v", "copy", "-c:a", "copy", output_path_abs
                ]
                result = subprocess.run(merge_cmd, capture_output=True, text=True, timeout=300)
                
                # Limpar temporários
                for p in [video_path, audio_path]:
                    try:
                        if os.path.exists(p):
                            os.remove(p)
                    except:
                        pass
                
                if result.returncode == 0 and os.path.exists(output_path_abs) and os.path.getsize(output_path_abs) > 1000:
                    logger.info(f"YouTube API: Download successful from HTML! File size: {os.path.getsize(output_path_abs)} bytes")
                    return {"status": "completed", "path": output_path_abs}
            else:
                # Apenas vídeo
                async with client.stream("GET", video_url_download, headers=headers) as resp:
                    if resp.status_code == 200:
                        with open(output_path_abs, "wb") as f:
                            async for chunk in resp.aiter_bytes():
                                f.write(chunk)
                        
                        if os.path.exists(output_path_abs) and os.path.getsize(output_path_abs) > 1000:
                            logger.info(f"YouTube API: Download successful from HTML! File size: {os.path.getsize(output_path_abs)} bytes")
                            return {"status": "completed", "path": output_path_abs}
            
            return {"status": "failed", "error": "Download failed"}
            
        except Exception as e:
            logger.error(f"YouTube API: Page extraction failed: {e}")
            import traceback
            logger.error(f"YouTube API: Traceback: {traceback.format_exc()}")
            return {"status": "failed", "error": f"Page extraction failed: {str(e)}"}
