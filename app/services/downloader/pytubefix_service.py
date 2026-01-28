"""
Serviço de download usando pytubefix (alternativa ao yt-dlp)
pytubefix é mantido ativamente e pode contornar bloqueios do YouTube
"""
import os
import logging
import subprocess
from typing import Optional

logger = logging.getLogger(__name__)


class PytubefixDownloaderService:
    """Serviço para download usando pytubefix"""
    
    def __init__(self):
        """Inicializa serviço stateless"""
        pass
    
    def _download_sync(
        self,
        video_url: str,
        output_path: str,
        external_video_id: Optional[str] = None
    ) -> dict:
        """
        Faz download usando pytubefix (método síncrono)
        """
        try:
            logger.info(f"Pytubefix: Starting download for {external_video_id or video_url}")
            
            from pytubefix import YouTube
            from pytubefix.exceptions import VideoUnavailable, RegexMatchError
            
            output_path_abs = os.path.abspath(output_path)
            output_dir = os.path.dirname(output_path_abs)
            os.makedirs(output_dir, exist_ok=True)
            
            # Criar instância do YouTube
            yt = YouTube(video_url)
            
            # Obter stream de maior qualidade disponível
            try:
                stream = yt.streams.get_highest_resolution()
            except Exception as e:
                logger.warning(f"Pytubefix: Could not get highest resolution, trying progressive: {e}")
                # Tentar streams progressivos (vídeo+áudio juntos)
                streams = yt.streams.filter(progressive=True)
                if streams:
                    stream = streams.order_by('resolution').desc().first()
                else:
                    # Se não houver progressivo, pegar melhor vídeo e melhor áudio separadamente
                    video_stream = yt.streams.filter(only_video=True).order_by('resolution').desc().first()
                    audio_stream = yt.streams.filter(only_audio=True).order_by('abr').desc().first()
                    if video_stream and audio_stream:
                        # Baixar ambos e fazer merge
                        video_path = os.path.join(output_dir, f"{external_video_id}_video.{video_stream.subtype}")
                        audio_path = os.path.join(output_dir, f"{external_video_id}_audio.{audio_stream.subtype}")
                        
                        logger.info("Pytubefix: Downloading video and audio separately for merge")
                        video_stream.download(output_path=output_dir, filename=f"{external_video_id}_video.{video_stream.subtype}")
                        audio_stream.download(output_path=output_dir, filename=f"{external_video_id}_audio.{audio_stream.subtype}")
                        
                        # Fazer merge com ffmpeg
                        logger.info("Pytubefix: Merging video and audio with ffmpeg")
                        merge_cmd = [
                            "ffmpeg", "-y", "-i", video_path, "-i", audio_path,
                            "-c:v", "copy", "-c:a", "copy", output_path_abs
                        ]
                        result = subprocess.run(merge_cmd, capture_output=True, text=True, timeout=300)
                        
                        # Limpar arquivos temporários
                        try:
                            if os.path.exists(video_path):
                                os.remove(video_path)
                            if os.path.exists(audio_path):
                                os.remove(audio_path)
                        except:
                            pass
                        
                        if result.returncode == 0 and os.path.exists(output_path_abs) and os.path.getsize(output_path_abs) > 1000:
                            logger.info(f"Pytubefix: Download successful! File size: {os.path.getsize(output_path_abs)} bytes")
                            return {"status": "completed", "path": output_path_abs}
                        else:
                            return {"status": "failed", "error": f"Merge failed: {result.stderr}"}
                    else:
                        return {"status": "failed", "error": "No suitable streams found"}
            
            if not stream:
                return {"status": "failed", "error": "No streams available"}
            
            # Baixar stream
            logger.info(f"Pytubefix: Downloading stream: {stream.resolution} ({stream.subtype})")
            
            # Definir nome do arquivo temporário
            temp_filename = f"{external_video_id}.{stream.subtype}"
            temp_path = os.path.join(output_dir, temp_filename)
            
            # Baixar
            stream.download(output_path=output_dir, filename=temp_filename)
            
            # Se não for MP4, converter ou renomear
            if stream.subtype != "mp4":
                if os.path.exists(temp_path) and os.path.getsize(temp_path) > 1000:
                    # Tentar converter para MP4
                    logger.info(f"Pytubefix: Converting {stream.subtype} to MP4")
                    convert_cmd = [
                        "ffmpeg", "-y", "-i", temp_path, "-c", "copy", output_path_abs
                    ]
                    result = subprocess.run(convert_cmd, capture_output=True, text=True, timeout=300)
                    
                    # Remover arquivo temporário
                    try:
                        if os.path.exists(temp_path):
                            os.remove(temp_path)
                    except:
                        pass
                    
                    if result.returncode == 0 and os.path.exists(output_path_abs) and os.path.getsize(output_path_abs) > 1000:
                        logger.info(f"Pytubefix: Download successful! File size: {os.path.getsize(output_path_abs)} bytes")
                        return {"status": "completed", "path": output_path_abs}
                    else:
                        # Se conversão falhar, renomear mesmo assim
                        if os.path.exists(temp_path):
                            os.rename(temp_path, output_path_abs)
                            if os.path.getsize(output_path_abs) > 1000:
                                logger.info(f"Pytubefix: Download successful (renamed)! File size: {os.path.getsize(output_path_abs)} bytes")
                                return {"status": "completed", "path": output_path_abs}
            else:
                # Já é MP4, apenas renomear se necessário
                if temp_path != output_path_abs:
                    if os.path.exists(temp_path):
                        os.rename(temp_path, output_path_abs)
            
            # Validar arquivo final
            if os.path.exists(output_path_abs) and os.path.getsize(output_path_abs) > 1000:
                logger.info(f"Pytubefix: Download successful! File size: {os.path.getsize(output_path_abs)} bytes")
                return {"status": "completed", "path": output_path_abs}
            else:
                return {"status": "failed", "error": "Downloaded file is invalid or too small"}
                
        except VideoUnavailable:
            logger.error("Pytubefix: Video is unavailable")
            return {"status": "failed", "error": "Video is unavailable"}
        except RegexMatchError as e:
            logger.error(f"Pytubefix: Regex match error (YouTube may have changed): {e}")
            return {"status": "failed", "error": f"pytubefix error: {str(e)}"}
        except Exception as e:
            logger.error(f"Pytubefix: Download failed: {e}")
            import traceback
            logger.error(f"Pytubefix: Traceback: {traceback.format_exc()}")
            return {"status": "failed", "error": f"pytubefix download failed: {str(e)}"}
    
    async def download_video(
        self,
        video_url: str,
        output_path: str,
        external_video_id: Optional[str] = None
    ) -> dict:
        """
        Faz download usando pytubefix (executa método síncrono em thread separada)
        """
        import asyncio
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            self._download_sync,
            video_url,
            output_path,
            external_video_id
        )
