#!/usr/bin/env bash
# =============================================================
# RerFire install.sh – Install theme + security into a profile
# Works with Firefox ESR, LibreWolf, or a built RerFire binary
# =============================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
info() { echo -e "${GREEN}[nordfox]${NC} $*"; }
warn() { echo -e "${YELLOW}[nordfox]${NC} $*"; }

# ── FIND PROFILE DIRECTORY ───────────────────────────────────
find_profile() {
  local candidates=(
    # NordFox (our own build; --with-app-name=nordfox)
    "$HOME/Library/Application Support/NordFox/Profiles"
    "$HOME/Library/Application Support/nordfox/Profiles"
    # LibreWolf
    "$HOME/Library/Application Support/librewolf/Profiles"
    # Firefox stable/ESR
    "$HOME/Library/Application Support/Firefox/Profiles"
    # Firefox nightly
    "$HOME/Library/Application Support/Firefox Nightly/Profiles"
  )

  local profiles_dir=""
  for d in "${candidates[@]}"; do
    if [[ -d "$d" ]]; then
      profiles_dir="$d"
      break
    fi
  done

  if [[ -z "$profiles_dir" ]]; then
    echo ""
    return
  fi

  # If there's exactly one profile, use it; otherwise ask user
  # (macOS ships bash 3.2 which has no `mapfile`, so use a while-read loop.)
  local profiles=()
  while IFS= read -r line; do
    profiles+=("$line")
  done < <(find "$profiles_dir" -maxdepth 1 -mindepth 1 -type d)

  if [[ ${#profiles[@]} -eq 0 ]]; then
    echo ""
  elif [[ ${#profiles[@]} -eq 1 ]]; then
    echo "${profiles[0]}"
  else
    # Diagnostics + the interactive menu MUST go to stderr — this
    # function's stdout is captured into TARGET_PROFILE, so anything
    # printed here other than the final path would corrupt the result.
    warn "Multiple profiles found in ${profiles_dir}:" >&2
    for i in "${!profiles[@]}"; do
      echo "  [$i] ${profiles[$i]}" >&2
    done
    local choice
    read -rp "Select profile number: " choice >&2
    # Reject anything that isn't a valid index into the array.
    if ! [[ "$choice" =~ ^[0-9]+$ ]] || (( choice >= ${#profiles[@]} )); then
      warn "Invalid selection: '${choice}'" >&2
      echo ""
      return
    fi
    echo "${profiles[$choice]}"
  fi
}

# ── BACKUP ──────────────────────────────────────────────────
# Preserve whatever the user had before NordFox touched the profile — but
# only on the FIRST install. Backing up unconditionally means a second run
# overwrites the original with the copy we installed last time, and the
# user's own config is gone for good.
backup_once() {
  local file="$1"
  [[ -f "$file" ]] || return 0
  if [[ -e "${file}.bak" ]]; then
    info "Keeping existing backup: $(basename "$file").bak"
    return 0
  fi
  cp "$file" "${file}.bak"
  warn "Backed up existing $(basename "$file") → $(basename "$file").bak"
}

# ── INSTALL ─────────────────────────────────────────────────
install_to_profile() {
  local profile="$1"

  info "Installing into: ${profile}"

  # 1. Create chrome directory
  local chrome_dir="${profile}/chrome"
  mkdir -p "$chrome_dir"

  # 2. Install userChrome.css
  backup_once "${chrome_dir}/userChrome.css"
  cp "${SCRIPT_DIR}/theme/userChrome.css" "${chrome_dir}/userChrome.css"
  info "Installed userChrome.css"

  # 3. Install userContent.css
  backup_once "${chrome_dir}/userContent.css"
  cp "${SCRIPT_DIR}/theme/userContent.css" "${chrome_dir}/userContent.css"
  info "Installed userContent.css"

  # 4. Build (compile TypeScript) and install retro start page
  if [[ -x "${SCRIPT_DIR}/theme/build.sh" ]]; then
    info "Building theme (compiling TypeScript)..."
    "${SCRIPT_DIR}/theme/build.sh" >/dev/null
  fi
  local theme_out="${SCRIPT_DIR}/theme/build"
  # Fall back to the legacy single-file homepage.html if no build/ exists.
  if [[ ! -f "${theme_out}/homepage.html" && -f "${SCRIPT_DIR}/theme/homepage.html" ]]; then
    theme_out="${SCRIPT_DIR}/theme"
  fi
  if [[ -f "${theme_out}/homepage.html" ]]; then
    backup_once "${chrome_dir}/homepage.html"
    cp "${theme_out}/homepage.html" "${chrome_dir}/homepage.html"
    [[ -f "${theme_out}/homepage.js" ]] && \
      cp "${theme_out}/homepage.js" "${chrome_dir}/homepage.js"
    info "Installed homepage.html + homepage.js (NordFox retro start page)"
  fi

  # 4b. New-tab page. Copied for reference/manual use only: Firefox has had
  # no browser.newtab.url pref since 61, so a profile-level install CANNOT
  # change about:newtab — only a NordFox build's autoconfig can (it points
  # AboutNewTab.newTabURL at the copy bundled next to the runtime).
  # To update a NordFox build's new tab, rebuild it with build_native.py.
  if [[ -f "${theme_out}/newtab.html" ]]; then
    cp "${theme_out}/newtab.html" "${chrome_dir}/newtab.html"
    [[ -f "${theme_out}/newtab.js" ]] && \
      cp "${theme_out}/newtab.js" "${chrome_dir}/newtab.js"
    info "Installed newtab.html + newtab.js (used by NordFox.app autoconfig)"
  fi

  # 5. Install user.js with the homepage URL substituted in.
  # macOS file:// URLs are stable per-profile, so we rewrite the placeholder
  # at install time rather than at browser startup.
  # URL-encode spaces — common in macOS' "Application Support" path.
  local encoded_path="${chrome_dir// /%20}"
  local homepage_url="file://${encoded_path}/homepage.html"
  backup_once "${profile}/user.js"
  # Use a temp file so we don't depend on sed -i flavor differences.
  sed "s|__NORDFOX_HOMEPAGE_URL__|${homepage_url}|g" \
      "${SCRIPT_DIR}/security/user.js" > "${profile}/user.js"
  info "Installed user.js (homepage → ${homepage_url})"

  info ""
  info "Done! Restart NordFox/LibreWolf/Firefox fully (quit + reopen) to apply changes."
  info ""
  info "Post-install checklist:"
  info "  1. In about:config → confirm toolkit.legacyUserProfileCustomizations.stylesheets = true"
  info "  2. View → Toolbars → Menu Bar (should already be checked)"
  info "  3. Right-click toolbar → Customize → switch to Compact density"
  info "  4. Check about:support → Firefox Features → Fingerprinting Protection = Active"
  info "  5. New windows should open the retro NordFox start page."
}

# ── MAIN ────────────────────────────────────────────────────
TARGET_PROFILE="${1:-}"

if [[ -z "$TARGET_PROFILE" ]]; then
  TARGET_PROFILE="$(find_profile)"
fi

if [[ -z "$TARGET_PROFILE" || ! -d "$TARGET_PROFILE" ]]; then
  echo "Usage: $0 [/path/to/profile]"
  echo ""
  echo "No Firefox/LibreWolf profile found automatically."
  echo "Run Firefox once to create a profile, then re-run this script."
  exit 1
fi

install_to_profile "$TARGET_PROFILE"
