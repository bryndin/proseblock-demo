# ==========================================
# Config
# ==========================================

HUGO_BASEURL := http://localhost:1313
HUGO_FLAGS   := --gc --minify
SERVER_PORT  := 1313
PYTHON       ?= python3
BASH         ?= bash
THEME_DIR    := themes/theme-x

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
# Help (Default Target)
# ==========================================

.PHONY: help
help: ## Show this help message
	@echo "$(BOLD)Usage:$(RESET) make $(CYAN)[target]$(RESET)\n"
	@echo "$(BOLD)Targets:$(RESET)"
	@awk -v cyan="$(CYAN)" -v reset="$(RESET)" \
		'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %s%-15s%s %s\n", cyan, $$1, reset, $$2}' $(MAKEFILE_LIST)

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
	@echo "$(BLUE)$(BOLD)--- Building Hugo Site ---$(RESET)"
	hugo $(HUGO_FLAGS)

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
lint: lint-js lint-css lint-templates ## Run all linters (JS, CSS, Templates)

.PHONY: lint-js
lint-js:
	npx eslint tests --max-warnings=0

.PHONY: lint-css
lint-css:
	npx stylelint "$(THEME_DIR)/assets/css/**/*.css"

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
	echo "\n$(BLUE)$(BOLD)--- Linting Templates (Python) ---------------------------------------------$(RESET)"; \
	for script in tests/*.py; do \
		if [ -f "$$script" ]; then \
			echo "$(CYAN)> Executing $(BOLD)$$script$(RESET)$(CYAN)...$(RESET)"; \
			$(PYTHON) "$$script" || fails=1; \
		fi; \
	done; \
	if [ "$$fails" -ne 0 ]; then \
		echo "\n$(RED)$(BOLD)🚨 Linting failed! One or more template checks reported issues.$(RESET)"; \
		exit 1; \
	else \
		echo "\n$(GREEN)$(BOLD)✅ All template linting scripts passed successfully!$(RESET)"; \
	fi

.PHONY: format-check
format-check: ## Check code formatting
	npx prettier --check "tests/**/*.{ts,js,json}"

# ==========================================
# TESTS (E2E requiring Build)
# ==========================================

.PHONY: test
test: build ## Run all Playwright E2E tests
	npx playwright test

.PHONY: test-fast
test-fast: build ## Run fast structure E2E tests
	npx playwright test --grep @structure --workers=4

.PHONY: test-visual
test-visual: build ## Run visual regression tests
	npx playwright test --grep @visual --workers=2

# ==========================================
# PERF & CI & BOOTSTRAP
# ==========================================

.PHONY: perf
perf: build ## Run Lighthouse performance tests
	npx lhci autorun

.PHONY: ci
ci: clean install lint test ## Full CI Pipeline

.PHONY: install
install: ## Install dependencies (npm & playwright)
	npm install
	npx playwright install --with-deps