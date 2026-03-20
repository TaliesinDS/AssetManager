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
    --bg: #3a3a3a;
    --card-bg: #303030;
    --text: #e0e0e0;
    --accent: #4a4a4a;
    --hover: #555555;
    --modal-bg: #2a2a2a;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    font-family: system-ui, -apple-system, sans-serif;
    background: var(--bg);
    color: var(--text);
    padding: 1.5rem;
  }
  h1 { margin-bottom: 0.5rem; font-size: 1.5rem; }
  .stats { color: #999; margin-bottom: 1.5rem; font-size: 0.9rem; }
  .controls {
    display: flex;
    gap: 1rem;
    margin-bottom: 1.5rem;
    flex-wrap: wrap;
    align-items: center;
  }
  .controls input, .controls select {
    padding: 0.5rem 0.75rem;
    border: 1px solid #555;
    border-radius: 6px;
    background: var(--card-bg);
    color: var(--text);
    font-size: 0.9rem;
  }
  .controls input { flex: 1; min-width: 200px; }

  /* Toggle switch */
  .toggle-group {
    display: flex;
    border: 1px solid #555;
    border-radius: 6px;
    overflow: hidden;
    font-size: 0.8rem;
  }
  .toggle-btn {
    padding: 0.45rem 0.75rem;
    background: var(--card-bg);
    color: #888;
    border: none;
    cursor: pointer;
    transition: background 0.15s, color 0.15s;
  }
  .toggle-btn.active {
    background: var(--accent);
    color: var(--text);
  }
  .toggle-btn:hover:not(.active) { background: #444; }

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
    cursor: pointer;
  }
  .card:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 20px rgba(0,0,0,0.4);
  }
  .thumb-wrap {
    position: relative;
    width: 100%;
    aspect-ratio: 1;
    background: #252525;
  }
  .thumb-wrap img {
    position: absolute;
    top: 0; left: 0;
    width: 100%;
    height: 100%;
    object-fit: cover;
    transition: opacity 0.2s;
  }
  .thumb-wrap img.hidden-thumb { opacity: 0; }
  .thumb-wrap .placeholder {
    width: 100%;
    height: 100%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 2rem;
    color: #888;
  }
  .info { padding: 0.6rem 0.75rem; }
  .info .name {
    font-size: 0.8rem;
    font-weight: 600;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .info .meta {
    font-size: 0.7rem;
    color: #999;
    margin-top: 0.25rem;
  }
  .badge {
    display: inline-block;
    padding: 0.1rem 0.4rem;
    border-radius: 3px;
    font-size: 0.65rem;
    margin-right: 0.3rem;
  }
  .badge.polyhaven { background: #4a4a4a; }
  .badge.ambientcg { background: #4a4a4a; }
  .badge.megascans { background: #4a4a4a; }
  .badge.unknown { background: #4a4a4a; }
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
    background: #444;
    color: #aaa;
    border: 1px solid #555;
  }
  .hidden { display: none; }

  /* Modal */
  .modal-overlay {
    display: none;
    position: fixed;
    inset: 0;
    background: rgba(0,0,0,0.75);
    z-index: 1000;
    justify-content: center;
    align-items: center;
    padding: 2rem;
  }
  .modal-overlay.open { display: flex; }
  .modal {
    background: var(--modal-bg);
    border-radius: 12px;
    max-width: 750px;
    width: 100%;
    max-height: 90vh;
    overflow-y: auto;
    padding: 1.5rem;
    position: relative;
  }
  .modal-close {
    position: absolute;
    top: 0.75rem;
    right: 1rem;
    background: none;
    border: none;
    color: #888;
    font-size: 1.5rem;
    cursor: pointer;
  }
  .modal-close:hover { color: var(--text); }
  .modal-previews {
    display: flex;
    gap: 1rem;
    margin-bottom: 1.25rem;
    justify-content: center;
    flex-wrap: wrap;
  }
  .modal-preview-box {
    text-align: center;
  }
  .modal-preview-box img {
    width: 280px;
    height: 280px;
    object-fit: cover;
    border-radius: 8px;
    background: #252525;
    display: block;
  }
  .modal-preview-box .label {
    font-size: 0.75rem;
    color: #888;
    margin-top: 0.4rem;
  }
  .modal h2 {
    font-size: 1.2rem;
    margin-bottom: 0.75rem;
  }
  .modal-detail {
    display: grid;
    grid-template-columns: auto 1fr;
    gap: 0.3rem 1rem;
    font-size: 0.85rem;
    margin-bottom: 1rem;
  }
  .modal-detail dt { color: #888; }
  .modal-detail dd { color: var(--text); }
  .modal-maps {
    display: flex;
    flex-wrap: wrap;
    gap: 0.3rem;
    margin-bottom: 1rem;
  }
  .modal-maps .map-badge {
    padding: 0.2rem 0.5rem;
    border-radius: 4px;
    font-size: 0.7rem;
    background: #3a3a3a;
    border: 1px solid #555;
    color: #aaa;
  }
  .btn {
    display: inline-block;
    padding: 0.5rem 1rem;
    border-radius: 6px;
    border: 1px solid #555;
    background: var(--accent);
    color: var(--text);
    font-size: 0.85rem;
    cursor: pointer;
    text-decoration: none;
    transition: background 0.15s;
  }
  .btn:hover { background: #555; }
  .btn + .btn { margin-left: 0.5rem; }
  .modal-res-tags {
    display: flex;
    gap: 0.3rem;
    margin-bottom: 1rem;
  }
  .modal-res-tag {
    padding: 0.25rem 0.6rem;
    border-radius: 4px;
    font-size: 0.75rem;
    font-weight: 600;
    background: #444;
    color: #aaa;
    border: 1px solid #555;
    cursor: pointer;
    transition: background 0.15s, color 0.15s, border-color 0.15s;
  }
  .modal-res-tag:hover { background: #555; color: var(--text); }
  .modal-res-tag.active {
    background: #666;
    color: var(--text);
    border-color: #999;
  }
  .folder-path {
    font-size: 0.75rem;
    color: #666;
    margin-top: 0.5rem;
    word-break: break-all;
  }
  .explorer-status {
    font-size: 0.75rem;
    color: #888;
    transition: opacity 0.3s;
  }
  /* Tiling preview */
  .tile-section { margin-bottom: 1.25rem; }
  .tile-section .label {
    font-size: 0.75rem;
    color: #888;
    margin-bottom: 0.4rem;
    display: flex;
    align-items: center;
    gap: 0.75rem;
  }
  .tile-section .label input[type=range] {
    width: 120px;
    accent-color: #999;
  }
  .tile-box {
    width: 100%;
    height: 280px;
    border-radius: 8px;
    background-color: #252525;
    background-repeat: repeat;
    background-size: 50% auto;
    cursor: grab;
    overflow: hidden;
  }
  .tile-box:active { cursor: grabbing; }
</style>
</head>
<body>
<h1>Texture Library</h1>
<div class="stats">{{ total }} materials ({{ sets_total }} texture sets) | {{ sources_summary }}</div>
<div class="controls">
  <input type="text" id="search" placeholder="Filter by name..." autocomplete="off">
  <div class="toggle-group">
    <button class="toggle-btn active" data-mode="sphere">Sphere</button>
    <button class="toggle-btn" data-mode="flat">Flat</button>
  </div>
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

<!-- Detail modal -->
<div class="modal-overlay" id="modal-overlay">
  <div class="modal" id="modal">
    <button class="modal-close" id="modal-close">&times;</button>
    <h2 id="modal-title"></h2>
    <div class="modal-previews">
      <div class="modal-preview-box">
        <img id="modal-sphere" src="" alt="Sphere preview">
        <div class="label">Sphere</div>
      </div>
      <div class="modal-preview-box">
        <img id="modal-flat" src="" alt="Flat preview">
        <div class="label">Flat</div>
      </div>
    </div>
    <div class="tile-section">
      <div class="label">Tiling <input type="range" id="tile-zoom" min="10" max="200" value="50"> <span id="tile-zoom-label">2×2</span></div>
      <div class="tile-box" id="tile-box"></div>
    </div>
    <div class="modal-res-tags" id="modal-res-tags"></div>
    <dl class="modal-detail" id="modal-detail"></dl>
    <div class="modal-maps" id="modal-maps"></div>
    <div style="display:flex;gap:0.5rem;flex-wrap:wrap;align-items:center">
      <a class="btn" id="modal-open-folder" href="#">Browse files</a>
      <button class="btn" id="modal-open-explorer">Open in Explorer</button>
      <span class="explorer-status" id="explorer-status"></span>
    </div>
    <div class="folder-path" id="modal-folder-path"></div>
  </div>
</div>

<script>
const search = document.getElementById("search");
const sourceFilter = document.getElementById("source-filter");
const resFilter = document.getElementById("res-filter");
const cards = document.querySelectorAll(".card");

// --- Filtering ---
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

// --- Flat / Sphere toggle ---
let currentMode = "sphere";
const toggleBtns = document.querySelectorAll(".toggle-btn");
toggleBtns.forEach(btn => {
  btn.addEventListener("click", () => {
    currentMode = btn.dataset.mode;
    toggleBtns.forEach(b => b.classList.toggle("active", b === btn));
    cards.forEach(c => {
      const sphere = c.querySelector(".thumb-sphere");
      const flat = c.querySelector(".thumb-flat");
      if (sphere && flat) {
        sphere.classList.toggle("hidden-thumb", currentMode !== "sphere");
        flat.classList.toggle("hidden-thumb", currentMode !== "flat");
      }
    });
  });
});

// --- Modal ---
const overlay = document.getElementById("modal-overlay");
const modal = document.getElementById("modal");
const modalClose = document.getElementById("modal-close");

cards.forEach(c => {
  c.addEventListener("click", () => {
    document.getElementById("modal-title").textContent = c.dataset.displayName;
    // Previews
    const sphere = c.querySelector(".thumb-sphere");
    const flat = c.querySelector(".thumb-flat");
    document.getElementById("modal-sphere").src = sphere ? sphere.src : "";
    document.getElementById("modal-flat").src = flat ? flat.src : "";
    // Tiling preview — use flat albedo
    const tileSrc = flat ? flat.src : (sphere ? sphere.src : "");
    tileBox.style.backgroundImage = tileSrc ? "url(" + tileSrc + ")" : "none";
    tileZoom.value = 50;
    tileBgPos = [0, 0];
    tileBox.style.backgroundPosition = "0px 0px";
    updateTile();
    // Resolution tags — clickable to switch folder
    const resFolders = JSON.parse(c.dataset.resFolders || "{}");
    const resTagsDiv = document.getElementById("modal-res-tags");
    const resList = (c.dataset.resolutions || "").split(",").filter(Boolean);
    const resOrder = {"1K":1,"2K":2,"4K":4,"8K":8};
    const defaultRes = resList.length ? resList.reduce((a,b) => (resOrder[b]||0) > (resOrder[a]||0) ? b : a) : "";
    function selectRes(res) {
      const folder = resFolders[res] || c.dataset.folder;
      currentFolder = folder;
      document.getElementById("modal-open-folder").href = "/browse?path=" + encodeURIComponent(folder);
      document.getElementById("modal-folder-path").textContent = folder;
      resTagsDiv.querySelectorAll(".modal-res-tag").forEach(t => {
        t.classList.toggle("active", t.dataset.res === res);
      });
    }
    if (resList.length > 1) {
      resTagsDiv.innerHTML = resList.map(r =>
        '<span class="modal-res-tag' + (r === defaultRes ? ' active' : '') + '" data-res="' + r + '">' + r + '</span>'
      ).join("");
      resTagsDiv.style.display = "";
      resTagsDiv.querySelectorAll(".modal-res-tag").forEach(t => {
        t.addEventListener("click", () => selectRes(t.dataset.res));
      });
    } else {
      resTagsDiv.innerHTML = "";
      resTagsDiv.style.display = "none";
    }
    // Detail info
    const dl = document.getElementById("modal-detail");
    dl.innerHTML =
      "<dt>Source</dt><dd>" + c.dataset.source + "</dd>" +
      "<dt>Resolutions</dt><dd>" + (c.dataset.resolutions || "unknown") + "</dd>" +
      "<dt>Folder</dt><dd>" + c.dataset.folder + "</dd>";
    // Maps
    const mapsDiv = document.getElementById("modal-maps");
    const mapNames = (c.dataset.maps || "").split(",").filter(Boolean);
    mapsDiv.innerHTML = mapNames.map(m => '<span class="map-badge">' + m + '</span>').join("");
    // Folder link — browse via server
    const browseUrl = "/browse?path=" + encodeURIComponent(c.dataset.folder);
    const browseLink = document.getElementById("modal-open-folder");
    browseLink.href = browseUrl;
    browseLink.target = "_blank";
    document.getElementById("modal-folder-path").textContent = c.dataset.folder;
    document.getElementById("explorer-status").textContent = "";
    currentFolder = c.dataset.folder;
    overlay.classList.add("open");
  });
});

modalClose.addEventListener("click", () => overlay.classList.remove("open"));
overlay.addEventListener("click", e => {
  if (e.target === overlay) overlay.classList.remove("open");
});
document.addEventListener("keydown", e => {
  if (e.key === "Escape") overlay.classList.remove("open");
});

// --- Tiling preview ---
const tileBox = document.getElementById("tile-box");
const tileZoom = document.getElementById("tile-zoom");
const tileZoomLabel = document.getElementById("tile-zoom-label");
let tileDragStart = null;
let tileBgPos = [0, 0];

function updateTile() {
  const pct = parseInt(tileZoom.value);
  tileBox.style.backgroundSize = pct + "% auto";
  const reps = Math.round(100 / pct);
  tileZoomLabel.textContent = reps + "\u00d7" + reps;
}
tileZoom.addEventListener("input", updateTile);

tileBox.addEventListener("mousedown", e => {
  tileDragStart = [e.clientX, e.clientY];
  e.preventDefault();
});
document.addEventListener("mousemove", e => {
  if (!tileDragStart) return;
  tileBgPos[0] += e.clientX - tileDragStart[0];
  tileBgPos[1] += e.clientY - tileDragStart[1];
  tileBox.style.backgroundPosition = tileBgPos[0] + "px " + tileBgPos[1] + "px";
  tileDragStart = [e.clientX, e.clientY];
});
document.addEventListener("mouseup", () => { tileDragStart = null; });

tileBox.addEventListener("wheel", e => {
  e.preventDefault();
  let v = parseInt(tileZoom.value) + (e.deltaY > 0 ? -5 : 5);
  v = Math.max(10, Math.min(200, v));
  tileZoom.value = v;
  updateTile();
}, {passive: false});

// --- Open in Explorer (via local server API) ---
let currentFolder = "";
document.getElementById("modal-open-explorer").addEventListener("click", () => {
  if (!currentFolder) return;
  const status = document.getElementById("explorer-status");
  fetch("/api/open-folder?path=" + encodeURIComponent(currentFolder))
    .then(r => r.json())
    .then(d => {
      status.textContent = d.ok ? "Opened!" : (d.error || "Failed");
      setTimeout(() => status.textContent = "", 2000);
    })
    .catch(() => {
      status.textContent = "Server not running — use the .bat";
      setTimeout(() => status.textContent = "", 3000);
    });
});
</script>
</body>
</html>
"""


def _embed_image(path: Path, alt: str = "") -> str | None:
    """Read an image file and return a base64 data URI src string."""
    if not path or not path.exists():
        return None
    data = path.read_bytes()
    b64 = base64.b64encode(data).decode("ascii")
    mime = "image/png" if path.suffix.lower() == ".png" else "image/jpeg"
    return f"data:{mime};base64,{b64}"


def _get_sphere_path(texture_set: TextureSet, thumbnails_dir: Path | None) -> Path | None:
    """Find the Blender-rendered .png sphere thumbnail."""
    if not thumbnails_dir:
        return None
    candidate = thumbnails_dir / f"{texture_set.folder.name}.png"
    return candidate if candidate.exists() else None


def _get_flat_path(texture_set: TextureSet, thumbnails_dir: Path | None) -> Path | None:
    """Find or generate the flat albedo-crop .jpg thumbnail."""
    if thumbnails_dir:
        candidate = thumbnails_dir / f"{texture_set.folder.name}.jpg"
        if candidate.exists():
            return candidate

    # Auto-generate from albedo
    if thumbnails_dir:
        result = _generate_quick_thumbnail(texture_set, thumbnails_dir)
        if result:
            return result

    # Fall back to provider preview (resize it)
    if texture_set.preview_image and texture_set.preview_image.exists() and thumbnails_dir:
        return _resize_preview(texture_set.preview_image, texture_set.folder.name, thumbnails_dir)

    return None


def _thumbnail_html(texture_set: TextureSet, thumbnails_dir: Path | None) -> str:
    """Build the thumb-wrap HTML with both sphere and flat images."""
    sphere_path = _get_sphere_path(texture_set, thumbnails_dir)
    flat_path = _get_flat_path(texture_set, thumbnails_dir)

    sphere_src = _embed_image(sphere_path) if sphere_path else None
    flat_src = _embed_image(flat_path) if flat_path else None

    if not sphere_src and not flat_src:
        return '<div class="thumb-wrap"><div class="placeholder">\U0001f3a8</div></div>'

    parts = ['<div class="thumb-wrap">']
    # Sphere shown by default, flat hidden
    if sphere_src:
        parts.append(f'<img class="thumb-sphere" src="{sphere_src}" alt="sphere" loading="lazy">')
    if flat_src:
        hidden = ' hidden-thumb' if sphere_src else ''
        parts.append(f'<img class="thumb-flat{hidden}" src="{flat_src}" alt="flat" loading="lazy">')
    # If only flat exists, show it as sphere too so toggle doesn't break
    if not sphere_src and flat_src:
        parts.append(f'<img class="thumb-sphere hidden-thumb" src="{flat_src}" alt="sphere" loading="lazy">')
    if sphere_src and not flat_src:
        parts.append(f'<img class="thumb-flat hidden-thumb" src="{sphere_src}" alt="flat" loading="lazy">')
    parts.append('</div>')
    return "".join(parts)


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
            cropped.thumbnail((256, 256), Image.Resampling.LANCZOS)
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
            img.thumbnail((256, 256), Image.Resampling.LANCZOS)
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
        map_list = sorted(all_map_types)

        thumb = _thumbnail_html(best, thumbnails_dir)

        # Build resolution tags
        res_tags = ""
        if resolutions:
            tags = [f'<span class="res-tag">{r}</span>' for r in resolutions]
            res_tags = f'<div class="res-tags">{" ".join(tags)}</div>'

        res_data = ",".join(resolutions)  # for filtering
        map_data = ",".join(map_list)  # for modal
        # Use the folder path of the highest-res variant for "open folder"
        folder_path = str(best.folder.resolve()).replace("\\", "\\\\")
        # Build resolution → folder mapping for modal switching
        import json as json_mod
        import html as html_mod
        res_folders = {}
        for ts in variants:
            if ts.resolution:
                res_folders[ts.resolution] = str(ts.folder.resolve()).replace("\\", "\\\\")
        res_folders_json = html_mod.escape(json_mod.dumps(res_folders))
        # HTML-safe display name
        safe_name = html_mod.escape(name)

        cards_html.append(
            f'<div class="card" data-name="{name.lower()}" '
            f'data-display-name="{safe_name}" '
            f'data-source="{best.source.value}" data-resolutions="{res_data}" '
            f'data-maps="{map_data}" data-folder="{folder_path}" '
            f'data-res-folders="{res_folders_json}">'
            f'{thumb}'
            f'<div class="info">'
            f'<div class="name" title="{safe_name}">{safe_name}</div>'
            f'<div class="meta">'
            f'<span class="badge {best.source.value}">{best.source.value}</span>'
            f'{", ".join(map_list)}'
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
