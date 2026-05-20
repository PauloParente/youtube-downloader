---
name: youtube-downloader-ui-view
description: >-
  Implementa ou estende telas CustomTkinter (nova view, painel, fila,
  Biblioteca, Histórico). Use ao criar ui/*_view.py, sidebar, callbacks,
  preview, fila de URLs ou ao mover UI para fora de app.py.
disable-model-invocation: true
---

# YouTube Downloader — UI (CustomTkinter)

Playbook para telas e widgets. Fluxo fila/Baixar/cancelar: [docs/ux-downloads-queue.md](../../../docs/ux-downloads-queue.md). Threading: [AGENTS.md](../../../AGENTS.md). Regras CTk: [`.cursor/rules/ui-customtkinter.mdc`](../../rules/ui-customtkinter.mdc).

## Onde colocar código

| O quê | Onde |
|-------|------|
| Layout, eventos, labels, botões | `src/youtube_downloader/ui/<nome>_view.py` |
| Fila de eventos, worker, navegação | `src/youtube_downloader/app.py` (~wiring só) |
| Lógica testável (scan, fila FIFO) | `src/youtube_downloader/core/` |

Meta: **&lt; ~20 linhas** novas em `app.py` por feature (callbacks + registro de view).

## Nova página na sidebar

1. Entrada em `ui/nav_sidebar.py` → `NavSidebar.ITEMS`
2. Instanciar view em `app.py` → `self._view_frames["id"] = view`
3. `NavSidebar` chama `on_select` → mostrar frame correto

Referência: `downloads_view`, `library_view`, `history_view`, `settings_view`.

## Threading (obrigatório)

```text
Main: usuário → view → callback → app._run_download_job
Worker: YoutubeDownloader.download → on_event(ProgressEvent) → queue.put
Main: after(50, _poll_queue) → DownloadsView.handle_progress_event
```

- **Nunca** atualizar `CTk*` no worker.
- Preview: debounce URL → thread `fetch_preview` → eventos `PREVIEW_*` na fila.

## Estilo e widgets

- Cores/estilos: `ui/theme.py` (`CARD_STYLE`, `ENTRY_STYLE`, `SECONDARY_BTN`, etc.).
- Textos da UI em **português**; símbolos/código em inglês.
- `CTkLabel` sem `border_width` — borda em `CTkFrame` (ver `history_view.py`).

## Callbacks na view

Injetar no `__init__`:

```python
def __init__(self, parent, *, on_save: Callable[[], None], ...) -> None:
```

Padrão: `downloads_view` (`on_start_download`, `on_enqueue_url`, `get_queue_snapshot`, …).

## Listas dinâmicas (fila, histórico)

- Snapshot em `core/` (ex. `DownloadQueue.snapshot()`).
- `_render_rows()`: destruir/recriar linhas no container (ver `history_view._render_rows`).
- Atualizar painel na **main thread** após mutar fila no `app.py`.

## Verificação

- [ ] Revisar observabilidade com skill `youtube-downloader-logging` (preview, fila, callbacks complexos)
- [ ] Smoke: `python main.py` ou `python -m youtube_downloader`
- [ ] `python -m pytest` se extrair função pura para `core/`
- [ ] Não crescer `app.py` com centenas de linhas de UI — extrair para `ui/`

## Não fazer

- Lógica yt-dlp ou `build_ytdl_opts` dentro da view.
- Bloquear a main thread com download ou preview sem worker + fila.
