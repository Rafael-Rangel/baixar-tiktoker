# 🔄 Sistema de Ordenação Automática de Serviços

## 📋 Como Funciona

O sistema testa automaticamente todos os serviços de download e os ordena por **confiabilidade real**, baseado em qual funcionou primeiro.

## 🎯 Regras do Sistema

1. **Testa um serviço por vez** (exceto Apify e Urlebird)
2. **Quando um serviço funciona**:
   - É movido para o topo da lista (ou logo após os que já funcionaram)
   - É marcado como válido
   - Não é testado novamente
3. **Serviços que falharam** ficam no final da lista
4. **Apify** não é testado (já considerado válido, usado como último recurso)
5. **Urlebird** sempre fica por último (fallback manual)

## 🚀 Como Usar

### Testar Todos os Serviços

```bash
cd "/home/rafael/Área de trabalho/Projetos/tiktok-api"
source venv/bin/activate

# Testar com URL padrão
python test_all_services.py

# Testar com URL específica
python test_all_services.py "https://www.tiktok.com/@usuario/video/123456"

# Resetar ordem anterior e testar tudo de novo
python test_all_services.py "URL" --reset
```

### Resultado do Teste

O teste cria/atualiza o arquivo `services_order.json`:

```json
{
  "last_updated": "2026-01-29T17:21:39.878190",
  "working_services": [
    "Snaptik",
    "TTDownloader",
    "TikWM",
    "MusicallyDown"
  ],
  "failed_services": [
    "Tikmate",
    "SSStik",
    "Tikdown"
  ],
  "total_tested": 7
}
```

## 📊 Ordem Atual (Baseada em Testes)

### ✅ Serviços que Funcionam (4):
1. **Snaptik** ⭐ (funcionou primeiro)
2. **TTDownloader** ⭐
3. **TikWM** ⭐
4. **MusicallyDown** ⭐

### ❌ Serviços que Falharam (3):
- Tikmate
- SSStik
- Tikdown

### 🔄 Ordem Final de Prioridade:

```
1. Snaptik ✅
2. TTDownloader ✅
3. TikWM ✅
4. MusicallyDown ✅
5. Tikmate ❌
6. SSStik ❌
7. Tikdown ❌
8. Urlebird (Fallback manual)
```

## 🔧 Como o Código Usa a Ordem

A função `download_tiktok_video()` agora:

1. **Carrega ordem otimizada** do arquivo `services_order.json`
2. **Coloca serviços que funcionaram no topo** (na ordem que funcionaram)
3. **Adiciona serviços que falharam depois** (na ordem padrão)
4. **Sempre adiciona Urlebird por último** (fallback)

### Exemplo de Log:

```
INFO:app:Ordem otimizada carregada: Snaptik, TTDownloader, TikWM, MusicallyDown
INFO:app:Tentando baixar com Snaptik...
INFO:app:✓ Snaptik encontrou vídeo. Baixando...
INFO:app:✓ Vídeo baixado com sucesso usando Snaptik: ./downloads/tiktok_xxx.mp4
```

## 📝 Arquivos do Sistema

- **`test_all_services.py`**: Script de teste automático
- **`services_order.json`**: Arquivo com ordem otimizada (gerado automaticamente)
- **`app.py`**: Funções `load_optimized_services_order()` e `get_services_list()`

## 🔄 Atualizar Ordem

Para testar tudo de novo e atualizar a ordem:

```bash
python test_all_services.py "URL_DO_VIDEO" --reset
```

Isso vai:
- Resetar ordem anterior
- Testar todos os serviços novamente
- Salvar nova ordem baseada nos resultados

## 💡 Vantagens

1. **Ordenação baseada em testes reais** (não em suposições)
2. **Serviços mais confiáveis são tentados primeiro**
3. **Economiza tempo** (não tenta serviços que já sabemos que não funcionam)
4. **Auto-otimização** conforme novos testes são feitos
5. **Persistência** (ordem salva em arquivo JSON)

## 🎯 Próximos Passos

1. Execute `test_all_services.py` periodicamente para atualizar a ordem
2. A ordem será usada automaticamente em todos os downloads
3. Serviços que começarem a funcionar serão promovidos automaticamente
