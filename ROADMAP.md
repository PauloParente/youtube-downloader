# Roadmap — YouTube Downloader

Estado do produto em relação ao código na branch `main`. Para arquitetura e convenções, veja [AGENTS.md](AGENTS.md).

## Concluído

### Fase 1 — Confiabilidade
- Nomes de arquivo seguros (`restrictfilenames`, `windowsfilenames`)
- Checkbox *Baixar playlist inteira* (padrão: só o vídeo da URL)
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
- Testes pytest em `tests/` (23 testes, foco em `core/`)
- Script `update-deps.ps1`
- Checklist de release no README
- Repositório no GitHub: CI (Windows), CONTRIBUTING, `settings.example.json`

### Fase 4 — Arquitetura e opções de download
- **`DownloadsView`** extraída de `app.py` (`ui/downloads_view.py`); `app.py` como shell (fila de eventos, worker, navegação)
- Preferências avançadas ligadas ao download: `build_download_job` + `build_ytdl_opts` (formato MP4/WebM, bitrate MP3, banda, legendas, notificações, cookies)
- Mensagem de merge dinâmica (MP4 vs WebM)
- Notificações ao concluir (`core/notifications.py` — Linux/macOS/Windows)
- Recuperação da UI após download (`force_release_download_ui`, botão Limpar URL)

### Fase 5 — Uso no dia a dia (entrega recente)
| Área | O que existe hoje |
|------|-------------------|
| **Downloads** | Botões Abrir pasta / Abrir arquivo; status pós-download; marcar playlist no preview se a opção padrão estiver ativa |
| **Fila** | `+ Adicionar à fila` + processamento **sequencial** automático (`core/download_queue.py`) |
| **Histórico** | Abrir pasta, abrir arquivo, **baixar de novo** (↻); `source_url` em `history.json` |
| **Biblioteca** | Lista arquivos de mídia na pasta de destino (`ui/library_view.py`, `core/library_scan.py`) |
| **Configurações** | Tema claro/escuro (`appearance_mode`); caminho para `cookies.txt`; rótulo **Idioma das legendas** (não traduz a UI) |
| **About** | Botão Ver logs |

---

## Backlog (conforme demanda)

Itens **não** implementados ou só parcialmente.

| Item | Situação atual | Próximo passo sugerido |
|------|----------------|------------------------|
| **Fila de downloads (UI)** | Contador + enfileirar URL; sem lista editável | Mostrar URLs na fila, remover item, limpar fila |
| **Biblioteca** | MVP: listagem por pasta, botão Abrir | Filtro/busca, abrir pasta, miniaturas ou metadados opcionais |
| **Histórico** | Sem excluir entrada | Botão remover + persistir `history.json` |
| **Arrastar URL** | Não feito | Drag-and-drop (ex. `tkinterdnd2`); validar Windows e Linux |
| **MKV** | Reconhecido no scan; não é opção de merge | Estender `video_format` + testes FFmpeg |
| **Idioma da interface (i18n)** | `language` só afeta legendas no yt-dlp | i18n completo ou manter só “idioma das legendas” |
| **Runtime JS (Deno)** | Documentado no README | Aviso na UI quando yt-dlp precisar de challenge solver |
| **CI Linux** | CI só em `windows-latest` | Job `ubuntu-latest`: `pytest` + smoke import Tk |
| **Duplicação Downloads ↔ Config** | Pasta/qualidade/áudio em duas telas | Unificar UX (defaults só em Configurações, por exemplo) |

### Engenharia (baixa urgência)
- Mais testes: merge settings + job, `force_release_download_ui` (mocks)
- Refinar paleta **light** em `ui/theme.py` se o modo claro precisar de ajustes visuais
- Export assistido de cookies do navegador (evolução do `cookies.txt` manual)

---

## Ordem sugerida para o backlog

1. Atualizar documentação quando mudar comportamento (este arquivo + AGENTS.md)
2. Fila com **lista visível** e remoção de itens
3. Histórico: **excluir** item
4. Biblioteca: **busca/filtro**
5. **CI em Linux** (ambiente principal de desenvolvimento)
6. Drag-and-drop de URL
7. MKV e demais formatos, se houver demanda

---

## Referência rápida: o que já vai de ponta a ponta

- Preview (título, thumbnail) → download (qualidade, MP4/WebM, MP3, playlist, cancelar)
- Configurações salvas → refletidas no próximo download via `DownloadJob`
- Fila sequencial, histórico, biblioteca da pasta de destino, tema e cookies
- Build `.exe` + FFmpeg embutido (Windows, `build.ps1`)

Para instalação e uso, veja [README.md](README.md).
