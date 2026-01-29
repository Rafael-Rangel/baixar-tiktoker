#!/usr/bin/env python3
"""
Script de teste para visualizar o Selenium funcionando
Abre o navegador visível para você ver o processo
"""

import sys
import time
import os
import shutil

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
        
        # Configurar Chrome com opções anti-detecção (simplificado - deixar undetected-chromedriver gerenciar)
        options = uc.ChromeOptions()
        
        if headless:
            options.add_argument('--headless=new')
        else:
            print("🌐 Abrindo navegador... (aguarde alguns segundos)")
        
        # Apenas argumentos essenciais
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--window-size=1920,1080')
        options.add_argument('--lang=pt-BR')
        
        # User-Agent mais recente e consistente
        options.add_argument('user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36')
        
        # NÃO adicionar excludeSwitches - causa erro
        # NÃO adicionar --disable-blink-features=AutomationControlled - undetected-chromedriver gerencia
        # NÃO adicionar useAutomationExtension - pode interferir
        
        print("🔧 Criando driver Chrome...")
        # Tentar encontrar Chrome automaticamente
        chrome_paths = [
            '/usr/bin/google-chrome',
            '/usr/bin/google-chrome-stable',
            '/usr/bin/chromium',
            '/usr/bin/chromium-browser',
            '/snap/bin/chromium',
            '/snap/chromium/current/usr/lib/chromium-browser/chrome',
            shutil.which('google-chrome'),
            shutil.which('google-chrome-stable'),
            shutil.which('chromium'),
            shutil.which('chromium-browser')
        ]
        
        chrome_binary = None
        for path in chrome_paths:
            if path and os.path.exists(path):
                chrome_binary = path
                print(f"   ✓ Chrome encontrado em: {chrome_binary}")
                options.binary_location = chrome_binary
                break
        
        if not chrome_binary:
            print("   ⚠ Chrome não encontrado, undetected-chromedriver tentará auto-detectar...")
        
        # Criar driver - especificar versão do Chrome para baixar ChromeDriver compatível
        try:
            # Detectar versão do Chrome instalado
            import subprocess
            try:
                chrome_version_output = subprocess.check_output(['google-chrome', '--version'], stderr=subprocess.STDOUT).decode()
                chrome_version = int(chrome_version_output.split()[2].split('.')[0])
                print(f"   Chrome versão detectada: {chrome_version}")
            except:
                chrome_version = 144  # Fallback para versão comum
                print(f"   Usando versão padrão: {chrome_version}")
            
            # Especificar versão para undetected-chromedriver baixar ChromeDriver correto
            print(f"   Baixando ChromeDriver compatível com Chrome {chrome_version}...")
            driver = uc.Chrome(options=options, use_subprocess=True, version_main=chrome_version)
        except Exception as e:
            print(f"   ⚠ Erro com opções: {e}")
            print("   Tentando método mais simples (sem opções extras)...")
            try:
                # Tentar sem opções extras - apenas essenciais
                simple_options = uc.ChromeOptions()
                simple_options.add_argument('--no-sandbox')
                simple_options.add_argument('--disable-dev-shm-usage')
                if not headless:
                    simple_options.add_argument('--window-size=1920,1080')
                driver = uc.Chrome(options=simple_options, use_subprocess=True, version_main=chrome_version)
            except Exception as e2:
                print(f"   ⚠ Erro método simples: {e2}")
                print("   Tentando método mínimo...")
                # Última tentativa - mínimo possível
                driver = uc.Chrome(use_subprocess=True, version_main=chrome_version)
        
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
        
        # Carregar cookies se disponível (para bypass Cloudflare)
        cookies_file = './cookies.txt'
        if os.path.exists(cookies_file):
            print("🍪 Carregando cookies para bypass Cloudflare...")
            driver.get('https://urlebird.com/')
            time.sleep(2)
            
            cookies_loaded = 0
            with open(cookies_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    parts = line.split('\t')
                    if len(parts) >= 7:
                        try:
                            cookie_domain = parts[0]
                            cookie_path = parts[2]
                            cookie_secure = parts[3] == 'TRUE'
                            cookie_name = parts[5]
                            cookie_value = parts[6]
                            if 'urlebird.com' in cookie_domain:
                                driver.add_cookie({
                                    'name': cookie_name,
                                    'value': cookie_value,
                                    'domain': cookie_domain,
                                    'path': cookie_path,
                                    'secure': cookie_secure
                                })
                                cookies_loaded += 1
                        except:
                            continue
            
            if cookies_loaded > 0:
                print(f"   ✓ {cookies_loaded} cookie(s) carregado(s)")
                driver.refresh()
                time.sleep(2)
            else:
                print("   ⚠ Nenhum cookie válido encontrado\n")
        else:
            print("⚠️ Arquivo cookies.txt não encontrado (continuando sem cookies)\n")
        
        # Acessar página principal
        print(f"🌐 Acessando página: {url}")
        driver.get(url)
        print("✅ Requisição enviada!\n")
        
        # Aguardar resolução de desafios Cloudflare e carregamento completo
        print("⏳ Aguardando resolução de desafios Cloudflare e carregamento...")
        max_wait = 60  # Máximo 60 segundos para resolver desafio (Cloudflare pode demorar)
        start_time = time.time()
        challenge_resolved = False
        last_title = ""
        
        while time.time() - start_time < max_wait:
            try:
                WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.TAG_NAME, "body"))
                )
                
                page_source_lower = driver.page_source.lower()
                page_title = driver.title
                page_title_lower = page_title.lower()
                
                # Verificar se título mudou (indica que desafio foi resolvido)
                if page_title != last_title:
                    print(f"   📄 Título mudou: '{page_title}'")
                    last_title = page_title
                
                # Verificar se ainda está em página de desafio
                is_challenge = (
                    'challenge' in page_source_lower or 
                    'checking your browser' in page_source_lower or 
                    'just a moment' in page_source_lower or
                    'um momento' in page_title_lower or
                    'please wait' in page_title_lower or
                    'ray id' in page_source_lower or  # Cloudflare sempre tem ray id
                    'cf-browser-verification' in page_source_lower
                )
                
                if is_challenge:
                    elapsed = int(time.time() - start_time)
                    print(f"   🔄 Desafio Cloudflare detectado, aguardando resolução... ({elapsed}s/{max_wait}s)")
                    
                    # Tentar interagir com a página para ajudar na resolução
                    try:
                        # Scroll para baixo e para cima (simula comportamento humano)
                        driver.execute_script("window.scrollTo(0, 100);")
                        time.sleep(0.5)
                        driver.execute_script("window.scrollTo(0, 0);")
                        
                        # Tentar mover mouse (simula comportamento humano)
                        from selenium.webdriver.common.action_chains import ActionChains
                        actions = ActionChains(driver)
                        actions.move_by_offset(100, 100).perform()
                        time.sleep(0.5)
                    except:
                        pass
                    
                    # Aguardar um pouco mais para desafios complexos
                    time.sleep(3)
                    continue
                
                # Verificar se conteúdo real carregou
                links_count = len(driver.find_elements(By.TAG_NAME, 'a'))
                if ('/video/' in driver.page_source or 
                    'follower' in page_source_lower or 
                    links_count > 10):
                    elapsed = int(time.time() - start_time)
                    print(f"✅ Página carregada e desafio resolvido! ({elapsed}s)")
                    print(f"   Links encontrados: {links_count}\n")
                    challenge_resolved = True
                    break
                    
                time.sleep(1)
            except TimeoutException:
                time.sleep(1)
                continue
        
        if not challenge_resolved:
            elapsed = int(time.time() - start_time)
            print(f"⚠️ Timeout aguardando resolução após {elapsed}s, continuando mesmo assim...\n")
        
        # Aguardar JavaScript carregar completamente
        print("⏳ Aguardando JavaScript carregar completamente...")
        time.sleep(3)
        
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
