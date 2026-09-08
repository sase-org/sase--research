# What Remains Before `sase init` Can Initialize Remote Dispatch For The Tailnet

**Research question:** epic `sase-xe` shipped remote dispatch, but `sase init` does not
discover the other machines on the `tail297af1.ts.net` tailnet that are running compatible
versions of sase. What work remains, and what is the recommended way to close it?

**Scope and method:** `sase` workspace at master `2edf986b6`; linked `sase-core` at
`1396607` (v0.32.43). I read `src/sase/dispatch/` end to end, the `sase init` registry and
its machine planner, `src/sase/main/parser_machine.py` / `machine_handler.py`, the dispatch
schema and defaults, the accepted plan `plan:202609/remote_dispatch_fleet.md`, the epic and
`sase-xe.8` beads, and `crates/sase_gateway/src/{routes,fleet_auth,main}.rs` plus
`crates/sase_core_py/`. Everything asserted about live state was measured on athena, apollo
and mac this session — commands and outputs are in §7.

---

## 1. Executive summary

`sase init` cannot discover the tailnet because **five independent things are missing, and
each one alone is sufficient to produce the silence you observe.** Ordered by how far they
are from the user:

| # | Gap | Where | Blocks |
| - | --- | ----- | ------ |
| 1 | `sase machine init` **does not exist**. `sase init machine` is an orphan alias whose help points at a command that was never written. | `parser_machine.py`, `parser_init.py:183` | Command shape |
| 2 | The tailnet discovery provider is a **stub that returns `()`** while advertising `supports_discovery: True`. | `dispatch/providers.py:73-82` | Discovery |
| 3 | Defaults ship tailnet **off in two places**, so the init planner short-circuits before discovery is even attempted. | `default_config.yml:35,39` | Discovery |
| 4 | There is **no compatibility signal to filter on**. The gateway's only unauthenticated endpoint reports its own crate version but nothing about the fleet protocol. | `routes.rs:780-790` | "compatible versions of sase" |
| 5 | The **enrollment bundle cannot be minted**. `issue_bootstrap` has no CLI, no route, and no binding, so even a perfect candidate list dead-ends at the bundle prompt. | `fleet_auth.rs:89` | Enrollment |

And beneath all five: **there is currently nothing on your tailnet to discover.** No
machine is serving the fleet API, the `sase_gateway` binary is not distributed to any of
the three machines, no `tailscale serve` config exists anywhere, and the tailnet does not
have HTTPS certificates enabled — which the client hard-requires (`fleet_client.py:100`).

The good news is that gaps 1-3 are small and self-contained, gap 4 is a two-field wire
addition, and gap 5 has an unusually clean fix available: **`sase_core_py` already depends
on the `sase_gateway` crate and already ships one of its binaries as a console script via a
PyO3 shim.** The same three-line pattern gives you both `sase machine bootstrap` and a
distributed `sase_gateway` without inventing any new distribution mechanism.

The recommendation in §6 is a four-phase sequence. Phase 0 (config defaults) and Phase 1
(the `sase machine init` command + real tailnet discovery) are what make `sase init`
*discover*; Phase 2 (bootstrap minting + gateway distribution) is what makes it *enroll*.
Discovery without Phase 2 produces a candidate list you cannot act on, so the phases should
land together even though they are separable.

---

## 2. What actually happens today

Measured, not inferred:

```
$ sase init --check --json
  ...
  { "name": "machine", "label": "Machine",
    "summary": "no remote machine discovery providers are configured",
    "actions": [], "action_count": 0, "requires_tty": false }
```

`sase init` never offers machine enrollment. It emits a one-line summary with zero actions,
so the onboarding coordinator has nothing to apply. The path there is short:

1. `plan_init_machine` (`init_machine_handler.py:31-40`) checks
   `config.discovery_enabled_provider_refs`. `default_config.yml:39` ships
   `discovery.enabled_providers: []` and your user layer declares no `dispatch:` key, so
   the tuple is empty and the planner returns the "no providers configured" summary with
   `actions=()`.
2. Even if you set `enabled_providers: [builtin@tailnet]`, `discover_dispatch_candidates`
   (`providers.py:191`) additionally requires `providers.builtin@tailnet.enabled`, which
   `default_config.yml:35` ships as `false`. The disabled provider is skipped **silently —
   no diagnostic is emitted**, so `sase machine discover -p builtin@tailnet` prints an
   empty candidate list with no explanation of why.
3. Even with *both* switches on, discovery still returns nothing, because the built-in
   hookimpl is a stub. Proved directly:

```python
>>> cfg = load_dispatch_config({'dispatch': {
...     'providers': {'builtin@tailnet': {'enabled': True}},
...     'discovery': {'enabled_providers': ['builtin@tailnet']}}})
>>> cfg.provider_enabled('builtin@tailnet'), cfg.discovery_enabled_provider_refs
(True, ('builtin@tailnet',))
>>> discover_dispatch_candidates(config=cfg)
()                                    # <-- the stub
>>> [(s.ref, s.supports_discovery) for s in collect_dispatch_providers().specs]
[('builtin@https', False), ('builtin@tailnet', True)]   # <-- advertised anyway
```

The last line is the sharpest form of the bug: the provider inventory tells every consumer
— `sase machine discover`, the init planner, any future UI — that `builtin@tailnet`
supports discovery, and the implementation behind that promise is:

```python
# src/sase/dispatch/providers.py:73-82
def dispatch_discover(self, provider_ref, config, timeout_seconds):
    del config, timeout_seconds
    if provider_ref == "builtin@tailnet":
        return ()
    return ()
```

There is no `tailscale` reference anywhere in `src/` (`grep -rn tailscale src/` matches only
the mobile-gateway bind help text and a hostname helper).

---

## 3. The command shape is wrong, and this is worth fixing first

Your framing — that `sase init` should delegate to a new `sase machine init` — matches the
established convention exactly, and `machine` is the one init spec that violates it.

Every other `sase init` subcommand is a documented compatibility alias for a canonical
command that owns the logic:

| `sase init …` | Canonical command | Help text |
| --- | --- | --- |
| `init config` | `sase config init` | "Alias for `sase config init`" |
| `init memory` | `sase memory init` | "Alias for `sase memory init`" |
| `init repo` | `sase repo init` | "Alias for `sase repo init`" |
| `init skills` | `sase skill init` | "Alias for `sase skill init`" |
| `init machine` | **— none —** | "Alias for `sase machine discover` plus optional enrollment" |

`parser_machine.py` registers `add, agent, attention, discover, list, remove, rename,
repair, status`. There is no `init`. So `sase init machine`'s own help advertises an alias
relationship to a command that cannot do what the alias does: `sase machine discover`
enrolls nothing and takes no interactive input, while `sase init machine` discovers *and*
enrolls. The behavior lives in `init_machine_handler.py` and is reachable from exactly one
place — the init tree — which is the opposite of how the other four work.

This matters beyond tidiness. Enrollment is a setup ceremony you will want to re-run for
one machine at a time, long after first-run onboarding: a new laptop joins the tailnet, a
target is reinstalled and its pin changes, you want to re-scan after enabling Tailscale
Serve. Today the only entry point is `sase init machine`, which reads as "onboarding," and
which under `sase init` (no subcommand) is bundled with config/memory/repo/skills work you
may not want to run. The plan's own CLI section (`plan:…:428-452`) describes `sase machine`
as the home for explicit machine operations and `sase init` as the surface that *offers*
them — so making `sase machine init` canonical is a return to the specified design, not a
new idea.

---

## 4. "Compatible versions of sase running" — what is actually knowable

This is the part of your request with genuine design content, so it is worth being precise
about what a tailnet peer can and cannot tell you.

**`tailscale status --json` gives you peers, not capabilities.** Your tailnet returns:

| HostName | DNSName | OS | Online |
| --- | --- | --- | --- |
| athena (self) | `athena.tail297af1.ts.net.` | linux | true |
| apollo | `apollo.tail297af1.ts.net.` | linux | true |
| Kelly's MacBook Pro | `kellys-macbook-pro.tail297af1.ts.net.` | macOS | true |
| Pixel 10 Pro XL | `pixel-10-pro-xl.tail297af1.ts.net.` | android | false |

Nothing in that payload says whether a peer runs sase, let alone which version. Tailscale
does not propagate a node's `serve` configuration to its peers. **Discovery therefore has
to be a two-stage operation: enumerate from `tailscale status --json`, then probe.** Any
design that tries to answer "compatible version" from the status JSON alone is impossible.

**The probe target already exists and is unauthenticated.** `GET /api/v1/health`
(`routes.rs:780-790`) needs no bearer token and returns:

```json
{ "schema_version": 1, "status": "ok", "service": "sase_gateway",
  "version": "0.32.43", "build": {"package_version": "...", "git_sha": null},
  "bind": {"address": "127.0.0.1:7629", "is_loopback": true}, "push": {...} }
```

`service == "sase_gateway"` is a clean positive identification, and `version` /
`build.git_sha` are exactly what you want to display next to a candidate. This is the right
probe: it is already public by design, it costs one bounded GET, and it needs no
credentials — which matters, because discovery runs *before* enrollment and therefore has
none.

**What health does not tell you is the fleet protocol version**, which is the thing
"compatible" actually means here. `FLEET_PROTOCOL_VERSION` is negotiated per-request via the
`X-SASE-Fleet-Protocol-Versions` header, and the health payload does not mention it. Two
ways to close that:

- **(a) Extend the health wire — recommended.** Add a `fleet` block to
  `HealthResponseWire`: `{"protocol_versions": [1], "api_base": "/api/fleet/v1",
  "enrollment_open": true}`. It is additive, it lives on an endpoint that is already
  unauthenticated, and it regenerates into the existing contract snapshot. Cost is one wire
  struct field, one contract regeneration, and a `sase-core-rs` floor bump in
  `pyproject.toml`.
- **(b) Zero-core-change fallback.** In `fleet_hello`, `fleet_protocol_version_from_headers`
  runs *before* `fleet_authenticate` (`routes.rs:835-845`). So an unauthenticated
  `GET /api/fleet/v1/hello` with `X-SASE-Fleet-Protocol-Versions: 1` returns **401** from a
  compatible gateway and a protocol/invalid-request error from an incompatible one. That is
  a usable oracle today, but it depends on handler ordering that no test pins, so it is a
  stopgap, not the design.

**Do not let discovery populate `installation_pin`.** `DiscoveryCandidate` has the field
(`models.py:288`), and it is tempting to fill it from a probe. Resist: `add_machine` takes
the pin from the enrollment *bundle* and then verifies the enrolled identity against it
(`machine_service.py:97-142`). A pin scraped off the network is trust-on-first-use and
would quietly convert a verified pin into an unverified one. Leave it empty and put the
version string in `detail` instead. For the same reason I would not add `installation_id`
to the unauthenticated health payload.

**Endpoint construction.** From a peer's `DNSName`, strip the trailing dot and prefix
`https://` → `https://apollo.tail297af1.ts.net`. Port 443 is implied because
`tailscale serve` fronts loopback on 443; make it overridable through provider config
(`dispatch.providers.builtin@tailnet.port`) rather than hard-coding, since a target using
its own TLS termination may differ. The client hard-rejects any non-`https` scheme
(`fleet_client.py:100`), so there is no http fallback to design.

---

## 5. The environment is not ready either, and this will bite before the code does

Three findings from probing the actual machines, all of which block the feature independent
of any code change:

**5.1 The `sase_gateway` binary is not distributed anywhere.** `crates/sase_gateway/Cargo.toml`
declares two `[[bin]]` targets, but `crates/sase_core_py/pyproject.toml:37` ships only:

```toml
[project.scripts]
sase_federation_worker = "sase_core_rs.federation_worker:main"
```

Confirmed on all three machines: `sase_federation_worker` is present, `sase_gateway` is
absent. `_resolve_gateway_command` (`integrations/mobile_gateway.py:286-296`) falls back to
`../sase-core/target/{debug,release}/sase_gateway`, so `sase mobile gateway start` works
only on a machine with a sase-core checkout and a cargo build. apollo and mac have `sase`
installed (both at `0.17.1+228.g0b292e49f`, same as athena) but no gateway to run.

**5.2 No target is serving, and there is no supervision story.** `~/.sase/fleet_gateway/`
does not exist on athena and `~/.sase/installation_identity.json` does not exist on apollo —
i.e. no gateway has ever run on either. `tailscale serve status` reports "No serve config"
on athena and apollo. Separately, `sase mobile gateway` has exactly one subcommand,
`start`, which runs in the foreground: there is no `stop`, no `status`, and no service unit.
A fleet target has to stay up across reboots, so systemd (linux) / launchd (macOS) units are
a real deliverable, not an afterthought.

**5.3 The tailnet does not have HTTPS certificates enabled.** `tailscale status --json`
reports `CertDomains: null` with `MagicDNSEnabled: true`. Without HTTPS certs,
`tailscale serve` cannot terminate TLS for `*.tail297af1.ts.net`, and every endpoint the
fleet client will accept must be `https://`. **This is a one-click change in the Tailscale
admin console (DNS → HTTPS Certificates) and it is a hard prerequisite for everything
else.** Worth doing before any code lands, so the first end-to-end test is not debugging TLS.

Note that 5.1-5.3 also mean discovery will legitimately find **zero** candidates on your
tailnet until a target is stood up — so "discovery returns nothing" will remain the observed
behavior after the discovery fix until Phase 2 and Phase 3 are both done. Plan the
verification accordingly (§6.5).

---

## 6. Recommended solution

### 6.0 Phase 0 — flip the defaults to match the accepted plan (tiny)

The plan states the tailnet provider is "enabled by default for explicit discovery"
(`plan:…:210-212`) and shows `discovery: - use: builtin@tailnet` in the config example
(`plan:…:390`). The shipped defaults do the opposite. Change `src/sase/default_config.yml`:

```yaml
dispatch:
  providers:
    builtin@https:
      enabled: true
    builtin@tailnet:
      enabled: true          # was false
  discovery:
    enabled_providers: [builtin@tailnet]   # was []
```

This is safe under the epic's own decision 5 ("discovery never runs at launch, completion,
or ordinary refresh — only during explicit setup"), so enabling the provider adds no
background work and no network traffic; it only means that when you *ask*, the provider is
consulted. Absent `tailscale`, the provider reports unavailable and everything else is
unaffected.

While here, fix the silent skip at `providers.py:191`: when a selected provider is disabled,
append a `MachineDiagnostic(code="dispatch_provider_disabled", severity="warning")` instead
of `continue`. Surface it from `sase machine discover` and from the init planner's
`warnings`. Today an explicitly requested `-p builtin@tailnet` produces indistinguishable
silence whether the provider is off, unavailable, or genuinely found nothing.

### 6.1 Phase 1 — `sase machine init`, with real tailnet discovery

**Command.** Register `init` in `parser_machine.py` between `discover` and `list` (argparse
lists in registration order; the CLI rules require alphabetical help). It does not disturb
the bare-group `list` delegation. Options, all optional per the CLI rules, all with short
aliases:

```
sase machine init [-j|--json] [-n|--dry-run] [-p|--provider PROVIDER]
                  [-t|--timeout SECONDS] [-y|--yes]
```

Move the planner/runner pair out of `main/init_machine_handler.py` into the dispatch layer
(`src/sase/dispatch/cli_init.py` or similar, per the plan's "`machine_handler.py` shim
delegates to `src/sase/dispatch/cli*.py`" note), and have **both** `sase machine init` and
`sase init machine` call it — exactly the `sase memory init` / `sase init memory` split.
Retarget `parser_init.py:183`'s help to "Alias for `sase machine init`", and update
`parser_machine.py`'s group description. Keep the `_init_input_func` / `_init_stdin`
injection convention that `init_machine_handler.py` already uses, so the interactive path
stays testable.

**Discovery provider.** Replace the stub in `BuiltinDispatchProviders.dispatch_discover`
with a real implementation in a new `src/sase/dispatch/providers_tailnet.py`. Keep the
hookimpl in `providers.py` a thin delegation so the positional-argument compatibility
comment there stays accurate. Algorithm:

1. `shutil.which("tailscale")` → absent means *provider unavailable*, not an error: return
   `()` plus a diagnostic. Never raise; a missing binary must not fail `sase init`.
2. `subprocess.run(["tailscale", "status", "--json"], timeout=min(timeout_seconds, 5),
   capture_output=True)`. Non-zero exit, timeout, or unparseable JSON → diagnostic, return
   `()`. Parse defensively with fixtures for missing and extra fields, per the plan's
   `dispatch-plugins` phase spec (`plan:…:766-768`).
3. Enumerate `Peer` (skip `Self`). Filter: skip `Online: false` and skip
   `OS in {"android", "ios"}` — both overridable through provider config
   (`include_offline`, `include_os`). Treat Tailscale online status as a hint, never as
   authorization.
4. Build `https://<DNSName without trailing dot>` (+ optional configured port).
5. Probe each candidate concurrently — `ThreadPoolExecutor(max_workers=8)`, per-peer
   deadline from `timeout_seconds`, and a total wall-clock cap so a hung peer cannot stall
   `sase init`. `GET {endpoint}/api/v1/health`, response body capped like
   `fleet_client._MAX_RESPONSE_BYTES`.
6. Accept iff `service == "sase_gateway"` **and** the reported fleet protocol versions
   intersect `{FLEET_PROTOCOL_VERSION}` (via §4(a); §4(b) as the interim oracle).
7. Emit `DiscoveryCandidate(provider_ref="builtin@tailnet", endpoint=…,
   display_name=HostName, machine_selector=HostName, installation_pin="",
   detail=f"sase_gateway {version} · fleet protocol {v}")`.

Peers that answer but are incompatible, and peers that do not answer at all, should surface
as **diagnostics with reasons** rather than being dropped silently — "apollo: reachable, no
sase gateway" is the single most useful line `sase init` can print while you are setting
this up.

**Tests.** `tests/dispatch/test_dispatch.py` already has the provider-hook harness. Add:
tailnet JSON fixtures (typical, missing fields, extra fields, empty `Peer`, offline peers);
`tailscale` binary absent; `tailscale` exiting non-zero; probe timeout; probe returning a
non-sase service; probe returning an incompatible protocol; and a lazy-loading assertion
that importing `sase` never spawns a subprocess. Add `tests/main/test_parser_machine.py`
coverage for the new subcommand's help ordering and the delegation notice.

### 6.2 Phase 2 — make enrollment completable (`sase machine bootstrap`)

This is the hard blocker and it has a much cleaner fix than it first appears.
`crates/sase_core_py/Cargo.toml:37` already declares `sase_gateway = { path =
"../sase_gateway" }`, and `lib.rs:12261-12269` already exposes a gateway-crate entry point
to Python:

```rust
#[pyfunction]
#[pyo3(name = "federation_worker_main")]
fn py_federation_worker_main(py: Python<'_>, args: Vec<String>) -> PyResult<()> {
    py.allow_threads(|| sase_gateway::run_federation_worker_cli(args))
        .map_err(PyRuntimeError::new_err)
}
```

…surfaced through a four-line Python shim and one `[project.scripts]` line. **Use that same
pattern twice:**

1. **`fleet_issue_bootstrap(sase_home, requested_scopes, ttl_seconds) -> dict`** — a new
   PyO3 function constructing `FleetCredentialStore` and calling `issue_bootstrap`
   (`fleet_auth.rs:89`). It is a pure local-file operation; the gateway need not be running.
   Python calls it through the existing `require_rust_binding(...)` convention already used
   by `validate_connection_plan` (`dispatch/config.py:75`). Then add
   `sase machine bootstrap [-j|--json] [-e|--expires SECONDS] [-s|--scope SCOPE]` printing
   the bundle as JSON (and offering base64/YAML, the three forms
   `_parse_enrollment_bundle` already accepts). Secret minting stays in Rust, satisfying the
   `rust_core_backend_boundary` memory.
2. **`sase_gateway = "sase_core_rs.gateway:main"`** — mirror the federation-worker shim over
   `sase_gateway::serve` (public in the crate's lib; `main.rs` is already a thin wrapper over
   it) and add the console script. This distributes the gateway to every machine that has
   `sase` installed and removes the "build it from a sase-core checkout" requirement (§5.1)
   for apollo and mac in one change.

**Do not add an HTTP route for bootstrap issuance.** It would have to be unauthenticated,
which is precisely what the `gateway-auth` phase set out to eliminate.

**Optional accelerator, and a good fit for your setup:** `sase machine init --via-ssh`.
Because every tailnet machine already has chezmoi-managed SSH access to every other
(`sase/memory/tailnet.md`; I confirmed `ssh apollo` and `ssh mac` work non-interactively
from athena this session), `sase machine init` can run
`ssh <peer> sase machine bootstrap --json`, pipe the result straight into `add_machine`, and
complete enrollment with no copy-paste at all. The security posture is unchanged — the
secret is still minted on the target, still single-use, still 600-second TTL, and it never
touches the viewer's disk. Make it opt-in and off by default so the manual-paste path
remains the contract; SSH availability is an accident of your environment, not a property of
the feature.

### 6.3 Phase 3 — stand up a real target

Independent of the code, and testable in parallel:

1. Enable **HTTPS Certificates** in the Tailscale admin console (§5.3). Verify with
   `tailscale status --json | jq .CertDomains` becoming non-null.
2. On apollo: install the sase version carrying the Phase 2 change, then
   `sase mobile gateway start` (loopback `127.0.0.1:7629`, never `--allow-non-loopback`).
3. `tailscale serve --bg http://127.0.0.1:7629` → `https://apollo.tail297af1.ts.net`.
   Never Funnel — `docs/mobile_gateway.md:227-229` is explicit about this.
4. Add a systemd unit for the gateway (and a launchd plist if mac becomes a target).
   Consider adding `sase mobile gateway status|stop` while you are here; `start` alone is
   not a service story.
5. `sase machine bootstrap --json` on apollo, then from athena: `sase machine init` (or
   `sase machine add apollo https://apollo.tail297af1.ts.net -B bundle.json`).
6. `sase machine status apollo`, `sase doctor --deep`, then open ACE — the Focus/Fleet strip
   is gated on `dispatch.machines` being non-empty (`federation/_hosts.py:87`), so it
   appears at this point and not before.

### 6.4 Phase 4 — the surrounding polish this exposes

Small items that the plan called for and that the epic did not land. None block discovery;
all of them will be missed within an hour of the feature working:

- `sase machine list` should print the **local identity row first** — the plan is explicit
  ("one machine vocabulary, not two", `plan:…:424-426`), and it is the natural place to read
  your own `installation_id` when configuring the other side. Today the command prints only
  "No remote machines are configured."
- The three Focus/Fleet keybindings ship as `"unbound"` in `default_config.yml`, so the strip
  is mouse-and-palette-only after enrollment.
- There is no `docs/remote_dispatch.md` and no `machine` row in `docs/cli.md`. Given how
  many prerequisites §5 turned up, the runbook is arguably the highest-value non-code
  deliverable in this whole list.

### 6.5 Sequencing and the honest expectation

Phases 0, 1, 2 are code and can land in one epic; Phase 3 is operational and gates
acceptance. **Do not close Phase 1 on "discovery returns `()` on athena"** — that is the
correct result until Phase 3 stands up a target, and it is indistinguishable from the bug
you are fixing. Land Phase 1 against fixture-driven tests plus one live end-to-end run after
Phase 3, and make the diagnostics good enough that "no candidates" always comes with a
reason attached.

Note also that the sase-xe landing already authored a child epic covering some of this —
"real tailnet discovery (`tailscale status --json` — currently a stub, no tailscale
reference in tree)" is named explicitly in epic note #7, and the plan draft was stashed in
the land agent's artifacts per note #8. Check for that draft before authoring a new plan;
the discovery item at minimum should be reconciled with it rather than duplicated.

---

## 7. Live evidence

All measured this session from the `sase_13` workspace on athena.

| Probe | Result |
| --- | --- |
| `sase init --check --json` | machine planner: "no remote machine discovery providers are configured", 0 actions |
| `sase machine list --json` | `"machines": []`, `"diagnostics": []` |
| `sase machine discover --json` | `"candidates": []` |
| `sase machine discover -p builtin@tailnet --json` | `"candidates": []`, no diagnostic explaining why |
| `discover_dispatch_candidates()` with tailnet fully enabled in-process | `()` — proves the stub, not the config, is the floor |
| `collect_dispatch_providers()` | `builtin@tailnet` advertises `supports_discovery=True` |
| `tailscale status --json` | 3 peers; `MagicDNSSuffix: tail297af1.ts.net`; **`CertDomains: null`** |
| `tailscale serve status` (athena, apollo) | "No serve config" on both |
| `sase version` (athena / apollo / mac) | all three `0.17.1+228.g0b292e49f`; athena and apollo `sase-core-rs 0.32.43` |
| `command -v sase_gateway` (athena / apollo / mac) | absent on all three |
| `command -v sase_federation_worker` | present on athena and apollo |
| `ls ~/.sase/installation_identity.json` | exists on athena, **absent on apollo** |
| `ls ~/.sase/fleet_gateway/` (athena) | does not exist — no gateway has ever run |
| `grep -rn tailscale src/` | no discovery-related match |
| `sase mobile gateway <x>` | only `start` is a valid subcommand |

Plan-versus-implementation deviations found (`plan:202609/remote_dispatch_fleet.md`):

| Plan says | Master does |
| --- | --- |
| :210 tailnet provider "enabled by default for explicit discovery" | `default_config.yml:35` `enabled: false`; `:39` `enabled_providers: []` |
| :766 tailnet discovery "via `tailscale status --json` parsed defensively with fixtures" | `providers.py:73-82` returns `()` |
| :424 `sase machine list` shows the local identity row first | prints only remote machines |
| :754 three hooks incl. `dispatch_connection_plan` | two hookspecs; connection-plan validation happens Rust-side instead |
| :770 providers imported only inside a bounded supervised subprocess | in-process `ep.load()` in `providers.py` |
| :447 `sase init` spec offers enrollment | spec exists but short-circuits; no canonical `sase machine init` |

---

## 8. Bottom line

`sase init` is not broken so much as **unfinished at both ends of the same operation**: the
discovery hookimpl was left as a placeholder, and the command that would own it was never
created. Fixing those two things is roughly a day of focused work and is well-specified by
the plan the epic already accepted.

But making `sase init` *useful* on your tailnet needs the enrollment ceremony too, and that
needs `sase machine bootstrap` plus a distributed `sase_gateway` — both of which follow an
existing, proven pattern in `sase_core_py` rather than requiring new machinery. Do Phase 0
today (four lines of YAML, plus the missing diagnostic), enable Tailscale HTTPS certificates
while you are thinking about it, and land Phases 1 and 2 together so that the candidate list
`sase init` finally prints is one you can act on.
