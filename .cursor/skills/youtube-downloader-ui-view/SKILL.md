---
name: youtube-downloader-ui-view
description: >-
  Implementa ou estende telas PySide6 (nova view, painel, fila,
  Biblioteca, Histórico). Use ao criar ui_qt/*_view.py, sidebar, callbacks,
  preview, fila de URLs ou ao mover UI para fora de main_window.py.
disable-model-invocation: true
---

# YouTube Downloader — UI (PySide6)

Playbook para telas e widgets. Fluxo fila/Baixar/cancelar: [docs/ux-downloads-queue.md](../../../docs/ux-downloads-queue.md). Threading: [AGENTS.md](../../../AGENTS.md). Regras Qt: [`.cursor/rules/ui-qt.mdc`](../../rules/ui-qt.mdc).

## Onde colocar código

| O quê | Onde |
|-------|------|
| Layout, eventos, labels, botões | `src/youtube_downloader/ui_qt/<nome>_view.py` |
| Fila de eventos, worker, navegação | `src/youtube_downloader/ui_qt/main_window.py` |
| Lógica testável (scan, fila FIFO) | `src/youtube_downloader/core/` |

Meta: **&lt; ~30 linhas** novas em `main_window.py` por feature (callbacks + registro no `QStackedWidget`).

## Nova página na sidebar

1. Entrada em `ui_qt/nav_sidebar.py` → `NavSidebar.ITEMS`
2. Instanciar view em `main_window.py` → `self._stack.addWidget(view)` + índice em `_switch_view`
3. `NavSidebar` chama `on_select` → `setCurrentIndex`

## Threading (obrigatório)

```text
Main: usuário → view → callback → start_download_thread
Worker (QThread): YoutubeDownloader.download → EventBridge.emit_progress
Main: signal progress → MainWindow._handle_event → views
```

- **Nunca** atualizar widgets Qt no worker.
- Preview: debounce URL → thread `fetch_preview` → `EventBridge` / `PREVIEW_READY`.

## Estilo

- QSS e `apply_theme` em `ui_qt/theme.py`.
- Textos da UI em **português**.

## Callbacks na view

Injetar no `__init__` (ver `downloads_view`, `history_view`).

## Verificação

- [ ] `python main.py` ou `python -m youtube_downloader`
- [ ] `python -m pytest`
- [ ] Não importar `PySide6` em `core/`
