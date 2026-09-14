# SASE scheduler and TUI terminology critique

## Executive judgment

The motivation is sound, but the proposed set should not be applied literally as one
global search-and-replace.

Two changes are clear improvements: make `sase tui` the canonical command and replace
the unexplained product acronym **ACE** with **SASE TUI**; replace **chop** with **job**
in the public model. Both make SASE easier to discover and explain. The current docs
must expand ACE to “Agentic Change Explorer” before saying that it is the terminal UI,
and the current Axe guide already defines a chop as “a single script-only job
unit.”^1,2 The proposed words remove translation work from every new reader.

Two changes need adjustment. **Routine** is a weak replacement for **lumberjack**
because it does not say that the object is a supervised, independently scheduled
grouping process; it can just as easily describe the job itself. **Schedule** is a
reasonable compact tab label only if the tab is narrowed to schedule editing. The
present tab is an operations surface: it shows scheduler health, process state, logs,
job history and manual execution, plus background commands that are explicitly not
scheduler-owned.^3 **Automation** is the more accurate tab label.

The recommended public vocabulary is therefore:

> The **SASE scheduler** runs **jobs** in independently supervised **lanes**. Each
> execution is a **job run**. Operators inspect it in the **Automation** tab of the
> **SASE TUI**, launched with `sase tui`.

Make that vocabulary change, but stage it. Preserve old CLI spellings, configuration
keys, serialized fields, artifact identities and storage paths as compatibility inputs
until there is an explicit migration story. Do not rewrite historical changelog entries
or commit scopes.

## What the names describe today

The current architecture is more specific than the proposed four-word substitution
suggests:

| Current term | Actual role | Important distinction |
| --- | --- | --- |
| ACE | The main interactive terminal UI, but also the name of a large Python namespace containing Patch, query, hook and scheduler code | The brand and the package boundary are not equivalent |
| AXE/Axe | A background automation subsystem with an orchestrator, independently supervised loops, event/time triggers, state, health and manual controls | It schedules work, but not all work is purely calendar-scheduled |
| lumberjack | One supervised scheduler process with its own interval, state, metrics and set of chops | It is both a cadence group and a process-failure boundary |
| chop | One configured script-only automation definition, with trigger/guard/timeout/dedupe policy and zero or more runner-executed launch proposals | The definition is different from an individual run |

That model is stated in SASE’s own canonical glossary and Axe guide.^2 It is also
encoded as a public configuration and wire hierarchy:
`axe.lumberjacks.<name>.chops.<name>`. The Rust core treats `axe`, `lumberjacks`, and
`chops` as exact key segments, and exposes selector kinds and status fields with those
names.^4,5 These are contracts, not merely prose.

The same caveat applies to ACE. The visible command is registered as `ace`, the startup
tab ID includes `axe`, and the configuration has separate `ace:` and `axe:` roots.^6,7
Meanwhile `src/sase/ace/` contains much more than Textual presentation: Patch models,
query engines, hooks, persistence, actions and an older scheduler namespace all live
there. Renaming that whole package to `sase.tui` would make the code less accurate, not
more.

## Naming criteria

The best vocabulary for SASE should satisfy five tests:

1. **Discoverable without prior lore.** A reader should infer the purpose from
   `sase --help`, a tab title, or a configuration path.
2. **One noun per level.** The subsystem, cadence grouping, work definition and
   execution need different names.
3. **Accurate across time and event triggers.** The subsystem supports fixed intervals,
   filesystem triggers, guards, manual runs and target fan-out, not just a calendar.
4. **Stable at external boundaries.** CLI tokens, YAML, environment variables, JSON,
   artifact references, executable prefixes and on-disk paths need deliberate
   compatibility.
5. **Consistent with adjacent tools.** Familiar scheduler vocabulary reduces the amount
   SASE must teach.

The readability case against ACE and AXE is strong. Microsoft’s style guide warns that
unfamiliar acronyms harm clarity and findability and specifically recommends not
creating acronyms from product or feature names.^8 ACE has an expansion; AXE appears to
function mainly as a paired metaphor. Neither tells a first-time reader “terminal UI”
or “scheduler.” Their distinctiveness and grepability are real advantages, but those
advantages primarily benefit maintainers who already know the system.

## Critique of each proposed rename

### `sase ace` to `sase tui`: make this change

`sase tui` is direct, predictable and consistent with what the command launches. The
current `sase ace` help text—“Interactively navigate through Patches matching a
query”—also understates a UI that now manages agents, artifacts, notifications,
configuration and automation.^6 The command has outgrown the Agentic Change Explorer
expansion.

Use **SASE TUI**, not “sase’s TUI,” as the canonical short name. The proper-name form is
cleaner in headings, UI copy and technical prose; the possessive form becomes awkward
in constructions such as “sase’s TUI’s Automation tab.” On first reference in broad
documentation, write “SASE terminal UI (TUI),” then “SASE TUI” or “the TUI.”

The old command should remain as a hidden or visibly deprecated alias for at least one
normal compatibility window. `sase ace` is embedded in docs, scripts, generated shell
completion, personal aliases, demo tapes and operational instructions. The linked
dotfiles checkout alone contains shell aliases, snippets, completions and configuration
copy that invoke it. The canonical docs can change immediately while the parser accepts
both tokens.

Do not mechanically rename every `sase.ace` import. First split the package by
responsibility. Presentation-only code belongs under a TUI namespace; Patch/domain
models and query or hook logic need neutral homes. A compatibility package can
re-export moved APIs. Treat `ace-run` as a separate storage migration: the Rust core
explicitly calls it a public workflow name and scans both flat and sharded paths.^9 A
future neutral name such as `agent-run` is better, but changing it safely requires
dual-read/one-write behavior, index compatibility and retention-tool coverage.

### AXE references to “SASE scheduler”: make the public change, not a blind internal rename

Calling the subsystem the **SASE scheduler** is clearer than AXE. Use that as a proper
product noun, rather than spelling the phrase possessively on every mention. In prose:
“The SASE scheduler starts automatically,” “scheduler health,” and “restart the
scheduler.” When implementation detail matters, “scheduler daemon” and “orchestrator”
remain useful.

However, if `sase axe`, the `axe:` YAML root, `--no-axe`, `SASE_AXE_*`, and an **AXE**
tab remain visible, prose-only replacement creates two names for one system. A coherent
public rename should eventually offer `sase scheduler`, `scheduler:`,
`--no-scheduler`, and `--restart-scheduler`, with the Axe forms accepted as compatibility
aliases. Conversely, internal module names can remain temporarily if they are hidden
implementation details.

“Scheduler” is slightly narrower than the implementation. Some jobs are triggered by
filesystem changes, some use periodic backstops, and jobs can be run manually. That is
not disqualifying—modern schedulers routinely combine time, event and manual triggers—but
docs should introduce it as “the background automation scheduler,” not imply that it is
only cron.

### AXE tab to Schedule: improve the label, but prefer Automation

**Schedule** is much better than an unexplained acronym. It is short and works visually
beside **Agents** and **Artifacts**. But it names a timetable, while the current tab is a
live operational console. Its sidebar contains scheduler lanes and jobs as well as a
separate “commands” group; its controls start and stop the daemon, show health and
metrics, inspect output, edit configuration, and manually rerun work.^3 The tab does not
primarily present a calendar or a “next run” schedule.

Prefer **Automation**. It covers scheduled jobs, event-driven jobs, manual execution,
daemon operations and background commands. Prefer **Scheduler** if the tab is later
narrowed to scheduler-owned state. Use **Schedule** if a future redesign centers on
editing cadence and seeing upcoming runs.

A label-only first step is low risk: change the displayed label while retaining the
internal tab ID `axe`, saved startup value `--tab axe`, CSS IDs and keymap group. A
later compatibility release can accept `--tab automation` and canonicalize it to the
same internal tab.

### lumberjacks to routines: do not choose this as the canonical term

**Routine** conveys recurrence, but not grouping, isolation or supervision. “A routine
runs jobs” is grammatically plausible, yet a user can reasonably ask whether the
routine is the script, the recurring schedule, or the worker process. It also hides the
important fact that hooks, waits, checks, comments and housekeeping are independent
failure and cadence domains.

**Lane** is the best fit for the current object. SASE’s own default descriptions already
call these groups “lanes”—for example, the hooks entry is a “Fast lane,” while comments
and housekeeping are described as separate placements.^7 A lane groups jobs that share
a cadence and supervision boundary without pretending to be the executable work. It
also produces readable UI and CLI copy: “hooks lane,” “lane status,” and
`sase scheduler lane run hooks`.

The main objection is that lane remains metaphorical. If maximal literalness matters,
use **schedule group** in prose and `groups:` or `schedules:` in configuration. Avoid
**worker**: SASE already uses worker for agents and execution capacity, and a lumberjack
is a loop that dispatches several jobs rather than a generic job runner.

### chops to jobs: make this change, with “job run” as a separate term

**Job** is the strongest proposed replacement. It is already the word used to explain a
chop in `docs/axe.md`, and it aligns with adjacent automation systems. Kubernetes
separates a repeating CronJob from the one-time Jobs it creates; GitHub Actions defines
a workflow as an automated process containing jobs, whose steps run on a runner; Airflow
separates a DAG’s schedule from its discrete tasks and runtime instances.^10,11,12 That
common pattern makes “lane owns jobs; each job produces job runs” easy to learn.

There is some overload: SASE uses agents, workflow steps, hook checks, proc shells and
task beads, and “job” can be colloquial shorthand for any of them. The solution is a
precise definition, not another invented noun:

- **job**: a configured scheduler work definition;
- **job run**: one execution of that definition;
- **job script**: its executable implementation;
- **proposed launch**: an agent launch requested by a job result.

Do not call the unit a **task**. SASE already has task beads, and major schedulers use
task for a finer-grained unit inside a workflow. Do not call it a **routine** for the
same ambiguity described above.

## Scale and compatibility risk

A case-insensitive token scan of the primary SASE checkout at commit
`c402a0431722` shows the scale. These are matching lines and files, not a proposed
replacement count: they include tests, fixtures and historical material, and one line
can contain multiple occurrences.

| Token | Matching lines | Files with content matches | Tracked paths whose names contain the token |
| --- | ---: | ---: | ---: |
| `ACE`/`ace` | 19,233 | 3,853 | 4,020 |
| `AXE`/`axe` | 5,661 | 966 | 435 |
| `lumberjack(s)` | 1,427 | 217 | 20 |
| `chop(s)` | 3,062 | 435 | 173 |

The unusually large ACE count reflects the `src/sase/ace/**` and `tests/ace/**`
namespace trees, not just branding. Relevant linked repositories add real downstream
scope:

| Repository | Axe lines/files | ACE lines/files | lumberjack(s) lines/files | chop(s) lines/files |
| --- | ---: | ---: | ---: | ---: |
| `sase-core` | 230 / 28 | 284 / 57 | 255 / 15 | 224 / 23 |
| `sase-telegram` | 15 / 9 | 27 / 6 | 6 / 5 | 48 / 20 |
| `sase-github` | 0 / 0 | 30 / 6 | 0 / 0 | 0 / 0 |
| `sase-nvim` | 0 / 0 | 20 / 8 | 0 / 0 | 0 / 0 |
| `sase-research-artifacts` | 0 / 0 | 4 / 3 | 0 / 0 | 0 / 0 |
| personal `chezmoi` configuration | 261 / 20 | 133 / 51 | 55 / 5 | 77 / 8 |

The Rust-core entries are particularly consequential because SASE’s shared backend
owns exact configuration composition and the schema-version-1 scheduler status wire.
For example, that public JSON contains `lumberjacks` and `configured_chops`, while the
job-result wire exposes `Chop*` types and versioned validation behavior.^4,5 The Telegram
plugin publishes `sase_chop_tg_inbound` and `sase_chop_tg_outbound` console scripts,^13
showing that “chop” is already an extension protocol, not just an internal class name.

## Concise replacement inventory

The following is the complete set of reference *categories* that a coherent rename
must classify. The listed paths and spellings are representative contract roots; an
implementation should generate an exact machine inventory at its chosen baseline.

1. **Visible TUI copy and navigation.** Tab display maps, onboarding/help, command
   palette categories, refresh panels, status badges, editor labels and notifications
   under `src/sase/ace/tui/**`; startup values such as `--tab axe`; keymap/copy-mode
   groups and CSS widget IDs if the internal ID is also migrated; visual goldens under
   `tests/ace/tui/visual/**`.
2. **CLI grammar.** `sase ace`; `sase axe`; `sase axe chop {doctor,list,run}`;
   `sase axe lumberjack {list,run,status}`; daemon lifecycle and maintenance commands;
   `--no-axe`, `--restart-axe`, `--lumberjack`, `--chop-verbose`; parser destinations,
   dispatch branches, help/usage text and generated Bash/Fish/Zsh completions.^6
3. **Configuration.** Top-level `ace:` and `axe:`; `lumberjacks:` and `chops:`;
   `ace.*` TUI preferences; `lumberjack_*`, `chop_*`, `chop_script_dirs`, and
   `verbose_lumberjack_diagnostics`; defaults, JSON schema, layered composition,
   provenance paths, mutation selectors, doctor checks and all user/project overlays.^4,7
4. **Python and Rust namespaces/symbols.** `sase.ace`, `sase.axe`, `sase.chops`,
   `sase.core.axe_chop_facade`; `Ace*`, `Axe*`, `Lumberjack*`, and `Chop*` types,
   functions, constants, modules and imports; the Rust `axe_chop`, `axe_status`,
   `axe_overrun`, and `config::axe` modules and Python bindings. This category must be
   responsibility-split, not globally renamed.
5. **Plugin and executable protocol.** Public `sase.chops` SDK, script discovery prefix
   `sase_chop_*`, built-in entry points in `pyproject.toml`, third-party plugin entry
   points, context/result/report schemas, and the Telegram integration’s scripts and
   documentation.^13,14
6. **Environment and process interfaces.** `SASE_AXE_*`, `SASE_CHOP_*`,
   `SASE_ACE_*`; process command lines; lifecycle sources; operation kind `axe.bgcmd`;
   holder/sender/source values such as `axe` and `ace`; systemd scope/timer names and
   restart/update messages.
7. **Persistent files and machine-readable wire.** `$SASE_HOME/axe/**`, including the
   `lumberjacks/` state tree, locks, logs, journals, desired state, job histories and
   metrics; schema-versioned status JSON fields including `lumberjacks` and
   `configured_chops`; config selector `kind` values; saved tab IDs, caches and
   diagnostics.^5,15
8. **Agent and artifact identity.** `artifacts/ace-run/**`; workflow value `ace-run`;
   `chop:<lumberjack>/<chop>` artifact refs; `.chop.<name>.` agent-name segments;
   `chop` tribe/source/producer labels; `workflow="chop:…"`; `chop_name`,
   `chop_lumberjack`, `parent_chop`, job-run IDs and projected `launched` links.^9,14,16
9. **Observability.** Prometheus names such as `sase_axe_cycles_total`,
   `sase_axe_lumberjacks_active` and `sase_axe_lumberjack_restarts_total`; telemetry
   component labels; log-pack sections, trace/span names, diagnostics and dashboards.^17
10. **Documentation, site and media.** `README.md`; `docs/ace.md`, `docs/axe.md`, the
    CLI/config/plugin/development guides and cross-links; `/ace/` and `/axe/` site URLs
    with redirects; glossary and generated `AGENTS.md`; blog posts; image alt text;
    demo tapes, GIF/MP4 names and generated documentation snapshots.
11. **Tests, CI and developer tooling.** `tests/ace/**`, Axe/job/lane test modules and
    fixtures, import-patching strings, snapshots, smoke scripts, `just` recipes, CI lane
    and artifact names, validators, performance baselines and spellcheck dictionaries.
12. **Downstream repositories and personal automation.** `sase-core`,
    `sase-telegram`, `sase-github`, `sase-nvim`, `sase-research-artifacts`, third-party
    chop packages, shell completions, aliases, snippets and machine-specific YAML in the
    linked dotfiles repository.
13. **Historical references that should not be replaced.** Released changelog entries,
    old commit subjects/links, archived plans/research, compatibility fixtures and
    migration documentation should retain the name that was true at the time. Add a
    terminology note or redirect; do not rewrite history.

## Recommended rollout

### Stage 1: vocabulary and additive command

- Add canonical `sase tui`; keep `sase ace` as a compatibility alias.
- Display **Automation** in the tab bar while preserving internal tab ID `axe`.
- Use **SASE TUI**, **SASE scheduler**, **lane**, **job**, and **job run** in current
  docs and new UI copy. Preserve old names only in compatibility notes.
- Define the mapping once in the glossary.

This stage captures most of the usability benefit without touching persisted identity.

### Stage 2: public scheduler aliases and migration tools

- Add `sase scheduler`, `sase scheduler lane`, and `sase scheduler job`; keep the Axe,
  lumberjack and chop spellings as hidden/deprecated aliases.
- Accept a new `scheduler.lanes.*.jobs` configuration hierarchy. If old and new forms
  coexist, fail with an actionable conflict instead of silently merging ambiguous
  values. Provide an exact-key migration command or preview.
- Add `sase.jobs` and `sase_job_*` discovery while continuing to load `sase.chops` and
  `sase_chop_*` for plugins.
- For machine-readable status, either keep version 1’s serialized keys stable or issue
  a version 2 schema. Deserialization aliases alone are insufficient if old consumers
  read newly emitted JSON.
- Add `job:` as an alias for `chop:` artifact identity before changing anything that is
  published or durable. Preserve resolution of old refs and `.chop.` agent names.

### Stage 3: internal cleanup only where it improves boundaries

- Split the current `sase.ace` package by responsibility before moving the TUI subtree.
- Rename internal Axe/job/lane modules after external compatibility is established,
  not as a prerequisite for the public language.
- If `ace-run` becomes `agent-run`, dual-read both layouts, write only the new layout,
  teach scanners/retention/indexing both names, and offer a reversible migration.
- Retain metric aliases or recording overlap long enough to avoid breaking dashboards.
- Remove public aliases only under the project’s normal deprecation policy and after
  linked plugins and personal configuration have migrated.

## Sources

1. SASE. “[ACE TUI User Guide](https://github.com/sase-org/sase/blob/c402a04317228e8709a5e915e19d36328d7b6615/docs/ace.md#L1-L77).” Source snapshot `c402a0431722`.
2. SASE. “[Axe — Background Automation Daemon](https://github.com/sase-org/sase/blob/c402a04317228e8709a5e915e19d36328d7b6615/docs/axe.md#L1-L49).” Source snapshot `c402a0431722`.
3. SASE. “[AXE sidebar model](https://github.com/sase-org/sase/blob/c402a04317228e8709a5e915e19d36328d7b6615/src/sase/ace/tui/widgets/bgcmd_list.py#L1-L75)” and “[tab display names](https://github.com/sase-org/sase/blob/c402a04317228e8709a5e915e19d36328d7b6615/src/sase/ace/tui/widgets/tab_bar.py#L11-L31).” Source snapshot `c402a0431722`.
4. SASE Core. “[Exact-key AXE configuration composition](https://github.com/sase-org/sase-core/blob/ab68522ac465d11544d48d6881ad1ea0c9f372d3/crates/sase_core/src/config/axe.rs#L1-L135).” Source snapshot `ab68522ac465`.
5. SASE Core. “[Portable AXE runtime status wire](https://github.com/sase-org/sase-core/blob/ab68522ac465d11544d48d6881ad1ea0c9f372d3/crates/sase_core/src/axe_status/wire.rs#L1-L288).” Source snapshot `ab68522ac465`.
6. SASE. “[ACE and Axe CLI parser](https://github.com/sase-org/sase/blob/c402a04317228e8709a5e915e19d36328d7b6615/src/sase/main/parser_ace.py#L23-L240).” Source snapshot `c402a0431722`.
7. SASE. “[Default ACE and Axe configuration](https://github.com/sase-org/sase/blob/c402a04317228e8709a5e915e19d36328d7b6615/src/sase/default_config.yml#L232-L250).” See also [scheduler defaults](https://github.com/sase-org/sase/blob/c402a04317228e8709a5e915e19d36328d7b6615/src/sase/default_config.yml#L903-L932). Source snapshot `c402a0431722`.
8. Microsoft. “[Acronyms — Microsoft Style Guide](https://learn.microsoft.com/en-us/style-guide/acronyms).” Updated August 26, 2024.
9. SASE Core. “[Agent artifact layout](https://github.com/sase-org/sase-core/blob/ab68522ac465d11544d48d6881ad1ea0c9f372d3/crates/sase_core/src/agent_scan/layout.rs#L1-L43).” Source snapshot `ab68522ac465`.
10. Kubernetes. “[Jobs](https://kubernetes.io/docs/concepts/workloads/controllers/job/)” and “[CronJob](https://kubernetes.io/docs/concepts/workloads/controllers/cron-jobs/).” Accessed September 14, 2026.
11. GitHub. “[Workflows](https://docs.github.com/en/actions/concepts/workflows-and-actions/workflows).” Accessed September 14, 2026.
12. Apache Airflow. “[Dags](https://airflow.apache.org/docs/apache-airflow/stable/core-concepts/dags.html).” Version 3.3.1; accessed September 14, 2026.
13. SASE Telegram. “[Console-script entry points](https://github.com/sase-org/sase-telegram/blob/3c479c0ad3a941b256ec28aff360c2c12280bf44/pyproject.toml#L30-L35).” Source snapshot `3c479c0ad3a9`.
14. SASE. “[Chop launch environment](https://github.com/sase-org/sase/blob/c402a04317228e8709a5e915e19d36328d7b6615/src/sase/axe/chop_agents.py#L22-L61)” and “[chop artifact projection](https://github.com/sase-org/sase/blob/c402a04317228e8709a5e915e19d36328d7b6615/src/sase/artifact_links/projection/_chop_agent.py#L21-L70).” Source snapshot `c402a0431722`.
15. SASE. “[Scheduler state paths](https://github.com/sase-org/sase/blob/c402a04317228e8709a5e915e19d36328d7b6615/src/sase/axe/state.py#L1-L43).” Source snapshot `c402a0431722`.
16. SASE. “[Public workflow directory constant](https://github.com/sase-org/sase/blob/c402a04317228e8709a5e915e19d36328d7b6615/src/sase/core/agent_artifact_paths.py#L1-L24).” Source snapshot `c402a0431722`.
17. SASE. “[Axe Prometheus metric names](https://github.com/sase-org/sase/blob/c402a04317228e8709a5e915e19d36328d7b6615/src/sase/telemetry/metrics.py#L202-L242).” Source snapshot `c402a0431722`.

## Recommended names to consider

| Rank | TUI command/name | Tab | Subsystem/CLI | Lumberjack replacement | Chop replacement | Assessment |
| --- | --- | --- | --- | --- | --- | --- |
| **1 — recommended** | `sase tui` / **SASE TUI** | **Automation** | **SASE scheduler** / `sase scheduler` | **lane** | **job**; execution = **job run** | Best semantic coverage and cleanest hierarchy |
| **2 — closest to the proposal** | `sase tui` / **SASE TUI** | **Schedule** | **SASE scheduler** / `sase scheduler` | **routine** | **job** | Understandable, but “routine” is ambiguous and “Schedule” undersells operations |
| **3 — maximally literal** | `sase tui` / **SASE terminal UI** | **Scheduler** | **scheduler daemon** / `sase scheduler` | **schedule group** (`groups:`) | **job** | Clearest prose, but longer and less distinctive |
| **4 — conservative transition** | `sase tui` with `sase ace` alias | **Automation** with internal ID `axe` | Public **scheduler**, internal `axe` | Display **lane**, persisted `lumberjack` | Display **job**, persisted `chop` | Lowest migration risk; good first release |
