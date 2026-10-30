**Why `16h.f0` started early: fork targets, session promotion, and a proposed contract**

Independent research by `cdx`, 2026-10-30. No other researcher’s report, transcript, or findings were consulted. This is research and a design recommendation; no production code was changed.

The incident is confirmed: `16h.f0` waited for the original **turn** of `16h`, then started while `16h`’s review gate was still pending. Its saved dependency says `kind: "agent"`, with the original turn’s artifact identity. After that turn became `16h--plan`, the dependency still tested that same turn’s terminal marker. It did not become a session dependency. This is a timing-dependent mismatch between the user’s bare agent name and the implementation’s launch-time classification—not evidence that all existing session waits ignore successors.

The proposed `target=session|turn` option is a good idea, with `session` the appropriate default for a bare agent name. However, adding one enum input to `fork.yml` is insufficient. Scheduling parses fork arguments separately from macro expansion; the history loader resolves names again; the repeatable parent argument prevents simply appending another ordinary input; and coder waits use `%wait`, not `#fork`. The solution should bind one typed target and use it throughout those paths.

**What happened, from recorded evidence.** All times below are EDT on 2026-10-30. Artifact directory timestamps identify registered runs, not necessarily the time the provider began working.

| Time | Recorded event | Interpretation |
|---|---|---|
| 15:16:00 | Original `16h` run registered, artifact timestamp `20261030151600` | The request asked for a plan for command-mode RECENT reruns. |
| 15:22:39 | `16h.f0` registered, timestamp `20261030152239` | Its raw prompt contained `#fork:16h` and requested a separate navigation fix. |
| 15:25:08.573959 | `16h--plan/done.json.finished_at = 1793388308.573959` | The planner handed the decision to a gate; implementation remained unfinished. |
| 15:25:39.497615 | Fork dependency wait completed, `wait_release_source = ready_json` | Its recorded dependency satisfaction time exactly equals the planner’s finish time. |
| 15:27:50.790918 | Fork planner’s workflow started | Its expanded prompt showed only the completed planner and omitted the running gate. |
| 15:30:48 | `16h--code` registered, timestamp `20261030153048` | The implementation successor was a later turn of the original session. Its workflow started at 15:32:30.009620. |
| 15:34:48.114096 | `16h.f0--plan` completed | The fork’s planning work finished before the original session’s coder. |
| 15:51:36.767679 | `16h--code` completed | This is the later completion the user expected the fork to await. |
| 15:51:54.013561 | `16h.f0--code` dependency wait completed | This later coder had an explicit `%wait(16h)` and did wait for the original coder’s completion. |

The decisive excerpt from the fork planner’s `agent_meta.json` is:

```json
{
  "wait_for": ["16h"],
  "wait_for_fork_sources": [{
    "kind": "agent",
    "name": "16h",
    "artifact_dir": "/home/bryan/.sase/projects/gh_bobs-org__bob-cli/artifacts/ace-run/202610/30/20261030151600",
    "timestamp": "20261030151600",
    "project_name": "gh_bobs-org__bob-cli"
  }],
  "wait_completed_at": "2026-10-30T19:25:39.497615+00:00",
  "wait_release_source": "ready_json",
  "wait_dependencies_satisfied_at": 1793388308.573959
}
```

Its saved expanded provider prompt is even more direct:

```text
## Source 1 of 1 — agent session `16h`
- **Members shown:** 1 of 2 (sequential chain, oldest first)
- **Not shown:** `16h--gate` (running)
```

Thus admission used a turn identity, while context expansion subsequently recognized a session and supplied its available subset. This is an actual disagreement between two stages, not just confusing TUI labeling.

For reproducibility, the runtime evidence read was under `/home/bryan/.sase/projects/gh_bobs-org__bob-cli/artifacts/ace-run/202610/30/`:

- `20261030151600/{agent_meta.json,done.json,raw_prompt.md,workflow_state.json}`: original planner, later named `16h--plan`.
- `20261030152239/{agent_meta.json,done.json,raw_prompt.md,workflow_state.json,workflow-tmp_261030_152750-main_prompt.md}`: fork planner, later named `16h.f0--plan`.
- `20261030153048/{agent_meta.json,done.json,workflow_state.json}`: original coder.
- `20261030153819/{agent_meta.json,raw_prompt.md}`: fork coder and its explicit wait.

The completed transcripts were inspected through `sase chat show` for `16h`, `16h.f0`, `16h--plan`, and `16h.f0--plan`. Bare-name lookup returned the later `16h--code` and `16h.f0--gate` transcripts respectively; it should not be used as proof of the original turns’ prompts. The planner transcript basenames are `gh_bobs_org__bob_cli-ace_run-16h__plan-261030_151600.md` and `gh_bobs_org__bob_cli-ace_run-16h_f0__plan-261030_152239.md`, under `~/.sase/chats/202610/`. The original coder’s basename is `gh_bobs_org__bob_cli-ace_run-16h__code-261030_153048.md`. The fork gate transcript records `wait_agents: ["16h"]` on approval, corroborating the later coder’s raw `%wait(16h)` prompt. The fork coder was still running when its metadata was inspected; its eventual outcome is outside this diagnosis.

**The mechanism in the current checkout.** The code reviewed was sase commit `ee7bcddb6062f5e22b04a548de0c603f47628aae` and linked sase-core commit `0ec67fdcebccd0154a84168ad54e45e6c5793c1d`. Runtime metadata proves the incident; the source explains it. I did not establish the exact installed package revision at the original launch, so the checkout is not presented as a recovered binary build identifier.

1. `resolve_wait_state()` extracts explicit fork parents and adds implicit waits. `fork_wait_dependency()` asks whether a parent is a clan, an already recognizable session, a named agent, or a proc. An ordinary agent gets `kind="agent"` plus an artifact identity. Session detection intentionally excludes plain exact agents without session metadata. Consequently a future session can be captured as an ordinary agent before promotion. [Wait construction][wait-build], [dependency classification][fork-binding], [session lookup][session-lookup].
2. `fork_source_status()` treats `kind="agent"` as an exact candidate and resolves when `candidate.is_done or candidate.is_failed`. It does not check whether that candidate has subsequently become a session root. `kind="session"` takes a different path through the root’s session aggregate, including successor state. [Fork status evaluator][fork-status], [session aggregate][session-aggregate].
3. The ordinary name in `wait_for` does not supply an additional session barrier. The top-level resolver skips name evaluation when a typed fork source already covers that name. Thus the metadata’s visible `wait_for: ["16h"]` is weaker evidence than its `wait_for_fork_sources` entry. [Dependency evaluation][wait-evaluation].
4. After admission, `fork.yml` passes names to `resolve_agent_chat_sources()`, which looks them up afresh. The session history path excludes running gate/monitor members and unavailable agent transcripts instead of requiring a complete session. That behavior explains the observed partial history. [Fork workflow][fork-yaml], [source resolution][history-resolution], [member classification][history-members].

The most likely precise sequence is that `16h` was still an ordinary named run when the fork dependency was captured, then promoted to a session when it handed off to its plan gate. The saved `kind="agent"`, original identity, and later session history establish the scope mismatch with high confidence. The original classification call’s complete scan snapshot was not retained in the evidence inspected, so its absence of session metadata at that exact instant remains a reconstruction from the code and timestamps.

A small read-only experiment against this checkout, using `PYTHONPATH=src .venv/bin/python`, built an in-memory index with one completed planner and one pending gate. Calling the real evaluator with the same root artifact produced:

```text
completed root + pending gate; agent resolved
completed root + pending gate; session waiting
```

This also separates the incident from an older, different bug. Commit `fdbc47b51a` already fixed session fork waits releasing while a successor was queued for runner capacity. Its tests should remain part of the regression set; this incident’s stored dependency never entered that session-aware path.

**Assessment of the proposed API.** Keep `target`; it is understandable and matches the request. `scope` would also be defensible, but introducing both names adds needless terminology. The allowed values should be exactly the lowercase strings `session` and `turn`, validated before a wait or provider launch is created. A default makes the option optional to supply; it does not make arbitrary supplied values valid.

Use the existing inline enum facility. One correction to the premise: in the current Rust catalog, `model` is a domain input with provider-routing validation, not an inline enum. `effort` is a named enum. A new fork target does not require a model-style resolver or a plugin input type. Existing enum checking supports exact, case-sensitive membership, default validation, descriptions, and useful error messages. [Input catalog][type-catalog], [enum validation][enum-values].

There is a concrete syntax obstacle. The existing `name` input is `repeatable: true`, and the binder requires a repeatable input to be the final user-facing input. There is currently no `keyword_only` field in `InputArg`. My direct binder checks produced:

```text
input order ['name', 'target']:
  MacroValidationError: A repeatable input must be the final user-facing positional input
input order ['target', 'name'], invocation #fork:demo:
  InputBindingError: Argument `target` expects one of session | turn, got `demo`
```

Do not solve this by removing multiple parents, inserting `target` before `name`, treating the last positional parent as a scope value, or smuggling an undeclared keyword into Jinja. Add a small, explicit keyword-only input capability to the shared macro contract. Its proposed declaration would be:

```yaml
input:
  name:
    type: agent
    default: null
    repeatable: true
  target:
    type: enum
    choices: [session, turn]
    default: session
    keyword_only: true  # proposed schema support; not valid in today's contract
```

That change must reach binding, validation, catalog projection, schemas, completion, and the LSP. It is useful infrastructure justified by this existing variadic macro, not a reason to build a general new argument language. [Current binder][input-binding], [input model][input-model], [Rust catalog input representation][catalog-input].

The early parser is a separate obstacle. `_resume_reference_arguments()` discards the named-argument mapping returned by `parse_args()`. Against the current code:

```text
#fork(demo, target=turn)       -> fork_agent_names: ['demo']
#fork(name=demo, target=turn)  -> fork_agent_names: []
#fork(demo, target=bogus)      -> fork_agent_names: ['demo']
```

The last result does not imply that the eventual macro expansion accepts an invalid enum; it demonstrates that the early scheduling parser cannot enforce it today. Replace the lossy list-of-names interface with structured fork references, using the shared argument binding contract. Keep compatibility wrappers for callers that only need names for derived naming. Include bare/default forks, templates, multiline syntax, multiple occurrences, disabled macro regions, and fenced examples in that work. [Early extraction][early-parser].

**Proposed semantics and explicit requirement adjustments.**

| Invocation | Recommended meaning |
|---|---|
| `#fork:16h` | Follow the bound `16h` session generation, including promotion from an initially standalone agent. |
| `#fork(16h, target=session)` | Same, explicitly requested. |
| `#fork(16h, target=turn)` | Pin the current turn when the launch is accepted; await that turn’s terminal result and import its context. |
| `#fork(16h--plan, target=turn)` | Pin that exact planner turn, even if another turn is now active. |
| `#fork:16h--plan` | Preserve the existing exact-turn spelling as shorthand for a turn target. This is the compatibility exception described below. |
| `#fork(16h--plan, target=session)` | Explicitly follow the owning session generation. |
| `#fork(a, b, target=session)` | Apply the choice to both parents; await both independently. |
| `#fork(a, target=turn) #fork(b, target=session)` | Mixed targets through separate invocations; no new list syntax is needed. |

The following adjustments should be part of the requirements, not left to incidental implementation choices:

- **Default exception for explicit member names.** I recommend `session` by default for bare agent/session names while preserving an explicitly named member such as `16h--plan` as an exact turn selector when `target` is omitted. This is an intentional exception to a universal session default. Otherwise existing commands that deliberately name a turn silently broaden, including generated continuations. Preserve whether `target` was explicitly supplied, rather than losing that information when filling its default. An explicit `target=session` can still lift a member to its owner. If a universal default is preferred instead, every affected exact-member call site needs deliberate migration; that is a larger compatibility change.
- **Promotion must not change intent.** A session target on a standalone agent is valid before any session exists. Bind its root identity now and follow attached successors if it is promoted. If it never acquires successors, its one turn is the complete target. This is the essential fix for `16h.f0`.
- **“Turn” means a SASE lifecycle turn.** It includes a gate or monitor as well as an LLM agent turn. Select the active lifecycle head, not merely the newest artifact directory or newest LLM row; a preallocated future successor must not displace the current head. If the session is already settled, select its last terminal turn. Contradictory active-head evidence should produce a diagnostic. An exact member name avoids this selection step.
- **Bind at acceptance, not every poll.** For a prompt, acceptance is the launch’s dependency-binding step. For a coder gate, it is acceptance of the approval request. Re-exec, runner capacity delays, retries of admission, and eventual history expansion must reuse the binding. A reused name must not redirect an already accepted fork. A turn target with no resolvable current turn should fail clearly; a future-name session wait can retain existing support but binds once when the intended target appears.
- **Scope controls the history source as well as the wait.** A turn target imports that pinned turn’s own saved conversation or execution/decision record, with any ancestry already contained in that conversation. It must not re-resolve the bare name and import later turns. A session target imports the settled generation’s ordered history. For an external session fork, encountering a still-running member after supposed release means recheck the barrier, not silently label partial history complete.
- **Terminal does not mean successful.** Preserve the ability to fork a failed turn/session for diagnosis. Report failure prominently in context. Explicit `%wait` can retain its success-oriented policy. Scope and success policy are separate concepts; the enum should not accidentally unify them.
- **A settled generation is the boundary.** Pending review, an active monitor, successor admission, and required finalization are unfinished session work. Future manual attachments after a verified terminal release cannot retroactively delay an already running consumer. Do not interpret “session” as every descendant with a dotted name, an entire hood, or every future task in perpetuity.
- **Keep other fork kinds compatible.** Omitted `target` should preserve existing clan, tribe, and standalone-proc behavior. There is no unique current turn of a parallel clan or an unresolved future tribe selection; reject an explicit `target=turn` there with a request for a concrete member. Standalone procs retain their exact proc-ID binding; do not invent an agent session for them. Spell out which explicit options are supported for non-agent targets instead of pretending every source is a session.

**One target record should cross the whole pipeline.** Persist a versioned bound-reference record containing the requested spelling, whether the option was explicit, effective scope, source kind, owner/project identity, root generation identity, optional exact turn identity or proc ID, and completion policy. These are conceptual fields, not a proposed final wire schema. Artifact identity must survive renaming `16h` to `16h--plan`; the bare display name is not the durable key.

The binding is stable; the membership of a session generation can grow while it is open. When a session wait releases, capture the resolved ordered source identities for history loading. Waiting and context expansion then cannot choose different generations. Missing retained context should produce an actionable error or a clearly identified terminal-member omission; it must not quietly substitute a newer namesake. The existing root/session aggregate and release confirmation are valuable starting points: they already account for queued successors and confirm fresh membership before release. Preserve those properties rather than replacing them with “all visible rows look done.” [Session aggregate][session-aggregate], [release confirmation][release-confirmation].

Do not let name-only deduplication erase different meanings. Currently an explicit `%wait:foo` suppresses the special implicit fork dependency for `foo`. With scopes, `%wait(foo, target=session)` plus `#fork(foo, target=turn)` must mean “wait for the session, import the pinned turn.” Keep context bindings even when an explicit wait supplies a stronger admission barrier; combine independent wait constraints conjunctively. Deduplicate by resolved identity, scope, and policy as appropriate, not just by a string name. Likewise, completed-dependency caches must distinguish a terminal turn from its still-open session.

Same-session continuations deserve special attention. The existing contract excludes the waiting agent itself, and host monitor/gate follow-ups intentionally fork their own session’s prior context. Simply making every self-session request await full session termination creates a circular dependency. Preserve a host-owned continuation path that imports the completed predecessor prefix and excludes its own future work. Keep that path distinct from an external “wait until this session finishes” request; expose its predecessor boundary in metadata. Exact-turn continuation calls can use `target=turn`, but replacing every monitor continuation with a monitor-only record would lose prior agent context. Reject ordinary user-created cycles rather than resolving them by silently omitting arbitrary unfinished members. [Existing documented continuation behavior][fork-docs], [host follow-up target selection][host-followup], [generated pipe fork][pipe-fork].

**The coder gate needs the same capability.** Its current “Wait for” field parses comma-separated agent names, `bead=`, and `hood=`. The approval response serializes `wait_agents`, and the accepted-plan path renders `%wait(...)` into a fresh coder prompt. The coder does not inherit the planner’s chat. Therefore a new `fork` argument alone will not add the requested choice to this surface. [Wait-spec parser][wait-spec], [approval response encoding][approval-response], [coder prompt construction][coder-prompt].

Use the shared target resolver for `%wait(16h, target=session)` and `%wait(16h, target=turn)`, with a per-agent choice in the TUI. Show what was bound: for example, “Entire session: 16h” or “Turn: 16h--code, captured when approved.” Persist structured wait entries through the approval response and successor launch; keep legacy `wait_agents` decoding for old requests. Multiple targets need independent choices, so a single global toggle is inadequate. Bead/hood targets should not acquire meaningless turn settings.

Also preserve the distinction from epic-follow. Explicit agent waits currently carry `wait_for_epics_of`; implicit fork waits do not. That behavior was visible in the two `16h.f0` runs. A bounded turn wait should not silently expand into waiting for an epic created by that turn. Make its effective epic-follow policy explicit, normally disabled, and reject incompatible requests or clearly require an explicit broader policy. Do not make “session” an accidental synonym for “all related epic work.”

**Implementation placement and verification.** The inspected fork/wait policy still has substantial Python implementation, but this project’s required architecture puts new shared backend/domain behavior in `sase-core`. Put target selection, promotion rules, typed binding validation, and the relevant completion-policy decisions in Rust with versioned wire types and PyO3 tests. Python should gather artifact facts and adapt the runner and history loader; Textual should present and edit the choice. Move the relevant existing policy as needed for one authoritative implementation, without making this feature contingent on migrating every unrelated wait subsystem. Update `sase-core-revision.txt` after the core change lands. Keyword-only input metadata must likewise reach the Rust catalog and LSP, not only Python’s binder.

A practical sequence is:

1. Lock down the scope contract and add the incident regression: bind a bare standalone agent, promote it to planner plus pending gate, finish the planner, and assert that a session waiter remains parked while a turn waiter releases.
2. Add typed core bindings and the shared keyword-only macro input support. Preserve exact-parent multi-fork syntax and explicitness metadata.
3. Wire early fork extraction, persisted waits, release confirmation, and history loading to the same bound references. Update host-generated follow-ups and compatibility decoding together.
4. Carry the same target records through `%wait`, coder gate responses, the TUI, completion suggestions, help, and documentation. Keep this a coordinated feature rather than shipping a macro whose scheduling and context disagree.

Acceptance coverage should include:

- Both before-promotion and already-promoted sessions; completed standalone agents; root renaming and same-name generation reuse.
- Pending gates, monitor handoffs, delayed successor publication, queued successors, live finalizers, terminal failures, stopped/lost turns, and recovered failed handoffs.
- Turn selection frozen across a long queue delay; history from exactly the bound identity; no partial external session history while a member remains active.
- Existing `#fork:a,b`, named `name=`, bare/default forks, templates, multiple scoped calls, invalid enum values, fences, disabled regions, and positional compatibility. `#fork(a, turn)` must remain two parents, not silently mean a scope switch.
- `%wait` plus `#fork` for the same name with different scopes or policies; persisted release-cache keys; fresh membership rechecks.
- Monitor/gate/pipe same-session continuations, self-wait rejection, and mixed-scope coder approval round trips.
- Reading legacy `kind=agent`, `kind=session`, and `kind=family` dependencies without rewriting already accepted waits. Apply the new default to new launches; an old queued record should change only through an intentional rebind/edit.

Relevant existing tests include `test_run_agent_wait_deps_fork_source.py`, `test_wait_dependency_slot_queued_session_members.py`, `test_wait_dependency_release_confirmation.py`, `test_wait_dependency_live_handoff_resolution.py`, `test_agent_names_extract_naming.py`, `test_fork_workflow.py`, and the plan approval response/launch tests. Research verification consisted of source inspection, recorded runtime evidence, and the direct in-memory evaluator/binder checks above. No production changes or full test-suite run were needed for this report.

**Alternatives and recommendation.** Merely documenting the current behavior would preserve a timing-dependent surprise. Adding `%wait:16h` is an available workaround and demonstrably worked for the later coder, but requiring users to add it to a fork duplicates intent and changes failure/epic-follow policy. Teaching `kind=agent` to follow sessions after promotion would fix this incident but remove legitimate exact-turn semantics unless there is an explicit preserved scope. A separate `fork_turn` macro avoids the variadic-input obstacle, but duplicates the public API and still leaves all binding, history, and TUI work. I would only use that alternative if maintaining a keyword-only macro input is judged too costly.

My recommended solution is **`#fork(..., target=session|turn)` backed by a shared, durable target binding, with session as the default for bare agent names**. Add real keyword-only enum support, preserve explicit turn-name shorthand, follow session promotion, and use the same binding for admission and context. Carry that model through `%wait` and the coder gate, while retaining terminal-failure context and host continuation semantics. The first release criterion should be the exact `16h` reproduction: the default fork remains waiting through review and coding, while `target=turn` intentionally proceeds after the captured planner turn ends.

[wait-build]: https://github.com/sase-org/sase/blob/ee7bcddb6062f5e22b04a548de0c603f47628aae/src/sase/axe/run_agent_directives_flow.py#L40
[fork-binding]: https://github.com/sase-org/sase/blob/ee7bcddb6062f5e22b04a548de0c603f47628aae/src/sase/agent/fork_waits.py#L13
[session-lookup]: https://github.com/sase-org/sase/blob/ee7bcddb6062f5e22b04a548de0c603f47628aae/src/sase/agent/names/_lookup_groups.py#L317
[fork-status]: https://github.com/sase-org/sase/blob/ee7bcddb6062f5e22b04a548de0c603f47628aae/src/sase/core/wait_dependency_resolution/_index_fork_queries.py#L72
[session-aggregate]: https://github.com/sase-org/sase/blob/ee7bcddb6062f5e22b04a548de0c603f47628aae/src/sase/core/wait_dependency_resolution/_index_queries.py#L287
[wait-evaluation]: https://github.com/sase-org/sase/blob/ee7bcddb6062f5e22b04a548de0c603f47628aae/src/sase/core/wait_dependency_resolution/_resolution.py#L14
[fork-yaml]: https://github.com/sase-org/sase/blob/ee7bcddb6062f5e22b04a548de0c603f47628aae/src/sase/macros/fork.yml
[history-resolution]: https://github.com/sase-org/sase/blob/ee7bcddb6062f5e22b04a548de0c603f47628aae/src/sase/scripts/_agent_chat_from_name_sources.py#L152
[history-members]: https://github.com/sase-org/sase/blob/ee7bcddb6062f5e22b04a548de0c603f47628aae/src/sase/scripts/_agent_chat_from_name_agent_session.py#L30
[type-catalog]: https://github.com/sase-org/sase-core/blob/0ec67fdcebccd0154a84168ad54e45e6c5793c1d/crates/sase_core/src/macro_input_types/catalog.rs
[enum-values]: https://github.com/sase-org/sase-core/blob/0ec67fdcebccd0154a84168ad54e45e6c5793c1d/crates/sase_core/src/macro_input_types/value.rs
[input-binding]: https://github.com/sase-org/sase/blob/ee7bcddb6062f5e22b04a548de0c603f47628aae/src/sase/macro/input_binding.py#L24
[input-model]: https://github.com/sase-org/sase/blob/ee7bcddb6062f5e22b04a548de0c603f47628aae/src/sase/macro/models.py#L87
[catalog-input]: https://github.com/sase-org/sase-core/blob/0ec67fdcebccd0154a84168ad54e45e6c5793c1d/crates/sase_core/src/macro_catalog/types.rs#L170
[early-parser]: https://github.com/sase-org/sase/blob/ee7bcddb6062f5e22b04a548de0c603f47628aae/src/sase/agent/names/_resume.py#L282
[release-confirmation]: https://github.com/sase-org/sase/blob/ee7bcddb6062f5e22b04a548de0c603f47628aae/src/sase/core/wait_dependency_resolution/_confirmation.py
[fork-docs]: https://github.com/sase-org/sase/blob/ee7bcddb6062f5e22b04a548de0c603f47628aae/docs/reference/macros/built-ins.md#L70
[host-followup]: https://github.com/sase-org/sase/blob/ee7bcddb6062f5e22b04a548de0c603f47628aae/src/sase/turns/followup.py#L465
[pipe-fork]: https://github.com/sase-org/sase/blob/ee7bcddb6062f5e22b04a548de0c603f47628aae/src/sase/axe/run_agent_exec_pipe.py#L202
[wait-spec]: https://github.com/sase-org/sase/blob/ee7bcddb6062f5e22b04a548de0c603f47628aae/src/sase/wait_spec.py#L19
[approval-response]: https://github.com/sase-org/sase/blob/ee7bcddb6062f5e22b04a548de0c603f47628aae/src/sase/ace/tui/actions/agents/_notification_plan_response.py#L21
[coder-prompt]: https://github.com/sase-org/sase/blob/ee7bcddb6062f5e22b04a548de0c603f47628aae/src/sase/axe/run_agent_exec_plan_accept.py#L600
