# Instruction bundles: keep explicit delivery, preserve a readable project contract

Independent research by **cdx**, 2026-10-14. Scope: whether to continue or revert the instruction migration around **sase-1ko**, including its later file-retirement roadmap. Code examined at sase commit `508eb963a33d745eba229efc753d5082d58f134a`. This report uses the epic, its approved plan and acceptance artifacts, earlier migration research, implementation code, official provider documentation, and independent local probes. It does not consult the other reports or findings from this swarm.

## Recommendation

**Continue the explicit-delivery architecture, fix its acceptance gaps, and pause the planned removal of substantive, committed project instructions.** The most useful destination is a hybrid: a readable, public project contract in `AGENTS.md`, plus an archived, per-invocation bundle delivered by SASE for managed runs.

The user’s concern identifies a real product requirement: someone browsing a fresh checkout should understand its standing instructions without installing SASE. Bundles improve historical auditability, but a command-only interface does not replace that experience. These benefits do not require deleting `AGENTS.md`.

Three decisions are being conflated:

1. Build and record the effective SASE instruction payload for each invocation.
2. Deliver that payload explicitly and prevent duplicate native loading.
3. Stop committing readable full project instructions and rely on a small bootstrap stub plus local generation.

I support **1**, support **2** subject to the provider-specific acceptance work below, and recommend revising **3**. E3 implements the first two; E4/E5 contain the more consequential file-retirement and interactive-environment changes. Stopping after E3, or changing the E4 design, is a valid outcome rather than an incomplete migration. [S1–S4]

## Direct answers to the concerns

### Are the instructions now opaque?

They are **less visible by default, but more precisely inspectable for a particular SASE run**. Those are different forms of transparency.

Previously, root `AGENTS.md` was a convenient, versioned account of project guidance. It was already generated from memory and templates; the migration did not introduce generation itself. It also was never the entire initial context: home files, adapter directives, provider instructions, skills, and sometimes provider-written memory contributed separately. The old file’s incompleteness does not negate its considerable value as an accessible project document.

Now the compiler joins package, home, and project memory into ordinary Markdown, archives it, and records ordered sections, sources, exclusions, sizes, hashes, actor, provider, and delivery details. A historical bundle can be opened as a file; it is not an opaque database representation. However, finding the correct file requires knowing where SASE puts it or using its CLI. A plain repository browser cannot discover the private runtime archive from `AGENTS.md` alone. [S1, S5]

| Transparency question | Earlier files | Bundles as implemented |
| --- | --- | --- |
| What are this checkout’s standing project instructions? | Easy: open `AGENTS.md` | Still easy today because that file remains; weaker under the planned stub-only future |
| What did agent X’s SASE launcher prepare? | Need the correct historical files and environment | Archived bytes and manifest identify the payload |
| Which home layer and adapter directive contributed? | Reconstruct multiple sources | Sections and provenance expose the composition |
| Did the provider load the payload once? | File existence was insufficient evidence | Transcript observations and markers offer evidence, subject to observer gaps |
| Why was a section absent? | Often implicit in discovery and precedence | Manifest can name shadowing, lifecycle exclusion, or superseded input |
| Did the agent obey the instruction? | Cannot infer from files | Cannot infer from bundle hashes or markers either |

**A stored manifest proves intended composition; a matching stored digest proves byte integrity against that manifest; provider observations support delivery; behavior requires separate evaluation.** These should remain separate claims in both documentation and UI.

### Must a new user or non-SASE agent run a SASE command?

**Today, no command is required just to read the standing project instructions.** This checkout still tracks 20 instruction files: the root and three nested scopes, each with five provider filenames. Root `AGENTS.md` is 18,694 bytes. It remains directly readable and available to native tools. Explicit SASE runs selectively suppress native loading; they do not delete these files. [S2, S6]

**For an exact SASE runtime payload, yes, there is now an additional inspection step**, unless the person already has the archived Markdown path. Use `show` for a historical run and `render` for a fresh preview. Re-rendering today is not a reliable reconstruction of yesterday’s inputs.

**Under the proposed E4 future, a fresh clone would contain a short export stub, not the full runtime instructions.** The roadmap explicitly proposes at most 80 lines, a bootstrap clause, a small Claude shim, and locally generated, gitignored interactive instructions after installation. A newcomer could read the stub without SASE, but would need installation/generation or another published projection to inspect the fuller composed guidance. `instructions export` and `instructions sync` are future roadmap commands, not commands implemented in the CLI inspected here. [S3]

The distinction also matters for non-SASE agents. They should receive repository conventions and build/test guidance automatically, but should not receive SASE root-only turn-ending obligations. A sensible public contract must work for both a human contributor and an ordinary coding agent before SASE is available.

## What changed, and what has not

The compiler reads structured memory units rather than treating each provider’s generated instruction file as the runtime authority. It renders the shared SASE template once, merges repository listings, applies project-over-home shadowing, and selects root/helper/interactive/export overlays. Source memory remains Markdown; the bundle and manifest are generated outputs. The Rust manifest contract and Python composition have an explicit division of responsibility. Plugin and launch layers have reserved identities but do not currently contribute content. [S1, S5]

The provider transport differs:

| Provider | Explicit root delivery | Native suppression / helper treatment |
| --- | --- | --- |
| Claude | `--append-system-prompt-file` | Exact SASE-owned root/home paths excluded; auto-memory off; separate helper bundle plus existing tool guard |
| Codex | `developer_instructions` | `project_doc_max_bytes=0` in SASE-managed projects; SASE home instruction copies omitted from shadow home; helpers declared `inherits_root` |
| Grok | `--rules` | Own explicit rules replace the previous stopgap; memory v2 disabled in the selected design |
| Muse | Prompt prefix | Drops `--trust-workspace`; one prefix reused across continuations; successful live delivery still needs quota-unblocked confirmation |
| agy / other legacy adapters | Native/legacy | The migration is not a universal cutover yet |

The flags are separate, default-on sunset flags. Turning one off restores that provider’s intended E1 delivery path while full native files remain. File removal is therefore a separate operational threshold: E4 must replace native fallback with a proven last-known-good mechanism before deleting its inputs. [S2, S4, S7]

Official documentation supports the general transport choices, but also explains the compatibility cost. Codex discovers a global file and directory-scoped project files, with a default 32 KiB project-doc limit; `developer_instructions` is a separate session configuration field. Claude supports file-based system-prompt additions and native file exclusions. Claude’s ordinary `CLAUDE.md` context arrives as a user message, so moving its text into a system-prompt append changes its instruction role. This is a semantic migration as well as a transport migration. [S8–S11]

## Immediate benefits, with their actual limits

The table enumerates the substantive immediate benefits I found. “Implemented” describes the code capability, not a claim that every live run has passed acceptance.

| Benefit | Why it matters now | Evidence / qualification |
| --- | --- | --- |
| **1. One full SASE contract per root invocation** | Removes duplicate home/project copies of shared SASE policy, reducing competing repetitions and input volume | Acceptance harness observed Claude/Codex going from two native contracts to one explicit contract; no measured dollar or quality gain yet |
| **2. Home/project parity across providers** | Grok and Muse can receive the same home memory layer as Claude and Codex | Selected design and compiler implement this; Muse’s final live observer row was quota-blocked |
| **3. Fresh composition at invocation time** | A memory/template change can affect the next run without waiting for every generated file and shim to be refreshed | Inputs and cache keys drive compilation; the compiler/cache becomes a new correctness dependency |
| **4. A historical record of prepared instructions** | Debugging a failed run no longer requires reconstructing its home tree and generated files by guesswork | Run-specific Markdown, digest, facts, and manifest; `show` supports dismissed agents |
| **5. Explainable inclusion and exclusion** | A missing rule can be traced to shadowing or actor selection rather than unexplained provider discovery | Stable section IDs, provenance, offsets, and reasons are recorded |
| **6. One shared SASE template render** | Common lifecycle and repository rules have one package contribution rather than separate repeated home/project copies | Generated `sase.md` inputs are explicitly superseded; semantic contradictions in differently named notes are not automatically resolved |
| **7. A deliberate helper contract** | Claude helpers need project context without inheriting the root’s final-declaration responsibility | Distinct helper bundle and manifest, with PreToolUse enforcement retained; helper guard originated in E1 rather than E3 |
| **8. Consistent treatment of recovery calls** | Declaration recovery and conflict repair use the same boundary and recording model as ordinary roots | All three purposes route through the instruction boundary when artifacts are available |
| **9. Explicit adapter capabilities** | A provider declares root/helper channels and limits; unknown plugins can remain legacy | Validated plan slots, byte limits, CLI version, fallback reasons, session IDs |
| **10. Controlled foreign-memory contribution** | Runtime knowledge depends less on provider-written memories tied to a workspace or profile | Selected design disables Claude auto-memory and omits Codex memories; loses some useful accumulated context unless deliberately harvested |
| **11. Per-provider rollback** | One broken CLI adapter does not require throwing away the compiler, archive, or other adapters | Four sunset flags; host-specific and temporary while native files remain |
| **12. Observable fallback and delivery drift** | Operators can see reasons and missing/duplicate loads | Deduplicated notifications, `.error.json`, verifier, doctor, coverage; current acceptance still reports matching noise |
| **13. Quantified context size** | Growth is visible by layer/section before it silently consumes more context or hits a slot cap | Byte counts and rough token estimates; budgets are diagnostic, not enforced general gates |
| **14. Content-addressed storage and warm render caching** | Repeated invocations can reuse compiled content and avoid unnecessary recomposition | Two local warm previews reported 90.1 and 119.6 ms; these are observations, not a new p95 measurement |
| **15. Cross-provider comparability** | The shared instruction core can be compared independently of adapter-specific directives | `common_digest` excludes provider-specific sections; equal digests do not guarantee identical model behavior or priority |
| **16. Codex state isolation improved in the same work** | An allowlist avoids linking shared SQLite/history state into disposable homes | A useful bundled fix for `sase-11s`; it can be retained independently of explicit instruction delivery |

The strongest immediate reasons to retain E3 are **delivery consistency, historical debugging, and root/helper separation**. The file-retirement benefit is absent from this list because E3 has not retired those files.

The earlier E1 stopgaps already repaired important harms. The E3 plan reports Grok’s final-declaration misses improving from about 14% to about 5% during the stopgap period. That improvement should not be credited to E3 bundles. E3 needs its own post-cutover behavioral evidence. [S2]

## Long-term benefits and what each depends on

| Potential benefit | Dependency / sober assessment |
| --- | --- |
| **Less generated Git churn and fewer merge conflicts** | Comes from retiring or shrinking tracked projections, not from explicit delivery alone. I counted 89 commits touching root `AGENTS.md` from 2026-08-15 through 2026-10-14. This differs from the earlier roadmap’s historical 112/60-day figure and should not be treated as a matching reproduction. Commit count is an exposure measure, not measured engineering time saved. |
| **Fewer provider shim copies to maintain** | Simplifying five byte-identical root files is useful. Keeping one substantive `AGENTS.md` with thin compatibility shims achieves much of this benefit without hiding the public contract. |
| **Cleaner non-SASE and interactive sessions** | Neutral overlays can exclude SASE root lifecycle text. Fleet/home rollout and globally deployed skill text still need compatible treatment; bundles alone do not finish this work. |
| **Better TUI instruction visibility** | A manifest can power an “instructions as launched” view, section provenance, current-vs-run diffs, and memory-consumption views. E6 is optional in the original roadmap; basic discoverability should become a prerequisite if readable files are reduced. |
| **Targeted context and budgets by audience** | Facts and stable sections provide a foundation for conditional density and budget ratchets. General `when:` audiences and matrix checks are E7, conditional on measured use cases. They are not current savings. |
| **Faster diagnosis of memory effectiveness** | Joining manifests, audited memory reads, and outcomes can identify unnecessary density or missing triggers. Reads show consultation, not comprehension or compliance. |
| **More reproducible provider comparisons and experiments** | Payload digests distinguish instruction changes from provider changes. Proper causal tests still need comparable tasks, models, tool policy, and launch versions. |
| **A consistent contract for future frontends/providers** | Rust-owned wire validation and adapter slots can support CLI, editor, web, and other launchers. Do not claim a finished non-Python compiler: composition is currently Python. |
| **More deliberate source ownership** | Package policy, project conventions, home preferences, and provider mechanics can evolve independently. Source ownership is clearer only if manifests and public projections explain the resulting order. |
| **A safer publishing boundary** | A purpose-built public export could omit personal instructions and runtime lifecycle rules. Current `mode=export` does not yet fully remove home configuration metadata; see the independent finding below. |
| **Less dependence on incidental cwd/ancestor discovery** | Explicit managed-run delivery stabilizes the full SASE layer across workspace locations. Native nested instructions, foreign rules, provider updates, and target-host code still influence the complete context. |
| **Reliable fallback after generated-file retirement** | A last-known-good store could preserve availability when composition fails. This is future work and an added maintenance obligation, not a present advantage over the existing native fallback. |

These options strengthen the architecture’s future usefulness. They do **not** justify implementing every optional feature. In particular, defer audience machinery until real instruction density and usage data demonstrate a need.

## Costs and risks that should affect the decision

**Discoverability and bootstrap cost.** A repo browser, offline reader, GitHub reviewer, or ordinary coding agent benefits from a substantial standing document. Requiring the project tool to explain the project introduces a circular dependency precisely when installation is broken or unfamiliar. A short stub can be an excellent quickstart, but cannot honestly stand in for the full governing project contract.

**More machinery can fail.** The migration adds compiler/cache correctness, manifests, a Rust binding contract, observer parsers, transport settings, CLI compatibility, flags, temporary files, and fallback state. Native instruction loading had fewer SASE-maintained components. The code inspection found concrete edges below, so this is an observed engineering cost rather than a hypothetical objection.

**Role and precedence change.** Claude’s system-prompt append and Codex’s developer channel place project-derived content differently from ordinary native project documentation. This may strengthen intended rules, but can also change how project, home, nested, and user instructions resolve. Moving repository content into a higher-priority channel should be an explicit trust decision, especially for projects not wholly controlled by the operator. It is not a substitute for enforcing tool constraints outside the model.

**Native scope compatibility.** Claude’s exact-path exclusions preserve nested guides. Codex’s zero project-doc budget is broad within a managed project; the code’s managed-vs-unmanaged check does not itself prove preservation of every nested instruction scenario. Exercise agents launched under a nested scope and agents opening linked repositories. Do not equate “only SASE-managed projects are suppressed” with “only one owned file is suppressed.” [S7–S10]

**Larger distribution of personal context.** Sharing the home layer with more providers is an approved decision, not a free parity improvement. Runtime bundles and manifests can contain private instructions and source metadata; public project documentation must use a separate, tested export. Per-invocation bundle files are 0644, while temporary transport files are private; archive-directory permissions and publication policy therefore matter. [S1, S2]

**Evidence gaps.** A marker can survive even if a provider changes how it interprets surrounding content. Archived byte integrity is not proof of complete provider context, and a bundle is not the whole provider system prompt, tool policy, skill catalog, later file reads, or conversation. Observers need to distinguish absent evidence from proven absence. `verify` may exit 0 while reporting problems; automation must inspect results rather than treating a successful command exit as a green delivery verdict. [S1, S12]

**No automatic prompt-quality improvement.** The independently rendered Codex root bundle was 20,038 bytes, about 5,013 estimated tokens. Changing the transport does not make those instructions shorter, clearer, or better followed. Grok/Muse gain context, so they may consume more input. Duplicate-contract savings cannot be extrapolated to “half the prompt cost.”

**Remote and installed-code differences.** Dispatch renders on the execution host with that host’s installed code. A local checkout preview is not evidence for a remote run. The acceptance artifact itself records different primary/workspace versions. Historical `show` is more trustworthy than fresh `render` for answering what was prepared for a particular run.

## Independent checks and concrete acceptance findings

### What I verified directly

- `git ls-files` finds **20 tracked instruction files**, totaling **129,985 bytes** across the four scopes. Storage size is trivial; the relevant cost is duplicated review/maintenance.
- `sase instructions render -f provider=codex -p` exits 0 with `contract_count=1` and five additional frame/provider sections. This is structural parity, not a byte-for-byte semantic equivalence proof.
- Root preview: SHA-256 `49526658010c050fd544e4679f4c7405b8be85597724c4d0446d8832b744387e`, **20,038 bytes**, **329 lines**, **27 included sections**, **3 excluded sections**. Layer bytes: package 5,655; project 13,479; home 246; frame 658.
- `sase instructions show research.1a.cdx -l` resolves this very run as explicit `codex.developer_instructions`, with the same digest and **bytes match**. This demonstrates improved inspectability of a real run’s prepared payload; I did not count a model echo as delivery evidence.
- `sase instructions render -f mode=export,provider=codex -j` selects actor `interactive`, excludes `home.*`, excludes `pkg.root.final_declaration`, and excludes the provider directive. Its bundle is **18,114 bytes**. It remains a full preview, not the planned <=80-line stub.
- No provider/model calls were launched for this report. Successful paid harness rows below come from the epic’s acceptance record; my additional probes exercised local composition and filesystem behavior.

### Finding A: Codex’s fallback does not fully restore the home instruction path

`_codex_home._create_shadow_codex_home` chooses native-home suppression from **the feature flag**, rather than whether this invocation actually has an explicit bundle. Separately, `CodexProvider.invoke` chooses its developer text from the active delivery; without one it uses only the single-turn directive. The instruction boundary directly invokes the provider with no active bundle when `artifacts_dir` is absent, and also proceeds after render failure. [S7]

I reproduced the filesystem consequence using a temporary home containing only a SASE `~/AGENTS.md`, an empty `.codex`, and no active delivery. Calling the production `codex_subprocess_env()` gave:

| Flag | Active delivery | Shadow `AGENTS.md` |
| --- | --- | --- |
| Off | None | Present, symlink to home file |
| On | None | Absent |

The test patched the flag function and HOME/CODEX_HOME to isolate the two cases; it used the real shadow-home implementation, no real user files, and no model. This **demonstrates loss of the home fallback**, not complete loss of project instructions. With the flag on but no explicit bundle, project discovery is not suppressed by the adapter, so project context may still load.

**Required correction:** base shadow-home suppression on actual explicit delivery, and cover render failure, oversize fallback, and no-artifacts invocations end to end. A valid atomic fallback must restore every native input it claims to restore. Retain the useful SQLite allowlist isolation in both states.

### Finding B: export mode still contains home-derived repository metadata

The export manifest has no included `home.*` sections. Nevertheless, the compiled export contains the personal `chezmoi` linked-repository entry and the `(home configuration)` tag. Its `pkg.sase.repos` sources include **package, project, and home**.

The implementation explains why: it merges project and home linked-repo configuration before assembling package sections; excluding the home memory layer does not undo that merge. [S5]

**Implication:** do not publish today’s `render -f mode=export` output under a blanket claim that it is free of personal/home data. A public export needs to filter transitive home contributions too, including package-rendered listings and manifest metadata. This is a design/acceptance requirement for public export, not evidence of a private secret in the specific observed repository name.

### What the existing acceptance record establishes

The record at `file:explicit:294276aba63ff9003d936aaf` reports:

- Claude, Codex, Grok flag-on harness rows: bundle 1, contract 1, home/project/directive present, native-full 0.
- Claude and Codex flag-off rows: two native contracts/full loads.
- Separate Claude helper marker with no root marker. One general-purpose helper’s final-submit attempt was denied; an Explore helper refused without attempting it.
- Muse both states: API 429, so argv/manifest evidence exists but a successful live observer row does not.
- Launch probes pending installation sync at the time of that record.
- Doctor conformance WARN from invocation/session matching pollution.
- Tiny post-cutover behavioral sample: Codex explicit non-research 1 miss out of 3; Grok 0 out of 1. These counts support no reliable quality conclusion.

The epic was in progress at my first read; its acceptance phase subsequently appeared closed while the parent remained in progress. Closing a phase does not erase the documented gaps. The record describes a promising partial acceptance result, not a completed seven-day, all-provider production soak. [S4]

Documentation also lags the code: `docs/instruction_bundles.md` still says Claude/Codex remain legacy, while the inspected adapters and registry enable their explicit plans. The instruction inventory still lists Codex shadow-home suppression as deferred. Resolving that mismatch is part of transparency, not merely documentation polish. [S1, S6, S7]

## Options compared

| Option | What it retains | What it gives up | Assessment |
| --- | --- | --- | --- |
| Revert E1–E3 broadly | Familiar files and native loading | Delivery fixes, observers, per-run bundles, helper protection unless separately restored | Unwarranted from present evidence |
| Disable an affected E3 provider, keep E1/E2 | Native compatibility and diagnostics | That provider’s explicit-delivery benefits temporarily | Reasonable containment if acceptance/fallback defects cannot be fixed promptly |
| Keep E3 and current full files | Runtime consistency plus familiar project inspection | Generated-file churn and some non-SASE lifecycle confusion remain | Best immediate stopping point |
| Keep E3, publish a substantive neutral project contract | Runtime auditability, zero-install readability, correct non-SASE guidance | Some projection maintenance persists | **Preferred destination** |
| Proceed unchanged to stub-only E4/E5 | Maximum reduction of tracked projections | Rich zero-install inspection and simpler native fallback | Defer until transparency and fallback requirements are met |

Keeping a readable generated projection is compatible with a single authored source. Memory/templates remain authoritative; the committed projection is a checked build artifact. The number of files and their audience can change without abandoning plain Markdown as the public entry point.

## A concrete way forward

1. **Finish E3 conservatively.** Fix Finding A; resolve observer/session-matching warnings; prove the nested/linked-repository cases; complete successful live Muse and installed-launch probes when possible. Keep each provider’s rollback available until its own seven-day clean window is actually satisfied. Do not start a missing provider’s soak clock at another provider’s first manifest.
2. **Preserve a public project contract.** Retain substantive `AGENTS.md` generated from project-owned sources, with a short explanation of source locations, generator identity, audience, runtime additions, and historical inspection. Exclude personal home inputs and root-only SASE lifecycle requirements. Use thin provider shims where compatible. Separate size reduction from the delivery migration.
3. **Publish enough to inspect without SASE.** A fresh checkout and the documentation site should expose that project contract and compiler/transport design. If the root must become a compact entry point, link a committed full project projection and make sure native non-SASE tools still load the essential rules automatically. A link that only a human can follow is weaker than an automatically loaded contract.
4. **Make historical runtime inspection obvious.** Show a bundle digest, actor, delivery status, and an openable Markdown/manifest path with each run. Distinguish “prepared,” “observed,” “inherited,” “legacy,” and “unknown.” Make this basic view a prerequisite for removing substantial files; defer the elaborate ledger UI if unnecessary.
5. **Re-scope E4 rather than accepting its file count as the goal.** First prove public export does not transitively include home configuration; prove zero-SASE fresh-clone usefulness; prove last-known-good fallback and older-run inspection. Keep native nested guides until their replacement demonstrates equal rule discovery. A target such as “20 files to 2” is secondary to these behaviors.
6. **Defer E7.** Measure actual density/adherence problems before introducing general audience conditionals. Preserve mandatory read triggers for every actor who can edit the relevant code.

Proceed with the delivery layer if those tests pass. Use a provider-specific disable if they fail. Consider a broader E3 rollback only if sustained evidence shows that adapter/version maintenance, precedence regressions, or launch latency outweigh the consistency and audit value. File transparency on its own is a reason to change the publication design, not to discard per-invocation recording.

## Inspection commands for the user

These commands exist in the inspected implementation:

```bash
# Standing instructions, with no SASE needed
cat AGENTS.md

# Intended current managed-run context
sase instructions render -f provider=codex
sase instructions render -f provider=codex -s
sase instructions render -f provider=codex -p

# Historical prepared bytes and all invocations
sase instructions show AGENT
sase instructions show AGENT -l
sase instructions show AGENT -j
sase instructions show AGENT -H -s

# Observed delivery and behavior-related readout
sase instructions verify -a AGENT
sase instructions readout --since 7d
sase doctor -D -C instructions
```

`render -a AGENT` uses the agent’s facts with **today’s sources**. It does not replace `show`. Inspect verifier/doctor findings, including unknowns and warnings; successful process exit alone is insufficient.

For an emergency rollback of one provider while E3 native files still exist, the approved plan documents `sase flag disable <provider>_explicit_instructions` on each execution host. This report did not change any flags or deployment settings.

## Sources and reproducibility

Internal sources were read through the audited bead/artifact commands where required. Implementation links below are pinned to the inspected checkout, not a moving branch.

- **S1 — Bundle design and CLI documentation:** [docs/instruction_bundles.md](https://github.com/sase-org/sase/blob/508eb963a33d745eba229efc753d5082d58f134a/docs/instruction_bundles.md). Its delivery-status prose is partially stale; source code and recorded probes take precedence for current adapter behavior.
- **S2 — Approved E3 plan and decisions:** `plan:202610/e3_explicit_delivery_cutover.md`, read with `sase artifact read`; [epic sase-1ko](https://github.com/sase-org/sase--beads/blob/main/pages/sase-1ko/README.md), read with `sase bead read sase-1ko -r ...`.
- **S3 — Earlier program roadmap:** `research:202610/memory_built_instruction_migration_epics/memory_built_instruction_migration_epics.md`, read with `sase artifact read`. This is earlier shared input, not a peer report from the present swarm. E4–E7 descriptions in this report are proposals from that roadmap, not claims of implementation.
- **S4 — E3 acceptance record:** `file:explicit:294276aba63ff9003d936aaf`, immutable SHA-256 prefix `a6b69f0124c53afc671d3bb08dedcf8ff5ecd6ab22abb255cea2`; retrieve with `sase artifact read file:explicit:294276aba63ff9003d936aaf "Review E3 acceptance evidence"`. Recorded 2026-10-14 against workspace `d265233491`, primary `8847d07a08`, core pin `a89eac09c29e2f493ef1152c0d6b0f94e3cce51c`; CLI versions Claude 2.1.299, Codex 0.162.1, Grok 1.0.52, Muse 1.4.7.
- **S5 — Composition and section provenance:** [compile.py](https://github.com/sase-org/sase/blob/508eb963a33d745eba229efc753d5082d58f134a/src/sase/instructions/compile.py), [sections_units.py](https://github.com/sase-org/sase/blob/508eb963a33d745eba229efc753d5082d58f134a/src/sase/instructions/sections_units.py), [facts.py](https://github.com/sase-org/sase/blob/508eb963a33d745eba229efc753d5082d58f134a/src/sase/instructions/facts.py).
- **S6 — Current files and inventory:** [AGENTS.md](https://github.com/sase-org/sase/blob/508eb963a33d745eba229efc753d5082d58f134a/AGENTS.md), [instruction_inventory.md](https://github.com/sase-org/sase/blob/508eb963a33d745eba229efc753d5082d58f134a/docs/instruction_inventory.md), plus local `git ls-files`, file-size, and Git-history measurements described above.
- **S7 — Boundary, adapters, flags:** [_instruction_boundary.py](https://github.com/sase-org/sase/blob/508eb963a33d745eba229efc753d5082d58f134a/src/sase/llm_provider/_instruction_boundary.py), [instruction_delivery.py](https://github.com/sase-org/sase/blob/508eb963a33d745eba229efc753d5082d58f134a/src/sase/llm_provider/instruction_delivery.py), [codex.py](https://github.com/sase-org/sase/blob/508eb963a33d745eba229efc753d5082d58f134a/src/sase/llm_provider/codex.py), [_codex_home.py](https://github.com/sase-org/sase/blob/508eb963a33d745eba229efc753d5082d58f134a/src/sase/llm_provider/_codex_home.py), [_claude_instruction_delivery.py](https://github.com/sase-org/sase/blob/508eb963a33d745eba229efc753d5082d58f134a/src/sase/llm_provider/_claude_instruction_delivery.py), [flag registry](https://github.com/sase-org/sase/blob/508eb963a33d745eba229efc753d5082d58f134a/src/sase/feature_flags/registry.py).
- **S8 — Official OpenAI documentation, native instruction discovery:** [Custom instructions with AGENTS.md](https://learn.chatgpt.com/docs/agent-configuration/agents-md), accessed 2026-10-14.
- **S9 — Official OpenAI documentation, injection and project-doc configuration:** [Configuration reference](https://learn.chatgpt.com/docs/config-file/config-reference), accessed 2026-10-14.
- **S10 — Official Claude documentation, native files, role, exclusions, and scope:** [How Claude remembers your project](https://code.claude.com/docs/en/memory), accessed 2026-10-14.
- **S11 — Official Claude documentation, explicit prompt channels:** [CLI reference](https://code.claude.com/docs/en/cli-reference), accessed 2026-10-14.
- **S12 — Archive inspection and conformance:** [show.py](https://github.com/sase-org/sase/blob/508eb963a33d745eba229efc753d5082d58f134a/src/sase/instructions/show.py), [checks_instructions.py](https://github.com/sase-org/sase/blob/508eb963a33d745eba229efc753d5082d58f134a/src/sase/doctor/checks_instructions.py), and [_verify_observers.py](https://github.com/sase-org/sase/blob/508eb963a33d745eba229efc753d5082d58f134a/src/sase/instructions/_verify_observers.py).

The central limitation is elapsed operational evidence: this was investigated on the day of cutover, not after its required soak. The recommendation is strong on architecture and transparency tradeoffs, but conditional on successful provider acceptance and production observation.
