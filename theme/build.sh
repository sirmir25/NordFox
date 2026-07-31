#!/usr/bin/env bash
# =============================================================
# NordFox theme build – compile the TypeScript pages, assemble
# the final HTML + JS pairs into theme/build/.
# Output is what install.sh copies into the user's profile.
# =============================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC_DIR="${SCRIPT_DIR}/src"
OUT_DIR="${SCRIPT_DIR}/build"

# Each page is a standalone <name>.html + <name>.ts pair in src/.
PAGES=(homepage newtab)

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
info() { echo -e "${GREEN}[nordfox-theme]${NC} $*"; }
warn() { echo -e "${YELLOW}[nordfox-theme]${NC} $*"; }

mkdir -p "$OUT_DIR"

if ! command -v npx &>/dev/null; then
  warn "npx not found; falling back to plain copy (no TS check)."
  for page in "${PAGES[@]}"; do
    cp "$SRC_DIR/${page}.html" "$OUT_DIR/${page}.html"
    # When TS isn't available, ship the .ts as-is — browsers can't
    # run it but we'd rather fail loudly than silently lose features.
    cp "$SRC_DIR/${page}.ts" "$OUT_DIR/${page}.js"
  done
  exit 0
fi

info "Compiling TypeScript (theme/src/*.ts → theme/build/)"
# `-y` auto-accepts the install prompt; cached after the first run.
( cd "$SRC_DIR" && npx -y -p typescript@5.6.3 tsc -p tsconfig.json )

for page in "${PAGES[@]}"; do
  # Drop the ESM "export {}" footer tsc emits when nothing is exported
  # — these are classic <script>s, not modules, and a stray `export`
  # causes a SyntaxError in non-module context.
  if [[ -f "$OUT_DIR/${page}.js" ]]; then
    # NB: BSD sed — no \s/\+ in basic regex, use -E + POSIX classes.
    /usr/bin/sed -i '' -E '/^export[[:space:]]+\{\};?$/d' "$OUT_DIR/${page}.js"
  fi
  cp "$SRC_DIR/${page}.html" "$OUT_DIR/${page}.html"
  info "Built: $OUT_DIR/${page}.html + $OUT_DIR/${page}.js"
done
