# Arandu Reka

AI guidance and preparation companion for Brazilian high-school (ensino médio) students. Arandu, a curious black cat, helps students discover university courses in São Paulo, choose a goal, and prepare for it.

Built for Hack Brasil 2026, Educação track.

## Landing

The landing is a Next.js app at the repository root (see `docs/adr/0001-web-landing-stack-and-architecture.md`).

```sh
npm install
npm run dev
```

- `src/app` holds the routes only; code is grouped by business area (`src/landing`, `src/design-system`).
- `src/design-system/tokens.json` is the design system's tokens file, copied as it is. `npm run tokens` regenerates `tokens.css` from it, and `npm run tokens:check` fails when that file is out of date.
- Tailwind's default palette, type scale, spacing, radii and shadows are switched off: only token utilities exist (`bg-surface`, `text-text-muted`, `p-3`, `rounded-card`, `type-h1`).
- `npm run lint` blocks raw design values in the app: hex and rgb colors, px and rem lengths, Tailwind arbitrary values and inline styles.
- `npm test` runs the tests.
