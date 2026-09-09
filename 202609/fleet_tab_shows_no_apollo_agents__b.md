# Why the Fleet tab shows no Apollo agents (researcher B)

- **Date:** 2026-09-09
- **Epic:** `sase-xe` (open, reopened) → `sase-xe.16` (in progress) → `sase-xe.16.11` (in progress)
- **Question:** Apollo is enrolled and has many done agents, but ACE's Fleet sub-view lists
  nothing. What is causing it, will the open beads fix it, and what should we do?

## Verdict up front

**Your Apollo setup is fine.** Enrollment, credentials, Tailscale Serve, the gateway, the
federation worker, HTTPS, and the authenticated hello all work. I pulled 100 live Apollo
rows over the tailnet during this investigation.

The Fleet tab is empty because of a **client-side wire-contract mismatch in the sase repo**:
the Python code that turns federation responses into TUI rows was written against a
response shape that no Rust code has ever produced. Three independent defects each
sufficient on their own to produce zero rows, plus a fourth that hides the failure from you.

**None of the currently open beads fix this.** The only place it surfaces is the last,
still-blocked phase (`sase-xe.16.11.5`, live Apollo acceptance), and that phase's own
instructions steer a worker toward recording a blocker rather than repairing TUI glue.

## Evidence: the remote side is healthy

```
$ sase machine list
apollo	configured	builtin@tailnet	https://apollo.tail297af1.ts.net
```

Calling the same facade the TUI calls, from the installed runtime:

```python
facade.catalog_sync({"schema_version": 1, "limit": 100, "include_terminal": True})
# -> hosts[0].status == "ok"
#    hosts[0].payload.page.rows        == 100 rows
#    hosts[0].payload.page.total_matching_rows == 152
```

Status distribution of those 100 live Apollo rows:

| field | values |
| --- | --- |
| `status` | DONE 48, TESTED 19, TALE APPROVED 13, EPIC CREATED 4, EPIC APPROVED 4, PLAN TIMED OUT 4, FAILED 3, ANSWERED 2, RUNNING 1, UNKNOWN 1, PLAN REJECTED 1 |
| `status_bucket` | done 76, failed 22, running 2 |
| `row_kind` | agent_shell 36, gate 31, proc 23, monitor 10 |
| `provider` | claude 56, codex 22, grok 22 |

These are exactly the "several done agents showing on the Apollo machine" you referred to.
They reach Athena. They are also already sitting in
`~/.sase/fleet/worker_cache.json`. They simply never reach the widget.

## Root causes

### Defect 1 — The TUI asks for a page size the gateway rejects (hard failure)

`src/sase/ace/tui/actions/agents/_fleet.py:51`

```python
_FLEET_CATALOG_LIMIT = 250
```

`sase-core` caps a catalog page at 100
(`crates/sase_core/src/fleet_contract.rs:68`, `FLEET_READ_MAX_PAGE_ROWS: u32 = 100`;
validated at `fleet_contract.rs:3754`). Reproduced live:

```
limit=100 -> status ok       rows=2   (see Defect 3 for why only 2)
limit=101 -> status invalid  error "fleet catalog limit exceeds 100"  rows=0
limit=250 -> status invalid  error "fleet catalog limit exceeds 100"  rows=0
```

The federation worker forwards the query verbatim
(`crates/sase_gateway/src/federation_worker.rs:1409-1418`); nothing clamps it. So **every**
Fleet catalog read the TUI issues is rejected, and the host result comes back with
`payload: None`.

Note the CLI sibling gets this right — `src/sase/ops/commands/machine.py:135` and
`src/sase/ops/commands/machine_attention.py:115` both send `"limit": 100`.

### Defect 2 — The row-projection code never opens the host `payload` envelope (deeper)

This one matters more, because fixing Defect 1 alone changes nothing.

The Rust worker returns `FederationReadResponseWire`
(`crates/sase_gateway/src/federation_worker.rs:321`):

```jsonc
{"schema_version":1, "operation":"catalog", "hosts":[{
   "schema_version":1, "alias":"apollo", "provider_ref":"builtin:tailnet",
   "installation_id":"sase_inst_v1_…", "endpoint":"https://…",
   "status":"ok", "cached":false, "age_seconds":null,
   "payload":{ "cursor":…, "counts":…, "freshness":…, "page":{"rows":[…]} },
   "error":null }]}
```

The Python traversal in `src/sase/ace/tui/models/_fleet_agents_payload.py:22-34`:

```python
def summary_payloads(host):
    for key in ("summaries", "agents", "rows"):   # never "payload"
        ...
    result = host.get("result")                    # never "payload"
```

`payload` is not in that list, and neither is `payload.page.rows`. So `summary_payloads()`
returns `()` for every real host result. Measured against a live, fully successful
`limit=100, include_terminal=true` response containing 100 rows:

```
host_payloads(catalog)   -> 1
summary_payloads(host)   -> 0
project_fleet_agents(...) -> fleet_rows=0  focus_rows=0  diagnostics=()  counts.fleet=0
```

**A completely healthy Apollo read projects to zero Fleet rows.** The same gap breaks
Focus: `followed_batch` returns `payload.entries[].summary`
(`fleet_contract.rs:601-608`), which `summary_payloads()` also cannot see.

Two details make this unambiguous rather than a judgement call:

1. In the *same module*, `_attention_entries_from_host()` (`_fleet_agents_payload.py:53-58`)
   *does* read `host["payload"]["entries"]`. One of the four consumers was written against
   reality; three were not.
2. `src/sase/ops/commands/machine.py:141-148` descends `host["payload"]["page"]["rows"]`
   correctly. The CLI path works; the TUI path does not.

### Defect 3 — Terminal rows are filtered out by default

`FleetCatalogQueryWire.include_terminal` defaults to `false`
(`fleet_contract.rs:559`), and `summary_matches_catalog_query()` drops any row whose
lifecycle is `Terminal` or `Failed` (`fleet_contract.rs:3322-3327`, `3858`).

`include_terminal` **appears nowhere in the sase Python codebase** — no caller ever sets it.
Live proof, same host, same limit:

```
{"limit":100}                        -> 2 rows   (the RUNNING one + one UNKNOWN)
{"limit":100,"include_terminal":true} -> 100 rows (152 matching)
```

So even after Defects 1 and 2 are fixed, the Fleet tab would show **2 rows**, and none of
your done agents. This directly contradicts the parent plan's own Fleet catalog semantics
(`plan:202609/remote_dispatch_fleet.md:359-361`): *"active + attention-needed + recent
first; older history reachable through paging and explicit filters"*, and
*"deliberately matched to existing local semantics"* — the local Agents tab does show
done agents.

### Defect 4 — The failure is silent, which is why you had nothing to go on

`FederationReadResponseWire` carries only `schema_version`, `operation`, `hosts`. It has no
top-level `diagnostics`, `partial`, or `configured_hosts`. Per-host trouble lives in
`hosts[i].status` and `hosts[i].error`.

The TUI reads none of that:

- `diagnostics_from_response()` (`_fleet_agents_payload.py:69-80`) only looks at a
  top-level `diagnostics` key → always `()`.
- `projection.partial` only looks at a top-level `partial` key → always `False`.
- `_fleet_call()` (`_fleet.py:365-386`) only converts *exceptions* into diagnostics. A
  well-formed response carrying `status: "invalid"` is not an exception.

So an `invalid_request` rejection renders as `"1 machine · 0 results"`
(`_fleet.py:519-539`) with the tab reading `Fleet 0`. That is precisely the acceptance-table
row the parent plan forbids
(`plan:202609/remote_dispatch_fleet.md:552`): *"Unauthorized/incompatible host → Specific
host state and remedy; **never an empty 'successful' catalog**."*

### Defect 5 — The Rust counts path silently falls back for the same reason

`rust_counts_or_fallback()` (`src/sase/ace/tui/models/_fleet_agents_counts.py:17-49`) passes
raw worker host dicts as `fleet_hosts`. The Rust binding expects
`FleetHostCountInputWire = {schema_version, origin, summaries, observed_at_unix, freshness}`
with `#[serde(deny_unknown_fields)]` (`fleet_contract.rs:834-840`). The worker host shape
(`alias`/`provider_ref`/`status`/`payload`/`error`/…) can never deserialize into it, so the
call raises and is swallowed by a bare `except Exception: return fallback`. Confirmed live —
the returned counts dict has no `wire` key, i.e. the Rust path never succeeded.

So the shared Rust counting function that phase `sase-xe.16.11` was built to centralize is,
in practice, dead code on this path.

### Defect 6 — The row adapter is wrong about the row schema too

I patched Defects 1–3 in-process and re-ran the real projection:

```
fleet_rows = 100
   apollo | attempt-0 | RUNNING       | gpt-5.5        None
   apollo | attempt-0 | UNKNOWN       | gpt-5.5        None
   apollo | attempt-0 | FAILED        | grok-4.6       None
   apollo | attempt-0 | EPIC CREATED  | claude-fable-5 None
```

Rows appear — but **every agent is named `attempt-0`** and every provider is `None`.
`_agent_from_summary()` (`_fleet_agents_rows.py:69-166`) is written against an invented
summary shape, not `ResolvedAgentSummaryWire` (`fleet_contract.rs:475-502`):

| Python assumption | Actual wire |
| --- | --- |
| `content` holds `agent_name`, `model`, `patch_name`, `bounded_intent` | `content` is `ContentMetadataWire` — `handle_count`, `total_byte_len`, `kinds`, `supports_range`, `supports_growth` |
| `lifecycle` is a mapping | `FleetLifecycleWire` — a bare string (`"running"`, `"terminal"`) |
| `liveness` is a mapping | `OwnerLivenessWire` — a bare string (`"dead"`) |
| display name from `content.agent_name` | `labels.agent_label` (`"a"`, `"sase-w3.1--code"`) — `labels` is never read |
| provider from `content.llm_provider` / `summary.llm_provider` | `summary.provider` (`"codex"`, `"claude"`) |
| intent from `content.bounded_intent` | `summary.intent` |
| — | `project_name`, `status_bucket`, `row_kind`, `connection_health`, `freshness`, `observed_at_unix`, `needs_attention` all present and mostly unread |

`model` only survives by accident, through a `summary.get("model")` fallback. The
`agent_name` fallback path `exact_key.rsplit(":")[-1]` yields `attempt-0` for every row
because the real `exact_key` ends in `|attempt:9:attempt-0`.

## Why the test suite is green

`tests/ace/tui/fleet_fixture.py:127-170` — the "offline fleet fixture" delivered by phase
`sase-xe.16.7` — **invents** the response shape:

```python
"hosts": [{"alias": alias, "origin": {...}, "freshness": "fresh",
           "connection_health": "online", "counts": host_counts,
           "summaries": summary_list}]          # ← no Rust code emits this
```

plus top-level `configured_hosts`, `diagnostics`, `partial`. Every Fleet test, every Fleet
bench, and the six Fleet/Focus PNG goldens from `sase-xe.16.8` are asserted against that
fiction. `tests/test_dispatch_federation.py:404-410` mocks the *federation worker itself*
with the same invented shape. `tests/ace/tui/test_fleet_agents.py:40-76` hand-writes it again.

There is **no contract test anywhere binding the Python fleet projection to
`FederationReadResponseWire` / `FleetCatalogPageWire` / `ResolvedAgentSummaryWire`.** That
is the systemic root cause: the entire Fleet read path was specified, implemented,
benchmarked, snapshotted and landed without ever being run against a real gateway response.
The `sase-xe.16` landing audit (bead note #1) reached the analogous conclusion about the
setup path — *"the purported host-hang and instance-reuse tests return prewritten mocked
decisions"* — but the read/projection path was never audited the same way.

Note also `#[serde(deny_unknown_fields)]` on the query and count wires: this contract is
strict by design, which is exactly why an untested adapter fails closed and silently.

## Will the open beads fix this?

**No.** Current state of `sase-xe.16.11` (plan `plan:202609/remote_dispatch_landing_remaining.md`):

| Phase | Status | Covers these defects? |
| --- | --- | --- |
| `.1` core-setup-policy | closed | No — Tailnet discovery/enrollment policy into Rust |
| `.2` core-follow-policy | closed | No — followed-family promotion into Rust |
| `.3` real-fault-proofs | in progress | **No.** Real worker/gateway fault tests, but they assert per-host `status` at the worker layer, not through `project_fleet_agents`. Bench work strengthens `bench_tui_jk_fleet.py`, which consumes the *invented* `fleet_fixture` shape — so it re-verifies the fiction. |
| `.4` setup-integration | in progress | No — discovery diagnostics, `machine add`/`repair` activation, chezmoi fallback, "update stale Fleet setup guidance" (that is the zero-machine `action_setup_agent_machine` toast text, not the projection). |
| `.5` live-apollo-acceptance | in progress | **Only by accident.** |

Grepping the whole open plan for `payload`, `catalog`, `rows`, `summaries`, `projection`,
`100` turns up nothing that touches any of the six defects.

Phase `.5` is the one place it must surface, because its acceptance text says (plan line 280):

> Use `sase ace --tmux`, tmux send-keys, and capture-pane to **show Apollo's Fleet rows and
> counts**, follow one into Focus, view output, and stop one of those test agents.

That is unreachable today. But three things make waiting for `.5` a bad plan:

1. `.5` depends on `.4` depends on `.3`. It is the *last* phase and cannot start until the
   others land.
2. The plan's own constraints push a `.5` worker *away* from fixing it: *"Preserve existing
   public behavior except for the identified correctness fixes"* (these are not identified),
   *"Phase workers record new outside-scope findings as `PROPOSED FOLLOW-UP:` notes"*, and
   *"Leave work open on failure and preserve the exact unmet gate."* The likely outcome is a
   blocker note, not a repair.
3. Even a worker who decides to fix it in place would be doing unplanned, unreviewed surgery
   on the row adapter (Defect 6 is not a one-liner) inside an acceptance phase, at the very
   end of a long dependency chain, on a twice-reopened epic.

So the realistic forecast without intervention: `.3` and `.4` land, `.5` runs, Fleet shows
zero rows, `.5` records a blocker, `sase-xe.16.11` / `sase-xe.16` / `sase-xe` all stay open,
and a new phase gets written anyway — several days later than it needs to be.

## Recommended solution

**Land a dedicated fix phase in `sase-xe.16.11` now, ordered before `live-apollo-acceptance`,
and make `.5` depend on it.** Do not file a standalone task bead: the work is squarely inside
this epic's goal ("real … Athena-to-Apollo evidence"), and `.5` cannot pass without it.

Proposed phase — *"Bind the Fleet read projection to the actual federation wire"*, size
medium, `depends_on: [real-fault-proofs]`, inserted before `live-apollo-acceptance`:

1. **Normalize the host envelope in `sase-core`, not in Python glue.** Add one binding —
   e.g. `fleet_normalize_read_response(response) -> {hosts: [FleetHostCountInputWire],
   diagnostics: [...], partial: bool, configured_hosts: int}` — that maps
   `FederationReadResponseWire` (catalog `payload.page.rows`, followed-batch
   `payload.entries[].summary`, summary `payload.counts`) into the host-count input shape the
   Rust counting function already consumes, and lifts each `hosts[i].status`/`error` into a
   typed diagnostic. This satisfies the `rust_core_backend_boundary` memory: the CLI
   (`ops/commands/machine.py:141-148`, `machine_attention.py`) duplicates this traversal
   today, so it is shared backend behavior, not presentation. Both frontends then consume the
   one binding and the duplication goes away.
2. **Fix the row adapter against `ResolvedAgentSummaryWire`.** `labels.agent_label` for the
   name, `summary.provider`, `summary.intent`, `project_name`, string-valued
   `lifecycle`/`liveness`/`connection_health`/`freshness`, per-row `observed_at_unix`, and
   stop treating `content` (`ContentMetadataWire`) as an agent-info blob.
3. **Fix the query.** Derive the page limit from `FLEET_READ_MAX_PAGE_ROWS` rather than
   hardcoding (or clamp client-side and page with `next_cursor` / `has_more`, both of which
   the gateway already returns), and set `include_terminal: true` for the Fleet catalog so
   Fleet matches the local Agents tab and the plan's stated catalog semantics.
4. **Surface per-host failures.** A non-`ok` host status must render as a specific state and
   remedy in the Fleet header, never as `"1 machine · 0 results"`. Stop swallowing the Rust
   counts exception silently — log it, and let a shape error be loud.
5. **Replace the fixture with the real shape, and add the missing contract test.** Regenerate
   `tests/ace/tui/fleet_fixture.py` from actual worker output (a captured golden, or built via
   the Rust wire types), re-record the six Fleet/Focus PNG goldens against it, and add a test
   that drives `project_fleet_agents` from a genuine `FederationReadResponseWire` and asserts
   non-zero rows with correct names/providers. Point the same golden at
   `tests/test_dispatch_federation.py:404-410`. **This test is the actual deliverable** — the
   six defects are cheap to fix and were only expensive to find because nothing pinned the
   two sides together.

**Sequencing note:** steps 3 and 4 alone are a ~20-line change that would already give you a
working, honest Fleet tab today if you want it before the full phase lands — but step 2 is
required for the rows to be *legible* (otherwise 100 rows all named `attempt-0`), and step 1
is what stops this from regressing the next time the wire moves.

**Also worth doing:** phase `.3` should assert its "healthy host remains usable" fault
scenarios *through* `project_fleet_agents` rather than at the worker boundary, and the
strengthened `bench_tui_jk_fleet.py` should run on the corrected fixture. Otherwise `.3`
hardens a path that still cannot produce a row.

## Loose ends noted, not acted on

- `~/.sase/feature_flags.json` still carries `"remote_dispatch": false`. That entry is inert —
  flag bead `sase-xp` ("Retire remote_dispatch") is closed done and the flag no longer appears
  anywhere in `src/sase/`. It is not the cause and needs no action, but it is misleading if
  you go looking.
- `sase machine agent` / `sase machine attention` read the catalog without
  `include_terminal`, so those CLI commands can only target non-terminal remote agents.
  Retrying or forking a *done* remote agent is not currently reachable. Same fix, step 3.
- `/tmp` on athena is a 32 GB tmpfs currently at 100% (largest consumers are stale per-workspace
  cargo target dirs: `sase-cargo-target-sase_20-main` 11 GB, `sase-core-target-sase16` 8.7 GB,
  `sase-conflict-recovery` 1.9 GB). It caused tool-output write failures during this session.
  Unrelated to the Fleet bug, but it will bite other agents.

## Reproduction

Run from any machine with Apollo enrolled, using the installed runtime:

```python
from sase.dispatch.federation import build_federation_facade, load_federation_config
from sase.ace.tui.models.fleet_agents import project_fleet_agents

f = build_federation_facade(load_federation_config())

# Defect 1: exactly what the TUI sends
r = f.catalog_sync({"schema_version": 1, "limit": 250}, timeout_seconds=60)
print(r["hosts"][0]["status"], r["hosts"][0]["error"]["message"])
# -> invalid  fleet catalog limit exceeds 100

# Defects 2/4/5: a fully successful read still projects to nothing
ok = f.catalog_sync({"schema_version": 1, "limit": 100, "include_terminal": True},
                    timeout_seconds=60)
print(len(ok["hosts"][0]["payload"]["page"]["rows"]))          # -> 100
p = project_fleet_agents(catalog_response=ok, local_agent_count=5)
print(len(p.fleet_rows), p.diagnostics, p.counts["fleet"])     # -> 0 () 0
```
