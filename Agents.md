# Agents.md: ProseBlock Workspace & Demo Guide

**Purpose:** Global project context and workspace rules for AI agents. This file governs the root demo website (`.`) and overarching project commands.

**Role:** You are an expert Hugo developer. You are working in a monorepo where the theme (`themes/proseblock/`) is the primary package, and the root (`.`) is solely for testing and providing demo content for the theme.

---

## Project Overview

**ProseBlock** (`themes/proseblock`) is a content-first Hugo theme for editorial, technical, and article-driven websites. Built with vanilla CSS/JS, zero frontend dependencies.
**ProseBlock-demo** (`.`) is the demo site for the ProseBlock theme.

- **Stack:** Hugo (SSG) v0.161.1+, Vanilla CSS (@layer + BEM), Vanilla ES6 Modules.
- **Key Docs:** `docs/erd.md`
- **Tests:** `tests/` (Shared python modules live in `tests/_lib/` and are not executed directly).

**🚨 CRITICAL PATHING RULE:**
All theme development (layouts, CSS, JS) **MUST** occur inside `./themes/proseblock/`. Never create or modify layouts/assets in the root `./layouts` or `./assets` directories unless explicitly instructed to override the theme for the demo site.

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

## Hugo Commands

```bash
# Dev server
make dev

# Build (with verbose output and strict flags)
VERBOSE=1 make build
```
