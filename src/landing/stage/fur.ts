import * as THREE from "three";

// Shell fur for Arandu, ported from the Blender preview (blender/arandu/preview/fur.js).
//
// The fur mesh is drawn once per layer, each shell pushed out along the skinned normal and laid down
// along the comb direction exported from Blender. The tips trail a spring-delayed copy of the
// skeleton, so the fur reacts to every motion without per-vertex simulation state.

const PARAMS = {
  length: 0.032,
  density: 420,
  thickness: 0.9,
  lay: 0.65,
  clump: 0.35,
  lag: 0.9,
  gravity: 0.5,
  wind: 0.25,
  rim: 0.35,
  sheen: 0.08,
  stiffness: 140,
  damping: 11,
};

const VERT_HEAD = /* glsl */ `
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

const VERT_BODY = /* glsl */ `
vRest = position;
vFur = furLen;
{
  float t = uLayer;
  float L = uLength * furLen;
  vec3 n = normalize(objectNormal);
  // The comb is exported raw in Blender space (Z up): convert it to glTF space (Y up).
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

const FRAG_HEAD = /* glsl */ `
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

// Strands are 3D Voronoi cells of the rest position: each shell fragment of one surface point
// samples the same cell, so a strand is a column through the layers that tapers to a tip.
const FRAG_COLOR = /* glsl */ `
{
  float t = uLayer;
  if (t > 0.0) {
    if (vFur < 0.03) discard;
    // Clumps: lookups spread out from the nearest clump centre as t grows, so the strands of one
    // clump converge toward their tips.
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

// The landing's camera is orthographic: every fragment looks straight down -Z.
const FRAG_RIM = /* glsl */ `
vec3 furView = isOrthographic ? vec3(0.0, 0.0, 1.0) : normalize(vViewPosition);
float furFresnel = pow(1.0 - clamp(dot(normal, furView), 0.0, 1.0), 3.0);
totalEmissiveRadiance += uRimColor * (uRim * furFresnel * (0.3 + 0.7 * uLayer));
// Strand sheen (Kajiya-Kay): a soft highlight across the strand direction.
vec3 furH = normalize(uKeyDir + furView);
float furTH = dot(normalize(vStrand), furH);
float furSpec = pow(sqrt(max(0.0, 1.0 - furTH * furTH)), 90.0);
totalEmissiveRadiance += uSheenColor * (uSheen * furSpec * (0.25 + 0.75 * uLayer) * (0.5 + 0.5 * dot(normal, uKeyDir)));
`;

export type FurColors = { rim: THREE.Color; sheen: THREE.Color };

export type Fur = {
  /** Call after the skeleton is posed for the frame. keyDir is the key light direction in view space. */
  update(dt: number, time: number, keyDir: THREE.Vector3): void;
  dispose(): void;
};

/** Grows shell fur on the cat's fur mesh. The shells share its geometry and skeleton. */
export function growFur(fur: THREE.SkinnedMesh, layers: number, colors: FurColors): Fur {
  const geo = fur.geometry;
  geo.setAttribute("furLen", geo.getAttribute("_fur"));
  geo.setAttribute("furComb", geo.getAttribute("_comb"));

  const skel = fur.skeleton;
  skel.computeBoneTexture();
  fur.updateMatrixWorld(true);
  skel.update();
  const bones = skel.boneMatrices;
  if (!bones) throw new Error("The fur skeleton has no bone matrices");
  const lag = new Float32Array(bones.length);
  const lagVel = new Float32Array(bones.length);
  lag.set(bones);
  const size = skel.boneTexture!.image.width;
  const lagTex = new THREE.DataTexture(lag, size, size, THREE.RGBAFormat, THREE.FloatType);
  lagTex.needsUpdate = true;

  const shared = {
    uTime: { value: 0 },
    uLength: { value: PARAMS.length },
    uDensity: { value: PARAMS.density },
    uThick: { value: PARAMS.thickness },
    uLay: { value: PARAMS.lay },
    uLagAmt: { value: PARAMS.lag },
    uGravity: { value: new THREE.Vector3() },
    uWind: { value: PARAMS.wind },
    uWindDir: { value: new THREE.Vector3() },
    uClump: { value: PARAMS.clump },
    uRim: { value: PARAMS.rim },
    uRimColor: { value: colors.rim },
    uSheen: { value: PARAMS.sheen },
    uSheenColor: { value: colors.sheen },
    uKeyDir: { value: new THREE.Vector3() },
    uLagTex: { value: lagTex },
  };

  const source = fur.material as THREE.MeshStandardMaterial;
  const materials: THREE.Material[] = [];
  const furMaterial = (layer: number) => {
    const m = source.clone();
    m.side = THREE.FrontSide;
    m.roughness = 0.82;
    m.metalness = 0;
    m.onBeforeCompile = (shader) => {
      Object.assign(shader.uniforms, shared, { uLayer: { value: layer } });
      shader.vertexShader = shader.vertexShader
        .replace("#include <common>", `#include <common>\n${VERT_HEAD}`)
        .replace("#include <skinning_vertex>", `#include <skinning_vertex>\n${VERT_BODY}`);
      shader.fragmentShader = shader.fragmentShader
        .replace("#include <common>", `#include <common>\n${FRAG_HEAD}`)
        .replace("#include <color_fragment>", `#include <color_fragment>\n${FRAG_COLOR}`)
        .replace("#include <emissivemap_fragment>", `#include <emissivemap_fragment>\n${FRAG_RIM}`);
    };
    m.customProgramCacheKey = () => "arandu-fur-v3";
    materials.push(m);
    return m;
  };

  fur.material = furMaterial(0);
  fur.frustumCulled = false;
  const shells: THREE.SkinnedMesh[] = [];
  for (let i = 1; i <= layers; i++) {
    const s = new THREE.SkinnedMesh(geo, furMaterial(i / layers));
    s.bindMode = fur.bindMode;
    s.bind(skel, fur.bindMatrix);
    s.position.copy(fur.position);
    s.quaternion.copy(fur.quaternion);
    s.scale.copy(fur.scale);
    s.frustumCulled = false;
    s.renderOrder = i;
    fur.parent!.add(s);
    shells.push(s);
  }

  const inverse = new THREE.Quaternion();

  // Each bone matrix chases the real one on a damped spring; the shells read the lagging copy.
  const springLag = (dt: number) => {
    const bm = bones;
    const steps = Math.max(1, Math.ceil(dt * 240));
    const h = dt / steps;
    for (let s = 0; s < steps; s++) {
      for (let i = 0; i < bm.length; i++) {
        const a = PARAMS.stiffness * (bm[i] - lag[i]) - PARAMS.damping * lagVel[i];
        lagVel[i] += a * h;
        lag[i] += lagVel[i] * h;
      }
    }
    lagTex.needsUpdate = true;
  };

  return {
    update(dt, time, keyDir) {
      skel.update();
      springLag(dt);
      fur.getWorldQuaternion(inverse).invert();
      shared.uGravity.value.set(0, -PARAMS.gravity, 0).applyQuaternion(inverse);
      shared.uWindDir.value.set(0.3, 0.1, 1).normalize().applyQuaternion(inverse);
      shared.uTime.value = time;
      shared.uKeyDir.value.copy(keyDir);
    },
    dispose() {
      lagTex.dispose();
      materials.forEach((m) => m.dispose());
    },
  };
}
