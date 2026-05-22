# UX — Downloads e fila

Especificação do comportamento da tela **Downloads**, da tela **Fila** na sidebar e da fila em memória. Implementação: `ui_qt/downloads_view.py`, `ui_qt/downloads_preview.py`, `ui_qt/queue_view.py`, `ui_qt/main_window.py`, `core/download_queue.py`, `core/download_url_flow.py`, `core/queue_coordinator.py`.

## Onde está cada coisa na UI

| Tela | Conteúdo |
|------|----------|
| **Downloads** | Hero URL (validação visual, colar, **arrastar link**, + Fila, **Ver fila (N)**), preview (`EmptyState` vazio / skeleton / row), alerta de erro inline, barra **Vídeo \| Áudio** + qualidade, action dock (chip pasta destino, status humanizado, Baixar) |
| **Fila** (sidebar) | Duas colunas: **esquerda (maior)** — *Baixando agora* (`QueueNowPlayingCard`) + **Atividade**; **direita (menor)** — *Na fila* com `CompactMediaRow` e remover |

A lista de pendentes e o progresso do download em curso ficam na tela **Fila** (card *Baixando agora*). Na Downloads, o dock inferior mostra apenas mensagens de status resumidas (ex. “Baixando…”, “Download concluído.”).

## Modelo

| Conceito | Descrição |
|----------|-----------|
| **Download atual** | Um job em execução; URL no campo Downloads durante o download; card *Baixando agora* na tela Fila |
| **Fila (pendentes)** | URLs aguardando FIFO; cards na tela **Fila** **não** incluem o item em execução; metadados via `PreviewCache` (`core/preview_cache.py`) em background; a UI actualiza **card a card** (sem reconstruir a lista inteira) |
| **Transição entre vídeos** | Histórico gravado em background se ainda há fila; próximo job usa `continue_queue_for_url` (sem repersistir definições nem re-renderizar toda a fila) |

Um único vídeo sem enfileirar = fila vazia na lista + **Baixar** no campo. Não há “modo sem fila” separado.

## Playlists

- Link `playlist?list=…` ou *Playlist inteira* no diálogo (`watch?v=…&list=…`) → `core/playlist_urls.expand_playlist_urls` → N URLs `watch?v=` na fila (dedupe).
- **+ Fila** / **Baixar** com playlist no campo: expande em thread (“A obter vídeos da playlist…”); Baixar enfileira todos e inicia o primeiro pendente.
- Vídeo único no campo: **Baixar** inicia direto (sem passar pela fila).
- Cada job na fila é um vídeo (`noplaylist: true` no yt-dlp).

## Erros amigáveis e feedback

- Mensagens yt-dlp mapeadas em português via `core/download_errors.humanize_ytdlp_error` (log técnico mantido em **Atividade**).
- **Atividade** (tela Fila, coluna esquerda): fechado mostra «Última: …» e badge de linhas novas; abre automaticamente em **ERROR**; fecha após o primeiro **DONE** (persistido em `activity_log_expanded`). Mensagens de enfileirar na Downloads também aparecem aqui.
- Erro de download: status no dock + banner `#downloadAlert` acima do preview.
- Progresso (% e barra): card *Baixando agora* na tela **Fila** (modo indeterminado ao expandir playlist ou preparar próximo da fila).

## Atalhos (tela Downloads com foco)

| Atalho | Ação |
|--------|------|
| `Ctrl+V` | Colar URL (global na janela) |
| `Enter` | Baixar (se botão ativo; não dispara com foco no combo de qualidade) |
| `Esc` | Cancelar download em curso; senão limpar URL |

## Arrastar URL (drag-and-drop)

- No campo hero da tela **Downloads**, aceita `text/uri-list` e `text/plain` (ex. arrastar link do Explorer).
- Extrai a primeira URL YouTube (`core/text_utils.extract_url_from_drop_text` + `is_youtube_url`); preenche o campo e dispara o preview (mesmo fluxo que colar).
- URLs não-YouTube ou texto sem link são ignorados.

## Antes (ocioso)

- Preview com debounce na URL do campo (Downloads).
- **+ Fila**: resolve URL (expande playlist se for o caso); dedupe; log; prefetch de título/miniatura/duração (`PreviewCache`, até 3 pedidos em paralelo); **não** inicia download.
- **Baixar**:
  1. Campo com URL de **vídeo único** → inicia esse vídeo (fila não é consumida primeiro).
  2. Campo com **playlist** → expande, enfileira todos, `pop_next` e inicia o primeiro.
  3. Campo vazio e fila com itens → `pop_next` e inicia o primeiro pendente.
  4. Campo vazio e fila vazia → erro no log.
- Opções da tela Downloads aplicam ao próximo job ao baixar; Configurações avançadas após **Salvar** (ver AGENTS.md).

## Durante download

Ao iniciar um job (`_run_download_job`), a janela muda automaticamente para a tela **Fila** (inclui o primeiro vídeo e os seguintes da fila).

| Controle | Onde | Estado |
|----------|------|--------|
| Baixar | Downloads | Desabilitado |
| Cancelar | Downloads (rodapé) e Fila | Ativo — para tudo e esvazia fila |
| Pular | Fila | Ativo se houver pendentes |
| Campo URL / Limpar URL / Ctrl+V | Downloads | Habilitados (preview pausado) |
| + Fila | Downloads | Habilitado |
| Remover item (🗑) | Fila | Habilitado (só pendentes) |
| Preview | Downloads | Pausado |

- Um download por vez (sequencial).
## Depois (evento terminal)

| Evento | UI Downloads | UI Fila | Fila |
|--------|--------------|---------|------|
| **DONE** | Sucesso; libera controles | Atualiza progresso / próximo | Próximo pendente inicia **automaticamente** |
| **CANCELLED** | Cancelado; libera controles | — | Próximo pendente inicia **automaticamente** (exceto Cancelar total) |
| **ERROR** | Erro; libera controles | — | **Não** avança automaticamente |

Notificação desktop: uma por DONE (se ativada em Configurações).

## Cancelar e pular

- **Cancelar** (Downloads ou Fila, durante download): interrompe o vídeo atual, **esvazia a fila** e remove parciais (`.part`, etc.). No rodapé de Downloads o botão permanece **Cancelar** enquanto houver job ativo.
- **Pular** (só na tela **Fila**, com pendentes): cancela só o vídeo atual e inicia o **próximo** da fila.
- **Limpar URL** (Downloads, ocioso): substitui Cancelar quando não há download em curso.
- Entre vídeos da fila (após DONE): a UI mantém modo download (Cancelar + Pular na Fila) até a fila acabar.

## Checklist manual de aceite

1. Só URL no campo → Baixar → um vídeo; fila vazia na tela Fila.
2. Três na fila, campo vazio → Baixar → sequência automática; Fila mostra *Baixando agora* e pendentes a diminuir.
3. Durante download → **+ Fila** quarto URL → roda após os anteriores.
4. **Pular** na Fila → passa ao próximo sem esvaziar o resto da fila.
5. **Cancelar** em Downloads → para tudo e limpa fila.
6. Erro no primeiro → fila **não** avança sozinha.
7. Remover itens com 🗑 durante download → pendentes somem; ativo continua.
8. URL de playlist → Baixar → N itens na fila; sequência automática; histórico com uma entrada por vídeo.
9. Arrastar link `youtube.com` ou `youtu.be` para o campo hero → URL preenchida e preview agendado.
