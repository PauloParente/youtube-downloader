# UX — Downloads e fila

Especificação do comportamento da tela **Downloads**, da tela **Fila** na sidebar e da fila em memória. Implementação: `ui_qt/downloads_view.py`, `ui_qt/downloads_preview.py`, `ui_qt/queue_view.py`, `ui_qt/main_window.py`, `core/download_queue.py`, `core/download_url_flow.py`, `core/queue_coordinator.py`.

## Onde está cada coisa na UI

| Tela | Conteúdo |
|------|----------|
| **Downloads** | Hero URL (validação visual + tooltips, colar, **arrastar link**, + Fila), resumo/banner de fila, preview (`EmptyState` com CTAs / skeleton / row), barra **Vídeo \| Áudio** + qualidade **sempre visível**, faixa **Em curso** durante download, alerta de erro inline, action dock (chip pasta, **Abrir arquivo** após concluir, Baixar / Cancelar, menu ⋯) |
| **Os meus downloads** (sidebar) | Abas **Biblioteca** (ficheiros na pasta) e **Histórico** (metadados); menu ⋯ por linha |
| **Fila** (sidebar) | Banner de resumo, *Baixando agora* (Cancelar vermelho, Pular), **Atividade**, *Na fila* com CTAs; layout **responsivo**; atalhos **Esc** / **S** (com foco na Fila) |

### Layout responsivo (Fila)

Política: [`layout_breakpoints.py`](../src/youtube_downloader/ui_qt/layout_breakpoints.py) (`CONTENT_BREAKPOINT_COMPACT = 720`).

| Largura do painel Fila | Disposição |
|------------------------|------------|
| **≥ 720px** (`comfortable`) | Duas colunas: **esquerda (2/3)** — *Baixando agora* + Atividade; **direita (1/3)** — *Na fila* |
| **&lt; 720px** (`compact`) | Abas **Agora** \| **Na fila** (em vez de scroll vertical longo) |

Com a janela no mínimo (`900×680`), a Fila usa modo **compact**. Ao alargar a janela, passa automaticamente a duas colunas.

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

## Atalhos (tela Fila com foco)

| Atalho | Ação |
|--------|------|
| `Esc` | Cancelar download em curso (para tudo e esvazia fila) |
| `S` | Pular para o próximo da fila (se houver pendentes) |

Não disparam com foco num campo de texto (ex. log de Atividade expandido).

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
- Opções da tela Downloads (vídeo/áudio/qualidade) gravam em `settings.json` ao clicar em **Baixar**; Configurações avançadas após **Salvar** (ver AGENTS.md).
- **+ Fila** / playlist: banner informativo na Downloads («N vídeos adicionados…») além do log na Fila.
- Pasta de destino: chip no dock abre a pasta; menu ⋯ → **Alterar pasta de destino…** (`QFileDialog`).

## Durante download

Ao iniciar um job (`_run_download_job`), a janela muda para a tela **Fila** por padrão (`focus_queue_on_download` em Configurações → Geral). Se o utilizador voltar manualmente a **Downloads** durante o download, os jobs seguintes da mesma sessão **não** forçam a mudança de ecrã. A faixa **Em curso** na Downloads mostra título, estado, % e link «Ver na Fila».

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

- **Cancelar** (Downloads ou Fila, durante download): interrompe o vídeo atual, **esvazia a fila** e remove parciais (`.part`, etc.). No rodapé de Downloads aparece **Cancelar** (botão vermelho) enquanto houver job ativo; ações secundárias ficam no menu **⋯**.
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
