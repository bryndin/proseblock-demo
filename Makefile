# ==========================================
# Config
# ==========================================

SHELL        := /bin/bash
SERVER_PORT  := 1315
TEST_SERVE   := tcp://localhost:$(SERVER_PORT)
HUGO_BASEURL := http://localhost:$(SERVER_PORT)
PROD_BASEURL ?=
HUGO_FLAGS   := --printI18nWarnings --printPathWarnings --printUnusedTemplates --gc --minify
SYSTEM_PYTHON:= python3
BASH         ?= bash
THEME_DIR    := themes/proseblock
TESTS_DIR    := tests
TOOLS_DIR    := $(TESTS_DIR)/tools

# Virtual Environment config
VENV         := .venv
VENV_BIN     := $(VENV)/bin
VENV_PYTHON  := $(VENV_BIN)/python
VENV_PIP     := $(VENV_BIN)/pip

# Lint success message macro (DRY)
define lint_success
	@echo -e "$(GREEN)$(BOLD)✅ $(1) linting passed successfully!$(RESET)"
endef

# ==========================================
# Colors
# ==========================================

RESET  := \033[0m
BOLD   := \033[1m
BLUE   := \033[34m
CYAN   := \033[36m
GREEN  := \033[32m
RED    := \033[31m
YELLOW := \033[33m

# ==========================================
# Verbosity Control
# ==========================================
# VERBOSE=1 → show all command output (debug)
# VERBOSE=0 → suppress noisy output (default)

VERBOSE ?= 0

ifeq ($(VERBOSE),1)
  QUIET :=
  REDIRECT :=
  PLAYWRIGHT_REPORTER :=
  FILTER_NOISE :=
else
  QUIET := @
  REDIRECT := > /dev/null 2>&1
  PLAYWRIGHT_REPORTER := --reporter=dot
  # Filter out the 3 specific hardcoded lines from start-server-and-test
  FILTER_NOISE := 2>&1 | grep -v -E '^(1: starting server using command|and when url|running tests using command)'
endif

define print_mode
	@echo -e "$(CYAN)> Mode: $(if $(filter 1,$(VERBOSE)),verbose,quiet)$(RESET)"
endef

# ==========================================
# Help (Default Target)
# ==========================================

.PHONY: help
help: ## Show this help message
	@echo -e "$(BOLD)Usage:$(RESET)"
	@echo -e "  make $(CYAN)<target>$(RESET) [VAR=value]\n"

	@echo -e "$(BOLD)Common examples:$(RESET)"
	@echo -e "  make $(CYAN)dev$(RESET)"
	@echo -e "  make $(CYAN)build$(RESET) PROD_BASEURL=https://my-site.com/"
	@echo -e "  $(CYAN)VERBOSE=1$(RESET) make $(CYAN)visual-diff$(RESET) VISUAL_URL=/blog/\n"

	@echo -e "$(BOLD)Targets:$(RESET)"
	@awk -v cyan="$(CYAN)" -v reset="$(RESET)" \
		'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %s%-18s%s %s\n", cyan, $$1, reset, $$2}' $(MAKEFILE_LIST)

# ==========================================
# DEV & BUILD
# ==========================================

.PHONY: dev
dev: ## Run Hugo development server
	hugo server -D -F -e development -b $(HUGO_BASEURL) \
		--disableFastRender --navigateToChanged --noHTTPCache \
		--gc --printI18nWarnings --printPathWarnings --printUnusedTemplates

.PHONY: build
build: ## Build the Hugo site for production
	@echo -e "$(BLUE)$(BOLD)--- Building Hugo Site ---$(RESET)"
	$(call print_mode)
	$(QUIET)hugo $(HUGO_FLAGS) $(if $(PROD_BASEURL),-b $(PROD_BASEURL)) $(REDIRECT) || (echo -e "$(RED)Build failed$(RESET)" && exit 1)

.PHONY: serve
serve: build ## Serve the built site locally
	npx serve public -l $(SERVER_PORT)

# ==========================================
# LINT & STATIC ANALYSIS
# ==========================================

.PHONY: lint
lint: lint-js lint-css lint-templates lint-python ## Run all linters
	@echo -e "\n$(GREEN)$(BOLD)✅ All linting checks passed successfully!$(RESET)"

.PHONY: lint-js
lint-js: ## Lint custom JS (excluding vendor)
	npx eslint "$(THEME_DIR)/assets/js/**/*.js" --ignore-pattern "**/vendor/**" --max-warnings=0
	$(call lint_success,JS)

.PHONY: lint-css
lint-css:
	npx stylelint "$(THEME_DIR)/assets/css/**/*.css"
	$(call lint_success,CSS)

.PHONY: lint-python
lint-python: $(VENV) ## Lint Python files using Ruff
	$(VENV_PYTHON) -m ruff check tests
	$(call lint_success,Python)

.PHONY: lint-templates
lint-templates: $(VENV) ## Run static analysis scripts on templates
	@fails=0; \
	echo -e "$(BLUE)$(BOLD)--- Linting Templates (Bash) -----------------------------------------------$(RESET)"; \
	for script in tests/*.sh; do \[ -e "$$script" ] || continue; \
		echo -e "$(CYAN)> Executing $(BOLD)$$script$(RESET)$(CYAN)...$(RESET)"; \
		$(BASH) "$$script" || fails=1; \
	done; \
	echo -e "\n$(BLUE)$(BOLD)--- Linting Templates (Python in VENV) ---------------------------------------$(RESET)"; \
	for script in tests/*.py; do \
		[ -e "$$script" ] || continue; \
		echo -e "$(CYAN)> Executing $(BOLD)$$script$(RESET)$(CYAN)...$(RESET)"; \
		$(VENV_PYTHON) "$$script" || fails=1; \
	done; \
	if [ "$$fails" -ne 0 ]; then \
		echo -e "\n$(RED)$(BOLD)🚨 Linting failed! One or more template checks reported issues.$(RESET)"; \
		exit 1; \
	else \
		echo -e "\n$(GREEN)$(BOLD)✅ All template linting scripts passed successfully!$(RESET)"; \
	fi

# ==========================================
# TESTS (E2E requiring Build)
# ==========================================

TEST_RUNNER  := npx start-server-and-test 'npx serve public -l $(SERVER_PORT) $(REDIRECT)' $(HUGO_BASEURL)

.PHONY: test
test: build ## Run all Playwright E2E tests
	@echo -e "$(BLUE)$(BOLD)--- Running Tests ---$(RESET)"
	$(call print_mode)
	$(QUIET)set -o pipefail; FORCE_COLOR=1 $(TEST_RUNNER) 'npx playwright test $(PLAYWRIGHT_REPORTER)' $(FILTER_NOISE)

.PHONY: test-fast
test-fast: build ## Run fast structure E2E tests
	$(QUIET)set -o pipefail; FORCE_COLOR=1 $(TEST_RUNNER) 'npx playwright test --grep @structure --workers=4 $(PLAYWRIGHT_REPORTER)' $(FILTER_NOISE)

.PHONY: test-visual
test-visual: build ## Run visual regression tests
	$(QUIET)set -o pipefail; FORCE_COLOR=1 $(TEST_RUNNER) 'npx playwright test --grep @visual --workers=2 $(PLAYWRIGHT_REPORTER)' $(FILTER_NOISE)

# ==========================================
# VISUAL DIFF
# ==========================================

VISUAL_URL     ?= /
VISUAL_ROOT    := tests/_visual-output
LOCAL_HOST     := localhost
LOCAL_PORT     := $(SERVER_PORT)
LOCAL_BASE     := http://$(LOCAL_HOST):$(LOCAL_PORT)
RUN_ID         ?= $(shell date +%Y%m%d-%H%M%S)-$$RANDOM

VISUAL_OUT_DIR := $(abspath $(VISUAL_ROOT)/$(RUN_ID))
VISUAL_TMP_DIR := $(HOME)/.cache/hugo-worktrees/visual-before-$(RUN_ID)

.PHONY: visual-diff
visual-diff: ## Run before/after visual diff
	@echo -e "$(BLUE)$(BOLD)--- Visual Diff: $(VISUAL_URL) ---$(RESET)"
	$(call print_mode)
	@echo -e "$(CYAN)> Run ID: $(RUN_ID)$(RESET)"
	$(QUIET)mkdir -p $(VISUAL_ROOT)
	$(QUIET)rm -rf $(VISUAL_OUT_DIR) $(VISUAL_TMP_DIR)
	@URL_NORM=$$(LOCAL_HOST=$(LOCAL_HOST) LOCAL_PORT=$(LOCAL_PORT) node $(TOOLS_DIR)/normalize-url.js "$(VISUAL_URL)"); \
	 VISUAL_URL=$$URL_NORM \
	 VISUAL_TMP_DIR=$(VISUAL_TMP_DIR) \
	 VISUAL_OUT_DIR=$(VISUAL_OUT_DIR) \
	 TEST_SERVE="$(TEST_SERVE)" \
	 LOCAL_BASE="$(LOCAL_BASE)" \
	 VERBOSE=$(VERBOSE) \
	 bash $(TOOLS_DIR)/visual-diff.sh
	@echo -e "$(GREEN)$(BOLD)✅ Visual snapshots captured.$(RESET)"
	@echo -e "$(CYAN)> Comparing images...$(RESET)"
	@$(MAKE) visual-diff-report VERBOSE=$(VERBOSE)

.PHONY: visual-diff-report
visual-diff-report: $(VENV) ## Generate visual diff images
	$(VENV_PYTHON) $(TOOLS_DIR)/diff_images.py

.PHONY: visual-clean-old
visual-clean-old: ## Keep last 5 runs, delete older ones
	@ls -dt $(VISUAL_ROOT)/* 2>/dev/null | tail -n +6 | xargs -r rm -rf
	@echo -e "$(GREEN)Old visual runs cleaned (kept latest 5)$(RESET)"

.PHONY: visual-clean
visual-clean: ## Remove ALL visual diff artifacts
	rm -rf $(VISUAL_ROOT)
	@echo -e "$(GREEN)Cleaned $(VISUAL_ROOT)$(RESET)"

# ==========================================
# PERF & CI & BOOTSTRAP
# ==========================================

.PHONY: perf
perf: build ## Run Lighthouse performance tests
	npx lhci autorun

.PHONY: ci
ci: clean install lint test ## Full CI Pipeline

.PHONY: install
install: node_modules $(VENV) ## Install dependencies

node_modules: package.json
	npm install
	npx playwright install --with-deps
	@touch node_modules

$(VENV): tests/requirements.txt
	@echo -e "$(BLUE)$(BOLD)--- Setting up Python Virtual Environment ---$(RESET)"
	$(SYSTEM_PYTHON) -m venv $(VENV)
	$(VENV_PIP) install --upgrade pip
	$(VENV_PIP) install -r tests/requirements.txt
	@touch $(VENV)
	@echo -e "$(GREEN)$(BOLD)✅ Dependencies installed successfully!$(RESET)"

# ==========================================
# CLEAN
# ==========================================

.PHONY: clean
clean: ## Remove Hugo build output (the generated site)
	rm -rf public

.PHONY: clean-all
clean-all: clean visual-clean ## Nuke all build/generated artifacts (venv, node_modules, tests)
	rm -rf $(VENV)
	rm -rf node_modules
	@echo -e "$(GREEN)All generated assets and dependencies removed.$(RESET)"
