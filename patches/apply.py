#!/usr/bin/env python3
"""
RerFire source patcher – applies edits by string substitution.
Robust against line-number drift between Firefox ESR point releases.

Usage: python3 patches/apply.py <firefox-source-root>
"""

import sys
import os

SRC = sys.argv[1] if len(sys.argv) > 1 else "."

applied = []
skipped = []
failed  = []


def _read(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def _write(path, text):
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)


def patch(rel_path, old, new, description):
    patch_group(rel_path, [(old, new)], description)


def patch_group(rel_path, edits, description):
    """Apply one or more edits to a single file, all or nothing.

    Every context is checked before anything is written, so a group can
    never leave the file half-edited. That matters where the edits are
    interdependent — rust.mk below has one edit that opens an `ifdef` and
    another that closes it; applying only the first yields a Makefile with
    an unbalanced conditional that no re-run would repair.

    An edit whose `new` text is already present is treated as satisfied and
    dropped from the batch, so re-running is safe and a previously
    half-applied file gets completed rather than rejected.
    """
    path = os.path.join(SRC, rel_path)
    if not os.path.exists(path):
        failed.append(f"NOT FOUND: {rel_path}  [{description}]")
        return

    text = _read(path)

    pending = []
    for old, new in edits:
        if old in text:
            pending.append((old, new))
        elif new not in text:
            failed.append(f"context not found: {rel_path}  [{description}]")
            return

    if not pending:
        skipped.append(f"already applied: {description}")
        return

    for old, new in pending:
        text = text.replace(old, new, 1)
    _write(path, text)
    applied.append(f"OK  {description}")


# ── 0001: Remove Normandy from toolkit build ─────────────────
patch(
    "toolkit/components/moz.build",
    '    DIRS += ["featuregates", "messaging-system", "normandy"]',
    '    DIRS += ["featuregates", "messaging-system"]  # RerFire: normandy removed',
    "toolkit/components/moz.build: remove normandy dir",
)

# ── 0002: Remove Pocket from browser build ───────────────────
patch(
    "browser/components/moz.build",
    '    "pocket",\n',
    '    # "pocket",  # RerFire: removed\n',
    "browser/components/moz.build: remove pocket dir",
)

# ── 0003: BrowserGlue – remove Normandy lazy import ──────────
patch(
    "browser/components/BrowserGlue.sys.mjs",
    '  Normandy: "resource://normandy/Normandy.sys.mjs",\n',
    '  // Normandy: removed by RerFire\n',
    "BrowserGlue.sys.mjs: remove Normandy lazy import",
)

# ── 0004: BrowserGlue – remove Normandy.init() call ──────────
patch(
    "browser/components/BrowserGlue.sys.mjs",
    "      lazy.Normandy.init();\n",
    "      // lazy.Normandy.init();  // RerFire: removed\n",
    "BrowserGlue.sys.mjs: remove Normandy.init()",
)

# ── 0005: BrowserGlue – remove Normandy.uninit() call ────────
patch(
    "browser/components/BrowserGlue.sys.mjs",
    "      () => lazy.Normandy.uninit(),\n",
    "      // () => lazy.Normandy.uninit(),  // RerFire: removed\n",
    "BrowserGlue.sys.mjs: remove Normandy.uninit()",
)

# ── 0006: BrowserGlue – remove ShieldFrame actor ─────────────
patch(
    "browser/components/BrowserGlue.sys.mjs",
    """\
  ShieldFrame: {
    parent: {
      esModuleURI: "resource://normandy-content/ShieldFrameParent.sys.mjs",
    },
    child: {
      esModuleURI: "resource://normandy-content/ShieldFrameChild.sys.mjs",
      events: {
        pageshow: {},
        pagehide: {},
        ShieldPageEvent: { wantUntrusted: true },
      },
    },
    matches: ["about:studies*"],""",
    "  // ShieldFrame: removed by RerFire (Normandy)\n  _ShieldFrameRemoved: {",
    "BrowserGlue.sys.mjs: remove ShieldFrame actor",
)

# ── 0007: BrowserGlue – remove SaveToPocket lazy import ──────
patch(
    "browser/components/BrowserGlue.sys.mjs",
    '  SaveToPocket: "chrome://pocket/content/SaveToPocket.sys.mjs",\n',
    '  // SaveToPocket: removed by RerFire\n',
    "BrowserGlue.sys.mjs: remove SaveToPocket lazy import",
)

# ── 0008: BrowserGlue – remove SaveToPocket.init() call ──────
patch(
    "browser/components/BrowserGlue.sys.mjs",
    "    lazy.SaveToPocket.init();\n",
    "    // lazy.SaveToPocket.init();  // RerFire: removed\n",
    "BrowserGlue.sys.mjs: remove SaveToPocket.init()",
)

# ── 0009: Performance.cpp – tighten timing precision floor ───
# nsRFPService already applies ReduceTimePrecisionAsMSecs.
# We tighten by forcing RTPCallerType to behave as CrossOriginIsolated
# (100µs floor) even for same-origin callers. This defeats averaging
# attacks that work at the 1ms default floor.
patch(
    "dom/performance/Performance.cpp",
    """\
  return nsRFPService::ReduceTimePrecisionAsMSecs(
      rawTime, GetRandomTimelineSeed(), mRTPCallerType);""",
    """\
  // RerFire: force 100µs precision floor for all non-system callers
  // to defeat averaging-based timing attacks (e.g. cache timing, Spectre).
  RTPCallerType callerType = (mRTPCallerType == RTPCallerType::SystemPrincipal)
      ? RTPCallerType::SystemPrincipal
      : RTPCallerType::CrossOriginIsolated;
  return nsRFPService::ReduceTimePrecisionAsMSecs(
      rawTime, GetRandomTimelineSeed(), callerType);""",
    "Performance.cpp: force 100µs timing floor for non-system callers",
)

# (former 0010 removed: it only inserted a comment into
#  SandboxPolicyContent.h — configd is not referenced anywhere in the
#  ESR 128 mac sandbox policies, so there was nothing to remove.)

# ── 0010: toolchain.configure – detect Apple ld-1267 (Sequoia/Xcode16+) ──
# Firefox ESR 128 was released before Apple replaced ld64 with ld-1267.
# Old detection: retcode==1 + "Logging ld64 options" in stderr.
# New Apple linker prints "ld: unknown options:" instead – add that check.
patch(
    "build/moz.configure/toolchain.configure",
    """\
            retcode, stdout, stderr = get_cmd_output(*cmd, env=env)
            if retcode == 1 and "Logging ld64 options" in stderr:
                kind = "ld64"\
""",
    """\
            retcode, stdout, stderr = get_cmd_output(*cmd, env=env)
            if retcode == 1 and (
                "Logging ld64 options" in stderr  # Apple ld64 (pre-Sequoia)
                or "ld: unknown options:" in stderr  # Apple ld-1267+ (Sequoia / Xcode 16+)
            ):
                kind = "ld64"\
""",
    "toolchain.configure: detect Apple ld-1267 (macOS 15 Sequoia)",
)

# ── 0011: rust.mk – do not auto-enable Rust LTO when --disable-lto ───
# Mach unconditionally adds `-Clto` and `-Cembed-bitcode=yes` to release Rust
# builds unless cross-language LTO is on, even when --disable-lto is set. That
# forces LLVM bitcode (Rust 1.95 → LLVM 22) into staticlibs that the C++ linker
# (LLVM 18) then tries to parse → "Unknown attribute kind (102)" / "Invalid
# attribute group entry" → link failure on libnssckbi.dylib.
# Gate the auto-Rust-LTO block on MOZ_LTO being defined, so --disable-lto truly
# disables LTO end-to-end.
#
# The two edits below MUST land together: the first opens an `ifdef MOZ_LTO`,
# the second closes it. Applying only one leaves rust.mk with an unbalanced
# conditional, so they go through patch_group, which writes nothing unless
# both contexts are found.
#
# The closing edit's anchor: the original block ends with five `endif`s for
# gkrust_gtest, MOZ_CODE_COVERAGE, rustflags_sancov, MOZ_LTO_RUST_CROSS, and
# MOZ_DEBUG_RUST/DEVELOPER_OPTIONS. We add a sixth. The trailing
# `ifdef CARGO_INCREMENTAL` line is what makes the run of `endif`s unique.
patch_group(
    "config/makefiles/rust.mk",
    [
        (
            """\
ifndef DEVELOPER_OPTIONS
ifndef MOZ_DEBUG_RUST
# Enable link-time optimization for release builds, but not when linking
# gkrust_gtest. And not when doing cross-language LTO.
ifndef MOZ_LTO_RUST_CROSS""",
            """\
ifndef DEVELOPER_OPTIONS
ifndef MOZ_DEBUG_RUST
# RerFire: only auto-enable per-crate Rust LTO when LTO is enabled at all.
# Upstream enables it whenever MOZ_LTO_RUST_CROSS is unset, which forces Rust
# bitcode into staticlibs and breaks links when rustc's LLVM != C++ clang's.
ifdef MOZ_LTO
# Enable link-time optimization for release builds, but not when linking
# gkrust_gtest. And not when doing cross-language LTO.
ifndef MOZ_LTO_RUST_CROSS""",
        ),
        (
            """\
endif
endif
endif
endif
endif

ifdef CARGO_INCREMENTAL""",
            """\
endif
endif
endif
endif
endif
endif  # RerFire: close MOZ_LTO guard

ifdef CARGO_INCREMENTAL""",
        ),
    ],
    "rust.mk: gate auto Rust LTO on MOZ_LTO (avoid LLVM-22/18 bitcode mismatch)",
)

# ── REPORT ────────────────────────────────────────────────────
print(f"\nRerFire patches: {len(applied)} applied, {len(skipped)} skipped, {len(failed)} failed\n")
for line in applied:
    print(f"  \033[32m✓\033[0m {line}")
for line in skipped:
    print(f"  \033[33m~\033[0m {line}")
for line in failed:
    print(f"  \033[31m✗\033[0m {line}")

if failed:
    print("\nSome patches failed – check paths above.")
    sys.exit(1)
