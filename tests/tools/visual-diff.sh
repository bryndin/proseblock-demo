#!/usr/bin/env bash
set -e

# TODO(DB): This doesn't seem to work, node_modules/playwright/.local-browsers doesn't exist
# export PLAYWRIGHT_BROWSERS_PATH=0

# Store the original repository root directory
ORIG_DIR="$PWD"

source "$ORIG_DIR/tests/tools/log.sh"

# TRAP: Guarantees cleanup runs when the script exits, fails, or is cancelled
cleanup() {
    # Step OUT of the temp directory before trying to delete it!
    cd "$ORIG_DIR" || true

    echo "> Cleaning up worktree..."
    git worktree remove -f "$VISUAL_TMP_DIR" 2>/dev/null || true
    rm -rf "$VISUAL_TMP_DIR"
}
trap cleanup EXIT

echo "> Preparing clean worktree..."
git worktree add -f "$VISUAL_TMP_DIR" HEAD

echo "> Normalized URL: $VISUAL_URL"

# ---------- BEFORE ----------
echo "> Running BEFORE snapshots..."

cd "$VISUAL_TMP_DIR"

if [ -d "$ORIG_DIR/node_modules" ]; then
    ln -s "$ORIG_DIR/node_modules" node_modules
else
    npm ci
fi

log "Checking Playwright browsers..."
run npx playwright install

if [ -d "$ORIG_DIR/.venv" ]; then
    ln -s "$ORIG_DIR/.venv" .venv
fi

# Copy tests and config from the active workspace
mkdir -p tests/e2e
cp -r "$ORIG_DIR/tests/e2e/"* tests/e2e/

for config_file in playwright.config.ts playwright.config.js playwright.config.mjs; do
    if [ -f "$ORIG_DIR/$config_file" ]; then
        cp "$ORIG_DIR/$config_file" .
    fi
done

git -c protocol.file.allow=always submodule sync --recursive
# git -c protocol.file.allow=always submodule update --init --recursive --checkout
# Refernce the local copy instead of the remote
git -c protocol.file.allow=always submodule update --init --recursive --reference "$ORIG_DIR/themes/proseblock"
run make build VERBOSE="$VERBOSE" --no-print-directory

VISUAL_BASELINE=before run timeout 30s npx start-server-and-test \
  "npx serve public -l $TEST_SERVE > /dev/null 2>&1" "$LOCAL_BASE" \
  "npx playwright test tests/e2e/visual_diff.spec.ts --workers=1"

# ---------- AFTER ----------
echo "> Running AFTER snapshots..."

cd "$ORIG_DIR"

run make build VERBOSE="$VERBOSE" --no-print-directory

VISUAL_BASELINE=after run timeout 30s npx start-server-and-test \
  "npx serve public -l $TEST_SERVE > /dev/null 2>&1" "$LOCAL_BASE" \
  "npx playwright test tests/e2e/visual_diff.spec.ts --workers=1"