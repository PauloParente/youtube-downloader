---
name: youtube-downloader-bugfix
description: >-
  Investiga e corrige bugs no YouTube Downloader começando por logs/errors.log
  e app.log. Use ao corrigir falha, crash, erro na UI, download que falha,
  diálogo em branco, exceção em callback Tk ou ao pedir depuração com logs.
disable-model-invocation: true
---

# YouTube Downloader — bugfix (logs primeiro)

Playbook para **corrigir** bugs. Infraestrutura de logging: [AGENTS.md](../../../AGENTS.md) (seção *Depuração de bugs*). Regras: [`.cursor/rules/`](../../rules/).

## Antes de editar código

1. Ler as **últimas linhas** de `logs/errors.log` na raiz do projeto (dev) ou ao lado do `.exe` (dist) — pasta via `get_project_root()` em `config.py`.
2. Se `errors.log` estiver vazio ou sem entrada recente, ler `logs/app.log`.
3. **Não** assumir a causa só pelo sintoma na UI; **não** commitar arquivos em `logs/`.

## Interpretar o stack

| Logger / mensagem | Origem provável |
|-------------------|-----------------|
| `youtube_downloader.ui.callback` — *Exceção em callback da interface* | Botão/comando/`after` Tk (hook `install_ui_exception_logging`) |
| `youtube_downloader.unhandled` | Thread principal ou worker sem `try/except` |
| `youtube_downloader.downloader` | yt-dlp, FFmpeg, merge, cancelamento |
| `youtube_downloader.downloads_view` / outra view | Preview, fila, UI na main thread |
| `youtube_downloader.settings` / `download_history` | JSON corrompido ou I/O |

## Fluxo

| Passo | Ação |
|-------|------|
| 1 | Ler `errors.log` → `app.log` se necessário |
| 2 | Identificar módulo e linha no stack trace |
| 3 | Reproduzir fluxo mínimo na UI se não houver exceção (bug só visual) |
| 4 | Corrigir com **diff mínimo**; sem refactor em massa |
| 5 | `python -m pytest` |
| 6 | Pedir ao usuário re-testar o fluxo que gerou o log |

## Não fazer

- Editar código antes de consultar os logs (salvo bloqueio óbvio sem app rodando).
- Refatorar arquivos não relacionados ao bug.
- Afirmar causa sem evidência em log ou reprodução.
- Instrumentar retroativamente todo o projeto — só o necessário para o fix (observabilidade nova: skill `youtube-downloader-logging`).

## Depois do fix (opcional)

Se o bug revelou falha **sem** log útil, adicionar `logger.warning` / `logger.exception` no ponto opaco seguindo [youtube-downloader-logging](../youtube-downloader-logging/SKILL.md).
