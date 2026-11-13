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

/** A book's dress: the token names of its cover and of its print (title and bands). */
export type BookLook = { cover: string; band: string };

export type Kit = {
  make(name: PropName): THREE.Object3D;
  /** A book with a degree course for title, written down its spine and across its covers. */
  book(name: BookName, look: BookLook, career: string): THREE.Object3D;
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

  // A book's print, drawn on a canvas as tall as TEXTURE_HEIGHT and as wide as the face's proportions
  // ask, filled with the cover color. glTF UVs put v = 0 at the top of the image: the top of the
  // canvas is the top of the book.
  const TEXTURE_HEIGHT = 512;
  const paint = (cover: string, width: number, height: number, draw: (g: CanvasRenderingContext2D, w: number, h: number) => void) => {
    const canvas = document.createElement("canvas");
    canvas.height = TEXTURE_HEIGHT;
    canvas.width = Math.max(8, Math.round((TEXTURE_HEIGHT * width) / height));
    const g = canvas.getContext("2d");
    if (!g) throw new Error("No 2D canvas for the book textures");
    g.fillStyle = cover;
    g.fillRect(0, 0, canvas.width, canvas.height);
    draw(g, canvas.width, canvas.height);
    const map = new THREE.CanvasTexture(canvas);
    map.colorSpace = THREE.SRGBColorSpace;
    map.flipY = false;
    map.anisotropy = 4;
    const material = new THREE.MeshStandardMaterial({ map, roughness: 0.6 });
    owned.push(map, material);
    return material;
  };

  // Writes text centred on the canvas origin, in the display font, shrunk to fit maxWidth.
  const write = (g: CanvasRenderingContext2D, text: string, size: number, maxWidth: number) => {
    const font = tokenValue("font-display");
    g.font = `600 ${size}px ${font}`;
    const fit = Math.min(size, (size * maxWidth) / g.measureText(text).width);
    g.font = `600 ${fit}px ${font}`;
    g.textAlign = "center";
    g.textBaseline = "middle";
    g.fillText(text, 0, 0);
  };

  // Each book gets its own spine and covers: no two carry the same title and proportions.
  const dress = (name: BookName, look: BookLook, career: string) => {
    const s = size(name);
    const cover = tokenValue(look.cover);
    const print = tokenValue(look.band);
    // The spine wraps round the book's rounded corners: about 1.45 times its thickness. u runs across
    // it, left to right seen from the front; the title reads down it, as on a real spine, as tall as
    // the front of the spine allows and as long as the space between its bands.
    const spine = paint(cover, s.x * 1.45, s.y, (g, w, h) => {
      g.fillStyle = print;
      g.fillRect(0, h * 0.09, w, h * 0.035);
      g.fillRect(0, h * 0.83, w, h * 0.035);
      g.translate(w / 2, h * 0.47);
      g.rotate(Math.PI / 2);
      write(g, career, w * 0.56, h * 0.66);
    });
    // Both covers map their flat part, from the spine's edge to the fore-edge, onto the full image.
    // The board edges sample its top-right corner, which stays plain.
    const covers = paint(cover, s.z * 0.88, s.y, (g, w, h) => {
      g.fillStyle = print;
      g.fillRect(w * 0.12, h * 0.14, w * 0.76, h * 0.01);
      g.fillRect(w * 0.12, h * 0.46, w * 0.76, h * 0.01);
      g.translate(w / 2, h * 0.3);
      write(g, career, w * 0.17, w * 0.76);
    });
    return { spine, covers };
  };

  const book = (name: BookName, look: BookLook, career: string) => {
    const o = make(name);
    const d = dress(name, look, career);
    o.traverse((m) => {
      if (!(m instanceof THREE.Mesh)) return;
      if (m.material.name === "BookCover") m.material = d.covers;
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
