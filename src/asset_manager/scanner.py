"""Scanner: walks the texture library and builds a catalog of TextureSets."""

from __future__ import annotations

import json
import re
from pathlib import Path

from .models import (
    MapType,
    Source,
    TextureMap,
    TextureSet,
    SUFFIX_TO_MAP,
)

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".exr", ".tif", ".tiff", ".tga", ".bmp"}


def detect_source(folder: Path) -> Source:
    """Guess the provider from folder naming and contents."""
    name = folder.name

    # AmbientCG: ends with _1K-JPG, _4K-PNG, etc.
    if re.search(r"\d+K-(JPG|PNG)$", name, re.IGNORECASE):
        return Source.AMBIENTCG

    # PolyHaven: ends with _4k.blend, _2k.blend, etc.
    if re.search(r"_\d+k\.blend$", name, re.IGNORECASE):
        return Source.POLYHAVEN

    # Megascans: has a short hash-like code and a .json metadata file
    if re.search(r"_[a-z0-9]{7,8}_\d+k$", name, re.IGNORECASE):
        return Source.MEGASCANS
    # Also check for json metadata as fallback
    if any(f.suffix == ".json" for f in folder.iterdir() if f.is_file()):
        return Source.MEGASCANS

    return Source.UNKNOWN


def detect_resolution(folder_name: str) -> str:
    """Extract resolution string from folder name."""
    match = re.search(r"(\d+)[kK]", folder_name)
    return f"{match.group(1)}K" if match else ""


def classify_map(filename: str, source: Source = Source.UNKNOWN) -> MapType:
    """Determine the PBR map type from a texture filename."""
    stem = Path(filename).stem.lower()

    # Try matching suffix after the last underscore, then progressively longer suffixes
    parts = stem.replace("-", "_").split("_")
    # Try 1-part, 2-part, 3-part suffix from the end
    for n in range(1, min(4, len(parts) + 1)):
        suffix = "_".join(parts[-n:])
        # Strip resolution codes like "4k", "2k" from the suffix
        suffix_clean = re.sub(r"_?\d+k$", "", suffix, flags=re.IGNORECASE).strip("_")
        # Strip format indicators that PolyHaven sometimes inserts (e.g. _diff_png_4k)
        suffix_clean = re.sub(r"_(png|jpg|exr|tif)$", "", suffix_clean).strip("_")
        if suffix_clean in SUFFIX_TO_MAP:
            map_type = SUFFIX_TO_MAP[suffix_clean]
            # Megascans "_Normal" (no GL/DX suffix) is actually DirectX format
            if map_type == MapType.NORMAL_GL and source == Source.MEGASCANS:
                if suffix_clean == "normal":
                    return MapType.NORMAL_DX
            return map_type

    return MapType.UNKNOWN


# Files that are provider previews, not PBR maps — detect by name pattern
_PREVIEW_PATTERNS = [
    re.compile(r"^preview$", re.IGNORECASE),
]


def _is_preview_image(path: Path, folder: Path) -> bool:
    """Check if an image file is a provider-supplied preview, not a PBR map."""
    stem = path.stem
    # AmbientCG previews: name matches the material base name with no suffix
    # e.g. Asphalt015.png in a folder called Asphalt015_4K-JPG
    # These have no underscore-delimited map suffix
    if "_" not in stem and path.parent == folder:
        return True
    if any(p.match(stem) for p in _PREVIEW_PATTERNS):
        return True
    return False


def scan_folder(folder: Path) -> TextureSet:
    """Scan a single texture folder and return a TextureSet."""
    source = detect_source(folder)
    resolution = detect_resolution(folder.name)

    # Build a clean name from the folder
    name = folder.name
    # Strip resolution and format suffixes for display
    name = re.sub(r"[_.]?\d+[kK](\.blend)?$", "", name)
    name = re.sub(r"_?\d+K-(JPG|PNG)$", "", name, flags=re.IGNORECASE)
    # Replace underscores with spaces for readability
    display_name = name.replace("_", " ").strip()

    ts = TextureSet(
        name=display_name,
        folder=folder,
        source=source,
        resolution=resolution,
    )

    # Collect all image files (including in subdirectories like textures/)
    image_files: list[Path] = []
    for f in folder.rglob("*"):
        if f.is_file() and f.suffix.lower() in IMAGE_EXTENSIONS:
            # Skip macOS resource fork files (._filename)
            if f.name.startswith("._"):
                continue
            image_files.append(f)

    # Find .blend file
    blend_files = [f for f in folder.iterdir() if f.is_file() and f.suffix.lower() == ".blend"]
    if blend_files:
        ts.blend_file = blend_files[0]

    # Find existing preview (AmbientCG includes a .png preview named after the material)
    for f in folder.iterdir():
        if f.is_file() and f.suffix.lower() == ".png" and "_" not in f.stem:
            ts.preview_image = f
            break

    # Load metadata from JSON if available (Megascans)
    json_files = [f for f in folder.iterdir() if f.is_file() and f.suffix == ".json"]
    for jf in json_files:
        try:
            with open(jf, "r") as fh:
                data = json.load(fh)
            ts.metadata = {
                "categories": data.get("categories", []),
                "tags": data.get("tags", []),
                "id": data.get("id", ""),
            }
        except (json.JSONDecodeError, OSError):
            pass

    # Classify each image into a map type
    for img in image_files:
        # Skip provider preview thumbnails (e.g. Asphalt015.png)
        if _is_preview_image(img, folder):
            # Still store it as the preview image if we don't have one
            if not ts.preview_image:
                ts.preview_image = img
            continue

        map_type = classify_map(img.name, source)

        # PolyHaven duplicates maps in textures/ subfolder — prefer root-level files
        if map_type != MapType.UNKNOWN:
            # Check if we already have this map type from a root-level file
            existing = ts.get_map(map_type)
            if existing and img.parent != folder and existing.path.parent == folder:
                continue  # Skip subfolder duplicate

        fmt = img.suffix.lstrip(".").lower()
        res = detect_resolution(img.stem) or resolution

        tm = TextureMap(path=img, map_type=map_type, resolution=res, format=fmt)
        if map_type != MapType.UNKNOWN:
            # Replace if this is root-level and existing was in subfolder
            existing = ts.get_map(map_type)
            if existing and existing.path.parent != folder and img.parent == folder:
                ts.maps.remove(existing)
            elif existing:
                continue  # Already have it, skip duplicate
        ts.maps.append(tm)

    return ts


def scan_library(library_path: Path) -> list[TextureSet]:
    """Scan the entire texture library and return all texture sets."""
    texture_sets: list[TextureSet] = []

    if not library_path.exists():
        raise FileNotFoundError(f"Texture library not found: {library_path}")

    for folder in sorted(library_path.iterdir()):
        if not folder.is_dir():
            continue
        ts = scan_folder(folder)
        texture_sets.append(ts)

    return texture_sets
