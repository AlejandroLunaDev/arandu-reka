import * as THREE from "three";

// The 3D scene takes its colors from the design tokens the page already loaded (tokens.css), so it
// never holds a color of its own.

/** The CSS value of a token, such as "violet-400". */
export function tokenValue(name: string): string {
  const value = getComputedStyle(document.documentElement).getPropertyValue(`--${name}`).trim();
  if (!value) throw new Error(`Unknown design token: ${name}`);
  return value;
}

export function tokenColor(name: string): THREE.Color {
  return new THREE.Color(tokenValue(name));
}
