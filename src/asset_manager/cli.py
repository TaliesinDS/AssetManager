"""CLI entry point for the Asset Manager tools."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .config import load_config
from .scanner import scan_library


def cmd_scan(args: argparse.Namespace, config: dict) -> None:
    """Scan the texture library and output a catalog."""
    lib_path = Path(args.path or config["paths"]["texture_library"])
    output_dir = Path(args.output or config["paths"]["output"])
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Scanning: {lib_path}")
    texture_sets = scan_library(lib_path)
    print(f"Found {len(texture_sets)} texture sets\n")

    # Print summary
    from collections import Counter
    sources = Counter(ts.source.value for ts in texture_sets)
    for src, count in sorted(sources.items()):
        print(f"  {src}: {count}")
    print()

    # Count map types
    map_counts = Counter()
    for ts in texture_sets:
        for m in ts.maps:
            map_counts[m.map_type.value] += 1
    print("Map types found:")
    for mt, count in sorted(map_counts.items(), key=lambda x: -x[1]):
        print(f"  {mt}: {count}")
    print()

    # Write catalog JSON
    catalog_path = output_dir / "catalog.json"
    catalog = [ts.to_dict() for ts in texture_sets]
    with open(catalog_path, "w") as f:
        json.dump(catalog, f, indent=2)
    print(f"Catalog written to: {catalog_path}")

    # Warn about texture sets with no albedo
    no_albedo = [ts for ts in texture_sets if not ts.has_albedo]
    if no_albedo:
        print(f"\n[WARN] {len(no_albedo)} sets have no albedo/diffuse/color map:")
        for ts in no_albedo:
            print(f"  - {ts.name} ({ts.folder.name})")


def cmd_gallery(args: argparse.Namespace, config: dict) -> None:
    """Generate an HTML thumbnail gallery."""
    lib_path = Path(args.path or config["paths"]["texture_library"])
    output_dir = Path(args.output or config["paths"]["output"])

    print(f"Scanning: {lib_path}")
    texture_sets = scan_library(lib_path)

    thumbnails_dir = output_dir / "thumbnails"
    gallery_path = output_dir / "gallery.html"

    from .gallery import generate_gallery
    generate_gallery(texture_sets, gallery_path, thumbnails_dir)
    print(f"Gallery written to: {gallery_path}")


def cmd_thumbnails(args: argparse.Namespace, config: dict) -> None:
    """Generate PBR sphere preview thumbnails via Blender."""
    lib_path = Path(args.path or config["paths"]["texture_library"])
    output_dir = Path(args.output or config["paths"]["output"])
    thumbnails_dir = output_dir / "thumbnails"

    blender_path = args.blender or config["paths"].get("blender", "blender")
    size = args.size or config.get("thumbnail", {}).get("size", 256)

    print(f"Scanning: {lib_path}")
    texture_sets = scan_library(lib_path)

    from .thumbnail import generate_all_thumbnails
    print(f"\nGenerating {size}x{size} thumbnails using: {blender_path}")
    results = generate_all_thumbnails(texture_sets, thumbnails_dir, blender_path, size)
    print(f"\nGenerated {len(results)} thumbnails in: {thumbnails_dir}")


def cmd_unity_export(args: argparse.Namespace, config: dict) -> None:
    """Export texture sets as Unity-ready folders."""
    lib_path = Path(args.path or config["paths"]["texture_library"])
    output_dir = Path(args.output or config["paths"]["output"]) / "unity"

    print(f"Scanning: {lib_path}")
    texture_sets = scan_library(lib_path)

    # Filter if a specific texture was requested
    if args.name:
        query = args.name.lower()
        texture_sets = [ts for ts in texture_sets if query in ts.name.lower() or query in ts.folder.name.lower()]
        if not texture_sets:
            print(f"No texture sets matching '{args.name}'")
            sys.exit(1)
        print(f"Matched {len(texture_sets)} texture sets")

    from .unity_export import export_all_for_unity
    results = export_all_for_unity(texture_sets, output_dir, include_all_maps=args.all_maps)
    print(f"\nExported {len(results)} materials to: {output_dir}")
    print("You can copy any of these folders directly into your Unity project's Assets/ folder.")


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="assetmgr",
        description="Texture library scanner, thumbnail generator, and Unity export tool",
    )
    parser.add_argument("--config", type=str, help="Path to config.yaml")
    parser.add_argument("--path", type=str, help="Override texture library path")
    parser.add_argument("--output", type=str, help="Output directory (default: from config.yaml)")

    subparsers = parser.add_subparsers(dest="command", required=True)

    # scan
    subparsers.add_parser("scan", help="Scan texture library and generate catalog.json")

    # gallery
    subparsers.add_parser("gallery", help="Generate HTML thumbnail gallery")

    # thumbnails
    thumb_parser = subparsers.add_parser("thumbnails", help="Generate PBR sphere preview thumbnails")
    thumb_parser.add_argument("--blender", type=str, help="Path to Blender executable")
    thumb_parser.add_argument("--size", type=int, help="Thumbnail size in pixels")

    # unity-export
    unity_parser = subparsers.add_parser("unity-export", help="Export textures as Unity-ready folders")
    unity_parser.add_argument("--name", type=str, help="Export only textures matching this name")
    unity_parser.add_argument("--all-maps", action="store_true", help="Include all map types, not just Unity essentials")

    args = parser.parse_args()
    config_path = Path(args.config) if args.config else None
    config = load_config(config_path)

    commands = {
        "scan": cmd_scan,
        "gallery": cmd_gallery,
        "thumbnails": cmd_thumbnails,
        "unity-export": cmd_unity_export,
    }
    commands[args.command](args, config)


if __name__ == "__main__":
    main()
