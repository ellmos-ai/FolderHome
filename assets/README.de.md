# FolderHome Design-System & Asset-Paket

[English](./README.md) | **Deutsch**

> Assistantify your home.

**Version:** 1.3  
**Repository:** [https://github.com/ellmos-ai/FolderHome](https://github.com/ellmos-ai/FolderHome)  
**Positionierung:** Lokaler Strands-Agent für Haushaltsdokumente, freigabegebundene Haushaltsabläufe, explizite Cloud-Gates und reversible Dateiaktionen.

---

## 🎨 Farbpalette & Design-Tokens

| Token | Hex | RGB | Verwendung |
|---|---|---|---|
| **Amber Gold (Primär)** | `#F59E0B` | `245, 158, 11` | Dokumentenordner, leuchtendes Hausfenster, primäre Markenakzente |
| **Warm Gold (Highlight)** | `#FBBF24` | `251, 191, 36` | Ordner-Glanzkanten, Kennzahlen, Farbverlaufsspitzen |
| **Deep Ochre (Schatten)** | `#D97706` | `217, 119, 6` | Verlaufstiefen, Ordnerrahmen, Workflow-Badges |
| **Cyber Cyan / Azure** | `#38BDF8` | `56, 189, 248` | Gated-Sicherheits-Schild, Strands-Engine-Tags, Schaltkreis-Spuren |
| **Deep Blue / Vault** | `#0284C7` | `2, 132, 199` | Schild-Verlauf, Fail-Closed-Badges, aktive Schaltflächen |
| **Emerald Green** | `#10B981` | `16, 185, 129` | Reversible Dateiaktionen, Gesundheitsdossiers, verifizierter Status |
| **Obsidian Dark (BG)** | `#050811` | `5, 8, 17` | Leinwand-Hintergrund, Dark-Mode-UI-Basis |
| **Navy Surface** | `#0D1627` | `13, 22, 39` | Karten-Oberflächen, Container-Panels, Blueprint-Gitter |
| **Slate Border** | `#1E293B` | `30, 41, 59` | Strukturelle Trennlinien, inaktive Rahmen |
| **Pure Ice White** | `#F8FAFC` | `248, 250, 252` | Hauptüberschriften, Papierseiten im Ordner |
| **Muted Slate** | `#94A3B8` | `148, 163, 184` | Untertitel, beschreibender Fließtext, Metadaten |

---

## 📦 Kanonische Marken- & Produkt-Assets

Banner, horizontales Logo und beide Thumbnails wurden am 9. September 2026 aktualisiert.
Verfügbare Abläufe hängen von konfigurierten Ressourcen und Freigaben ab; maßgeblich
ist der [Laufzeit-Fähigkeitsindex](../CAPABILITY-INDEX.de.md), keine feste Badge-Zahl.
Diese Markenbilder sind kein Beleg einer Live-Service-Abnahme. Die aktuelle
Komponenten- und Freigabekarte steht in der [Produktarchitektur](../docs/submission/PRODUCT_ARCHITECTURE.svg).

| Datei | Typ | Dimensionen | Zweck / Beschreibung |
|---|---|---|---|
| [`banner.svg`](./banner.svg) | Vektor-SVG | 1200 × 340 | Responsiver Vektor-Banner mit FolderHome-Emblem, Dokument-Matrix und 4 präzisen Feature-Pills (*Gated Execution*, *Reversible File Actions*, *Explicit Cloud Gates*, *Gated Home Workflows*). |
| [`banner.png`](./banner.png) | Raster-PNG (@2x) | 2400 × 680 | High-DPI gerenderter GitHub-Header-Banner für README und Release-Header. |
| [`logo.svg`](./logo.svg) | Vektor-SVG | 800 × 200 | Horizontales Marken-Logo (Emblem + Wortmarke + Untertitel + Gated Home Workflows). |
| [`logo.png`](./logo.png) | Raster-PNG (@2x) | 1600 × 400 | Horizontales Logo für Web-Header, Dokumentationen und Präsentationen. |
| [`logo_vertical.svg`](./logo_vertical.svg) | Vektor-SVG | 500 × 500 | Zentrierter / gestapelter Marken-Logo-Lockup. |
| [`logo_vertical.png`](./logo_vertical.png) | Raster-PNG (@2x) | 1000 × 1000 | Gestapeltes Logo für quadratische Avatare und Card-Layouts. |
| [`icon.svg`](./icon.svg) | Vektor-SVG | 512 × 512 | Squircle-App-Icon mit 3D-Folder, Haus-Silhouette und Vault-Shield. |
| [`icon.png`](./icon.png) | Raster-PNG (@2x) | 1024 × 1024 | Hochauflösendes App- und System-Tray-Icon. |
| [`favicon.svg`](./favicon.svg) | Vektor-SVG | 64 × 64 | Skalierbares Browser-Tab-Favicon. |
| [`favicon.png`](./favicon.png) | Raster-PNG | 64 × 64 | 64px Browser-Favicon. |
| [`thumbnail.svg`](./thumbnail.svg) | Vektor-SVG | 1280 × 720 | 16:9 Video- und Showcase-Thumbnail mit großzügigem Padding, sauberem Textumbruch und 3 Architektur-Säulen. |
| [`thumbnail.png`](./thumbnail.png) | Raster-PNG (@2x) | 2560 × 1440 | 16:9 High-Impact Showcase-Thumbnail für YouTube, Devpost und Social-Media-Vorschauen. |
| [`thumbnail_features.svg`](./thumbnail_features.svg) | Vektor-SVG | 1280 × 720 | 16:9 4-Säulen-Feature-Matrix (*Lokaler FTS-Dokumenten-Index*, *Gated Planning & Governance*, *Gated Home Workflows*, *Explicit Approval & Effect Evidence*). |
| [`thumbnail_features.png`](./thumbnail_features.png) | Raster-PNG (@2x) | 2560 × 1440 | 16:9 gerenderte Feature-Matrix-Folie für Devpost und Video-Präsentationen. |

---

## 💡 Explorative Konzept-Visualisierungen (Moodboard)

> [!NOTE]
> Die folgenden Renderings sind generative **Design-Konzeptstudien** für visuelle Moodboards und Social-Media-Teaser. Sie enthalten modellgenerierte Text- und Interface-Artefakte und dienen **nicht** als UI-Produktbeleg. Die aktuelle Produktarchitektur wird in [ARCHITECTURE.de.md](../ARCHITECTURE.de.md) beschrieben, nicht durch diese Moodboards.

| Datei | Typ | Dimensionen | Zweck / Status |
|---|---|---|---|
| [`concept_hero_3d.jpg`](./concept_hero_3d.jpg) | KI-Konzeptgrafik | 1376 × 768 | 3D-Moodboard: Modernes Smart Home verschmolzen mit leuchtendem Folder-Vault. |
| [`concept_icon_3d.jpg`](./concept_icon_3d.jpg) | KI-Konzeptgrafik | 1024 × 1024 | 3D-Glassmorphism Icon-Konzeptstudie (Gold & Deep Navy). |
| [`concept_dashboard_3d.jpg`](./concept_dashboard_3d.jpg) | KI-Konzeptgrafik | 1376 × 768 | Futuristische Smart-Home-Dokumentenhub-Vision (Konzeptbild). |

---

## 🚀 Markdown-Einbindung

### Header-Banner

```markdown
<img src="assets/banner.png" width="100%" alt="FolderHome Banner">
```

### Social / OpenGraph Card

```html
<meta property="og:image" content="https://raw.githubusercontent.com/ellmos-ai/FolderHome/main/assets/thumbnail.png" />
<meta property="og:title" content="FolderHome — Assistantify your home." />
<meta property="og:description" content="Lokaler Strands-Agent für Haushaltsdokumente, freigabegebundene Haushaltsabläufe, explizite Cloud-Gates und reversible Dateiaktionen." />
```

### Badges

```markdown
[![Local-First](https://img.shields.io/badge/architecture-local--first-blue.svg)](https://github.com/ellmos-ai/FolderHome)
[![Strands Agent](https://img.shields.io/badge/strands--agents-1.53.0-orange.svg)](https://github.com/ellmos-ai/FolderHome)
[![Fail-Closed](https://img.shields.io/badge/security-fail--closed-green.svg)](https://github.com/ellmos-ai/FolderHome)
[![Gated Workflows](https://img.shields.io/badge/workflows-gated-purple.svg)](https://github.com/ellmos-ai/FolderHome)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](../LICENSE)
```

---

<!-- REMEMBER: ENDUSERTEXTE BEKOMMEN ECHTE UMLAUTE Ü Ö Ä -->

## Reproduzierbarer Rasterexport

Die vier aktualisierten SVGs benötigen keine Remote-Schriften. Der PNG-Export
nutzt `resvg-py==0.5.0`, Segoe UI, Consolas und Segoe UI Symbol aus einer
lokalen Windows-Installation; Schriftdateien werden nicht mitgeliefert.
Andere Schriftversionen können andere Bytes erzeugen. Bestehende @2x-Maße
bleiben erhalten. Beispiel in Python vom Repository-Root:

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
