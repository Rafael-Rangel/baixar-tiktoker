FROM python:3.11-slim

WORKDIR /app

# Instalar dependências do sistema
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements e instalar dependências Python
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copiar código da aplicação
COPY app.py .

# Criar diretório de downloads com permissões corretas
RUN mkdir -p /app/downloads && chmod 755 /app/downloads

# Expor porta
EXPOSE 5000

# Usuário não-root para segurança (1000:1000 compatível com n8n)
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app
USER appuser

# Health check (curl já está instalado acima)
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:5000/health || exit 1

# Comando para rodar a aplicação
CMD ["python", "app.py"]

