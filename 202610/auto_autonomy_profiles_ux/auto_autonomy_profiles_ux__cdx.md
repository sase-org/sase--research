# Designing `%auto` around the agent session

**Independent UX research — cdx — 2026-10-08**

The most useful redesign is a small, consistent control surface around the accepted autonomy policy: choose a named profile, see its effects, change it for a clearly identified session, and inspect what it decided. Keep `%auto` terse. Put the power in a profile picker, a shared explanation model, and reliable controls that work from the terminal or a phone.

There is meaningful UX work here. A profile chip alone would improve recognition but leave difficult questions unanswered: Does switching automation off affect the next gate? Did a waiting plan just get approved? Does this choice apply to one turn or its successors? Why is an unattended agent waiting? Did plan approval publish code? These are product behaviors, not decoration.

This report accepts the recommendations in [the supplied autonomy-policy report](auto_directive_autonomy_policy/auto_directive_autonomy_policy.md). Interfaces and commands described below are **proposed**, unless explicitly identified as current. The final section gives the recommended design.

## 1. Method and boundaries

I read the supplied report through `sase artifact read research:202610/auto_directive_autonomy_policy/auto_directive_autonomy_policy.md`, then independently examined the primary checkout, Rust core, and Telegram plugin. I did not read other researchers' reports, transcripts, or findings from this UX swarm.

| Repository | Inspected revision | Scope |
| --- | --- | --- |
| sase | `6828ed3836b8e1d0d7dcbab28e696fc208f444e5` | TUI controls/headers, launch requests, gates, CLI parsers, decision receipts |
| sase-core | `7b3b9aa51876f7435e9b2e8dcfca97dd59529dde` | Directive metadata and completion |
| sase-telegram | `70701a0155bb4c7504ca054bf88dd582812256d0` | Launch/show/list controls, callbacks, durable gate submission, quiet receipts |

I visually inspected `agents_auto_approve_metadata_tale_120x40.png`. This was source research and interface review, not a live reproduction of defects or a usability study. Historical defects and usage figures remain the supplied report's findings; I did not remeasure them. External documentation was checked on 2026-10-08. Usability targets below are goals, not measured results.

Accepted constraints remain intact: explicit gate option IDs; fail-closed validation; config profiles and narrow overrides; project/role/parent ceilings; one live persisted policy; structural session inheritance; agent awareness; audit; and Rust-owned resolution. I do not propose another permissions directive, autonomous sudo/custom-gate approval, or a sandbox implementation.

## 2. The current UX: useful foundations, unclear consequences

| Observation | Source | Implication |
| --- | --- | --- |
| `A` toggles bare `%auto` on eligible active agents without a panel; the enabled-to-disabled footer says `unapprove`. | `src/sase/ace/tui/actions/agents/_approve.py`; `widgets/_keybinding_bindings_agents.py`; `default_config.yml` maps `accept_proposal` to `A`. | Preserve speed. Turning off future automation differs from withdrawing an approval. |
| Headers show `⚡ PLAN`, `⚡ TALE`, or `⚡ EPIC`; rows show `⚡`, `⚡T`, or `⚡E`; help repeats this vocabulary. | `prompt_panel/_agent_display_header_metadata_identity.py`; `_identity_header_compact.py`; `_agent_list_render_agent_prefix.py`; `help_modal/agents_reference_sections.py`. | Tier labels do not explain questions, saving, inheritance, or ceilings. |
| Persistence is queued, with optimistic local fields and rollback. | `_approve.py`, `_set_auto_approve`. | Keep responsiveness; distinguish requested changes from confirmed state. |
| Editor metadata offers colon/bare/plus, three compatibility values, and no keywords. | sase-core `editor/directive/metadata.rs`, `auto` entry. | New profiles need profile-aware completion and diagnostics. |
| Launch requests require explicit approval and already have a preview. | `agent/launch_request_planning.py`; `main/parser_launch.py`; TUI `_notification_launch_approval.py`. | Extend existing review, not another approval layer. |
| Telegram typed prompts use the canonical launcher; launch messages show model/name/workspace/prompt excerpt. Standard buttons are Fork, Wait, Kill, Retry. | Telegram `inbound_handlers/agent_launch.py`. | Add summary and Autonomy button here. |
| Telegram list/show already includes auto badges and an `Auto` detail row. | Telegram `agent_format.py`. | Extend existing visibility; do not claim it is entirely absent. |
| Telegram gate answers have durable submission, revision/fingerprint checks, and later completion delivery. | Telegram `inbound.py`, `submit_gate_response`; `gate_completions.py`; `formatting.py`, `_bound_gate_token`. | Reuse acceptance-versus-completion semantics for policy edits. |
| General auto gates omit ordinary actionable notifications; narrower quiet receipts exist for auto-approved plans with decision definitions. | `notification_gates/service.py`; `adapters.py`, `_post_plan_auto_receipt_best_effort`; `sdd/plan_decision_handoff.py`. | Gap: incomplete coverage and provenance, not zero receipts. |
| Telegram outbound specially accepts quiet decision receipts; ordinary silent notifications are filtered. | Telegram `outbound.py`, `_is_quiet_decision_receipt`. | A digest needs an explicit category; `silent=True` alone is insufficient. |

The screenshot's existing tree/header/content/footer arrangement is coherent but dense. Use one concise header line and an on-demand card within it. A permanent dashboard would compete with the work.

The user needs five answers: before launch, what happens without me; during work, what policy is active; at an interruption, why it asks and what happens if ignored; during edits, what changes and where; after work, what was automatic, omitted, or left waiting. A profile name alone answers only part of this.

## 3. Outside evidence and implications

These are precedents, not proof that this SASE design will perform well.

- Microsoft Human–AI guidance supports clear capabilities, efficient correction/dismissal, explanations, and visible consequences. SASE needs effect summaries and an easy return to manual choices. [Microsoft Research](https://www.microsoft.com/en-us/research/blog/guidelines-for-human-ai-interaction-design/)
- Google PAIR supports contextual explanations, progressive detail, adjustment/opt-out, and minimal demands on attention. Favor a compact card over a permanent rule matrix. [Explainability + Trust](https://pair.withgoogle.com/chapter/explainability-trust/), [Feedback + Control](https://pair.withgoogle.com/chapter/feedback-controls/)
- VS Code places approval selection at chat input, supports session changes, separates approval from sandboxing, and links automatic-approval messages to enabling configuration. Borrow placement, scope, and provenance rather than its tool-permission modes. [Approval UX](https://code.visualstudio.com/docs/agents/run/approvals), [Security UX](https://code.visualstudio.com/docs/agents/run/security)
- Telegram supports inline keyboards/message edits, limits callback data to 64 bytes, and requires acknowledgment to dismiss callback progress. Keep policy server-side, referenced by short revision-bound records. [Inline keyboards](https://core.telegram.org/bots/api#inlinekeyboardbutton), [Callback queries](https://core.telegram.org/bots/api#callbackquery)
- W3C supports meaning beyond color and status messages without focus theft. Useful terminal principles, but not proof of terminal accessibility or WCAG conformance. [Use of Color](https://www.w3.org/WAI/WCAG22/Understanding/use-of-color.html), [Status Messages](https://www.w3.org/WAI/WCAG21/Understanding/status-messages)

**My inference:** use a session control near the work, honest feedback, and explanation on demand. More syntax or a reassuring icon alone will not solve the problem.

## 4. Mental model and vocabulary

Name the control **Autonomy** and saved configuration **profile**:

> Autonomy chooses how SASE handles host checkpoints for this agent session.

Keep `%auto`/`%a` as expert syntax. **Manual** means no automatic checkpoint choices, not read-only or sandboxed execution. The card's coverage line:

> Coverage: host checkpoints. Tool access is configured separately.

Provider coverage belongs in secondary detail when relevant. Avoid repetitive warnings and shields/locks implying wider enforcement.

| Policy value | User wording |
| --- | --- |
| `plan: approve` | Approve tale plans and start implementation |
| `plan: approve_archive` | Approve tale plans, save them, and start implementation |
| `plan: archive` | Save tale plans without starting implementation |
| `epic: approve` | Save epic plans and launch their workers |
| `question: recommended` | Choose recommended answer; use first if none is marked |
| `question: decide` | Let the agent decide and report assumptions |
| `ask` + `on_ask: park` | Wait for your answer |
| `ask` + `on_ask: deny` | Decline the request and report the limitation |
| explicit `deny` | Decline automatically |

Choose Save/Archive consistently with product vocabulary; expanded detail states the VCS side effect. Do not label a compound effect merely approve. Keep `Delivery: draft PR`, derived from finalizers/VCS workflow, separate: plan approval, saving, code commit, and publication are distinct.

| Picker choice | Description |
| --- | --- |
| Manual | You answer host checkpoints |
| `standard` | Automate tales, epics, and questions; other requests wait |
| `attended` | Automate plans; bring questions to you |
| `overnight` | Continue without waiting; report declined requests and assumptions |
| `epic_worker` | Worker policy; nested epic plans need review |

Generate/check descriptions from effective values. Never infer behavior from profile names. Compatibility profiles stay valid in a separate group; role profiles do not top every human picker. Mark configured default; search user profiles.

Use `standard + 1 override`, not anonymous custom. If ceilings apply, show `standard · limited` and the affected kind. Summaries describe effective results. Manual does not remove independent prohibitions or host constraints.

## 5. TUI: compact card, useful picker, fast control

### Launch composer

Add a focusable line near launch settings:

```text
Project: sase          Model: cdx          Delivery: draft PR
Autonomy: attended     tales + epics automatic · questions wait

Implement the requested change ...

[ Launch ]  [ Autonomy… ]  [ Preview ]
```

It reflects parsed, expanded intent. Manual is explicit and subdued. The same picker serves drafts and sessions. Choosing a profile updates the draft through canonical directive machinery; typed `%auto` updates the control. Avoid hidden settings disagreeing with the prompt.

For macro-provided policy, show `From #worker` and its expansion location. Replace a known editable parsed span. If a macro provides a conflicting selector, diagnose it and offer source navigation/removal of conflicting draft input. Never append duplicate `%auto`, guess precedence, or override ceilings. More advanced macro editing can wait.

Fan-out preview groups identical effective policies and lists exceptions: `5 agents: 4 attended, 1 manual`. It does not summarize the swarm from the first segment.

Routine launch retains its existing gesture, with no additional mandatory approval. Bad policy blocks dispatch, highlights the token, and suggests legal values. `launch=allow` explains config-only delegation; `%auto:off` offers Manual migration guidance without activating automation.

### Picker

Searchable list plus resolved effects; stack on small terminals. Selection previews, Apply commits, Escape cancels. Arrow/search/Tab/Enter/mouse work; explanations do not require hover.

```text
Autonomy · session fixer                       [ search profiles ]

Manual                Standard                 Scope: this session
standard  default     Tales     approve + save + implement
attended              Epics     save + launch workers
overnight             Questions recommended, else first
                      Other     wait for your answer
                      If asked  keep request waiting

                      Coverage: host checkpoints
                      [ Overrides… ] [ Why these rules? ]

Pending gates: 1       Existing requests remain for review
                                      [ Cancel ] [ Apply ]
```

Common overrides are plans/epics/questions, with supported kind-specific choices. Privileged kinds show effective outcomes and configuration explanations; unavailable grants have reasons. Save and implement remain separately named effects, even with combined choices.

Include Reset overrides. Defer Save as profile until demand: show config diff and user/project scope, validate, use existing config mechanisms. Applying to a session and saving a reusable profile are separate targets.

### Running sessions

Use `Autonomy: attended` in selected header and `auto:attended` in rows when space permits. Reuse cyan; words identify limitations.

```text
Autonomy: attended + 1 override                 [ Change… ]
Session: fixer · current and successor turns
Tales approve + save · epics wait · questions wait
Inherited by planner → coder → verification
Decisions: 3 automatic · 1 waiting              [ Review ]
```

Lineage explains actual inheritance. Separate children have separate policies; clan/tribe adjacency grants nothing. Label narrower children. Test node/deck views and direct child selection.

At small widths use `auto:attend…` rather than an unlabeled glyph; selected detail retains full name. Hide secondary counters before main identity. No permanent new panel taking space from prompt/result.

### Preserve `A`

Keep accepted fast toggle: active automation → Manual; Manual → configured default. Footer names next action: manual or auto:standard. Pending-input contexts retain `A` answering; Autonomy remains separately reachable from agent actions/help.

A selected turn targets its owning session, named in feedback. `A` does not cycle profiles. Remember previous choice as an explicit Restore attended option without changing Manual-to-default semantics.

After acceptance:

> Manual applied to session fixer. Future checkpoints require your answer.

While pending, keep confirmed profile with changing to Manual. Optimistic local fields must not imply automation has stopped. Failure says change failed, attended remains active, with retry. Avoid unapproved/paused/stopped: tools can still run.

Update default_config.yml, conditional footer, help, and legend together. Do not scatter new default bindings across modes.

## 6. CLI and editor

Keep accepted `sase autonomy list|show|explain`, adding a small session edit and specific-gate explanation. **Proposed** commands:

```sh
sase autonomy list
sase autonomy show attended
sase autonomy explain -a fixer
sase autonomy explain -p '+sase %auto(attended, epic=ask) fix the bug'
sase autonomy explain -g gate-selector
sase agent autonomy fixer
sase agent autonomy fixer -p attended
sase agent autonomy fixer -m
sase agent autonomy fixer -p attended -n
```

| Surface | Contract |
| --- | --- |
| `list` | Profiles/descriptions/default/source |
| `show PROFILE` | Definition/provenance; contextual ceilings identified |
| `explain -a/--agent NAME` | Persisted session policy, scope, revision, overrides, ceilings |
| `explain -p/--prompt TEXT` | Planned effects/fan-out, no dispatch |
| `explain -g/--gate SELECTOR` | Historical policy for settled request; labeled current evaluation for waiting one |
| `agent autonomy NAME` | Read-only session card |
| `-p/--profile` or `-m/--manual` | Explicit single-session edit; mutually exclusive |
| `-n/--dry-run` | Before/after effects and target, no mutation |
| `-j/--json` | Versioned result on applicable commands |

Use short aliases, sorted options/subcommands, excellent examples, Rich tables. Bare autonomy delegates to list via existing convention. Ambiguous selectors return candidates, not recency guesses.

Edits show target, confirmed revision, changed effects, pending-request behavior. Explicit single-session edits need no repeated confirmation. Future batches need explicit target set and preview; never implicit all.

Typed errors distinguish bad input, unsupported override, stale revision, unreachable host, settled target. Unsupported runtime behavior is not advertised. An intended approval never changes executor exit codes.

TUI and macro LSP completion list configured profiles with descriptions/provenance, then supported keys/values. Group compatibility values. Diagnose exact spans using the same Rust metadata/config snapshot as launch.

**Dry-run limit:** macro arguments can run `$(...)`. Static explanation leaves dynamic expansion unresolved, rather than executes shell code while promising a dry run. Exact preview can reuse materialized expansion or explicitly request expansion. Typing/LSP must never run substitutions. This follows from audited macro grammar, not a newly reproduced vulnerability.

## 7. Telegram: session control from a phone

Add Autonomy to existing agent buttons and effective profile to launch acknowledgment and `/show`. Users can inspect/change session policy without syntax or relaunching.

```text
fixer · RUNNING
Autonomy: attended
Tales + epics automatic. Questions wait for you.
Scope: this session and successor turns.

[ Change profile ] [ Manual ]
[ Decisions ]      [ Refresh ]
```

Proposed `/auto fixer` opens the card; `/show fixer` remains discovery. Bot help explains it. No sticky chat mode affecting unrelated prompts: missing `%auto` stays Manual.

Change profile shows paginated choices; tap previews, Apply to fixer commits. This is one intentional commit of reviewed selection, not another approval dialog. Manual is direct with precise acknowledgment. Defer phone override editing; display all rules and use the same host mutation path.

Typed prompts stay direct. Add policy summary to acknowledgment and optional explicit preview flow. Never assume human availability from Telegram delivery.

### Callbacks

Keep full session/host/actor identity, change, expected revision server-side; callback has a short key. Recheck authorization; forwarding a message grants nothing.

Acknowledge promptly and distinguish submitted from applied. Reuse durable operations/later completion. Duplicate taps are idempotent. Old button after TUI edit says settings changed, refreshed, not overwrite. Unreachable host says not applied, last-known profile and timestamp. Do not retry stale edits without revalidation.

Message editing alone may miss the user: callback feedback for quick success, durable reply for delayed completion/failure. Refresh host state. Retire mutation controls for terminal sessions; using profile in a new prompt is separate.

### Notifications

Default to completion digest and on-demand history, not push per auto gate. Pending requests/failures remain actionable per preferences. On-ask deny records decline/limitation, not a fresh approval request.

Generalize existing quiet receipt category/deduplication and aggregate for phone delivery; avoid competing histories. Opt-in per-decision delivery. Muting notifications never changes policy.

```text
fixer · finished with a remaining limitation
Autonomy: overnight
3 tales approved + saved · 2 questions decided
1 launch request declined; extra review was not run

[ Result ] [ Decisions ] [ Autonomy ]
```

Illustrative copy: actual outcome comes from run/task results. Automatically handling gates does not prove task completion; denied steps may leave work incomplete.

## 8. Reliability contracts

The backend must make these true before UI promises them.

| Situation | Required behavior |
| --- | --- |
| Switch to Manual | Persist atomic revision; auto acceptance ordered after it uses new rule; earlier accepted work remains visible/in flight. |
| Edit races auto gate | Defined host ordering determines winning revision; acknowledge already-accepted actions; do not promise cancellation. |
| Two frontends edit | Compare revision, reject stale edit, refresh while retaining draft for re-review. |
| Gate already waiting | No sweep into execution. Normal human answer or explicit per-request reevaluation with effect preview. |
| Gate settled | History only; no reopening/undo/duplicate successor. |
| Config edited/deleted | Keep snapshot, show drift, explicit Compare/Reapply subject to ceilings. |
| Successor starts | Structural current-session inheritance on every route; old prompt/env cannot resurrect automation. |
| Edit during LLM turn | Next host gate uses new policy; next successor awareness updates; no claim the model received context without delivery. |
| Independent child | Own policy/provenance/ceilings; parent edits do not silently rewrite existing children. |
| Role restricts grant | Bad authored escalation fails launch; derived limits show requested versus effective. |
| New plugin kind | Ask default, explicit unattended consequence. |
| Unsupported value | Reject config/launch; runtime mismatch leaves request unexecuted with diagnostic. |
| Remote unreachable | Timestamp last-confirmed state; requested Manual is not applied. |
| Future batch partially fails | Per-target result, failed target retains old policy; no global success toast. |

State sequence: confirmed → submitting → confirmed, or submitting → failed, previous retained. RUNNING can remain RUNNING; autonomy is not a process lifecycle status.

Separate decision and execution:

```text
10:41  tale plan   auto-selected approve + save
       standard · plan=approve_archive · revision 7
10:41  execution   saved; implementation launch submitted
10:42  execution   launch failed; retry available
```

Record actual IDs/effects, historical policy revision/digest/provenance, request identity, human overrides, outcome. Digests belong in details/JSON. Explanation of yesterday's decision uses yesterday's policy, not edited config.

When asking, lead with cause/consequence:

> Nested epic plan needs your answer. This worker profile requires review. It stays waiting until you answer or dismiss it.

Review once and Autonomy are separate. One answer never silently edits policy/profile. Future standing approvals state kind/scope/expiry/ceiling; omit Always allow in v1.

## 9. Beauty: restraint, legibility, stability

- Hierarchy: identity, lifecycle, autonomy; expand matrix on demand.
- Reuse type, borders, focus, cyan. Text carries meaning; amber/red accompany waiting/failure.
- No shields, levels, or autonomy percentages: profiles are not totally ordered.
- Whitespace/aligned labels, not nested boxes. Small layouts stack/scroll, preserving Apply/Cancel/errors.
- Preserve focus on refresh; do not reorder beneath selection or replace reviews with toasts.
- Test contrast, monochrome, no-color CLI, ASCII words, keyboard access; terminal accessibility requires real testing.
- Routine controls show consequences; configuration mechanisms appear only when helpful for explanation/correction.

Wireframes specify structure, not a new theme. A separate visual language would make `%auto` less intuitive in SASE.

## 10. Scope, rollout, evaluation

| Design | Benefit | Cost/problem | Judgment |
| --- | --- | --- | --- |
| Docs/badges | Immediate clarity | Live/pending/phone gaps remain | Necessary, insufficient |
| Picker/summary/Manual/explain/history | Covers launch/control/exception/review | Shared dependable contracts needed | Recommend |
| Full rule editor/phone wizard/dashboard | Maximum exposed controls | Complexity before demand | Defer |
| Learned authority from approvals | Fewer selections | Ambiguous behavior widens authority | Do not build |
| Global unattended/sticky Telegram | Bulk convenience | Surprising unrelated future scope | No implicit mode |
| Countdown/undo approval | Feels controllable | Latency and false rollback promise | Not default |

### Rollout

1. **Truth first:** accepted P0 parsing/live read/inheritance/worker restrictions/doc fixes. UI cannot substitute.
2. **Shared explanation:** policy/revision/provenance/effects, list/show/explain, named header, launch summary, awareness/audit. Reuse receipts.
3. **Daily controls:** picker/overrides, session mutation/race semantics, completion/diagnostics, pending cause, history, Manual. Ship Telegram card/profile change through same path here.
4. **After usage:** Save profile, batches, richer comparison/mobile editing, standing approvals, delegation-budget display. When delegation exists, show remaining/max children and depth; do not infer spend guarantees from runner slots.

Rust owns schema/evaluation/mutation/wire; Python presentation/glue; Telegram renders shared results. Update Rust pin. Separate notification preferences from policy. Old environment-based runners need drain/compatibility; do not advertise reliable live edits on unsupported versions.

### Acceptance scenarios

| Scenario | Evidence |
| --- | --- |
| No directive/inheritance/roles/overrides | Cross-surface agreement; unrelated Manual |
| Bad profile/key, off, duplicate | Corrective error, no dispatch |
| Live `A` | Next gate uses accepted revision; confirmed feedback |
| TUI then stale Telegram | Rejected stale callback, no lost update |
| Edit with waiting plan | No silent approval |
| Edited/deleted config | Snapshot survives; explicit reapply |
| Every successor path | Policy/awareness survive |
| Heterogeneous fan-out | Per-slot preview agrees |
| Auto decision, failed execution | Failure visible; approved ≠ implemented |
| Overnight forbidden/unknown | Correct consequence/limitation, no contradictory push |
| Dynamic macro draft | Static preview/completion no shell execution |
| Small/no-color/phone | Policy/state/effect/action legible |

Run task-based evaluation with Bryan and, if available, another user: launch automatic plans with human questions, predict standard effects, switch Manual, explain nested-epic review, find why an answer was chosen. Ask predictions before clicking; speed can hide incorrect mental models.

Targets: find autonomy unaided, pick common profile in one visit, switch Manual with one deliberate action, distinguish saving/publication, identify stale edits, retrieve decision reason within two navigation steps. Observe surprises/accidents/waiting/notification burden/override use through opt-in evaluation or local audit analysis, not hidden telemetry.

If usage settles on standard plus one profile, simplify top choices while keeping summaries/Manual/explanations/inheritance.

## 11. Source map

Primary input: [accepted report](auto_directive_autonomy_policy/auto_directive_autonomy_policy.md), audited as `research:202610/auto_directive_autonomy_policy/auto_directive_autonomy_policy.md`. Historical figures were not remeasured.

Paths above are relative to the revisions in section 1. Main anchors:

- sase TUI: `src/sase/ace/tui/actions/agents/_approve.py`; `widgets/_keybinding_bindings_agents.py`; `widgets/_agent_list_render_agent_prefix.py`; `widgets/prompt_panel/_identity_header_compact.py`; `widgets/prompt_panel/_agent_display_header_metadata_identity.py`; `modals/help_modal/agents_reference_sections.py`; `src/sase/default_config.yml`.
- sase glue: `src/sase/agent/launch_request_planning.py`; `src/sase/ace/tui/actions/agents/_notification_launch_approval.py`; `src/sase/main/parser_launch.py`; `parser_agent_lifecycle.py`; `src/sase/notification_gates/service.py`; `adapters.py`; `src/sase/sdd/plan_decision_handoff.py`; `docs/macros.md`.
- sase-core: `crates/sase_core/src/editor/directive/metadata.rs`; `crates/sase_core/src/editor/completion/tests/directive_candidates.rs`.
- Telegram: `src/sase_telegram/inbound_handlers/agent_launch.py`; `agent_show.py`; `gate_completions.py`; `src/sase_telegram/agent_format.py`; `inbound.py`; `callback_data.py`; `formatting.py`; `outbound.py`.
- Visual: `tests/ace/tui/visual/snapshots/png/agents_auto_approve_metadata_tale_120x40.png`.
- Audited conventions: `macros.md`, `tui.md`, `cli_rules.md`, `sase_artifacts.md`. No application code, canonical memory, or profile config changed.

External primary sources, retrieved 2026-10-08: [Microsoft](https://www.microsoft.com/en-us/research/blog/guidelines-for-human-ai-interaction-design/); [PAIR explanations](https://pair.withgoogle.com/chapter/explainability-trust/); [PAIR controls](https://pair.withgoogle.com/chapter/feedback-controls/); [VS Code approvals](https://code.visualstudio.com/docs/agents/run/approvals); [VS Code security](https://code.visualstudio.com/docs/agents/run/security); [Telegram](https://core.telegram.org/bots/api); [W3C color](https://www.w3.org/WAI/WCAG22/Understanding/use-of-color.html); [W3C status](https://www.w3.org/WAI/WCAG21/Understanding/status-messages).

## 12. Recommended UX design

**Build a session autonomy card shared by TUI, CLI, and Telegram, backed by the accepted typed policy.** Compact form names effective profile and summarizes automatic effects/what waits. Expanded form shows overrides, ceilings, scope, provenance, decisions. Place at launch, selected session, and pending requests.

Use a profile picker and small plans/epics/questions override editor. Preserve `%auto`/`%a`, compatibility, fast `A` Manual/default. Keep absent directives Manual for unrelated launches. Completion and fail-closed diagnostics make typing/clicking agree.

Make changes honest: confirmed revisions, explicit scope, no pending-gate sweep, no claim to stop tools, no stale overwrite. Carry policy through successors and disclose child restrictions. Telegram gets Autonomy, profile selection, Manual, history through the same host path.

Keep routine automation quiet. Audit decisions, explain human requests, deliver a concise completion digest with failures/omissions, reuse existing receipts. Defer global modes, learned approvals, broad editors, speculative dashboards.

The experience should feel simple: **I choose how this session handles checkpoints; I can see the consequences, change them, and understand what happened.** This makes the accepted policy intuitive and powerful while leaving most of the screen—and attention—for the work.
