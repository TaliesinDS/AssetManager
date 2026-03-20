"""Generate PBR sphere preview thumbnails using Blender headless rendering."""

from __future__ import annotations

import subprocess
import textwrap
from pathlib import Path

from .models import MapType, TextureSet

# Blender Python script template that creates a sphere, applies PBR maps, and renders.
BLENDER_SCRIPT = textwrap.dedent('''\
    import bpy
    import sys
    import os

    argv = sys.argv[sys.argv.index("--") + 1:]
    albedo_path = argv[0] if len(argv) > 0 and argv[0] else ""
    normal_path = argv[1] if len(argv) > 1 and argv[1] else ""
    roughness_path = argv[2] if len(argv) > 2 and argv[2] else ""
    output_path = argv[3] if len(argv) > 3 else "/tmp/preview.png"
    size = int(argv[4]) if len(argv) > 4 else 256

    # Clean default scene
    bpy.ops.wm.read_factory_settings(use_empty=True)

    # Create a UV Sphere
    bpy.ops.mesh.primitive_uv_sphere_add(radius=1, segments=64, ring_count=32)
    sphere = bpy.context.active_object
    bpy.ops.object.shade_smooth()

    # Create material
    mat = bpy.data.materials.new("Preview")
    mat.use_nodes = True
    sphere.data.materials.append(mat)

    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    # Principled BSDF
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.location = (0, 0)

    output_node = nodes.new("ShaderNodeOutputMaterial")
    output_node.location = (300, 0)
    links.new(bsdf.outputs["BSDF"], output_node.inputs["Surface"])

    # Texture coordinate + mapping
    tex_coord = nodes.new("ShaderNodeTexCoord")
    tex_coord.location = (-800, 0)

    # Albedo
    if albedo_path and os.path.isfile(albedo_path):
        albedo_tex = nodes.new("ShaderNodeTexImage")
        albedo_tex.location = (-400, 200)
        albedo_tex.image = bpy.data.images.load(albedo_path)
        links.new(tex_coord.outputs["UV"], albedo_tex.inputs["Vector"])
        links.new(albedo_tex.outputs["Color"], bsdf.inputs["Base Color"])

    # Normal map
    if normal_path and os.path.isfile(normal_path):
        normal_tex = nodes.new("ShaderNodeTexImage")
        normal_tex.location = (-400, -200)
        normal_tex.image = bpy.data.images.load(normal_path)
        normal_tex.image.colorspace_settings.name = "Non-Color"
        normal_map = nodes.new("ShaderNodeNormalMap")
        normal_map.location = (-100, -200)
        links.new(tex_coord.outputs["UV"], normal_tex.inputs["Vector"])
        links.new(normal_tex.outputs["Color"], normal_map.inputs["Color"])
        links.new(normal_map.outputs["Normal"], bsdf.inputs["Normal"])

    # Roughness
    if roughness_path and os.path.isfile(roughness_path):
        rough_tex = nodes.new("ShaderNodeTexImage")
        rough_tex.location = (-400, -500)
        rough_tex.image = bpy.data.images.load(roughness_path)
        rough_tex.image.colorspace_settings.name = "Non-Color"
        links.new(tex_coord.outputs["UV"], rough_tex.inputs["Vector"])
        links.new(rough_tex.outputs["Color"], bsdf.inputs["Roughness"])

    # Camera
    bpy.ops.object.camera_add(location=(2.5, -2.5, 1.8))
    cam = bpy.context.active_object
    cam.rotation_euler = (1.1, 0, 0.8)
    bpy.context.scene.camera = cam

    # Lighting - HDRI-like setup with area lights
    bpy.ops.object.light_add(type="AREA", location=(3, -2, 4))
    key_light = bpy.context.active_object
    key_light.data.energy = 150
    key_light.data.size = 3

    bpy.ops.object.light_add(type="AREA", location=(-2, 3, 2))
    fill_light = bpy.context.active_object
    fill_light.data.energy = 50
    fill_light.data.size = 4

    # World background
    world = bpy.data.worlds.new("World")
    bpy.context.scene.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes["Background"]
    bg.inputs["Color"].default_value = (0.15, 0.15, 0.18, 1.0)
    bg.inputs["Strength"].default_value = 0.5

    # Render settings
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE_NEXT"
    scene.render.resolution_x = size
    scene.render.resolution_y = size
    scene.render.film_transparent = True
    scene.render.filepath = output_path
    scene.render.image_settings.file_format = "PNG"

    bpy.ops.render.render(write_still=True)
''')


def generate_thumbnail(
    texture_set: TextureSet,
    output_dir: Path,
    blender_path: str = "blender",
    size: int = 256,
) -> Path | None:
    """Render a PBR sphere thumbnail for a texture set using Blender.

    Returns the path to the generated thumbnail, or None on failure.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{texture_set.folder.name}.png"

    # Need at least an albedo map to render anything useful
    albedo = texture_set.get_map(MapType.ALBEDO)
    if not albedo:
        return None

    normal = texture_set.get_normal_map()  # Prefers GL for URP
    roughness = texture_set.get_map(MapType.ROUGHNESS)

    # Write the Blender script to a temp file
    script_path = output_dir / "_render_preview.py"
    script_path.write_text(BLENDER_SCRIPT)

    cmd = [
        blender_path,
        "--background",
        "--python", str(script_path),
        "--",
        str(albedo.path),
        str(normal.path) if normal else "",
        str(roughness.path) if roughness else "",
        str(output_path),
        str(size),
    ]

    try:
        subprocess.run(
            cmd,
            capture_output=True,
            timeout=60,
            check=True,
        )
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError) as e:
        print(f"  [WARN] Thumbnail generation failed for {texture_set.name}: {e}")
        return None

    return output_path if output_path.exists() else None


def generate_all_thumbnails(
    texture_sets: list[TextureSet],
    output_dir: Path,
    blender_path: str = "blender",
    size: int = 256,
) -> dict[str, Path]:
    """Generate thumbnails for all texture sets. Returns mapping of folder name -> thumbnail path."""
    results: dict[str, Path] = {}
    total = len(texture_sets)

    for i, ts in enumerate(texture_sets, 1):
        thumb_path = output_dir / f"{ts.folder.name}.png"
        if thumb_path.exists():
            print(f"  [{i}/{total}] {ts.name} — cached")
            results[ts.folder.name] = thumb_path
            continue

        print(f"  [{i}/{total}] {ts.name} — rendering...")
        result = generate_thumbnail(ts, output_dir, blender_path, size)
        if result:
            results[ts.folder.name] = result

    return results
