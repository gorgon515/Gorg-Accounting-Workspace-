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
sections (`practice.html#cross-border`, etc.). Every Client Portal document and
statement opens a real viewer page via `document.html?id=<slug>` (content in
`assets/js/documents.js`) with an on-page download. No link dead-ends.

### Visual approach & interaction

Typographic and structural, with NYC architecture as the only imagery —
**no gradients, no AI art**, per the brand brief.

- **NYC photography** in the hero, a skyline band, and "The room" on The Firm.
  Real Unsplash photos load at view-time, treated monochrome + darkened to
  read on-brand. Each sits over **hand-drawn line-art** (`assets/img/skyline.svg`,
  `tower.svg`) that shows automatically if a photo is blocked — never a broken
  image. Swap the three `--photo-*` URLs at the top of `assets/css/styles.css`
  for the firm's own licensed photography (dusk facades, lobbies — no people).
- **Hairline specimen panel** in the hero and a **holding-structure diagram**
  on the Practice page — built in HTML/CSS (mono labels, hairline rules).
- **Nav preview** ("precursor highlight") — hovering a tab reveals a hairline
  bar describing what that tab opens before you click.
- **Portal documents** open real viewer pages with on-page downloads.

> The photos must be served over http(s) and reach `images.unsplash.com`
> (allowlisted in the CSP). Offline/`file://`, you'll see the line-art instead.

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

## Security & accessibility

- **Content-Security-Policy** (meta on every page) — `script-src 'self'`,
  `object-src 'none'`, no inline scripts, fonts limited to Google Fonts. A
  `_headers` file ships the same CSP plus `X-Content-Type-Options`,
  `X-Frame-Options`, `Referrer-Policy`, `Permissions-Policy`, and HSTS for
  hosts that honor it (Netlify/Cloudflare; GitHub Pages ignores custom headers,
  so the meta CSP is the enforced layer there).
- **No inline event handlers or inline `<script>`** — all JS is external and
  same-origin, so the strict CSP holds.
- **CRM `innerHTML` is escaped** (`escapeHtml`) on every user-entered field.
- **Contact form honeypot** silently drops bot submissions; required fields
  use native validation.
- **Accessibility** — skip-to-content link, `:focus-visible` rings, a `#main`
  landmark, WAI-ARIA tabs in the Client Portal with full keyboard support
  (arrows / Home / End, roving tabindex), and `prefers-reduced-motion` honored.
- **Efficiency** — scroll work is `requestAnimationFrame`-throttled behind a
  single passive listener; scripts are `defer`red; an SVG favicon and
  `theme-color` are set. No images, no gradients, no web fonts beyond three.

> Note: the strict CSP requires the site to be served over http(s) (the local
> `http.server` command, or GitHub Pages). Opening pages directly via
> `file://` will have the CSP block same-origin scripts — use the server.

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
