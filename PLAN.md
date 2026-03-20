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

**Status: Fully working with sphere/flat toggle, detail modal, and local server**

- [x] `gallery.py` — self-contained HTML with base64-embedded thumbnails (~18MB with both sphere + flat per card)
- [x] Both sphere (Blender PBR) and flat (albedo crop) thumbnails per card with toggle switch
- [x] Dark theme, responsive grid, search by name, filter by source & resolution
- [x] Detail modal with both previews, map list, source, resolutions, folder path
- [x] "Browse Files" — server-side directory listing with clickable image previews
- [x] "Open in Explorer" — opens texture folder in Windows Explorer via server API
- [x] `server.py` — localhost server (port 8271) serving gallery + browse + folder-open API
- [x] Port auto-fallback if 8271 is occupied; bat file auto-kills stale server

---

## Phase 3 — PBR Sphere Thumbnails ✅ DONE

**Status: Fully working with Blender 5.0**

- [x] `thumbnail.py` — Blender headless script: UV sphere + Principled BSDF + albedo/normal/roughness
- [x] Uses EEVEE render engine (compatible with Blender 5.0)
- [x] Caching (skips already-rendered .png thumbnails)
- [x] Pillow fallback generates flat .jpg crops when Blender isn't available
- [x] `Generate Thumbnails.bat` for one-click batch rendering
- [x] 188/190 materials have both sphere and flat thumbnails

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

### Tiling Preview — Options

Add a tiling preview to the gallery modal so you can see how a texture repeats and check for visible seams. Several approaches, from simplest to richest:

#### Option A: CSS tiling + zoom slider (easiest, no new deps)

Tile the flat albedo image using `background-image: repeat` in a div inside the modal. Add a range slider that adjusts `background-size` to zoom in/out (fewer/more repetitions visible). Click-drag to pan via CSS `background-position`.

- **Pros:** Zero dependencies, instant (no extra rendering), works on any image we already have, tiny amount of JS.
- **Cons:** Flat albedo only — no PBR lighting, no normal/roughness contribution. Purely a seam/pattern check.
- **Effort:** ~30 min. Add a `<div>` + slider + ~20 lines of JS to the gallery template.

#### Option B: Blender-rendered tiling plane (best quality, slow)

Add a second Blender render pass in `thumbnail.py`: a flat plane viewed top-down, tiled 3×3 or 4×4, with full PBR (albedo + normal + roughness). Cache as `{name}_tile.png` alongside the sphere `.png`.

- **Pros:** Full PBR tiling with correct lighting and surface detail. Consistent with the existing sphere workflow.
- **Cons:** Doubles the Blender render time (~2× thumbnail generation). Static image — not zoomable unless we render at high res. Large file per material.
- **Effort:** ~1 hour. Copy the sphere render script, swap the sphere for a subdivided plane, set UV tiling, aim camera straight down.

#### Option C: Three.js / WebGL live tiling (richest, heaviest)

Embed a small Three.js scene in the modal: a subdivided plane with the albedo, normal, and roughness maps loaded as textures, tiled via UV repeat. Mouse wheel zooms (adjusts tile count), click-drag orbits or pans.

- **Pros:** Full interactive PBR tiling that responds to zoom in real-time. Can rotate lighting. Most impressive UX.
- **Cons:** Adds Three.js as a dependency (~150KB gzipped CDN). Loading full-res textures per material on click is slow. Complex JS. The gallery HTML would need to link to the CDN or bundle Three.js.
- **Effort:** ~3–4 hours. Requires loading map files from the server on demand (not embedded in the HTML).

#### Option D: CSS tiling + Blender tile hybrid

Use Option A (CSS tiling with zoom) as the default quick preview. Optionally pre-render a tiled PBR plane via Blender (Option B) and show it as a static "Tiling (PBR)" tab in the modal when available.

- **Pros:** Best of both — instant CSS preview for seam checking, high-quality PBR tile when pre-rendered.
- **Cons:** Two preview systems to maintain. Doubles Blender render time if you want the PBR tiles.
- **Effort:** ~1.5 hours total.

**Recommendation:** Start with **Option A** (CSS tiling + zoom slider) — it's fast to build, zero dependencies, and covers the main use case (checking seams and tiling patterns). If PBR tiling becomes important later, add Option B renders on top.

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
│       ├── gallery.py               # HTML gallery generator
│       └── server.py                # Localhost gallery server with browse/Explorer API
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

1. **Phase 1 complete** — all core features (scan, gallery, thumbnails, server, Unity export) are working
2. **Phase 5 candidates** when needed:
   - Normal map DX→GL auto-flip for Megascans textures
   - Metallic+Smoothness RGBA packing for URP
   - Blender Asset Library bridge
   - Megascans JSON category tags in gallery search
