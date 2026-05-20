---
name: youtube-downloader-logging
description: >-
  Define onde adicionar logs ao implementar feature nova ou extensão no
  YouTube Downloader (core, UI, download). Use após feature ou UI view, ao
  revisar observabilidade, ou ao evitar bugs opacos sem errors.log.
disable-model-invocation: true
---

# YouTube Downloader — observabilidade (features)

Checklist ao **concluir** implementação de feature ou tela. Não substitui hooks globais em [`logging_config.py`](../../../src/youtube_downloader/core/logging_config.py). Depuração de bugs: skill [youtube-downloader-bugfix](../youtube-downloader-bugfix/SKILL.md).

## Padrão

```python
from youtube_downloader.core.logging_config import get_logger

logger = get_logger(__name__)  # → youtube_downloader.<module>
```

Arquivos: `logs/app.log` (DEBUG+), `logs/errors.log` (ERROR+). Não versionar `logs/`.

## Onde vale log (percorrer em 1–2 min)

| Onde | O quê logar | Nível |
|------|-------------|-------|
| `core/` — settings, histórico, I/O | Falha ler/gravar JSON; valor inválido após `_coerce_*` | `warning` / `error` |
| `core/downloader.py` | Início/fim/cancelamento/falha de job; FFmpeg ausente; merge | `info` / `error`; `exception` no `except` |
| `core/metadata.py` | Preview falhou (URL + motivo curto) | `warning` |
| `core/download_job_builder.py` | Job inválido ou opção incoerente antes do download | `warning` |
| `app.py` | Notificação, abrir pasta, wiring crítico | `exception` no `except` |
| `ui/*_view.py` | Ação destrutiva ou estado inconsistente | `info` / `warning` pontual |
| Diálogos / montagem UI pesada | `try/except` + `logger.exception` se além do hook Tk | `exception` |

## Já coberto (não duplicar)

- Exceções em callbacks Tk → `install_ui_exception_logging` em [`app.py`](../../../src/youtube_downloader/app.py).
- Thread principal e workers → `install_exception_hooks` em `__main__` / `main.py`.

## Não logar

- Conteúdo de cookies ou credenciais.
- Progresso contínuo (byte a byte) — usar UI / `ProgressEvent`.
- Cada evento de fila ou keystroke (spam em `app.log`).
- PII desnecessária.

## Antes de concluir a feature

- [ ] Percorrer a tabela acima nos arquivos **alterados** nesta tarefa.
- [ ] Adicionar log **só** onde falha futura seria opaca em `errors.log` / `app.log`.
- [ ] Manter mensagens em inglês nos logs (padrão do `core/`); UI em português.

## Referência

Exemplos existentes: `core/downloader.py`, `ui/downloads_view.py`, `app.py` (`logger.exception` em handlers).
