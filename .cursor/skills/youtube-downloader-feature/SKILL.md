---
name: youtube-downloader-feature
description: >-
  Liga opções de Configurações ou Downloads ao download real via AppSettings,
  DownloadJob e build_ytdl_opts. Use ao adicionar preferência, qualidade,
  legendas, cookies, export_profile, formato WebM/MP3 ou ao afirmar que uma
  opção já funciona no download.
disable-model-invocation: true
---

# YouTube Downloader — feature (settings → download)

Playbook para opções que afetam o yt-dlp. Arquitetura: [AGENTS.md](../../../AGENTS.md). Regras: [`.cursor/rules/`](../../rules/).

## Antes de codar

- [ ] Ler em AGENTS.md: tabela *Implementado vs. pendente* e regra **Salvar** em Configurações.
- [ ] Opções da tela **Downloads** (pasta, qualidade, áudio, playlist) aplicam-se ao baixar; opções em **Configurações** exigem **Salvar** (ou valor já em `settings.json`).

## Checklist por camada

| Camada | Arquivo(s) | O que fazer |
|--------|------------|-------------|
| Persistência | `src/youtube_downloader/core/settings.py` | Campo em `AppSettings`; validação em `_coerce_settings` |
| Job | `core/models.py`, `core/download_job_builder.py` | Campo em `DownloadJob`; preencher em `build_download_job` |
| yt-dlp | `core/downloader.py` (`build_ytdl_opts`) | Mapear job → opções yt-dlp |
| Codec/format | `core/format_selectors.py` | Se mudar perfil, container ou seletor de stream |
| UI | `ui/settings_view.py`, `ui/downloads_view.py` | Controle visível; não só texto solto |
| Testes | `tests/test_download_opts.py` ou `test_<modulo>.py` | Assert offline, sem rede/YouTube |

## Fluxo

```text
settings.json → load_settings → _coerce_settings → AppSettings
DownloadsView + AppSettings → build_download_job → DownloadJob
DownloadJob → build_ytdl_opts → YoutubeDownloader.download
```

## Antes de concluir

- [ ] `python -m pytest` (ver [pytest.ini](../../../pytest.ini), `pythonpath = src`)
- [ ] README só se UX visível ou instalação mudou

## Não fazer

- Feature nova só em `app.py` (orquestração mínima).
- Checkbox em Configurações sem `DownloadJob` + `build_ytdl_opts`.
- Teste que baixa vídeo real ou depende de rede.
- Afirmar “implementado” sem percorrer a tabela acima.
