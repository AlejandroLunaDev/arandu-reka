import { gsap } from "gsap";
import * as THREE from "three";
import { DRACOLoader } from "three/addons/loaders/DRACOLoader.js";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import { makeCat } from "./cat";
import { tokenColor } from "./palette";
import { makeKit, type Kit } from "./props";
import { heroRoom, knowYouRoom, TILT, type Room } from "./rooms";

// The landing's 3D layer: one fixed canvas over the page that never takes clicks. Each scene with a
// [data-room] anchor gets its room of shelves, and Arandu follows the scroll from room to room. While
// a scene is pinned he sits and watches the pointer; while the next scene comes in he walks or leaps
// to its seat. If WebGL or the models fail, <html> gets the "no3d" class and the page shows its
// drawn cats instead.

const BUILD: Record<string, (anchor: HTMLElement, kit: Kit) => Room> = {
  hero: heroRoom,
  "know-you": knowYouRoom,
};

const clamp = (v: number, a: number, b: number) => Math.min(b, Math.max(a, v));
const lerp = (a: number, b: number, t: number) => a + (b - a) * t;
const smooth = (a: number, b: number, v: number) => {
  const t = clamp((v - a) / (b - a), 0, 1);
  return t * t * (3 - 2 * t);
};
const ease = (t: number) => (t < 0.5 ? 2 * t * t : 1 - (-2 * t + 2) ** 2 / 2);

/** A soft round shadow, 1 by 1, lying flat: its alpha falls off from the middle. */
function shadowTexture() {
  const n = 64;
  const data = new Uint8Array(n * n * 4);
  for (let y = 0; y < n; y++) {
    for (let x = 0; x < n; x++) {
      const r = Math.hypot(x - n / 2 + 0.5, y - n / 2 + 0.5) / (n / 2);
      const v = Math.round(255 * Math.max(0, 1 - r) ** 1.6);
      data.set([v, v, v, v], (y * n + x) * 4);
    }
  }
  const tex = new THREE.DataTexture(data, n, n, THREE.RGBAFormat);
  tex.needsUpdate = true;
  return tex;
}

/** Starts the stage in host and returns its cleanup. */
export function runStage(host: HTMLElement): () => void {
  const root = document.documentElement;
  const canvas = document.createElement("canvas");
  host.appendChild(canvas);
  const fail = () => {
    root.classList.add("no3d");
    canvas.remove();
  };

  let renderer: THREE.WebGLRenderer;
  try {
    renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true });
  } catch {
    fail();
    return () => {};
  }
  renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
  renderer.outputColorSpace = THREE.SRGBColorSpace;

  let cancelled = false;
  const stops: Array<() => void> = [];
  const cleanup = () => {
    cancelled = true;
    stops.forEach((stop) => stop());
    renderer.dispose();
    canvas.remove();
  };

  const draco = new DRACOLoader().setDecoderPath("/draco/");
  const loader = new GLTFLoader().setDRACOLoader(draco);
  // The books print their titles in the page's display font: wait for it too.
  Promise.all([loader.loadAsync("/models/arandu.glb"), loader.loadAsync("/models/props.glb"), document.fonts.ready])
    .then(([catGltf, propsGltf]) => {
      draco.dispose();
      if (cancelled) return;
      stops.push(start(renderer, catGltf, propsGltf));
    })
    .catch((error: unknown) => {
      draco.dispose();
      if (cancelled) return;
      console.error("The 3D stage could not start", error);
      fail();
    });

  return cleanup;
}

type Gltf = Awaited<ReturnType<GLTFLoader["loadAsync"]>>;

function start(renderer: THREE.WebGLRenderer, catGltf: Gltf, propsGltf: Gltf): () => void {
  const reduce = matchMedia("(prefers-reduced-motion: reduce)").matches;

  const scene = new THREE.Scene();
  // Pixel units: one unit is one CSS pixel, the origin at the middle of the viewport.
  const camera = new THREE.OrthographicCamera(-1, 1, 1, -1, -4000, 4000);
  camera.position.z = 2000;

  scene.add(new THREE.HemisphereLight(tokenColor("cream-100"), tokenColor("ink-800"), 1.3));
  const key = new THREE.DirectionalLight(tokenColor("cream-50"), 2.4);
  key.position.set(1.2, 1.6, 0.9);
  scene.add(key);
  const back = new THREE.DirectionalLight(tokenColor("cream-200"), 1.6);
  back.position.set(-1.5, 0.8, -1);
  scene.add(back);

  const kit = makeKit(propsGltf);
  const rooms = [...document.querySelectorAll<HTMLElement>("[data-room]")].map((anchor) => {
    const build = BUILD[anchor.dataset.room ?? ""];
    if (!build) throw new Error(`Unknown room: ${anchor.dataset.room}`);
    const room = build(anchor, kit);
    scene.add(room.group);
    return room;
  });
  if (rooms.length === 0) throw new Error("The page has no [data-room] anchor");

  // One warm light per room, hung at its main lamp's bulb. The count never changes, so the shaders
  // compile once.
  const lights = rooms.map(() => {
    const light = new THREE.PointLight(tokenColor("amber-300"), 1.4, 1, 0);
    scene.add(light);
    return light;
  });

  const cat = makeCat(catGltf);
  scene.add(cat.root);
  // The cat's soft shadow, 1 m by 1 m, lying flat under him.
  const shadowTex = shadowTexture();
  const shadowGeo = new THREE.PlaneGeometry(1, 1).rotateX(-Math.PI / 2);
  const catShadowMaterial = new THREE.MeshBasicMaterial({
    color: tokenColor("ink-950"),
    alphaMap: shadowTex,
    transparent: true,
    opacity: 0.55,
    depthWrite: false,
  });
  const catShadow = new THREE.Mesh(shadowGeo, catShadowMaterial);
  scene.add(catShadow);

  // The cat leaves room i - 1 for room i while the scene of room i comes in: from when its top is
  // 85% of the viewport down to when it reaches the top.
  let W = 0;
  let H = 0;
  let ranges: Array<[number, number]> = [];
  const layout = () => {
    W = innerWidth;
    H = innerHeight;
    renderer.setSize(W, H, false);
    Object.assign(camera, { left: -W / 2, right: W / 2, top: H / 2, bottom: -H / 2 });
    camera.updateProjectionMatrix();
    rooms.forEach((r) => r.layout());
    ranges = rooms.map((r) => {
      const top = r.scene.getBoundingClientRect().top + scrollY;
      return [top - H * 0.85, top];
    });
  };
  const progress = () => {
    let p = 0;
    for (let i = 1; i < ranges.length; i++) {
      const [s, e] = ranges[i];
      const f = clamp((scrollY - s) / (e - s), 0, 1);
      p += f;
      if (f < 1) break;
    }
    return p;
  };

  let laidOut = false;
  const relayout = () => {
    if (laidOut) return;
    laidOut = true;
    requestAnimationFrame(() => {
      laidOut = false;
      layout();
    });
  };
  addEventListener("resize", relayout);
  const watcher = new ResizeObserver(relayout);
  watcher.observe(document.body);
  document.fonts?.ready.then(relayout);
  layout();

  const pointer = { x: 0, y: 0, on: false };
  const onPointer = (e: PointerEvent) => {
    if (e.pointerType !== "mouse") return;
    pointer.x = e.clientX;
    pointer.y = e.clientY;
    pointer.on = true;
  };
  addEventListener("pointermove", onPointer, { passive: true });

  // The first room makes its entrance once the models are in: the shelves rise, the lamp drops.
  const intro = { rise: reduce ? 1 : 0, drop: reduce ? 1 : 0 };
  const tweens = reduce
    ? []
    : [
        gsap.to(intro, { rise: 1, duration: 1, ease: "power3.out" }),
        gsap.to(intro, { drop: 1, duration: 1.4, ease: "elastic.out(1, 0.5)", delay: 0.15 }),
      ];
  const pa = new THREE.Vector3();
  const pb = new THREE.Vector3();
  const look = new THREE.Vector3();
  let pS = progress();
  let yawNow = rooms[0].face;
  let stride = 0;
  let prevX: number | null = null;
  let last = performance.now();
  let raf = 0;

  const frame = (now: number) => {
    raf = requestAnimationFrame(frame);
    const dt = Math.min(0.05, (now - last) / 1000);
    last = now;
    const t = now / 1000;

    rooms[0].reveal(intro.rise, intro.drop);
    rooms.forEach((r, i) => {
      r.place(W, H);
      r.light.getWorldPosition(lights[i].position);
      lights[i].distance = 2.2 * r.k;
    });
    kit.tick(t);

    pS = reduce ? progress() : lerp(pS, progress(), 1 - 0.0009 ** dt);
    const i0 = clamp(Math.floor(pS), 0, Math.max(0, rooms.length - 2));
    const iB = Math.min(i0 + 1, rooms.length - 1);
    const f = clamp(pS - i0, 0, 1);
    const A = rooms[i0];
    const B = rooms[iB];
    A.seat.getWorldPosition(pa);
    B.seat.getWorldPosition(pb);
    const e = ease(f);
    const dx = pb.x - pa.x;
    const dy = pb.y - pa.y;
    const leap = Math.abs(dy) > 24 || Math.abs(dx) > W * 0.3;
    const air = leap && !reduce ? Math.sin(Math.PI * f) : 0;
    const x = lerp(pa.x, pb.x, e);
    const y = lerp(pa.y, pb.y, e);
    const z = lerp(pa.z, pb.z, e);
    const k = lerp(A.k, B.k, e);
    const hop = air * (k * 0.5 + Math.abs(dy) * 0.25);
    const sit = 1 - smooth(0, 0.16, f) * (1 - smooth(0.84, 1, f));

    cat.root.position.set(x, y + hop, z);
    cat.root.scale.setScalar(k);
    cat.root.rotation.x = TILT;
    // In profile while he travels, a three-quarter turn toward the copy while he sits.
    const yawTo = sit < 0.5 ? (dx >= 0 ? 0 : -Math.PI) : (f < 0.5 ? A : B).face;
    yawNow = lerp(yawNow, yawTo, 1 - 0.004 ** dt);
    cat.yaw.rotation.y = yawNow;
    if (prevX !== null && !air) stride += Math.abs(x - prevX) / (k * 0.35);
    prevX = x;

    const watching = pointer.on && sit > 0.5;
    if (watching) look.set(pointer.x - W / 2, H / 2 - pointer.y, 700);
    cat.update({ sit, leap: f, air, stride, look: watching ? look : null }, dt, t);

    const lift = 1 - Math.min(0.7, hop / (k * 1.2));
    catShadow.position.set(x, y + 0.004 * k, z);
    catShadow.rotation.x = TILT;
    catShadow.scale.set(k * 0.62 * lift, 1, k * 0.3 * lift);
    catShadowMaterial.opacity = 0.55 * lift;

    renderer.render(scene, camera);
  };
  raf = requestAnimationFrame(frame);

  return () => {
    cancelAnimationFrame(raf);
    tweens.forEach((tween) => tween.kill());
    removeEventListener("resize", relayout);
    removeEventListener("pointermove", onPointer);
    watcher.disconnect();
    cat.dispose();
    kit.dispose();
    shadowTex.dispose();
    shadowGeo.dispose();
    catShadowMaterial.dispose();
  };
}
