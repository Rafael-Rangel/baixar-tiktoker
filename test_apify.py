#!/usr/bin/env python3
"""
Script de teste para Apify TikTok Scraper
Testa localmente antes de enviar para VPS
"""

import os
import sys

# Verificar se está no venv
if not hasattr(sys, 'real_prefix') and not (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
    print("⚠️  AVISO: Não está em um ambiente virtual!")
    print("   Ative o venv primeiro: source venv/bin/activate")
    resposta = input("   Continuar mesmo assim? (s/N): ")
    if resposta.lower() != 's':
        sys.exit(1)

print("\n" + "="*60)
print("🧪 TESTE APIFY TIKTOK SCRAPER")
print("="*60 + "\n")

# Verificar se apify-client está instalado
try:
    from apify_client import ApifyClient
    print("✅ apify-client instalado")
except ImportError:
    print("❌ apify-client NÃO está instalado")
    print("\n📦 Instalando apify-client...")
    os.system("pip install apify-client")
    try:
        from apify_client import ApifyClient
        print("✅ apify-client instalado com sucesso!")
    except ImportError:
        print("❌ Erro ao instalar apify-client")
        sys.exit(1)

# Verificar token do Apify
apify_token = os.getenv('APIFY_API_TOKEN', None)
if not apify_token:
    print("\n⚠️  APIFY_API_TOKEN não configurado!")
    print("\n📝 Como obter:")
    print("   1. Acesse: https://console.apify.com/integrations")
    print("   2. Copie seu API Token")
    print("   3. Configure:")
    print("      export APIFY_API_TOKEN='seu_token_aqui'")
    print("\n   Ou adicione no arquivo .env:")
    print("      APIFY_API_TOKEN=seu_token_aqui")
    
    token = input("\n🔑 Cole seu token aqui (ou pressione Enter para pular): ").strip()
    if token:
        os.environ['APIFY_API_TOKEN'] = token
        apify_token = token
    else:
        print("\n❌ Teste cancelado - token necessário")
        sys.exit(1)
else:
    print(f"✅ APIFY_API_TOKEN configurado (primeiros 10 chars: {apify_token[:10]}...)")

# Perguntar username para testar
if len(sys.argv) > 1:
    username = sys.argv[1]
else:
    username = input("\n👤 Digite o username do TikTok para testar (sem @): ").strip()

if not username:
    username = "nathanharenice"  # Usar o mesmo do teste que funcionou
    print(f"   Usando username padrão: {username}")

print(f"\n🔍 Testando com username: @{username}")
print("-" * 60)

# Importar função do app.py
try:
    # Adicionar diretório atual ao path
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    
    # Importar apenas o necessário
    from app import get_latest_video_url_from_channel_apify, validate_username
    
    print("\n🚀 Executando teste...\n")
    
    # Executar função
    tiktok_url, service_url, channel_data, error = get_latest_video_url_from_channel_apify(username)
    
    print("\n" + "="*60)
    print("📊 RESULTADO DO TESTE")
    print("="*60)
    
    if error:
        print(f"\n❌ ERRO: {error}\n")
        sys.exit(1)
    
    if tiktok_url:
        print(f"\n✅ SUCESSO!")
        print(f"\n📹 URL do Vídeo:")
        print(f"   {tiktok_url}")
        
        if channel_data:
            print(f"\n👤 Dados do Canal:")
            print(f"   Username: {channel_data.get('username', 'N/A')}")
            print(f"   Nickname: {channel_data.get('nickname', 'N/A')}")
            print(f"   Seguidores: {channel_data.get('followers', 'N/A')}")
            print(f"   Total Likes: {channel_data.get('total_likes', 'N/A')}")
            print(f"   Vídeos Postados: {channel_data.get('videos_posted', 'N/A')}")
            print(f"   Verificado: {'Sim' if channel_data.get('verified') else 'Não'}")
        
        print("\n" + "="*60)
        print("✅ TESTE CONCLUÍDO COM SUCESSO!")
        print("="*60 + "\n")
    else:
        print("\n❌ Nenhum vídeo encontrado\n")
        sys.exit(1)
        
except Exception as e:
    print(f"\n❌ ERRO ao executar teste: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
