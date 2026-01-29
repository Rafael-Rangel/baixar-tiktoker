# 🍪 Criar Arquivo cookies.txt Apenas com Cookies do Urlebird

O arquivo copiado parece ser o arquivo grande com cookies de vários sites. Precisamos criar um arquivo limpo apenas com cookies do Urlebird.

## Na VPS, Execute:

```bash
# Criar arquivo apenas com cookies do Urlebird
cat > /root/cookies_urlebird.txt << 'EOF'
.urlebird.com	TRUE	/	FALSE	1804213800	_ga_LC23RQB8HX	GS2.1.s1769653799$o3$g0$t1769653799$j60$l0$h0
.urlebird.com	TRUE	/	FALSE	1804213800	_ga	GA1.2.2141088358.1769644462
.urlebird.com	TRUE	/	FALSE	1769740199	_gid	GA1.2.867063945.1769644464
.urlebird.com	TRUE	/	TRUE	1803349800	usprivacy	1---
.urlebird.com	TRUE	/	FALSE	1777420464	sharedid	9db1174e-3d79-4394-9c59-11afa4a3c3f1
.urlebird.com	TRUE	/	FALSE	1777420464	sharedid_cst	znv0HA%3D%3D
.urlebird.com	TRUE	/	FALSE	1770249264	panoramaId_expiry	1770249264396
.urlebird.com	TRUE	/	FALSE	1792972464	_cc_id	dbf68c8c1e0d5b391a306c03cbfc87b1
.urlebird.com	TRUE	/	FALSE	1770249264	panoramaId	b51b18f3a2f6b161d5f9448451a7185ca02cfee5ca310a71d701d82cb67c5b26
urlebird.com	FALSE	/	TRUE	1769730865	_adplus_id	201666.11683067863
urlebird.com	FALSE	/	FALSE	1770249265	adplusId	201666.11683067863
urlebird.com	FALSE	/	FALSE	1770249265	adplusId_cst	znv0HA%3D%3D
urlebird.com	FALSE	/	FALSE	1770249265	adplusId_last	Wed%2C%2028%20Jan%202026%2023%3A54%3A25%20GMT
urlebird.com	FALSE	/	FALSE	1769740199	f59ff8f2f4dad6d42577b2feb08af481831e7e8e	dbec074218e50711u0THmIXBRE-gXuhyACCaZg
.urlebird.com	TRUE	/	FALSE	1803349802	cto_bundle	cSHF6183aVFJRWQwaVBaOVNqUGFqUXJXJTJGVGJWVU1YdWhWUUlIOEpIJTJCcE9NOHROQSUyQjFGaDI2OHRwdWpBeFZoOThYVHNQWkZQbCUyQkx5Q2hVczJoZFVsUTdQQ2I1b2I0bkIzWjB4S2FaR0VGTEV6NTQyQm1nallMJTJCSUdtV1V0ZXQyaWdNRm1HeHRZeWZtNGN5eGxkd0JSeGpGRjNOSVV4b1BHSzRFNzFLWDU5SXQ0bG5uc1NLWmtxdnUzV0FpazNYbXAzaFRY
.urlebird.com	TRUE	/	FALSE	1803349799	cto_bidid	na_Gzl9uQ1NqTEdTUmFoZURlQk52NnVMOW55Y3JHQ1ZKdnJnRTVhaXBuUlluZG1LR3Q1MEZnTU1DQyUyQlF2b3hvRjNUSGR5S2JEVTZwOG5WZ0FydiUyQnBKd2RPYVNFdWxCMFpUUyUyRlczcTBlZERDeSUyRmxwWGQ2bUtiZjNqckdtVXFUbDZ4bHA1WjlkN3V3YSUyQjI1S2RlZ0ZZNkhpNGx3JTNEJTNE
.urlebird.com	TRUE	/	TRUE	1769666067	fidflexlastcheck	1
.urlebird.com	TRUE	/	TRUE	1785196467	firstid	599f8569cd9b412e80a2fbc59c7f0de4
.urlebird.com	TRUE	/	TRUE	1785196467	firstid_flex_type	0
.urlebird.com	TRUE	/	FALSE	1803349799	cto_dna_bundle	SpfDhF83aVFJRWQwaVBaOVNqUGFqUXJXJTJGVGIyVHg1Tnl0dGViYXVUVVVPN3VSS1VhRUI5SHlTT2tHSXRNSHFhQ0R1JTJGbDI3cmFhNWhwazlKanFBY1habERLdnclM0QlM0Q
.urlebird.com	TRUE	/	FALSE	1769653859	_gat_gtag_UA_156932907_1	1
.urlebird.com	TRUE	/	TRUE	1801189798	cf_clearance	_8YPFesjCHtRGJIs_LiCwov7USExDsO1N3V2scAaD_s-1769653797-1.2.1.1-npPdNoRA0d52P_GoKL0CJQz_CGBEqRtPCAejjOEAIX9Uy6F1.HqWUwQEISqLBBx0hOMOTErjI9IZMGg_qIMIxRczjMY5RVrYpuRguA03W0Mr6TXTtnVBGmKTMUG1X57kiFoh64x_T.mg7vp.S4QdJ3SK8cXU33bc6eMPC8xevjMRjswMixWP9qXdjhRbU6v8HcEoCaW.TOHJcDwVec9KZyHYmDL_ZuwXDdILRo9cjls
EOF

# Copiar para container
docker cp /root/cookies_urlebird.txt tiktok-downloader-api:/app/cookies.txt

# Verificar
docker exec tiktok-downloader-api head -5 /app/cookies.txt
```

## Ou Extrair do Arquivo Grande:

```bash
# Na VPS, extrair apenas cookies do Urlebird do arquivo grande
grep -i "^\.urlebird\.com\|^urlebird\.com" /root/cookies.txt > /root/cookies_urlebird.txt

# Verificar quantos cookies foram extraídos
wc -l /root/cookies_urlebird.txt

# Copiar para container
docker cp /root/cookies_urlebird.txt tiktok-downloader-api:/app/cookies.txt

# Verificar no container
docker exec tiktok-downloader-api head -5 /app/cookies.txt
```

## Depois de Copiar:

```bash
# Reiniciar container
docker compose restart tiktok-downloader-api

# Ver logs
docker logs -f tiktok-downloader-api
```

Você deve ver:
```
INFO:__main__:✓ X cookie(s) carregado(s) de /app/cookies.txt
```
