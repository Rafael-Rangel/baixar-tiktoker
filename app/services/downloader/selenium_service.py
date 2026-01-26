"""
Serviço de download usando Selenium (Chrome headless) como fallback
Usado quando yt-dlp falha devido a detecção de bot do YouTube
"""
import os
import logging
import time
from typing import Optional
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from webdriver_manager.chrome import ChromeDriverManager
import yt_dlp

logger = logging.getLogger(__name__)


class SeleniumDownloaderService:
    """Serviço para download usando navegador real (Chrome headless)"""
    
    def __init__(self):
        """Inicializa serviço stateless"""
        self.driver = None
    
    def _get_chrome_options(self) -> Options:
        """Configura opções do Chrome para modo headless"""
        options = Options()
        options.add_argument("--headless=new")  # Novo modo headless do Chrome
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-software-rasterizer")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--disable-features=IsolateOrigins,site-per-process")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--start-maximized")
        options.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
        options.add_experimental_option('useAutomationExtension', False)
        options.add_experimental_option("detach", True)
        # User agent mais recente e completo
        options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")
        # Adicionar preferências para parecer mais humano
        prefs = {
            "profile.default_content_setting_values": {
                "notifications": 2,
                "geolocation": 2,
            },
            "profile.managed_default_content_settings": {
                "images": 1
            }
        }
        options.add_experimental_option("prefs", prefs)
        return options
    
    def _init_driver(self) -> webdriver.Chrome:
        """Inicializa driver do Chrome"""
        try:
            options = self._get_chrome_options()
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=options)
            # Remover indicadores de automação com script mais completo
            driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
                'source': '''
                    Object.defineProperty(navigator, 'webdriver', {
                        get: () => undefined
                    });
                    window.chrome = {
                        runtime: {}
                    };
                    Object.defineProperty(navigator, 'plugins', {
                        get: () => [1, 2, 3, 4, 5]
                    });
                    Object.defineProperty(navigator, 'languages', {
                        get: () => ['en-US', 'en']
                    });
                '''
            })
            return driver
        except Exception as e:
            logger.error(f"Failed to initialize Chrome driver: {e}")
            raise
    
    def _load_existing_cookies(self) -> bool:
        """Carrega cookies existentes do arquivo cookies.txt no navegador"""
        try:
            from app.core.config import get_settings
            from app.services.downloader.service import DownloaderService
            
            settings = get_settings()
            downloader = DownloaderService()
            cookies_path = downloader._resolve_cookies_path()
            
            if not cookies_path or not os.path.exists(cookies_path):
                logger.warning("Selenium: No existing cookies file found")
                return False
            
            # Ler cookies do arquivo Netscape
            logger.info(f"Selenium: Loading existing cookies from {cookies_path}")
            cookies_loaded = 0
            
            # Primeiro navegar até o domínio para poder adicionar cookies
            self.driver.get("https://www.youtube.com")
            time.sleep(2)
            
            with open(cookies_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    
                    # Formato Netscape: domain, flag, path, secure, expiration, name, value
                    parts = line.split('\t')
                    if len(parts) < 7:
                        continue
                    
                    domain, flag, path, secure, expiration, name, value = parts[:7]
                    
                    # Converter para formato do Selenium
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
                        self.driver.add_cookie(cookie_dict)
                        cookies_loaded += 1
                    except Exception as e:
                        # Alguns cookies podem falhar (domínio incorreto, etc)
                        pass
            
            logger.info(f"Selenium: Loaded {cookies_loaded} cookies from file")
            return cookies_loaded > 0
            
        except Exception as e:
            logger.warning(f"Selenium: Failed to load existing cookies: {e}")
            return False
    
    def _extract_cookies_from_browser(self, video_url: str) -> Optional[str]:
        """Extrai cookies do navegador após navegar até o vídeo"""
        try:
            self.driver = self._init_driver()
            
            # Carregar cookies existentes primeiro
            logger.info("Selenium: Loading existing cookies...")
            cookies_loaded = self._load_existing_cookies()
            
            # Estabelecer sessão navegando primeiro para a página inicial do YouTube
            logger.info("Selenium: Establishing session on YouTube homepage...")
            self.driver.get("https://www.youtube.com")
            time.sleep(3)  # Aguardar página inicial carregar
            
            # Fazer scroll para simular interação humana
            try:
                self.driver.execute_script("window.scrollTo(0, 300);")
                time.sleep(1)
                self.driver.execute_script("window.scrollTo(0, 0);")
                time.sleep(1)
            except:
                pass
            
            logger.info(f"Selenium: Navigating to {video_url}")
            
            # Navegar até o vídeo (agora com cookies carregados e sessão estabelecida)
            self.driver.get(video_url)
            
            # Verificar se não há bloqueio de bot
            page_source = self.driver.page_source.lower()
            if "sorry" in page_source and "bot" in page_source:
                logger.error("Selenium: YouTube bot detection page detected!")
                return None
            
            # Aguardar página carregar (aguardar elemento de vídeo aparecer)
            video_found = False
            try:
                WebDriverWait(self.driver, 20).until(
                    EC.presence_of_element_located((By.TAG_NAME, "video"))
                )
                logger.info("Selenium: Video element found, page loaded")
                video_found = True
            except TimeoutException:
                logger.warning("Selenium: Video element not found, but continuing...")
                # Verificar se há mensagem de erro na página
                if "unavailable" in page_source or "private" in page_source:
                    logger.error("Selenium: Video appears to be unavailable or private")
                    return None
            
            # Aguardar mais tempo para garantir que página carregou completamente
            # e cookies de sessão foram atualizados
            time.sleep(8)  # Aumentado de 5 para 8 segundos
            
            # Simular interações humanas mais realistas
            try:
                # Scroll gradual para baixo
                for i in range(3):
                    scroll_pos = (i + 1) * 200
                    self.driver.execute_script(f"window.scrollTo(0, {scroll_pos});")
                    time.sleep(1.5)
                
                # Scroll de volta para cima
                self.driver.execute_script("window.scrollTo(0, 0);")
                time.sleep(2)
                
                # Tentar interagir com o player de vídeo (se disponível)
                if video_found:
                    try:
                        # Tentar clicar no vídeo para iniciar (pode gerar mais cookies)
                        video_element = self.driver.find_element(By.TAG_NAME, "video")
                        self.driver.execute_script("arguments[0].click();", video_element)
                        time.sleep(2)
                    except:
                        pass
            except Exception as e:
                logger.warning(f"Selenium: Error during page interaction: {e}")
            
            # Aguardar mais um pouco para cookies serem atualizados após interações
            time.sleep(3)
            
            # Extrair cookies do navegador
            cookies = self.driver.get_cookies()
            
            # Log cookies importantes para debug
            important_cookies = ['__Secure-3PSID', '__Secure-3PAPISID', 'LOGIN_INFO', 'VISITOR_INFO1_LIVE', 'YSC']
            found_important = [c['name'] for c in cookies if c['name'] in important_cookies]
            logger.info(f"Selenium: Found important cookies: {found_important}")
            
            # Criar arquivo temporário de cookies no formato Netscape
            import tempfile
            temp_cookies_file = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False)
            
            # Escrever header do formato Netscape
            temp_cookies_file.write("# Netscape HTTP Cookie File\n")
            temp_cookies_file.write("# This file is generated by Selenium. Do not edit.\n\n")
            
            # Escrever cookies
            for cookie in cookies:
                domain = cookie.get('domain', '')
                if not domain.startswith('.'):
                    domain = '.' + domain
                
                # Formato Netscape: domain, flag, path, secure, expiration, name, value
                secure = 'TRUE' if cookie.get('secure', False) else 'FALSE'
                expiration = str(int(cookie.get('expiry', 0))) if cookie.get('expiry') else '0'
                path = cookie.get('path', '/')
                
                line = f"{domain}\tTRUE\t{path}\t{secure}\t{expiration}\t{cookie['name']}\t{cookie['value']}\n"
                temp_cookies_file.write(line)
            
            temp_cookies_file.close()
            logger.info(f"Selenium: Extracted {len(cookies)} cookies to {temp_cookies_file.name}")
            
            return temp_cookies_file.name
            
        except Exception as e:
            logger.error(f"Selenium: Failed to extract cookies: {e}")
            import traceback
            logger.error(f"Selenium: Traceback: {traceback.format_exc()}")
            return None
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
        """
        Faz download usando Selenium como fallback
        Estratégia: Extrai cookies do navegador e usa com yt-dlp
        """
        cookies_file = None
        try:
            logger.info(f"Selenium: Starting download fallback for {external_video_id or video_url}")
            
            # Extrair cookies do navegador (executar em thread separada para não bloquear)
            import asyncio
            loop = asyncio.get_event_loop()
            cookies_file = await loop.run_in_executor(None, self._extract_cookies_from_browser, video_url)
            
            if not cookies_file:
                return {"status": "failed", "error": "Failed to extract cookies from browser"}
            
            # Tentar download com yt-dlp usando cookies do navegador
            logger.info("Selenium: Attempting download with yt-dlp using browser cookies")
            
            output_path_abs = os.path.abspath(output_path)
            
            # Tentar múltiplas estratégias com os cookies do navegador
            strategies = [
                {
                    "name": "bestvideo+bestaudio",
                    "opts": {
                        "cookiefile": cookies_file,
                        "outtmpl": output_path_abs.replace(".mp4", ".%(ext)s"),
                        "format": "bestvideo+bestaudio/best",
                        "merge_output_format": "mp4",
                        "quiet": True,
                        "no_warnings": True,
                        "noplaylist": True,
                        "extractor_args": {
                            "youtube": {
                                "player_client": ["ios", "android", "mweb", "web"]
                            }
                        },
                        "referer": "https://www.youtube.com/",
                        "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
                        "http_headers": {
                            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                            "Accept-Language": "en-US,en;q=0.5",
                            "Accept-Encoding": "gzip, deflate",
                            "DNT": "1",
                            "Connection": "keep-alive",
                            "Upgrade-Insecure-Requests": "1",
                        }
                    }
                },
                {
                    "name": "best format",
                    "opts": {
                        "cookiefile": cookies_file,
                        "outtmpl": output_path_abs.replace(".mp4", ".%(ext)s"),
                        "format": "best",
                        "quiet": True,
                        "no_warnings": True,
                        "noplaylist": True,
                        "extractor_args": {
                            "youtube": {
                                "player_client": ["ios", "android"]
                            }
                        },
                        "referer": "https://www.youtube.com/",
                        "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
                    }
                },
                {
                    "name": "format 18",
                    "opts": {
                        "cookiefile": cookies_file,
                        "outtmpl": output_path_abs.replace(".mp4", ".%(ext)s"),
                        "format": "18",
                        "quiet": True,
                        "no_warnings": True,
                        "noplaylist": True,
                        "referer": "https://www.youtube.com/",
                        "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
                    }
                }
            ]
            
            for strategy in strategies:
                try:
                    logger.info(f"Selenium: Trying strategy: {strategy['name']}")
                    with yt_dlp.YoutubeDL(strategy['opts']) as ydl:
                        ydl.download([video_url])
                    
                    # Verificar se arquivo foi criado
                    if os.path.exists(output_path_abs) and os.path.getsize(output_path_abs) > 1000:
                        logger.info(f"Selenium: Download successful with {strategy['name']}! File size: {os.path.getsize(output_path_abs)} bytes")
                        return {"status": "completed", "path": output_path_abs}
                    
                    # Tentar outros formatos/extensões
                    base = output_path_abs.replace(".mp4", "")
                    for ext in [".webm", ".mkv", ".m4a"]:
                        p = base + ext
                        if os.path.exists(p) and os.path.getsize(p) > 1000:
                            if ext != ".mp4":
                                os.rename(p, output_path_abs)
                            logger.info(f"Selenium: Download successful with {strategy['name']}! File size: {os.path.getsize(output_path_abs)} bytes")
                            return {"status": "completed", "path": output_path_abs}
                            
                except Exception as e:
                    logger.warning(f"Selenium: Strategy {strategy['name']} failed: {e}")
                    continue
            
            # Se todas as estratégias falharam, retornar erro
            return {"status": "failed", "error": "All Selenium download strategies failed"}
            
            
        except Exception as e:
            logger.error(f"Selenium: Download failed: {e}")
            return {"status": "failed", "error": f"Selenium download failed: {str(e)}"}
        finally:
            # Limpar arquivo temporário de cookies
            if cookies_file and os.path.exists(cookies_file):
                try:
                    os.unlink(cookies_file)
                except:
                    pass
            
            # Garantir que driver está fechado
            if self.driver:
                try:
                    self.driver.quit()
                except:
                    pass
                self.driver = None
