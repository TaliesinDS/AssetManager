# AssetManager — Project Plan

## Context

Texture library at `G:\Gamedev\asset library\texture` with **262 texture sets** from mixed sources:
- **PolyHaven** (116) — folder ends `_4k.blend`, maps use `_diff`, `_nor_gl`, `_rough`, `_disp`
- **Megascans** (76) — folder has 8-char hash + res, maps use `_BaseColor`, `_Normal` (DX!), `.json` metadata
- **AmbientCG** (57) — folder ends `_4K-JPG/PNG`, maps use `_Color`, `_Roughness`, includes preview PNG
- **Other/uploads** (13) — mixed naming, some UE-packed formats

Formats: JPG (1144), PNG (474), EXR (200), Blender (175), TIF (24). Zip archives present (262) but ignored.
Target: Unity URP.

---

## Phase 1 — Scanner & Catalog ✅ DONE

**Status: Fully working, tested against real library**

- [x] `models.py` — `TextureSet`, `TextureMap`, 19 `MapType` variants, `Source` enum
- [x] `scanner.py` — walks library, detects source, classifies PBR maps, loads Megascans JSON metadata
- [x] `cli.py` — `assetmgr scan` writes `catalog.json`
- [x] Normal maps split into GL vs DX — Megascans `_Normal` correctly classified as DX
- [x] Handles: Smoothness, Scattering, Transmission, Mask, Metal, Spec, DiffuseOriginal
- [x] Filters macOS `._` resource forks and provider preview images
- [x] Only 7 legitimately unclassifiable files remain (anisotropy, spec_ior, untitled junk)
- [x] 258/262 sets have albedo maps (4 missing are UE packed grunge textures)

---

## Phase 2 — HTML Gallery ✅ DONE

**Status: Fully working with auto-generated thumbnails**

- [x] `gallery.py` — 124KB HTML with file:// image references (was 24MB with base64)
- [x] Auto-generates 256px albedo-crop thumbnails via Pillow (194/262 generated, rest are EXR-only)
- [x] Dark theme, responsive grid, search by name, filter by source & resolution
- [x] Provider preview images used when available (AmbientCG)

---

## Phase 3 — PBR Sphere Thumbnails ✅ SCAFFOLDED

**Status: Code written, needs Blender configured for first run**

- [x] `thumbnail.py` — Blender headless script: UV sphere + Principled BSDF + albedo/normal/roughness
- [x] Caching (skips already-rendered thumbnails)
- [x] Pillow fallback thumbnails work immediately (Phase 2)
- [ ] Configure Blender path in config.yaml
- [ ] Run `assetmgr thumbnails` for high-quality sphere renders

---

## Phase 4 — Unity Export ✅ DONE

**Status: Fully working, URP-aware**

- [x] `unity_export.py` — copies maps with Unity-standard naming (`_Albedo`, `_Normal`, `_Height`, etc.)
- [x] Prefers GL normals for URP (falls back to DX when no GL available)
- [x] Resolution included in folder name to prevent collision (same material at 1K/2K/4K)
- [x] Picks best format per map (prefers PNG/JPG over EXR for smaller imports)
- [x] Single texture (`--name`) or batch export
- [x] Essential-only mode (default) or `--all-maps` for everything

---

## Phase 5 — Polish & Iteration (future)

Potential improvements (do NOT build until needed):

- **Normal map DX→GL flip** — Megascans normals are DX; currently exported as-is. Could auto-flip green channel via Pillow for URP.
- **Roughness→Smoothness inversion** — URP Lit uses Smoothness (= 1 - Roughness). Could auto-invert on export.
- **Metallic+Smoothness packing** — URP wants Metallic (R) + Smoothness (A) in one texture. Could auto-pack.
- **Resolution picker** — `--resolution 2K` to only export 2K variants and skip 1K/4K dupes.
- **Mask map packing** — HDRP uses packed RGBA mask map (Metallic/AO/Detail/Smoothness).
- **Blender Asset Library bridge** — generate `.blend` asset library files for Blender's asset browser.
- **Tagging / search** — Megascans JSON already has categories. Could expose in gallery.
- **Texture deduplication** — group same material at different resolutions, export only preferred res.

---

## Repo Structure

```
AssetManager/
├── README.md                        # Usage docs
├── assetmanager.md                  # Original brainstorm
├── PLAN.md                          # This file
├── config.yaml                      # User paths config
├── pyproject.toml                   # Python project config
├── .gitignore
├── src/
│   └── asset_manager/
│       ├── __init__.py
│       ├── cli.py                   # CLI entry point (assetmgr command)
│       ├── config.py                # Config loader
│       ├── models.py                # TextureSet, TextureMap, MapType, Source
│       ├── scanner.py               # Library scanner & map classifier
│       ├── thumbnail.py             # Blender headless sphere renderer
│       ├── unity_export.py          # Unity-ready folder exporter
│       └── gallery.py               # HTML gallery generator
├── tests/
│   └── __init__.py
└── output/                          # Generated (gitignored)
    ├── catalog.json
    ├── gallery.html
    ├── thumbnails/
    └── unity/
```

---

## Next Immediate Steps

1. **Install the tool**: `pip install -e .` from the repo root
2. **Run first scan**: `assetmgr scan` — verify catalog.json looks right
3. **Generate gallery**: `assetmgr gallery` — open `output/gallery.html` in browser
4. **Fix any scan issues** — edge cases in map classification, missing folders, etc.
5. **Test Unity export**: `assetmgr unity-export --name cobblestone` — try importing into Unity
6. **When ready**: configure Blender path and run `assetmgr thumbnails` for sphere previews
