# AssetManager

Python CLI tool for managing a game dev texture library. Scans PBR texture sets from mixed sources (PolyHaven, AmbientCG, Megascans, etc.), generates sphere preview thumbnails, and exports Unity-ready material folders.

## Quick Start

```bash
# Install (from repo root)
pip install -e . --user

# Or just run directly without installing:
cd src
python -m asset_manager.cli scan

# Scan your library → writes output/catalog.json
assetmgr scan
# (or: python -m asset_manager.cli scan)

# Generate HTML gallery (works immediately, no Blender needed)
assetmgr gallery

# Generate PBR sphere thumbnails (requires Blender)
assetmgr thumbnails --blender "C:\Program Files\Blender Foundation\Blender 4.2\blender.exe"

# Re-generate gallery with thumbnails
assetmgr gallery

# Export a specific texture for Unity
assetmgr unity-export --name cobblestone

# Export everything
assetmgr unity-export
```

## Commands

| Command | What it does |
|---|---|
| `scan` | Index the texture library → `output/catalog.json` with map types, sources, metadata |
| `gallery` | Generate a self-contained `output/gallery.html` with search & filter |
| `thumbnails` | Render PBR sphere previews via Blender headless (cached — only renders new) |
| `unity-export` | Copy & rename maps into Unity-standard folders you can drop into `Assets/` |

## Configuration

Edit `config.yaml` to set your paths:

```yaml
paths:
  texture_library: "G:\\Gamedev\\asset library\\texture"
  output: "./output"
  blender: "C:\\Program Files\\Blender Foundation\\Blender 4.2\\blender.exe"
```

All commands accept `--path` and `--output` overrides.

## Supported Sources

The scanner auto-detects the texture provider and normalizes map naming:

| Source | Folder pattern | Map naming | Extras |
|---|---|---|---|
| PolyHaven | `name_4k.blend` | `_diff`, `_nor_gl`, `_rough`, `_disp` | `.blend` file included |
| AmbientCG | `Name_4K-JPG` | `_Color`, `_Roughness`, `_NormalGL` | Preview `.png`, `.blend`, `.usdc` |
| Megascans | `name_hashcode_4k` | `_BaseColor`, `_Normal`, `_Roughness` | `.json` metadata with categories |

## Unity Export

`unity-export` creates folders like:

```
output/unity/
├── Cobblestone_01/
│   ├── Cobblestone_01_Albedo.jpg
│   ├── Cobblestone_01_Normal.exr
│   ├── Cobblestone_01_Height.png
│   └── Cobblestone_01_Roughness.jpg
├── Castle_Wall/
│   ├── ...
```

These can be copied directly into your Unity project's `Assets/Textures/` folder. Unity imports them without complaint.

## Requirements

- Python 3.10+
- Blender (only for `thumbnails` command — everything else works without it)
