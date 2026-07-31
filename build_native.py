#!/usr/bin/env python3
"""Build native NordFox packages for Linux and Windows.

The script downloads and verifies Firefox ESR source, applies NordFox's
source-level hardening, installs cross-platform branding/runtime assets, and
uses Mozilla's own ``mach build`` / ``mach package`` pipeline. Windows builds
must run on Windows with MozillaBuild installed; Linux builds must run on a
supported 64-bit Linux host.
"""

from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tarfile
import urllib.request
import zipfile


ROOT = Path(__file__).resolve().parent
BUILD_ROOT = ROOT / "build" / "native"
FIREFOX_ESR_VERSION = os.environ.get("FIREFOX_ESR_VERSION", "140.13.0esr")
NORDFOX_VERSION = os.environ.get("NORDFOX_VERSION", "140.13.0-1")
SOURCE_NAME = f"firefox-{FIREFOX_ESR_VERSION}"
SOURCE_DIR = BUILD_ROOT / SOURCE_NAME
SOURCE_ARCHIVE = BUILD_ROOT / f"{SOURCE_NAME}.source.tar.xz"
ARCHIVE_BASE = "https://archive.mozilla.org/pub/firefox/releases"

MOZCONFIGS = {
    "linux": ROOT / "mozconfigs" / "linux-x86_64.mozconfig",
    "windows": ROOT / "mozconfigs" / "windows-x86_64.mozconfig",
}
OBJDIRS = {
    "linux": "obj-nordfox-linux",
    "windows": "obj-nordfox-windows",
}


def info(message: str) -> None:
    print(f"[nordfox] {message}", flush=True)


def fail(message: str) -> "None":
    raise RuntimeError(message)


def run(command: list[str], *, cwd: Path | None = None, env: dict[str, str] | None = None) -> None:
    printable = " ".join(command)
    info(f"$ {printable}")
    subprocess.run(command, cwd=cwd, env=env, check=True)


def download(url: str, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    partial = destination.with_suffix(destination.suffix + ".part")
    request = urllib.request.Request(url, headers={"User-Agent": "NordFox build/1"})
    with urllib.request.urlopen(request) as response, partial.open("wb") as output:
        total = int(response.headers.get("Content-Length", "0"))
        copied = 0
        while True:
            chunk = response.read(1024 * 1024)
            if not chunk:
                break
            output.write(chunk)
            copied += len(chunk)
            if copied % (64 * 1024 * 1024) < len(chunk):
                if total:
                    info(f"Downloaded {copied // (1024 * 1024)} / {total // (1024 * 1024)} MB")
                else:
                    info(f"Downloaded {copied // (1024 * 1024)} MB")
    partial.replace(destination)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def safe_extract(archive: tarfile.TarFile, destination: Path) -> None:
    destination = destination.resolve()
    for member in archive.getmembers():
        target = (destination / member.name).resolve()
        if destination not in target.parents and target != destination:
            fail(f"Unsafe path in Firefox source archive: {member.name}")
    archive.extractall(destination)


def fetch_source() -> None:
    if SOURCE_DIR.is_dir():
        info(f"Source already present: {SOURCE_DIR}")
        return

    BUILD_ROOT.mkdir(parents=True, exist_ok=True)
    source_url = (
        f"{ARCHIVE_BASE}/{FIREFOX_ESR_VERSION}/source/"
        f"{SOURCE_NAME}.source.tar.xz"
    )
    sums_url = f"{ARCHIVE_BASE}/{FIREFOX_ESR_VERSION}/SHA256SUMS"

    if not SOURCE_ARCHIVE.is_file():
        info(f"Downloading Firefox ESR {FIREFOX_ESR_VERSION} source")
        download(source_url, SOURCE_ARCHIVE)

    info("Fetching Mozilla SHA-256 manifest")
    request = urllib.request.Request(sums_url, headers={"User-Agent": "NordFox build/1"})
    with urllib.request.urlopen(request) as response:
        sums = response.read().decode("utf-8")
    archive_name = f"source/{SOURCE_ARCHIVE.name}"
    expected = next(
        (line.split()[0] for line in sums.splitlines() if archive_name in line),
        None,
    )
    if expected is None:
        fail(f"Mozilla checksum entry not found for {archive_name}")
    actual = sha256(SOURCE_ARCHIVE)
    if actual != expected:
        fail(f"Firefox source checksum mismatch: expected {expected}, got {actual}")
    info(f"Source checksum verified: {actual}")

    info("Extracting Firefox source")
    with tarfile.open(SOURCE_ARCHIVE, "r:xz") as archive:
        roots = {
            parts[0]
            for member in archive.getmembers()
            if (parts := Path(member.name).parts) and parts[0] not in (".", "")
        }
        if len(roots) != 1:
            fail(f"Unexpected Firefox archive layout: {sorted(roots)}")
        extracted_root = BUILD_ROOT / roots.pop()
        safe_extract(archive, BUILD_ROOT)
    if extracted_root != SOURCE_DIR:
        extracted_root.replace(SOURCE_DIR)
    info(f"Source ready: {SOURCE_DIR}")


def patch_source() -> None:
    run([sys.executable, str(ROOT / "patches" / "apply.py"), str(SOURCE_DIR)])


def compile_theme() -> Path:
    npx = shutil.which("npx.cmd" if os.name == "nt" else "npx") or shutil.which("npx")
    if npx is None:
        fail("Node.js/npx is required to compile the NordFox start pages")
    source = ROOT / "theme" / "src"
    output = ROOT / "theme" / "build"
    output.mkdir(parents=True, exist_ok=True)
    run([npx, "-y", "-p", "typescript@5.6.3", "tsc", "-p", "tsconfig.json"], cwd=source)
    for page in ("homepage", "newtab"):
        shutil.copy2(source / f"{page}.html", output / f"{page}.html")
        javascript = output / f"{page}.js"
        text = javascript.read_text(encoding="utf-8")
        text = re.sub(r"^export\s+\{\};?\s*$", "", text, flags=re.MULTILINE)
        javascript.write_text(text, encoding="utf-8")
    return output


def render_branding(branding_dir: Path) -> None:
    try:
        from PIL import Image
    except ImportError as exc:
        fail("Pillow is required to generate Windows/Linux branding icons")
        raise exc

    source_icon = Image.open(ROOT / "branding" / "preview.png").convert("RGBA")
    resampling = getattr(Image, "Resampling", Image).LANCZOS

    def write_fitted_png(path: Path) -> None:
        existing = Image.open(path)
        width, height = existing.size
        side = max(1, int(min(width, height) * 0.92))
        icon = source_icon.resize((side, side), resampling)
        canvas = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        canvas.alpha_composite(icon, ((width - side) // 2, (height - side) // 2))
        canvas.save(path, "PNG")

    for path in branding_dir.glob("default*.png"):
        write_fitted_png(path)
    for path in branding_dir.glob("PrivateBrowsing_*.png"):
        write_fitted_png(path)
    for path in branding_dir.glob("VisualElements_*.png"):
        write_fitted_png(path)
    for path in (branding_dir / "content").glob("about*.png"):
        write_fitted_png(path)
    msix_assets = branding_dir / "msix" / "Assets"
    if msix_assets.is_dir():
        for path in msix_assets.glob("*.png"):
            write_fitted_png(path)

    ico_sizes = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    for name in ("firefox.ico", "firefox64.ico", "newwindow.ico", "newtab.ico", "pbmode.ico"):
        target = branding_dir / name
        if target.exists():
            source_icon.save(target, format="ICO", sizes=ico_sizes)


def generated_autoconfig() -> str:
    config = (ROOT / "branding" / "autoconfig" / "nordfox.cfg").read_text(encoding="utf-8")
    prefs: list[str] = []
    for line in (ROOT / "security" / "user.js").read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped.startswith("user_pref("):
            continue
        if "__NORDFOX_HOMEPAGE_URL__" in stripped:
            continue
        prefs.append(stripped.replace("user_pref(", "defaultPref(", 1))
    return config.rstrip() + "\n\n// Generated from security/user.js at build time.\n" + "\n".join(prefs) + "\n"


def install_branding_and_runtime() -> None:
    branding_dir = SOURCE_DIR / "browser" / "branding" / "unofficial"
    if not branding_dir.is_dir():
        fail(f"Firefox unofficial branding directory not found: {branding_dir}")

    shutil.copy2(ROOT / "branding" / "brand.ftl", branding_dir / "locales" / "en-US" / "brand.ftl")
    shutil.copy2(
        ROOT / "branding" / "brand.properties",
        branding_dir / "locales" / "en-US" / "brand.properties",
    )
    configure = branding_dir / "configure.sh"
    configure_text = configure.read_text(encoding="utf-8")
    configure_text = re.sub(
        r"^MOZ_APP_DISPLAYNAME=.*$",
        "MOZ_APP_DISPLAYNAME=NordFox",
        configure_text,
        flags=re.MULTILINE,
    )
    configure.write_text(configure_text, encoding="utf-8")
    render_branding(branding_dir)

    theme_output = compile_theme()
    runtime_dir = SOURCE_DIR / "browser" / "nordfox"
    runtime_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(
        ROOT / "branding" / "autoconfig" / "nordfox-autoconfig.js",
        runtime_dir / "nordfox-autoconfig.js",
    )
    (runtime_dir / "nordfox.cfg").write_text(generated_autoconfig(), encoding="utf-8")
    for page in ("homepage", "newtab"):
        shutil.copy2(theme_output / f"{page}.html", runtime_dir / f"nordfox-{page}.html")
        shutil.copy2(theme_output / f"{page}.js", runtime_dir / f"nordfox-{page}.js")
    shutil.copy2(ROOT / "theme" / "userChrome.css", runtime_dir / "nordfox-userChrome.css")
    shutil.copy2(ROOT / "theme" / "userContent.css", runtime_dir / "nordfox-userContent.css")

    (runtime_dir / "moz.build").write_text(
        """# Generated NordFox runtime payload.\n"
        "FINAL_TARGET_FILES += [\n"
        "    \"nordfox.cfg\",\n"
        "    \"nordfox-homepage.html\",\n"
        "    \"nordfox-homepage.js\",\n"
        "    \"nordfox-newtab.html\",\n"
        "    \"nordfox-newtab.js\",\n"
        "    \"nordfox-userChrome.css\",\n"
        "    \"nordfox-userContent.css\",\n"
        "]\n"
        "FINAL_TARGET_FILES.defaults.pref += [\"nordfox-autoconfig.js\"]\n""",
        encoding="utf-8",
    )

    browser_mozbuild = SOURCE_DIR / "browser" / "moz.build"
    browser_text = browser_mozbuild.read_text(encoding="utf-8")
    marker = 'DIRS += ["nordfox"]'
    if marker not in browser_text:
        browser_mozbuild.write_text(browser_text.rstrip() + f"\n\n{marker}\n", encoding="utf-8")

    manifest = SOURCE_DIR / "browser" / "installer" / "package-manifest.in"
    manifest_text = manifest.read_text(encoding="utf-8")
    runtime_manifest = """@RESPATH@/nordfox.cfg
@RESPATH@/nordfox-homepage.html
@RESPATH@/nordfox-homepage.js
@RESPATH@/nordfox-newtab.html
@RESPATH@/nordfox-newtab.js
@RESPATH@/nordfox-userChrome.css
@RESPATH@/nordfox-userContent.css
@RESPATH@/defaults/pref/nordfox-autoconfig.js"""
    if "@RESPATH@/nordfox.cfg" not in manifest_text:
        anchor = "@RESPATH@/platform.ini"
        if anchor not in manifest_text:
            fail("Could not locate platform.ini in Firefox package manifest")
        manifest_text = manifest_text.replace(anchor, anchor + "\n" + runtime_manifest, 1)
        manifest.write_text(manifest_text, encoding="utf-8")


def install_mozconfig(platform: str) -> None:
    shutil.copy2(MOZCONFIGS[platform], SOURCE_DIR / "mozconfig")


def prepare_source(platform: str) -> None:
    if not SOURCE_DIR.is_dir():
        fail("Firefox source is missing; run the fetch or all action first")
    patch_source()
    install_branding_and_runtime()
    install_mozconfig(platform)
    (SOURCE_DIR / f".nordfox-prepared-{platform}").write_text(NORDFOX_VERSION + "\n", encoding="utf-8")
    info(f"Firefox source prepared for native {platform} build")


def mach_command(platform: str, arguments: list[str]) -> list[str]:
    if platform == "windows":
        mach_ps1 = SOURCE_DIR / "mach.ps1"
        if mach_ps1.exists():
            return [
                "powershell.exe",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(mach_ps1),
                *arguments,
            ]
    return [sys.executable, str(SOURCE_DIR / "mach"), *arguments]


def build(platform: str) -> None:
    env = os.environ.copy()
    env["MOZCONFIG"] = str(SOURCE_DIR / "mozconfig")
    run(
        mach_command(platform, ["bootstrap", "--application-choice=browser", "--no-interactive"]),
        cwd=SOURCE_DIR,
        env=env,
    )
    run(mach_command(platform, ["build"]), cwd=SOURCE_DIR, env=env)


def newest(paths: list[Path], label: str) -> Path:
    candidates = [path for path in paths if path.is_file()]
    if not candidates:
        fail(f"No {label} produced by mach package")
    return max(candidates, key=lambda path: path.stat().st_mtime)


def verify_archive(path: Path) -> None:
    required = ("nordfox.cfg", "nordfox-homepage.html", "nordfox-userChrome.css")
    if zipfile.is_zipfile(path):
        with zipfile.ZipFile(path) as archive:
            names = archive.namelist()
    else:
        with tarfile.open(path, "r:*") as archive:
            names = archive.getnames()
    for required_name in required:
        if not any(name.endswith("/" + required_name) or name == required_name for name in names):
            fail(f"Packaged archive is missing {required_name}: {path}")


def copy_artifact(source: Path, destination: Path) -> Path:
    shutil.copy2(source, destination)
    checksum_file = destination.with_name(destination.name + ".sha256")
    checksum_file.write_text(f"{sha256(destination)}  {destination.name}\n", encoding="utf-8")
    info(f"Artifact ready: {destination}")
    return destination


def package(platform: str) -> list[Path]:
    env = os.environ.copy()
    env["MOZCONFIG"] = str(SOURCE_DIR / "mozconfig")
    run(mach_command(platform, ["package"]), cwd=SOURCE_DIR, env=env)

    dist = SOURCE_DIR / OBJDIRS[platform] / "dist"
    artifacts: list[Path] = []
    if platform == "linux":
        package_file = newest(
            list(dist.glob("*.tar.bz2")) + list(dist.glob("*.tar.xz")) + list(dist.glob("*.tar.gz")),
            "Linux package",
        )
        verify_archive(package_file)
        suffix = "".join(package_file.suffixes[-2:])
        artifacts.append(
            copy_artifact(
                package_file,
                ROOT / f"NordFox-{NORDFOX_VERSION}-linux-x86_64{suffix}",
            )
        )
    else:
        portable = newest(list(dist.glob("*.zip")), "Windows portable package")
        verify_archive(portable)
        artifacts.append(
            copy_artifact(
                portable,
                ROOT / f"NordFox-{NORDFOX_VERSION}-windows-x86_64.zip",
            )
        )
        installer = newest(
            list(dist.glob("*installer*.exe")) + list(dist.glob("*setup*.exe")),
            "Windows installer",
        )
        artifacts.append(
            copy_artifact(
                installer,
                ROOT / f"NordFox-{NORDFOX_VERSION}-windows-x86_64-installer.exe",
            )
        )
    return artifacts


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("platform", choices=sorted(MOZCONFIGS))
    parser.add_argument("action", choices=("fetch", "prepare", "build", "package", "all"), nargs="?", default="all")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.action in ("fetch", "all"):
        fetch_source()
    if args.action in ("prepare", "all"):
        prepare_source(args.platform)
    if args.action in ("build", "all"):
        build(args.platform)
    if args.action in ("package", "all"):
        package(args.platform)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (RuntimeError, subprocess.CalledProcessError) as exc:
        print(f"[nordfox] ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
