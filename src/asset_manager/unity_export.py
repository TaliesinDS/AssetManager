"""Export texture sets into Unity-ready folder structures."""

from __future__ import annotations

import shutil
from pathlib import Path

from .models import MapType, TextureMap, TextureSet

# Unity URP conventional map suffixes
UNITY_MAP_NAMES: dict[MapType, str] = {
    MapType.ALBEDO: "_Albedo",
    MapType.NORMAL_GL: "_Normal",
    MapType.NORMAL_DX: "_Normal",  # same output name — we just prefer GL source
    MapType.HEIGHT: "_Height",
    MapType.ROUGHNESS: "_Roughness",
    MapType.SMOOTHNESS: "_Smoothness",
    MapType.AO: "_AO",
    MapType.METALLIC: "_Metallic",
    MapType.OPACITY: "_Opacity",
    MapType.SPECULAR: "_Specular",
    MapType.GLOSS: "_Gloss",
    MapType.BUMP: "_Bump",
    MapType.CAVITY: "_Cavity",
    MapType.EMISSIVE: "_Emissive",
    MapType.SCATTERING: "_Scattering",
    MapType.TRANSMISSION: "_Transmission",
    MapType.PACKED_MR: "_MaskMap",
}

# Map types that URP Lit shader actually uses
UNITY_ESSENTIAL_MAPS = {
    MapType.ALBEDO,
    MapType.NORMAL_GL,
    MapType.NORMAL_DX,
    MapType.HEIGHT,
    MapType.AO,
    MapType.METALLIC,
    MapType.ROUGHNESS,
    MapType.SMOOTHNESS,
    MapType.OPACITY,
    MapType.EMISSIVE,
}

# Preferred format priority for Unity (avoid EXR bloat when possible)
FORMAT_PREFERENCE = ["png", "jpg", "jpeg", "tif", "tiff", "exr", "tga"]


def pick_best_map(texture_set: TextureSet, map_type: MapType) -> TextureMap | None:
    """Pick the best version of a map type (prefer smaller formats, right resolution)."""
    candidates = [m for m in texture_set.maps if m.map_type == map_type]
    if not candidates:
        return None
    if len(candidates) == 1:
        return candidates[0]

    # Sort by format preference
    def sort_key(m: TextureMap) -> int:
        try:
            return FORMAT_PREFERENCE.index(m.format)
        except ValueError:
            return 99

    candidates.sort(key=sort_key)
    return candidates[0]


def export_for_unity(
    texture_set: TextureSet,
    output_dir: Path,
    include_all_maps: bool = False,
) -> Path | None:
    """Copy a texture set into a Unity-ready folder.

    Creates:  output_dir/MaterialName/MaterialName_Albedo.png, etc.

    Args:
        texture_set: The scanned texture set to export.
        output_dir: Root output directory. A subfolder is created per material.
        include_all_maps: If False, only copy maps Unity shaders commonly use.

    Returns:
        Path to the exported folder, or None if no maps to export.
    """
    # Clean name for the Unity folder (PascalCase-ish, no spaces)
    clean_name = texture_set.name.replace(" ", "_").title().replace(" ", "")
    # Keep it filesystem safe
    clean_name = "".join(c for c in clean_name if c.isalnum() or c == "_")
    # Append resolution to avoid collisions (same material at different res)
    if texture_set.resolution:
        clean_name = f"{clean_name}_{texture_set.resolution}"

    mat_dir = output_dir / clean_name
    mat_dir.mkdir(parents=True, exist_ok=True)

    allowed_types = None if include_all_maps else UNITY_ESSENTIAL_MAPS
    exported_count = 0
    exported_normal = False

    for map_type in MapType:
        if map_type == MapType.UNKNOWN:
            continue
        if allowed_types and map_type not in allowed_types:
            continue

        # For normals, prefer GL (URP) and skip DX if we already have GL
        if map_type == MapType.NORMAL_DX and exported_normal:
            continue
        if map_type == MapType.NORMAL_DX:
            # Use DX only as fallback when no GL normal exists
            gl = pick_best_map(texture_set, MapType.NORMAL_GL)
            if gl:
                continue

        best = pick_best_map(texture_set, map_type)
        if not best:
            continue

        if map_type in (MapType.NORMAL_GL, MapType.NORMAL_DX):
            exported_normal = True

        unity_suffix = UNITY_MAP_NAMES.get(map_type, f"_{map_type.value}")
        dest_name = f"{clean_name}{unity_suffix}{best.path.suffix}"
        dest_path = mat_dir / dest_name

        if not dest_path.exists():
            shutil.copy2(best.path, dest_path)
        exported_count += 1

    return mat_dir if exported_count > 0 else None


def export_all_for_unity(
    texture_sets: list[TextureSet],
    output_dir: Path,
    include_all_maps: bool = False,
) -> list[Path]:
    """Export all texture sets for Unity. Returns list of exported folder paths."""
    output_dir.mkdir(parents=True, exist_ok=True)
    results: list[Path] = []
    total = len(texture_sets)

    for i, ts in enumerate(texture_sets, 1):
        print(f"  [{i}/{total}] Exporting {ts.name}...")
        result = export_for_unity(ts, output_dir, include_all_maps)
        if result:
            results.append(result)

    return results
