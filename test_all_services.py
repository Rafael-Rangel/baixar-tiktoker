#!/usr/bin/env python3
"""
Script para testar automaticamente todos os serviços de download
e ordená-los por confiabilidade (baseado em qual funcionou primeiro)
"""

import os
import sys
import json
import time
from datetime import datetime

# Adicionar diretório atual ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Importar funções necessárias
from app import download_tiktok_video, TIKTOK_DOWNLOADER_AVAILABLE
from app import snaptik, Tikmate, ssstik, ttdownloader, tikwm, mdown, tikdown

# Arquivo para salvar ordem otimizada
SERVICES_ORDER_FILE = "services_order.json"

# Lista completa de serviços (exceto Apify e Urlebird que são fallbacks)
ALL_SERVICES = [
    ('Snaptik', snaptik, True, False),
    ('Tikmate', Tikmate, False, False),
    ('SSStik', ssstik, True, False),
    ('TTDownloader', ttdownloader, True, False),
    ('TikWM', tikwm, True, False),
    ('MusicallyDown', mdown, True, False),
    ('Tikdown', tikdown, True, False),
]

def load_services_order():
    """Carrega ordem otimizada dos serviços do arquivo JSON"""
    if os.path.exists(SERVICES_ORDER_FILE):
        try:
            with open(SERVICES_ORDER_FILE, 'r') as f:
                data = json.load(f)
                return data.get('working_services', []), data.get('failed_services', [])
        except Exception as e:
            print(f"⚠️  Erro ao carregar ordem: {e}")
    return [], []

def save_services_order(working_services, failed_services):
    """Salva ordem otimizada dos serviços no arquivo JSON"""
    data = {
        'last_updated': datetime.now().isoformat(),
        'working_services': working_services,
        'failed_services': failed_services,
        'total_tested': len(working_services) + len(failed_services)
    }
    try:
        with open(SERVICES_ORDER_FILE, 'w') as f:
            json.dump(data, f, indent=2)
        print(f"✅ Ordem salva em {SERVICES_ORDER_FILE}")
    except Exception as e:
        print(f"⚠️  Erro ao salvar ordem: {e}")

def test_service(service_name, service_func, is_function, test_url):
    """Testa um serviço específico"""
    print(f"\n🧪 Testando {service_name}...")
    
    try:
        if is_function:
            data_list = service_func(test_url)
        else:
            # Classes: Tikmate
            if service_name == 'Tikmate':
                service = service_func()
                data_list = service.get_media(test_url)
            else:
                data_list = service_func(test_url)
        
        # Verificar se retornou lista válida
        if data_list and isinstance(data_list, list) and len(data_list) > 0:
            video_item = data_list[0]
            if hasattr(video_item, 'download'):
                print(f"   ✅ {service_name} FUNCIONOU!")
                return True
            else:
                print(f"   ❌ {service_name} retornou item sem método download")
                return False
        else:
            print(f"   ❌ {service_name} não retornou lista válida")
            return False
            
    except Exception as e:
        print(f"   ❌ {service_name} falhou: {str(e)[:100]}")
        return False

def test_all_services(test_url, skip_working=True):
    """Testa todos os serviços e ordena por confiabilidade"""
    
    print("\n" + "="*60)
    print("🚀 TESTE AUTOMÁTICO DE SERVIÇOS")
    print("="*60)
    print(f"\n📹 URL de teste: {test_url}")
    print(f"⏭️  Apify será ignorado (já considerado válido)")
    print(f"⏭️  Urlebird será ignorado (fallback manual)")
    
    # Carregar ordem existente
    working_services, failed_services = load_services_order()
    
    if skip_working and working_services:
        print(f"\n✅ Serviços que já funcionaram (serão pulados):")
        for svc in working_services:
            print(f"   - {svc}")
    
    # Filtrar serviços já testados
    tested_names = set(working_services + failed_services)
    services_to_test = [
        svc for svc in ALL_SERVICES 
        if svc[0] not in tested_names or not skip_working
    ]
    
    if not services_to_test:
        print("\n✅ Todos os serviços já foram testados!")
        print(f"\n📊 Ordem atual:")
        print(f"   Trabalhando: {', '.join(working_services)}")
        print(f"   Falharam: {', '.join(failed_services)}")
        return working_services, failed_services
    
    print(f"\n🔍 Testando {len(services_to_test)} serviço(s)...")
    
    # Testar cada serviço
    new_working = []
    new_failed = []
    
    for service_name, service_func, is_function, is_urlebird in services_to_test:
        # Pular se já está na lista de funcionando
        if skip_working and service_name in working_services:
            print(f"\n⏭️  Pulando {service_name} (já funciona)")
            continue
        
        success = test_service(service_name, service_func, is_function, test_url)
        
        if success:
            new_working.append(service_name)
            print(f"   ⬆️  {service_name} será movido para o topo da lista!")
        else:
            new_failed.append(service_name)
        
        # Pequeno delay entre testes
        time.sleep(1)
    
    # Combinar com resultados anteriores
    # Serviços que funcionaram ficam no topo (ordem de quando funcionaram)
    final_working = working_services + new_working
    final_failed = failed_services + new_failed
    
    # Salvar nova ordem
    save_services_order(final_working, final_failed)
    
    print("\n" + "="*60)
    print("📊 RESULTADO FINAL")
    print("="*60)
    print(f"\n✅ Serviços que funcionam ({len(final_working)}):")
    for i, svc in enumerate(final_working, 1):
        print(f"   {i}. {svc}")
    
    if final_failed:
        print(f"\n❌ Serviços que falharam ({len(final_failed)}):")
        for svc in final_failed:
            print(f"   - {svc}")
    
    print("\n" + "="*60)
    print("✅ TESTE CONCLUÍDO!")
    print("="*60 + "\n")
    
    return final_working, final_failed

if __name__ == '__main__':
    # URL de teste padrão
    test_url = "https://www.tiktok.com/@nathanharenice/video/7388139978473245958"
    
    if len(sys.argv) > 1:
        test_url = sys.argv[1]
    
    if not TIKTOK_DOWNLOADER_AVAILABLE:
        print("❌ Biblioteca tiktok-downloader não está disponível!")
        sys.exit(1)
    
    # Perguntar se quer resetar ordem anterior
    reset = False
    if len(sys.argv) > 2 and sys.argv[2] == '--reset':
        reset = True
        if os.path.exists(SERVICES_ORDER_FILE):
            os.remove(SERVICES_ORDER_FILE)
            print("🔄 Ordem anterior resetada\n")
    
    # Executar testes
    working, failed = test_all_services(test_url, skip_working=not reset)
    
    print(f"\n💡 Próximos passos:")
    print(f"   1. A ordem otimizada foi salva em {SERVICES_ORDER_FILE}")
    print(f"   2. O código será atualizado para usar essa ordem")
    print(f"   3. Execute novamente com --reset para testar tudo de novo")
