from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from app.core.config import get_settings
from app.core.logging import setup_logging
from app.api.routes import fetch, select, download, confirm, health, n8n, test_download

setup_logging()
settings = get_settings()

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# Include Routers
app.include_router(n8n.router, prefix=f"{settings.API_V1_STR}/n8n", tags=["n8n"])
app.include_router(fetch.router, prefix=f"{settings.API_V1_STR}/fetch", tags=["Fetch"])
app.include_router(select.router, prefix=f"{settings.API_V1_STR}/select", tags=["Select"])
app.include_router(download.router, prefix=f"{settings.API_V1_STR}/download", tags=["Download"])
app.include_router(confirm.router, prefix=f"{settings.API_V1_STR}/confirm_publish", tags=["Confirm"])
app.include_router(test_download.router, prefix=f"{settings.API_V1_STR}/test-download", tags=["Test"])
app.include_router(health.router, tags=["Health"])

@app.get("/", response_class=HTMLResponse)
def root():
    return """
    <!DOCTYPE html>
    <html lang="pt-br">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Content Orchestrator</title>
        <style>
            body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 2rem; line-height: 1.6; background-color: #f4f4f9; color: #333; }
            .container { background: white; padding: 2rem; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
            h1 { color: #2c3e50; margin-bottom: 0.5rem; }
            .status { display: inline-block; padding: 0.25rem 0.75rem; border-radius: 999px; background-color: #def7ec; color: #03543f; font-weight: bold; font-size: 0.875rem; margin-bottom: 2rem; }
            .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 1.5rem; }
            .card { border: 1px solid #e5e7eb; border-radius: 6px; padding: 1.5rem; transition: all 0.2s; }
            .card:hover { border-color: #3b82f6; box-shadow: 0 4px 6px rgba(59, 130, 246, 0.1); }
            h2 { font-size: 1.25rem; margin-top: 0; }
            a { color: #2563eb; text-decoration: none; font-weight: 500; }
            a:hover { text-decoration: underline; }
            code { background: #f3f4f6; padding: 0.2rem 0.4rem; border-radius: 4px; font-size: 0.9em; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Content Orchestrator</h1>
            <div class="status">● Sistema Operacional</div>
            
            <p>Bem-vindo ao painel de controle da API de Orquestração de Conteúdo. Este sistema é controlado via API (n8n), mas você pode usar os links abaixo para monitoramento e testes manuais.</p>
            
            <div class="grid">
                <div class="card">
                    <h2>📚 Documentação</h2>
                    <p>Interface interativa para testar todos os endpoints da API.</p>
                    <a href="/docs">Acessar Swagger UI &rarr;</a>
                </div>
                
                <div class="card">
                    <h2>🔍 Especificação</h2>
                    <p>Documentação técnica em formato Redoc.</p>
                    <a href="/redoc">Acessar Redoc &rarr;</a>
                </div>
                
                <div class="card">
                    <h2>⚡ Endpoints Principais</h2>
                    <ul style="padding-left: 1.2rem; margin: 0;">
                        <li><code>POST /v1/fetch/run</code></li>
                        <li><code>POST /v1/select</code></li>
                        <li><code>POST /v1/download</code></li>
                    </ul>
                </div>
            </div>
            
            <p style="margin-top: 2rem; color: #6b7280; font-size: 0.875rem;">Powered by FastAPI & n8n</p>
        </div>
    </body>
    </html>
    """
