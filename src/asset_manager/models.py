"""Data models for texture sets and their maps."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


class Source(Enum):
    """Detected source/provider of the texture set."""
    POLYHAVEN = "polyhaven"
    AMBIENTCG = "ambientcg"
    MEGASCANS = "megascans"
    UNKNOWN = "unknown"


class MapType(Enum):
    """Normalized PBR map types (Unity-centric naming)."""
    ALBEDO = "Albedo"
    NORMAL_GL = "NormalGL"      # OpenGL format (Y+ up) — URP expects this
    NORMAL_DX = "NormalDX"      # DirectX format (Y- up) — needs flip for URP
    HEIGHT = "Height"
    ROUGHNESS = "Roughness"
    SMOOTHNESS = "Smoothness"   # Inverse of roughness (Unity convention)
    AO = "AO"
    METALLIC = "Metallic"
    OPACITY = "Opacity"
    SPECULAR = "Specular"
    GLOSS = "Gloss"
    BUMP = "Bump"
    CAVITY = "Cavity"
    EMISSIVE = "Emissive"
    SCATTERING = "Scattering"   # Subsurface scattering / translucency
    TRANSMISSION = "Transmission"
    PACKED_MR = "MetallicRoughness"  # Packed metallic-roughness (e.g. UE _MR)
    PREVIEW = "Preview"         # Provider-supplied preview image (not a PBR map)
    UNKNOWN = "Unknown"


# Mapping from raw suffix (lowercase) to normalized MapType.
# Order matters for matching — more specific first.
SUFFIX_TO_MAP: dict[str, MapType] = {
    # AmbientCG
    "color": MapType.ALBEDO,
    # Megascans
    "basecolor": MapType.ALBEDO,
    "basecol": MapType.ALBEDO,
    # PolyHaven
    "diff": MapType.ALBEDO,
    "diffuse": MapType.ALBEDO,
    "albedo": MapType.ALBEDO,
    # Normals — GL (OpenGL, Y+ up) is what URP expects
    "normalgl": MapType.NORMAL_GL,
    "nor_gl": MapType.NORMAL_GL,
    # DX normals (Y- up) — Megascans default; needs green channel flip for URP
    "normaldx": MapType.NORMAL_DX,
    "nor_dx": MapType.NORMAL_DX,
    # Ambiguous "normal" — Megascans uses DX, but could be either
    "normal": MapType.NORMAL_GL,
    # Height / Displacement
    "displacement": MapType.HEIGHT,
    "disp": MapType.HEIGHT,
    "height": MapType.HEIGHT,
    # Roughness
    "roughness": MapType.ROUGHNESS,
    "rough": MapType.ROUGHNESS,
    # Smoothness (inverse of roughness)
    "smoothness": MapType.SMOOTHNESS,
    "glossiness": MapType.SMOOTHNESS,
    # AO
    "ao": MapType.AO,
    "ambientocclusion": MapType.AO,
    # Metallic
    "metallic": MapType.METALLIC,
    "metalness": MapType.METALLIC,
    "metal": MapType.METALLIC,
    # Opacity
    "opacity": MapType.OPACITY,
    "alpha": MapType.OPACITY,
    "mask": MapType.OPACITY,
    # Other maps
    "specular": MapType.SPECULAR,
    "spec": MapType.SPECULAR,
    "gloss": MapType.GLOSS,
    "bump": MapType.BUMP,
    "cavity": MapType.CAVITY,
    "emissive": MapType.EMISSIVE,
    "emission": MapType.EMISSIVE,
    # Packed
    "mr": MapType.PACKED_MR,
    "arm": MapType.PACKED_MR,
    # Additional maps
    "scattering": MapType.SCATTERING,
    "transmission": MapType.TRANSMISSION,
    "translucency": MapType.TRANSMISSION,
    "diffuseoriginal": MapType.ALBEDO,
    # Alternate normal map naming (e.g. plants_0002_normal_opengl_1k)
    "normal_opengl": MapType.NORMAL_GL,
    "normal_directx": MapType.NORMAL_DX,
}


@dataclass
class TextureMap:
    """A single texture map file within a texture set."""
    path: Path
    map_type: MapType
    resolution: str = ""        # e.g. "4K", "2K", "1K"
    format: str = ""            # e.g. "jpg", "png", "exr"

    @property
    def size_bytes(self) -> int:
        return self.path.stat().st_size if self.path.exists() else 0


@dataclass
class TextureSet:
    """A complete PBR texture set (one material) with all its maps."""
    name: str                           # Human-readable name, e.g. "cobblestone_01"
    folder: Path                        # Path to the texture set folder
    source: Source = Source.UNKNOWN
    resolution: str = ""                # Primary resolution, e.g. "4K"
    maps: list[TextureMap] = field(default_factory=list)
    blend_file: Path | None = None      # .blend file if present
    metadata: dict = field(default_factory=dict)  # Tags, categories from JSON etc.
    preview_image: Path | None = None   # Existing preview if available (AmbientCG)

    def get_map(self, map_type: MapType) -> TextureMap | None:
        """Get the first map matching this type."""
        return next((m for m in self.maps if m.map_type == map_type), None)

    def get_normal_map(self) -> TextureMap | None:
        """Get the best normal map — prefers GL (OpenGL) for URP."""
        gl = self.get_map(MapType.NORMAL_GL)
        if gl:
            return gl
        return self.get_map(MapType.NORMAL_DX)

    @property
    def has_albedo(self) -> bool:
        return self.get_map(MapType.ALBEDO) is not None

    @property
    def map_types(self) -> list[MapType]:
        return [m.map_type for m in self.maps]

    def to_dict(self) -> dict:
        """Serialize for JSON catalog output."""
        return {
            "name": self.name,
            "folder": str(self.folder),
            "source": self.source.value,
            "resolution": self.resolution,
            "maps": [
                {
                    "path": str(m.path),
                    "type": m.map_type.value,
                    "resolution": m.resolution,
                    "format": m.format,
                }
                for m in self.maps
            ],
            "blend_file": str(self.blend_file) if self.blend_file else None,
            "metadata": self.metadata,
            "preview_image": str(self.preview_image) if self.preview_image else None,
        }
