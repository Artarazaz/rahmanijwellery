# رحمانی — Design System Specification

> Haute Joaillerie Noir · Persian RTL · Espresso + Champagne Gold

---

## 1. Design Philosophy

**Aesthetic**: Haute Joaillerie Noir — deep espresso backgrounds with champagne gold accents, inspired by high-end jewelry houses (Cartier, Van Cleef, Bvlgari) but rooted in Persian calligraphic tradition.

**Core Principles**:
- Noir restraint: let the jewelry breathe against darkness
- Gold as punctuation, not decoration — every gold element earns its place
- Nastaliq calligraphy as the primary visual identity
- Arch-frame motif as the signature photographic element
- RTL-native layout, not mirrored LTR

---

## 2. Color Tokens

### Ink Scale (Backgrounds)

| Token | Hex | Usage |
|-------|-----|-------|
| `--ink-0` | `#14120f` | Page background — deep espresso noir |
| `--ink-1` | `#1c1915` | Raised surfaces (header, cards) |
| `--ink-2` | `#241f1a` | Cards, media containers |
| `--ink-3` | `#2e2820` | Borders, subtle dividers |

### Gold Scale (Accents)

| Token | Hex | Usage |
|-------|-----|-------|
| `--gold-50` | `#f3e3bd` | Highlight text, hover states |
| `--gold-100` | `#e2c384` | Primary accent, headings, links |
| `--gold-200` | `#cdab5f` | Secondary accent, borders |
| `--gold-300` | `#a9834a` | Deep metallic, arch frame borders |
| `--gold-400` | `#8a6d2f` | Darkest gold, subtle elements |

### Semantic Colors

| Token | Hex | Usage |
|-------|-----|-------|
| `--cream` | `#f2e7cf` | Primary body text |
| `--ivory` | `#faf5ec` | Headlines, emphasis text |
| `--muted` | `#b3a891` | Secondary text, labels |
| `--muted-dark` | `#7a7060` | Tertiary text, timestamps |
| `--green` | `#8faa84` | Positive indicators, live dot |
| `--red` | `#c98c78` | Negative indicators, errors |

### Utility Colors

| Token | Value | Usage |
|-------|-------|-------|
| `--gold-line` | `rgba(219, 178, 110, 0.22)` | Borders, dividers |
| `--gold-glow` | `rgba(219, 178, 110, 0.08)` | Subtle backgrounds |
| `--gold-shimmer` | `linear-gradient(105deg, #a9834a 0%, #cdab5f 30%, #e2c384 50%, #cdab5f 70%, #a9834a 100%)` | Button hover animation |

---

## 3. Typography

### Font Stack

| Role | Font | Fallbacks | Weight |
|------|------|-----------|--------|
| Display (Nastaliq) | `'Noto Nastaliq Urdu'` | `'Aref Ruqaa', Georgia, serif` | 400–700 |
| English Serif | `'Cormorant Garamond'` | `Georgia, serif` | 300–600 |
| Body (Persian) | `'Vazirmatn'` | `Tahoma, sans-serif` | 300–600 |

### Type Scale

| Element | Size | Line-Height | Font | Color |
|---------|------|-------------|------|-------|
| Hero H1 | `clamp(42px, 5vw, 72px)` | 1.4 | Nastaliq | `--ivory` |
| Section H2 | `clamp(28px, 3.2vw, 40px)` | 1.6 | Nastaliq | `--cream` |
| Card H3 | `20px` | 1.4 | Nastaliq | `--cream` |
| Body | `15px` | 1.7 | Vazirmatn | `--cream` |
| Small / Labels | `12.5px` | 1.5 | Vazirmatn | `--muted` |
| Ticker | `12.5px` | 1 | Vazirmatn | `--muted` (values: `--gold-100`) |
| Eyebrow | `12.5px` | 1 | Vazirmatn | `--gold-200` |
| English Micro | `13px` | 1.4 | Cormorant Garamond | `--muted` |

### Persian Number Formatting

All prices and numeric displays use `Intl.NumberFormat('fa-IR')` for proper Persian numeral rendering (۰۱۲۳۴۵۶۷۸۹).

---

## 4. Spacing Scale

| Token | Value | Usage |
|-------|-------|-------|
| `--space-xs` | `4px` | Tight gaps (icon + text) |
| `--space-sm` | `8px` | Small padding |
| `--space-md` | `16px` | Standard gaps, card padding |
| `--space-lg` | `24px` | Section padding, grid gaps |
| `--space-xl` | `40px` | Section vertical spacing |
| `--space-2xl` | `64px` | Major section breaks |
| `--space-3xl` | `96px` | Hero vertical padding |

---

## 5. Layout System

### Container

```css
--wrap: min(1280px, calc(100% - 96px));
```

Max-width 1280px with 48px padding on each side. Fluid down to mobile.

### Breakpoints

| Name | Max-Width | Layout |
|------|-----------|--------|
| Desktop | `> 1050px` | Full grid, 2-column hero, 4-col categories |
| Tablet | `760px – 1050px` | 2-col categories, stacked feature rows |
| Mobile | `< 760px` | Single column, stacked everything |

### RTL Implementation

- `html[lang="fa"][dir="rtl"]` on root
- Content containers: `direction: rtl`
- Flex/Grid containers: `direction: ltr` (to prevent column reversal)
- Text alignment: `text-align: right` on RTL text blocks
- Hero grid: `grid-template-columns: 1fr 0.92fr` with `direction: ltr` — text appears on right (RTL first), image on left

---

## 6. Component Specifications

### 6.1 Announcement Bar

- Height: `38px`
- Background: `--ink-0`
- Border-bottom: `1px solid var(--gold-line)`
- Text: `12.5px Vazirmatn`, `--muted` color
- Gold dot: `5px` circle, `--gold-100`, `animation: dot-pulse 2.4s infinite`
- Mobile: hides `.announcement-label` (brand name), keeps message

### 6.2 Header / Navigation

- Position: `sticky`, `top: 0`, `z-index: 100`
- Background: `rgba(20, 18, 15, 0.92)` with `backdrop-filter: blur(18px)`
- Border-bottom: `1px solid var(--gold-line)`
- `.scrolled` state: background opacity increases to `0.97`
- Brand "رحمانی": `30px Nastaliq`, `--cream`, centered
- Nav links: `12.5px Vazirmatn`, `--cream`, hover → `--gold-100`
- Cart badge: `10px` circle, `--gold-200` background, `--ink-0` text
- Mobile: hamburger toggle → vertical dropdown `--ink-1` background

### 6.3 Hero Section

- Grid: `1fr 0.92fr` (LTR direction for correct RTL placement)
- Height: `min(640px, 80vh)`
- **Arch Frame** (`.hero-visual`):
  - `border-radius: 0 190px 0 0` (top-right arch)
  - `border: 1px solid var(--gold-300)`
  - `box-shadow: 0 0 60px rgba(219, 178, 110, 0.06)`
  - `overflow: hidden` with `::before` radial gradient overlay
- **"R" Monogram** (`.hero-visual::after`):
  - `content: "R"`, Cormorant Garamond italic, `26px`
  - Position: bottom `38px`, RTL-aware inset
  - `border: 1px solid var(--gold-line)`, `border-radius: 50%`
  - `width/height: 48px`, backdrop-blur `2px`
- Mobile: `column-reverse` (image first), arch becomes `0 0 0 90px`

### 6.4 Buttons

**Primary (`.button-gold`)**:
- Background: `--gold-100`
- Color: `--ink-0`
- Padding: `14px 28px`
- Border-radius: `0 14px 0 14px` (diagonal cut-corner)
- Font: `600 13px Vazirmatn`
- Hover: `background-size: 250%` shimmer animation, `translateY(-2px)`

**Secondary (`.button-outline`)**:
- Background: transparent
- Border: `1px solid var(--gold-line)`
- Color: `--cream`
- Same border-radius and padding

**Ghost (`.button-ghost`)**:
- Background: transparent
- Color: `--muted`
- No border
- Hover: `color: var(--cream)`

### 6.5 Ticker Strip

- Border-top/bottom: `1px solid var(--gold-line)`
- Background: `rgba(0, 0, 0, 0.15)`
- Animation: `ticker-scroll 30s linear infinite`
- Pause on hover: `animation-play-state: paused`
- Items: `12.5px`, `--muted`, values in `--gold-100`

### 6.6 Category Grid

- Desktop: `grid-template-columns: repeat(4, 1fr)`
- Tablet: `repeat(2, 1fr)`
- Mobile: `repeat(2, 1fr)` with smaller tiles
- Tile: `aspect-ratio: 121/103`, gradient background, overlay `rgba(0,0,0,0.35)`
- Hover: `translateY(-4px)` with transition `0.35s cubic-bezier(0.22, 1, 0.36, 1)`
- Label: `15px Vazirmatn`, `--ivory`, `z-index: 1`

### 6.7 Feature Rows (Zigzag)

- Flex direction alternates: normal / `row-reverse`
- Image box: `140px × 120px`, gradient background
- Offset border: `::before` pseudo-element, `1px solid var(--gold-line)`, positioned `-8px` offset
- Text: Nastaliq heading `24px`, body `14px`, gold outline CTA

### 6.8 Product Cards

- Background: `--ink-2`
- Border: `1px solid var(--ink-3)`
- `::before`: gradient overlay on image
- `::after`: inner border inset `6px`
- Image filter: `brightness(0.9) contrast(1.05)`
- Hover: `translateY(-6px)`, border → `var(--gold-line)`, shadow glow
- Index badge: `--muted-dark` text, `11px`
- Price: `--gold-100` / `--gold-200`

### 6.9 Market Section

- Panel background: `--ink-2`
- Header: uppercase `11.5px` tracking `0.18em`, `--muted` color
- Price values: `--gold-100`, `font-variant-numeric: tabular-nums`
- Live dot: `--green`, `animation: dot-pulse 1.8s infinite`
- Toggle tabs: `.button-ghost` active → `.button-gold`

### 6.10 Modals

- Overlay: `rgba(10, 8, 6, 0.85)`, `backdrop-filter: blur(6px)`
- Panel: `--ink-1` background, `0 28px 0 28px` border-radius
- Close button: `--muted` → `--cream` on hover
- Open state: `.is-open` class, `aria-hidden="false"`

### 6.11 Footer

- Background: `#0e0c0a`
- Border-top: `1px solid var(--gold-line)`
- Nastaliq CTA headline: `clamp(32px, 4vw, 48px)`
- Link columns: `12.5px Vazirmatn`, `--cream`, hover → `--gold-100`
- Copyright: `11.5px`, `--muted`

---

## 7. Animations & Motion

### Keyframes

| Name | Duration | Usage |
|------|----------|-------|
| `ticker-scroll` | `30s linear infinite` | Price ticker marquee |
| `dot-pulse` | `2.4s ease-in-out infinite` | Announcement gold dot |
| `dot-pulse` (market) | `1.8s ease-in-out infinite` | Live market indicator |
| `shimmer` | `2.5s ease infinite` | Gold button hover gradient |
| `reveal-up` | `0.7s cubic-bezier(0.22, 1, 0.36, 1)` | Scroll reveal fade-up |
| `reveal-fade` | `0.6s ease` | Simple fade-in |
| `float` | `6s ease-in-out infinite` | Decorative floating elements |

### Scroll Reveal

- `.reveal` class on elements below the fold
- `.is-visible` added by IntersectionObserver (threshold: 0.12)
- Transform: `translateY(28px)` → `translateY(0)`, opacity `0` → `1`
- Staggered delays for grouped elements (0.1s increments)

### Reduced Motion

```css
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.01ms !important;
    transition-duration: 0.01ms !important;
  }
}
```

---

## 8. Accessibility

- **Contrast**: `--cream` (#f2e7cf) on `--ink-0` (#14120f) = **12.8:1** (AAA)
- **Focus visible**: `2px solid var(--gold-100)` with `2px` offset
- **Touch targets**: minimum `44px × 44px` on all interactive elements
- **Alt text**: all product images require descriptive `alt` attributes
- **ARIA**: modals use `aria-hidden` toggle, nav uses `aria-expanded`
- **Skip link**: `.skip-link` at top of page, visible on focus
- **Keyboard**: Escape closes modals, Tab order follows visual flow

---

## 9. CSS Architecture

### File Structure

```
frontend/css/
├── style.css                    # Core design system + homepage styles
├── zarnegar-design-system.css   # Shared component library (loaded by all pages)
├── catalog.css                  # Products page grid styles
└── (no per-page CSS needed)     # index.html uses style.css only
```

### Loading Order

1. Google Fonts (Noto Nastaliq Urdu, Cormorant Garamond, Vazirmatn)
2. `zarnegar-design-system.css` — shared components (dividers, section heads)
3. `style.css` — design tokens + all page styles (cascade wins)

### Token Usage

Always use CSS custom properties, never raw hex values:

```css
/* ✅ Correct */
color: var(--gold-100);
background: var(--ink-2);

/* ❌ Wrong */
color: #e2c384;
background: #241f1a;
```

---

## 10. Print Styles

```css
@media print {
  body { background: #fff; color: #111; }
  .announcement-bar, .ticker-strip, .site-header,
  .hero-cta, .market-section, .site-footer { display: none; }
}
```

---

*Design system version: 2026-09-15 · Rahmani Haute Joaillerie*
