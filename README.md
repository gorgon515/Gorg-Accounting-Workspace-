# Verum Advisory — Website

A static marketing and client-access website for **Verum Advisory**, an
international tax advisory firm. Built to the firm's brand brief:
*Truth. Precision. Discretion.*

> The website of a Zurich private bank. The lobby of a Midtown law firm.
> A Bloomberg Terminal. Not a fintech startup.

## Pages (client tabs)

| Tab | File | Purpose |
|-----|------|---------|
| Home | `index.html` | Positioning, practice preview, the standard |
| Practice | `practice.html` | The four disciplines and how engagements are worked |
| The Firm | `firm.html` | Principles and the partners |
| Insights | `insights.html` | Notes on structure, controversy, consequence |
| Client Portal | `portal.html` | Tabbed secure area: Documents · Tax Calendar · Statements · Secure Messages · Sign In |
| CRM | `crm.html` | Internal engagement register (localStorage) |
| Contact | `contact.html` | Request an introduction |

Insights articles open real pages via `article.html?id=<slug>` (content in
`assets/js/articles.js`). Practice cards deep-link to anchored discipline
sections (`practice.html#cross-border`, etc.).

### Graphics & interaction

- **Custom SVG line-art** in `assets/img/` (no stock photos, no gradients):
  a glass-tower `facade`, a one-point-perspective `corridor`, a cross-border
  holding-`structure` diagram, and a `skyline` divider.
- **Nav preview** ("precursor highlight") — hovering a tab reveals a hairline
  bar describing what that tab opens before you click.
- **Portal downloads** generate real letterhead text files locally (Blob).

## Design system

- **Palette** — Obsidian `#0E0E10`, Charcoal `#1A1A1E`, Slate `#242428`,
  Ivory `#F2EDE4`, Warm Gray `#8C8880`, Antique Gold `#B8976A` (used sparingly),
  hairline borders. Never pure black or pure white.
- **Type** — Cormorant Garamond (headings), Inter (body/UI),
  JetBrains Mono (numbers, references, codes).
- **Motion** — slow, deliberate fades and subtle translates (400–600ms).
  No parallax, no bounce. Respects `prefers-reduced-motion`.

All design tokens live as CSS custom properties at the top of
`assets/css/styles.css`.

## Running

No build step. It is plain HTML/CSS/JS. Open `index.html` directly, or serve
the folder:

```bash
python3 -m http.server 8000
# then visit http://localhost:8000
```

## Notes

- Forms and the portal sign-in are front-end demonstrations only — there is no
  backend. Submissions are acknowledged client-side.
- Contact details, statistics, and partner descriptions are placeholders to be
  replaced with the firm's real information.
