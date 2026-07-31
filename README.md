<div align="center">

<img src="branding/preview.png" alt="NordFox" width="120">

# NordFox

**A quieter web — hardened LibreWolf, Nord-styled.**

A reproducible recipe for building a privacy-hardened Firefox ESR 128 on
macOS arm64, with the theme, prefs, and branding that go with it.

<p>
<img src="https://img.shields.io/badge/platform-macOS%20arm64-5E81AC?style=flat-square" alt="platform: macOS arm64">
<img src="https://img.shields.io/badge/base-Firefox%20ESR%20128.11-81A1C1?style=flat-square" alt="base: Firefox ESR 128.11">
<img src="https://img.shields.io/badge/patches-LibreWolf%20128.11.0--1-88C0D0?style=flat-square" alt="patches: LibreWolf 128.11.0-1">
<img src="https://img.shields.io/badge/license-MIT-8FBCBB?style=flat-square" alt="license: MIT">
</p>

<img src="site/img/startpage.png" alt="The NordFox start page" width="820">

</div>

---

## What this is

Not a fork with its own release cadence. It is a build recipe: every artifact
starts from an upstream Firefox ESR tarball and a LibreWolf patch set that you
fetch yourself, both verified before anything is compiled.

The result is an app bundle you built, from sources you can check, with the
telemetry surfaces removed at the source level rather than switched off by a
preference that a future update can flip back.

## What it changes

### Removed from the source

| | |
|---|---|
| **Normandy** | Shield studies — dropped from the toolkit build and from `BrowserGlue` |
| **Pocket** | Dropped from the browser build and from `BrowserGlue` |
| **EME / DRM** | `--disable-eme` |
| **Crash reporter** | `--disable-crashreporter` |
| **Mozilla updater** | `--disable-updater` |

These are compiled out, not disabled by a pref.

### Hardened

- **Timing precision.** `performance.now()` is forced to a 100 µs floor for
  every non-system caller, not only cross-origin-isolated ones. The 1 ms
  default falls to averaging attacks; this does not.
- **Build flags.** `--enable-hardening`, `-fstack-protector-all`,
  `_FORTIFY_SOURCE=2`, sandbox enabled.
- **Preferences.** ~340 prefs in `security/user.js`, based on
  [arkenfox/user.js](https://github.com/arkenfox/user.js) and retuned for
  ESR 128 — every one verified to still exist in this source tree.

### Fixed

Two build breakages on current macOS that upstream ESR 128 predates:

- Detection of Apple's `ld-1267`, which replaced `ld64` in macOS 15 / Xcode 16.
- Auto Rust LTO is gated on `MOZ_LTO`, so `--disable-lto` actually disables LTO
  end to end. Without this the linker meets Rust's LLVM-22 bitcode with an
  LLVM-18 reader and dies on `libnssckbi.dylib`.

### Styled

A Nord-palette `userChrome.css` / `userContent.css`, plus a retro start page
and new-tab page written in TypeScript — local, no network, no telemetry.

## Requirements

macOS on Apple Silicon, plus:

```sh
brew install python node llvm@18 git
xcode-select --install
# Rust: brew install rust, or rustup
```

> [!IMPORTANT]
> LLVM 18 specifically. ESR 128's NSS/NSPR bindgen produces incorrect bindings
> under newer LLVM, which is also why LTO is off — see the comments in
> `mozconfig` for the full reasoning.

## Build

```sh
./build.sh all      # deps → fetch → patch → build → brand → dmg
```

First build takes 30–90 minutes and downloads roughly 5 GB of source.

<details>
<summary>Running it step by step</summary>

```sh
./build.sh deps     # check the toolchain is present
./build.sh fetch    # download + verify Firefox source and LibreWolf patches
./build.sh patch    # apply LibreWolf patches, then NordFox patches, install mozconfig
./build.sh build    # compile, brand, package
./build.sh brand    # re-brand and rebuild the DMG only — no recompile
```

`./build.sh brand` is the fast path when you have changed branding, the theme,
or the start page and do not want to wait for a rebuild.

</details>

### Verifying what you build

The Firefox tarball is checked against Mozilla's published `SHA256SUMS` before
extraction.

The LibreWolf patch set is *cloned* rather than downloaded as an archive:
Codeberg generates archive tarballs on the fly and they are not
byte-reproducible, so there is no stable checksum to pin. A git commit hash is
content-addressed and stable, so it is something you can actually verify:

```sh
./build.sh fetch                       # prints the commit it resolved
export LIBREWOLF_COMMIT=<that hash>    # subsequent fetches verify against it
```

> [!NOTE]
> With `LIBREWOLF_COMMIT` unset the clone is taken on trust and the build says
> so. Pin it once and the check is real from then on.

A LibreWolf patch that fails to apply **aborts the build**. Each one carries a
privacy change, and a build quietly missing one would still call itself
hardened.

## Install the theme and prefs only

To apply the theme and `user.js` to an existing Firefox or LibreWolf profile
without building a browser:

```sh
./install.sh [/path/to/profile]
```

With no argument it auto-detects a profile. Anything it would overwrite is
backed up to `.bak` on the first run — and only the first, so re-running never
destroys your original.

## Layout

| Path | |
|---|---|
| `build.sh` | fetch, patch, build, brand, package |
| `install.sh` | install theme + `user.js` into a profile |
| `mozconfig` | hardened build configuration |
| `patches/apply.py` | source patches, applied by string substitution |
| `security/user.js` | privacy and security preferences |
| `theme/src/` | start page and new-tab page (TypeScript) |
| `theme/build.sh` | compile `theme/src/` → `theme/build/` |
| `branding/` | icon, brand strings, autoconfig |
| `site/` | project landing page |

Patches are applied by matching source text, not line numbers, so they survive
line drift between ESR point releases. Interdependent edits are applied as an
atomic group — nothing is written unless every context resolves.

> [!TIP]
> `patches/*.patch` are the original unified diffs, kept for reference only.
> The build runs `patches/apply.py`; it does not read those files.

## Caveats

- macOS arm64 only. Nothing here has been tried on Intel, Linux, or Windows.
- The objdir is still named `obj-rerfire-aarch64`, after this project's earlier
  name. Renaming it would invalidate an existing incremental build tree.
- The app is ad-hoc signed, so Gatekeeper will want the usual right-click →
  Open on first launch.

## License

MIT for the code in this repository. The patch files quote Firefox source,
which is MPL-2.0; `security/user.js` derives from arkenfox/user.js (MIT).

<div align="center">
<sub>Built on <a href="https://librewolf.net/">LibreWolf</a> · themed with <a href="https://www.nordtheme.com/">Nord</a></sub>
</div>
