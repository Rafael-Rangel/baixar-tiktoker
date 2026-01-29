#!/usr/bin/env python3
"""
Script de teste para download de vídeo TikTok
Testa qual método funcionou para baixar o vídeo
"""

import os
import sys
import json

# Verificar se está no venv
if not hasattr(sys, 'real_prefix') and not (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
    print("⚠️  AVISO: Não está em um ambiente virtual!")
    print("   Ative o venv primeiro: source venv/bin/activate")
    resposta = input("   Continuar mesmo assim? (s/N): ")
    if resposta.lower() != 's':
        sys.exit(1)

print("\n" + "="*60)
print("🧪 TESTE DE DOWNLOAD - TikTok Video")
print("="*60 + "\n")

# URL do vídeo para testar
video_url = "https://www.tiktok.com/@nathanharenice/video/7388139978473245958"

if len(sys.argv) > 1:
    video_url = sys.argv[1]

print(f"📹 URL do Vídeo: {video_url}")
print("-" * 60)

# Importar função do app.py
try:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    
    from app import download_tiktok_video
    
    print("\n🚀 Iniciando download...")
    print("   Testando métodos na ordem de prioridade:\n")
    print("   1. Snaptik")
    print("   2. Tikmate")
    print("   3. SSStik")
    print("   4. TTDownloader")
    print("   5. TikWM")
    print("   6. MusicallyDown")
    print("   7. Tikdown")
    print("   8. Urlebird (Fallback)\n")
    
    # Executar download
    video_file, error = download_tiktok_video(video_url)
    
    print("\n" + "="*60)
    print("📊 RESULTADO DO TESTE")
    print("="*60)
    
    if error:
        print(f"\n❌ ERRO: {error}\n")
        sys.exit(1)
    
    if video_file and os.path.exists(video_file):
        file_size = os.path.getsize(video_file)
        file_size_mb = round(file_size / (1024 * 1024), 2)
        
        print(f"\n✅ SUCESSO!")
        print(f"\n📁 Arquivo Baixado:")
        print(f"   Caminho: {video_file}")
        print(f"   Tamanho: {file_size_mb} MB ({file_size} bytes)")
        print(f"\n💡 Dica: Verifique os logs acima para ver qual método funcionou!")
        print(f"   Procure por: '✓ Vídeo baixado com sucesso usando'")
        
        print("\n" + "="*60)
        print("✅ TESTE CONCLUÍDO COM SUCESSO!")
        print("="*60 + "\n")
        
        # Perguntar se quer manter o arquivo (apenas se terminal interativo)
        try:
            resposta = input("🗑️  Deseja deletar o arquivo de teste? (s/N): ")
            if resposta.lower() == 's':
                try:
                    os.remove(video_file)
                    print(f"✅ Arquivo removido: {video_file}")
                except Exception as e:
                    print(f"⚠️  Erro ao remover arquivo: {e}")
        except EOFError:
            print(f"💾 Arquivo mantido em: {video_file}")
    else:
        print("\n❌ Arquivo não foi baixado corretamente\n")
        sys.exit(1)
        
except Exception as e:
    print(f"\n❌ ERRO ao executar teste: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
