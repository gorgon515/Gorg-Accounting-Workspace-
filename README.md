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

### Visual approach & interaction

Strictly typographic and structural — **no imagery, no gradients, no AI art**,
per the brand brief ("not anything with a gradient or a hero video").

- **Hairline specimen panel** in the hero and a **holding-structure diagram**
  on the Practice page — both built in HTML/CSS (mono labels, hairline rules),
  treated as data/structural elements rather than decoration.
- **Marque bands** (monospace location lines between hairline rules) as dividers.
- **Nav preview** ("precursor highlight") — hovering a tab reveals a hairline
  bar describing what that tab opens before you click.
- **Portal downloads** generate real letterhead text files locally (Blob).

If real architectural photography (stone, glass, steel — no people) becomes
available, it can be dropped into the hero/marque slots later.

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
  (arrows / Home / End, roving tabindex), `prefers-reduced-motion` honored,
  and a custom `404.html`.
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
