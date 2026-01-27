"""
Serviço de download usando Cobalt API como fallback
Cobalt é uma ferramenta open-source robusta que lida com bloqueios do YouTube/Instagram
"""
import os
import logging
import httpx
from typing import Optional
from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class CobaltDownloaderService:
    """Serviço para download usando Cobalt API"""
    
    def __init__(self):
        """Inicializa serviço stateless"""
        # URL da API do Cobalt (pode ser auto-hospedada ou pública)
        # Configure COBALT_API_URL no .env para sua instância do Cobalt
        # Exemplo: COBALT_API_URL=https://api.cobalt.tools
        # Ou deixe vazio para usar padrão (pode não estar disponível)
        settings = get_settings()
        self.api_url = settings.COBALT_API_URL or os.getenv("COBALT_API_URL", "https://api.cobalt.tools")
        self.timeout = 60.0  # Timeout para requisições
    
    async def download_video(
        self,
        video_url: str,
        output_path: str,
        external_video_id: Optional[str] = None
    ) -> dict:
        """
        Faz download usando Cobalt API
        Estratégia: Envia URL para Cobalt, recebe link de download, baixa arquivo
        """
        try:
            logger.info(f"Cobalt: Starting download fallback for {external_video_id or video_url}")
            
            # Passo 1: Solicitar informações do vídeo à API do Cobalt
            logger.info(f"Cobalt: Requesting video info from {self.api_url}")
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                # Tentar endpoint /api/json (formato mais comum)
                try:
                    response = await client.post(
                        f"{self.api_url}/api/json",
                        json={
                            "url": video_url,
                            "vCodec": "h264",  # Preferir h264 para compatibilidade
                            "vQuality": "max",  # Melhor qualidade disponível
                            "aFormat": "best",  # Melhor áudio disponível
                            "isAudioOnly": False,
                            "isNoTTWatermark": True,
                            "isTTFullAudio": False,
                        },
                        headers={
                            "Content-Type": "application/json",
                            "Accept": "application/json",
                        }
                    )
                    
                    if response.status_code != 200:
                        logger.warning(f"Cobalt: API returned status {response.status_code}")
                        # Tentar endpoint alternativo /api/parse
                        response = await client.post(
                            f"{self.api_url}/api/parse",
                            json={"url": video_url},
                            headers={"Content-Type": "application/json"}
                        )
                    
                    if response.status_code != 200:
                        error_text = response.text[:200]
                        logger.error(f"Cobalt: API error {response.status_code}: {error_text}")
                        return {
                            "status": "failed",
                            "error": f"Cobalt API returned status {response.status_code}: {error_text}"
                        }
                    
                    data = response.json()
                    
                except httpx.TimeoutException:
                    logger.error("Cobalt: Request timeout")
                    return {"status": "failed", "error": "Cobalt API request timeout"}
                except httpx.RequestError as e:
                    logger.error(f"Cobalt: Request error: {e}")
                    return {"status": "failed", "error": f"Cobalt API request failed: {str(e)}"}
                except Exception as e:
                    logger.error(f"Cobalt: Unexpected error: {e}")
                    return {"status": "failed", "error": f"Cobalt API error: {str(e)}"}
            
            # Passo 2: Processar resposta do Cobalt
            # Cobalt pode retornar diferentes formatos de resposta
            download_url = None
            
            if isinstance(data, dict):
                # Formato padrão: { "status": "success", "url": "...", ... }
                if data.get("status") == "success" or "url" in data:
                    download_url = data.get("url") or data.get("text")  # Algumas APIs usam "text"
                
                # Formato picker: múltiplas opções de qualidade
                elif "picker" in data or "formats" in data:
                    formats = data.get("picker") or data.get("formats", [])
                    if formats:
                        # Escolher melhor formato disponível
                        # Priorizar MP4, depois melhor qualidade
                        mp4_formats = [f for f in formats if f.get("format") == "mp4" or "mp4" in f.get("url", "")]
                        if mp4_formats:
                            # Ordenar por qualidade (se disponível)
                            mp4_formats.sort(key=lambda x: x.get("quality", 0), reverse=True)
                            download_url = mp4_formats[0].get("url")
                        else:
                            # Usar primeiro formato disponível
                            download_url = formats[0].get("url")
                
                # Verificar se há erro na resposta
                if data.get("status") == "error":
                    error_msg = data.get("text") or data.get("message") or "Unknown error"
                    logger.error(f"Cobalt: API returned error: {error_msg}")
                    return {"status": "failed", "error": f"Cobalt API error: {error_msg}"}
            
            if not download_url:
                logger.error(f"Cobalt: No download URL found in response: {data}")
                return {"status": "failed", "error": "Cobalt API did not return download URL"}
            
            logger.info(f"Cobalt: Got download URL, downloading file...")
            
            # Passo 3: Baixar arquivo do link fornecido pelo Cobalt
            output_path_abs = os.path.abspath(output_path)
            
            async with httpx.AsyncClient(timeout=300.0) as client:  # Timeout maior para download
                async with client.stream("GET", download_url) as response:
                    if response.status_code != 200:
                        logger.error(f"Cobalt: Download failed with status {response.status_code}")
                        return {"status": "failed", "error": f"Download failed: HTTP {response.status_code}"}
                    
                    # Criar diretório se não existir
                    os.makedirs(os.path.dirname(output_path_abs), exist_ok=True)
                    
                    # Baixar arquivo
                    total_size = 0
                    with open(output_path_abs, "wb") as f:
                        async for chunk in response.aiter_bytes():
                            f.write(chunk)
                            total_size += len(chunk)
                    
                    logger.info(f"Cobalt: Downloaded {total_size} bytes to {output_path_abs}")
            
            # Passo 4: Validar arquivo baixado
            if os.path.exists(output_path_abs) and os.path.getsize(output_path_abs) > 1000:
                logger.info(f"Cobalt: Download successful! File size: {os.path.getsize(output_path_abs)} bytes")
                return {"status": "completed", "path": output_path_abs}
            else:
                logger.error(f"Cobalt: Downloaded file is too small or doesn't exist")
                return {"status": "failed", "error": "Downloaded file is invalid or too small"}
            
        except Exception as e:
            logger.error(f"Cobalt: Download failed: {e}")
            import traceback
            logger.error(f"Cobalt: Traceback: {traceback.format_exc()}")
            return {"status": "failed", "error": f"Cobalt download failed: {str(e)}"}
