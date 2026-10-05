# How Big Is a Project's Preloaded Memory Once `AGENTS.md` Is Gone?

**Date:** 2026-10-05 · **sase checkout:** `235e9ba0c9` · **Builds on:**

- `research:202610/sase_md_instruction_delivery/sase_md_instruction_delivery.md`
  (**R-delivery**)
- `research:202610/instruction_bundles_provider_parity_and_memory_ledger.md`
  (**R-ledger**)
- `research:202610/fresh_clone_bootstrap_and_native_subagent_instructions/fresh_clone_bootstrap_and_native_subagent_instructions.md`
  (**R-fresh**)
- the five epic-split reports in `202610/` (`instruction_delivery_epic_split__grk.md`,
  `memory_built_instructions_epic_split__cld.md`,
  `dynamic_memory_built_instructions_epic_split__mus.md`,
  `dynamic_instruction_migration_epic_boundaries__cdx.md`,
  `agent_instruction_migration_epic_decomposition__gem.md`)
- `research:202610/agent_instructions_budgeted_router/agent_instructions_budgeted_router.md`
  (**R-router**)

> **Question:** Under the instruction-delivery plan, how will I easily tell how large
> (for example, how many lines) each SASE project's preloaded memory is? Today it is an
> `AGENTS.md` file I can open in vim. Does the earlier research address this?

## Bottom line

**Only partly, and mostly by accident.** The research thoroughly answers "what did
*this agent* get?". It does not answer "how big is *this project's* preloaded memory?",
which is your question. No report makes it a requirement, and no proposed command takes
a project as its key. The tools you use today stop giving the right answer in the
untrack phase. Their replacements arrive only in Phase 3 or in the optional ledger/TUI
epic.

Four findings:

1. **Every tool you use today either loses its meaning or starts under-reporting.**
   - `vim AGENTS.md` opens a stub of at most 80 lines.
   - `sase memory list` reads `AGENTS.md` from disk, so it reports the stub's size. No
     report proposes changing it.
   - `git log -p AGENTS.md` and Memory History's INSTRUCTIONS rail show the stub's
     history.
   - The gitignored file you *can* open, `.sase/instructions/claude.md`, holds the
     **interactive** render. By design it omits the runtime contract that every SASE
     agent receives.
2. **What the research does propose is keyed by agent, not by project.** It proposes
   `sase instructions render --as <agent|facts>`, `sase instructions show <agent>
   --bundle`, per-run receipts with `bytes` and `tokens`, and a TUI MEMORY deck that
   prints `4.6k tok / 18.7 KB · budget ✓`. These are good tools, but each needs an
   agent or a hand-typed set of facts.
3. **"The size" stops being one number.** A bundle stacks package, plugin, home,
   project, and launch layers. Phase 3 `when:` filters then make it vary by provider,
   role, tribe, and other facts. R8 sets budgets "per audience in a matrix", but no
   report chooses which audience gives *the* number a human sees.
4. **The size gate comes last.** R-router's ratchet (≤100 lines, ≤1,600 tokens) is not
   implemented: `src/` has no `instructions_budget`, and there is no `sase instructions`
   CLI yet. The matrix check is scheduled for Phase 3 (Epics 4–6 in the split
   proposals). Meanwhile the SASE-owned contract moves out of project memory into a
   packaged base, so a sase upgrade can grow every project's preloaded memory without a
   commit in any project.

**Recommendation:** add one requirement, **R15 (size visibility parity)**, and make it
an exit criterion of the *renderer* epic, before any instruction file is untracked. It
has two parts:

- **Point `sase memory list` at the renderer.** It already prints "Loaded lines" and
  "Approx loaded tokens", which is exactly your question. Today those rows read files
  on disk.
- **Give `sase instructions render` a default audience,** so that
  `sase instructions render | nvim -` replaces `vim AGENTS.md`.

[§5](#5-recommendation) has the details.

## 1. Today's "size" is one number, and it was already approximate

| Tool | What it shows for `sase` on 2026-10-05 |
| --- | --- |
| `wc -l AGENTS.md` / `vim AGENTS.md` | 285 lines, 17.4 KB |
| `sase memory list` (measured for this report) | `AGENTS.md` 285 lines ≈4,370 tok; `~/AGENTS.md` 74 lines ≈966 tok; **Loaded lines 359, ≈5,336 tok** |
| `git log -p AGENTS.md`, Memory History `INSTRUCTIONS` rail | Every committed version. This is how R-router saw the file grow back from 227 to 283 lines in one month. |

That number is precise about the file but only approximate about the agent.
R-delivery and R-ledger measured what each provider actually loads:

- **Claude and Codex** get home plus project, so they receive the contract twice.
- **Muse** gets the project layer only.
- **Grok** has loaded **nothing** since about 2026-09-10.

So `vim AGENTS.md` never showed "what an agent saw". It showed "what SASE rendered".
A renderer knows exactly what it sends, so the migration could make the honest answer
*easier* to get than it is today. The research just never connects that to a size view
for humans.

## 2. What happens to each tool after the migration

| Today's tool | After the untrack phase (R-delivery Phase 2 / R-fresh Phase 2) | Addressed by prior research? |
| --- | --- | --- |
| `vim AGENTS.md` in the primary checkout | Opens the committed `mode: export` stub: at most 80 lines, about 1.5k tokens, target about 40 lines (R-fresh R12; mus's epic split says ≤15). It has no runtime contract, no reference triggers, no webs, and no home layer. | The stub's budget is covered. Nothing warns that the stub is **not** the runtime size. |
| `vim .sase/instructions/claude.md` or `AGENTS.override.md` | These exist only after `sase instructions sync` or `just install`, and go stale between syncs. They hold the **interactive** render (R-fresh R14), which drops the final declaration plus the workspace, handoff, plan, monitor, and sidecar rules, and swaps skills for CLI forms. It is smaller than what any SASE run gets. | The files exist, but they serve a different audience. |
| `vim SASE.md` | Shows layout only (slots and `when:` blocks). The file is optional and may not exist; the content stays in notes (R2). | — |
| `sase memory list` "Loaded lines / Approx loaded tokens" | Computed by `instruction_roots()` (`src/sase/memory/inventory_references.py:157`), which reads `AGENTS.md` and the shims from disk. After untracking it measures the stub plus the home files, and **silently under-reports**. | **No.** Only R-router mentions it, and only before the migration ("report each provider's effective total"). The delivery, ledger, fresh-clone, and epic-split reports never update it. |
| `git log -p AGENTS.md`, Memory History INSTRUCTIONS rail | Shows the stub's history. cld's epic split (E4.4) keeps the rail opening "across the stub boundary" and points launch rows at bundle manifests, but the runtime bundle itself has no git history. | Partly: cld flagged the breakage. The size history is lost. |
| A budget check | R-router's `sase memory init --check` ratchet (`memory.instructions_budget`) is **not implemented**. | It moves to `sase instructions check --matrix` in Phase 3. |

## 3. What the prior research does provide

**R-delivery (the `SASE.md` report):**

- `sase instructions render --as <agent|facts>` and `--matrix`, described as a
  "preview" that must not consume model-alias rotation state.
- `sase instructions check` in CI and pre-commit, with R8: the router ratchet
  "applies to each rendered audience in a matrix. The provider-effective total is
  reported separately."
- `instructions.md` and `instructions.json` for each invocation in
  `$SASE_ARTIFACTS_DIR`, plus `SASE_INSTRUCTIONS_FILE`.
- `sase instructions sync` for gitignored projections that humans can use.

**R-ledger (provider parity and the memory ledger)** is the report most aware of size:

- Each receipt carries `bundle.bytes`, `bundle.tokens`, and `bundle.budget`, plus
  `tokens` for each section.
- Bundles go into a content-addressed store, `~/.sase/instruction_bundles/<sha>.md`.
  That is a real file you can open in vim once you know the hash.
- The TUI shows:
  - a header chip, `❖ 4.6k`;
  - a Receipt card, `BUNDLE 7f3a91c · 4.6k tok / 18.7 KB · budget ✓`;
  - a Ledger card with PACKAGE, HOME, and PROJECT groups and token counts for each
    note;
  - a Bundle card with the exact bytes.
- When you edit a core note, the Memory pane footer reads "core · inlined into every
  run (≈1.1k tok each)".
- `sase instructions show <agent> [--json] [--bundle]`.
- Token bars, today vs. after:
  - **Claude and Codex:** 5.3k today, 0.8k of it duplicated;
  - **Muse:** 4.4k;
  - **Grok:** 0;
  - **every provider after:** about 4.6k, plus a 0.1k provider section.

**R-fresh (fresh clones and subagents):**

- `render` to stdout stays available as the "read-only alternative".
- The stub's budget is enforced by `sase instructions export --check`.

**The epic splits:**

- **cld:** E2's exit checks include `sase instructions render --as
  <a-recent-agent-name> | head -40`, and a `diff` between `--as codex` and
  `--as grok` that should show only the provider section.
- **mus, item 10:** "Budgets need a measured baseline before they become gates… E2 must
  record the baseline numbers as artifacts; E6's `--matrix` gate is vacuous without
  them."
- **cdx, item 10:**
  - "Keep the export budget separate from the full runtime budget and report effective
    cost including any native stub."
  - Getting from the measured 4.4k tokens to the proposed 1.6k is content work, not
    deduplication.
- **grk, item 16:** the router ratchet is a "parallel tale" that can be confirmed today
  with `wc -l AGENTS.md` and `sase memory init --check`.
- **gem:** token counts in `instructions.json` in Epic 2, and the TUI and CLI views in
  Epic 4.

## 4. Gap analysis

People ask five kinds of question about preloaded size. Here is how the research covers
each one.

| Question | Covered? | By what | Gap |
| --- | --- | --- | --- |
| **A.** What did agent X actually get, and how big was it? | **Yes, well** | The receipt, `instructions show --bundle`, the MEMORY deck, `SASE_INSTRUCTIONS_FILE` | The receipt JSON lands in Phase 1, but the human views come in Epics 4–6 or are marked optional. |
| **B.** How big is project P's preloaded memory **right now**, before launching anything? | **Partly** | `render --as <facts>`, piped to `wc` | It isn't keyed by project and has no default audience. You must know the fact vocabulary. There is no size summary and no breakdown by layer. No exit criterion covers it. |
| **C.** Which projects are big, comparing `sase`, `bob-cli`, and `actstat`? | **No** | — | Nothing iterates over projects. |
| **D.** Is it growing? | **No (lost)** | The receipt index could hold it | The git history of the full file disappears, and no report proposes a size time series. |
| **E.** Can I open it in vim? | **By accident** | `render > file`, the bundle store, the per-run artifact | None of these is documented for this use. The gitignored file you *can* open belongs to the interactive audience. |

The gap has two structural causes.

1. **Every report reasons outward from the agent.** The questions asked were "what does
   each provider load?", "how do we track what each agent saw?", and "what do fresh
   clones get?". None asked "what does a project's owner see when they ask how big its
   instructions are?". So the views are keyed by agent (receipt, deck) or by a set of
   audience facts (render, matrix).
2. **After Phase 3 the size is a matrix, and no one picked a headline cell.** The layers
   are:
   - package: SASE-owned and shared by all projects;
   - plugins;
   - home: yours, and shared by all projects;
   - project: the only per-project part;
   - launch facts.

   On top of that, `when:` varies the text by provider, role, tribe, `phase_worker`, and
   `commit_method`. R8 budgets the *project layer* per audience, and R-router said to
   report the *effective total* per provider. Neither gives you the single "this project
   preloads N lines" that `wc -l` gives today.

There is a further trap in budgeting only the project layer. Today's shared contract,
`sase/memory/sase.md`, is 83 lines and about 1,097 tokens, and R-router named it one of
the two biggest contributors to file size. R2 retires it into the packaged base. That
takes it out of project memory, so a budget that covers only the project layer stops
seeing it. A sase release could then grow every project's preloaded memory, and no
project-level check would notice.

## 5. Recommendation

### R15: size visibility parity (a new requirement)

> Before any generated instruction file is untracked, a human in a primary checkout can
> run one command, with no flags, and see the size of the bundle a SASE root agent in
> that project would receive. The size is given in lines at the configured width, bytes,
> and approximate tokens, broken down by layer. The human can also open those exact
> bytes in an editor. The numbers come from the same renderer the launch path uses, and
> they match the `bytes` and `tokens` in a real run's receipt.

Make this an exit criterion of the **renderer epic**, not the ledger/TUI epic. The
renderer epic is:

- R-delivery Phase 1;
- cld's E2;
- cdx's Epic 2;
- mus's E2;
- grk's and gem's Epic 2.

That epic already has to ship `render --as` and record a budget baseline (mus, item 10).
R15 adds only a small surface for humans on top of that.

### Concrete steps

1. **Define a headline audience.** It should be the *largest* SASE root render across
   the providers that are enabled. Budgets care about the worst case, and the largest
   render is a stable number. Before Phase 3, renders differ only by the provider
   section of about 0.1k tokens, so the choice barely matters. After Phase 3, show the
   headline number together with the minimum-to-maximum range across the matrix.

2. **Point `sase memory list` at the renderer** instead of the instruction roots on
   disk, starting when the first provider's delivery flag turns on.
   - Its summary panel already says "Loaded lines" and "Approx loaded tokens". Keep
     those rows and their meaning ("what a SASE agent preloads"), and change only where
     the numbers come from.
   - Add one row per layer, plus a budget column.
   - List the export stub and the interactive projection as separate rows, each labeled
     with its audience, so their smaller numbers are never mistaken for the runtime
     size.

   This fixes the silent under-report and needs no new command. A new
   `sase instructions stats` would still leave `memory list` reporting the wrong
   number.

3. **Make the vim path one command.**
   - **Render with no flags.** `sase instructions render` with no `--as` prints the
     headline render to stdout. Each section carries an id comment, like the gutter on
     R-ledger's Bundle card, and a size footer goes to stderr. Then
     `sase instructions render | nvim -`, or `-o FILE`, replaces `vim AGENTS.md`.
   - **Optional preview file.** `sase instructions sync` can also write the headline
     render to a gitignored path that no CLI loads, such as
     `.sase/instructions/preview.md`. Give it a header such as
     `<!-- audience: sase root · N lines · N KB · ≈N tok · digest … -->`. No provider
     discovers this path: Claude imports only `claude.md`, Codex reads only
     `AGENTS*.md`, and Grok skips gitignored files.

   The preview file is the closest drop-in for "open the file in vim" and costs almost
   nothing. Like the other projections, it can go stale between syncs, and its digest
   header shows when it has.

4. **Compare all projects at once.** `sase memory list --all-projects` iterates over
   the enabled projects from `sase project list` and prints one row per project: the
   headline lines and tokens, and the project-layer size against its budget.
   Implementers should read the `cli_rules` memory before adding the flag.

5. **Keep a size history without committing anything.**
   - Each line that R-ledger proposes for `instruction_receipts.jsonl` should carry
     `lines`, `bytes`, and `tokens`. The receipt already has them.
   - `sase instructions check` should print its per-layer table in CI, so every commit
     to master has a recorded size.

   Don't commit a size manifest. It would bring back the churn that R7 removes.

6. **Land the budget ratchet now, on the current generator.** This is grk's "parallel
   tale" (item 16) and R-router's budget-check step. It doesn't depend on the
   migration, `wc -l AGENTS.md` can confirm it today, and it gives the renderer epic the
   measured baseline mus asks for. When bundles land:
   - move the gate to `sase instructions check`;
   - add a separate effective-total line, so growth in the package and home layers is
     visible too (cdx, item 10). This matters because the contract leaves project
     memory.

7. **Add a TUI line later; it is cheap.** In Admin Center → Config → Memory, show one
   header line computed the same way. R-ledger's "Seen by" footer is the per-note
   version of this; the project-level total is what's missing.

Here is what the retargeted `sase memory list` summary could look like. Only the
≈4.6k total and the ≈1.6k budget come from the reports; the layer split and the other
numbers are illustrative.

```
╭──────────────────── SASE Memory Context · sase ─────────────────────╮
│ Preloaded (SASE root, headline)   ≈4.6k tok · ≈18 KB · N lines      │
│   package   contract + provider   ≈1.2k                             │
│   home      ~/sase/memory         ≈0.2k   (triggers only)           │
│   project   sase/memory           ≈3.2k   budget 1.6k  ✗ over       │
│ Audience range (Phase 3+)         min (monitor) … max (root)        │
│ Export stub   AGENTS.md           ≈40 lines   fresh clones only     │
│ Interactive   .sase/instructions  ≈N tok      raw CLIs here only    │
╰─────────────────────────────────────────────────────────────────────╯
```

### Where this fits the existing epic proposals

| Epic proposal | Addition |
| --- | --- |
| Renderer epic (cld E2, cdx Epic 2, mus E2, grk and gem Epic 2) | Exit criterion: R15. `sase memory list` reports the headline render by layer, and a receipt from the same day matches its `bytes`. |
| Untrack phase (cld E4, R-fresh Phase 2) | Precondition: R15 is green. Otherwise `vim AGENTS.md` and `sase memory list` both start under-reporting the day the files are removed. |
| Audiences epic (Phase 3) | `--matrix` also feeds the headline number and the range in `sase memory list`. |
| Ledger/TUI epic | Unchanged. Add the Memory-pane header line from step 7. |

## 6. Summary

**What I found:**

- The earlier research doesn't address your concern directly.
- It covers per-agent inspection very well: receipts with `bytes` and `tokens`,
  `instructions show --bundle`, the MEMORY deck, and a stored copy of every bundle.
- It offers an audience-keyed preview, `sase instructions render --as <facts>`, and
  budget gates per audience.
- It never makes "how big is this project's preloaded memory?" a requirement:
  - no proposed command takes a project as its key;
  - no report picks a headline audience, now that the size becomes a matrix;
  - the budget gate and the human-facing views come in the last epics.
- Your current tools all break when the full files are untracked:
  - `vim AGENTS.md` opens a stub of at most 80 lines;
  - `sase memory list` reads that stub from disk and silently under-reports;
  - `git log` shows the stub's history;
  - the gitignored file you can open is the interactive audience.
- The packaged contract also moves out of project memory, so a sase upgrade can grow
  every project's preloaded size with no project-level signal.

**What I recommend:**

- Add **R15, size visibility parity**, as an exit criterion of the renderer epic, and
  make it a precondition for untracking anything.
- Concretely:
  - point `sase memory list`'s existing "Loaded lines / Approx loaded tokens" at the
    renderer, with a per-layer breakdown and an `--all-projects` view;
  - give `sase instructions render` a default headline audience (the largest SASE root
    render), so `sase instructions render | nvim -` replaces `vim AGENTS.md`;
  - optionally have `sync` write a never-loaded preview file.
- Land R-router's budget ratchet now on the current generator. When bundles arrive,
  extend it to an effective total, so growth in the package and home layers stays
  visible.

Done this way, the migration makes size visibility better than today. You'd see what
agents actually receive, by layer, for every project, instead of the size of one file
that no provider loads exactly as written.
