# Are We Ready for E3 (Explicit Delivery Cutover)? And How to See an Agent's Instruction Bundle

> **Research query:** I am considering launching agents to implement the E3 epic
> described in `memory_built_instruction_migration_epics.md`. Am I ready for this work?
> Also, how can I figure out what a given SASE agent's instruction bundle looked like
> (for example, a completed agent on the Agents tab)?
>
> _Researcher: cld · 2026-10-13 · measured on apollo against sase `8959b0e6fc`._

## Bottom line

**Yes, you can write and approve the E3 plan now. Before launching it, the plan needs
four amendments.** E3's two entry gates are met. E1 (`sase-1gu`) closed on 2026-10-06,
seven days ago, and its stopgaps are working. E2 (`sase-1h3`) has shadow-rendered a bundle
for every root invocation since 2026-10-07: 795 manifests, zero render errors, and the
legacy-parity check passes in all three enabled projects. Waiting longer won't add
evidence. The remaining risk is in the plan, so fix the plan.

| E3 entry gate (from the epics report) | Status | Evidence |
| --- | --- | --- |
| E1 landed, at least 3 days of runs | ✅ 7 days | `sase-1gu` closed 2026-10-06 16:05Z |
| E1 readout acceptable | ✅ by my measurement, **⚠ never recorded** | Grok declaration rate went from 37% during the regression to 74% after E1. 177 Claude helper transcripts: helper template in all 177, 0 `sase final` attempts. ([§2](#2-the-e1-readout-nobody-recorded)) |
| E2 parity clean | ✅ | `sase instructions render -p` exits 0 with `contract_count=1` in `sase`, `bob-cli`, and `job` |
| E2 renders on every invocation, fail-open | ✅ | 795 manifests from Oct 7–13, 0 `*.error.json` files; all three purposes appear |
| Warm render within budget | ✅ | cache hit p50 59 ms, p95 188 ms (budget 250 ms) |

**Four amendments to make in the E3 plan** (details in [§4](#4-gaps-to-close-in-or-before-e3)):

1. **Fix the scoreboard before E3 relies on it.** E3's exit criteria and its 7-day watch
   both read `sase instructions verify`. Today that command has three blind spots:
   - It can't see **dismissed** agents. For the last 7 days it found 10 Claude runs,
     while 147 Claude bundles were rendered.
   - It blanks the whole per-section diff (`◌ partial`) for any transcript over 512 KB.
     Every Claude and Codex run I sampled showed `◌`.
   - Its Muse per-purpose coverage rows are miscounted.
2. **Update the plan for facts that changed after Oct 5:**
   - Codex **multi-agent v2** is active in every SASE Codex run. The plan assumed v1
     children.
   - A new **`job`** project adds 5 generated files.
   - Every provider CLI has a new version.
   - Open bug `sase-11s` touches the same shadow `CODEX_HOME` code as E3.4.
   - Claude auto-memory has mostly been cleaned out already.
3. **Record the baseline before E3 changes behavior.** Write down an E1/E2 readout:
   final-declaration rate per provider and memory reads per run. When the flags were
   retired on 2026-10-10 (`sase-1jc`), the E1/E2 flag beads were closed with test
   evidence only. No soak readout exists.
4. **Put your open decisions in the plan's `decisions:` block:**
   - whether to send the home layer to Grok, Muse, and agy (privacy);
   - foreign memory (Claude auto-memory, Grok memory v2): on or off;
   - how long the per-provider `sunset` flags stay;
   - Claude's instructions moving from a user message into the system prompt.

**How to see an agent's bundle (details in [§6](#6-how-to-see-what-an-agents-instruction-bundle-looked-like)):**
run `sase agent show <name>`, or press `%` then `d` on the Agents tab, to get the agent's
artifacts dir. Then open `<artifacts_dir>/instructions/NN-<provider>.md` for the exact
bundle bytes, and the `NN-<provider>.json` file beside it for the manifest. **Until E3
ships, that bundle is shadow-only: the agent never received it.** It actually loaded the
legacy native files. The Agents tab shows the project `AGENTS.md` it loaded through the
MEMORY lane's **`AGENTS.md as launched`** row (`v` hint). `sase instructions verify -a
<name>` shows what the provider's own session record says it loaded.

## 1. Where the migration stands

| Date (2026) | Event | Commit / bead |
| --- | --- | --- |
| Oct 5 | Epics report published (E1–E7) | research `c964178` |
| Oct 5–6 | **E1 landed**: `sase instructions` group, observed-mode scoreboard, Grok `--rules` stopgap, Claude helper template and PreToolUse guard, root-only sentence, decision record `helpers-return-roots-declare`, ownership inventory (`docs/instruction_inventory.md`) | `sase-1gu` (6 phases); `8071b49282` … `9e4b9767d2` |
| Oct 6 | **E2 landed**: manifest wire schema in `sase-core` (pin `fa390362`), Python compiler and cache, shadow render at `invoke_with_instructions`, `render` CLI with `-p` parity, coverage and section diff | `sase-1h3` (7 phases); `ed2a8f78ad` … `66d598d198` |
| Oct 7 12:57Z | First shadow manifest on apollo (deployed by auto-sync) | — |
| Oct 10 | **Every feature flag retired** at your request, including E1's `grok_rules_delivery` and `claude_helper_channel` and E2's `instruction_shadow_render`. The stopgaps and shadow rendering are now unconditional. | `sase-1jc.10`, `2c9f761210` |
| Oct 13 | No E3 plan or bead exists yet (checked `plans/202610/` and `sase bead search`) | — |

The flag rules themselves are unchanged (`sase_flags.md`). A `sunset` flag is still the
right tool for keeping a legacy branch reachable, and the registry and CLI still work.
One unrelated `sunset` flag has been registered since the retirement.

## 2. The E1 readout nobody recorded

The epics report says: *"About 3 days later … read the E1 watch metrics, then approve
E3."* The E1 land agent attached the baseline and after-state JSON (notes #6–#8 on
`sase-1gu`). The flag beads `sase-1gv`, `sase-1gw`, and `sase-1h4` were later closed by
`sase-1jc.10` with test evidence only. I measured the two watch metrics directly.

**Grok final-declaration rate** (finished, non-research root runs; gate, monitor, and plan
handoffs excluded; "declared" means `final_submission.json` exists):

| Period | Claude | Codex | Grok | Muse |
| --- | ---: | ---: | ---: | ---: |
| Aug 25 – Sep 9 (before the Grok regression) | 64% (n=11) | 67% (n=6) | 71% (n=7) | — |
| Sep 10 – Oct 5 (regression) | 76% (n=21) | 35% (n=55) | **37% (n=46)** | 57% (n=158) |
| Oct 6 – Oct 13 (after E1) | n<5 | 38% (n=34) | **74% (n=31)** | 61% (n=85) |

My method differs from the 60% → 26% figures in the epics report, but the direction is
clear: **Grok recovered after E1.** Codex is the outlier at about 38%. That is E3's
baseline to beat, and something to watch: Codex is the second-busiest provider, and E3
moves its contract into a private `$CODEX_HOME/AGENTS.md` plus `developer_instructions`.

**Claude helpers:** 177 subagent transcripts since 2026-10-06 10:00.

- All 177 contain the `# SASE Helper Instructions` marker.
- Six mention `sase final …` text. All six mentions are file contents the helper was
  reading, not tool calls.
- Zero helpers attempted `sase final submit`, `prepare`, `context`, or `defer`, so none
  were accepted.

The template alone keeps helpers from trying, so the guard has had nothing to deny.

**Memory reads per run**, the second E3 watch metric. I joined each project's
`memory_reads.jsonl` to the runs that have manifests, Oct 7–13:

| Provider | Runs | Mean audited reads | Runs with ≥1 read |
| --- | ---: | ---: | ---: |
| claude | 146 | 1.71 | 70% |
| codex | 186 | 1.65 | 89% |
| grok | 103 | 1.87 | 93% |
| muse | 255 | **0.57** | **35%** |
| agy | 26 | 1.12 | 69% |

Muse reads memory about a third as often as the others. E3 gives Muse the home layer
through a prompt prefix, so this is the column where E3 should show the clearest win.
**Attach these tables, or a re-run of them, to the E3 plan as the pre-cutover baseline.**

## 3. What E2's shadow data says about readiness

All 795 manifests written on apollo from Oct 7 to Oct 13:

- **Providers:** muse 318, codex 191, claude 147, grok 106, agy 32.
- **Projects:** `bob-cli` 435, `sase` 308, `job` 51.
- **Purposes:** ordinary 722, declaration recovery 54, conflict repair 18. The
  finalizer follow-up routes are exercised for real.
- **Render cost.** Cache hit p50 59 ms, p95 188 ms, max 413 ms. Cache miss (20%) p50
  681 ms, p95 2.4 s, max 5.1 s. E3 adds no new latency, because shadow mode already pays
  this cost on the launch path. What changes is the impact: after E3, a slow or failing
  render matters, so E3.2's rule "fall back to legacy for this one invocation and notify"
  is load-bearing.
- **Determinism.** 794 manifests produced 56 distinct bundles and 12 distinct
  `common_digest`s, as expected from a few projects × 5 providers × memory edits.
  Re-rendering this run (`sase instructions render -a research.13.cld`) reported
  `bundle matches recorded bb8aa409fd26`.
- **Size.** Bundle `tokens_est` p50 is 4,042 (range 1,738 to 5,254). No truncation, as
  designed. The epics report's ≤1.6k project budget is still an E7 matter.
- **Hosts.** Every manifest says `host: apollo`, and `sase machine list` shows no remote
  machines configured. My evidence covers apollo only.

**Live scoreboard today** (`sase instructions verify --since 7d -n 200`). This is the
state E3 must change, and it matches E1's after-state exactly:

```
provider manifest contract home project directive native-full foreign          helpers
claude   7/7      2×       ✓    ✓       ✓         2×          auto-memory      0 attempts, 0 accepted
codex    25/25    2×       ✓    ✓       ✓         2×          —                0 spawns
muse     12/12    1×       ✗    ✓       ✓         1×          —                —
grok     23/23    1×       ✗    ✓       ✓         0           memory-v2½:False —
agy      2/2      ◌        ✗    ◌       ◌         ◌           —                —
```

This session saw the same thing first-hand. My context holds `~/CLAUDE.md` and the
workspace `CLAUDE.md`, both carrying the SASE Memory, Repositories, and Final Declaration
sections. It also holds Claude's auto-memory instructions, and the nested
`src/sase/ace/CLAUDE.md` loaded when I read a file under that directory. Claude still
gets the contract twice.

## 4. Gaps to close in or before E3

Ordered by how much they would hurt E3.

### G1. The scoreboard can't see dismissed agents (high)

`sase instructions verify` enumerates runs through `listing_snapshot` (`include_hidden=False`,
bounded recent window). Dismissed agents are skipped.

- For the last 7 days with `-n 200`, the scoreboard counted 10 Claude, 36 Codex,
  29 Grok, 14 Muse, and 2 agy runs. Over the same window, 147, 191, 106, 318, and 32
  bundles were rendered.
- `sase instructions verify -a research.10.cld` and
  `sase instructions render -a research.10.cld` both report "no runs found". The agent
  was dismissed on Oct 12, but its artifacts and bundle are still on disk, and
  `sase agent show research.10.cld` resolves it immediately.

**Why it matters for E3:** each exit criterion checks `verify --since <landing>`, and the
7-day watch reads the same command. Whether an agent is dismissed affects whether it is
counted, so the readout is biased. **Fix:** enumerate archived runs too. The
dismissed-archive index (`sase agent search in:archive`, `~/.sase/dismissed_bundles`) and
`sase agent show` already resolve them. Alternatively, walk the manifests.

### G2. One large transcript blanks the per-section diff (medium–high)

`run_index.read_jsonl_capped` caps root transcripts at 512 KB, and `coverage_diff` then
zeroes **every** section when the read was partial. Instructions sit at the start of the
transcript, so the cap rarely hides them. The diff throws them away anyway.

- `verify -a research.12.cld` (Claude) and `verify -a research.12.image` (Codex) both
  show `◌ partial` for all ten fingerprinted sections.
- Grok (`research.12.grk`) shows real 0/1 counts.

E3.6's "each bundle id appears exactly once per invocation" therefore has nothing to
compare against for the two most important providers. **Fix inside E3:**

- put a bundle-id marker in delivered bundles (for example an HTML comment carrying
  `sha256[:12]`);
- treat "found in the prefix" as observed;
- reserve `◌` for "not found and the file was truncated".

### G3. Muse per-purpose coverage is miscounted (low)

`verify -c` attributes all 13 Muse sessions to every purpose row. As a result, the
`conflict_repair` and `declaration_recovery` rows list ordinary sessions as "uncovered".
The ordinary row is correct (13/13). This is cosmetic today. Under E3 it would make the
recovery-route conformance check look red.

### G4. Codex multi-agent v2 is already on (medium)

E3.4 assumes "v1 children copy `developer_instructions`", and the epics report deferred
the v2 helper override "until v2 is enabled". I measured otherwise:

- Every sampled SASE Codex rollout since Oct 1 (CLI 0.159.3 onward, now 0.162.1)
  carries a `<multi_agent_role>` developer message. That message describes v2's
  `spawn_agent` / `followup_task` / `fork_turns`, and says "Full-history forks … inherit
  the parent".
- So a full-history Codex child would inherit the **root** bundle, including the Final
  Declaration contract, which is the same failure E1 fixed for Claude helpers.
- Actual risk is low today: the scoreboard shows 0 Codex spawns, and Codex's own
  `<multi_agent_mode>` text forbids spawning unless instructions ask.

**Amend E3.4 to:**

- declare Codex `subagent: inherits-root`, with the actor-qualified root-only sentence
  as the mitigation;
- add an E3.1 probe of what a `fork_turns: "none"` child receives;
- keep the "Codex helper channel" spike trigger in "What should not be an epic".

### G5. `sase-11s` overlaps E3.4, and its suggested fix would break the scoreboard (medium)

`sase-11s` (READY, bug, medium) reports that `_create_shadow_codex_home` symlinks shared
SQLite state and `sessions/` into each per-run `CODEX_HOME`. E3.4 rewrites the same
function to make `AGENTS.md` a private file.

The bead's suggested remedy is to "let each run start with fresh empty state … sessions
dir". That would put rollouts inside the disposable shadow home, which gets deleted
afterwards. But the scoreboard deliberately reads `real_codex_home()/sessions`. **Either
fold `sase-11s` into E3.4 with the constraint that rollouts must stay readable under
`~/.codex/sessions`, or land it first with that constraint.**

### G6. The inventory grew: a new `job` project (low for E3, matters for E5)

`job` (`gh_bbugyi200__job`, first commit 2026-10-11) is an enabled project with a
generated `AGENTS.md` plus 4 shims. That makes **40** generated files, not 35.
`docs/instruction_inventory.md` doesn't list it. E3 itself is runtime-only and already
covers `job` runs (51 manifests, and parity passes there). Add `job` to E3's parity
fixtures and to E5's scope. (`actstat` no longer appears in `sase project list`; decide
whether it stays in E5.)

### G7. Provider CLIs have moved; spike status

| CLI | Version at the Oct 5 report → now | E3-relevant check today |
| --- | --- | --- |
| Claude Code | 2.1.289 → **2.1.296** | Binary still contains `append-subagent-system-prompt-file`, `append-system-prompt-file`, `claudeMdExcludes`, `autoMemoryEnabled`, `CLAUDE_CODE_DISABLE_AUTO_MEMORY` (strings only; behavior is for E3.1). The subagent flag is still hidden from `--help`. |
| Codex | 0.160.1 → **0.162.1** | **Re-probed offline with `codex debug prompt-input`** in a scratch git repo with a temporary `CODEX_HOME`. Default: both the project `AGENTS.md` and `$CODEX_HOME/AGENTS.md` load. With `-c project_doc_max_bytes=0`, the project doc is gone and `$CODEX_HOME/AGENTS.md` still loads. `-c developer_instructions=…` arrives as the first developer message. **E3.4's Codex design still holds.** |
| Grok | 1.0.46 → **1.0.52** | `--rules` still listed. E1's land evidence already answered E3.1's "does Grok record the rules text" (one `<human_rules>` block in `system_prompt.txt`), so drop that spike. |
| Muse | → **1.4.7** | `--trust-workspace` is still what SASE passes. The "run safely without trust" spike is still open. |
| agy | → **1.3.4** | Still records nothing (`◌`). Declared legacy until E4, as planned. |

**Claude auto-memory:** 19 workspace-keyed memory directories now, only 2 non-empty
(`sase_12`, `sase_16`; 5 files total, none newer than Sep 25), down from 46 and 11 on
Oct 5. The harvest that E3.3's planned `memory` task bead was for is now about five
files. Turning auto-memory off is still worth doing, because it costs prompt tokens and
invites workspace-specific writes.

### G8. Minor items worth a line in the plan

- Shadow bundle `.md` files are created by `os.open(..., O_CREAT|O_EXCL|O_WRONLY)`
  without a mode, so they come out `0775` (executable). The store copy is `0444`.
  Pass `0o644`.
- Manifests keep `observation.status: "unobserved"` forever. Observation is computed
  live by `verify`, so E3.6 shouldn't expect a backfilled field.
- On Oct 13 the Master Gate failed once (`8959b0e6fc`) and then went green. Phases will
  hit the normal `just check` and flake friction, nothing E3-specific.
- Global installs are human-only (`decisions:global-install-is-human-only`). The 7-day
  watch starts when the execution hosts run E3 code (the first manifest whose
  `delivery.status` is no longer `shadow`), not at landing.

## 5. Recommendation

**Write the E3 plan now and launch it after the amendments below.** None of them needs
more calendar time; they are plan edits plus one small phase.

1. **Add a scoreboard-readiness step**, either an `E3.0` phase or the start of E3.1:
   - archive-aware run enumeration (G1);
   - prefix-tolerant section matching and a bundle-id marker (G2);
   - the per-purpose coverage fix (G3).

   This step must land before the provider phases, because their exit criteria read it.
   It also adds `sase instructions show <agent>`, pulled forward from E6: print the
   recorded bundle and manifest for any agent, archived ones included. It is cheap, and
   the soak needs it.
2. **E3.1 spikes:**
   - drop the Grok rules-recording question (answered);
   - keep Muse-without-trust, `claudeMdExcludes` exact paths, and the auto-memory switch
     probe;
   - add a Codex v2 child probe (G4);
   - re-run my Codex `prompt-input` fixture as a test.
3. **E3.4:** fold in or sequence `sase-11s`, and keep rollouts in `~/.codex/sessions`
   (G5).
4. **Baseline:** attach the [§2](#2-the-e1-readout-nobody-recorded) tables, re-run at
   plan time, as the E1/E2 readout. This also closes the gap left when `sase-1jc` retired
   the flags without a soak note.
5. **Decisions block.** E1 and E2 had none, but many recent plans (for example
   `retire_all_feature_flags.md`) put choices in a frontmatter `decisions:` block. Do
   the same here for:
   - home-layer privacy for Grok, Muse, and agy;
   - Claude auto-memory and Grok memory v2: off in SASE runs (recommended: off);
   - how long the per-provider `sunset` flags stay (you retired every flag within four
     days last week, so name the condition in each flag's `--remove-when`);
   - Claude's instructions moving from user-message `CLAUDE.md` into
     `--append-system-prompt-file`.
6. **Scope:** add `job` to parity fixtures (E3) and to E5 (G6).

If you'd rather not add a phase, the lighter path is to launch E3 as written and treat
E3.6 (conformance) as the place where G1–G3 get fixed. The risk is that E3.3–E3.5 can't
prove their own exit criteria for Claude and Codex until E3.6 lands. I would not take
that path.

## 6. How to see what an agent's instruction bundle looked like

### 6.1 "What it looked like" means three different things today

| Question | Where the answer lives | Before E3 | After E3 |
| --- | --- | --- | --- |
| **A. The memory-built bundle SASE rendered for that invocation** | `<artifacts_dir>/instructions/NN-<provider>.md` plus its `.json` manifest | Exists for agents launched since **2026-10-07 12:57Z**. **Shadow only: never delivered.** | The exact bytes delivered |
| **B. What the provider actually loaded** | Launch snapshot (`instruction_snapshot`), the provider's own session record, `sase instructions verify -a` | Legacy files: project `AGENTS.md`/`CLAUDE.md` and home `~/CLAUDE.md` or `~/AGENTS.md` (2× contract for Claude and Codex) | Should equal A (bundle 1×, native 0) |
| **C. What that agent would get if launched now** | `sase instructions render -a <name>` | A fresh compile from **today's** memory | Same |

### 6.2 Step by step for a completed agent

1. **Find the artifacts dir.**
   - **Agents tab:** select the agent, press `%` (copy mode), then `d` to copy its
     artifacts dir. These are the `copy_mode.prefix: percent_sign` and
     `agents.artifacts_dir: "d"` bindings in `default_config.yml`.
   - **CLI:** `sase agent show <name>` prints `Artifacts dir:`. It also works for
     **dismissed** agents, which `sase instructions …-a` can't find (G1).
2. **List the bundles:** `ls <artifacts_dir>/instructions/`. You get one pair per root
   provider invocation:
   - `00-<provider>.md` is the bundle and `00-<provider>.json` its manifest;
   - higher numbers appear for declaration recovery, conflict repair, or fallback to
     another provider;
   - `NN-<provider>.error.json` means that render failed and the invocation went ahead
     anyway.

   `agent_meta.json` → `.instructions.latest` points at the newest manifest.
3. **Read it:**

   ```bash
   A=<artifacts_dir>
   less "$A/instructions/00-claude.md"                         # the bundle, verbatim
   jq '{facts, bundle, delivery}' "$A/instructions/00-claude.json"
   jq -r '.sections[] | [.id, .layer, .status, (.reason // ""), .tokens_est] | @tsv' \
      "$A/instructions/00-claude.json"                          # what was in or out, and why
   ```

   The manifest's `bundle.store_path` points at the content-addressed copy,
   `~/.sase/instructions/bundles/<sha[:2]>/<sha>.md` (read-only, never pruned). Agents
   with the same `bundle.sha256` got byte-identical bundles. If two providers' bundles
   share a `common_digest`, they differ only in the provider section.
4. **Example: this run.** `00-claude.md` holds 19,629 bytes, about 4,911 tokens, and 30
   section rows, 27 of them included. The facts are `actor sase_root`, `mode runtime`,
   `purpose ordinary`, `provider claude`, `project sase`, `host apollo`. Rendering took
   206 ms (`cache: hit`). Excluded rows are labeled with a reason:
   - `home.core.sase` and `proj.core.sase` are `superseded_input`;
   - `pkg.helper.contract` is `overlay`, because this is the root render.

### 6.3 What the agent actually saw (pre-E3)

- **Agents tab:** the agent's SASE CONTEXT / MEMORY lane starts with an **`AGENTS.md as
  launched`** row (`◇`). Its `v` hint opens the pager at the exact launch version, or at
  the stored snapshot when those bytes were never committed (`docs/memory_history.md`).
  This covers the **project root** `AGENTS.md` only, which today is byte-identical to the
  project `CLAUDE.md` shim.
- **Launch evidence:** `agent_meta.json` → `instruction_snapshot` lists every project and
  home instruction file with its git `blob_oid`. Bytes that were never committed are kept
  in `~/.sase/instruction_snapshots/<oid>`. Committed ones can be read with
  `git cat-file -p <oid>` in the owning repo.
- **Provider record:** `sase instructions verify -a <name>` reads the provider's own
  session files. It shows contract count, home, project, directive, native-full,
  foreign, and helpers, plus a per-section intended-vs-observed table. That table shows
  `◌` when the transcript is over 512 KB (G2). The raw files are:
  - Claude: `~/.claude/projects/<encoded cwd>/<session>.jsonl` and
    `…/subagents/agent-*.jsonl`;
  - Codex: `~/.codex/sessions/YYYY/MM/DD/rollout-*.jsonl` (the `# AGENTS.md
    instructions for …` user message);
  - Grok: `prompt_context.json` and `system_prompt.txt`;
  - Muse: `session.jsonl`;
  - agy records nothing.

### 6.4 Gotchas

- **Use the name the Agents tab shows.** For an agent session that handed off, that is
  the member name. `verify -a 7e` found nothing, while `verify -a 7e--plan` worked. The
  manifest's `delivery.agent_name` keeps the launch-time name (`7e`).
- **Dismissed agents:** `verify -a` and `render -a` fail with "no runs found". The files
  are still on disk, so go through `sase agent show` (G1).
- **`render -a` is not a history viewer.** It compiles from the **current project's**
  memory, using only the agent's facts. Run from the wrong project, it misleads:
  rendering the `job`-project agent `research.12.cld` from the `sase` checkout reported
  15 changed sections. Run from the agent's own project with unchanged memory, it
  reproduces the recorded hash (it did for this run). Use it to answer "has anything
  changed since that agent ran?", not "what did it get?".
- **Agents launched before Oct 7 12:57Z** have no `instructions/` dir. Only B applies to
  them.

### 6.5 What E3 and E6 change

After E3, A becomes the delivered bytes, and the E3 exit criterion "re-rendering a
finished agent reproduces its manifest hash" makes the record trustworthy. E6, the
optional TUI epic, adds the in-TUI view: a MEMORY deck (press `p`, then `y`) with
Manifest, Ledger, and Bundle cards, plus an identity-header chip. Until E6, the files
above are the source of truth. The `sase instructions show <agent>` I recommend pulling
into E3 would turn §6.2 into one command.

## Evidence index

**Beads and plans** (audited reads):

- `sase-1gu` (E1, notes #1–#9);
- `sase-1h3` (E2, land note #4);
- `sase-1gv`, `sase-1gw`, `sase-1h4` (flag retirement notes, Oct 10);
- `sase-11s` (shadow `CODEX_HOME`);
- plans `202610/e1_instruction_scoreboard_and_stopgaps.md`,
  `e2_instruction_bundles_shadow_mode.md`, `retire_all_feature_flags.md`;
- `sase bead search` for E3, auto-memory, and instruction (no E3 bead).

**Memory:** `sase_flags.md` and `sase_beads.md` via `sase memory read`.

**Code:**

- `src/sase/llm_provider/_instruction_boundary.py` (shadow render, `O_EXCL` without a
  mode, env export);
- `src/sase/instructions/run_index.py` (`listing_snapshot`, 512 KB cap);
- `src/sase/instructions/verify.py` and `coverage_diff.py` (partial zeroing);
- `src/sase/llm_provider/codex.py` (`_create_shadow_codex_home`, home `AGENTS.md`
  symlink);
- `src/sase/axe/launch_evidence.py` (`capture_instruction_snapshot`);
- `src/sase/ace/tui/widgets/prompt_panel/_agent_memory_versions.py`;
- `src/sase/default_config.yml` (copy-mode keys);
- `docs/instruction_bundles.md`, `docs/memory_history.md`,
  `docs/instruction_inventory.md`.

**Commands run (apollo, 2026-10-13):**

- `sase instructions verify --since 7d -n 200 [-j] [-c]`;
- `verify -a` for `research.12.cld`, `research.12.image`, `research.12.grk`, `7e`,
  `7e--plan`, `research.10.cld`, `bob-cli-78.land`;
- `sase instructions render -p` in `sase`, `job`, and `bob-cli` (each opened with
  `sase repo open`; all trees left clean);
- `render -a research.13.cld` (hash match) and `render -a research.12.cld` (wrong
  project);
- `sase agent show research.10.cld`; `sase agent list -a -j`; `sase project list`;
  `sase machine list`; `sase flag list`;
- `gh run list --branch master`.

**On-disk scans (scripts run outside every repo):**

- all `~/.sase/projects/*/artifacts/*/2026*/*/*/instructions/*.json` since Oct 6:
  795 manifests, aggregated by provider, purpose, project, cache, and render time;
- `done.json`, `agent_meta.json`, and `final_submission.json` across artifacts since
  Aug 25 (declaration rates);
- `memory_reads.jsonl` joined to manifest runs;
- `~/.claude/projects/*/subagents/agent-*.jsonl` since Oct 6 (177 helpers);
- Codex rollouts Oct 1–13 (`multi_agent_role`, `cli_version`);
- `~/.sase/dismissed_agents.json`;
- `~/.claude/projects/*/memory`.

**Provider probes:**

- `--version` for each CLI;
- `claude --help` and strings in the Claude binary;
- `grok --help`, `muse --help`;
- `codex debug prompt-input` with and without `project_doc_max_bytes=0` and
  `developer_instructions`, in a scratch repo with a temporary `CODEX_HOME`.

**Caveats:**

- Declaration rates are my reconstruction: small n before Sep 10, and "declared" means
  `final_submission.json` exists.
- All evidence is from apollo.
- The Claude auto-memory switch and Muse-without-trust behavior were **not** tested;
  they remain E3.1 spikes.
