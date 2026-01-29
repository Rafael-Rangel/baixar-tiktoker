# API Python para Download de Vídeos TikTok

API backend simples em Python usando Flask e yt-dlp para baixar vídeos do TikTok sem watermark.

## 📋 Requisitos

- Python 3.8 ou superior
- pip (gerenciador de pacotes Python)
- ffmpeg (opcional, mas recomendado para limpar metadados dos vídeos)
  - Windows: Baixe de https://ffmpeg.org/download.html
  - Linux: `sudo apt install ffmpeg` ou `sudo yum install ffmpeg`
  - Mac: `brew install ffmpeg`

## 🚀 Instalação

1. **Instalar dependências:**

```bash
pip install -r requirements.txt
```

2. **Instalar yt-dlp separadamente (recomendado):**

```bash
pip install yt-dlp
```

Ou via pip do requirements.txt (já incluído).

## ▶️ Como Usar

1. **Iniciar o servidor:**

```bash
python app.py
```

Ou especificar porta:

```bash
PORT=8080 python app.py
```

O servidor iniciará em `http://localhost:5000` (ou na porta especificada).

2. **Fazer download de vídeo:**

**POST /download**

```bash
curl -X POST http://localhost:5000/download \
  -H "Content-Type: application/json" \
  -d '{"url": "https://www.tiktok.com/@usuario/video/123456"}'
```

**GET /download** (para teste)

```bash
curl "http://localhost:5000/download?url=https://www.tiktok.com/@usuario/video/123456" --output video.mp4
```

## 📡 Endpoints

### POST /download

Baixa um vídeo do TikTok.

**Request:**
```json
{
  "url": "https://www.tiktok.com/@usuario/video/123456"
}
```

**Parâmetros:**
- `url` (obrigatório): URL do vídeo TikTok

**Response:**
- Sucesso: Arquivo MP4 (video/mp4)
- Erro: JSON com mensagem de erro

**Status Codes:**
- `200 OK` - Vídeo baixado e retornado com sucesso
- `400 Bad Request` - URL inválida ou campo faltando
- `500 Internal Server Error` - Erro ao processar

### GET /health

Health check da API.

**Response:**
```json
{
  "status": "ok",
  "message": "API funcionando"
}
```

## 🎯 Integração com n8n

1. **HTTP Request Node:**
   - Method: `POST`
   - URL: `http://seu-servidor:5000/download`
   - Headers: `Content-Type: application/json`
   - Body:
   ```json
   {
     "url": "{{ $json.tiktok_url }}"
   }
   ```

2. **Salvar arquivo:**
   - Use o node "Write Binary File" após o HTTP Request
   - O response será o arquivo de vídeo diretamente

## ⚙️ Variáveis de Ambiente

- `PORT` - Porta do servidor (padrão: 5000)
- `DOWNLOAD_DIR` - Pasta para arquivos temporários (padrão: ./downloads)

**Exemplo:**
```bash
export PORT=8080
export DOWNLOAD_DIR=/tmp/tiktok-downloads
python app.py
```

## 📝 Formato de URLs Aceitas

A API aceita os seguintes formatos de URL do TikTok:

- `https://www.tiktok.com/@usuario/video/123456`
- `https://tiktok.com/@usuario/video/123456`
- `https://vt.tiktok.com/XXXXXX/`

## 🔒 Segurança

- Arquivos temporários são removidos automaticamente após o download
- Validação de URL para aceitar apenas TikTok
- CORS habilitado para integração com n8n

## 🧹 Limpeza de Metadados

Para limpar metadados dos vídeos e não parecer que é o vídeo original, use FFmpeg diretamente no n8n após o download.

### 📋 Comando FFmpeg

Use este comando para remover todos os metadados de um vídeo:

```bash
ffmpeg -i INPUT_FILE.mp4 \
  -map_metadata -1 \
  -metadata title= \
  -metadata artist= \
  -metadata album= \
  -metadata date= \
  -metadata comment= \
  -metadata copyright= \
  -metadata encoder= \
  -codec copy \
  -y \
  OUTPUT_FILE.mp4
```

### 🔧 Como Usar no n8n

#### Opção 1: Execute Command Node (Recomendado)

1. **Após baixar o vídeo da API:**
   - Adicione um node "Execute Command"
   - Configure:
     ```
     Command: ffmpeg
     Arguments (adicione cada linha separadamente): 
       -i
       {{ $json.file_path }}
       -map_metadata
       -1
       -metadata
       title=
       -metadata
       artist=
       -metadata
       album=
       -metadata
       date=
       -metadata
       comment=
       -metadata
       copyright=
       -metadata
       encoder=
       -codec
       copy
       -y
       {{ $json.file_path.replace('.mp4', '_clean.mp4') }}
     ```
   
   **Importante:** No n8n Execute Command, cada argumento deve ser uma linha separada ou separado por espaço dependendo da configuração do node.

2. **Exemplo de Workflow:**
   ```
   HTTP Request (Download) → Write Binary File → Execute Command (FFmpeg) → (Vídeo Limpo)
   ```

#### Opção 2: Code Node (JavaScript)

No n8n Code node:

```javascript
const { exec } = require('child_process');

const inputFile = $input.item.json.filePath; // Caminho do arquivo baixado
const outputFile = inputFile.replace('.mp4', '_clean.mp4');

const ffmpegCommand = `ffmpeg -i "${inputFile}" ` +
  `-map_metadata -1 ` +
  `-metadata title= ` +
  `-metadata artist= ` +
  `-metadata album= ` +
  `-metadata date= ` +
  `-metadata comment= ` +
  `-metadata copyright= ` +
  `-metadata encoder= ` +
  `-codec copy -y "${outputFile}"`;

return new Promise((resolve, reject) => {
  exec(ffmpegCommand, (error, stdout, stderr) => {
    if (error) {
      return reject(error);
    }
    resolve({
      json: {
        originalFile: inputFile,
        cleanFile: outputFile,
        success: true
      }
    });
  });
});
```

### 📝 Exemplo Completo de Workflow n8n

**Passo a passo detalhado:**

```
1. HTTP Request Node (Download)
   ├─ Method: POST
   ├─ URL: http://seu-servidor:5000/download
   ├─ Headers: Content-Type: application/json
   ├─ Body (JSON):
   │  {
   │    "url": "{{ $json.tiktok_url }}"
   │  }
   └─ Response: Binary

2. Write Binary File Node (Salvar vídeo baixado)
   ├─ File Name: video_{{ $json.tiktok_url.split('/').pop() }}.mp4
   ├─ Data: {{ $binary.data }}
   └─ File Path: /tmp/videos/video.mp4

3. Execute Command Node (Limpar metadados)
   ├─ Command: ffmpeg
   └─ Arguments (um por linha):
      -i /tmp/videos/video.mp4
      -map_metadata -1
      -metadata title=
      -metadata artist=
      -metadata album=
      -metadata date=
      -metadata comment=
      -metadata copyright=
      -metadata encoder=
      -codec copy
      -y
      /tmp/videos/video_clean.mp4

4. (Opcional) Read Binary File Node
   ├─ File Path: /tmp/videos/video_clean.mp4
   └─ Para usar o vídeo limpo em outro lugar
```

**Nota:** No n8n, cada argumento do ffmpeg deve ser colocado em uma linha separada no campo "Arguments" do Execute Command node.

### ⚡ Parâmetros do Comando

- `-i INPUT`: Arquivo de entrada
- `-map_metadata -1`: Remove TODOS os metadados
- `-metadata campo=`: Remove campo específico (vazio remove)
- `-codec copy`: Copia sem re-encodar (rápido, mantém qualidade)
- `-y`: Sobrescreve arquivo de saída se existir

### ✅ O que é Removido

- Título
- Artista/Autor
- Álbum
- Data
- Comentários
- Copyright
- Informações do TikTok
- Todos os outros metadados identificáveis

**Nota:** Restam apenas metadados técnicos essenciais necessários para o arquivo funcionar.

### 🔍 Verificar Metadados Removidos

Para verificar se os metadados foram removidos:

```bash
ffprobe -v quiet -print_format json -show_format -show_streams video_clean.mp4
```

ou no n8n Execute Command:

```bash
ffprobe -v quiet -print_format json -show_format video_clean.mp4
```

### 💡 Dicas e Explicações Importantes

1. **Performance**: Usar `-codec copy` é muito mais rápido pois não re-encoda o vídeo (copia direto os streams)
2. **Qualidade**: Mantém qualidade original (100% igual) - não perde qualidade
3. **Tamanho**: Arquivo final tem tamanho similar ao original (pode ser ligeiramente menor por remover metadados)
4. **Tempo**: Limpeza leva segundos, não minutos (geralmente 1-5 segundos)
5. **Resultado**: O vídeo ficará "limpo" sem qualquer informação que identifique sua origem
6. **Uso**: Perfeito para não parecer que é vídeo original baixado

### ⚠️ Importante - Como Funciona

- `-map_metadata -1` remove TODOS os metadados do container do vídeo
- `-metadata campo=` remove campos específicos (o `=` vazio remove o valor)
- `-codec copy` mantém os streams de vídeo/áudio sem alteração (não re-encoda)
- Resultado: Vídeo idêntico ao original, mas sem qualquer informação de origem

### 📸 Exemplo Visual do Comando

**Antes (com metadados):**
```
ffprobe video.mp4
→ title: "TikTok Video"
→ artist: "username"
→ date: "2025-01-09"
→ encoder: "TikTok"
```

**Depois (sem metadados):**
```
ffprobe video_clean.mp4
→ Apenas metadados técnicos (encoder: Lavf, major_brand: isom)
→ Nenhuma informação de TikTok ou autor
```


## ⚠️ Observações

1. **Metadados:** Use FFmpeg no n8n para remover metadados (veja seção acima).

2. **ffmpeg:** Opcional mas recomendado. Use o comando fornecido no n8n após o download.

3. **Vídeos Privados:** Alguns vídeos podem requerer autenticação.

4. **Rate Limiting:** Para uso em produção, considere adicionar rate limiting para evitar abuso.

5. **VPS:** Para usar em VPS, certifique-se de que:
   - Python 3.8+ está instalado
   - ffmpeg está instalado (para limpeza de metadados no n8n)
   - Firewall permite acesso à porta escolhida

## 🐛 Troubleshooting

**Erro: "Vídeo privado"**
- Alguns vídeos requerem login. Pode ser necessário adicionar cookies de sessão.

**Erro: "Video unavailable"**
- O vídeo pode ter sido removido ou não estar mais disponível.

**Erro: "yt-dlp não encontrado"**
- Instale: `pip install yt-dlp`

## 📦 Estrutura do Projeto

```
/
├── app.py              # API Flask principal
├── requirements.txt    # Dependências Python
├── downloads/          # Pasta temporária para vídeos (criada automaticamente)
└── README_API.md      # Este arquivo
```

## 📁 Por que há vídeos na pasta downloads?

Se você encontrar vídeos na pasta `downloads/`, isso é normal. Eles são arquivos temporários criados durante o processo de download.

### Explicação dos Arquivos:

1. **`tiktok_XXXXXX.mp4`** - Vídeos originais baixados
   - Criados durante o download do TikTok
   - Contêm metadados originais
   - São removidos automaticamente após o envio para o cliente
   - Podem ficar se:
     - O download do cliente foi interrompido
     - O servidor foi reiniciado antes da limpeza
     - Houve erro durante o envio

2. **`clean_XXXXXX.mp4`** - Vídeos com metadados limpos
   - Criados durante testes da funcionalidade de limpeza
   - Versões processadas com metadados removidos
   - Também são temporários

**Nota:** A API remove arquivos automaticamente após enviar para o cliente. Arquivos que ficam são normalmente de testes ou de downloads interrompidos. Você pode deletá-los manualmente sem problemas:

```bash
# Limpar todos os vídeos temporários
Remove-Item downloads\*.mp4  # Windows
# ou
rm downloads/*.mp4           # Linux/Mac
```

## 🔄 Atualizações

Mantenha o yt-dlp atualizado para melhor compatibilidade:

```bash
pip install --upgrade yt-dlp
```

