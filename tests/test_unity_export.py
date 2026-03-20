"""Tests for Unity export logic."""

from __future__ import annotations

from pathlib import Path

from asset_manager.models import MapType, Source, TextureMap, TextureSet
from asset_manager.unity_export import pick_best_map, export_for_unity, UNITY_ESSENTIAL_MAPS


def _make_texture_set(maps_data: list[tuple[str, MapType, str]], source=Source.POLYHAVEN) -> TextureSet:
    """Helper to create a TextureSet with given maps."""
    ts = TextureSet(
        name="Test Material",
        folder=Path("/fake/test_material_4k.blend"),
        source=source,
        resolution="4K",
    )
    for filename, map_type, fmt in maps_data:
        ts.maps.append(TextureMap(
            path=Path(f"/fake/{filename}"),
            map_type=map_type,
            resolution="4K",
            format=fmt,
        ))
    return ts


class TestPickBestMap:
    def test_single_candidate(self):
        ts = _make_texture_set([("tex_Albedo.jpg", MapType.ALBEDO, "jpg")])
        result = pick_best_map(ts, MapType.ALBEDO)
        assert result is not None
        assert result.format == "jpg"

    def test_prefers_png_over_exr(self):
        ts = _make_texture_set([
            ("tex_Normal.exr", MapType.NORMAL_GL, "exr"),
            ("tex_Normal.png", MapType.NORMAL_GL, "png"),
        ])
        result = pick_best_map(ts, MapType.NORMAL_GL)
        assert result is not None
        assert result.format == "png"

    def test_no_candidate(self):
        ts = _make_texture_set([("tex_Albedo.jpg", MapType.ALBEDO, "jpg")])
        result = pick_best_map(ts, MapType.METALLIC)
        assert result is None


class TestExportForUnity:
    def test_exports_essential_maps(self, tmp_path):
        # Create real files for the texture set
        src_dir = tmp_path / "source"
        src_dir.mkdir()
        albedo_file = src_dir / "test_diff_4k.jpg"
        albedo_file.write_bytes(b"\xff\xd8\xff\xe0" + b"\x00" * 100)  # fake JPEG
        normal_file = src_dir / "test_nor_gl_4k.png"
        normal_file.write_bytes(b"\x89PNG" + b"\x00" * 100)

        ts = TextureSet(
            name="Test Material",
            folder=src_dir,
            source=Source.POLYHAVEN,
            resolution="4K",
            maps=[
                TextureMap(path=albedo_file, map_type=MapType.ALBEDO, resolution="4K", format="jpg"),
                TextureMap(path=normal_file, map_type=MapType.NORMAL_GL, resolution="4K", format="png"),
            ],
        )

        out_dir = tmp_path / "unity_out"
        result = export_for_unity(ts, out_dir)

        assert result is not None
        assert result.exists()
        # Check exported files
        exported = list(result.iterdir())
        names = {f.name for f in exported}
        assert any("_Albedo" in n for n in names)
        assert any("_Normal" in n for n in names)

    def test_prefers_gl_normal_over_dx(self, tmp_path):
        src_dir = tmp_path / "source"
        src_dir.mkdir()
        gl_file = src_dir / "tex_NormalGL.jpg"
        gl_file.write_bytes(b"\xff\xd8" + b"\x00" * 100)
        dx_file = src_dir / "tex_NormalDX.jpg"
        dx_file.write_bytes(b"\xff\xd8" + b"\x00" * 100)

        ts = TextureSet(
            name="Test Material",
            folder=src_dir,
            source=Source.AMBIENTCG,
            resolution="4K",
            maps=[
                TextureMap(path=gl_file, map_type=MapType.NORMAL_GL, resolution="4K", format="jpg"),
                TextureMap(path=dx_file, map_type=MapType.NORMAL_DX, resolution="4K", format="jpg"),
            ],
        )

        out_dir = tmp_path / "unity_out"
        result = export_for_unity(ts, out_dir)

        assert result is not None
        # Should only have one _Normal file (GL preferred)
        normal_files = [f for f in result.iterdir() if "_Normal" in f.name]
        assert len(normal_files) == 1

    def test_no_export_when_empty(self, tmp_path):
        ts = TextureSet(name="Empty", folder=tmp_path, source=Source.UNKNOWN)
        result = export_for_unity(ts, tmp_path / "out")
        assert result is None


class TestUnityCoverage:
    def test_essential_maps_include_normals(self):
        assert MapType.NORMAL_GL in UNITY_ESSENTIAL_MAPS
        assert MapType.NORMAL_DX in UNITY_ESSENTIAL_MAPS

    def test_essential_maps_include_emissive(self):
        assert MapType.EMISSIVE in UNITY_ESSENTIAL_MAPS
