# Pluggable Remote Dispatch: `%dispatch`, Machine Providers, And The Fleet UX

## Research question

How should SASE dispatch agents to remote machines and manage them from one TUI, with
device discovery and transport expressed as SASE plugin hooks rather than a hard
Tailscale dependency? And — the part I was asked to lead — what is the *right* UX for
this, judged against the proposed Local/Remote Agents sub-tabs, the subscribe model, and
the `%dispatch:<machine>` directive?

Researcher B (`research.1h.cld`, claude/opus-5). Independent report; a peer is writing
`__a.md` separately. Examined `sase` @ `58f16fe68`, `sase-core` @ `0504155`, with live
measurements on `athena` on 2026-09-06.

---

## Executive summary

**The proposed architecture is right in its instincts and wrong in three of its seams.
The most valuable thing in the request is `%dispatch`; the most expensive thing is the
Remote sub-tab; and they are separable. Ship dispatch first, over SSH, with no daemon
anywhere.**

Six findings drive everything below.

1. **The bottleneck is local and it is worse than prior research recorded.** On athena
   today, `sase agent list --json` takes **11.0 s warm**. `sase --version` is 0.65 s and
   a `COUNT(*)` over the 9,501-row, 195 MB artifact index is **2 ms**. Filtering changes
   nothing: `-p <nomatch>` returns *3 bytes* in **11.0 s**, and `--all` returns *161 KB*
   in **10.6 s**. This is a fixed-cost full enumeration in Python — not interpreter
   startup (which `tailnet_agent_fleet` blamed) and not the database. Any remote read
   path that goes through the Python CLI or the gateway's fork-per-request bridge costs
   ~11 s *per machine per poll*. This makes `tailnet_fleet_federation`'s central finding
   — split resolution from presentation — the top priority whether or not the fleet ever
   ships.

2. **"Dispatch provider" is one plugin seam where there should be two, and they are
   Ansible's two.** Ansible separates *inventory* plugins (discovery: what hosts exist)
   from *connection* plugins (transport: how to talk to them). SASE needs the same split,
   for a concrete reason: **Tailscale is not a transport.** Once you hold
   `apollo.tail297af1.ts.net:7629` and a token, the wire is ordinary HTTPS. Tailscale
   contributes discovery, naming, encryption, and NAT traversal — only the first is a
   SASE-visible concern. A single "Tailscale dispatch provider" would be 95 % generic
   HTTP client and 5 % `tailscale status --json`, and every future provider would
   re-implement the 95 %.

3. **A global `dispatch_provider:` config field is the wrong control.** Every existing
   SASE provider family (`sase_vcs`, `sase_llm`, `sase_workspace`, artifact providers)
   is `firstresult=True` because there is exactly one answer per repo/project. Machines
   are heterogeneous by nature: apollo over the tailnet, a work laptop over SSH, a cloud
   box over something else. Transport belongs **on the machine record**, not on a global
   setting. Discovery, by contrast, must *aggregate* across plugins, so its hook must not
   be `firstresult`.

4. **The Local/Remote sub-tab split is the weakest part of the proposal, and the
   proposal contains its own refutation.** The spec puts subscribed *remote* agents in
   the *Local* tab. So the real axis is **followed / not-followed**, not local/remote —
   and a tab named "Local" holding remote rows is the kind of mismatch that makes a UI
   feel arbitrary forever. Worse, the split is by *provenance* while the Agents tab's job
   is *attention*: an agent that needs your answer would be one tab away. SASE's own
   Artifacts sub-tabs split by **artifact kind** (genuinely different objects, different
   verbs), never by origin. Remote agents are the same object.

5. **Everything the Local/Remote split would buy already exists as machinery.** The
   Agents tab has `GroupingMode` (STANDARD/BY_DATE/BY_STATUS) with `o`/`O` cycling,
   accented group banners with count chips, fold persistence, and a query language
   (`status:`, `project:`, `tribe:`, `model:`, `age>=`…). Adding a **`machine:` query
   field** and a **`BY_MACHINE` grouping mode** reproduces both tabs exactly, composes
   with every existing filter, needs no new pane, and is already keyboard-reachable.
   Meanwhile the Remote roster is a *picker* — rare, shallow, different verbs — and SASE
   puts pickers in the Admin Center, whose tabs are already
   `config | logs | procs | projects | statistics | updates`. **Machines is to the Admin
   Center exactly what Projects is.**

6. **The SSH transport should be built first, not last.** It is slow (~11 s/call) but it
   needs no daemon, no pairing, no Tailscale, and no `sase-core` work — and dispatch is a
   rare, user-initiated, spinner-bearing operation where 11 s is fine. Shipping `ssh`
   first delivers `%dispatch` in one phase, and gives the plugin seam a *second real
   implementation*, which is the only way to know the abstraction is correct before the
   expensive `sase_host` transport is written behind it.

**Recommended shape:** two pluggy hook families (`machine_discover`, aggregating, called
only by `sase init`; `machine_transport`, `firstresult`, keyed per machine record); a
`machines:` config block written at init and never re-discovered at runtime; a
capability-negotiated transport protocol of seven methods; `%dispatch:<machine>` /
`%dispatch:auto` that ships the *residual prompt* and lets the target parse, name, and
admit it; a `machine:` query facet plus `BY_MACHINE` grouping instead of sub-tabs; a
Machines pane in the Admin Center as the roster/follow picker; and a `FleetIndicator` in
the top bar carrying the count the sub-tabs were going to carry, visible from every tab.

---

## 1. Evidence: what I measured and verified

### 1.1 New measurements (athena, 2026-09-06)

| Probe | Result |
| --- | --- |
| `sase --version` (interpreter + import floor) | **0.65 s** |
| `sqlite3 COUNT(*)` over `agent_artifact_index.sqlite` (195 MB, 9,501 rows) | **2 ms** |
| `sase agent list --json` (19 live agents, 28 KB) | **11.0 s** warm |
| `sase agent list -j -p <no match>` (**3 bytes** of output) | **11.0 s** |
| `sase agent list -j --all` (**161 KB** of output) | **10.6 s** |
| `tailscale ping apollo` | **10 ms**, direct (public endpoint, no DERP) |
| Tailnet membership | athena (self), apollo, kellys-macbook-pro, pixel-10-pro-xl (offline 27 d) |
| Shared `agents` sidecar | 11,070 agent dirs: 10,355 athena · 289 kellys_mbp · 88 apollo |

Three conclusions the prior reports did not draw:

- **Result size is irrelevant to cost.** 3 bytes and 161 KB take the same ~11 s. The
  list path performs a fixed full enumeration and filters afterward. This is not a
  scaling problem you can dodge with a narrower query; it is a structural one.
- **The blame is neither startup nor SQLite.** 0.65 s of import and 2 ms of database
  leave ~10 s of Python-side scanning, PID liveness resolution, marker repair, and
  enrichment. `tailnet_agent_fleet`'s framing ("interpreter startup dominates") is
  wrong today; `tailnet_fleet_federation`'s framing (resolution vs. presentation) is
  right and understated.
- **The tailnet is free and the process model is the whole cost.** 10 ms RTT against an
  11 s read means the network contributes 0.1 % of a remote list. Every transport
  argument is downstream of this.

### 1.2 Repo facts verified for this design

- **Plugin idiom.** `src/sase/{vcs,workspace,llm}_provider/` each pair a `_hookspec.py`
  (pluggy, `firstresult=True`, `<family>_` prefixed hook names), a `_plugin_manager.py`
  that delegates and raises `NotImplementedError` when nothing handles a hook, a
  `_registry.py` resolving *env var → config → auto-detect*, and a `plugins/`
  directory of built-ins. `VCSPluginManager._has_hookimpls()` performs **structural
  capability probes** (`supports_issue_listing()`) that never execute a remote command —
  the exact idiom I want for transport capabilities.
- **Config already knows about machines.** `discover_machine_names()`
  (`src/sase/config/_owner.py:54`) returns machine discriminators from per-machine config
  overlays; `~/.config/sase/sase_athena.yml` exists on this box.
  `AgentIdentitySnapshot.sibling_machines` already carries them, used "solely for
  launch/namespace guards." Owner identity is `username.machine_name`
  (`bbugyi200.athena`).
- **Machine name ≠ hostname.** The tailnet calls the MacBook `kellys-macbook-pro`; SASE
  calls it `kellys_mbp`. Discovery must *propose* a mapping and config must *record* it.
  Nothing may infer one from the other at runtime.
- **A remote-launch path already exists and works.** `launch_mobile_text_agents(request)`
  (`src/sase/integrations/_mobile_agent_launch.py`) takes a prompt string plus a project
  context and launches through the normal SASE path on the receiving host. That is
  precisely the `%dispatch` execution mechanism, already written and already exercised by
  the phone.
- **Directives are extract-and-strip.** `extract_prompt_directives()` returns
  `(cleaned_prompt, PromptDirectives)`. `_KNOWN_DIRECTIVES` = auto, clan, effort, final,
  hide, model, id, repeat, wait, if, proc. Aliases taken: a, c, e, h, i, m, n, r, t, w —
  **`d` is free**.
- **Launch already has a durable, versioned request envelope.**
  `LAUNCH_REQUEST_SCHEMA_VERSION`, `normalize_request_payload`, `read_launch_request`,
  `dispatch_approved_launch_request` (`src/sase/agent/launch_request*.py`) plus
  `launch_preview.py`. A dispatch is a launch request with a destination.
- **The TUI sub-tab machinery is already built.** `PanelTabStrip` (`id`, `label`,
  `accent_color`, `compact_label`, `micro_label`, `shortcut`, `icon`, `description`,
  responsive full/compact/micro tiers) + `ContentSwitcher` + an `activate()`/
  `deactivate()` pane lifecycle, used by `ArtifactsView`, the Config hub, Projects,
  Statistics, and Help.
- **Key budget is already spent.** `cycle_artifacts_subtab` is `]` / `[` — and on the
  Agents tab those same keys are `toggle_thinking` / `toggle_thinking_reverse`,
  disambiguated by tab. Agents sub-tabs therefore *cannot* reuse the established sub-tab
  gesture.
- **Count chips exist.** `format_agent_count_chip()` renders a zero-suppressing
  `[S1 R2 Q3 W1 F2 U3 D5]` with per-metric colors.
- **Stable accent colors exist.** `src/sase/palette_hash.py` gives
  `sha256(key)[:8] % len(palette)`, already shared by project, provider-kind, and
  monitor-status accents.
- **Admin Center tabs** are `config | logs | procs | projects | statistics | updates`
  (`config_center_catalog.py:17`), with `ProjectsSubTab = projects | repos | workspaces`.
- **The provider seam is real and idle.** `AgentsProviderSnapshot` carries `used_daemon`,
  `fallback_reason`, `snapshot_id`; `AgentEventApplyResult` carries `resync_required`;
  `AgentsViewport` bounds the read window; `agents_daemon_reads_enabled()` is a hard
  `return False` and the factory returns only `DirectAgentsDataProvider`.
- **The shared `agents` sidecar is not a liveness source.** Remote machines' agents *are*
  already in the local checkout (289 kellys_mbp, 88 apollo pages) — but pages read
  `**State:** completed`, published after the fact, among 11,070 historical directories.
  Useful later as a durable/content plane; useless for "what is running right now."
- **`tailscale status --json`** yields `HostName`, `DNSName`, `OS`, `Online`,
  `TailscaleIPs`, `Tags`, `LastSeen`, `MagicDNSSuffix` — everything discovery needs, and
  it also lists an Android phone, so discovery must filter and confirm rather than
  auto-enroll.

---

## 2. Critique: is there a better way to achieve the same goal?

### 2.1 Two goals are bundled; they should be unbundled

The request mixes:

- **(A) Placement** — "run this agent on a different machine," because `max_running_agents`
  is 10 and host-wide, or because the work needs macOS/a GPU/a different network.
- **(B) Fleet observability and control** — "see and manage every machine's agents from
  one TUI."

(A) is cheap, high-value, and needs no live federated state: you dispatch, and the thing
you dispatched shows up in your list. (B) is where all the cost lives — resident readers,
revision cursors, SSE feeds, staleness models, idempotency journals, mutation fencing —
and at N = 3 machines its marginal value is real but modest.

**They are separable, and separating them is the single biggest improvement available.**
`%dispatch` + auto-follow gives you the fleet rows you actually care about (the ones you
created) without a roster, a subscription UI, or a daemon. Build (A) first; let (B) earn
its way in.

### 2.2 The plugin seam: right instinct, wrong shape

**Keep:** generalizing beyond Tailscale, and shipping a built-in default. That instinct
is correct and it matches how SASE already handles VCS, LLM, and workspace providers.

**Change three things:**

1. **Split discovery from transport.** [Ansible's inventory-vs-connection split](https://docs.ansible.com/projects/ansible/latest/dev_guide/developing_plugins.html)
   is the canonical prior art: *inventory plugins define what hosts exist; connection
   plugins define how to communicate with them*. SASE's needs map one-to-one. Tailscale
   is an inventory plugin. HTTP-to-a-`sase_gateway` and SSH are connection plugins.
2. **Discovery must aggregate, so it must not be `firstresult`.** You may well want the
   tailnet *and* `~/.ssh/config` *and* a static list. Every other SASE hook family is
   `firstresult` because there is one right answer; here there are several partial ones.
3. **Transport is per-machine, not global.** Replace the proposed
   `dispatch_provider: tailscale` field with a `transport:` key on each machine record.
   This is not pedantry: it is what lets a work laptop reachable only over SSH coexist
   with tailnet peers, and it is what makes the SSH-first phasing possible.

**A fourth, quieter point:** discovery must never run at runtime. Shelling out to
`tailscale` on a render path, a tick, or a completion keystroke violates `tui_perf` rules
1, 8, and 11 (rule 11 is explicit that keystroke paths must not spawn subprocesses). The
request already anticipates this — "it's fine if auto-discovery is handled by
`sase init`" — and the design should make it *structurally impossible* to regress, by
having the discovery hook reachable only from `sase init` / `sase machine discover`.

### 2.3 The Local/Remote sub-tabs: six objections and a replacement

**O1 — The names contradict the contents.** The spec's Local tab holds subscribed remote
agents. The axis is followed/unfollowed, not local/remote. If two panes survive, they must
be named for what they hold — e.g. **Agents** and **Fleet** — not for a property half
their rows lack.

**O2 — It splits by provenance; the tab's job is attention.** The Agents tab answers
"what needs me?" A remote agent asking a question is exactly as urgent as a local one.
Putting it behind a tab boundary makes urgency a function of geography. The count chip
in the title mitigates but does not fix this — you now have to watch two numbers.

**O3 — SASE's own sub-tab precedent is by *kind*, not origin.** Artifacts sub-tabs are
`agents | stitches | patches | beads | files`: different objects, different verbs,
different detail panels. Remote agents are the *same object* with the *same verbs*. There
is no second pane's worth of difference.

**O4 — The gesture is unavailable.** `]`/`[` is the established sub-tab cycle and on the
Agents tab those keys are the thinking-panel toggles. A surface used once a day would
need to mint a *new* global gesture. That is a cost signal.

**O5 — It duplicates grouping machinery that already exists and is better.**
`GroupingMode` + `o`/`O` + accented banners + fold persistence + `machine:` in the query
language reproduces both tabs, and also expresses things two tabs cannot: "everything
failed anywhere," "everything on apollo needing input," "everything *except* athena." A
saved query is a user-defined tab; two hard-coded tabs are the degenerate case.

**O6 — The expensive half is the roster, and a roster is a picker.** "All remote agents
on all machines, enough info to decide whether to subscribe" is a *catalog*: consulted
rarely, shallow rows, its own verbs (follow, unfollow, see slots), and dangerous to render
eagerly (athena alone has 9,501 index rows). SASE consistently puts catalogs in the Admin
Center. Terminal tooling generally agrees:
[k9s stays single-context and switches](https://www.baeldung.com/ops/k9s-kubernetes-cluster-management),
while [aggregating dashboards are the exception and the heavyweight](https://crolytics.ai/k9s-vs-lens-kubernetes-management-comparison/).
The lesson is not "never aggregate" — it is "aggregate on demand, in a surface built for
it, not in the hot path."

**Steelman, honestly stated.** Sub-tabs are *discoverable* in a way a leader-key panel
is not, and a persistent Remote pane gives ambient fleet awareness. Both are real. But
discoverability for a single-user tool the user designed themselves is a weak
consideration, and ambient awareness is delivered better and cheaper by a top-bar
indicator visible from *every* tab — including Artifacts and AXE, where sub-tabs on
Agents show nothing at all.

**Replacement (ranked):**

1. **`machine:` query field + `BY_MACHINE` grouping mode + a Machines pane in the Admin
   Center + a `FleetIndicator` in the top bar.** No new tab chrome; every piece reuses an
   existing widget; the "two tabs" become two saved queries if the user wants them.
2. *If a dedicated surface is still wanted:* a fourth **top-level** tab, `Fleet`, in
   `TAB_ORDER`. It gets `tab`-cycling for free, its own keymap namespace (no `[`/`]`
   collision), and lazy composition exactly like `ArtifactsView`.
3. *If Agents sub-tabs are still wanted:* build them with `PanelTabStrip` +
   `ContentSwitcher` + `activate()`/`deactivate()`, name them **Agents** and **Fleet**
   (not Local/Remote), put `format_agent_count_chip()` in `PanelTab.label`, and pick a
   gesture that is not `]`/`[`.

### 2.4 "Subscribe": right idea, wrong word and wrong granularity

**Wrong word.** *Subscribe* implies push. It raises the question the spec never answers:
**if I subscribe to a remote agent, do its questions and gates reach my notification
inbox?** My answer is that this is the *entire point* — the reason to follow a remote
agent is so it can interrupt you — and it should be stated as a design commitment, not
discovered later. Use **follow** (`f`): it is the established verb for "keep this in my
view and tell me when it changes," it reads well on a row, and it pairs naturally with
SASE's existing `dismiss`.

**Wrong granularity.** Per-agent following means permanent curation: every `%dispatch`
creates a new one, and every agent someone (you, an hour ago, on another box) started
requires a trip to the roster. The natural units, in the order they should be built:

1. **Auto-follow anything I dispatched** — already in the spec, and correct.
2. **Follow a machine** — one decision, permanent: "show me apollo's live agents."
3. **Follow one agent** — the escape hatch, from the roster.
4. **Follow a query** — nearly free once `machine:` exists, and the most powerful:
   "anything, any machine, project sase, needs input."

Once the main list's source set is *local ∪ followed*, "follow a machine" is literally
"add the machine to the followed set," and the Local/Remote distinction dissolves into a
filter.

**Where follow state lives.** Viewer-local, one small file
(`~/.sase/fleet/follows.json`), mirroring `dismissed_agents.json`. **Never** in the
artifact index, the name registry, or dismissed bundles. That is the line separating this
feature from a resurrected `agents_sync` import leg, which epic `sase-ws` deliberately
deleted (decision `agents-sync-publish-only`).

### 2.5 `%dispatch`: keep it, sharpen it

**Keep** the directive form. It composes with `%{a | b}` fan-out, it is discoverable
through the existing directive completion menu, and it puts placement where the rest of
launch intent already lives.

**Sharpen six things.**

1. **Spelling.** `%dispatch` canonical, `%d` alias (free). `%on:apollo` reads better in
   prose but `on` is too common a word to sit at a directive position safely. Keep
   `%dispatch`.

2. **The argument is a *placement*, not a hostname.** Support
   `%dispatch:<machine>` · `%dispatch:auto` · `%dispatch:<tag>` · `%dispatch:local`.
   `auto` is the one that will actually get used — "run this somewhere that isn't busy" is
   the real feature, and it is what makes a 10-slot cap across three machines feel like 30.
   Tags (`gpu`, `macos`) seed naturally from Tailscale's `Tags` field. `local` exists so a
   per-project default can be overridden explicitly.

3. **Ship the residual prompt, not a resolved plan.** Strip only `%dispatch`; send the
   remaining prompt text plus a thin envelope (project key, origin machine, origin agent,
   idempotency key). Let the **target** parse the remaining directives, expand xprompts
   from *its* catalog, resolve model aliases from *its* config, allocate the name in *its*
   registry, and admit against *its* `max_running_agents`. This is the single most
   important decision in the whole feature: it makes `%dispatch` compose with every
   existing and future directive for free, and it keeps the target authoritative.
   `launch_mobile_text_agents()` already proves the shape works.

4. **Pre-flight validation is the feature.** This is where it will actually break, and a
   generic failure 30 seconds later in a log you have to hunt for is the difference
   between magic and garbage. Before shipping, refuse with a *specific* message when: the
   project is not enabled/checked out on the target; the prompt names local absolute
   paths, attachments, or images that will not exist there; a referenced sidecar is not
   cloned there (recoverable — the target clones lazily); the target lacks the provider or
   credential for the requested model; or the target is offline / unauthorized / wire-
   incompatible. **Render the target machine and the pre-flight verdict in the existing
   `launch_preview` / LaunchApproval gate** — the preview already exists; it just needs a
   destination line.

5. **Refuse cross-machine clans and waits in v1.** `%clan`, and `%wait:<agent>` naming an
   agent on another machine, create a family that can never complete without cross-machine
   agent-to-agent coordination — which both prior reports named as the condition that
   *reopens the transport decision*. Fail loudly at parse time. Silently producing a
   permanently-blocked family is the worst possible outcome.

6. **A failed dispatch stashes the prompt.** SASE already has a prompt stash
   (`restore_prompt_stash`, `@`, and a `StashedPromptsIndicator`). If the target is
   unreachable, the dispatch fails immediately — **never queues** — and the prompt lands
   in the stash. Recovery is a gesture the user already knows. This is the prettiest reuse
   available in the whole design.

Also: the dispatch itself must be a **tracked proc** (`tui_perf` rule 3) so it dedups,
appears in the Procs tab, and counts at quit; and it must be **idempotent** — the target
journals the request id before spawning, so a lost response retried yields exactly one
agent, not two runner slots and two invoices.

### 2.6 Alternatives I considered and rejected

| Alternative | Verdict |
| --- | --- |
| **Don't build it; just `ssh apollo` and run `sase` there** | Rejected. This *is* the status quo, and it loses the unified attention surface entirely — you must remember to go look. But it is the right mental model for the *transport*, which is why the SSH connection plugin is phase one. |
| **Build only `%dispatch`; never federate reads** | Genuinely tempting and it is ~70 % of the value. Rejected only because auto-follow implies you must be able to *see* what you dispatched, which requires at least the followed-set read path. |
| **Use the shared `agents` git sidecar as the fleet plane** | Rejected. Verified: pages carry terminal state only, published after the run, buried in 11,070 directories. Fine as a durable/offline content plane later; useless for liveness — and re-materializing it locally is exactly the import leg `sase-ws` deleted. |
| **A central scheduler that owns placement fleet-wide** | Rejected. A client scheduling from a 60 s-old snapshot oversubscribes; `max_running_agents` is host-wide and the target already has a working admission gate. The client proposes; the target decides. |
| **Make Tailscale a hard dependency after all** | Rejected on the user's own grounds, and independently: the transport is HTTPS and does not care where the address came from. Tailscale earns its keep in discovery, naming, and encryption — all of which it keeps in this design. |
| **A new global "dispatch provider" hook family** | Rejected in favor of discovery + transport, per §2.2. |
| **ZeroMQ / NATS / gRPC / new broker** | Not re-litigated. Three prior reports converged on "no"; nothing I measured changes that, and my 11 s-vs-10 ms finding makes the case *stronger*: no messaging framework can help a problem that is 99.9 % local CPU. |

---

## 3. The recommended design

### 3.1 Configuration (written by `sase init`, never inferred at runtime)

```yaml
machines:
  athena:
    self: true                          # no transport; this box
  apollo:
    transport: sase_host                # names a sase_machine_transport hookimpl
    endpoint: https://apollo.tail297af1.ts.net:7629
    identity: sha256:…                  # pinned at enrollment; fail closed on mismatch
    token_ref: keychain:sase/apollo     # never inline a secret
    tags: [linux, workhorse]
    projects: [gh_sase-org__sase, gh_bobs-org__bob-cli]   # cached; target re-verifies
    follow: live                        # off | live
  kellys_mbp:
    transport: sase_host
    endpoint: https://kellys-macbook-pro.tail297af1.ts.net:7629
    tags: [macos]
    follow: "off"
  work_laptop:
    transport: ssh                      # zero-install escape hatch
    ssh_host: work                      # resolved from ~/.ssh/config
    follow: "off"

fleet:
  staleness_horizon_seconds: 90
  default_dispatch: local               # local | auto
```

Notes: there is deliberately **no `discovery:` runtime key** — discovery is an init-time
action, not a setting. `sase machine add|check|discover|list|remove|status` follows
`cli_rules.md` (alphabetical subcommands, bare `sase machine` delegating to `list`, every
long option with a short alias, no required options). "Machine," never "node" — the
glossary already owns *Sase Node* / *Agent Node* in the exact surface this touches.

### 3.2 Hooks: `src/sase/machine_provider/`

Mirrors `vcs_provider/` exactly: `_hookspec.py`, `_plugin_manager.py`, `_registry.py`,
`_types.py`, `plugins/`, and a `sase_machine` entry-point group.

```python
hookspec = pluggy.HookspecMarker("sase_machine")

class MachineHookSpec:
    # DISCOVERY — aggregating (deliberately NOT firstresult).
    # Called only by `sase init` and `sase machine discover`. Never from a
    # render path, timer, tick, or completion keystroke.
    @hookspec
    def machine_discover(self) -> list[DiscoveredMachine]: ...

    # TRANSPORT — firstresult, dispatched on the record's `transport` name.
    @hookspec(firstresult=True)
    def machine_transport(self, record: MachineRecord) -> MachineTransport | None: ...
```

**Built-in discovery impls:** `tailscale` (parses `tailscale status --json`; contributes
nothing if the binary is absent), `ssh_config` (parses `~/.ssh/config` Host entries — the
chezmoi-managed config already names these boxes), `static` (reads a list from config).
All three enabled by default; all three cost zero at runtime because nothing calls them
at runtime.

**Built-in transport impls:** `sase_host` (HTTP/JSON + SSE to a `sase_gateway serve`
role) and `ssh` (`ssh <host> sase machine-bridge <op>`).

```python
class MachineTransport(Protocol):
    def hello(self) -> HostIdentity: ...          # pinned identity, wire version, capabilities
    def roster(self, cursor) -> RosterPage: ...   # shallow live rows (Machines pane only)
    def snapshot(self, cursor, selector) -> AgentSnapshotPage: ...  # AgentArtifactScanWire rows
    def events(self, cursor) -> Iterator[Invalidation] | None: ...  # None ⇒ poller fallback
    def dispatch(self, request) -> DispatchReceipt: ...             # idempotency-keyed
    def mutate(self, op) -> OperationReceipt: ...                   # kill/retry/answer/approve
    def fetch(self, handle) -> bytes: ...                           # content by opaque handle
```

**Capabilities are negotiated, not assumed.** `hello()` returns a capability set;
`ssh` declares `{dispatch, roster_on_demand, mutate}` and *not* `{live_follow, events}`.
This is the same structural-probe idiom `VCSPluginManager._has_hookimpls()` already uses,
and it is what lets a slow transport be *honestly* slow rather than silently broken: an
SSH machine simply cannot be set to `follow: live`, and the UI says why.

### 3.3 Execution model

Unchanged from the two prior reports where they agree, and I concur: each machine is the
**sole authority** for its own agents; liveness is a **resolved verdict** shipped by the
owner with its resolution timestamp, never a viewer inference; remote paths are **inert**
(`RemoteArtifactRef` with no `__fspath__`, so misuse is a type error, not a runtime
disaster); mutations are **name-addressed, target-resolved, journaled, revision-fenced,
and never queued**; the viewer cache is one disposable blob per machine under
`~/.sase/machines/<machine>/`, touching no index, registry, or dismissal state; and with
zero machines configured the code path is **byte-for-byte today**.

Two additions specific to this design:

- **A followed remote agent never disappears.** Past the staleness horizon it degrades
  `RUNNING → UNKNOWN`, renders a stale age, and becomes non-actionable — but it stays on
  screen. Vanishing rows destroy trust faster than wrong ones.
- **Attention federates or the feature is a toy.** Following a remote agent must route its
  questions and gates into the local notification inbox, read-only, with *acting* on them
  routed back as a mutation. The gateway already serves the attention plane
  (notifications, gate approval, question answering) — this is mostly wiring, and it is
  what makes "follow" mean something.

### 3.4 The UX, concretely

**One Agents list.** Local rows carry **no badge** — absence is the cheapest signal and it
keeps the common case quiet. Followed remote rows carry a 2–3 character machine badge in a
`palette_hash`-derived accent, so `apollo` is the same teal in the badge, the
`BY_MACHINE` banner, the Machines pane, and the top-bar indicator. Freshness is a single
glyph — `●` fresh · `◐` reconnecting · `○` stale — with the exact age on the detail panel.
No spinners in a list.

**`machine:` query field.** Joins `status:`, `project:`, `model:`, `provider:`, `tribe:`,
`type:`, `source:`, `needs:`, `text:`, `age`. `machine:athena` and `-machine:athena` are
the requested two tabs, as saved queries. Push it down through
`compile_agent_query_pushdown` like every other facet.

**`BY_MACHINE` grouping mode.** A fourth `GroupingMode`, on the existing `o`/`O` cycle,
rendering L0 banners in the machine accent with the existing count chip. The fleet view
then *looks like* the project view — parity, not a new visual language.

**Machines pane in the Admin Center** (`CenterTab` gains `machines`, alphabetically
between `logs` and `procs`), with `MachinesSubTab = machines | agents` mirroring
`ProjectsSubTab`. Left: machine cards — link state
(`online · reconnecting · stale · unauthorized · incompatible · offline`), capacity meter
(`R4/10`), count chip, project availability, last-seen. Right: that machine's shallow
live roster; `f` follows/unfollows; a followed row shows a filled bookmark glyph.
Data is fetched **only while the pane is open**, enforced by the existing
`activate()`/`deactivate()` lifecycle. Reached with a leader key (`,F`) or the Admin
Center's numbered sub-tab selection.

**`FleetIndicator` in the top bar.** `⌁ apollo 4 · mbp 2`, collapsing to `⌁ 6` when
narrow, served from the federate cache and stale-badged. This carries the count the
sub-tab titles were going to carry — and carries it on *every* tab, including the ones
where an Agents sub-tab would show nothing. One widget, alongside the nine indicators
already there.

**Dispatch feedback.** `%dispatch:apollo` shows the destination in the launch preview with
its pre-flight verdict, runs as a tracked proc, and on success inserts the new agent into
the list already followed, badged `apollo`, in `STARTING`. On failure it toasts a specific
reason and stashes the prompt.

### 3.5 Why this is lazy by construction

Laziness has to be structural, not aspirational. Four rules do it:

1. **Zero machines configured ⇒ zero fleet code runs.** No widget, no timer, no import,
   no socket. The flag-off branch is today's binary.
2. **Discovery is unreachable at runtime.** The hook is called only from `sase init` /
   `sase machine discover`. It cannot regress into a render path because nothing on a
   render path can reach it.
3. **The roster is pane-scoped.** `activate()`/`deactivate()` already gates it.
4. **The main list fetches only the followed set** — live tier only, never history,
   cursor-paged, gzipped (~18 KB/machine per prior measurement).

Plus the standing `tui_perf` rules, which are acceptance criteria rather than advice: all
transport I/O in `spawn_pump_free_task()` cancelled at teardown; cache-first first paint
that never awaits the network; deltas as `patch_row()` calls, never list rebuilds;
selection re-captured after every await (remote latency widens that window); explicit
deadlines, jittered backoff, and a per-machine circuit breaker so one hung host cannot
touch p95 `j`/`k`; and the connection state living in a `sase_gateway federate` process
rather than in ACE, because **ACE restarts constantly and the fleet connection should
not**.

---

## 4. Phasing

One `beta` feature flag, `remote_dispatch`, created with `sase flag new` per
`sase_flags.md`, removed when P5 lands (delete the Off branch, make On unconditional,
close the bead).

| Phase | Deliverable | Why here |
| --- | --- | --- |
| **P0** | **Resolution/presentation split** in the ACE agent loader; fence liveness checks, index mutation, and `artifacts_dir` behind an explicit resolution pass. **`machine:` query field + `BY_MACHINE` grouping.** | Pure local win. Fixes the 11 s fixed-cost enumeration. Zero network. Do it even if the fleet is cancelled. |
| **P1** | `src/sase/machine_provider/` hooks; `machines:` config; `sase machine` CLI; `sase init` discovery step with `tailscale` / `ssh_config` / `static` impls. | The CLI must exist before the TUI — agents and scripts need it, and it is how the config gets written. |
| **P2** | **`ssh` transport + `%dispatch:<machine>`**, pre-flight validation, launch-preview destination, tracked proc, target-side idempotency journal, auto-follow, failed-dispatch-to-stash, cross-machine clan/wait refusal. | **First user-visible payoff, and it needs no daemon anywhere.** Also proves the plugin seam with a second implementation before the expensive one is written. |
| **P3** | **Machines pane** in the Admin Center (roster on demand, follow/unfollow, slots, projects, link states) + **`FleetIndicator`**. | The "Remote sub-tab" requirement, delivered where catalogs live. |
| **P4** | `sase_gateway serve` role: resident `sase_core` reads, resolution pass, monotonic index `revision` + tombstones, real `AgentsChanged{revision}` SSE, gzip. **Blocker: fix pairing (currently self-authorizable once remotely reachable), scope tokens, pin identity — before any tailnet exposure.** | The performance transport, behind the seam P2 proved. |
| **P5** | `federate` role + `sase_host` transport + `FederatedAgentsDataProvider` behind the existing seam: followed remote rows in the main list, cache-first, staleness-degraded. **Read-only.** | The observability half, now on a wire that costs milliseconds. |
| **P6** | Remote mutations: kill, answer-question, approve-gate — journal, host-side name resolution, revision fencing, fault gates. Attention federation. | Blast radius grows here; it goes last among the essentials. |
| **P7** | `%dispatch:auto` + tags; content-by-handle (enabling remote fork / retry / kill-and-edit); phone sees the fleet through one pairing. | Compounding wins, all cheap once P5 lands. |

The reordering relative to `tailnet_fleet_federation` is deliberate: **dispatch before
federation, SSH before HTTP.** It front-loads the value, defers the daemon, and buys a
second transport implementation as the design's own regression test.

### 4.1 Acceptance gates

**P2 (dispatch):** a lost dispatch response retried with the same key yields exactly one
agent; an unreachable target fails immediately and stashes the prompt; a dispatch naming a
project absent on the target is refused *before* sending, with the project named; a
cross-machine `%clan` / `%wait` is refused at parse time; the dispatched agent's name is
allocated by the target and never by the origin; no local artifact, index row, or registry
entry is created for the remote agent beyond one follow entry.

**P5 (read-only federation):** local rows paint and stay navigable with one machine hung;
healthy machines hydrate independently; cached rows show honest ages and degrade
`RUNNING → UNKNOWN` past the horizon; a machine that goes offline never loses its rows;
daemon restart, cursor gaps, and replay overflow converge automatically; sleep/wake and
direct↔DERP transitions recover without restarting ACE; an endpoint presenting a different
pinned identity fails closed; no snapshot discloses an actionable absolute path (asserted
by type *and* by test); p95 `j`/`k` stays under 16 ms with one machine hung; flag off is
byte-for-byte today.

**P6 (mutations):** a disconnect mid-kill recovers the journaled terminal result; a stale
kill against a reused name or recycled PID returns a conflict, never a wrong kill; a
stale-`UNKNOWN` row refuses mutation; revoked tokens and denied grants stop access
predictably; turning the daemon off leaves local CLI and ACE fully functional.

---

## 5. Open questions for you

1. **Is placement or observability the real motivation?** If it is placement, P0–P2 may be
   the whole feature and P4–P6 can wait indefinitely. My reading of "I want to dispatch to
   remote machines" is that placement leads — but the sub-tab spec implies observability
   leads. This changes the phasing more than any other answer.
2. **Do you accept dropping Local/Remote sub-tabs** for `machine:` + `BY_MACHINE` + a
   Machines pane + a top-bar indicator? If not, do you prefer a fourth top-level `Fleet`
   tab (ranked #2) or Agents sub-tabs renamed to **Agents / Fleet** (ranked #3)?
3. **Should following a remote agent route its questions and gates into your local
   notification inbox?** I have designed for yes. If no, "follow" is only a visibility
   choice and P6 shrinks a lot.
4. **Follow-a-machine as the primary gesture, per-agent as the escape hatch?** Or is
   per-agent curation actually what you want?
5. **`%dispatch:auto` in v1 or v7?** It is the placement feature people will actually use,
   but it needs live slot data from every candidate, which means it cannot ship before P5
   unless `auto` is allowed to mean "ask each candidate synchronously over SSH," which at
   ~11 s × N is honest but slow.
6. **Is 90 s the right staleness horizon** — a config field, not a flag, trading
   phantom-`RUNNING` risk against badge churn?
7. **Remote `tmux attach`:** refuse with an explanation, or shell out to
   `ssh -t <machine> tmux attach`? I have assumed refuse-plus-explicit-escape.

---

## 6. Sources

**Repo evidence** (verified 2026-09-06 against `sase` @ `58f16fe68`, `sase-core` @
`0504155`): `src/sase/{vcs,workspace,llm}_provider/{_hookspec,_plugin_manager,_registry}.py`;
`src/sase/config/_owner.py:54`; `src/sase/core/agent_identity_facade.py`;
`src/sase/core/machine_hood_facade.py` (now scoped to *legacy v1 transport* only — the
predecessor reports' identity plumbing claim is thinner than it reads);
`src/sase/xprompt/_directive_types.py`, `_directive_extract.py`;
`src/sase/agent/launch_request*.py`, `launch_preview.py`, `launch_admission.py`,
`launch_spawn.py`, `running.py:45`; `src/sase/integrations/_mobile_agent_launch.py`,
`mobile_agents.py`; `src/sase/main/{parser_init,init_registry,parser_mobile}.py`;
`src/sase/ace/tui/{tab_order,artifact_tabs,_artifact_tab_model,agent_count_chip,
provider_contract}.py`; `src/sase/ace/tui/data_providers/{_types,_factory,_settings}.py`;
`src/sase/ace/tui/widgets/{tab_bar,panel_tab_strip,_agent_list_render_banner}.py`;
`src/sase/ace/tui/widgets/artifacts/view.py`;
`src/sase/ace/tui/modals/{config_center_catalog,config_hub_pane,config_hub_session,
projects_pane}.py`; `src/sase/ace/tui/models/agent_groups/_buckets.py`;
`src/sase/ace/agent_query/{tokenizer,evaluator,pushdown}.py`;
`src/sase/feature_flags/registry.py`; `src/sase/palette_hash.py`;
`src/sase/default_config.yml` (`max_running_agents: 10` at line 38; keymaps at lines 291–760);
`~/.sase/projects/gh_sase-org__sase/repos/agents/` (11,070 pages).

**Live probes (athena, 2026-09-06):** `sase --version`; `sase agent list --json` in three
scopings; SQLite read-only probe of `agent_artifact_index.sqlite`; `tailscale status`,
`tailscale status --json`, `tailscale ping apollo`.

**Prior SASE research:**
`research:202609/tailnet_agent_fleet/tailnet_agent_fleet.md` (superseded),
`research:202609/sase_collaboration_architecture.md`,
`research:202609/tailnet_fleet_federation/tailnet_fleet_federation.md`.

**Project memory and decisions:** `tui_perf.md`, `cli_rules.md`, `sase_flags.md`; core
memory `rust_core_backend_boundary`; decisions `agents-sync-publish-only`,
`rust-core-required`, `two-speed-verification`, `single-turn-agents`.

**External:**
[Ansible: developing plugins](https://docs.ansible.com/projects/ansible/latest/dev_guide/developing_plugins.html) ·
[Ansible inventory plugins](https://docs.ansible.com/projects/ansible/latest/plugins/inventory.html) ·
[Ansible connection plugins](https://docs.ansible.com/ansible/latest/plugins/connection.html) ·
[pluggy documentation](https://pluggy.readthedocs.io/en/stable/) ·
[pluggy API reference (`firstresult`)](https://pluggy.readthedocs.io/en/stable/api_reference.html) ·
[Plugins case study: Pluggy — Eli Bendersky](https://eli.thegreenplace.net/2026/plugins-case-study-pluggy/) ·
[Managing Kubernetes clusters with k9s](https://www.baeldung.com/ops/k9s-kubernetes-cluster-management) ·
[k9s vs Lens comparison](https://crolytics.ai/k9s-vs-lens-kubernetes-management-comparison/) ·
[Top open-source Kubernetes dashboards (multi-cluster aggregation)](https://www.bytebase.com/blog/top-open-source-kubernetes-dashboard/)

---

## 7. Recommended solution

**Build remote dispatch as two small pluggy hook families, ship it over SSH first, and
replace the Local/Remote sub-tabs with a query facet, a grouping mode, an Admin Center
pane, and a top-bar indicator.**

Concretely:

1. **Split the seam in two.** `machine_discover` (aggregating, called only by
   `sase init` / `sase machine discover`; built-ins `tailscale`, `ssh_config`, `static`)
   and `machine_transport` (`firstresult`, keyed by a `transport:` field on each machine
   record; built-ins `ssh` and `sase_host`). Tailscale becomes a *discovery* plugin —
   enabled by default, free at runtime, never a hard dependency. There is no global
   `dispatch_provider:` setting, because machines are heterogeneous and transport belongs
   on the machine.

2. **Fix the local list before touching the network.** 11 s for 19 agents — the same 11 s
   whether the answer is 3 bytes or 161 KB — is the actual bottleneck, and splitting
   resolution from presentation in the ACE loader fixes it for local users regardless of
   whether the fleet ever ships. It also makes remote parity *structural* rather than a
   checklist: the owner resolves, the viewer presents, both running code that already
   exists.

3. **Ship `%dispatch` over SSH in one phase, with no daemon.** Strip only `%dispatch`,
   send the residual prompt plus a thin envelope, and let the target parse, expand, name,
   and admit it — the path `launch_mobile_text_agents()` already walks. Validate
   pre-flight and refuse specifically; render the destination in the existing launch
   preview; run it as a tracked, idempotent proc; auto-follow the result; stash the prompt
   on failure; never queue; refuse cross-machine clans and waits. This delivers the
   feature's core value before a single line of daemon code exists, and it proves the
   plugin seam with a second real implementation.

4. **Drop the Local/Remote sub-tabs.** They split by provenance when the tab's job is
   attention; they name a tab "Local" that holds remote rows; they need a gesture that is
   already spent on the thinking panel; and they duplicate grouping machinery that already
   exists and generalizes better. Instead: a `machine:` query field, a `BY_MACHINE`
   grouping mode on the existing `o`/`O` cycle, a **Machines** pane in the Admin Center
   beside Projects (which is the same kind of thing), and a `FleetIndicator` in the top
   bar carrying the count — visible from every tab rather than one.

5. **Say "follow," not "subscribe," and follow machines before agents.** Auto-follow what
   you dispatched, follow a machine with one decision, follow an agent as the escape
   hatch, follow a query once `machine:` exists. Keep follow state in one viewer-local
   file that touches no index, registry, or dismissal state — that single constraint is
   what keeps this from becoming the import leg `sase-ws` deleted. And commit to the
   consequence: a followed remote agent's questions and gates reach your inbox, because
   otherwise following means nothing.

6. **Only then federate reads and mutations**, behind the `sase_host` transport, the
   resident Rust reader, one monotonic revision that is simultaneously cursor, delta
   query, and mutation fence — and with the gateway's pairing, token scoping, and identity
   pinning fixed *before* the first tailnet exposure, since Serve publication is precisely
   what makes today's self-authorizable pairing flow reachable.

This is **intuitive** because nothing new is learned: a remote agent is an agent with a
badge, a machine is a filter and a group like a project, the fleet catalog lives where
every other catalog lives, and a failed dispatch is a stashed prompt. It is **reliable**
because each failure has one bounded consequence — no machines configured means no code
runs, an unreachable target means an immediate honest failure and a saved prompt, a stale
row means `UNKNOWN` rather than a phantom kill target, and a lost response means a retry
that cannot duplicate. And it is **beautiful** because the machine's accent is the same
color in the badge, the banner, the pane, and the indicator; because local rows stay
unmarked so the common case stays quiet; and because remote and local rows are built by
the same function from the same contract, so parity is not a promise to maintain but the
shape of the thing.
