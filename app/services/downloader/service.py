"""
Serviço de download usando yt-dlp (biblioteca Python)
Estratégia única e confiável para download de vídeos
"""
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

    def _youtube_watch_url(self, external_video_id: str) -> str:
        """URL alternativa: watch?v= a partir do ID (fallback quando /shorts/ falha)."""
        return f"https://www.youtube.com/watch?v={external_video_id}"

    def _resolve_cookies_path(self) -> Optional[str]:
        """Procura cookies.txt em data/ e na raiz do projeto (cookies.txt)."""
        # Sempre usar caminhos absolutos
        data_path = settings.DATA_PATH
        if not os.path.isabs(data_path):
            # Se DATA_PATH for relativo, tornar absoluto baseado no diretório de trabalho
            data_path = os.path.abspath(os.path.join(os.getcwd(), data_path))
        
        candidates = [
            os.path.join(data_path, "cookies.txt"),
            os.path.join(os.getcwd(), "cookies.txt"),
        ]
        root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
        if root not in (os.getcwd(),):
            candidates.append(os.path.join(root, "cookies.txt"))
        # Adicionar caminho absoluto explícito para /app/data/cookies.txt (container Docker)
        candidates.append("/app/data/cookies.txt")
        
        for p in candidates:
            if os.path.isfile(p):
                abs_path = os.path.abspath(p)
                logger.info(f"Found cookies file at: {abs_path}")
                return abs_path
        logger.warning("No cookies file found in any candidate location")
        return None

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
        
        # Mapear caracteres especiais ANTES da normalização
        # Isso garante que caracteres como ª e º sejam convertidos antes de serem decompostos
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
            
            cookies_path = self._resolve_cookies_path()
            if cookies_path:
                ydl_opts["cookiefile"] = cookies_path

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
        # Organizar estrutura de pastas (caminhos absolutos)
        base_dir = os.path.abspath(settings.LOCAL_STORAGE_PATH)
        if group_name and source_name:
            group_folder = group_name.replace(" ", "_").lower()
            source_folder = source_name.replace("@", "").strip().replace(" ", "_").lower()
            download_dir = os.path.abspath(os.path.join(base_dir, group_folder, source_folder))
        else:
            download_dir = os.path.abspath(os.path.join(base_dir, platform))
        os.makedirs(download_dir, exist_ok=True)
        
        # Buscar título do vídeo
        video_title = await self._get_video_title(video_url)
        
        # Usar título se disponível, senão usar external_video_id
        if video_title:
            filename = self._sanitize_filename(video_title)
            output_path = os.path.abspath(os.path.join(download_dir, f"{filename}.mp4"))
            logger.info(f"Using video title as filename: {filename}")
        else:
            output_path = os.path.abspath(os.path.join(download_dir, f"{external_video_id}.mp4"))
            logger.warning(f"Could not get video title, using external_video_id: {external_video_id}")

        # Verificar se arquivo já existe e está completo
        # Verificar tanto pelo nome do título quanto pelo video_id (caso já tenha sido baixado antes)
        existing_path = None
        if os.path.exists(output_path) and os.path.getsize(output_path) > 1000:
            existing_path = output_path
        else:
            # Verificar se existe com o nome antigo (video_id)
            old_path = os.path.abspath(os.path.join(download_dir, f"{external_video_id}.mp4"))
            if os.path.exists(old_path) and os.path.getsize(old_path) > 1000:
                existing_path = old_path
        
        if existing_path:
            logger.info(f"File already exists: {existing_path} ({os.path.getsize(existing_path)} bytes)")
            return {"status": "completed", "path": existing_path}

        # Padrão: usa a URL recebida (ex.: https://www.youtube.com/shorts/ID). Fallback: watch?v=ID.
        try:
            logger.info(f"Downloading {external_video_id} with yt-dlp")
            result = await self._download_with_ytdlp_library(video_url, output_path, external_video_id)
            
            # Verificar se arquivo foi criado mesmo se status não for "completed"
            if os.path.exists(output_path) and os.path.getsize(output_path) > 1000:
                logger.info(f"Download completed - file created ({os.path.getsize(output_path)} bytes)")
                return {"status": "completed", "path": output_path}
            
            if result.get('status') == 'completed':
                logger.info("Download completed successfully")
                return result
            else:
                logger.error(f"Download failed: {result.get('error')}")
                return result
        except Exception as e:
            logger.error(f"Download exception: {e}")
            # Verificar se arquivo foi criado mesmo com exceção
            if os.path.exists(output_path) and os.path.getsize(output_path) > 1000:
                logger.info(f"File created despite exception ({os.path.getsize(output_path)} bytes)")
                return {"status": "completed", "path": output_path}
            return {"status": "failed", "error": f"Download failed: {str(e)}"}

    def _check_download_output(self, output_path: str) -> Optional[dict]:
        """Verifica se o download produziu um arquivo válido (> 1KB)."""
        if os.path.exists(output_path) and os.path.getsize(output_path) > 1000:
            return {"status": "completed", "path": output_path}
        base = output_path.replace(".mp4", "")
        for ext in [".mp4", ".webm", ".mkv", ".m4a"]:
            p = base + ext
            if os.path.exists(p) and os.path.getsize(p) > 1000:
                if ext != ".mp4":
                    os.rename(p, output_path)
                return {"status": "completed", "path": output_path}
        return None

    def _format18_opts(self, output_path_abs: str) -> dict:
        """Opts para formato 18, com cookies se disponível."""
        opts = {
            "format": "18",
            "outtmpl": output_path_abs.replace(".mp4", ".%(ext)s"),
            "noplaylist": True,
            "quiet": True,
            "no_warnings": True,
        }
        # Tentar usar cookies também no formato 18
        cookies_path = self._resolve_cookies_path()
        if cookies_path:
            opts["cookiefile"] = cookies_path
            logger.info("Format 18: Using cookies file: %s", cookies_path)
        # Adicionar opções para evitar detecção de bot
        if "youtube.com" in str(output_path_abs) or True:  # Sempre adicionar para YouTube
            opts["extractor_args"] = {"youtube": {"player_client": ["ios"]}}
        return opts

    def _base_opts(self, url: str, output_path_abs: str) -> dict:
        """Opts com cookies e extractor_args (merge/best)."""
        o = {
            "outtmpl": output_path_abs.replace(".mp4", ".%(ext)s"),
            "quiet": True,
            "no_warnings": True,
            "noplaylist": True,
        }
        if "youtube.com" in url:
            # Tentar diferentes clientes para evitar detecção
            o["extractor_args"] = {"youtube": {"player_client": ["ios", "android", "web"]}}
            # Adicionar referer para parecer mais legítimo
            o["referer"] = "https://www.youtube.com/"
        cookies_path = self._resolve_cookies_path()
        if cookies_path:
            o["cookiefile"] = cookies_path
            logger.info("Using cookies file: %s", cookies_path)
        else:
            logger.warning("No cookies file found - YouTube may block downloads")
        return o

    def _clean_partial_files(self, output_path: str) -> None:
        """Remove arquivos vazios ou parciais (<= 1KB) em output_path e base+ext."""
        base = output_path.replace(".mp4", "")
        candidates = [output_path] + [base + e for e in [".webm", ".mkv", ".m4a"]]
        for p in candidates:
            if not os.path.exists(p):
                continue
            try:
                if os.path.getsize(p) <= 1000:
                    os.remove(p)
            except OSError:
                pass

    async def _download_with_ytdlp_library(self, video_url: str, output_path: str, external_video_id: Optional[str] = None):
        """yt-dlp: 1) URL como recebida (ex. /shorts/ID); 2) fallback watch?v=ID; 3) format 18 (CLI-like) depois merge/best."""
        try:
            import yt_dlp
        except ImportError:
            return {"status": "failed", "error": "yt-dlp library not installed"}

        output_path_abs = os.path.abspath(output_path)
        logger.info("Download output_path (absolute): %s", output_path_abs)

        errors_collected = []
        
        def try_download(url: str) -> Optional[dict]:
            self._clean_partial_files(output_path_abs)
            # 1) YouTube: formato 18, opts mínimos (igual CLI: sem cookies, sem extractor_args)
            if "youtube.com" in url:
                try:
                    logger.info("Attempt: format 18 (no cookies, no extractor_args)")
                    opts = self._format18_opts(output_path_abs)
                    with yt_dlp.YoutubeDL(opts) as ydl:
                        ydl.download([url])
                    ok = self._check_download_output(output_path_abs)
                    if ok:
                        logger.info("Format 18: file found, size %s", os.path.getsize(output_path_abs))
                        return ok
                    error_msg = "Format 18: file not found or size <= 1KB"
                    logger.warning(error_msg)
                    errors_collected.append(error_msg)
                except Exception as e:
                    error_msg = f"yt-dlp format 18 failed: {str(e)}"
                    logger.warning(error_msg)
                    errors_collected.append(error_msg)
            # 2) bestvideo+bestaudio + merge (requer ffmpeg)
            self._clean_partial_files(output_path_abs)
            try:
                logger.info("Attempt: bestvideo+bestaudio + merge")
                opts = {**self._base_opts(url, output_path_abs), "format": "bestvideo+bestaudio/best", "merge_output_format": "mp4"}
                with yt_dlp.YoutubeDL(opts) as ydl:
                    ydl.download([url])
                ok = self._check_download_output(output_path_abs)
                if ok:
                    logger.info("Merge: file found, size %s", os.path.getsize(output_path_abs))
                    return ok
                error_msg = "Merge: file not found or size <= 1KB"
                logger.warning(error_msg)
                errors_collected.append(error_msg)
            except Exception as e:
                error_msg = f"yt-dlp merge failed: {str(e)}"
                logger.warning(error_msg)
                errors_collected.append(error_msg)
            # 3) best (formato único)
            self._clean_partial_files(output_path_abs)
            try:
                logger.info("Attempt: best")
                opts = {**self._base_opts(url, output_path_abs), "format": "best"}
                with yt_dlp.YoutubeDL(opts) as ydl:
                    ydl.download([url])
                ok = self._check_download_output(output_path_abs)
                if ok:
                    logger.info("Best: file found, size %s", os.path.getsize(output_path_abs))
                    return ok
                error_msg = "Best: file not found or size <= 1KB"
                logger.warning(error_msg)
                errors_collected.append(error_msg)
            except Exception as e:
                error_msg = f"yt-dlp best failed: {str(e)}"
                logger.warning(error_msg)
                errors_collected.append(error_msg)
            return None

        # 1) Padrão: URL como veio (ex. https://www.youtube.com/shorts/ID)
        logger.info("Trying URL (padrão): %s", video_url)
        ok = try_download(video_url)
        if ok:
            return ok

        # 2) Fallback: watch?v=ID (derivado do padrão)
        if external_video_id and "youtube.com" in video_url:
            alt = self._youtube_watch_url(external_video_id)
            logger.info("Trying URL (fallback): %s", alt)
            ok = try_download(alt)
            if ok:
                return ok

        # Coletar informações sobre arquivos criados (mesmo que pequenos)
        file_info = []
        base = output_path_abs.replace(".mp4", "")
        for ext in [".mp4", ".webm", ".mkv", ".m4a"]:
            p = base + ext
            if os.path.exists(p):
                size = os.path.getsize(p)
                file_info.append(f"{os.path.basename(p)}: {size} bytes")
        
        error_detail = "All download strategies failed"
        if errors_collected:
            error_detail += f". Errors: {'; '.join(errors_collected[:3])}"  # Limitar a 3 erros
        if file_info:
            error_detail += f". Files created: {', '.join(file_info)}"
        
        logger.error(f"Download failed for {external_video_id}: {error_detail}")
        return {"status": "failed", "error": error_detail}

