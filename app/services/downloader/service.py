"""
Serviço de download usando múltiplas estratégias gratuitas
1. yt-dlp como biblioteca Python (mais confiável)
2. pytubefix (biblioteca Python pura)
3. Playwright para extrair URL
4. Requests + parsing manual (fallback)
"""
import os
import logging
import httpx
import re
import json
from typing import Optional
from app.core.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

class DownloaderService:
    def __init__(self):
        """Serviço stateless - não precisa de sessão de banco"""
        pass

    def _sanitize_filename(self, filename: str, max_length: int = 200) -> str:
        """Limpa o nome do arquivo criando um slug: minúsculo, sem acentos, sem emojis, espaços viram underscores"""
        import re
        import unicodedata
        
        # Remover emojis e caracteres especiais
        # Remove emojis (Unicode ranges para emojis)
        emoji_pattern = re.compile(
            "["
            "\U0001F600-\U0001F64F"  # emoticons
            "\U0001F300-\U0001F5FF"  # symbols & pictographs
            "\U0001F680-\U0001F6FF"  # transport & map symbols
            "\U0001F1E0-\U0001F1FF"  # flags (iOS)
            "\U00002702-\U000027B0"
            "\U000024C2-\U0001F251"
            "]+", flags=re.UNICODE
        )
        filename = emoji_pattern.sub('', filename)
        
        # Mapear caracteres especiais comuns
        # Fazer ANTES da normalização para garantir conversão
        char_map = {
            '\u00AA': 'a',  # ª (ordinal feminino)
            '\u00BA': 'o',  # º (ordinal masculino)
            '\u00B0': 'o',  # ° (grau)
            '\u00E7': 'c',  # ç
            '\u00C7': 'c',  # Ç
            '\u00F1': 'n',  # ñ
            '\u00D1': 'n',  # Ñ
        }
        for old, new in char_map.items():
            filename = filename.replace(old, new)
        
        # Normalizar Unicode (NFD = Normalized Form Decomposed)
        # Isso separa acentos dos caracteres
        filename = unicodedata.normalize('NFD', filename)
        
        # Remover acentos (diacríticos) - categoria 'Mn' = Mark, Nonspacing
        filename = ''.join(
            char for char in filename 
            if unicodedata.category(char) != 'Mn'  # Remove acentos
        )
        
        # Agora manter apenas letras ASCII, números e alguns caracteres básicos
        filename = ''.join(
            char for char in filename 
            if (char.isascii() and char.isalnum()) or char in ' _-.'  # Mantém apenas ASCII alfanumérico
        )
        
        # Converter para minúsculas
        filename = filename.lower()
        
        # Remover caracteres inválidos para nome de arquivo
        filename = re.sub(r'[<>:"/\\|?*]', '', filename)
        
        # Substituir espaços, hífens e pontos por underscore
        filename = re.sub(r'[\s\-_\.]+', '_', filename)
        
        # Remover underscores múltiplos
        filename = re.sub(r'_+', '_', filename)
        
        # Remover underscores no início e fim
        filename = filename.strip('_')
        
        # Limitar tamanho
        if len(filename) > max_length:
            filename = filename[:max_length].rstrip('_')
        
        # Se ficar vazio, usar um nome padrão
        if not filename:
            filename = "video"
        
        return filename

    async def _get_video_title(self, video_url: str) -> Optional[str]:
        """Busca o título do vídeo usando yt-dlp"""
        try:
            import yt_dlp
            
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'skip_download': True,  # Não baixar, só pegar info
            }
            
            # Tentar usar cookies se existirem
            cookies_path = os.path.join(settings.LOCAL_STORAGE_PATH, '..', 'data', 'cookies.txt')
            if os.path.exists(cookies_path):
                ydl_opts['cookiefile'] = cookies_path
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(video_url, download=False)
                return info.get('title')
        except Exception as e:
            logger.warning(f"Could not get video title: {e}")
            return None

    async def download_video(
        self,
        video_url: str,
        platform: str,
        external_video_id: str,
        group_name: Optional[str] = None,
        source_name: Optional[str] = None
    ):
        """
        Faz download de um vídeo usando múltiplas estratégias
        Organiza por: downloads/{grupo}/{fonte}/{titulo_do_video}.mp4
        """
        # Organizar estrutura de pastas
        if group_name and source_name:
            group_folder = group_name.replace(" ", "_").lower()
            source_folder = source_name.replace(" ", "_").lower()
            download_dir = os.path.join(settings.LOCAL_STORAGE_PATH, group_folder, source_folder)
        else:
            download_dir = os.path.join(settings.LOCAL_STORAGE_PATH, platform)
        
        os.makedirs(download_dir, exist_ok=True)
        
        # Buscar título do vídeo
        video_title = await self._get_video_title(video_url)
        
        # Usar título se disponível, senão usar external_video_id
        if video_title:
            filename = self._sanitize_filename(video_title)
            output_path = os.path.join(download_dir, f"{filename}.mp4")
            logger.info(f"Using video title as filename: {filename}")
        else:
            # Fallback para external_video_id se não conseguir o título
        output_path = os.path.join(download_dir, f"{external_video_id}.mp4")
            logger.warning(f"Could not get video title, using external_video_id: {external_video_id}")

        # Verificar se arquivo já existe e está completo
        # Verificar tanto pelo nome do título quanto pelo video_id (caso já tenha sido baixado antes)
        existing_path = None
        if os.path.exists(output_path) and os.path.getsize(output_path) > 1000:
            existing_path = output_path
        else:
            # Verificar se existe com o nome antigo (video_id)
            old_path = os.path.join(download_dir, f"{external_video_id}.mp4")
            if os.path.exists(old_path) and os.path.getsize(old_path) > 1000:
                existing_path = old_path
        
        if existing_path:
            logger.info(f"File already exists: {existing_path} ({os.path.getsize(existing_path)} bytes)")
            return {"status": "completed", "path": existing_path}

        # Tentar múltiplas estratégias em ordem (da mais confiável para menos)
        strategies = [
            ("yt-dlp-library", self._download_with_ytdlp_library),
            ("pytubefix", self._download_with_pytubefix),
            ("yt-dlp-subprocess", self._download_with_ytdlp_subprocess),
            ("Playwright", self._download_with_playwright),
            ("Requests", self._download_with_requests),
        ]
        
        for strategy_name, strategy_func in strategies:
            try:
                logger.info(f"Trying {strategy_name} for {external_video_id}")
                result = await strategy_func(video_url, output_path)
                
                # Verificar se arquivo foi criado mesmo se status não for "completed"
                if os.path.exists(output_path) and os.path.getsize(output_path) > 1000:
                    logger.info(f"Success with {strategy_name} - file created ({os.path.getsize(output_path)} bytes)")
                    return {"status": "completed", "path": output_path}
                
                if result.get('status') == 'completed':
                    logger.info(f"Success with {strategy_name}")
                    return result
                else:
                    logger.warning(f"{strategy_name} failed: {result.get('error')}")
            except Exception as e:
                logger.warning(f"{strategy_name} exception: {e}")
                # Verificar se arquivo foi criado mesmo com exceção
                if os.path.exists(output_path) and os.path.getsize(output_path) > 1000:
                    logger.info(f"File created despite exception with {strategy_name}")
                    return {"status": "completed", "path": output_path}
                continue
        
        # Verificar uma última vez se arquivo foi criado
        if os.path.exists(output_path) and os.path.getsize(output_path) > 1000:
            logger.info(f"File was created by one of the strategies ({os.path.getsize(output_path)} bytes)")
            return {"status": "completed", "path": output_path}
        
        return {"status": "failed", "error": "All download strategies failed"}

    async def _download_with_ytdlp_library(self, video_url: str, output_path: str):
        """Estratégia 1: yt-dlp como biblioteca Python (MAIS CONFIÁVEL)"""
        try:
            import yt_dlp
            
            # Configurações do yt-dlp
        ydl_opts = {
                'format': 'best[ext=mp4]/best',
            'outtmpl': output_path.replace('.mp4', '.%(ext)s'),
                'quiet': True,
                'no_warnings': True,
                'noplaylist': True,
            }
            
            # Tentar usar cookies se existirem
            cookies_path = os.path.join(settings.LOCAL_STORAGE_PATH, '..', 'data', 'cookies.txt')
            if os.path.exists(cookies_path):
                ydl_opts['cookiefile'] = cookies_path
                logger.info("Using cookies file")
            
            # Usar yt-dlp como biblioteca
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([video_url])
            
            # Verificar se arquivo foi criado
            if os.path.exists(output_path):
                return {"status": "completed", "path": output_path}
            
            # Procurar arquivo com extensão diferente
            base_path = output_path.replace('.mp4', '')
            for ext in ['.mp4', '.webm', '.mkv', '.m4a']:
                test_path = base_path + ext
                if os.path.exists(test_path):
                    # Se não for mp4, renomear para mp4
                    if ext != '.mp4':
                        os.rename(test_path, output_path)
                    return {"status": "completed", "path": output_path}
            
            return {"status": "failed", "error": "File not found after yt-dlp download"}
                
        except ImportError:
            return {"status": "failed", "error": "yt-dlp library not installed"}
        except Exception as e:
            logger.error(f"yt-dlp library error: {e}")
            return {"status": "failed", "error": f"yt-dlp error: {str(e)[:200]}"}

    async def _download_with_pytubefix(self, video_url: str, output_path: str):
        """Estratégia 2: pytubefix (biblioteca Python pura)"""
        try:
            from pytubefix import YouTube
            
            # Criar objeto YouTube
            yt = YouTube(video_url)
            
            # Pegar melhor stream de vídeo
            stream = yt.streams.filter(progressive=True, file_extension='mp4').order_by('resolution').desc().first()
            
            if not stream:
                # Tentar streams adaptativos
                video_stream = yt.streams.filter(only_video=True, file_extension='mp4').order_by('resolution').desc().first()
                audio_stream = yt.streams.filter(only_audio=True).first()
                
                if video_stream and audio_stream:
                    # Baixar vídeo e áudio separadamente (precisa ffmpeg para combinar)
                    video_path = video_stream.download(output_path=os.path.dirname(output_path), filename=f"{os.path.basename(output_path).replace('.mp4', '')}_video.mp4")
                    audio_path = audio_stream.download(output_path=os.path.dirname(output_path), filename=f"{os.path.basename(output_path).replace('.mp4', '')}_audio.mp4")
                    
                    # Combinar com ffmpeg (se disponível)
                    try:
                        import subprocess
                        subprocess.run([
                            'ffmpeg', '-i', video_path, '-i', audio_path,
                            '-c:v', 'copy', '-c:a', 'copy', '-y', output_path
                        ], check=True, capture_output=True)
                        os.remove(video_path)
                        os.remove(audio_path)
                        return {"status": "completed", "path": output_path}
                    except:
                        return {"status": "failed", "error": "ffmpeg not available for merging"}
                else:
                    return {"status": "failed", "error": "No suitable streams found"}
            else:
                # Download direto
                stream.download(output_path=os.path.dirname(output_path), filename=os.path.basename(output_path))
                return {"status": "completed", "path": output_path}
                
        except ImportError:
            return {"status": "failed", "error": "pytubefix not installed"}
        except Exception as e:
            logger.error(f"pytubefix error: {e}")
            return {"status": "failed", "error": f"pytubefix error: {str(e)[:200]}"}

    async def _download_with_ytdlp_subprocess(self, video_url: str, output_path: str):
        """Estratégia 3: yt-dlp via subprocess (fallback)"""
        try:
            import subprocess
            import asyncio
            
            # Verificar se yt-dlp está disponível
            try:
                process = await asyncio.create_subprocess_exec(
                    'yt-dlp', '--version',
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                await process.communicate()
                if process.returncode != 0:
                    raise FileNotFoundError("yt-dlp not found")
            except FileNotFoundError:
                return {"status": "failed", "error": "yt-dlp not installed"}
            
            # Usar yt-dlp via subprocess
            cmd = [
                'yt-dlp',
                video_url,
                '-f', 'best[ext=mp4]/best',
                '-o', output_path.replace('.mp4', '.%(ext)s'),
                '--no-warnings',
                '--quiet'
            ]
            
            # Adicionar cookies se existirem
            cookies_path = os.path.join(settings.LOCAL_STORAGE_PATH, '..', 'data', 'cookies.txt')
            if os.path.exists(cookies_path):
                cmd.extend(['--cookies', cookies_path])
            
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
                
                # Procurar arquivo com extensão diferente
                base_path = output_path.replace('.mp4', '')
                for ext in ['.mp4', '.webm', '.mkv']:
                    test_path = base_path + ext
                    if os.path.exists(test_path):
                        return {"status": "completed", "path": test_path}
                
                return {"status": "failed", "error": "File not found after yt-dlp download"}
            else:
                error_msg = stderr.decode('utf-8', errors='ignore') if stderr else "Unknown error"
                return {"status": "failed", "error": f"yt-dlp failed: {error_msg[:200]}"}
                
        except FileNotFoundError:
            return {"status": "failed", "error": "yt-dlp not installed"}
        except Exception as e:
            logger.error(f"yt-dlp subprocess error: {e}")
            return {"status": "failed", "error": f"yt-dlp error: {str(e)}"}

    async def _download_with_playwright(self, video_url: str, output_path: str):
        """Estratégia 4: Playwright para extrair URL e fazer download"""
        try:
            from playwright.async_api import async_playwright
            
            async with async_playwright() as p:
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
                
                # Interceptar requisições de vídeo
                video_urls = []
                
                async def handle_response(response):
                    url = response.url
                    if 'googlevideo.com' in url and 'videoplayback' in url and 'itag=' in url:
                        if 'mime=video' in url:
                            video_urls.append(url)
                
                page.on('response', handle_response)
                
                logger.info(f"Navigating to {video_url}")
                await page.goto(video_url, wait_until='networkidle', timeout=60000)
                await page.wait_for_timeout(5000)
                
                # Tentar clicar no vídeo para iniciar reprodução
                try:
                    video_selector = 'video'
                    if await page.query_selector(video_selector):
                        await page.click(video_selector)
                        await page.wait_for_timeout(3000)
                except:
                    pass
                
                # Tentar extrair do JavaScript
                try:
                    video_info = await page.evaluate("""
                        () => {
                            if (window.ytInitialPlayerResponse) {
                                const streamingData = window.ytInitialPlayerResponse.streamingData;
                                if (streamingData && streamingData.formats) {
                                    const best = streamingData.formats
                                        .filter(f => f.mimeType && f.mimeType.includes('video/mp4'))
                                        .sort((a, b) => ((b.width || 0) * (b.height || 0)) - ((a.width || 0) * (a.height || 0)))[0];
                                    if (best && best.url) return best.url;
                                }
                            }
                            return null;
                        }
                    """)
                    if video_info and not video_info.startswith('blob:'):
                        video_urls.append(video_info)
                except:
                    pass
                
                if not video_urls:
                    await browser.close()
                    return {"status": "failed", "error": "Could not extract video URL"}
                
                # Pegar melhor URL
                video_url_direct = video_urls[0]
                if len(video_urls) > 1:
                    video_urls.sort(key=lambda x: int(re.search(r'itag=(\d+)', x).group(1)) if re.search(r'itag=(\d+)', x) else 0, reverse=True)
                    video_url_direct = video_urls[0]
                
                # Obter cookies
                cookies = await context.cookies()
                cookie_dict = {cookie['name']: cookie['value'] for cookie in cookies}
                
                await browser.close()
                
                # Fazer download com httpx
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Referer': 'https://www.youtube.com/',
                    'Accept': '*/*',
                }
                
                async with httpx.AsyncClient(timeout=300.0, headers=headers, cookies=cookie_dict, follow_redirects=True) as client:
                    async with client.stream('GET', video_url_direct) as response:
                        if response.status_code == 403:
                            return {"status": "failed", "error": "403 Forbidden"}
                        
                        response.raise_for_status()
                        
                        with open(output_path, 'wb') as f:
                            async for chunk in response.aiter_bytes(chunk_size=8192):
                                f.write(chunk)
                
                if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            return {"status": "completed", "path": output_path}
                else:
                    return {"status": "failed", "error": "File not created or empty"}
                    
        except ImportError:
            return {"status": "failed", "error": "Playwright not installed"}
        except Exception as e:
            logger.error(f"Playwright error: {e}")
            return {"status": "failed", "error": f"Playwright error: {str(e)}"}

    async def _download_with_requests(self, video_url: str, output_path: str):
        """Estratégia 5: Requests + parsing manual (100% gratuito, sem dependências externas)"""
        try:
            import requests
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9',
            }
            
            # Fazer requisição para a página do vídeo
            logger.info(f"Fetching page with requests: {video_url}")
            response = requests.get(video_url, headers=headers, timeout=30)
            response.raise_for_status()
            
            html = response.text
            
            # Extrair ytInitialPlayerResponse do HTML
            video_url_direct = None
            
            # Procurar por ytInitialPlayerResponse
            pattern = r'var ytInitialPlayerResponse = ({.+?});'
            match = re.search(pattern, html)
            
            if match:
                try:
                    player_response = json.loads(match.group(1))
                    streaming_data = player_response.get('streamingData', {})
                    
                    # Tentar formats primeiro
                    formats = streaming_data.get('formats', [])
                    if formats:
                        best_format = max(
                            [f for f in formats if 'video/mp4' in f.get('mimeType', '')],
                            key=lambda f: (f.get('width', 0) * f.get('height', 0)),
                            default=None
                        )
                        if best_format and best_format.get('url'):
                            video_url_direct = best_format['url']
                    
                    # Se não encontrou, tentar adaptiveFormats
                    if not video_url_direct:
                        adaptive_formats = streaming_data.get('adaptiveFormats', [])
                        if adaptive_formats:
                            best_video = max(
                                [f for f in adaptive_formats if 'video/mp4' in f.get('mimeType', '') and 'audio' not in f.get('mimeType', '')],
                                key=lambda f: (f.get('width', 0) * f.get('height', 0)),
                                default=None
                            )
                            if best_video and best_video.get('url'):
                                video_url_direct = best_video['url']
                except (json.JSONDecodeError, KeyError) as e:
                    logger.debug(f"Failed to parse player response: {e}")
            
            if not video_url_direct:
                return {"status": "failed", "error": "Could not extract video URL from HTML"}
            
            # Fazer download
            logger.info(f"Downloading from extracted URL...")
            download_headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Referer': 'https://www.youtube.com/',
                'Accept': '*/*',
            }
            
            download_response = requests.get(video_url_direct, headers=download_headers, stream=True, timeout=300)
            
            if download_response.status_code == 403:
                return {"status": "failed", "error": "403 Forbidden - YouTube blocked request"}
            
            download_response.raise_for_status()
            
            total_size = int(download_response.headers.get('content-length', 0))
            
            with open(output_path, 'wb') as f:
                downloaded = 0
                for chunk in download_response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total_size > 0 and downloaded % (1024 * 1024) == 0:
                            percent = (downloaded / total_size) * 100
                            logger.info(f"Downloaded {downloaded}/{total_size} bytes ({percent:.1f}%)")
            
            if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                return {"status": "completed", "path": output_path}
            else:
                return {"status": "failed", "error": "File not created or empty"}
                
        except ImportError:
            return {"status": "failed", "error": "requests library not installed"}
        except Exception as e:
            logger.error(f"Requests error: {e}")
            return {"status": "failed", "error": f"Requests error: {str(e)}"}
