#!/usr/bin/env python3
"""
Script de teste para visualizar o SeleniumBase funcionando
Abre o navegador visível para você ver o processo
Conforme guia Cloudflare: Method #5 - Implement Fortified Headless Browsers
"""

import sys
import time

# Importar bibliotecas
try:
    from seleniumbase import Driver
    from bs4 import BeautifulSoup
    import re
except ImportError as e:
    print(f"❌ Erro ao importar bibliotecas: {e}")
    print("\nInstale as dependências:")
    print("pip install seleniumbase beautifulsoup4")
    sys.exit(1)

def test_urlebird_seleniumbase(username, headless=False):
    """Testa acesso ao Urlebird usando SeleniumBase com UC"""
    
    print(f"\n{'='*60}")
    print(f"🧪 TESTE SELENIUMBASE - Urlebird")
    print(f"{'='*60}")
    print(f"Username: @{username}")
    print(f"Modo: {'Headless' if headless else 'VISÍVEL (você verá o navegador)'}")
    print(f"Método: SeleniumBase com Undetected ChromeDriver (conforme guia Cloudflare)")
    print(f"{'='*60}\n")
    
    driver = None
    try:
        url = f"https://urlebird.com/pt/user/{username}/"
        print(f"📌 URL: {url}\n")
        
        # SeleniumBase com UC (Undetected ChromeDriver) - método recomendado pelo guia
        print("🔧 Criando driver SeleniumBase com UC...")
        driver = Driver(uc=True, headless=headless)
        print("✅ Driver criado com sucesso!\n")
        
        # Usar uc_open_with_reconnect para melhor handling de desafios Cloudflare
        print(f"🌐 Acessando página com reconexão automática...")
        driver.uc_open_with_reconnect(url, reconnect_time=4)
        print("✅ Requisição enviada!\n")
        
        # Aguardar resolução de desafios Cloudflare
        print("⏳ Aguardando resolução de desafios Cloudflare...")
        max_wait = 60
        start_time = time.time()
        challenge_resolved = False
        
        while time.time() - start_time < max_wait:
            try:
                page_source_lower = driver.page_source.lower()
                page_title = driver.title.lower()
                
                # Verificar se ainda está em página de desafio
                if ('challenge' in page_source_lower or 
                    'checking your browser' in page_source_lower or 
                    'just a moment' in page_source_lower or
                    'um momento' in page_title or
                    'please wait' in page_title):
                    elapsed = int(time.time() - start_time)
                    print(f"   🔄 Desafio Cloudflare detectado, aguardando resolução... ({elapsed}s/{max_wait}s)")
                    time.sleep(2)
                    continue
                
                # Verificar se conteúdo real carregou
                if '/video/' in driver.page_source or 'follower' in page_source_lower:
                    elapsed = int(time.time() - start_time)
                    print(f"✅ Página carregada e desafio resolvido! ({elapsed}s)\n")
                    challenge_resolved = True
                    break
                    
                time.sleep(1)
            except Exception as e:
                print(f"   ⚠ Erro durante espera: {e}")
                time.sleep(1)
                continue
        
        if not challenge_resolved:
            elapsed = int(time.time() - start_time)
            print(f"⚠️ Timeout aguardando resolução após {elapsed}s, continuando mesmo assim...\n")
        
        # Tentar resolver CAPTCHA Turnstile se presente
        try:
            print("🔐 Tentando resolver CAPTCHA Turnstile (se presente)...")
            driver.uc_gui_click_captcha()
            time.sleep(5)
            print("✅ CAPTCHA processado!\n")
        except Exception as e:
            print(f"   ℹ️ CAPTCHA não encontrado ou já resolvido\n")
        
        # Aguardar mais um pouco para garantir carregamento completo
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
            if not headless:
                print("="*60)
                print("👀 NAVEGADOR ABERTO - Verifique a página manualmente")
                print("="*60)
                try:
                    input("\nPressione ENTER para fechar o navegador...")
                except EOFError:
                    pass
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
        if driver:
            print("🔒 Fechando navegador...")
            try:
                driver.quit()
                print("✅ Navegador fechado!\n")
            except:
                pass

if __name__ == '__main__':
    print("\n" + "="*60)
    print("🧪 TESTE SELENIUMBASE - Urlebird")
    print("Método: SeleniumBase com Undetected ChromeDriver")
    print("Conforme guia Cloudflare: Method #5")
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
    sucesso = test_urlebird_seleniumbase(username, headless=headless)
    
    print("="*60)
    if sucesso:
        print("✅ TESTE CONCLUÍDO COM SUCESSO!")
    else:
        print("❌ TESTE FALHOU")
    print("="*60 + "\n")
