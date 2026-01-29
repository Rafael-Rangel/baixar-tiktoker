import os
import uuid
import re
import requests
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

def get_latest_video_url_from_channel(username):
    """Extrai a URL do vídeo mais recente e dados do canal usando Urlebird
    
    Retorna: (tiktok_url, urlebird_video_url, channel_data, error)
    """
    if not BEAUTIFULSOUP_AVAILABLE:
        return None, None, None, "BeautifulSoup4 não está instalado"
    
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
        session.headers.update(headers)
        
        # Tentar primeiro acessar a página inicial para obter cookies
        try:
            logger.info("Obtendo cookies da página inicial...")
            session.get('https://urlebird.com/', timeout=10)
            import time
            time.sleep(1)  # Pequeno delay para parecer mais humano
        except Exception as e:
            logger.warning(f"Erro ao obter cookies: {str(e)}")
        
        # Tentar primeiro com /pt/ (versão em português)
        urls_to_try = [
            f"https://urlebird.com/pt/user/{username}/",
            f"https://urlebird.com/user/{username}/"
        ]
        
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
                    logger.warning(f"403 Forbidden em {url} - Urlebird está bloqueando requisições")
                    # Tentar com headers diferentes
                    session.headers.update({
                        'Referer': 'https://www.google.com/',
                        'Origin': 'https://www.google.com'
                    })
                    import time
                    time.sleep(1)
                    response = session.get(url, timeout=15, allow_redirects=True)
                    if response.status_code == 200:
                        url_used = url
                        logger.info(f"✓ Sucesso após mudar referer: {url}")
                        break
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
        'urlebird_available': BEAUTIFULSOUP_AVAILABLE
    })

@app.route('/channels/latest', methods=['POST'])
def get_latest_videos():
    """Endpoint para listar os últimos vídeos de múltiplos canais
    
    Retorna apenas as URLs dos vídeos mais recentes de cada canal.
    Use este endpoint no passo 1 do workflow n8n.
    
    Body:
    {
        "channels": ["usuario1", "@usuario2", "usuario3"]
    }
    
    Response:
    {
        "total": 3,
        "success": 2,
        "failed": 1,
        "results": [
            {
                "channel": "usuario1",
                "success": true,
                "url": "https://www.tiktok.com/@usuario1/video/123456"
            },
            {
                "channel": "usuario2",
                "success": false,
                "error": "Não foi possível encontrar vídeo"
            }
        ]
    }
    """
    try:
        # Validar request
        if not request.is_json:
            return jsonify({'error': 'Content-Type deve ser application/json'}), 400
        
        data = request.get_json()
        
        if not data or 'channels' not in data:
            return jsonify({'error': 'Campo "channels" é obrigatório'}), 400
        
        channels = data['channels']
        if not isinstance(channels, list) or len(channels) == 0:
            return jsonify({'error': 'Campo "channels" deve ser uma lista não vazia'}), 400
        
        logger.info(f"Buscando últimos vídeos de {len(channels)} canal(is)...")
        
        results = []
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
        
        # Retornar resultados
        success_count = sum(1 for r in results if r.get('success'))
        return jsonify({
            'total': len(channels),
            'success': success_count,
            'failed': len(channels) - success_count,
            'results': results,
            'message': f'{success_count} de {len(channels)} canal(is) encontrado(s) com sucesso'
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
        'urlebird_available': BEAUTIFULSOUP_AVAILABLE
    })

if __name__ == '__main__':
    logger.info(f"Iniciando servidor na porta {PORT}")
    logger.info(f"Pasta de downloads: {os.path.abspath(DOWNLOAD_DIR)}")
    if TIKTOK_DOWNLOADER_AVAILABLE:
        logger.info("Biblioteca tiktok-downloader disponível ✓")
    else:
        logger.warning("Biblioteca tiktok-downloader NÃO está instalada!")
    app.run(host='0.0.0.0', port=PORT, debug=False)
