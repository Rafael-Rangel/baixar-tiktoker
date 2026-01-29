import os
import uuid
import re
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

app = Flask(__name__)
CORS(app)  # Permitir CORS para n8n

# Configurações
DOWNLOAD_DIR = os.getenv('DOWNLOAD_DIR', './downloads')
PORT = int(os.getenv('PORT', 5000))

# Criar pasta de downloads se não existir
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# Importar biblioteca tiktok-downloader
try:
    from tiktok_downloader import Tikmate, TTDownloader, TikWM
    from tiktok_downloader import snaptik, mdown, tikdown, tikwm, ttdownloader
    from tiktok_downloader.ssstik import ssstik
    TIKTOK_DOWNLOADER_AVAILABLE = True
except ImportError as e:
    logger.error(f"tiktok-downloader não está instalado ou erro na importação: {e}. Execute: pip install tiktok_downloader")
    TIKTOK_DOWNLOADER_AVAILABLE = False
    Tikmate = TTDownloader = TikWM = None
    snaptik = mdown = tikdown = tikwm = ttdownloader = ssstik = None

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
        
        # Configurar Chrome com opções anti-detecção
        options = uc.ChromeOptions()
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_argument('--disable-extensions')
        options.add_argument('--disable-gpu')
        options.add_argument('--window-size=1920,1080')
        options.add_argument('--start-maximized')
        options.add_argument('--lang=pt-BR')
        # Removido excludeSwitches - não é suportado em todas as versões
        # options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        
        # User-Agent realista
        options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        
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

def get_latest_video_url_from_channel(username):
    """Extrai a URL do vídeo mais recente e dados do canal usando Urlebird
    
    Tenta primeiro com Selenium (anti-detecção), depois com requests.
    Retorna: (tiktok_url, urlebird_video_url, channel_data, error)
    """
    if not BEAUTIFULSOUP_AVAILABLE:
        return None, None, None, "BeautifulSoup4 não está instalado"
    
    # Tentar primeiro com Selenium (mais confiável contra bloqueios)
    if SELENIUM_AVAILABLE:
        logger.info("Tentando método Selenium (anti-detecção)...")
        result = get_latest_video_url_from_channel_selenium(username)
        if result[0] is not None:  # Se obteve sucesso
            return result
        logger.warning("Selenium falhou, tentando método requests...")
    
    # Fallback para método requests
    try:
        username = validate_username(username)
        if not username:
            return None, None, None, "Username inválido"
        
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
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0',
            'Referer': 'https://urlebird.com/',
            'Origin': 'https://urlebird.com'
        }
        
        # Criar sessão para manter cookies
        session = requests.Session()
        
        # Estratégia 1: Tentar com headers básicos primeiro
        basic_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'pt-BR,pt;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }
        session.headers.update(basic_headers)
        
        # Tentar primeiro acessar a página inicial em PT para obter cookies
        try:
            logger.info("Obtendo cookies da página inicial (PT)...")
            initial_response = session.get('https://urlebird.com/pt/', timeout=10)
            if initial_response.status_code == 200:
                logger.info("✓ Cookies obtidos com sucesso")
            import time
            time.sleep(2)  # Delay maior para parecer mais humano
        except Exception as e:
            logger.warning(f"Erro ao obter cookies: {str(e)}")
            # Tentar página inicial sem /pt/ como fallback
            try:
                session.get('https://urlebird.com/', timeout=10)
                import time
                time.sleep(1)
            except:
                pass
        
        # Agora atualizar com headers completos
        session.headers.update(headers)
        
        # URL exata: sempre usar /pt/ primeiro (versão em português)
        urls_to_try = [
            f"https://urlebird.com/pt/user/{username}/"
        ]
        
        # Fallback apenas se necessário
        # urls_to_try = [
        #     f"https://urlebird.com/pt/user/{username}/",
        #     f"https://urlebird.com/user/{username}/"
        # ]
        
        response = None
        url_used = None
        last_status = None
        
        for url in urls_to_try:
            try:
                logger.info(f"Tentando acessar: {url}")
                import time
                time.sleep(0.5)  # Delay entre tentativas
                
                response = session.get(url, timeout=15, allow_redirects=True)
                last_status = response.status_code
                
                if response.status_code == 200:
                    url_used = url
                    logger.info(f"✓ Sucesso ao acessar: {url}")
                    break
                elif response.status_code == 403:
                    logger.warning(f"403 Forbidden em {url} - Tentando estratégias alternativas...")
                    
                    # Estratégia 1: Mudar referer para Google
                    session.headers.update({
                        'Referer': 'https://www.google.com/',
                        'Origin': 'https://www.google.com'
                    })
                    import time
                    time.sleep(2)
                    response = session.get(url, timeout=15, allow_redirects=True)
                    if response.status_code == 200:
                        url_used = url
                        logger.info(f"✓ Sucesso após mudar referer: {url}")
                        break
                    
                    # Estratégia 2: User-Agent diferente
                    session.headers.update({
                        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                        'Referer': 'https://urlebird.com/pt/',
                        'Origin': 'https://urlebird.com'
                    })
                    import time
                    time.sleep(2)
                    response = session.get(url, timeout=15, allow_redirects=True)
                    if response.status_code == 200:
                        url_used = url
                        logger.info(f"✓ Sucesso com User-Agent alternativo: {url}")
                        break
                    
                    # Se ainda falhar, continuar para próxima URL ou retornar erro
                    logger.error(f"Todas as estratégias falharam para {url}")
                    continue
                else:
                    logger.warning(f"Status {response.status_code} em {url}")
                    continue
            except requests.exceptions.RequestException as e:
                logger.warning(f"Erro ao acessar {url}: {str(e)}")
                continue
        
        if not response or response.status_code != 200:
            error_msg = f"Erro ao acessar Urlebird: Não foi possível acessar nenhuma URL. Último status HTTP: {last_status if last_status else 'N/A'}. O Urlebird pode estar bloqueando requisições automatizadas. Tente novamente mais tarde ou use outro método."
            logger.error(error_msg)
            return None, None, None, error_msg
        
        logger.info(f"✓ Acesso bem-sucedido via: {url_used}")
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Extrair dados do canal
        channel_data = get_channel_data(username, soup)
        
        # Armazenar base_url para uso posterior
        base_url = url_used.rstrip('/').rsplit('/user/', 1)[0] if url_used else 'https://urlebird.com'
        
        # Procura pelo primeiro link que aponta para um vídeo
        latest_video_element = soup.find('a', href=lambda href: href and '/video/' in href)
        
        if latest_video_element:
            urlebird_video_url = latest_video_element.get('href', '')
            
            # Garantir URL completa - usar o mesmo domínio/base da URL usada
            if urlebird_video_url.startswith('/'):
                # Se começa com /, pode ser /pt/video/ ou /video/
                urlebird_video_url = f"{base_url}{urlebird_video_url}"
            elif not urlebird_video_url.startswith('http'):
                urlebird_video_url = f"{base_url}/{urlebird_video_url}"
            
            # Extrair o ID do vídeo para reconstruir a URL original do TikTok
            # Formato esperado: /video/{username}-{video_id}/ ou similar
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
            
            logger.info(f"✓ Vídeo mais recente encontrado: {tiktok_url}")
            return tiktok_url, urlebird_video_url, channel_data, None
        else:
            return None, None, channel_data, f"Nenhum vídeo encontrado para @{username}"
            
    except requests.exceptions.RequestException as e:
        error_msg = f"Erro ao acessar Urlebird: {str(e)}"
        logger.warning(error_msg)
        return None, None, None, error_msg
    except Exception as e:
        error_msg = f"Erro ao processar página do Urlebird: {str(e)}"
        logger.warning(error_msg)
        return None, None, None, error_msg

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

def download_tiktok_video(url):
    """Baixa vídeo do TikTok usando tiktok-downloader"""
    
    if not TIKTOK_DOWNLOADER_AVAILABLE:
        return None, "Biblioteca tiktok-downloader não está instalada. Execute: pip install tiktok_downloader"
    
    # Lista de serviços para tentar (em ordem de prioridade)
    # Format: (name, service_callable, is_function, is_urlebird)
    services = [
        ('Snaptik', snaptik, True, False),
        ('Tikmate', Tikmate, False, False),
        ('SSStik', ssstik, True, False),
        ('TTDownloader', ttdownloader, True, False),
        ('TikWM', tikwm, True, False),
        ('MusicallyDown', mdown, True, False),
        ('Tikdown', tikdown, True, False),
        ('Urlebird', None, False, True),  # Último método - fallback
    ]
    
    downloaded_file = None
    last_error = None
    
    for service_name, service_func, is_function, is_urlebird in services:
        try:
            logger.info(f"Tentando baixar com {service_name}...")
            
            # Método Urlebird (último na lista - fallback)
            if is_urlebird:
                downloaded_file, error = download_video_via_urlebird(url)
                if error:
                    last_error = error
                    logger.warning(f"Erro ao usar {service_name}: {error}")
                    continue
                if downloaded_file and os.path.exists(downloaded_file) and os.path.getsize(downloaded_file) > 0:
                    logger.info(f"✓ Vídeo baixado com sucesso usando {service_name}: {downloaded_file}")
                    return downloaded_file, None
                else:
                    logger.warning(f"{service_name} não conseguiu baixar o vídeo")
                    continue
            
            # Métodos padrão do tiktok-downloader
            if service_func is None:
                continue
            
            # Chamar serviço (função ou classe)
            # Segundo a documentação, todos retornam uma lista diretamente
            if is_function:
                data_list = service_func(url)
            else:
                # Classes: Tikmate, TTDownloader, TikWM
                if service_name == 'Tikmate':
                    # Tikmate usa get_media() em vez de passar URL no construtor
                    service = service_func()
                    data_list = service.get_media(url)
                else:
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
    
    # Se nenhum serviço funcionou
    error_msg = f"Nenhum serviço conseguiu baixar o vídeo. Último erro: {last_error}" if last_error else "Nenhum serviço conseguiu baixar o vídeo"
    return None, error_msg

@app.route('/health', methods=['GET'])
def health():
    """Endpoint de health check"""
    status = 'ok' if (TIKTOK_DOWNLOADER_AVAILABLE or BEAUTIFULSOUP_AVAILABLE) else 'warning'
    message = 'API funcionando'
    if not TIKTOK_DOWNLOADER_AVAILABLE and not BEAUTIFULSOUP_AVAILABLE:
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
        'selenium_available': SELENIUM_AVAILABLE
    })

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
        if 'channels' in data:
            channels = data['channels']
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
                
                # Buscar URL do vídeo mais recente e dados do canal usando Urlebird
                tiktok_url, urlebird_video_url, channel_data, error = get_latest_video_url_from_channel(username)
                
                if error or not tiktok_url:
                    results.append({
                        'channel': username,
                        'success': False,
                        'error': error or 'Não foi possível encontrar vídeo mais recente'
                    })
                    continue
                
                # Extrair metadados e métricas completas do vídeo
                video_details, details_error = get_video_details_from_urlebird(urlebird_video_url)
                
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
    services_list = [
            'Snaptik',
            'Tikmate',
            'SSStik',
            'TTDownloader',
            'TikWM',
            'MusicallyDown',
        'Tikdown',
        'Urlebird'  # Último método - fallback
    ]
    
    return jsonify({
        'services': services_list,
        'available': TIKTOK_DOWNLOADER_AVAILABLE,
        'urlebird_available': BEAUTIFULSOUP_AVAILABLE,
        'selenium_available': SELENIUM_AVAILABLE
    })

if __name__ == '__main__':
    logger.info(f"Iniciando servidor na porta {PORT}")
    logger.info(f"Pasta de downloads: {os.path.abspath(DOWNLOAD_DIR)}")
    if TIKTOK_DOWNLOADER_AVAILABLE:
        logger.info("Biblioteca tiktok-downloader disponível ✓")
    else:
        logger.warning("Biblioteca tiktok-downloader NÃO está instalada!")
    app.run(host='0.0.0.0', port=PORT, debug=False)
