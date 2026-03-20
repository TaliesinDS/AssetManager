"""Tests for the TextureSet and TextureMap models."""

from __future__ import annotations

from pathlib import Path

from asset_manager.models import MapType, Source, TextureMap, TextureSet


class TestTextureSet:
    def test_get_normal_map_prefers_gl(self):
        ts = TextureSet(name="test", folder=Path("/fake"), maps=[
            TextureMap(path=Path("/fake/dx.jpg"), map_type=MapType.NORMAL_DX, format="jpg"),
            TextureMap(path=Path("/fake/gl.jpg"), map_type=MapType.NORMAL_GL, format="jpg"),
        ])
        normal = ts.get_normal_map()
        assert normal is not None
        assert normal.map_type == MapType.NORMAL_GL

    def test_get_normal_map_falls_back_to_dx(self):
        ts = TextureSet(name="test", folder=Path("/fake"), maps=[
            TextureMap(path=Path("/fake/dx.jpg"), map_type=MapType.NORMAL_DX, format="jpg"),
        ])
        normal = ts.get_normal_map()
        assert normal is not None
        assert normal.map_type == MapType.NORMAL_DX

    def test_get_normal_map_returns_none(self):
        ts = TextureSet(name="test", folder=Path("/fake"), maps=[
            TextureMap(path=Path("/fake/col.jpg"), map_type=MapType.ALBEDO, format="jpg"),
        ])
        assert ts.get_normal_map() is None

    def test_has_albedo(self):
        ts = TextureSet(name="test", folder=Path("/fake"), maps=[
            TextureMap(path=Path("/fake/col.jpg"), map_type=MapType.ALBEDO, format="jpg"),
        ])
        assert ts.has_albedo is True

    def test_no_albedo(self):
        ts = TextureSet(name="test", folder=Path("/fake"))
        assert ts.has_albedo is False

    def test_to_dict_roundtrip(self):
        ts = TextureSet(
            name="Test Material",
            folder=Path("/fake/test_4k.blend"),
            source=Source.POLYHAVEN,
            resolution="4K",
            maps=[
                TextureMap(path=Path("/fake/diff.jpg"), map_type=MapType.ALBEDO, resolution="4K", format="jpg"),
            ],
        )
        d = ts.to_dict()
        assert d["name"] == "Test Material"
        assert d["source"] == "polyhaven"
        assert d["resolution"] == "4K"
        assert len(d["maps"]) == 1
        assert d["maps"][0]["type"] == "Albedo"
