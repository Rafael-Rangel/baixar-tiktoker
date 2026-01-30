import os
import uuid
import re
import random
import json
import requests
import http.cookiejar as cookiejar
from flask import Flask, request, send_file, jsonify
from flask_cors import CORS
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Importar BeautifulSoup para método Urlebird
try:
    from bs4 import BeautifulSoup
    BEAUTIFULSOUP_AVAILABLE = True
except ImportError:
    logger.warning("BeautifulSoup4 não está instalado. Método Urlebird não estará disponível.")
    BEAUTIFULSOUP_AVAILABLE = False
    BeautifulSoup = None

# Importar Selenium para método Urlebird com anti-detecção
try:
    import undetected_chromedriver as uc
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.common.exceptions import TimeoutException, WebDriverException
    SELENIUM_AVAILABLE = True
except ImportError:
    logger.warning("Selenium/undetected-chromedriver não está instalado. Método Urlebird com Selenium não estará disponível.")
    SELENIUM_AVAILABLE = False
    uc = None

# Importar SeleniumBase (método mais avançado conforme guia Cloudflare)
try:
    from seleniumbase import Driver
    SELENIUMBASE_AVAILABLE = True
except ImportError:
    logger.info("SeleniumBase não está instalado. Usando undetected-chromedriver padrão.")
    SELENIUMBASE_AVAILABLE = False
    Driver = None

# Importar Browser Use (Agent-based browser automation)
try:
    from browser_use import Agent, Browser, ChatBrowserUse
    import asyncio
    BROWSER_USE_AVAILABLE = True
except ImportError:
    logger.info("Browser Use não está instalado. Execute: pip install browser-use")
    BROWSER_USE_AVAILABLE = False
    Agent = Browser = ChatBrowserUse = None
    asyncio = None

# Importar Playwright com Stealth (método recomendado pelo Manus para bypass Cloudflare)
try:
    from playwright.async_api import async_playwright
    try:
        from playwright_stealth.stealth import Stealth
        PLAYWRIGHT_STEALTH_AVAILABLE = True
    except ImportError:
        logger.info("playwright-stealth não está instalado. Execute: pip install playwright-stealth")
        PLAYWRIGHT_STEALTH_AVAILABLE = False
        Stealth = None
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    logger.info("Playwright não está instalado. Execute: pip install playwright")
    PLAYWRIGHT_AVAILABLE = False
    async_playwright = None
    Stealth = None
    PLAYWRIGHT_STEALTH_AVAILABLE = False

# Importar Apify Client (API profissional para scraping TikTok)
try:
    from apify_client import ApifyClient
    APIFY_AVAILABLE = True
except ImportError:
    logger.info("Apify Client não está instalado. Execute: pip install apify-client")
    APIFY_AVAILABLE = False
    ApifyClient = None

app = Flask(__name__)
CORS(app)  # Permitir CORS para n8n

# Configurações
DOWNLOAD_DIR = os.getenv('DOWNLOAD_DIR', './downloads')
PORT = int(os.getenv('PORT', 5000))

# Criar pasta de downloads se não existir
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# Importar biblioteca tiktok-downloader
try:
    # Importar apenas serviços que funcionam: Snaptik, TTDownloader, TikWM, MusicallyDown
    from tiktok_downloader import TTDownloader, TikWM
    from tiktok_downloader import snaptik, mdown, tikwm, ttdownloader
    TIKTOK_DOWNLOADER_AVAILABLE = True
except ImportError as e:
    logger.error(f"tiktok-downloader não está instalado ou erro na importação: {e}. Execute: pip install tiktok_downloader")
    TIKTOK_DOWNLOADER_AVAILABLE = False
    TTDownloader = TikWM = None
    snaptik = mdown = tikwm = ttdownloader = None

# Função para carregar cookies de um arquivo formato Netscape
def load_cookies_from_file(file_path="/app/cookies.txt"):
    """Carrega cookies do arquivo formato Netscape e retorna dicionário"""
    cookies_dict = {}
    if not os.path.exists(file_path):
        logger.debug(f"Arquivo de cookies não encontrado: {file_path}")
        return cookies_dict
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                
                # Formato Netscape: domain, flag, path, secure, expiration, name, value
                parts = line.split('\t')
                if len(parts) >= 7:
                    try:
                        cookie_domain = parts[0]
                        cookie_name = parts[5]
                        cookie_value = parts[6]
                        
                        # Só adicionar cookies do domínio urlebird.com
                        if 'urlebird.com' in cookie_domain:
                            cookies_dict[cookie_name] = cookie_value
                    except Exception as e:
                        logger.debug(f"Erro ao processar cookie: {e}")
                        continue
        
        if cookies_dict:
            logger.info(f"✓ {len(cookies_dict)} cookie(s) carregado(s) de {file_path}")
        else:
            logger.warning(f"Nenhum cookie válido encontrado em {file_path}")
    except Exception as e:
        logger.warning(f"Erro ao carregar cookies: {e}")
    
    return cookies_dict

# Carregar cookies globalmente na inicialização
URLEBIRD_COOKIES = load_cookies_from_file()

def validate_tiktok_url(url):
    """Valida se a URL é do TikTok"""
    tiktok_patterns = [
        r'https?://(www\.)?(tiktok\.com|vt\.tiktok\.com)',
        r'https?://(www\.)?tiktok\.com/@[\w.]+/video/\d+',
        r'https?://vt\.tiktok\.com/\w+',
        r'https?://vm\.tiktok\.com/\w+',
    ]
    
    if not url or not isinstance(url, str):
        return False
    
    return any(re.search(pattern, url, re.IGNORECASE) for pattern in tiktok_patterns)

def validate_username(username):
    """Valida se o username é válido (remove @ se presente)"""
    if not username or not isinstance(username, str):
        return None
    username = username.strip().lstrip('@')
    # Validar formato básico de username
    if re.match(r'^[\w.]+$', username):
        return username
    return None

def get_channel_data(username, soup):
    """Extrai dados do canal (seguidores, curtidas totais, vídeos postados)"""
    channel_data = {
        'followers': None,
        'total_likes': None,
        'videos_count': None
    }
    
    try:
        # Tentar encontrar elementos com classes específicas
        # Seguidores
        followers_elem = soup.find('span', class_=lambda x: x and 'follower' in x.lower())
        if not followers_elem:
            followers_elem = soup.find('span', string=lambda x: x and 'follower' in x.lower())
        if followers_elem:
            followers_text = followers_elem.get_text(strip=True)
            # Extrair número
            followers_match = re.search(r'([\d.]+[KMB]?)', followers_text)
            if followers_match:
                channel_data['followers'] = followers_match.group(1)
        
        # Curtidas totais (hearts)
        hearts_elem = soup.find('span', class_=lambda x: x and 'heart' in x.lower())
        if hearts_elem:
            hearts_text = hearts_elem.get_text(strip=True)
            hearts_match = re.search(r'([\d.]+[KMB]?)', hearts_text)
            if hearts_match:
                channel_data['total_likes'] = hearts_match.group(1)
        
        # Vídeos postados
        videos_elem = soup.find('span', class_=lambda x: x and 'video' in x.lower())
        if videos_elem:
            videos_text = videos_elem.get_text(strip=True)
            videos_match = re.search(r'(\d+)', videos_text)
            if videos_match:
                channel_data['videos_count'] = videos_match.group(1)
        
    except Exception as e:
        logger.warning(f"Erro ao extrair dados do canal: {str(e)}")
    
    return channel_data

def get_latest_video_url_from_channel_selenium(username):
    """Extrai a URL do vídeo mais recente usando Selenium com anti-detecção
    
    Retorna: (tiktok_url, urlebird_video_url, channel_data, error)
    """
    if not SELENIUM_AVAILABLE:
        return None, None, None, "Selenium não está instalado. Execute: pip install selenium undetected-chromedriver"
    
    driver = None
    try:
        username = validate_username(username)
        if not username:
            return None, None, None, "Username inválido"
        
        url = f"https://urlebird.com/pt/user/{username}/"
        logger.info(f"Buscando vídeo mais recente de @{username} via Selenium (anti-detecção)...")
        
        # Configurar Chrome com opções anti-detecção (simplificado - deixar undetected-chromedriver gerenciar mais)
        options = uc.ChromeOptions()
        # Apenas argumentos essenciais para Docker/VPS
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--window-size=1920,1080')
        options.add_argument('--lang=pt-BR')
        
        # User-Agent mais recente e consistente (Linux para VPS, mas funciona local também)
        options.add_argument('user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36')
        
        # NÃO adicionar --disable-blink-features=AutomationControlled
        # O undetected-chromedriver já gerencia isso internamente
        # NÃO adicionar useAutomationExtension - pode interferir com o undetected-chromedriver
        
        # Tentar encontrar Chrome automaticamente
        import shutil
        chrome_paths = [
            '/usr/bin/google-chrome',
            '/usr/bin/google-chrome-stable',
            '/usr/bin/chromium',
            '/usr/bin/chromium-browser',
            '/snap/bin/chromium',
            shutil.which('google-chrome'),
            shutil.which('google-chrome-stable'),
            shutil.which('chromium'),
            shutil.which('chromium-browser')
        ]
        
        chrome_binary = None
        for path in chrome_paths:
            if path and os.path.exists(path):
                chrome_binary = path
                options.binary_location = chrome_binary
                break
        
        # Criar driver com undetected-chromedriver
        try:
            if chrome_binary:
                driver = uc.Chrome(options=options, use_subprocess=True)
            else:
                # Tentar sem especificar binary_location - auto-detectar
                driver = uc.Chrome(options=options, use_subprocess=True)
        except Exception as e:
            logger.warning(f"Erro ao criar driver com opções: {e}, tentando método simples...")
            driver = uc.Chrome(use_subprocess=True)
        
        # Executar script para remover webdriver property
        driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
            'source': '''
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
                window.navigator.chrome = {
                    runtime: {}
                };
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5]
                });
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['pt-BR', 'pt', 'en-US', 'en']
                });
            '''
        })
        
        # Carregar cookies se disponível (para bypass Cloudflare)
        cookies_file = os.getenv('COOKIES_FILE', '/app/cookies.txt')
        if os.path.exists(cookies_file):
            try:
                logger.info("Carregando cookies para bypass Cloudflare...")
                # Primeiro acessar o domínio para poder adicionar cookies
                driver.get('https://urlebird.com/')
                import time
                time.sleep(2)
                
                # Ler cookies do arquivo (formato Netscape)
                cookies_loaded = 0
                with open(cookies_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if not line or line.startswith('#'):
                            continue
                        
                        # Formato Netscape: domain, flag, path, secure, expiration, name, value
                        parts = line.split('\t')
                        if len(parts) >= 7:
                            try:
                                cookie_domain = parts[0]
                                cookie_path = parts[2]
                                cookie_secure = parts[3] == 'TRUE'
                                cookie_name = parts[5]
                                cookie_value = parts[6]
                                
                                # Só adicionar cookies do domínio urlebird.com
                                if 'urlebird.com' in cookie_domain:
                                    driver.add_cookie({
                                        'name': cookie_name,
                                        'value': cookie_value,
                                        'domain': cookie_domain,
                                        'path': cookie_path,
                                        'secure': cookie_secure
                                    })
                                    cookies_loaded += 1
                            except Exception as e:
                                logger.debug(f"Erro ao processar cookie: {e}")
                                continue
                
                if cookies_loaded > 0:
                    logger.info(f"✓ {cookies_loaded} cookie(s) carregado(s)")
                else:
                    logger.warning("Nenhum cookie válido encontrado no arquivo")
            except Exception as e:
                logger.warning(f"Erro ao carregar cookies: {e}")
        
        # Acessar página
        logger.info(f"Acessando: {url}")
        driver.get(url)
        
        # Aguardar carregamento (com timeout)
        try:
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            import time
            time.sleep(3)  # Aguardar JavaScript carregar
        except TimeoutException:
            return None, None, None, "Timeout ao carregar página"
        
        # Aguardar elementos específicos aparecerem (links de vídeo)
        try:
            logger.info("Aguardando elementos específicos da página...")
            WebDriverWait(driver, 20).until(
                lambda d: '/video/' in d.page_source or 
                          len(d.find_elements(By.TAG_NAME, 'a')) > 10
            )
            time.sleep(2)  # Aguardar mais um pouco para garantir
        except TimeoutException:
            logger.warning("Timeout aguardando elementos específicos, continuando...")
        
        # Obter HTML da página
        html = driver.page_source
        soup = BeautifulSoup(html, 'html.parser')
        
        # Verificar se foi bloqueado
        if "403" in html or "Forbidden" in html or "blocked" in html.lower():
            return None, None, None, "Página bloqueada pelo Cloudflare (403 Forbidden)"
        
        # Extrair dados do canal
        channel_data = get_channel_data(username, soup)
        
        # Procurar primeiro link de vídeo
        latest_video_element = soup.find('a', href=lambda href: href and '/video/' in href)
        
        if latest_video_element:
            urlebird_video_url = latest_video_element.get('href', '')
            
            # Garantir URL completa
            base_url = 'https://urlebird.com'
            if urlebird_video_url.startswith('/'):
                urlebird_video_url = f"{base_url}{urlebird_video_url}"
            elif not urlebird_video_url.startswith('http'):
                urlebird_video_url = f"{base_url}/{urlebird_video_url}"
            
            # Extrair ID do vídeo
            video_id_match = re.search(r'/video/[^/]+-(\d+)', urlebird_video_url)
            if video_id_match:
                video_id = video_id_match.group(1)
                tiktok_url = f"https://www.tiktok.com/@{username}/video/{video_id}"
            else:
                parts = urlebird_video_url.rstrip('/').split('/')
                if len(parts) > 0:
                    last_part = parts[-1]
                    video_id_match = re.search(r'(\d+)', last_part)
                    if video_id_match:
                        video_id = video_id_match.group(1)
                        tiktok_url = f"https://www.tiktok.com/@{username}/video/{video_id}"
                    else:
                        tiktok_url = None
                else:
                    tiktok_url = None
            
            logger.info(f"✓ Vídeo mais recente encontrado via Selenium: {tiktok_url}")
            return tiktok_url, urlebird_video_url, channel_data, None
        else:
            return None, None, channel_data, f"Nenhum vídeo encontrado para @{username}"
            
    except Exception as e:
        error_msg = f"Erro ao usar Selenium: {str(e)}"
        logger.error(error_msg)
        return None, None, None, error_msg
    finally:
        if driver:
            try:
                driver.quit()
            except:
                pass

def get_latest_video_url_from_channel_rapidapi(username):
    """Extrai a URL do vídeo mais recente usando RapidAPI TikTok Scraper
    
    Retorna: (tiktok_url, service_video_url, channel_data, error)
    """
    try:
        username = validate_username(username)
        if not username:
            return None, None, None, "Username inválido"
        
        logger.info(f"Tentando RapidAPI TikTok Scraper para @{username}...")
        
        # RapidAPI TikTok Scraper endpoint
        api_url = "https://tiktok-scraper7.p.rapidapi.com/user/posts"
        
        params = {
            'unique_id': username,
            'count': 1  # Apenas o mais recente
        }
        
        headers = {
            'x-rapidapi-host': 'tiktok-scraper7.p.rapidapi.com',
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
            'Accept': 'application/json',
        }
        
        # Tentar com chave de API se disponível (opcional)
        rapidapi_key = os.getenv('RAPIDAPI_KEY', None)
        if rapidapi_key:
            headers['x-rapidapi-key'] = rapidapi_key
        
        response = requests.get(api_url, params=params, headers=headers, timeout=15)
        
        if response.status_code == 200:
            data = response.json()
            
            # Verificar estrutura da resposta
            if 'data' in data and 'videos' in data['data']:
                videos = data['data']['videos']
            elif 'videos' in data:
                videos = data['videos']
            elif isinstance(data, list) and len(data) > 0:
                videos = data
            else:
                videos = None
            
            if videos and len(videos) > 0:
                latest_video = videos[0]
                
                # Extrair informações do vídeo (estrutura pode variar)
                video_id = latest_video.get('video_id') or latest_video.get('id') or latest_video.get('aweme_id', '')
                if not video_id and 'url' in latest_video:
                    # Tentar extrair ID da URL
                    import re
                    url_match = re.search(r'/video/(\d+)', latest_video['url'])
                    if url_match:
                        video_id = url_match.group(1)
                
                if video_id:
                    tiktok_url = f"https://www.tiktok.com/@{username}/video/{video_id}"
                    
                    # Criar URL do serviço (usar URL do vídeo se disponível)
                    service_video_url = latest_video.get('url', tiktok_url)
                    
                    # Extrair dados do canal
                    channel_data = {
                        'username': username,
                        'followers': data.get('data', {}).get('followerCount') or data.get('followerCount', 'N/A'),
                        'total_likes': data.get('data', {}).get('heartCount') or data.get('heartCount', 'N/A'),
                        'videos_posted': data.get('data', {}).get('videoCount') or data.get('videoCount', 'N/A')
                    }
                    
                    logger.info(f"✓ Vídeo mais recente encontrado via RapidAPI: {tiktok_url}")
                    return tiktok_url, service_video_url, channel_data, None
                else:
                    return None, None, None, "Não foi possível extrair ID do vídeo da resposta"
            else:
                return None, None, None, f"Nenhum vídeo encontrado para @{username}"
        elif response.status_code == 401 or response.status_code == 403:
            error_detail = response.text[:200] if hasattr(response, 'text') else 'Sem detalhes'
            logger.warning(f"RapidAPI retornou {response.status_code}: {error_detail}")
            return None, None, None, f"Erro de autenticação (pode precisar de chave RapidAPI): HTTP {response.status_code}"
        else:
            error_detail = response.text[:200] if hasattr(response, 'text') else 'Sem detalhes'
            logger.warning(f"RapidAPI retornou {response.status_code}: {error_detail}")
            return None, None, None, f"Erro HTTP {response.status_code} ao acessar RapidAPI"
            
    except requests.exceptions.RequestException as e:
        error_msg = f"Erro ao acessar RapidAPI: {str(e)}"
        logger.warning(error_msg)
        logger.debug(f"Detalhes do erro RapidAPI: {type(e).__name__}: {str(e)}")
        return None, None, None, error_msg
    except Exception as e:
        error_msg = f"Erro ao processar resposta RapidAPI: {str(e)}"
        logger.warning(error_msg)
        logger.debug(f"Detalhes do erro RapidAPI: {type(e).__name__}: {str(e)}")
        import traceback
        logger.debug(traceback.format_exc())
        return None, None, None, error_msg

def get_latest_video_url_from_channel_apify(username):
    """Extrai a URL do vídeo mais recente usando Apify TikTok Scraper (API profissional)
    
    Apify é uma plataforma profissional que já resolve bypass de Cloudflare e anti-bot.
    Muito mais confiável que métodos manuais.
    
    Retorna: (tiktok_url, service_video_url, channel_data, error)
    """
    if not APIFY_AVAILABLE:
        return None, None, None, "Apify Client não está instalado. Execute: pip install apify-client"
    
    try:
        username = validate_username(username)
        if not username:
            return None, None, None, "Username inválido"
        
        logger.info(f"Tentando Apify TikTok Scraper para @{username}...")
        
        # Obter API token do Apify (variável de ambiente)
        apify_token = os.getenv('APIFY_API_TOKEN', None)
        if not apify_token:
            return None, None, None, "APIFY_API_TOKEN não configurado. Configure a variável de ambiente com sua chave do Apify"
        
        # Inicializar cliente Apify
        client = ApifyClient(apify_token)
        
        # Preparar input para o Actor TikTok Scraper
        run_input = {
            "profiles": [username],  # Lista de usernames
            "resultsPerPage": 1,  # Apenas o vídeo mais recente
            "profileScrapeSections": ["videos"],  # Apenas vídeos
            "profileSorting": "latest",  # Mais recente primeiro
            "excludePinnedPosts": False,  # Incluir posts fixados
            "maxFollowersPerProfile": 0,
            "maxFollowingPerProfile": 0,
            "commentsPerPost": 0,
            "maxRepliesPerComment": 0,
            "shouldDownloadVideos": False,  # Não baixar vídeos (apenas metadados)
            "shouldDownloadCovers": False,
            "shouldDownloadSubtitles": False,
            "shouldDownloadAvatars": False,
            "proxyCountryCode": "None"
        }
        
        # Executar Actor e aguardar conclusão
        logger.info("Executando Apify TikTok Scraper...")
        run = client.actor("clockworks/tiktok-scraper").call(run_input=run_input)
        
        # Buscar resultados do dataset
        dataset_id = run.get("defaultDatasetId")
        if not dataset_id:
            return None, None, None, "Dataset não foi criado pelo Apify"
        
        logger.info(f"Buscando resultados do dataset {dataset_id}...")
        
        # Iterar pelos itens do dataset
        items = list(client.dataset(dataset_id).iterate_items())
        
        if not items or len(items) == 0:
            return None, None, None, f"Nenhum vídeo encontrado para @{username}"
        
        # Pegar o primeiro item (mais recente devido ao profileSorting: "latest")
        latest_video = items[0]
        
        # Log para debug: ver o que está vindo do Apify
        logger.debug(f"Dados completos do Apify (primeiros 1000 chars): {json.dumps(latest_video, indent=2, ensure_ascii=False)[:1000]}")
        logger.info(f"Campos disponíveis no objeto do Apify: {list(latest_video.keys())[:20]}")
        
        # Extrair URL do vídeo
        web_video_url = latest_video.get("webVideoUrl") or latest_video.get("submittedVideoUrl")
        if not web_video_url:
            return None, None, None, "URL do vídeo não encontrada na resposta do Apify"
        
        # Extrair dados do canal do authorMeta
        author_meta = latest_video.get("authorMeta", {})
        channel_data = {
            'username': username,
            'followers': author_meta.get("fans", "N/A"),
            'total_likes': author_meta.get("heart", "N/A"),
            'videos_posted': author_meta.get("video", "N/A"),
            'nickname': author_meta.get("nickName", "N/A"),
            'verified': author_meta.get("verified", False),
            'signature': author_meta.get("signature", "")
        }
        
        # Extrair metadados do vídeo do Apify (baseado na documentação oficial)
        # Campos estão DIRETAMENTE no objeto latest_video, não dentro de stats
        def format_number(num):
            """Formata números grandes (ex: 1000000 -> "1M")"""
            if num is None:
                return None
            try:
                num = int(num)
                if num >= 1_000_000_000:
                    return f"{num / 1_000_000_000:.1f}B"
                elif num >= 1_000_000:
                    return f"{num / 1_000_000:.1f}M"
                elif num >= 1_000:
                    return f"{num / 1_000:.1f}K"
                return str(num)
            except:
                return str(num) if num else None
        
        # Extrair campos conforme documentação do Apify
        # text = caption/descrição do vídeo (campo direto)
        caption = latest_video.get("text") or latest_video.get("desc") or None
        
        # createTimeISO = data de postagem formatada (campo direto)
        posted_time = latest_video.get("createTimeISO") or latest_video.get("createTime") or None
        
        # Métricas estão DIRETAMENTE no objeto latest_video (não dentro de stats)
        # Conforme documentação: playCount, diggCount, commentCount, shareCount são campos diretos
        play_count = latest_video.get("playCount")
        digg_count = latest_video.get("diggCount")  # likes
        comment_count = latest_video.get("commentCount")
        share_count = latest_video.get("shareCount")
        
        # Log para debug dos valores extraídos
        logger.debug(f"Valores extraídos - caption: {caption is not None}, playCount: {play_count}, diggCount: {digg_count}, commentCount: {comment_count}, shareCount: {share_count}, createTimeISO: {posted_time}")
        
        # CDN link - pode estar em videoMeta.videoUrl ou mediaUrls
        video_meta = latest_video.get("videoMeta", {})
        media_urls = latest_video.get("mediaUrls", [])
        
        # Tentar obter URL do vídeo de várias fontes
        cdn_link = None
        if media_urls and len(media_urls) > 0:
            # Se tiver mediaUrls (quando shouldDownloadVideos=true), usar o primeiro
            cdn_link = media_urls[0] if isinstance(media_urls[0], str) else media_urls[0].get("url") if isinstance(media_urls[0], dict) else None
        else:
            # Tentar outros campos possíveis
            cdn_link = (
                latest_video.get("videoUrl") or 
                latest_video.get("downloadAddr") or 
                video_meta.get("videoUrl") or
                None
            )
        
        # Criar objeto de metadados do vídeo (formato compatível com Urlebird)
        video_details_apify = {
            'caption': caption,
            'posted_time': posted_time,
            'views': format_number(play_count),
            'likes': format_number(digg_count),
            'comments': format_number(comment_count),
            'shares': format_number(share_count),
            'cdn_link': cdn_link
        }
        
        logger.info(f"Metadados extraídos do Apify: caption={'✓' if caption else '✗'}, views={play_count}, likes={digg_count}, comments={comment_count}, shares={share_count}, cdn_link={'✓' if cdn_link else '✗'}")
        
        # Adicionar metadados do vídeo ao channel_data para retornar junto
        channel_data['_video_details_apify'] = video_details_apify
        
        logger.info(f"✓ Vídeo mais recente encontrado via Apify: {web_video_url}")
        return web_video_url, web_video_url, channel_data, None
        
    except Exception as e:
        error_msg = f"Erro ao usar Apify: {str(e)}"
        logger.error(error_msg)
        logger.warning(f"Detalhes do erro Apify: {type(e).__name__}: {str(e)}")
        import traceback
        logger.debug(traceback.format_exc())
        return None, None, None, error_msg

def get_latest_video_url_from_channel_tikwm(username):
    """Extrai a URL do vídeo mais recente usando TikWM API
    
    Retorna: (tiktok_url, urlebird_video_url, channel_data, error)
    """
    try:
        username = validate_username(username)
        if not username:
            return None, None, None, "Username inválido"
        
        logger.info(f"Tentando TikWM API para @{username}...")
        
        # TikWM API endpoint para listar vídeos de um usuário
        api_url = f"https://www.tikwm.com/api/user/posts"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
            'Accept': 'application/json',
            'Content-Type': 'application/json',
        }
        
        payload = {
            'unique_id': username,
            'count': 1  # Apenas o mais recente
        }
        
        response = requests.post(api_url, json=payload, headers=headers, timeout=15)
        
        if response.status_code == 200:
            data = response.json()
            
            if data.get('code') == 0 and 'data' in data and 'videos' in data['data']:
                videos = data['data']['videos']
                if videos and len(videos) > 0:
                    latest_video = videos[0]
                    
                    # Extrair informações do vídeo
                    video_id = latest_video.get('video_id', '')
                    tiktok_url = f"https://www.tiktok.com/@{username}/video/{video_id}"
                    
                    # Criar URL do TikWM para o vídeo (similar ao Urlebird)
                    tikwm_video_url = f"https://www.tikwm.com/video/{video_id}"
                    
                    # Extrair dados do canal
                    channel_data = {
                        'username': username,
                        'followers': data['data'].get('followerCount', 'N/A'),
                        'total_likes': data['data'].get('heartCount', 'N/A'),
                        'videos_posted': data['data'].get('videoCount', 'N/A')
                    }
                    
                    logger.info(f"✓ Vídeo mais recente encontrado via TikWM: {tiktok_url}")
                    return tiktok_url, tikwm_video_url, channel_data, None
                else:
                    return None, None, None, f"Nenhum vídeo encontrado para @{username}"
            else:
                error_msg = data.get('msg', 'Erro desconhecido da API TikWM')
                logger.warning(f"TikWM retornou erro: {error_msg} (código: {data.get('code', 'N/A')})")
                return None, None, None, f"Erro TikWM: {error_msg}"
        else:
            error_detail = response.text[:200] if hasattr(response, 'text') else 'Sem detalhes'
            logger.warning(f"TikWM retornou HTTP {response.status_code}: {error_detail}")
            return None, None, None, f"Erro HTTP {response.status_code} ao acessar TikWM"
            
    except requests.exceptions.RequestException as e:
        error_msg = f"Erro ao acessar TikWM: {str(e)}"
        logger.warning(error_msg)
        logger.debug(f"Detalhes do erro TikWM: {type(e).__name__}: {str(e)}")
        return None, None, None, error_msg
    except Exception as e:
        error_msg = f"Erro ao processar resposta TikWM: {str(e)}"
        logger.warning(error_msg)
        logger.debug(f"Detalhes do erro TikWM: {type(e).__name__}: {str(e)}")
        import traceback
        logger.debug(traceback.format_exc())
        return None, None, None, error_msg

def get_latest_video_url_from_channel_browseruse(username):
    """Extrai a URL do vídeo mais recente usando Browser Use (Agent-based)
    
    Browser Use usa Agent com LLM para navegação inteligente e bypass automático de Cloudflare
    
    Retorna: (tiktok_url, urlebird_video_url, channel_data, error)
    """
    if not BROWSER_USE_AVAILABLE:
        return None, None, None, "Browser Use não está instalado. Execute: pip install browser-use"
    
    if not BEAUTIFULSOUP_AVAILABLE:
        return None, None, None, "BeautifulSoup4 não está instalado"
    
    try:
        username = validate_username(username)
        if not username:
            return None, None, None, "Username inválido"
        
        logger.info(f"Tentando Browser Use para @{username}...")
        
        url = f"https://urlebird.com/pt/user/{username}/"
        
        # Função assíncrona interna para usar Browser Use
        async def run_browser_use_agent():
            try:
                # Criar Browser instance (pode usar use_cloud=True para stealth mode se tiver API key)
                browser_use_api_key = os.getenv('BROWSER_USE_API_KEY', None)
                use_cloud = browser_use_api_key is not None
                
                browser = Browser(
                    use_cloud=use_cloud,
                    headless=True  # Modo headless para produção
                )
                
                # Criar LLM (ChatBrowserUse requer API key, senão usar outro LLM ou modo local)
                if browser_use_api_key:
                    llm = ChatBrowserUse()
                    
                    # Criar Agent com task específica
                    task = f"Navigate to {url}, wait for Cloudflare challenges to resolve, and extract the HTML content. Find the first video link on the page."
                    
                    agent = Agent(
                        task=task,
                        llm=llm,
                        browser=browser,
                    )
                    
                    history = await agent.run()
                    
                    # Tentar obter HTML do browser
                    if hasattr(browser, 'page'):
                        html = await browser.page.content()
                    else:
                        html = str(history) if history else None
                    
                    await browser.close()
                    return html
                else:
                    # Modo local - usar Playwright diretamente sem Agent
                    from playwright.async_api import async_playwright
                    playwright = await async_playwright().start()
                    browser_instance = await playwright.chromium.launch(headless=True)
                    page = await browser_instance.new_page()
                    
                    # Navegar até a URL
                    await page.goto(url, wait_until='networkidle', timeout=60000)
                    
                    # Aguardar resolução de desafios Cloudflare
                    import time as time_module
                    max_wait = 60
                    start_time = time_module.time()
                    
                    while time_module.time() - start_time < max_wait:
                        content = await page.content()
                        if '/video/' in content or 'follower' in content.lower():
                            break
                        await page.wait_for_timeout(2000)
                    
                    # Obter HTML
                    html = await page.content()
                    await browser_instance.close()
                    await playwright.stop()
                    
                    return html
                
            except Exception as e:
                logger.error(f"Erro no Browser Use Agent: {e}")
                import traceback
                logger.debug(traceback.format_exc())
                return None
        
        # Executar função assíncrona
        html = asyncio.run(run_browser_use_agent())
        
        if not html:
            return None, None, None, "Não foi possível obter HTML da página"
        
        # Parsear HTML com BeautifulSoup
        soup = BeautifulSoup(html, 'html.parser')
        
        # Verificar se foi bloqueado
        if "403" in html or "Forbidden" in html or "blocked" in html.lower():
            return None, None, None, "Página bloqueada pelo Cloudflare (403 Forbidden)"
        
        # Extrair dados do canal
        channel_data = get_channel_data(username, soup)
        
        # Procurar primeiro link de vídeo
        latest_video_element = soup.find('a', href=lambda href: href and '/video/' in href)
        
        if latest_video_element:
            urlebird_video_url = latest_video_element.get('href', '')
            
            # Garantir URL completa
            base_url = 'https://urlebird.com'
            if urlebird_video_url.startswith('/'):
                urlebird_video_url = f"{base_url}{urlebird_video_url}"
            elif not urlebird_video_url.startswith('http'):
                urlebird_video_url = f"{base_url}/{urlebird_video_url}"
            
            # Extrair ID do vídeo
            video_id_match = re.search(r'/video/[^/]+-(\d+)', urlebird_video_url)
            if video_id_match:
                video_id = video_id_match.group(1)
                tiktok_url = f"https://www.tiktok.com/@{username}/video/{video_id}"
            else:
                parts = urlebird_video_url.rstrip('/').split('/')
                if len(parts) > 0:
                    last_part = parts[-1]
                    video_id_match = re.search(r'(\d+)', last_part)
                    if video_id_match:
                        video_id = video_id_match.group(1)
                        tiktok_url = f"https://www.tiktok.com/@{username}/video/{video_id}"
                    else:
                        tiktok_url = None
                else:
                    tiktok_url = None
            
            logger.info(f"✓ Vídeo mais recente encontrado via Browser Use: {tiktok_url}")
            return tiktok_url, urlebird_video_url, channel_data, None
        else:
            return None, None, channel_data, f"Nenhum vídeo encontrado para @{username}"
            
    except Exception as e:
        error_msg = f"Erro ao usar Browser Use: {str(e)}"
        logger.error(error_msg)
        import traceback
        logger.debug(traceback.format_exc())
        return None, None, None, error_msg

def get_latest_video_url_from_channel_seleniumbase(username):
    """Extrai a URL do vídeo mais recente usando SeleniumBase com Undetected ChromeDriver
    
    Método avançado conforme guia Cloudflare: Method #5 - Implement Fortified Headless Browsers
    Usa SeleniumBase com UC (Undetected ChromeDriver) para bypass eficaz do Cloudflare.
    
    Retorna: (tiktok_url, urlebird_video_url, channel_data, error)
    """
    if not SELENIUMBASE_AVAILABLE:
        return None, None, None, "SeleniumBase não está instalado. Execute: pip install seleniumbase"
    
    if not BEAUTIFULSOUP_AVAILABLE:
        return None, None, None, "BeautifulSoup4 não está instalado"
    
    driver = None
    try:
        username = validate_username(username)
        if not username:
            return None, None, None, "Username inválido"
        
        url = f"https://urlebird.com/pt/user/{username}/"
        logger.info(f"Buscando vídeo mais recente de @{username} via SeleniumBase (UC)...")
        
        # SeleniumBase com UC (Undetected ChromeDriver) - método recomendado pelo guia
        driver = Driver(uc=True, headless=True)
        
        # Usar uc_open_with_reconnect para melhor handling de desafios Cloudflare
        driver.uc_open_with_reconnect(url, reconnect_time=4)
        
        # Aguardar resolução de desafios Cloudflare
        import time
        max_wait = 60
        start_time = time.time()
        challenge_resolved = False
        
        while time.time() - start_time < max_wait:
            try:
                page_source_lower = driver.page_source.lower()
                page_title = driver.title.lower()
                
                # Verificar se ainda está em página de desafio
                if ('challenge' in page_source_lower or 
                    'checking your browser' in page_source_lower or 
                    'just a moment' in page_source_lower or
                    'um momento' in page_title or
                    'please wait' in page_title):
                    elapsed = int(time.time() - start_time)
                    logger.debug(f"Desafio Cloudflare detectado, aguardando resolução... ({elapsed}s/{max_wait}s)")
                    time.sleep(2)
                    continue
                
                # Verificar se conteúdo real carregou
                if '/video/' in driver.page_source or 'follower' in page_source_lower:
                    elapsed = int(time.time() - start_time)
                    logger.info(f"✓ Página carregada e desafio resolvido! ({elapsed}s)")
                    challenge_resolved = True
                    break
                    
                time.sleep(1)
            except Exception as e:
                logger.debug(f"Erro durante espera: {e}")
                time.sleep(1)
                continue
        
        if not challenge_resolved:
            elapsed = int(time.time() - start_time)
            logger.warning(f"Timeout aguardando resolução após {elapsed}s, continuando mesmo assim...")
        
        # Tentar resolver CAPTCHA Turnstile se presente
        try:
            driver.uc_gui_click_captcha()
            time.sleep(5)
        except Exception:
            pass  # CAPTCHA não encontrado ou já resolvido
        
        # Aguardar mais um pouco para garantir carregamento completo
        time.sleep(3)
        
        # Verificar se foi bloqueado
        page_source = driver.page_source
        if "403" in page_source or "Forbidden" in page_source or "blocked" in page_source.lower():
            return None, None, None, "Página bloqueada pelo Cloudflare (403 Forbidden)"
        
        # Obter HTML da página
        html = driver.page_source
        soup = BeautifulSoup(html, 'html.parser')
        
        # Extrair dados do canal
        channel_data = get_channel_data(username, soup)
        
        # Procurar primeiro link de vídeo
        latest_video_element = soup.find('a', href=lambda href: href and '/video/' in href)
        
        if latest_video_element:
            urlebird_video_url = latest_video_element.get('href', '')
            
            # Garantir URL completa
            base_url = 'https://urlebird.com'
            if urlebird_video_url.startswith('/'):
                urlebird_video_url = f"{base_url}{urlebird_video_url}"
            elif not urlebird_video_url.startswith('http'):
                urlebird_video_url = f"{base_url}/{urlebird_video_url}"
            
            # Extrair ID do vídeo
            video_id_match = re.search(r'/video/[^/]+-(\d+)', urlebird_video_url)
            if video_id_match:
                video_id = video_id_match.group(1)
                tiktok_url = f"https://www.tiktok.com/@{username}/video/{video_id}"
            else:
                # Tentar extrair de outra forma
                parts = urlebird_video_url.rstrip('/').split('/')
                if len(parts) > 0:
                    last_part = parts[-1]
                    video_id_match = re.search(r'(\d+)', last_part)
                    if video_id_match:
                        video_id = video_id_match.group(1)
                        tiktok_url = f"https://www.tiktok.com/@{username}/video/{video_id}"
                    else:
                        tiktok_url = None
                else:
                    tiktok_url = None
            
            logger.info(f"✓ Vídeo mais recente encontrado via SeleniumBase: {tiktok_url}")
            return tiktok_url, urlebird_video_url, channel_data, None
        else:
            return None, None, channel_data, f"Nenhum vídeo encontrado para @{username}"
            
    except Exception as e:
        error_msg = f"Erro ao usar SeleniumBase: {str(e)}"
        logger.error(error_msg)
        import traceback
        logger.debug(traceback.format_exc())
        return None, None, None, error_msg
    finally:
        if driver:
            try:
                driver.quit()
            except:
                pass

def get_latest_video_url_from_channel_countik(username):
    """Extrai a URL do vídeo mais recente usando Countik (scraping)
    
    Retorna: (tiktok_url, countik_video_url, channel_data, error)
    """
    if not BEAUTIFULSOUP_AVAILABLE:
        return None, None, None, "BeautifulSoup4 não está instalado"
    
    try:
        username = validate_username(username)
        if not username:
            return None, None, None, "Username inválido"
        
        logger.info(f"Tentando Countik para @{username}...")
        
        url = f"https://countik.com/user/{username}"
        
        session = requests.Session()
        headers = {
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
            'Referer': 'https://www.google.com/',
            'Origin': 'https://www.google.com',
        }
        session.headers.update(headers)
        
        # Acessar página inicial primeiro para obter cookies
        session.get('https://countik.com/', timeout=10)
        time.sleep(1)
        
        # Acessar perfil do usuário
        response = session.get(url, timeout=15)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Procurar primeiro link de vídeo
            latest_video_element = soup.find('a', href=lambda href: href and '/video/' in href)
            
            if latest_video_element:
                countik_video_url = latest_video_element.get('href', '')
                
                # Garantir URL completa
                if countik_video_url.startswith('/'):
                    countik_video_url = f"https://countik.com{countik_video_url}"
                elif not countik_video_url.startswith('http'):
                    countik_video_url = f"https://countik.com/{countik_video_url}"
                
                # Extrair ID do vídeo
                video_id_match = re.search(r'/video/[^/]+-(\d+)', countik_video_url)
                if video_id_match:
                    video_id = video_id_match.group(1)
                    tiktok_url = f"https://www.tiktok.com/@{username}/video/{video_id}"
                else:
                    # Tentar extrair de outra forma
                    parts = countik_video_url.rstrip('/').split('/')
                    if len(parts) > 0:
                        last_part = parts[-1]
                        video_id_match = re.search(r'(\d+)', last_part)
                        if video_id_match:
                            video_id = video_id_match.group(1)
                            tiktok_url = f"https://www.tiktok.com/@{username}/video/{video_id}"
                        else:
                            tiktok_url = None
                    else:
                        tiktok_url = None
                
                # Extrair dados do canal (se disponível)
                channel_data = get_channel_data(username, soup)
                
                logger.info(f"✓ Vídeo mais recente encontrado via Countik: {tiktok_url}")
                return tiktok_url, countik_video_url, channel_data, None
            else:
                return None, None, None, f"Nenhum vídeo encontrado para @{username}"
        else:
            return None, None, None, f"Erro HTTP {response.status_code} ao acessar Countik"
            
    except requests.exceptions.RequestException as e:
        error_msg = f"Erro ao acessar Countik: {str(e)}"
        logger.warning(error_msg)
        return None, None, None, error_msg
    except Exception as e:
        error_msg = f"Erro ao processar Countik: {str(e)}"
        logger.warning(error_msg)
        return None, None, None, error_msg

def get_latest_video_url_from_channel_playwright(username):
    """Extrai a URL do vídeo mais recente usando Playwright + Stealth (método do Manus)
    
    Este método usa Playwright com playwright-stealth para bypass eficaz do Cloudflare.
    Baseado no código oficial do Manus que conseguiu acessar o Urlebird com sucesso.
    
    Retorna: (tiktok_url, urlebird_video_url, channel_data, error)
    """
    if not PLAYWRIGHT_AVAILABLE or not PLAYWRIGHT_STEALTH_AVAILABLE:
        return None, None, None, "Playwright ou playwright-stealth não está instalado. Execute: pip install playwright playwright-stealth && playwright install chromium"
    
    if not BEAUTIFULSOUP_AVAILABLE:
        return None, None, None, "BeautifulSoup4 não está instalado"
    
    try:
        username = validate_username(username)
        if not username:
            return None, None, None, "Username inválido"
        
        logger.info(f"Tentando Playwright + Stealth para @{username}...")
        
        url = f"https://urlebird.com/pt/user/{username}/"
        
        # Função assíncrona interna usando Playwright + Stealth
        async def run_playwright_stealth():
            try:
                async with async_playwright() as p:
                    # Lançar navegador Chromium com modo headless=new (muito mais difícil de detectar)
                    # O modo headless=new se comporta exatamente como navegador com tela
                    browser = await p.chromium.launch(
                        headless=True,  # Playwright usa headless=new automaticamente quando headless=True
                        args=[
                            '--disable-blink-features=AutomationControlled',
                            '--disable-dev-shm-usage',
                            '--no-sandbox',
                            '--disable-setuid-sandbox',
                            '--use-gl=egl',  # Emular GPU para WebGL (Manus: "emulo uma GPU real")
                            '--enable-webgl',
                            '--enable-accelerated-2d-canvas'
                        ]
                    )
                    
                    # Criar contexto com configurações realistas e persistent storage
                    # Persistent context ajuda a manter cookies entre sessões
                    context_storage_path = os.path.join(os.getcwd(), '.playwright_context')
                    os.makedirs(context_storage_path, exist_ok=True)
                    
                    # Tentar carregar cookies salvos de sessão anterior (incluindo cf_clearance)
                    # Manus: "Use context.storage_state(path='state.json') para salvar cookies"
                    storage_file = os.path.join(context_storage_path, 'urlebird_storage.json')
                    storage_state = None
                    if os.path.exists(storage_file):
                        try:
                            with open(storage_file, 'r') as f:
                                storage_state = json.load(f)
                            logger.info("Cookies anteriores carregados (incluindo cf_clearance se disponível)")
                        except Exception as e:
                            logger.debug(f"Erro ao carregar cookies: {e}")
                    else:
                        logger.info("Nenhum cookie salvo encontrado. Execute setup_session.py para criar sessão inicial")
                    
                    # User-Agent sincronizado com SO (Manus: "Case o User-Agent com o SO da sua VPS")
                    # Como é VPS Linux, usar User-Agent de Linux para evitar inconsistência TCP/IP Fingerprint
                    user_agents = [
                        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",  # Exato do Manus
                        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
                        "Mozilla/5.0 (X11; Ubuntu; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
                    ]
                    selected_ua = random.choice(user_agents)
                    
                    context = await browser.new_context(
                        user_agent=selected_ua,
                        viewport={'width': 1920, 'height': 1080},  # Resolução comum
                        locale="pt-BR",
                        timezone_id="America/Sao_Paulo",
                        permissions=["geolocation"],
                        geolocation={"latitude": -23.5505, "longitude": -46.6333},  # São Paulo
                        color_scheme="light",
                        # Persistent storage para cookies (carregar se existir)
                        # Manus: "Carregue esse arquivo: browser.new_context(storage_state='state.json')"
                        storage_state=storage_state,
                        # Configurações extras para parecer mais real
                        device_scale_factor=1,
                        has_touch=False,
                        is_mobile=False,
                        java_script_enabled=True,
                        # Manus: "garanta que o webgl não esteja desativado"
                        ignore_https_errors=False
                    )
                    
                    page = await context.new_page()
                    
                    # APLICAR STEALTH (o segredo do bypass do Cloudflare)
                    stealth = Stealth()
                    await stealth.apply_stealth_async(page)
                    
                    # Remover propriedades de automação adicionais
                    # Manus: "navigator.webdriver = false" e "Consistência de Idioma"
                    await page.add_init_script("""
                        Object.defineProperty(navigator, 'webdriver', {
                            get: () => undefined
                        });
                        Object.defineProperty(navigator, 'plugins', {
                            get: () => [1, 2, 3, 4, 5]
                        });
                        // Manus: "Consistência de Idioma: languages: ['en-US', 'en']"
                        Object.defineProperty(navigator, 'languages', {
                            get: () => ['pt-BR', 'pt', 'en-US', 'en']
                        });
                        window.navigator.chrome = {
                            runtime: {}
                        };
                        // Remover assinaturas de automação adicionais
                        delete window.cdc_adoQpoasnfa76pfcZLmcfl_Array;
                        delete window.cdc_adoQpoasnfa76pfcZLmcfl_Promise;
                        delete window.cdc_adoQpoasnfa76pfcZLmcfl_Symbol;
                    """)
                    
                    logger.info(f"Acessando {url}...")
                    
                    # Manus: "Resolução de Desafios JS: deixe o navegador processar o JavaScript por 2 a 5 segundos"
                    # Navegar até a URL com wait_until networkidle (como no exemplo do Manus)
                    await page.goto(url, wait_until="networkidle", timeout=60000)
                    
                    # Manus: "O Cloudflare Turnstile geralmente precisa de 3 a 7 segundos para validar"
                    # Aguardar processamento do Cloudflare
                    logger.info("Aguardando Cloudflare processar desafio (5 segundos)...")
                    await asyncio.sleep(5)
                    
                    # Aguardar resolução do desafio Cloudflare
                    logger.info("Aguardando resolução de desafios Cloudflare...")
                    max_wait = 60  # Máximo de 60 segundos
                    start_time = asyncio.get_event_loop().time()
                    
                    while True:
                        await asyncio.sleep(2)  # Verificar a cada 2 segundos
                        page_title = await page.title()
                        html = await page.content()
                        elapsed = asyncio.get_event_loop().time() - start_time
                        
                        # Simular interações humanas periódicas (movimentos de mouse curvos - Bezier)
                        if elapsed > 5 and elapsed % 8 < 2:  # A cada ~8 segundos
                            try:
                                # Movimento de mouse em curva (Bezier) - mais natural
                                for i in range(3):
                                    x = random.randint(100, 800)
                                    y = random.randint(100, 600)
                                    await page.mouse.move(x, y, steps=random.randint(10, 20))
                                    await asyncio.sleep(random.uniform(0.1, 0.3))
                                
                                # Scroll suave ocasional
                                scroll_amount = random.randint(100, 500)
                                await page.evaluate(f"window.scrollBy({{top: {scroll_amount}, behavior: 'smooth'}})")
                                await asyncio.sleep(random.uniform(0.5, 1))
                            except Exception as e:
                                logger.debug(f"Erro ao simular interação: {e}")
                        
                        # Verificar se o desafio foi resolvido
                        if ("um momento" not in page_title.lower() and 
                            "checking" not in page_title.lower() and
                            "challenge" not in html.lower() and
                            ("/video/" in html or "follower" in html.lower() or username.lower() in html.lower())):
                            logger.info(f"Desafio Cloudflare resolvido após {elapsed:.1f}s")
                            
                            # Salvar cookies para próxima vez (persistent context)
                            try:
                                storage_state = await context.storage_state()
                                storage_file = os.path.join(context_storage_path, 'urlebird_storage.json')
                                import json
                                with open(storage_file, 'w') as f:
                                    json.dump(storage_state, f)
                                logger.info("Cookies salvos para próxima sessão")
                            except Exception as e:
                                logger.debug(f"Erro ao salvar cookies: {e}")
                            
                            break
                        
                        # Verificar se foi bloqueado
                        if "403" in html or "Forbidden" in html or "blocked" in html.lower():
                            logger.warning("Página bloqueada (403 Forbidden)")
                            break
                        
                        # Timeout
                        if elapsed >= max_wait:
                            logger.warning(f"Timeout após {max_wait}s aguardando resolução do Cloudflare")
                            break
                        
                        if elapsed % 10 < 2:  # Log a cada 10 segundos para não poluir
                            logger.info(f"Aguardando... ({elapsed:.1f}s/{max_wait}s) - Título: {page_title[:50]}")
                    
                    # Obter HTML final da página
                    html = await page.content()
                    
                    await browser.close()
                    return html
                    
            except Exception as e:
                logger.error(f"Erro no Playwright: {e}")
                import traceback
                logger.debug(traceback.format_exc())
                return None
        
        # Executar função assíncrona
        html = asyncio.run(run_playwright_stealth())
        
        if not html:
            return None, None, None, "Não foi possível obter HTML da página"
        
        # Parsear HTML com BeautifulSoup
        soup = BeautifulSoup(html, 'html.parser')
        
        # Verificar se foi bloqueado
        if "403" in html or "Forbidden" in html or "blocked" in html.lower():
            return None, None, None, "Página bloqueada pelo Cloudflare (403 Forbidden)"
        
        # Extrair dados do canal
        channel_data = get_channel_data(username, soup)
        
        # Procurar primeiro link de vídeo
        latest_video_element = soup.find('a', href=lambda href: href and '/video/' in href)
        
        if latest_video_element:
            urlebird_video_url = latest_video_element.get('href', '')
            
            # Garantir URL completa
            base_url = 'https://urlebird.com'
            if urlebird_video_url.startswith('/'):
                urlebird_video_url = f"{base_url}{urlebird_video_url}"
            elif not urlebird_video_url.startswith('http'):
                urlebird_video_url = f"{base_url}/{urlebird_video_url}"
            
            # Extrair ID do vídeo
            video_id_match = re.search(r'/video/[^/]+-(\d+)', urlebird_video_url)
            if video_id_match:
                video_id = video_id_match.group(1)
                tiktok_url = f"https://www.tiktok.com/@{username}/video/{video_id}"
            else:
                parts = urlebird_video_url.rstrip('/').split('/')
                if len(parts) > 0:
                    last_part = parts[-1]
                    video_id_match = re.search(r'(\d+)', last_part)
                    if video_id_match:
                        video_id = video_id_match.group(1)
                        tiktok_url = f"https://www.tiktok.com/@{username}/video/{video_id}"
                    else:
                        tiktok_url = None
                else:
                    tiktok_url = None
            
            logger.info(f"✓ Vídeo mais recente encontrado via Playwright + Stealth: {tiktok_url}")
            return tiktok_url, urlebird_video_url, channel_data, None
        else:
            return None, None, channel_data, f"Nenhum vídeo encontrado para @{username}"
            
    except Exception as e:
        error_msg = f"Erro ao usar Playwright + Stealth: {str(e)}"
        logger.error(error_msg)
        import traceback
        logger.debug(traceback.format_exc())
        return None, None, None, error_msg

def get_latest_video_url_from_channel(username):
    """Extrai a URL do vídeo mais recente e dados do canal usando Apify
    
    Usa apenas Apify TikTok Scraper (API profissional, resolve Cloudflare automaticamente)
    
    Retorna: (tiktok_url, service_video_url, channel_data, error)
    """
    logger.info(f"Tentando obter último vídeo de @{username} usando Apify...")
    
    # Usar apenas Apify
    if not APIFY_AVAILABLE:
        return None, None, None, "Apify Client não está instalado. Execute: pip install apify-client"
    
    apify_token = os.getenv('APIFY_API_TOKEN', None)
    if not apify_token:
        return None, None, None, "APIFY_API_TOKEN não configurado. Configure a variável de ambiente com sua chave do Apify"
    
    logger.info("Tentando método Apify TikTok Scraper (API profissional)...")
    result = get_latest_video_url_from_channel_apify(username)
    if result[0] is not None:  # Se obteve sucesso
        logger.info("✓ Sucesso com Apify TikTok Scraper")
        return result
    
    logger.warning("Apify falhou.")
    return None, None, None, "Apify falhou. Não foi possível obter o último vídeo do canal."

def get_video_details_from_urlebird(urlebird_video_url):
    """Extrai metadados, métricas e link de download (CDN) do vídeo no Urlebird
    
    Retorna: (video_details, error)
    video_details contém:
    - caption: Legenda do vídeo
    - posted_time: Data/hora da postagem
    - views: Visualizações
    - likes: Curtidas
    - comments: Comentários
    - shares: Compartilhamentos
    - cdn_link: Link direto para download
    """
    if not BEAUTIFULSOUP_AVAILABLE:
        return None, "BeautifulSoup4 não está instalado"
    
    try:
        # Headers mais realistas para evitar bloqueio - simular navegador real
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'same-origin',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0',
            'Referer': urlebird_video_url.rsplit('/', 2)[0] + '/' if '/' in urlebird_video_url else 'https://urlebird.com/'
        }
        
        # Criar sessão para manter cookies
        session = requests.Session()
        
        # Adicionar cookies carregados do arquivo (se disponíveis)
        if URLEBIRD_COOKIES:
            logger.info("Aplicando cookies carregados à sessão requests...")
            for cookie_name, cookie_value in URLEBIRD_COOKIES.items():
                session.cookies.set(cookie_name, cookie_value, domain='.urlebird.com')
        
        session.headers.update(headers)
        
        # Tentar obter cookies primeiro
        try:
            base_url = urlebird_video_url.rsplit('/', 3)[0] if '/' in urlebird_video_url else 'https://urlebird.com'
            session.get(base_url + '/', timeout=10)
            import time
            time.sleep(0.5)
        except:
            pass
        
        response = session.get(urlebird_video_url, timeout=15, allow_redirects=True)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        video_details = {
            'caption': None,
            'posted_time': None,
            'views': None,
            'likes': None,
            'comments': None,
            'shares': None,
            'cdn_link': None
        }
        
        # 1. Extrair legenda (caption) - geralmente em h1
        h1_tag = soup.find('h1')
        if h1_tag:
            video_details['caption'] = h1_tag.get_text(strip=True)
        
        # 2. Extrair data/hora da postagem - geralmente em h6
        h6_tag = soup.find('h6')
        if h6_tag:
            video_details['posted_time'] = h6_tag.get_text(strip=True)
        
        # 3. Extrair métricas - podem estar em diferentes estruturas
        # Tentar encontrar div com classe stats ou similar
        stats_div = soup.find('div', class_=lambda x: x and 'stat' in x.lower())
        if not stats_div:
            # Tentar encontrar spans com classes específicas
            stats_spans = soup.find_all('span', class_=lambda x: x and ('view' in x.lower() or 'like' in x.lower() or 'comment' in x.lower() or 'share' in x.lower()))
            if stats_spans:
                for span in stats_spans:
                    text = span.get_text(strip=True)
                    class_name = span.get('class', [])
                    class_str = ' '.join(class_name).lower()
                    
                    if 'view' in class_str or 'view' in text.lower():
                        video_details['views'] = text
                    elif 'like' in class_str or 'like' in text.lower():
                        video_details['likes'] = text
                    elif 'comment' in class_str or 'comment' in text.lower():
                        video_details['comments'] = text
                    elif 'share' in class_str or 'share' in text.lower():
                        video_details['shares'] = text
        else:
            # Se encontrou div stats, extrair todos os spans dentro
            stats = [s.get_text(strip=True) for s in stats_div.find_all('span')]
            if len(stats) > 0:
                video_details['views'] = stats[0]
            if len(stats) > 1:
                video_details['likes'] = stats[1]
            if len(stats) > 2:
                video_details['comments'] = stats[2]
            if len(stats) > 3:
                video_details['shares'] = stats[3]
        
        # Tentar encontrar métricas em outros formatos (texto direto)
        page_text = soup.get_text()
        
        # Buscar padrões como "1.2M views", "50K likes", etc.
        if not video_details['views']:
            views_match = re.search(r'([\d.]+[KMB]?)\s*(?:views?|visualizações)', page_text, re.IGNORECASE)
            if views_match:
                video_details['views'] = views_match.group(1)
        
        if not video_details['likes']:
            likes_match = re.search(r'([\d.]+[KMB]?)\s*(?:likes?|curtidas)', page_text, re.IGNORECASE)
            if likes_match:
                video_details['likes'] = likes_match.group(1)
        
        if not video_details['comments']:
            comments_match = re.search(r'([\d.]+[KMB]?)\s*(?:comments?|comentários)', page_text, re.IGNORECASE)
            if comments_match:
                video_details['comments'] = comments_match.group(1)
        
        if not video_details['shares']:
            shares_match = re.search(r'([\d.]+[KMB]?)\s*(?:shares?|compartilhamentos)', page_text, re.IGNORECASE)
            if shares_match:
                video_details['shares'] = shares_match.group(1)
        
        # 4. Extrair link de download (CDN) - tag <video>
        video_tag = soup.find('video')
        
        if video_tag:
            # Tentar src primeiro
            cdn_link = video_tag.get('src')
            if not cdn_link:
                # Tentar source dentro de video
                source_tag = video_tag.find('source')
                if source_tag:
                    cdn_link = source_tag.get('src')
            
            if cdn_link:
                # Garantir URL completa
                if cdn_link.startswith('//'):
                    cdn_link = f"https:{cdn_link}"
                elif cdn_link.startswith('/'):
                    cdn_link = f"https://urlebird.com{cdn_link}"
                
                video_details['cdn_link'] = cdn_link
                logger.info(f"✓ Link CDN encontrado via Urlebird")
        
        return video_details, None
        
    except requests.exceptions.RequestException as e:
        error_msg = f"Erro ao acessar página do vídeo no Urlebird: {str(e)}"
        logger.warning(error_msg)
        return None, error_msg
    except Exception as e:
        error_msg = f"Erro ao processar página do vídeo: {str(e)}"
        logger.warning(error_msg)
        return None, error_msg

def get_download_link_from_urlebird(urlebird_video_url):
    """Extrai apenas o link direto de download (CDN) do vídeo no Urlebird (função legada)"""
    video_details, error = get_video_details_from_urlebird(urlebird_video_url)
    if error:
        return None, error
    return video_details.get('cdn_link'), None

def download_video_from_cdn(cdn_link, output_path):
    """Baixa vídeo diretamente do CDN usando requests"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Referer': 'https://urlebird.com/'
        }
        
        logger.info(f"Baixando vídeo do CDN...")
        response = requests.get(cdn_link, headers=headers, timeout=30, stream=True)
        response.raise_for_status()
        
        # Salvar arquivo
        with open(output_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        
        if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            logger.info(f"✓ Vídeo baixado do CDN com sucesso: {output_path}")
            return True, None
        else:
            return False, "Arquivo baixado está vazio"
            
    except Exception as e:
        error_msg = f"Erro ao baixar vídeo do CDN: {str(e)}"
        logger.warning(error_msg)
        return False, error_msg

def download_video_via_urlebird(url_or_username):
    """Baixa vídeo usando método Urlebird (último método na lista)
    
    Aceita tanto URL do TikTok quanto username do canal.
    Se for username, baixa o vídeo mais recente do canal.
    """
    if not BEAUTIFULSOUP_AVAILABLE:
        return None, "BeautifulSoup4 não está instalado. Execute: pip install beautifulsoup4"
    
    try:
        urlebird_video_url = None
        username = None
        
        # Verificar se é URL ou username
        if validate_tiktok_url(url_or_username):
            # É uma URL do TikTok
            tiktok_url = url_or_username
            # Extrair username da URL
            username_match = re.search(r'@([\w.]+)', tiktok_url)
            if username_match:
                username = username_match.group(1)
            else:
                return None, "Não foi possível extrair username da URL"
            
            # Buscar vídeo mais recente do canal no Urlebird
            _, urlebird_video_url, _, error = get_latest_video_url_from_channel(username)
            if error:
                return None, error
            if not urlebird_video_url:
                return None, f"Não foi possível encontrar vídeo para @{username}"
        else:
            # É um username, buscar vídeo mais recente
            username = validate_username(url_or_username)
            if not username:
                return None, "Username inválido"
            
            _, urlebird_video_url, _, error = get_latest_video_url_from_channel(username)
            if error:
                return None, error
            if not urlebird_video_url:
                return None, f"Não foi possível encontrar vídeo para @{username}"
        
        # Obter link de download direto do CDN
        cdn_link, error = get_download_link_from_urlebird(urlebird_video_url)
        if error or not cdn_link:
            return None, f"Não foi possível obter link de download: {error}"
        
        # Criar nome de arquivo temporário único
        temp_filename = f"tiktok_{uuid.uuid4().hex[:8]}.mp4"
        temp_path = os.path.join(DOWNLOAD_DIR, temp_filename)
        
        # Baixar vídeo do CDN
        success, error = download_video_from_cdn(cdn_link, temp_path)
        if not success:
            return None, error
        
        return temp_path, None
        
    except Exception as e:
        error_msg = f"Erro no método Urlebird: {str(e)}"
        logger.warning(error_msg)
        return None, error_msg

def load_optimized_services_order():
    """Carrega ordem otimizada dos serviços baseada em testes anteriores"""
    services_order_file = os.path.join(os.path.dirname(__file__), 'services_order.json')
    
    if os.path.exists(services_order_file):
        try:
            with open(services_order_file, 'r') as f:
                data = json.load(f)
                working_services = data.get('working_services', [])
                logger.info(f"Ordem otimizada carregada: {', '.join(working_services)}")
                return working_services
        except Exception as e:
            logger.debug(f"Erro ao carregar ordem otimizada: {e}")
    
    return []

def get_services_list():
    """Retorna lista de serviços ordenada por confiabilidade (baseada em testes)
    
    Serviços que funcionam: Snaptik, TTDownloader, TikWM, MusicallyDown
    
    Serviços removidos permanentemente:
    - Urlebird (decisão do usuário)
    - Tikmate (site bloqueado pelo Cloudflare)
    - SSStik (erro de extração de token)
    - Tikdown (erro de extração de token)
    """
    # Mapeamento de nomes para objetos (apenas serviços que funcionam)
    service_map = {
        'Snaptik': ('Snaptik', snaptik, True, False),
        'TTDownloader': ('TTDownloader', ttdownloader, True, False),
        'TikWM': ('TikWM', tikwm, True, False),
        'MusicallyDown': ('MusicallyDown', mdown, True, False),
    }
    
    # Ordem padrão (apenas serviços que funcionam)
    default_order = [
        'Snaptik',
        'TTDownloader',
        'TikWM',
        'MusicallyDown',
    ]
    
    # Carregar ordem otimizada
    optimized_order = load_optimized_services_order()
    
    # Combinar: serviços que funcionaram primeiro, depois os demais
    if optimized_order:
        # Serviços que funcionaram (na ordem que funcionaram)
        working_list = [service_map[name] for name in optimized_order if name in service_map]
        
        # Serviços que não foram testados ou não funcionaram (ordem padrão)
        remaining = [name for name in default_order if name not in optimized_order]
        remaining_list = [service_map[name] for name in remaining if name in service_map]
        
        # Combinar: funcionando primeiro, depois os demais
        services = working_list + remaining_list
    else:
        # Usar ordem padrão se não houver ordem otimizada
        services = [service_map[name] for name in default_order if name in service_map]
    
    # Urlebird foi removido permanentemente
    # Não adicionar mais Urlebird como fallback
    
    return services

def download_tiktok_video_apify(url):
    """Baixa vídeo do TikTok usando Apify TikTok Scraper
    
    Usa Apify para obter URL de download direto do vídeo e baixa usando requests.
    """
    if not APIFY_AVAILABLE:
        return None, "Apify Client não está instalado. Execute: pip install apify-client"
    
    try:
        # Obter API token do Apify
        apify_token = os.getenv('APIFY_API_TOKEN', None)
        if not apify_token:
            return None, "APIFY_API_TOKEN não configurado. Configure a variável de ambiente com sua chave do Apify"
        
        # Extrair username da URL
        username_match = re.search(r'@([\w.]+)', url)
        if not username_match:
            return None, "Não foi possível extrair username da URL"
        
        username = username_match.group(1)
        
        logger.info(f"Tentando baixar vídeo via Apify: {url}")
        
        # Inicializar cliente Apify
        client = ApifyClient(apify_token)
        
        # Preparar input para o Actor TikTok Scraper (formato conforme exemplo do usuário)
        run_input = {
            "startURLs": [url],  # URL direta do vídeo
            "resultsPerPage": 1,
            "shouldDownloadVideos": True,  # Habilitar download de vídeos
            "shouldDownloadSubtitles": True,
            "shouldDownloadAvatars": False,
            "shouldDownloadCovers": False,
            "shouldDownloadMusicCovers": False,
            "shouldDownloadSlideshowImages": False,
            "proxyCountryCode": "None"
        }
        
        # Executar Actor e aguardar conclusão
        logger.info("Executando Apify TikTok Scraper para download...")
        run = client.actor("clockworks/tiktok-scraper").call(run_input=run_input)
        
        # Buscar resultados do dataset
        dataset_id = run.get("defaultDatasetId")
        if not dataset_id:
            return None, "Dataset não foi criado pelo Apify"
        
        logger.info(f"Buscando resultados do dataset {dataset_id}...")
        
        # Iterar pelos itens do dataset
        items = list(client.dataset(dataset_id).iterate_items())
        
        if not items or len(items) == 0:
            return None, "Nenhum vídeo encontrado no Apify"
        
        # Pegar o primeiro item
        video_data = items[0]
        
        # Tentar obter URL de download direto (várias possibilidades de campos)
        video_url = (video_data.get("videoUrl") or 
                    video_data.get("videoDownloadUrl") or 
                    video_data.get("downloadAddr") or
                    video_data.get("videoMeta", {}).get("videoUrl") or
                    video_data.get("videoMeta", {}).get("downloadAddr"))
        
        if not video_url:
            # Tentar obter do campo videoMeta ou outros campos aninhados
            video_meta = video_data.get("videoMeta", {})
            if video_meta:
                video_url = (video_meta.get("videoUrl") or 
                           video_meta.get("downloadAddr") or
                           video_meta.get("playAddr"))
        
        if video_url:
            # Baixar vídeo da URL direta
            logger.info(f"Baixando vídeo da URL obtida do Apify...")
            
            # Criar nome de arquivo temporário único
            temp_filename = f"tiktok_{uuid.uuid4().hex[:8]}.mp4"
            temp_path = os.path.join(DOWNLOAD_DIR, temp_filename)
            
            # Baixar vídeo usando requests
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Referer': url
            }
            
            response = requests.get(video_url, headers=headers, timeout=60, stream=True)
            response.raise_for_status()
            
            with open(temp_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            if os.path.exists(temp_path) and os.path.getsize(temp_path) > 0:
                logger.info(f"✓ Vídeo baixado com sucesso via Apify: {temp_path}")
                return temp_path, None
            else:
                return None, "Arquivo baixado está vazio"
        
        # Se não encontrou URL direta, tentar baixar arquivo do dataset do Apify
        # (quando shouldDownloadVideos: true, o Apify pode ter baixado o arquivo)
        logger.info("URL de download direto não encontrada, tentando baixar arquivo do dataset do Apify...")
        
        # Tentar acessar arquivos do dataset
        try:
            # Listar arquivos do dataset
            dataset_files = list(client.dataset(dataset_id).list_files())
            
            if dataset_files and len(dataset_files) > 0:
                # Encontrar arquivo de vídeo
                video_file = None
                for file_info in dataset_files:
                    file_name = file_info.get('name', '') or file_info.get('key', '')
                    if file_name.endswith('.mp4'):
                        video_file = file_info
                        break
                
                if video_file:
                    # Obter URL de download do arquivo
                    file_key = video_file.get('key') or video_file.get('name')
                    if file_key:
                        # Criar nome de arquivo temporário único
                        temp_filename = f"tiktok_{uuid.uuid4().hex[:8]}.mp4"
                        temp_path = os.path.join(DOWNLOAD_DIR, temp_filename)
                        
                        # Baixar arquivo do dataset usando a URL
                        file_url = f"https://api.apify.com/v2/datasets/{dataset_id}/items/{file_key}?format=json"
                        # Ou tentar baixar diretamente do storage
                        try:
                            # Tentar obter o arquivo diretamente
                            file_response = client.dataset(dataset_id).get_item(file_key)
                            # Se retornar bytes, salvar diretamente
                            if isinstance(file_response, bytes):
                                with open(temp_path, 'wb') as f:
                                    f.write(file_response)
                                if os.path.exists(temp_path) and os.path.getsize(temp_path) > 0:
                                    logger.info(f"✓ Vídeo baixado com sucesso via Apify (dataset): {temp_path}")
                                    return temp_path, None
                        except:
                            pass
            
        except Exception as e:
            logger.debug(f"Erro ao tentar baixar arquivo do dataset: {e}")
        
        return None, "Não foi possível obter URL de download ou arquivo do Apify"
        
    except Exception as e:
        error_msg = f"Erro ao usar Apify para download: {str(e)}"
        logger.error(error_msg)
        import traceback
        logger.debug(traceback.format_exc())
        return None, error_msg

def download_tiktok_video(url):
    """Baixa vídeo do TikTok usando tiktok-downloader
    
    Usa ordem otimizada baseada em testes anteriores.
    Serviços que funcionaram primeiro são tentados primeiro.
    Apify é usado como último recurso.
    """
    
    if not TIKTOK_DOWNLOADER_AVAILABLE:
        return None, "Biblioteca tiktok-downloader não está instalada. Execute: pip install tiktok_downloader"
    
    # Carregar lista de serviços ordenada por confiabilidade
    services = get_services_list()
    
    downloaded_file = None
    last_error = None
    
    for service_name, service_func, is_function, is_urlebird in services:
        try:
            logger.info(f"Tentando baixar com {service_name}...")
            
            # Urlebird foi removido permanentemente - não usar mais
            if is_urlebird:
                logger.warning(f"{service_name} foi removido permanentemente")
                continue
            
            # Métodos padrão do tiktok-downloader
            if service_func is None:
                continue
            
            # Chamar serviço (função ou classe)
            # Segundo a documentação, todos retornam uma lista diretamente
            if is_function:
                data_list = service_func(url)
            else:
                # Classes: TTDownloader, TikWM
                data_list = service_func(url)
            
            # Verificar se retornou lista válida
            if not data_list or not isinstance(data_list, list) or len(data_list) == 0:
                logger.warning(f"{service_name} não retornou lista de vídeos válida")
                continue
            
            # Pegar o primeiro vídeo da lista
            video_item = data_list[0]
            
            # Verificar se tem método download
            if not hasattr(video_item, 'download'):
                logger.warning(f"{service_name} retornou item sem método download")
                continue
            
            # Criar nome de arquivo temporário único
            temp_filename = f"tiktok_{uuid.uuid4().hex[:8]}.mp4"
            temp_path = os.path.join(DOWNLOAD_DIR, temp_filename)
            
            # Usar método download() do objeto
            logger.info(f"✓ {service_name} encontrou vídeo. Baixando...")
            video_item.download(temp_path)
            
            if os.path.exists(temp_path) and os.path.getsize(temp_path) > 0:
                downloaded_file = temp_path
                logger.info(f"✓ Vídeo baixado com sucesso usando {service_name}: {temp_path}")
                return downloaded_file, None
            else:
                logger.warning(f"Arquivo baixado está vazio ou não existe")
                
        except Exception as e:
            last_error = str(e)
            logger.warning(f"Erro ao usar {service_name}: {last_error}")
            continue
    
    # ÚLTIMO RECURSO: Tentar Apify se todos os outros métodos falharam
    # Só tentar Apify se estiver disponível E tiver token configurado
    if APIFY_AVAILABLE:
        apify_token = os.getenv('APIFY_API_TOKEN', None)
        if apify_token:
            logger.warning("Todos os métodos do tiktok-downloader falharam, tentando Apify como último recurso...")
            downloaded_file, error = download_tiktok_video_apify(url)
            if downloaded_file:
                return downloaded_file, None
            if error:
                last_error = f"Apify também falhou: {error}"
        else:
            logger.info("Apify disponível mas APIFY_API_TOKEN não configurado. Pulando Apify no download.")
    
    # Se nenhum serviço funcionou
    error_msg = f"Nenhum serviço conseguiu baixar o vídeo. Último erro: {last_error}" if last_error else "Nenhum serviço conseguiu baixar o vídeo"
    return None, error_msg

@app.route('/health', methods=['GET'])
def health():
    """Endpoint de health check"""
    status = 'ok' if (TIKTOK_DOWNLOADER_AVAILABLE or BEAUTIFULSOUP_AVAILABLE or APIFY_AVAILABLE) else 'warning'
    message = 'API funcionando'
    if not TIKTOK_DOWNLOADER_AVAILABLE and not BEAUTIFULSOUP_AVAILABLE and not APIFY_AVAILABLE:
        message = 'Nenhuma biblioteca de download disponível'
    elif not TIKTOK_DOWNLOADER_AVAILABLE:
        message = 'API funcionando (apenas método Urlebird disponível)'
    elif not BEAUTIFULSOUP_AVAILABLE:
        message = 'API funcionando (método Urlebird não disponível)'
    
    return jsonify({
        'status': status,
        'message': message,
        'tiktok_downloader_available': TIKTOK_DOWNLOADER_AVAILABLE,
        'urlebird_available': BEAUTIFULSOUP_AVAILABLE,
        'apify_available': APIFY_AVAILABLE,
        'apify_token_configured': bool(os.getenv('APIFY_API_TOKEN')),
        'selenium_available': SELENIUM_AVAILABLE,
        'seleniumbase_available': SELENIUMBASE_AVAILABLE,
        'browser_use_available': BROWSER_USE_AVAILABLE,
        'playwright_available': PLAYWRIGHT_AVAILABLE,
        'playwright_stealth_available': PLAYWRIGHT_STEALTH_AVAILABLE
    }), 200

@app.route('/channels/latest', methods=['POST'])
def get_latest_videos():
    """Endpoint para listar os últimos vídeos de múltiplos canais OU extrair metadados de URLs
    
    Aceita:
    - channels: Lista de usernames para buscar último vídeo de cada canal
    - urls: Lista de URLs do TikTok para extrair metadados diretamente
    
    Body:
    {
        "channels": ["usuario1", "@usuario2"]  OU
        "urls": ["https://www.tiktok.com/@usuario/video/123456"]
    }
    
    Response:
    {
        "total": 2,
        "success": 2,
        "failed": 0,
        "results": [
            {
                "url": "https://www.tiktok.com/@usuario/video/123456",
                "success": true,
                "channel": "usuario",
                "video": { ... metadados ... }
            }
        ]
    }
    """
    try:
        # Validar request
        if not request.is_json:
            return jsonify({'error': 'Content-Type deve ser application/json'}), 400
        
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'Body vazio'}), 400
        
        results = []
        
        # Modo 1: Processar URLs diretamente
        if 'urls' in data:
            urls = data['urls']
            if not isinstance(urls, list) or len(urls) == 0:
                return jsonify({'error': 'Campo "urls" deve ser uma lista não vazia'}), 400
            
            logger.info(f"Extraindo metadados de {len(urls)} URL(s)...")
            
            for url in urls:
                url = url.strip() if isinstance(url, str) else str(url).strip()
                
                # Verificar se é URL do Urlebird (perfil de usuário)
                if 'urlebird.com' in url and '/user/' in url:
                    # Extrair username da URL do Urlebird
                    username_match = re.search(r'/user/([^/]+)', url)
                    if username_match:
                        username = username_match.group(1)
                        logger.info(f"Processando perfil Urlebird: @{username}")
                        # Buscar último vídeo do canal usando Urlebird
                        tiktok_url, urlebird_video_url, channel_data, error = get_latest_video_url_from_channel(username)
                        if error or not tiktok_url:
                            results.append({
                                'url': url,
                                'success': False,
                                'error': error or 'Não foi possível encontrar vídeo mais recente'
                            })
                            continue
                        
                        # Extrair metadados completos
                        video_details, details_error = get_video_details_from_urlebird(urlebird_video_url)
                        
                        result = {
                            'url': tiktok_url,
                            'urlebird_profile_url': url,
                            'success': True,
                            'channel': username,
                            'urlebird_url': urlebird_video_url
                        }
                        
                        if channel_data:
                            result['channel_data'] = {
                                'followers': channel_data.get('followers'),
                                'total_likes': channel_data.get('total_likes'),
                                'videos_count': channel_data.get('videos_count')
                            }
                        
                        if video_details:
                            result['video'] = {
                                'caption': video_details.get('caption'),
                                'posted_time': video_details.get('posted_time'),
                                'metrics': {
                                    'views': video_details.get('views'),
                                    'likes': video_details.get('likes'),
                                    'comments': video_details.get('comments'),
                                    'shares': video_details.get('shares')
                                },
                                'cdn_link': video_details.get('cdn_link')
                            }
                        elif details_error:
                            result['video_error'] = details_error
                        
                        results.append(result)
                        continue
                
                # Validar URL do TikTok
                if not validate_tiktok_url(url):
                    results.append({
                        'url': url,
                        'success': False,
                        'error': 'URL inválida. Deve ser URL do TikTok ou Urlebird'
                    })
                    continue
                
                logger.info(f"Processando URL do TikTok: {url}")
                
                # Extrair username da URL
                username_match = re.search(r'@([\w.]+)', url)
                username = username_match.group(1) if username_match else None
                
                # Tentar obter URL do Urlebird para este vídeo específico
                # Primeiro, tentar construir URL do Urlebird a partir da URL do TikTok
                video_id_match = re.search(r'/video/(\d+)', url)
                if video_id_match:
                    video_id = video_id_match.group(1)
                    if username:
                        # Tentar acessar diretamente a página do vídeo no Urlebird
                        urlebird_video_urls = [
                            f"https://urlebird.com/pt/video/{username}-{video_id}/",
                            f"https://urlebird.com/video/{username}-{video_id}/"
                        ]
                        
                        video_details = None
                        urlebird_url_used = None
                        
                        for urlebird_url in urlebird_video_urls:
                            try:
                                details, error = get_video_details_from_urlebird(urlebird_url)
                                if details and not error:
                                    video_details = details
                                    urlebird_url_used = urlebird_url
                                    break
                            except:
                                continue
                        
                        if video_details:
                            result = {
                                'url': url,
                                'success': True,
                                'channel': username,
                                'urlebird_url': urlebird_url_used
                            }
                            
                            # Adicionar metadados do vídeo
                            result['video'] = {
                                'caption': video_details.get('caption'),
                                'posted_time': video_details.get('posted_time'),
                                'metrics': {
                                    'views': video_details.get('views'),
                                    'likes': video_details.get('likes'),
                                    'comments': video_details.get('comments'),
                                    'shares': video_details.get('shares')
                                },
                                'cdn_link': video_details.get('cdn_link')
                            }
                            
                            results.append(result)
                            continue
                
                # Se não conseguiu via Urlebird direto, tentar buscar último vídeo do canal
                if username:
                    tiktok_url, urlebird_video_url, channel_data, error = get_latest_video_url_from_channel(username)
                    if error or not tiktok_url:
                        results.append({
                            'url': url,
                            'success': False,
                            'error': error or 'Não foi possível encontrar vídeo'
                        })
                        continue
                    
                    # Se a URL fornecida não corresponde ao último vídeo, usar a URL fornecida
                    if tiktok_url != url:
                        # Tentar extrair metadados da URL fornecida usando outros métodos
                        results.append({
                            'url': url,
                            'success': True,
                            'channel': username,
                            'note': 'URL fornecida não é o último vídeo do canal',
                            'latest_video_url': tiktok_url
                        })
                    else:
                        # Extrair metadados completos
                        video_details, details_error = get_video_details_from_urlebird(urlebird_video_url)
                        
                        result = {
                            'url': url,
                            'success': True,
                            'channel': username,
                            'urlebird_url': urlebird_video_url
                        }
                        
                        if channel_data:
                            result['channel_data'] = {
                                'followers': channel_data.get('followers'),
                                'total_likes': channel_data.get('total_likes'),
                                'videos_count': channel_data.get('videos_count')
                            }
                        
                        if video_details:
                            result['video'] = {
                                'caption': video_details.get('caption'),
                                'posted_time': video_details.get('posted_time'),
                                'metrics': {
                                    'views': video_details.get('views'),
                                    'likes': video_details.get('likes'),
                                    'comments': video_details.get('comments'),
                                    'shares': video_details.get('shares')
                                },
                                'cdn_link': video_details.get('cdn_link')
                            }
                        elif details_error:
                            result['video_error'] = details_error
                        
                        results.append(result)
                else:
                    results.append({
                        'url': url,
                        'success': False,
                        'error': 'Não foi possível extrair username da URL'
                    })

        # Modo 2: Processar canais (buscar último vídeo)
        channels = data.get('channels')
        if channels is not None:
            if not isinstance(channels, list) or len(channels) == 0:
                return jsonify({'error': 'Campo "channels" deve ser uma lista não vazia'}), 400

            logger.info(f"Buscando últimos vídeos de {len(channels)} canal(is)...")
            
            for channel in channels:
                username = validate_username(channel)
                if not username:
                    results.append({
                        'channel': channel,
                        'success': False,
                        'error': 'Username inválido'
                    })
                    continue
                
                logger.info(f"Buscando último vídeo de @{username}...")
                
                # Buscar URL do vídeo mais recente e dados do canal
                tiktok_url, urlebird_video_url, channel_data, error = get_latest_video_url_from_channel(username)
                
                if error or not tiktok_url:
                    results.append({
                        'channel': username,
                        'success': False,
                        'error': error or 'Não foi possível encontrar vídeo mais recente'
                    })
                    continue
                
                # Verificar se veio do Apify (tem metadados do vídeo no channel_data)
                video_details = None
                details_error = None
                
                if channel_data and '_video_details_apify' in channel_data:
                    # Usar metadados do Apify diretamente
                    video_details = channel_data.pop('_video_details_apify')
                    logger.info("Usando metadados do vídeo do Apify")
                else:
                    # Tentar extrair metadados do Urlebird (só se for URL do Urlebird)
                    if urlebird_video_url and 'urlebird.com' in urlebird_video_url:
                        video_details, details_error = get_video_details_from_urlebird(urlebird_video_url)
                    else:
                        # Se não for URL do Urlebird, não tenta extrair metadados
                        logger.info("URL não é do Urlebird, pulando extração de metadados")
                        details_error = "Metadados não disponíveis (método usado não fornece metadados detalhados)"
                
                # Montar resultado completo
                result = {
                    'channel': username,
                    'success': True,
                    'url': tiktok_url,
                    'urlebird_url': urlebird_video_url
                }
                
                # Adicionar dados do canal
                if channel_data:
                    result['channel_data'] = {
                        'followers': channel_data.get('followers'),
                        'total_likes': channel_data.get('total_likes'),
                        'videos_count': channel_data.get('videos_count')
                    }
                
                # Adicionar metadados e métricas do vídeo
                if video_details:
                    result['video'] = {
                        'caption': video_details.get('caption'),
                        'posted_time': video_details.get('posted_time'),
                        'metrics': {
                            'views': video_details.get('views'),
                            'likes': video_details.get('likes'),
                            'comments': video_details.get('comments'),
                            'shares': video_details.get('shares')
                        },
                        'cdn_link': video_details.get('cdn_link')
                    }
                elif details_error:
                    result['video_error'] = details_error
                
                results.append(result)
        
        # Validar se pelo menos um campo foi fornecido
        if 'urls' not in data and 'channels' not in data:
            return jsonify({'error': 'Campo "channels" ou "urls" é obrigatório'}), 400
        
        # Retornar resultados
        total_items = len(data.get('urls', [])) + len(data.get('channels', []))
        success_count = sum(1 for r in results if r.get('success'))
        return jsonify({
            'total': total_items,
            'success': success_count,
            'failed': total_items - success_count,
            'results': results,
            'message': f'{success_count} de {total_items} item(s) processado(s) com sucesso'
        }), 200
        
    except Exception as e:
        logger.error(f"Erro no endpoint /channels/latest: {str(e)}")
        return jsonify({'error': f'Erro interno: {str(e)}'}), 500

@app.route('/download', methods=['POST'])
def download():
    """Endpoint principal para download de vídeos TikTok
    
    Aceita:
    - url: URL única do vídeo TikTok (retorna arquivo MP4)
    - urls: Lista de URLs para baixar múltiplos vídeos (retorna JSON com resultados)
    
    Use este endpoint no passo 2 do workflow n8n após obter as URLs de /channels/latest
    """
    
    try:
        # Validar request
        if not request.is_json:
            return jsonify({'error': 'Content-Type deve ser application/json'}), 400
        
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'Body vazio'}), 400
        
        # Verificar se é lista de URLs (múltiplos downloads)
        if 'urls' in data:
            urls = data['urls']
            if not isinstance(urls, list) or len(urls) == 0:
                return jsonify({'error': 'Campo "urls" deve ser uma lista não vazia'}), 400
            
            logger.info(f"Iniciando download de {len(urls)} vídeo(s)...")
            
            results = []
            for url in urls:
                url = url.strip() if isinstance(url, str) else str(url).strip()
                
                # Validar URL do TikTok
                if not validate_tiktok_url(url):
                    results.append({
                        'url': url,
                        'success': False,
                        'error': 'URL inválida'
                    })
                    continue
                
                logger.info(f"Baixando vídeo: {url}")
                
                # Baixar vídeo usando todos os métodos disponíveis
                video_file, error = download_tiktok_video(url)
                
                if error:
                    results.append({
                        'url': url,
                        'success': False,
                        'error': error
                    })
                    continue
                
                if video_file and os.path.exists(video_file):
                    file_size = os.path.getsize(video_file)
                    results.append({
                        'url': url,
                        'success': True,
                        'filename': os.path.basename(video_file),
                        'file_path': video_file,
                        'file_size': file_size,
                        'file_size_mb': round(file_size / (1024 * 1024), 2)
                    })
                else:
                    results.append({
                        'url': url,
                        'success': False,
                        'error': 'Arquivo não foi baixado corretamente'
                    })
            
            # Retornar resultados em JSON
            success_count = sum(1 for r in results if r.get('success'))
            return jsonify({
                'total': len(urls),
                'success': success_count,
                'failed': len(urls) - success_count,
                'results': results,
                'message': f'{success_count} de {len(urls)} vídeo(s) baixado(s) com sucesso'
            }), 200 if success_count > 0 else 400
        
        # Modo tradicional: URL única (retorna arquivo MP4)
        if 'url' not in data:
            return jsonify({'error': 'Campo "url" ou "urls" é obrigatório'}), 400
        
        url = data['url'].strip()
        
        # Validar URL do TikTok
        if not validate_tiktok_url(url):
            return jsonify({'error': 'URL inválida. Deve ser uma URL do TikTok'}), 400
        
        logger.info(f"Iniciando download de: {url}")
        
        # Baixar vídeo
        video_file, error = download_tiktok_video(url)
        
        if error:
            return jsonify({'error': error}), 400
        
        if not video_file or not os.path.exists(video_file):
            return jsonify({'error': 'Arquivo não foi baixado corretamente'}), 500
        
        logger.info(f"Vídeo baixado com sucesso: {video_file}")
        
        # Criar função para limpar arquivo após envio
        def remove_file(response):
            try:
                # Aguardar um pouco antes de deletar para garantir que foi enviado
                import time
                time.sleep(1)
                if os.path.exists(video_file):
                    os.remove(video_file)
                    logger.info(f"Arquivo temporário removido: {video_file}")
            except Exception as e:
                logger.warning(f"Erro ao remover arquivo temporário: {e}")
            return response
        
        # Enviar arquivo
        response = send_file(
            video_file,
            mimetype='video/mp4',
            as_attachment=True,
            download_name=os.path.basename(video_file)
        )
        
        # Adicionar callback para limpar após envio
        response.call_on_close(lambda: remove_file(None))
        
        return response
        
    except Exception as e:
        logger.error(f"Erro no endpoint /download: {str(e)}")
        return jsonify({'error': f'Erro interno: {str(e)}'}), 500

@app.route('/download', methods=['GET'])
def download_get():
    """Endpoint GET para teste (aceita URL como query parameter)"""
    url = request.args.get('url')
    if not url:
        return jsonify({'error': 'Parâmetro "url" é obrigatório'}), 400
    
    # Redirecionar para POST
    data = {'url': url}
    request.json = data
    request.is_json = True
    return download()

@app.route('/services', methods=['GET'])
def list_services():
    """Lista serviços disponíveis"""
    services_list = []
    
    # Adicionar Apify primeiro (mais confiável)
    if APIFY_AVAILABLE:
        services_list.append('Apify TikTok Scraper')
    
    # Serviços padrão do tiktok-downloader (apenas os que funcionam)
    services_list.extend([
            'Snaptik',
            'TTDownloader',
            'TikWM',
            'MusicallyDown',
        'Tikdown',
    ])
    
    return jsonify({
        'services': services_list,
        'available': TIKTOK_DOWNLOADER_AVAILABLE,
        'apify_available': APIFY_AVAILABLE,
        'apify_token_configured': bool(os.getenv('APIFY_API_TOKEN'))
    })

if __name__ == '__main__':
    logger.info(f"Iniciando servidor na porta {PORT}")
    logger.info(f"Pasta de downloads: {os.path.abspath(DOWNLOAD_DIR)}")
    if TIKTOK_DOWNLOADER_AVAILABLE:
        logger.info("Biblioteca tiktok-downloader disponível ✓")
    else:
        logger.warning("Biblioteca tiktok-downloader NÃO está instalada!")
    app.run(host='0.0.0.0', port=PORT, debug=False)
