"""Render transparent PNGs of the props to blender/props/renders/.

Run it inside Blender, for example through the Blender MCP:
    import runpy; runpy.run_path("<repo>/blender/props/render.py", run_name="__main__")

It rebuilds the props, then gives each shot its own camera and light, renders it with EEVEE on a
transparent film cropped to the prop, and puts the scene back: settings restored, props rebuilt as
build.py leaves them. The books shot stands the books together in brand colors, one leaning and
one lying down, the way the landing shelves them.
"""

import math
import os
import runpy

import bpy
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "renders")
BUILD = runpy.run_path(os.path.join(HERE, "build.py"))
BOOKS, srgb = BUILD["BOOKS"], BUILD["srgb"]

FRONT = Vector((0.35, -1.0, 0.3))  # from the front, a little to the right and above
BELOW = Vector((0.35, -1.0, -0.12))  # a hanging lamp is seen from under it
SHOTS = {  # file name: objects in the shot, direction from the shot toward the camera
    "books": (list(BOOKS), FRONT),
    "shelf-large": (["ShelfLarge"], FRONT),
    "shelf-medium": (["ShelfMedium"], FRONT),
    "shelf-small": (["ShelfSmall"], FRONT),
    "plant": (["PlantPot"], FRONT),
    "lamp-mushroom": (["LampMushroom"], FRONT),
    "lamp-classic": (["LampClassic"], FRONT),
    "lamp-desk": (["LampDesk"], FRONT),
    "lamp-pendant": (["LampPendant", "LampPendantCord"], BELOW),
    "yarn": (["YarnBall"], FRONT),
    "ball": (["Ball"], FRONT),
}
BOOK_COLORS = {  # the landing's book colors
    "BookThick": "#6B3FA0", "Book": "#B97F22", "BookShort": "#9B72CF",
    "BookSlim": "#DDD3C0", "BookTall": "#432765", "BookPaperback": "#E0A845",
}
LONGEST = 1200  # pixels on the longer side of each cropped render
MARGIN = 0.02  # of the frame, around the prop


def dress_books():
    """Give each book its own cover color, then stand them in a row, one leaning, one lying down."""
    for name, color in BOOK_COLORS.items():
        me = bpy.data.objects[name].data
        for i, mat in enumerate(me.materials):
            if mat.name in ("BookCover", "BookSpine"):
                own = mat.copy()
                next(n for n in own.node_tree.nodes if n.type == "BSDF_PRINCIPLED").inputs["Base Color"].default_value = srgb(color)
                me.materials[i] = own

    x = 0.0
    for name in ("BookThick", "Book", "BookShort", "BookSlim"):
        T = BOOKS[name][2]
        obj = bpy.data.objects[name]
        obj.location, obj.rotation_euler = (x + T / 2, 0, 0), (0, 0, 0)
        x += T + 0.003

    lean = math.radians(9)  # tipped onto its left neighbour, pivoting on its bottom left edge
    H, _, T = BOOKS["BookTall"][:3]
    pivot = x + BOOKS["BookSlim"][0] * math.tan(lean)  # its left face meets the neighbour's top corner
    tall = bpy.data.objects["BookTall"]
    tall.rotation_euler = (0, -lean, 0)
    tall.location = (pivot + T / 2 * math.cos(lean), 0, T / 2 * math.sin(lean))

    T = BOOKS["BookPaperback"][2]
    flat = bpy.data.objects["BookPaperback"]
    flat.rotation_euler = (0, math.radians(-90), math.radians(-6))  # front cover up, spine to the front
    flat.location = (-0.02, 0, T / 2)


def frame(cam, objs, toward):
    """Aim the camera at the objects along `toward` and crop the render to them."""
    scene = bpy.context.scene
    bpy.context.view_layer.update()  # the staging moved things: refresh their world matrices
    pts = [o.matrix_world @ v.co for o in objs for v in o.data.vertices]
    lo = Vector([min(p[i] for p in pts) for i in range(3)])
    hi = Vector([max(p[i] for p in pts) for i in range(3)])
    centre = (lo + hi) / 2
    radius = max((p - centre).length for p in pts)
    cam.data.lens, cam.data.sensor_width = 50, 36
    cam.data.clip_start = 0.01  # the ball's camera stands closer than the default 0.1
    half = math.atan(18 / 50)
    cam.location = centre + toward.normalized() * radius / math.sin(half) * 1.02
    cam.rotation_euler = (centre - cam.location).to_track_quat("-Z", "Y").to_euler()
    bpy.context.view_layer.update()

    scene.render.resolution_x = scene.render.resolution_y = 1000
    seen = [world_to_camera_view(scene, cam, p) for p in pts]
    x0, x1 = min(s.x for s in seen) - MARGIN, max(s.x for s in seen) + MARGIN
    y0, y1 = min(s.y for s in seen) - MARGIN, max(s.y for s in seen) + MARGIN
    size = min(4000, math.ceil(LONGEST / max(x1 - x0, y1 - y0)))
    scene.render.resolution_x = scene.render.resolution_y = size
    r = scene.render
    r.use_border, r.use_crop_to_border = True, True
    r.border_min_x, r.border_max_x = max(0.0, x0), min(1.0, x1)
    r.border_min_y, r.border_max_y = max(0.0, y0), min(1.0, y1)


def sun(name, toward, strength):
    data = bpy.data.lights.new(name, "SUN")
    data.energy, data.angle = strength, math.radians(6)
    obj = bpy.data.objects.new(name, data)
    bpy.context.scene.collection.objects.link(obj)
    obj.rotation_euler = (-toward.normalized()).to_track_quat("-Z", "Y").to_euler()  # shines along its -Z
    return obj


def render_all():
    scene, r = bpy.context.scene, bpy.context.scene.render
    BUILD["build"]()
    dress_books()

    background = next(n for n in scene.world.node_tree.nodes if n.type == "BACKGROUND")
    saved = {
        "camera": scene.camera, "engine": r.engine, "film": r.film_transparent,
        "res": (r.resolution_x, r.resolution_y, r.resolution_percentage),
        "border": (r.use_border, r.use_crop_to_border, r.border_min_x, r.border_max_x, r.border_min_y, r.border_max_y),
        "format": (r.image_settings.file_format, r.image_settings.color_mode),
        "view": scene.view_settings.view_transform, "path": r.filepath,
        "world": (tuple(background.inputs["Color"].default_value), background.inputs["Strength"].default_value),
        "hidden": {o.name: o.hide_render for o in scene.objects},
    }
    cam = bpy.data.objects.new("PropsCamera", bpy.data.cameras.new("PropsCamera"))
    scene.collection.objects.link(cam)
    lights = [sun("PropsKey", Vector((-0.6, -1.0, 1.3)), 3.0), sun("PropsRim", Vector((0.5, 1.0, 0.8)), 1.5)]
    try:
        scene.camera, r.film_transparent, r.resolution_percentage = cam, True, 100
        r.image_settings.file_format, r.image_settings.color_mode = "PNG", "RGBA"
        try:
            scene.view_settings.view_transform = "Standard"  # keeps the brand colors as they are
        except TypeError:
            pass
        background.inputs["Color"].default_value = srgb("#E8E0CF")  # a warm fill from every side
        background.inputs["Strength"].default_value = 0.6
        os.makedirs(OUT, exist_ok=True)
        for file, (names, toward) in SHOTS.items():
            objs = [bpy.data.objects[n] for n in names]
            if "LampPendantCord" in names:
                bpy.data.objects["LampPendantCord"].scale.z = 0.35
            for o in scene.objects:
                o.hide_render = o not in objs and o not in lights
            frame(cam, [o for o in objs if o.type == "MESH"], toward)
            r.filepath = os.path.join(OUT, file + ".png")
            bpy.ops.render.render(write_still=True)
            print("Props: rendered", r.filepath)
    finally:
        for o in [cam] + lights:
            data, kind = o.data, o.type
            bpy.data.objects.remove(o)
            (bpy.data.cameras if kind == "CAMERA" else bpy.data.lights).remove(data)
        scene.camera, r.engine, r.film_transparent = saved["camera"], saved["engine"], saved["film"]
        r.resolution_x, r.resolution_y, r.resolution_percentage = saved["res"]
        r.use_border, r.use_crop_to_border, r.border_min_x, r.border_max_x, r.border_min_y, r.border_max_y = saved["border"]
        r.image_settings.file_format, r.image_settings.color_mode = saved["format"]
        scene.view_settings.view_transform, r.filepath = saved["view"], saved["path"]
        background.inputs["Color"].default_value, background.inputs["Strength"].default_value = saved["world"]
        for name, hidden in saved["hidden"].items():
            if name in scene.objects:
                scene.objects[name].hide_render = hidden
        BUILD["build"]()
        for mat in [m for m in bpy.data.materials if m.users == 0 and m.name.startswith(("BookCover.", "BookSpine."))]:
            bpy.data.materials.remove(mat)


if __name__ == "__main__":
    render_all()
