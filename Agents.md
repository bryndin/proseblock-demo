# Agents.md: ProseBlock Project Guide

**Purpose:** Quick reference for AI agents working on the ProseBlock Hugo theme and its demo site. Contains reusable patterns, architecture decisions, and project conventions.

**Role:** You are an expert Hugo developer and frontend CSS Architect. Your goal is to write strict, zero-dependency, vanilla code following the conventions below. **Crucially, assume you are working in a monorepo where the theme (`themes/proseblock/`) is the primary package, and the root (`.`) is for testing and providing content for the theme.**

---

## Project Overview

**ProseBlock** (`themes/proseblock`) is a content-first Hugo theme for editorial, technical, and article-driven websites. Built with vanilla CSS/JS, zero frontend dependencies. It relies on typography, spacing and small icons instead of images.
**ProseBlock-demo** (`.`) is the demo site for the ProseBlock theme.

- **Stack:** Hugo (SSG) v0.161.1+, Vanilla CSS (@layer + BEM), Vanilla ES6 Modules.
- **Key Docs:** `docs/erd.md`
- **Tests:** `tests/` (Shared python modules live in `tests/_lib/` and are not executed directly).

**🚨 CRITICAL PATHING RULE:**
All theme development (layouts, CSS, JS) **MUST** occur inside `./themes/proseblock/`. Never create or modify layouts/assets in the root `./layouts` or `./assets` directories unless explicitly instructed to override the theme for the demo site.

---

## CSS Architecture

### Cascade Layers (strict order)

```css
@layer reset, tokens, vendor, base, prose, layout, components, utilities;
```

Files **must NOT** contain `@layer` wrappers—assignment happens in `layouts/_partials/head/css.html`.

### 3-Tier Design Token System

| Tier | Scope | Example | Rule |
| ---- | ----- | ------- | ---- |
| **T1** | Primitives | `--color-gray-900` | Physical values only (OKLCH preferred) |
| **T2.1** | Global Semantic | `--text-primary` | Dark mode flips happen here only |
| **T2.2** | Component Semantic | `--header-bg`, `--metadata-text` | Aliases T2.1 |
| **T3** | Private (`--_`) | `--_bg`, `--_edge-spacing` | Inside component selector only |

### Tier 3 Structure (inside component)

```css
.c-button {
  /* @api: consume Tier 2.2 tokens */
  --_bg: var(--btn-bg-default);
  --_text: var(--btn-text-default);

  /* @internal: config affecting multiple properties */
  --_edge-spacing: var(--space-4);

  background-color: var(--_bg);
  color: var(--_text);
  padding: var(--_edge-spacing);
  gap: var(--_edge-spacing);
}

/* States: reassign variables ONLY */
.c-button:hover {
  --_bg: var(--btn-bg-hover);
}

/* Modifiers: reassign variables ONLY */
.c-button--primary {
  --_bg: var(--btn-bg-primary);
  --_text: var(--btn-text-primary);
}
```

### @provides Pattern (Parent → Child Overrides)

```css
/* Parent overrides child's Tier 2.2 API only */
/* @provides: Contextual child overrides */
.c-hero > .c-metadata {
  --metadata-text: var(--_text);  /* OK: mutates child API */
  /* display: none; */            /* FORBIDDEN: no standard properties */
  /* --_color: red; */            /* FORBIDDEN: no Tier 3 vars */
}
```

### Muting Elements (Relative Color Syntax)

```css
color: oklch(from var(--text-primary) l c h / var(--opacity-medium));
```

- **Never** use CSS `opacity` property for muting (causes cascade issues)
- **Never** create Tier 1 decomposed color channels
- Maintain WCAG 2.2 AA 4.5:1 contrast ratio

---

## Component Registration Workflow

The theme uses custom orchestrators in `layouts/_partials/head/` to bundle assets automatically. 

### CSS Components

Do **not** use `@import` statements to load new CSS components.

1. Create your component file: `themes/proseblock/assets/css/components/mycomponent.css`
2. `layouts/_partials/head/css.html` automatically bundles it via `resources.Match "css/components/*.css"`.

### JS Modules

The theme uses Hugo's `js.Build` to bundle ES modules.

1. Create your ES module: `themes/proseblock/assets/js/components/mycomponent.js`
2. You **MUST** explicitly import it into the master entry point: `themes/proseblock/assets/js/main.js`.
3. Do not use IIFEs for modular JS; use standard `export default function()` syntax.

---

## Template Patterns (Go Templates)

### Zero-Dot Policy

The literal `.` is **forbidden** outside explicit context captures.

```go
{{/* CORRECT */}}
{{- $page := . -}}
{{- $title := $page.Title -}}
{{ range $item := $collection }}
  {{ $item.Name }}
{{ end }}

{{/* WRONG */}}
{{ .Title }}
{{ range . }}
  {{ .Name }}
{{ end }}
```

### kwargs Pattern (Partial Arguments)

```go
{{/* Caller */}}
{{ partial "widgets/toc.html" (dict "page" $page "native" true) }}

{{/* Receiver - always first line */}}
{{- $kwargs := . | default dict -}}
{{- $page := $kwargs.page -}}
{{- $native := $kwargs.native | default false -}}
```

### Boolean Safety (Respecting Explicit `false`)

```go
{{- $siteEnable := site.Params.enableFeature | default true -}}
{{- $pageEnable := $siteEnable -}}
{{- if ne $page.Params.enablefeature nil -}}
  {{- $pageEnable = $page.Params.enablefeature -}}
{{- end -}}
```

### API Contract Header

```go
{{- /*
  @api: param1, param2, param3
  Dependencies: site.Params.X, $page.Params.Y
*/ -}}
```

---

## File Organization

```text
themes/proseblock/
├── assets/
│   ├── css/
│   │   ├── tokens.css          # Tier 1 + 2 tokens
│   │   ├── base.css            # Bare HTML tags
│   │   ├── prose.css           # Typography
│   │   ├── layout/             # Page-level grids
│   │   └── components/         # BEM components (one file each)
│   ├── js/
│   │   ├── main.js             # Entry point
│   │   └── components/         # Modular JS (IIFE or ES modules)
│   └── vendor/                 # Third-party libs (one folder per package)
│       ├── clipboard/
│       └── syntax-highlighting/
├── layouts/
│   ├── _partials/
│   │   ├── head/               # CSS/JS injection
│   │   ├── widgets/            # Sidebar widgets
│   │   └── svg/                # Inline icons
│   ├── _markup/                # Render hooks (code blocks, admonitions)
│   └── _default/               # Base templates
```

---

## Icon System (SVG)

- Stored in `layouts/_partials/svg/`
- Injected as inline SVG (no network request)
- Must have `aria-hidden="true"` by default
- Accept `$ariaLabel` param for standalone icons (injects `<title>`, removes `aria-hidden`)
- `viewBox="0 0 24 24"` normalized

```go
{{ partial "svg/icon.html" (dict "name" "github" "ariaLabel" "GitHub") }}
```

---

## Testing & Linting

Run all lints via Make from the root directory: `make lint`.
To run a specific file individually: `.venv/bin/python tests/<filename>.py`

> **Note:** Shared libraries for Python scripts are stored in `tests/_lib/` and should not be executed directly.

| Script | Purpose |
| ------ | ------- |
| `lint_css_tiers.py` | Token tier violations |
| `lint_css_layers.py` | `@layer` in source files (forbidden) |
| `lint_css_provides.py` | `@provides` block validity |
| `lint_css_states.py` | State selector rules (vars only) |
| `lint_css_relative_colors.py` | OKLCH relative color syntax |
| `lint_templates_kwargs_defaults.py` | `$kwargs` default patterns |
| `lint_templates_dangling_periods.py` | Zero-dot policy enforcement |

### CI Pipeline

1. Pre-build: Stylelint, ESLint, Hugo build
2. Post-build: HTMLHint, axe-cli (WCAG 2.2 AA)
3. Deploy: GitHub Pages (only if all checks pass)

---

## Common Reusable Snippets

### Component CSS Boilerplate

```css
/* themes/proseblock/assets/css/components/my-component.css */
.c-my-component {
  /* @api */
  --_bg: var(--my-component-bg);
  --_text: var(--my-component-text);

  /* @internal */
  --_padding: var(--space-4);

  background-color: var(--_bg);
  color: var(--_text);
  padding: var(--_padding);
}

.c-my-component:hover {
  --_bg: var(--my-component-bg-hover);
}

.c-my-component--variant {
  --_text: var(--my-component-text-variant);
}
```

### Widget Partial Boilerplate

```go
{{- /* Widget: My Widget */ -}}
{{- $kwargs := . | default dict -}}
{{- $title := $kwargs.title | default "My Widget" -}}
{{- $limit := $kwargs.limit | default 10 -}}

<div class="c-widget-my">
  <h3 class="c-widget-my__title">{{ $title }}</h3>
  {{/* Widget content */}}
</div>
```

### Render Hook Boilerplate

```go
{{- /* layouts/_markup/render-blockquote.html */ -}}
{{- $page := .Page -}}
{{- $content := .Text -}}

<blockquote class="c-blockquote">
  {{ $content | safeHTML }}
</blockquote>
```

### JS Component Boilerplate (ES Module)

```javascript
// themes/proseblock/assets/js/components/my-component.js
export default function initMyComponent() {
  const elements = document.querySelectorAll('.js-my-component');
  if (!elements.length) return;

  elements.forEach(el => {
    // Component logic
  });
}

// In themes/proseblock/assets/js/main.js:
// import initMyComponent from './components/my-component';
// document.addEventListener('DOMContentLoaded', initMyComponent);
```

---

## Hugo Commands

```bash
# Dev server
make dev

# Build (with verbose output and strict flags)
VERBOSE=1 make build
```

---

## Decision Log

| Decision | Context |
| -------- | ------- |
| CSS Layers over specificity hacks | Flat specificity, predictable cascade |
| 3-Tier Tokens over flat variables | Encapsulation + automatic dark mode |
| `@provides` pattern | Parent-child styling without global leakage |
| kwargs pattern | Named partial arguments, explicit contracts |
| Zero-dot policy | Eliminate Go template scope bleeding |
| Hugo Pipes over Node.js | Zero-dependency build pipeline |
| Vendor layer for 3rd party | Isolated, easily overridable |
| Render hooks over shortcodes | Native Markdown compatibility |

---

## Troubleshooting

| Issue | Check |
| ----- | ----- |
| CSS not applying | Verify layer order in `css.html`, check lint output |
| Dark mode not flipping | Only T2.1 tokens should change in `[data-theme="dark"]` |
| Template scope bug | Search for dangling `.` with `lint_templates_dangling_periods.py` |
| Partial argument not passing | Ensure `dict` keys match partial's `$kwargs.X` |
| Stylelint error | OKLCH format, no `@layer` in source files |

---

*Last updated: Generated from project docs. Keep in sync with `docs/erd.md`
