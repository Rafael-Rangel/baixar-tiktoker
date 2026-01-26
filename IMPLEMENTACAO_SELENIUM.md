# Implementação Selenium como Fallback

## Resumo

Implementado Selenium/Chrome headless como fallback automático quando yt-dlp falha devido a detecção de bot do YouTube.

## Arquivos Modificados/Criados

### 1. `Dockerfile`
- Adicionado Chrome/Chromium e todas as dependências necessárias
- Instalação via repositório oficial do Google
- Chrome headless configurado para rodar em container

### 2. `requirements.txt`
- Adicionado `selenium>=4.15.0`
- Adicionado `webdriver-manager>=4.0.0` (gerencia ChromeDriver automaticamente)

### 3. `app/services/downloader/selenium_service.py` (NOVO)
- Classe `SeleniumDownloaderService` com método `download_video()`
- Extrai cookies do navegador após navegar até o vídeo
- Usa cookies extraídos com yt-dlp para fazer download
- Implementa timeouts e tratamento de erros

### 4. `app/services/downloader/service.py`
- Integrado fallback automático do Selenium
- Detecta erros de bot detection
- Chama Selenium apenas quando necessário (YouTube + erro de bot)

### 5. `app/services/downloader/__init__.py` (NOVO)
- Arquivo necessário para imports do módulo

## Como Funciona

### Fluxo de Download

1. **Tentativa 1: yt-dlp** (rápido, ~2-5s)
   - Format 18
   - Merge (bestvideo+bestaudio)
   - Best

2. **Se falhar com erro de bot detection:**
   - **Tentativa 2: Selenium** (mais lento, ~15-30s)
     - Abre Chrome headless
     - Navega até URL do vídeo
     - Extrai cookies do navegador
     - Usa cookies com yt-dlp para download

### Detecção de Erro de Bot

O código detecta automaticamente se o erro é relacionado a bot detection verificando palavras-chave:
- "bot"
- "sign in"
- "authentication"
- "confirm you're not a bot"

## Vantagens

- **Automático**: Não requer configuração adicional
- **Transparente**: Usuário não precisa escolher estratégia
- **Eficiente**: Só usa Selenium quando necessário
- **Confiável**: Muito mais difícil de detectar como bot

## Desvantagens

- **Mais pesado**: Chrome consome ~200-500MB RAM
- **Mais lento**: Selenium leva 15-30s vs 2-5s do yt-dlp
- **Maior imagem Docker**: Chrome adiciona ~300MB à imagem

## Deploy na VPS

```bash
# 1. Atualizar código
cd ~/content-orchestrator
git fetch origin
git reset --hard origin/main
git pull origin main

# 2. Rebuild SEM CACHE (importante para instalar Chrome)
docker compose build content-orchestrator --no-cache

# 3. Reiniciar container
docker stop content-orchestrator
docker rm content-orchestrator
docker compose up -d content-orchestrator

# 4. Verificar logs
docker logs content-orchestrator --tail 50
```

## Verificação

Após deploy, os logs devem mostrar:
- Tentativas normais do yt-dlp
- Se falhar: "yt-dlp failed with bot detection, trying Selenium fallback..."
- "Selenium: Navigating to..."
- "Selenium: Extracted X cookies..."
- "Selenium fallback succeeded!" (se funcionar)

## Notas Importantes

1. **Primeira execução**: ChromeDriver será baixado automaticamente pelo webdriver-manager
2. **Cookies**: Selenium extrai cookies frescos do navegador a cada tentativa
3. **Timeout**: Selenium aguarda até 15s para página carregar
4. **Limpeza**: Driver e arquivos temporários são limpos automaticamente

## Troubleshooting

Se Selenium falhar:
- Verificar se Chrome está instalado: `docker exec content-orchestrator google-chrome --version`
- Verificar logs para erros específicos
- Verificar se há espaço em disco suficiente
- Verificar permissões do diretório de downloads
