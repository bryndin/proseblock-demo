---
date: "2026-04-16T14:50:00-07:00"
title: "ERD: Theme X"
description: "Engineering Requirements Document (ERD): Project 'Theme X'"
summary: |
  Engineering Requirements Document (ERD): Project "Theme X".
  **Version:** 1.1
  **Date:** April 2026
---

**Version:** 1.1
**Date:** April 2026
**Derived from:** PRD v6.2, VDD v0.3 & DTS v1.0
**Target Architecture:** Static Site Generation (Hugo), zero-dependency frontend.

## 1. System Architecture & Asset Pipeline

### 1.1 Core Methodology

Theme X utilizes Vanilla CSS and Vanilla JavaScript. It achieves modularity, maintainability, and flat specificity by combining **CSS Cascade Layers**, strict **BEM naming**, and a **3-Tier CSS Custom Property (Variable) system**. The templating system enforces explicit local variables to eliminate Go-template scope bleeding.

### 1.2 CSS Bundling (Hugo Pipes)

To process stylesheets securely and efficiently without relying on external Node.js bundlers, the theme strictly utilizes **Hugo Pipes**.

Assets are stored in `assets/css/`. Standard `@import` statements inside CSS files are processed via Hugo's `resources.ExecuteAsTemplate` and `resources.Concat` pipeline. This resolves file lookup scopes, allows template variable injection into CSS, and inherently solves any "404 not published" errors.

The CSS orchestrator (`layouts/_partials/head/css.html`) defines the layer order and concatenates the files.

---

### 1.3 CSS Cascade Layers (`@layer`)

All CSS is explicitly scoped into ordered layers to eliminate specificity conflicts. Later layers explicitly override earlier ones, regardless of selector weight.

1. `reset`: Minimal resets (box-sizing, margin clearing).
2. `tokens`: CSS Custom Properties (Variables) registry.
3. `base`: Bare HTML tags (crucial for raw Markdown output).
4. `layout`: Macro-level structural grids (page wrappers, header, footer).
5. `components`: Encapsulated UI elements (widgets, cards).
6. `utilities`: Immutable helper classes (`.u-sr-only`, `.u-mt-4`).

Layers are defined in `layouts/_partials/head/css.html`.

### 1.4 JavaScript Architecture

Vanilla JS must be used for core interactions. To prevent global scope pollution, all scripts must be authored as ES Modules or wrapped in an IIFE.
The primary entry point `assets/js/main.js` must be processed via Hugo's `js.Build` to bundle dependencies, minify, and fingerprint the output. Script tags must be injected with the `defer` attribute.

### 1.5 Iconography (SVG)

Icons are stored in `layouts/_partials/svg/` and injected as inline SVGs to eliminate secondary network requests.
**Accessibility Constraint:** All inline SVGs must include `aria-hidden="true"` by default. If an icon is standalone (no accompanying text), the partial must accept an `$ariaLabel` parameter to inject a `<title>` and remove `aria-hidden`. `viewBox` attributes must be strictly normalized (e.g., `0 0 24 24`).

---

## 2. Design Token System

To maintain scalability and a DRY dark mode, the theme enforces a strict **3-tier CSS Custom Property architecture**.

### 2.1 Tier 1: Primitives (Global Palette & Scales)

Raw values strictly defined inside the `:root` selector.

* **Rule:** Names must describe *what the value physically is* (e.g., `--color-gray-900`, `--space-4`), not *how it is used*. OKLCH is the standard color format.

### 2.2 Tier 2: Semantic (Contextual)

Abstract names representing design intent. This tier is split into two sub-levels:

* **Tier 2.1: Global Semantics:** Broad abstractions (e.g., `--text-primary`). Must map directly to *Tier 1 Primitives*. **Only variables in this tier should be reassigned inside the `[data-theme="dark"]` selector.**
* **Tier 2.2: Component Semantics:** Component-specific hooks (e.g., `--header-bg`, `--metadata-color`) that alias *Tier 2.1* variables. They automatically inherit dark mode flips.

### 2.3 Tier 3: Private Component Variables (`--_name`)

Defined strictly inside specific component selectors (e.g., `.c-header`) to ensure encapsulation. The CSS cascading order dictates that variables flow downward; thus, we divide Tier 3 blocks into three strict tagging sections:

* **API:** (`@api` tagged) Declare private variables referencing ingested Tier 2.2 Component Semantics (what the component needs for itself).
* **Provides:** (`@provides` tagged) Reassign Tier 2.2 variables to push contextual styles down to nested child components. This loosely couples parents to children without breaking BEM encapsulation.
* **Configuration:** (`@internal` tagged) Hardcoded structural values or Tier 1 references (e.g., `--_padding: var(--space-4);`). Magic numbers must be quarantined here and never written inline in the CSS body.

**Example: Component Overriding (Hero overriding Metadata child)**

```css
/* ==============================================
   1. tokens.css (Central Registry)
   ============================================== */
:root {
  /* Tier 2.1 */
  --text-primary: var(--color-gray-650);
  --text-secondary: var(--color-gray-500);

  /* Tier 2.2 Defaults */
  --metadata-color: var(--text-secondary);
  --hero-text: var(--text-primary);
}

/* ==============================================
   2. components/metadata.css (Child)
   ============================================== */
.c-metadata {
  /* @api: Ingested Semantics */
  --_color: var(--metadata-color);

  color: var(--_color); /* Applies to text, SVG currentcolor, and separators */
}

/* ==============================================
   3. components/hero.css (Parent)
   ============================================== */
.c-hero {
  /* @api: Ingested Semantics */
  --_bg: var(--hero-bg);
  --_text: var(--hero-text);

  /* @provides: Contextual Overrides
     Forces any .c-metadata nested inside this hero
     to inherit the hero's text color. */
  --metadata-color: var(--_text);

  /* @internal: Geometry & Layout */
  --_padding-y: var(--space-8);

  background-color: var(--_bg);
  color: var(--_text);
  padding-block: var(--_padding-y);
}
```

### 2.4 Muting Secondary Elements (Color Alpha)

To establish typographic hierarchy (e.g., muting subtitles, metadata, captions), developers MUST use **Color Alpha** (semi-transparent colors) rather than CSS `opacity` or solid grayscale colors.

* **Implementation:** Apply the alpha channel natively using the standard OKLCH format (e.g., `color: oklch(var(--text-primary-lch) / 0.6);`) or via designated Tier 2 semantic tokens (e.g., `--text-muted`).
* **Rationale:** Color alpha adapts dynamically, harmonizing with underlying background shifts across light and dark themes. It strictly isolates the muting effect to the text element, explicitly avoiding the side-effects of CSS `opacity` (which inescapably mutes vivid child elements and triggers unwanted stacking contexts).
* **Constraint:** Alpha-muted text MUST maintain a minimum WCAG 2.2 AA **4.5:1 contrast ratio** against the background layer.

---

## 3. Template Engineering Guardrails

To ensure a resilient, debuggable Go-template codebase, developers must adhere to strict data-flow constraints.

### 3.1 Zero-Dot Policy (No Dangling Periods)

The literal `.` (dot) is **forbidden** in all template expressions except during explicit context captures at the absolute top of a file or scope. Go templating context shifts unpredictably inside loops and conditionals; relying on the bare dot causes untraceable scope bugs.

1. **Every template must open** with an explicit assignment: `{{- $page := . -}}` (or `$kwargs := .`).
2. **Never pass `.` as an argument**. Always pass the captured variable: `{{ partial "seo.html" $page }}`.
3. **Always use named iteration:** `{{ range $item := $collection }}` (Never `{{ range . }}`).

### 3.2 Dictionary Arguments (`$kwargs`)

When passing multiple arguments to a partial, use `dict`. The receiving partial must unpack this explicitly into local variables.

**Caller:**

```go
{{ partial "widgets/toc.html" (dict "page" $page "native" true) }}
```

**Receiver (`toc.html`):**

```go
{{- $kwargs := . -}}
{{- $page := $kwargs.page -}}
{{- $native := $kwargs.native | default false -}}
```

### 3.3 Explicit Parameter Declaration (API Contract)

All references to global configuration (`site.Params`) or page front-matter (`$page.Params`) must be declared as local variables at the very top of the template.

* **Rule:** Accessing `.Params` directly within HTML structures or business logic is prohibited.
* **Boolean Safety:** When checking boolean parameters, account for explicit `false` overrides to prevent `default true` from erroneously overriding user intent.

**Example (Production API Contract):**

```go
{{- $kwargs := . -}}
{{- $page := $kwargs.page -}}

/* @api: text, text-hover, accent, rail-bg, separator */
{{- $native := $kwargs.native | default false -}}
{{- $siteEnableTOC := site.Params.enableTOC | default true -}}

{{- /* Safely extract boolean, respecting explicit 'false' */ -}}
{{- $pageEnableTOC := $siteEnableTOC -}}
{{- if ne $page.Params.enabletoc nil -}}
  {{- $pageEnableTOC = $page.Params.enabletoc -}}
{{- end -}}

{{- $isEnabled := and $native $pageEnableTOC -}}
```

---

## 4. Markdown & Render Hooks

Theme X heavily relies on Hugo Render Hooks (`layouts/_markup/`) to upgrade standard Markdown into rich UI components without proprietary shortcodes.

* **Code Blocks:** `render-codeblock.html` intercepts backticks, applying Chroma syntax highlighting inside a custom UI shell featuring a native copy-to-clipboard button.
* **Automated Syntax Theming:** Syntax highlighting CSS is generated via `hugo gen chromastyles`. **Manual editing is forbidden.** The dark theme payload must be wrapped via a deterministic build script (`npm run build:syntax`) that outputs a `.c-chroma-dark` layer file to prevent drift.
* **Admonitions:** `render-blockquote.html` parses GitHub-flavored alert syntax (`> [!NOTE]`) into semantic components.

---

## 5. End-User Customization

Users can extend the theme gracefully via `customCSS` and `customJS` parameters in `hugo.toml`.

**Architecture Advantage:** Because the theme operates strictly on CSS `@layer`, any standard CSS written by the end-user in their custom stylesheet is inherently **unlayered**. By CSS specification, unlayered styles automatically possess higher priority than layered styles.

* Users can simply write `.c-header { background: red; }` in their custom CSS, and it will effortlessly override the theme's default styles without requiring `!important` tags or complex specificity hacks.

---

## 6. Testing, QA, & CI/CD

Quality Assurance avoids brittle E2E browser tests in favor of high-fidelity static analysis on Hugo's output.

### 6.1 Automated Linting (Pre-Build)

* **CSS:** `Stylelint` enforces standard formatting, variable naming conventions, and OKLCH syntax.
* **JS:** `ESLint` ensures vanilla ES6 conventions and prevents global scope leaks.
* **Hugo Build:** Executed with strict flags (`hugo --printI18nWarnings --printPathWarnings --printUnusedTemplates --minify --gc`).

### 6.2 Post-Build Analysis (CI Pipeline)

The GitHub Actions pipeline builds the site and validates the static `/public/` directory:

1. **HTML Validation:** `HTMLHint` scans for unclosed tags and invalid nesting.
2. **WCAG Compliance:** `axe-cli` scans for contrast failures, missing ARIA labels, and structural accessibility issues. **The build fails if WCAG 2.2 AA standards are violated.**
3. **Deployment:** Merges to `main` automatically publish to GitHub Pages via `actions/deploy-pages` exclusively if all post-build steps pass.
