# ADR-0001: Web landing stack and architecture

- Status: accepted
- Date: 2026-11-13
- Decided by: Alejandro (owner), with the web squad ingeniero

## Context

The web squad builds the informational landing page of Arandu Reka for Hack Brasil 2026 (deadline 2026-11-30 23:59 Brasília). The product itself (student, family and school apps) is out of this squad's current scope.

The landing design is in the diseno squad: live at https://claude.ai/artifact/5z2EBxExjSXYbvAQfzJ8jj, source outside the repo. The design system is at https://claude.ai/artifact/NBNz4q9R1e4jJf9m1cLZaM (`project/README.md`, `project/tokens.json`).

## Decisions

### Scope
- The squad builds the landing only, not the product. No LLM, embeddings or email for now.
- A backend may come later, for example a waitlist button to learn whether judges and early viewers are interested. It is a step after the whole design is built.

### Stack
- Next.js, latest stable version, with TypeScript. Chosen so a backend can be added to the landing later.
- CSS with Tailwind CSS 4.
- shadcn/ui only where it helps, always restyled to the Arandu design system, never its default look.
- Three.js for the 3D scene and GSAP (with ScrollTrigger) for animation. WebGL beyond Three.js is kept on the radar, not planned.

### Hosting
- Vercel.

### Architecture and code rules
- Screaming architecture: code is grouped by business area, not by technical layer.
- The design system is tokenized in the front end. No hard-coded colors, typography, spacing or radii in components; every value comes from the tokens.
- State management is consistent and uses one pattern everywhere. No prop drilling.
- Future data fetching is taken into account in the structure from the start.
- Code is kept clean and scalable so more people can join later.

### Agent workflow rules
- The rules for AI agents and contributors live in the repository (`AGENTS.md`, `CLAUDE.md`, `CONTRIBUTING.md`), modeled on the owner's v2.0 repository.
- Kept from that model: issue-driven development (issue, branch, pull request), verified and cited claims, "keep it small and plain", a lint that blocks raw design values, and the front-end rules.
- Left out because they do not apply here: monorepo rules, fellows, QA team, changesets, NestJS.

### 3D assets (first step)
- The first step of the build is 3D modeling in Blender, done by the AI through the Blender MCP, with the owner running Blender.
- Models: the cat (Arandu, the mascot), books, shelves, a lamp, a yarn ball, and a plant pot if needed.
- Cat GLB contract (from the CTO): the file sits next to `index.html`, feet at the origin, facing +X, animation clips `sit`, `walk`, `jump` and `tap`, and one bone named `head`.
- The Blender MCP server (`uvx mcp-for-blender`) is registered in Claude Code at user scope.

## Open points (not decided here)
- The exact Next.js version is checked when the project is scaffolded.
- In the design system, the README says the logo is never placed next to university logos, which conflicts with the closed decision in commit 0f487fb (logos allowed). Its prose radii (buttons 10px, cards 14px, inputs 8px) also differ from its radius tokens (6, 8, 12, pill). Both were reported to the CTO; which is right is not verified.
