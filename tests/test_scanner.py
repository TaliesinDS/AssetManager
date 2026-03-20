"""Tests for the map classifier and scanner logic."""

from __future__ import annotations

from pathlib import Path

from asset_manager.models import MapType, Source
from asset_manager.scanner import classify_map, detect_source, detect_resolution, _is_preview_image


class TestClassifyMap:
    """Test PBR map type classification from filenames."""

    # --- Albedo ---
    def test_polyhaven_diff(self):
        assert classify_map("cobblestone_01_diff_4k.jpg") == MapType.ALBEDO

    def test_ambientcg_color(self):
        assert classify_map("Asphalt015_4K-JPG_Color.jpg") == MapType.ALBEDO

    def test_megascans_basecolor(self):
        assert classify_map("Castle_Wall_scpgdgca_4K_BaseColor.jpg") == MapType.ALBEDO

    def test_diffuse_original(self):
        assert classify_map("Wod_029_diffuseOriginal.png") == MapType.ALBEDO

    # --- Normal GL ---
    def test_polyhaven_nor_gl(self):
        assert classify_map("brick_wall_02_nor_gl_4k.exr") == MapType.NORMAL_GL

    def test_ambientcg_normalgl(self):
        assert classify_map("Asphalt015_4K-JPG_NormalGL.jpg") == MapType.NORMAL_GL

    def test_plants_normal_opengl(self):
        assert classify_map("plants_0002_normal_opengl_1k.png") == MapType.NORMAL_GL

    # --- Normal DX ---
    def test_ambientcg_normaldx(self):
        assert classify_map("Asphalt015_4K-JPG_NormalDX.jpg") == MapType.NORMAL_DX

    def test_plants_normal_directx(self):
        assert classify_map("plants_0002_normal_directx_1k.png") == MapType.NORMAL_DX

    def test_megascans_normal_is_dx(self):
        """Megascans _Normal (no GL/DX suffix) is actually DirectX format."""
        assert classify_map("Castle_Wall_scpgdgca_4K_Normal.jpg", Source.MEGASCANS) == MapType.NORMAL_DX

    def test_generic_normal_defaults_gl(self):
        """Generic _Normal without source hint defaults to GL."""
        assert classify_map("some_texture_Normal.jpg") == MapType.NORMAL_GL

    # --- Height ---
    def test_polyhaven_disp(self):
        assert classify_map("cobblestone_01_disp_4k.png") == MapType.HEIGHT

    def test_ambientcg_displacement(self):
        assert classify_map("Asphalt015_4K-JPG_Displacement.jpg") == MapType.HEIGHT

    def test_height(self):
        assert classify_map("some_texture_height.png") == MapType.HEIGHT

    # --- Roughness ---
    def test_polyhaven_rough(self):
        assert classify_map("cobblestone_01_rough_4k.jpg") == MapType.ROUGHNESS

    def test_ambientcg_roughness(self):
        assert classify_map("Asphalt015_4K-JPG_Roughness.jpg") == MapType.ROUGHNESS

    # --- AO ---
    def test_megascans_ao(self):
        assert classify_map("Castle_Wall_scpgdgca_4K_AO.jpg") == MapType.AO

    # --- Metallic ---
    def test_metallic(self):
        assert classify_map("corrugated_iron_02_metal_4k.exr") == MapType.METALLIC

    def test_metalness(self):
        assert classify_map("some_texture_Metalness.jpg") == MapType.METALLIC

    # --- Smoothness ---
    def test_smoothness(self):
        assert classify_map("Wod_029_smoothness.png") == MapType.SMOOTHNESS

    def test_glossiness(self):
        assert classify_map("Plaster_02_glossiness.jpg") == MapType.SMOOTHNESS

    # --- Opacity ---
    def test_opacity(self):
        assert classify_map("Asphalt_Patch_tjxmsch_4K_Opacity.jpg") == MapType.OPACITY

    def test_mask(self):
        assert classify_map("leafy_grass_mask_4k.png") == MapType.OPACITY

    # --- Other ---
    def test_specular(self):
        assert classify_map("brown_mud_03_spec_4k.png") == MapType.SPECULAR

    def test_scattering(self):
        assert classify_map("Foliage007_1K-JPG_Scattering.jpg") == MapType.SCATTERING

    def test_transmission(self):
        assert classify_map("Mossy_Forest_Floor_vfylbge_4K_Transmission.jpg") == MapType.TRANSMISSION

    def test_packed_mr(self):
        assert classify_map("T_tedwdiic_4K_MR.png") == MapType.PACKED_MR

    # --- Format indicator in name (PolyHaven edge case) ---
    def test_diff_png_stripped(self):
        """PolyHaven sometimes embeds format: _diff_png_4k should still be Albedo."""
        assert classify_map("church_bricks_02_diff_png_4k.png") == MapType.ALBEDO

    # --- Unknown ---
    def test_anisotropy_is_unknown(self):
        assert classify_map("hessian_230_anisotropy_rotation_4k.png") == MapType.UNKNOWN

    def test_untitled_is_unknown(self):
        assert classify_map("untitled.png") == MapType.UNKNOWN


class TestDetectSource:
    """Test texture source/provider detection."""

    def test_polyhaven(self, tmp_path):
        folder = tmp_path / "cobblestone_01_4k.blend"
        folder.mkdir()
        assert detect_source(folder) == Source.POLYHAVEN

    def test_ambientcg(self, tmp_path):
        folder = tmp_path / "Asphalt015_4K-JPG"
        folder.mkdir()
        assert detect_source(folder) == Source.AMBIENTCG

    def test_megascans_by_name(self, tmp_path):
        folder = tmp_path / "castle_wall_scpgdgca_4k"
        folder.mkdir()
        assert detect_source(folder) == Source.MEGASCANS

    def test_megascans_by_json(self, tmp_path):
        folder = tmp_path / "some_texture"
        folder.mkdir()
        (folder / "metadata.json").write_text("{}")
        assert detect_source(folder) == Source.MEGASCANS

    def test_unknown(self, tmp_path):
        folder = tmp_path / "random_folder"
        folder.mkdir()
        assert detect_source(folder) == Source.UNKNOWN


class TestDetectResolution:
    def test_4k(self):
        assert detect_resolution("cobblestone_01_4k.blend") == "4K"

    def test_2k(self):
        assert detect_resolution("castle_wall_scpgdgca_2k") == "2K"

    def test_1k_uppercase(self):
        assert detect_resolution("Asphalt015_1K-JPG") == "1K"

    def test_no_resolution(self):
        assert detect_resolution("random_folder") == ""


class TestIsPreviewImage:
    def test_ambientcg_preview(self, tmp_path):
        folder = tmp_path / "Asphalt015_4K-JPG"
        folder.mkdir()
        preview = folder / "Asphalt015.png"
        preview.touch()
        assert _is_preview_image(preview, folder) is True

    def test_map_file_is_not_preview(self, tmp_path):
        folder = tmp_path / "Asphalt015_4K-JPG"
        folder.mkdir()
        mapfile = folder / "Asphalt015_4K-JPG_Color.jpg"
        mapfile.touch()
        assert _is_preview_image(mapfile, folder) is False

    def test_preview_png(self, tmp_path):
        folder = tmp_path / "some_folder"
        folder.mkdir()
        preview = folder / "Preview.png"
        preview.touch()
        assert _is_preview_image(preview, folder) is True
