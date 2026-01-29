# 🚀 Deploy na VPS - Passo a Passo

## 1. Atualizar Código do GitHub

```bash
cd ~/tiktok-downloader-api
git pull origin main
```

## 2. Parar Container Atual

```bash
cd ~
docker compose stop tiktok-downloader-api
```

## 3. Rebuild com Novas Dependências (Selenium + Chrome)

```bash
docker compose build tiktok-downloader-api
```

**⚠️ IMPORTANTE:** Este build pode demorar 5-10 minutos porque:
- Instala Google Chrome
- Instala todas as dependências Python (Selenium, undetected-chromedriver, etc.)

## 4. Iniciar Container

```bash
docker compose up -d tiktok-downloader-api
```

## 5. Verificar Logs

```bash
docker logs -f tiktok-downloader-api
```

Você deve ver:
- `INFO:__main__:Iniciando servidor na porta 5000`
- `Biblioteca tiktok-downloader disponível ✓`
- Se Selenium estiver disponível, não verá erro de importação

## 6. Testar Health Check

```bash
curl http://localhost:5000/health
```

Deve retornar JSON com:
- `selenium_available: true` (se funcionou)
- `urlebird_available: true`
- `tiktok_downloader_available: true`

## 7. Testar Endpoint `/channels/latest`

```bash
curl -X POST http://localhost:5000/channels/latest \
  -H "Content-Type: application/json" \
  -d '{"channels": ["oprimorico"]}'
```

Ou com URLs:

```bash
curl -X POST http://localhost:5000/channels/latest \
  -H "Content-Type: application/json" \
  -d '{"urls": ["https://urlebird.com/pt/user/oprimorico/"]}'
```

## 8. Verificar se Selenium Funcionou

Nos logs, procure por:
- `Tentando método Selenium (anti-detecção)...`
- `✓ Vídeo mais recente encontrado via Selenium: ...`

Se aparecer erro de Selenium, verifique:
- Chrome foi instalado? (`docker exec tiktok-downloader-api google-chrome --version`)
- Dependências foram instaladas? (`docker exec tiktok-downloader-api pip list | grep selenium`)

## Troubleshooting

### Erro: "Selenium não está instalado"
```bash
docker compose build --no-cache tiktok-downloader-api
```

### Erro: "Chrome não encontrado"
Verifique se Chrome foi instalado:
```bash
docker exec tiktok-downloader-api google-chrome --version
```

### Ver logs em tempo real
```bash
docker logs -f tiktok-downloader-api
```

### Reiniciar container
```bash
docker compose restart tiktok-downloader-api
```
