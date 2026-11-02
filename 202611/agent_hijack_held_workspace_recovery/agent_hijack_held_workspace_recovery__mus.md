# Agent Hijack ("kill without release"): design research

Researcher: mus · 2026-11-02 · swarm 33 (`__mus`)

Question: how should sase support "hijacking" a stalled agent — killing it
without releasing its workspace or dismissing its row — rendering a new
`HIJACKED` status, and offering an `<enter>` panel with restart / edit /
escalate options?

Short answer: the feature fills a real gap (today every kill path releases the
workspace claim *and* removes the row, so a stalled agent with valuable
in-progress state forces an all-or-nothing choice), and it is implementable
almost entirely by recombining existing machinery (Enter-target resolver +
single-keypress chooser modal + kill/edit/relaunch flows). The one genuinely
new and risky piece is the **retained workspace claim on a dead agent**: every
sweeper in the system (reaper, doctor, auto-restart, relaunch name reservation)
assumes "no process ⇒ claim is releasable ⇒ row is dismissable." A hijacked
row violates that invariant on purpose, so the design must make hijack
*explicit, durable, and self-expiring*, or leaked workspaces will accumulate.
Details and a phased recommendation are at the end.

## 1. How the pieces work today

### 1.1 Agent statuses and buckets

- What the user sees on the Agents tab is a *display label* plus a *bucket*.
  Bucketing is canonical text owned by Rust: `status_bucket_for_status` behind
  the `sase_core` binding, wrapped in Python by
  `src/sase/agent/status_buckets.py:status_bucket_for_values`. Any new
  `HIJACKED` label needs the Rust table, the Python wrapper, docs, and probably
  a visual snapshot update to agree — it is a cross-boundary change (cf. the
  `rust_core_backend_boundary` core-memory note).
- TUI-side predicates live in `src/sase/ace/tui/models/agent_status.py`:
  `DISMISSABLE_STATUSES` (DONE, FAILED, PLAN COMMITTED, PLAN DONE, TALE DONE,
  PLAN REJECTED, EPIC CREATED, STOPPED), `RESUMABLE_DONE_STATUSES`, stopped /
  failed / revertable helpers.
- Crucially, `is_stopped_agent` already honors an **explicit `status_bucket`
  override** (`valid_status_bucket`), exactly like grouping and header counts.
  Precedent exists for a row whose display label is free-form while its bucket
  is pinned (pending custom gates showing `CONFIRM`). A hijacked row could
  similarly carry display label `HIJACKED` with a pinned bucket — no new bucket
  strictly required (see §5.1).
- Full status catalog: `docs/reference/tui/agent-statuses.md`.

### 1.2 `<enter>` is already a context-aware chooser

- Enter handling is a resolver + chooser pair:
  - `src/sase/ace/tui/actions/agents/_agent_enter_resolver.py:resolve_agent_enter_targets`
    resolves ordered targets per scope (gate rows, clan containers, members,
    remote-attention, stranded, Patch-last).
  - `src/sase/ace/tui/modals/agent_action_chooser_modal.py:AgentActionChooserModal`
    is the **single-keypress chooser**: generic view model, deterministic hotkeys
    (`g` for a lone gate, `1`–`9` for several, `p` for Patch), sections
    `gate|patch|archive|read|stranded`.
- The hijack panel should be a new section (e.g. `"hijack"`) in this same modal,
  not a bespoke modal. That buys keyboard behavior, footer guidance, and visual
  consistency for free, and it is the "beautiful" answer: one chooser idiom
  everywhere.

### 1.3 Kill vs. dismiss vs. what hijack needs

`src/sase/agent/running.py` has exactly two terminal paths, and **both release
the workspace claim**:

- `kill_named_agent(name, exact_name=, retain_for_retry=)`: SIGTERM the process
  group, then release the workspace claim (non-home), remove running/waiting
  markers, record dismissal, dismiss notifications. `retain_for_retry` only
  skips the dismissed-agents *index write* — the claim is still released and
  markers still removed. There is **no "kill but keep everything" flag today**.
- `dismiss_named_agent(name, exact_name=)`: for already-done rows; no SIGTERM,
  but likewise releases the claim, drops markers, records dismissal.
- Kill failure modes are explicit and must be respected by hijack:
  `permission_denied`, `survivors` (process still alive ⇒ **claim and markers
  deliberately kept**), `not_found`, `already_completed`, plus the
  stale-state path ("was not running; cleaned up stale state").
- `src/sase/agent/_restart_execute.py:execute_agent_restart` (kill → wipe name
  → relaunch rewritten prompt from the home directory) is the closest existing
  relative of "restart with the exact same prompt," and
  `get_restartable_prompt_content` (`src/sase/ace/tui/models/artifact_files.py`,
  `raw_prompt.md` authoritative with a cached-panel fallback) is the prompt
  source to reuse — do not invent a second prompt-recovery path.

### 1.4 Auto-restart will never fight hijack (good)

`docs/reference/agent-auto-restart.md:88`: "Never restarted: provider errors,
rate limits, auth, **kills and cancels**…" A hijacked (user-killed) agent spends
no auto-restart budget and triggers no healer race. Manual recovery owns the row
after hijack. This removes a whole class of races from the design.

### 1.5 `,x` / `,X` (kill-and-edit) already cover "edit the prompt"

- Leader-mode keymaps (`src/sase/ace/tui/keymaps/mode_keymaps.py:LeaderModeKeymaps`):
  `kill_and_edit: "x"`, `kill_and_edit_last: "X"`.
- `src/sase/ace/tui/actions/agent_workflow/_kill_last_launch.py` and
  `_entry_relaunch.py:prepare_kill_edit_agent_prompt` resolve the exact
  relaunch prompt (including session-role suffixes `--plan/--2/--code`).
- So the panel's "dismiss + edit" option should **delegate to the existing
  kill-and-edit flow**, not reimplement prompt seeding.

### 1.6 Revive is the workspace-preserving continuation precedent

- `AgentRevivalMixin` (`src/sase/ace/tui/actions/agents/_revive*.py`) un-dismisses
  runs (`!R`/`R`), reattaching artifact dirs (`revived_artifact_dir`). The
  escalation option ("smarter model, keep the workspace") is philosophically a
  *revive/continuation*, not a *restart*: the successor needs the old workspace
  **and** ideally the conversation history. The `F` fork-by-name flow (follow-up
  waits for completion, then loads history — see
  `docs/reference/tui/agent-workflows.md` on auto-naming) is the other
  precedent. Escalation should ride one of these, not a fresh launch.
- `docs/guides/recover-interrupted-agent.md` documents the user-visible
  recovery ladder (auto-restart → manual retry → revive). Hijack slots in as a
  new first rung: *deliberate* interruption with state preserved.

### 1.7 Model aliases and the escalation rule

- Exactly five built-in aliases (`@xsmall…@xlarge`);
  `default_model: "@large"`, `epic_lander_model: "@large"`,
  `big_epic_lander_model: "@xlarge"` (`src/sase/default_config.yml:1867-1901`;
  shipped targets live in `src/sase/llm_provider/models.yml`).
- The proposed rule ("`@large` ⇒ `@xlarge`, else `@large`") needs one
  correction: if the previous run already used `@xlarge` (or a custom alias),
  "otherwise `@large`" would *downgrade*. Rule must be max(current, `@large`)
  with `@large→@xlarge`, i.e. never step down (see §4.3).
- Open implementation question: the agent row must record which alias (or
  explicit model) launched it. I did not find a `requested_model` on the TUI
  `Agent` model; the reliable sources are `agent_meta.json` and/or parsing
  `%model` out of the recovered raw prompt, falling back to `default_model`.
  Whichever is chosen, **persist the alias at launch** if it is not already
  persisted — string-parsing prompts at hijack time is brittle (a `%model:`
  line could be quoted, commented, or inherited from a macro default).

### 1.8 Workspace claims: the invariant hijack breaks

- Claims are tracked per project (`get_claimed_workspaces` / `release_workspace`
  in the `running_field` module); the reaper prunes aged entries
  (`default_config.yml` reaper settings), `sase doctor` has workspace checks,
  and names stay reserved until wiped (enabling fork-by-name).
- A hijacked row is "dead process + live claim + visible row." Every janitor
  will read that as garbage: reaper (age-based prune), doctor (stale claim),
  relaunch (name still reserved ⇒ needs `%id:!<name>` force-reuse or an
  explicit wipe-then-relaunch ordering). The design must therefore include:
  (a) a **durable hijack marker** (file alongside the agent artifacts, same
  idiom as `pending_question.json`) so refresh/reboot re-derive HIJACKED
  instead of "cleaning up stale state"; (b) a **TTL/auto-release** so abandoned
  hijacks converge back to releasable (see §6); (c) claim-ledger awareness so
  doctor reports "hijacked (held)" rather than "stale."
- Note the `survivors` precedent in `kill_named_agent`: when the process won't
  die, sase *keeps* claim+markers and reports failure. Hijack must fail the
  same way — a failed SIGTERM must never produce a HIJACKED row over a live
  process.

## 2. Glossary term

The request asks for a new glossary term ("hijack" as working title). Options
considered:

| Candidate | Pros | Cons |
| --------- | ---- | ---- |
| `hijack` / `Hijacked Agent` | User's word; memorable; matches "unstick" vernacular | Hostile connotation (taking from someone); slightly jokey for docs |
| `commandeer` | Precise (take over one's own stalled resource); dignified | Less obvious; still militaristic |
| `reclaim` / `salvage` | Friendly; implies rescuing work | Implies the workspace was lost (it wasn't); salvage ≈ garbage |
| `intercept` | Neutral | Vague; collides with proxy/interceptor language |
| `take over` | Plain | Two words; weak as a status label |

Recommendation: keep **`hijack` (verb) / `Hijacked Agent` (noun, keyword
`hijacked-agent`)** with `commandeer` documented as a synonym, and define it
*against* its neighbors in one breath: "kill ends the process and releases the
workspace; dismiss retires the row; revive un-dismisses; **hijack kills the
process while retaining the workspace claim and the row**." The contrastive
definition is what will stop the term from blurring into "kill." Status label:
`HIJACKED`.

## 3. Critique of the plan as stated

**Is it a good idea? Yes — with adjustments.** The gap is real: today a stalled
agent offers only "wait indefinitely" or "kill (destroying the workspace
context that made the run valuable)." For long implementation runs, the
workspace *is* the asset (exploration, partial edits, test results, conversation
history), and the process is the liability (looping, wedged on a gate/tool,
burning budget). Separating the two is the right primitive. That said:

1. **"Stalled" is a human judgment in this plan, and that is correct for v1 —
   but say so.** There is no heartbeat/idle detector in the tree (only adjacent
   signals: `SLOW TOOL CALLS` rows in clan documents, retry countdowns,
   wait-dependency views). Do not gate v1 on automatic stall detection; it is a
   hard problem (slow ≠ stuck; a compiling agent looks dead for 20 minutes).
   Hijack is a *manual* action on a *suspected-stuck* agent. Optionally show
   "idle-since" (last output/activity timestamp) on the row/panel to help the
   judgment — cheap, read-only, high value.
2. **The workspace-retention half is where all the risk lives** (§1.8). The
   kill half is trivial. Review effort should go 80/20 toward retention
   semantics (claim ledger, marker durability, TTL, doctor/reaper interplay),
   not toward the panel.
3. **Two of the three panel options are already thin wrappers around existing
   flows** (restart-same-prompt ≈ restart/revive machinery; edit ≈ `,x`). That
   is good news for cost, but it means the panel must *delegate*, and the only
   truly new execution path is escalation-with-workspace-adoption. Keep the new
   code surface exactly there.
4. **Escalation as specified ("relaunch with a smarter model into the same
   workspace") is underspecified at the critical point**: a fresh launch
   writes a fresh artifacts dir and claims a workspace; "same workspace" needs
   an adoption mechanism (successor attaches to the hijacked artifacts/workspace,
   ideally as a session continuation so history inherits). Without that, the
   option silently becomes "fresh run that happens to share a directory" —
   risking clobbered state and double-writes. §4.3 makes this concrete.
5. **A HIJACKED row must be un-hijackable without launching anything.** The plan
   lists only launch-or-dismiss exits. If the user hijacks by mistake (or the
   agent was merely slow), the cheapest correct exit is "release the claim and
   dismiss the row" (converge to today's kill outcome) — and arguably "resume"
   (the process is dead, so true resume is impossible; the honest version is
   "adopt as continuation," which is escalation without the model change).
   Missing exits turn a safety feature into a trap.

## 4. The `<enter>` panel, option by option

Frame: reuse `AgentActionChooserModal` with a `"hijack"` section; single
keypress per option; `Esc` cancels; show idle-since + retained-workspace path +
original model in the title/subtitle so the choice is informed.

### 4.1 Restart with the exact same prompt (dismiss + release + relaunch) — keep

- This is `execute_agent_restart` semantics (dismiss old row, release name and
  claim, relaunch rewritten prompt from home). Mostly existing code; the
  hijack-specific bit is only that the starting row is HIJACKED rather than
  RUNNING/DONE.
- Adjustment: after a hijack, the name is still reserved, so relaunch must go
  through the same name-release/force-reuse ordering as restart (wipe-then-claim
  or `%id:!<name>`). Reuse that ordering verbatim; do not add a parallel one.
- Key suggestion: `r` (mnemonic: restart). Check against chooser collisions
  (`g`/`p`/digits are taken by convention; `r` must be audited).

### 4.2 Dismiss + edit prompt (the `,x` flow) — keep, by delegation

- Literally invoke the `prepare_kill_edit_agent_prompt` path and drop the user
  into the prompt bar with the recovered prompt. Zero new prompt logic.
- Note: since the agent is already dead, this is "dismiss + edit," skipping the
  kill step — slightly simpler than `,x`, same destination.
- Key suggestion: `e` (edit). Audit against existing chooser hotkeys.

### 4.3 Escalate to a smarter model, keeping the workspace — keep, redesigned

- Fix the model rule so it never downgrades: if previous alias was `@large` →
  use `@xlarge`; else if previous was already `@xlarge` (or a custom alias at
  or above) → keep it; otherwise → `@large`. One rung up, never down. (Also
  consider carrying the effort suffix up unchanged rather than resetting it.)
- Fix the execution semantics: implement as a **continuation/successor in the
  same session** (the `F` fork / serial-session pattern), launched with the
  escalated `%model`, attached to the retained workspace and history — not as a
  detached fresh launch pointed at a directory. This is the only honest reading
  of "the smarter model needs access to all of the previous agent's file
  changes" *plus* its reasoning context. If session-continuation turns out to
  be too costly for v1, the documented fallback is: new agent, same workspace
  adoption, with the old conversation history injected as context — and the
  panel copy must say so honestly.
- Requires the launch-alias persistence from §1.7.
- Key suggestion: `s` (smarter). Audit hotkeys.

### 4.4 Additional options considered

- **(a) Inspect first: open workspace shell / tmux (recommend: include).** The
  most common real workflow is "is there anything worth saving?" before
  choosing. A read-only-ish peek (workspace path, `tmux`-attach idiom already
  exists: `agent_workspace_tmux_modal.py`) prevents destructive choices. Cheap,
  high value, non-destructive default. Key: `v` (view) or `i` (inspect).
- **(b) Copy prompt to stash (weak include / cut).** Useful but redundant with
  (4.2), which already lands the prompt in the editable bar. Skip unless user
  testing asks for it.
- **(c) Release + dismiss without relaunching — "un-hijack" (recommend:
  include).** Converges the row to exactly what a normal kill would have
  produced (claim released, row dismissed, dismissal recorded). This is the
  mistake-recovery exit and the TTL-expiry behavior made manual. Without it,
  hijack is a roach motel. Key: `x` or `d` (dismiss) — mirrors the existing
  footer idiom.
- **(d) Convert to continuation with the *same* model (cut).** Subsumed by
  (4.3) with "keep model" — but that doubles the continuation code paths for
  no user-visible difference worth a dedicated key. If escalation's continuation
  machinery exists, offering same-model continuation is nearly free; still, keep
  the panel to ≤5 choices. Verdict: only if free.
- **(e) Auto-escalate on stall detection (cut for v1).** No detector exists;
  speculative. Revisit if idle-since telemetry proves predictive.

Recommended panel (4 options + cancel): `r` restart same prompt · `e` dismiss
and edit · `s` escalate (keep workspace) · `v` inspect workspace · `x` release
and dismiss. Plus idle-since + workspace + model context in the header.

## 5. Status rendering and config

### 5.1 Rendering `HIJACKED`

- Display label `HIJACKED`; bucket: pin via the existing `status_bucket`
  override mechanism rather than minting a new bucket, unless the Rust owners
  prefer a first-class bucket (stopped-family: grey? no — hijacked needs
  attention). Color recommendation: **orange/amber** — distinct from gold
  RUNNING, red FAILED, grey STOPPED/DONE; reuse the RETRYING-orange family
  language ("needs attention, action available") but with its own glyph
  (suggest `◈` or `⚓`; avoid `Ø` STOPPED and `↻` RESTARTING collisions; verify
  against the Fira Code pinned-snapshot constraint noted in `agent_status.py`).
- Footer chips for a HIJACKED selection: `enter hijack-menu`, `x release/dismiss`
  — mirroring the conditional-chip idiom in
  `src/sase/ace/tui/widgets/_keybinding_bindings_agents.py`.
- Triggering hijack itself needs a keymap on RUNNING-ish rows. Leader-mode
  audit required: `,x`/`,X` taken, `,h`/`,H` taken (`agent_home`,
  `collapse_fold_by_hint`). Candidates: `,K` (kill family, mnemonic "kill and
  keep") or `,d`-family if free — decide during implementation after the audit;
  do not hard-code in this report beyond the recommendation to stay in leader
  mode near `,x`.

### 5.2 Config fields (keep minimal — two, maybe three)

1. `agents.hijack_retention_hours` (default ~24): TTL for a retained hijack
   claim. On expiry the row auto-converges to released+dismissed (option 4.4c,
   automatic) with a notification. This bounds leaked workspaces and is the
   single most important reliability knob. Without it, every forgotten hijack
   is a permanently reserved name + held workspace.
2. `agents.hijack_escalation` mapping (default `{large: xlarge, default: large,
   keep_xlarge: true}` or equivalent): declarativizes the §4.3 rule so model
   policy changes without code changes. Small, honest configurability.
3. Possible third: `agents.hijack_confirm` (bool, default true): confirm before
   hijacking a RUNNING agent (SIGTERM is destructive). Cheap safety; include if
   it fits the existing confirm-dialog idiom (`confirm_dialog.py`,
   `confirm_kill_modal.py` exist — reuse, do not build).

Explicitly *not* proposed: per-project hijack pools, automatic stall thresholds,
custom HIJACKED colors in v1. Each is a real future, none earns its keep now.

## 6. Reliability notes (what must hold)

1. **Fail closed on kill failure.** `survivors` / `permission_denied` ⇒ row
   stays RUNNING, no marker, no HIJACKED. (Mirrors the existing survivors path
   that keeps claim+markers.)
2. **Marker durability.** Hijack writes a marker into the agent's artifacts dir
   (+ claim-ledger annotation) *before* reporting success, so TUI refresh,
   restart, and reboot re-derive HIJACKED instead of "stale state cleanup."
   Boot reconciliation must know the marker (else the first refresh after a
   restart will "heal" the row away — the exact failure mode to test).
3. **Doctor/reaper awareness.** Doctor workspace checks must classify hijacked
   claims as "held (hijacked, TTL …)" not "stale"; reaper must not prune live
   hijacks (only TTL-expired ones, via the converge path). Both need the marker
   or a ledger flag — coordinate, do not special-case strings.
4. **Name reservation.** Hijack retains the name (row is visible). Restart and
   escalation must handle reservation explicitly (release-then-relaunch
   ordering / force-reuse), reusing restart's ordering.
5. **No double-writer.** While HIJACKED, nothing else may launch into the
   retained workspace. The claim staying held is the mutex — which is exactly
   why the TTL + converge path matters.
6. **Tests to require:** kill-fails-⇒-not-hijacked; reboot-⇒-still-HIJACKED;
   TTL-expiry-⇒-released+dismissed; restart-from-HIJACKED reuses prompt
   (`raw_prompt.md` path); escalation never downgrades model (parametrized over
   prior alias); doctor/reaper classify hijacked claims as held.

## 7. Adjustments to the requirements (explicit list)

- **A1.** "Otherwise `@large`" ⇒ **never downgrade**: `@xlarge` stays
  `@xlarge`; mapping becomes one-rung-up-or-keep (§4.3). Justification: the
  stated rule demotes the strongest runs.
- **A2.** Add **inspect-workspace** (`v`) and **release-and-dismiss** (`x`)
  options to the panel (§4.4a/c). Justification: decide-informed-first, and
  every destructive-ish state needs a no-launch exit.
- **A3.** Escalation executes as a **session continuation with history**, not a
  fresh launch into a directory (§4.3/§1.6). Justification: "access to all file
  changes" without reasoning context is half the asset; fresh-launch adoption
  risks clobbered state.
- **A4.** Add a **retention TTL + auto-converge** config (default ~24h) (§5.2).
  Justification: without it hijack leaks names and workspaces permanently.
- **A5.** Persist the **launch model alias** per agent (§1.7). Justification:
  the escalation rule is unimplementable reliably by prompt-string parsing.
- **A6.** Prefer the **`status_bucket` override + durable marker** over a new
  Rust bucket for v1, pending Rust-owner input (§5.1). Justification: smaller
  cross-boundary change; precedent exists.
- **A7.** Defer **automatic stall detection**; ship manual hijack + read-only
  idle-since display (§3.1). Justification: no detector exists, slow ≠ stuck,
  and the manual primitive is useful regardless.

## 8. Recommended solution

**Phase 0 (contract):** add glossary strand `hijacked-agent` (keep the word
*hijack*, alias *commandeer*); document the kill/dismiss/revive/hijack contrast;
reserve chooser hotkeys (`r/e/s/v/x` pending audit) and the hijack keymap
(`K` in leader mode pending audit).

**Phase 1 (the primitive):** `hijack_named_agent` — SIGTERM path cloned from
`kill_named_agent` with fail-closed semantics, but writes the durable marker,
annotates (not releases) the workspace claim, keeps the row, and records the
launch alias. Boot reconciliation, doctor classification, and reaper exemption
for live hijacks. Plus the TTL converge job (`hijack_retention_hours`).

**Phase 2 (the panel):** `"hijack"` section in `AgentActionChooserModal`
reached via Enter on HIJACKED rows: `r` restart (delegate to restart ordering),
`e` dismiss+edit (delegate to `,x` flow), `v` inspect (existing tmux/workspace
modal), `x` release+dismiss (converge). Header shows idle-since, workspace,
original model. HIJACKED rendering in orange with its own glyph; footer chips.

**Phase 3 (escalation):** `s` — session-continuation successor at one-rung-up
model (`hijack_escalation` mapping), attached to the retained workspace with
history; same-model continuation only if it falls out for free.

**Explicit non-goals for v1:** auto stall detection, fresh-launch workspace
adoption, new Rust status bucket, per-project hijack policy, customizable
colors.

Why this shape: it makes the dangerous new state (dead process + live claim)
explicit, bounded (TTL), and recoverable (release exit), while spending new
code only where no flow exists (the primitive + continuation escalation) and
delegating everything else to the chooser, restart, kill-and-edit, revive, and
confirm idioms the codebase already owns. Intuitive (one menu, five
single-key choices, mistake exit), reliable (fail-closed kill, durable marker,
TTL, doctor/reaper coordination, six named tests), and beautiful (one chooser
idiom, one new color+glyph, context-rich header) — in that order of priority.

