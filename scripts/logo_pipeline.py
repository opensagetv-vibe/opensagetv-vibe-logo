#!/usr/bin/env python3
"""Build, validate, and install canonical OpenSageTV Vibe Android artwork."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = ROOT / "generated" / "source" / "dev"
DENSITIES = {
    "mdpi": (48, 108), "hdpi": (72, 162), "xhdpi": (96, 216),
    "xxhdpi": (144, 324), "xxxhdpi": (192, 432),
}
EXPECTED_PNGS = {
    "android-shared/src/main/ic_launcher_v2-playstore.png": (512, 512),
    "android-shared/src/main/res/drawable/sage_logo_256.png": (320, 150),
    "android-tv/src/main/res/drawable/banner_v2.png": (320, 180),
}
for density, (legacy, adaptive) in DENSITIES.items():
    base = f"android-shared/src/main/res/mipmap-{density}"
    EXPECTED_PNGS[f"{base}/ic_launcher_v2.png"] = (legacy, legacy)
    EXPECTED_PNGS[f"{base}/ic_launcher_v2_round.png"] = (legacy, legacy)
    EXPECTED_PNGS[f"{base}/ic_launcher_v2_background.png"] = (adaptive, adaptive)
    EXPECTED_PNGS[f"{base}/ic_launcher_v2_foreground.png"] = (adaptive, adaptive)
EXPECTED_XMLS = {
    "android-shared/src/main/res/mipmap-anydpi-v26/ic_launcher_v2.xml",
    "android-shared/src/main/res/mipmap-anydpi-v26/ic_launcher_v2_round.xml",
}
EXPECTED = sorted([*EXPECTED_PNGS, *EXPECTED_XMLS])


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def validate(root: Path) -> None:
    actual = {p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file()}
    missing = sorted(set(EXPECTED) - actual)
    if missing:
        raise RuntimeError("missing required Android logo assets: " + ", ".join(missing))
    for relative, dimensions in EXPECTED_PNGS.items():
        with Image.open(root / relative) as image:
            if image.size != dimensions or image.mode != "RGBA":
                raise RuntimeError(
                    f"{relative}: expected RGBA {dimensions}, got {image.mode} {image.size}"
                )
            image.verify()
    for relative in EXPECTED_XMLS:
        text = (root / relative).read_text(encoding="utf-8")
        if "<adaptive-icon" not in text or "@mipmap/ic_launcher_v2_" not in text:
            raise RuntimeError(f"invalid adaptive-icon resource: {relative}")
    print(f"PASS: validated {len(EXPECTED)} Android logo assets")


def build() -> None:
    with tempfile.TemporaryDirectory(prefix="opensagetv_vibe_logo_") as temporary:
        staged = Path(temporary) / "generated"
        subprocess.run([
            sys.executable, str(ROOT / "sagetv_logo_generator.py"),
            str(ROOT / "SageTV_VIBE_512_V3.svg"), "--config",
            str(ROOT / "sagetv_logo.ini"), "--output", str(staged),
        ], cwd=ROOT, check=True)
        destination = ROOT / "generated"
        if destination.exists():
            shutil.rmtree(destination)
        shutil.copytree(staged, destination)
    validate(SOURCE_ROOT)


def install(android_root: Path) -> None:
    validate(SOURCE_ROOT)
    android_source = android_root / "source" / "dev"
    if not (android_source / "settings.gradle").is_file():
        raise RuntimeError(f"not an OpenSageTV Vibe Android checkout: {android_root}")
    entries = []
    for relative in EXPECTED:
        source = SOURCE_ROOT / relative
        target = android_source / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_name(target.name + ".logo-tmp")
        shutil.copy2(source, temporary)
        temporary.replace(target)
        source_hash = digest(source)
        if digest(target) != source_hash:
            raise RuntimeError(f"post-copy verification failed: {relative}")
        entries.append({"path": f"source/dev/{relative}", "sha256": source_hash})
    manifest_path = android_root / "config" / "logo-assets.sha256"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps({
        "schema": 1, "source_project": "opensagetv-vibe-logo",
        "generator_version": "1.6.4", "assets": entries,
    }, indent=2) + "\n", encoding="utf-8")
    refresh_android_source_manifest(android_root, [entry["path"] for entry in entries])
    print(f"PASS: installed {len(entries)} logo assets into {android_root}")


def refresh_android_source_manifest(android_root: Path, asset_paths: list[str]) -> None:
    """Update only logo-owned entries; never bless unrelated source changes."""
    path = android_root / "PROJECT_MANIFEST.sha256"
    if not path.is_file():
        raise RuntimeError(f"Android source manifest is missing: {path}")
    values = {}
    for line in path.read_text(encoding="ascii").splitlines():
        if "  " not in line:
            raise RuntimeError(f"malformed Android source manifest entry: {line}")
        checksum, relative = line.split("  ", 1)
        values[relative] = checksum
    values.pop("branding/SageTV-Vibe.png", None)
    managed = [*asset_paths, "config/logo-assets.sha256"]
    for relative in managed:
        target = android_root / relative
        if not target.is_file():
            raise RuntimeError(f"logo-owned Android file is missing: {relative}")
        values[relative] = digest(target)
    path.write_text(
        "".join(f"{values[name]}  {name}\n" for name in sorted(values)),
        encoding="ascii",
        newline="\n",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("build", "validate", "install", "all"))
    parser.add_argument("--android-root", type=Path,
                        default=ROOT.parent / "opensagetv-vibe-android-client")
    args = parser.parse_args()
    if args.command in {"build", "all"}:
        build()
    if args.command == "validate":
        validate(SOURCE_ROOT)
    if args.command in {"install", "all"}:
        install(args.android_root.resolve())
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(f"ERROR: {error}", file=sys.stderr)
        raise SystemExit(1)
