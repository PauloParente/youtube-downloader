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

## Tokens de cor (dark)

| Token | Uso |
|-------|-----|
| `app_bg` | Fundo da janela |
| `card_bg` / `card_border` | Cards (`#card`) |
| `input_bg` / `input_border` | Campos de texto |
| `text_primary` / `text_secondary` / `text_muted` | Hierarquia de texto |
| `accent` / `accent_hover` / `accent_muted` | Ação primária, progresso, focus outline |
| `accent_subtle` | Item nav ativo, hovers suaves |
| `surface_elevated` | Placeholder de miniatura, fundo inset |
| `divider` | Separador sidebar/conteúdo (`#sidebarDivider`) |
| `danger` | Ações destrutivas discretas |

Light mode: mesmos nomes em `LightPalette` com valores ajustados para contraste.

## Espaçamento (grid 8px)

`SPACE_XS=4`, `SPACE_SM=8`, `SPACE_MD=16`, `SPACE_LG=24`, `SPACE_XL=32`

Margens de página: `PAGE_MARGINS = (24, 20, 24, 20)` — usar `apply_page_margins(layout)`.

Padding interno de card: 16px (`Card` / QSS).

## Tipografia

| objectName / class | Tamanho | Uso |
|--------------------|---------|-----|
| `pageTitle` | 22px semibold | Título de página (`PageHeader`) |
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
| `GhostButton` | `ghost` | Secundário / link |
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
| Preview vazio / inset | `surfaceInset` | Sem borda dupla com card pai |
| Log de atividade | `logInset` | `QPlainTextEdit` dentro do card ATIVIDADE |
| Toggle de secção | `sectionToggle` | Colapsar ATIVIDADE (Downloads) |
| Campo URL hero | `urlHero` | Input principal na tela Downloads (`INPUT_HERO_HEIGHT`) |
| Linha URL + ações | `urlToolRow` | Colar, + Fila, ícones — mesma altura que `urlHero` |
| Faixa de progresso | `progressStrip` | Download em curso na Downloads |
| Skeleton preview | `skeletonLine` | Placeholder de metadados |
| Action dock | `actionDock` | Rodapé fixo (status + ações) |
| Segmentado | `segment` | Vídeo / Áudio (`SegmentedControl`) |
| Primário outline | `primaryOutline` | Baixar quando URL inválida |

| Switch | `switch` | Checkboxes estilo toggle (Configurações) |
| Banner de status | `statusBanner` / `statusBannerSlot` | Avisos FFmpeg no topo do conteúdo; slot com margem 16px (laterais) e 8px (vertical) |
| Filtro de lista | `filterInput` | Histórico / Biblioteca |
| Linha compacta | `compactRow` | Histórico, Fila pendente, Biblioteca |
| Estado vazio | — | `EmptyState` (ícone + título + CTA opcional) |
| Alerta de erro (Downloads) | `downloadAlert` | Banner dismissível acima do preview |
| Chip pasta destino | `destinationChip` | Action dock — abre pasta de download |

Widgets reutilizáveis: `PreviewSkeleton`, `MediaPreviewRow`, `CompactMediaRow`, `EmptyState`, `DownloadAlert`, `StatusBanner`, `UrlDropLineEdit`, `DownloadOptionsBar`, `DownloadProgressStrip`, `SegmentedControl` em `ui_qt/widgets/`.

Raios: `RADIUS_CARD=10`, `RADIUS_BUTTON` / `RADIUS_INPUT=8`. Fonte base: `FONT_BODY=13`, família `Segoe UI Variable`.

Helper `field_label(text)` — mesmo estilo que `class="fieldLabel"`.

## Hierarquia de botões

1. **Primário** (`#primary`): ação principal (Baixar, Salvar).
2. **Padrão** (QSS global): secundário (Abrir pasta, + Fila).
3. **Ghost** (`#ghost`): limpar, fechar, ícones discretos.
4. **Danger** (`#danger`): remover da fila/histórico quando precisa destaque.

## Tema em runtime

`apply_theme(app, "dark"|"light")` define estilo Fusion + QSS + paleta. Após mudar `class` em widgets, chamar `polish_widget(widget)`.

## QA visual (checklist)

- [x] Dark e light: sidebar (`accent_subtle`), inputs, cards, switches, scrollbars
- [x] Todas as páginas: `PageHeader` e margens iguais; Fila/Histórico/Biblioteca com `CompactMediaRow` / `EmptyState`
- [x] Downloads: preview, DnD, erros PT, progress com contexto, chip destino, atalhos Enter/Esc
- [x] Configurações: `actionDock`, switches, alternar tema
- [ ] Ícones SVG legíveis em 100% e 125% DPI (Windows) — validar manualmente
- [x] `python -m pytest`

## Lacunas corrigidas (auditoria)

- QSS `QLabel#muted` vs `setProperty("class", "muted")` — unificado em `QLabel[class="muted"]`.
- Tema claro incompleto — paridade com dark em `build_light_qss()`.
- Estilos inline (`#2a2a2a`, `#007BFF`) — movidos para tokens/QSS.
- Emojis como ícones — substituídos por SVG em `resources/icons/`.
- Linha branca na sidebar — `VLine` nativo substituído por `#sidebarDivider` com token `divider`.
- Títulos de secção em Configurações — `#cardSectionTitle` em `text_primary` (ícone colorido separado).
