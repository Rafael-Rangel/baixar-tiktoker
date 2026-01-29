#!/usr/bin/env python3
"""
Script de teste para testar as alternativas ao Urlebird
"""

import sys
import os
import re
import requests
import time
import logging
import json

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# Importar BeautifulSoup
try:
    from bs4 import BeautifulSoup
    BEAUTIFULSOUP_AVAILABLE = True
except ImportError:
    logger.error("BeautifulSoup4 não está instalado")
    BEAUTIFULSOUP_AVAILABLE = False
    BeautifulSoup = None

def validate_username(username):
    """Valida e limpa username"""
    if not username:
        return None
    username = username.strip().lstrip('@')
    if not username or len(username) < 1:
        return None
    return username

def test_rapidapi(username):
    """Testa RapidAPI TikTok Scraper"""
    print("\n" + "="*60)
    print("TESTE 1: RapidAPI TikTok Scraper")
    print("="*60)
    
    try:
        username = validate_username(username)
        api_url = "https://tiktok-scraper7.p.rapidapi.com/user/posts"
        
        params = {'unique_id': username, 'count': 1}
        
        headers = {
            'x-rapidapi-host': 'tiktok-scraper7.p.rapidapi.com',
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36',
            'Accept': 'application/json',
        }
        
        # Tentar com chave de API se disponível
        rapidapi_key = os.getenv('RAPIDAPI_KEY', None)
        if rapidapi_key:
            headers['x-rapidapi-key'] = rapidapi_key
            print("Usando chave RapidAPI fornecida")
        else:
            print("⚠️ Nenhuma chave RapidAPI encontrada (testando sem chave)")
        
        print(f"Enviando requisição para: {api_url}")
        response = requests.get(api_url, params=params, headers=headers, timeout=15)
        
        print(f"Status HTTP: {response.status_code}")
        
        if response.status_code == 200:
            try:
                data = response.json()
                print(f"Resposta JSON: {json.dumps(data, indent=2)[:1000]}")
                
                # Verificar estrutura da resposta
                videos = None
                if 'data' in data and 'videos' in data['data']:
                    videos = data['data']['videos']
                elif 'videos' in data:
                    videos = data['videos']
                elif isinstance(data, list) and len(data) > 0:
                    videos = data
                
                if videos and len(videos) > 0:
                    latest_video = videos[0]
                    video_id = latest_video.get('video_id') or latest_video.get('id') or latest_video.get('aweme_id', '')
                    
                    if not video_id and 'url' in latest_video:
                        import re
                        url_match = re.search(r'/video/(\d+)', latest_video['url'])
                        if url_match:
                            video_id = url_match.group(1)
                    
                    if video_id:
                        tiktok_url = f"https://www.tiktok.com/@{username}/video/{video_id}"
                        print(f"✅ SUCESSO! URL encontrada: {tiktok_url}")
                        return True, tiktok_url
                    else:
                        print("❌ Não foi possível extrair ID do vídeo")
                        return False, None
                else:
                    print("❌ Nenhum vídeo encontrado")
                    return False, None
            except Exception as e:
                print(f"❌ Erro ao processar JSON: {e}")
                print(f"Resposta: {response.text[:500]}")
                return False, None
        elif response.status_code == 401:
            print("❌ Erro 401: Chave de API inválida ou não fornecida")
            print("   Para usar RapidAPI, você precisa:")
            print("   1. Criar conta em https://rapidapi.com")
            print("   2. Assinar a API 'TikTok Scraper'")
            print("   3. Obter sua chave de API")
            print("   4. Definir variável de ambiente: export RAPIDAPI_KEY=sua_chave")
            return False, None
        else:
            print(f"❌ Erro HTTP {response.status_code}")
            print(f"Resposta: {response.text[:500]}")
            return False, None
            
    except Exception as e:
        print(f"❌ Erro: {e}")
        import traceback
        traceback.print_exc()
        return False, None

def test_tikwm_api(username):
    """Testa TikWM API"""
    print("\n" + "="*60)
    print("TESTE 1: TikWM API")
    print("="*60)
    
    try:
        username = validate_username(username)
        api_url = "https://www.tikwm.com/api/user/posts"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
            'Accept': 'application/json',
            'Content-Type': 'application/json',
        }
        
        payload = {'unique_id': username, 'count': 1}
        
        print(f"Enviando requisição para: {api_url}")
        response = requests.post(api_url, json=payload, headers=headers, timeout=15)
        
        print(f"Status HTTP: {response.status_code}")
        
        if response.status_code == 200:
            try:
                data = response.json()
                print(f"Resposta JSON: {data}")
                
                if data.get('code') == 0 and 'data' in data and 'videos' in data['data']:
                    videos = data['data']['videos']
                    if videos and len(videos) > 0:
                        latest_video = videos[0]
                        video_id = latest_video.get('video_id', '')
                        tiktok_url = f"https://www.tiktok.com/@{username}/video/{video_id}"
                        print(f"✅ SUCESSO! URL encontrada: {tiktok_url}")
                        return True, tiktok_url
                    else:
                        print("❌ Nenhum vídeo encontrado")
                        return False, None
                else:
                    print(f"❌ Erro na resposta: {data.get('msg', 'Erro desconhecido')}")
                    return False, None
            except Exception as e:
                print(f"❌ Erro ao processar JSON: {e}")
                print(f"Resposta: {response.text[:500]}")
                return False, None
        else:
            print(f"❌ Erro HTTP {response.status_code}")
            print(f"Resposta: {response.text[:500]}")
            return False, None
            
    except Exception as e:
        print(f"❌ Erro: {e}")
        return False, None

def test_countik(username):
    """Testa Countik"""
    print("\n" + "="*60)
    print("TESTE 2: Countik")
    print("="*60)
    
    if not BEAUTIFULSOUP_AVAILABLE:
        print("❌ BeautifulSoup4 não está instalado")
        return False, None
    
    try:
        username = validate_username(username)
        url = f"https://countik.com/user/{username}"
        
        session = requests.Session()
        headers = {
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
            'Referer': 'https://www.google.com/',
        }
        session.headers.update(headers)
        
        print(f"Acessando página inicial...")
        session.get('https://countik.com/', timeout=10)
        time.sleep(1)
        
        print(f"Acessando perfil: {url}")
        response = session.get(url, timeout=15)
        
        print(f"Status HTTP: {response.status_code}")
        print(f"Tamanho HTML: {len(response.text)}")
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            latest_video_element = soup.find('a', href=lambda href: href and '/video/' in href)
            
            if latest_video_element:
                countik_video_url = latest_video_element.get('href', '')
                if countik_video_url.startswith('/'):
                    countik_video_url = f"https://countik.com{countik_video_url}"
                
                video_id_match = re.search(r'/video/[^/]+-(\d+)', countik_video_url)
                if video_id_match:
                    video_id = video_id_match.group(1)
                    tiktok_url = f"https://www.tiktok.com/@{username}/video/{video_id}"
                    print(f"✅ SUCESSO! URL encontrada: {tiktok_url}")
                    return True, tiktok_url
                else:
                    print(f"⚠️ Link encontrado mas não foi possível extrair ID: {countik_video_url}")
                    return False, None
            else:
                print("❌ Nenhum link de vídeo encontrado")
                return False, None
        else:
            print(f"❌ Erro HTTP {response.status_code}")
            return False, None
            
    except Exception as e:
        print(f"❌ Erro: {e}")
        import traceback
        traceback.print_exc()
        return False, None

if __name__ == '__main__':
    username = sys.argv[1] if len(sys.argv) > 1 else 'oprimorico'
    
    print("\n" + "="*60)
    print(f"TESTANDO ALTERNATIVAS PARA @{username}")
    print("="*60)
    
    # Testar RapidAPI primeiro
    success_rapidapi, url_rapidapi = test_rapidapi(username)
    
    # Testar TikWM
    success_tikwm, url_tikwm = test_tikwm_api(username)
    
    # Testar Countik
    success_countik, url_countik = test_countik(username)
    
    # Resumo
    print("\n" + "="*60)
    print("RESUMO DOS TESTES")
    print("="*60)
    print(f"RapidAPI TikTok Scraper: {'✅ FUNCIONOU' if success_rapidapi else '❌ FALHOU'}")
    if success_rapidapi:
        print(f"  URL: {url_rapidapi}")
    print(f"TikWM API: {'✅ FUNCIONOU' if success_tikwm else '❌ FALHOU'}")
    if success_tikwm:
        print(f"  URL: {url_tikwm}")
    print(f"Countik: {'✅ FUNCIONOU' if success_countik else '❌ FALHOU'}")
    if success_countik:
        print(f"  URL: {url_countik}")
    
    if success_rapidapi or success_tikwm or success_countik:
        print("\n✅ PELO MENOS UMA ALTERNATIVA FUNCIONOU!")
    else:
        print("\n❌ NENHUMA ALTERNATIVA FUNCIONOU")
        if not success_rapidapi:
            print("   💡 RapidAPI precisa de chave de API (veja RAPIDAPI_SETUP.md)")
