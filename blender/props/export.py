"""Build the room props and write public/models/props.glb.

Run it inside Blender, for example through the Blender MCP:
    import runpy; runpy.run_path("<repo>/blender/props/export.py", run_name="__main__")

Every prop is a root node of the GLB, at the origin, named as in build.py: the web clones the one it
needs and places it. The books share their materials, so clone a book's materials before dressing
it. The plant keeps its "_sway" attribute. Geometry is Draco-compressed: load it with DRACOLoader.
"""

import os
import runpy

import bpy

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.normpath(os.path.join(HERE, "..", "..", "public", "models", "props.glb"))


def export(path=OUT):
    props = runpy.run_path(os.path.join(HERE, "build.py"))["build"]()
    layout = {obj: obj.location.copy() for obj in props}
    bpy.ops.object.select_all(action="DESELECT")
    for obj in props:
        obj.location = (0, 0, 0)
        for o in [obj] + list(obj.children):
            o.select_set(True)
    bpy.context.view_layer.objects.active = props[0]
    os.makedirs(os.path.dirname(path), exist_ok=True)
    try:
        bpy.ops.export_scene.gltf(
            filepath=path,
            use_selection=True,
            export_format="GLB",
            export_apply=True,  # bakes the weighted normals
            export_attributes=True,
            export_animations=False,
            export_draco_mesh_compression_enable=True,
        )
    finally:
        for obj, at in layout.items():
            obj.location = at
    print("Props: wrote %s (%d KB)" % (path, os.path.getsize(path) // 1024))
    return path


if __name__ == "__main__":
    export()
