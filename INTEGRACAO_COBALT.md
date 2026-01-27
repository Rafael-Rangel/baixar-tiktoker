# Integração com Cobalt API

## Visão Geral

O **Cobalt** é uma ferramenta open-source robusta que lida automaticamente com bloqueios do YouTube, Instagram e outras plataformas. Ele foi integrado como uma **estratégia adicional de fallback** no sistema de download, sendo acionado quando o yt-dlp falha devido a detecção de bot.

## Arquitetura de Fallback

A ordem de execução das estratégias de download é:

1. **yt-dlp Direto** (Estratégias primárias)
   - Format 18
   - bestvideo+bestaudio + merge
   - best format

2. **Cobalt API** (Fallback nível 1 - mais rápido e leve)
   - Acionado quando yt-dlp falha com erro de bot detection
   - Suporta YouTube, Instagram, TikTok
   - Mais rápido que Selenium (não requer navegador)

3. **Selenium** (Fallback nível 2 - último recurso)
   - Acionado apenas se Cobalt falhar e for YouTube
   - Requer Chrome/Chromium instalado
   - Mais lento mas mais robusto

## Configuração

### Opção 1: Usar Instância Pública (se disponível)

Se houver uma instância pública do Cobalt disponível, configure no `.env`:

```bash
COBALT_API_URL=https://api.cobalt.tools
```

### Opção 2: Auto-hospedar Cobalt (Recomendado)

O Cobalt é open-source e pode ser auto-hospedado para maior controle e confiabilidade.

**Repositório**: https://github.com/imputnet/cobalt

**Passos para auto-hospedar**:

1. Clone o repositório:
```bash
git clone https://github.com/imputnet/cobalt.git
cd cobalt
```

2. Siga as instruções de deploy no README do projeto

3. Configure a URL no `.env`:
```bash
COBALT_API_URL=https://sua-instancia-cobalt.com
```

### Opção 3: Deixar Vazio (Desabilitado)

Se não configurar `COBALT_API_URL`, o sistema tentará usar `https://api.cobalt.tools` como padrão, mas pode não estar disponível. Nesse caso, o sistema automaticamente pula para o Selenium fallback.

## Como Funciona

### Fluxo de Execução

```
1. yt-dlp tenta download
   ↓ (falha com bot detection)
   
2. Cobalt API é acionado
   ├─ Envia URL do vídeo para API
   ├─ Recebe link de download direto
   └─ Baixa arquivo do link fornecido
   ↓ (sucesso ou falha)
   
3. Se Cobalt falhar e for YouTube:
   └─ Selenium fallback é acionado
```

### Endpoints da API Cobalt

O serviço tenta dois endpoints:

1. **`/api/json`** (preferencial):
   - Envia JSON com opções de download
   - Recebe resposta estruturada

2. **`/api/parse`** (fallback):
   - Envia apenas URL
   - Formato mais simples

### Opções de Download

O serviço envia as seguintes opções para o Cobalt:

```json
{
  "url": "https://www.youtube.com/watch?v=...",
  "vCodec": "h264",           // Preferir h264 para compatibilidade
  "vQuality": "max",          // Melhor qualidade disponível
  "aFormat": "best",          // Melhor áudio disponível
  "isAudioOnly": false,       // Queremos vídeo completo
  "isNoTTWatermark": true,    // Sem marca d'água (se aplicável)
  "isTTFullAudio": false      // Áudio completo (se aplicável)
}
```

## Vantagens do Cobalt

1. **Mais Rápido**: Não requer inicialização de navegador
2. **Mais Leve**: Menor consumo de recursos (RAM, CPU)
3. **Mais Confiável**: Lida automaticamente com bloqueios
4. **Suporte Multi-plataforma**: YouTube, Instagram, TikTok, etc.

## Desvantagens

1. **Requer Instância**: Precisa de uma instância do Cobalt rodando
2. **Dependência Externa**: Depende de serviço externo estar disponível
3. **Pode Ter Limites**: Instâncias públicas podem ter rate limiting

## Logs

O serviço registra logs detalhados:

```
INFO - Cobalt: Starting download fallback for VIDEO_ID
INFO - Cobalt: Requesting video info from https://api.cobalt.tools
INFO - Cobalt: Got download URL, downloading file...
INFO - Cobalt: Downloaded 5242880 bytes to /path/to/file.mp4
INFO - Cobalt: Download successful! File size: 5242880 bytes
```

Em caso de erro:

```
WARNING - Cobalt: API returned status 500
ERROR - Cobalt: API error: Error message
WARNING - Cobalt fallback failed: Error details
```

## Troubleshooting

### Erro: "Cobalt API request timeout"

**Causa**: A instância do Cobalt não está respondendo ou está muito lenta.

**Solução**:
- Verifique se a URL está correta
- Verifique se a instância está online
- Aumente o timeout se necessário (modificar `self.timeout` no código)

### Erro: "Cobalt API did not return download URL"

**Causa**: A API retornou resposta em formato inesperado ou erro.

**Solução**:
- Verifique os logs para ver a resposta completa
- Verifique se a URL do vídeo é válida
- Tente com outra instância do Cobalt

### Erro: "Cobalt fallback not available (ImportError)"

**Causa**: Módulo não encontrado (improvável, já que está no mesmo projeto).

**Solução**:
- Verifique se o arquivo `cobalt_service.py` existe
- Verifique se há erros de sintaxe

## Recomendações

1. **Auto-hospedar**: Para produção, recomenda-se auto-hospedar o Cobalt para maior controle
2. **Monitoramento**: Monitore a disponibilidade da instância do Cobalt
3. **Fallback**: O sistema sempre tem o Selenium como último recurso
4. **Rate Limiting**: Se usar instância pública, implemente rate limiting no seu código

## Referências

- **Repositório Cobalt**: https://github.com/imputnet/cobalt
- **Documentação**: https://cobalt.tools/
- **API Documentation**: Ver README do repositório para detalhes da API
