// ESLint rule: design values come from the design tokens (src/design-system/tokens.json), never
// written by hand. It reports, in any string or template: hex colors, color functions such as
// rgb() or hsl(), px/rem/em/pt lengths, and Tailwind arbitrary values such as p-[13px]. It also
// reports hex color numbers (0x09090d, as three.js takes them) and inline JSX style attributes.

const CHECKS = [
  ["hexColor", /(?:^|[^\w&])#(?:[0-9a-f]{8}|[0-9a-f]{6}|[0-9a-f]{3,4})(?![\w-])/i],
  ["colorFunction", /\b(?:rgba?|hsla?|hwb|lab|lch|oklab|oklch)\(/i],
  ["length", /(?:^|[^\w.-])-?(?:\d*\.)?\d+(?:px|rem|em|pt)(?![\w-])/],
  ["arbitraryValue", /(?:^|[\s:!])-?[a-z][\w-]*-\[[^\]\s]+\]|(?:^|[\s:!])\[[a-z-]+:[^\]\s]+\]/],
];

const rule = {
  meta: {
    type: "problem",
    docs: { description: "Disallow design values that do not come from the design tokens." },
    schema: [],
    messages: {
      hexColor: "Raw hex color: use a color token (bg-surface, text-text-muted...).",
      colorFunction: "Raw color function: use a color token (bg-surface, text-text-muted...).",
      length: "Raw length: use a spacing, radius or type token (p-3, rounded-card, type-body...).",
      arbitraryValue: "Tailwind arbitrary value: use a token utility, or add the value to the design tokens.",
      hexNumber: "Raw hex color number: read the color from the design tokens.",
      inlineStyle: "Inline style bypasses the design tokens: use token utilities.",
    },
  },
  create(context) {
    const check = (node, text) => {
      const found = CHECKS.find(([, pattern]) => pattern.test(text));
      if (found) context.report({ node, messageId: found[0] });
    };
    return {
      Literal(node) {
        if (typeof node.value === "string") check(node, node.value);
        else if (typeof node.value === "number" && /^0x(?:[0-9a-f]{6}|[0-9a-f]{8})$/i.test(node.raw)) {
          context.report({ node, messageId: "hexNumber" });
        }
      },
      TemplateElement(node) {
        check(node, node.value.raw);
      },
      JSXAttribute(node) {
        if (node.name.name === "style") context.report({ node, messageId: "inlineStyle" });
      },
    };
  },
};

export default rule;
