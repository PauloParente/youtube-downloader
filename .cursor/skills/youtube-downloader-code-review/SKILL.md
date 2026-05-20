---
name: youtube-downloader-code-review
description: >-
  Revisa diff ou alterações do YouTube Downloader contra AGENTS.md, rules e
  padrões do projeto (arquitetura, settings→DownloadJob, threading Tk, testes).
  Use após implementação por outro agente, antes de commit/PR, ou ao pedir code
  review, revisão de conformidade ou qualidade do patch.
disable-model-invocation: true
---

# YouTube Downloader — code review

Playbook de **revisão** (não implementação). Referências: [AGENTS.md](../../../AGENTS.md), [`.cursor/rules/`](../../rules/).

## Modo desta sessão

1. **Somente leitura** na primeira passagem: inspecionar diff (`git diff`, arquivos alterados); **não** editar código ainda.
2. Emitir relatório no formato abaixo.
3. Só corrigir código se o usuário pedir explicitamente após o relatório.

## Checklist

| Área | Verificar |
|------|-----------|
| Arquitetura | UI em `ui/`; lógica em `core/`; `app.py` só wiring (~20 linhas por feature) |
| Feature completa | Opção em Configurações → `AppSettings` + `_coerce_settings` → `DownloadJob` + `build_ytdl_opts` (skill `youtube-downloader-feature`) |
| Salvar vs baixar | Avançado em Configurações exige **Salvar**; campos da tela Downloads aplicam ao baixar |
| Threading | Worker → `ProgressEvent` → `queue.put`; **nunca** `CTk*` no worker |
| UI | `ui/theme.py`; `CTkLabel` sem borda — usar `CTkFrame` |
| Testes | Offline; sem rede/YouTube; `tmp_path` para JSON; novo comportamento em `tests/` |
| Escopo | Diff mínimo; sem refactor massivo, `ruff`/`mypy` não pedidos |
| Segredos / local | Sem `settings.json`, `history.json`, cookies, `dist/`, `logs/` no commit |
| Docs | README só se UX ou instalação mudou |
| Afirmações | Não aceitar "já funciona no download" sem rastrear até `build_ytdl_opts` |

Rodar mentalmente: `python -m pytest` deve ser exigido antes do merge.

## Formato de saída (obrigatório)

```markdown
## Resumo
[1–2 frases]

## Critical (corrigir antes de merge)
- [arquivo:linha ou trecho] — problema — sugestão

## Suggestion (recomendado)
- ...

## OK
- [o que está conforme]
```

Se não houver Critical, dizer explicitamente.

## Skills relacionadas (se o diff for desse tipo)

- Implementação de opção/download → conferir contra `youtube-downloader-feature`
- Telas / fila / sidebar → `youtube-downloader-ui-view`
- Versão / build → `youtube-downloader-release`

## Não fazer nesta skill

- Reescrever a feature no mesmo turno (mistura reviewer e autor).
- Aprovar sem olhar `tests/` quando `core/` ou regras de download mudaram.
- Pedir mudanças fora do escopo do diff (gold-plating).
