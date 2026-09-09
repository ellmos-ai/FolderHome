# FolderHome Design System & Asset Package

**English** | [Deutsch](./README.de.md)

> Assistantify your home.

**Version:** 1.3  
**Repository:** [https://github.com/ellmos-ai/FolderHome](https://github.com/ellmos-ai/FolderHome)  
**Positioning:** Local-first Strands agent for household documents, gated home workflows, explicit cloud gates, and reversible file actions.

---

## 🎨 Color Palette & Design Tokens

| Token | Hex | RGB | Usage |
|---|---|---|---|
| **Amber Gold (Primary)** | `#F59E0B` | `245, 158, 11` | Document folder body, glowing home window, primary brand accents |
| **Warm Gold (Highlight)** | `#FBBF24` | `251, 191, 36` | Folder highlight edges, key metric callouts, gradient tops |
| **Deep Ochre (Shade)** | `#D97706` | `217, 119, 6` | Gradient depths, folder borders, workflow badges |
| **Cyber Cyan / Azure** | `#38BDF8` | `56, 189, 248` | Gated security shield, Strands engine tags, circuit traces |
| **Deep Blue / Vault** | `#0284C7` | `2, 132, 199` | Shield gradient, fail-closed badges, active buttons |
| **Emerald Green** | `#10B981` | `16, 185, 129` | Reversible file actions, health dossiers, verified status |
| **Obsidian Dark (BG)** | `#050811` | `5, 8, 17` | Canvas background, dark mode UI base |
| **Navy Surface** | `#0D1627` | `13, 22, 39` | Card surfaces, container panels, blueprint grids |
| **Slate Border** | `#1E293B` | `30, 41, 59` | Structural dividers, inactive component borders |
| **Pure Ice White** | `#F8FAFC` | `248, 250, 252` | Primary headlines, paper sheets inside folders |
| **Muted Slate** | `#94A3B8` | `148, 163, 184` | Subtitles, descriptive copy, secondary metadata |

---

## 📦 Canonical Brand & Product Assets

Banner, horizontal logo and both thumbnails were refreshed on 9 September 2026.
Workflow availability depends on configured resources and gates; consult the
[runtime capability index](../CAPABILITY-INDEX.md), not a fixed badge count.
These brand images are not live-service acceptance evidence. For the current
component and approval map, see [product architecture](../docs/submission/PRODUCT_ARCHITECTURE.svg).

| File | Type | Dimensions | Purpose / Description |
|---|---|---|---|
| [`banner.svg`](./banner.svg) | Vector SVG | 1200 × 340 | Responsive vector GitHub repo banner with FolderHome emblem, document matrix, and 4 precise feature pills (*Gated Execution*, *Reversible File Actions*, *Explicit Cloud Gates*, *Gated Home Workflows*). |
| [`banner.png`](./banner.png) | Raster PNG (@2x) | 2400 × 680 | High-DPI rendered GitHub header banner for README and release headers. |
| [`logo.svg`](./logo.svg) | Vector SVG | 800 × 200 | Horizontal brand lockup (Emblem + Wordmark + Subtitle + Gated Home Workflows). |
| [`logo.png`](./logo.png) | Raster PNG (@2x) | 1600 × 400 | High-DPI horizontal logo for web headers, docs, and presentations. |
| [`logo_vertical.svg`](./logo_vertical.svg) | Vector SVG | 500 × 500 | Centered / stacked brand logo lockup. |
| [`logo_vertical.png`](./logo_vertical.png) | Raster PNG (@2x) | 1000 × 1000 | Centered stacked logo for square avatars and card layouts. |
| [`icon.svg`](./icon.svg) | Vector SVG | 512 × 512 | Squircle app icon featuring the 3D layered FolderHome vault emblem. |
| [`icon.png`](./icon.png) | Raster PNG (@2x) | 1024 × 1024 | High-res app and system-tray icon. |
| [`favicon.svg`](./favicon.svg) | Vector SVG | 64 × 64 | Scalable browser tab favicon. |
| [`favicon.png`](./favicon.png) | Raster PNG | 64 × 64 | 64px browser favicon. |
| [`thumbnail.svg`](./thumbnail.svg) | Vector SVG | 1280 × 720 | 16:9 Video and showcase thumbnail with generous padding, clean multi-line wrapping, and 3 architecture pillars. |
| [`thumbnail.png`](./thumbnail.png) | Raster PNG (@2x) | 2560 × 1440 | 16:9 High-impact showcase thumbnail for YouTube, Devpost, and OpenGraph preview. |
| [`thumbnail_features.svg`](./thumbnail_features.svg) | Vector SVG | 1280 × 720 | 16:9 4-Pillar Feature Matrix (*Local FTS Document Ingestion*, *Gated Planning & Governance*, *Gated Home Workflows*, *Explicit Approval & Effect Evidence*). |
| [`thumbnail_features.png`](./thumbnail_features.png) | Raster PNG (@2x) | 2560 × 1440 | 16:9 Rendered feature matrix slide for Devpost and video presentations. |

---

## 💡 Exploratory Concept Art (Moodboard)

> [!NOTE]
> The following renderings are generative **design concept studies** for visual moodboards and social media teasers. They contain model-generated text and UI artifacts and do **not** serve as product or architectural evidence. The current product architecture is described in [ARCHITECTURE.md](../ARCHITECTURE.md), not by these moodboards.

| File | Type | Dimensions | Purpose / Status |
|---|---|---|---|
| [`concept_hero_3d.jpg`](./concept_hero_3d.jpg) | AI Concept Art | 1376 × 768 | 3D Moodboard: Modern smart home integrated with a glowing folder-vault. |
| [`concept_icon_3d.jpg`](./concept_icon_3d.jpg) | AI Concept Art | 1024 × 1024 | 3D Glassmorphism app icon concept study (Gold & Deep Navy). |
| [`concept_dashboard_3d.jpg`](./concept_dashboard_3d.jpg) | AI Concept Art | 1376 × 768 | Futuristic smart home document hub vision (concept art). |

---

## 🚀 Markdown Integration

### Header Banner

```markdown
<img src="assets/banner.png" width="100%" alt="FolderHome Banner">
```

### Social / OpenGraph Card

```html
<meta property="og:image" content="https://raw.githubusercontent.com/ellmos-ai/FolderHome/main/assets/thumbnail.png" />
<meta property="og:title" content="FolderHome — Assistantify your home." />
<meta property="og:description" content="Local-first Strands agent for household documents, gated home workflows, explicit cloud gates, and reversible file actions." />
```

### Badges

```markdown
[![Local-First](https://img.shields.io/badge/architecture-local--first-blue.svg)](https://github.com/ellmos-ai/FolderHome)
[![Strands Agent](https://img.shields.io/badge/strands--agents-1.53.0-orange.svg)](https://github.com/ellmos-ai/FolderHome)
[![Fail-Closed](https://img.shields.io/badge/security-fail--closed-green.svg)](https://github.com/ellmos-ai/FolderHome)
[![Gated Workflows](https://img.shields.io/badge/workflows-gated-purple.svg)](https://github.com/ellmos-ai/FolderHome)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](../LICENSE)
```

## Reproducible raster export

The four refreshed SVGs need no remote fonts. PNG export uses
`resvg-py==0.5.0`, Segoe UI, Consolas and Segoe UI Symbol from a local Windows
installation; font files are not distributed. Other font versions can produce
different bytes. Existing @2x dimensions are retained. Python example from
the repository root:

```python
from pathlib import Path
import resvg_py

fonts = [str(Path('C:/Windows/Fonts') / name) for name in
         ('segoeui.ttf', 'segoeuib.ttf', 'consola.ttf', 'consolab.ttf', 'seguisym.ttf')]
for name, (width, height) in {
    'banner': (2400, 680), 'logo': (1600, 400),
    'thumbnail': (2560, 1440), 'thumbnail_features': (2560, 1440),
}.items():
    png = resvg_py.svg_to_bytes(
        svg_string=Path('assets', name + '.svg').read_text(encoding='utf-8'),
        width=width, height=height, skip_system_fonts=True, font_files=fonts,
        sans_serif_family='Segoe UI', monospace_family='Consolas',
    )
    Path('assets', name + '.png').write_bytes(png)
```
