#!/usr/bin/env bash
# =============================================================
# NordFox build.sh – Clone LibreWolf, apply patches, build
# Platform: macOS arm64
#
# SUPERSEDED. The current macOS build is
#
#     python3 build_native.py macos all
#
# which targets Firefox ESR 140 from Mozilla's own tarball, on the same
# code path as the Windows and Linux packages, and ships the enterprise
# policies this script knows nothing about.
#
# This script is kept because it is the only thing that still builds the
# ESR 128 + LibreWolf-patch-set tree, and because an existing incremental
# objdir is expensive to recreate. It is not maintained; nothing here has
# been run against ESR 140.
#
# (Project directory and obj-dir name still say "rerfire" for backward
#  compatibility with the existing incremental build tree.)
# =============================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BUILD_DIR="${SCRIPT_DIR}/build"
LIBREWOLF_TAG="${LIBREWOLF_TAG:-128.11.0-1}"   # update as needed
FIREFOX_ESR_VERSION="128.11.0esr"

# Pin the exact LibreWolf commit the patch set is taken from. Git objects are
# content-addressed, so this is a real integrity check on code we are about to
# compile and run. Leave empty and `./build.sh fetch` will print the commit it
# resolved so you can pin it. See fetch_source().
LIBREWOLF_COMMIT="${LIBREWOLF_COMMIT:-}"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
info()  { echo -e "${GREEN}[nordfox]${NC} $*"; }
warn()  { echo -e "${YELLOW}[nordfox]${NC} $*"; }
error() { echo -e "${RED}[nordfox] ERROR:${NC} $*" >&2; exit 1; }

# ── DEPENDENCY CHECK ─────────────────────────────────────────
check_deps() {
  info "Checking build dependencies..."
  local missing=()

  command -v python3   &>/dev/null || missing+=("python3 (brew install python)")
  command -v node      &>/dev/null || missing+=("node (brew install node)")
  command -v git       &>/dev/null || missing+=("git (xcode-select --install)")
  command -v xcodebuild &>/dev/null || missing+=("Xcode Command Line Tools (xcode-select --install)")

  # Accept rustup OR Homebrew rust (cargo + rustc)
  if ! command -v rustup &>/dev/null && ! command -v cargo &>/dev/null; then
    missing+=("Rust: brew install rust  OR  curl https://sh.rustup.rs | sh")
  fi

  # LLVM 18 specifically — mozconfig pins CC/CXX to llvm@18 (ESR 128's
  # NSS/NSPR bindgen only produces correct bindings with LLVM 18).
  if [[ ! -x "/opt/homebrew/opt/llvm@18/bin/clang" ]]; then
    missing+=("LLVM 18: brew install llvm@18")
  fi

  if [[ ${#missing[@]} -gt 0 ]]; then
    error "Missing dependencies:\n  - $(IFS=$'\n  - '; echo "${missing[*]}")\n\nInstall them and re-run."
  fi

  # Ensure aarch64-apple-darwin target is available
  if command -v rustup &>/dev/null; then
    rustup target add aarch64-apple-darwin 2>/dev/null || true
  else
    # Homebrew rust on arm64 already targets aarch64-apple-darwin natively
    info "Homebrew Rust detected ($(rustc --version 2>/dev/null | cut -d' ' -f2)), skipping rustup target add."
  fi

  info "All dependencies OK."
}

# ── FETCH LIBREWOLF SOURCE ───────────────────────────────────
fetch_source() {
  mkdir -p "$BUILD_DIR"
  cd "$BUILD_DIR"

  if [[ -d "librewolf-${LIBREWOLF_TAG}" ]]; then
    warn "Source directory already exists, skipping download."
    return
  fi

  info "Downloading LibreWolf ${LIBREWOLF_TAG} source..."

  # LibreWolf ships a patch set; Mozilla ships the browser source.
  #
  # The patch set is cloned rather than downloaded as an archive: Codeberg
  # generates archive tarballs on the fly and they are not byte-reproducible,
  # so there is no stable checksum to pin. A git commit hash IS stable and
  # content-addressed, which gives us something real to verify against.
  local lw_dir="librewolf-patches-${LIBREWOLF_TAG}"
  rm -rf "$lw_dir"
  git clone --quiet --depth 1 --branch "$LIBREWOLF_TAG" \
    "https://codeberg.org/librewolf/source.git" "$lw_dir" \
    || error "Could not clone LibreWolf source at tag ${LIBREWOLF_TAG}"

  local lw_commit
  lw_commit="$(git -C "$lw_dir" rev-parse HEAD)"
  if [[ -n "$LIBREWOLF_COMMIT" ]]; then
    if [[ "$lw_commit" != "$LIBREWOLF_COMMIT" ]]; then
      error "LibreWolf commit mismatch!\n  expected: ${LIBREWOLF_COMMIT}\n  actual:   ${lw_commit}\nThe tag was moved or the clone was tampered with. Refusing to build."
    fi
    info "LibreWolf commit verified: ${lw_commit}"
  else
    warn "LIBREWOLF_COMMIT is unset — the patch set was taken on trust."
    warn "Pin it so future builds are verifiable:"
    warn "  LIBREWOLF_COMMIT=${lw_commit}"
  fi

  local ff_url="https://archive.mozilla.org/pub/firefox/releases/${FIREFOX_ESR_VERSION}/source/firefox-${FIREFOX_ESR_VERSION}.source.tar.xz"
  curl -L --progress-bar -o "firefox-${FIREFOX_ESR_VERSION}.source.tar.xz" "$ff_url"

  # Verify the Firefox tarball against Mozilla's published SHA256SUMS
  # before extracting ~5GB of source we're about to compile and run.
  info "Verifying Firefox source checksum..."
  local sums_url="https://archive.mozilla.org/pub/firefox/releases/${FIREFOX_ESR_VERSION}/SHA256SUMS"
  local expected actual
  expected=$(curl -sL "$sums_url" \
    | grep "source/firefox-${FIREFOX_ESR_VERSION}.source.tar.xz" \
    | awk '{print $1}')
  if [[ -z "$expected" ]]; then
    error "Could not fetch SHA256SUMS for ${FIREFOX_ESR_VERSION} from archive.mozilla.org"
  fi
  actual=$(shasum -a 256 "firefox-${FIREFOX_ESR_VERSION}.source.tar.xz" | awk '{print $1}')
  if [[ "$expected" != "$actual" ]]; then
    error "Firefox tarball checksum mismatch!\n  expected: ${expected}\n  actual:   ${actual}\nDelete the file and re-run fetch."
  fi
  info "Checksum OK: ${actual}"

  info "Extracting Firefox ESR source (~5GB, be patient)..."
  tar -xJf "firefox-${FIREFOX_ESR_VERSION}.source.tar.xz"
  # Detect actual top-level directory name (varies: may omit "esr" suffix)
  local ff_extracted
  ff_extracted=$(tar -tJf "firefox-${FIREFOX_ESR_VERSION}.source.tar.xz" 2>/dev/null \
    | grep -m1 '/' | cut -d'/' -f1)
  [[ -d "$ff_extracted" ]] || error "Could not find extracted Firefox directory (looked for: ${ff_extracted})"
  mv "$ff_extracted" "librewolf-${LIBREWOLF_TAG}"
}

# ── APPLY LIBREWOLF PATCHES ──────────────────────────────────
apply_librewolf_patches() {
  cd "${BUILD_DIR}/librewolf-${LIBREWOLF_TAG}"
  info "Applying LibreWolf patches..."

  local patch_dir="${BUILD_DIR}/librewolf-patches-${LIBREWOLF_TAG}/patches"
  [[ -d "$patch_dir" ]] || error "LibreWolf patch directory not found: ${patch_dir}\nRun './build.sh fetch' first."

  # Every one of these carries a privacy change. A patch that does not apply
  # means that change is silently absent from a build we would then ship as
  # "hardened" — so a failure here is fatal, never a warning.
  #
  # Three-way check so re-running './build.sh patch' is safe:
  #   forward dry-run OK  → not yet applied, apply it
  #   reverse dry-run OK  → already applied, skip
  #   neither             → the tree does not match the patch set, stop
  local applied=0 already=0 p name
  for p in "${patch_dir}"/*.patch; do
    [[ -f "$p" ]] || continue
    name="$(basename "$p")"
    if patch -p1 --dry-run --forward --silent < "$p" >/dev/null 2>&1; then
      info "  Applying ${name}"
      patch -p1 --no-backup-if-mismatch --forward --silent < "$p" \
        || error "LibreWolf patch failed while applying: ${name}\nThe source tree is now partially patched. Delete build/librewolf-${LIBREWOLF_TAG}\nand re-run './build.sh fetch' before retrying."
      applied=$((applied + 1))
    elif patch -p1 --dry-run --reverse --silent < "$p" >/dev/null 2>&1; then
      info "  Already applied: ${name}"
      already=$((already + 1))
    else
      error "LibreWolf patch does not apply: ${name}\nThe Firefox source does not match this LibreWolf patch set — check that\nLIBREWOLF_TAG (${LIBREWOLF_TAG}) and FIREFOX_ESR_VERSION (${FIREFOX_ESR_VERSION}) agree.\nRefusing to continue: the build would be missing this privacy change."
    fi
  done

  if (( applied + already == 0 )); then
    error "No patches found in ${patch_dir} — the LibreWolf clone looks wrong."
  fi
  info "LibreWolf patches: ${applied} applied, ${already} already present."
}

# ── APPLY RERFIRE PATCHES ────────────────────────────────────
apply_rerfire_patches() {
  cd "${BUILD_DIR}/librewolf-${LIBREWOLF_TAG}"
  info "Applying NordFox patches via patches/apply.py..."
  python3 "${SCRIPT_DIR}/patches/apply.py" . || error "NordFox patch step failed"
}

# ── INSTALL BRANDING (post-build) ────────────────────────────
install_branding() {
  local app_dir="${BUILD_DIR}/librewolf-${LIBREWOLF_TAG}/obj-rerfire-aarch64/dist"
  local nightly_app="${app_dir}/Nightly.app"
  local nordfox_app="${app_dir}/NordFox.app"

  # Pick whichever is currently present.
  local target=""
  [[ -d "$nordfox_app" ]] && target="$nordfox_app"
  [[ -z "$target" && -d "$nightly_app" ]] && target="$nightly_app"
  if [[ -z "$target" ]]; then
    warn "No .app found in ${app_dir}, skipping branding."
    return
  fi

  info "Applying NordFox branding to $(basename "$target")"
  # Swap the icon
  if [[ -f "${SCRIPT_DIR}/branding/firefox.icns" ]]; then
    cp "${SCRIPT_DIR}/branding/firefox.icns" "${target}/Contents/Resources/firefox.icns"
  fi
  # Install autoconfig (makes Cmd+T and Home both load the retro page)
  if [[ -d "${SCRIPT_DIR}/branding/autoconfig" ]]; then
    mkdir -p "${target}/Contents/Resources/defaults/pref"
    cp "${SCRIPT_DIR}/branding/autoconfig/nordfox-autoconfig.js" \
       "${target}/Contents/Resources/defaults/pref/nordfox-autoconfig.js"
    cp "${SCRIPT_DIR}/branding/autoconfig/nordfox.cfg" \
       "${target}/Contents/Resources/nordfox.cfg"
  fi
  # Bundle the retro homepage + new-tab page so autoconfig can find them
  # independent of profile. Prefer the TypeScript-compiled output if present.
  # The bundled copies are renamed nordfox-<page>.*, so the <script src>
  # inside the HTML must be rewritten to match the renamed sibling JS.
  local page
  for page in homepage newtab; do
    local page_src=""
    if [[ -f "${SCRIPT_DIR}/theme/build/${page}.html" ]]; then
      page_src="${SCRIPT_DIR}/theme/build/${page}.html"
    elif [[ -f "${SCRIPT_DIR}/theme/${page}.html" ]]; then
      page_src="${SCRIPT_DIR}/theme/${page}.html"
    fi
    if [[ -n "$page_src" ]]; then
      /usr/bin/sed "s|src=\"${page}.js\"|src=\"nordfox-${page}.js\"|" \
        "$page_src" > "${target}/Contents/Resources/nordfox-${page}.html"
      [[ -f "${SCRIPT_DIR}/theme/build/${page}.js" ]] && \
        cp "${SCRIPT_DIR}/theme/build/${page}.js" \
           "${target}/Contents/Resources/nordfox-${page}.js"
    fi
  done
  # Brand strings: rename "Nightly" → "NordFox" in the Fluent + legacy
  # properties files so menus, About dialog, window titles, etc. all
  # display the right product name. No rebuild required.
  local ftl="${target}/Contents/Resources/browser/localization/en-US/branding/brand.ftl"
  local props="${target}/Contents/Resources/browser/chrome/en-US/locale/branding/brand.properties"
  if [[ -f "${SCRIPT_DIR}/branding/brand.ftl" && -f "$ftl" ]]; then
    cp "${SCRIPT_DIR}/branding/brand.ftl" "$ftl"
  fi
  if [[ -f "${SCRIPT_DIR}/branding/brand.properties" && -f "$props" ]]; then
    cp "${SCRIPT_DIR}/branding/brand.properties" "$props"
  fi
  # Rename the CodeName in application.ini so process-level tooling
  # (about:support, crash reporter URLs, menu titles) stops saying
  # Nightly. NB: application.ini in a dev/objdir build is usually a
  # SYMLINK back into the build tree, so `sed -i` fails. We resolve
  # the symlink, read+rewrite via a tmp file, and replace.
  local app_ini="${target}/Contents/Resources/application.ini"
  if [[ -e "$app_ini" ]]; then
    local real_ini
    real_ini="$(/usr/bin/readlink -f "$app_ini" 2>/dev/null || echo "$app_ini")"
    [[ -L "$app_ini" ]] && rm -f "$app_ini"
    local tmp_ini
    tmp_ini="$(mktemp)"
    /usr/bin/sed \
      -e 's/^Name=Firefox$/Name=NordFox/' \
      -e 's/^CodeName=Nightly$/CodeName=NordFox/' \
      -e 's/^RemotingName=.*$/RemotingName=nordfox/' \
      "$real_ini" > "$tmp_ini"
    mv "$tmp_ini" "$app_ini"
  fi

  # Force LaunchServices to forget the old "Nightly" name cached for
  # this bundle identifier. Without this, the dock / notification
  # prompts can keep displaying the previous name for hours.
  /System/Library/Frameworks/CoreServices.framework/Versions/A/Frameworks/LaunchServices.framework/Versions/A/Support/lsregister \
    -u "$target" >/dev/null 2>&1 || true
  /System/Library/Frameworks/CoreServices.framework/Versions/A/Frameworks/LaunchServices.framework/Versions/A/Support/lsregister \
    -f -R "$target" >/dev/null 2>&1 || true
  /usr/bin/killall -u "$USER" cfprefsd usernoted NotificationCenter 2>/dev/null || true
  # Patch Info.plist — name, identifier, and crucially the
  # DISPLAY name (what macOS shows in the menu bar, dock, and
  # notification prompts). Without CFBundleDisplayName, macOS
  # may fall back to CFBundleName or the bundle filename, and the
  # OS cache can hold on to the old value.
  local plist="${target}/Contents/Info.plist"
  /usr/libexec/PlistBuddy -c "Set :CFBundleName NordFox"               "$plist" 2>/dev/null || true
  /usr/libexec/PlistBuddy -c "Set :CFBundleIdentifier org.nordfox.browser" "$plist" 2>/dev/null || true
  /usr/libexec/PlistBuddy -c "Set :CFBundleGetInfoString \"NordFox ${LIBREWOLF_TAG%-*}\"" "$plist" 2>/dev/null || true
  /usr/libexec/PlistBuddy -c "Add  :CFBundleDisplayName string NordFox" "$plist" 2>/dev/null || \
    /usr/libexec/PlistBuddy -c "Set :CFBundleDisplayName NordFox" "$plist" 2>/dev/null || true
  /usr/bin/sed -i '' 's|within Nightly will|within NordFox will|g' "$plist" 2>/dev/null || true

  # macOS reads the menu-bar / Dock label from the localized
  # CFBundleName in <bundle>/Contents/Resources/<lang>.lproj/InfoPlist.strings.
  # This OVERRIDES the value in Info.plist. Patch every lproj.
  local lproj
  for lproj in "${target}/Contents/Resources/"*.lproj; do
    if [[ -f "${lproj}/InfoPlist.strings" ]]; then
      /usr/libexec/PlistBuddy -c "Set :CFBundleName NordFox" \
        "${lproj}/InfoPlist.strings" 2>/dev/null || true
      /usr/libexec/PlistBuddy -c "Add :CFBundleDisplayName string NordFox" \
        "${lproj}/InfoPlist.strings" 2>/dev/null || \
        /usr/libexec/PlistBuddy -c "Set :CFBundleDisplayName NordFox" \
          "${lproj}/InfoPlist.strings" 2>/dev/null || true
    fi
  done

  # Plugin-container sub-app shows up as "NightlyCP" in Activity
  # Monitor. Rename for consistency.
  local pc="${target}/Contents/MacOS/plugin-container.app"
  if [[ -d "$pc" ]]; then
    for lproj in "$pc/Contents/Resources/"*.lproj; do
      if [[ -f "${lproj}/InfoPlist.strings" ]]; then
        /usr/libexec/PlistBuddy -c "Set :CFBundleName NordFoxCP" \
          "${lproj}/InfoPlist.strings" 2>/dev/null || true
      fi
    done
  fi

  # Media-plugin-helper sub-app — both the executable file name AND
  # the Info.plist refer to "Nightly Media Plugin Helper".
  local helper="${target}/Contents/MacOS/media-plugin-helper.app"
  if [[ -d "$helper" ]]; then
    local hplist="${helper}/Contents/Info.plist"
    /usr/libexec/PlistBuddy -c "Set :CFBundleIdentifier org.nordfox.media-plugin-helper" "$hplist" 2>/dev/null || true
    /usr/libexec/PlistBuddy -c "Set :CFBundleExecutable \"NordFox Media Plugin Helper\"" "$hplist" 2>/dev/null || true
    /usr/libexec/PlistBuddy -c "Add :CFBundleName string \"NordFox Media Plugin Helper\"" "$hplist" 2>/dev/null \
      || /usr/libexec/PlistBuddy -c "Set :CFBundleName \"NordFox Media Plugin Helper\"" "$hplist" 2>/dev/null || true
    /usr/libexec/PlistBuddy -c "Add :CFBundleDisplayName string \"NordFox Media Plugin Helper\"" "$hplist" 2>/dev/null \
      || /usr/libexec/PlistBuddy -c "Set :CFBundleDisplayName \"NordFox Media Plugin Helper\"" "$hplist" 2>/dev/null || true
    if [[ -f "${helper}/Contents/MacOS/Nightly Media Plugin Helper" ]]; then
      mv "${helper}/Contents/MacOS/Nightly Media Plugin Helper" \
         "${helper}/Contents/MacOS/NordFox Media Plugin Helper"
    fi
  fi

  # Rename bundle if still Nightly
  if [[ "$target" == "$nightly_app" ]]; then
    mv "$nightly_app" "$nordfox_app"
    info "Renamed Nightly.app → NordFox.app"
    target="$nordfox_app"
  fi

  # Re-sign (ad-hoc) — the Info.plist edits and executable renames above
  # invalidate the existing ad-hoc signature seal, and Apple Silicon
  # refuses to run code with a broken signature.
  info "Re-signing $(basename "$target") (ad-hoc)..."
  codesign --force --deep -s - "$target" 2>/dev/null || \
    warn "codesign failed — app may not launch; run manually: codesign --force --deep -s - '$target'"

  # Force LaunchServices to pick up new icon / name
  /System/Library/Frameworks/CoreServices.framework/Versions/A/Frameworks/LaunchServices.framework/Versions/A/Support/lsregister -f "$target" >/dev/null 2>&1 || true
}

# ── PACKAGE DMG (from the BRANDED app) ───────────────────────
# `mach package` builds its DMG from the pre-branding staging dir, so the
# shipped image would contain a plain Nightly.app. Build the DMG ourselves
# from the branded bundle instead.
package_dmg() {
  local app="${BUILD_DIR}/librewolf-${LIBREWOLF_TAG}/obj-rerfire-aarch64/dist/NordFox.app"
  if [[ ! -d "$app" ]]; then
    warn "NordFox.app not found, skipping DMG."
    return
  fi
  local dmg="${SCRIPT_DIR}/NordFox-${LIBREWOLF_TAG}-arm64.dmg"
  info "Creating DMG from branded app..."
  local staging
  staging="$(mktemp -d)"
  cp -R "$app" "${staging}/NordFox.app"
  ln -s /Applications "${staging}/Applications"
  hdiutil create -volname "NordFox" -srcfolder "$staging" -ov -format UDZO "$dmg" >/dev/null
  rm -rf "$staging"
  info "DMG ready: ${dmg}"
}

# ── INSTALL MOZCONFIG ────────────────────────────────────────
install_mozconfig() {
  cd "${BUILD_DIR}/librewolf-${LIBREWOLF_TAG}"
  info "Installing hardened mozconfig..."
  cp "${SCRIPT_DIR}/mozconfig" ./mozconfig
}

# ── BUILD ────────────────────────────────────────────────────
do_build() {
  cd "${BUILD_DIR}/librewolf-${LIBREWOLF_TAG}"

  info "Bootstrapping build environment (first run only)..."
  ./mach bootstrap --application-choice=browser --no-interactive || true

  info "Building NordFox (this takes 30–90 min on first run)..."
  ./mach build 2>&1 | tee "${BUILD_DIR}/build.log"

  install_branding
  package_dmg
  info "Build complete. App: obj-rerfire-aarch64/dist/NordFox.app"
}

# ── BRANDING-ONLY (no rebuild) ───────────────────────────────
do_brand_only() {
  install_branding
  package_dmg
}

# ── MAIN ─────────────────────────────────────────────────────
case "${1:-all}" in
  deps)    check_deps ;;
  fetch)   check_deps; fetch_source ;;
  patch)   apply_librewolf_patches; apply_rerfire_patches; install_mozconfig ;;
  build)   do_build ;;
  brand)   do_brand_only ;;
  all)
    check_deps
    fetch_source
    apply_librewolf_patches
    apply_rerfire_patches
    install_mozconfig
    do_build
    ;;
  *)
    echo "Usage: $0 [deps|fetch|patch|build|brand|all]"
    exit 1
    ;;
esac
