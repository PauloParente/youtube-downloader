# Roadmap — YouTube Downloader

Melhorias implementadas (Fases 1–3) e backlog futuro (Fase 4).

## Concluído

### Fase 1 — Confiabilidade
- Nomes de arquivo seguros (`restrictfilenames`, `windowsfilenames`)
- Checkbox *Baixar playlist inteira* (padrão: só o vídeo da URL)
- `settings.json` (pasta, qualidade, áudio, playlist)
- Progresso de playlist na UI

### Fase 2 — Interface
- Layout em seções (cards)
- Barra de menu (Arquivo, Editar, Ajuda) e diálogo Preferências
- Colar / limpar URL (menu e atalhos)
- Limpar log
- Diálogo Sobre (versões app, yt-dlp, FFmpeg)
- Abrir pasta / último arquivo / logs via menu

### Fase 3 — Manutenção
- Testes pytest em `tests/`
- Script `update-deps.ps1`
- Checklist de release no README

## Fase 4 — Backlog (conforme demanda)

| Item | Descrição |
|------|-----------|
| Fila de downloads | Várias URLs em sequência com estado por item |
| Legendas | `writesubtitles` / idiomas PT+EN |
| Cookies | `cookies.txt` para conteúdo restrito |
| Tema claro/escuro | Toggle + persistir em settings |
| Arrastar URL | Drag-and-drop na janela (ex. tkinterdnd2) |
| Formatos extras | MKV/WebM além de MP4 |

## Ordem sugerida para Fase 4

1. Legendas (valor alto, esforço médio)
2. Tema claro/escuro
3. Fila de downloads
4. Cookies
5. Drag-and-drop
