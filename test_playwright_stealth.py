#!/usr/bin/env python3
"""
Script de teste para visualizar o Playwright + Stealth funcionando
Baseado no código oficial do Manus que conseguiu acessar o Urlebird com sucesso
"""

import sys
import asyncio
import os

# Importar bibliotecas
try:
    from playwright.async_api import async_playwright
    from playwright_stealth.stealth import Stealth
    from bs4 import BeautifulSoup
    import re
except ImportError as e:
    print(f"❌ Erro ao importar bibliotecas: {e}")
    print("\nInstale as dependências:")
    print("pip install playwright playwright-stealth beautifulsoup4")
    print("playwright install chromium")
    sys.exit(1)

async def test_urlebird_playwright_stealth(username, headless=False):
    """Testa acesso ao Urlebird usando Playwright + Stealth (método do Manus)"""
    
    print(f"\n{'='*60}")
    print(f"🧪 TESTE PLAYWRIGHT + STEALTH - Urlebird")
    print(f"{'='*60}")
    print(f"Username: @{username}")
    print(f"Modo: {'Headless' if headless else 'VISÍVEL (você verá o navegador)'}")
    print(f"Método: Playwright + Stealth (baseado no código do Manus)")
    print(f"{'='*60}\n")
    
    browser = None
    try:
        url = f"https://urlebird.com/pt/user/{username}/"
        print(f"📌 URL: {url}\n")
        
        async with async_playwright() as p:
            print("🔧 Lançando navegador Chromium...")
            
            # Lançar navegador Chromium
            browser = await p.chromium.launch(headless=headless)
            print("✅ Navegador lançado!\n")
            
            # Criar contexto com configurações realistas (igual ao Manus)
            print("🔧 Criando contexto com configurações realistas...")
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
                viewport={'width': 1280, 'height': 720},
                locale="pt-BR",
                timezone_id="America/Sao_Paulo"
            )
            print("✅ Contexto criado!\n")
            
            page = await context.new_page()
            
            # APLICAR STEALTH (o segredo do bypass do Cloudflare)
            print("🛡️ Aplicando stealth (bypass Cloudflare)...")
            stealth = Stealth()
            await stealth.apply_stealth_async(page)
            print("✅ Stealth aplicado!\n")
            
            print(f"🌐 Navegando para: {url}")
            # Navegar até a URL com wait_until load
            await page.goto(url, wait_until="load", timeout=90000)
            print("✅ Página carregada!\n")
            
            # Aguardar resolução do desafio Cloudflare
            # Verificar se o título mudou de "Um momento…" para algo relacionado ao perfil
            print("⏳ Aguardando resolução de desafios Cloudflare...")
            max_wait = 60  # Máximo de 60 segundos
            start_time = asyncio.get_event_loop().time()
            
            while True:
                await asyncio.sleep(2)  # Verificar a cada 2 segundos
                page_title = await page.title()
                html = await page.content()
                elapsed = asyncio.get_event_loop().time() - start_time
                
                # Verificar se o desafio foi resolvido
                if ("um momento" not in page_title.lower() and 
                    "checking" not in page_title.lower() and
                    "challenge" not in html.lower() and
                    ("/video/" in html or "follower" in html.lower() or username.lower() in html.lower())):
                    print(f"✅ Desafio Cloudflare resolvido após {elapsed:.1f}s\n")
                    break
                
                # Verificar se foi bloqueado
                if "403" in html or "Forbidden" in html or "blocked" in html.lower():
                    print("❌ Página bloqueada (403 Forbidden)\n")
                    break
                
                # Timeout
                if elapsed >= max_wait:
                    print(f"⚠️ Timeout após {max_wait}s aguardando resolução do Cloudflare\n")
                    break
                
                print(f"   Aguardando... ({elapsed:.1f}s/{max_wait}s) - Título: {page_title[:50]}")
            
            # Obter HTML final
            html = await page.content()
            page_title = await page.title()
            
            print("📊 Verificando status da página...")
            print(f"   Título: {page_title}")
            print(f"   Tamanho HTML: {len(html)} caracteres\n")
            
            # Parsear HTML
            soup = BeautifulSoup(html, 'html.parser')
            
            # Verificar se foi bloqueado
            if "403" in html or "Forbidden" in html or "blocked" in html.lower():
                print("❌ PÁGINA BLOQUEADA (403 Forbidden)")
                print("   O Urlebird ainda está bloqueando o acesso\n")
                if not headless:
                    print("="*60)
                    print("👀 NAVEGADOR ABERTO - Verifique a página manualmente")
                    print("="*60)
                    try:
                        input("\nPressione ENTER para fechar o navegador...")
                    except EOFError:
                        pass
                await browser.close()
                return False
            
            # Procurar primeiro link de vídeo
            print("🔍 Procurando links de vídeo...")
            latest_video_element = soup.find('a', href=lambda href: href and '/video/' in href)
            
            if latest_video_element:
                urlebird_video_url = latest_video_element.get('href', '')
                
                # Garantir URL completa
                base_url = 'https://urlebird.com'
                if urlebird_video_url.startswith('/'):
                    urlebird_video_url = f"{base_url}{urlebird_video_url}"
                elif not urlebird_video_url.startswith('http'):
                    urlebird_video_url = f"{base_url}/{urlebird_video_url}"
                
                print(f"✅ Vídeo encontrado!")
                print(f"   URL Urlebird: {urlebird_video_url}\n")
                
                # Extrair ID do vídeo
                video_id_match = re.search(r'/video/[^/]+-(\d+)', urlebird_video_url)
                if video_id_match:
                    video_id = video_id_match.group(1)
                    tiktok_url = f"https://www.tiktok.com/@{username}/video/{video_id}"
                    print(f"✅ URL do TikTok extraída:")
                    print(f"   {tiktok_url}\n")
                else:
                    print("⚠️ Não foi possível extrair ID do vídeo\n")
                
                if not headless:
                    print("="*60)
                    print("👀 NAVEGADOR ABERTO - Você pode ver a página agora!")
                    print("   Feche o navegador quando terminar de visualizar")
                    print("="*60)
                    try:
                        input("\nPressione ENTER para fechar o navegador...")
                    except EOFError:
                        pass
                
                await browser.close()
                return True
            else:
                print("❌ Nenhum link de vídeo encontrado na página\n")
                if not headless:
                    print("="*60)
                    print("👀 NAVEGADOR ABERTO - Verifique a página manualmente")
                    print("="*60)
                    try:
                        input("\nPressione ENTER para fechar o navegador...")
                    except EOFError:
                        pass
                await browser.close()
                return False
            
    except Exception as e:
        print(f"❌ Erro: {str(e)}\n")
        import traceback
        traceback.print_exc()
        if browser:
            try:
                await browser.close()
            except:
                pass
        return False

def main():
    print("\n" + "="*60)
    print("🧪 TESTE PLAYWRIGHT + STEALTH - Urlebird")
    print("Método baseado no código oficial do Manus")
    print("="*60)
    
    # Perguntar username
    if len(sys.argv) > 1:
        username = sys.argv[1]
    else:
        username = input("\nDigite o username do TikTok (sem @): ").strip()
    
    if not username:
        print("❌ Username não fornecido!")
        sys.exit(1)
    
    # Perguntar modo
    if len(sys.argv) > 2:
        modo = sys.argv[2]
    else:
        print("\nEscolha o modo:")
        print("1. Visível (você verá o navegador abrir)")
        print("2. Headless (sem interface gráfica)")
        try:
            modo = input("Escolha (1 ou 2, padrão: 1): ").strip() or "1"
        except EOFError:
            modo = "1"
    
    headless = (modo == "2")
    
    # Executar teste
    sucesso = asyncio.run(test_urlebird_playwright_stealth(username, headless=headless))
    
    print("="*60)
    if sucesso:
        print("✅ TESTE CONCLUÍDO COM SUCESSO!")
    else:
        print("❌ TESTE FALHOU")
    print("="*60 + "\n")

if __name__ == '__main__':
    main()
