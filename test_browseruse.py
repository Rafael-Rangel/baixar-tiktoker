#!/usr/bin/env python3
"""
Script de teste para visualizar o Browser Use funcionando
Abre o navegador visível para você ver o processo
"""

import sys
import asyncio
import os

# Importar bibliotecas
try:
    from browser_use import Agent, Browser, ChatBrowserUse
    from bs4 import BeautifulSoup
    import re
except ImportError as e:
    print(f"❌ Erro ao importar bibliotecas: {e}")
    print("\nInstale as dependências:")
    print("pip install browser-use beautifulsoup4")
    sys.exit(1)

async def test_urlebird_browseruse(username, headless=False, use_cloud=False):
    """Testa acesso ao Urlebird usando Browser Use"""
    
    print(f"\n{'='*60}")
    print(f"🧪 TESTE BROWSER USE - Urlebird")
    print(f"{'='*60}")
    print(f"Username: @{username}")
    print(f"Modo: {'Headless' if headless else 'VISÍVEL (você verá o navegador)'}")
    print(f"Cloud: {'Sim' if use_cloud else 'Não (modo local)'}")
    print(f"{'='*60}\n")
    
    browser = None
    try:
        url = f"https://urlebird.com/pt/user/{username}/"
        print(f"📌 URL: {url}\n")
        
        # Verificar se tem API key para cloud
        browser_use_api_key = os.getenv('BROWSER_USE_API_KEY', None)
        if use_cloud and not browser_use_api_key:
            print("⚠️ Cloud mode requer BROWSER_USE_API_KEY")
            print("   Continuando em modo local...\n")
            use_cloud = False
        
        print("🔧 Criando Browser Use...")
        
        # Criar Browser instance
        browser = Browser(
            use_cloud=use_cloud,
            headless=headless
        )
        print("✅ Browser criado!\n")
        
        # Se tiver API key, usar Agent com LLM
        if browser_use_api_key and use_cloud:
            print("🤖 Usando Agent com LLM (modo cloud)...")
            llm = ChatBrowserUse()
            
            task = f"Navigate to {url}, wait for Cloudflare challenges to resolve, and extract the HTML content. Find the first video link on the page."
            
            agent = Agent(
                task=task,
                llm=llm,
                browser=browser,
            )
            
            print("🚀 Executando Agent...")
            history = await agent.run()
            print("✅ Agent concluído!\n")
            
            # Tentar obter HTML do browser
            try:
                if hasattr(browser, 'page'):
                    html = await browser.page.content()
                else:
                    html = str(history) if history else None
            except:
                html = str(history) if history else None
        else:
            # Modo local - usar Playwright diretamente
            print("🌐 Usando Playwright diretamente (modo local)...")
            from playwright.async_api import async_playwright
            
            playwright = await async_playwright().start()
            browser_instance = await playwright.chromium.launch(headless=headless)
            page = await browser_instance.new_page()
            
            print(f"🌐 Navegando para: {url}")
            await page.goto(url, wait_until='networkidle', timeout=60000)
            print("✅ Página carregada!\n")
            
            # Aguardar resolução de desafios Cloudflare
            print("⏳ Aguardando resolução de desafios Cloudflare...")
            import time
            max_wait = 60
            start_time = time.time()
            
            while time.time() - start_time < max_wait:
                content = await page.content()
                page_title = await page.title()
                
                if ('challenge' in content.lower() or 
                    'checking your browser' in content.lower() or 
                    'just a moment' in content.lower() or
                    'um momento' in page_title.lower()):
                    elapsed = int(time.time() - start_time)
                    print(f"   🔄 Desafio Cloudflare detectado, aguardando... ({elapsed}s/{max_wait}s)")
                    await page.wait_for_timeout(2000)
                    continue
                
                if '/video/' in content or 'follower' in content.lower():
                    elapsed = int(time.time() - start_time)
                    print(f"✅ Página carregada e desafio resolvido! ({elapsed}s)\n")
                    break
                
                await page.wait_for_timeout(1000)
            
            html = await page.content()
            await browser_instance.close()
            await playwright.stop()
        
        # Verificar status
        print("📊 Verificando status da página...")
        soup = BeautifulSoup(html, 'html.parser')
        page_title = soup.title.string if soup.title else "N/A"
        print(f"   Título: {page_title}")
        print(f"   Tamanho HTML: {len(html)} caracteres\n")
        
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
            return False
            
    except Exception as e:
        print(f"❌ Erro: {str(e)}\n")
        import traceback
        traceback.print_exc()
        return False
    finally:
        if browser:
            print("🔒 Fechando browser...")
            try:
                await browser.close()
                print("✅ Browser fechado!\n")
            except:
                pass

def main():
    print("\n" + "="*60)
    print("🧪 TESTE BROWSER USE - Urlebird")
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
    
    # Verificar se quer usar cloud
    use_cloud = os.getenv('BROWSER_USE_API_KEY') is not None
    
    # Executar teste
    sucesso = asyncio.run(test_urlebird_browseruse(username, headless=headless, use_cloud=use_cloud))
    
    print("="*60)
    if sucesso:
        print("✅ TESTE CONCLUÍDO COM SUCESSO!")
    else:
        print("❌ TESTE FALHOU")
    print("="*60 + "\n")

if __name__ == '__main__':
    main()
