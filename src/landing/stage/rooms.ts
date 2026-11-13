import * as THREE from "three";
import type { BookLook, BookName, Kit } from "./props";

// Each scene's room is composed here in metres and drawn over the page. A room follows one element
// of its scene, its anchor ([data-room]): the room's origin sits on the anchor's bottom-left corner,
// and the anchor's --room-k says how many pixels a metre is. The page's CSS keeps the layout; the
// room only dresses it.

/** The rooms and the cat lean back a little, so the shelves show their tops. */
export const TILT = 0.22;

/** Where the cat looks while he sits: a three-quarter turn toward the scene's text. */
const FACE = { left: -2.25, right: -0.9 };

export type Room = {
  anchor: HTMLElement;
  /** The scene the room belongs to: the cat moves to it while that scene scrolls in. */
  scene: HTMLElement;
  group: THREE.Group;
  /** Where the cat sits, a point on a plank. */
  seat: THREE.Object3D;
  /** The bulb of the room's main lamp: the stage hangs a warm light there. */
  light: THREE.Object3D;
  /** The cat's turn about Y while he sits here. */
  face: number;
  /** Pixels per metre. */
  k: number;
  /** Re-reads the anchor's scale and size: call it when the layout changes. */
  layout(): void;
  /** Follows the anchor: call it every frame, with the viewport size. */
  place(width: number, height: number): void;
  /**
   * The entrance of the page's first room, once the models are in: rise and drop go from 0 to 1.
   * The other rooms come in with their anchors, which the page animates.
   */
  reveal(rise: number, drop: number): void;
};

export type RoomTools = {
  kit: Kit;
  /** A soft contact shadow, 1 m by 1 m, lying flat. */
  shadow(): THREE.Object3D;
};

type Shelved = [BookName, BookLook] | [BookName, BookLook, "lean"];

const LOOK = {
  v8: { cover: "violet-800", band: "violet-400" },
  v6: { cover: "violet-600", band: "cream-300" },
  v4: { cover: "violet-400", band: "violet-800" },
  a8: { cover: "amber-800", band: "amber-400" },
  a6: { cover: "amber-600", band: "cream-100" },
  a4: { cover: "amber-400", band: "amber-800" },
  c3: { cover: "cream-300", band: "violet-600" },
  i7: { cover: "ink-700", band: "amber-400" },
} satisfies Record<string, BookLook>;

const GAP = 0.006;
const LEAN = 0.16;

function put(parent: THREE.Object3D, o: THREE.Object3D, x: number, y: number, z = 0) {
  o.position.set(x, y, z);
  parent.add(o);
  return o;
}

/** Stands books side by side from x, left to right; returns the x where the row ends. */
function standBooks(kit: Kit, parent: THREE.Object3D, x: number, y: number, books: Shelved[]) {
  let cx = x;
  for (const [name, look, lean] of books) {
    const s = kit.size(name);
    const b = kit.book(name, look);
    if (lean) {
      // Tipped onto its left neighbour: it pivots on its bottom-left edge, its top resting on the
      // neighbour's.
      const shift = s.y * Math.sin(LEAN);
      b.rotation.z = LEAN;
      put(parent, b, cx + shift + (s.x / 2) * Math.cos(LEAN), y + (s.x / 2) * Math.sin(LEAN));
      cx += shift + s.x * Math.cos(LEAN) + GAP;
    } else {
      put(parent, b, cx + s.x / 2, y);
      cx += s.x + GAP;
    }
  }
  return cx;
}

/** Lays books flat in a pile from x, spines to the front; returns the height of its top. */
function pileBooks(kit: Kit, parent: THREE.Object3D, x: number, y: number, books: Array<[BookName, BookLook]>) {
  let cy = y;
  books.forEach(([name, look], i) => {
    const s = kit.size(name);
    const b = kit.book(name, look);
    b.rotation.set(0, (i % 2 ? -1 : 1) * 0.04, -Math.PI / 2);
    put(parent, b, x + (i % 2) * 0.012, cy + s.x / 2);
    cy += s.x;
  });
  return cy;
}

function seatAt(parent: THREE.Object3D, x: number, y: number) {
  const seat = new THREE.Object3D();
  return put(parent, seat, x, y);
}

function readK(anchor: HTMLElement) {
  const k = parseFloat(getComputedStyle(anchor).getPropertyValue("--room-k"));
  if (!Number.isFinite(k) || k <= 0) throw new Error("A [data-room] anchor needs --room-k");
  return k;
}

function base(anchor: HTMLElement, face: number) {
  const group = new THREE.Group();
  const content = new THREE.Group();
  group.add(content);
  const scene = anchor.closest<HTMLElement>("[data-scene]");
  if (!scene) throw new Error("A [data-room] anchor must sit inside a [data-scene]");
  // One object for the room's whole life: the stage keeps it and reads k from it every frame.
  const room: Room = {
    anchor,
    scene,
    group,
    seat: new THREE.Object3D(),
    light: group,
    face,
    k: readK(anchor),
    layout() {
      room.k = readK(anchor);
    },
    reveal() {},
    place(width, height) {
      const r = anchor.getBoundingClientRect();
      group.position.set(r.left - width / 2, height / 2 - r.bottom, 0);
      group.scale.setScalar(room.k);
      group.rotation.x = TILT;
      group.updateMatrixWorld(true);
    },
  };
  return Object.assign(room, { content });
}

/** The hero: two wall shelves, a hanging lamp, and the cat waiting on the lower shelf. */
export function heroRoom(anchor: HTMLElement, { kit }: RoomTools): Room {
  const room = base(anchor, FACE.left);
  const { content } = room;

  // Lower shelf: books, the cat, and a ball of yarn that lost a strand toward him.
  put(content, kit.make("ShelfLarge"), 0.8, 0);
  const end = standBooks(kit, content, 0.1, 0, [
    ["Book", LOOK.v6],
    ["BookTall", LOOK.a6],
    ["BookSlim", LOOK.c3],
    ["BookThick", LOOK.v8],
    ["BookShort", LOOK.a4, "lean"],
  ]);
  const seat = seatAt(content, end + 0.25, 0);
  standBooks(kit, content, end + 0.52, 0, [
    ["BookPaperback", LOOK.a8],
    ["Book", LOOK.v4],
  ]);
  // Its strand runs back along the plank, to the shelf's end.
  const yarn = put(content, kit.make("YarnBall"), 1.29, 0, 0.05);
  yarn.rotation.y = 0.6;

  // Upper shelf: the plant hangs over its edge, books lie in a pile, a little lamp glows.
  const upper = new THREE.Group();
  put(content, upper, 1.25, 1.0);
  put(upper, kit.make("ShelfMedium"), 0, 0);
  // The plant stands POT_EDGE (0.12 m) behind the shelf's front edge (0.17 m from its middle).
  put(upper, kit.make("PlantPot"), -0.36, 0, 0.05);
  pileBooks(kit, upper, 0, 0, [
    ["BookThick", LOOK.v6],
    ["BookShort", LOOK.c3],
    ["BookPaperback", LOOK.i7],
  ]);
  const mushroom = put(upper, kit.make("LampMushroom"), 0.36, 0);

  // The pendant lamp hangs from above the top of the screen. Where the copy sits above the room
  // (one column), its cord would cross the copy: there the anchor's --room-pendant is 0 and the
  // room goes without it.
  const pendant = kit.make("LampPendant");
  const cord = pendant.getObjectByName("LampPendantCord");
  const LAMP_Y = 1.75;
  put(content, pendant, 0.35, LAMP_Y);

  room.seat = seat;
  room.layout = () => {
    room.k = readK(anchor);
    pendant.visible = getComputedStyle(anchor).getPropertyValue("--room-pendant").trim() !== "0";
    const lamp = pendant.visible ? pendant : mushroom;
    room.light = lamp.getObjectByName(pendant.visible ? "LampPendantLight" : "LampMushroomLight") ?? lamp;
    // The cord reaches past the top of the pinned scene, wherever the anchor sits in it.
      const pin = anchor.closest<HTMLElement>("[data-pin]") ?? anchor;
      const above = (anchor.getBoundingClientRect().bottom - pin.getBoundingClientRect().top) / room.k;
    if (cord) cord.scale.y = Math.max(0.2, above - LAMP_Y + 0.4);
  };
  room.reveal = (rise, drop) => {
    content.position.y = -0.5 * (1 - rise);
    pendant.position.y = LAMP_Y + 1.6 * (1 - drop);
  };
  room.layout();
  return room;
}

/** "O Arandu te conhece": the phone stands on its shelf; the cat waits higher up, beside it. */
export function knowYouRoom(anchor: HTMLElement, { kit, shadow }: RoomTools): Room {
  const room = base(anchor, FACE.right);
  const { content } = room;

  // The anchor is the phone: its shelf and shadow, and everything to its right, follow its width.
  const under = put(content, kit.make("ShelfLarge"), 0, 0);
  const phoneShadow = put(content, shadow(), 0, 0.002, 0);

  const right = new THREE.Group();
  content.add(right);
  const mid = new THREE.Group();
  put(right, mid, 0.66, 0.9);
  put(mid, kit.make("ShelfMedium"), 0, 0);
  const end = standBooks(kit, mid, -0.49, 0, [
    ["BookThick", LOOK.a8],
    ["BookSlim", LOOK.c3],
  ]);
  const seat = seatAt(mid, end + 0.27, 0);
  const lamp = put(mid, kit.make("LampClassic"), 0.34, 0);

  const top = new THREE.Group();
  put(right, top, 0.66, 1.9);
  put(top, kit.make("ShelfSmall"), 0, 0);
  put(top, kit.make("LampDesk"), -0.18, 0);
  put(top, kit.book("BookTall", LOOK.v4), 0.07, 0);
  put(top, kit.make("Ball"), 0.19, 0, 0.04);

  const fit = () => {
    const w = anchor.getBoundingClientRect().width / room.k;
    under.position.x = w / 2;
    phoneShadow.position.x = w / 2;
    phoneShadow.scale.set(w * 1.05, 1, 0.14);
    right.position.x = w;
  };

  room.seat = seat;
  room.light = lamp.getObjectByName("LampClassicLight") ?? lamp;
  room.layout = () => {
    room.k = readK(anchor);
    fit();
  };
  room.layout();
  return room;
}
