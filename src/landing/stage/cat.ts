import * as THREE from "three";
import type { GLTF } from "three/addons/loaders/GLTFLoader.js";
import { growFur } from "./fur";
import { tokenColor } from "./palette";

// Arandu, from public/models/arandu.glb (built by blender/arandu): feet at the origin, facing +X,
// metres. The clips (sit, walk, jump, tap) key the body bones only; this file drives the face bones:
// the head and eyes follow the pointer and the ears twitch now and then.

export type CatPose = {
  /** 1 while he sits, 0 while he walks or leaps. */
  sit: number;
  /** 0..1, how far through a leap he is: drives the jump clip. */
  leap: number;
  /** Weight of the jump clip: 0 on the ground, 1 in the air. */
  air: number;
  /** Walk cycles done so far: drives the walk clip. */
  stride: number;
  /** A world point to look at, or null to look around on his own. */
  look: THREE.Vector3 | null;
};

export type Cat = {
  /** Place, scale and tilt the cat through this group. */
  root: THREE.Group;
  /** Turn the cat about Y through this group. */
  yaw: THREE.Group;
  update(pose: CatPose, dt: number, time: number, keyDir: THREE.Vector3): void;
  dispose(): void;
};

type Rig = {
  bone: THREE.Bone;
  rest: THREE.Quaternion;
  inv: THREE.Quaternion;
  dir: THREE.Vector3;
  pos: THREE.Vector3;
  clip?: THREE.Quaternion;
};

const AX = { x: new THREE.Vector3(1, 0, 0), y: new THREE.Vector3(0, 1, 0), z: new THREE.Vector3(0, 0, 1) };
const clamp = (v: number, a: number, b: number) => Math.min(b, Math.max(a, v));

export function makeCat(gltf: GLTF, layers: number): Cat {
  const model = gltf.scene;
  const furs: THREE.SkinnedMesh[] = [];
  model.traverse((o) => {
    if (!(o instanceof THREE.Mesh)) return;
    o.frustumCulled = false;
    const m = o.material as THREE.MeshStandardMaterial;
    if (m.name === "AranduFur" && o instanceof THREE.SkinnedMesh) furs.push(o);
    if (m.name === "AranduEye") {
      m.emissive = tokenColor("amber-300");
      m.emissiveIntensity = 0.35;
    }
    if (m.name === "AranduGlint") {
      m.emissive = tokenColor("cream-100");
      m.emissiveIntensity = 1;
    }
  });
  const furMesh = furs[0];
  if (!furMesh) throw new Error("arandu.glb has no AranduFur skinned mesh");
  const fur = growFur(furMesh, layers, { rim: tokenColor("violet-400"), sheen: tokenColor("cream-50") });

  // Rest orientation of every bone, in model space: the model is not placed yet.
  model.updateMatrixWorld(true);
  const rig: Record<string, Rig> = {};
  for (const bone of furMesh.skeleton.bones) {
    const wq = bone.getWorldQuaternion(new THREE.Quaternion());
    rig[bone.name] = {
      bone,
      rest: bone.quaternion.clone(),
      inv: wq.clone().invert(),
      dir: new THREE.Vector3(0, 1, 0).applyQuaternion(wq),
      pos: bone.getWorldPosition(new THREE.Vector3()),
    };
  }

  const root = new THREE.Group();
  const yaw = new THREE.Group();
  root.add(yaw);
  yaw.add(model);

  const mixer = new THREE.AnimationMixer(model);
  const act: Record<string, THREE.AnimationAction> = {};
  for (const clip of gltf.animations) {
    const a = mixer.clipAction(clip);
    a.play();
    a.setEffectiveWeight(0);
    act[clip.name] = a;
  }
  for (const name of ["walk", "jump"]) if (act[name]) act[name].paused = true;

  // Turns about model axes, taken from the bone's rest orientation.
  const tq = new THREE.Quaternion();
  const axis = new THREE.Vector3();
  const turn = (q: THREE.Quaternion, r: Rig, rots: Array<[THREE.Vector3, number]>) => {
    for (const [a, angle] of rots) q.multiply(tq.setFromAxisAngle(axis.copy(a).applyQuaternion(r.inv).normalize(), angle));
  };
  // Face bones are never keyed: pose them from rest.
  const pose = (name: string, rots: Array<[THREE.Vector3, number]>) => {
    const r = rig[name];
    if (r) turn(r.bone.quaternion.copy(r.rest), r, rots);
  };
  // Keyed bones: add to what the clip set this frame. The mixer only writes a bone whose value
  // changed, so update() puts the clip value back first, or the nudges would pile up.
  const nudge = (name: string, rots: Array<[THREE.Vector3, number]>) => {
    const r = rig[name];
    if (!r) return;
    (r.clip ??= new THREE.Quaternion()).copy(r.bone.quaternion);
    turn(r.bone.quaternion, r, rots);
  };

  const look = { yaw: 0, pitch: 0, eyeYaw: 0, eyePitch: 0 };
  const twitch = { L: 0, R: 0, next: 2 };
  const local = new THREE.Vector3();
  const earAxis = new THREE.Vector3();
  const back = AX.x.clone().negate();

  return {
    root,
    yaw,
    update(p, dt, time, keyDir) {
      for (const r of Object.values(rig)) if (r.clip) r.bone.quaternion.copy(r.clip);
      act.sit?.setEffectiveWeight(p.sit);
      act.walk?.setEffectiveWeight((1 - p.sit) * (1 - p.air));
      act.jump?.setEffectiveWeight(p.air);
      if (act.walk) act.walk.time = (((p.stride % 1) + 1) % 1) * act.walk.getClip().duration;
      if (act.jump) act.jump.time = clamp(p.leap, 0, 1) * act.jump.getClip().duration;
      mixer.update(dt);

      // Head and eyes follow the target; with none he looks around slowly.
      let yawTo = 0.35 * Math.sin(time * 0.4) * Math.sin(time * 0.13);
      let pitchTo = 0.08 * Math.sin(time * 0.31);
      if (p.look) {
        root.updateMatrixWorld(true);
        model.worldToLocal(local.copy(p.look)).sub(rig.head.pos);
        yawTo = clamp(Math.atan2(-local.z, local.x), -1, 1);
        pitchTo = clamp(Math.atan2(local.y, Math.hypot(local.x, local.z)), -0.4, 0.5);
      }
      yawTo *= p.sit;
      pitchTo *= p.sit;
      const k = Math.min(1, dt * 5);
      look.yaw += (yawTo - look.yaw) * k;
      look.pitch += (pitchTo - look.pitch) * k;
      const ke = Math.min(1, dt * 14);
      look.eyeYaw += (clamp(yawTo - look.yaw * 0.9, -0.35, 0.35) - look.eyeYaw) * ke;
      look.eyePitch += (clamp(pitchTo - look.pitch * 0.9, -0.25, 0.25) - look.eyePitch) * ke;
      const tilt = 0.08 * Math.sin(time * 0.7) * p.sit;
      nudge("neck", [
        [AX.y, look.yaw * 0.35],
        [AX.z, look.pitch * 0.3],
      ]);
      pose("head", [
        [AX.y, look.yaw * 0.55],
        [AX.z, look.pitch * 0.6],
        [AX.x, tilt],
      ]);
      for (const side of ["L", "R"]) {
        pose(`eye${side}`, [
          [AX.y, look.eyeYaw],
          [AX.z, look.eyePitch],
        ]);
      }

      twitch.next -= dt;
      if (twitch.next <= 0) {
        twitch[Math.random() < 0.5 ? "L" : "R"] = 1;
        twitch.next = 2 + Math.random() * 3;
      }
      for (const side of ["L", "R"] as const) {
        twitch[side] = Math.max(0, twitch[side] - dt * 4);
        const r = rig[`ear${side}`];
        if (r) pose(`ear${side}`, [[earAxis.copy(r.dir).cross(back).normalize(), 0.35 * Math.sin(Math.PI * twitch[side])]]);
      }

      root.updateMatrixWorld(true);
      fur.update(dt, time, keyDir);
    },
    dispose() {
      mixer.stopAllAction();
      fur.dispose();
      model.traverse((o) => {
        if (!(o instanceof THREE.Mesh)) return;
        o.geometry.dispose();
        (o.material as THREE.Material).dispose();
      });
    },
  };
}
