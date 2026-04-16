---
date: "2026-04-16T14:50:00-07:00"
draft: true
title: "ERD: Theme X"
description: "Engineering Requirements Document (ERD): Project 'Theme X'"
summary: |
  Engineering Requirements Document (ERD): Project "Theme X".
  **Version:** 1.0
  **Date:** April 2026
---

**Version:** 1.0
**Date:** April 2026
**Derived from:** PRD v6.2, VDD v0.3 & DTS v1.0

## 1. CSS Architecture

### 1.1 Core Methodology

The theme utilizes Vanilla CSS without preprocessors (no Sass/Tailwind). It achieves modularity, maintainability, and flat specificity by combining **CSS Cascade Layers**, strict **BEM naming**, and a **3-Tier CSS Custom Property (Variable) system**. Templating system uses local variables to avoid scope bugs.

---

### 1.2 Cascade Layers (`@layer`)

All CSS are explicitly loaded into the following ordered layers to eliminate specificity conflicts. Later layers override earlier ones, regardless of selector weight.

1. `reset`: Custom minimal reset (box-sizing, margin clearing, image defaults).
2. `tokens`: Definition of all CSS Custom Properties (Variables).
3. `base`: Styling of bare HTML tags (crucial for Hugo markdown output).
4. `layout`: Macro-level structural grids (the 2-column layout, header, footer).
5. `components`: Self-contained, encapsulated UI elements (widgets, cards, code blocks).
6. `utilities`: Single-purpose helper classes (e.g., `.u-sr-only` for screen readers).

Layers are defined in `layouts/_partials/head/css.html`.

#### 1.2.1 Workaround for Hugo inability to import CSS files from `assets/` directory

The theme uses Hugo's native templating engine as a CSS bundler.

- **The Problem:** Native CSS `@import` statements for files inside Hugo's `assets/` directory return 404 MIME type errors because the files are not published to the server.
- **The Solution (`ExecuteAsTemplate`):** The orchestrator file (`css.html`) declares the `@layer` order by appending the content of each layer file to a slice in order. It then concatenated these slices, runs `ExecuteAsTemplate` to process any Hugo template variables inside the combined CSS, and finally outputs the result.

Example (`layouts/_partials/head/css.html`):

```Go
{{- /* 1. Initialize an empty slice to hold all our CSS resources */ -}}
{{- $cssSlice := slice -}}

{{- /* 2. Append individual base files */ -}}
{{- $cssSlice = $cssSlice | append (resources.Get "css/reset.css") -}}
{{- $cssSlice = $cssSlice | append (resources.Get "css/tokens.css") -}}
{{- $cssSlice = $cssSlice | append (resources.Get "css/base.css") -}}

{{- /* 3. Append Layout files naturally flattened by ranging over them */ -}}
{{- range resources.Match "css/layout/*.css" -}}
  {{- $cssSlice = $cssSlice | append . -}}
{{- end -}}

{{- /* 4. Append Component files */ -}}
{{- range resources.Match "css/components/*.css" -}}
  {{- $cssSlice = $cssSlice | append . -}}
{{- end -}}

{{- /* 5. Append final utilities */ -}}
{{- $cssSlice = $cssSlice | append (resources.Get "css/utilities.css") -}}
...
```

---

### 1.3 The 3-Tier Design Token API

Variables are declared in the `tokens` layer and cascade down to components. To maintain high scalability, DRY dark mode overrides, and encapsulated components, the theme enforces a strict 3-tier CSS Custom Property architecture.

- **Tier 1: Primitives (Global Palette):** Raw values strictly defined inside the `:root` selector. **All** primitive values (including those only intended for Dark Mode, like True Charcoals) must be defined here to act as a single global registry.
  - _Rule:_ No semantic names are allowed here (e.g., use `--color-gray-900`, not `--text-color`).

Example (top of `tokens.css`):

```css
:root {
  /* Tier 1: Primitives */
  --color-white: oklch(100% 0 0);
  --color-gray-100: oklch(96% 0.005 90);
  --color-gray-900: oklch(18% 0.01 90);
  --font-sans: "Inter", system-ui, sans-serif;
  --space-4: 1rem;
}
```

- **Tier 2: Semantic (Contextual):** Meaningful names representing design intent. No raw values (Primitives) may be declared inside this block. To keep theming scalable and Dark Mode DRY, this tier is strictly split into two sub-levels:
  - **Tier 2.1: Global Semantics:** Broad abstractions (e.g., `--text-primary`, `--bg-secondary`) that map directly to *Tier 1 Primitives*. **Only these variables should be reassigned inside the `[data-theme="dark"]` selector**, ensuring 90% of the site inverts automatically.
  - **Tier 2.2: Component Semantics:** Component-specific hooks (e.g., `--article-title-text`, `--header-bg`) that map strictly to *Tier 2.1 Global Semantics*. They inherit dark mode flips automatically and should only be explicitly redefined in dark mode if a component structurally deviates from the global pattern.

Example (`tokens.css`):

```css
:root {
  /* Tier 2.1: Global Semantics */
  --text-primary: var(--color-gray-900);
  --bg-primary: var(--color-white);

  /* Tier 2.2: Component Semantics */
  --article-title-text: var(--text-primary);
  --header-bg: var(--bg-primary);
}

[data-theme="dark"] {
  /* Flipping 2.1 automatically updates 2.2 without redeclaring it */
  --text-primary: var(--color-gray-100);
  --bg-primary: var(--color-gray-900);
}
```

- **Tier 3: Private Component Variables (`--_name`)**: Defined strictly inside specific component selectors (e.g., `.c-header { ... }`) to ensure total encapsulation. All "magic values" in the component's CSS body must be factored out into these variables. They are split into two mandatory sections:
  - **Arguments (The Public API):** Declares private variables referencing _only_ the specific "Tier 2.2: Component Semantics" declared for this component (e.g., `--_bg: var(--header-bg);`).
    - _Rule:_ They must **not** refer to direct values, Tier 1 Primitives, or _Tier 2.1 Global Semantics_ (like `--text-primary`).
    - _Purpose:_ Safely connects the component to global theming hooks without risking side effects from broader semantic changes.

  - **Configuration (Internal Styling):** Declares private variables using direct values or referencing _only_ "Tier 1: Primitives" (e.g., `--_padding: var(--space-4);`).
    - _Rule:_ They must **not** refer to Tier 2 Semantics.
    - _Purpose:_ Locks the component's internal geometry and layout defaults to the design system's primitive scales, keeping structural intent completely isolated from semantic color/theming shifts.

Example:

```css
.c-header {
  /* *** Arguments (The Public API) ****************************************************** */
  --_bg: var(--header-bg);
  --_text: var(--header-text);

  /* *** Configuration (Internal Styling) ************************************************** */
  --_padding-y: var(--space-4);
  --_padding-x: var(--space-6);
  --_title-font: var(--font-sans);
  --_transition: 150ms ease;

  background-color: var(--_bg);
  color: var(--_text);
  padding: var(--_padding-y) var(--_padding-x);
  font-family: var(--_title-font);
  transition: background-color var(--_transition);
}
```

---

### 1.4 Syntax Highlighting

The theme strictly avoids custom CSS syntax mapping. It utilizes `hugo gen chromastyles` to dump native Light and Dark themes. The Dark theme output is manually nested inside a `[data-theme="dark"]` selector to ensure seamless toggling.

---

### 1.6 Render Hooks Architecture

The theme utilizes Hugo Render Hooks (located in `layouts/_markup/`) to intercept standard Markdown and automatically upgrade it to rich UI components, preventing the need for proprietary shortcodes.

- **Code Blocks (`render-codeblock.html`):** Wraps standard backticks in a custom UI shell featuring native Chroma highlighting and a Vanilla JS copy-to-clipboard button.
- **Admonitions (`render-blockquote.html`):** Intercepts GitHub-flavored alert syntax (`> [!NOTE]`) to output specific SVG icons and colored overlays, falling back to standard blockquotes otherwise.

---

### 1.7 JavaScript Architecture

Vanilla JS is used sparingly for core interactions.
`themes/theme-x/assets/js/main.js` is the main entry point for all JavaScript code.

---

### 1.8 Icons

SVG icons are stored in `themes/theme-x/layouts/_partials/svg` as Hugo partials, to enable inline SVGs.
They must not be stored as standalone `.svg` files, nor hardcoded directly into HTML or templates.

---

## 2. Best Practices

To ensure a resilient codebase, developers must adhere to:

### 2.1 Zero-Dot Policy (No Dangling Periods)

The literal `.` (dot) is **forbidden** in all template expressions except during explicit context captures (e.g., assigning `$variable := .` or `$page := $kwargs.page`). While these captures are generally done at the entry point of a template or loop, they are the only permitted use of a bare dot. Go templating context shifts unpredictably inside `{{ range }}`, `{{ with }}` and similar blocks — relying on the dangling dot causes scope bugs that are hard to trace and debug.

**Rules:**

1. **Every template/partial must open** with `{{- $page := . -}}` (or `$page := $kwargs.page` for dict-context partials).
2. **Never pass `.` as an argument** — use `$page` in `partial`, `block`, and `ExecuteAsTemplate` calls.
3. **Use `with $var :=` for conditional assignments** — write `{{ with $var := expr }}` to bind the value to a named variable, keeping the dot untouched.
4. **Always use named iteration variables** in `range` — write `range $i, $item := $collection` (if index is needed) or `range $item := $collection` (if index is not used). Never include `$i` if it's not used in the code. Never use bare `range $collection`.
5. **Always use named variables for `with` blocks** — write `{{ with $var := expr }}` to bind the value to a named variable, keeping the dot untouched.
6. **The only allowed occurrence of bare `.`** is the initial capture `$variable := .` at the top of each template scope.

**Example (good — `with $var :=`, named range variables, `$page` passed to partials):

  ```Go
  {{- $kwargs := . }}
  {{- $page := $kwargs.page }}
  {{- $menuID := $kwargs.menuID }}

  {{- with $menuEntries := index site.Menus $menuID }}
    <nav>
      <ul>
        {{- range $entry := $menuEntries }}
          {{- $name := $entry.Name }}
          {{- with $identifier := $entry.Identifier }}
            {{- with $translated := T $identifier }}
              {{- $name = $translated }}
            {{- end }}
          {{- end }}
        {{- end }}
      </ul>
    </nav>
  {{- end }}
  ```

**Example (bad — dangling periods `.`, `.Name`, `.Identifier`, `.` passed to `T`):

  ```Go
  {{- $name := .Name }}
  {{- with .Identifier }}
    {{- with T . }}
      {{- $name = . }}
    {{- end }}
  {{- end }}
  ```

### 2.2 Dictionary Arguments in Partials (`$kwargs` pattern)

When passing arguments to a partial as an dictionary, the receiving partial must use the `$kwargs` local variable pattern. This ensures a consistent, explicit, and readable way to unpack arguments while continuing to adhere strictly to the Zero-Dot Policy.

**Rules:**

1. **Context Capture:** If a partial expects a dictionary of arguments, its entry point must capture the context explicitly as `{{- $kwargs := . -}}`.
2. **No Direct Property Captures:** You must not extract dictionary items directly from the context dot. Statements like `{{- $page := .page -}}` or `{{- $modifier := .modifier -}}` are completely forbidden.
3. **Dedicated Local Variables:** Extract each required dictionary item from `$kwargs` into its own dedicated local variable immediately following the capture. You should use `| default` to set explicit fallback values for optional arguments.

**Example Caller:**

  ```go
  {{ partial "widgets/toc.html" (dict "page" $page "native" true) }}
  ```

**Example Receiving Partial (Good):**

  ```go
  {{- $kwargs := . -}}
  {{- $page := $kwargs.page -}}
  {{- $native := $kwargs.native | default false -}}
  ```

**Example Receiving Partial (Bad):**

  ```go
  {{- $page := .page -}}
  {{- $native := .native -}}
  ```

_(Note: If a partial only accepts a single domain object instead of a dictionary, e.g., `{{ partial "author.html" $page }}`, capturing `{{- $page := . -}}` is still the correct and allowed approach)._

#### 2.3 WCAG Semantic HTML

All layouts must enforce strict semantic HTML5 structural tags to ensure WCAG 2.2 AA compliance for screen readers. Developers must use `<main>`, `<article>`, `<aside>`, `<nav>`, `<header>`, and `<footer>` appropriately. Meaningless `<div>` wrappers should only be used for CSS grid/flexbox structuring, never for document outlining.

#### 2.4 CSS Best Practices

- **CSS units:** Use `rem` for all font sizes and spacing. Use `px` for fixed-size elements like icons and borders.

- **CSS colors:** Use `oklch()` for all color values. This is a modern color space that is more perceptually uniform than RGB and allows for easier color manipulation.

#### 2.5 Additional Guidelines

- **Minimum Hugo Version:** The theme requires **Hugo v0.146.0** or higher. This strict baseline is necessary to support the modern template lookup rules (e.g., `layouts/_partials/`, `layouts/home.html`, no `_default` directory) and natively support GitHub-flavored Markdown Alerts via blockquote render hooks.

- **Data Source Truth:** Structural site metadata (Site Title, Description, Navigation links) must be driven strictly by `hugo.toml`. Hardcoding these into HTML partials is forbidden.

- **TOC & Heading Hierarchy:** Developers and writers must assume that Markdown content uses `## H2` as the top-level section heading. The TOC is configured to ignore `H1` tags within the content body to preserve SEO semantics.

### 2.6 Explicit Parameter Declaration (API Contract)

All references to global Hugo identifiers (`site.Params.<X>`, `site.Menus`, etc.) and page-level parameters (`$page.Params.<X>`, front matter values) must be declared as local variables at the top of each template file. These declarations serve as an explicit API contract, documenting the external dependencies required by the template. This improves readability, makes dependencies discoverable at a glance, and prevents hidden configuration references deep within business logic that are hard to trace and refactor.

**Rules:**

1. **Declare all `site.Params` references at the top** — Extract any `site.Params.<X>` usage into a dedicated local variable immediately after context capture. Use `| default` to provide fallback values.
2. **Declare all page params at the top** — Extract `$page.Params.<X>` references into local variables before any conditional or rendering logic.
3. **No direct params access in business logic** — After the declaration section, the template body must reference only the local variables, never direct `site.Params` or `$page.Params` lookups.
4. **The declaration block is the contract** — Developers reading the first 10 lines of a template should understand its complete external dependency surface.

**Example (good — params extracted into API contract at the top):**

```Go
{{ define "main" }}
{{- $page := . -}}

/* === API Contract: External Dependencies ===================================== */
{{- $searchParams := site.Params.widgets | default dict -}}
{{- $catLimit := index $searchParams "CategoriesLimit" | default 5 -}}
{{- $tagLimit := index $searchParams "TagsLimit" | default 4 -}}
/* ============================================================================= */

{{- /* Business logic only uses local variables */ -}}
<div class="categories">
  {{- range $i, $cat := first $catLimit site.Taxonomies.categories -}}
    <span>{{ $cat.Name }}</span>
  {{- end -}}
</div>
```

**Example (bad — `site.Params` hidden inside business logic):**

```Go
{{- /* Author block */ -}}
{{ $page := . }}

{{- with $authors := $page.Params.authors }}
{{- if site.Params.enableAuthorBlock }}  <!-- VIOLATION: site.Params in logic -->
{{- with $authorName := index $authors 0 }}
{{- $authorTerm := site.GetPage (printf "/authors/%s" ($authorName | urlize)) }}
```

**Example (bad — page params accessed deep in conditional blocks):**

```Go
{{- $kwargs := . -}}
{{- $page := $kwargs.page -}}
{{- $native := $kwargs.native | default false -}}
{{- $items := $kwargs.items | default slice -}}

{{- /* Determine if TOC is enabled */ -}}
{{- $isEnabled := true -}}
{{- if $native -}}
  {{- $isEnabled = site.Params.enableTOC -}}  <!-- VIOLATION: site.Params in logic -->
  {{- if isset $page.Params "enabletoc" -}}
    {{- $isEnabled = $page.Params.enabletoc -}}  <!-- VIOLATION: page.Params in logic -->
  {{- end -}}
{{- end -}}
```

**Refactored (good):**

```Go
{{- $kwargs := . -}}
{{- $page := $kwargs.page -}}

/* === API Contract ============================================================ */
{{- $native := $kwargs.native | default false -}}
{{- $items := $kwargs.items | default slice -}}
{{- $siteEnableTOC := site.Params.enableTOC | default true -}}
{{- $pageEnableTOC := $page.Params.enabletoc | default true -}}
/* ============================================================================= */

{{- $isEnabled := true -}}
{{- if $native -}}
  {{- $isEnabled = $siteEnableTOC -}}
  {{- if isset $page.Params "enabletoc" -}}
    {{- $isEnabled = $pageEnableTOC -}}
  {{- end -}}
{{- end -}}
```

## 3. Customization (End-User Extension)

Site owners can extend the theme without forking the repository by utilizing the `customCSS` and `customJS` arrays in `hugo.toml`.

- **How it works:** The theme loops through these arrays and injects the specified files at the end of the `<head>` (for CSS) or `<body>` (for JS).
- **Limitations & Best Practices:**
  - Because the theme uses CSS `@layer`, custom CSS injected normally will actually have _lower_ priority than unlayered CSS. To override theme styles, users should ideally redefine Tier 2 Semantic variables in the `:root` of their custom CSS, or explicitly place their overrides in a higher-priority layer.
  - Custom JS is deferred and should rely on standard `DOMContentLoaded` event listeners.

---

## 4. Testing & Quality Assurance

The theme relies on a dual-testing strategy (Manual and Automated) to ensure layout stability and WCAG 2.2 AA compliance.

---

### 4.1 Manual Testing (Demo Site)

The `/theme-x-demo/` repository contains a suite of stress-test pages in the `content/posts/` directory:

- **Markdown Kitchen Sink:** Tests all standard HTML elements, tables, footnotes, and task lists.
- **Admonitions Test:** Verifies alert parsing and nested transparency.
- **Code Blocks Test:** Verifies syntax highlighting themes and copy-button JS.
- **i18n & Taxonomy Test:** Verifies RTL rendering, long-word breaking, and sidebar widget logic.

---

### 4.2 Automated Linting

To maintain code quality without over-engineering, the codebase is audited using standard CLI tools:

- **CSS:** `Stylelint` (ensures standard formatting and OKLCH syntax).
- **JS:** `ESLint` (vanilla ES6 configuration).
- **Hugo:** Run strictly with `--printI18nWarnings --printPathWarnings --printUnusedTemplates`.

---

### 4.3 Automated Post-Build Testing

Rather than maintaining complex end-to-end browser tests, automated testing is performed directly on Hugo's static output.

- **HTML Validation:** `HTMLHint` scans the generated `/public/` directory for unclosed tags or invalid nesting.
- **Accessibility:** `axe-cli` scans the generated HTML for WCAG contrast failures, missing ARIA labels, and structural accessibility issues.

---

## 5. CI/CD Pipeline

Continuous Integration and Deployment are handled via GitHub Actions.

---

### 5.1 The Workflow Pipeline

1. **Lint Run:** Executes `Stylelint`, `ESLint`, and Markdown linters on Pull Requests.
2. **Build Run:** Compiles the Hugo site using the production command (`hugo --minify --gc`). This automatically executes the CSS bundling, minification, and JS fingerprinting.
3. **Test Run:** Executes `axe-cli` and `HTMLHint` against the compiled `/public/` folder. The pipeline fails if WCAG AA standards are violated.
4. **Deployment:** If the `main` branch passes all checks, the generated `/public/` folder is pushed to GitHub Pages via the official `actions/deploy-pages` workflow.
