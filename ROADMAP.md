# Roadmap — YouTube Downloader

Estado do produto em relação ao código na branch `main`. Para arquitetura e convenções, veja [AGENTS.md](AGENTS.md).

## Concluído

### Fase 1 — Confiabilidade
- Nomes de arquivo seguros (`restrictfilenames`, `windowsfilenames`)
- Playlists expandem para a fila (um download por vídeo; ver `core/playlist_urls.py`)
- `settings.json` (pasta, qualidade, áudio, playlist)
- Progresso de playlist na UI
- Priorização DASH em `QUALITY_FORMATS` (evita regressão para 360p)

### Fase 2 — Interface
- Layout em seções (cards) na tela de download
- **Sidebar**: Downloads, Biblioteca, Histórico, Configurações
- Página **Configurações** (substitui o antigo diálogo Preferências)
- Página **Histórico** com persistência em `history.json`
- Colar URL (`Ctrl+V`); atalho `Ctrl+,` para Configurações
- Tema visual unificado (`ui/theme.py`)
- Ícones de atalho no topo (configurações, ajuda)

### Fase 3 — Manutenção
- Testes pytest em `tests/` (35+ testes, foco em `core/`)
- Script `update-deps.ps1`
- Checklist de release no README
- Repositório no GitHub: CI (Windows + Ubuntu), CONTRIBUTING, `settings.example.json`

### Fase 4 — Arquitetura e opções de download
- **`DownloadsView`** extraída de `app.py` (`ui/downloads_view.py`); `app.py` como shell (fila de eventos, worker, navegação)
- Preferências avançadas ligadas ao download: `build_download_job` + `build_ytdl_opts` (formato MP4/WebM, bitrate MP3, banda, legendas, notificações, cookies)
- Mensagem de merge dinâmica (MP4 vs WebM)
- Notificações ao concluir (`core/notifications.py` — Linux/macOS/Windows)
- Recuperação da UI após download (`force_release_download_ui`, botão Limpar URL)

### Fase 5 — Uso no dia a dia (entrega recente)
| Área | O que existe hoje |
|------|-------------------|
| **Downloads** | Botões Abrir pasta / Abrir arquivo; status pós-download; preview de playlist com contagem de vídeos |
| **Fila** | URLs de vídeo (`watch?v=`); playlists expandem para N itens; remover, limpar; **sequencial** (`core/download_queue.py`, `core/playlist_urls.py`) |
| **Histórico** | Abrir pasta/arquivo, **baixar de novo** (↻), **excluir** (🗑); `source_url` em `history.json` |
| **Biblioteca** | Lista + **filtro por nome** na pasta de destino (`ui/library_view.py`, `core/library_scan.py`) |
| **Configurações** | Tema claro/escuro (`appearance_mode`); caminho para `cookies.txt`; rótulo **Idioma das legendas** (não traduz a UI) |
| **Perfil de exportação** | Compatível Windows (H.264) vs melhor qualidade (AV1/VP9); padrão `compatible` |
| **About** | Botão Ver logs |

---

## Backlog (conforme demanda)

Itens **não** implementados ou só parcialmente.

| Item | Situação atual | Próximo passo sugerido |
|------|----------------|------------------------|
| **Fila de downloads (UI)** | Lista, remover, limpar; spec em [docs/ux-downloads-queue.md](docs/ux-downloads-queue.md) | Persistir fila; URL editável ao enfileirar durante download; *Parar tudo* |
| **Biblioteca** | Lista + filtro por nome; botão Abrir arquivo | Abrir pasta de destino, miniaturas ou metadados opcionais |
| **Arrastar URL** | Não feito | Drag-and-drop (ex. `tkinterdnd2`); validar Windows e Linux |
| **MKV** | Reconhecido no scan; não é opção de merge | Estender `video_format` + testes FFmpeg |
| **Idioma da interface (i18n)** | `language` só afeta legendas no yt-dlp | i18n completo ou manter só “idioma das legendas” |
| **Runtime JS (Deno)** | Documentado no README | Aviso na UI quando yt-dlp precisar de challenge solver |
| **Duplicação Downloads ↔ Config** | Pasta/qualidade/áudio em duas telas | Unificar UX (defaults só em Configurações, por exemplo) |
| **Onboarding Linux no README** | Seção Linux + Tk/FFmpeg documentados | Manter alinhado ao testar novas distros |

### Engenharia (baixa urgência)
- Mais testes: merge settings + job, `force_release_download_ui` (mocks)
- Refinar paleta **light** em `ui/theme.py` se o modo claro precisar de ajustes visuais
- Export assistido de cookies do navegador (evolução do `cookies.txt` manual)

---

## Ordem sugerida para o backlog

1. ~~Fila com lista visível~~ (feito)
2. Biblioteca: **abrir pasta** de destino e polish da listagem
3. Drag-and-drop de URL
4. MKV e demais formatos, se houver demanda
5. Aviso na UI para runtime JS (Deno), se yt-dlp exigir

---

## Referência rápida: o que já vai de ponta a ponta

- Preview (título, thumbnail) → download (qualidade, MP4/WebM, MP3, playlist, cancelar)
- Configurações salvas → refletidas no próximo download via `DownloadJob`
- Fila sequencial, histórico, biblioteca da pasta de destino, tema e cookies
- Build `.exe` + FFmpeg embutido (Windows, `build.ps1`)

Para instalação e uso, veja [README.md](README.md).
