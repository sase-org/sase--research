# Instruction Bundles vs. a Readable `AGENTS.md`: Proceed, Re-scope, or Revert?

> **Research question:** You're unsure about the migration from agent instruction files
> to instruction bundles (epic `sase-1ko`). You worry that an agent's core instructions
> are no longer transparent: you used to read `AGENTS.md` to see what a SASE agent was
> told, and now new users and non-SASE agents may need a `sase` command. You also don't
> see the benefits clearly. This report lists every immediate and long-term benefit and
> helps you decide whether to proceed or revert.

Lead consolidation of four independent reports (`cdx`, `cld`, `grk`, `gem`), plus the
lead's own checks on 2026-10-14 against sase `88acef6234` (the E3 acceptance commit).
The lead checks covered: the `sase-1ko` bead and its 15 notes, the accepted decision
record, the E4–E7 roadmap, the fresh-clone research, the live scoreboard and readout,
this run's own delivered bundle, the code paths the reports cite, CI, and git history.
The [evidence section](#evidence) lists the sources.

## Bottom line

**Don't revert. Keep E3's delivery. Change E4 so the repo keeps a full, readable,
CI-checked `AGENTS.md`.**

Three of the four researchers reached the same conclusion on their own (`cdx`, `cld`,
and, with gates, `grk`). Only `gem` backs the current E4 plan. The lead's checks support
the majority.

1. **The transparency loss you're worried about hasn't happened yet.** All 20
   instruction files are still committed. A test (`test_parity_committed_agents_md`)
   checks the committed `AGENTS.md` against the bundle compiler. This run's own Claude
   bundle (19,901 bytes) differs from the committed `AGENTS.md` (18,966 bytes) in only
   five ways:
   - the `Home:` line;
   - the home-only `chezmoi` repo bullet;
   - the two home reference notes (`obsidian`, `tailnet`);
   - a "Claude Single-Turn Instructions" section;
   - unnumbered headings.

   Reading `AGENTS.md` still tells you nearly everything a SASE agent in this repo gets.
2. **Nobody needs a `sase` command today.** A new user, a GitHub reader, or a raw
   `claude`/`codex` session sees exactly what it saw before. That changes only if E4
   ships as planned. E4 would replace the full file with a stub of at most 80 lines and
   move the full render into gitignored files written by `sase instructions sync`. That
   command doesn't exist yet, and E4 has no plan or bead.
3. **E3's benefits are real but modest. Almost none of them require deleting
   `AGENTS.md`.** Of the 29 benefits listed below, only one strictly needs the full
   file gone: no more generated-file churn. It is also the weakest, now that the churn
   has been measured.
4. **The original reasons for removing the file have weakened:**
   - The Codex "can't suppress a committed `AGENTS.md`" constraint is false
     (`project_doc_max_bytes=0` works).
   - The churn is small: 89 of 3,699 commits in 60 days, and 8 in the last 14 days.
     Only 1 of the 89 touched nothing but generated files.
   - The lead found no recorded merge-conflict harm.
   - The "wrong audience" problem can be solved by committing *different content*. It
     doesn't require committing *no content*.
5. **E3 has three live defects to fix before the epic closes.** None is a reason to
   revert.
   - The Codex fallback drops the home layer (cdx Finding A, confirmed in code).
   - Muse explicit runs show the bundle **twice** (new lead finding).
   - Claude runs are still mostly legacy because of install skew.

| Option | What you get | Transparency | Verdict |
| --- | --- | --- | --- |
| **A. Soft revert**: `sase flag disable <p>_explicit_instructions` on each host | E1's after-state: the contract twice for Claude and Codex, no home layer for Grok or Muse, directives hidden in Python, auto-memory back on | **No gain.** `AGENTS.md` was never removed. | Only if the soak triggers [below](#what-would-change-this) fire |
| **A′. Hard revert**: revert the commits, the sase-core wire v2, and the pin | Same runtime as A, plus a lost scoreboard and archive | Loses `show` and per-run records | **No.** Highest cost for the same result. |
| **B. Proceed as planned**: E4 stub plus `sync`, then E5 | Every benefit, including no churn | **Real loss** for GitHub readers, new users, non-SASE tools, and you | Not as written |
| **C. Keep E3; re-scope E4 around a committed full `AGENTS.md`** | Every E3 benefit and nearly every E4–E6 benefit | **Kept**, with per-agent provenance added | **Recommended** |

## Your two concerns, answered directly

### "Are an agent's core instructions no longer transparent?"

"Transparent" covers four separate questions, and E3 moved each one differently.

| Question | Before E3 | Now (E3 on) | After E4 as planned | Option C |
| --- | --- | --- | --- | --- |
| **Q1. What will a SASE agent in this project be told?** | Read `AGENTS.md`. Mostly accurate, but it omitted the home file, the hidden adapter directives, the double contract, Grok's zero load, and auto-memory. | `AGENTS.md` is still a parity-checked projection, about 95% of the bundle. The exact answer is `sase instructions render [-f provider=X]`, which takes about 0.1 s warm. | `render` only; the repo holds a stub | Same as now |
| **Q2. What exactly was agent X told?** | No reliable answer. `instruction_snapshot` recorded files on disk, not what the provider loaded. | **New:** `sase instructions show X` prints the archived bytes and checks their sha256 (`bytes match`). It works for dismissed agents. In a run, use `$SASE_INSTRUCTIONS_FILE`. | Same | Same |
| **Q3. What does a human, a non-SASE tool, or a GitHub reader see?** | The full file, including the SASE runtime contract, so a raw `claude` is told to run `/sase_final` | **Unchanged** | Stub plus "run sync" | Full file, optionally with a header that points to `render`/`show` |
| **Q4. What does the TUI show?** | The "AGENTS.md as launched" row | **Regressed:** the row still opens `AGENTS.md`, which explicit agents no longer load. No TUI surface opens the bundle. | Fixed in E4.4/E6 | Fix as a small task |

Net: Q2 got much better, Q1 and Q3 are unchanged, and Q4 got slightly worse. **Only E4
as written makes Q1 and Q3 worse.**

The four reports framed this differently. Here is how they resolve:

- **`gem`** calls the old transparency "an illusion".
- **`grk`** says "reading `AGENTS.md` is no longer a way to see what a SASE agent was
  told."
- **`cld`** says the file is still "nearly everything".

The lead's byte comparison supports `cld`. `grk` is technically right, because
`AGENTS.md` is not the delivered document, but in practice it overstates the gap.
`gem` overstates the history:

- For Claude, Codex, and Muse, the old file *was* most of what the model saw.
- The serious exceptions were Grok, which loaded nothing for about four weeks, and the
  invisible adapter directives.

The old file was incomplete, not fictional.

### "Do new users and non-SASE agents now need a `sase` command?"

**Not today.** The repo tracks 20 instruction files: root `AGENTS.md` plus byte-identical
`CLAUDE.md`, `GEMINI.md`, `QWEN.md`, and `OPENCODE.md`, and the same five in `tools/`,
`src/sase/ace/`, and `demos/tapes/`. E3 only suppresses *loading* them inside
SASE-launched runs:

- Claude: exact-path `claudeMdExcludes`.
- Codex: `project_doc_max_bytes=0`.
- Grok: untrusted workspace.
- Muse: no `--trust-workspace`.

E3 does not delete the files.

**Under E4 as planned, partly yes:**

- A fresh clone would contain an export stub of at most 80 lines (the roadmap aims for
  about 40), with build and test guidance and a bootstrap clause.
- Full content would require `just agent-instructions` or `sase instructions sync`, or
  `uvx --from 'sase>=X' sase instructions sync`. Neither command is implemented.
- `gem`'s "10–15 line stub" is wrong. The roadmap rejected 15 lines as too small.

## What actually shipped, and what's next

| Epic | Status (2026-10-14) | What it did | Effect on `AGENTS.md` |
| --- | --- | --- | --- |
| E1 `sase-1gu` | Closed 10-06 | Scoreboard (`verify`); Grok `--rules` stopgap; root-only declaration sentence plus a Claude helper PreToolUse guard | None |
| E2 `sase-1h3` | Closed | Compiler; shadow render of a bundle and manifest on every root invocation | None |
| E3 `sase-1ko` | All 10 phases closed; landing (`sase-1ko.land`) | Delivers the bundle once per invocation through an explicit channel; suppresses SASE-owned native files; four default-on sunset flags; `show`, `readout`, conformance check | **Still committed and regenerated**; SASE runs just don't load it |
| E4 | Proposed only | Export stub, `sync`, last-known-good (LKG) store, delete shims, Memory History "stub era". Exit criterion: **20 → 2 tracked files** | Full content leaves git |
| E5 / E6 / E7 | Proposed or optional | Home files and fleet / TUI MEMORY deck / `when:` audiences | E7 makes any single static file less representative |

The accepted decision record (`decisions:instructions-per-invocation`) says in its Cost
paragraph: "Native files remain committed until E4/E5, so the per-invocation fallback
still depends on them." **The record assumes the files will be retired.** Decision
records can't be edited once accepted. If you choose option C, write a new record, for
example "The committed `AGENTS.md` stays a readable projection". Then no future E4 plan
can untrack the file by default.

## Every benefit, immediate and long-term

The last column answers the question that matters for your decision: **does this
benefit require removing the full committed `AGENTS.md`?** "Strength" reflects the
evidence today, on cutover day.

### Immediate (live with E3)

| # | Benefit | Evidence / strength | Needs `AGENTS.md` untracked? |
| ---: | --- | --- | --- |
| 1 | **The SASE contract arrives once, not twice**, for Claude and Codex (about 56% of runs). It also ends the contradictory linked-repo lists in the home and project files. | Harness flag-on: contract 1×; flag-off: 2×. About 3 KB (about 0.8k tokens) per call. Measured. | No |
| 2 | **The same instructions for every provider.** Grok and Muse (about 42% of runs) now get the home layer (tailnet, Obsidian, chezmoi). `common_digest` proves the bundles differ only in the provider section. | Measured on live bundles | No |
| 3 | **Grok gets the full bundle**, not E1's directive plus project text. Before E1 it got nothing. | Live: Grok explicit 1×, native 0. **Most of the Grok recovery belongs to E1:** handoff-aware misses fell from about 14% to about 5% before E3. | No |
| 4 | **Provider directives are reviewable.** Four hand-maintained Python strings are now rendered `pkg.provider.<p>` sections that `render` shows. | A transparency *gain* | No |
| 5 | **Claude instructions move to the system prompt.** They survive `--resume` (snapshot), compaction can't summarize them away, and they outrank repo-supplied text. | Spike-verified. The behavioral effect is **unmeasured**, and this is a semantic change, not just a new transport (cdx). | No |
| 6 | **A dedicated helper bundle for Claude helpers**: memory triggers without the root's `/sase_final` contract. Codex children are declared `inherits_root`. | Probe: one helper attempt denied, no root marker leaked. The guard came from E1. | No |
| 7 | **Deterministic context.** Claude auto-memory (which varied by `sase_<N>`), Grok memory v2, and Codex memories are off in SASE runs. | Decided and spike-verified. The cost is losing any useful accumulated provider memory. | No |
| 8 | **A per-invocation record**: bytes, manifest, sha256, ordered sections, inclusion and exclusion reasons, facts, channel, CLI version. Use `show` afterwards or `$SASE_INSTRUCTIONS_FILE` during a run. | Verified on this run: `explicit` via `claude.append_system_prompt_file`, `bytes match`, and a separate helper row | No |
| 9 | **Exactly-once delivery is measurable.** The bundle marker is counted in the provider's *own* session records, and `sase doctor -C instructions` adds a conformance check. A silent four-week regression like Grok's would show up the same day. | The scoreboard is from E1; the marker is from E3. Currently noisy (session-matching WARNs). | No |
| 10 | **Per-provider kill switches and an atomic per-invocation fallback.** One broken adapter doesn't throw away the rest, and no run starts with empty context. | Designed and tested. **But see Finding A:** the Codex fallback is incomplete. | **No. The fallback *depends* on the committed files.** |
| 11 | **A smaller trust surface.** Muse runs without `--trust-workspace`, and Codex's shadow home is an allowlist (`sase-11s`). | `sase-11s` applies in both flag states and is worth keeping regardless | No |
| 12 | **Foreign and OSS repos.** SASE's contract is delivered without touching upstream files, and a repo's own `AGENTS.md` still loads. | Tested with exact-path excludes | No |
| 13 | **Fresh composition.** A memory edit reaches the next SASE run without regenerating any file. | Minor; the compiler cache becomes a new correctness dependency | No |
| 14 | **Context size is visible** per section and layer, before it silently grows or hits a slot cap. | Diagnostic only; budgets aren't enforced | No |
| 15 | **Recovery and conflict-repair invocations** use the same boundary and recording as ordinary roots. | Code path | No |

### Long-term (enabled by E3, realized in E4–E7)

| # | Benefit | Epic | Needs `AGENTS.md` untracked? |
| ---: | --- | --- | --- |
| 16 | **No generated-file churn or merge conflicts.** Measured today: 89 commits in 60 days (2.4% of all commits), 8 in 14 days, 1 that touched only generated files. No conflict harm found in beads or git messages. | E4 | **Yes. This is the only one, and it's the weakest.** |
| 17 | **Fewer shim copies.** Delete `GEMINI.md`, `QWEN.md`, and `OPENCODE.md` in all four directories (12 of 20 files). Keep `CLAUDE.md` as a byte copy or an `@AGENTS.md` import. | E4.3 | No. Switch agy to prefix delivery in the same change. |
| 18 | **The right content for non-SASE readers.** Today the committed file tells a raw `claude` to run `/sase_final`. | E4/E5 | **No.** That needs *different content* (`mode: export`), not untracking. **Blocked by Finding B.** |
| 19 | **Home files become `interactive` renders,** so `~/AGENTS.md` stops pushing `/sase_final` into every interactive session under `$HOME` (a present bug). | E5 | No |
| 20 | **`sase tmux-agent` and other projects** (bob-cli, actstat) go through the same delivery hook. | E5 | No |
| 21 | **In-TUI visibility:** a MEMORY deck (Manifest, Ledger, Bundle cards), a delivery chip (`‼2×`, `∅`), and a "Seen by" index. This is the in-product answer to your concern. | E6 (can run alongside E4) | No |
| 22 | **Memory History and the "as launched" row keyed to bundle ids** instead of a disk snapshot | E4.4/E6 | No |
| 23 | **Audiences:** role-, provider-, and phase-specific content with per-audience budgets. Hard rules and read triggers stay unconditional (R9). | E7 (conditional on measured value) | No. But it makes "read one file" impossible by design. |
| 24 | **Plugin sections** that appear only when the plugin is active | E7+ | No |
| 25 | **Smaller, cache-friendly prompts**: a stable prefix plus a trailing marker | E7 | No |
| 26 | **Better experiments:** digests separate instruction changes from provider changes, and joining manifests, memory reads, and outcomes can find dead density | Any time | No |
| 27 | **`%dispatch` renders on the target host** with its own facts; no instruction bytes cross the wire. | Already true | No |
| 28 | **A Rust-owned manifest wire** that a web, editor, or other frontend can consume | Already true (composition is still Python) | No |
| 29 | **A safer publishing boundary**: a public export that omits personal and home instructions | E4 | No. **Today's export still leaks home metadata (Finding B).** |

`gem` adds "prompt-injection resistance" as a benefit. That cuts both ways. A
system-prompt channel raises the priority of SASE's text, but it also raises the
priority of everything in the bundle, including repo-derived memory. Treat it as a trust
decision, not a free win (cdx).

**Key observation:** of 29 benefits, only #16 needs the full file gone, and the measured
churn is small. The roadmap ties "deliver explicitly" to "stop committing a readable
file" for historical reasons:

- R7's Codex constraint, which turned out to be false.
- The fresh-clone report rejected full files for three reasons: "wrong audience, 112
  commits in 60 days, conflicts across 47 workspaces". Each is weaker than it looked:
  - **Audience:** solvable by changing the content.
  - **Churn:** now 89 commits in 60 days, falling, and riding along with real edits.
  - **Conflicts:** no measured evidence found.
- The roadmap noted R7 "still holds for audience and churn reasons," but that was
  before anyone weighed GitHub and human readability as a cost. No earlier report did.

## Costs and risks of keeping E3

- **Code volume.** `src/sase/instructions/` is about 7.4k lines, with about 6.2k lines of
  tests. Much of that is E1 and E2 (scoreboard, compiler), which you would keep even
  after a revert.
- **Fragile provider surfaces:**
  - Claude's `--append-subagent-system-prompt-file` is hidden from `--help`.
  - Codex's `project_doc_max_bytes=0` behavior is undocumented.
  - Grok has a 120 KiB argv cap, and Codex has a 32 KiB slot cap.
  - Muse depends on a prompt prefix.

  The conformance check, the fallback, and the flags mitigate this. The file-based world
  was fragile too: a Grok trust change silently cut its instructions to zero.
- **Precedence shift.** Claude's project context moved from a user-message file to the
  system prompt. There is no behavior data yet.
- **Privacy.** With `home_layer = yes`, tailnet and Obsidian triggers now reach xAI and
  the Muse vendor. Per-invocation bundle files are mode 0644 (cdx).
- **Thin soak evidence.** Since the first explicit render, there have been about 22
  explicit runs with 1 miss (Codex non-research, 1 in 4). Pre-cutover baselines:
  - Claude: 0/74 misses.
  - Codex: 0%.
  - Grok: 6/85 (7%).
  - Muse: 11/231 (5%).

  That's too small to conclude anything either way.
- **Two artifacts to keep aligned** under option C. See the CI gap under
  [lead findings](#new-findings-from-the-lead).

## Where the reports disagreed, and how this report resolves it

| Topic | Positions | Resolution |
| --- | --- | --- |
| **E4: untrack the file?** | gem: proceed as planned. grk: hold E4 until export, sync, docs, and a TUI view exist. cld and cdx: re-scope E4 to keep a full committed file. | **Re-scope (C).** grk's gates are necessary but not sufficient. Even with `sync` built, a GitHub reader or a broken install still can't see the contract. AGENTS.md is now a cross-vendor convention (donated to the Linux Foundation's Agentic AI Foundation in Dec 2025; OpenAI reports 60k+ adopting projects), which raises the value of a real committed file. |
| **Was the old file transparent?** | gem: an "illusion". grk: no longer what agents see. cld: still nearly everything. | **cld**, verified by the lead's byte diff of this run's bundle against `AGENTS.md` |
| **Effect of a revert on Grok** | gem: "Grok immediately breaks again", back toward 26% compliance | **Wrong for a flag revert.** Flags restore E1's `--rules` stopgap (directive plus project `AGENTS.md`). Grok loads nothing only if E1 is reverted too (grk, cld). The 60%→26% figure was a raw rate from earlier research; the later handoff-aware readout put Grok misses at about 14% before E1 and about 5% after. |
| **Revert brings back churn** | gem | **Wrong.** E3 didn't change churn; the files are still committed and regenerated. |
| **Helper "crashes"** | gem | **Overstated.** 13–15 helper attempts in 30 days led to 2 accepted parent declarations. That's a correctness bug, not a crash. E1 fixed it. |
| **"Cryptographic provenance"** | gem | **Overstated.** It is a sha256 integrity check of archived bytes against the manifest, not signed provenance. cdx's framing is the right one: a manifest proves intended composition; a digest proves integrity; observations support delivery; behavior needs separate evaluation. |
| **File counts and churn** | gem: 35 files, 111 commits. cld and grk: 20 files, 88 commits. | 35 counts the whole inventory (sase 20, home 5, bob-cli 5, actstat 5). The sase repo has **20**. Churn at HEAD: **89** in 60 days and **8** in 14 days. 112 was the roadmap's older figure. |
| **Stale docs** | cld, grk, and cdx: `docs/instruction_bundles.md` says Claude and Codex are legacy | **Fixed at HEAD `88acef6234`.** The bundle template wording ("render into this file", "every provider instruction shim") is still from the file era (`src/sase/main/init_memory/templates/memory-sase.template.md:5,7`). |
| **Claude live status** | cld: first Claude explicit at 13:10Z. grk: Claude still legacy, 2×, auto-memory. | **Both are true.** This run is explicit and verified. The 4–6 hour scoreboard still rates Claude `legacy:provider_legacy` with 2× contract and auto-memory, and the readout shows 7 legacy and 4 explicit Claude runs since cutover. Launch paths and installed binaries are behind the workspace. |

## New findings from the lead

1. **cdx Finding A is confirmed in code. The Codex fallback drops the home layer.**
   - The suppression decision keys off the feature flag, not the actual delivery:
     `_codex_home._create_shadow_codex_home` sets
     `explicit = explicit_instructions_enabled()` (`src/sase/llm_provider/_codex_home.py:128`)
     and links the home `AGENTS.md` only `if not explicit` (`:152`).
   - Meanwhile `CodexProvider.invoke` uses the bundle only when an active `explicit`
     delivery exists (`src/sase/llm_provider/codex.py:269-300`).
   - So in the render-failure and no-`artifacts_dir` paths, Codex gets neither the
     bundle nor the home file.
   - This is recorded as epic note #15. Fix it before the epic closes.
2. **cdx Finding B is confirmed. The export render leaks home metadata.**
   `sase instructions render -f mode=export,provider=codex` (18,386 bytes) still
   contains the home-only `chezmoi` repo bullet tagged "(home configuration)". Fix this
   before committing any export render publicly.
3. **New: Muse explicit runs show the bundle twice.** In the last 6 hours, both Muse
   runs (2 sessions) score `bundle 2×`, `contract 2×`, all explicit, native 0. That
   either violates the exactly-once invariant (R6) or is an observer artifact of prompt
   prefixes repeated across continuations. No other report saw this; they assumed Muse
   was quota-blocked.
4. **CI regenerates the file instead of checking it.**
   - Both `.github/workflows/master-gate.yml:135` and `ci.yml:57` run
     `sase init memory --no-commit`, which rewrites files before tests run.
   - So the committed-file parity test passes against the *regenerated* file, and a
     stale commit isn't caught.
   - `sase init memory --check` already exists and reports drift without writing (clean
     at HEAD).
   - Option C should add that check before the regeneration step. This is the cheap
     version of E4.1's `export --check`.
5. **The TUI "as launched" row still reads `instruction_snapshot`.**
   `src/sase/ace/tui/widgets/prompt_panel/_agent_memory_versions.py:266-298` resolves
   the row to the workspace `AGENTS.md`. Under option C this is close to right
   (parity-checked), but it should open the run's bundle.
6. **Option C has two variants with a fallback trade-off that no report noticed:**
   - **C1 (commit today's runtime projection):** costs nothing and keeps the legacy
     fallback complete.
   - **C2 (commit the `mode: export` render, without the `/sase_final` contract):** a
     better fit for humans and non-SASE tools, but it weakens the fallback. On a render
     failure:
     - Grok's E1 `--rules` path and Muse's legacy path, which use only the project
       file, would lose the turn contract.
     - Claude and Codex would still get it from the home file.

   **Start with C1.** Move to C2 only together with an LKG store, or with a fallback
   that injects the package contract.

## Recommendation and next steps

1. **Keep E3 on and finish it properly.**
   - Fix Finding A.
   - Explain or fix Muse's 2× marker.
   - Get every execution host's installed `sase` onto E3 so Claude runs are explicit
     everywhere.
   - Soak each provider for 7 days from **its own** first explicit render, comparing
     `sase instructions readout -s <first explicit>` against the baselines. Muse has
     very few runs (quota until 10-19).
   - If the soak is clean, answer the flag beads (`sase-1kv`, `sase-1ks`, `sase-1kt`,
     `sase-1ku`) with Remove. If one provider regresses, disable only that flag.
2. **Decide E4's shape now, in a decision record.** "The committed `AGENTS.md` stays a
   CI-checked readable projection; untracking reopens only on a named trigger." Records
   are immutable, so this is a new record that narrows the Cost sentence in
   `instructions-per-invocation`.
3. **Re-scoped E4 (about one medium epic):**
   - Keep the full root `AGENTS.md` (C1).
   - Add a 3–4 line header naming the source (`sase/memory/`), stating that SASE-launched
     agents also get the home layer and a provider directive, and pointing to
     `sase instructions render` and `show`.
   - Add `sase init memory --check` to CI.
   - Delete the `GEMINI.md`, `QWEN.md`, and `OPENCODE.md` copies, switching agy to
     prefix delivery in the same change.
   - Decide separately whether to fold the nested `tools/`, `ace/`, and `tapes/` sets
     into path-scoped notes.
   - Keep `CLAUDE.md` as an `@AGENTS.md` import or a copy.
   - Point the "as launched" row at the bundle.
   - Update the file-era wording in the bundle template.
   - **Drop** the stub, `sync`, the gitignored projections, the bootstrap clause, and the
     LKG store. The committed file remains the fallback.
4. **Pull a thin slice of E6 forward.** List `instructions/*.md` in the Agents-tab Files
   deck, and put the four inspection commands in its help text. That restores casual
   in-product inspection within a week. The full MEMORY deck can wait.
5. **Keep E5 and treat E7 skeptically.** E5 fixes a real present bug: home files push
   `/sase_final` into interactive sessions. E7 is the one direction that makes "read one
   file" impossible by design, so hold it to its measured entry gate.

### What would change this

- **Disable one provider's flag** if, after 7 days, that provider's explicit-run misses
  are more than 2 points above baseline, a non-declared fallback appears, or Claude
  behavior worsens after the move to the system prompt. That is the decision record's
  own reopen clause.
- **Return to the original E4 (untrack the file)** if any of these happens:
  - merge conflicts on generated files measurably slow landings;
  - E7 audiences ship and a single file becomes misleading;
  - outside contributors need a purpose-built stub more than the full contract.
- **Stop after E3 entirely** if the soak shows no measurable gain and you value
  simplicity. E3 plus a committed `AGENTS.md` is a defensible end state.

## Cheat sheet: how to see what an agent gets

```bash
cat AGENTS.md                                 # standing project instructions (no SASE needed)
sase instructions render                      # what a root agent here would get now
sase instructions render -f provider=grok -s  # one provider's bundle as a section table
sase instructions show NAME [-l|-H|-s|-j]     # exact bytes delivered to agent NAME (archived)
sase instructions verify -a NAME              # what the provider's own records show it loaded
sase instructions readout --since 7d          # declaration misses × delivery mode
echo $SASE_INSTRUCTIONS_FILE                  # inside a run: this invocation's bundle
```

`render -a NAME` uses the agent's facts but **today's** sources. Use `show` for history.
`verify` reports but doesn't gate, so read its rows rather than its exit code.

## Evidence

- **Researcher reports** (this directory): `__cdx` (code-level findings A and B, the
  "three decisions conflated" framing, what manifests prove), `__cld` (four-question
  transparency matrix, benefit-by-benefit untracking test, option C), `__grk`
  (provider-by-provider history, sequencing gates, E6 as the transparency epic), and
  `__gem` (legacy failure catalogue and inspection walkthrough; several overstatements
  corrected above).
- **Bead `sase-1ko`** (via `sase bead read`): every phase closed, the landing phase in
  progress, and notes #1–#15, including the spike results, the acceptance record
  `file:explicit:294276aba63ff9003d936aaf`, the readout baselines, and the cdx Finding A
  note.
- **Decision record** `decisions:instructions-per-invocation` (via `sase memory read`).
- **Prior research** (via `sase artifact read`): the E1–E7 roadmap
  `research:202610/memory_built_instruction_migration_epics/memory_built_instruction_migration_epics.md`
  and the fresh-clone design
  `research:202610/fresh_clone_bootstrap_and_native_subagent_instructions/fresh_clone_bootstrap_and_native_subagent_instructions.md`.
- **Lead's live checks (apollo, about 13:45–14:00Z):**
  - `sase instructions show research.1a.final -l`: root `explicit` via
    `claude.append_system_prompt_file`, `38870537c9d6`, 19,901 B, `bytes match`; helper
    `explicit` via `claude.append_subagent_system_prompt_file`.
  - `sase instructions verify -a research.1a.final`: all 21 observed sections seen once,
    explicit, native 0.
  - `sase instructions verify -s 4h/6h` (Claude legacy aggregate; Codex and Grok
    explicit 1×; Muse explicit 2×).
  - `sase instructions readout -s 2026-10-14T10:35:06Z`.
  - `render -f mode=export,provider=codex`.
  - `sase init memory --check`.
- **Repo measurements at `88acef6234`:**
  - `git ls-files`: 20 instruction files, 131,345 B, root files byte-identical.
  - `git log --since='60 days ago' -- AGENTS.md`: 89 of 3,699 commits; weekly
    distribution falling to 1–5 per week; 76 mixed with code, 12 memory plus generated
    only, 1 generated only.
  - Bead regex search and git-message search: no recorded `AGENTS.md` merge-conflict
    harm.
  - CI workflow steps.
  - `tests/instructions/test_render_parity.py::test_parity_committed_agents_md`.
- **External context:**
  - [OpenAI: Agentic AI Foundation](https://openai.com/index/agentic-ai-foundation/):
    AGENTS.md donated to the Linux Foundation's AAIF, Dec 2025; adoption figure
    self-reported.
  - [Technology Magazine: Linux Foundation launches AAIF](https://technologymagazine.com/news/one-rule-for-all-agents-linux-foundation-launches-aaif).
  - [agents-md standard summary](https://agentic-ai.readthedocs.io/en/latest/Standards/agents-md/).

**Main limitation:** this was researched on cutover day. The architectural and
transparency conclusions are solid. The behavioral case for E3, beyond exactly-once and
parity, still depends on the 7-day soak.
