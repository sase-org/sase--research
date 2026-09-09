# Apollo Fleet visibility requires a wire-contract repair

Research snapshot: September 9, 2026, 08:28–08:35 EDT. This report combines
[researcher A](apollo_fleet_contract_repair__a.md),
[researcher B](apollo_fleet_contract_repair__b.md), and independent source review and
live probes by the lead researcher.

**Apollo's enrollment and authenticated read path work. ACE's Fleet integration is
broken.** Two defects independently prevent any catalog rows from appearing: ACE asks
for a page larger than the gateway permits, and its projection does not understand the
response envelope the federation worker actually returns. Another omission excludes
completed agents even after those blockers are repaired. Host errors are discarded,
which makes these failures look like an empty, successful catalog.

The remaining epic work includes a live acceptance phase that should expose this
failure. It does **not** explicitly assign its repair. Waiting for the existing workers
is therefore not a reliable resolution. The repair belongs inside active child epic
`sase-xe.16.11`, before its live Apollo acceptance gate.

The two researchers agree on the mechanism. Their disagreement is chiefly a forecast:
A expects acceptance to force a fix or escalation; B expects an out-of-scope blocker.
Both are possible. The defensible conclusion is that acceptance must detect the defect,
but no current scope guarantees that a worker will repair it.

The lead's probes used this SASE checkout at `27bbd2f4e4bcab9c364b175ad44c3fa24e13250d`,
with its Python source selected explicitly, the installed Rust extension, and the
normal authenticated federation facade. Current Rust source was independently reviewed
in the opened core checkout at `7af26400fbca87eb70102c7082a1b029c65e310b`. No production
source, machine enrollment, follow subscription, or remote agent lifecycle was changed.
No predecessor chat transcripts were read.

The live observations establish the following:

| Probe | Result | Meaning |
| --- | --- | --- |
| `sase machine status apollo -j` | `state: ok`, `hello ok`, protocol 1 and Fleet capabilities | Athena can authenticate to the enrolled Apollo installation. |
| SSH: `tailscale serve status` | Tailnet HTTPS root proxies to `127.0.0.1:7629` | The earlier missing-Serve blocker is no longer present. |
| Apollo loopback `/api/v1/health` | Gateway healthy, protocol 1 | The gateway process is serving. |
| Catalog, `limit: 250` | Host `invalid`; `invalid_request: fleet catalog limit exceeds 100` | The request ACE actually sends is rejected. |
| Catalog, `limit: 100` | 2 rows: `RUNNING`, `UNKNOWN` | Valid nonterminal reads work. |
| Catalog, `limit: 100, include_terminal: true` | 100 rows, 152 matches, `next_cursor: off:100` | Recent completed records are available remotely. |
| Same query, `cursor: off:100` | 52 rows, no next page | Both available pages were retrieved successfully. |
| Unmodified ACE projection of either successful page | 0 Fleet rows, no diagnostics, `partial: false` | Network success still cannot produce UI rows. |

The two pages contained **90 records whose status was exactly `DONE`**: 48 on the first,
42 on the second. These are catalog records, including historical shells and other row
kinds, not 152 distinct running agents. The same responses reported **one logical
running agent and zero occupied runner slots**. Those distinctions matter when testing
the eventual count fix.

Process versions differ: the live Apollo gateway reported core 0.32.48; Athena's worker
reported 0.32.52; Athena's installed extension reported `0.32.53+1.gcb669ec96`.
Researchers also observed installation/process drift. Refreshing these processes after
deployment is appropriate, but the current core source still caps pages at 100 and the
current Python source still has the mismatches below. Restarting alone cannot repair
them. Likewise, a successful machine status or deep doctor's hello check does not test
catalog decoding. These observations verify the read path, not the entire remote
launch/stop workflow; that remains the live acceptance phase's responsibility.

The failure chain is concrete and reproducible:

1. **The catalog query violates the contract.** `_FLEET_CATALOG_LIMIT = 250` is sent as
   the size of one request. Core's `FLEET_READ_MAX_PAGE_ROWS` is 100, and the worker
   forwards the catalog query without clamping. `docs/ace.md` describes up to 250 remote
   rows, but an overall UI bound and a protocol page limit are separate quantities.
   The correct implementation must request legal pages.

2. **The response adapter reads the wrong fields.** The worker returns catalog rows
   under `hosts[].payload.page.rows`. `summary_payloads()` accepts `summaries`, `agents`,
   `rows`, or a nested `result`; it never enters `payload.page`. The followed-batch
   response instead contains `hosts[].payload.entries[].summary`, which this traversal
   also misses. A summary response carries counts and freshness, not a catalog of rows.

3. **Completed rows are excluded by the request.** `include_terminal` defaults to false
   in `FleetCatalogQueryWire`, and ACE omits it. This accounts for the difference between
   2 and 152 matching records. It is not, by itself, the cause of zero rows in this live
   snapshot because two nonterminal records exist. It would still hide the done agents
   the user wants after the first two defects were fixed. The parent plan explicitly
   includes active, attention-needed, and recent records, and applies normal
   recent/history rules to completed follows.

4. **Failures are presented as clean emptiness.** Worker host results carry `status`
   and `error`. ACE looks for top-level `diagnostics` and `partial` instead. A valid IPC
   response containing a rejected host request does not raise an exception, so the
   exception handler cannot rescue this case. Host errors, cached age, and payload
   freshness/partial state need deliberate projection into the visible host state.

5. **Unwrapping rows alone produces unusable metadata and counts.** In a temporary
   in-process experiment, changing only row traversal exposed 100 rows, all named
   `attempt-0`, all with provider `None`, and all missing the host installation ID.
   Real names come from `labels.agent_label`, provider from `provider`, intent from
   `intent`, and origin from host `installation_id`. Lifecycle and liveness are enum
   strings. `content` describes available content; it is not an agent metadata object.
   The adapter must map `ResolvedAgentSummaryWire` completely, including project,
   freshness, observation time, capabilities, and the original locators/revisions.

6. **The Rust counting call receives an incompatible host object.** The live call fails
   with `unknown field alias, expected one of schema_version, origin, summaries,
   observed_at_unix, freshness`. ACE swallows that exception and falls back to the
   number of projected rows. After traversal alone was patched, its Fleet count became
   100 even though the authoritative running count was one. Simply converting each
   catalog page into `FleetHostCountInputWire` is also insufficient: running counts
   must not depend on the current page or search filter. Use authoritative host
   `payload.counts` for Fleet aggregation and the complete bounded followed set for
   remote Focus counts, with shared Rust semantics and explicit unknown/stale hosts.

The lead found **an additional Focus request defect absent from both reports**.
`_run_agents_fleet_refresh()` submits a followed-batch request containing
`logical_locators`. The worker requires `FleetLogicalBatchRequestWire.logical_keys`.
A live probe of a known completed record, `2--code`, returned its `DONE` summary when
sent with `logical_keys`. Sending the equivalent locator using ACE's request shape
raised `FederationWorkerUnavailable: federation worker returned a mismatched request_id`.
Source explains the misleading message: strict frame deserialization fails, the worker
uses the placeholder request ID `<frame>` for that error, and Python rejects the ID
before inspecting the underlying validation error. Thus fixing catalog traversal and
followed-response traversal still leaves Focus refresh broken until the request is
corrected. Unlike the silent per-host catalog rejection, this exception does enter
ACE's unavailable-diagnostic path.

The regression gap is at the boundary between independently tested layers.
`tests/ace/tui/fleet_fixture.py` constructs `hosts[].summaries`, mapping-valued liveness,
and an invented content metadata layout. The facade test in
`tests/test_dispatch_federation.py` similarly mocks a worker response containing
`summaries`. These fixtures agree with the Python adapter but disagree with the real
worker and core types. They can support passing UI tests and screenshots while live
integration returns no rows. The inspected coverage does not establish the missing
request-to-worker-to-projection contract; acceptance needs that proof explicitly.

For implementation review, the principal source anchors are:

| Concern | SASE source | Core source |
| --- | --- | --- |
| Requests and refresh | `src/sase/ace/tui/actions/agents/_fleet.py:50,280–343` | `crates/sase_gateway/src/federation_worker.rs`: `FederationIpcRequestWire`, `read_remote` |
| Response/error shape | `src/sase/ace/tui/models/_fleet_agents_payload.py:10–95`; `fleet_agents.py:42–121` | `crates/sase_gateway/src/federation_worker.rs:320–340` |
| Row fields | `src/sase/ace/tui/models/_fleet_agents_rows.py:40–205` | `crates/sase_core/src/fleet_contract.rs:475–502` |
| Query, batch, and page contracts | Same refresh caller | `crates/sase_core/src/fleet_contract.rs:548–611,3745–3759,3847–3864` |
| Counts | `src/sase/ace/tui/models/_fleet_agents_counts.py:11–49` | `crates/sase_core/src/fleet_contract.rs:834–850`; `count_focus_and_fleet` |
| Bounded recent tier | — | `crates/sase_gateway/src/fleet_reads.rs:503–520` |

The gateway snapshot includes active and bounded recent-completed records, with a
recent limit of 512 and `include_full_history: false`. Following the second cursor proved
access to all 152 records in this snapshot; it did **not** prove arbitrary archive
history. Preserve that distinction in documentation and acceptance. The immediate
repair should recover the user's known recent done agents; any claim of full older
history also needs a tested history-query path.

The current work allocation comes from audited reads of
`bead:sase-xe`, `bead:sase-xe.16.11`, and phases `.3`, `.4`, `.5`, together with
`plan:202609/remote_dispatch_landing_remaining.md`. Live `sase agent list -j` distinguishes
preassigned `in_progress` beads from workers actually running:

| Work | Observed runtime state | Expected effect on this issue |
| --- | --- | --- |
| `sase-xe.16.11.3`, real fault proofs | Successor `--2` running at 08:28; monitor `--mon-1` waiting for load by 08:34 | Covers worker/gateway deadlines, fencing, bootstrap, and fault benchmarks. It could expose a boundary failure if coverage reaches ACE, but repair is not assigned explicitly. |
| `sase-xe.16.11.4`, setup integration | Waiting on `.3` | Covers discovery, activation, Rust policy adapters, and setup guidance. These do not repair catalog/Focus request and response schemas. |
| `sase-xe.16.11.5`, live Apollo acceptance | Waiting on `.4` | Must demonstrate Apollo Fleet rows/counts, follow into Focus, output, stop, and restart recovery. It cannot pass honestly today; it may fix or report a blocker. |
| `sase-xe.16.11.land` | Waiting on the child phases | Must reject incomplete acceptance and preserve the parent epic's catalog/count semantics. |

The open phase descriptions and notes at inspection time did not name these contract
defects. Searches across task statuses and a sweep of the last week's tasks found no
dedicated duplicate; broad matches were unrelated supervisor records. This is unfinished
work from the remote-dispatch epic, so its existing child epic is the appropriate owner.
The facts support neither a promise that current workers will fix it nor a prediction
of a particular delay. They do support assigning it explicitly now. A proof using only
a newly launched active agent would still miss terminal filtering, history paging, and
page-independent counts.

Both input reports were identified by dependency name and existing canonical suffix,
not list order, and preserved byte-for-byte in this directory:

| Dependency | Preserved report | Immutable registered reference |
| --- | --- | --- |
| `research.1p.cdx` | `apollo_fleet_contract_repair__a.md` | `file:explicit:5d1b6cb9ad19ebb5b6fd716f` |
| `research.1p.cld` | `apollo_fleet_contract_repair__b.md` | `file:explicit:b9ae70a15789da7c18cbf16c` |

Their original canonical labels were respectively
`research:202609/apollo_fleet_empty_catalog_contract_mismatch__a.md` and
`research:202609/fleet_tab_shows_no_apollo_agents__b.md`; both were read through
`sase artifact read` before relocation. The original plan
`plan:202609/remote_dispatch_fleet.md` was also read through that audited command and is
the basis for the recent/history, failure-visibility, and authoritative-count requirements.

**Recommended solution:** assign a dedicated Fleet/Focus contract repair within
`sase-xe.16.11`, explicitly ordered before live acceptance `.5`, and record this report
as a blocking discovered issue for the epic's landing audit. Retain the existing setup
work. Implement the repair as one coherent cross-repository change:

1. Put shared request validation, response normalization, diagnostic/freshness handling,
   and count aggregation in Rust core with a thin Python binding. Keep Textual row
   construction and rendering in Python. Establish the shared wire types without making
   the transport-free core depend on the gateway crate.
2. Request catalog pages of at most 100, include recent terminal records, and consume
   per-host cursors on demand. Treat 250 as a possible overall UI/cache bound, never a
   page size or a reason to silently make later results unreachable. Correct followed
   batch requests to use logical keys and decode their summary entries.
3. Map real display fields and preserve authoritative origin, exact identity, revisions,
   capabilities, and observation state. Surface host failures and schema errors; replace
   the silent row-count fallback with correct authoritative running counts that remain
   unchanged when pages or filters change.
4. Add regression coverage using actual serialized worker/gateway envelopes. Exercise the
   **ACE-generated requests**, not just hand-authored legal requests, and assert active
   plus recent-DONE rows, readable names/providers, completed follows outside page one,
   legal pagination, accurate counts, and mixed healthy/failed hosts. Update UI fixtures,
   affected goldens, and fault benchmarks to consume that real shape. Query/error-only
   patches cannot produce a working view while envelope decoding remains broken.
5. Publish/install matching host and core builds, refresh the gateway/worker/AXE and ACE
   processes, and rerun `.5` with live pane evidence. Require a known recent completed
   Apollo agent as well as a new active launch, follow/output/stop, a second-page check,
   honest failure presentation, and recovery in the same ACE session after gateway
   restart. Preserve hidden-Fleet and zero-machine laziness and the navigation budget.

Until that lands, use `ssh apollo 'sase agent list --all'` to inspect Apollo's agents.
There is no configuration-only fix for the reproduced Fleet failures. Make this explicit
repair a prerequisite for accepting the remote-dispatch epic.
