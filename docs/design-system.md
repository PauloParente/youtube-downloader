# Design system — YouTube Downloader (PySide6)

Identidade visual centralizada em tokens Python e QSS global. Evitar `setStyleSheet` local e hex soltos nas views.

## Arquivos

| Arquivo | Papel |
|---------|--------|
| [`theme_tokens.py`](../src/youtube_downloader/ui_qt/theme_tokens.py) | Cores, espaçamento, tipografia, raios |
| [`theme.py`](../src/youtube_downloader/ui_qt/theme.py) | `build_dark_qss()` / `build_light_qss()`, `apply_theme()` |
| [`ui_qt/widgets/`](../src/youtube_downloader/ui_qt/widgets/) | Componentes reutilizáveis |
| [`ui_qt/icons.py`](../src/youtube_downloader/ui_qt/icons.py) | Ícones SVG embutidos |
| [`resources/icons/`](../src/youtube_downloader/resources/icons/) | SVGs (empacotados no `.exe`) |

## Tokens de cor (dark — GitHub-style)

| Token | Valor (dark) | Uso |
|-------|--------------|-----|
| `app_bg` | `#0D1117` | Fundo da janela |
| `sidebar_bg` | `#161B22` | Sidebar e coluna da title bar |
| `card_bg` / `card_border` | `#161B22` / `#30363D` | Cards (`#card`) |
| `input_bg` / `input_border` | `#0D1117` / `#30363D` | Campos de texto |
| `text_primary` / `text_secondary` / `text_muted` | `#FFFFFF` / `#8B949E` / `#6E7681` | Hierarquia de texto |
| `ACCENT` / `ACCENT_HOVER` | `#007BFF` / `#0069D9` | Ação primária, progresso, focus |
| `accent_subtle` | `#111D2C` | Pill nav ativo, hovers suaves |
| `btn_secondary` + `btn_secondary_border` | `#21262D` + `#30363D` | Botões secundários com borda |
| `alert_info_bg` / `alert_info_border` / `alert_info_text` | `#111D2C` / `#1F6FEB` / `#58A6FF` | `#statusBanner` informativo |
| `surface_elevated` | `#21262D` | Skeleton, log inset |
| `divider` | `#30363D` | Separadores (`#sidebarDivider`, `#actionDock`) |
| `danger` | `#DC3545` | Ações destrutivas |

Light mode: mesmos nomes em `LIGHT` (`ThemePalette`) com valores ajustados para contraste.

## Espaçamento (grid 8px)

`SPACE_XS=4`, `SPACE_SM=8`, `SPACE_MD=16`, `SPACE_LG=24`, `SPACE_XL=32`

Margens de página: `PAGE_MARGINS = (24, 20, 24, 20)` — usar `apply_page_margins(layout)`.

Padding interno de card: 16px (`Card` / QSS).

Helpers: `apply_page_margins(layout)` e `apply_layout_spacing(layout, gap=SPACE_LG)` em [`widgets/common.py`](../src/youtube_downloader/ui_qt/widgets/common.py).

## Layout e responsividade (desktop)

### Regras

| Regra | Detalhe |
|-------|---------|
| Margens de página | Só `apply_page_margins` — não repetir `PAGE_MARGINS` nas views |
| Espaçamento entre widgets | Preferir `SPACE_*` ou `apply_layout_spacing`; `SPACE_XS` (4px) só para gaps ícone–texto ou controlos muito densos |
| Tamanhos fixos | Reservar a `theme_tokens.py` (sidebar, hero input, scroll mínimos); evitar literais `8`, `200`, `18` nas views |
| Política de tamanho | `QSizePolicy` + `stretch` nos layouts; não `setFixedSize` salvo sidebar/title bar/miniaturas |
| Breakpoints | Política pura em [`layout_breakpoints.py`](../src/youtube_downloader/ui_qt/layout_breakpoints.py) |

### Tamanhos de controlo

| Token | px | Uso |
|-------|-----|-----|
| `INPUT_HERO_HEIGHT` | 44 | Campo URL, filtros hero (~40–48px) |
| `NAV_ITEM_HEIGHT` | 40 | Entradas da sidebar |
| `ICON_XS` / `ICON_SM` / `ICON_MD` / `ICON_LG` | 12 / 16 / 18 / 24 | `themed_icon` / `icon_on_button` |

### Breakpoints (área de conteúdo)

Largura de referência = largura do widget de página (área à direita da sidebar, já descontada nos filhos do stack).

| Modo | Condição | Comportamento |
|------|----------|---------------|
| `comfortable` | largura ≥ `CONTENT_BREAKPOINT_COMPACT` (720) | Fila: duas colunas (2:1) |
| `compact` | largura &lt; 720 | Fila: coluna única empilhada (*Baixando agora* + Atividade → *Na fila*) |

Com `WINDOW_MIN_WIDTH=900`, a Fila arranca em modo **compact** (~680px úteis). Ao alargar a janela (≥ ~940px de largura total), passa a **duas colunas**.

### Janela mínima

| Constante | Valor | Notas |
|-----------|-------|-------|
| `WINDOW_SIZE` | 980×720 | Tamanho inicial |
| `WINDOW_MIN_WIDTH` / `WINDOW_MIN_HEIGHT` | 900×680 | Não reduzir sem validar empilhamento + action dock + preview |

### HiDPI (Qt 6)

- O Qt escala widgets automaticamente; não é necessário `AA_EnableHighDpiScaling`.
- Ícones: tamanhos da escala `ICON_*`; SVG em `resources/icons/`.
- Após `setProperty("class", …)` ou mudança de tema: `polish_widget(widget)`.

### Miniaturas (referência)

| Contexto | Tamanho | Fonte |
|----------|---------|--------|
| Fila / Histórico (linha compacta) | 128×72 | `CARD_THUMB_SIZE` em `core/preview_cache.py` |
| Preview Downloads | 240×135 | `THUMB_DISPLAY_SIZE` em `media_preview_row.py` |

## Tipografia

| objectName / class | Tamanho | Uso |
|--------------------|---------|-----|
| `pageTitle` | 26px semibold | Título de página (`PageHeader`) |
| `sectionTitle` | 13px semibold | Secções (ex. Atividade) |
| `class="muted"` | 12px | Metadados, versão |
| `class="secondary"` | 12px | Subtítulos |
| `class="fieldLabel"` | 11px | Rótulo acima de inputs (Configurações) |

**Importante:** classes `muted`, `secondary`, `fieldLabel` usam `setProperty("class", …)` ou `field_label()` / `muted_label()` em `widgets/common.py`, não `objectName`.

## Componentes

| Widget | objectName | Notas |
|--------|------------|-------|
| `Card` | `card` | Container com borda |
| `PageHeader` | — | Título + subtítulo opcional |
| `SectionTitle` | `sectionTitle` | Cabeçalho de secção |
| `ThumbnailLabel` | `thumb` | Miniatura + badge opcional |
| `Separator` | — | Linha horizontal |
| `PrimaryButton` | `primary` | Uma por ecrã |
| `SecondaryButton` | — | Secundário com borda (QSS global); Colar, + Fila |
| `GhostButton` | `ghost` | Ações discretas sem borda (Limpar URL) |
| `DangerButton` | `danger` | Remover, cancelar forte |
| Nav | `nav` | Sidebar checkable; hover/press animados em `NavButton`; foco teclado (`:focus` + `focus_border`) |
| Indicador nav | `navPill` | Pill `accent_subtle` + barra esquerda 2px `ACCENT`; desliza ~200ms |
| Badge fila (nav) | `navBadge` | Contagem na entrada Fila (`1`…`99+`); `active=true` quando Fila selecionada |
| Itens / ordem nav | `nav_registry.py` | Fonte única: `view_id`, ícone, rótulo, atalho e índice do `QStackedWidget` |
| Atalhos nav | `nav_shortcuts.py` | Derivado de `nav_registry`; Ctrl+1…5; tooltips nos botões |
| Divisor sidebar | `sidebarDivider` | 1px entre nav e conteúdo |
| Barra de título (frameless) | `customTitleBar` | Marca na coluna da sidebar (`titleBarBrand`): ícone + `titleBarTitle` (13px, semibold) + arrastar (`titleBarDrag`) + ícones SVG nos botões da janela |
| Divisor título / conteúdo | `titleBarDivider` | 1px horizontal (`divider`), entre `customTitleBar` e o corpo |
| Contorno da janela (frameless) | `windowRoot` | Borda 1px `card_border` no `centralWidget`; resize nas bordas (~6px) via `WM_NCHITTEST` (Windows) ou arrasto com rato |
| Preview vazio (Downloads) | `previewEmpty` / `previewEmptyIcon` | Moldura tracejada; ícone circular (`PREVIEW_EMPTY_MIN_HEIGHT=240`) |
| Preview loading / inset | `surfaceInset` | Skeleton sem borda dupla com card pai |
| Atividade (Fila) | `ActivityLogPanel` (`#card`) | Coluna esquerda (maior) da tela Fila; cabeçalho clicável |
| Última linha (log fechado) | `activityLastLine` | `muted_label` com prefixo «Última: …» |
| Log de atividade | `logInset` | `QPlainTextEdit` (só visível expandido) |
| Toggle de secção | `sectionToggle` | Colapsar/expandir Atividade |
| Campo URL hero | `urlHero` | Input principal na tela Downloads (`INPUT_HERO_HEIGHT`) |
| Linha URL + ações | `urlToolRow` | Colar, + Fila, ícones — mesma altura que `urlHero`; modo compact (&lt;720px): só ícones |
| Faixa em curso (Downloads) | `DownloadsNowPlayingStrip` | Card durante download: título, status, barra, «Ver na Fila» |
| Opções de formato (Downloads) | `downloadOptionsBar` | Sempre abaixo do preview (não só dentro do card de metadados) |
| Faixa de progresso (legado) | `progressStrip` | Widget `DownloadProgressStrip` — não usado na UI; progresso na tela **Fila** |
| Skeleton preview | `skeletonLine` | Placeholder de metadados |
| Action dock | `actionDock` | Rodapé fixo: linha 1 status + atalhos; linha 2 pasta/ações/Baixar |
| Segmentado | `segment` | Vídeo / Áudio (`SegmentedControl`) |
| Primário outline | `primaryOutline` | Baixar quando URL inválida |

| Switch | `switch` | Checkboxes estilo toggle (Configurações) |
| Tema claro/escuro | `appearanceToggle` | Botão ícone único na linha do **Sobre** (lua/sol, alinhado à direita); persiste `appearance_mode` em `settings.json` |
| Banner de status | `statusBanner` / `statusBannerSlot` | Avisos FFmpeg no topo do conteúdo; slot com margem 16px (laterais) e 8px (vertical) |
| Filtro de lista | `filterInput` | Histórico / Biblioteca |
| Linha compacta | `compactRow` | Histórico, Fila pendente, Biblioteca |
| Baixando agora (Fila) | `QueueNowPlayingCard` | `#card` + `#surfaceInset`: miniatura 128×72, título/URL/status, barra full-width, Cancelar/Pular |
| Estado vazio (listas) | — | `EmptyState` (ícone + título + CTA opcional) |
| Preview vazio tracejado | `previewEmpty` | `PreviewEmptyPanel` na tela Downloads |
| Alerta de erro (Downloads) | `downloadAlert` | Banner dismissível acima do preview |
| Chip pasta destino | `destinationChip` | Action dock — abre pasta de download |

Widgets reutilizáveis: `ActivityLogPanel`, `AppearanceToggle`, `PreviewSkeleton`, `PreviewEmptyPanel`, `MediaPreviewRow`, `CompactMediaRow`, `QueueNowPlayingCard`, `EmptyState`, `DownloadAlert`, `StatusBanner`, `UrlDropLineEdit`, `DownloadOptionsBar`, `DownloadProgressStrip`, `SegmentedControl`, `SecondaryButton` em `ui_qt/widgets/`.

Raios: `RADIUS_CARD=10`, `RADIUS_BUTTON` / `RADIUS_INPUT=8`. Fonte base: `FONT_BODY=13`, família `Segoe UI Variable`.

Helper `field_label(text)` — mesmo estilo que `class="fieldLabel"`.

## Hierarquia de botões

1. **Primário** (`#primary`): ação principal (Baixar, Salvar).
2. **Padrão** (`SecondaryButton` / QSS global): borda `btn_secondary_border` (Abrir pasta, Colar, + Fila).
3. **Ghost** (`#ghost`): limpar, fechar — sem borda até hover.
4. **Danger** (`#danger`): remover da fila/histórico quando precisa destaque.

## Tema em runtime

`apply_theme(app, "dark"|"light")` define estilo Fusion + QSS + paleta. O atalho na sidebar chama `MainWindow._set_appearance_mode` (grava `settings.json` e atualiza ícones da title bar, nav e cabeçalhos de Configurações). Após mudar `class` em widgets, chamar `polish_widget(widget)`.

## QA visual (checklist)

### Automático (CI / local)

- [x] `python -m pytest` (incl. `test_layout_breakpoints`, `test_theme_qss`, tokens 8px)

### Manual — antes de merge de PR com UI

- [ ] **Dark e light:** sidebar, inputs, cards, switches, scrollbars
- [ ] **Margens:** todas as páginas com `PageHeader` + `apply_page_margins`
- [ ] **Janela no mínimo (900×680):** sem clipping; Fila em layout empilhado; action dock Downloads legível
- [ ] **Janela confortável (~980×720+):** Fila em duas colunas; redimensionar transição suave
- [ ] **HiDPI Windows:** ícones legíveis a 100% e 125% DPI (`ICON_*` na URL row e title bar)
- [ ] **Downloads:** preview, DnD, erros PT, chip destino, Enter/Esc
- [ ] **Fila:** *Baixando agora*, Atividade, pendentes, Cancelar/Pular

## Lacunas corrigidas (auditoria)

- QSS `QLabel#muted` vs `setProperty("class", "muted")` — unificado em `QLabel[class="muted"]`.
- Tema claro incompleto — paridade com dark em `build_light_qss()`.
- Estilos inline (`#2a2a2a`, `#007BFF`) — movidos para tokens/QSS.
- Emojis como ícones — substituídos por SVG em `resources/icons/`.
- Linha branca na sidebar — `VLine` nativo substituído por `#sidebarDivider` com token `divider`.
- Títulos de secção em Configurações — `#cardSectionTitle` em `text_primary` (ícone colorido separado).
