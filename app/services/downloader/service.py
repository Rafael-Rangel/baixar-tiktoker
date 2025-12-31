"""
Serviço de download usando Playwright
Simula navegador real para fazer download de vídeos do YouTube
"""
import os
import logging
import httpx
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
        Faz download de um vídeo usando Playwright
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

        # Usar Playwright para fazer download
        try:
            logger.info(f"Starting Playwright download for {external_video_id}")
            result = await self._download_with_playwright(video_url, output_path)
            return result
        except Exception as e:
            logger.error(f"Playwright download failed for {external_video_id}: {e}")
            return {"status": "failed", "error": f"Playwright error: {str(e)}"}

    async def _download_with_playwright(self, video_url: str, output_path: str):
        """Download usando Playwright - simula navegador real"""
        try:
            from playwright.async_api import async_playwright
            import re
            import json
            
            async with async_playwright() as p:
                # Lançar navegador headless
                browser = await p.chromium.launch(
                    headless=True,
                    args=[
                        '--no-sandbox',
                        '--disable-setuid-sandbox',
                        '--disable-dev-shm-usage',
                        '--disable-accelerated-2d-canvas',
                        '--disable-gpu'
                    ]
                )
                
                context = await browser.new_context(
                    viewport={'width': 1920, 'height': 1080},
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                )
                
                page = await context.new_page()
                
                # Navegar até o vídeo
                logger.info(f"Navigating to {video_url}")
                await page.goto(video_url, wait_until='networkidle', timeout=60000)
                
                # Aguardar vídeo carregar
                await page.wait_for_timeout(3000)
                
                # Tentar extrair URL do vídeo de várias formas
                video_url_direct = None
                
                # Método 1: Tentar encontrar URL no player
                try:
                    # Esperar pelo player do YouTube
                    await page.wait_for_selector('video', timeout=10000)
                    
                    # Tentar pegar src do elemento video
                    video_element = await page.query_selector('video')
                    if video_element:
                        src = await video_element.get_attribute('src')
                        if src and src.startswith('http'):
                            video_url_direct = src
                            logger.info("Found video URL in video element")
                except Exception as e:
                    logger.debug(f"Method 1 failed: {e}")
                
                # Método 2: Extrair do JavaScript/network
                if not video_url_direct:
                    try:
                        # Interceptar requisições de mídia
                        video_urls = []
                        
                        async def handle_response(response):
                            url = response.url
                            # Procurar por URLs de vídeo
                            if any(ext in url for ext in ['.mp4', '.webm', 'videoplayback', 'googlevideo.com']):
                                if 'mime=video' in url or 'itag=' in url:
                                    video_urls.append(url)
                        
                        page.on('response', handle_response)
                        
                        # Recarregar página para capturar requisições
                        await page.reload(wait_until='networkidle', timeout=60000)
                        await page.wait_for_timeout(5000)
                        
                        if video_urls:
                            # Pegar melhor qualidade (maior itag ou resolução)
                            video_url_direct = video_urls[0]
                            logger.info(f"Found video URL from network: {video_url_direct[:100]}...")
                    except Exception as e:
                        logger.debug(f"Method 2 failed: {e}")
                
                # Método 3: Usar yt-dlp via subprocess como fallback
                if not video_url_direct:
                    logger.info("Could not extract direct URL, trying yt-dlp as fallback")
                    await browser.close()
                    return await self._download_with_ytdlp_fallback(video_url, output_path)
                
                await browser.close()
                
                # Fazer download do vídeo usando httpx
                if video_url_direct:
                    logger.info(f"Downloading video from direct URL...")
                    async with httpx.AsyncClient(timeout=300.0) as client:
                        async with client.stream('GET', video_url_direct) as response:
                            response.raise_for_status()
                            total_size = int(response.headers.get('content-length', 0))
                            
                            with open(output_path, 'wb') as f:
                                downloaded = 0
                                async for chunk in response.aiter_bytes(chunk_size=8192):
                                    f.write(chunk)
                                    downloaded += len(chunk)
                                    if total_size > 0:
                                        percent = (downloaded / total_size) * 100
                                        if downloaded % (1024 * 1024) == 0:  # Log a cada MB
                                            logger.info(f"Downloaded {downloaded}/{total_size} bytes ({percent:.1f}%)")
                    
                    if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                        logger.info(f"Downloaded with Playwright: {output_path}")
                        return {"status": "completed", "path": output_path}
                    else:
                        return {"status": "failed", "error": "File not created or empty"}
                else:
                    return {"status": "failed", "error": "Could not extract video URL"}
                    
        except Exception as e:
            logger.error(f"Playwright download failed: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return {"status": "failed", "error": f"Playwright error: {str(e)}"}

    async def _download_with_ytdlp_fallback(self, video_url: str, output_path: str):
        """Fallback usando yt-dlp via subprocess"""
        try:
            import subprocess
            import asyncio
            
            # Usar yt-dlp via subprocess
            cmd = [
                'yt-dlp',
                video_url,
                '-f', 'best[ext=mp4]/best',
                '-o', output_path.replace('.mp4', '.%(ext)s'),
                '--no-warnings',
                '--quiet'
            ]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                # Verificar se arquivo foi criado
                if os.path.exists(output_path):
                    return {"status": "completed", "path": output_path}
                else:
                    # Procurar arquivo com extensão diferente
                    base_path = output_path.replace('.mp4', '')
                    for ext in ['.mp4', '.webm', '.mkv']:
                        if os.path.exists(base_path + ext):
                            return {"status": "completed", "path": base_path + ext}
                    return {"status": "failed", "error": "File not found after yt-dlp download"}
            else:
                error_msg = stderr.decode() if stderr else "Unknown error"
                return {"status": "failed", "error": f"yt-dlp failed: {error_msg}"}
                
        except Exception as e:
            logger.error(f"yt-dlp fallback failed: {e}")
            return {"status": "failed", "error": f"yt-dlp fallback error: {str(e)}"}
