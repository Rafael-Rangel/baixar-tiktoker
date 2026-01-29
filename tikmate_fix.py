"""
Patch para corrigir o parsing do Tikmate
Tenta fazer parsing mais robusto do código JavaScript capturado pela regex
"""

import re
from ast import literal_eval
from typing import Optional, Tuple


def safe_literal_eval(match_str: str) -> Optional[Tuple]:
    """
    Tenta fazer parsing seguro de uma string que pode conter código JavaScript
    em vez de uma tupla Python válida.
    
    Args:
        match_str: String capturada pela regex (pode ser JS ou Python)
    
    Returns:
        Tupla Python válida ou None se não conseguir fazer parsing
    """
    if not match_str:
        return None
    
    # Tentar 1: Parsing direto (caso seja Python válido)
    try:
        return literal_eval(match_str)
    except (SyntaxError, ValueError):
        pass
    
    # Tentar 2: Extrair apenas strings entre aspas e reconstruir tupla
    try:
        # Encontrar todas as strings entre aspas
        strings = re.findall(r'"([^"]+)"', match_str)
        
        if len(strings) >= 5:
            # Reconstruir tupla Python válida com as primeiras 5 strings
            tuple_str = '(' + ', '.join([f'"{s}"' for s in strings[:5]]) + ')'
            return literal_eval(tuple_str)
    except (SyntaxError, ValueError, IndexError):
        pass
    
    # Tentar 3: Procurar por padrão mais específico de tupla Python
    try:
        # Padrão: ("string1", "string2", "string3", "string4", "string5")
        pattern = r'\("([^"]+)",\s*"([^"]+)",\s*"([^"]+)",\s*"([^"]+)",\s*"([^"]+)"\)'
        match = re.search(pattern, match_str)
        if match:
            tuple_str = f'("{match.group(1)}", "{match.group(2)}", "{match.group(3)}", "{match.group(4)}", "{match.group(5)}")'
            return literal_eval(tuple_str)
    except (SyntaxError, ValueError, AttributeError):
        pass
    
    # Tentar 4: Limpar código JavaScript e extrair apenas strings
    try:
        # Remover código JS comum
        cleaned = match_str
        # Remover padrões JS como: {class:t.cssClass,style:r}
        cleaned = re.sub(r'\{[^}]*\}', '', cleaned)
        # Remover código após vírgulas problemáticas
        cleaned = re.sub(r',[^"]*\)', ')', cleaned)
        
        # Tentar parsing novamente
        strings = re.findall(r'"([^"]+)"', cleaned)
        if len(strings) >= 5:
            tuple_str = '(' + ', '.join([f'"{s}"' for s in strings[:5]]) + ')'
            return literal_eval(tuple_str)
    except (SyntaxError, ValueError, IndexError):
        pass
    
    return None


def patch_tikmate_get_media(original_get_media):
    """
    Wrapper para o método get_media do Tikmate que tenta corrigir o parsing
    """
    def patched_get_media(self, url: str):
        from requests.models import InvalidURL
        from tiktok_downloader.decoder import decoder
        from tiktok_downloader.utils import Download
        
        # Chamar método original até a parte do parsing
        media = self.post(
            self.BASE_URL+'abc.php',
            data={'url': url, **dict(re.findall(
                'name="(token)" value="(.*?)"', self.get(
                    'https://tikmate.online/?lang=id').text))},
            headers={
                "origin": "https://tikmate.online",
                "referer": "https://tikmate.online/",
                "sec-ch-ua": '"Chromium";v="94",\
                    "Google Chrome";v="94", \
                    ";Not A Brand";v="99"',
                "sec-ch-ua-mobile": "?0",
                "sec-ch-ua-platform": "Linux",
                "sec-fetch-dest": "iframe",
                "sec-fetch-mode": "navigate",
                "sec-fetch-site": "same-origin",
                "sec-fetch-user": "?1",
                "upgrade-insecure-requests": "1",
                "user-agent": "Mozilla/5.0 (X11; Linux x86_64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/94.0.4606.81 Safari/537.36"
            }
        )
        
        if "'error_api_get'" in media.text:
            raise InvalidURL()
        
        # Tentar regex original
        tt = re.findall(r'\(\".*?,.*?,.*?,.*?,.*?.*?\)', media.text)
        
        if not tt:
            raise ValueError("Não foi possível encontrar dados no HTML")
        
        # Tentar parsing seguro
        parsed_tuple = safe_literal_eval(tt[0])
        
        if parsed_tuple is None:
            raise ValueError(f"Não foi possível fazer parsing do código capturado: {tt[0][:200]}")
        
        # Continuar com o resto do processo original
        from tiktok_downloader.tikmate import decodeJWT
        decode = decodeJWT(decoder(*parsed_tuple))
        
        return [
            Download(
                x['url'],
                self,
                type=(['video', 'music'][x['filename'].endswith('.mp3')])) 
            for x in decode
        ]
    
    return patched_get_media


def apply_tikmate_patch():
    """
    Aplica o patch ao Tikmate para usar parsing mais robusto
    """
    try:
        from tiktok_downloader import Tikmate
        
        # Substituir método get_media
        Tikmate.get_media = patch_tikmate_get_media(Tikmate.get_media)
        
        return True
    except Exception as e:
        print(f"Erro ao aplicar patch: {e}")
        return False
