import { describe, it } from "node:test";
import { RuleTester } from "eslint";
import tsParser from "@typescript-eslint/parser";
import rule from "./no-raw-design-values.mjs";

RuleTester.describe = describe;
RuleTester.it = it;
RuleTester.itOnly = it.only;

const tester = new RuleTester({
  languageOptions: {
    parser: tsParser,
    parserOptions: { ecmaFeatures: { jsx: true } },
  },
});

const bad = (code, messageId) => ({ code, errors: [{ messageId }] });

tester.run("no-raw-design-values", rule, {
  valid: [
    '<p className="type-body text-text-muted p-3 rounded-card md:type-h1" />',
    // section anchors are not colors
    '<a href="#como" />',
    '<a href="#bolinha" />',
    'const url = "/models/arandu.glb"',
    // not a 6/8-digit color number
    "const n = 0x10",
    "const n = 42",
    'const label = "7 DIAS SEGUIDOS"',
    'const cls = "w-1/2 -mt-1"',
  ],
  invalid: [
    // hex color is checked before arbitrary values
    bad('<div className="bg-[#fff]" />', "hexColor"),
    bad('const c = "#09090d"', "hexColor"),
    bad('const c = "#FFF"', "hexColor"),
    bad('const c = "rgb(0 0 0)"', "colorFunction"),
    bad('const c = "oklch(0.5 0.1 200)"', "colorFunction"),
    bad('const s = "12px"', "length"),
    bad('const s = "1.5rem"', "length"),
    bad("const s = `gap: 8px`", "length"),
    // length is checked before arbitrary values
    bad('<p className="md:text-[42px]" />', "length"),
    bad('<p className="[mask-type:luminance]" />', "arbitraryValue"),
    bad("new Color(0x09090d)", "hexNumber"),
    bad('<div style={{ color: "red" }} />', "inlineStyle"),
  ],
});
