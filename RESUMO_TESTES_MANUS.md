# Resumo de Testes - Playwright + Stealth vs Cloudflare Urlebird

**Data:** $(date)  
**Objetivo:** Testar bypass do Cloudflare Turnstile no Urlebird usando Playwright + Stealth  
**Username testado:** @oprimorico  
**URL:** https://urlebird.com/pt/user/oprimorico/

## Configuração Atual

### Bibliotecas Utilizadas
- **Playwright:** 1.57.0
- **playwright-stealth:** 2.0.1
- **Python:** 3.12
- **Sistema:** Linux (VPS)

### Melhorias Implementadas (baseadas nas suas sugestões)

1. ✅ **Headless "New"**: Playwright usa automaticamente `--headless=new`
2. ✅ **Random User-Agent**: Seleção aleatória entre Windows/Mac (evita detectar Linux/VPS)
3. ✅ **Movimentos de Mouse (Bezier)**: Simulação de movimentos curvos periódicos
4. ✅ **Persistent Context**: Carregamento e salvamento de cookies entre sessões
5. ✅ **Interações Humanas**: Scroll suave, tempos aleatórios, movimentos de mouse
6. ✅ **Stealth Completo**: Remoção de propriedades webdriver, plugins, etc.

## Teste 1: Playwright + Stealth (Modo Headless)

### Configuração
```python
browser = await p.chromium.launch(headless=True)
context = await browser.new_context(
    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64)...",
    viewport={'width': 1920, 'height': 1080},
    locale="pt-BR",
    timezone_id="America/Sao_Paulo"
)
stealth = Stealth()
await stealth.apply_stealth_async(page)
```

### Resultado
- ⏱️ **Tempo de espera:** 60 segundos (timeout)
- 📄 **Título da página:** "Um momento…" (permaneceu durante todo o teste)
- 🚫 **Status:** Cloudflare Turnstile NÃO foi resolvido automaticamente
- 📊 **HTML obtido:** 18,983 caracteres (página de desafio)
- ❌ **Vídeos encontrados:** 0

### Análise
O Cloudflare detectou a automação e manteve o desafio ativo. Mesmo com todas as melhorias de stealth, o Turnstile não foi resolvido automaticamente.

## Teste 2: Acesso Direto Simplificado

### Configuração
- Mesma configuração do Teste 1, mas sem interações adicionais
- Apenas: navegar → esperar 5s → verificar

### Resultado
- 📄 **Título:** "Um momento…"
- 🚫 **Status:** Mesmo resultado - desafio não resolvido
- 📊 **HTML contém '/video/':** False
- 📊 **HTML contém 'Um momento':** True

## Problemas Identificados

1. **Cloudflare Turnstile não resolve automaticamente**
   - Mesmo com stealth completo, o desafio permanece ativo
   - O título "Um momento…" não muda após 60 segundos

2. **Falta de cookies válidos**
   - Não há cookies de sessão anterior (`cf_clearance`)
   - Primeira visita sempre recebe desafio completo

3. **IP pode ser datacenter**
   - VPS geralmente tem IPs de datacenter
   - Cloudflare pode ser mais rigoroso com esses IPs

## Perguntas para o Manus

1. **Como você resolve o Turnstile automaticamente?**
   - Você usa cookies válidos (`cf_clearance`) de uma sessão real?
   - Há algum serviço de resolução de CAPTCHA integrado?
   - O Playwright resolve sozinho ou precisa de intervenção?

2. **Configurações específicas que funcionam:**
   - Qual User-Agent você usa exatamente?
   - Você usa modo headless ou visível?
   - Há alguma extensão ou configuração especial do navegador?

3. **Estratégia de cookies:**
   - Como você obtém e mantém cookies válidos?
   - Os cookies expiram rápido?
   - Precisa resolver manualmente na primeira vez?

4. **IP e ambiente:**
   - Você usa IP residencial ou datacenter?
   - Há diferença significativa no comportamento?

## Próximos Passos Sugeridos

1. Testar com cookies válidos exportados de navegador real
2. Testar em modo visível para ver o que acontece visualmente
3. Considerar serviço de resolução de CAPTCHA (2Captcha, AntiCaptcha)
4. Testar com IP residencial via proxy

## Código Atual (Resumo)

```python
# Configuração do navegador
browser = await p.chromium.launch(headless=True, args=[...])
context = await browser.new_context(
    user_agent=random.choice(user_agents),  # Windows/Mac
    viewport={'width': 1920, 'height': 1080},
    storage_state=storage_state  # Cookies salvos
)

# Aplicar stealth
stealth = Stealth()
await stealth.apply_stealth_async(page)

# Navegar e aguardar
await page.goto(url, wait_until="load")
await asyncio.sleep(8)
# ... movimentos de mouse, scroll, etc.
```

## Logs Detalhados

Ver arquivo: `/tmp/teste_playwright_1.log`
