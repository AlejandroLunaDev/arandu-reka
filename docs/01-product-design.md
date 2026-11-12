# Arandu Reka: product design (v2, 2026-11-12)

Status: scope agreed with the owner (Alejandro) on 2026-11-12. This replaces the first draft (`arandu-reka/docs/01-product-design.md`). That draft centred on Enem preparation and used the persona Ana. Items marked **[consultant's call]** are proposals the owner has not confirmed. `05-functional-map.md` is on hold: it follows the old model and will be redone from this document.

## 1. Intent

Arandu Reka helps Brazilian high-school (ensino médio) students understand themselves well enough to choose a university career. **The core is vocational orientation and self-knowledge, not test preparation.**

The student does not just read about careers. With Arandu, she lives a short version of one: real topics and real exercises from the first-semester subjects of the career she picked. Arandu then reads what she did and how she felt, and helps her decide whether this path fits or she wants to try another one.

The student is not alone. **The ecosystem is the student, her family and her school.** Reports let the family and the school follow her trajectory, so they can help her or act when needed. Those reports are the product's output, not an extra.

**Why it should exist**
- Today's free vocational tools in Brazil are run by institutions or course platforms that steer students into their own offer: UNIP, Estácio "Play na Carreira", Descomplica and Quero Bolsa (research 2026-11-12). No neutral product that follows the student over time was found.
- Lei 14.945/2024 requires schools to support the student's *projeto de vida* (Art. 35-B §2) and to guide the choice of formative itinerary (Art. 36 §2-D).
- A wrong choice is costly. Dropout in Brazilian higher education is 24.8% for in-person courses and 41.6% for distance courses (Semesp).

**Track fit.** Hack Brasil 2026, "Acesso à educação" track: "projetos que ajudam pessoas a aprender ou a ensinar". The student learns real first-semester content of a career and learns about herself. The track excludes general-purpose assistants without a learning focus; Arandu's harness keeps every conversation on the student's path (owner's position: the product is not borderline).

## 2. Users

| Actor | What they get | Role in the business |
|---|---|---|
| Student (ensino médio, years 1–3; demo persona **Sofia**) | Self-knowledge, real career information, a lived taste of a career, reports on herself | Primary user. She enters the data everything else depends on, so the demo starts with her |
| Family | The richest report on the student's journey and how to support her | Main follow-up channel (owner: "more important than the school in that aspect") |
| School (coordinator, orientador) | A shorter report per student with alerts to act on, plus a whole-class view | Buyer (B2B), the main sales target |

Client model: schools first. Universities may later provide data through partnerships, but **never paid placement in recommendations**.

## 3. Goals, non-goals, anti-goals

**Goals for the hack**
- One demo run tells the whole ecosystem story: Sofia explores and discovers, and the family and the school follow and support her.
- Real university data with cited sources (curricula, admission routes, cut-offs). Student data is synthetic (rule 6.9).

**Non-goals for the hack**
- Enem preparation, diagnostics or score-gap plans. Cut-offs appear as information about a career, not as a target to train for.
- Covering every institution in São Paulo, or other states.
- Real school onboarding, payments, native apps, WhatsApp (ruled out on cost).

**Anti-goals: the product fails if...**
- recommendations are influenced by who pays;
- the student feels watched, stops being honest, and her profile becomes wrong;
- anyone other than the student sees her conversation with Arandu;
- it shows prose or logos copied from institution sites;
- Arandu decides for the student. The decision is always hers.

## 4. The student journey

Platform: responsive web in the mobile browser, no install.

**Arandu** is a live, interactive 3D black cat, curious by nature. He carries the voice and the interface (owner's decision; brand board v2: https://claude.ai/artifact/JkD2yi29ci8w9kDAVkPese). Interface language: Brazilian Portuguese.

### 4.1 Onboarding (owner's order)
1. **Welcome.** Arandu introduces himself.
2. **Profile questionnaire**, Duolingo style: short, one question at a time, with tappable answers. It covers the school subjects she likes and finds hard, interests, and what she enjoys doing. School grades, if entered, are context only. Measured behaviour (exercises, enjoyment) carries more weight, because self-reported answers may not be honest.
3. **"Vamos percorrer o caminho".** Arandu invites her on the journey and asks whether she already had a career in mind.
4. **Options with real data.** Arandu shows her idea, if she had one, plus related careers that fit her profile. Each comes with the reason it fits, where it is offered in SP, how one gets in (SISU, ProUni, Fuvest) and the cut-off with its edition and source. **[consultant's call]** Entry routes are shown as information; quota groups and ProUni eligibility carry a label.
5. **She picks one path.**
6. **She picks one of 3 intensity levels** before starting. The names and daily load of each level are open (§11).

### 4.2 The path
- A path is **1–2 real first-semester subjects** of the chosen career, taken from a real curriculum. If she finishes fast, Arandu offers **one more subject**.
- Each subject has **several stops on the map, one per topic.** Example: Cálculo I → functions, limits, derivatives, a real application.
- Some medical schools organise the first year by modules or clinical cases rather than subjects. In that case the stops are the modules.

### 4.3 The daily loop
Each day, Arandu:
1. tells her something new about the career and what working in it is like;
2. gives her a real exercise from the current stop;
3. answers whatever she wants to ask, freely, within the career and her path.

Progress shows as a **daily streak** and a **path map that fills in**. The mechanics are like Duolingo's, but the look is Arandu's own: the ball, paw prints, the cat.

**The exercise format depends on the career:**

| Career | What an exercise looks like |
|---|---|
| Engenharia / Ciência da Computação | Solve: a logic or programming problem, a calculus question |
| Medicina / Enfermagem | Identify structures (anatomy), reason through a simple clinical case |
| Direito | Argue: an open answer to a case, evaluated by AI against stated criteria |

### 4.4 The ball checkpoint ("bolinha")
The ball is the cat's toy. At set points in the path, Arandu "stops the ball" and sits down with her.
- He gives an **evidence-based read** of what she did: performance, how much she enjoyed it, how curious she was. It ends with a few questions about how she feels.
- **She decides:** continue, try another career, or go back to one she tried before. When she wants to try another, the affinity map can suggest related careers.
- **[consultant's call]** A checkpoint comes at the end of each subject and at the end of the path.

### 4.5 "Quem sou eu": the living profile
A profile that Arandu fills in over time: interests, strengths, what she enjoyed and what she did not, which careers she tried and how each went. She can see it at any moment, and it is the base of every report.

## 5. Reports and visibility

| Report | For | Content | When |
|---|---|---|---|
| Path report | Sofia | The checkpoint read for that path | At each ball checkpoint |
| Final report | Sofia | The whole journey: who she is, what she tried, where the evidence points | When she completes the experience |
| Family report | Family | What she is exploring, how she is doing, how they can support her (for example, "ask her what she thought of Anatomia") | **[consultant's call]** Weekly, plus at each checkpoint |
| School report | School | A shorter version per student: trajectory and alerts to act on | **[consultant's call]** Alerts in real time; summary weekly |
| Class view | School | The whole class aggregated: interest areas, careers being explored, progress | Always available |

**Visibility rules (owner's decisions)**
- **Arandu stores the full conversation**, under privacy terms the user accepts when starting to use the app (or under the usage contract). In the MVP this is an acceptance step in onboarding; the owner already runs this pattern in his portfolio and can reuse it. After the hack, the consent flow for minors must be checked against LGPD Art. 14 with a professional.
- **No one but Sofia sees her conversation with Arandu.** Family and school only see reports.
- **Transparency for everyone (owner's decision).** Reports use only what Sofia did (exercises, progress, her checkpoint answers) and what she herself sees in "Quem sou eu". Nothing Arandu infers from the conversation reaches the family or the school unless it is first visible to her in her profile.
- **Sofia does not control what is shared or how reports are generated (owner's decision).** For her, Arandu is only the experience. The rules are fixed by the product and are the same for every student. She can always see what the family and the school receive.
- **[consultant's call]** Alert examples for the school: she stopped coming in, she is torn between two careers, she finished a path.
- **[consultant's call]** In the class view, no group smaller than 5 students is shown.

**Delivery (owner's decision).** Real-time in-app notifications in each interface, using WebSocket. Email is also in scope. Demo moment: Sofia finishes a checkpoint, and the notice appears live on the family and school screens.

## 6. Content

Arandu cannot hold every subject of every career in advance. The owner's architecture:
- **embeddings** over defined, stored content;
- **HTTP** for hard data (curricula, cut-offs, entry routes);
- **AI harnesses** that keep Arandu on topic and enforce the guardrails.

Content is generated by AI with web search, written in its own words, cited, and never copied.

**Three tiers**
1. **Curated and reviewed:** the demo path and the most-chosen careers first. INEP 2024 top careers in SP by students: Direito, Psicologia, Medicina, Sistemas de Informação, Administração.
2. **Generated on first request, then cached,** and labelled "gerado". This covers a full playable path for any career outside tier 1: the topic stops, the content and the exercises of its first-semester subjects.
3. **Live search** for the student's free questions.

**Store content per subject, not per career.** Subjects repeat across careers (Cálculo I appears in many engineering courses), so a subject is generated once and reused.

## 7. Data and constraints

**Demo institutions.** USP (Fuvest and ENEM-USP), Unifesp, UFSCar and UFABC (SISU), and Mackenzie, São Judas, Anhembi Morumbi and FIAP (ProUni). Curriculum feasibility per institution: `arandu-reka/docs/04-sp-data-mapping-summary.md`.

**Recommendation scope (owner's decision, first draft).** Arandu recommends among **all courses** at the 8 demo institutions, so the scraper covers every course there: curriculum, entry route and cut-off.

**Cut-offs**
- SISU public data cover editions 1-2020 to 1-2024. ProUni covers 1-2023 to 2-2026.
- Every cut-off shows its edition and source link.
- A ProUni cut-off is the score for a scholarship, not the institution's general admission bar, and is labelled that way. **[consultant's call]**
- Fuvest scores stay on their own scale and are never compared with Enem.

**Scraping and reuse**
- Respect robots.txt and terms of use. No captcha bypass, no logins, no proxy rotation, no personal data.
- Extract facts only, never prose. Cite every source. Show no institution logos.
- USP's portal forbids reproducing institutional content without written authorization, so take facts only.
- Background: Lei 9.610/1998 Art. 8 V and Art. 7 §2; Decreto 8.777/2016.

**Minors' data (after the hack)**
- LGPD Art. 14 applies.
- ECA Digital (Lei 15.211/2025) bans profiling minors for advertising.
- In practice: no ads, no data sale, and explainable recommendations.

## 8. Hack rules and the MVP's legal minimum

Source: https://hackbrasil.com/regulamento, updated 2026-11-09. Research summary; literal quotes still to be checked.

- **Deadline:** 2026-11-30 23:59 Brasília. **Deliver:** a public repo, a live demo link and a video of at most 3 minutes. The final is in São Paulo on 2026-12-12.
- **Criteria:** four, weighted equally, 0–10 each: technical execution, technical implementation (architecture and code quality), impact, communication. Ties break on execution, then impact.
- **Selection:** the online score only picks finalists (top 5 per track with at least 20/40). The final re-scores from zero.
- **Repo:** frozen from 30/11 until the final, and public until 15/12.
- **AI, libraries and APIs** are allowed, respecting their licences.

**Legal for the MVP**
- **Required for the hack:** synthetic personal data only (6.9), respect for licences and terms (6.5, 11), and a repo licence judges can run.
- **After the hack:** LGPD consent flows, school contracts, legal review, INPI trademark.
- **Recommended:** a short "privacy by design" section in the README and the pitch, built on the visibility rules in §5.

## 9. MVP scope

**In**
- Onboarding (§4.1), with real career data and entry routes.
- Arandu in 3D.
- Paths with stops, the daily loop, career-specific exercises, the streak and the map, the 3 intensity levels.
- The ball checkpoint.
- The living profile.
- All reports in §5, the visibility rules, a view where Sofia sees what each audience receives, real-time notifications, and email.
- Curated content for the demo path; tier-2 generation for any other career.
- Seeded demo accounts for student, family and school.

**Out**
- Real accounts and parental consent, school onboarding, payments.
- Enem preparation and diagnostics.
- Push notifications outside the app.

**Build.** Solo build by the owner, with AI agents.

**Cut order, only if the build runs short [consultant's call].** Sofia's video path (§10) comes first. Cut from the top, keeping the story intact:
1. Email (the in-app notifications stay).
2. Tier-2 generation for careers outside the demo (they show "em breve").
3. The extra subject offered after a fast finish.
4. The final report (path reports and the living profile stay).

## 10. Demo story (Sofia)

**[consultant's call]** The 3-minute video:

1. Sofia meets Arandu and answers the questionnaire.
2. Arandu shows her options with real data, and she picks a path.
3. A daily session: something new about the career, a real exercise, a free question.
4. The ball checkpoint: Arandu's read, and her decision.
5. "Quem sou eu" fills in.
6. The family's screen gets the notice and the report: what she did and what her profile shows, never the conversation.
7. The school sees her alert and the class view.

The career for Sofia's path is open (§11).

## 11. Open decisions

**For the owner**
1. Sofia's demo career. It needs a term-ordered curriculum and entry data in the dataset. By the mapping in `04`, Unifesp, USP, Mackenzie and FIAP have the easiest curricula to extract.
2. The 3 intensity levels: their names and daily load.
3. Where ball checkpoints fall (proposal in §4.4).
4. The family and school report cadence (proposal in §5).
5. Brand items owed to the designer: the redrawn cat, and the font (Outfit, or Poppins (recommended), or Plus Jakarta Sans).

**To check**
- Whether reusing ENEM or INEP questions is allowed. It matters less now that exercises come from career subjects; ask oi@hackbrasil.com if any are used.

## 12. Left to the builder

- Stack, hosting, LLM provider, embedding store, 3D engine.
- Producing the rigged, animated 3D model of Arandu. The designer's "redrawn cat" (§11) is the 2D brand drawing that the model follows.
- Scraper design within §7.
- Screen layouts, after this document and the brand work.
- How the checkpoint read weighs performance, enjoyment and curiosity, as long as it is explainable to the student.
