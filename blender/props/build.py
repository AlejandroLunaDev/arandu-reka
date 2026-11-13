"""Build the Arandu room props in the open Blender scene.

Run it inside Blender, for example through the Blender MCP:
    import runpy; runpy.run_path("<repo>/blender/props/build.py", run_name="__main__")

Units are metres, Z is up and the front of every prop faces -Y, toward the camera. The props share
the cat's scale: Arandu sits about 0.5 tall. Each prop is one mesh object whose origin is where the
web places it:
- The books, PlantPot, YarnBall, Ball and the table lamps: the centre of the base, on Z = 0.
- The shelves (see SHELVES): the centre of the plank's top, so whatever sits on one goes at the
  shelf's own height.
- LampPendant: the top of the shade. Its child LampPendantCord rises 1 m from there: scale it on
  Z (Y on the web) to the length the page needs.
Every lamp carries an empty named <lamp>Light where the bulb is, for the web's point light. Lamps
are built switched off: the web lights them by giving "LampBulb" and "LampShadeInner" an emissive
color.

The books (see BOOKS) are blanks in several proportions that the web dresses through canvas
textures. Each one stands with its spine to the front. "BookCover" maps each cover to the full 0-1
UV square, the spine at u = 0 on the front (+X) cover; "BookSpine" maps the spine with u across
it, left to right seen from the front, and v up.

The plant's vertices carry "_sway", 0 at the pot rising to 1 at the vine tips, for a wind shader.
It is made for a shelf: stand it POT_EDGE behind the shelf's front edge.
Everything the script creates lives in the "Props" collection, which it rebuilds on every run.
"""

import math
import random

import bmesh
import bpy
from mathutils import Matrix, Vector

COLL = "Props"

# ---------------------------------------------------------------- palette (ds/tokens.css)


def srgb(hex_color):
    """Brand hex (sRGB) to the linear RGBA Blender stores."""
    h = hex_color.lstrip("#")
    out = []
    for i in (0, 2, 4):
        c = int(h[i:i + 2], 16) / 255
        out.append(c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4)
    return (out[0], out[1], out[2], 1.0)


MATERIALS = {  # name: (color, roughness, metallic)
    "BookCover": (srgb("#6B3FA0"), 0.6, 0.0),  # violet-600
    "BookSpine": (srgb("#6B3FA0"), 0.6, 0.0),
    "BookPages": (srgb("#E8E0CF"), 0.85, 0.0),  # cream-200
    "ShelfWood": (srgb("#3A3645"), 0.7, 0.0),  # ink-700
    "ShelfBracket": (srgb("#6F6880"), 0.45, 0.5),  # ink-500
    "LampShade": (srgb("#DDD3C0"), 0.8, 0.0),  # cream-300
    "LampShadeInner": (srgb("#F1EBDD"), 0.9, 0.0),  # cream-100
    "LampBulb": (srgb("#3A3645"), 0.3, 0.0),  # ink-700 while off, amber-300 when lit
    "LampMetal": (srgb("#57525F"), 0.4, 0.6),  # ink-600
    "LampCord": (srgb("#6F6880"), 0.6, 0.0),
    "LampAccent": (srgb("#D99A32"), 0.35, 0.7),  # amber-500 brass
    "LampBodyViolet": (srgb("#6B3FA0"), 0.35, 0.0),
    "LampBodyAmber": (srgb("#B97F22"), 0.35, 0.0),  # amber-600
    "PotCeramic": (srgb("#6B3FA0"), 0.55, 0.0),
    "PotSoil": (srgb("#2A2018"), 0.95, 0.0),
    "Leaf": (srgb("#3D8B5A"), 0.55, 0.0),
    "LeafDark": (srgb("#2B6544"), 0.55, 0.0),
    "Stem": (srgb("#47703F"), 0.7, 0.0),
    "Yarn": (srgb("#D99A32"), 0.95, 0.0),  # amber-500, as on the landing
    "YarnDark": (srgb("#8A5A12"), 0.95, 0.0),  # amber-700
    "BallMain": (srgb("#9B72CF"), 0.4, 0.0),  # violet-400
    "BallStripe": (srgb("#F1EBDD"), 0.4, 0.0),
}


def material(name):
    color, roughness, metallic = MATERIALS[name]
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Base Color"].default_value = color
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = metallic
    return mat


# ---------------------------------------------------------------- mesh building


class Part:
    """Faces with a material each, optional UVs and "_sway", joined into one mesh object."""

    def __init__(self):
        self.v, self.f, self.m, self.uv, self.sway, self.mats = [], [], [], [], [], []

    def add(self, verts, faces, mat, uvs=None, sway=0.0):
        """mat is one material name or one per face; sway is a number or a function of the vertex."""
        base = len(self.v)
        for p in verts:
            p = Vector(p)
            self.v.append(p)
            self.sway.append(sway(p) if callable(sway) else sway)
        for i, face in enumerate(faces):
            name = mat if isinstance(mat, str) else mat[i]
            if name not in self.mats:
                self.mats.append(name)
            self.f.append(tuple(base + j for j in face))
            self.m.append(self.mats.index(name))
            self.uv.append(uvs[i] if uvs else [(0.0, 0.0)] * len(face))

    def build(self, name, coll, uv=False, sway=False):
        me = bpy.data.meshes.new(name)
        me.from_pydata([tuple(p) for p in self.v], [], self.f)
        me.polygons.foreach_set("material_index", self.m)
        me.polygons.foreach_set("use_smooth", [True] * len(self.f))
        if uv:
            me.uv_layers.new(name="UVMap").data.foreach_set("uv", [c for face in self.uv for corner in face for c in corner])
        if sway:
            me.attributes.new("_sway", "FLOAT", "POINT").data.foreach_set("value", self.sway)
        bm = bmesh.new()
        bm.from_mesh(me)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        bm.to_mesh(me)
        bm.free()
        for n in self.mats:
            me.materials.append(material(n))
        obj = bpy.data.objects.new(name, me)
        coll.objects.link(obj)
        # Face-area weighted normals keep flat faces flat next to their rounded edges.
        obj.modifiers.new("WeightedNormal", "WEIGHTED_NORMAL").keep_sharp = True
        return obj


def moved(verts, m):
    return [tuple(m @ Vector(v)) for v in verts]


def lathe(profile, mats, seg=48, closed=False):
    """Revolve (r, z) points about Z; r == 0 makes a pole. mats: one name, or one per profile segment."""
    verts, faces, face_mats, rings = [], [], [], []
    for r, z in profile:
        if r < 1e-6:
            rings.append([len(verts)])
            verts.append((0.0, 0.0, z))
        else:
            rings.append(list(range(len(verts), len(verts) + seg)))
            verts.extend((r * math.cos(2 * math.pi * j / seg), r * math.sin(2 * math.pi * j / seg), z) for j in range(seg))
    pairs = list(range(len(rings) - 1)) + ([len(rings) - 1] if closed else [])
    for k in pairs:
        a, b = rings[k], rings[(k + 1) % len(rings)]
        for j in range(seg):
            j2 = (j + 1) % seg
            if len(a) == 1:
                faces.append((a[0], b[j], b[j2]))
            elif len(b) == 1:
                faces.append((a[j], a[j2], b[0]))
            else:
                faces.append((a[j], a[j2], b[j2], b[j]))
            face_mats.append(mats if isinstance(mats, str) else mats[k])
    return verts, faces, face_mats


def sphere(center, radius, lats=None, seg=32):
    lats = lats or [-90 + 180 * i / 16 for i in range(17)]
    profile = [(radius * math.cos(math.radians(a)), radius * math.sin(math.radians(a))) for a in lats]
    return profile, Matrix.Translation(center)


def tube(points, radius, sides=8, closed=False):
    """Sweep a circle along points. radius is a number or one per point."""
    pts = [Vector(p) for p in points]
    radii = radius if isinstance(radius, (list, tuple)) else [radius] * len(pts)
    count = len(pts)
    t = (pts[1] - pts[0]).normalized()
    n = t.cross(Vector((0, 0, 1)) if abs(t.z) < 0.9 else Vector((1, 0, 0))).normalized()
    verts, faces = [], []
    for i, p in enumerate(pts):
        if closed:
            t = (pts[(i + 1) % count] - pts[i - 1]).normalized()
        else:
            t = (pts[min(i + 1, count - 1)] - pts[max(i - 1, 0)]).normalized()
        n = (n - t * n.dot(t)).normalized()  # carry the frame along without twisting it
        b = t.cross(n)
        for s in range(sides):
            a = 2 * math.pi * s / sides
            verts.append(tuple(p + (n * math.cos(a) + b * math.sin(a)) * radii[i]))
    for i in range(count if closed else count - 1):
        i2 = (i + 1) % count
        for s in range(sides):
            s2 = (s + 1) % sides
            faces.append((i * sides + s, i * sides + s2, i2 * sides + s2, i2 * sides + s))
    if not closed:
        for i in (0, count - 1):
            c = len(verts)
            verts.append(tuple(pts[i]))
            faces.extend((c, i * sides + s, i * sides + (s + 1) % sides) for s in range(sides))
    return verts, faces


def rbox(size, radius, center, seg=3):
    """A box with rounded edges."""
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co = Vector((v.co.x * size[0], v.co.y * size[1], v.co.z * size[2])) + Vector(center)
    bmesh.ops.bevel(bm, geom=list(bm.edges), offset=radius, segments=seg, profile=0.5, affect="EDGES", clamp_overlap=True)
    index = {v: i for i, v in enumerate(bm.verts)}
    verts = [tuple(v.co) for v in bm.verts]
    faces = [tuple(index[v] for v in f.verts) for f in bm.faces]
    bm.free()
    return verts, faces


def spline(ctrl, n):
    """n points on a Catmull-Rom curve through ctrl."""
    p = [Vector(c) for c in ctrl]
    p = [2 * p[0] - p[1]] + p + [2 * p[-1] - p[-2]]
    spans = len(ctrl) - 1
    out = []
    for i in range(n):
        t = i / (n - 1) * spans
        k = min(int(t), spans - 1)
        u = t - k
        p0, p1, p2, p3 = p[k], p[k + 1], p[k + 2], p[k + 3]
        out.append(0.5 * (2 * p1 + (p2 - p0) * u + (2 * p0 - 5 * p1 + 4 * p2 - p3) * u * u + (3 * p1 - p0 - 3 * p2 + p3) * u ** 3))
    return out


def add_lathe(part, profile, mats, m=Matrix(), seg=48, closed=False, sway=0.0):
    verts, faces, face_mats = lathe(profile, mats, seg, closed)
    part.add(moved(verts, m), faces, face_mats, sway=sway)


def add_sphere(part, center, radius, mat, lats=None, m=Matrix()):
    profile, at = sphere(center, radius, lats)
    add_lathe(part, profile, mat, m @ at, seg=32)


def light(name, parent, at):
    empty = bpy.data.objects.new(name, None)
    empty.empty_display_size = 0.03
    parent.users_collection[0].objects.link(empty)
    empty.parent = parent
    empty.location = at
    return empty


# ---------------------------------------------------------------- props


BOOKS = {  # name: height, depth (spine to fore-edge, along Y), thickness (along X), spine corner radius,
    #         board thickness, board overhang past the pages
    "Book": (0.40, 0.28, 0.075, 0.03, 0.007, 0.008),
    "BookTall": (0.44, 0.30, 0.06, 0.026, 0.007, 0.008),
    "BookSlim": (0.38, 0.26, 0.042, 0.018, 0.005, 0.007),
    "BookThick": (0.37, 0.27, 0.11, 0.045, 0.008, 0.009),
    "BookShort": (0.30, 0.21, 0.07, 0.028, 0.006, 0.007),
    "BookPaperback": (0.33, 0.22, 0.05, 0.006, 0.0025, 0.0),  # soft cover, flush with its pages
}


def arc(r, cx, cy, a0, a1, n):
    return [(cx + r * math.cos(a0 + (a1 - a0) * i / n), cy + r * math.sin(a0 + (a1 - a0) * i / n)) for i in range(n + 1)]


def prism(outline, z0, z1):
    """Extrude a counter-clockwise outline from z0 to z1: its sides, then the top and bottom caps."""
    n = len(outline)
    verts = [(x, y, z0) for x, y in outline] + [(x, y, z1) for x, y in outline]
    faces = [(i, (i + 1) % n, n + (i + 1) % n, n + i) for i in range(n)]
    return verts, faces + [tuple(range(n, 2 * n)), tuple(reversed(range(n)))]


def book(coll, name):
    """A blank book: two covers and a rounded spine around a page block, the block rounded to match."""
    H, D, T, RS, C, O = BOOKS[name]
    gap = max(O, 0.0015)  # how far the pages sit inside the covers, so their faces never coincide
    cy, left, right = -D / 2 + RS, -T / 2 + RS, T / 2 - RS  # centres of the spine's two rounded corners

    spine = arc(RS, left, cy, math.pi, 1.5 * math.pi, 8) + arc(RS, right, cy, 1.5 * math.pi, 2 * math.pi, 8)
    inside = arc(RS - C, right, cy, 2 * math.pi, 1.5 * math.pi, 6) + arc(RS - C, left, cy, 1.5 * math.pi, math.pi, 6)
    inner = [(T / 2 - C, D / 2)] + inside + [(-T / 2 + C, D / 2)]  # the cover's inside, a board's width in
    outline = [(-T / 2, D / 2)] + spine + [(T / 2, D / 2)] + inner  # counter-clockwise seen from +Z
    n = len(outline)
    first, last = 1, len(spine)  # outline indices where the spine starts and ends

    lengths = [0.0]
    for i in range(first, last):
        lengths.append(lengths[-1] + math.dist(outline[i], outline[i + 1]))

    flat = D - RS  # covers map their flat part, from the spine's edge to the fore-edge
    blank = (0.995, 0.005)

    def corner_uv(i, side, z):
        x, y = outline[i]
        v = z / H
        if side == "back":
            return ((D / 2 - y) / flat, v)
        if side == "front":
            return ((y + D / 2 - RS) / flat, v)
        if side == "spine":
            return (lengths[i - first] / lengths[-1], v)
        return blank

    verts, faces = prism(outline, 0.0, H)
    mats, uvs = [], []
    for i in range(n):
        j = (i + 1) % n
        side = "back" if i == 0 else "spine" if first <= i < last else "front" if i == last else "edge"
        mats.append("BookSpine" if side == "spine" else "BookCover")
        uvs.append([corner_uv(i, side, 0), corner_uv(j, side, 0), corner_uv(j, side, H), corner_uv(i, side, H)])
    mats += ["BookCover", "BookCover"]
    uvs += [[blank] * n, [blank] * n]

    r = RS - C - 0.0015
    block = arc(r, left, cy, math.pi, 1.5 * math.pi, 6) + arc(r, right, cy, 1.5 * math.pi, 2 * math.pi, 6)
    block = [(-T / 2 + C + 0.0015, D / 2 - gap)] + block + [(T / 2 - C - 0.0015, D / 2 - gap)]

    p = Part()
    p.add(verts, faces, mats, uvs)
    p.add(*prism(block, gap, H - gap), "BookPages")
    return p.build(name, coll, uv=True)


SHELVES = {"ShelfLarge": 1.6, "ShelfMedium": 1.0, "ShelfSmall": 0.55}  # name: length. All share one depth,
# deep enough for the tallest book and the plant pot.


def shelf(coll, name):
    """A wall plank on two L brackets. Its back rests on the wall at +Y."""
    L, W, TH = SHELVES[name], 0.34, 0.05
    p = Part()
    p.add(*rbox((L, W, TH), 0.008, (0, 0, -TH / 2)), "ShelfWood")
    inset = min(0.25, 0.16 * L)  # how far each bracket sits in from its end
    for x in (-L / 2 + inset, L / 2 - inset):
        p.add(*rbox((0.03, 0.022, 0.2), 0.004, (x, W / 2 - 0.011, -TH - 0.1), seg=2), "ShelfBracket")
        p.add(*rbox((0.03, W - 0.05, 0.018), 0.004, (x, 0.025, -TH - 0.009), seg=2), "ShelfBracket")
        p.add(*tube([(x, W / 2 - 0.02, -TH - 0.17), (x, -0.07, -TH - 0.016)], 0.006), "ShelfBracket")
    return p.build(name, coll)


def shade_profile(top, bottom, height, thick, n=10, flare=1.35):
    """A bell shade closed at the top, open below, hanging from z = 0. Returns profile and materials."""
    outer = [(top + (bottom - top) * (t ** flare), -height * t) for t in (i / n for i in range(n + 1))]
    inner = [(r - thick, min(z, -thick)) for r, z in reversed(outer)]
    profile = [(0.0, 0.0)] + outer + inner + [(0.0, -thick)]
    mats = ["LampShade"] * (n + 2) + ["LampShadeInner"] * (n + 1)
    return profile, mats


def lamp_pendant(coll):
    p = Part()
    add_lathe(p, *shade_profile(0.09, 0.21, 0.18, 0.006))
    add_lathe(p, [(0.0, 0.0), (0.012, 0.0), (0.012, 0.022), (0.0, 0.022)], "LampMetal", seg=24)  # collar
    add_lathe(p, [(0.0, -0.006), (0.02, -0.006), (0.02, -0.125), (0.0, -0.125)], "LampMetal", seg=24)  # socket
    add_sphere(p, (0, 0, -0.17), 0.05, "LampBulb")
    lamp = p.build("LampPendant", coll)
    cord = Part()
    cord.add(*tube([(0, 0, 0.0), (0, 0, 1.0)], 0.004), "LampCord")
    cord = cord.build("LampPendantCord", coll)
    cord.parent = lamp
    light("LampPendantLight", lamp, (0, 0, -0.15))
    return lamp


def lamp_mushroom(coll):
    """A rounded dome on a slim stem."""
    p = Part()
    add_lathe(p, [(0.0, 0.0), (0.08, 0.0), (0.088, 0.006), (0.088, 0.016), (0.08, 0.024), (0.0, 0.026)], "LampBodyViolet")
    add_lathe(p, [(0.0, 0.02), (0.016, 0.02), (0.013, 0.2), (0.0, 0.2)], "LampBodyViolet", seg=24)
    n = 12
    outer = [(0.14 * math.cos(a), 0.19 + 0.11 * math.sin(a)) for a in (math.pi / 2 * (1 - i / n) for i in range(n + 1))]
    inner = [(0.134 * math.cos(a), 0.19 + 0.104 * math.sin(a)) for a in (math.pi / 2 * i / n for i in range(n + 1))]
    add_lathe(p, outer + inner, ["LampShade"] * (n + 1) + ["LampShadeInner"] * n)
    add_sphere(p, (0, 0, 0.215), 0.03, "LampBulb")
    lamp = p.build("LampMushroom", coll)
    light("LampMushroomLight", lamp, (0, 0, 0.22))
    return lamp


def lamp_classic(coll):
    """A ceramic vase base under a tapered drum shade."""
    p = Part()
    body = spline([(0.055, 0.0), (0.07, 0.014), (0.084, 0.06), (0.084, 0.1), (0.062, 0.14), (0.036, 0.165), (0.03, 0.18)], 28)
    add_lathe(p, [(0.0, 0.0)] + [tuple(v) for v in body] + [(0.036, 0.182), (0.036, 0.19), (0.0, 0.19)], "LampBodyAmber")
    add_lathe(p, [(0.0, 0.19), (0.007, 0.19), (0.007, 0.40), (0.0, 0.40)], "LampAccent", seg=16)
    drum = [(0.15, 0.25), (0.10, 0.41), (0.095, 0.41), (0.145, 0.25)]
    add_lathe(p, drum, ["LampShade", "LampShade", "LampShadeInner", "LampShade"], closed=True)
    for k in range(3):
        a = 2 * math.pi * k / 3
        p.add(*tube([(0, 0, 0.40), (0.095 * math.cos(a), 0.095 * math.sin(a), 0.405)], 0.003, sides=6), "LampAccent")
    add_sphere(p, (0, 0, 0.31), 0.035, "LampBulb")
    add_sphere(p, (0, 0, 0.415), 0.012, "LampAccent")
    lamp = p.build("LampClassic", coll)
    light("LampClassicLight", lamp, (0, 0, 0.31))
    return lamp


def lamp_desk(coll):
    """A reading lamp: two arms with brass joints and a small bell head aimed down at +X."""
    p = Part()
    add_lathe(p, [(0.0, 0.0), (0.075, 0.0), (0.08, 0.008), (0.078, 0.02), (0.07, 0.026), (0.0, 0.028)], "LampMetal")
    foot, elbow, wrist = Vector((-0.02, 0, 0.03)), Vector((-0.05, 0, 0.22)), Vector((0.09, 0, 0.29))
    p.add(*tube([foot, elbow], 0.008), "LampMetal")
    p.add(*tube([elbow, wrist], 0.008), "LampMetal")
    for at, r in ((foot, 0.014), (elbow, 0.016), (wrist, 0.014)):
        add_sphere(p, at, r, "LampAccent")
    head = Matrix.Translation(wrist + Vector((0.01, 0, -0.005))) @ Matrix.Rotation(math.radians(-40), 4, "Y")
    profile, mats = shade_profile(0.025, 0.075, 0.09, 0.004, n=8)
    add_lathe(p, profile, [m if m != "LampShade" else "LampBodyViolet" for m in mats], head)
    add_sphere(p, (0, 0, -0.06), 0.022, "LampBulb", m=head)
    lamp = p.build("LampDesk", coll)
    light("LampDeskLight", lamp, head @ Vector((0, 0, -0.07)))
    return lamp


def leaf(p, base, axis, normal, length, width, mat, sway):
    """A pothos leaf: heart-shaped, folded along the midrib, its tip curling back."""
    x = axis.normalized()
    n = (normal - x * normal.dot(x)).normalized()
    y = n.cross(x)
    rows = 6
    verts = []
    for i in range(rows):
        t = i / rows
        w = width * math.sin(math.pi * t ** 0.75) ** 0.9
        back = 0.14 * length * (1 - t) ** 4  # the lobes reach behind the stalk
        curl = -0.12 * length * t * t
        for side in (-1, 0, 1):
            along = t * length - (back if side else 0.0)
            lift = 0.18 * w if side == 0 else 0.0
            verts.append(base + x * along + y * (side * w) + n * (lift + curl))
    verts.append(base + x * length + n * (-0.12 * length))
    faces = []
    for i in range(rows - 1):
        a, b = 3 * i, 3 * (i + 1)
        faces += [(a, a + 1, b + 1, b), (a + 1, a + 2, b + 2, b + 1)]
    tip = 3 * rows
    a = 3 * (rows - 1)
    faces += [(a, a + 1, tip), (a + 1, a + 2, tip)]
    p.add(verts, faces, mat, sway=sway)


POT_EDGE = 0.12  # the pot's centre sits this far behind the front edge of the shelf it stands on


def plant_pot(coll):
    """A pothos in a ceramic pot, made for a shelf: its long vines fall off the front edge (-Y) and the
    side ones lie on the plank. Place the pot with its centre POT_EDGE behind the shelf's front edge."""
    rng = random.Random(3)
    up = Vector((0, 0, 1))

    def sway(v):
        return min(1.0, max(0.0, (0.16 - v.z) / 0.5)) ** 1.2

    def lying(v):
        return 0.1 * sway(v)

    p = Part()
    pot = [(0.0, 0.0), (0.066, 0.0), (0.072, 0.006), (0.088, 0.125), (0.097, 0.13), (0.099, 0.15),
           (0.092, 0.155), (0.086, 0.15), (0.084, 0.14), (0.0, 0.14)]
    add_lathe(p, pot, ["PotCeramic"] * 8 + ["PotSoil"])

    # (direction in degrees, -90 is the front; how far it falls below the shelf, or None if it lies on it;
    #  how far a lying vine trails along the plank)
    vines = [(-66, 0.42, 0), (-84, 0.22, 0), (-100, 0.34, 0), (-118, 0.5, 0),
             (-14, None, 0.16), (-166, None, 0.13), (24, None, 0.1), (156, None, 0.12)]
    for phi, hang, trail in vines:
        a = math.radians(phi)
        u, side = Vector((math.cos(a), math.sin(a), 0)), Vector((-math.sin(a), math.cos(a), 0))
        ctrl = [0.04 * u + 0.14 * up, 0.085 * u + 0.175 * up, 0.112 * u + 0.165 * up, 0.125 * u + 0.12 * up]
        if hang:  # out past the edge first, then down, so the vine never cuts into the plank
            for k in range(1, 5):
                t = k / 4
                x = 0.14 * u.x + 0.022 * math.sin(4.7 * t + a)
                ctrl.append(Vector((x, -(POT_EDGE + 0.02 + 0.015 * t), 0.12 - hang * t)))
        else:  # down the pot's side and along the plank
            ctrl += [0.115 * u + 0.06 * up, 0.14 * u + 0.0035 * up]
            for k in range(1, 4):
                t = k / 3
                ctrl.append((0.14 + trail * t) * u + side * (0.02 * math.sin(5 * t + a)) + 0.0035 * up)
        pts = spline(ctrl, 28)
        vine_sway = sway if hang else lying
        p.add(*tube(pts, [0.0032 - 0.0012 * i / 27 for i in range(28)], sides=6), "Stem", sway=vine_sway)

        walked, nxt, flip = 0.0, 0.03, 1
        total = sum((pts[i + 1] - pts[i]).length for i in range(27))
        for i in range(1, 27):
            walked += (pts[i] - pts[i - 1]).length
            if walked < nxt:
                continue
            nxt += 0.03 + rng.uniform(-0.006, 0.006)
            tangent = (pts[i + 1] - pts[i - 1]).normalized()
            axis = flip * tangent.cross(u) + 0.6 * tangent + 0.3 * u + Vector([rng.uniform(-0.15, 0.15) for _ in range(3)])
            size = 0.05 * (1 - 0.45 * walked / total)
            base, normal = pts[i], u + 0.3 * up
            if pts[i].z < 0.03:  # on the plank the leaves lie flat, just above it
                axis.z = 0.1 + 0.2 * abs(axis.z)
                base, normal = pts[i] + 0.007 * up, up + 0.2 * u
            leaf(p, base, axis, normal, size, 0.62 * size, rng.choice(["Leaf", "LeafDark"]), vine_sway)
            flip = -flip

    for k in range(11):  # the crown: leaves on short stalks, arching out of the soil
        a = math.radians(360 * k / 11 + rng.uniform(-14, 14))
        u = Vector((math.cos(a), math.sin(a), 0))
        root = rng.uniform(0.0, 0.05) * u + 0.14 * up
        base = root + rng.uniform(0.015, 0.045) * u + rng.uniform(0.025, 0.07) * up
        p.add(*tube([root, base], 0.0028, sides=6), "Stem")
        axis = rng.uniform(0.5, 1.0) * u + rng.uniform(0.3, 0.9) * up + Vector([rng.uniform(-0.2, 0.2) for _ in range(3)])
        size = rng.uniform(0.05, 0.075)
        leaf(p, base, axis, up + Vector([rng.uniform(-0.3, 0.3) for _ in range(3)]), size, 0.64 * size,
             rng.choice(["Leaf", "LeafDark"]), lambda v: 0.15 * min(1.0, max(0.0, (v.z - 0.15) / 0.08)))
    return p.build("PlantPot", coll, sway=True)


def yarn_ball(coll):
    """An amber ball of yarn wound with darker strands, its loose end trailing on the floor."""
    rng = random.Random(7)
    R, c = 0.1, Vector((0, 0, 0.1))
    p = Part()
    add_sphere(p, c, R, "Yarn")
    for k in range(16):
        axis = Vector([rng.gauss(0, 1) for _ in range(3)]).normalized()
        a = axis.cross(Vector((0, 0, 1)) if abs(axis.z) < 0.9 else Vector((1, 0, 0))).normalized()
        b = axis.cross(a)
        phase = rng.uniform(0, 6.28)
        ring = [c + (R + 0.002 + 0.0015 * math.sin(3 * th + phase)) * (a * math.cos(th) + b * math.sin(th))
                for th in (2 * math.pi * i / 48 for i in range(48))]
        p.add(*tube(ring, 0.0045, sides=6, closed=True), "YarnDark" if k % 3 == 0 else "Yarn")
    start = c + R * Vector((0.6, -0.7, -0.4)).normalized()
    trail = [start, (0.12, -0.1, 0.03), (0.2, -0.13, 0.005), (0.27, -0.08, 0.005), (0.33, -0.13, 0.005), (0.38, -0.11, 0.005)]
    p.add(*tube(spline(trail, 30), 0.0045, sides=6), "Yarn")
    return p.build("YarnBall", coll)


def ball(coll):
    """A small toy ball with one cream band, tipped for a playful look."""
    band = math.degrees(math.asin(0.012 / 0.045))
    lats = sorted({-90 + 180 * i / 16 for i in range(17)} | {-band, band})
    profile, _ = sphere((0, 0, 0), 0.045, lats)
    mats = ["BallStripe" if -band <= (lats[k] + lats[k + 1]) / 2 <= band else "BallMain" for k in range(len(lats) - 1)]
    p = Part()
    add_lathe(p, profile, mats, Matrix.Translation((0, 0, 0.045)) @ Matrix.Rotation(math.radians(30), 4, "Y"), seg=32)
    return p.build("Ball", coll)


# ---------------------------------------------------------------- assembly

LAYOUT = {  # where each prop stands in the Blender scene; the export puts every one at the origin
    **{name: (-2.35 + 0.15 * i, 0, 0) for i, name in enumerate(BOOKS)},
    "Ball": (-1.2, 0, 0),
    "YarnBall": (-0.9, 0, 0),
    "PlantPot": (-0.45, 0, 0.6),
    "LampMushroom": (0.0, 0, 0),
    "LampClassic": (0.45, 0, 0),
    "LampDesk": (0.9, 0, 0),
    "LampPendant": (1.45, 0, 0.9),
    "ShelfLarge": (-0.45, 0.05, 0.6),
    "ShelfMedium": (-0.45, 0.05, 1.15),
    "ShelfSmall": (-0.45, 0.05, 1.6),
}


def reset_collection():
    coll = bpy.data.collections.get(COLL)
    if coll:
        meshes = {o.data for o in coll.objects if isinstance(o.data, bpy.types.Mesh)}
        for o in list(coll.objects):
            bpy.data.objects.remove(o)
        # The glTF exporter can leave a user on a mesh: remove the old meshes whatever their count,
        # or the new ones come out named "Book.001".
        for me in meshes:
            if not any(o.data == me for o in bpy.data.objects):
                bpy.data.meshes.remove(me, do_unlink=True)
    else:
        coll = bpy.data.collections.new(COLL)
        bpy.context.scene.collection.children.link(coll)
    return coll


def build():
    if bpy.context.object and bpy.context.object.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")
    coll = reset_collection()
    props = [book(coll, name) for name in BOOKS]
    props += [shelf(coll, name) for name in SHELVES]
    props += [f(coll) for f in (plant_pot, lamp_pendant, lamp_mushroom, lamp_classic, lamp_desk, yarn_ball, ball)]
    for obj in props:
        obj.location = LAYOUT[obj.name]
    tris = sum(sum(len(f.vertices) - 2 for f in o.data.polygons) for o in coll.objects if o.type == "MESH")
    print("Props: %d objects, %d triangles" % (len(coll.objects), tris))
    return props


if __name__ == "__main__":
    build()
