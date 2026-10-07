# An Outline for SASE's First Blog Post

> **Research question:** Help Bryan decide on an outline for the first sase blog post. Review the related Obsidian
> notes and tasks first, then do independent research, and end with a recommended outline (structure and suggested
> sub-sections only, no drafted content).

Researcher: `cld` (one of five independent researchers). Verified against the `~/bob` vault, this repo, and the
`sase--research` sidecar on **2026-10-07**.

---

## Bottom Line

1. **The outline is already in your notes. What has gone stale is the axis it is organized on.** The July `^outline`
   in `sase_blog_0.md` (Introduction → Overview → XPrompts → ACE → AXE → Future Blog Posts) gives each section a
   product name. Since that outline was decided on 2026-07-07, almost every one of those names has changed:
   xprompt → **macro** (2026-10-03), `ace` → **`sase tui`** (2026-09-15), AXE → **scheduler**, chops → **jobs**,
   lumberjacks → **routines**, agent family → **agent session**, ChangeSpec → **Patch**. More renames are queued
   (`s/shell/turn/`, pipe → loop, Main deck → IO), and **the product name itself is on a two-week rename clock**
   (`202610/sase_rename_new_name_shortlist`). The live July post already needed a "xprompts have been renamed"
   banner. An outline indexed by product nouns goes stale faster than you can write it.

2. **Organize the post around your 2026-08-07 list, "Things that sase generalizes," instead.** It is the strongest
   framing you have written, and no published draft uses it. It turns a feature tour into an argument: *this narrow
   thing (plan mode, a tmux window, one CLI, one prompt) is a special case of something more general, and here is
   what that buys you.* Each section then has the 😈 → 😇 shape you asked for. Those headings also survive renames,
   because they name ideas rather than products.

3. **Recommended spine (6 H2 sections, about 2,800 words):** the pride hook plus a stats strip → *How I got here*
   (12-month timeline plus your personal ladder) → *What SASE is and isn't* → *What SASE generalizes* (four
   sub-sections) → *The slop I shipped* → *Limitations* → *What's next, and I need your help*. Full outline in
   [§8](#8-recommended-outline).

4. **The post can include a payoff that was not possible in June.** In your requirements you wrote: *"Plan mode is
   the canonical or best example of some deeper primitive. I know it. Interrupts?"* Since then you shipped that
   primitive: **gates** (plan, question, launch, and custom gates, with "a gate never blocks an agent" as a decision
   record). Raise the question in the introduction and answer it in §3.2. That is a narrative thread a tour cannot
   carry.

5. **Each section should have a slot only you can fill.** The July diagnosis still holds. Agent-produced text
   finishes; text you must own stalls. The four things agents dropped were admissions, jokes, opinions, and scars
   (`202607/first_post_authorship_gap`). Norms have also hardened. HN's guidelines ban generated or AI-edited
   comments, and in July 2026 dang said the community "mostly doesn't want to read" AI-generated articles. So every
   section below centers on a human-only slot: the value / untapped opportunity / lesson-learned grid, the slop
   confession, or the limitations list. Agents verify facts and render assets; they do not fill slots.

6. **Salvage the July post; do not start a fourth replace cycle.** Its opening (the `tmux_ai_window` scene and the 😈
   list) is the best prose in the corpus. Lift it into §1 of the new post. Move the rest, which is a docs tour (CLI
   providers, macro syntax, keymaps, install), to a docs page with a redirect.

7. **Four gates before drafting:** (a) settle the rename, since it decides the H1, the naming-joke slot, and every
   noun in the post; (b) freeze terminology for the post; (c) review the four screenshots your notes point to.
   Earlier research reported them lost, but they are back in `~/tmp/screenshots/` (verified 2026-10-07). They
   predate the renames, so check them against the current UI. (d) do your own task *"Update default model alias config … right before the blog post"*
   (`sase.md`, scheduled 2026-10-10).

---

## 1. Where Things Stand (verified 2026-10-07)

| Item | State |
| --- | --- |
| Vault project | `sase_blog_0` is **wip**, with the `^prj` task "Post first blog post to https://sase.sh!" still open. Last edited 2026-10-06. |
| Open or blocked tasks | `^zk` (launch an agent to create `~/bob/zk/` notes, plus a `.base` and the key architecture principles as zettels): open. *Gather references* (REF `harness_for_rsi`, now marked dropped): blocked, next 2026-10-08. *Read zettelkasten research*: blocked, next 2026-10-09. *Describe demo video and infographic for each main section*: blocked, next 2026-10-09. |
| Recently cancelled | *Flesh out high value / untapped opportunity / lesson learned per section*, cancelled 2026-10-06 as "the same as the ^zk task". The grid survives inside `^zk`. |
| `why_sase.md` | Described as "the contents of the first sase.sh blog post". Contains the identity/pride paragraph, a stats + *"Motion isn't progress"* bullet, and a 12-month timeline stub ("It started with Claude Code… claude, codex"). |
| `~/bob/zk/` | **Does not exist yet.** |
| Live post | `docs/blog/posts/structured-agentic-software-engineering.md`: **2,882 words**, HTTP 200 on sase.sh. Agent-maintained through the renames, with a "xprompts renamed to macros" banner. Sections: untitled intro, *SASE Wraps Agent CLIs, Not Models*, *Macros*, *The Agents Tab In sase's TUI*, *Install, Configure, Initialize*, *What's Next*. |
| Other drafts | 10 `draft: true` posts (`[00]`–`[09]`), already excluded from the built site. |
| Diagram briefs | `window_farm_vs_control_tower`, `one_prompt_provider_clis`, `prompt_burrito` (`.prompt.md`). None rendered yet. |
| Existing media | Multi-model fan-out GIF, agents observability GIF and still, prompt input GIF, history/stash GIF, Patches pipeline still. |
| Repo ledger | **15,753 commits** since 2026-02-14, 6,365 with `SASE_AGENT=` trailers, and 1,642–3,428 commits every month from March to September. Re-derive every number at publish time. |

## 2. What Your Notes Already Decided, and What Changed Since

**Decided (July):** the `^outline` skeleton, the 😈/😇 bullets, `tmux_ai_window` in the intro, TUI media, a literal
title (your 2026-06-18 comment accepted *"SASE: Structured Agentic Software Engineering"*), and a "Future Blog Posts"
closer.

**Added after the outline was closed (Aug–Oct), in your own words:**

- *Start the post with a brief timeline of software engineering transformation*, summarized as a funny timeline
  infographic (2026-08-01, now under Introduction in `^outline`).
- `why_sase.md`'s identity opener: *"My attempt to take back some control from this thing that seemed like it was
  coming for a core part of my identity."*
- *Things that sase generalizes* (2026-08-07): Gates → Plans → Epics; Beads → Sidecar repos; Agent CLIs (skills,
  memory, provider interface, *not* hooks); VCS and workspace operations; agent presentation and organization;
  Macros / agent control flow (forks/waits/queues); agent project management; conditional agent automations
  (jobs).
- *Include a "Why a TUI?" section* (2026-08-10).
- *"I need your help. I'm out of tokens."*, `type:poll` GitHub issues at the end, angel/devil stick figures, and the
  Vim-mode joke (2026-08-07).
- *Explain how you use the different types of tokens* (08-03). *"Sub-agent" doesn't cut it* (08-01). *Skills as
  procedural memory* (08-12). *Loop engineering and graph engineering* (08-11). *`reads` and `snips` as future
  sidecars* (08-13).
- *Create key architecture principles as zk zettels* (09-07). *Add AI broccoli section* (09-10; the body lives in a
  Google Keep note I could not read).

**What this means:** after July, your own additions moved the post from a tour toward an argument (why → what it
generalizes → honesty). The July skeleton still works as an *order* (intro → overview → core ideas → future), but
not as an *index of nouns*.

## 3. What Changed Outside

- **The "timeline" idea has a famous precedent you should differentiate from.** Steve Yegge's *Welcome to Gas Town*
  (January 2026; in your library, queued) built its launch around an 8-stage ladder, from no AI up to "building your
  own orchestrator". Readers will have seen it. An industry-wide timeline is commodity material. **Your personal
  ladder** (Boris method → `tmux_ai_window` → auto-approved plans → `%wait`/`#fork` → …) is not. Keep the industry
  timeline to one infographic and let the prose be yours.
- **Personal adoption-journey posts land with this audience.** Mitchell Hashimoto's *My AI Adoption Journey*
  (2026-02-05) is a step-by-step personal ladder ("Drop the chatbot" → … → "Engineer the harness" → "Always have an
  agent running"). It shows that the shape of your §1 works.
- **The critique to inoculate against is already written.** Maggie Appleton's Gas Town essay (2026-01-23) called it
  entirely vibecoded, hastily designed, and expensive. Whatever SASE says about itself, readers will apply that frame.
  Your "slop I shipped" and "limitations" sections pre-empt it. That is why they are full H2s in the outline, not
  footnotes.
- **The category has filled in.** OpenAI's Symphony spec (2026-04-27; you finished it) makes an issue board the
  control plane for Codex agents. The Codex app, Claude Code agent view and agent teams, and Gas Town cover parallel
  agents, worktrees, and background runs. Do not build sections on those. Build them on what SASE generalizes:
  provider neutrality, a prompt language with control flow, gates as a primitive, and durable records in git.
- **HN norms:** the guidelines ban generated or AI-edited comments. In July 2026 dang said there is no article rule
  yet, but the community mostly does not want AI-written articles. HN also discourages promotional titles and
  gratuitous numbers, which is another reason to keep `[00]` out of the title.

## 4. Options Considered

| Option | Verdict |
| --- | --- |
| **A. Keep the July `^outline` as written** (XPrompts → ACE → AXE tour) | ❌ Every heading is now a renamed noun. It reads as docs, and it is the structure that dropped all your opinion-type requirements. |
| **B. Pure origin essay** (pride → ladder → feelings) | ⚠️ Strongest voice, but no proof artifacts. HN readers want technical depth. |
| **C. "Ledger" post** (stats-led: commits, runs, cost) | ⚠️ A great **second** post (prior research agreed). As post 0 it hands the "motion isn't progress" critique to commenters. |
| **D. Architecture-principles essay** (single-turn agents, host-owned completion, gates never block…) | ⚠️ Very shareable, but too internal for a front door. Use principles as the "lesson learned" slot of each §3 sub-section, then give them their own post. |
| **E. Hybrid: personal ladder → what SASE generalizes → honesty → help** | ✅ **Recommended.** Keeps July's order, uses your Aug–Oct additions, has a proof slot in every section, and survives renames. |

## 5. Criteria the Outline Was Built Against

1. **At most 6 H2 sections and about 2,500–3,000 words.** The `[00]` draft failed review at 20 sections and 5,400
   words.
2. **Rename-proof headings.** Headings name ideas; product nouns appear only in body text.
3. **Every section has a human-only slot** (grid answer, confession, limitation, or joke that really happened) **and
   a proof slot** (GIF, screenshot, diagram, or snippet).
4. **No install section inline.** Link to Getting Started (Diátaxis: explanation ≠ tutorial).
5. **Defer, don't cram.** Anything that needs its own vocabulary (beads, Patches, scheduler, memory webs, sidecars)
   goes in the series map.
6. **The outline doubles as the structure note for `^zk`.** Each sub-section maps to 1–3 claim-titled zettels.

## 6. Requirement Triage (every blog requirement in the vault)

| Requirement (source) | Destination |
| --- | --- |
| Identity/pride paragraph; stats + "Motion isn't progress" (`why_sase`) | Opening |
| Timeline of SWE transformation + funny infographic; "crazy 12 months", "it started with Claude Code" (`sase_blog_0`, `why_sase`) | §1.1 |
| AI Daily Brief reference (`sase_blog_0`) | §1.1 source |
| Boris method → `tmux_ai_window` → auto-approve plans → wait/fork ladder (`^outline`) | §1.2 |
| Devil/halo emoji bullets; angel/devil stick figures; caveman diagram (`sase_blog_0`, legacy) | §1.3, and the template for §3.x |
| "…but the truth is …"; tinkering vs trying quote (legacy, `sase_blog_0` Contents) | §1.4 |
| Name origin (SASE paper); naming jokes for sase and xprompts→macros; "I'm bad at naming things…" (legacy, `sase_blog`) | §2.1 (written after the rename gate) |
| "Optimal experience, not optimal performance" (`sase_blog_0`) | §2.1 |
| Gas Town: beads (way less use), rigs, no mayor; can't interweave LLM calls with deterministic code (`sase_blog`, legacy) | §2.3 |
| Things that sase generalizes (`sase_blog_0`) | §3 frame |
| PIW goals (LSP; "so awesome that any other editor is unthinkable"); alternations → vibe evals; `%wait` and `#fork` 😈/😇 (your one proofread comment); stashed prompts; loop/graph engineering (`sase_blog`, `sase_blog_0`, `ref/docs/sase_blog_260708`) | §3.1 |
| "Plan mode is … some deeper primitive. Interrupts?" (`sase_blog`) | §3.2 setup → payoff |
| "Why a TUI?"; "sub-agent doesn't cut it"; agents tab is the buggiest part; Vim-mode joke (`sase_blog_0`, `sase_blog`) | §3.3 |
| Codex parity / unified agent CLI interface goals; different types of tokens; skills as procedural memory; retry-during-Claude-outage screenshot (legacy, `sase_blog_0`, `sase_blog`) | §3.4 |
| AI slop definition and four categories incl. **prompt debt** (`sase_blog`) | §4 |
| AI broccoli (`sase_blog_0`, Keep note) | §4.3 if it is about healthy-but-unappealing work; otherwise §6 |
| List of limitations (`sase_blog`, asked three times) | §5 |
| Beads/SDD, ChangeSpecs (now Patches), AXE (now scheduler/routines/jobs), memory, mobile/Telegram, evals, architecture, `reads`/`snips` sidecars, `sase artifact read` plans example, zettelkasten hub-note quote | §6.1 series map (later posts; the hub-note quote fits the memory post, since memory-web descriptors are hub notes) |
| "I need your help. I'm out of tokens."; `type:poll` issues (`sase_blog_0`) | §6.2 |
| "No weasels; just work." (legacy) | Closing line |
| Citations; 3 funny AI diagrams; TUI screenshots; demo video + infographic per section (`sase_blog_0`) | Proof slots in §8 |
| Email the agent_swe paper authors (`sase_blog`) | Launch checklist, not content |
| Install / configure / init (July post) | Docs: Getting Started (link only) |

## 7. Gates Before Drafting

1. **Rename decision.** The H1, the naming-joke slot, the pronunciation line, and the URL depend on it. Both outcomes
   produce a good §2.1 beat, so write that slot last.
2. **Terminology freeze for this post.** Pick one name per concept as of the draft date. Headings are rename-proof by
   design (§5.2), so only body text is exposed.
3. **Review the flagged screenshots against the current UI.** `20260616_140429` (outage retries),
   `20260616_115015` (`%wait`), `20260619_214831` (alternations), and `20260624_074728` (questions/retries/tales)
   are **present** in `~/tmp/screenshots/` as of 2026-10-07. The July and August research reported them missing,
   which is now out of date. All four predate the xprompt → macro, ACE → `sase tui`, and family → session renames,
   so re-capture any that show old labels. The `img/20260802_*` stash screenshots and `img/20260824_141701.png` are
   in the vault.
4. **Your model-alias config task** (scheduled 2026-10-10), so the screenshots show the config you actually use.

---

## Sources

**Vault (reviewed first):** `sase_blog.md` · `sase_blog_0.md` (`^outline`, Requirements, Contents) ·
`sase_blog_0_legacy_notes.md` · `why_sase.md` · `sase_blog_blockers.md` · `sase.md` (rename ideas, model-alias task,
terminology renames) · `ref/docs/sase_blog_260708` (proofread highlights) · `ref/chat/*` highlight notes for
`sase_hacker_news_popularity_strategy_consolidated` (your comments on the "recommended spine", "known limitations",
"lead with the reader's problem") · `ref/chat/blog00_launch_post_review_consolidated` (title comment) · `bob ref`
library state.

**Prior research (read via `sase artifact read`):** `202606/sase_blog_series_structure_consolidated.md` ·
`202606/blog00_launch_post_review_consolidated.md` · `202606/sase_blog_launch_strategy_consolidated.md` ·
`202607/blog_launch_xprompts_agents_tui_consolidated.md` ·
`202607/first_post_authorship_gap/first_post_authorship_gap.md` ·
`202608/directed_zettelkasten_first_post/directed_zettelkasten_first_post.md` ·
`202610/sase_rename_new_name_shortlist/sase_rename_new_name_shortlist.md`.

**Repo:** `docs/blog/posts/*` · `docs/images/blog/*` · `git log` (commit ledger, docs rename history) · SASE glossary
(macro, gate, scheduler, job, routine, Patch, agent session/clan/hood/tribe, goal, monitor).

**External:**
- [Steve Yegge — Welcome to Gas Town](https://steve-yegge.medium.com/welcome-to-gas-town-4f25ee16dd04) (8-stage
  ladder summarized via [dsebastien: AI Coding Maturity](https://concepts.dsebastien.net/concept/ai-coding-maturity/))
- [Maggie Appleton — Gas Town's Agent Patterns, Design Bottlenecks, and Vibecoding at Scale](https://maggieappleton.com/gastown)
  and [Allen Pike's link post](https://allenpike.com/2026/maggie-coding-agents)
- [Mitchell Hashimoto — writing index (My AI Adoption Journey, 2026-02-05)](https://mitchellh.com/writing)
- [Help Net Security — OpenAI releases Symphony](https://www.helpnetsecurity.com/2026/04/28/openai-symphony-codex-orchestration-linear/)
- [Hacker News Guidelines](https://news.ycombinator.com/newsguidelines.html) and
  [AI Weekly — HN debates flag for AI-generated articles](https://aiweekly.co/alerts/hacker-news-debates-user-facing-flag-for-ai-generated-articles)
- [newslepear #56 — How to launch on Hacker News](https://newslepear.beehiiv.com/p/56-how-to-launch-on-hacker-news-brand-vs-product-messaging-on-the-homepage-and-an-awesome-1-2-3-how)
- Optional framing references already queued in your library (contents not verified here): Geoffrey Litt,
  *Understanding is the new bottleneck*; Ethan Mollick, *The Dot and the Swarm*; Hassan et al., *Agentic Software
  Engineering* (arXiv:2509.06216).

Library check: 6 of 9 candidates already in your library (2 finished).

---

## 8. Recommended Outline

Target about **2,800 words** across **6 H2 sections** (hard cap 3,000). Headings are working titles chosen to survive
renames. Each line describes a *slot*: what belongs there and where its material lives. No content is drafted.
"Grid" means your three questions: **high value / high untapped opportunity / lesson learned**.

**H1: `<Name>: Structured Agentic Software Engineering`.** A literal title, matching the pattern you accepted on
2026-06-18. No `[00]`. Finalize after the rename gate. A one-line dek carries the positioning.

### Opening (no heading, ~200 words)

- **Pride hook.** The identity paragraph already in `why_sase.md`.
- **Stats strip + "Motion isn't progress."** 3–4 re-derived numbers with their caveats printed alongside, undercut
  by the quote.
- **Plain-language promise + escape hatch.** One sentence on what the post covers, and one link to Getting Started
  for readers who only want to try it.
- *Proof slot:* none (keep the first screen text-only and fast).

### 1. How I Got Here (~450 words)

- **1.1 The last twelve months.** The industry timeline, kept to one infographic plus ≤100 words. *Proof slot:*
  funny stick-figure timeline infographic (angel/devil theme).
- **1.2 My ladder.** Your rungs from `^outline`: Boris method → `tmux_ai_window` → auto-approved plans → `%wait` /
  `#fork` → … Each rung is a step up, and each says what broke. Salvage the July post's opening here.
- **1.3 The window farm, itemized.** The 😈 list (salvaged from July, extended as needed). *Proof slot:*
  `window_farm_vs_control_tower` diagram (brief exists).
- **1.4 "…but the truth is …"** The honest motivation beat (legacy sentence + the tinkering-vs-trying quote). Also
  plant the question here: *plan mode is a special case of something; what?*

### 2. What SASE Is, and Isn't (~350 words)

- **2.1 One sentence, one pronunciation, one joke.** Definition, name origin (the SASE paper), and the naming jokes
  ("I'm bad at naming things…", xprompts → macros). Include "optimal experience, not optimal performance". Written
  after the rename gate.
- **2.2 Who it's for, and who can wait.** The reader already running several agent CLIs in real repos; optionally
  place them on Yegge's ladder in one line.
- **2.3 Neighbors.** A compact comparison (Gas Town: beads, rigs, no mayor, deterministic interleaving; Codex app /
  Symphony; Claude Code agent view). Phrase claims narrowly, as what their public docs emphasize. *Proof slot:*
  `one_prompt_provider_clis` diagram (brief exists), or a small table.

### 3. What SASE Generalizes (~1,100 words; four sub-sections of about 275)

- **3.0 The list.** Your eight "things sase generalizes" as a one-line-each table or visual, then: *four here; the
  rest get their own posts.*
- **Sub-section template (use for each of 3.1–3.4):** 😈 the special case → 😇 the generalization → proof artifact →
  grid (value / untapped opportunity / lesson learned). The "lesson learned" slot is where your architecture
  principles go.
- **3.1 Prompts Become Programs.** Macros as a prompt language: directives, alternations → *vibe evals*,
  multi-prompt segments, `%wait` and `#fork` (with the 😈/😇 bullets from your proofread comment), stashes, and the
  PIW/LSP "goal number one / goal number two" quote. Lesson slot: loop and graph engineering. *Proof slots:*
  multi-model fan-out GIF (exists), alternation and `%wait` screenshots (`20260619_214831`, `20260616_115015`), `prompt_burrito` diagram (brief
  exists), stash screenshots (`img/20260802_*`).
- **3.2 Plan Mode Was a Gate All Along.** Answer the planted question: Gates → Plans → Epics; questions and launch
  approvals as the same primitive. Lesson slot: gates never block an agent, or single-turn agents. *Proof slot:* plan
  approval or question gate GIF (to record), questions/retries/tales screenshot (`20260624_074728`).
- **3.3 From Windows to a Cockpit: Why a TUI.** The "Why a TUI?" argument; agent organization vocabulary (sessions,
  clans, hoods, tribes) and why "sub-agent" doesn't cut it; the Vim-mode joke; and a forward pointer to "the buggiest
  part" in §5. *Proof slots:* agents observability GIF and still (exist).
- **3.4 One Interface Over Every Agent CLI.** Codex parity and unified-CLI goals; skills, memory, and instructions
  written once (and why hooks are *not* generalized); the different types of tokens; retries through a provider
  outage. Lesson slot: skills as procedural memory. *Proof slot:* outage-retry screenshot (`20260616_140429`).

### 4. The Slop I Shipped (~300 words)

- **4.1 What I mean by AI slop.** Your definition.
- **4.2 Four categories, one real example each.** Unnecessary backward compatibility · features never or no longer
  used · duplicated logic · **prompt debt**.
- **4.3 What I do about it.** Where the "AI broccoli" note likely fits; tie back to "motion isn't progress" and the
  stats caveats. *Optional proof slot:* one small chart (e.g., commits by month or test-to-source ratio).

### 5. Limitations (~200 words)

- **One bulleted list, no sub-sections.** Product limits only: the Agents tab is the buggiest part of the TUI; alpha
  and POSIX-only; inherits provider pricing, policy, and CLI changes; vocabulary still moving (renames); attention
  and token cost at your run volume. *Proof slot:* none (plain text builds trust).

### 6. What's Next, and I Need Your Help (~250 words)

- **6.1 The series map.** One line per future post: Beads & SDD · Patches and review · the scheduler and jobs ·
  memory and sidecars (`reads`, `snips`) · mobile/Telegram · evals · architecture principles · the ledger post
  ("what N agent runs a day actually cost").
- **6.2 "I need your help. I'm out of tokens."** The ask, plus links to the `type:poll` GitHub issues.
- **6.3 Try it.** One link to Getting Started (no inline install).
- **Closing line:** *"No weasels; just work."*
