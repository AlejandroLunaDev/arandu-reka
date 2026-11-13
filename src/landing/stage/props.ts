import * as THREE from "three";
import type { GLTF } from "three/addons/loaders/GLTFLoader.js";
import { tokenColor, tokenValue } from "./palette";

// The room props from public/models/props.glb (built by blender/props/build.py). Units are metres,
// Y is up and every prop faces +Z, toward the camera. Each root node is one prop, its origin where
// the room places it: the centre of the base, or the centre of the plank's top for the shelves.

export type BookName = "Book" | "BookTall" | "BookSlim" | "BookThick" | "BookShort" | "BookPaperback";
export type PropName =
  | BookName
  | "ShelfLarge"
  | "ShelfMedium"
  | "ShelfSmall"
  | "LampClassic"
  | "LampDesk"
  | "LampMushroom"
  | "LampPendant"
  | "PlantPot"
  | "YarnBall"
  | "Ball";

/** A book's dress: the token names of its cover and of the two bands across its spine. */
export type BookLook = { cover: string; band: string };

export type Kit = {
  make(name: PropName): THREE.Object3D;
  book(name: BookName, look: BookLook): THREE.Object3D;
  /** Width (x), height (y) and depth (z) of a prop, in metres. */
  size(name: PropName): THREE.Vector3;
  tick(time: number): void;
  dispose(): void;
};

// The plant's vertices carry "_sway": 0 at the pot, 1 at the vine tips.
const SWAY_HEAD = /* glsl */ `
attribute float sway;
uniform float uTime;
`;
const SWAY_BODY = /* glsl */ `
transformed.x += sway * 0.03 * sin(uTime * 1.3 + position.y * 4.0);
transformed.z += sway * 0.015 * sin(uTime * 0.9 + position.x * 5.0);
`;

export function makeKit(gltf: GLTF): Kit {
  const protos = new Map<string, THREE.Object3D>();
  for (const child of gltf.scene.children) protos.set(child.name, child);

  const owned: Array<THREE.Material | THREE.Texture> = [];
  const time = { value: 0 };

  gltf.scene.traverse((o) => {
    if (!(o instanceof THREE.Mesh)) return;
    const m = o.material as THREE.MeshStandardMaterial;
    // Lamps are built switched off: the landing lights them.
    if (m.name === "LampBulb") {
      m.color.copy(tokenColor("amber-300"));
      m.emissive.copy(tokenColor("amber-300"));
      m.emissiveIntensity = 1.4;
    }
    if (m.name === "LampShadeInner") {
      m.emissive.copy(tokenColor("amber-200"));
      m.emissiveIntensity = 0.7;
    }
    const sway = o.geometry.getAttribute("_sway");
    if (sway) {
      o.geometry.setAttribute("sway", sway);
      if (!m.userData.sways) {
        m.userData.sways = true;
        m.onBeforeCompile = (shader) => {
          shader.uniforms.uTime = time;
          shader.vertexShader = shader.vertexShader
            .replace("#include <common>", `#include <common>\n${SWAY_HEAD}`)
            .replace("#include <begin_vertex>", `#include <begin_vertex>\n${SWAY_BODY}`);
        };
        m.customProgramCacheKey = () => "arandu-sway";
      }
    }
  });

  const proto = (name: string) => {
    const p = protos.get(name);
    if (!p) throw new Error(`props.glb has no ${name}`);
    return p;
  };

  const sizes = new Map<string, THREE.Vector3>();
  const size = (name: PropName) => {
    let s = sizes.get(name);
    if (!s) {
      const p = proto(name);
      const saved = p.position.clone();
      p.position.set(0, 0, 0);
      p.updateMatrixWorld(true);
      s = new THREE.Box3().setFromObject(p).getSize(new THREE.Vector3());
      p.position.copy(saved);
      sizes.set(name, s);
    }
    return s;
  };

  const make = (name: PropName) => {
    const o = proto(name).clone();
    o.position.set(0, 0, 0);
    return o;
  };

  // One spine texture and one cover material per look, shared by every book that wears it.
  const looks = new Map<string, { cover: THREE.MeshStandardMaterial; spine: THREE.MeshStandardMaterial }>();
  const dress = (look: BookLook) => {
    const key = `${look.cover}/${look.band}`;
    let d = looks.get(key);
    if (!d) {
      const canvas = document.createElement("canvas");
      canvas.width = 32;
      canvas.height = 128;
      const g = canvas.getContext("2d")!;
      g.fillStyle = tokenValue(look.cover);
      g.fillRect(0, 0, 32, 128);
      g.fillStyle = tokenValue(look.band);
      g.fillRect(0, 12, 32, 5);
      g.fillRect(0, 106, 32, 5);
      const map = new THREE.CanvasTexture(canvas);
      map.colorSpace = THREE.SRGBColorSpace;
      // glTF UVs put v = 0 at the top of the image.
      map.flipY = false;
      const spine = new THREE.MeshStandardMaterial({ map, roughness: 0.6 });
      const cover = new THREE.MeshStandardMaterial({ color: tokenColor(look.cover), roughness: 0.6 });
      owned.push(map, spine, cover);
      d = { cover, spine };
      looks.set(key, d);
    }
    return d;
  };

  const book = (name: BookName, look: BookLook) => {
    const o = make(name);
    const d = dress(look);
    o.traverse((m) => {
      if (!(m instanceof THREE.Mesh)) return;
      if (m.material.name === "BookCover") m.material = d.cover;
      if (m.material.name === "BookSpine") m.material = d.spine;
    });
    return o;
  };

  return {
    make,
    book,
    size,
    tick(t) {
      time.value = t;
    },
    dispose() {
      owned.forEach((o) => o.dispose());
      gltf.scene.traverse((o) => {
        if (!(o instanceof THREE.Mesh)) return;
        o.geometry.dispose();
        (o.material as THREE.Material).dispose();
      });
    },
  };
}
