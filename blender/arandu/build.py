"""Build Arandu, the black long-haired cat, in the open Blender scene.

Run it inside Blender, for example through the Blender MCP:
    import runpy; runpy.run_path("<repo>/blender/arandu/build.py", run_name="__main__")

Units are metres. Z is up, the cat faces +X and its feet rest on Z = 0 around the origin.
Everything the script creates lives in the "Arandu" collection, which it rebuilds on every run.

Modeling: the body, head, ears and a few big fur tufts are closed shapes fused into one smooth
surface through a signed distance field (Geometry Nodes SDF grids: union, fillet, mean). The long
fur lives in the silhouette (cheeks, chest bib, neck ruff, hind legs, tail plume), never as
separate strands. Eyes, lids, nose, mouth and whiskers are separate parts with their own materials.

The web draws the moving fur on top with shell layers. For that, every fur vertex carries two
attributes: "_fur", the fur length from 0 to 1, and "_comb", the unit direction the fur lies in.

Rig rules, shared with the web code:
- Face bones (head, ears, eyes, pupils, lids) point straight up with no roll, so in glTF their rest
  rotation is identity and their local axes are the world's: x forward, y up, z the cat's right.
- Limb, spine and tail bones follow the body, so bone-heat skinning gives smooth weights.
- Clips never key the face bones: the page drives gaze, blinks, moods and the head look-at.
"""

import math

import bmesh
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

COLL = "Arandu"

# ---------------------------------------------------------------- palette (brand board v2)


def srgb(hex_color):
    """Brand hex (sRGB) to the linear RGBA that Blender color attributes store."""
    h = hex_color.lstrip("#")
    out = []
    for i in (0, 2, 4):
        c = int(h[i:i + 2], 16) / 255
        out.append(c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4)
    return (out[0], out[1], out[2], 1.0)


FUR_LOW = srgb("#0A0A0B")  # belly and the undersides
FUR = srgb("#0F0F11")
FUR_TOP = srgb("#18181B")  # back and crown: neutral black, lit by the fur sheen on the web
EAR_IN = srgb("#8456BC")
AMBER = srgb("#F2B53C")
AMBER_TOP = srgb("#D99A32")
AMBER_LOW = srgb("#F8CB62")
PUPIL = srgb("#09090D")
GLINT = srgb("#F1EBDD")
NOSE = srgb("#6B3FA0")
WHISKER = srgb("#B8B8BC")

# Material slots, in this order. The names reach three.js unchanged.
MATERIALS = ["AranduFur", "AranduEye", "AranduPupil", "AranduGlint", "AranduNose", "AranduWhisker"]
M_FUR, M_EYE, M_PUPIL, M_GLINT, M_NOSE, M_WHISKER = range(6)

# ---------------------------------------------------------------- proportions (chibi)

HEAD_C = Vector((0.235, 0.0, 0.36))  # head centre
HEAD_R = (0.135, 0.166, 0.14)  # head semi-axes: depth, width, height
HEAD_PIVOT = Vector((0.17, 0.0, 0.29))  # where the neck meets the head
EYE_R = 0.052
EYE_SINK = 0.024  # how far the eye centre sits under the head surface
LID_OPEN_UP = math.radians(50)  # upper lid edge at rest, measured up from the eye's forward axis
LID_OPEN_LOW = math.radians(-52)
EAR_H, EAR_W, EAR_T = 0.13, 0.12, 0.024  # ear height, width at the base, shell thickness
EAR_ARC = math.radians(105)  # half the angle the ear shell wraps around its axis

TAIL_CTRL = (Vector((-0.19, 0.0, 0.21)), Vector((-0.37, 0.0, 0.24)), Vector((-0.38, 0.0, 0.48)))

VOXEL = 0.003  # SDF voxel size
BODY_TRIS = 9000  # triangle budget of the fused surface

# ---------------------------------------------------------------- small math


def smooth(e0, e1, x):
    t = max(0.0, min(1.0, (x - e0) / (e1 - e0)))
    return t * t * (3 - 2 * t)


def mix(a, b, t):
    return tuple(a[i] + (b[i] - a[i]) * t for i in range(len(a)))


def unit(theta, phi):
    return Vector((math.sin(theta) * math.cos(phi), math.sin(theta) * math.sin(phi), math.cos(theta)))


def bezier(ctrl, t):
    a, b, c = ctrl
    return a * (1 - t) ** 2 + b * (2 * t * (1 - t)) + c * (t * t)


def bezier_tangent(ctrl, t):
    a, b, c = ctrl
    return ((b - a) * (2 * (1 - t)) + (c - b) * (2 * t)).normalized()


def tangent_frame(n):
    """Two unit vectors perpendicular to n."""
    helper = Vector((0, 0, 1)) if abs(n.z) < 0.9 else Vector((1, 0, 0))
    s = n.cross(helper).normalized()
    return s, n.cross(s).normalized()


# ---------------------------------------------------------------- closed shapes


def sphere_grid(seg, rings, fn):
    """A closed sphere-topology surface. fn(theta, phi) -> position. Returns (verts, faces)."""
    verts = [fn(0.0, 0.0)]
    for i in range(1, rings):
        th = math.pi * i / rings
        verts += [fn(th, 2 * math.pi * j / seg) for j in range(seg)]
    verts.append(fn(math.pi, 0.0))
    bottom = len(verts) - 1

    def row(i, j):
        return 1 + i * seg + j

    faces = []
    for j in range(seg):
        k = (j + 1) % seg
        faces.append((0, row(0, j), row(0, k)))
        for i in range(rings - 2):
            faces.append((row(i, j), row(i + 1, j), row(i + 1, k), row(i, k)))
        faces.append((bottom, row(rings - 2, k), row(rings - 2, j)))
    return verts, faces


def ellipsoid(centre, semi, seg=32, rings=16):
    c, (a, b, h) = Vector(centre), semi
    return sphere_grid(seg, rings, lambda th, ph: c + Vector((
        a * math.sin(th) * math.cos(ph), b * math.sin(th) * math.sin(ph), h * math.cos(th))))


def ellipsoid_surface(centre, semi, direction):
    """Point and normal of an ellipsoid surface along a direction from its centre."""
    d = Vector(direction).normalized()
    a, b, h = semi
    t = 1 / math.sqrt((d.x / a) ** 2 + (d.y / b) ** 2 + (d.z / h) ** 2)
    n = Vector((d.x / a ** 2, d.y / b ** 2, d.z / h ** 2)).normalized()
    return Vector(centre) + d * t, n


def tuft(base, normal, flow, length, width, flat=0.55, lift=0.3, flat_axis=None, sides=14, rings=12):
    """A big soft fur tuft: rooted under the surface at base, leaving along the normal, bending
    toward flow and tapering to a point. Thin along flat_axis (the surface normal by default),
    so tufts lie on the body like layered fur."""
    n = Vector(normal).normalized()
    f = Vector(flow).normalized()
    d0 = (n * lift + f * (1 - lift)).normalized()
    p0 = base - n * (width * 0.5)
    p2 = base + f * length
    p1 = p0 + d0 * (length * 0.45)
    ctrl = (p0, p1, p2)
    ref = Vector(flat_axis or n).normalized()
    verts = [p0 - bezier_tangent(ctrl, 0.0) * (width * 0.6)]
    rows = []
    for i in range(rings):
        t = i / rings
        c = bezier(ctrl, t)
        tg = bezier_tangent(ctrl, t)
        side = tg.cross(ref)
        side = side.normalized() if side.length > 1e-6 else tangent_frame(tg)[0]
        up = side.cross(tg).normalized()
        r = width * (1 - t) ** 0.9 * (1 + 0.4 * math.sin(math.pi * t))
        row = []
        for j in range(sides):
            a = 2 * math.pi * j / sides
            row.append(len(verts))
            verts.append(c + side * (math.cos(a) * r) + up * (math.sin(a) * r * flat))
        rows.append(row)
    verts.append(p2)
    tip = len(verts) - 1
    faces = []
    for j in range(sides):
        k = (j + 1) % sides
        faces.append((0, rows[0][k], rows[0][j]))
        for i in range(rings - 1):
            faces.append((rows[i][j], rows[i][k], rows[i + 1][k], rows[i + 1][j]))
        faces.append((rows[-1][j], rows[-1][k], tip))
    return verts, faces


def sweep(points, radii):
    """Spheres along a path; fused by the SDF into a smooth tube."""
    verts, faces = [], []
    for p, r in zip(points, radii):
        v, f = ellipsoid(p, (r, r, r), seg=16, rings=10)
        o = len(verts)
        verts += v
        faces += [tuple(i + o for i in face) for face in f]
    return verts, faces


class Shape:
    """Closed parts grouped by owner (head, earL, earR, body); the owners drive the skin weights."""

    def __init__(self):
        self.parts = {}

    def add(self, owner, part):
        verts, faces = part
        V, F = self.parts.setdefault(owner, ([], []))
        o = len(V)
        V.extend(verts)
        F.extend(tuple(i + o for i in face) for face in faces)

    def merged(self):
        verts, faces = [], []
        for V, F in self.parts.values():
            o = len(verts)
            verts += V
            faces += [tuple(i + o for i in face) for face in F]
        return verts, faces

    def bvh(self, owner):
        V, F = self.parts[owner]
        return BVHTree.FromPolygons(V, F)


# ---------------------------------------------------------------- the head


BUMPS = [  # direction, height, angular spread
    (Vector((1, 0, -0.32)).normalized(), 0.016, 0.30),  # muzzle
    (Vector((1, 0.22, -0.40)).normalized(), 0.009, 0.15),  # whisker pads
    (Vector((1, -0.22, -0.40)).normalized(), 0.009, 0.15),
    (Vector((1, 0, -0.75)).normalized(), 0.007, 0.16),  # chin
]


def head_offset(n):
    """Head surface point for the unit direction n, relative to HEAD_C."""
    a, b, c = HEAD_R
    p = Vector((a * n.x, b * n.y, c * n.z))
    if n.x > 0:
        p.x *= 1 - 0.10 * smooth(0.35, 1.0, n.x)  # a flat, friendly face
    if n.z > 0.55:
        p.z -= 0.012 * smooth(0.55, 1.0, n.z)  # a lower crown
    p.y *= 1 + 0.08 * smooth(0.25, 0.85, abs(n.y)) * math.exp(-((n.z + 0.25) / 0.35) ** 2)  # full cheeks
    for d, height, spread in BUMPS:
        ang = math.acos(max(-1.0, min(1.0, n.dot(d))))
        p += n * height * math.exp(-((ang / spread) ** 2))
    return p


def head_point(n):
    return HEAD_C + head_offset(n)


def head_normal(n):
    a, b, c = HEAD_R
    p = head_offset(n)
    return Vector((p.x / a ** 2, p.y / b ** 2, p.z / c ** 2)).normalized()


def eye_layout(side):
    """Eye centre, pupil rest direction and glint direction for side +1 (left) or -1 (right)."""
    n = Vector((1, 0.52 * side, -0.02)).normalized()
    centre = head_point(n) - head_normal(n) * EYE_SINK
    pupil_dir = Vector((1, 0.08 * side, 0.02)).normalized()
    glint_dir = Vector((0.85, 0.30, 0.45)).normalized()  # same light for both eyes
    return centre, pupil_dir, glint_dir


def ear_layout(side):
    n = Vector((-0.12, 0.52 * side, 0.84)).normalized()
    base = head_point(n) - head_normal(n) * 0.014
    up = Vector((-0.10, 0.30 * side, 1.0)).normalized()
    fwd = Vector((1, 0.30 * side, 0))
    fwd = (fwd - up * fwd.dot(up)).normalized()
    across = up.cross(fwd).normalized()
    out = Vector((0, side, 0))
    return base, up, fwd, across, out


def ear_radius(v):
    return (EAR_W / 2) * (1 - v) ** 0.8


def ear_half_thickness(v):
    return (EAR_T / 2) * (1 - 0.5 * v)


def ear_shell(side):
    """A C-shaped shell: the ear opens forward, its cup faces the viewer."""
    base, up, fwd, across, out = ear_layout(side)

    def fn(th, ph):
        v = th / math.pi  # 0 base, 1 tip
        radius = ear_radius(v)
        a = EAR_ARC * -math.cos(ph)
        r = radius + ear_half_thickness(v) * math.sin(ph)
        return (base + up * (EAR_H * v) + out * (0.008 * v * v)
                + across * (r * math.sin(a)) + fwd * (0.72 * radius - r * math.cos(a)))

    return sphere_grid(28, 18, fn)


def ear_inner(p, side):
    """1 on the violet inside of an ear, 0 elsewhere."""
    base, up, fwd, across, out = ear_layout(side)
    q = p - base
    v = q.dot(up) / EAR_H
    if v < 0.0 or v > 0.95:
        return 0.0
    radius = ear_radius(v)
    d = q - up * (EAR_H * v) - out * (0.008 * v * v) - fwd * (0.72 * radius)
    f, a = d.dot(fwd), d.dot(across)
    rho = math.hypot(f, a)
    ang = abs(math.atan2(a, -f))
    ht = ear_half_thickness(v)
    return (smooth(radius, radius - 0.6 * ht, rho) * smooth(EAR_ARC * 0.97, EAR_ARC * 0.78, ang)
            * smooth(0.88, 0.7, v) * smooth(0.04, 0.14, v))


def shape_head(shape):
    shape.add("head", sphere_grid(64, 40, lambda th, ph: head_point(unit(th, ph))))
    for side in (1, -1):
        # Cheek ruff: three soft points that frame the face, flat when seen from the front.
        for beta, length in ((-0.10, 0.055), (-0.45, 0.07), (-0.82, 0.058)):
            n = Vector((0.18, side * math.cos(beta), math.sin(beta))).normalized()
            flow = Vector((-0.25, side * math.cos(beta), math.sin(beta) - 0.35))
            shape.add("head", tuft(head_point(n), head_normal(n), flow, length, 0.042,
                                   flat=0.5, lift=0.5, flat_axis=Vector((1, 0, 0))))
        tag = "L" if side > 0 else "R"
        shape.add("ear" + tag, ear_shell(side))
        base, up, fwd, across, out = ear_layout(side)
        tip = base + up * (EAR_H * 0.93) + out * 0.007
        shape.add("ear" + tag, tuft(tip, up, up + out * 0.3, 0.03, 0.012, flat=0.6, lift=0.8, flat_axis=fwd))


# ---------------------------------------------------------------- the body


SPINE = ((-0.12, 0, 0.20), (0.08, 0, 0.198))
# The torso is one sweep (no seams); CHEST only places the bib tufts on its front.
CHEST = ((0.07, 0, 0.20), (0.12, 0.11, 0.115))
NECK = ((0.14, 0, 0.27), (0.08, 0.085, 0.09))


def torso_radius(t):
    """From the hips (t=0) to the chest (t=1), one smooth profile."""
    return 0.105 + 0.009 * smooth(0.0, 0.6, t)


def tail_radius(t):
    """Full in the middle, tapering to a soft point."""
    return (0.026 + 0.03 * math.sin(math.pi * (0.1 + 0.8 * t))) * (1 - 0.75 * smooth(0.6, 1.0, t))


def shape_body(shape):
    hips, chest = (Vector(c) for c in SPINE)
    ts = [i / 30 for i in range(31)]
    shape.add("body", sweep([hips.lerp(chest, t) for t in ts], [torso_radius(t) for t in ts]))
    shape.add("body", ellipsoid(*NECK))
    for s in (1, -1):
        y = 0.062 * s
        shape.add("body", sweep([Vector((0.10 + 0.012 * t, y, 0.15 - 0.115 * t)) for t in (i / 7 for i in range(8))],
                                [0.036] * 8))
        shape.add("body", ellipsoid((0.124, y, 0.026), (0.046, 0.038, 0.027)))
        y = 0.07 * s
        shape.add("body", ellipsoid((-0.125, y, 0.155), (0.07, 0.05, 0.08)))
        shape.add("body", sweep([Vector((-0.14 + 0.005 * t, y, 0.09 - 0.05 * t)) for t in (i / 5 for i in range(6))],
                                [0.033] * 6))
        shape.add("body", ellipsoid((-0.112, y, 0.026), (0.054, 0.039, 0.027)))

    ts = [i / 40 for i in range(41)]
    shape.add("body", sweep([bezier(TAIL_CTRL, t) for t in ts], [tail_radius(t) for t in ts]))

    def on(part, direction, flow, length, width, **kw):
        p, n = ellipsoid_surface(part[0], part[1], direction)
        shape.add("body", tuft(p, n, Vector(flow), length, width, **kw))

    # Chest bib: a V of soft points under the chin.
    on(CHEST, (1, 0, -0.1), (0.15, 0, -1), 0.06, 0.055, lift=0.2)
    for s in (1, -1):
        on(CHEST, (1, 0.45 * s, 0.05), (0.1, 0.3 * s, -1), 0.05, 0.05, lift=0.2)
        on(CHEST, (1, 0.25 * s, 0.4), (0.2, 0.4 * s, -1), 0.05, 0.05, lift=0.2)
        # Neck ruff behind the cheeks.
        on(NECK, (-0.3, s, 0.3), (-0.7, 0.5 * s, -0.5), 0.05, 0.055, lift=0.25)
        on(NECK, (-0.2, 0.7 * s, -0.6), (-0.4, 0.6 * s, -0.8), 0.05, 0.055, lift=0.25)
        # Britches on the back of the thighs.
        thigh = ((-0.125, 0.07 * s, 0.155), (0.07, 0.05, 0.08))
        on(thigh, (-1, 0.3 * s, -0.2), (-0.6, 0.2 * s, -1), 0.045, 0.045, lift=0.2)
        on(thigh, (-0.8, 0.5 * s, -0.6), (-0.4, 0.3 * s, -1), 0.04, 0.042, lift=0.2)
    on(NECK, (-0.6, 0, 0.8), (-1, 0, -0.3), 0.045, 0.055, lift=0.2)
    # The tail plume is its radius profile plus the shell fur; tufts there read as a paddle.


# ---------------------------------------------------------------- SDF fusion


def fused_mesh(coll, shape):
    """Union every part through an SDF, fillet the joins, smooth, and decimate to the budget."""
    verts, faces = shape.merged()
    src_me = bpy.data.meshes.new("AranduShapeSrc")
    src_me.from_pydata([tuple(v) for v in verts], [], faces)
    src = bpy.data.objects.new("AranduShapeSrc", src_me)
    coll.objects.link(src)

    ng = bpy.data.node_groups.new("AranduSDF", "GeometryNodeTree")
    ng.interface.new_socket("Geometry", in_out="INPUT", socket_type="NodeSocketGeometry")
    ng.interface.new_socket("Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
    N, L = ng.nodes, ng.links
    gi, go = N.new("NodeGroupInput"), N.new("NodeGroupOutput")
    to_sdf = N.new("GeometryNodeMeshToSDFGrid")
    to_sdf.inputs["Voxel Size"].default_value = VOXEL
    to_sdf.inputs["Band Width"].default_value = 6
    fillet = N.new("GeometryNodeSDFGridFillet")
    fillet.inputs["Iterations"].default_value = 16
    mean = N.new("GeometryNodeSDFGridMean")
    mean.inputs["Width"].default_value = 1
    mean.inputs["Iterations"].default_value = 3
    to_mesh = N.new("GeometryNodeGridToMesh")
    to_mesh.inputs["Threshold"].default_value = 0.0
    L.new(gi.outputs[0], to_sdf.inputs["Mesh"])
    L.new(to_sdf.outputs[0], fillet.inputs["Grid"])
    L.new(fillet.outputs[0], mean.inputs["Grid"])
    L.new(mean.outputs[0], to_mesh.inputs["Grid"])
    L.new(to_mesh.outputs[0], go.inputs[0])
    src.modifiers.new("sdf", "NODES").node_group = ng

    dg = bpy.context.evaluated_depsgraph_get()
    dg.update()
    raw_tris = sum(len(p.vertices) - 2 for p in src.evaluated_get(dg).data.polygons)
    dec = src.modifiers.new("decimate", "DECIMATE")
    dec.ratio = min(1.0, BODY_TRIS / max(raw_tris, 1))
    dg = bpy.context.evaluated_depsgraph_get()
    dg.update()
    me = bpy.data.meshes.new_from_object(src.evaluated_get(dg), preserve_all_data_layers=False, depsgraph=dg)
    me.name = "AranduBody"
    bpy.data.objects.remove(src)
    bpy.data.meshes.remove(src_me)
    bpy.data.node_groups.remove(ng)
    body = bpy.data.objects.new("AranduBody", me)
    coll.objects.link(body)
    print("fused surface: %d raw triangles, decimated to %d" % (raw_tris, sum(len(p.vertices) - 2 for p in me.polygons)))
    return body


# ---------------------------------------------------------------- fur data for the shell shader


TAIL_SAMPLES = [(i / 40, bezier(TAIL_CTRL, i / 40)) for i in range(41)]
NOSE_TIP = HEAD_C + Vector((0.16, 0, -0.03))


def fur_data(p, n, head, ear_inside, on_ear):
    """Fur length (0 to 1) and comb direction (unit, tangent to the surface) at a vertex."""
    t, dist = min(((t, (p - q).length) for t, q in TAIL_SAMPLES), key=lambda x: x[1])
    on_tail = smooth(0.09, 0.06, dist) * smooth(-0.17, -0.21, p.x)

    # Body: fur lies back and down; down on the legs and the chest; along the tail.
    comb = Vector((-1, 0, -0.6))
    comb = comb.lerp(Vector((0.1, 0, -1)), smooth(0.1, 0.4, n.x) * smooth(0.06, 0.12, p.x))
    comb = comb.lerp(Vector((0, 0, -1)), smooth(0.12, 0.06, p.z))
    comb = comb.lerp(bezier_tangent(TAIL_CTRL, t), on_tail)
    length = 0.6
    length = max(length, smooth(0.2, 0.5, n.x) * smooth(0.06, 0.1, p.x) * smooth(0.06, 0.12, p.z))  # chest bib
    length = max(length, smooth(-0.2, -0.5, n.x) * smooth(-0.07, -0.11, p.x) * smooth(0.04, 0.08, p.z) * 0.9)  # britches
    length = max(length, smooth(-0.4, -0.7, n.z) * 0.85)  # belly fringe
    length = max(length, on_tail)
    length *= 0.3 + 0.7 * smooth(0.03, 0.1, p.z)  # short on the paws

    # Head: fur grows away from the nose; short on the face, long on the cheeks.
    away = (p - NOSE_TIP).normalized().lerp(Vector((-1, 0, -0.3)).normalized(), 0.3)
    hn = (p - HEAD_C).normalized()
    head_len = 0.5 - 0.38 * smooth(0.3, 0.8, hn.dot(Vector((1, 0, -0.1)).normalized()))
    head_len += 0.45 * smooth(0.55, 0.85, abs(hn.y)) * smooth(0.25, -0.2, hn.z)
    if on_ear:
        away, head_len = Vector((0, 0, 1)), 0.25 * (1 - ear_inside)

    comb = comb.lerp(away, head)
    length = length + (head_len - length) * head
    comb = comb - n * comb.dot(n)
    comb = comb.normalized() if comb.length > 1e-6 else tangent_frame(n)[0]
    return max(0.0, min(1.0, length)), comb


# ---------------------------------------------------------------- the rig


def tail_points():
    return [bezier(TAIL_CTRL, i / 5) for i in range(6)]


def bone_specs():
    """(name, head, tail, parent, deforms the body by bone heat)."""
    up = Vector((0, 0, 0.04))
    specs = [
        ("root", Vector((0, 0, 0)), Vector((0, 0, 0.05)), None, False),
        ("hips", Vector((-0.11, 0, 0.20)), Vector((-0.02, 0, 0.20)), "root", True),
        ("spine", Vector((-0.02, 0, 0.20)), Vector((0.07, 0, 0.21)), "hips", True),
        ("chest", Vector((0.07, 0, 0.21)), Vector((0.14, 0, 0.25)), "spine", True),
        ("neck", Vector((0.14, 0, 0.25)), HEAD_PIVOT.copy(), "chest", True),
        ("head", HEAD_PIVOT.copy(), HEAD_PIVOT + up, "neck", False),
    ]
    tp = tail_points()
    for i in range(5):
        specs.append(("tail%d" % (i + 1), tp[i], tp[i + 1], "hips" if i == 0 else "tail%d" % i, True))
    for s, tag in ((1, "L"), (-1, "R")):
        y = 0.062 * s
        specs += [
            ("upperArm" + tag, Vector((0.10, y, 0.17)), Vector((0.106, y, 0.09)), "chest", True),
            ("foreArm" + tag, Vector((0.106, y, 0.09)), Vector((0.112, y, 0.03)), "upperArm" + tag, True),
            ("paw" + tag, Vector((0.112, y, 0.03)), Vector((0.15, y, 0.012)), "foreArm" + tag, True),
        ]
        y = 0.07 * s
        specs += [
            ("thigh" + tag, Vector((-0.12, y, 0.19)), Vector((-0.115, y, 0.10)), "hips", True),
            ("shin" + tag, Vector((-0.115, y, 0.10)), Vector((-0.14, y, 0.045)), "thigh" + tag, True),
            ("foot" + tag, Vector((-0.14, y, 0.045)), Vector((-0.10, y, 0.01)), "shin" + tag, True),
        ]
        centre, pupil_dir, _ = eye_layout(s)
        base = ear_layout(s)[0]
        specs += [
            ("ear" + tag, base, base + up, "head", False),
            ("eye" + tag, centre, centre + up, "head", False),
            ("pupil" + tag, centre + pupil_dir * EYE_R, centre + pupil_dir * EYE_R + up, "eye" + tag, False),
            ("lidUp" + tag, centre, centre + up, "head", False),
            ("lidLow" + tag, centre, centre + up, "head", False),
        ]
    return specs


def build_armature(coll):
    data = bpy.data.armatures.new("Arandu")
    arm = bpy.data.objects.new("Arandu", data)
    coll.objects.link(arm)
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    arm.select_set(True)
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode="EDIT")
    specs = bone_specs()
    for name, head, tail, _, _ in specs:
        eb = data.edit_bones.new(name)
        eb.head, eb.tail, eb.roll = head, tail, 0.0
        eb.use_connect = False
    for name, _, _, parent, _ in specs:
        if parent:
            data.edit_bones[name].parent = data.edit_bones[parent]
    bpy.ops.object.mode_set(mode="OBJECT")
    return arm, specs


def heat_weights(body, arm, specs):
    """Bone-heat weights from the body bones, read back as one {bone: weight} per vertex."""
    heat = {name for name, *_, deforms in specs if deforms}
    for b in arm.data.bones:
        b.use_deform = b.name in heat
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    body.select_set(True)
    arm.select_set(True)
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.parent_set(type="ARMATURE_AUTO")
    names = {g.index: g.name for g in body.vertex_groups}
    out, missing = [], 0
    for v in body.data.vertices:
        w = {names[g.group]: g.weight for g in v.groups if g.weight > 0.01}
        total = sum(w.values())
        if not total:
            missing += 1
            w, total = {"spine": 1.0}, 1.0
        out.append({k: x / total for k, x in w.items()})
    for b in arm.data.bones:
        b.use_deform = b.name != "root"
    if missing:
        print("bone heat left %d vertices without weights" % missing)
    return out


def skin(body, shape, heat):
    """Blend bone heat with rigid head and ear weights, by which part each vertex came from.
    Returns (weights, head share, left ear share, right ear share) per vertex."""
    trees = {owner: shape.bvh(owner) for owner in shape.parts}
    out = []
    for v, w in zip(body.data.vertices, heat):
        p = v.co
        d = {owner: tree.find_nearest(p)[3] for owner, tree in trees.items()}
        d_face = min(d["head"], d["earL"], d["earR"])
        h = smooth(-0.012, 0.012, d["body"] - d_face)
        e_l = smooth(-0.008, 0.008, d["head"] - d["earL"])
        e_r = smooth(-0.008, 0.008, d["head"] - d["earR"])
        mixed = {k: x * (1 - h) for k, x in w.items()}
        for bone, x in (("head", h * (1 - e_l - e_r)), ("earL", h * e_l), ("earR", h * e_r)):
            if x > 0.001:
                mixed[bone] = mixed.get(bone, 0.0) + x
        mixed = {k: x for k, x in mixed.items() if x > 0.01}
        total = sum(mixed.values())
        out.append(({k: x / total for k, x in mixed.items()}, h, e_l, e_r))
    return out


# ---------------------------------------------------------------- detail parts


class Geo:
    """Vertices with a color, bone weights and fur data each; faces with a material slot each."""

    def __init__(self):
        self.v, self.c, self.w, self.fur, self.comb, self.f, self.m = [], [], [], [], [], [], []

    def add(self, part, mat, color, w, fur=0.0):
        """color: one RGBA, or a function of the vertex position."""
        verts, faces = part
        o = len(self.v)
        for p in verts:
            self.v.append(Vector(p))
            self.c.append(color(p) if callable(color) else color)
            self.w.append(w)
            self.fur.append(fur)
            self.comb.append((0.0, 0.0, -1.0))
        for face in faces:
            self.f.append(tuple(i + o for i in face))
            self.m.append(mat)


def tube(pts, radii, sides=4):
    """A closed thin tube along pts, pointed at the end."""
    verts, rows = [], []
    for i in range(len(pts) - 1):
        t = (pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]).normalized()
        s, u = tangent_frame(t)
        row = []
        for j in range(sides):
            a = 2 * math.pi * j / sides
            row.append(len(verts))
            verts.append(pts[i] + (s * math.cos(a) + u * math.sin(a)) * radii[i])
        rows.append(row)
    verts.append(pts[0])
    cap = len(verts) - 1
    verts.append(pts[-1])
    tip = len(verts) - 1
    faces = []
    for j in range(sides):
        k = (j + 1) % sides
        faces.append((cap, rows[0][k], rows[0][j]))
        for i in range(len(rows) - 1):
            faces.append((rows[i][j], rows[i][k], rows[i + 1][k], rows[i + 1][j]))
        faces.append((rows[-1][j], rows[-1][k], tip))
    return verts, faces


def build_eyes(geo):
    head_w = {"head": 1.0}
    for side, tag in ((1, "L"), (-1, "R")):
        centre, pupil_dir, glint_dir = eye_layout(side)

        def eye_color(p, centre=centre):
            n = (Vector(p) - centre).normalized()
            col = mix(AMBER, AMBER_LOW, smooth(-0.05, -0.6, n.z))
            return mix(col, AMBER_TOP, smooth(0.18, 0.34, n.z))  # the lid's shadow, as on the brand eye

        geo.add(sphere_grid(32, 18, lambda th, ph, c=centre: c + unit(th, ph) * EYE_R), M_EYE, eye_color, head_w)

        # Pupil and glint: thin lenses that hug the eyeball. The pupil follows the eye bone
        # (gaze) and the pupil bone (dilation: scale across); the glint stays with the head.
        def lens(direction, half_w, half_h, height, centre=centre):
            across = Vector((0, 0, 1)).cross(direction).normalized()
            up = direction.cross(across).normalized()

            def fn(th, ph):
                n = unit(th, ph)
                d = (direction + across * math.tan(n.x * half_w) + up * math.tan(n.y * half_h)).normalized()
                r = EYE_R * (1 + height * n.z ** 0.35) if n.z >= 0 else EYE_R * (1 - 0.04 * -n.z)
                return centre + d * r

            return fn

        geo.add(sphere_grid(24, 12, lens(pupil_dir, 0.36, 0.62, 0.05)), M_PUPIL, PUPIL, {"pupil" + tag: 1.0})
        geo.add(sphere_grid(14, 7, lens(glint_dir, 0.15, 0.15, 0.075)), M_GLINT, GLINT, head_w)

        # Lids: thin shells around the eye that turn about the across axis (world Y).
        def lid(edge, span, centre=centre):
            r_mid, r_half = EYE_R * 1.11, EYE_R * 0.03

            def fn(th, ph):
                u, rho = math.cos(th), math.sin(th)
                phi = edge + span * (0.5 - 0.5 * math.cos(ph))
                r = r_mid + r_half * math.sin(ph)
                return centre + Vector((r * rho * math.cos(phi), r * u, r * rho * math.sin(phi)))

            return fn

        geo.add(sphere_grid(24, 14, lid(LID_OPEN_UP, math.radians(170))), M_FUR, FUR, {"lidUp" + tag: 1.0}, fur=0.1)
        geo.add(sphere_grid(24, 14, lid(LID_OPEN_LOW, math.radians(-170))), M_FUR, FUR, {"lidLow" + tag: 1.0}, fur=0.1)


def build_face(geo):
    w = {"head": 1.0}
    # Nose: a small rounded triangle, wider at the top.
    n = Vector((1, 0, -0.20)).normalized()
    centre = head_point(n) + head_normal(n) * 0.003

    def nose(th, ph):
        d = unit(th, ph)
        top = 0.5 + 0.5 * d.z
        return centre + Vector((0.011 * d.x, 0.028 * d.y * (0.45 + 0.55 * top), 0.017 * d.z))

    geo.add(sphere_grid(16, 10, nose), M_NOSE, NOSE, w)

    # Mouth: a short line down from the nose that splits into two small curves.
    def on_face(direction, lift=0.0025):
        d = Vector(direction).normalized()
        return head_point(d) + head_normal(d) * lift

    philtrum = [on_face((1, 0, -0.26 - 0.07 * i / 4)) for i in range(5)]
    geo.add(tube(philtrum, [0.0024] * 5), M_NOSE, NOSE, w)
    for side in (1, -1):
        pts = [on_face((1, side * 0.10 * u, -0.33 - 0.05 * math.sin(math.pi * u))) for u in (i / 6 for i in range(7))]
        geo.add(tube(pts, [0.0024 * (1 - 0.4 * i / 6) for i in range(7)]), M_NOSE, NOSE, w)

    # Whiskers: three per side, drooping a little.
    for side in (1, -1):
        root_dir = Vector((1, 0.28 * side, -0.38)).normalized()
        root = head_point(root_dir) - head_normal(root_dir) * 0.004
        for k, rise in enumerate((0.20, 0.0, -0.20)):
            start = root + Vector((0, 0, 0.006 * (1 - k)))
            direction = Vector((0.35, side, rise)).normalized()
            pts = [start + direction * (0.11 * t) + Vector((0, 0, -0.025 * t * t)) for t in (i / 6 for i in range(7))]
            geo.add(tube(pts, [0.0017 * (1 - 0.7 * i / 6) for i in range(7)]), M_WHISKER, WHISKER, w)


# ---------------------------------------------------------------- materials and assembly


def material(name, color=None, vertex_colors=False, roughness=0.5, emit=None, emit_strength=0.0):
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    for n in [n for n in nodes if n.type not in ("BSDF_PRINCIPLED", "OUTPUT_MATERIAL")]:
        nodes.remove(n)
    bsdf = next(n for n in nodes if n.type == "BSDF_PRINCIPLED")
    if vertex_colors:
        vc = nodes.new("ShaderNodeVertexColor")
        vc.layer_name = "Col"
        mat.node_tree.links.new(vc.outputs["Color"], bsdf.inputs["Base Color"])
    elif color:
        bsdf.inputs["Base Color"].default_value = color
    bsdf.inputs["Roughness"].default_value = roughness
    if emit:
        bsdf.inputs["Emission Color"].default_value = emit
        bsdf.inputs["Emission Strength"].default_value = emit_strength
    return mat


def assemble(geo, coll, arm):
    me = bpy.data.meshes.new("AranduMesh")
    me.from_pydata([tuple(v) for v in geo.v], [], geo.f)
    me.polygons.foreach_set("material_index", geo.m)
    me.polygons.foreach_set("use_smooth", [True] * len(geo.f))
    bm = bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me)
    bm.free()
    me.color_attributes.new("Col", "FLOAT_COLOR", "POINT").data.foreach_set("color", [x for c in geo.c for x in c])
    me.attributes.new("_fur", "FLOAT", "POINT").data.foreach_set("value", geo.fur)
    me.attributes.new("_comb", "FLOAT_VECTOR", "POINT").data.foreach_set("vector", [x for c in geo.comb for x in c])
    for mat in (
        material("AranduFur", vertex_colors=True, roughness=0.62),
        material("AranduEye", vertex_colors=True, roughness=0.12, emit=AMBER, emit_strength=0.35),
        material("AranduPupil", PUPIL, roughness=0.08),
        material("AranduGlint", GLINT, roughness=0.3, emit=GLINT, emit_strength=1.0),
        material("AranduNose", NOSE, roughness=0.3),
        material("AranduWhisker", WHISKER, roughness=0.5),
    ):
        me.materials.append(mat)
    obj = bpy.data.objects.new("AranduMesh", me)
    coll.objects.link(obj)
    groups = {}
    for i, w in enumerate(geo.w):
        # glTF skins carry 4 influences per vertex: keep the strongest 4, renormalized.
        top = sorted(w.items(), key=lambda kv: kv[1], reverse=True)[:4]
        total = sum(x for _, x in top) or 1.0
        for bone, x in top:
            x /= total
            if bone not in groups:
                groups[bone] = obj.vertex_groups.new(name=bone)
            groups[bone].add([i], x, "REPLACE")
    obj.parent = arm
    obj.modifiers.new("Armature", "ARMATURE").object = arm
    return obj


def reset_collection():
    coll = bpy.data.collections.get(COLL)
    if coll:
        for o in list(coll.objects):
            data = o.data
            bpy.data.objects.remove(o)
            if isinstance(data, bpy.types.Mesh) and data.users == 0:
                bpy.data.meshes.remove(data)
            elif isinstance(data, bpy.types.Armature) and data.users == 0:
                bpy.data.armatures.remove(data)
    else:
        coll = bpy.data.collections.new(COLL)
        bpy.context.scene.collection.children.link(coll)
    return coll


def build():
    if bpy.context.object and bpy.context.object.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")
    coll = reset_collection()
    arm, specs = build_armature(coll)

    shape = Shape()
    shape_head(shape)
    shape_body(shape)
    body = fused_mesh(coll, shape)
    heat = heat_weights(body, arm, specs)

    geo = Geo()
    me = body.data
    for v, (w, head, e_l, e_r) in zip(me.vertices, skin(body, shape, heat)):
        p, n = v.co.copy(), v.normal.copy()
        inside = max(e_l * ear_inner(p, 1), e_r * ear_inner(p, -1))
        fur, comb = fur_data(p, n, head, inside, max(e_l, e_r) > 0.5)
        geo.v.append(p)
        geo.c.append(mix(mix(FUR_LOW, FUR_TOP, smooth(-0.6, 0.9, n.z)), EAR_IN, inside))
        geo.w.append(w)
        geo.fur.append(fur)
        geo.comb.append(tuple(comb))
    for poly in me.polygons:
        geo.f.append(tuple(poly.vertices))
        geo.m.append(M_FUR)
    bpy.data.objects.remove(body)
    bpy.data.meshes.remove(me)

    build_eyes(geo)
    build_face(geo)
    obj = assemble(geo, coll, arm)
    tris = sum(len(f) - 2 for f in geo.f)
    low = min(v.z for v in geo.v)
    print("Arandu: %d vertices, %d triangles, %d bones, lowest point z=%.4f" % (len(geo.v), tris, len(arm.data.bones), low))
    return arm, obj


if __name__ == "__main__":
    build()
