# ==========================================
# Config
# ==========================================

SERVER_PORT  := 1315
TEST_SERVE   := tcp://localhost:$(SERVER_PORT)
HUGO_BASEURL := http://localhost:$(SERVER_PORT)
HUGO_FLAGS   := --gc --minify
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
else
  QUIET := @
  REDIRECT := > /dev/null 2>&1
endif

define print_mode
	@echo "$(CYAN)> Mode: $(if $(filter 1,$(VERBOSE)),verbose,quiet)$(RESET)"
endef

# ==========================================
# Help (Default Target)
# ==========================================

.PHONY: help
help: ## Show this help message
	@echo "$(BOLD)Usage:$(RESET)"
	@echo "  make $(CYAN)<target>$(RESET) [VAR=value]\n"

	@echo "$(BOLD)Common examples:$(RESET)"
	@echo "  make $(CYAN)dev$(RESET)"
	@echo "  make $(CYAN)build$(RESET)"
	@echo "  make $(CYAN)test$(RESET)"
	@echo "  make $(CYAN)visual-diff$(RESET) VISUAL_URL=/blog/"
	@echo "  make $(CYAN)visual-diff$(RESET) VISUAL_URL=/blog/ VERBOSE=1"
	@echo "  $(CYAN)VERBOSE=1$(RESET) make $(CYAN)visual-diff$(RESET)\n"

	@echo "$(BOLD)Global options:$(RESET)"
	@echo "  $(CYAN)VERBOSE=1$(RESET)   Show full command output (debug mode)"
	@echo "  $(CYAN)VERBOSE=0$(RESET)   Silent mode (default)\n"

	@echo "$(BOLD)Targets:$(RESET)"
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

build: ## Build the Hugo site for production
	@echo "$(BLUE)$(BOLD)--- Building Hugo Site ---$(RESET)"
	$(call print_mode)
	$(QUIET)hugo $(HUGO_FLAGS) $(REDIRECT) || (echo "$(RED)Build failed$(RESET)" && exit 1)

.PHONY: clean
clean: ## Remove the public directory
	rm -rf public

.PHONY: serve
serve: build ## Serve the built site locally
	npx serve public -l $(SERVER_PORT)

# ==========================================
# LINT & STATIC ANALYSIS (Pre-build)
# ==========================================

.PHONY: lint
lint: lint-js lint-css lint-templates lint-python ## Run all linters (JS, CSS, Templates, Python)

.PHONY: lint-js
lint-js: ## Lint custom JS (excluding vendor)
	npx eslint "$(THEME_DIR)/assets/js/**/*.js" --ignore-pattern "**/vendor/**" --max-warnings=0

.PHONY: lint-css
lint-css:
	npx stylelint "$(THEME_DIR)/assets/css/**/*.css"

.PHONY: lint-python
lint-python: ## Lint Python test and script files using Ruff
	$(VENV_PYTHON) -m ruff check tests

.PHONY: lint-templates
lint-templates: ## Run static analysis Python/Bash scripts on templates
	@fails=0; \
	echo "$(BLUE)$(BOLD)--- Linting Templates (Bash) -----------------------------------------------$(RESET)"; \
	for script in tests/*.sh; do \
		if [ -f "$$script" ]; then \
			echo "$(CYAN)> Executing $(BOLD)$$script$(RESET)$(CYAN)...$(RESET)"; \
			$(BASH) "$$script" || fails=1; \
		fi; \
	done; \
	echo "\n$(BLUE)$(BOLD)--- Linting Templates (Python in VENV) ---------------------------------------$(RESET)"; \
	if [ ! -d "$(VENV)" ]; then \
		echo "$(YELLOW)Virtual environment not found. Please run 'make install' first.$(RESET)"; \
		exit 1; \
	fi; \
	for script in tests/*.py; do \
		if [ -f "$$script" ]; then \
			echo "$(CYAN)> Executing $(BOLD)$$script$(RESET)$(CYAN)...$(RESET)"; \
			$(VENV_PYTHON) "$$script" || fails=1; \
		fi; \
	done; \
	if [ "$$fails" -ne 0 ]; then \
		echo "\n$(RED)$(BOLD)🚨 Linting failed! One or more template checks reported issues.$(RESET)"; \
		exit 1; \
	else \
		echo "\n$(GREEN)$(BOLD)✅ All template linting scripts passed successfully!$(RESET)"; \
	fi

# ==========================================
# TESTS (E2E requiring Build)
# ==========================================
test: build ## Run all Playwright E2E tests
	@echo "$(BLUE)$(BOLD)--- Running Tests ---$(RESET)"
	$(call print_mode)
	$(QUIET)npx start-server-and-test 'npx serve public -l $(TEST_SERVE) $(REDIRECT)' $(HUGO_BASEURL) 'npx playwright test'

.PHONY: test-fast
test-fast: build ## Run fast structure E2E tests
	$(QUIET)npx start-server-and-test 'npx serve public -l $(TEST_SERVE) $(REDIRECT)' $(HUGO_BASEURL) 'npx playwright test --grep @structure --workers=4'

.PHONY: test-visual
test-visual: build ## Run visual regression tests
	$(QUIET)npx start-server-and-test 'npx serve public -l $(TEST_SERVE) $(REDIRECT)' $(HUGO_BASEURL) 'npx playwright test --grep @visual --workers=2'

# ==========================================
# VISUAL DIFF (Before / After)
# ==========================================

VISUAL_URL     ?= /
VISUAL_ROOT    := tests/_visual-output

LOCAL_HOST     := localhost
LOCAL_PORT     := $(SERVER_PORT)
LOCAL_BASE     := http://$(LOCAL_HOST):$(LOCAL_PORT)

# Unique run id (portable enough for WSL/Linux)
RUN_ID ?= $(shell date +%Y%m%d-%H%M%S)-$$RANDOM

VISUAL_OUT_DIR := $(abspath $(VISUAL_ROOT)/$(RUN_ID))
VISUAL_TMP_DIR := $(HOME)/.cache/hugo-worktrees/visual-before-$(RUN_ID)

URL_NORM=$$(LOCAL_HOST=$(LOCAL_HOST) LOCAL_PORT=$(LOCAL_PORT) node $(TOOLS_DIR)/normalize-url.js "$(VISUAL_URL)");

visual-diff: ## Run before/after visual diff
	@echo "$(BLUE)$(BOLD)--- Visual Diff: $(VISUAL_URL) ---$(RESET)"
	$(call print_mode)
	@echo "$(CYAN)> Run ID: $(RUN_ID)$(RESET)"
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
	@echo "$(GREEN)$(BOLD)✅ Visual snapshots captured.$(RESET)"
	@echo "$(CYAN)> Comparing images...$(RESET)"
	@$(MAKE) visual-diff-report VERBOSE=$(VERBOSE)

.PHONY: visual-clean
visual-clean: ## Remove ALL visual diff artifacts
	rm -rf $(VISUAL_ROOT)
	@echo "$(GREEN)Cleaned $(VISUAL_ROOT)$(RESET)"

.PHONY: visual-clean-old
visual-clean-old: ## Keep last 5 runs, delete older ones
	@ls -dt $(VISUAL_ROOT)/* 2>/dev/null | tail -n +6 | xargs -r rm -rf
	@echo "$(GREEN)Old visual runs cleaned (kept latest 5)$(RESET)"

.PHONY: visual-diff-report
visual-diff-report: ## Generate visual diff images
	$(VENV_PYTHON) $(TOOLS_DIR)/diff_images.py

# ==========================================
# PERF & CI & BOOTSTRAP
# ==========================================

.PHONY: perf
perf: build ## Run Lighthouse performance tests
	npx lhci autorun

.PHONY: ci
ci: clean install lint test ## Full CI Pipeline

.PHONY: install
install: ## Install dependencies (npm, playwright, & python venv)
	npm install
	npx playwright install --with-deps
	@echo "$(BLUE)$(BOLD)--- Setting up Python Virtual Environment ---$(RESET)"
	$(SYSTEM_PYTHON) -m venv $(VENV)
	$(VENV_PIP) install --upgrade pip
	$(VENV_PIP) install -r tests/requirements.txt
	@echo "$(GREEN)$(BOLD)✅ Dependencies installed successfully!$(RESET)"
