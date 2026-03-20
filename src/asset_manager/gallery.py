"""Generate an HTML thumbnail gallery for browsing the texture catalog."""

from __future__ import annotations

import base64
from pathlib import Path

from .models import MapType, TextureSet

GALLERY_TEMPLATE = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Texture Library</title>
<style>
  :root {
    --bg: #1a1a2e;
    --card-bg: #16213e;
    --text: #e0e0e0;
    --accent: #0f3460;
    --hover: #533483;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    font-family: system-ui, -apple-system, sans-serif;
    background: var(--bg);
    color: var(--text);
    padding: 1.5rem;
  }
  h1 { margin-bottom: 0.5rem; font-size: 1.5rem; }
  .stats { color: #888; margin-bottom: 1.5rem; font-size: 0.9rem; }
  .controls {
    display: flex;
    gap: 1rem;
    margin-bottom: 1.5rem;
    flex-wrap: wrap;
  }
  .controls input, .controls select {
    padding: 0.5rem 0.75rem;
    border: 1px solid #333;
    border-radius: 6px;
    background: var(--card-bg);
    color: var(--text);
    font-size: 0.9rem;
  }
  .controls input { flex: 1; min-width: 200px; }
  .grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
    gap: 1rem;
  }
  .card {
    background: var(--card-bg);
    border-radius: 8px;
    overflow: hidden;
    transition: transform 0.15s, box-shadow 0.15s;
    cursor: default;
  }
  .card:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 20px rgba(0,0,0,0.4);
  }
  .thumb {
    width: 100%;
    aspect-ratio: 1;
    object-fit: cover;
    background: #111;
    display: block;
  }
  .thumb.placeholder {
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 2rem;
    color: #555;
  }
  .info {
    padding: 0.6rem 0.75rem;
  }
  .info .name {
    font-size: 0.8rem;
    font-weight: 600;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .info .meta {
    font-size: 0.7rem;
    color: #888;
    margin-top: 0.25rem;
  }
  .badge {
    display: inline-block;
    padding: 0.1rem 0.4rem;
    border-radius: 3px;
    font-size: 0.65rem;
    margin-right: 0.3rem;
  }
  .badge.polyhaven { background: #2d6a4f; }
  .badge.ambientcg { background: #b56727; }
  .badge.megascans { background: #3a5a9c; }
  .badge.unknown { background: #555; }
  .res-tags {
    display: flex;
    gap: 0.25rem;
    margin-top: 0.3rem;
    flex-wrap: wrap;
  }
  .res-tag {
    display: inline-block;
    padding: 0.1rem 0.35rem;
    border-radius: 3px;
    font-size: 0.6rem;
    font-weight: 600;
    background: #2a2a4a;
    color: #aaa;
    border: 1px solid #3a3a5a;
  }
  .res-tag.active {
    background: #1a3a5a;
    color: #7cb3e0;
    border-color: #4a7aaa;
  }
  .hidden { display: none; }
</style>
</head>
<body>
<h1>Texture Library</h1>
<div class="stats">{{ total }} materials ({{ sets_total }} texture sets) | {{ sources_summary }}</div>
<div class="controls">
  <input type="text" id="search" placeholder="Filter by name..." autocomplete="off">
  <select id="source-filter">
    <option value="">All sources</option>
    <option value="polyhaven">PolyHaven</option>
    <option value="ambientcg">AmbientCG</option>
    <option value="megascans">Megascans</option>
    <option value="unknown">Other</option>
  </select>
  <select id="res-filter">
    <option value="">All resolutions</option>
    <option value="1K">1K</option>
    <option value="2K">2K</option>
    <option value="4K">4K</option>
    <option value="8K">8K</option>
  </select>
</div>
<div class="grid" id="gallery">
{{ cards }}
</div>
<script>
const search = document.getElementById("search");
const sourceFilter = document.getElementById("source-filter");
const resFilter = document.getElementById("res-filter");
const cards = document.querySelectorAll(".card");
function filterCards() {
  const q = search.value.toLowerCase();
  const src = sourceFilter.value;
  const res = resFilter.value;
  cards.forEach(c => {
    const name = c.dataset.name;
    const csrc = c.dataset.source;
    const cres = c.dataset.resolutions || "";
    const show = name.includes(q)
      && (!src || csrc === src)
      && (!res || cres.includes(res));
    c.classList.toggle("hidden", !show);
  });
}
search.addEventListener("input", filterCards);
sourceFilter.addEventListener("change", filterCards);
resFilter.addEventListener("change", filterCards);
</script>
</body>
</html>
"""


def _thumbnail_src(texture_set: TextureSet, thumbnails_dir: Path | None) -> str:
    """Get thumbnail as an embedded base64 data URI."""
    thumb_path = None

    # 1. Check for a rendered/cached thumbnail (Blender or Pillow-generated)
    #    Prefer .png (Blender renders) over .jpg (Pillow crops)
    if thumbnails_dir:
        for ext in (".png", ".jpg"):
            candidate = thumbnails_dir / f"{texture_set.folder.name}{ext}"
            if candidate.exists():
                thumb_path = candidate
                break

    # 2. Auto-generate a quick thumbnail from the albedo map using Pillow
    if not thumb_path and thumbnails_dir:
        thumb_path = _generate_quick_thumbnail(texture_set, thumbnails_dir)

    # 3. Fall back to provider-supplied preview — resize it to a small thumbnail first
    if not thumb_path and texture_set.preview_image and texture_set.preview_image.exists():
        if thumbnails_dir:
            thumb_path = _resize_preview(texture_set.preview_image, texture_set.folder.name, thumbnails_dir)
        if not thumb_path:
            thumb_path = texture_set.preview_image

    if thumb_path:
        # Embed as base64 data URI — thumbnails are small (~10-30KB) so this is fine
        data = thumb_path.read_bytes()
        b64 = base64.b64encode(data).decode("ascii")
        mime = "image/png" if thumb_path.suffix.lower() == ".png" else "image/jpeg"
        return f'<img class="thumb" src="data:{mime};base64,{b64}" alt="{texture_set.name}" loading="lazy">'

    return '<div class="thumb placeholder">\U0001f3a8</div>'


def _generate_quick_thumbnail(texture_set: TextureSet, thumbnails_dir: Path) -> Path | None:
    """Create a small center-cropped thumbnail from the albedo map using Pillow."""
    albedo = texture_set.get_map(MapType.ALBEDO)
    if not albedo or not albedo.path.exists():
        return None

    # Skip EXR — Pillow can't read those without extra plugins
    if albedo.format in ("exr",):
        return None

    out_path = thumbnails_dir / f"{texture_set.folder.name}.jpg"
    if out_path.exists():
        return out_path

    try:
        from PIL import Image
        thumbnails_dir.mkdir(parents=True, exist_ok=True)
        with Image.open(albedo.path) as img:
            # Center crop to square
            w, h = img.size
            side = min(w, h)
            left = (w - side) // 2
            top = (h - side) // 2
            cropped = img.crop((left, top, left + side, top + side))
            cropped.thumbnail((256, 256), Image.LANCZOS)
            cropped = cropped.convert("RGB")  # JPEG needs RGB
            cropped.save(out_path, "JPEG", quality=80)
        return out_path
    except Exception:
        return None


def _resize_preview(preview_path: Path, folder_name: str, thumbnails_dir: Path) -> Path | None:
    """Resize a provider preview image to thumbnail size and cache it."""
    out_path = thumbnails_dir / f"{folder_name}.jpg"
    if out_path.exists():
        return out_path
    try:
        from PIL import Image
        thumbnails_dir.mkdir(parents=True, exist_ok=True)
        with Image.open(preview_path) as img:
            img.thumbnail((256, 256), Image.LANCZOS)
            img = img.convert("RGB")
            img.save(out_path, "JPEG", quality=80)
        return out_path
    except Exception:
        return None


def generate_gallery(
    texture_sets: list[TextureSet],
    output_path: Path,
    thumbnails_dir: Path | None = None,
) -> Path:
    """Generate a self-contained HTML gallery file."""
    from collections import Counter, defaultdict

    source_counts = Counter(ts.source.value for ts in texture_sets)
    sources_summary = " | ".join(f"{v}: {c}" for v, c in sorted(source_counts.items()))

    # Group texture sets by material name (strips resolution)
    groups: dict[str, list[TextureSet]] = defaultdict(list)
    for ts in texture_sets:
        groups[ts.name].append(ts)

    # Sort resolutions in a sensible order
    RES_ORDER = {"1K": 1, "2K": 2, "4K": 4, "8K": 8}

    cards_html = []
    for name in sorted(groups.keys(), key=str.lower):
        variants = groups[name]
        # Sort by resolution (highest first for thumbnail)
        variants.sort(key=lambda ts: RES_ORDER.get(ts.resolution, 0), reverse=True)

        # Use the highest-res variant for the thumbnail and source info
        best = variants[0]

        # Collect unique resolutions across all variants
        resolutions = sorted(
            set(ts.resolution for ts in variants if ts.resolution),
            key=lambda r: RES_ORDER.get(r, 0),
        )

        # Collect all unique map types across all resolution variants
        all_map_types = set()
        for ts in variants:
            for m in ts.maps:
                if m.map_type.name != "UNKNOWN":
                    all_map_types.add(m.map_type.value)
        map_list = ", ".join(sorted(all_map_types))

        thumb = _thumbnail_src(best, thumbnails_dir)

        # Build resolution tags
        res_tags = ""
        if resolutions:
            tags = [f'<span class="res-tag">{r}</span>' for r in resolutions]
            res_tags = f'<div class="res-tags">{" ".join(tags)}</div>'

        res_data = ",".join(resolutions)  # for filtering

        cards_html.append(
            f'<div class="card" data-name="{name.lower()}" '
            f'data-source="{best.source.value}" data-resolutions="{res_data}">'
            f'{thumb}'
            f'<div class="info">'
            f'<div class="name" title="{name}">{name}</div>'
            f'<div class="meta">'
            f'<span class="badge {best.source.value}">{best.source.value}</span>'
            f'{map_list}'
            f'</div>'
            f'{res_tags}'
            f'</div></div>'
        )

    html = GALLERY_TEMPLATE.replace("{{ total }}", str(len(groups)))
    html = html.replace("{{ sets_total }}", str(len(texture_sets)))
    html = html.replace("{{ sources_summary }}", sources_summary)
    html = html.replace("{{ cards }}", "\n".join(cards_html))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8")
    return output_path
