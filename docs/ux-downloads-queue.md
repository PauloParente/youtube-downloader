# UX — Downloads e fila

Especificação do comportamento da tela **Downloads** (campo URL, fila, Baixar, cancelar). Implementação: `ui/downloads_view.py`, `app.py`, `core/download_queue.py`.

## Modelo

| Conceito | Descrição |
|----------|-----------|
| **Download atual** | Um job em execução; URL no campo durante o download; linha *Baixando agora:* |
| **Fila (pendentes)** | URLs aguardando FIFO; lista na UI **não** inclui o item em execução |

Um único vídeo sem enfileirar = fila vazia na lista + **Baixar** no campo. Não há “modo sem fila” separado.

## Antes (ocioso)

- Preview com debounce na URL do campo.
- **+ Adicionar à fila**: valida URL YouTube; dedupe; log se duplicata; **não** inicia download.
- **Baixar**:
  1. Campo com URL válida → inicia **essa** URL (fila não é consumida primeiro).
  2. Campo vazio e fila com itens → `pop_next` e inicia o primeiro pendente.
  3. Campo vazio e fila vazia → erro no log.
- Opções da tela Downloads aplicam ao próximo job ao baixar; Configurações avançadas após **Salvar** (ver AGENTS.md).

## Durante download

| Controle | Estado |
|----------|--------|
| Baixar | Desabilitado |
| Cancelar | Ativo (só o job atual) |
| Campo URL / Limpar URL / Ctrl+V | Habilitados (preview pausado) |
| + Adicionar à fila | Habilitado |
| Remover item / Limpar fila | Habilitado (só pendentes) |
| Preview | Pausado |

- Um download por vez (sequencial).
- **Limpar fila** não cancela o download ativo.

## Depois (evento terminal)

| Evento | UI | Fila |
|--------|-----|------|
| **DONE** | Sucesso; libera controles | Próximo pendente inicia **automaticamente** |
| **CANCELLED** | Cancelado; libera controles | Próximo pendente inicia **automaticamente** |
| **ERROR** | Erro; libera controles | **Não** avança automaticamente |

Notificação desktop: uma por DONE (se ativada em Configurações).

## Cancelar vs parar tudo

- **Cancelar**: interrompe só o atual; remove arquivos parciais (`.part`, faixas `.fNNN.`, etc.) da pasta; depois segue a fila (como DONE/CANCELLED). Itens já concluídos numa playlist em curso não são apagados.
- **Limpar fila**: remove apenas pendentes.
- **Parar tudo** (backlog): cancelar ativo + esvaziar fila — não implementado.

## Checklist manual de aceite

1. Só URL no campo → Baixar → um vídeo; fila vazia.
2. Três na fila, campo vazio → Baixar → sequência automática dos três.
3. Durante download → enfileirar quarto → roda após os anteriores.
4. Cancelar no meio → seguintes da fila continuam.
5. Erro no primeiro → fila **não** avança sozinha.
6. Limpar fila durante download → pendentes somem; ativo continua.
