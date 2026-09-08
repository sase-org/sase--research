---
create_time: 2026-09-08
updated_time: 2026-09-08
status: research
---

# Why The Focus/Fleet Sub-Tabs Are Invisible, And What It Takes To Actually Use Remote Machine Management

**Research question:** epic `sase-xe` ("Remote dispatch and the Focus/Fleet agents
experience") is closed with all 15 phases done, but the Agents tab in the TUI still shows
no Focus/Fleet sub-tabs. Why? And what is the concrete, minimal sequence of steps required
to use SASE's new remote machine management functionality end to end?

**Scope:** `sase` at master `0b292e49f`; linked `sase-core` at `1396607` (v0.32.43), pinned
in `sase-core-revision.txt` at `3fa05777d`. Read paths: the ACE fleet mixin
(`src/sase/ace/tui/actions/agents/_fleet.py`), the whole `src/sase/dispatch/` package, the
`sase machine` CLI (`src/sase/main/parser_machine.py`, `machine_handler.py`,
`init_machine_handler.py`), the dispatch config schema and defaults, the gateway crate
(`crates/sase_gateway/src/{routes,fleet_auth,main}.rs`), `crates/sase_core/src/fleet_contract.rs`,
and the accepted plan `plan:202609/remote_dispatch_fleet.md`. Live state was sampled on
this machine (`athena`): `sase machine list`, `sase machine --help`, `sase config layers`,
the installed console-script set, and a direct `load_federation_config()` probe.

---

## Executive summary

There are **two separate reasons** you see nothing, and only the first one is by design.

1. **The strip is gated on enrollment, not on a flag.** With `dispatch.machines` empty,
   `_agents_fleet_available` is false and `#agents-header` is force-hidden. This is exactly
   what the plan specifies ("rendered only when at least one machine is enrolled; before
   that, the tab is visually unchanged"). Nothing is broken here. `sase machine list` on
   this machine confirms the state: *"No remote machines are configured."*

2. **Enrollment cannot currently be completed, because the target-side half of the
   handshake has no user-facing surface.** `sase machine add` requires a one-time
   *enrollment bundle* minted on the target machine. The only code that mints one is
   `FleetCredentialStore::issue_bootstrap` in the Rust gateway — and it is reachable from
   **no CLI, no HTTP route, and no PyO3 binding**. Its own contract snapshot names it
   "local-only Rust `FleetCredentialStore::issue_bootstrap` API". Every non-test call site
   in the repository is a Rust unit test.

So the honest status is: **the viewer half of remote dispatch shipped complete; the
operator-facing enrollment ceremony did not.** Everything downstream of a valid bundle
(enroll → pin → credential → federation worker → Fleet rows → `%dispatch`) is implemented
and wired.

Three smaller gaps compound it:

- `builtin@tailnet` discovery is a **stub that returns `()`** — `sase machine discover`
  can never produce a candidate.
- The three new keybindings (`cycle_agents_subtab`, `cycle_agents_subtab_reverse`,
  `toggle_agent_follow`) ship as **`"unbound"`**, so even after enrollment the strip is
  mouse/command-palette-only.
- There is **no docs page** for `sase machine` or `%dispatch`; `docs/cli.md` has no
  `machine` row.

The recommendation is a small, well-bounded follow-up: add one `sase machine bootstrap`
(or `sase mobile gateway bootstrap`) command that calls `issue_bootstrap` and prints the
bundle, bind the three keymaps, and implement the tailnet discovery provider. A verified
manual workaround for the missing command is given in §4 so you can exercise the feature
today.

---

## 1. Why the sub-tabs are hidden — the gating chain

The chain is short and entirely deterministic:

1. `_apply_fleet_projection` sets availability from three inputs
   (`src/sase/ace/tui/actions/agents/_fleet.py:396`):

   ```python
   self._agents_fleet_available = bool(
       config.hosts or config.diagnostics or projection.configured_host_count
   )
   ```

2. `_update_agents_header` (`_fleet.py:478`) hides the widget unless
   `_fleet_mode_available()` is true (`_fleet.py:486`):

   ```python
   if not self._fleet_mode_available() and not getattr(self, "_agents_fleet_loading", False):
       header.add_class("hidden")
       return
   ```

3. All three inputs are empty when no machine is configured, because
   `load_federation_config` returns early before it can produce hosts *or* diagnostics
   (`src/sase/dispatch/federation/_hosts.py:87`):

   ```python
   if not dispatch_config.machines:
       return FederationConfig(worker=worker, diagnostics=tuple(diagnostics))
   ```

4. `src/sase/default_config.yml:37` ships `machines: {}`, and this machine's user layer
   (`~/.config/sase/sase.yml`) declares no `dispatch` key at all (`sase config layers`
   confirms: `dispatch` appears only in the `default` layer).

**Note that the feature flag is irrelevant now.** `remote_dispatch` was removed in the
`sase-xe.15` / landing work on both sides of the boundary — the Python registry no longer
has it and `sase-core` no longer gates `%dispatch` in `editor/wire.rs`. Toggling flags in
the TUI flag pane will never make the strip appear; only an entry under `dispatch.machines`
will.

### The zero-machine discovery affordance does exist (but is only a notification)

The landing turn fixed the epic's own note #1 by adding `app.setup_agent_machine`
("Agents: connect a machine"), available exactly when the fleet is *not* enabled
(`src/sase/ace/tui/commands/_availability_agents.py:121`). Its handler
(`_fleet.py:146`) does not open a wizard — it emits a 12-second notification telling you to
run `sase machine discover` then `sase machine add <alias> <https-endpoint>` from a shell.
Two problems with that guidance:

- `sase machine discover` cannot return anything (§3).
- `sase machine add` cannot succeed without a bundle you cannot mint (§2).

---

## 2. The real blocker: no way to mint an enrollment bundle

### What `sase machine add` demands

`MachineService.add_machine` (`src/sase/dispatch/machine_service.py:81`) does, in order:

1. validate the alias; reject a duplicate;
2. **require the provider to be enabled** (`provider_enabled(provider_ref)`);
3. parse the pasted bundle (`_parse_enrollment_bundle`, `machine_service.py:330`) — it
   accepts JSON, YAML, or base64-encoded JSON, and requires `bootstrap_id`,
   `bootstrap_secret`, and `pinned_installation_id` (alias `installation_pin`);
4. `POST <endpoint>/api/fleet/v1/enroll` with the bundle plus controller metadata;
5. verify the returned installation identity equals the pin, store the bearer credential in
   a 0600 store, and write the machine record into config.

The CLI reads the bundle from `--bootstrap-file` or an interactive `getpass` prompt and
**never** from a command-line option (`src/sase/main/machine_handler.py:199`). Config alone
cannot substitute: `dispatchMachineRecord` in `src/sase/config/sase.schema.json` requires
`provider`, `endpoint`, `credential_ref`, **and** `installation_pin` matching
`^sase_inst_v1_[0-9a-f]{64}$`, and `credential_ref` must resolve to a real bearer token in
the local credential store.

### Where a bundle is supposed to come from

`crates/sase_gateway/src/fleet_auth.rs:89`:

```rust
pub fn issue_bootstrap(
    &self,
    request: FleetBootstrapIssueRequestWire,
    now_unix: f64,
) -> Result<FleetBootstrapIssueResponseWire, FleetStoreError>
```

It generates `bootstrap_id` (`boot_…`) and `bootstrap_secret` (`sase_bootstrap_…`), stores
`sha256("sase-fleet-bootstrap-v1\0" || secret)`, pins the gateway's installation identity,
and defaults to a **600-second, single-use** TTL.

**Nothing calls it outside tests.** Verified three ways:

- `crates/sase_gateway/src/routes.rs:760` — the fleet router exposes `enroll`, `hello`,
  `summary`, `catalog`, `batch`, `detail`, `content`, `projects/eligibility`, `events`,
  `launch`, `mutate`, `attention`, `attention/resolve`, `credential/rotate`,
  `credential/revoke`. **No bootstrap-issuing route** (correctly so — it would have to be
  unauthenticated).
- `crates/sase_gateway/src/main.rs` — the binary's flags are `--bind`, `--sase-home`,
  `--allow-non-loopback`, `--contract-out`, `--fleet-contract-out`,
  `--agent-bridge-command`, `--helper-bridge-command`, and the push options. **No
  subcommand at all.**
- `crates/sase_core_py/src/lib.rs` exposes no bootstrap binding, and
  `grep -rn "issue_bootstrap\|FleetBootstrapIssue" src/` in the Python repo returns nothing.

The gateway's own contract snapshot documents the gap in its own words
(`crates/sase_gateway/src/contract.rs:939`):

```json
"bootstrap": { "issuer": "local-only Rust FleetCredentialStore::issue_bootstrap API", ... }
```

The plan assumed an operator ceremony here — "run the authenticated enrollment handshake
(operator enters the short-lived bootstrap secret **generated on the target**)"
(`plan:202609/remote_dispatch_fleet.md`, `machine-cli` phase) — but no phase ever built the
generator's user-facing surface.

---

## 3. Secondary gaps found while tracing the path

| Gap | Evidence | Effect |
| --- | --- | --- |
| Tailnet discovery is a stub | `src/sase/dispatch/providers.py:73` — `dispatch_discover` returns `()` for `builtin@tailnet` and `()` otherwise; no `tailscale` reference anywhere in the tree | `sase machine discover` always prints nothing; `sase init machine` reports "No remote machine candidates found." |
| Tailnet provider is disabled by default | `src/sase/default_config.yml:35-36` (`builtin@tailnet.enabled: false`), and `discovery.enabled_providers: []` | Even a working provider would be skipped; `discover_dispatch_candidates` filters on `provider_enabled` |
| The new keys ship unbound | `src/sase/default_config.yml:519-521` — `cycle_agents_subtab`, `cycle_agents_subtab_reverse`, `toggle_agent_follow` all `"unbound"` | After enrollment the strip is reachable only by mouse click (`PanelTabStrip.TabClicked`, `_fleet.py:70`) or the command palette |
| `sase machine list` shows no local identity row | Observed output is a bare "No remote machines are configured." | The plan called for the local machine's own identity row first ("one machine vocabulary, not two"); it is also the natural place to surface your own `installation_id` |
| No documentation | `grep -rln "sase machine\|%dispatch" docs/` matches only `docs/plugins.md`; `docs/cli.md` has no `machine` row | No runbook exists for any of this |
| `sase_gateway` binary is not distributed | `crates/sase_core_py/pyproject.toml:37` ships only `sase_federation_worker` as a console script; `~/.local/share/uv/tools/sase/bin/` contains `sase_federation_worker` but **not** `sase_gateway`; no built binary exists under any `sase-core/target/` | The target machine must build the gateway from source with cargo |

The viewer-side worker is fine: `sase_federation_worker` **is** installed and
`resolve_federation_worker_command` (`src/sase/dispatch/federation/_supervisor.py:26`)
finds it on `PATH`, falling back to linked/external `sase-core` dev builds.

---

## 4. Steps to use remote machine management

Two tracks. Track A is the honest, complete sequence assuming the missing command is added
(§5). Track B is a verified workaround that works **today** without changing any code.

Terminology: **target** = the machine that will run agents (e.g. `apollo`); **viewer** =
the machine running your TUI (e.g. `athena`).

### 4.1 Just want to see the sub-tabs (30 seconds, no target needed)

The strip appears on `config.hosts` **or** `config.diagnostics`. A machine entry with a
missing credential produces a diagnostic, which is enough. Verified directly:

```python
>>> load_federation_config({"dispatch": {"machines": {"apollo": {...}}}})
hosts: 0
diagnostics: (MachineDiagnostic(code='credential_missing',
              message='credential ref fleet:apollo is missing from the local store',
              severity='error', alias='apollo'),)
```

Add to `~/.config/sase/sase.yml` (via chezmoi — that file is chezmoi-managed):

```yaml
dispatch:
  machines:
    apollo:
      provider: builtin@https
      endpoint: https://apollo.your-tailnet.ts.net
      credential_ref: fleet:apollo
      installation_pin: sase_inst_v1_<64 hex chars from the target>
```

Restart ACE. Focus/Fleet appears; Fleet shows `apollo` as unavailable with the
`credential_missing` diagnostic. Use this to confirm the UI exists — it is not a working
fleet.

### 4.2 Track A — the intended sequence (blocked on §5, item 1)

**On the target machine:**

1. **Build and install the gateway.** It is not in the wheel:
   ```
   cd <sase-core checkout> && cargo build --release -p sase_gateway
   cp target/release/sase_gateway ~/.local/bin/
   ```
2. **Start it loopback-bound.** The fleet API is served by the *same* process as the mobile
   API (`routes.rs:709` nests `/api/fleet/v1` into the main router):
   ```
   sase mobile gateway start          # 127.0.0.1:7629 by default
   ```
   Keep the `127.0.0.1` bind. `docs/mobile_gateway.md` is explicit: use Tailscale Serve in
   front of loopback rather than `--allow-non-loopback`, and never Funnel.
3. **Expose it over HTTPS.** `tailscale serve` in front of `127.0.0.1:7629` gives you
   `https://<target>.<tailnet>.ts.net`. Plain HTTPS with your own TLS termination also
   works — the client hard-requires the `https://` scheme
   (`src/sase/dispatch/fleet_client.py:100`).
4. **Note the installation identity.** The gateway writes/reads
   `<sase_home>/installation_identity.json`
   (`crates/sase_core/src/fleet_contract.rs:1312`). Its `installation_id` is the value the
   viewer pins. (On this machine: `~/.sase/installation_identity.json` already exists.)
5. **Mint a one-time enrollment bundle.** *This is the missing step.* Once the command in
   §5 exists it will print JSON containing `bootstrap_id`, `bootstrap_secret`,
   `pinned_installation_id`, `supported_protocol_versions`, `requested_scopes`. It expires
   in 10 minutes and is single-use.

**On the viewer machine:**

6. **Enable the provider you will use.** `builtin@https` is enabled by default;
   `builtin@tailnet` is not. `add_machine` refuses a disabled provider outright:
   ```yaml
   dispatch:
     providers:
       builtin@tailnet:
         enabled: true      # only if you pass -p builtin@tailnet
   ```
7. **Enroll.** Paste the bundle at the prompt, or hand it over as a file:
   ```
   sase machine add apollo https://apollo.your-tailnet.ts.net
   sase machine add apollo https://apollo.your-tailnet.ts.net -B ./bundle.json
   ```
   This performs the handshake, verifies the returned identity against the pin, writes the
   bearer token to the 0600 credential store, and writes the machine record to config.
8. **Verify:**
   ```
   sase machine list                 # config only, no network
   sase machine status apollo        # authenticated hello: reachability, protocol, counts
   sase doctor                       # dispatch.config + dispatch.credentials
   sase doctor --deep                # adds dispatch.live (gateway hello)
   ```
9. **Open ACE.** Focus/Fleet now renders. Switch modes by clicking the strip or via the
   command palette ("Agents: …"). To get keys, bind them yourself (they are `"unbound"` by
   default) in `ace.keymaps.app`:
   ```yaml
   ace:
     keymaps:
       app:
         cycle_agents_subtab: "B"
         cycle_agents_subtab_reverse: "I"
         toggle_agent_follow: "P"
   ```
   The plan flagged `B`/`I`/`P` and the digits `1`-`9` as the known-free options on the
   Agents tab; `[`/`]` are already `toggle_thinking`.
10. **Launch remotely:**
    ```
    sase run "#gh:sase %dispatch:apollo Investigate the cache regression."
    ```
    `%dispatch` is now unflagged in both the Python directive table
    (`src/sase/xprompt/_directive_types.py:46`) and the Rust contract. Dispatched agents are
    auto-followed, so they appear in **Focus**. Remote kill/retry/fork/answer/approve run
    through `sase machine agent` and `sase machine attention`, or the equivalent ACE
    actions.

### 4.3 Track B — verified workaround to mint a bundle today

The gateway's bootstrap store is a plain JSON file with a hashed secret, so you can seed a
bootstrap record by hand. **On the target**, with the gateway stopped:

1. Read `<sase_home>/installation_identity.json` → `installation_id`.
2. Choose any `bootstrap_id` and `bootstrap_secret` (non-empty, ≤256 bytes, no control
   characters — `validate_label`, `fleet_auth.rs:859`).
3. Compute `secret_hash = sha256(b"sase-fleet-bootstrap-v1\x00" + secret.encode()).hex()`
   (`hash_secret`, `fleet_auth.rs:923`).
4. Append a record to `<sase_home>/fleet_gateway/credentials.json` (schema_version `1`,
   under `bootstraps`), with fields `bootstrap_id`, `secret_hash`, `allowed_scopes`
   (**empty list = all 14 default scopes**, `default_fleet_scopes`, `fleet_auth.rs:713`),
   `supported_protocol_versions: [1]`, `pinned_installation_id`, `issued_at_unix`,
   `expires_at_unix` (set it generously), and `consumed_at_unix`/
   `consumed_by_credential_id`/`revoked_at_unix` all `null`. Keep the file `0600`.
5. Start the gateway. Its credential cache refreshes on `credentials.json` metadata change,
   so a restart is the safe way.
6. On the viewer, hand `sase machine add` a bundle file:
   ```json
   {"bootstrap_id": "...", "bootstrap_secret": "...",
    "pinned_installation_id": "sase_inst_v1_...",
    "supported_protocol_versions": [1], "requested_scopes": []}
   ```

This is a legitimate stopgap for your own machines, not a pattern to keep: it puts a
long-lived shared secret through a hand-edited file, whereas the real command mints a
10-minute single-use secret. Treat it as a way to exercise §4.2 steps 6-10 now and to
validate the rest of the stack before the command lands.

---

## 5. Recommended follow-up work, in priority order

1. **`sase machine bootstrap` on the target** (small, unblocks everything). A thin command
   that calls `FleetCredentialStore::issue_bootstrap` and prints the bundle as JSON /
   base64 / YAML — the three forms `_parse_enrollment_bundle` already accepts. Two viable
   placements: a `--bootstrap` mode on the `sase_gateway` binary (it already has
   `--sase-home`, and the store is a pure local-file operation needing no running server),
   or a PyO3 binding plus a `sase machine bootstrap` subcommand for symmetry with
   `sase machine add`. The gateway binary route is smaller and keeps the secret-minting
   code on the Rust side of the boundary. **Do not add an HTTP route** — it would have to
   be unauthenticated, which is precisely what `gateway-auth` set out to eliminate.
2. **Bind the three keymaps** in `src/sase/default_config.yml` (`B`/`I`/`P` or digits, per
   the plan's own analysis), and update `AppKeymaps`, `_BINDING_META`, the help modal, and
   the palette metadata together.
3. **Implement `builtin@tailnet` discovery** — shell out to `tailscale status --json`,
   bounded and timeout-guarded, mapping peers to `DiscoveryCandidate`s. This is already on
   the child-epic plan described in `sase-xe` note #7 ("real tailnet discovery … currently a
   stub").
4. **Write the runbook.** A `docs/remote_dispatch.md` covering §4.2 end to end, plus a
   `machine` row in `docs/cli.md`. This is the single largest usability gap after item 1.
5. **Ship or document the `sase_gateway` binary.** Today the target must build it from a
   `sase-core` checkout; the wheel ships only `sase_federation_worker`. Either add it to the
   distribution or state the build requirement in the runbook.
6. **Add the local identity row to `sase machine list`**, per the plan — it is the obvious
   place to read your own `installation_id` when setting up the other side.

Items 1, 2, and 4 together are what stands between "the epic is closed" and "the user can
use the feature." Items 3, 5, and 6 are polish that the child epic
(`sase_plan_remote_dispatch_acceptance_hardening`, stashed in the land agent's artifacts per
`sase-xe` notes #7-#8) already partly covers.

---

## Appendix: what *is* fully built

For the record, everything below was verified present and wired — the epic's substance is
real, and only the enrollment ceremony is missing:

- **Fleet gateway API v1** — 15 routes under `/api/fleet/v1`, bearer-scoped, protocol-negotiated,
  rate-limited on enrollment, with a generated contract snapshot
  (`crates/sase_gateway/contracts/api_fleet_v1/fleet_api_v1.json`).
- **Identity, journal, and fencing** — installation identity with quarantine-on-mismatch;
  durable mutation/attention/launch journals (`fleet_mutations.rs`, `fleet_attention.rs`,
  `fleet_launch.rs`) with replay decisions in `sase_core`.
- **Local federation worker** — a second binary in the gateway crate
  (`sase_federation_worker`), shipped as a console script by the `sase-core-rs` wheel,
  supervised on demand over a unix socket (`src/sase/dispatch/federation/_supervisor.py`).
- **Python dispatch layer** — pluggy `sase_dispatch` hooks with builtin `https`/`tailnet`
  providers, layer-aware config parsing, 0600 credential store, follow store, launch and
  mutation intents, machine catalog, attention notices.
- **`sase machine` CLI** — `add`, `agent`, `attention`, `discover`, `list`, `remove`,
  `rename`, `repair`, `status`, all with `--json`.
- **ACE Focus/Fleet** — mode switch over one list machinery, follow toggle, remote
  lifecycle/content/attention actions, per-host diagnostics, partial-count handling.
- **`%dispatch:<alias>`** — in both directive vocabularies with exact-set parity tests, and
  no longer flag-gated on either side of the Rust boundary.
- **Doctor** — `dispatch.config`, `dispatch.credentials` (offline) and `dispatch.live`
  (`deep=True`).
