# Why Apollo's agents do not appear in ACE Fleet

Research snapshot: 2026-09-09 08:15 EDT  
Researcher: A  
Scope: current Athena/Apollo state, the `sase-xe` bead tree, the shipped SASE and
`sase-core` implementations, and the active follow-up plan.

## Executive conclusion

Apollo is now enrolled and reachable enough for remote dispatch: Tailscale Serve is
active, Athena's authenticated `sase machine status apollo -j` succeeds, and the gateway
returns real fleet data. The empty Fleet view is caused by SASE implementation defects,
not by a remaining Apollo enrollment error.

There are two independently sufficient causes of an empty Fleet view:

1. ACE requests a catalog page of 250 rows, but the version-1 gateway contract rejects
   any page larger than 100. The live response is `invalid_request: fleet catalog limit
   exceeds 100`.
2. Even when the request is corrected to 100 and Apollo returns rows, ACE's projection
   adapter does not understand the real federation response shape. It looks for rows at
   `hosts[].summaries`; the worker returns them at `hosts[].payload.page.rows`. A direct
   projection of a successful live response still produces zero rows.

Two further defects explain why the UI provides no useful clue and why the user's done
agents would remain absent after only the first two fixes:

- ACE ignores `hosts[].error` and derives partial/error state only from top-level fields,
  so the rejected request is rendered as an apparently clean empty Fleet.
- ACE omits `include_terminal`; its protocol default is false. Recent `DONE`/`FAILED`
  agents are therefore intentionally excluded by the gateway. ACE also does not follow
  catalog cursors, despite the original plan requiring viewport-driven paging.

The active `sase-xe.16.11.5` live-Apollo phase cannot honestly pass its Fleet acceptance
without finding and fixing the zero-row defects. However, none of the open bead scopes
or notes names the catalog limit, real response-shape adaptation, terminal visibility,
or paging. The live phase will probably expose the empty-Fleet blocker, but it may pass
after showing a newly launched active agent and still leave completed/history behavior
broken. These findings should therefore be attached to the active epic now rather than
left for incidental discovery.

## Current machine state

The earlier `sase-xe.16.10` blocker is no longer the current cause:

- `sase machine list -j` on Athena contains one non-quarantined `apollo` record at the
  tailnet HTTPS endpoint.
- `sase machine status apollo -j` succeeds with `state: ok`, `message: hello ok`, fleet
  protocol 1, and the catalog/summary/content/mutation capabilities.
- `sase machine discover -j` classifies Apollo as compatible and reports the fleet-v1
  health advertisement.
- Apollo's `tailscale serve status` now proxies its tailnet-only HTTPS root to
  `http://127.0.0.1:7629`.
- Apollo's loopback health endpoint returns `status: ok`, service `sase_gateway`, and
  fleet protocol 1.

There is process-version drift worth cleaning up, but it does not explain the contract
mismatch. Apollo's installed SASE reports host `0.17.1+291.gce344836d` and core
`0.32.53+1.gcb669ec96`, while the still-running transient gateway reports core 0.32.48.
Athena's already-running federation worker reports 0.32.52 while its installed core is
0.32.53. The page maximum is still 100 on current core commit `cb669ec96`, so restarting
these processes is good hygiene but will not make Fleet work.

`sase doctor -D -C dispatch` currently reports OK because it checks configuration, not
a catalog read/projection. Likewise, `machine status` proves authenticated hello, not
that ACE and the catalog contract interoperate. This explains why setup can look correct
while Fleet remains empty.

## Live reproductions

All probes used the enrolled credential through the normal local federation facade;
no credential or bootstrap secret was printed or recorded.

### 1. The exact ACE request is rejected

ACE defines `_FLEET_CATALOG_LIMIT = 250` and submits:

```json
{"schema_version": 1, "limit": 250}
```

The live Apollo host response is:

```text
host status: invalid
error code: invalid_request
message: fleet catalog limit exceeds 100
payload: null
```

This is a permanent cross-layer contract mismatch, not old-gateway skew:

- SASE: `src/sase/ace/tui/actions/agents/_fleet.py:50,327-332`
- Current core: `crates/sase_core/src/fleet_contract.rs:64-68,3745-3758`
- The values were introduced independently in the original phase commits:
  `e2fc10c3c` (`sase-xe.11`, UI) and `949266359` (`sase-xe.5`, gateway reads).

### 2. A legal nonterminal catalog request returns data

Changing only the live probe to `limit: 100` succeeds. Apollo returns two nonterminal
rows. The gateway snapshot reports 152 input rows, one logical running agent, and zero
occupied runner slots. This proves that enrollment, authentication, federation, the
gateway, and the remote artifact index all work.

### 3. Recent completed rows exist and are protocol-visible

A legal request with `limit: 100, include_terminal: true` succeeds and reports:

```text
total_matching_rows: 152
page row count:       100
has_more:             true
next_cursor:          off:100
DONE rows on page 1:  48
```

This agrees with `sase agent list --all --json` on Apollo, which shows many recent
completed agents. The gateway is not missing the data; ACE is not requesting terminal
rows and is not consuming continuation pages.

The relevant protocol behavior is explicit in current core:

- `FleetCatalogQueryWire.include_terminal` defaults false:
  `crates/sase_core/src/fleet_contract.rs:547-561`.
- Terminal lifecycle rows are filtered when the flag is false:
  `crates/sase_core/src/fleet_contract.rs:3847-3864`.
- The gateway snapshot does load recent completed records (up to 512):
  `crates/sase_gateway/src/fleet_reads.rs:503-520`.

### 4. ACE cannot project a successful real response

Passing either successful live response above to `project_fleet_agents()` yields:

```text
fleet_rows: 0
counts.fleet: 0
configured_host_count: 1
partial: false
diagnostics: []
```

The mismatch is visible in source:

- `summary_payloads()` only recognizes `summaries`, `agents`, `rows`, or nested
  `result`; it never traverses `payload.page.rows`:
  `src/sase/ace/tui/models/_fleet_agents_payload.py:21-32`.
- `diagnostics_from_response()` reads only top-level `diagnostics`, while live worker
  failures are carried per host in `hosts[].error`:
  `src/sase/ace/tui/models/_fleet_agents_payload.py:55-67`.
- `project_fleet_agents()` similarly derives `partial` only from top-level response
  flags: `src/sase/ace/tui/models/fleet_agents.py:42-91`.
- The offline UI fixture constructs `hosts[].summaries`, not the worker's real envelope:
  `tests/ace/tui/fleet_fixture.py:128-170`. Its tests therefore validate a synthetic
  shape and cannot catch this integration failure.

After row traversal is fixed, the row adapter should also be audited against the real
row schema. Real records put the display name under `labels.agent_label`, use direct
`project_name`, `provider`, and `intent` fields, and carry the origin installation ID on
the host. The current adapter primarily expects older/top-level aliases such as
`agent_name`, `llm_provider`, and `bounded_intent`. Without a complete shape audit, rows
may render with opaque locator-derived names or missing metadata.

## Contract against the original epic

The result does not meet the original `sase-xe` plan, even if “Fleet only shows active
agents” were treated as a product choice:

- `plan:202609/remote_dispatch_fleet.md` defines Fleet as the union of enrolled hosts'
  authoritative catalogs.
- Its catalog semantics say active, attention-needed, and recent rows come first, with
  older history reachable through paging and explicit filters.
- It requires the first/visible catalog page plus additional pages requested by the
  viewport and says host errors must not masquerade as an empty successful catalog.
- `plan:202609/fleet_ui.md` specifically requires parsing real federation summary,
  catalog, and followed-batch responses, honest empty/unavailable states, and paging.
- The user documentation says Fleet loads up to 250 remote rows, but a single protocol
  page is capped at 100 and the implementation issues only one request.

Thus this is unfinished epic work rather than a new optional feature.

## Will the currently open beads fix it?

Current state at the research snapshot:

| Bead | State | Relevant scope | Assessment |
| --- | --- | --- | --- |
| `sase-xe.16.11.3` | in progress; monitor running | Real gateway/worker deadline, fencing, bootstrap tests; Fleet fault benchmark | Does not explicitly exercise the ACE-to-real-catalog response contract. It might expose the limit only if the strengthened benchmark stops using synthetic responses, but that is not stated. |
| `sase-xe.16.11.4` | in progress, waiting on `.3` | Rust policy adapters, discovery truth, durable activation, setup guidance, core pin | No catalog query/projection or terminal/paging scope. Do not expect it to fix this. |
| `sase-xe.16.11.5` | in progress, waiting on `.4` | Live Athena-to-Apollo launch plus Fleet/Focus follow, content, stop, and restart proof | The two zero-row defects block its explicit acceptance, so a correct phase completion must fix or escalate them. It does not explicitly require recent completed rows or multi-page history, so those can still be missed. |
| `sase-xe.16.11.land` | waiting | Child-epic landing audit | Can reject an incomplete `.5`, but only if the defect is made visible in phase evidence. |

Searches across all bead statuses for `fleet catalog limit`, `include_terminal`, `250
remote rows`, and `exceeds 100` returned no matches. No current note explicitly owns
these findings.

Confidence is high that `.5` will encounter the empty-Fleet failure if it performs the
required live TUI proof. Confidence is low that the swarm will fix terminal/history and
paging semantics without an explicit note, because newly launched active agents are
enough for the narrow live demonstration once the request and response-shape blockers
are repaired.

## Recommended solution

Treat this as a blocking `DISCOVERED ISSUE` on the active child epic
`sase-xe.16.11` (and point phase `.5` at it) rather than creating a detached task bead.
Attach this research artifact and require the live phase/land agent to preserve all four
parts of the fix:

1. **Honor protocol bounds.** Send catalog pages no larger than
   `FLEET_READ_MAX_PAGE_ROWS` (currently 100). Do not raise the gateway cap merely to
   match an accidental UI constant.
2. **Adapt the real wire envelope.** Decode `hosts[].payload.page.rows`, followed-batch
   entries, host counts/freshness/origin, direct row fields, and `hosts[].error` into the
   presentation model. Mark any failed/invalid host partial and visible rather than
   presenting a clean zero-result state.
3. **Restore promised catalog semantics.** Request `include_terminal: true` for Fleet so
   the gateway's bounded recent-completed tier is visible, and consume per-host cursors
   incrementally to the UI's overall 250-row bound (or revise the documented behavior
   through an explicit product decision). Focus should continue to resolve followed
   completed agents under the normal recent/history rules.
4. **Add a cross-layer regression.** Feed a response serialized by the actual gateway/
   federation worker into the ACE projection and assert real active and recent-DONE rows,
   legal page sizes, continuation, and visible per-host validation errors. Synthetic
   `host.summaries` fixtures alone are insufficient. A deep dispatch doctor/catalog
   smoke check would also prevent “hello OK, Fleet broken” from looking healthy.

Then restart the installed gateway, federation worker/AXE, and ACE on both machines and
rerun the `.5` live proof. Acceptance should show at least one live remote launch and a
known recent completed Apollo agent, follow/view/stop the test launch, traverse the
second page or prove its cursor, and recover after a gateway restart.

There is no configuration-only fix for the current TUI. Until the code lands, SSH to
Apollo and `sase agent list --all` is the reliable read-only workaround. Restarting the
stale processes is advisable, but by itself it cannot fix the hard-coded 250-vs-100
request or the response adapter.

## Evidence consulted

- Live read-only commands on Athena and Apollo: SASE versions, machine inventory,
  authenticated status, discovery, deep dispatch doctor, Tailscale Serve status,
  loopback gateway health, Apollo agent listing, federation health/summary/catalog, and
  ACE projection of live responses.
- Beads `sase-xe`, `sase-xe.16`, `sase-xe.16.10`, and
  `sase-xe.16.11{,.3,.4,.5}` plus their dependencies and current agent status.
- Audited plans `plan:202609/remote_dispatch_fleet.md`,
  `plan:202609/fleet_ui.md`, `plan:202609/gateway_reads_1.md`, and
  `plan:202609/remote_dispatch_landing_remaining.md`.
- SASE checkout `cef06cdcad1c34723d9f1ce1d9c9bce013624fed` and opened `sase-core`
  checkout `cb669ec96526294cb14b07cd936c28b8b39be9bc`.

