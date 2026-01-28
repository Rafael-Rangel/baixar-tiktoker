"""
Serviço de download usando Chrome DevTools Protocol (CDP)
Intercepta requisições de rede para capturar URLs de streaming diretamente
Técnica avançada que contorna completamente yt-dlp e APIs públicas
"""
import os
import logging
import time
import json
import re
import httpx
import subprocess
from typing import Optional, Dict, List
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from webdriver_manager.chrome import ChromeDriverManager

logger = logging.getLogger(__name__)


class CDPDownloaderService:
    """Serviço para download usando Chrome DevTools Protocol"""
    
    def __init__(self):
        """Inicializa serviço stateless"""
        self.driver = None
        self.captured_urls = []
        self.video_urls = []
        self.audio_urls = []
    
    def _get_chrome_options(self) -> Options:
        """Configura opções do Chrome com CDP habilitado"""
        options = Options()
        options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")
        
        # Habilitar logging para CDP
        options.set_capability('goog:loggingPrefs', {'performance': 'ALL'})
        options.add_experimental_option('excludeSwitches', ['enable-logging'])
        options.add_experimental_option('useAutomationExtension', False)
        
        return options
    
    def _init_driver(self) -> webdriver.Chrome:
        """Inicializa driver do Chrome com CDP"""
        try:
            options = self._get_chrome_options()
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=options)
            
            # Remover indicadores de automação
            driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
                'source': '''
                    Object.defineProperty(navigator, 'webdriver', {
                        get: () => undefined
                    });
                    window.chrome = { runtime: {} };
                '''
            })
            
            # Habilitar Network Domain para interceptar requisições
            driver.execute_cdp_cmd('Network.enable', {})
            driver.execute_cdp_cmd('Page.enable', {})
            
            return driver
        except Exception as e:
            logger.error(f"Failed to initialize Chrome driver with CDP: {e}")
            raise
    
    def _extract_streaming_urls_from_logs(self, driver: webdriver.Chrome) -> Dict[str, List[str]]:
        """Extrai URLs de streaming dos logs de performance do Chrome"""
        video_urls = []
        audio_urls = []
        
        try:
            # Obter logs de performance
            logs = driver.get_log('performance')
            
            for log in logs:
                try:
                    message = json.loads(log['message'])
                    method = message.get('message', {}).get('method', '')
                    params = message.get('message', {}).get('params', {})
                    
                    # Interceptar respostas de rede
                    if method == 'Network.responseReceived':
                        response = params.get('response', {})
                        url = response.get('url', '')
                        mime_type = response.get('mimeType', '')
                        
                        # Procurar por URLs de streaming do YouTube
                        if 'googlevideo.com' in url:
                            if 'videoplayback' in url:
                                # Verificar se é vídeo ou áudio
                                if 'mime=video' in url or 'itag=' in url:
                                    # Extrair itag para determinar qualidade
                                    itag_match = re.search(r'itag=(\d+)', url)
                                    if itag_match:
                                        itag = int(itag_match.group(1))
                                        # Itags de vídeo: 18, 22, 37, 38, 43, 44, 45, 46, 135-140, 242-248, 271-278
                                        # Itags de áudio: 139, 140, 141, 171, 249-251
                                        if itag in [139, 140, 141, 171, 249, 250, 251]:
                                            if url not in audio_urls:
                                                audio_urls.append(url)
                                        else:
                                            if url not in video_urls:
                                                video_urls.append(url)
                                elif 'mime=audio' in url:
                                    if url not in audio_urls:
                                        audio_urls.append(url)
                    
                    # Interceptar requisições de rede também
                    elif method == 'Network.requestWillBeSent':
                        request = params.get('request', {})
                        url = request.get('url', '')
                        
                        if 'googlevideo.com' in url and 'videoplayback' in url:
                            if 'mime=video' in url or ('itag=' in url and 'mime=audio' not in url):
                                if url not in video_urls:
                                    video_urls.append(url)
                            elif 'mime=audio' in url:
                                if url not in audio_urls:
                                    audio_urls.append(url)
                
                except (json.JSONDecodeError, KeyError, ValueError) as e:
                    continue
            
            logger.info(f"CDP: Found {len(video_urls)} video URLs and {len(audio_urls)} audio URLs")
            
        except Exception as e:
            logger.warning(f"CDP: Error extracting URLs from logs: {e}")
        
        return {"video": video_urls, "audio": audio_urls}
    
    def _extract_urls_from_page_source(self, driver: webdriver.Chrome, video_id: str) -> Dict[str, List[str]]:
        """Extrai URLs de streaming do HTML da página"""
        video_urls = []
        audio_urls = []
        
        try:
            page_source = driver.page_source
            
            # Procurar por player_response no HTML
            patterns = [
                r'var ytInitialPlayerResponse = ({.+?});',
                r'ytInitialPlayerResponse\s*=\s*({.+?});',
                r'"playerResponse":\s*({.+?})',
            ]
            
            player_data = None
            for pattern in patterns:
                match = re.search(pattern, page_source, re.DOTALL)
                if match:
                    try:
                        player_data = json.loads(match.group(1))
                        break
                    except json.JSONDecodeError:
                        continue
            
            if player_data:
                # Extrair streamingData
                streaming_data = player_data.get('streamingData', {})
                formats = streaming_data.get('formats', [])
                adaptive_formats = streaming_data.get('adaptiveFormats', [])
                
                all_formats = formats + adaptive_formats
                
                for fmt in all_formats:
                    url = fmt.get('url') or fmt.get('signatureCipher', '')
                    mime_type = fmt.get('mimeType', '')
                    itag = fmt.get('itag', 0)
                    
                    if url and 'googlevideo.com' in url:
                        if mime_type.startswith('video/'):
                            if url not in video_urls:
                                video_urls.append(url)
                        elif mime_type.startswith('audio/'):
                            if url not in audio_urls:
                                audio_urls.append(url)
                        elif itag:
                            # Classificar por itag se mimeType não estiver disponível
                            if itag in [139, 140, 141, 171, 249, 250, 251]:
                                if url not in audio_urls:
                                    audio_urls.append(url)
                            else:
                                if url not in video_urls:
                                    video_urls.append(url)
            
            logger.info(f"CDP: Extracted {len(video_urls)} video URLs and {len(audio_urls)} audio URLs from page source")
            
        except Exception as e:
            logger.warning(f"CDP: Error extracting URLs from page source: {e}")
        
        return {"video": video_urls, "audio": audio_urls}
    
    def _load_cookies(self, driver: webdriver.Chrome) -> bool:
        """Carrega cookies existentes"""
        try:
            from app.core.config import get_settings
            from app.services.downloader.service import DownloaderService
            
            settings = get_settings()
            downloader = DownloaderService()
            cookies_path = downloader._resolve_cookies_path()
            
            if not cookies_path or not os.path.exists(cookies_path):
                return False
            
            driver.get("https://www.youtube.com")
            time.sleep(2)
            
            cookies_loaded = 0
            with open(cookies_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    
                    parts = line.split('\t')
                    if len(parts) < 7:
                        continue
                    
                    domain, flag, path, secure, expiration, name, value = parts[:7]
                    
                    cookie_dict = {
                        'name': name,
                        'value': value,
                        'domain': domain.lstrip('.'),
                        'path': path,
                        'secure': secure == 'TRUE',
                    }
                    
                    if expiration and expiration != '0':
                        try:
                            cookie_dict['expiry'] = int(expiration)
                        except:
                            pass
                    
                    try:
                        driver.add_cookie(cookie_dict)
                        cookies_loaded += 1
                    except:
                        pass
            
            logger.info(f"CDP: Loaded {cookies_loaded} cookies")
            return cookies_loaded > 0
            
        except Exception as e:
            logger.warning(f"CDP: Failed to load cookies: {e}")
            return False
    
    def _download_direct_sync(self, video_url: str, audio_url: Optional[str], output_path: str) -> bool:
        """Faz download direto das URLs capturadas (método síncrono)"""
        try:
            if not video_url:
                return False
            
            output_path_abs = os.path.abspath(output_path)
            output_dir = os.path.dirname(output_path_abs)
            os.makedirs(output_dir, exist_ok=True)
            
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
                "Accept": "*/*",
                "Accept-Language": "en-US,en;q=0.9",
                "Referer": "https://www.youtube.com/",
                "Origin": "https://www.youtube.com",
            }
            
            if audio_url:
                # Baixar vídeo e áudio separadamente
                video_temp = os.path.join(output_dir, f"_temp_video.mp4")
                audio_temp = os.path.join(output_dir, f"_temp_audio.m4a")
                
                logger.info("CDP: Downloading video and audio separately")
                
                async def download_file(url: str, path: str):
                    try:
                        async with httpx.AsyncClient(timeout=300.0, follow_redirects=True) as client:
                            async with client.stream("GET", url, headers=headers) as response:
                                if response.status_code == 200:
                                    with open(path, "wb") as f:
                                        async for chunk in response.aiter_bytes():
                                            f.write(chunk)
                                    return True
                                else:
                                    logger.warning(f"CDP: Download failed with status {response.status_code}")
                                    return False
                    except Exception as e:
                        logger.error(f"CDP: Download error: {e}")
                        return False
                
                import asyncio
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                try:
                    # Baixar vídeo
                    video_ok = loop.run_until_complete(download_file(video_url, video_temp))
                    if not video_ok:
                        return False
                    
                    # Baixar áudio
                    audio_ok = loop.run_until_complete(download_file(audio_url, audio_temp))
                    if not audio_ok:
                        if os.path.exists(video_temp):
                            os.remove(video_temp)
                        return False
                finally:
                    loop.close()
                
                # Fazer merge
                logger.info("CDP: Merging video and audio")
                merge_cmd = [
                    "ffmpeg", "-y", "-i", video_temp, "-i", audio_temp,
                    "-c:v", "copy", "-c:a", "copy", output_path_abs
                ]
                result = subprocess.run(merge_cmd, capture_output=True, text=True, timeout=300)
                
                # Limpar temporários
                for p in [video_temp, audio_temp]:
                    try:
                        if os.path.exists(p):
                            os.remove(p)
                    except:
                        pass
                
                if result.returncode == 0 and os.path.exists(output_path_abs) and os.path.getsize(output_path_abs) > 1000:
                    logger.info(f"CDP: Download successful! File size: {os.path.getsize(output_path_abs)} bytes")
                    return True
            else:
                # Apenas vídeo
                logger.info("CDP: Downloading video only")
                import asyncio
                async def download():
                    try:
                        async with httpx.AsyncClient(timeout=300.0, follow_redirects=True) as client:
                            async with client.stream("GET", video_url, headers=headers) as response:
                                if response.status_code == 200:
                                    with open(output_path_abs, "wb") as f:
                                        async for chunk in response.aiter_bytes():
                                            f.write(chunk)
                                    return True
                                else:
                                    logger.warning(f"CDP: Download failed with status {response.status_code}")
                                    return False
                    except Exception as e:
                        logger.error(f"CDP: Download error: {e}")
                        return False
                
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    if loop.run_until_complete(download()):
                        if os.path.exists(output_path_abs) and os.path.getsize(output_path_abs) > 1000:
                            logger.info(f"CDP: Download successful! File size: {os.path.getsize(output_path_abs)} bytes")
                            return True
                finally:
                    loop.close()
            
            return False
            
        except Exception as e:
            logger.error(f"CDP: Direct download failed: {e}")
            import traceback
            logger.error(f"CDP: Traceback: {traceback.format_exc()}")
            return False
    
    def _download_video_sync(self, video_url: str, output_path: str, external_video_id: Optional[str] = None) -> dict:
        """Método síncrono para download usando CDP"""
        try:
            logger.info(f"CDP: Starting download for {external_video_id or video_url}")
            
            self.driver = self._init_driver()
            
            # Carregar cookies
            self._load_cookies(self.driver)
            
            # Navegar para página inicial do YouTube
            logger.info("CDP: Establishing session on YouTube homepage")
            self.driver.get("https://www.youtube.com")
            time.sleep(5)
            
            # Simular interações humanas
            for scroll_pos in [200, 400, 300, 0]:
                self.driver.execute_script(f"window.scrollTo(0, {scroll_pos});")
                time.sleep(1)
            
            # Navegar até o vídeo
            logger.info(f"CDP: Navigating to {video_url}")
            self.driver.get(video_url)
            
            # Aguardar página carregar
            try:
                WebDriverWait(self.driver, 30).until(
                    EC.presence_of_element_located((By.TAG_NAME, "video"))
                )
                logger.info("CDP: Video element found")
            except TimeoutException:
                logger.warning("CDP: Video element not found, but continuing...")
            
            # Aguardar mais tempo para requisições de rede serem feitas
            time.sleep(10)
            
            # Simular interações
            try:
                video_element = self.driver.find_element(By.TAG_NAME, "video")
                self.driver.execute_script("arguments[0].play();", video_element)
                time.sleep(5)
            except:
                pass
            
            # Extrair URLs de duas formas
            urls_from_logs = self._extract_streaming_urls_from_logs(self.driver)
            urls_from_page = self._extract_urls_from_page_source(self.driver, external_video_id or "")
            
            # Combinar URLs (priorizar logs, depois page source)
            all_video_urls = urls_from_logs["video"] + urls_from_page["video"]
            all_audio_urls = urls_from_logs["audio"] + urls_from_page["audio"]
            
            # Remover duplicatas mantendo ordem
            seen_video = set()
            unique_video_urls = []
            for url in all_video_urls:
                if url not in seen_video:
                    seen_video.add(url)
                    unique_video_urls.append(url)
            
            seen_audio = set()
            unique_audio_urls = []
            for url in all_audio_urls:
                if url not in seen_audio:
                    seen_audio.add(url)
                    unique_audio_urls.append(url)
            
            logger.info(f"CDP: Found {len(unique_video_urls)} unique video URLs and {len(unique_audio_urls)} unique audio URLs")
            
            if not unique_video_urls:
                return {"status": "failed", "error": "No video URLs found"}
            
            # Tentar fazer download com cada URL até uma funcionar
            best_video_url = unique_video_urls[0]  # Pegar a primeira (geralmente melhor qualidade)
            best_audio_url = unique_audio_urls[0] if unique_audio_urls else None
            
            # Tentar download direto
            if self._download_direct_sync(best_video_url, best_audio_url, output_path):
                return {"status": "completed", "path": os.path.abspath(output_path)}
            
            return {"status": "failed", "error": "Direct download failed for all URLs"}
            
        except Exception as e:
            logger.error(f"CDP: Download failed: {e}")
            import traceback
            logger.error(f"CDP: Traceback: {traceback.format_exc()}")
            return {"status": "failed", "error": f"CDP download failed: {str(e)}"}
        finally:
            if self.driver:
                try:
                    self.driver.quit()
                except:
                    pass
                self.driver = None
    
    async def download_video(
        self,
        video_url: str,
        output_path: str,
        external_video_id: Optional[str] = None
    ) -> dict:
        """Faz download usando Chrome DevTools Protocol"""
        import asyncio
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._download_video_sync, video_url, output_path, external_video_id)
