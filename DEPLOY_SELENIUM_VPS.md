# 🚀 Deploy Selenium Fallback na VPS

## ✅ Mudanças Implementadas

- **Selenium/Chrome headless** como fallback automático
- **Detecção automática** de erros de bot detection
- **Extração de cookies** do navegador em tempo real
- **Fallback transparente** - funciona automaticamente quando necessário

## 📋 Comandos para Executar na VPS

```bash
# 1. Atualizar código
cd ~/content-orchestrator
git fetch origin
git reset --hard origin/main
git pull origin main

# 2. Verificar mudanças (opcional)
git log --oneline -3
git diff HEAD~1 Dockerfile | head -20

# 3. Rebuild SEM CACHE (importante para instalar Chrome)
# Isso vai demorar ~5-10 minutos devido à instalação do Chrome
docker compose build content-orchestrator --no-cache

# 4. Parar e remover container antigo
docker stop content-orchestrator
docker rm content-orchestrator

# 5. Subir container novo
docker compose up -d content-orchestrator

# 6. Verificar se Chrome está instalado
docker exec content-orchestrator google-chrome --version

# 7. Verificar logs
docker logs content-orchestrator --tail 30

# 8. Testar download pelo n8n e monitorar logs
docker logs -f content-orchestrator | grep -E "(Selenium|bot|fallback|Downloading)"
```

## 🔍 Verificações

### Verificar Chrome instalado:
```bash
docker exec content-orchestrator google-chrome --version
# Deve mostrar: Google Chrome 120.x.x ou similar
```

### Verificar Selenium disponível:
```bash
docker exec content-orchestrator python3 -c "import selenium; print(selenium.__version__)"
# Deve mostrar: 4.15.0 ou superior
```

### Verificar webdriver-manager:
```bash
docker exec content-orchestrator python3 -c "import webdriver_manager; print('OK')"
# Deve mostrar: OK
```

## 📊 O que Esperar nos Logs

### Quando yt-dlp funcionar normalmente:
```
INFO - Downloading YPD6K509zfI with yt-dlp
INFO - Found cookies file at: /app/data/cookies.txt
INFO - Using cookies file (absolute): /app/data/cookies.txt
INFO - Download completed successfully
```

### Quando yt-dlp falhar e Selenium for ativado:
```
WARNING - yt-dlp best failed: ERROR: [youtube] ... Sign in to confirm you're not a bot...
INFO - yt-dlp failed with bot detection, trying Selenium fallback...
INFO - Selenium: Starting download fallback for YPD6K509zfI
INFO - Selenium: Navigating to https://www.youtube.com/shorts/YPD6K509zfI
INFO - Selenium: Video element found, page loaded
INFO - Selenium: Extracted 45 cookies to /tmp/tmpXXXXXX.txt
INFO - Selenium: Attempting download with yt-dlp using browser cookies
INFO - Selenium: Download successful! File size: 1234567 bytes
INFO - Selenium fallback succeeded!
```

## ⚠️ Observações Importantes

1. **Primeira execução**: ChromeDriver será baixado automaticamente (~5-10MB)
2. **Tamanho da imagem**: Aumenta ~300MB devido ao Chrome
3. **Tempo de build**: ~5-10 minutos na primeira vez (instalação do Chrome)
4. **RAM**: Chrome consome ~200-500MB RAM quando ativo
5. **Performance**: Selenium é mais lento (~15-30s vs 2-5s do yt-dlp)

## 🐛 Troubleshooting

### Se o build falhar:
```bash
# Verificar logs do build
docker compose build content-orchestrator --no-cache 2>&1 | tail -50

# Verificar se há espaço em disco
df -h

# Limpar cache do Docker (se necessário)
docker system prune -a
```

### Se Chrome não instalar:
```bash
# Verificar se repositório está correto
docker exec content-orchestrator cat /etc/apt/sources.list.d/google-chrome.list

# Tentar instalação manual dentro do container (para debug)
docker exec -it content-orchestrator bash
apt-get update
apt-get install -y google-chrome-stable
```

### Se Selenium falhar:
```bash
# Verificar logs detalhados
docker logs content-orchestrator --tail 100 | grep -i selenium

# Verificar se ChromeDriver foi baixado
docker exec content-orchestrator ls -la ~/.wdm/

# Testar Selenium manualmente
docker exec content-orchestrator python3 -c "
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
options = Options()
options.add_argument('--headless=new')
options.add_argument('--no-sandbox')
options.add_argument('--disable-dev-shm-usage')
driver = webdriver.Chrome(options=options)
driver.get('https://www.google.com')
print('Selenium OK!')
driver.quit()
"
```

## ✅ Checklist de Deploy

- [ ] Código atualizado na VPS (`git pull`)
- [ ] Build concluído sem erros
- [ ] Container reiniciado
- [ ] Chrome instalado e funcionando
- [ ] Selenium importável
- [ ] Teste de download pelo n8n
- [ ] Logs mostrando fallback funcionando (se necessário)

## 📝 Próximos Passos Após Deploy

1. Testar download pelo n8n
2. Monitorar logs para ver se Selenium é ativado
3. Verificar se downloads estão funcionando
4. Se ainda houver bloqueios, considerar:
   - Exportar cookies mais recentes
   - Aguardar rate limiting passar
   - Testar com outros vídeos
