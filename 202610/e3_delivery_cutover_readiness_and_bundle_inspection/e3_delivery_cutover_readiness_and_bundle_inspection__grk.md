# E3 explicit delivery cutover: readiness and bundle inspection

> Researcher `research.13.grk` · 2026-10-13 · independent of the other four swarm
> reports. Primary input:
> `research:202610/memory_built_instruction_migration_epics/memory_built_instruction_migration_epics.md`.

## Bottom line

**The E3 entry gates are met. The E3 implementation epic has not been created yet.**

E1 (`sase-1gu`) and E2 (`sase-1h3`) have been closed for a week. Live
`sase instructions verify --since 7d` still shows the E1 after-state (Claude and Codex
load the contract twice from native files; Muse and Grok miss the home layer; Grok
gets the contract once through `--rules`; Claude helpers accept zero declarations).
Shadow manifests cover ordinary sessions `N/N` with zero `.error.json`.
`sase instructions render -p` in the sase checkout is clean (`contract_count=1`).

That is exactly the yardstick the consolidated epic report said you should see *before*
E3. What is missing is the E3 plan itself: there is no
`plan:202610/e3_explicit_delivery_cutover.md` (or any similarly named epic plan), no E3
bead, and none of E3.1's spikes have landed in code. Launching "the E3 epic" today would
mean writing and approving that plan first, then launching its six phases. The
codebase is ready for that plan. It is not already mid-cutover.

## What E3 is

From the consolidated migration report, **E3 Explicit delivery cutover** is the epic
that makes every major provider load the *memory-built instruction bundle exactly once*
through an explicit channel, suppresses SASE-owned full native instruction files for
those runs, and gives Claude helpers the helper bundle. The report treats E3 as the
point where "every SASE agent's instructions are built from memory at launch."

| Phase | Slug | Size | Depends on | Job |
| ---: | --- | --- | --- | --- |
| E3.1 | `spikes` | small + xsmall probes | — | Muse without `--trust-workspace`? Does Grok persist `--rules`? Do `claudeMdExcludes` exact paths cover home, workspace, and nested files while sparing `sase/repos/**`? Codex `project_doc_max_bytes=0` fixture. Auto-memory probe. |
| E3.2 | `delivery-plan` | medium | E3.1 | `llm_instruction_delivery` hook → `DeliveryPlan` with `root` / `subagent` slots (`explicit` \| `inherits-native` \| `inherits-root` \| `none`). Per-provider **sunset** flags. Render failure falls back to legacy for that invocation. `%dispatch` renders on the target host. |
| E3.3 | `claude` | medium | E3.2 | Root bundle via `--append-system-prompt-file`. Helper bundle replaces the E1 template. Exact-path `claudeMdExcludes`. Auto-memory off in SASE runs. |
| E3.4 | `codex-grok` | medium | E3.2 | Codex: private `$CODEX_HOME/AGENTS.md` (neutral core + home) + `developer_instructions` for the root overlay; `project_doc_max_bytes=0` in SASE-managed projects. Grok: `--rules` carries the **full root bundle**, replacing the E1 stopgap. |
| E3.5 | `muse-agy` | medium | E3.2 | Muse prompt-prefix delivery; drop `--trust-workspace` if the spike passed. agy / Qwen / OpenCode stay `inherits-native` until E4. |
| E3.6 | `conformance` | small | E3.3–E3.5 | Scoreboard asserts each bundle id once per invocation. Decision record **"Instructions Are Rendered Per Invocation And Delivered By Adapters"**. |

**Documented entry:** E1 has had at least 3 days of runs and an acceptable readout; E2's
parity check is clean.

**Documented confirm-yourself after E3 lands:**

```bash
sase instructions verify --since <landing>      # major rows: 1× / ✓ / ✓ / 0
sase instructions verify -p claude --helpers     # helper bundle ids, no root ids
sase flag list | grep instruction                # per-provider sunset kill switches
```

## Entry gates: current evidence

Checked 2026-10-13 against this workspace's `sase` checkout at `8959b0e6fc`
(2026-10-13 16:15 EDT, `fix(tests): stabilize New Project flows and sudo checks`).
The live CLI is the installed sase that agents actually run.

### Gate 1 — E1 landed, ≥3 days of runs, readout acceptable

| Item | Status |
| --- | --- |
| Epic `sase-1gu` | Closed 2026-10-06 16:05 UTC as `done`. Six phases closed. Plan `plan:202610/e1_instruction_scoreboard_and_stopgaps.md`. |
| Grok stopgap (`sase-1gu.3`) | Unconditional after flag retirement. `grok.py` always passes `--rules` = single-turn directive + project `AGENTS.md` once in SASE-managed projects. Home layer and `CLAUDE.md` are omitted. 120 KiB argv guard. |
| Claude helper channel (`sase-1gu.4`) | Unconditional. Packaged helper template + PreToolUse guard. |
| `sase-1gj` | Closed as superseded by E1. |
| Calendar | Grok fix deployed 2026-10-05 16:34 EDT; Claude helper channel 2026-10-06 05:26 EDT; E1 land 2026-10-06. **Seven days of production runs** as of this report. |

**Scoreboard `--since 7d -n 50` (generated 2026-10-13T20:35Z):**

| Provider | Manifest | Contract | Home | Project | Directive | Native-full | Foreign | Helpers |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| claude | 7/7 | 2× | ✓ | ✓ | ✓ | 2× | auto-memory | general-purpose, web-fetch: 0 attempts, 0 accepted |
| codex | 25/25 | 2× | ✓ | ✓ | ✓ | 2× | — | 0 spawns |
| muse | 13/13 | 1× | ✗ | ✓ | ✓ | 1× | — | — |
| grok | 24/24 | 1× | ✗ | ✓ | ✓ | 0 | memory-v2 ½:False | — |
| agy | 2/2 | ◌ | ✗ | ◌ | ◌ | ◌ | — | — |

This is the E1 *after* table plus E2's coverage column. Claude still double-loads; that
is the bug E3 is supposed to fix, so seeing it still is a healthy scoreboard, not a
failed soak.

`sase doctor -D -C instructions` WARNs on `instructions.delivery` for Claude and Codex
`contract 2×, native-full 2×`. That WARN is the same expected pre-E3 drift. Helpers
check is OK (zero accepted helper declarations).

**Grok final-declaration watch metric** (the E1 report's 3-day readout). Among 2026-10
Grok runs, excluding research names, `--mon` / `--plan` members, and
`outcome` in `{monitored, gated}`:

| Window | Completed runs with `final_submission.json` |
| --- | --- |
| Before the E1 Grok fix (2026-10-01 … 2026-10-05 20:34 UTC) | 6 / 23 = **26%** |
| After the fix through 2026-10-13 | 23 / 31 = **74%** |

The pre-fix 26% matches the research report's post-regression figure. Post-fix completed
Grok runs submit declarations at 74%, above the pre-regression 60% the report used as
the recovery target. Sample is small (n=31 completed) and includes every enabled
project's ace-run tree for the month, but the direction is a recovery, not a
regression.

Claude helper `sase final` attempts in the 7-day scoreboard: **0 attempts, 0 accepted**.

### Gate 2 — E2 landed, parity clean, shadow coverage

| Item | Status |
| --- | --- |
| Epic `sase-1h3` | Closed 2026-10-06 22:09 UTC. Seven phases closed. Plan `plan:202610/e2_instruction_bundles_shadow_mode.md`. Land note: origin/master `66d598d198`. |
| Shadow render | Unconditional after `sase-1jc.10` retired `instruction_shadow_render`. Fail-open. Still **shadow-only**: providers do not read `SASE_INSTRUCTIONS_FILE`. |
| `sase instructions render -p` (sase checkout) | Exit 0. `contract_count=1`, five extra bundle sections (four frames + `pkg.provider.codex`), none of them failures. |
| Ordinary-session coverage `--since 7d` | claude 7/7, codex 25/25, grok 24/24, muse 13/13, agy 2/2. `errors_total: 0`. |
| Warm render p95 | claude 167 ms, codex 99 ms, grok 119 ms, muse ordinary 171 ms. All under E2's 250 ms warm budget. |
| Cold p95 | 0.46–1.12 s. First miss on this Grok run was 1170 ms (`cache: miss`). Warm path is the budget that E2 committed to. |

The `-c` table also prints Muse `conflict_repair` (1/13) and `declaration_recovery`
(5/13) with long uncovered lists. Those denominators are **all Muse sessions in the
window**, including ordinary ones. Ordinary Muse coverage is 13/13; the "uncovered"
names (`research.12.mus`, `bob-cli-74.2`, …) are ordinary sessions that have no
conflict-repair or declaration-recovery manifest, which is the expected shape. Treat
the per-purpose Muse rows as a scoreboard presentation quirk, not missing shadow
renders.

## What has moved under E3's feet since the 2026-10-05 report

Three later landings change how you would write the E3 plan. They do not remove the
need for E3.

1. **E1 and E2 sunset flags are gone.** Epic `sase-1jc` (closed 2026-10-11) phase
   `sase-1jc.10` retired `grok_rules_delivery`, `claude_helper_channel`,
   `instruction_shadow_render`, and `muse_synchronous_shell`, and made the On branches
   unconditional. The live registry has a single unrelated flag,
   `artifacts_agent_pane_retired`. E3 still needs **new** per-provider sunset flags for
   the *delivery cutover* (legacy native path reachable while the explicit path soaks).
   Those flags cannot be the retired E1/E2 keys. Rollback remains
   `sase flag disable <provider-flag>` per host, once E3 creates them.

2. **Shadow render is already always on.** `sase-1h4`'s removal note is explicit:
   "still shadow-only, no E3 delivery cutover." Docs (`docs/instruction_bundles.md`,
   `docs/agent_providers.md`) still describe E2. The renderer E3 would consume is in
   production.

3. **No E3 plan was written after E2 landed.** The consolidated report said to write
   each plan after the previous epic lands so the new plan can use that epic's evidence.
   E2 has been closed for seven days. `sase artifact show` for
   `plan:202610/e3_explicit_delivery_cutover.md` and
   `plan:202610/e3_instruction_delivery_cutover.md` both resolve as **missing**. The
   202610 plans sidecar has E1 and E2 instruction plans and no E3 cutover plan.

## Spikes E3.1 still has to answer (code as of HEAD)

These are *phase work*, not failed entry gates. They are still unanswered in the tree:

| Spike | Finding today |
| --- | --- |
| Muse `--trust-workspace` | Still hard-coded in `src/sase/llm_provider/muse_provider.py` (`base_args.extend(["--trust-workspace", ...])`). |
| Grok `--rules` recording | E1 already showed the payload in `system_prompt.txt` inside `<human_rules>`. `prompt_context.json` `agents_md_files` stays `[]` because Grok still does not load native files. A live `verify -a` on completed Grok `research.12.grk` observed `pkg.provider.grok`, `pkg.root.final_declaration`, and project refs on the **explicit** channel only (`native=0`). |
| `claudeMdExcludes` | No matches under `src/sase/llm_provider/`. Claude still loads native `CLAUDE.md` / `AGENTS.md` (scoreboard native-full 2×). |
| Codex `project_doc_max_bytes=0` | No matches under `src/sase`. Codex native-full remains 2×. |
| Claude auto-memory | Scoreboard foreign column still `auto-memory`. No `CLAUDE_CODE_DISABLE_AUTO_MEMORY` / `autoMemoryEnabled` wiring in `src/`. |
| Grok memory v2 | Scoreboard `memory-v2½:False` (mixed; majority off in this window). E3.4 is where the report said to decide it. |

**Grok argv size.** E3.4 would put the *full root bundle* on `--rules`. This run's
shadow bundle is 20,238 bytes / 5,062 `tokens_est`. Project `AGENTS.md` is 18,694 bytes;
home `AGENTS.md` is 4,084. The 120 KiB guard has plenty of headroom for today's sase
render. A future audience or a much larger home layer is the thing that would hit it.

Current Claude root delivery is still `--append-system-prompt` for the directive, plus
native files — not `--append-system-prompt-file` with the bundle. That is E3.3.

## Ready / not-yet, in launch terms

**Ready now**

- Write the E3 epic plan from the consolidated report, using this week's scoreboard,
  E1/E2 acceptance records, and the flag-retirement change above.
- Approve that plan and launch E3.1 (spikes + probes) as soon as it exists. The soak
  the report asked for has already happened.
- Keep `sase instructions verify` and `sase doctor -D -C instructions` as the
  landing yardstick. After E3, those Claude/Codex 2× WARNs should flip to 1× / native 0.

**Do before calling the whole epic "in flight"**

- An approved epic plan with six phases, `depends_on`, per-provider sunset flags created
  via `sase flag new` (kind `sunset`), and the decision-record memory edit named in the
  plan (required by `/sase_memory_write`).
- E3.1 answers, especially Muse `--trust-workspace` and Claude excludes / auto-memory.
  E3.2–E3.5 depend on those answers.
- A file-by-file memory-edit list on the plan. The only planned memory edit in the
  research report is the E3 decision record, plus a `memory` task bead (via
  `/sase_new_task`) to harvest Claude auto-memory notes when E3.3 lands.

**Out of this epic, and easy to mix up**

- Optional **E6** (TUI instruction visibility, `sase instructions show`, MEMORY deck on
  picker letter `y`) is *after* E3. Bundle inspection today is CLI + the run's
  `instructions/` directory. See the next section.
- **E4** (retire committed full instruction files) waits for E3's sunset flags to be
  *removed*, about 7 days after E3 lands.
- A different closed epic also named "E3" (`sase-18j`, failure triage) is unrelated.

## How to see what a completed agent's instruction bundle contained

There are **three different objects** people call "the instructions." The Agents tab
today shows two of them well and the third only by path.

| Object | What it is | Where it lives | Proves delivery? |
| --- | --- | --- | --- |
| **Shadow bundle + manifest** | The memory-built Markdown the compiler would have delivered, plus the sase-core v1 manifest | `<artifacts>/instructions/NN-<provider>.{md,json}` and `~/.sase/instructions/bundles/<sha[:2]>/<sha>.md` | No. `delivery.status` is `shadow`. Providers ignore `SASE_INSTRUCTIONS_FILE`. |
| **Native launch snapshot** | Blob inventory of workspace `AGENTS.md` / shims plus the first home instruction file | `agent_meta.json` → `instruction_snapshot`; bytes at `~/.sase/instruction_snapshots/<oid>` | No. Launch-time file inventory. Nested files omitted. |
| **Observed load** | What the provider's own session records actually contained | `sase instructions verify -a NAME` (Claude transcripts, Codex rollouts, Grok `system_prompt.txt` / `prompt_context.json`, Muse `session.jsonl`) | Yes, for the scoreboard columns. |

E6 is the epic that would put Manifest / Ledger / Bundle cards on the Agents tab. It
has not started. `sase instructions show` is not a command (`list`, `render`, `verify`
only).

### From the Agents tab (completed agent selected)

1. **Identity / copy the artifacts directory.** The agents copy-target map binds
   `artifacts_dir` to `d`. `sase agent show NAME` always prints `Artifacts dir:` if you
   would rather stay in a shell. Example for this run:
   `…/artifacts/ace-run/202610/13/20261013162424`.
2. **`V` (`view_agent_metadata`)** opens `agent_meta.json` in the pager. The
   `instructions` object names the latest shadow file:

   ```json
   "instructions": {
     "schema_version": 1,
     "count": 1,
     "latest": {
       "seq": 0,
       "provider": "grok",
       "purpose": "ordinary",
       "sha256": "bc648948db99e217b88de3d4add6b6fb32c796d9b0ddc23ec24a7c085f88401f",
       "common_digest": "6b4280fc40a67a470899ee92c0b84e995d37a984f057a80c904d4963653acea6",
       "manifest": "instructions/00-grok.json"
     }
   }
   ```

3. **Context card, MEMORY lane.** The `◇ AGENTS.md as launched` row is the *native
   snapshot* (tracked `AGENTS.md` / shims / home file at launch), with a version chip
   that opens that snapshot in the pager. It is the E4-era "launch row," not the
   compiler bundle.
4. **`a` (artifact files).** The picker lists synthesized/indexed artifacts: chat
   transcript, plan, images, PDFs. `synthesize_default_artifact_files` does not register
   `instructions/*.md`. Pressing `a` on a completed agent will not open the bundle.
5. **Files deck (`p` then `f`).** One card per workspace diff or attached file. Shadow
   instruction files are not diffs, so they do not appear here.
6. **Memory pane INSTRUCTIONS rail** (Memory panel, not an Agents-tab deck). Git
   history of tracked `AGENTS.md` / shim subjects (`instructions:<scope>/<dir>`). Useful
   for "what did the committed file look like," not for the per-invocation bundle.

### From the CLI (this is the supported path today)

```bash
# 1. Artifacts dir for a completed agent
sase agent show NAME                    # prints Artifacts dir
sase agent list -a -j                   # JSON includes artifacts_dir

# 2. Historical bundle that was recorded at invoke time
less "$ART/instructions/00-<provider>.md"
python3 -m json.tool "$ART/instructions/00-<provider>.json" | less

# 3. Same bytes in the content-addressed store (path is bundle.store_path in the JSON)
#    ~/.sase/instructions/bundles/<sha[:2]>/<sha>.md   mode 0444

# 4. Intended vs observed, section by section
sase instructions verify -a NAME --since 7d

# 5. Fresh preview from *today's* memory using that agent's facts
sase instructions render -a NAME        # Markdown
sase instructions render -a NAME -s     # section table
sase instructions render -a NAME -j     # preview manifest
# stderr: "agent NAME: bundle matches recorded <sha>" when sources are unchanged

# 6. Fleet view
sase instructions verify --since 7d
sase instructions verify -c --since 7d
sase instructions verify -p claude -H
sase doctor -D -C instructions
```

`render -a` recompiles from the **current** project and home sources. If memory changed
after the run, the fresh sha256 diverges and stderr lists changed section ids. The
historical truth is always `$ART/instructions/NN-<provider>.md` (or the store path in
the manifest).

Worked example on this Grok run (`research.13.grk`):

- `$ART/instructions/00-grok.md` — 20,238 bytes, 329 lines, 27 included sections.
- Manifest `delivery.status: "shadow"`, `observation.status: "unobserved"` at write
  time, `facts.actor: sase_root`, `facts.purpose: ordinary`, `cache: miss` then a later
  `render -a` cache hit at 75.9 ms that reported **`bundle matches recorded bc648948db99`**.
- Headings: `# … Agent Instructions`, `## Core Memory`, `## Reference Memory`,
  `## Memory Webs`. Home layer is present in the *bundle* (`Home: apollo - …`) even
  though Grok's *observed* load still misses home — that gap is the E1 stopgap, and E3.4
  is what would put the full bundle on `--rules`.

Worked example on a completed Grok agent (`research.12.grk`, job project):

```
sase instructions verify -a research.12.grk --since 7d
```

Scoreboard: contract 1×, home ✗, project ✓, directive ✓, native-full 0, coverage 1/1.
Section diff (excerpt): `pkg.provider.grok` observed 1 on **explicit**; home refs
observed 0; `proj.web.task_types` observed 0. That is "what this completed Grok agent
actually received" versus "what the shadow bundle contained."

Worked example on completed Claude `research.12.cld`: contract 2×, auto-memory, helper
template present on seven `web-fetch` helpers, 0 attempts / 0 accepted. The section
diff for that session was `◌ partial` — Claude's observed-mode parser sometimes cannot
attribute section bodies even when the summary columns are populated. Use the summary
row plus the helper table; do not treat a fully-blank section table as "the bundle was
empty."

### After E3 / E6 (for orientation)

Once E3 lands, `verify -a` should show each included section on the **explicit**
channel once, native-full 0, and helper rows carrying the helper bundle id. Once E6
lands, `sase instructions show -j NAME` is specified to equal the Agents-tab MEMORY
deck (Manifest, Ledger, Bundle cards, picker letter `y`). Until then, the commands in
the CLI block above are the way to see a completed agent's bundle.

## Recommendation

Write and approve the E3 epic plan now; launch E3.1 as soon as it is approved. The
3-day E1 soak and E2 parity gate the consolidated report asked for are already in
hand. Keep E3.2–E3.5 behind E3.1's spike answers. Create new per-provider sunset flags
in E3.2 — the E1/E2 flags were retired on purpose and must not be revived. Use the
live 7-day scoreboard in this report as the "before" JSON to attach when E3 lands.

## Evidence index

- `sase artifact read research:202610/memory_built_instruction_migration_epics/memory_built_instruction_migration_epics.md`
- `sase artifact read plan:202610/e2_instruction_bundles_shadow_mode.md`
- `sase bead read` of `sase-1gu`, `sase-1h3`, `sase-1h4`, `sase-1jc`, `sase-1jc.10`,
  `sase-1gj`
- `sase instructions verify --since 7d -n 50 -j` (generated 2026-10-13T20:35Z)
- `sase instructions verify -c --since 7d -n 50 -j` (`errors_total: 0`)
- `sase instructions verify -a research.12.grk` and `-a research.12.cld`
- `sase instructions render -p` (exit 0); `sase instructions render -a research.13.grk -s`
- `sase doctor -D -C instructions`
- `sase flag list` (only `artifacts_agent_pane_retired`)
- `sase artifact show` of `plan:202610/e3_explicit_delivery_cutover.md` (missing)
- Code: `src/sase/llm_provider/_instruction_boundary.py`, `grok.py` `_grok_rules_text`,
  `muse_provider.py` `--trust-workspace`, `src/sase/core/artifact_file_defaults.py`,
  Agents-tab MEMORY lane / `open_artifact_files` / copy-target `artifacts_dir`
- Docs: `docs/instruction_bundles.md`, `docs/agent_providers.md` "Instruction delivery"
  / "Verifying instruction delivery", `docs/memory.md` `instruction_snapshot`
- This run's `$ART/instructions/00-grok.{md,json}` and `agent_meta.json`
- Grok `final_submission.json` scan of `~/.sase/projects/*/artifacts/ace-run/202610/**`
  (non-research, excluding monitor/plan/gate members)
- Memory: `sase_flags.md`, `glossary:agent-instruction-file`, `glossary:agent-tab`,
  `glossary:agent-data-deck`, `glossary:prompt-stash`
)
