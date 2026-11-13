"""Key Arandu's clips on the armature that build.py made: sit, walk, jump and tap.

Run it inside Blender after build.py, for example through the Blender MCP:
    import runpy; runpy.run_path("<repo>/blender/arandu/animate.py", run_name="__main__")

Every clip is one action at 30 fps, keyed on every frame with linear interpolation, so the web
plays exactly what is keyed here. Clips key only the body bones (root, spine, legs, tail): the page
owns the face bones (head, ears, eyes, pupils, lids) for gaze, blinks, moods and the head look-at.
sit and walk loop (their last frame repeats the first); jump and tap start and end in a rest pose.

Poses are written in the armature's axes: x forward, y the cat's left, z up. A negative turn about
y lifts the nose or swings a leg forward. The tail is posed by aiming its five bones at points.
"""

import math

import bpy
from bpy_extras import anim_utils
from mathutils import Matrix, Quaternion, Vector

ARMATURE = "Arandu"
FPS = 30
LEGS = ["upperArm", "foreArm", "paw", "thigh", "shin", "foot"]
TAIL = ["tail1", "tail2", "tail3", "tail4", "tail5"]
BODY = ["root", "hips", "spine", "chest", "neck"] + [b + s for b in LEGS for s in "LR"] + TAIL
AXES = {"x": Vector((1, 0, 0)), "y": Vector((0, 1, 0)), "z": Vector((0, 0, 1))}
# Upper, middle and lower bone of each leg: front left/right, hind left/right.
LIMBS = {
    "FL": ("upperArmL", "foreArmL", "pawL"), "FR": ("upperArmR", "foreArmR", "pawR"),
    "HL": ("thighL", "shinL", "footL"), "HR": ("thighR", "shinR", "footR"),
}
SPEC_KEYS = ("at", "tail", "plant")  # spec keys that hold settings instead of bone rotations


def smooth(t):
    return t * t * (3 - 2 * t)


EASE = {
    "smooth": smooth,
    "linear": lambda t: t,
    "out": lambda t: 1 - (1 - t) ** 2,  # fast start: a take-off
    "in": lambda t: t * t,  # fast end: a landing
}


# ---------------------------------------------------------------- posing


def pose(arm, spec):
    """Pose the body from a spec and return each body bone's local rotation and location.

    Spec keys: a bone name maps to rotations [(axis, degrees), ...] in armature axes, applied in
    order; "at" moves the root in armature axes; "tail" lists five points the tail bones aim at,
    in armature space; "plant" lists the legs (FL, FR, HL, HR) whose paw rests flat on the floor:
    for those, only the upper bone's turns matter.
    """
    for pb in arm.pose.bones:
        pb.rotation_mode = "QUATERNION"
        pb.rotation_quaternion = (1, 0, 0, 0)
        pb.location = (0, 0, 0)
        pb.scale = (1, 1, 1)
    for name, turns in spec.items():
        if name in SPEC_KEYS:
            continue
        pb = arm.pose.bones[name]
        for axis, deg in turns:
            turn(pb, axis, deg)
    if "at" in spec:
        root = arm.pose.bones["root"]
        root.location = root.bone.matrix_local.to_quaternion().inverted() @ Vector(spec["at"])
    for limb in spec.get("plant", ()):
        plant(arm, *LIMBS[limb])
    if "tail" in spec:
        aim_chain(arm, TAIL, spec["tail"])
    bpy.context.view_layer.update()
    return {n: (arm.pose.bones[n].rotation_quaternion.copy(), arm.pose.bones[n].location.copy()) for n in BODY}


def turn(pb, axis, deg):
    """Add a turn about an armature axis, taken in the frame the parent leaves the bone in."""
    rest = pb.bone.matrix_local.to_quaternion()
    q = rest.inverted() @ Quaternion(AXES[axis], math.radians(deg)) @ rest
    pb.rotation_quaternion = q @ pb.rotation_quaternion


def plant(arm, upper, middle, lower):
    """Fold the middle bone until the lower bone's head is back at its rest height, then lay the
    lower bone flat as at rest, so the paw sits on the floor. The upper bone keeps its swing; the
    middle bone folds the way it already leans, and whatever the spec gave the lower bone is lost."""
    pm, pl = arm.pose.bones[middle], arm.pose.bones[lower]
    target = pl.bone.head_local.z
    base = pm.rotation_quaternion.copy()

    def joint_height(deg):
        pm.rotation_quaternion = base
        turn(pm, "y", deg)
        bpy.context.view_layer.update()
        return pl.head.z

    joint_height(0.0)
    down = pm.tail - pm.head
    low = math.degrees(math.atan2(down.x, -down.z))  # this turn points the middle bone straight down
    high = low - 170.0 if low > 0 else low + 170.0  # fold on the side the bone already leans to
    if joint_height(low) < target:  # otherwise the leg is too short: leave it straight
        for _ in range(16):
            mid = (low + high) / 2
            low, high = (mid, high) if joint_height(mid) < target else (low, mid)
    joint_height(low)
    pl.matrix = Matrix.Translation(pl.head) @ pl.bone.matrix_local.to_3x3().to_4x4()


def aim_chain(arm, names, points):
    """Turn each bone of a chain about its posed head so it points at the next target."""
    for name, target in zip(names, points):
        bpy.context.view_layer.update()
        pb = arm.pose.bones[name]
        head = pb.head.copy()
        turn = (pb.tail - head).normalized().rotation_difference((Vector(target) - head).normalized())
        pb.matrix = Matrix.Translation(head) @ turn.to_matrix().to_4x4() @ Matrix.Translation(-head) @ pb.matrix


def merge(*specs):
    """Combine specs: rotations of the same bone are chained, later settings replace earlier ones."""
    out = {}
    for spec in specs:
        for name, value in spec.items():
            out[name] = value if name in SPEC_KEYS else out.get(name, []) + list(value)
    return out


def blend(a, b, t):
    return {n: (a[n][0].slerp(b[n][0], t), a[n][1].lerp(b[n][1], t)) for n in a}


# ---------------------------------------------------------------- poses

STAND = {"plant": ["FL", "FR", "HL", "HR"]}

# Haunches down, front legs straight, tail on the floor wrapped round the cat's right side.
SIT = {
    "at": (0, 0, -0.105),
    "hips": [("y", -28)],
    "thighL": [("y", -55)], "thighR": [("y", -55)],
    "shinL": [("y", 120)], "shinR": [("y", 120)],
    "footL": [("y", -45)], "footR": [("y", -45)],
    "upperArmL": [("y", 26)], "upperArmR": [("y", 26)],
    "neck": [("y", 24)],
    "plant": ["FL", "FR"],
    "tail": [(-0.24, -0.03, 0.05), (-0.27, -0.09, 0.055), (-0.245, -0.15, 0.055),
             (-0.18, -0.175, 0.05), (-0.095, -0.17, 0.05)],
}
BREATH_IN = {"spine": [("y", -1.2)], "chest": [("y", -1.6)], "neck": [("y", 1.4)]}
TIP_UP = {"tail": SIT["tail"][:4] + [(-0.11, -0.19, 0.11)]}
TIP_FLICK = {"tail": SIT["tail"][:4] + [(-0.10, -0.15, 0.09)]}

CROUCH = {
    "at": (0, 0, -0.045),
    "hips": [("y", 6)],
    "thighL": [("y", -32)], "thighR": [("y", -32)],
    "upperArmL": [("y", -12)], "upperArmR": [("y", -12)],
    "neck": [("y", -10)],
    "tail1": [("y", 18)],
    "plant": ["FL", "FR", "HL", "HR"],
}
LAUNCH = {
    "at": (0, 0, 0.035),
    "hips": [("y", -14)],
    "thighL": [("y", 34)], "thighR": [("y", 34)],
    "shinL": [("y", -12)], "shinR": [("y", -12)],
    "footL": [("y", 34)], "footR": [("y", 34)],
    "upperArmL": [("y", -50)], "upperArmR": [("y", -50)],
    "foreArmL": [("y", -6)], "foreArmR": [("y", -6)],
    "pawL": [("y", 10)], "pawR": [("y", 10)],
    "neck": [("y", 4)],
    "tail1": [("y", 26)], "tail2": [("y", 10)],
}
TUCK = {
    "at": (0, 0, 0.16),
    "thighL": [("y", -38)], "thighR": [("y", -38)],
    "shinL": [("y", 66)], "shinR": [("y", 66)],
    "footL": [("y", -36)], "footR": [("y", -36)],
    "upperArmL": [("y", -22)], "upperArmR": [("y", -22)],
    "foreArmL": [("y", 64)], "foreArmR": [("y", 64)],
    "pawL": [("y", 36)], "pawR": [("y", 36)],
    "tail1": [("y", 8)], "tail2": [("y", -8)], "tail3": [("y", -8)],
}
REACH = {
    "at": (0, 0, 0.0),
    "hips": [("y", 9)],
    "thighL": [("y", 16)], "thighR": [("y", 16)],
    "shinL": [("y", 14)], "shinR": [("y", 14)],
    "upperArmL": [("y", -16)], "upperArmR": [("y", -16)],
    "neck": [("y", -6)],
    "tail1": [("y", 14)],
    "plant": ["FL", "FR"],
}
ABSORB = {
    "at": (0, 0, -0.03),
    "hips": [("y", 3)],
    "thighL": [("y", -22)], "thighR": [("y", -22)],
    "upperArmL": [("y", 4)], "upperArmR": [("y", 4)],
    "neck": [("y", 6)],
    "plant": ["FL", "FR", "HL", "HR"],
}

# Tap: from sit, the right front paw lifts and taps the floor ahead twice while the cat looks down.
LOOK_DOWN = {"neck": [("y", 18)], "chest": [("x", -3)]}
PAW_UP = merge(LOOK_DOWN, {
    "upperArmR": [("y", -70)], "foreArmR": [("y", 40)], "pawR": [("y", 40)], "plant": ["FL"],
})
PAW_DOWN = merge(LOOK_DOWN, {
    "upperArmR": [("y", -16)], "plant": ["FL", "FR"],
})
PAW_HOVER = merge(LOOK_DOWN, {
    "upperArmR": [("y", -45)], "foreArmR": [("y", 30)], "pawR": [("y", 25)], "plant": ["FL"],
})


# ---------------------------------------------------------------- clips


def keyed(arm, keys):
    """Turn [(frame, spec, ease), ...] into one snapshot per frame, easing each span into its key.

    A leg planted at both ends of a span is planted again on every frame in between, so blending
    the angles never sinks the paw into the floor.
    """
    snaps = [(f, pose(arm, spec), EASE[ease], set(spec.get("plant", ()))) for f, spec, ease in keys]
    frames = []
    for (f0, a, _, plants0), (f1, b, ease, plants1) in zip(snaps, snaps[1:]):
        for f in range(f0, f1):
            snap = blend(a, b, ease((f - f0) / (f1 - f0)))
            frames.append(replant(arm, snap, plants0 & plants1) if f > f0 else snap)
    frames.append(snaps[-1][1])
    return frames


def replant(arm, snap, limbs):
    if not limbs:
        return snap
    for name, (rot, loc) in snap.items():
        arm.pose.bones[name].rotation_quaternion = rot
        arm.pose.bones[name].location = loc
    for limb in sorted(limbs):
        plant(arm, *LIMBS[limb])
    bpy.context.view_layer.update()
    return {n: (arm.pose.bones[n].rotation_quaternion.copy(), arm.pose.bones[n].location.copy()) for n in BODY}


def sit(arm):
    base = SIT
    return keyed(arm, [
        (0, base, "smooth"),
        (24, merge(base, TIP_UP), "smooth"),
        (34, merge(base, BREATH_IN, TIP_FLICK), "smooth"),
        (46, merge(base, BREATH_IN), "smooth"),
        (90, base, "smooth"),
    ])


STANCE = 0.6  # share of the stride a foot is on the ground


def stride(phase, back, front, lift):
    """One leg at this phase of the stride: (upper, middle, lower) turns in degrees.

    On the ground the upper bone sweeps from front to back and the lower bone counters it, so the
    paw stays flat; in the air the middle joint folds by lift[0] and the paw curls by lift[1].
    """
    if phase < STANCE:
        upper, up = mix(front, back, phase / STANCE), 0.0
    else:
        s = (phase - STANCE) / (1 - STANCE)
        upper, up = mix(back, front, smooth(s)), math.sin(math.pi * s)
    middle = lift[0] * up
    return upper, middle, lift[1] * up - upper - middle


def mix(a, b, t):
    return a + (b - a) * t


def walk(arm):
    """In-place lateral-sequence walk: left hind, left fore, right hind, right fore."""
    frames = []
    for f in range(25):
        p = f / 24
        spec = {
            "at": (0, 0, 0.004 + 0.002 * math.cos(4 * math.pi * p)),
            "hips": [("x", 2.5 * math.sin(2 * math.pi * p)), ("z", 3 * math.sin(2 * math.pi * p))],
            "chest": [("z", -3 * math.sin(2 * math.pi * (p - 0.25)))],
            "neck": [("y", 2 * math.cos(4 * math.pi * p))],
        }
        for side, offset in (("L", 0.0), ("R", 0.5)):
            thigh, shin, foot = stride((p + offset) % 1, 18, -16, (52, 25))
            arm_, fore, paw = stride((p + offset + 0.75) % 1, 16, -14, (72, 40))
            spec.update({
                "thigh" + side: [("y", thigh)], "shin" + side: [("y", shin)], "foot" + side: [("y", foot)],
                "upperArm" + side: [("y", arm_)], "foreArm" + side: [("y", fore)], "paw" + side: [("y", paw)],
            })
        for i, bone in enumerate(TAIL):
            spec[bone] = [("z", (4 + 2 * i) * math.sin(2 * math.pi * (p - 0.1 * i)))]
        frames.append(pose(arm, spec))
    return frames


def jump(arm):
    return keyed(arm, [
        (0, STAND, "smooth"),
        (8, CROUCH, "smooth"),
        (12, LAUNCH, "in"),
        (17, TUCK, "out"),
        (22, REACH, "in"),
        (25, ABSORB, "out"),
        (30, STAND, "smooth"),
    ])


def tap(arm):
    return keyed(arm, [
        (0, SIT, "smooth"),
        (7, merge(SIT, PAW_UP), "smooth"),
        (10, merge(SIT, PAW_DOWN), "in"),
        (13, merge(SIT, PAW_HOVER), "out"),
        (16, merge(SIT, PAW_DOWN), "in"),
        (20, merge(SIT, PAW_DOWN), "smooth"),
        (25, merge(SIT, PAW_UP), "smooth"),
        (32, SIT, "smooth"),
    ])


CLIPS = {"sit": sit, "walk": walk, "jump": jump, "tap": tap}


def bake(arm, name, frames):
    """Store the frames as a linear action named after the clip."""
    old = bpy.data.actions.get(name)
    if old:
        bpy.data.actions.remove(old)
    action = bpy.data.actions.new(name)
    action.use_fake_user = True
    arm.animation_data.action = action
    for f, snap in enumerate(frames):
        for bone, (rot, loc) in snap.items():
            pb = arm.pose.bones[bone]
            pb.rotation_quaternion = rot
            pb.keyframe_insert("rotation_quaternion", frame=f, group=bone)
            if bone == "root":
                pb.location = loc
                pb.keyframe_insert("location", frame=f, group=bone)
    for fc in anim_utils.action_get_channelbag_for_slot(action, action.slots[0]).fcurves:
        for key in fc.keyframe_points:
            key.interpolation = "LINEAR"
    action.frame_range = (0, len(frames) - 1)
    return action


def animate(arm=None):
    arm = arm or bpy.data.objects[ARMATURE]
    scene = bpy.context.scene
    scene.render.fps = FPS
    if arm.animation_data is None:
        arm.animation_data_create()
    actions = []
    for name, clip in CLIPS.items():
        arm.animation_data.action = None  # pose from the properties, not from a keyed action
        actions.append(bake(arm, name, clip(arm)))
    arm.animation_data.action = actions[0]
    scene.frame_start, scene.frame_end = 0, int(actions[0].frame_range[1])
    scene.frame_set(0)
    print("Arandu clips: " + ", ".join("%s %d frames" % (a.name, a.frame_range[1] + 1) for a in actions))
    return actions


if __name__ == "__main__":
    animate()
