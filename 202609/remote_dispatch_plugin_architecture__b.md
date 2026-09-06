# Remote Dispatch As A Plugin Seam: Discovery, Channels, `%machine`, And One Agents List

## Research question

How should SASE dispatch agent launches to, and manage agents on, remote machines —
generalized behind the existing plugin architecture rather than hard-wired to Tailscale,
lazy enough not to tax the TUI, and expressed through a UX that is intuitive, reliable,
and beautiful? Where is the proposed design (Local/Remote subtabs, subscription,
`%dispatch:<machine>`) right, and where is there a better way to reach the same goal?

## Provenance and method

Researcher B of a two-researcher swarm; conclusions are my own. Prior research read as
context, in the order the user specified:
`research:202609/tailnet_agent_fleet/tailnet_agent_fleet.md`,
`research:202609/sase_collaboration_architecture.md`, and
`research:202609/tailnet_fleet_federation/tailnet_fleet_federation.md`.

Everything in §2 was measured or read by me on **athena, 2026-09-06**, against `sase` @
`58f16fe68` and `sase-core` @ `0504155`. Where my measurements contradict the prior
reports I say so explicitly and show the numbers (§2.1 is the important one). I did not
consult the peer researcher's report.

---

## 1. Executive summary

**The proposed feature is worth building, the plugin instinct is right, and two of the
three UX requirements should change.** Concretely:

1. **Make the plugin seam narrower than "dispatch."** A dispatch provider that owns
   discovery *and* transport *and* remote agent semantics would produce N
   implementations of liveness, staleness, and idempotency — the exact drift the
   `rust_core_backend_boundary` core memory forbids. Ship **two hooks only**:
   `remote_discover_machines()` (read-only, `sase init`-time) and
   `remote_open_channel(machine)` (returns an authenticated stream to that machine's
   sase host endpoint). Everything above the channel — wire, row model, liveness,
   journal, admission — is core and identical for every provider. Ship three built-ins:
   `manual`, `ssh`, `tailscale`. Tailscale is then genuinely optional, and SSH is the
   honest universal default.

2. **The config field should be per machine, not global.** A single
   `dispatch.provider: tailscale` cannot express the normal case — a tailnet laptop, a
   work box reachable only over SSH, a cloud VM behind a URL. Use
   `machines.<name>.via:` for transport and `machines.discovery: [tailscale, ssh_config]`
   for which providers `sase init` consults.

3. **Rename the directive and give it `%model`'s grammar.** `%dispatch:<machine>` names
   the mechanism; every other SASE directive names the intent. **`%machine:<name>`** (or
   `%on:` as a short spelling) is the right name, and modelling its argument grammar on
   `%model` — bare name, `@pool` alias, keyword options — buys machine fan-out for free
   through the existing `%alt` machinery: `%{%machine:apollo | %machine:athena}`. That
   symmetry ("`%machine` is `%model` for hardware") is the single most delightful thing
   available in this design space, and it costs nothing extra.

4. **Do not split the Agents tab into Local and Remote panes.** Machine is an *attribute*
   of a run — like project, model, status, and tribe, all of which SASE already handles
   with grouping modes and query facets, not with tabs. Instead: add `machine:` to the
   query allowlist, add `BY_MACHINE` to the grouping cycle, and put a one-line **machine
   strip** in the existing `AgentInfoPanel`. If the user still wants the two labelled,
   counted entry points, implement them as **view presets over one list** (§6.4) — same
   widget, same provider, same counting code — so the counts can never disagree and
   switching is a refilter, not a reload.

5. **Delete "subscription" as a user-facing concept.** Subscription is manual cache
   management for a problem the measurements say does not exist: a full running-agent
   snapshot is **28 KB** and tailnet RTT is **10–33 ms**. What is expensive is *reading
   agent state at all* (§2.1), and that cost is paid per machine whether you subscribed
   or not. Replace subscription with **tiered hydration** (invisible) plus a
   **dispatch receipt** (automatic): the runs you launched are yours by construction, so
   `%machine` needs no auto-subscribe rule — the receipt already exists locally the
   instant you press enter.

6. **Fix the local read path before writing one line of network code.** This is the
   finding that changes the plan the most, and it contradicts both prior reports.

---

## 2. What I measured, and where the prior reports are wrong

### 2.1 The bottleneck is not the fork, and it is not interpreter startup

Both predecessor reports state that remote reads are slow because the gateway forks a
Python interpreter per request — "interpreter startup dominates," "the fork is the entire
problem," "~3.8 s → milliseconds by making reads resident in Rust." **That diagnosis does
not survive measurement on athena today.**

| Measurement (athena, 2026-09-06, repeated) | Result |
| --- | --- |
| `sase version` (full CLI start: argparse, plugin entry points, Rust binding) | **0.32 s** |
| `python3 -c "import sase"` | **0.078 s** |
| `sase agent list --json` (19 live agents, 28,179 bytes) | **10.9 s** |
| — of which `sase_core_rs.scan_agent_artifacts` (**already Rust**), 2 calls | **7.36 s** |
| — of which Python wire conversion of 23,330 records | **~3.0 s** |
| `query_agent_artifact_index(...)` for the same `ace-run` corpus | **0.579 s**, 802 records |
| Raw SQL status aggregation over the index | **15.2 ms** |
| `~/.sase/agent_artifact_index.sqlite` | **195 MB**, 9,506 rows, 40,507 dismissed |
| Directories under `~/.sase/projects` | **37,663** (11,786 timestamped run dirs) |

Three consequences, in descending order of importance:

**(a) Keeping a process warm saves 0.32 s of a 10.9 s problem.** A resident daemon is not
the fix. It was never going to be the fix. The 7.36 s is a *filesystem walk over 37,663
directories, performed in Rust, twice per call* — once by `list_running_agents()` and
again by `_children_by_parent_timestamp()`, which exists only to compute child counts
(`src/sase/integrations/agent_list_entries.py:177`,
`src/sase/agent/running_listing.py:119`). Both call `scan_agent_artifacts`, not the
index.

**(b) ACE already solved this; the CLI did not.** The TUI loads through
`query_agent_artifact_index` (`src/sase/ace/tui/models/agent_loader.py:130`) and is fast.
`sase agent list` — and therefore `sase mobile agent-bridge`, and therefore every gateway
read (`src/sase/integrations/_mobile_agent_summary.py:54` → `list_running_agents`) —
takes the scan path. **The "remote reads are slow" problem is, right now, "the remote
read path is the one path in the tree that ignores the index ACE already uses."**

**(c) Therefore Phase 0 is local, needs no network, and is worth ~10 s today.** Point the
listing path at the index, and stop scanning twice. Every remote read inherits the fix.
Nothing else in this design produces a comparable return, and it is independently a live
performance bug in `sase agent list` for a user who never enables a single remote
machine.

I want to be precise about what this does *not* overturn: the predecessor recommendation
to serve reads in-process from Rust rather than by forking a CLI is still correct, and the
transport conclusion (HTTP/JSON + SSE over the existing gateway, no ZeroMQ/NATS/gRPC) is
still correct. What changes is the *ordering and the expected payoff*: you cannot get to
milliseconds by removing a fork, because the fork is 3% of the cost. You get there by
querying the index and resolving liveness for the ~19 rows that matter.

### 2.2 Liveness cannot be inferred from stored state — 99% of "active" rows are phantom

| | Count |
| --- | --- |
| Index rows with an active status (`running` 1,170 + `waiting` 660 + `starting` 37) | **1,867** |
| Agents actually alive (`sase agent list --json`) | **19** |
| Phantom rate | **99.0%** |

A viewer that trusts a remote machine's stored status renders ~1,850 agents that do not
exist. This corroborates the federation report's measurement (1,871/27 on 2026-09-05)
independently, one day later, on a machine that has run agents since. **Liveness must be
a verdict resolved by the owning machine and shipped on the wire with its resolution
timestamp**; a remote PID must never reach a local process-table check. This is
non-negotiable and it is the single most likely way this feature becomes untrustworthy.

### 2.3 Tailnet device names are not SASE machine names — and cannot be

Measured on this tailnet (`tailscale status --json`):

| Tailscale `HostName` | `DNSName` | OS | SASE machine name |
| --- | --- | --- | --- |
| `athena` | `athena.tail297af1.ts.net.` | linux | `athena` |
| `apollo` | `apollo.tail297af1.ts.net.` | linux | `apollo` |
| `Kelly's MacBook Pro` | `kellys-macbook-pro.tail297af1.ts.net.` | macOS | `kellys_mbp` |
| `Pixel 10 Pro XL` | `pixel-10-pro-xl.tail297af1.ts.net.` | android | **unrepresentable** |

SASE machine names are validated `^[a-z_]+$` (`src/sase/config/identity.py:21`,
`sase_core::machine_hood::validate_machine_name`) — no digits, no hyphens. Tailscale
hostnames carry spaces and a Unicode right single quote; DNS names carry hyphens and
digits. `pixel-10-pro-xl` has **no legal SASE machine name at all**.

Both prior reports assume machine identity ports across the two systems ("the node is the
machine name"). It does not. The discovery hook must therefore return a *candidate* — a
provider-native id, a display label, an address, an OS, an online flag — and enrollment
must obtain the authoritative `machine_name` from **the remote machine's own
`id.machine_name`, over the channel, in a handshake**. That is also how you learn that a
discovered device is not a SASE host at all (the Pixel: discovered, handshake fails,
recorded as "no sase host" rather than silently enrolled), and it gives identity pinning
for free.

### 2.4 Gateway readiness: verified gaps

Re-read directly in `sase-core` @ `0504155`:

- **`pair_start` is unauthenticated and returns the pairing code in its own response
  body** (`crates/sase_gateway/src/routes.rs:563-592` — no `authenticate()` call, `code`
  is a response field). Loopback binding is the only thing that makes this safe today.
  Publishing the gateway to the tailnet makes loopback tailnet-reachable, which is
  precisely the deployment this feature wants. **This is a hard blocker, not polish.**
- **SSE is not a change feed.** `events()` (`routes.rs:764-788`) replays buffered records
  and then yields `EventPayloadWire::Heartbeat` forever. `publish_agents_changed` is
  called from exactly four sites (`routes.rs:854, 889, 925, 967`), all the gateway's own
  mutation handlers. An agent launched by a local TUI, a chop, or a finalizer emits
  nothing.
- **`sase_core` has no tokio, reqwest, axum, or pyo3** (`crates/sase_core/Cargo.toml`).
  The HTTP client cannot live there. `sase_gateway` has all of them.
- **No `UnixListener` exists in the gateway crate**; `DaemonConfig` models a socket path
  nothing binds.
- **`tower-http` is pulled with only the `trace` feature** — no compression.
- `sase mobile gateway` has exactly one subcommand, `start`, foreground-only.

### 2.5 The real ACE insertion point is narrower and better than "the provider seam"

Both prior reports name `AgentsDataProvider` / `agents_daemon_reads_enabled()` as the
seam. True, but there is a more precise one directly beneath it:

`artifact_snapshot_for_tui_load()`
(`src/sase/ace/tui/models/_agent_loader_artifacts.py:188`) already takes an injected
scanner and index loader and returns `(AgentArtifactScanWire, AgentLoadState)`, where
`AgentLoadState` carries `tier`, `artifact_source`, `complete_history`, and
`used_artifact_index`. It is *already* a tiered, source-tagged loader with a documented
fallback ladder.

**A remote machine is simply a third source of `AgentArtifactScanWire`.** Add
`artifact_source="remote_index"`, a per-machine `AgentLoadState`, and remote rows are
built by the same loader, into the same 200+-field row model, as local rows. The prior
reports' invariant "one wire, one row model" is not something to build — it is something
to *not break*, and this is the function where it is enforced.

---

## 3. Critique: is the idea itself right?

Yes, with three caveats worth stating before the design.

**It is a single-user feature and must stay one.** `sase_collaboration_architecture` §5.3
rejected extending a host control plane across users, for four reasons that all still
hold. Keep the scope: these are *your* machines. Do not build a permission model, a
tenancy story, or a scheduler. The moment a second person's hardware appears, this design
is the wrong one and should be replaced, not extended.

**Roughly half the value is local.** The measurements in §2.1–2.2 describe a machine
where listing agents takes 10.9 s and 99% of stored "running" rows are lies. Both are
true on apollo and the MacBook too. A significant fraction of this epic — index-backed
reads, single scan, owner-resolved liveness, staleness rendering — improves the
single-machine experience whether or not you ever configure a peer. **Sequence the work so
that is literally true** (§8): if the fleet half is cancelled at any point, everything
already landed is still a win. That is the strongest possible risk posture for a feature
of this size.

**The honest alternative is `ssh apollo && sase ace`, and it is not bad.** It costs no
code, has no staleness, no idempotency, no version skew, and no security surface. What it
cannot do is (a) show you one list, (b) tell you a remote agent is *waiting for you*
without you going to look, and (c) let you start work on the right machine from where you
are. Those three are the real product. Notice that (b) — attention — is the one you can
neither poll for nor discover by habit, and it is the cheapest to build (the gateway
already serves notifications, questions, and gate approval). **Attention is the feature;
the fleet list is the container.** I weight the phasing accordingly (§8), which is where
I differ most from both prior reports.

---

## 4. The plugin seam

### 4.1 Why "dispatch provider" is one word for four different things

The word bundles:

| Capability | Varies by provider? | Where it belongs |
| --- | --- | --- |
| **Discovery** — enumerate candidate machines | **Yes** (tailnet, `~/.ssh/config`, static, cloud API) | Plugin |
| **Channel** — authenticated stream to a machine's sase endpoint | **Yes** (Serve URL + token, `ssh -W`, plain URL) | Plugin |
| **Placement / admission** — who may take this launch | No | Core |
| **Agent-plane semantics** — list, liveness, kill, fork, staleness, idempotency | No | Core |

Only the first two vary. If a plugin can implement "list remote agents," then every
provider owns its own answer to *what does RUNNING mean when the link is 40 s stale* —
and SASE acquires N inconsistent answers to the question §2.2 says is the one that must
never be wrong. The `rust_core_backend_boundary` litmus test applies exactly: a web app,
a phone, and the TUI must all agree, so it is core.

The existing seams in the tree support this reading. `sase_llm` (8 providers) is a wide
behavioral seam and is correspondingly the most expensive to evolve. `sase_task_types`
and `sase_artifact_refs` are **declarative** seams — a plugin returns *specs*, and the
host owns all behavior — and they are the newest and cleanest
(`src/sase/task_types/_discovery.py` is the model implementation: builtin plugin +
entry-point discovery + typed diagnostics + `SASE_DISABLE_PLUGIN_*` kill switch). The
remote seam should look like `task_types`, not like `llm_provider`.

### 4.2 The two hooks

New pluggy project `sase_remote`, entry-point group `sase_remote`, mirroring
`src/sase/task_types/` in structure (`_hookspec.py`, `_discovery.py`, `_builtin.py`,
typed diagnostics, env kill switch).

```python
hookspec = pluggy.HookspecMarker("sase_remote")

class RemoteHookSpec:
    @hookspec
    def remote_discover_machines(self) -> Iterable[Mapping[str, Any]] | None:
        """Return machine *candidates* for enrollment. Read-only.

        Called by `sase init`, `sase machine discover`, and never on a
        keystroke, refresh tick, launch, or render path. Implementations
        must not mutate state, prompt, or block longer than the caller's
        deadline. Each mapping is a MachineCandidateWire:
            provider_id, display_name, address, os, online, last_seen,
            labels
        `provider_id` is the provider's own identifier (a MagicDNS name, an
        ssh_config Host). It is NOT a SASE machine name (see 2.3).
        """

    @hookspec(firstresult=True)
    def remote_open_channel(
        self, machine: str, address: str, options: Mapping[str, Any]
    ) -> RemoteChannel | None:
        """Return an authenticated channel to *machine*, or None if unowned."""
```

`RemoteChannel` is deliberately tiny — the smallest contract that admits both an HTTPS
endpoint and a piped stdio tunnel:

```python
@dataclass(frozen=True)
class RemoteChannel:
    kind: Literal["url", "stream"]
    url: str | None            # kind="url": https://apollo.tail….ts.net
    command: tuple[str, ...]   # kind="stream": ("ssh","apollo","sase","machine","serve","--stdio")
    auth_header: str | None
    identity_hint: str | None  # provider-visible endpoint identity, pinned at enrollment
    deadline_seconds: float
```

Everything else in the feature consumes `RemoteChannel` and nothing else. The two hooks
are ~40 lines of contract, and a provider is small enough to be obviously correct.

### 4.3 The three built-in providers

| Provider | Discovery | Channel | Deps |
| --- | --- | --- | --- |
| `manual` | none (config only) | `url` from `machines.<n>.url` | none |
| `ssh` | parse `~/.ssh/config` `Host` blocks | `stream`: `ssh <host> sase machine serve --stdio` | `ssh` binary |
| `tailscale` | `tailscale status --json` | `url`: `https://<DNSName>` via Tailscale Serve | `tailscale` binary |

Two things follow that the user's framing did not assume:

**Tailscale should be built-in and *available* by default, but `ssh` is the better
default *transport*.** Tailscale's value here is discovery, NAT traversal, and identity —
enormous when present, absent when not. SSH works everywhere, needs no daemon publication,
and — because the channel is a stdio stream to a process the user already has permission
to run — **skips the entire pairing/bearer-token surface that §2.4 says is currently
unsafe**. That is a large, concrete reliability and security win for the fallback path,
and it means the first working version of this feature needs no gateway hardening at all.
Recommendation: `ssh` is the default `via:` when a machine has an SSH host; `tailscale`
is preferred when the machine is in the tailnet *and* the gateway hardening in §7 has
landed.

**Discovery is genuinely optional and genuinely cheap.** `tailscale status --json` on
this machine returns in well under the CLI's own startup cost, and it runs at `sase init`,
`sase machine discover`, or `sase doctor` — never at runtime. The user's instinct to pay
discovery cost once is correct and should be a documented rule, not just a default.

### 4.4 Configuration

```yaml
machines:
  # Which providers `sase init` and `sase machine discover` consult.
  # Empty disables discovery entirely; machines can still be added by hand.
  discovery: ["tailscale", "ssh_config"]

  # Freshness horizon before a cached remote RUNNING degrades to UNKNOWN.
  # Derived default: 3 x the observed reconcile interval.
  stale_after_seconds: 0        # 0 = derive

  # Enrolled peers. Written by `sase machine add`; hand-editable.
  peers:
    apollo:
      via: ssh                  # ssh | tailscale | url | <plugin name>
      address: apollo           # provider-native address
      identity: "sha256:…"      # pinned at enrollment; mismatch fails closed
      labels: ["linux", "big"]  # for %machine:@label pools
    kellys_mbp:
      via: tailscale
      address: kellys-macbook-pro.tail297af1.ts.net
      identity: "sha256:…"
```

Why not the single `dispatch.provider` field the user floated: a heterogeneous fleet is
the normal case, and a global selector makes the second machine a config rewrite instead
of an addition. `via:` per peer also makes failover legible ("apollo is unreachable via
tailscale; it is enrolled via ssh") and makes the plugin choice inspectable per row in the
TUI. Keep `machines.discovery` as the only global list, because *that* genuinely is a
global policy question.

Per `sase_flags.md`, the whole surface lands behind one `beta` flag (`remote_machines`,
default off) that the epic deletes before it lands; `machines.peers` being empty is the
permanent, flagless "off" state thereafter. Per `cli_rules.md`: `sase machine
add|discover|list|remove|serve|status|stop`, alphabetical, bare `sase machine` delegating
to `list`, every long option with a short alias, no required options.

---

## 5. `%machine`: the dispatch directive

### 5.1 Naming

`%dispatch:<machine>` describes the mechanism. Every existing directive describes the
intent: `%model`, `%effort`, `%id`, `%clan`, `%wait`, `%repeat`, `%hide`, `%auto`,
`%final`. The glossary already forbids "node" for machines (it means an Agents-tab row),
and both prior reports settled on **machine** / **host** as the fleet noun. `id.machine_name`
is the field. **`%machine:<name>`** is the consistent spelling; `%on:<name>` is a
defensible shorter alias (all good single letters are taken: `a c e h i m n r t w`).

### 5.2 Grammar — copy `%model` exactly

```text
%machine:apollo                        bare name
%machine:@big                          label pool (round-robin across labelled peers)
%machine:auto                          any peer with a free slot and the project present
%machine(apollo, on_unreachable=fail)  keyword options: fail (default) | local | stash
%{%machine:apollo | %machine:athena}   fan-out, free from the existing %alt machinery
```

The last line is the argument for the whole design. `%alt`/`%{a | b}` fan-out already
exists and already splits directives per branch (`_directive_alt.py`,
`plan_prompt_fanout_variants`). Making `%machine` an ordinary single-value directive means
"run this same task on three machines at once and compare" is not a feature anyone has to
build — it falls out. Users who have internalized `%{%m:opus | %m:sonnet}` will discover
it without documentation. That is what "beautiful" means for a directive system: a new
noun that composes with every verb already there.

Implementation touchpoints, all small and enumerable: add `machine` to
`_KNOWN_DIRECTIVES` (`src/sase/xprompt/_directive_types.py:41`), one field on
`PromptDirectives`, one branch in `_directive_extract`, a completion source beside the
existing `%model` completion (`_directive_completion_agents.py`), a validation rule in
`launch_validation.py`, and one row in the `xprompts.md` directive table.

### 5.3 Semantics — the dispatch receipt replaces "auto-subscribe"

The user's rule — a `%machine` launch is auto-subscribed on the launching machine — is
right, but "subscription" is the wrong mechanism for it. A launch you initiated is not
something you *observe*; it is something you *own*. So:

**On dispatch, the launching machine writes a local launch receipt before the remote
machine is contacted.** The receipt carries `(idempotency_key, target_machine,
requested_name, prompt digest, launch options, deadline, created_at)`. It has three
properties that a subscription does not:

1. **The row exists immediately**, in a `DISPATCHING` state, before the target has
   accepted. You see your launch the instant you press enter, even if apollo takes two
   seconds. There is no window in which you pressed enter and nothing happened.
2. **It is the idempotency journal entry.** If the response is lost, the retry carries the
   same key and the target replays its outcome instead of launching a second agent. A
   duplicate kill is harmless; a duplicate launch burns a runner slot and real money.
   This is the one place idempotency is genuinely required on day one.
3. **It survives a crash.** ACE restarting mid-dispatch finds the receipt and reconciles
   it against the target, rather than losing the run or double-launching it.

The receipt is then *the* reason a remote row is hydrated eagerly. "Auto-subscribe" is not
a rule anyone has to implement or explain; it is what having a receipt means.

### 5.4 Failure semantics

| Situation | Behavior |
| --- | --- |
| Target unreachable | **Fail immediately and visibly. Never queue.** Then stash the prompt with the target recorded (`StashedPromptsIndicator`, `restore_prompt_stash` is already bound to `@`) so nothing typed is ever lost. Reuse, do not invent a queue. |
| Target at slot capacity | The **target** admits or queues against its own `max_running_agents`. The client proposes; it never schedules from a 60 s-old snapshot. |
| Project not checked out on target | Refuse **at completion time**, not at launch time. The picker greys the machine and says why. Failing in the picker is kind; failing after enter is not. |
| `%machine:auto` with no eligible peer | Typed error naming each peer and its reason (offline / no slots / project absent). Never silently fall back to local — that is the surprise that destroys trust in a dispatch directive. |
| Version skew | The target advertises capabilities; unsupported launch options are refused with the target's version, not a generic 400. |

`on_unreachable=local` exists as an explicit opt-in for people who want fallback, precisely
so the default can be strict.

---

## 6. UX: the part I most want to change

### 6.1 Is there a better way than Local/Remote subtabs?

Five arguments against, then the version I would build.

**(a) It splits the wrong axis.** The Agents tab answers "what is running, and what needs
me." Machine is an attribute of a run, exactly like project, date, status, model, and
tribe — and SASE already has two established mechanisms for attributes: the grouping cycle
(`GroupingMode.STANDARD | BY_DATE | BY_STATUS`,
`src/sase/ace/tui/models/agent_groups/_buckets.py:39`) and the closed query-property
allowlist (`SUBSTRING_PROPERTY_KEYS` in `src/sase/ace/agent_query/tokenizer.py:33`).
Promoting one attribute to a tab sets a precedent with no natural stopping point.

**(b) Two counted titles create a third counting surface.** `AgentInfoPanel` already
renders `[S R Q W F U D]` chips and the runner-slot denominator
(`src/sase/ace/tui/agent_count_chip.py`). Subtab titles carrying their own running counts
will disagree with those chips during hydration — local is instant, remote is seconds
stale — and adjacent chrome that disagrees about a number is the precise opposite of
beautiful.

**(c) The keys are gone.** `[`/`]` are `cycle_artifacts_subtab` at app level
(`default_config.yml:425`) *and* `toggle_thinking`/`toggle_thinking_reverse` on the
Agents tab (`default_config.yml:549`). A Local/Remote cycle needs a third meaning for a
doubly-bound key, or a new key on a map with 162 action modules where nearly every letter
is taken.

**(d) The Remote pane is a browse-once surface with a permanent tax.** Its stated job is
"decide whether to subscribe." That is a rare action — a machine joins, or you go looking
for something you started on the laptop. Permanently spending half the Agents tab's
navigation budget on a rare action is a poor exchange rate, and it forces a second mental
model: two places an agent can be, with a transfer ritual between them.

**(e) Subscription is manual cache management for a cost that is not there.** 28 KB per
machine, 10–33 ms RTT. Subscribing to two machines instead of three saves you nothing
measurable. The expensive thing is *reading agent state at all* (§2.1) and *hydrating a
209-field row with chat, diff, and artifacts* — both of which are solved by tiering, which
is invisible, rather than by subscription, which is a chore you will forget to perform and
then be surprised by.

### 6.2 What I would build instead

**One Agents list. Machine is a facet. The fleet gets one line of chrome.**

1. **`machine:` query facet.** Add to `SUBSTRING_PROPERTY_KEYS`, plus the virtual values
   `local` and `remote`. `machine:apollo`, `-machine:athena`,
   `machine:remote AND needs:input`. It composes immediately with saved query slots 0–9
   (`src/sase/ace/saved_queries.py`), marks, tribes, and the Rust query pushdown
   (`compile_agent_query_pushdown`) — none of which needs to know the feature exists.

2. **`GroupingMode.BY_MACHINE`.** One enum member; L0 becomes the machine, local first.
   This *is* the "show me the fleet" view, reachable with the grouping key users already
   press, and it renders exactly the tree the Remote subtab wanted — with the local
   machine in it, which is more useful than either subtab alone.

3. **The machine strip**, one line in `AgentInfoPanel`:

   ```text
   ⬢ athena 6/10   ◇ apollo 3/10   ◇ kellys_mbp ·2m   ◌ pixel
   ```

   Filled glyph = this machine. Open = linked and fresh. `·2m` = seconds since last
   successful reconcile (rendered, never inferred). Dotted/dim = offline or not a sase
   host. `n/m` = live runner slots, which is the number you actually need before
   dispatching. Colors from the existing palette: `#00D7AF` healthy, `#FFAF00` stale,
   `#FF5F5F` unauthorized/incompatible, dim offline. Selecting an entry sets
   `machine:<name>` in the filter bar.

   This one line replaces both subtabs. It answers "what is out there, is it healthy, does
   it have capacity" without navigating anywhere, and it is the natural launch-target
   affordance.

4. **Row badge, not row class.** A remote row renders in the same list, built by the same
   loader, with the machine as a dim hood prefix on the name — mirroring how ACE already
   strips the local machine hood for display. Rows you dispatched carry the accent color;
   rows you are merely observing are dim. No second widget, no second provider, no
   transfer ritual.

5. **A modal for deliberate browsing**, if one is wanted at all: the same picker
   `%machine` completion opens, bound to one key. The codebase is full of well-built
   modals (gate, tribe, cleanup, config hub); a modal is the correct widget for "look,
   choose, return," and it costs zero permanent navigation budget.

### 6.3 What this preserves from the user's requirements

- *"A count of running agents per scope"* — the machine strip shows per-machine live slots
  continuously, which is strictly more information than two subtab counts, computed by the
  same code as the existing chips so it cannot disagree.
- *"Remote agents visually distinct"* — accent vs dim on the row, plus the machine badge.
- *"Manage remote agents the same way as local"* — strengthened: they are the *same rows*
  in the *same list*, so parity is structural rather than a checklist.
- *"Don't create sub-sub-tabs"* — honored absolutely; there is not even one sub-tab.
- *"As lazy and performant as possible"* — §6.5.

### 6.4 If you want the subtabs anyway: build them as view presets

The user may reasonably prefer the explicit two-entry-point UX. Here is the version that
costs almost nothing and cannot rot:

**Make "Local" and "Remote" saved *view presets* over one list — not two panes.** A preset
is `(query, grouping, label, accent)`. Render them as a small strip under the Agents
header using the existing `PanelTabStrip` widget
(`src/sase/ace/tui/widgets/panel_tab_strip.py`), which already does clickable, centered,
width-tiered tab strips with icons and compact/micro fallbacks. Switching a preset calls
`_refilter_agents()` — the existing instant cached-data refilter — and never triggers a
reload.

Consequences:

- **Counts cannot disagree**, because both presets count the same in-memory list with the
  same function that feeds the info-panel chips.
- **Switching is free** — a refilter, not a provider swap, so `tui_perf` rule 5 is
  satisfied by construction.
- **A third preset is free**: `All`. Which the two-tab design cannot express, and which is
  what you actually want most days.
- **Users can add presets later** (`machine:apollo`, `needs:input`) with no new code,
  because presets are just saved queries — a mechanism that already exists.
- The keybinding problem shrinks: presets can be selected by the digit keys already used
  for saved query slots, instead of contending for `[`/`]`.

This is the design that says yes to the requested UX and no to the architectural cost. If
subtabs must exist, they should be this.

### 6.5 Laziness: tiers, not subscriptions

Four tiers, mapping onto the `AgentLoadState` vocabulary that already exists (§2.5):

| Tier | Content | When | Cost |
| --- | --- | --- | --- |
| **T0 — link** | per-machine health, slot counts, revision | every reconcile (30–60 s, jittered) | ~200 bytes |
| **T1 — live rows** | active + recent runs, owner-resolved liveness | every reconcile | ~28 KB/machine measured |
| **T2 — row detail** | the fields the detail panel shows for the *selected* row | on selection, debounced (`DetailPanelDebouncer`, 150 ms) | one row |
| **T3 — content** | chat, response, diff, artifacts | on explicit open, by handle, digest-cached | bounded |

Rules that make it honest, all of which are `tui_perf` restatements rather than new
inventions: never fetch on a keystroke path; first paint from cache without awaiting the
network; land deltas as `patch_row()` selective updates rather than list rebuilds; run
every fetch in `spawn_pump_free_task()` with an explicit deadline, per-machine circuit
breaker, and teardown cancellation; re-capture selection after every await; remote
mutations submit as tracked procs so they dedup, appear in the Procs tab, and count at
quit. Acceptance: **p95 `j`/`k` under 16 ms with one machine hung.**

History is never fetched on a tick. It is a cursor-paged T3 read, which the wire already
expresses (`record_shape: full | list`, `AcePage.next_cursor`).

### 6.6 Scope honesty: what "manage the same way" decomposes into

| Class | Examples | Where it runs |
| --- | --- | --- |
| List / group / search | status, model, duration, tribe | Remote records, local presentation, pushed-down queries |
| **Attention** | answer question, approve gate, dismiss notification | Remote; routes already exist; **highest value** |
| Lifecycle mutation | kill, retry, wait/resume | Remote, name-addressed, journaled |
| **Fork** | `#fork:<agent>` | See below — two different operations |
| Content read | chat, response, diff, artifacts | Remote by handle, digest-cached, lazy |
| Viewer-local state | folds, marks, dismissal, tribe, query profiles | Local, keyed by global name |
| Genuinely local | `tmux attach`, `$EDITOR` on workspace files | Named escape hatch, never faked |

**Fork deserves its own note**, because the user named it and it hides an ambiguity.
Forking a remote agent can mean "fork it *there*" (the target machine already has the
context, the workspace, and the checkout — nothing moves) or "fork it *here*" (materialize
the prompt and context locally, then launch locally). These are different operations with
the same word. **Default to fork-where-it-lives**: it is the fast one, the correct one,
and the one that cannot half-fail. Offer "fork here" explicitly, as a content read followed
by a local launch, and label it as such.

**`tmux attach` on a remote row** should open a confirm that says, in words, "this opens
an SSH session on apollo," and then shell out. Naming the mechanism is what makes an escape
hatch feel trustworthy instead of magic. Pretending a remote process is local is the one
dishonesty this design should refuse.

---

## 7. Reliability: the invariants

Each is a test, not a discipline. Together they are why this is safe by construction.

- **R1 — Local truth is never remote-mediated.** Local rows always load through the direct
  path. Every remote component failing costs remote rows and nothing else. (This is the
  sase-3e daemon-revert lesson, encoded structurally.)
- **R2 — A machine is the sole authority for its own agents.** The viewer's cache is a
  disposable presentation blob under `~/.sase/machines/<machine>/`. It never touches the
  artifact index, the name registry, or dismissed bundles — or it recreates the import leg
  that epic `sase-ws` just deleted.
- **R3 — Liveness is a resolved verdict, never an inference.** Only the owner runs a
  process check. The wire carries `liveness: alive|dead|unknown` plus its resolution
  time. §2.2 is why.
- **R4 — Staleness is rendered, and a stale row is not actionable.** Past the horizon a
  cached `RUNNING` renders `UNKNOWN`, and mutations on it are refused with a refresh
  prompt. Derive the horizon from the observed reconcile interval (3 missed ticks) rather
  than a magic constant, so a slow link degrades gracefully instead of flapping.
- **R5 — Remote paths are inert.** `artifacts_dir` and friends arrive as a typed
  `RemoteArtifactRef` with **no `__fspath__`**, making misuse a type error at authoring
  time. No remote string reaches `open()`, `unlink()`, `$EDITOR`, `tmux`, or the local
  index mutator.
- **R6 — Mutations are name-addressed, target-resolved, journaled, fenced, never queued.**
  `kill_named_agent` (`src/sase/agent/running.py:45`) already re-resolves by name and
  returns typed `not_found` / `already_completed` outcomes — that is the pattern.
- **R7 — One wire, one row model.** Remote records enter through
  `artifact_snapshot_for_tui_load` as `AgentArtifactScanWire` with
  `artifact_source="remote_index"`. A field renders remotely iff it renders locally.
- **R8 — Identity is pinned, never inferred.** The authoritative machine name comes from
  the remote's own `id.machine_name` at handshake (§2.3). The endpoint identity is pinned
  at enrollment and verified on every connect; a mismatch fails closed. A MagicDNS rename
  must never silently substitute a different machine as the target of a kill.
- **R9 — Qualify exactly once.** `machine_hood::qualify_machine_agent_name` is idempotent
  and has *no internal Rust callers yet* — only PyO3 exports. Double-globalization is
  already producing dead provenance links in shared artifacts today
  (`sase_collaboration_architecture` §2.3). Route every qualification through the one
  helper, in Rust, at the boundary.
- **R10 — Off is byte-for-byte today.** Flag off, or `machines.peers` empty: the factory
  returns the direct provider, discovery never runs, no plugin is loaded, no socket is
  bound.

### 7.1 Security preconditions (blocking, verified in §2.4)

Before any endpoint is published to the tailnet: replace the self-authorizing
`pair_start`/`pair_finish` flow with local-only pairing initiation (on-host command or the
daemon's Unix socket) using a short-lived single-use secret; add scoped tokens
(`view`/`operate`/`admin`); pin gateway identity at enrollment; rate-limit pairing, auth,
and mutations independently; coalesce `last_seen_at` persistence instead of rewriting
`devices.json` per request. Loopback bind plus `tailscale serve` remains the only
supported exposure — never Funnel, never `--allow-non-loopback`.

**The `ssh` provider sidesteps this entire list**, which is a further reason to make it the
first transport that works: a stdio channel to a process you were already authorized to
run needs no pairing, no bearer token, and no published port. Phases 2–5 below can ship
completely before any gateway hardening is done.

---

## 8. Phasing

Ordered so that **every phase pays for itself at N=0 machines**, and so the highest-value
remote capability (attention) lands before the most dangerous one (launch).

| Phase | Deliverable | Value if the fleet half is cancelled |
| --- | --- | --- |
| **0** | Index-backed `sase agent list`; eliminate the double scan; owner-resolved liveness on the listing path. | **~10.9 s → sub-second on a live bug today.** Fixes the mobile bridge for free. |
| **1** | `machine:` query facet, `GroupingMode.BY_MACHINE`, machine strip rendering a one-machine fleet. | Slot capacity becomes visible at a glance; new saved-query facet. |
| **2** | `sase_remote` seam (2 hooks, task_types-shaped); `manual` provider; `machines:` config; `sase machine add/list/remove/status`; handshake + identity pinning. | A documented, tested plugin seam; no TUI change. |
| **3** | `ssh` provider; `sase machine serve --stdio`; the *serve* side answers from the index with resolved liveness. | Remote read works with zero daemon, zero pairing, zero published ports. |
| **4** | Read-only remote rows through `artifact_snapshot_for_tui_load`; per-machine cache, deadlines, circuit breakers, staleness. **The core ask.** | — |
| **5** | **Attention plane**: remote question answering and gate approval. Routes exist; mostly UI. | The reason the feature exists. |
| **6** | Mutations: kill, retry, wait/resume — journal, host-side resolution, revision fencing. | — |
| **7** | `%machine` dispatch + launch receipts + machine picker with live slots and project availability. | — |
| **8** | `tailscale` provider + `sase init` discovery/reconcile; gateway hardening (§7.1); SSE change feed driven by index writes; gzip. | — |
| **9** | Content by handle: chat, diff, artifacts, remote fork. | — |

Two deliberate departures from the predecessor phasings:

- **Attention (5) before mutations (6).** A remote agent blocked on a question is the one
  fleet event you cannot discover by habit; answering it is idempotent against a specific
  pending request id; and the routes already exist. Killing a remote agent is rarer,
  riskier, and needs the journal.
- **Tailscale last (8), not first.** Discovery is a convenience; SSH proves the whole
  design end to end without the gateway's unsafe pairing flow, and it keeps the seam
  honest — a design whose first working provider is the *non*-privileged one cannot have
  accidentally hard-wired Tailscale assumptions.

`%machine` at Phase 7 can move earlier if the user prefers; the cost is dispatching into a
view that cannot yet show you the result.

---

## 9. Acceptance gates

**Phase 0–1 (local).** `sase agent list` p95 under 1 s on a 195 MB index; exactly one
filesystem scan per invocation, asserted by test; no row reports `RUNNING` without a
resolved liveness check; `machine:` and `BY_MACHINE` behave identically with zero peers
configured.

**Phase 4 (read-only remote).** Local rows paint and stay navigable with one peer hung;
healthy peers hydrate independently; p95 `j`/`k` under 16 ms with a hung peer; cached rows
show honest ages and degrade `RUNNING`→`UNKNOWN` past the horizon; viewing remote state
creates zero local artifacts, index rows, or registry entries; no snapshot discloses an
actionable absolute path (asserted by type *and* by test); an endpoint presenting a
different pinned identity fails closed; a peer running an older version stays legible with
an upgrade hint rather than a generic error; disabling the feature restores byte-identical
behavior.

**Phase 6–7 (mutations and dispatch).** A lost launch response retried with the same key
yields exactly one agent; a disconnect mid-kill recovers the journaled terminal result; a
stale kill against a reused name or recycled PID returns a conflict, never a wrong kill; a
stale-`UNKNOWN` row refuses mutation; `%machine:auto` never silently falls back to local;
a failed dispatch stashes the prompt with its target; ACE restarting mid-dispatch
reconciles the receipt without double-launching; the target's own slot cap admits, never
the client's snapshot.

---

## 10. Open questions for the user

1. **Subtabs: presets or panes?** §6.2 recommends no subtabs at all; §6.4 gives the
   preset-based version if the two labelled entry points are wanted. Which?
2. **`%machine` or `%on`?** Both are better than `%dispatch`; `%machine` matches
   `id.machine_name`, `%on` is shorter and reads well in a prompt.
3. **Is `ssh`-first acceptable?** It ships the whole feature before any gateway hardening,
   at the cost of a per-request process spawn on the target (bounded by Phase 0 making
   that spawn cheap).
4. **Should discovery ever run outside `sase init`?** I recommend also wiring it into
   `sase doctor` (read-only drift: "apollo is in your tailnet but not enrolled") but never
   into a refresh tick.
5. **Remote `tmux attach`: named escape hatch or refusal?** §6.6 assumes the named escape
   hatch with an explicit confirm.
6. **Dismissal: per-viewer or fleet-wide?** Per-viewer is assumed, consistent with the
   `athena_agent_sync_repair` separation of provenance from visibility.

---

## 11. Sources

**Prior research (read as context):**
`research:202609/tailnet_agent_fleet/tailnet_agent_fleet.md`,
`research:202609/sase_collaboration_architecture.md`,
`research:202609/tailnet_fleet_federation/tailnet_fleet_federation.md`.

**Repo evidence, verified 2026-09-06 against `sase` @ `58f16fe68` and `sase-core` @
`0504155`:** `src/sase/xprompt/_directive_types.py`, `src/sase/xprompt/directives.py`,
`src/sase/task_types/{_hookspec,_discovery}.py`,
`src/sase/artifact_providers/_hookspec.py`,
`src/sase/workspace_provider/{_hookspec,_plugin_manager}.py`,
`src/sase/llm_provider/_registry_plugins.py`, `pyproject.toml` entry-point groups,
`src/sase/ace/tui/{_app_layout,tab_order,agent_count_chip}.py`,
`src/sase/ace/tui/widgets/{tab_bar,panel_tab_strip,agent_info_panel,agent_list}.py`,
`src/sase/ace/tui/data_providers/{_types,_factory,_settings}.py`,
`src/sase/ace/tui/models/agent_loader.py`,
`src/sase/ace/tui/models/_agent_loader_artifacts.py:188`,
`src/sase/ace/tui/models/agent_groups/_buckets.py:39`,
`src/sase/ace/agent_query/{tokenizer,types}.py`, `src/sase/ace/saved_queries.py`,
`src/sase/ace/grouping_strategy.py`, `src/sase/ace/agent_tribes.py`,
`src/sase/integrations/agent_list_entries.py:177`,
`src/sase/integrations/_mobile_agent_summary.py:54`,
`src/sase/agent/running_listing.py:119`, `src/sase/agent/running.py:45`,
`src/sase/core/agent_scan_facade.py`, `src/sase/config/identity.py:21`,
`src/sase/config/layers.py`, `src/sase/default_config.yml` (`:38`, `:291-440`,
`:1145-1300`), `src/sase/main/parser_init.py`, `src/sase/main/parser_mobile.py`;
`sase-core/crates/sase_gateway/src/routes.rs` (`:563-592` pairing, `:764-788` SSE,
`:854/889/925/967` publish sites), `crates/sase_gateway/Cargo.toml`,
`crates/sase_core/Cargo.toml`, `crates/sase_core/src/machine_hood.rs`,
`crates/sase_core_py/src/lib.rs:1319`.

**Original measurements (athena, 2026-09-06):** `sase version` 0.32 s; `sase agent list
--json` 10.9 s / 19 agents / 28,179 bytes, repeated; cProfile attribution
(`scan_agent_artifacts` 7.36 s over 2 calls; `_agent_meta_from_dict` 2.18 s over 23,330
records); `query_agent_artifact_index` 0.579 s / 802 records; SQL status aggregation
15.2 ms over 9,506 rows; index 195 MB, 40,507 dismissed rows; 1,867 active-status rows vs
19 live (99.0% phantom); 37,663 directories and 11,786 run dirs under `~/.sase/projects`;
`tailscale status --json` device inventory and name shapes.

**Project memory and decisions:** `rust_core_backend_boundary`, `tui_perf.md`,
`cli_rules.md`, `sase_flags.md`, `xprompts.md`; decisions `agents-sync-publish-only`,
`rust-core-required`, `two-speed-verification`, `corpus-before-mechanism`,
`single-turn-agents`.

---

## 12. Recommended solution

**Build remote machine support as a narrow two-hook plugin seam over one Agents list, and
fix the local read path first.**

1. **Phase 0 is local and immediate.** Point `sase agent list` at the artifact index the
   TUI already uses, and stop scanning the filesystem twice. This is a ~10.9 s → sub-second
   fix on a live bug, it is the exact code path every remote read will inherit, and it
   removes the premise ("the fork is the problem") on which the previous plans were
   built.

2. **Add a `sase_remote` pluggy seam with exactly two hooks** — `remote_discover_machines`
   (read-only, `sase init`-time only) and `remote_open_channel` — shaped like
   `sase_task_types` (builtin plugin, entry-point discovery, typed diagnostics, env kill
   switch). Ship `manual`, `ssh`, and `tailscale` built in. Everything above the channel —
   wire, row model, liveness, staleness, journal, admission — stays core, because a web
   app, a phone, and the TUI must all agree about what `RUNNING` means.

3. **Configure per machine, not globally**: `machines.peers.<name>.via`, with
   `machines.discovery` as the only global policy list. Enroll by handshake; the
   authoritative machine name comes from the peer's own `id.machine_name`, never from a
   MagicDNS label that may contain hyphens, digits, or a Unicode apostrophe.

4. **Ship `ssh` before `tailscale`.** It works everywhere, needs no daemon, no published
   port, and no pairing — which matters because today's `pair_start` is unauthenticated
   and hands out its own pairing code. Tailscale then lands as the discovery and
   low-latency transport it genuinely is, after the gateway hardening it requires.

5. **One Agents list, machine as a facet.** `machine:` in the query allowlist,
   `BY_MACHINE` in the grouping cycle, and a one-line machine strip in the existing info
   panel showing per-machine health, freshness, and live slots. If two labelled counted
   entry points are wanted, build them as **view presets over the one list** using the
   existing `PanelTabStrip` and `_refilter_agents()` — never as two panes with two
   providers, so the counts cannot disagree and switching costs nothing.

6. **Replace subscription with tiers and receipts.** Hydration is T0 link → T1 live rows →
   T2 selected-row detail → T3 content-on-open. Dispatch writes a local launch receipt
   before contacting the target, which makes the row appear instantly, serves as the
   idempotency key, and survives a crash — so "auto-subscribe" is not a rule anyone has to
   implement.

7. **Name the directive `%machine` and give it `%model`'s grammar**, so that
   `%{%machine:apollo | %machine:athena}` fan-out falls out of machinery that already
   exists. Fail fast and visibly on an unreachable target, stash the prompt rather than
   losing it, refuse in the picker rather than after enter, and let the target admit its
   own launches.

8. **Land attention before mutations.** A remote agent waiting on your answer is the one
   fleet event you cannot notice by habit; the gateway already serves those routes; and it
   is safe long before kill semantics are.

This is **reliable** because every failure has exactly one bounded consequence: the seam
failing costs remote rows, a peer going offline costs freshness, a lost response costs a
retry that cannot duplicate, and the whole feature off is byte-for-byte today. It is
**intuitive** because it introduces one new noun — the machine — and attaches it to the
verbs SASE already has: a query facet, a grouping mode, a directive with `%model`'s
grammar. And it is **beautiful** because there is no second list, no second row model, and
no transfer ritual: a remote agent is an agent, rendered by the same function, honest about
exactly how stale it is and exactly which machine it belongs to.
