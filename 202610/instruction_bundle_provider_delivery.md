# How Agent CLIs Will Receive SASE Instruction Bundles

> **Research query:** How exactly will agent CLI providers receive these instruction
> bundle files? In other words, how will these instructions be loaded into context?
> Builds on
> [E3 readiness and bundle inspection](e3_delivery_cutover_readiness_and_bundle_inspection/e3_delivery_cutover_readiness_and_bundle_inspection.md).

## Bottom line

**No provider will discover or open a bundle file by itself.** SASE renders one bundle
for each provider call. The provider adapter then passes that text through an input the
CLI already supports: a system-prompt file, a config value plus a private home file, a
command-line flag, or a prompt prefix. At the same time it turns off the CLI's native
loading of SASE's own full instruction files, so the content arrives **exactly once**.

| Provider | Explicit channel after E3 | Where it lands in the model's context | Native SASE files switched off by |
| --- | --- | --- | --- |
| **Claude** | `--append-system-prompt-file <artifacts>/instructions/NN-claude.md` | **System prompt**, appended after Claude Code's default prompt. Today these instructions arrive as a user message. | `claudeMdExcludes` (exact absolute paths) in the per-run `--settings` JSON. Auto-memory is also switched off. |
| **Codex** | Split in two:<br>• `-c developer_instructions=…` carries the root-only part.<br>• A private `$CODEX_HOME/AGENTS.md` in the per-run shadow home carries everything else. | • Root part: the **first developer message**.<br>• The rest: a **user message** headed `# AGENTS.md instructions`, before the environment context and the prompt. | `-c project_doc_max_bytes=0`, in SASE-managed projects only |
| **Grok** | `--rules "<full root bundle text>"` | **End of the system prompt**, inside `<human_rules>…</human_rules>` | Nothing new: the workspace stays untrusted, and SASE never passes `--trust` |
| **Muse** | Prompt prefix: `<bundle>` + `--- User Prompt ---` + prompt, sent through the existing 0600 `--prompt-file` | The **first user message**. Muse has no system-prompt or rules flag. | Dropping `--trust-workspace`, **if** the E3.1 spike shows Muse is safe without it. Otherwise Muse stays legacy until E4. |
| **agy, Qwen, OpenCode, plugins** | None in E3. Each is declared `inherits-native` and keeps today's native files. | Unchanged | — (E4 switches agy, with its stub, to a prompt prefix) |

**Today (pre-E3), no agent receives the bundle.** Every root invocation renders one, but
only in **shadow** mode. This agent shows how that looks:

- `SASE_INSTRUCTIONS_FILE` points at its own `instructions/00-claude.md`. That file is
  19,629 bytes, and its manifest says `delivery.status: shadow`.
- Its actual context received `~/CLAUDE.md` and the workspace `CLAUDE.md` as two
  `<system-reminder>` blocks in the first user message.
- Each of those files has its own "SASE Final Declaration" section. That is the 2×
  contract the scoreboard reports.

## How one invocation will work

1. **Render.** `invoke_with_instructions` (`llm_provider/_instruction_boundary.py`)
   compiles a bundle for this provider and purpose (ordinary, declaration recovery, or
   conflict repair). It writes `instructions/NN-<provider>.md` and its `.json` manifest.
   This step already runs today.
2. **Plan.** *(New in E3.2.)* A provider hook returns a `DeliveryPlan` with two slots:
   - `root`: the SASE agent itself;
   - `subagent`: the provider's native helpers.

   Each slot declares a status: `explicit`, `inherits-native`, `inherits-root`, or
   `none`. Each provider gets a `sunset` flag.
3. **Deliver.** The adapter turns the plan into flags, environment, and files (table
   above), and the manifest records `delivery.status` and `channel`.
4. **Fall back atomically.** If the render or the transport fails, that one invocation
   gets **both** legacy delivery and native discovery back, and SASE notifies the user.
   An agent must never start with an empty instruction context.
5. **Verify.** `sase instructions verify` reads the provider's own session record and
   checks that the bundle appears once.

**Scope of one bundle:** one bundle per `provider.invoke` call.

- A recovery or repair follow-up is a new invocation, so it gets a new `NN`.
- Continuation cycles inside one invocation reuse the original bundle. These are
  Claude's `--resume` wait loop and Muse's interrupt and continuation cycles.
- Claude already enforces this. `--system-prompt-snapshot on` is the 2.1.296 default: it
  records the system prompt on the first request and resends it verbatim on every resume,
  even if a later launch passes different text, until compaction. E3.3 records these
  continuations as `inherits_root`.
- Muse wraps the prompt once, at the top of `invoke`. E3.5 must keep the bundle prefix
  there so that a reconstructed interrupt prompt never nests a second copy.

## Provider by provider

### Claude: system prompt instead of a user message

- **Root.** `--append-system-prompt-file` loads the bundle and makes it part of the
  system prompt. On 2.1.296 the flag parses and reads the file at launch (probe:
  `Error: Append system prompt file not found` for a bad path). The bundle already
  contains the "Claude Single-Turn Instructions" section (`pkg.provider.claude`), so the
  separate `--append-system-prompt "$DIRECTIVE"` argument goes away.
- **This is the biggest behavioral change in E3.** Today `CLAUDE.md` arrives as a user
  message. After E3 it becomes system-prompt text that compaction doesn't drop. The
  epic's 7-day watch exists for this change.
- **Helpers.** The root's appended system prompt does **not** reach subagents (verified
  in R-fresh).
  - E3.3 renders a helper bundle: the neutral core plus the helper overlay, with no
    `/sase_final`.
  - It passes that bundle through `--append-subagent-system-prompt-file`, which E1
    already uses for a static template.
  - That channel also reaches Explore and Plan, which get no project instructions today.
  - The PreToolUse guard that denies `sase final` to helpers stays.
- **Suppression.**
  - `claudeMdExcludes` lists exact paths: `~/CLAUDE.md`, the workspace `CLAUDE.md` and
    `AGENTS.md`, and any import target. It must spare `sase/repos/**` guides.
  - Claude 2.1.296's `instructionFiles` setting defaults to loading `AGENTS.md` when
    there is no `CLAUDE.md`. The E3.1 spike must show that excluding one does not pull in
    the other.

### Codex: a developer message plus a home `AGENTS.md`

An offline `codex debug prompt-input` probe on 0.162.1, with a temporary `CODEX_HOME`
and marker text, shows exactly where each part lands:

```
developer  "PROBE_DEV_MARKER root overlay"        ← -c developer_instructions=…  (1st)
developer  <skills_instructions> … <permissions> … <multi_agent_role>You are `/root` …
user       "# AGENTS.md instructions\n\n<INSTRUCTIONS>\n# PROBE_HOME_MARKER …"  ← $CODEX_HOME/AGENTS.md
user       <environment_context> …
user       "hello"                                 ← the prompt
```

- **With `project_doc_max_bytes=0`**, the workspace `AGENTS.md` disappears and the
  home file still loads.
- **Without it**, Codex merges the project file into the same user message under
  `# AGENTS.md instructions for <cwd>`. That is today's double load.
- **How E3.4 splits the bundle.**
  - The root-only overlay (the final declaration contract and the Codex single-turn
    directive) goes into `developer_instructions`. It is small, so passing it as an
    argument is fine.
  - The rest goes into the shadow home's `AGENTS.md`: the neutral core, project memory,
    and the home layer. That file must be written as a private regular file. Today it is
    a symlink to `~/AGENTS.md`.
- **Helpers: `inherits-root`.**
  - Children copy the root's `developer_instructions`, and forks copy its history.
  - The actor-qualified sentence ("only the root agent submits…") is the mitigation.
  - Multi-agent v2 is live: the probe shows `<multi_agent_role>You are /root`. So
    `subagent_developer_instructions` is a possible later helper channel.
  - Risk is low today: the scoreboard shows 0 Codex spawns.

### Grok: one system-prompt rules block

- `--rules` text is appended to Grok's system prompt inside `<human_rules>`.
- A live bob-cli session checked here has a 23 KB `system_prompt.txt` whose last 16 KB
  is that block. It holds E1's stopgap: the directive plus the project `AGENTS.md`.
- E3.4 simply swaps in the full root bundle (~20 KB, under the 120 KiB argv guard).
- `--rules` does not reach Grok subagents, so the helper slot is `none` (4 of 706
  sessions used one).

### Muse and agy: prompt prefixes

- **Muse.**
  - `muse exec` has no system-prompt or rules flag. SASE already prefixes its
    single-turn directive this way (`wrap_muse_prompt`). E3.5 widens that prefix to the
    whole bundle.
  - Native loading comes from `--trust-workspace`, which loads the workspace's rules
    *and skills* as `rules_file` context blocks. So the open spike is whether dropping
    it costs skills.
  - If it does, Muse is declared `inherits-native` until E4 replaces the full
    `AGENTS.md` with a stub.
- **agy.** It has no system-prompt flag and records no session data. It loads
  `GEMINI.md` and `AGENTS.md` natively. It stays legacy through E3. E4 moves it to a
  prompt prefix in its argv prompt, which has a 120 KiB guard.

## Things this research adds

- **Codex's 32 KiB cap does not apply to the home file.** A 45 KB
  `$CODEX_HOME/AGENTS.md` loaded in full, tail marker included, with
  `project_doc_max_bytes=0`. E3.4's "fail loudly over 32 KiB" check is therefore SASE
  policy, not a Codex limit. Keep it as a budget guard, but don't describe it as
  truncation protection.
- **Claude's system-prompt snapshot is now a documented default.** It confirms that a
  resumed Claude conversation keeps its first bundle. One consequence: flipping a
  `sunset` flag affects new conversations, not resumes.
- **The bundle file is read by Claude only.** Every other channel carries the text
  (argument, config value, copied home file, or prompt file). For those providers,
  `NN-<provider>.md` is the record, not the transport. Its 0775 mode is cosmetic but
  still worth fixing.

## Evidence

Checked on apollo on 2026-10-13, against sase `e8ec9cb291`.

- **Code:**
  - `_instruction_boundary.py`;
  - `claude.py` (argv, helper channel);
  - `codex.py` (`_create_shadow_codex_home`, `developer_instructions`);
  - `grok.py` (`_grok_rules_text`);
  - `muse_provider.py` and `_muse_directive.py` (prefix, `--prompt-file`,
    `--trust-workspace`);
  - `agy.py` (print-mode prefix, argv guard);
  - the `instructions/{claude,codex,grok,muse}.py` observers.
- **CLIs:** claude 2.1.296, codex 0.162.1, grok 1.0.52, muse 1.4.7, agy 1.3.4.
- **Live probes:**
  - `codex debug prompt-input` with a temporary `CODEX_HOME`, run with and without
    `project_doc_max_bytes=0`, plus the 45 KB home file;
  - `claude -p --append-system-prompt-file <missing>`;
  - `claude --help` (`--system-prompt-snapshot`);
  - a Grok `system_prompt.txt` `<human_rules>` check;
  - this agent's own shadow manifest and context.
- **Design sources:** the E3 section of
  [the migration epics](memory_built_instruction_migration_epics/memory_built_instruction_migration_epics.md#e3-explicit-delivery-cutover),
  the two-slot table in
  [R-fresh](fresh_clone_bootstrap_and_native_subagent_instructions/fresh_clone_bootstrap_and_native_subagent_instructions.md#delivery-plan-per-provider),
  and
  [R-delivery](sase_md_instruction_delivery/sase_md_instruction_delivery.md#delivery-per-provider).
  No E3 plan or bead exists yet, so these channels are the agreed design, re-checked
  against today's CLIs. They are not shipped behavior.
