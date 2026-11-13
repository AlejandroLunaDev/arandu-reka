import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { DRACOLoader } from 'three/addons/loaders/DRACOLoader.js';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { GUI } from 'three/addons/libs/lil-gui.module.min.js';

// Preview of Arandu as the landing will show it: the clips from the GLB
// (sit, walk, jump, tap) drive the body, this page drives the face.
//
// Shell fur: the fur mesh is drawn LAYERS extra times, each shell pushed out
// along the skinned normal and laid down along the exported comb direction.
// Tips trail behind a spring-delayed copy of the skeleton, so fur reacts to
// every motion (clips, head, spins) without per-vertex simulation state.
const LAYERS = 40;
const params = {
  length: 0.032, density: 420, thickness: 0.9, lay: 0.65, clump: 0.35,
  lag: 0.9, gravity: 0.5, wind: 0.25, rim: 0.35, sheen: 0.08, stiffness: 140, damping: 11,
};

const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true, preserveDrawingBuffer: true });
renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
renderer.setSize(innerWidth, innerHeight);
renderer.outputColorSpace = THREE.SRGBColorSpace;
document.body.appendChild(renderer.domElement);

const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(30, innerWidth / innerHeight, 0.01, 20);
const controls = new OrbitControls(camera, renderer.domElement);
controls.enableDamping = true;
controls.minDistance = 0.4;
controls.maxDistance = 3;

scene.add(new THREE.HemisphereLight(0xfff4e2, 0x2b2723, 1.3));
const key = new THREE.DirectionalLight(0xfff1dc, 2.6);
key.position.set(1.2, 1.6, 0.9);
scene.add(key);
const rimLight = new THREE.DirectionalLight(0xdde4ee, 2.2);
rimLight.position.set(-1.5, 0.8, -1.0);
scene.add(rimLight);

const shadow = (() => {
  const c = document.createElement('canvas');
  c.width = c.height = 128;
  const g = c.getContext('2d');
  const grd = g.createRadialGradient(64, 64, 0, 64, 64, 64);
  grd.addColorStop(0, 'rgba(40,28,50,0.45)');
  grd.addColorStop(1, 'rgba(40,28,50,0)');
  g.fillStyle = grd;
  g.fillRect(0, 0, 128, 128);
  const m = new THREE.Mesh(new THREE.PlaneGeometry(0.9, 0.5),
    new THREE.MeshBasicMaterial({ map: new THREE.CanvasTexture(c), transparent: true, depthWrite: false }));
  m.rotation.x = -Math.PI / 2;
  m.position.y = 0.001;
  scene.add(m);
  return m;
})();

const shared = {
  uTime: { value: 0 },
  uLength: { value: params.length },
  uDensity: { value: params.density },
  uThick: { value: params.thickness },
  uLay: { value: params.lay },
  uLagAmt: { value: params.lag },
  uGravity: { value: new THREE.Vector3() },
  uWind: { value: params.wind },
  uWindDir: { value: new THREE.Vector3() },
  uClump: { value: params.clump },
  uRim: { value: params.rim },
  uRimColor: { value: new THREE.Color(0xc9ced8) },
  uSheen: { value: params.sheen },
  uSheenColor: { value: new THREE.Color(0xfff1dc) },
  uKeyDir: { value: new THREE.Vector3() },
  uLagTex: { value: null },
};

const VERT_HEAD = /* glsl */`
attribute float furLen;
attribute vec3 furComb;
uniform float uLayer;
uniform float uTime;
uniform float uLength;
uniform float uLay;
uniform float uLagAmt;
uniform float uWind;
uniform vec3 uGravity;
uniform vec3 uWindDir;
uniform highp sampler2D uLagTex;
varying vec3 vRest;
varying float vFur;
varying vec3 vStrand;
mat4 lagMatrix(const in float i) {
  int size = textureSize(uLagTex, 0).x;
  int j = int(i) * 4;
  int x = j % size;
  int y = j / size;
  return mat4(texelFetch(uLagTex, ivec2(x, y), 0), texelFetch(uLagTex, ivec2(x + 1, y), 0),
              texelFetch(uLagTex, ivec2(x + 2, y), 0), texelFetch(uLagTex, ivec2(x + 3, y), 0));
}
`;

const VERT_BODY = /* glsl */`
vRest = position;
vFur = furLen;
{
  float t = uLayer;
  float L = uLength * furLen;
  vec3 n = normalize(objectNormal);
  // _COMB is exported raw in Blender space (Z-up): convert to glTF Y-up.
  vec3 cb = (skinMatrix * vec4(furComb.x, furComb.z, -furComb.y, 0.0)).xyz;
  vec3 c = cb - n * dot(cb, n);
  float cl = length(c);
  c = cl > 1e-4 ? c / cl : vec3(0.0);
  vec3 dir = normalize(n * (1.0 - uLay * t) + c * (uLay * t + 0.1));
  vec3 off = dir * (L * t);
  vStrand = (modelViewMatrix * vec4(dir, 0.0)).xyz;
  mat4 lm = skinWeight.x * lagMatrix(skinIndex.x) + skinWeight.y * lagMatrix(skinIndex.y)
          + skinWeight.z * lagMatrix(skinIndex.z) + skinWeight.w * lagMatrix(skinIndex.w);
  vec3 lagPos = (bindMatrixInverse * lm * bindMatrix * vec4(position, 1.0)).xyz;
  vec3 lag = lagPos - transformed;
  lag *= min(1.0, (2.0 * L + 1e-6) / max(length(lag), 1e-6));
  float t2 = t * t;
  off += lag * (uLagAmt * t2);
  off += uGravity * (L * t2);
  float w = 0.6 * sin(uTime * 1.9 + dot(position, vec3(23.0, 17.0, 11.0)))
          + 0.4 * sin(uTime * 3.3 + dot(position, vec3(-13.0, 29.0, 7.0)));
  off += uWindDir * (w * uWind * L * t2);
  transformed += off;
}
`;

const FRAG_HEAD = /* glsl */`
uniform float uLayer;
uniform float uDensity;
uniform float uThick;
uniform float uClump;
uniform float uRim;
uniform vec3 uRimColor;
uniform float uSheen;
uniform vec3 uSheenColor;
uniform vec3 uKeyDir;
varying vec3 vRest;
varying float vFur;
varying vec3 vStrand;
vec3 furHash(vec3 p) {
  p = fract(p * vec3(0.1031, 0.1030, 0.0973));
  p += dot(p, p.yxz + 33.33);
  return fract((p.xxy + p.yxx) * p.zyx);
}
`;

// Strands are 3D Voronoi cells of the rest position: each shell fragment of
// one surface point samples the same cell, so a strand is a column through
// the layers that tapers to a tip.
const FRAG_COLOR = /* glsl */`
{
  float t = uLayer;
  if (t > 0.0) {
    if (vFur < 0.03) discard;
    // Clumps: lookups spread out from the nearest clump centre as t grows,
    // so the strands of one clump converge toward their tips.
    float cs = uDensity * 0.18;
    vec3 cq = vRest * cs;
    vec3 cip = floor(cq);
    vec3 cfp = fract(cq);
    float cbest = 8.0;
    vec3 centre = vec3(0.0);
    for (int x = -1; x <= 1; x++)
    for (int y = -1; y <= 1; y++)
    for (int z = -1; z <= 1; z++) {
      vec3 g = vec3(float(x), float(y), float(z));
      vec3 o = furHash(cip + g + 17.0);
      vec3 r = g + o - cfp;
      float d = dot(r, r);
      if (d < cbest) { cbest = d; centre = cip + g + o; }
    }
    vec3 cRest = centre / cs;
    vec3 p = (cRest + (vRest - cRest) / (1.0 - t * uClump)) * uDensity;
    vec3 ip = floor(p);
    vec3 fp = fract(p);
    float best = 8.0;
    vec3 pick = vec3(0.0);
    for (int x = -1; x <= 1; x++)
    for (int y = -1; y <= 1; y++)
    for (int z = -1; z <= 1; z++) {
      vec3 g = vec3(float(x), float(y), float(z));
      vec3 o = furHash(ip + g);
      vec3 r = g + o - fp;
      float d = dot(r, r);
      if (d < best) { best = d; pick = o; }
    }
    float len = mix(0.5, 1.0, pick.y);
    if (t > len) discard;
    float rad = uThick * (1.0 - t / len);
    if (best > rad * rad) discard;
  }
  float ao = mix(1.0, mix(0.4, 1.2, pow(t, 0.8)), smoothstep(0.03, 0.2, vFur));
  diffuseColor.rgb *= ao;
}
`;

const FRAG_RIM = /* glsl */`
float furFresnel = pow(1.0 - clamp(dot(normal, normalize(vViewPosition)), 0.0, 1.0), 3.0);
totalEmissiveRadiance += uRimColor * (uRim * furFresnel * (0.3 + 0.7 * uLayer));
// Strand sheen (Kajiya-Kay): a soft highlight across the strand direction.
vec3 furH = normalize(uKeyDir + normalize(vViewPosition));
float furTH = dot(normalize(vStrand), furH);
float furSpec = pow(sqrt(max(0.0, 1.0 - furTH * furTH)), 90.0);
totalEmissiveRadiance += uSheenColor * (uSheen * furSpec * (0.25 + 0.75 * uLayer) * (0.5 + 0.5 * dot(normal, uKeyDir)));
`;

function furMaterial(src, layer) {
  const m = src.clone();
  m.side = THREE.FrontSide;
  m.roughness = 0.82;
  m.metalness = 0;
  m.onBeforeCompile = (shader) => {
    Object.assign(shader.uniforms, shared, { uLayer: { value: layer } });
    shader.vertexShader = shader.vertexShader
      .replace('#include <common>', `#include <common>\n${VERT_HEAD}`)
      .replace('#include <skinning_vertex>', `#include <skinning_vertex>\n${VERT_BODY}`);
    shader.fragmentShader = shader.fragmentShader
      .replace('#include <common>', `#include <common>\n${FRAG_HEAD}`)
      .replace('#include <color_fragment>', `#include <color_fragment>\n${FRAG_COLOR}`)
      .replace('#include <emissivemap_fragment>', `#include <emissivemap_fragment>\n${FRAG_RIM}`);
  };
  m.customProgramCacheKey = () => 'arandu-fur-v2';
  return m;
}

const AX = { x: new THREE.Vector3(1, 0, 0), y: new THREE.Vector3(0, 1, 0), z: new THREE.Vector3(0, 0, 1) };
const LOOPS = ['sit', 'walk'];
const state = {
  model: null, fur: null, shells: [], rig: {}, lag: null, lagVel: null, lagTex: null,
  mixer: null, actions: {}, current: null, loop: 'sit',
  look: { yaw: 0, pitch: 0, eyeYaw: 0, eyePitch: 0 }, spinT: -1, wind: true,
  twitch: { L: 0, R: 0, next: 2 },
};

const VIEWS = {
  front: [[1.05, 0.42, 0.95], [0.02, 0.22, 0]],
  side: [[0.0, 0.3, 1.55], [0.0, 0.22, 0]],
  close: [[0.72, 0.42, 0.38], [0.2, 0.34, 0]],
  back: [[-1.1, 0.5, 0.75], [-0.1, 0.25, 0]],
  // Wide enough for every clip, the jump included: used for the PNG renders.
  render: [[1.0, 0.52, 1.65], [0.0, 0.33, 0]],
};
function view(name) {
  const [p, t] = VIEWS[name];
  camera.position.set(...p);
  controls.target.set(...t);
  controls.update();
}
view('front');

// Turns about world axes, taken from the bone's rest orientation.
const tmpQ = new THREE.Quaternion();
function turn(q, r, rots) {
  for (const [axis, angle] of rots) {
    q.multiply(tmpQ.setFromAxisAngle(axis.clone().applyQuaternion(r.inv).normalize(), angle));
  }
}
// Face bones are never keyed: pose them from rest.
function pose(name, rots) {
  const r = state.rig[name];
  if (r) turn(r.bone.quaternion.copy(r.rest), r, rots);
}
// Keyed bones: add to what the clip set this frame. The mixer only writes a bone whose keyed
// value changed, so animate() puts the clip value back first or the nudges would pile up.
function nudge(name, rots) {
  const r = state.rig[name];
  if (!r) return;
  (r.clip ??= new THREE.Quaternion()).copy(r.bone.quaternion);
  turn(r.bone.quaternion, r, rots);
}

function play(name) {
  const next = state.actions[name];
  if (!next || next === state.current) return;
  if (LOOPS.includes(name)) state.loop = name;
  next.reset().play();
  if (state.current) next.crossFadeFrom(state.current, 0.25, false);
  state.current = next;
  document.querySelectorAll('[data-clip]').forEach((b) => b.setAttribute('aria-pressed', b.dataset.clip === state.loop));
}

const draco = new DRACOLoader().setDecoderPath('https://cdn.jsdelivr.net/npm/three@0.170.0/examples/jsm/libs/draco/gltf/');
new GLTFLoader().setDRACOLoader(draco).load('/public/models/arandu.glb', (gltf) => {
  const model = gltf.scene;
  scene.add(model);
  model.traverse((o) => {
    if (!o.isMesh) return;
    o.frustumCulled = false;
    const n = o.material.name;
    if (n === 'AranduFur') state.fur = o;
    if (n === 'AranduEye') { o.material.emissive = new THREE.Color(0xf2b53c); o.material.emissiveIntensity = 0.35; }
    if (n === 'AranduGlint') { o.material.emissive = new THREE.Color(0xf1ebdd); o.material.emissiveIntensity = 1.0; }
  });
  const fur = state.fur;
  const geo = fur.geometry;
  geo.setAttribute('furLen', geo.getAttribute('_fur'));
  geo.setAttribute('furComb', geo.getAttribute('_comb'));

  const skel = fur.skeleton;
  skel.computeBoneTexture();
  model.updateMatrixWorld(true);
  skel.update();
  state.lag = new Float32Array(skel.boneMatrices.length);
  state.lagVel = new Float32Array(skel.boneMatrices.length);
  state.lag.set(skel.boneMatrices);
  const size = skel.boneTexture.image.width;
  state.lagTex = new THREE.DataTexture(state.lag, size, size, THREE.RGBAFormat, THREE.FloatType);
  state.lagTex.needsUpdate = true;
  shared.uLagTex.value = state.lagTex;

  const src = fur.material;
  fur.material = furMaterial(src, 0);
  for (let i = 1; i <= LAYERS; i++) {
    const s = new THREE.SkinnedMesh(geo, furMaterial(src, i / LAYERS));
    s.bindMode = fur.bindMode;
    s.bind(skel, fur.bindMatrix);
    s.position.copy(fur.position);
    s.quaternion.copy(fur.quaternion);
    s.scale.copy(fur.scale);
    s.frustumCulled = false;
    s.renderOrder = i;
    fur.parent.add(s);
    state.shells.push(s);
  }

  for (const b of skel.bones) {
    const wq = b.getWorldQuaternion(new THREE.Quaternion());
    state.rig[b.name] = {
      bone: b, rest: b.quaternion.clone(), restPos: b.position.clone(), inv: wq.clone().invert(),
      dir: new THREE.Vector3(0, 1, 0).applyQuaternion(wq),
      pos: b.getWorldPosition(new THREE.Vector3()),
    };
  }

  state.mixer = new THREE.AnimationMixer(model);
  for (const clip of gltf.animations) {
    const action = state.mixer.clipAction(clip);
    if (!LOOPS.includes(clip.name)) { action.setLoop(THREE.LoopOnce); action.clampWhenFinished = true; }
    state.actions[clip.name] = action;
  }
  state.mixer.addEventListener('finished', () => play(state.loop));
  play('sit');

  state.model = model;
  window.__arandu.ready = true;
  window.__arandu.clips = gltf.animations.map((c) => [c.name, +c.duration.toFixed(3), c.tracks.length]);
  window.__arandu.attributes = Object.keys(geo.attributes);
}, undefined, (err) => { window.__arandu.error = String(err); console.error(err); });

const ndc = new THREE.Vector2(0, 0);
const raycaster = new THREE.Raycaster();
const plane = new THREE.Plane();
const target = new THREE.Vector3();
addEventListener('pointermove', (e) => ndc.set((e.clientX / innerWidth) * 2 - 1, -(e.clientY / innerHeight) * 2 + 1));

let downAt = null;
renderer.domElement.addEventListener('pointerdown', (e) => { downAt = [e.clientX, e.clientY]; });
renderer.domElement.addEventListener('pointerup', (e) => {
  if (downAt && Math.hypot(e.clientX - downAt[0], e.clientY - downAt[1]) < 4) play('jump');
  downAt = null;
});

function spin() { if (state.spinT < 0) state.spinT = 0; }
function furOn(on) { state.shells.forEach((s) => { s.visible = on; }); }

const toggle = (id, fn) => {
  const b = document.getElementById(id);
  b.addEventListener('click', () => { const on = b.getAttribute('aria-pressed') !== 'true'; b.setAttribute('aria-pressed', on); fn(on); });
};
document.querySelectorAll('[data-clip]').forEach((b) => b.addEventListener('click', () => play(b.dataset.clip)));
document.getElementById('spin').addEventListener('click', spin);
toggle('wind', (on) => { state.wind = on; });
toggle('fur', furOn);

const gui = new GUI({ title: 'Fur' });
const bind = (k, min, max, step, u) => gui.add(params, k, min, max, step).onChange((v) => { if (u) shared[u].value = v; });
bind('length', 0, 0.06, 0.001, 'uLength');
bind('density', 100, 900, 10, 'uDensity');
bind('thickness', 0.2, 1.4, 0.01, 'uThick');
bind('lay', 0, 1, 0.01, 'uLay');
bind('clump', 0, 0.8, 0.01, 'uClump');
bind('lag', 0, 2, 0.01, 'uLagAmt');
bind('gravity', 0, 1.5, 0.01);
bind('wind', 0, 1, 0.01, 'uWind');
bind('rim', 0, 3, 0.01, 'uRim');
bind('sheen', 0, 0.5, 0.005, 'uSheen');
bind('stiffness', 20, 400, 1);
bind('damping', 1, 40, 0.5);
gui.close();

const easeInOut = (s) => (s < 0.5 ? 2 * s * s : 1 - ((-2 * s + 2) ** 2) / 2);
const clamp = (v, a, b) => Math.min(b, Math.max(a, v));

function animate(t, dt) {
  const { model, rig, look } = state;
  for (const r of Object.values(rig)) if (r.clip) r.bone.quaternion.copy(r.clip);
  state.mixer.update(dt);

  // Spin turns the whole model; the delayed skeleton turns that into fur motion.
  if (state.spinT >= 0) {
    state.spinT += dt;
    const s = state.spinT / 1.4;
    if (s >= 1) { state.spinT = -1; model.rotation.y = 0; } else model.rotation.y = 2 * Math.PI * easeInOut(s);
  }
  shadow.scale.setScalar(1 - Math.max(0, rig.root.bone.position.y - rig.root.restPos.y) * 2.5);

  // Head and eyes follow the pointer, projected on a plane between the cat and the viewer.
  model.updateMatrixWorld(true);
  const head = rig.head;
  const headWorld = head.bone.getWorldPosition(new THREE.Vector3());
  const camDir = camera.position.clone().sub(headWorld);
  plane.setFromNormalAndCoplanarPoint(camDir.clone().normalize(), headWorld.clone().addScaledVector(camDir, 0.6));
  raycaster.setFromCamera(ndc, camera);
  if (raycaster.ray.intersectPlane(plane, target)) {
    const d = model.worldToLocal(target.clone()).sub(head.pos);
    const yaw = clamp(Math.atan2(-d.z, d.x), -1.0, 1.0);
    const pitch = clamp(Math.atan2(d.y, Math.hypot(d.x, d.z)), -0.4, 0.5);
    const k = Math.min(1, dt * 5);
    look.yaw += (yaw - look.yaw) * k;
    look.pitch += (pitch - look.pitch) * k;
    const ke = Math.min(1, dt * 14);
    look.eyeYaw += (clamp(yaw - look.yaw * 0.9, -0.35, 0.35) - look.eyeYaw) * ke;
    look.eyePitch += (clamp(pitch - look.pitch * 0.9, -0.25, 0.25) - look.eyePitch) * ke;
  }
  const tilt = 0.08 * Math.sin(t * 0.7);
  nudge('neck', [[AX.y, look.yaw * 0.35], [AX.z, look.pitch * 0.3]]);
  pose('head', [[AX.y, look.yaw * 0.55], [AX.z, look.pitch * 0.6], [AX.x, tilt]]);
  for (const side of ['L', 'R']) pose(`eye${side}`, [[AX.y, look.eyeYaw], [AX.z, look.eyePitch]]);

  const tw = state.twitch;
  tw.next -= dt;
  if (tw.next <= 0) { tw[Math.random() < 0.5 ? 'L' : 'R'] = 1; tw.next = 2 + Math.random() * 3; }
  for (const side of ['L', 'R']) {
    tw[side] = Math.max(0, tw[side] - dt * 4);
    const r = rig[`ear${side}`];
    if (r) pose(`ear${side}`, [[r.dir.clone().cross(AX.x.clone().negate()).normalize(), 0.35 * Math.sin(Math.PI * tw[side])]]);
  }
}

function springLag(dt) {
  const bm = state.fur.skeleton.boneMatrices;
  const { lag, lagVel } = state;
  const steps = Math.max(1, Math.ceil(dt * 240));
  const h = dt / steps;
  for (let s = 0; s < steps; s++) {
    for (let i = 0; i < bm.length; i++) {
      const a = params.stiffness * (bm[i] - lag[i]) - params.damping * lagVel[i];
      lagVel[i] += a * h;
      lag[i] += lagVel[i] * h;
    }
  }
  state.lagTex.needsUpdate = true;
}

const clock = new THREE.Clock();
const inv = new THREE.Quaternion();
function frame() {
  const dt = Math.min(clock.getDelta(), 1 / 20);
  const t = clock.elapsedTime;
  controls.update();
  if (state.model) {
    animate(t, dt);
    state.model.updateMatrixWorld(true);
    state.fur.skeleton.update();
    springLag(dt);
    state.fur.getWorldQuaternion(inv).invert();
    shared.uGravity.value.set(0, -params.gravity, 0).applyQuaternion(inv);
    shared.uWindDir.value.set(0.3, 0.1, 1).normalize().applyQuaternion(inv);
    shared.uWind.value = state.wind ? params.wind : 0;
    shared.uTime.value = t;
    shared.uKeyDir.value.copy(key.position).sub(key.target.position).normalize().transformDirection(camera.matrixWorldInverse);
  }
  renderer.render(scene, camera);
  requestAnimationFrame(frame);
}
requestAnimationFrame(frame);

addEventListener('resize', () => {
  camera.aspect = innerWidth / innerHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(innerWidth, innerHeight);
});

// Render hooks: hold a clip at a time, then save the canvas as a transparent PNG
// through the preview server (server.py writes blender/arandu/renders/<name>.png).
function hold(name, time) {
  for (const a of Object.values(state.actions)) a.stop();
  const a = state.actions[name];
  a.reset().play();
  a.time = time;
  a.paused = true;
  state.current = a;
}

// Waits a number of frames, not of seconds, so the fur springs settle even when the browser
// draws slowly.
async function render(name, frames = 40) {
  shadow.visible = false;
  for (let i = 0; i < frames; i++) await new Promise((r) => requestAnimationFrame(r));
  const blob = await new Promise((r) => renderer.domElement.toBlob(r, 'image/png'));
  shadow.visible = true;
  await fetch(`/render/${name}`, { method: 'POST', body: blob });
}

window.__arandu = { ready: false, view, play, hold, spin, furOn, render, ndc, params, shared, state };
