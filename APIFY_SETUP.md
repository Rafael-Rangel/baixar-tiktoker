# 🔧 Configuração do Apify TikTok Scraper

## 📋 O que é Apify?

Apify é uma plataforma profissional de web scraping que já resolve automaticamente:
- ✅ Bypass de Cloudflare
- ✅ Anti-bot detection
- ✅ Rate limiting
- ✅ Proxy rotation
- ✅ Cookies management

**Muito mais confiável que métodos manuais!**

## 🚀 Como Configurar

### 1. Criar conta no Apify

1. Acesse: https://apify.com/
2. Crie uma conta gratuita (tem créditos grátis para testar)
3. Vá em **Settings → Integrations**
4. Copie sua **API Token**

### 2. Configurar na VPS

#### Opção A: Variável de ambiente no docker-compose.yml

Adicione no seu `docker-compose.yml`:

```yaml
tiktok-downloader-api:
  environment:
    - APIFY_API_TOKEN=seu_token_aqui
```

#### Opção B: Arquivo .env (se usar)

```bash
APIFY_API_TOKEN=seu_token_aqui
```

#### Opção C: Direto no container

```bash
docker exec -it tiktok-downloader-api bash
export APIFY_API_TOKEN=seu_token_aqui
```

### 3. Rebuild do container (para instalar apify-client)

```bash
cd ~/tiktok-downloader-api
git pull origin main
cd ~
docker compose build tiktok-downloader-api
docker compose up -d tiktok-downloader-api
```

## ✅ Verificar se está funcionando

```bash
# Verificar health check
curl http://localhost:5000/health | python3 -m json.tool

# Deve mostrar:
# "apify_available": true
# "apify_token_configured": true
```

## 🎯 Como Funciona

O Apify agora é a **primeira opção** na lista de métodos:

1. **Apify TikTok Scraper** ← PRIMEIRO (mais confiável)
2. RapidAPI TikTok Scraper
3. TikWM API
4. Countik
5. Playwright + Stealth
6. Browser Use
7. SeleniumBase
8. Selenium
9. Requests (fallback)

## 💰 Preços

- **Plano Gratuito**: Créditos grátis para testar
- **Pay-per-event**: Você paga apenas pelo que usar
- **Preço**: Verifique em https://apify.com/clockworks/tiktok-scraper/pricing

## 📝 Exemplo de Uso

O endpoint `/channels/latest` agora usa Apify automaticamente se:
- ✅ `apify-client` estiver instalado
- ✅ `APIFY_API_TOKEN` estiver configurado

**Não precisa mudar nada no código!** Apenas configure o token.

## 🔍 Troubleshooting

### Erro: "APIFY_API_TOKEN não configurado"

**Solução**: Configure a variável de ambiente `APIFY_API_TOKEN`

### Erro: "Apify Client não está instalado"

**Solução**: Rebuild do container Docker para instalar `apify-client`

### Erro: "Erro de autenticação"

**Solução**: Verifique se o token está correto em https://console.apify.com/integrations

## 📚 Documentação

- Apify TikTok Scraper: https://apify.com/clockworks/tiktok-scraper
- Apify API Docs: https://docs.apify.com/api/client/python
