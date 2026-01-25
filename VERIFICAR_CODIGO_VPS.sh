#!/bin/bash
# Script para verificar qual código está rodando no container

echo "🔍 Verificando código no container..."
echo ""

# Verificar commit atual no diretório
echo "📋 Commit atual no diretório:"
cd ~/content-orchestrator
git log --oneline -1
echo ""

# Verificar arquivo dentro do container
echo "📋 Verificando código dentro do container:"
docker exec content-orchestrator cat /app/app/api/routes/n8n.py | head -30
echo ""

# Verificar se o endpoint existe
echo "📋 Testando endpoint diretamente:"
docker exec content-orchestrator curl -s http://localhost:8000/docs 2>/dev/null | grep -o "process-sources" | head -1 && echo "✅ Endpoint encontrado" || echo "❌ Endpoint não encontrado"
echo ""

# Verificar versão do código (data de modificação)
echo "📋 Data de modificação dos arquivos no container:"
docker exec content-orchestrator ls -la /app/app/api/routes/n8n.py
echo ""

echo "✅ Verificação concluída"
