#!/usr/bin/env python3
from __future__ import annotations

import argparse
import configparser
import copy
import io
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

try:
    from PIL import Image, ImageDraw
except ImportError as exc:
    raise SystemExit(
        "Pillow is required. Install it with:\n"
        "    python -m pip install Pillow\n"
    ) from exc


VERSION = "1.6.4"

SVG_NS = "http://www.w3.org/2000/svg"
INKSCAPE_NS = "http://www.inkscape.org/namespaces/inkscape"
XML_NS = "http://www.w3.org/XML/1998/namespace"
INKSCAPE_LABEL = "{" + INKSCAPE_NS + "}label"
XML_BASE = "{" + XML_NS + "}base"

FONT_EXTENSIONS = {".ttf", ".otf", ".ttc", ".otc"}

DENSITIES = {
    "mdpi": (48, 108),
    "hdpi": (72, 162),
    "xhdpi": (96, 216),
    "xxhdpi": (144, 324),
    "xxxhdpi": (192, 432),
}

ADAPTIVE_XML = """<?xml version="1.0" encoding="utf-8"?>
<adaptive-icon xmlns:android="http://schemas.android.com/apk/res/android">
    <background android:drawable="@mipmap/ic_launcher_v2_background"/>
    <foreground android:drawable="@mipmap/ic_launcher_v2_foreground"/>
</adaptive-icon>
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Generate SageTV Android logo resources from a 512x512 SVG using "
            "CairoSVG only. Linux/docker friendly; no Inkscape required."
        )
    )
    parser.add_argument("svg", type=Path, help="Input SVG, normally 512x512")
    parser.add_argument(
        "--config",
        type=Path,
        default=Path(__file__).with_name("sagetv_logo.ini"),
        help="INI settings file (default: sagetv_logo.ini next to script)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Override [general] output_root",
    )
    parser.add_argument(
        "--font-dir",
        action="append",
        type=Path,
        default=[],
        help=(
            "Additional local font directory. May be repeated. Relative paths "
            "are searched from the current/project directory, the SVG folder, "
            "the INI folder, and the script folder, plus their parents."
        ),
    )
    parser.add_argument(
        "--disable-local-fonts",
        action="store_true",
        help=(
            "Do not search for or load project-local fonts. Use fonts already "
            "installed on the operating system instead."
        ),
    )
    parser.add_argument(
        "--no-preview",
        action="store_true",
        help="Do not generate SageTV_logo_preview.png",
    )
    return parser.parse_args()


def cfg_get(cfg: configparser.ConfigParser, section: str, key: str, fallback: str) -> str:
    return cfg.get(section, key, fallback=fallback)


def cfg_int(cfg: configparser.ConfigParser, section: str, key: str, fallback: int) -> int:
    return cfg.getint(section, key, fallback=fallback)


def cfg_float(cfg: configparser.ConfigParser, section: str, key: str, fallback: float) -> float:
    return cfg.getfloat(section, key, fallback=fallback)


def cfg_bool(cfg: configparser.ConfigParser, section: str, key: str, fallback: bool) -> bool:
    return cfg.getboolean(section, key, fallback=fallback)


def parse_color(value: str) -> tuple[int, int, int, int]:
    value = value.strip()
    if value.lower() in {"transparent", "none", ""}:
        return (0, 0, 0, 0)
    if value.startswith("#"):
        hex_value = value[1:]
        if len(hex_value) == 6:
            return tuple(int(hex_value[index:index + 2], 16) for index in (0, 2, 4)) + (255,)
        if len(hex_value) == 8:
            return tuple(int(hex_value[index:index + 2], 16) for index in (0, 2, 4, 6))
    raise ValueError(
        f"Unsupported color {value!r}. Use transparent, #RRGGBB, or #RRGGBBAA."
    )


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1] if "}" in tag else tag


def parse_style_map(style: str) -> list[tuple[str, str]]:
    pairs: list[tuple[str, str]] = []
    for chunk in style.split(";"):
        if ":" not in chunk:
            continue
        key, value = chunk.split(":", 1)
        key = key.strip()
        value = value.strip()
        if key:
            pairs.append((key, value))
    return pairs


def style_with_visible_display(style: str | None) -> str:
    pairs = []
    if style:
        for key, value in parse_style_map(style):
            lowered = key.casefold()
            if lowered == "display" and value.strip().casefold() == "none":
                continue
            if lowered == "visibility" and value.strip().casefold() == "hidden":
                continue
            pairs.append((key, value))
    pairs.append(("display", "inline"))
    pairs.append(("visibility", "visible"))

    merged: list[tuple[str, str]] = []
    seen: set[str] = set()
    for key, value in reversed(pairs):
        lowered = key.casefold()
        if lowered in seen:
            continue
        seen.add(lowered)
        merged.append((key, value))
    merged.reverse()
    return ";".join(f"{key}:{value}" for key, value in merged)


def force_element_visible(element: ET.Element) -> None:
    if element.get("display", "").strip().casefold() == "none":
        element.set("display", "inline")
    if element.get("visibility", "").strip().casefold() == "hidden":
        element.set("visibility", "visible")

    style = element.get("style")
    if style is not None:
        element.set("style", style_with_visible_display(style))


def force_visible_recursive(element: ET.Element) -> None:
    force_element_visible(element)
    for child in list(element):
        force_visible_recursive(child)


def register_svg_namespaces(svg_path: Path) -> None:
    for _event, (prefix, uri) in ET.iterparse(svg_path, events=("start-ns",)):
        ET.register_namespace(prefix or "", uri)


def parse_list_values(value: str) -> list[str]:
    items: list[str] = []
    seen: set[str] = set()
    flattened = value.replace("\r", "\n").replace("\n", ",")
    for raw_item in flattened.split(","):
        item = raw_item.strip().strip('"')
        key = item.casefold()
        if item and key not in seen:
            items.append(item)
            seen.add(key)
    return items


def parse_aliases(value: str) -> list[tuple[str, str]]:
    aliases: list[tuple[str, str]] = []
    for raw_line in value.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if "=>" not in line:
            raise ValueError(
                f"Invalid font_name_aliases entry {raw_line!r}; expected old => new."
            )
        old_name, new_name = (part.strip() for part in line.split("=>", 1))
        if old_name and new_name:
            aliases.append((old_name, new_name))
    aliases.sort(key=lambda item: len(item[0]), reverse=True)
    return aliases


def unique_paths(paths: list[Path]) -> list[Path]:
    result: list[Path] = []
    seen: set[str] = set()
    for path in paths:
        key = os.path.normcase(str(path))
        if key not in seen:
            result.append(path)
            seen.add(key)
    return result


def compute_search_roots(current: Path, svg_path: Path, config_path: Path, script_path: Path, include_parents: bool) -> list[Path]:
    roots: list[Path] = []
    starts = [current, svg_path.parent, config_path.parent, script_path.parent]
    for start in starts:
        start = start.expanduser()
        try:
            start = start.resolve()
        except OSError:
            start = start.absolute()
        roots.append(start)
        if include_parents:
            roots.extend(start.parents)
    return unique_paths(roots)


def resolve_local_font_files(
    config: configparser.ConfigParser,
    svg_path: Path,
    config_path: Path,
    script_file: Path,
    cli_font_dirs: list[Path],
) -> tuple[list[Path], list[Path], list[str]]:
    if not cfg_bool(config, "fonts", "enabled", True):
        return [], [], []

    configured_dirs = parse_list_values(
        cfg_get(config, "fonts", "directories", "M_PLUS_Rounded_1c")
    )
    requested_dirs = [str(path) for path in cli_font_dirs] + configured_dirs
    required = cfg_bool(config, "fonts", "required", True)
    recursive = cfg_bool(config, "fonts", "recursive", True)
    include_parents = cfg_bool(
        config, "fonts", "search_parent_directories", True
    )

    roots = compute_search_roots(
        Path.cwd(), svg_path, config_path, script_file, include_parents
    )
    resolved_dirs: list[Path] = []
    missing_dirs: list[str] = []

    for raw_value in requested_dirs:
        item = raw_value.strip()
        if not item:
            continue
        raw_path = Path(os.path.expandvars(item)).expanduser()
        found_dir: Path | None = None

        if raw_path.is_absolute():
            if raw_path.is_dir():
                found_dir = raw_path.resolve()
        else:
            for root in roots:
                candidate = root / raw_path
                if candidate.is_dir():
                    found_dir = candidate.resolve()
                    break

        if found_dir is None:
            missing_dirs.append(item)
            continue
        if found_dir not in resolved_dirs:
            resolved_dirs.append(found_dir)

    if required and not resolved_dirs:
        raise FileNotFoundError(
            "Project-local font loading is enabled, but no configured font "
            "directory was found. Looked for: "
            + ", ".join(requested_dirs or ["M_PLUS_Rounded_1c"])
        )

    font_files: list[Path] = []
    seen_files: set[str] = set()
    for directory in resolved_dirs:
        iterator = directory.rglob("*") if recursive else directory.iterdir()
        for path in sorted(iterator):
            if not path.is_file():
                continue
            if path.suffix.casefold() not in FONT_EXTENSIONS:
                continue
            resolved_file = path.resolve()
            key = os.path.normcase(str(resolved_file))
            if key not in seen_files:
                font_files.append(resolved_file)
                seen_files.add(key)

    if required and not font_files:
        raise FileNotFoundError(
            "Project-local font directories were found, but no supported font "
            "files were present."
        )

    required_files = parse_list_values(
        cfg_get(config, "fonts", "required_files", "MPLUSRounded1c-ExtraBold.ttf")
    )
    available_names = {font_file.name.casefold() for font_file in font_files}
    missing_required_files = [
        file_name
        for file_name in required_files
        if Path(file_name).name.casefold() not in available_names
    ]
    if required and missing_required_files:
        raise FileNotFoundError(
            "Required font file(s) were not found: "
            + ", ".join(missing_required_files)
        )

    return resolved_dirs, font_files, missing_dirs


def make_fontconfig_environment(font_dirs: list[Path], work_root: Path) -> tuple[dict[str, str], Path | None]:
    if not font_dirs:
        return os.environ.copy(), None

    fc_root = work_root / "fontconfig"
    fc_root.mkdir(parents=True, exist_ok=True)
    cache_dir = fc_root / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    config_file = fc_root / "fonts.conf"

    dir_lines = "\n".join(f"  <dir>{directory}</dir>" for directory in font_dirs)
    config_file.write_text(
        "<?xml version=\"1.0\"?>\n"
        "<!DOCTYPE fontconfig SYSTEM \"fonts.dtd\">\n"
        "<fontconfig>\n"
        f"{dir_lines}\n"
        f"  <cachedir>{cache_dir}</cachedir>\n"
        "</fontconfig>\n",
        encoding="utf-8",
    )

    env = os.environ.copy()
    env["FONTCONFIG_FILE"] = str(config_file)
    env["FONTCONFIG_PATH"] = str(fc_root)
    env["XDG_CACHE_HOME"] = str(cache_dir)

    fc_cache = shutil.which("fc-cache")
    if fc_cache:
        subprocess.run(
            [fc_cache, "-f", *[str(directory) for directory in font_dirs]],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env,
        )

    return env, config_file


def prepare_svg_font_names(source_svg: Path, prepared_svg: Path, aliases: list[tuple[str, str]]) -> dict[str, int]:
    register_svg_namespaces(source_svg)
    try:
        svg_text = source_svg.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValueError(f"The SVG is not valid UTF-8 text: {source_svg}") from exc

    applied: dict[str, int] = {}
    for old_name, new_name in aliases:
        pattern = re.compile(re.escape(old_name), flags=re.IGNORECASE)
        svg_text, count = pattern.subn(new_name, svg_text)
        if count:
            applied[f"{old_name} => {new_name}"] = count

    prepared_svg.parent.mkdir(parents=True, exist_ok=True)
    prepared_svg.write_text(svg_text, encoding="utf-8")

    tree = ET.parse(prepared_svg)
    root = tree.getroot()
    if not root.get(XML_BASE):
        try:
            root.set(XML_BASE, source_svg.resolve().parent.as_uri() + "/")
        except ValueError:
            pass
    tree.write(prepared_svg, encoding="utf-8", xml_declaration=True)
    return applied


def build_font_report_lines(
    font_dirs: list[Path],
    font_files: list[Path],
    config_file: Path | None,
    alias_counts: dict[str, int],
    missing_dirs: list[str],
) -> list[str]:
    lines = [
        f"SageTV Android Logo Generator v{VERSION}",
        "CairoSVG local font loading report",
        "",
        "Fonts are provided through a temporary Fontconfig configuration.",
        "No fonts are installed globally and Inkscape is not required.",
        "",
        "Resolved font directories:",
    ]
    if font_dirs:
        lines.extend(f"  {directory}" for directory in font_dirs)
    else:
        lines.append("  (none)")
    lines.extend(["", "Font files loaded:"])
    if font_files:
        lines.extend(f"  {font_file.name}" for font_file in font_files)
    else:
        lines.append("  (none)")
    lines.extend(["", "Fontconfig file:"])
    lines.append(f"  {config_file}" if config_file else "  (none)")
    lines.extend(["", "Temporary SVG font-name aliases:"])
    if alias_counts:
        lines.extend(
            f"  {alias}: {count} replacement(s)"
            for alias, count in alias_counts.items()
        )
    else:
        lines.append("  (none)")
    if missing_dirs:
        lines.extend(["", "Optional font directories not found:"])
        lines.extend(f"  {item}" for item in missing_dirs)
    return lines


def render_svg_with_cairosvg(svg: Path, width: int, height: int, env: dict[str, str]) -> Image.Image:
    helper = (
        "import sys, cairosvg;"
        "svg_path, width, height, out_path = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), sys.argv[4];"
        "cairosvg.svg2png(url=svg_path, write_to=out_path, output_width=width, output_height=height)"
    )
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as temp_file:
        temp_path = temp_file.name
    try:
        result = subprocess.run(
            [sys.executable, "-c", helper, str(svg), str(width), str(height), temp_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
        )
        if result.returncode != 0:
            raise RuntimeError(
                "CairoSVG render failed.\n\n"
                f"stderr:\n{result.stderr.decode('utf-8', errors='replace')}"
            )
        return Image.open(temp_path).convert("RGBA")
    finally:
        try:
            os.unlink(temp_path)
        except OSError:
            pass


def transformed_canvas(
    source: Image.Image,
    width: int,
    height: int,
    *,
    mode: str,
    scale: float,
    offset_x: float,
    offset_y: float,
    background: tuple[int, int, int, int],
) -> Image.Image:
    mode = mode.strip().lower()
    if mode not in {"cover", "contain"}:
        raise ValueError("mode must be cover or contain")
    if scale <= 0:
        raise ValueError("scale must be > 0")

    canvas = Image.new("RGBA", (width, height), background)
    if mode == "cover":
        base_scale = max(width / source.width, height / source.height)
    else:
        base_scale = min(width / source.width, height / source.height)

    final_scale = base_scale * scale
    new_w = max(1, round(source.width * final_scale))
    new_h = max(1, round(source.height * final_scale))
    resized = source.resize((new_w, new_h), Image.Resampling.LANCZOS)

    x = round((width - new_w) / 2 + offset_x)
    y = round((height - new_h) / 2 + offset_y)
    canvas.alpha_composite(resized, (x, y))
    return canvas


def resize_square(source: Image.Image, size: int, scale: float, offset_x: float, offset_y: float) -> Image.Image:
    return transformed_canvas(
        source,
        size,
        size,
        mode="contain",
        scale=scale,
        offset_x=offset_x,
        offset_y=offset_y,
        background=(0, 0, 0, 0),
    )


def round_mask(image: Image.Image, supersample: int = 4) -> Image.Image:
    source = image.convert("RGBA")
    width, height = source.size
    if width != height:
        raise ValueError("round_mask requires a square image")
    if supersample < 1:
        raise ValueError("round_mask supersample must be >= 1")

    large_size = width * supersample
    large_mask = Image.new("L", (large_size, large_size), 0)
    draw = ImageDraw.Draw(large_mask)
    draw.ellipse((0, 0, large_size - 1, large_size - 1), fill=255)
    mask = large_mask.resize((width, height), Image.Resampling.LANCZOS)

    red, green, blue, alpha = source.split()
    import PIL.ImageChops
    combined_alpha = PIL.ImageChops.multiply(alpha, mask)

    clipped = Image.merge("RGBA", (red, green, blue, combined_alpha))
    result = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    result.alpha_composite(clipped)
    return result


def assert_transparent_round_background(image: Image.Image, label: str) -> None:
    rgba = image.convert("RGBA")
    width, height = rgba.size
    corners = (
        rgba.getpixel((0, 0)),
        rgba.getpixel((width - 1, 0)),
        rgba.getpixel((0, height - 1)),
        rgba.getpixel((width - 1, height - 1)),
    )
    if any(pixel != (0, 0, 0, 0) for pixel in corners):
        raise RuntimeError(
            f"Round icon {label} does not have fully transparent corners: {corners}"
        )


def trim_transparent(image: Image.Image, threshold: int = 1, padding: int = 0) -> Image.Image:
    rgba = image.convert("RGBA")
    alpha = rgba.getchannel("A")
    mask = alpha.point(lambda value: 255 if value >= threshold else 0)
    bbox = mask.getbbox()
    if bbox is None:
        return rgba

    left, top, right, bottom = bbox
    left = max(0, left - padding)
    top = max(0, top - padding)
    right = min(rgba.width, right + padding)
    bottom = min(rgba.height, bottom + padding)
    return rgba.crop((left, top, right, bottom))


def save_png(image: Image.Image, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path, "PNG", optimize=True)


def write_adaptive_xml(base: Path) -> None:
    anydpi = base / "source/dev/android-shared/src/main/res/mipmap-anydpi-v26"
    anydpi.mkdir(parents=True, exist_ok=True)
    (anydpi / "ic_launcher_v2.xml").write_text(ADAPTIVE_XML, encoding="utf-8")
    (anydpi / "ic_launcher_v2_round.xml").write_text(ADAPTIVE_XML, encoding="utf-8")


def get_element_name_candidates(element: ET.Element) -> list[str]:
    candidates: list[str] = []
    for value in (element.get("id"), element.get(INKSCAPE_LABEL)):
        if value:
            candidates.append(value)
    return candidates


def token_match(selector: str, name: str) -> bool:
    folded_selector = selector.casefold()
    folded_name = name.casefold()
    if folded_name.startswith(folded_selector + "-"):
        return True
    tokens = re.split(r"[^a-z0-9]+", folded_name)
    return folded_selector in {token for token in tokens if token}


def find_selector_matches(root: ET.Element, selector: str) -> tuple[list[ET.Element], str]:
    folded_selector = selector.casefold()
    exact: list[ET.Element] = []
    fuzzy: list[ET.Element] = []

    for element in root.iter():
        names = get_element_name_candidates(element)
        if any(name.casefold() == folded_selector for name in names):
            exact.append(element)
            continue
        if any(token_match(selector, name) for name in names):
            fuzzy.append(element)

    if exact:
        return exact, "exact"
    if fuzzy:
        return fuzzy, "prefix/token fallback"
    return [], "missing"


def prepare_master_render_svg(
    source_svg: Path,
    selectors: list[str],
    require_all: bool,
) -> tuple[ET.ElementTree, list[str], dict[str, str]]:
    register_svg_namespaces(source_svg)
    tree = ET.parse(source_svg)
    root = tree.getroot()

    match_modes: dict[str, str] = {}
    report_lines: list[str] = []

    for selector in selectors:
        matches, mode = find_selector_matches(root, selector)
        match_modes[selector] = mode
        if require_all and not matches:
            raise ValueError(
                f"Required full-render selector {selector!r} was not found in the SVG."
            )
        if matches:
            report_lines.append(f"{selector}: {mode} ({len(matches)})")
            for match in matches[:25]:
                force_visible_recursive(match)
                label = match.get(INKSCAPE_LABEL)
                identifier = match.get("id")
                details = []
                if identifier:
                    details.append(f"id={identifier}")
                if label:
                    details.append(f"label={label}")
                report_lines.append("  - " + ", ".join(details or [local_name(match.tag)]))
        else:
            report_lines.append(f"{selector}: missing")

    return tree, report_lines, match_modes


def build_filtered_svg(
    source_svg: Path,
    selectors: list[str],
    require_all: bool,
) -> tuple[ET.ElementTree, list[str], dict[str, str]]:
    register_svg_namespaces(source_svg)
    tree = ET.parse(source_svg)
    root = tree.getroot()
    parent_map = {child: parent for parent in root.iter() for child in list(parent)}

    matched_elements: set[ET.Element] = set()
    match_modes: dict[str, str] = {}
    report_lines: list[str] = []

    for selector in selectors:
        matches, mode = find_selector_matches(root, selector)
        match_modes[selector] = mode
        if require_all and not matches:
            raise ValueError(
                f"Required selector {selector!r} was not found in the SVG."
            )
        if matches:
            matched_elements.update(matches)
            report_lines.append(f"{selector}: {mode} ({len(matches)})")
            for match in matches[:25]:
                label = match.get(INKSCAPE_LABEL)
                identifier = match.get("id")
                details = []
                if identifier:
                    details.append(f"id={identifier}")
                if label:
                    details.append(f"label={label}")
                report_lines.append("  - " + ", ".join(details or [local_name(match.tag)]))
        else:
            report_lines.append(f"{selector}: missing")

    keep: set[ET.Element] = set()
    for element in matched_elements:
        current: ET.Element | None = element
        while current is not None:
            keep.add(current)
            current = parent_map.get(current)

    def clone_node(node: ET.Element) -> ET.Element | None:
        tag = local_name(node.tag)

        # Shared definitions/styles must remain available to selected artwork.
        if tag == "defs":
            return copy.deepcopy(node)

        # When a selector matches a whole group/layer (for example TEXT or wave),
        # keep the complete authored subtree and make sure hidden-layer state
        # does not suppress it.
        if node in matched_elements:
            clone = copy.deepcopy(node)
            force_visible_recursive(clone)
            return clone

        child_copies: list[ET.Element] = []
        for child in list(node):
            copied = clone_node(child)
            if copied is not None:
                child_copies.append(copied)

        # Ancestors are kept only as structural/transform containers around the
        # selected descendants. If a source ancestor was hidden, force it visible
        # so the kept descendants still render.
        if node in keep or child_copies:
            clone = ET.Element(node.tag, node.attrib)
            clone.text = node.text
            clone.tail = node.tail
            for child in child_copies:
                clone.append(child)
            force_element_visible(clone)
            return clone
        return None

    new_root = ET.Element(root.tag, root.attrib)
    new_root.text = root.text
    for child in list(root):
        copied = clone_node(child)
        if copied is not None:
            new_root.append(copied)

    return ET.ElementTree(new_root), report_lines, match_modes


def overlay_tree(source_root: Path, dest_root: Path) -> int:
    count = 0
    for item in sorted(source_root.rglob("*")):
        if not item.is_file():
            continue
        destination = dest_root / item.relative_to(source_root)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(item, destination)
        count += 1
    return count


def create_preview(output_root: Path) -> None:
    items = [
        ("Play Store",
         output_root / "source/dev/android-shared/src/main/ic_launcher_v2-playstore.png"),
        ("Launcher xxxhdpi",
         output_root / "source/dev/android-shared/src/main/res/mipmap-xxxhdpi/ic_launcher_v2.png"),
        ("Round xxxhdpi",
         output_root / "source/dev/android-shared/src/main/res/mipmap-xxxhdpi/ic_launcher_v2_round.png"),
        ("TV Banner",
         output_root / "source/dev/android-tv/src/main/res/drawable/banner_v2.png"),
        ("In-app logo",
         output_root / "source/dev/android-shared/src/main/res/drawable/sage_logo_256.png"),
    ]

    cell_w, cell_h = 620, 260
    preview = Image.new("RGBA", (cell_w, cell_h * len(items)), (238, 238, 238, 255))
    draw = ImageDraw.Draw(preview)

    for index, (label, path) in enumerate(items):
        top = index * cell_h
        draw.rectangle((8, top + 8, cell_w - 8, top + cell_h - 8), fill=(255, 255, 255, 255))
        if path.is_file():
            with Image.open(path) as loaded:
                image = loaded.convert("RGBA")
            label = f"{label} {image.width}x{image.height}"
            draw.text((18, top + 18), label, fill=(0, 0, 0, 255))
        else:
            draw.text((18, top + 18), f"{label} (missing)", fill=(0, 0, 0, 255))
            continue

        if path.is_file():
            max_w = cell_w - 60
            max_h = cell_h - 70
            factor = min(max_w / image.width, max_h / image.height, 1.0)
            display = image.resize(
                (max(1, round(image.width * factor)), max(1, round(image.height * factor))),
                Image.Resampling.LANCZOS,
            )

            background = Image.new("RGBA", display.size, (220, 220, 220, 255))
            for y in range(0, display.height, 16):
                for x in range(0, display.width, 16):
                    fill = (210, 210, 210, 255) if ((x // 16) + (y // 16)) % 2 == 0 else (235, 235, 235, 255)
                    for py in range(y, min(y + 16, display.height)):
                        for px in range(x, min(x + 16, display.width)):
                            background.putpixel((px, py), fill)
            background.alpha_composite(display)
            x = (cell_w - display.width) // 2
            y = top + 48 + (max_h - display.height) // 2
            preview.alpha_composite(background, (x, y))

    save_png(preview, output_root / "SageTV_logo_preview.png")


def generate_to_stage(
    source_svg: Path,
    config: configparser.ConfigParser,
    stage_root: Path,
    render_env: dict[str, str],
    *,
    create_preview_image: bool,
) -> dict[str, str]:
    launcher_scale = cfg_float(config, "launcher", "scale", 1.0)
    launcher_x = cfg_float(config, "launcher", "offset_x", 0.0)
    launcher_y = cfg_float(config, "launcher", "offset_y", 0.0)

    round_antialias = cfg_int(config, "round_icon", "antialias_scale", 4)

    adaptive_layer = cfg_get(
        config, "adaptive_icon", "artwork_layer", "background"
    ).strip().lower()
    adaptive_scale = cfg_float(config, "adaptive_icon", "scale", 1.0)
    adaptive_x = cfg_float(config, "adaptive_icon", "offset_x", 0.0)
    adaptive_y = cfg_float(config, "adaptive_icon", "offset_y", 0.0)
    adaptive_background = parse_color(
        cfg_get(config, "adaptive_icon", "background_color", "transparent")
    )

    banner_width = cfg_int(config, "banner", "width", 320)
    banner_height = cfg_int(config, "banner", "height", 180)
    banner_mode = cfg_get(config, "banner", "mode", "cover")
    banner_scale = cfg_float(config, "banner", "scale", 1.0)
    banner_x = cfg_float(config, "banner", "offset_x", 0.0)
    banner_y = cfg_float(config, "banner", "offset_y", 0.0)
    banner_background = parse_color(
        cfg_get(config, "banner", "background_color", "#000000")
    )

    in_app_width = cfg_int(config, "in_app_logo", "width", 256)
    in_app_height = cfg_int(config, "in_app_logo", "height", 89)
    in_app_mode = cfg_get(config, "in_app_logo", "mode", "cover")
    if in_app_mode.strip().lower() != "cover":
        raise ValueError(
            "The in-app logo must use mode = cover so it clips center like the banner."
        )
    in_app_scale = cfg_float(config, "in_app_logo", "scale", 1.0)
    in_app_x = cfg_float(config, "in_app_logo", "offset_x", 0.0)
    in_app_y = cfg_float(config, "in_app_logo", "offset_y", 0.0)
    in_app_background = parse_color(
        cfg_get(config, "in_app_logo", "background_color", "transparent")
    )
    if in_app_background != (0, 0, 0, 0):
        raise ValueError("The in-app logo background must be transparent.")
    in_app_render_size = cfg_int(config, "in_app_logo", "render_size", 2048)
    in_app_trim = cfg_bool(config, "in_app_logo", "trim_transparent_margins", True)
    trim_alpha_threshold = cfg_int(config, "in_app_logo", "trim_alpha_threshold", 1)
    trim_padding = cfg_int(config, "in_app_logo", "trim_padding", 0)

    master_size = cfg_int(config, "general", "master_render_size", 512)
    full_render_selectors = parse_list_values(
        cfg_get(config, "full_render", "force_visible", "background, hex-patterns")
    )
    full_render_require_all = cfg_bool(
        config, "full_render", "require_all_groups", False
    )

    work_debug = stage_root / "_sagetv_logo_debug"
    work_debug.mkdir(parents=True, exist_ok=True)

    if full_render_selectors:
        master_tree, master_visibility_report_lines, master_match_modes = prepare_master_render_svg(
            source_svg,
            full_render_selectors,
            require_all=full_render_require_all,
        )
        master_svg_path = work_debug / "master_render_forced_visible.svg"
        master_tree.write(master_svg_path, encoding="utf-8", xml_declaration=True)
        master_source_svg = master_svg_path
    else:
        master_visibility_report_lines = []
        master_match_modes = {}
        master_source_svg = source_svg

    master = render_svg_with_cairosvg(master_source_svg, master_size, master_size, render_env)

    selectors = parse_list_values(
        cfg_get(config, "in_app_logo", "groups", "TEXT, flower, wave")
    )
    require_all = cfg_bool(config, "in_app_logo", "require_all_groups", True)
    save_debug_files = cfg_bool(config, "in_app_logo", "save_debug_files", True)

    filtered_tree, selection_report_lines, match_modes = build_filtered_svg(
        source_svg,
        selectors,
        require_all=require_all,
    )

    filtered_svg_path = work_debug / "in_app_groups_only.svg"
    filtered_tree.write(filtered_svg_path, encoding="utf-8", xml_declaration=True)

    filtered_page = render_svg_with_cairosvg(
        filtered_svg_path,
        in_app_render_size,
        in_app_render_size,
        render_env,
    )
    filtered_for_crop = trim_transparent(
        filtered_page,
        threshold=trim_alpha_threshold,
        padding=trim_padding,
    ) if in_app_trim else filtered_page

    in_app_logo = transformed_canvas(
        filtered_for_crop,
        in_app_width,
        in_app_height,
        mode="cover",
        scale=in_app_scale,
        offset_x=in_app_x,
        offset_y=in_app_y,
        background=(0, 0, 0, 0),
    )
    if in_app_logo.getchannel("A").getextrema()[1] == 0:
        raise RuntimeError("The in-app logo rendered completely transparent.")

    if save_debug_files:
        save_png(filtered_page, work_debug / "in_app_groups_only_page.png")
        save_png(filtered_for_crop, work_debug / "in_app_groups_only_trimmed.png")
        (work_debug / "in_app_selection.txt").write_text(
            "\n".join(selection_report_lines) + "\n",
            encoding="utf-8",
        )
        (work_debug / "master_visibility_selection.txt").write_text(
            "\n".join(master_visibility_report_lines) + "\n",
            encoding="utf-8",
        )

    save_png(
        resize_square(master, 512, launcher_scale, launcher_x, launcher_y),
        stage_root / "source/dev/android-shared/src/main/ic_launcher_v2-playstore.png",
    )

    for density, (legacy_size, adaptive_size) in DENSITIES.items():
        folder = stage_root / f"source/dev/android-shared/src/main/res/mipmap-{density}"

        normal = resize_square(master, legacy_size, launcher_scale, launcher_x, launcher_y)
        save_png(normal, folder / "ic_launcher_v2.png")

        round_icon = round_mask(normal, supersample=round_antialias)
        assert_transparent_round_background(round_icon, density)
        round_path = folder / "ic_launcher_v2_round.png"
        save_png(round_icon, round_path)
        with Image.open(round_path) as loaded_round:
            assert_transparent_round_background(loaded_round, density + " saved")

        transparent = Image.new("RGBA", (adaptive_size, adaptive_size), (0, 0, 0, 0))
        if adaptive_layer == "background":
            adaptive_background_layer = transformed_canvas(
                master,
                adaptive_size,
                adaptive_size,
                mode="contain",
                scale=adaptive_scale,
                offset_x=adaptive_x,
                offset_y=adaptive_y,
                background=adaptive_background,
            )
            adaptive_foreground_layer = transparent
        elif adaptive_layer == "foreground":
            adaptive_background_layer = Image.new(
                "RGBA",
                (adaptive_size, adaptive_size),
                adaptive_background,
            )
            adaptive_foreground_layer = transformed_canvas(
                master,
                adaptive_size,
                adaptive_size,
                mode="contain",
                scale=adaptive_scale,
                offset_x=adaptive_x,
                offset_y=adaptive_y,
                background=(0, 0, 0, 0),
            )
        else:
            raise ValueError("[adaptive_icon] artwork_layer must be background or foreground")

        save_png(adaptive_background_layer, folder / "ic_launcher_v2_background.png")
        save_png(adaptive_foreground_layer, folder / "ic_launcher_v2_foreground.png")

    write_adaptive_xml(stage_root)

    banner = transformed_canvas(
        master,
        banner_width,
        banner_height,
        mode=banner_mode,
        scale=banner_scale,
        offset_x=banner_x,
        offset_y=banner_y,
        background=banner_background,
    )
    save_png(
        banner,
        stage_root / "source/dev/android-tv/src/main/res/drawable/banner_v2.png",
    )

    save_png(
        in_app_logo,
        stage_root / "source/dev/android-shared/src/main/res/drawable/sage_logo_256.png",
    )

    if create_preview_image:
        create_preview(stage_root)

    return {
        "renderer": "CairoSVG",
        "selection_count": str(len(selectors)),
        "in_app_match_modes": ", ".join(f"{key}={value}" for key, value in match_modes.items()),
        "full_render_match_modes": ", ".join(
            f"{key}={value}" for key, value in master_match_modes.items()
        ),
    }


def main() -> int:
    args = parse_args()
    svg_path = args.svg.expanduser().resolve()
    if not svg_path.is_file():
        raise SystemExit(f"Input SVG was not found: {svg_path}")

    config_path = args.config.expanduser().resolve()
    config = configparser.ConfigParser()
    if not config_path.is_file():
        raise FileNotFoundError(
            f"Config file was not found: {config_path}\n"
            "The default name is exactly sagetv_logo.ini. If your browser saved "
            "it as sagetv_logo(1).ini, either rename it or pass "
            "--config sagetv_logo(1).ini."
        )
    loaded_configs = config.read(config_path, encoding="utf-8")
    if not loaded_configs:
        raise RuntimeError(f"Config file could not be loaded: {config_path}")

    output_root = (
        args.output.expanduser().resolve()
        if args.output is not None
        else Path(cfg_get(config, "general", "output_root", "generated")).expanduser().resolve()
    )
    preview_enabled = cfg_bool(config, "general", "create_preview", True) and not args.no_preview

    script_file = Path(__file__).resolve()
    if args.disable_local_fonts:
        font_dirs, font_files, missing_dirs = [], [], []
    else:
        font_dirs, font_files, missing_dirs = resolve_local_font_files(
            config,
            svg_path,
            config_path,
            script_file,
            args.font_dir,
        )
    aliases = parse_aliases(
        cfg_get(
            config,
            "fonts",
            "font_name_aliases",
            (
                "Rounded Mplus 1c, Ultra-Bold => M PLUS Rounded 1c, ExtraBold\n"
                "Rounded Mplus 1c => M PLUS Rounded 1c\n"
                "M_PLUS_Rounded_1c => M PLUS Rounded 1c"
            ),
        )
    )

    print(f"SageTV Android Logo Generator v{VERSION}")
    print(f"Input:   {svg_path}")
    print(f"Config:  {config_path}")
    print(f"Output:  {output_root}")
    print(
        "Banner:  "
        f"{cfg_int(config, 'banner', 'width', 320)}x"
        f"{cfg_int(config, 'banner', 'height', 180)}"
    )
    print(
        "In-app:  "
        f"{cfg_int(config, 'in_app_logo', 'width', 256)}x"
        f"{cfg_int(config, 'in_app_logo', 'height', 89)} "
        f"scale={cfg_float(config, 'in_app_logo', 'scale', 1.0)} "
        f"offset=({cfg_float(config, 'in_app_logo', 'offset_x', 0.0)},"
        f"{cfg_float(config, 'in_app_logo', 'offset_y', 0.0)})"
    )

    with tempfile.TemporaryDirectory(prefix="sagetv_logo_work_") as temp_name:
        work_root = Path(temp_name)
        prepared_svg = work_root / "prepared" / svg_path.name
        applied_aliases = prepare_svg_font_names(svg_path, prepared_svg, aliases)

        render_env, fontconfig_file = make_fontconfig_environment(font_dirs, work_root)
        stage_root = work_root / "generated"
        stage_root.mkdir(parents=True, exist_ok=True)

        result = generate_to_stage(
            prepared_svg,
            config,
            stage_root,
            render_env,
            create_preview_image=preview_enabled,
        )

        if cfg_bool(config, "fonts", "save_report", True):
            report_dir = stage_root / "_sagetv_logo_debug"
            report_dir.mkdir(parents=True, exist_ok=True)
            report_path = report_dir / "font_loading.txt"
            report_path.write_text(
                "\n".join(
                    build_font_report_lines(
                        font_dirs,
                        font_files,
                        fontconfig_file,
                        applied_aliases,
                        missing_dirs,
                    )
                ) + "\n",
                encoding="utf-8",
            )

        copied_count = overlay_tree(stage_root, output_root)

    print(f"Renderer: {result['renderer']}")
    if args.disable_local_fonts:
        print("Project-local font loading: disabled")
        print("Using fonts already installed on the operating system.")
    elif font_dirs:
        print("Project-local font directories:")
        for directory in font_dirs:
            print(f"  - {directory}")
        print(f"Project-local font files loaded: {len(font_files)}")
    if applied_aliases:
        print("Temporary SVG font-name aliases:")
        for alias, count in applied_aliases.items():
            print(f"  - {alias} ({count} replacement(s))")
    print(f"Generated/updated files: {copied_count}")
    print("Done.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
