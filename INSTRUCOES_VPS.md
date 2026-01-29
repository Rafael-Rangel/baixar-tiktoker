# Instruções para Deploy na VPS

## Passo 1: Remover Instalação Antiga

```bash
cd ~
rm -rf tiktok-downloader-api
```

## Passo 2: Clonar Repositório Atualizado

```bash
git clone https://github.com/Rafael-Rangel/baixar-tiktoker.git tiktok-downloader-api
cd tiktok-downloader-api
```

## Passo 3: Configurar Sessão Inicial (Resolver Cloudflare Manualmente)

**IMPORTANTE:** Execute este passo ANTES de rodar o Docker, para criar a sessão com cookies válidos.

### Opção A: Se você tem acesso gráfico à VPS (X11/VNC)

```bash
# Ativar venv e instalar dependências
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
playwright install chromium

# Executar setup (abrirá navegador visível)
python setup_session.py oprimorico

# Seguir instruções na tela:
# 1. Resolver desafio Cloudflare manualmente
# 2. Aguardar página carregar
# 3. Pressionar ENTER
# 4. Cookies serão salvos em .playwright_context/urlebird_storage.json
```

### Opção B: Se NÃO tem acesso gráfico (recomendado usar proxy ou IP residencial)

Se sua VPS não tem interface gráfica, você pode:

1. **Usar um proxy residencial** (recomendado pelo Manus)
2. **Exportar cookies do seu PC** e copiar para VPS:
   ```bash
   # No seu PC (após resolver Cloudflare manualmente):
   # Exportar cookies do navegador e salvar como .playwright_context/urlebird_storage.json
   # Copiar para VPS:
   scp -r .playwright_context/ root@SEU_IP_VPS:/root/tiktok-downloader-api/
   ```

## Passo 4: Build e Deploy Docker

```bash
cd ~
docker compose build tiktok-downloader-api
docker compose up -d tiktok-downloader-api
```

## Passo 5: Verificar Logs

```bash
docker logs -f tiktok-downloader-api
```

## Teste

```bash
curl -X POST http://localhost:5000/channels/latest \
  -H "Content-Type: application/json" \
  -d '{"channels": ["oprimorico"]}'
```

## Notas Importantes

- **IP Datacenter:** Se sua VPS usa IP de datacenter conhecido (AWS, DigitalOcean, etc.), o Cloudflare pode ser mais rigoroso
- **Cookies:** O cookie `cf_clearance` expira após algumas horas/dias. Se parar de funcionar, execute `setup_session.py` novamente
- **User-Agent:** O código agora usa User-Agent de Linux sincronizado com o SO da VPS (recomendação do Manus)

## Troubleshooting

### Se ainda receber 403:
1. Verifique se `.playwright_context/urlebird_storage.json` existe e tem cookies válidos
2. Execute `setup_session.py` novamente para renovar cookies
3. Considere usar proxy residencial (recomendado pelo Manus para IPs de datacenter)
