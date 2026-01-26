#!/bin/bash
# Script para verificar se os cookies estão sendo encontrados nos logs

echo "📊 Verificando logs do container para ver se cookies estão sendo usados:"
echo ""
echo "docker logs content-orchestrator 2>&1 | grep -i cookie"
echo ""
echo "📋 Verificar se o caminho está sendo resolvido corretamente:"
echo ""
echo "docker exec content-orchestrator python3 -c \"
import os
import sys
sys.path.insert(0, '/app')
from app.services.downloader.service import DownloaderService
ds = DownloaderService()
path = ds._resolve_cookies_path()
print(f'Cookies path: {path}')
if path:
    print(f'File exists: {os.path.exists(path)}')
    print(f'File readable: {os.access(path, os.R_OK)}')
    print(f'File size: {os.path.getsize(path)} bytes')
    print(f'Permissions: {oct(os.stat(path).st_mode)}')
else:
    print('No cookies file found!')
\""
echo ""
echo "🧪 Testar download manualmente dentro do container:"
echo ""
echo "docker exec content-orchestrator python3 -c \"
import yt_dlp
opts = {
    'cookiefile': '/app/data/cookies.txt',
    'quiet': False,
    'no_warnings': False,
}
try:
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info('https://www.youtube.com/shorts/YPD6K509zfI', download=False)
        print('SUCCESS: Video info retrieved')
        print(f'Title: {info.get(\"title\")}')
except Exception as e:
    print(f'ERROR: {e}')
\""
