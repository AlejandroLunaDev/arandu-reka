"""Build Arandu, key its clips and write public/models/arandu.glb.

Run it inside Blender, for example through the Blender MCP:
    import runpy; runpy.run_path("<repo>/blender/arandu/export.py", run_name="__main__")

The GLB keeps the "_fur" and "_comb" vertex attributes the web fur shells read, one skin and the
clips sit, walk, jump and tap. Geometry is Draco-compressed: load it with DRACOLoader.
"""

import os
import runpy

import bpy

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.normpath(os.path.join(HERE, "..", "..", "public", "models", "arandu.glb"))


def export(path=OUT):
    arm, mesh = runpy.run_path(os.path.join(HERE, "build.py"))["build"]()
    runpy.run_path(os.path.join(HERE, "animate.py"))["animate"](arm)
    bpy.ops.object.select_all(action="DESELECT")
    for obj in (arm, mesh):
        obj.select_set(True)
    bpy.context.view_layer.objects.active = arm
    os.makedirs(os.path.dirname(path), exist_ok=True)
    bpy.ops.export_scene.gltf(
        filepath=path,
        use_selection=True,
        export_format="GLB",
        export_attributes=True,
        export_skins=True,
        export_animations=True,
        export_animation_mode="ACTIONS",
        export_force_sampling=False,  # the clips are already keyed on every frame
        export_optimize_animation_size=False,  # every clip keeps every body channel
        export_draco_mesh_compression_enable=True,
    )
    print("Arandu: wrote %s (%d KB)" % (path, os.path.getsize(path) // 1024))
    return path


if __name__ == "__main__":
    export()
