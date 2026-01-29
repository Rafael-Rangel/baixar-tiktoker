# 🎬 API de Download de Vídeos TikTok

API Flask para baixar vídeos do TikTok usando múltiplos serviços gratuitos. Projetada para ser usada com n8n e deploy em VPS com Docker.

## 🚀 Início Rápido

### Para desenvolvimento local:

```bash
# Instalar dependências
pip install -r requirements.txt

# Rodar API
python app.py
```

A API estará disponível em `http://localhost:5000`

### Para produção na VPS:

Consulte o guia completo: **[INSTALACAO_RAPIDA.md](INSTALACAO_RAPIDA.md)**

## 📚 Documentação

- **[README_API.md](README_API.md)** - Documentação completa da API
- **[INSTALACAO_RAPIDA.md](INSTALACAO_RAPIDA.md)** - Guia rápido de instalação na VPS
- **[DEPLOY_VPS.md](DEPLOY_VPS.md)** - Guia detalhado de deploy e configuração

## 🔧 Arquivos Principais

- `app.py` - API Flask principal
- `requirements.txt` - Dependências Python
- `Dockerfile` - Imagem Docker para produção
- `docker-compose-snippet.yml` - **CÓDIGO PARA COPIAR** no seu `docker-compose.yml` da raiz da VPS

## 📦 Estrutura do Projeto

```
.
├── app.py                      # API Flask
├── requirements.txt            # Dependências
├── Dockerfile                  # Build Docker
├── docker-compose.yml          # Docker Compose exemplo
├── docker-compose-snippet.yml  # Snippet para seu docker-compose.yml
├── README.md                   # Este arquivo
├── README_API.md              # Documentação completa
├── INSTALACAO_RAPIDA.md       # Guia rápido
├── DEPLOY_VPS.md              # Guia detalhado
└── downloads/                  # Pasta temporária (vazia)
```

## 🌐 Endpoints

- `GET /health` - Health check
- `POST /download` - Download de vídeo TikTok

Consulte [README_API.md](README_API.md) para detalhes completos.

## 🔗 Integração com n8n

Veja exemplos de integração no [README_API.md](README_API.md#-integração-com-n8n).

## 🧹 Limpeza de Metadados

Instruções completas sobre como limpar metadados de vídeos usando FFmpeg no n8n estão no [README_API.md](README_API.md#-limpeza-de-metadados).

## 📝 Licença

Este projeto é fornecido como está, para fins educacionais e de pesquisa.

