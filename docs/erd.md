---
date: "2026-04-16T14:50:00-07:00"
title: "ERD: ProseBlock"
description: "Engineering Requirements Document (ERD): Project 'ProseBlock'"
summary: |
  Engineering Requirements Document (ERD): Project "ProseBlock".
  **Version:** 1.1
  **Date:** April 2026
---

**Version:** 1.1
**Date:** April 2026
**Derived from:** PRD v6.2, VDD v0.3 & DTS v1.0
**Target Architecture:** Static Site Generation (Hugo), zero-dependency frontend.

## 1. System Architecture & Asset Pipeline

### 1.1 Core Methodology

ProseBlock utilizes Vanilla CSS and Vanilla JavaScript. It achieves modularity, maintainability, and flat specificity by combining **CSS Cascade Layers**, strict **BEM naming**, and a **3-Tier CSS Custom Property (Variable) system**. The templating system enforces explicit local variables to eliminate Go-template scope bleeding.

### 1.2 CSS Bundling (Hugo Pipes)

To process stylesheets securely and efficiently without relying on external Node.js bundlers, the theme strictly utilizes **Hugo Pipes**.

CSS assets are stored in `assets/css/`. Third-party libraries are co-located in `assets/vendor/` (see Section 1.6). Standard `@import` statements inside CSS files are processed via Hugo's `resources.ExecuteAsTemplate` and `resources.Concat` pipeline. This resolves file lookup scopes, allows template variable injection into CSS, and inherently solves any "404 not published" errors.

The CSS orchestrator (`layouts/_partials/head/css.html`) defines the layer order and concatenates the files.

---

### 1.3 CSS Cascade Layers (`@layer`)

All CSS is scoped into an ordered layer hierarchy to eliminate specificity conflicts. Later layers explicitly override earlier ones, regardless of selector weight.

1. `reset`: Minimal resets (box-sizing, margin clearing).
2. `tokens`: CSS Custom Properties (Variables) registry.
3. `vendor`: Third-party library styles (syntax-highlighting, etc.).
4. `base`: Bare HTML tags (crucial for raw Markdown output).
5. `prose`: Typography styles for rich content.
6. `layout`: Macro-level structural grids (page wrappers, header, footer).
7. `components`: Encapsulated UI elements (widgets, cards).
8. `utilities`: Immutable helper classes (`.u-sr-only`, `.u-mt-4`).

**Implementation Rule:** To ensure absolute, centralized control over the cascade, individual CSS files **must not** contain `@layer` wrappers. Instead, layer assignment is orchestrated dynamically during the Hugo asset pipeline via `layouts/_partials/head/css.html`.

### 1.4 JavaScript Architecture

Vanilla JS must be used for core interactions. To prevent global scope pollution, all scripts must be authored as ES Modules or wrapped in an IIFE.
The primary entry point `assets/js/main.js` must be processed via Hugo's `js.Build` to bundle dependencies, minify, and fingerprint the output. Script tags must be injected with the `defer` attribute.

### 1.5 Iconography (SVG)

Icons are stored in `layouts/_partials/svg/` and injected as inline SVGs to eliminate secondary network requests.
**Accessibility Constraint:** All inline SVGs must include `aria-hidden="true"` by default. If an icon is standalone (no accompanying text), the partial must accept an `$ariaLabel` parameter to inject a `<title>` and remove `aria-hidden`. `viewBox` attributes must be strictly normalized (e.g., `0 0 24 24`).

### 1.6 Vendor Directory (`assets/vendor/`)

Third-party libraries are organized in a **package-based structure** under `assets/vendor/`. Each package lives in its own subdirectory, co-locating CSS and JS files when applicable.

**Directory Structure:**

```text
assets/
├── css/           # Theme styles
├── js/            # Theme scripts
└── vendor/        # Third-party libraries (one folder per package)
    ├── clipboard/
    │   └── clipboard.min.js
    └── syntax-highlighting/
        ├── code-highlight-github.css
        └── code-highlight-github-dark.css
```

**Rules for Adding Third-Party Content:**

1. **Package-per-Folder:** Each library gets its own subdirectory (e.g., `vendor/swiper/`, `vendor/photoswipe/`).
2. **Co-location:** If a library provides both CSS and JS, both files belong in the same package folder.
3. **No Modification:** Vendor files must remain unmodified. If patches are required, use CSS layer overrides.
4. **Import Paths:**
   - JS: `import Library from "../../vendor/package/file.js";` (relative from `js/components/`)
   - CSS: Referenced via `vendor/**/*.css` glob in the Hugo CSS pipeline

**Rationale:** High cohesion—removing a library requires deleting a single folder. The `vendor` cascade layer ensures third-party styles are isolated and easily overridable.

---

## 2. Design Token System

To maintain scalability and a DRY dark mode, the theme enforces a strict **3-tier CSS Custom Property architecture**.

### 2.1 Tier 1: Primitives (Global Palette & Scales)

Raw values strictly defined inside the `:root` selector.

* **Rule:** Names MUST describe *what the value physically is* (e.g., `--color-gray-900`, `--space-4`), not *how it is used*. OKLCH is the standard color format.

### 2.2 Tier 2: Semantic (Contextual)

Abstract names representing design intent. This tier acts as the central configuration registry and is split into two sub-levels:

* **Tier 2.1: Global Semantics:** Broad abstractions (e.g., `--text-primary`). Must map to *Tier 1 Primitives* or other *Tier 2.1* variables. **Only variables in this tier should be reassigned inside the `[data-theme="dark"]` selector.**
* **Tier 2.2: Component Semantics:** Component-specific hooks (e.g., `--header-bg`, `--metadata-text`) that alias *Tier 2.1* variables. They automatically inherit dark mode flips.

### 2.3 Tier 3: Private Component Variables (`--_name`)

Defined strictly inside specific component base selectors (e.g., `.c-header`) to ensure encapsulation. We divide Tier 3 custom property declarations into specific, tagged blocks:

* **API (`@api` tagged):** Declare private variables referencing ingested Tier 2.2 Component Semantics (what the component needs for itself).
* **Configuration (`@internal` tagged):** Private component configuration registry.

**Deterministic Rules for `@internal` Variables:**

1. **Grouping Intent:** `@internal` variables MUST be used when a single value dictates multiple CSS properties (e.g., `--_edge-spacing` applying to both `padding` and `gap`).
2. **Interactive Base:** `@internal` variables MUST be used to define initial values that will be reassigned by interactive states or BEM modifiers (see 2.5 State Architecture).
3. **No Redundant Boilerplate:** An `@internal` variable MUST NOT be created for a static property that is used exactly once and never changes state. (Variables mapped 1:1 to single static properties are forbidden).

**LLM Code Generation Example (Tier 3):**

```css
.c-card {
  /* @api */
  --_bg: var(--card-bg);

  /* @internal */
  --_edge-spacing: var(--space-4); /* Rule 1: Used multiple times */
  
  background-color: var(--_bg);
  padding: var(--_edge-spacing);
  gap: var(--_edge-spacing);
  
  /* Rule 3: Permitted static assignment (no variable needed) */
  display: flex; 
}
```

### 2.4 Component Overrides and Contextual Mutations (`@provides`)

Parents often dictate the styling of child components (e.g., a Hero component forcing a nested Metadata component to use inverse colors).

**Deterministic Rules for Overrides:**

1. **No Global Mutation:** A parent component MUST NOT redefine a Tier 2.2 token globally on its own root class.
2. **Explicit Targeting:** Contextual overrides MUST use a strict descendant selector (`.parent .child`). To prevent deep inheritance bleeding into unrelated nested components (e.g., a Card inside a Hero), prefer the direct child combinator (`.parent > .child`) when applicable. Ambient token injection on the parent root (e.g., `.c-hero { --child-token: red; }`) is STRICTLY FORBIDDEN as it breaks encapsulation and bleeds infinitely down the DOM.
3. **No Fallbacks:** Components MUST rely on strict assignment, completely avoiding CSS custom property fallbacks (`var(--a, var(--b))`) to prevent hidden visual bugs.
4. **The `@provides` Block:** Parent components overriding children MUST declare this in a comment block tagged `@provides`.
5. **API Mutation Only:** The override block MUST ONLY contain custom property reassignments that belong to the child's explicit Tier 2.2 API. Standard CSS properties (e.g., `margin`, `display`) or private Tier 3 variables (`--_`) are strictly forbidden. Layout spacing MUST be handled by the parent's own grid/flex gaps or layout wrappers.

**LLM Code Generation Example (Overrides):**

```css
/* tokens.css (Central Registry) */
:root {
  --text-primary: var(--color-gray-900);
  --metadata-text: var(--text-primary);
  --hero-text: var(--color-white);
}

/* components/metadata.css (Child) */
.c-metadata {
  /* @api */
  --_color: var(--metadata-text);
  color: var(--_color);
}

/* components/hero.css (Parent) */
.c-hero {
  /* @api */
  --_text: var(--hero-text);
  color: var(--_text);
}

/* @provides: Contextual child overrides */
.c-hero .c-metadata {
  /* Strict target mutation. Safely modifies child's API without global leakage. */
  --metadata-text: var(--_text);
  
  /* FORBIDDEN: display: none; margin-top: 1rem; --_color: red; */
}
```

### 2.5 State and Variant Architecture

Components handle visual permutations via BEM modifiers (`.c-block--modifier`) and interactive pseudo-classes (`:hover`, `:focus-visible`, `[aria-expanded="true"]`).

**Deterministic Rules for State and Variants:**

1. **Variable Reassignment Only:** Modifier and state selectors MUST ONLY reassign Tier 3 (`--_`) custom properties.
2. **No Property Redeclaration:** Modifier and state selectors MUST NOT declare standard CSS properties (e.g., `background-color`, `border`).
3. **Co-location:** State selectors MUST immediately follow the base component selector they modify.

**LLM Code Generation Example (State/Variants):**

```css
.c-button {
  /* @api: Base state variables */
  --_bg: var(--btn-bg-default);
  --_text: var(--btn-text-default);
  
  background-color: var(--_bg);
  color: var(--_text);
  transition: background-color 0.2s ease;
}

/* Interactive States: Mutate variables only */
.c-button:hover {
  --_bg: var(--btn-bg-hover);
}

/* BEM Modifiers: Mutate variables only */
.c-button--primary {
  --_bg: var(--btn-bg-primary);
  --_text: var(--btn-text-primary);
}
```

### 2.6 Muting Elements (Relative Color Syntax)

To establish typographic hierarchy (e.g., muting subtitles, metadata, borders), developers MUST use **CSS Relative Color Syntax** to apply alpha (transparency) dynamically.

* **Implementation:** Use the `from` keyword combined with OKLCH syntax and Tier 1 Opacity primitives:
  `color: oklch(from var(--text-primary) l c h / var(--opacity-medium));`
* **Rationale:** Relative color syntax eliminates the need to pollute Tier 1 with decomposed color channels. It harmonizes seamlessly with underlying background shifts across light and dark themes, and strictly isolates the muting effect to the target element (avoiding the cascading side-effects of CSS `opacity`).
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

ProseBlock heavily relies on Hugo Render Hooks (`layouts/_markup/`) to upgrade standard Markdown into rich UI components without proprietary shortcodes.

* **Code Blocks:** `render-codeblock.html` intercepts backticks, applying Chroma syntax highlighting inside a custom UI shell featuring a native copy-to-clipboard button.
* **Automated Syntax Theming:** Syntax highlighting CSS is generated via `hugo gen chromastyles`. **Manual editing is forbidden.** The generated CSS files are placed in `assets/vendor/syntax-highlighting/` and loaded via the `vendor` cascade layer.
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
