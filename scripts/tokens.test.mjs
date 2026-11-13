import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { generate } from "./tokens.mjs";

const read = (path) => readFileSync(new URL(path, import.meta.url), "utf8");
const tokens = JSON.parse(read("../src/design-system/tokens.json"));
const css = generate(tokens);

// Body of the first block that starts with the given header.
const block = (source, header) => {
  const start = source.indexOf(`${header} {`);
  assert.notEqual(start, -1, `missing block: ${header}`);
  const end = source.indexOf("\n}", start);
  return source.slice(start, end);
};

const colors = tokens.color.tokens;
const isThemed = (t) => typeof t.value !== "string";

describe("tokens.css generation", () => {
  it("writes every color under :root and the dark theme, lowercased", () => {
    const root = block(css, ':root, [data-theme="dark"]');
    for (const t of colors) {
      const value = (isThemed(t) ? t.value.dark : t.value).toLowerCase();
      assert.ok(root.includes(`  --${t.name}: ${value};`), `--${t.name}`);
    }
  });

  it("maps every color into the Tailwind theme through its variable", () => {
    const inline = block(css, "@theme inline");
    for (const t of colors) {
      assert.ok(inline.includes(`  --color-${t.name}: var(--${t.name});`), t.name);
    }
  });

  it("puts exactly the themed tokens in the light theme, with their light values", () => {
    const light = block(css, '[data-theme="light"]');
    const lines = light.split("\n").slice(1);
    const themed = colors.filter(isThemed);
    assert.equal(lines.length, themed.length);
    for (const t of themed) {
      assert.ok(lines.includes(`  --${t.name}: ${t.value.light.toLowerCase()};`), t.name);
    }
    for (const t of colors.filter((c) => !isThemed(c))) {
      assert.ok(!lines.some((l) => l.startsWith(`  --${t.name}:`)), `single-value ${t.name} leaked`);
    }
  });

  it("switches off Tailwind's default theme", () => {
    const theme = block(css, "@theme");
    for (const reset of ["--color-*", "--text-*", "--spacing", "--spacing-*", "--radius-*", "--shadow-*"]) {
      assert.ok(theme.includes(`  ${reset}: initial;`), reset);
    }
  });

  it("emits the radius tokens with their values", () => {
    const theme = block(css, "@theme");
    const expected = {
      "radius-sm": "6px",
      "radius-md": "8px",
      "radius-lg": "12px",
      "radius-button": "10px",
      "radius-button-sm": "9px",
      "radius-card": "14px",
      "radius-pill": "999px",
    };
    for (const [name, value] of Object.entries(expected)) {
      assert.ok(theme.includes(`  --${name}: ${value};`), name);
    }
  });

  it("maps space-N tokens to --spacing-N", () => {
    const theme = block(css, "@theme");
    assert.ok(tokens.spacing.tokens.length > 0);
    for (const t of tokens.spacing.tokens) {
      const n = t.name.replace(/^space-/, "");
      assert.ok(theme.includes(`  --spacing-${n}: ${t.value};`), t.name);
    }
  });

  it("writes every spacing token as a plain --space-N variable under :root and the dark theme", () => {
    const root = block(css, ':root, [data-theme="dark"]');
    assert.ok(tokens.spacing.tokens.length > 0);
    for (const t of tokens.spacing.tokens) {
      assert.ok(root.includes(`  --${t.name}: ${t.value};`), t.name);
    }
  });

  it("grows display and h1 on wide screens, and h2 not", () => {
    const display = block(css, "@utility type-display");
    assert.match(display, /@media \(width >= 768px\) \{\s+font-size: 36px;\s+line-height: 42px;/);
    const h1 = block(css, "@utility type-h1");
    assert.match(h1, /@media \(width >= 768px\) \{\s+font-size: 24px;\s+line-height: 30px;/);
    const h2 = block(css, "@utility type-h2");
    assert.ok(!h2.includes("@media"));
  });

  it("maps font faces to their next/font variables", () => {
    const theme = block(css, "@theme");
    assert.ok(theme.includes("  --font-display: var(--font-outfit, Outfit), system-ui, sans-serif;"));
    assert.ok(theme.includes("  --font-body: var(--font-lexend, Lexend), system-ui, sans-serif;"));
  });

  it("keeps the committed tokens.css in sync with tokens.json", () => {
    assert.equal(read("../src/design-system/tokens.css"), css);
  });
});
