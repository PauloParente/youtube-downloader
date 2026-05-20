# Roadmap — YouTube Downloader

Melhorias implementadas (Fases 1–3) e backlog futuro (Fase 4).

## Concluído

### Fase 1 — Confiabilidade
- Nomes de arquivo seguros (`restrictfilenames`, `windowsfilenames`)
- Checkbox *Baixar playlist inteira* (padrão: só o vídeo da URL)
- `settings.json` (pasta, qualidade, áudio, playlist)
- Progresso de playlist na UI
- Priorização DASH em `QUALITY_FORMATS` (evita regressão para 360p)

### Fase 2 — Interface
- Layout em seções (cards) na tela de download
- **Sidebar** de navegação: Downloads, Biblioteca (placeholder), Histórico, Configurações
- Página **Configurações** (substitui o antigo diálogo Preferências e menus Arquivo/Editar/Ajuda)
- Página **Histórico** com persistência em `history.json`
- Colar URL (`Ctrl+V`); atalho `Ctrl+,` para Configurações
- Tema visual unificado (`ui/theme.py`)
- Ícones de atalho no topo (configurações, ajuda)

### Fase 3 — Manutenção
- Testes pytest em `tests/`
- Script `update-deps.ps1`
- Checklist de release no README
- Repositório preparado para GitHub: CI, CONTRIBUTING, `settings.example.json`

## Fase 4 — Backlog (conforme demanda)

| Item | Descrição |
|------|-----------|
| Biblioteca | Tela placeholder na sidebar — organizar arquivos baixados |
| Fila de downloads | Várias URLs em sequência com estado por item |
| Legendas | Integrado (`writesubtitles` via Configurações → `DownloadJob`) |
| Cookies | `cookies.txt` para conteúdo restrito |
| Tema claro/escuro | Toggle + persistir em settings |
| Arrastar URL | Drag-and-drop na janela (ex. tkinterdnd2) |
| Formatos extras | MKV além de MP4/WebM |
| Notificações / banda | Integrado no download; idioma da UI ainda só persistido em JSON |

## Ordem sugerida para Fase 4

1. Tema claro/escuro
3. Fila de downloads
4. Biblioteca (listagem real)
5. Cookies
6. Drag-and-drop
