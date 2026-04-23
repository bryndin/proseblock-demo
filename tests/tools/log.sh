#!/usr/bin/env bash

# ------------------------------------------
# Config
# ------------------------------------------

VERBOSE="${VERBOSE:-0}"

# ------------------------------------------
# Colors
# ------------------------------------------

RESET="\033[0m"
BOLD="\033[1m"

RED="\033[31m"
GREEN="\033[32m"
YELLOW="\033[33m"
BLUE="\033[34m"
CYAN="\033[36m"

# ------------------------------------------
# Logging helpers
# ------------------------------------------

log() {
  echo -e "${CYAN}> $*${RESET}"
}

success() {
  echo -e "${GREEN}${BOLD}✅ $*${RESET}"
}

warn() {
  echo -e "${YELLOW}⚠️  $*${RESET}"
}

error() {
  echo -e "${RED}❌ $*${RESET}"
}

# ------------------------------------------
# Execution wrapper
# ------------------------------------------

run() {
  if [ "$VERBOSE" -eq 1 ]; then
    env "$@"
  else
    OUTPUT_FILE=$(mktemp)
    if ! env "$@" >"$OUTPUT_FILE" 2>&1; then
      cat "$OUTPUT_FILE"
      rm -f "$OUTPUT_FILE"
      return 1
    fi
    rm -f "$OUTPUT_FILE"
  fi
}