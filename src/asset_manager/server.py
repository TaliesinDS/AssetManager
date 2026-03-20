"""Tiny localhost server that serves the gallery and can open folders in Explorer."""

from __future__ import annotations

import html
import json
import mimetypes
import os
import subprocess
import sys
import webbrowser
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
import traceback
from urllib.parse import parse_qs, quote, unquote, urlparse

from .config import load_config


class GalleryHandler(SimpleHTTPRequestHandler):
    """Serves files from the output directory + handles API and browse endpoints."""

    # Set by serve_gallery() before the server starts
    allowed_roots: list[Path] = []

    def do_GET(self):
        try:
            parsed = urlparse(self.path)

            if parsed.path == "/favicon.ico":
                self.send_response(204)
                self.end_headers()
                return

            if parsed.path == "/api/open-folder":
                self._handle_open_folder(parsed.query)
                return

            if parsed.path == "/browse" or parsed.path == "/browse/":
                self._handle_browse(parsed.path, parsed.query)
                return

            # Serve static files from the output directory
            super().do_GET()
        except Exception as exc:
            traceback.print_exc()
            self._serve_error_page(500, f"Browse handler failed: {exc}")

    def _handle_open_folder(self, query: str):
        params = parse_qs(query)
        folder = params.get("path", [None])[0]

        if not folder:
            self._json_response(400, {"error": "Missing 'path' parameter"})
            return

        folder_path = Path(folder).resolve()

        # Security: only allow opening folders under the configured library roots
        if not any(self._is_under(folder_path, root) for root in self.allowed_roots):
            self._json_response(403, {"error": "Folder is outside allowed library paths"})
            return

        if not folder_path.is_dir():
            self._json_response(404, {"error": "Folder does not exist"})
            return

        # Open in Windows Explorer
        subprocess.Popen(["explorer", str(folder_path)])
        self._json_response(200, {"ok": True, "path": str(folder_path)})

    def _handle_browse(self, path: str, query: str):
        """Serve a directory listing or file from an allowed library path."""
        params = parse_qs(query)
        folder = params.get("path", [None])[0]

        if not folder:
            self._json_response(400, {"error": "Missing 'path' parameter"})
            return

        folder_path = Path(folder).resolve()

        if not any(self._is_under(folder_path, root) for root in self.allowed_roots):
            self._json_response(403, {"error": "Path is outside allowed library paths"})
            return

        file_name = params.get("file", [None])[0]
        if file_name:
            file_path = (folder_path / file_name).resolve()
            if not self._is_under(file_path, folder_path):
                self._json_response(403, {"error": "Path traversal denied"})
                return
            if file_path.is_file():
                self._serve_file(file_path)
                return
            self._json_response(404, {"error": "File not found"})
            return

        # Directory listing
        if not folder_path.is_dir():
            self._json_response(404, {"error": "Folder does not exist"})
            return

        self._serve_directory_listing(folder_path)

    def _serve_file(self, file_path: Path):
        """Serve a single file with the correct MIME type."""
        mime, _ = mimetypes.guess_type(str(file_path))
        mime = mime or "application/octet-stream"
        try:
            data = file_path.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", mime)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        except Exception:
            self._json_response(500, {"error": "Could not read file"})

    def _serve_directory_listing(self, folder_path: Path):
        """Render an HTML directory listing for a texture folder."""
        entries = sorted(folder_path.iterdir(), key=lambda p: (p.is_file(), p.name.lower()))
        folder_str = str(folder_path)

        rows = []
        for entry in entries:
            name = entry.name
            safe_name = html.escape(name)
            if entry.is_dir():
                sub_url = "/browse?path=" + quote(str(entry.resolve()), safe="")
                rows.append(
                    f'<tr><td><a href="{sub_url}">{safe_name}/</a></td>'
                    f'<td>-</td><td>folder</td></tr>'
                )
                continue

            size_kb = entry.stat().st_size / 1024
            size_str = f"{size_kb:.0f} KB" if size_kb < 1024 else f"{size_kb/1024:.1f} MB"
            ext = entry.suffix.lower() or "file"
            # Image files get a preview link
            if ext in (".png", ".jpg", ".jpeg", ".tga", ".tif", ".tiff", ".bmp"):
                file_url = "/browse?path=" + quote(folder_str, safe="") + "&file=" + quote(name, safe="")
                rows.append(
                    f'<tr><td><a href="{file_url}" target="_blank">{safe_name}</a></td>'
                    f'<td>{size_str}</td>'
                    f'<td>{ext}</td></tr>'
                )
            else:
                rows.append(f'<tr><td>{safe_name}</td><td>{size_str}</td><td>{ext}</td></tr>')

        body = f"""\
<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>{html.escape(folder_path.name)}</title>
<style>
  body {{ font-family: system-ui; background: #1a1a2e; color: #e0e0e0; padding: 1.5rem; }}
  h1 {{ font-size: 1.2rem; margin-bottom: 0.5rem; }}
  .path {{ font-size: 0.8rem; color: #666; margin-bottom: 1rem; word-break: break-all; }}
  table {{ border-collapse: collapse; width: 100%; }}
  th, td {{ text-align: left; padding: 0.4rem 1rem; border-bottom: 1px solid #222; }}
  th {{ color: #888; font-size: 0.8rem; }}
  a {{ color: #7cb3e0; text-decoration: none; }}
  a:hover {{ text-decoration: underline; }}
</style></head><body>
<h1>{html.escape(folder_path.name)}</h1>
<div class="path">{html.escape(folder_str)}</div>
<table><tr><th>Name</th><th>Size</th><th>Type</th></tr>
{"".join(rows)}
</table></body></html>"""

        encoded = body.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def _serve_error_page(self, code: int, message: str):
        body = f"""<!DOCTYPE html><html><head><meta charset=\"utf-8\"><title>Error</title>
<style>body {{ font-family: system-ui; background: #1a1a2e; color: #e0e0e0; padding: 2rem; }}</style>
</head><body><h1>Error {code}</h1><pre>{html.escape(message)}</pre></body></html>"""
        encoded = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    @staticmethod
    def _is_under(path: Path, root: Path) -> bool:
        try:
            path.relative_to(root)
            return True
        except ValueError:
            return False

    def _json_response(self, code: int, data: dict):
        body = json.dumps(data).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        # Quieter logging — only show API calls, not every static file request
        first = str(args[0]) if args else ""
        if "/api/" in first or "/browse" in first:
            super().log_message(format, *args)


def serve_gallery(port: int = 8271):
    """Start the gallery server on localhost."""
    cfg = load_config()
    output_dir = Path(cfg["paths"]["output"])

    # Build list of allowed roots for the open-folder endpoint
    allowed = [Path(cfg["paths"]["texture_library"]).resolve()]
    for key in ("game_ready", "in_progress", "unsorted"):
        p = cfg["paths"].get(key)
        if p:
            allowed.append(Path(p).resolve())

    GalleryHandler.allowed_roots = allowed

    gallery_file = output_dir / "gallery.html"
    if not gallery_file.exists():
        print(f"Gallery not found at {gallery_file}")
        print("Run 'Open Gallery.bat' first to generate it.")
        sys.exit(1)

    os.chdir(output_dir)

    server = None
    chosen_port = port
    for candidate_port in range(port, port + 10):
        try:
            server = HTTPServer(("127.0.0.1", candidate_port), GalleryHandler)
            chosen_port = candidate_port
            break
        except OSError:
            continue

    if server is None:
        print(f"Could not bind gallery server to any port from {port} to {port + 9}.")
        sys.exit(1)

    url = f"http://localhost:{chosen_port}/gallery.html"
    print(f"Serving gallery at {url}")
    print("Press Ctrl+C to stop.\n")
    webbrowser.open(url)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")
        server.server_close()
