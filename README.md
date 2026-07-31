# NordFox

A hardened LibreWolf / Firefox ESR 128 build for macOS arm64, plus the theme,
`user.js`, and branding that go with it.

Not a fork with its own release cadence — a reproducible recipe. Everything
here operates on an upstream Firefox ESR tarball you download yourself.

## What it changes

**Source-level** (`patches/apply.py`, applied before the build):

- Normandy (Shield studies) removed from the build and from `BrowserGlue`.
- Pocket removed from the build and from `BrowserGlue`.
- `performance.now()` forced to a 100 µs precision floor for all non-system
  callers, not just cross-origin-isolated ones — defeats averaging attacks that
  work at the 1 ms default.
- Two build fixes needed on modern macOS: detecting Apple's `ld-1267` (which
  replaced `ld64` in macOS 15 / Xcode 16), and gating auto Rust LTO on
  `MOZ_LTO` so `--disable-lto` actually disables LTO end to end.

**Build config** (`mozconfig`): release, no debug symbols, `--enable-hardening`,
stack protector, `_FORTIFY_SOURCE=2`, sandbox on, crash reporter / updater /
EME off.

**Profile** (`security/user.js`): ~340 prefs based on
[arkenfox/user.js](https://github.com/arkenfox/user.js), retuned for ESR 128.

**Theme** (`theme/`): a Nord-palette `userChrome.css` / `userContent.css`, and a
retro start page + new-tab page written in TypeScript.

## Requirements

macOS on Apple Silicon, plus:

```sh
brew install python node llvm@18
xcode-select --install
# Rust: brew install rust, or rustup
```

LLVM 18 specifically. ESR 128's NSS/NSPR bindgen produces incorrect bindings
under newer LLVM — see the comments in `mozconfig` for why this also forces
`--disable-lto`.

## Build

```sh
./build.sh all      # deps → fetch → patch → build → brand → dmg
```

Or step by step: `./build.sh deps | fetch | patch | build | brand`.

First build takes 30–90 minutes. `./build.sh brand` re-applies branding and
rebuilds the DMG from an existing objdir without recompiling.

The Firefox source tarball is checksum-verified against Mozilla's published
`SHA256SUMS` before extraction.

## Install theme + prefs only

To apply the theme and `user.js` to an existing Firefox / LibreWolf profile
without building anything:

```sh
./install.sh [/path/to/profile]
```

With no argument it auto-detects a profile; existing files are backed up to
`.bak` first.

## Layout

| Path | |
|---|---|
| `build.sh` | fetch, patch, build, brand, package |
| `install.sh` | install theme + `user.js` into a profile |
| `mozconfig` | hardened build configuration |
| `patches/apply.py` | source patches (string-substitution, resilient to line drift) |
| `security/user.js` | privacy/security preferences |
| `theme/src/` | start page + new-tab page (TypeScript) |
| `branding/` | icon, brand strings, autoconfig |
| `site/` | project landing page |

`patches/*.patch` are the original unified diffs, kept for reference. The build
applies `apply.py`, not those files.

## License

MIT for the code in this repository. The patch files quote Firefox source,
which is MPL-2.0; `security/user.js` derives from arkenfox/user.js (MIT).
