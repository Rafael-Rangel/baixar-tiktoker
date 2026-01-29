#!/usr/bin/env python3
"""
Script de Setup de Sessão - Resolver Cloudflare Manualmente

Este script abre o navegador em modo VISÍVEL (não-headless) para que você possa
resolver o desafio do Cloudflare manualmente uma única vez. Após resolver, os
cookies (incluindo cf_clearance) serão salvos para uso automático posterior.

Baseado nas recomendações do Manus:
"Use uma ferramenta como o Playwright com interface gráfica para abrir o site
uma única vez. Resolva o Desafio: Você mesmo clica no 'Verify you are human'.
Salve o Estado: Use context.storage_state(path='state.json')"

Uso:
    python setup_session.py
    # Ou especificar username:
    python setup_session.py oprimorico
"""

import sys
import asyncio
import os
import json
from pathlib import Path

try:
    from playwright.async_api import async_playwright
    from playwright_stealth.stealth import Stealth
except ImportError as e:
    print(f"❌ Erro ao importar bibliotecas: {e}")
    print("\nInstale as dependências:")
    print("pip install playwright playwright-stealth")
    print("playwright install chromium")
    sys.exit(1)

async def setup_session(username="oprimorico"):
    """Abre navegador visível para resolver Cloudflare manualmente"""
    
    print("\n" + "="*70)
    print("🔧 SETUP DE SESSÃO - Resolver Cloudflare Manualmente")
    print("="*70)
    print(f"\nUsername: @{username}")
    print("URL: https://urlebird.com/pt/user/{username}/")
    print("\n📋 INSTRUÇÕES:")
    print("1. O navegador abrirá em modo VISÍVEL")
    print("2. Resolva o desafio do Cloudflare manualmente (clique em 'Verify you are human')")
    print("3. Aguarde a página carregar completamente")
    print("4. Pressione ENTER aqui no terminal quando terminar")
    print("5. Os cookies serão salvos automaticamente")
    print("="*70 + "\n")
    
    # Criar diretório para salvar estado
    context_storage_path = Path('.playwright_context')
    context_storage_path.mkdir(exist_ok=True)
    storage_file = context_storage_path / 'urlebird_storage.json'
    
    async with async_playwright() as p:
        print("🌐 Lançando navegador Chromium (MODO VISÍVEL)...")
        
        # Lançar em modo VISÍVEL (headless=False) para resolução manual
        browser = await p.chromium.launch(
            headless=False,  # VISÍVEL para você resolver manualmente
            args=[
                '--disable-blink-features=AutomationControlled',
                '--use-gl=egl',  # Emular GPU para WebGL
                '--enable-webgl',
                '--enable-accelerated-2d-canvas'
            ]
        )
        
        print("✅ Navegador aberto!\n")
        
        # User-Agent sincronizado com Linux (VPS)
        user_agent = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
        
        context = await browser.new_context(
            user_agent=user_agent,
            viewport={'width': 1920, 'height': 1080},
            locale="pt-BR",
            timezone_id="America/Sao_Paulo",
            permissions=["geolocation"],
            geolocation={"latitude": -23.5505, "longitude": -46.6333},
            color_scheme="light"
        )
        
        page = await context.new_page()
        
        # Aplicar stealth
        print("🛡️ Aplicando stealth...")
        stealth = Stealth()
        await stealth.apply_stealth_async(page)
        
        # Remover propriedades de automação
        await page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
            Object.defineProperty(navigator, 'languages', {
                get: () => ['pt-BR', 'pt', 'en-US', 'en']
            });
        """)
        
        url = f"https://urlebird.com/pt/user/{username}/"
        print(f"🌐 Navegando para: {url}\n")
        
        await page.goto(url, wait_until="load", timeout=60000)
        
        print("="*70)
        print("👀 NAVEGADOR ABERTO - RESOLVA O DESAFIO DO CLOUDFLARE AGORA")
        print("="*70)
        print("\n1. Veja a página no navegador que abriu")
        print("2. Se aparecer 'Verify you are human', clique no checkbox")
        print("3. Aguarde a página carregar completamente (deve mostrar o perfil)")
        print("4. Quando a página estiver carregada, volte aqui e pressione ENTER")
        print("\n" + "="*70 + "\n")
        
        # Aguardar usuário resolver manualmente
        try:
            input("Pressione ENTER quando tiver resolvido o desafio e a página estiver carregada...")
        except EOFError:
            print("\n⚠️ Entrada não disponível. Aguardando 30 segundos...")
            await asyncio.sleep(30)
        
        # Verificar se página carregou
        page_title = await page.title()
        html = await page.content()
        
        print(f"\n📊 Verificando status...")
        print(f"   Título: {page_title}")
        print(f"   HTML contém '/video/': {'/video/' in html}")
        
        if "/video/" in html or username.lower() in html.lower():
            print("✅ Página carregada com sucesso!\n")
            
            # Salvar estado (cookies incluindo cf_clearance)
            print("💾 Salvando cookies e estado da sessão...")
            storage_state = await context.storage_state()
            
            with open(storage_file, 'w') as f:
                json.dump(storage_state, f, indent=2)
            
            print(f"✅ Estado salvo em: {storage_file}\n")
            
            # Verificar se cf_clearance foi salvo
            cookies = storage_state.get('cookies', [])
            cf_clearance = [c for c in cookies if c.get('name') == 'cf_clearance']
            
            if cf_clearance:
                print("🎉 Cookie cf_clearance encontrado e salvo!")
                print(f"   Valor: {cf_clearance[0].get('value', '')[:50]}...")
            else:
                print("⚠️ Cookie cf_clearance não encontrado. O desafio pode não ter sido resolvido completamente.")
            
            print("\n✅ Setup concluído! Agora você pode usar o código automático.")
            print("   Os cookies serão carregados automaticamente na próxima execução.\n")
            
        else:
            print("⚠️ A página pode não ter carregado completamente.")
            print("   Título atual: " + page_title)
            print("   Você pode tentar novamente executando este script.\n")
        
        print("🔒 Fechando navegador...")
        await browser.close()
        print("✅ Concluído!\n")

def main():
    username = sys.argv[1] if len(sys.argv) > 1 else "oprimorico"
    asyncio.run(setup_session(username))

if __name__ == '__main__':
    main()
