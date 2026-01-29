#!/usr/bin/env python3
"""
Script de teste para visualizar o Selenium funcionando
Abre o navegador visível para você ver o processo
"""

import sys
import time

# Importar bibliotecas
try:
    import undetected_chromedriver as uc
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.common.exceptions import TimeoutException
    from bs4 import BeautifulSoup
    import re
except ImportError as e:
    print(f"❌ Erro ao importar bibliotecas: {e}")
    print("\nInstale as dependências:")
    print("pip install selenium undetected-chromedriver beautifulsoup4")
    sys.exit(1)

def test_urlebird_selenium(username, headless=False):
    """Testa acesso ao Urlebird usando Selenium"""
    
    print(f"\n{'='*60}")
    print(f"🧪 TESTE SELENIUM - Urlebird")
    print(f"{'='*60}")
    print(f"Username: @{username}")
    print(f"Modo: {'Headless' if headless else 'VISÍVEL (você verá o navegador)'}")
    print(f"{'='*60}\n")
    
    driver = None
    try:
        url = f"https://urlebird.com/pt/user/{username}/"
        print(f"📌 URL: {url}\n")
        
        # Configurar Chrome com opções anti-detecção
        options = uc.ChromeOptions()
        
        if headless:
            options.add_argument('--headless=new')
        else:
            print("🌐 Abrindo navegador... (aguarde alguns segundos)")
        
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_argument('--disable-extensions')
        options.add_argument('--window-size=1920,1080')
        options.add_argument('--start-maximized')
        options.add_argument('--lang=pt-BR')
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        
        # User-Agent realista
        options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        
        print("🔧 Criando driver Chrome...")
        driver = uc.Chrome(options=options, version_main=None, use_subprocess=True)
        
        print("✅ Driver criado com sucesso!\n")
        
        # Executar script para remover webdriver property
        print("🛡️ Aplicando proteções anti-detecção...")
        driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
            'source': '''
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
                window.navigator.chrome = {
                    runtime: {}
                };
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5]
                });
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['pt-BR', 'pt', 'en-US', 'en']
                });
            '''
        })
        print("✅ Proteções aplicadas!\n")
        
        # Acessar página
        print(f"🌐 Acessando página: {url}")
        driver.get(url)
        print("✅ Página carregada!\n")
        
        # Aguardar carregamento
        print("⏳ Aguardando conteúdo carregar...")
        try:
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            time.sleep(3)  # Aguardar JavaScript carregar
            print("✅ Conteúdo carregado!\n")
        except TimeoutException:
            print("❌ Timeout ao carregar página")
            return False
        
        # Verificar status
        print("📊 Verificando status da página...")
        current_url = driver.current_url
        page_title = driver.title
        print(f"   URL atual: {current_url}")
        print(f"   Título: {page_title}\n")
        
        # Verificar se foi bloqueado
        page_source = driver.page_source
        if "403" in page_source or "Forbidden" in page_source or "blocked" in page_source.lower():
            print("❌ PÁGINA BLOQUEADA (403 Forbidden)")
            print("   O Urlebird ainda está bloqueando o acesso\n")
            return False
        
        # Obter HTML da página
        print("📄 Extraindo HTML da página...")
        html = driver.page_source
        soup = BeautifulSoup(html, 'html.parser')
        print(f"   Tamanho do HTML: {len(html)} caracteres\n")
        
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
                input("\nPressione ENTER para fechar o navegador...")
            
            return True
        else:
            print("❌ Nenhum link de vídeo encontrado na página\n")
            if not headless:
                print("="*60)
                print("👀 NAVEGADOR ABERTO - Verifique a página manualmente")
                print("="*60)
                input("\nPressione ENTER para fechar o navegador...")
            return False
            
    except Exception as e:
        print(f"❌ Erro: {str(e)}\n")
        import traceback
        traceback.print_exc()
        return False
    finally:
        if driver:
            print("🔒 Fechando navegador...")
            try:
                driver.quit()
                print("✅ Navegador fechado!\n")
            except:
                pass

if __name__ == '__main__':
    print("\n" + "="*60)
    print("🧪 TESTE SELENIUM - Urlebird")
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
            modo = "1"  # Padrão se não houver input
    
    headless = (modo == "2")
    
    # Executar teste
    sucesso = test_urlebird_selenium(username, headless=headless)
    
    print("="*60)
    if sucesso:
        print("✅ TESTE CONCLUÍDO COM SUCESSO!")
    else:
        print("❌ TESTE FALHOU")
    print("="*60 + "\n")
