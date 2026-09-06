# Remote dispatch and a focused fleet experience for SASE

**Date:** 2026-09-06

**Status:** Consolidated research and recommended design; no implementation changes.

**Evidence:** Independent reports A and B, the three requested earlier studies, lead code review, fresh local profiles, and primary protocol documentation.

## Decision in brief

Build a personal fleet control plane: **one SASE protocol, pluggable machine access, and two views over the existing Agents list**. Keep `%dispatch:<machine>` and automatic subscription. Call the views **Focus** and **Fleet**, and call subscribing **Follow** in the interface.

Focus preserves today's local Agents experience and adds followed remote agents. Fleet is one searchable, paged catalog of agents owned by configured remote machines, with followed entries visibly marked. Following expresses attention and membership in the working view; independent hydration tiers control performance. Neither a launch receipt nor a small network payload eliminates that product need.

Ship a built-in, default-enabled **tailnet** access provider and a built-in **HTTPS** provider so Tailscale is optional. Discovery runs during explicit setup or rediscovery, never on launch, completion, or ordinary refresh. Each machine records its own provider. Reuse the Rust gateway for the host protocol and an optional local federation worker; keep local ACE independent of that worker.

The implementation's first problems are **bounded, owner-resolved reads**, **portable identity/content/action boundaries**, and **safe mutation recovery**. The existing gateway is a useful starting point, not an endpoint to expose unchanged. Do not promise full remote parity merely because records share a serializer.

## 1. Provenance and how the reports were reconciled

Exactly one report belongs to each dependency. Their canonical filenames establish their suffixes; list order did not:

| Dependency | Original canonical reference | Preserved report |
| --- | --- | --- |
| `research.1i.cdx` | `research:202609/provider_neutral_remote_dispatch__a.md` | [Researcher A](remote_dispatch_and_fleet_focus__a.md) |
| `research.1i.cld` | `research:202609/remote_dispatch_plugin_architecture__b.md` | [Researcher B](remote_dispatch_and_fleet_focus__b.md) |

Both were read through `sase artifact read`. Only their copies in this turn's opened research checkout were moved; the registered immutable snapshots and other researchers' checkouts were untouched. SHA-256 verification confirmed both files were preserved byte for byte:

- A: `af79fefa39efde38f32dabb33db2f2734941e76a6fd943cc728a4cf58f68e895`; snapshot `file:explicit:ddb67197632f3b24bcfc6283`.
- B: `55134183b364ba9b6479f2a4dce522181489659e7492e2626524ee2f7fa3e15e`; snapshot `file:explicit:a06be91b908a10c584eccea8`.

The earlier studies were reviewed in their requested creation order:

1. [Tailnet agent fleet](../tailnet_agent_fleet/tailnet_agent_fleet.md): establishes HTTP/SSE and per-host authority. Its git-import offline fallback is obsolete.
2. [SASE collaboration architecture](../sase_collaboration_architecture.md): separates personal process control from collaboration through durable artifacts.
3. [Tailnet fleet federation](../tailnet_fleet_federation/tailnet_fleet_federation.md): accounts for the deleted import leg, identifies unsafe loader effects, and develops the gateway/federator approach. Its performance attribution and identity/cursor conclusions require the corrections below.

No predecessor chat transcripts were consulted. Lead source review used `sase` at `58f16fe6878c273d85d99ea6c521829838a5a827` and the opened `sase-core` checkout at `050415532b16572fe443fc80c159d516e00baa67`, matching A and B. Timing results below are local samples on athena, not a fleet benchmark or an implementation guarantee.

| Disagreement | Consolidated decision and reason |
| --- | --- |
| A: Focus/Fleet and Follow. B: one global list, no subscriptions. | **Two explicit view presets over one list widget, with Follow.** Keep A's attention model and B's shared presentation machinery. Packet size does not decide which work belongs in the user's working set. |
| A: keep `%dispatch`. B: rename to `%machine` and add pools/auto placement. | **Keep the requested spelling and explicit target.** `%dispatch` composes with the same parser machinery. Naming is subjective; pools introduce a scheduler that is unnecessary here. |
| A: Tailnet plus static HTTPS. B: SSH first, Tailnet last. | **Tailnet plus HTTPS in the first complete release.** SSH tunneling is a useful later adapter to the same protocol. Do not delay the requested default or create a second stdio protocol to evade gateway work. |
| A: five access/enrollment hooks. B: two discovery/channel hooks. | **Three small hooks initially: provider specification, discovery, connection plan.** Core owns enrollment and connection lifecycle. Add provider provisioning only when a real adapter requires it. |
| B/federation: reuse raw scan wire and machine-qualified names. A: portable protocol and global locators. | **Share domain types and rendering, but version a safe resolved projection.** Raw scan records contain local effects and paths. Use stable origin/agent/run identities; names remain labels. |
| Early studies: fork removal turns seconds into milliseconds. B: scans dominate. | **B's diagnosis is supported, with a correction:** CLI scans twice; the mobile bridge scans once. Fix query shape and liveness before attributing gains to process residency. |
| B: answer questions/approve gates before mutation safety. | **Attention visibility early; answering and approving after mutation safety.** Gate approval can run a command and launch a successor. |

## 2. Lead findings that change the design

### Reads: the slow algorithm survives a warm process

Fresh profiles used the workspace virtualenv, `cProfile`, and the CLI entry function. They printed timing/count summaries, not agent prompt bodies. An initial profiling invocation used an unavailable package entry point and was discarded; the successful measurements were:

| Measurement | Lead sample |
| --- | --- |
| Installed `sase version`, unprofiled | 0.352 s |
| Workspace `sase agent list --json`, profiled | **11.703 s**, 17 entries, 25,216 output bytes |
| Rust scan function within that listing | **2 calls, 6.538 s** total |
| Python scan facade, including conversion | 2 calls, 9.792 s cumulative |
| `_agent_meta_from_dict` | 23,336 calls, 2.037 s cumulative |
| Workspace `sase mobile agent-bridge list-agents`, profiled | **6.514 s**, 17 entries, 15,334 output bytes |
| Rust scan function within the bridge | **1 call, 3.331 s** |

Cumulative timings overlap and must not be added. Profiling overhead and concurrent host activity make these diagnostic samples, not p95 estimates. The installed version command is only a startup comparison, not a controlled subtraction from the workspace profiles.

Source review explains the difference. `agent_list_entries()` obtains a listing snapshot but still invokes `_children_by_parent_timestamp()`, which scans again. The mobile bridge calls `list_running_agents()` directly; it does **not** inherit the extra child-summary scan. Both paths need bounded index-backed reads; removing the redundant CLI scan alone will not fix gateway latency.

ACE already uses `query_agent_artifact_index()` with bounded active/recent tiers, candidate filters, and cached/revalidate modes. Reuse that approach, while preserving owner-side liveness resolution and an explicit incomplete/index-repair state. A raw SQL status aggregation is not an equivalent answer: it omits liveness, visibility, family rules, and conversion. B's reported 1,867 active-status records versus 19 live entries demonstrates a serious semantic discrepancy, but the scopes are not identical enough to treat the ratio as a universal measured false-positive rate. The reliable conclusion is that stored active status alone is insufficient.

### The existing loader is an unsafe shortcut for remote records

`_running_loaders.py` checks a PID with the local kernel, unlinks a running marker, and updates the local artifact index. `_meta_enrichment_common.py` also checks a response path. Passing another host's scan record through these paths can inspect or modify the wrong machine's resources.

Split **owner resolution** from **pure presentation**. The owner resolves process identity, lifecycle state, and content availability. The viewer receives resolved values and opaque handles. Reuse the shared domain types and existing widgets, but do not export absolute paths and then rely on developers to remember not to open them. A Python object without `__fspath__` is helpful, not a complete safety proof; existing string conversion and path construction must also be removed or guarded.

### Gateway hardening is real work, and SSH changes only part of it

Verified in `crates/sase_gateway/src/routes.rs`:

- `pair_start` is unauthenticated and returns its own pairing secret; `pair_finish` accepts that secret to mint a bearer token. Remotely exposing that flow allows the caller to authorize itself.
- `events()` emits initial replay records and then heartbeats; it does not deliver later agent changes to an already-connected client. Four production mutation sites publish changes, but local launches and lifecycle changes need coverage too.
- The bridge spawns a process; `request_id` is correlation, not a durable deduplication mechanism.

SSH can remove the need for a network pairing endpoint when authentication is delegated to an authorized OS account. It does not solve version negotiation, run identity, portable content, idempotency, family continuation, or bounded reads. “SSH needs no hardening” is therefore too broad. A per-request SSH process also retains process and scan costs; a persistent tunnel is a better fit for the chosen HTTP protocol. OpenSSH supports port forwarding and multiplexed connections. [OpenSSH manual](https://man.openbsd.org/ssh)

The crate boundary also needs precision. `sase_core` currently has no Tokio/Reqwest dependencies; `sase_gateway` has both and already depends on it. That does not make adding a Rust client elsewhere impossible. It makes the existing gateway/runtime crate the least disruptive home for connection management. Keep reusable identity, subscription, launch, and mutation rules in `sase_core`; expose the necessary contracts through the binding or thin IPC adapter. Do not move shared policy into Textual.

## 3. Product model and UX

### Is there a better way than Local/Remote subtabs?

Yes: **Focus / Fleet**, implemented as two modes of the existing list and detail area. “Local” would contain remote agents by design and require a permanent explanation. “Following” would imply that local agents must be followed too. Focus describes membership without implying execution location.

A single all-machines list with filters is useful as an optional saved query, but it makes browsing and everyday management compete for the same attention. Conversely, two independent list implementations would duplicate selection, grouping, counts, and action logic. Use one widget with mode-specific query, layout density, selection, scroll position, and detail state. Switching paints cached state immediately; it may schedule missing pages in the background.

```text
 Agents
 ┌─ Focus  7 running ───────── Fleet  12 running · partial ──────┐
 │ Search agents…                                             │
 ├────────────────────────────────────────────────────────────┤
 │ ● fix-auth       apollo    RUNNING   04:12   codex           │
 │ ? review-cache   athena    QUESTION  00:38   claude          │
 │ ● docs-cleanup   here      RUNNING   01:05   codex           │
 ├────────────────────────────────────────────────────────────┤
 │ fix-auth · apollo · Updated now                             │
 │ … existing detail layout, hydrated on demand …              │
 └────────────────────────────────────────────────────────────┘
```

### Fleet should answer “Do I want to follow this?”

Use a single scrollable list with light machine section headers, not per-machine tabs. Keep the columns restrained: follow state, agent/family name, project, status, elapsed time, and a short intent summary. Model is optional at wider widths. A host header supplies origin, connectivity, freshness, and running count; repeat origin on rows when filtering mixes hosts or a header is offscreen.

```text
 Focus  7 running        [ Fleet  12 running · partial ]

 apollo       Online · Updated now · 5 running
 ★ fix-auth       sase       RUNNING    4m   Repair auth race
 ☆ docs-refresh   website    WAITING   41s   Refresh examples

 mac          Last seen 2m ago · 3 running then
 ★ perf-study     sase       UNKNOWN        Was running

 athena       Online · Updated now · 4 running · 1 needs input
 ☆ review-cache   sase       QUESTION  38s   Choose cache policy

 Follow / Unfollow          Preview          Filter machines
```

Use a filled versus outlined star plus a subtle accent rail for followed rows. Color reinforces meaning; it does not carry it alone. Preserve the origin label before optional model/time columns at narrow widths. Reuse ACE's palette, status chips, and `PanelTabStrip`; avoid another decorative machine strip permanently competing for vertical space. A compact machine filter/picker can expose capacity when it matters.

Selection shows a bounded intent preview, not a full transcript. Following adds the row to Focus immediately without moving focus or switching tabs; the footer can offer “View in Focus.” Unfollowing removes only this viewer's follow rule and offers Undo. A host going offline keeps cached rows in place with age and unavailable actions. An empty, loading, unavailable, and fully loaded zero-result catalog must look different.

### What does “all agents shown in remote TUIs” mean?

It should mean **the same underlying eligible agent catalog**, not each remote viewer's current query, folds, selection, or private dismissal choices. Make all eligible active and historical agents reachable through paging and explicit history filters; initial display favors active, attention-needed, and recent work. Declare hidden/history eligibility in the host API and match the existing local product semantics deliberately.

There is an additional recursion trap: once a remote TUI also shows subscriptions, copying its displayed list would re-export agents from third machines. A follows B, B follows A, and both would show duplicates or loops. **Each host exports only agents it owns.** Fleet takes the union of those authoritative catalogs, deduplicated by stable origin identity. No implicit transitive discovery, subscriptions, or control. If a third host is useful, enroll it directly. This is a deliberate refinement of literal TUI mirroring.

### Why keep Follow if network snapshots are small?

Follow answers “keep this work here and tell me when it needs me.” It is durable user intent, not permission, ownership, or a download setting. It remains useful with zero network cost and is essential for adopting work launched from another machine.

Persist a small viewer-local subscription separately from caches and dispatch receipts. Dispatch creates it automatically. An explicit Unfollow overrides automatic membership; restarting ACE or retry reconciliation must not recreate it. A receipt remains useful for recovery after unfollowing, but no longer determines Focus membership.

Follow the **logical SASE agent/family** across sequential agent, monitor, and gate shells. This matters because SASE agents are single-turn and continuation is mechanical. A subscription that stops when the first provider run ends will lose the very approval or monitor completion the user needs. Promote singleton follows to the stable family identity when a family forms. Do not automatically follow every sibling in a clan or unrelated descendant; a fork/retry launched by this viewer receives its own follow. Broader lineage-following can be an explicit later preference.

Completed followed agents remain in Focus under the normal recent/history rules. Viewer dismissal does not archive or delete the remote authority's record. A dismissed run can stay followed for subsequent family activity. Notification deduplication uses the origin plus request/event identity; following a remote family must surface its question/gate promptly without repeated toasts on reconnect.

### Counts must communicate both scope and freshness

Use a single core count definition across snapshots, title bars, and status chips. Count distinct logical agents whose current agent shell satisfies the existing running predicate; do not count tree headers, historical shells, gates, or monitors as running LLM agents. Deduplicate transient family handoffs. Track waiting/attention and occupied runner slots separately—these are useful numbers, but not interchangeable with “running.”

- **Focus:** local running agents plus running followed remote agents.
- **Fleet:** running agents owned by enrolled remote hosts, including followed agents.
- Counts overlap; do not add the two to produce a total. Query-specific counts belong in the list footer; the two title totals retain stable scope.
- A never-contacted host contributes **unknown**, not zero. Show “partial” when some host counts are unknown, and “last seen” for cached totals. A detail/help line identifies missing hosts and observation times.

Compute counts from authoritative summaries, not whichever page happens to be loaded. Even one in-memory list cannot guarantee exact counts when history is paged or some hosts are unreachable. Apply rows/counts from the same per-host revision where possible; there is no atomic snapshot across machines. Explain partial information instead of fabricating consistency.

### Interaction and beauty

Use familiar actions and short, specific feedback: “Following fix-auth on apollo”; “Stop requested on apollo”; “Already answered on mac.” Repeat the target host in the detail header and consequential action dialog. Remote location alone should not add a confirmation to every harmless action; use existing confirmation policy for stop/approval and make the target explicit.

Do not reuse `[`/`]` casually: they already control artifact subtabs and thinking mode in the reviewed keymap. Add named, configurable Focus/Fleet and Follow actions, audit conflicts, and update `default_config.yml` and help together. Mouse support and command-menu actions should work independently of the final shortcut choice. Hide the mode strip until a machine is configured; an explicit “Connect a machine” action opens setup without adding idle work.

## 4. Architecture and plugin contract

```text
 ACE / CLI
   ├─ local reads and actions ───────────── existing direct path
   └─ remote facade / thin IPC adapter
           │
     local Rust federation worker (started only when needed)
       subscriptions · cached projections · operation recovery
       per-host deadlines, connection pools and invalidations
           │
     versioned HTTP/JSON + SSE, same protocol for every provider
           │
     target Rust gateway → core resolution/admission/lifecycle

 Python plugin registry → validated connection descriptors
       tailnet       HTTPS       later: SSH tunnel / other access
```

Use the existing Rust gateway/runtime crate for the federation worker and server integration. Keep local reads direct and independent. Start one per-user worker on demand, shared by local consumers through a permission-restricted IPC endpoint; binding that endpoint and shipping/supervising the binary are new work. It need not be an always-on daemon on a viewer. Persist subscriptions and dispatch intents before worker startup so process failure cannot lose them. Always-on notification delivery while ACE is closed is a later opt-in, not implied by Follow.

The worker receives core-validated machine configuration and serializable connection plans from the Python plugin adapter. It must not import Python modules or contain Textual policy. Provider preparation runs through a bounded, separately supervised helper when necessary; hot reads do not execute plugin hooks. A plugin exception or timeout affects only its machines. In-process Pluggy calls cannot enforce a hard timeout on a hung plugin; slow/untrusted preparation needs a process boundary and cancellation.

### Proposed hooks

Use a new entry-point group, provisionally `sase_dispatch`, with typed, versioned request/results and keyword arguments:

| Hook | Contract |
| --- | --- |
| `dispatch_provider_spec()` | Stable provider ID, schema version, configuration schema, supported connection kinds, diagnostic metadata. Static and cheap. |
| `dispatch_discover(request)` | Read-only candidate enumeration for explicit setup/rediscovery, with deadline and cancellation. Never enrolls or opens a control channel implicitly. |
| `dispatch_connection_plan(request)` | For the **selected provider**, return a serializable plan to reach the standard SASE endpoint, including credential references and any required preparation. No agent semantics. |

Core owns identity verification, common enrollment, credentials, channel lifetime, authorization, retries, caches, listing, launch and control. Aggregate discovery across enabled providers, then deduplicate candidates at authenticated enrollment by installation identity. Select a provider before invoking connection planning; plugin registration order must never select a kill target. Inspect entry-point metadata before loading implementations, and import only providers actually needed.

For the first built-ins a connection plan is simply HTTPS URL, credential reference, pinned installation identity, and TLS/trust settings. A future tunnel plan can establish access to the same HTTP service and include explicit renewal/cleanup semantics. Avoid a Python `RemoteChannel` object containing live streams or raw auth headers: it crosses the Rust process boundary poorly, hides lifetime ownership, and risks logging credentials. Avoid separate list/kill/fork plugin hooks.

### Configuration and setup

Illustrative proposed configuration—not an existing schema:

```yaml
dispatch:
  discovery_providers: [tailnet]
  machines:
    apollo:
      provider: tailnet
      endpoint: https://apollo.example-tailnet.ts.net
      installation_id: install_opaque_id
      credential_ref: secret-store://sase/apollo
    buildbox:
      provider: https
      endpoint: https://buildbox.example.net/sase
      installation_id: another_installation_id
      credential_ref: secret-store://sase/buildbox
```

A global discovery default is useful; a global execution provider is not. The directive resolves an enrolled alias to a pinned machine record. The built-in tailnet provider is enabled by default for explicit setup, but an absent/unconfigured Tailscale binary leaves normal local operation unchanged. Empty `machines` means no runtime provider load, federation process, network traffic, or remote timers.

`sase init` should offer remote setup, enumerate candidates, show cached/provider labels and reachability, and enroll selected machines through an authenticated handshake. Existing explicit choices authorize the configuration being performed; do not turn every individual setup step into another confirmation. A newly discovered device is not implicitly trusted, and setting up access must not silently expose a service or change a tailnet policy.

Tailscale documents `status --json` for automation, but warns that its format may change. Parse defensively and keep fixtures for missing/extra fields. Peer visibility and Tailscale “online” status are hints, not proof that a compatible SASE host is listening. [Tailscale CLI reference](https://tailscale.com/docs/reference/tailscale-cli)

Provider device names, DNS names, local aliases, and `id.machine_name` are separate fields. Read the authoritative SASE name from the authenticated host; do not sanitize DNS into process identity. The Mac's `kellys-macbook-pro` DNS name and `kellys_mbp` SASE name already differ. B's stronger claim that a digit-bearing device has no possible valid SASE name is incorrect: it can receive a valid alias; it simply cannot reuse that string unchanged.

Use `sase machine` for explicit add/discover/list/status/remove operations if a CLI group is added; preserve the project's default-list and help conventions. Ordinary `doctor` should check enrolled records without surprise network discovery. Runtime rediscovery is unnecessary; endpoint resolution such as DNS and configured credential renewal remains allowed and lazy.

## 5. Protocol, identity, and reliability

### Portable identity and resolved records

An authoritative locator should include a **per-user SASE installation identity**, project identity, logical agent/family identity, and exact shell/run instance identity where an operation needs it. A machine-wide network identity cannot distinguish two SASE homes. Human labels remain familiar; IDs need not become user-facing syntax.

Do **not** include provider ID in canonical agent identity as A suggests: changing from Tailnet to HTTPS must not duplicate rows, invalidate follows, or create a new agent. Provider and URL are routing metadata. Host reinstall/clone handling must rotate or explicitly migrate the installation identity; a pin mismatch quarantines that connection until deliberately resolved. A self-reported ID is not cryptographic proof; enrollment needs an authenticated channel and trusted pin/bootstrap.

Use versioned resolved summary/detail records built from shared Rust types. Include origin, stable IDs, display fields, owner-resolved liveness, observation time, row revision, capability set, and content handles. Never send a PID or filesystem path as an actionable identity. Name-addressed convenience commands must resolve to an exact instance and verify it before acting; “look up the same name again” alone cannot prevent name reuse errors.

Separate lifecycle status, process liveness, connection health, and observation freshness. A healthy heartbeat does not make an old process observation current. Compute elapsed cache age using the viewer's monotonic clock during a session; use owner-relative duration/owner time for runtime display and conservative staleness after restart. When liveness becomes unknown, retain “was running; last seen…” instead of converting the run to completed or silently keeping it live.

### Small reads and recoverable events

The host API needs hello/capabilities, summaries, bounded catalog pages, batch lookups for followed IDs, lazy detail, content handles, project eligibility, mutation receipts, and invalidations. Summary computation must use maintained resolved state; a tiny JSON response backed by an archive scan is still expensive. Counts and row pages need independent query contracts.

Use snapshots plus invalidations. SSE offers event IDs and `Last-Event-ID` on reconnect; it does not provide durable delivery or application deduplication automatically. [WHATWG SSE specification](https://html.spec.whatwg.org/dev/server-sent-events.html)

Return a cursor with a **store generation plus sequence/revision**. The preceding federation report's durable revision alone does not cover index rebuilds, restores, cloned stores, or liveness changes outside index writes. Maintain tombstones or emit `resync_required` when deletion history is unavailable. Include process exits and locally originated launches/approvals in invalidation coverage. Periodic bounded reconciliation repairs missed watcher/events; it must not mean serializing all history every minute.

Keep feed position and mutation preconditions conceptually separate. A fleet-wide index revision would reject an action because an unrelated agent changed. Use an exact run identity plus a resource/action revision or pending-request ID. Validate a snapshot and its cursor consistently so changes between snapshot capture and event attachment are replayed or force resync.

### Safe mutations include attention actions

Every mutation requires authorization, exact target, a durable operation key and payload fingerprint, relevant preconditions, and a bounded acceptance policy. Scope keys to the authenticated controller. A repeat with the same key and payload returns the original operation; the same key with another payload conflicts. Retain receipts/tombstones through the documented retry window, and reject expired keys instead of silently treating them as new launches. HTTP itself does not make POST retries safe. [RFC 9110, idempotent methods](https://www.rfc-editor.org/rfc/rfc9110.html#section-9.2.2)

A journal entry alone is insufficient for launch crash recovery. Atomically reserve the run identity and admission record before spawn; serialize workers with durable ownership/fencing, and let recovery find an existing process/run for that reservation. Test crashes between reservation, spawn, run-record persistence, and reply. The achievable guarantee is one admitted run per launch intent through the supported recovery window—not arbitrary exactly-once execution of every tool the agent later invokes.

Question answers and gate approvals are mutations. Reconcile the exact pending request and revision, consume it once, and return “already answered” for a conflicting second controller. A gate may execute shell commands and launch a follow-up; it must not bypass the mutation journal because its button looks like notification UI.

### Enrollment and authorization

Fix or isolate the existing pairing endpoints before making the gateway remotely reachable. Require target-authorized bootstrap, short-lived single-use enrollment secrets, scoped revocable credentials, and rate limits. Store credentials outside YAML and cache only the data the local user can read. Audit operation metadata without logging secrets or full prompts by default.

For Tailnet, prefer loopback gateway plus Tailscale Serve and explicit network access policy. Serve is private to the tailnet; Funnel is public. Serve strips spoofed identity headers, but tagged clients lack user identity headers, shared external users can have them, and local services can bypass the proxy. Consequently, a user header or loopback bind is not sufficient SASE authorization. Keep SASE credentials and per-user host policy as the baseline. [Tailscale Serve identity documentation](https://tailscale.com/docs/features/tailscale-serve#identity-headers)

The HTTPS provider uses equivalent authenticated SASE semantics behind validated TLS. Tailnet membership is never an agent-management permission. Keep the first release to one owner's installations; cross-user collaboration remains artifact-based.

## 6. `%dispatch` and action parity

Keep the requested syntax:

```text
#gh:sase %dispatch:apollo Investigate the cache regression.
```

No directive means local. Reserve `local` as an explicit escape if overrides are supported. Completion reads enrolled aliases and cached eligibility; it never loads a provider, probes SSH, or resolves a project with side effects. Stale eligibility can inform the picker but cannot permanently disable a healthy target. Authoritative validation still happens on submission.

### Launch sequence

1. **Parse routing without side effects.** Extract the target and branch structure before reserving local agent names, timestamps, workspaces, or artifacts. The current `_submit_resolved_launch()` allocates a timestamp before the durable launch, so routing must move earlier. Consume `%dispatch` into the typed launch envelope; the target executes locally instead of dispatching the same prompt again. Reject conflicting targets and unsupported cross-host dependencies clearly.
2. **Persist source intent.** Store target installation ID, operation key, reconstructible launch input/attachments or their durable references, payload digest, and `follow_requested=true`. A digest alone cannot recover a lost prompt. Show a pending dispatch row immediately; it is not counted as running.
3. **Prepare a portable request.** Identify the project by provider/repository identity plus the intended revision or Patch context. Do not send a local checkout path or assume that two repos with the same basename are equivalent. Resolve machine-specific workspace setup and execution on the target. Source and target Git credentials remain separate.
4. **Validate and admit on the target.** Check project registration, repository/revision availability, provider/model/plugins, supported directives and finalizers, and capacity. The target reserves identity and allocates its own workspace. Full capacity can produce a durable target-side queued run; an unreachable machine cannot accept a launch.
5. **Bind the receipt and follow.** Persist the authoritative agent/family/run locator, replace the pending row without losing selection, and activate the prewritten subscription. Loss of the reply leaves “Checking dispatch outcome,” not “Failed; launch again.” Reconcile using the same operation key after reconnection or controller restart.

Never silently fall back to local or another machine. If transmission definitely did not occur, retain the prompt as unsent/retryable. If acceptance is uncertain, preserve that distinction until the target confirms the receipt. A source timeout is not evidence of nonexecution. User cancellation after acceptance is its own reconciled operation.

### Expansion, source material, and continuation

Ordinary side-effectful xprompt expansion, command substitutions, workspace setup, and finalizers must execute on the selected target. Source-side routing parses syntax only; it must not execute setup once locally and again remotely. For v1, require `%dispatch` at the outer launch level and reject hidden or late target changes after expansion. Show cached target/model information in the composer and the accepted configuration in the receipt.

Validate `@` references and attachments explicitly. Portable published references can resolve at the target; machine-local files need a deliberate, bounded content package. Do not assume uncommitted source work, dirty patches, private environment variables, or unpublished artifacts exist remotely. Initially reject unsupported local-only context with a useful preparation action; do not silently launch from the target's unrelated default branch. Missing projects should be set up separately rather than automatically cloning during completion.

Same-target family continuations, plans, gates, monitors, and host finalizers stay on the execution host. Following tracks that family from the controller. Cross-host `%wait`, clan coordination, pools, automatic placement, and mixed-host fan-out need a separate dependency/identity design. `%alt` parser composition may help later; safe distributed workflows do not come “for free.”

### Familiar actions, explicit capabilities

| Action | Remote behavior |
| --- | --- |
| Follow/unfollow, folds, selection, viewer dismissal | Local subscription/presentation state; no target process mutation. |
| View summary/detail | Cache first; bounded lazy fetch; keep origin and age visible. |
| View chat/output/diff/artifact | Opaque handle, size limits and digest cache; range/offset reads for growing output. Following never downloads all history. |
| Kill/stop, retry, child creation | Same action vocabulary, executed by target authority with exact identity and recovery. |
| Question answer/gate approval | Exact pending request, capabilities and mutation protections. Read decision/command details before approval. |
| Fork | Default to **Fork on apollo** for a remote row; follow the resulting agent. Target owns context and provider-session availability. |
| Fork here | Separate later operation requiring portable context; reading a prompt alone does not migrate a provider conversation or workspace. |
| Open terminal/editor/tmux | Explicit remote-session integration when configured, or a clear unsupported reason. Never hand a remote path or PID to a local action. |

Capability checks belong to both host and selected resource, combined with authorization and freshness. A stale selection can first revalidate in the background; offline destructive work is not queued for execution hours later. Target-side revalidation remains mandatory even when the UI just fetched a fresh row. Bulk commands partition by origin and report per-target results without pretending to be an atomic fleet transaction.

## 7. Laziness, failure behavior, and acceptance criteria

| Demand | Work permitted |
| --- | --- |
| No configured machines | Existing direct behavior; no discovery, provider imports, worker, or extra remote timer. |
| First paint | Local data and a bounded cached remote working set; no network/provider wait. Larger cache decoding stays off the event loop. |
| Agents visible, Fleet hidden | Cheap summary reconciliation for title counts; batch watched/followed state. No unfollowed row/detail/history fetches. |
| Fleet visible | Independently fetch first/visible pages per host and compact previews. Cancel obsolete requests on query/selection changes. |
| Explicit content open | Bounded stream/range fetch with cache validation. |
| ACE not displaying Agents | Slow or suspend decorative count refresh; preserve subscribed attention/operation recovery as required. Closing ACE does not cancel remote runs. |

These are independent demand tiers, not a promise of zero traffic and always-live counts simultaneously. Start with jittered 30–60 second summary reconciliation while visible, event-driven invalidation when available, and backoff for unavailable hosts. Treat intervals as tunable starting points. Share one summary calculation across clients on a host, pool connections, bound concurrency, prioritize followed/visible work, and enforce byte/page/cache limits. Compression can help snapshots; do not buffer SSE enough to delay attention events.

All I/O, decoding, provider preparation and merging stays off Textual's event loop **and serial message pump**. Launch worker tasks from thin callbacks, cancel them at teardown, preserve coalescing/navigation gates, patch changed rows, and re-read selection before applying asynchronous results. User operations use the existing durable launch/cleanup proc lineage; a proc completing means the request was submitted or settled, not necessarily that a remote run finished.

| Failure | User-visible result |
| --- | --- |
| Missing Tailscale/provider | That route is unavailable; local work and other providers remain usable. |
| One host hangs or laptop sleeps | Cached rows with age; other hosts update independently. Resume/reconcile without restarting ACE. |
| Unauthorized/incompatible host | Specific host state and remedy; never an empty successful catalog or automatic weaker-auth fallback. |
| Same endpoint presents another installation | Quarantine it; preserve follows and require deliberate re-enrollment. |
| Stream replay gap, database rebuild/restore | Generation mismatch or resync result; fetch a bounded authoritative snapshot. |
| Launch reply lost or source crashes | Recover the same operation/run and follow intent; no fresh launch key. |
| Name/PID reused | Exact instance/fencing conflict; never target the replacement. |
| Gate answered elsewhere | Show its settled result; do not execute twice. |
| User unfollows during pending dispatch | Reconcile the operation while respecting the explicit unfollow. |

Measure acceptance rather than assuming the network is cheap:

- Local-only first paint stays within baseline measurement noise; no new remote work occurs with an empty machine registry.
- Existing `j`/`k` p95 target of **under 16 ms** holds with a hung host, reconnect storms, and event bursts.
- Hot summary/read work is bounded by relevant candidates, not archive size; instrument scan count, candidate count, liveness checks, decoding time, and bytes. No fixed “14 ms fleet read” claim until the full resolved query is measured.
- Followed IDs remain visible even when absent from the first catalog page. Hidden Fleet never triggers full catalog hydration.
- Counts remain honest under partial failures, paging, clock skew, shell handoff, and overlapping views.
- Remote rendering cannot call local process checks, marker cleanup, index mutation, or path opens; verify this with effect-failing tests as well as types.
- Fault tests cover every launch crash boundary, receipt expiry, two competing controllers, lost replies, request cancellation, token revocation, store generation changes, and all supported transports.
- UX review includes keyboard-only and narrow-terminal layouts, no-color followed/origin recognition, and stale/empty/error states. Update existing PNG snapshots for intentional UI changes.

## 8. Delivery order and scope

1. **Bounded local reads and portable contracts.** Remove redundant scans; build indexed, owner-resolved summaries; split loader effects from rendering. Define identity, count units, family continuity, handles, capabilities, and operation recovery. These changes should improve local listing even if remote UI is delayed.
2. **One secure vertical slice.** Extend and package the Rust gateway, add authenticated enrollment and the local IPC worker, then read one target through HTTPS. Implement the three-hook adapter and Tailnet discovery/exposure against that same protocol. Prove non-Tailscale operation as part of this slice.
3. **Focus/Fleet reads and Follow.** Add durable subscriptions, cached rows and counts, partial/stale UX, compact intent previews, and remote attention visibility. Read-only remote browsing is an internal milestone; it does not complete the dispatch request.
4. **Reliable dispatch and essential management.** Deliver `%dispatch`, automatic family following, portable launch validation, viewable output, stop and retry with the durable journal. This is the first complete useful release of the requested workflow. Do not postpone launch behind every historical content feature.
5. **Parity expansion.** Add gate/question responses, same-host fork, child creation and richer artifacts using the same action contracts. Ship each only when its target-side semantics and fault tests exist. Optional SSH tunneling and explicit remote terminal integration can follow actual demand.

Do not expand v1 into cross-user process control, automatic scheduling, provider-session migration, replicated agent history, or transitive federation. A simple SSH session remains a good escape hatch, but it cannot provide one working view, automatic following, or consolidated attention—the reasons to build this feature.

The remaining choices are implementation refinements: benchmark-driven page and cache limits, a conflict-free default shortcut, and platform-specific binary supervision. They do not require another product-design decision before proceeding. Any rollout flag or memory/CLI change should follow the corresponding project workflow when implementation begins.

## 9. Evidence map

These repository locations were inspected in the pinned checkouts above. They are implementation pointers, not claims that the proposed interfaces already exist:

| Finding | Source locations |
| --- | --- |
| CLI scan plus child scan; bridge's separate path | `src/sase/agent/running_listing.py`; `src/sase/integrations/agent_list_entries.py`; `src/sase/integrations/_mobile_agent_summary.py` |
| Bounded indexed ACE reads | `src/sase/ace/tui/models/agent_loader.py`; `models/_agent_loader_artifacts.py` |
| Local effects in rendering pipeline | `src/sase/ace/tui/models/_loaders/_running_loaders.py`; `_meta_enrichment_common.py` |
| Provider paging/count contracts and local row keys | `src/sase/ace/tui/provider_contract.py`; `data_providers/_handles.py` |
| Timestamp allocated before submission | `src/sase/ace/tui/actions/agent_workflow/_launch_start.py`; `actions/agent_durable.py` |
| Declarative Pluggy precedent | `src/sase/task_types/_hookspec.py`; `_discovery.py`—including eager `ep.load()`, which dispatch must make demand-driven |
| Current key conflicts and count rendering | `src/sase/default_config.yml`; `src/sase/ace/tui/agent_count_chip.py`; `widgets/agent_info_panel.py` |
| Existing name-based kill resolution | `src/sase/agent/running.py` |
| Pairing, heartbeat-only stream, bridge process | `sase-core: crates/sase_gateway/src/routes.rs`; `host_bridge.rs` |
| Domain/runtime crate separation | `sase-core: crates/sase_core/Cargo.toml`; `crates/sase_gateway/Cargo.toml` |

Project context was read through the audited memory workflow: artifact provenance, tailnet inventory, TUI performance, xprompts/directives, CLI conventions, verification, and agent/family/shell terminology. External protocol claims link directly to primary documentation where used. Historical network and SQL measurements belong to the predecessor reports; they were not re-run on remote machines during this consolidation.

## Recommended solution

**Implement `%dispatch:<machine>` over one Rust-owned remote agent protocol, reached through lazy access-provider plugins. Ship Tailnet enabled for explicit discovery by default, plus HTTPS as the non-Tailscale baseline. Configure and pin each machine separately.**

**Build Focus and Fleet as two views of the existing Agents list.** Focus contains local and followed remote work; Fleet browses the authoritative catalogs of configured remote hosts. Keep Follow as durable viewer intent, mark it with a star and accent, show origin everywhere actions occur, and maintain honest running counts through cheap resolved summaries. Follow logical families across gates and monitors; hydrate content independently and only as needed.

Start with indexed owner-side resolution and a pure presentation boundary, then harden the gateway and establish exact instance identity, durable operation recovery, and portable launch context. Deliver dispatch with automatic following, output viewing, and essential lifecycle controls as one coherent release. This preserves the requested experience while making its difficult cases—sleeping machines, lost replies, family handoffs, stale counts, and changing transports—predictable.
