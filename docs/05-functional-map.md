# Arandu Reka: feature and screen map (2026-11-12)

Status: **superseded, on hold.** This map follows the first product draft (Enem prep at the core). It will be redone from `01-product-design.md` v2. Kept for reference only.

Original status: draft for the owner's review. It turns the demo flow and features in `01-product-design.md` into screens, and marks what the demo needs first. Items marked **[consultant's call]** are proposals the owner (Alejandro) has not confirmed.

Sources: `01-product-design.md`, `03-brand.md`, `04-sp-data-mapping-summary.md`, and the brand board v2 (https://claude.ai/artifact/JkD2yi29ci8w9kDAVkPese).

## 1. How the demo is judged, and what follows from it

Judges can evaluate three things: the code, the live demo link and a video of up to 3 minutes (regulamento 7.2–7.4). Two consequences shape this map.

1. **The video follows Sofia's scripted path.** Every screen on that path must exist and look finished. This is the critical path (P0).
2. **Judges may use the live app on their own.** They arrive cold, on a phone or a laptop, with no account. They need a fast way in, and a way to see the school and parent views without three logins. **[consultant's call]**

## 2. Priorities

| Priority | Meaning |
|---|---|
| **P0** | On Sofia's video path. Without it there is no story. |
| **P1** | Makes the live demo hold up when a judge explores alone. |
| **P2** | Adds depth. Cut first if the build runs short. |

## 3. Global elements

| ID | Element | What it does | Priority |
|---|---|---|---|
| G1 | Demo entry | The landing offers two doors: "Ver como Sofia" (seeded persona, jumps through the story) and "Começar do zero" (a fresh, empty student). **[consultant's call]** | P0 |
| G2 | Role switcher | A small persistent bar: Estudante / Escola / Família. It replaces real login for the demo, which `01` already rules out. **[consultant's call]** | P0 |
| G3 | Arandu presence | The mascot is in every student screen, with one of four expressions from the brand board (curious, thinking, celebrating, encouraging). | P0 |
| G4 | Sources and method page | "Fontes e metodologia": where each cut-off and curriculum comes from, the edition of each cut-off, and how the gap estimate works. It backs the "real data with cited sources" goal. **[consultant's call]** | P1 |
| G5 | Off-topic guardrail | If a judge types something unrelated, Arandu answers briefly and steers back to the current step. `01` §3b says the owner builds this harness. | P1 |

## 4. Student screens (mobile first)

### S0 Landing
- **Shows:** logo, one line on what Arandu does, the two doors from G1.
- **Live or seeded:** static.
- **Priority:** P0.

### S1 Conversation with Arandu (F1)
- **Shows:** chat in Portuguese, in Arandu's voice. Five or six questions: favourite subjects, free time, what is hard. Each question offers quick-reply chips and a free-text field. A progress hint ("3 de 6").
- **Live or seeded:** live LLM. On the Sofia path the answers are pre-filled.
- **Done when:**
  - Arandu asks one question at a time.
  - Every answer feeds a structured profile (interests, liked subjects, hard subjects), not just a transcript.
  - Off-topic input gets steered back (G5).
- **Priority:** P0.

### S2 Grades (F2)
- **Shows:** a form with the student's latest grades per subject, plus a "Usar boletim de exemplo" button that fills synthetic grades.
- **Live or seeded:** form input; the example is seeded.
- **Done when:** grades map to the four Enem areas plus the essay, so the gap step can use them.
- **Priority:** P0 for the form. File upload is P2 and the first cut. **[consultant's call]**

### S3 "Isto é o que entendi sobre você" (F3)
- **Shows:** the profile as editable chips: interests, strong subjects and weak subjects. One button to confirm.
- **Live or seeded:** live, built from S1 and S2.
- **Done when:**
  - The student can remove or add any item before continuing.
  - Her corrections, not the first draft, feed S4.
- **Priority:** P0.

### S4 Three courses (F4)
- **Shows:** three course cards. Each card has a one-line reason that links back to the profile ("Porque você curte lógica e matemática").
- **Live or seeded:** live ranking over all courses at the 8 demo institutions (owner's decision in `01` §3b).
- **Done when:**
  - Every reason cites at least one item from the profile.
  - No paid or sponsored ordering exists anywhere (anti-goal).
- **Priority:** P0.

### S5 Course detail (F4)
- **Shows:**
  - curriculum by year;
  - where it is offered in SP;
  - the cut-off, with its source link and edition;
  - two actions: "Experimentar" (S6) and "Quero este objetivo" (S7).
- **Live or seeded:** data from the dataset (D1).
- **Done when:**
  - Every cut-off shows its edition and source link.
  - A SISU cut-off says which quota group it belongs to (ampla concorrência by default).
  - **A ProUni cut-off is labelled as the score for a ProUni scholarship, with its eligibility label.** It is not the general admission bar of that private institution. Showing it as "the cut-off" would mislead the student. **[consultant's call]**
  - USP courses with only Fuvest data show the Fuvest score on its own scale, never next to Enem numbers.
  - No institution logos, and no prose copied from institution sites.
- **Priority:** P0.

### S6 Mini-challenge (F5)
- **Shows:** three to five short questions built from a real first-year subject of that course, then a light result ("Você foi bem em lógica; é isso que se vê no 1º ano").
- **Live or seeded:** hand-checked for Sofia's three courses. For other courses, generated from real subject names and labelled "gerado" (`01` §3b).
- **Done when:** the subject name and the year it comes from are visible, and generated challenges carry their label.
- **Priority:** P0 for Sofia's three courses. Generated challenges for other courses are P2.

### S7 Choose the goal (F6)
- **Shows:** the chosen course and institution, the entry route (SISU, ProUni or Fuvest), and the quota group (default: ampla concorrência).
- **Live or seeded:** live.
- **Done when:**
  - A ProUni route shows the eligibility requirement before the student confirms.
  - The goal can be changed later from the plan.
- **Priority:** P0.

### S8 Diagnostic (F7)
- **Shows:** a short Enem-style quiz across the areas, with Arandu in his thinking expression.
- **Live or seeded:** the question bank is fixed. Scoring is live.
- **Done when:** the question source and its licence are recorded (`01` §7).
- **Priority:** P0.

### S9 The gap (F7): the winning moment
- **Shows:** for each area, the student's estimated range next to the target derived from the real cut-off. Weakest areas come first. Arandu closes with the encouraging expression.
- **Live or seeded:** live.
- **Done when:**
  - Every estimate is shown as a labelled range, never as one exact Enem score (anti-goal).
  - If the dataset has no per-area weights for the course, the screen shows the overall gap plus the weakest areas (`01` §6).
- **Priority:** P0.

### S10 Plan (F8)
- **Shows:** the weekly plan up to the Enem, today's mission and the streak.
- **Live or seeded:** the plan is generated live from the gap. The streak history on the Sofia path is seeded.
- **Done when:** the plan puts more weight on the areas with the largest gap.
- **Priority:** P0.

### S11 Today's mission (F8)
- **Shows:** a short practice set for today, then celebration and the streak going up.
- **Priority:** P1. If short, S10 shows the mission without running it.

### S12 What my family sees (F10)
- **Shows:** toggles per goal: shared or not. The conversation is never shared.
- **Done when:** the parent report shows only what is switched on here.
- **Priority:** P1. The Sofia path shows it in one tap before the parent view.

## 5. School coordinator (desktop first)

### C1 Class dashboard (F9)
- **Shows:** the year-2 class (about 30 synthetic students):
  - interest areas, using the chart palette from the brand board;
  - gaps by Enem area for the chosen courses, for example "60% estão fracos em Matemática para os cursos que escolheram";
  - plan progress.
- **Live or seeded:** seeded class. Sofia's live session may join it.
- **Done when:**
  - Everything is aggregated and anonymous.
  - No group smaller than 5 students is shown, so no one can be identified. **[consultant's call]**
- **Priority:** P0. It carries the B2B story.

## 6. Parents

### P1 Weekly report (F10)
- **Shows:** the shared goals, plan progress, the streak and next steps, as one screen styled like an email preview.
- **Done when:** it shows progress, never the conversation (owner confirmed in `01` §4).
- **Priority:** P0 as a single screen. Real email sending is out of scope.

## 7. Sofia's video path (P0 critical path)

S0 → S1 → S2 → S3 → S4 → S5 → S6 → S7 → S8 → S9 → S10 → G2 to Escola → C1 → G2 to Família → P1.

## 8. Cut order if the build runs short

Cut from the top. Each cut keeps the story intact.

1. File upload in S2 (the form stays).
2. Generated mini-challenges for courses outside Sofia's path (S6 shows "em breve" for those).
3. Running the mission in S11 (S10 still shows it).
4. S12 as its own screen (sharing is pre-set on the Sofia path and explained in P1).
5. G4 as a full page (keep the source link on every cut-off).

## 9. Decisions waiting for the owner

1. **Sofia's goal course.** It needs direct entry, a term-ordered curriculum and a SISU cut-off in the dataset. UFABC fails the first two (interdisciplinary entry was not verified; no term order). By the mapping in `04`, Unifesp has the easiest curriculum to extract and has SISU cut-offs. A Unifesp computing course is a candidate, but its entry route has not been checked.
2. **The ProUni label** in S5 and S7 (§4).
3. **The two demo doors and the role switcher** (G1, G2).
4. **The minimum group size** on the coordinator dashboard (C1).
5. **The diagnostic question source and its licence** (S8).
