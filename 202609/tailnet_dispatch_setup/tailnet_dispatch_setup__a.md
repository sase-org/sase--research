# Tailnet Remote-Dispatch Initialization: What Remains After `sase-xe`

**Researcher:** A  
**Date:** 2026-09-08  
**Question:** What work remains for bare `sase init` to discover compatible SASE
machines on Bryan's Tailnet and initialize usable remote-dispatch configuration?

## Executive conclusion

The remote-dispatch initialization path is present in name but not operational. The
failure is a chain, not one missing call:

1. There is no canonical `sase machine init` command. The shipped direction is reversed:
   `sase init machine` directly owns a small discovery/enrollment loop.
2. Bare `sase init` skips that loop under the default configuration. Its machine planner
   returns zero actions when no discovery providers are configured, and the coordinator
   only runs plans with actions. The live result on Athena is therefore
   `status: current` with the summary “no remote machine discovery providers are
   configured.”
3. The accepted epic design says Tailnet discovery is the default, but the shipped
   defaults disable `builtin@tailnet` and set `discovery.enabled_providers: []`.
4. Even when selected, the built-in Tailnet hook is a literal stub returning `()`; no
   code invokes `tailscale status --json`.
5. Discovery alone would still not yield a usable target today. Apollo and the Mac have
   compatible SASE/core installations, but none of Athena, Apollo, or the Mac can resolve
   a `sase_gateway` executable. Athena and Apollo have empty Tailscale Serve
   configurations, and the peer HTTPS health URLs refuse connections.
6. Even after manually building and exposing a gateway, the only enrollment-bundle
   issuer is the Rust-only `FleetCredentialStore::issue_bootstrap` API. There is no SASE
   CLI, gateway CLI mode, or PyO3 binding that an operator can use to mint the required
   short-lived secret.

Consequently, `sase init` cannot currently write `dispatch.machines`: the only write path
is after a successful gateway enrollment, and every path needed to reach that handshake
is missing or disabled.

The recommended solution is a focused child epic spanning `sase-core` and `sase`:

- make `sase machine init` the canonical, idempotent workflow and have bare `sase init`
  plus `sase init machine` call the same planner/service;
- ship a runnable gateway and a local-only bootstrap command from normal installations;
- implement bounded Tailnet enumeration plus SASE gateway/protocol probing, with Tailnet
  discovery enabled by default only for explicit setup;
- enroll selected, compatible gateways through the existing identity-pinned handshake;
- prove the flow on Athena → Apollo and Athena → Mac.

This should not be treated as a one-file discovery fix. Tailnet enumeration can be done
entirely in Python, but target bootstrap, gateway distribution, and the compatibility
contract cross the Rust-core boundary.

## Sources and scope

I inspected:

- epic bead `sase-xe`, especially phases `.7`, `.8`, `.15`, and landing notes 7–11;
- accepted plan `plan:202609/remote_dispatch_fleet.md` and phase plan
  `plan:202609/machine_cli_enrollment_1.md` through audited artifact reads;
- prior context `research:202609/remote_machine_management_enablement.md` through an
  audited artifact read;
- current `sase` workspace HEAD `2edf986b6` and linked `sase-core` HEAD `1396607`
  (`v0.32.43`);
- live Tailnet, installed-package, gateway-resolution, Serve, and HTTPS-health state on
  Athena, Apollo, and the Mac.

The installed `sase` executable currently reports host revision `0b292e49f`, one commit
behind this workspace. A targeted diff confirms no relevant dispatch, machine-init,
default-config, or test files changed between those revisions, so the live observations
and workspace source describe the same implementation.

I did not inspect the other researcher’s report or transcript.

## The exact failure chain

### 1. The CLI ownership is backwards

`src/sase/main/parser_machine.py:10-23` registers the machine group. Its sorted public
children are `add`, `agent`, `attention`, `discover`, `list`, `remove`, `rename`,
`repair`, and `status`; there is no `init` child (`parser_machine.py:267-396`). Live
`sase machine --help` confirms the same surface.

Instead, `src/sase/main/parser_init.py:182-196` adds `sase init machine`, and
`src/sase/main/init_machine_handler.py` contains the implementation. That makes the
generic onboarding coordinator the owner of machine-specific policy and prevents the
more natural contract requested here: a standalone `sase machine init` that bare
`sase init` wraps.

The accepted plan did ask for an init-registry spec but did not explicitly require a
`machine init` child. The requested command direction is nevertheless a better boundary:
the machine subsystem should own discovery and enrollment; generic onboarding should
only schedule it.

### 2. Bare `sase init` never schedules machine initialization by default

The decisive code is `src/sase/main/init_machine_handler.py:18-52`:

- any configured machine makes the plan immediately “current”;
- no `discovery_enabled_provider_refs` also makes it “current”;
- only a configured discovery provider produces the `InitAction` that allows apply.

`src/sase/main/_init_onboarding_apply.py:74-109` then skips every plan for which
`plan.has_changes` is false. The default config at `src/sase/default_config.yml:30-41`
sets:

```yaml
dispatch:
  providers:
    builtin@https:
      enabled: true
    builtin@tailnet:
      enabled: false
  machines: {}
  discovery:
    enabled_providers: []
```

The live `sase init --check --json` result on Athena is therefore internally consistent
but operationally misleading:

```json
{
  "name": "machine",
  "summary": "no remote machine discovery providers are configured",
  "actions": [],
  "has_changes": false
}
```

The aggregate status is `current`, so interactive bare init does not get an opportunity
to discover anything.

There is a second reconciliation defect: once *one* machine exists, the early return at
lines 22–30 suppresses all later discovery. Bare init can never notice a newly prepared
Tailnet peer. An explicit `sase machine init` should always support rescan; bare init may
remain conservative after the first successful onboarding.

### 3. The defaults contradict a settled epic decision

The accepted epic plan states that the built-in Tailnet provider is enabled by default
for explicit discovery and that discovery runs only during `sase init` or
`sase machine discover`. It also specifically calls for defensive parsing of
`tailscale status --json`.

The shipped implementation does the opposite at rest: Tailnet is disabled and no
discovery provider is selected. These defaults do preserve the “no ordinary config-load
network traffic” invariant, but enabling an explicit-only provider would preserve that
invariant too because `load_dispatch_config()` is pure
(`src/sase/dispatch/config.py:27-77`).

This is not just a documentation discrepancy. Even
`sase machine discover -p builtin@tailnet --json` returns an empty candidate list because
`discover_dispatch_candidates()` skips explicitly requested providers when their
provider setting is disabled (`src/sase/dispatch/providers.py:171-203`).

### 4. Tailnet discovery was never implemented

`BuiltinDispatchProviders.dispatch_discover()` at
`src/sase/dispatch/providers.py:72-82` deletes its config and timeout arguments and
returns `()` for `builtin@tailnet`. There is no Tailscale invocation anywhere in the
dispatch package. Tests verify fake-plugin collection and fake discovery, but there are
no Tailnet JSON fixtures and no test asserting that the built-in provider can produce a
candidate.

The surrounding provider runner is also short of the accepted hardening contract:

- `_safe_discover()` invokes plugin code in-process (`providers.py:290-311`); the timeout
  is advisory data passed to the plugin, not an enforced deadline;
- every exception becomes an indistinguishable empty tuple;
- discovery returns candidates only, so missing Tailscale, malformed JSON, provider
  timeout, incompatible SASE, and a legitimately empty Tailnet all render as the same
  “No remote machine candidates found.”

This matters to `sase init`: a broken provider currently looks like successful
initialization and returns exit code 0 (`init_machine_handler.py:81-89`).

### 5. The live Tailnet has peers, but no fleet endpoints

On 2026-09-08, `tailscale status --json` on Athena reported:

| Node | Tailnet state | OS | SASE host version | Core version |
| --- | --- | --- | --- | --- |
| Athena | self, online | Linux | `0.17.1+228.g0b292e49f` | `0.32.43` |
| Apollo | online, active | Linux | `0.17.1+228.g0b292e49f` | `0.32.43` |
| Kelly’s MacBook Pro | online, active | macOS | `0.17.1+228.g0b292e49f` | `0.32.43` |
| Pixel 10 Pro XL | offline | Android | not probed | not applicable |

Apollo and the Mac were probed over their established SSH aliases. Their SASE and core
versions exactly match Athena’s installed versions, so package skew is not the reason
they are absent.

However:

- `resolve_gateway_command()` returned `()` on all three computers;
- `tailscale serve status --json` returned `{}` on Athena and Apollo;
- the Mac’s Tailscale CLI was not on the noninteractive SSH `PATH`;
- HTTPS requests to both
  `https://apollo.tail297af1.ts.net/api/v1/health` and
  `https://kellys-macbook-pro.tail297af1.ts.net/api/v1/health` failed to connect on port
  443.

This matches the packaging. `sase-core`’s
`crates/sase_core_py/pyproject.toml:37-39` installs only
`sase_federation_worker`; it does not install `sase_gateway`. The Python resolver in
`src/sase/integrations/mobile_gateway.py:281-299` succeeds only when a standalone binary
is on `PATH` or happens to exist in a sibling development checkout. A normal SASE/core
installation is therefore insufficient to become a remote-dispatch target.

Tailscale itself can enumerate nodes, but it cannot infer that a Python package is
installed on them. Its official CLI documentation describes `tailscale status --json`
as detailed peer/user metadata suitable for automation, while warning that the JSON
format can change. The live peer records contain DNS name, OS, online/active state, IPs,
and user ID—not arbitrary application-installation metadata. See the
[Tailscale CLI status reference](https://tailscale.com/docs/reference/tailscale-cli#status).

Therefore “compatible SASE running” should mean “a reachable SASE fleet gateway whose
fleet protocol intersects the controller’s,” not merely “the `sase` console script is
installed.”

### 6. Compatibility is not currently discoverable

The gateway’s unauthenticated `/api/v1/health` response already includes
`service: sase_gateway`, the gateway crate version, and build metadata
(`sase-core/crates/sase_gateway/src/routes.rs:780-789`). This is enough to distinguish a
SASE gateway from an unrelated HTTPS server, but it does not publish supported fleet
protocol versions or capabilities.

The authenticated fleet hello does negotiate and return protocol/capabilities, but it
cannot be called until enrollment has produced a credential. Using package semver as a
pre-enrollment compatibility rule would duplicate and weaken the existing protocol
contract. The discovery health payload should instead expose a minimal non-secret field
such as:

```json
{
  "service": "sase_gateway",
  "version": "0.32.43",
  "fleet": {"supported_protocol_versions": [1]}
}
```

This is a compatibility hint, not identity or authorization. The installation pin must
continue to come from the target-authorized bootstrap and be verified during enrollment.

### 7. There is no operator path to issue the enrollment bundle

The existing viewer-side path is sound once a valid bundle exists:
`MachineService.add_machine()` validates the provider and bundle, contacts
`/api/fleet/v1/enroll`, verifies the authoritative installation ID against the target
pin, stores the bearer credential, and only then writes the machine record
(`src/sase/dispatch/machine_service.py:81-154`).

But the bundle can only be minted by
`sase-core/crates/sase_gateway/src/fleet_auth.rs:89-153`. The Rust operation is local,
single-use, identity-pinned, and defaults to a ten-minute TTL. It has no production call
site. The standalone gateway CLI has no bootstrap mode, the Python binding exports no
bootstrap function, and the HTTP router correctly exposes no unauthenticated bootstrap
route.

The current init loop also reads the bundle with ordinary `input()`
(`src/sase/main/init_machine_handler.py:102-110`), unlike `sase machine add`, which uses
`getpass`. That echoes a live enrollment secret in the terminal and should be fixed when
the flow is moved.

### 8. The intended follow-up was not durably launched

Epic `sase-xe` landing note 7 explicitly lists real Tailnet discovery as remaining work
and says the implementation is currently a stub. Notes 7–8 describe a child acceptance
and hardening plan that was moved to the land agent’s artifact directory so the landing
stitch could stay clean. The epic was then auto-closed by stitch creation in note 11.

Current bead searches for “remote dispatch acceptance,” “machine init,” and “discovery
provider” find no child bead. The only Tailnet-discovery hit is the closed parent epic.
Thus there is no discoverable active owner for this gap, even though the parent’s own
landing note records it as unfinished.

## What safe Tailnet discovery can and cannot do

The accepted trust model should remain unchanged:

- Tailnet membership, DNS names, online flags, and gateway health are discovery hints.
- A discovered device is never implicitly trusted.
- Target authorization is a local-only bootstrap action.
- Enrollment pins the target installation and returns a scoped controller credential.
- Dispatch always uses the standard fleet HTTPS protocol; provider identity is routing
  metadata.

The correct endpoint shape is a node-specific MagicDNS URL behind Tailscale Serve. The
[Serve documentation](https://tailscale.com/docs/features/tailscale-serve) confirms that
Serve proxies a loopback service to an HTTPS URL within the tailnet and that normal
tailnet access controls still apply. The
[Serve CLI reference](https://tailscale.com/docs/reference/tailscale-cli/serve) also
documents persistent background mode and JSON status.

Tailscale Services are not a good default substitute. They are designed to place one
stable service identity in front of one or more back-end hosts and require tag-based
service hosts plus approval. Remote dispatch deliberately targets one pinned SASE
installation; a load-balanced service name would obscure that identity. See
[Tailscale Services](https://tailscale.com/docs/features/tailscale-services).

One unavoidable limitation should be explicit in the UX: a viewer cannot safely turn an
arbitrary Tailnet peer into a dispatch target without an authorized action on that
target. Bare init may discover an unready peer and explain how to prepare it, but it must
not silently install a service, alter Tailscale Serve policy, or mint a secret remotely.
An optional SSH-assisted setup can come later, after explicit machine selection and
confirmation; manual target-local setup must remain the baseline.

## Recommended implementation

### Phase 1: Finish the target-side Rust/core surface

1. **Make the gateway runnable from an ordinary `sase-core-rs` installation.** Add a
   synchronous `gateway_main(args)` binding analogous to the existing federation worker
   binding (internally owning its Tokio runtime), expose a small Python module, and add a
   `sase_gateway` console-script entry point. Packaging the standalone binary is also
   viable, but the acceptance criterion is that `resolve_gateway_command()` succeeds on
   supported Linux and macOS installations without a sibling source checkout.
2. **Expose local bootstrap issuance, never an HTTP bootstrap route.** Add a narrow Rust
   binding around `FleetCredentialStore::issue_bootstrap`; wrap it as
   `sase machine bootstrap --json`. Default output should be a single pasteable bundle,
   emitted once, with restrictive file/stdout guidance and no logging. Preserve the
   ten-minute/single-use semantics.
3. **Advertise fleet compatibility in health.** Extend `/api/v1/health` with supported
   fleet protocol versions. Do not expose credentials or treat the response as an
   installation pin.
4. **Give the gateway a machine-facing lifecycle name.** Add
   `sase machine gateway start/status` (the existing `sase mobile gateway start` can be a
   compatibility alias) because the process serves both mobile and fleet APIs.

Persistent OS-service installation is desirable but can be staged. For the first usable
slice, document foreground gateway startup plus explicit
`tailscale serve --bg 7629`. A follow-up can install systemd-user and launchd units with
separate consent. Tailscale Serve itself persists background configurations across
restarts, but the proxied gateway process also needs persistence.

### Phase 2: Make `sase machine init` canonical and implement Tailnet discovery

1. **Add `sase machine init`.** Move the plan/apply logic into a machine-owned service
   module. `sase init machine` remains a compatibility wrapper, and the machine
   `InitCommandSpec` used by bare `sase init` calls the same functions rather than
   spawning another CLI process.
2. **Restore the intended defaults.** Enable `builtin@tailnet` and put it in
   `dispatch.discovery.enabled_providers` by default. This does not create ambient
   traffic because discovery is only invoked by explicit setup commands. An explicit
   empty provider list remains the opt-out.
3. **Keep planning offline.** `--check`, `--diff`, JSON planning, ordinary config loads,
   launch completion, and ACE refresh must not execute Tailscale or probe peers. When no
   machines are configured and Tailnet discovery is available, the planner should emit
   one TTY-required setup action instead of declaring the whole installation current.
   Explicit `sase machine init` should always support rescan even after one machine has
   been enrolled.
4. **Implement a bounded provider report.** Execute
   `tailscale status --json` without a shell, with an enforced wall-clock deadline and
   output-size cap. Parse maps/lists defensively, exclude self, retain stable node/DNS
   identity, and represent offline state as a hint. Do not filter solely by OS: the
   decisive filter is gateway health and fleet protocol.
5. **Probe candidates, bounded and independently.** Derive
   `https://<DNSName-without-trailing-dot>` and probe `/api/v1/health` concurrently with
   small per-host deadlines. A candidate is enrollable only when service identity is
   `sase_gateway` and protocol intersection is non-empty. Offline, unavailable,
   malformed, unrelated, and incompatible peers should become structured diagnostics,
   not disappear.
6. **Do not swallow provider failures.** Replace the candidates-only return with a
   discovery report containing candidates plus diagnostics. Missing Tailscale should say
   so; timeout should identify the provider/peer; an empty healthy Tailnet should remain
   distinguishable from provider failure.
7. **Enroll through the existing service.** Present ready candidates and readiness
   diagnostics, allow zero or more selections, request a target-local bootstrap bundle
   with a non-echoing input seam, and call `MachineService.add_machine()`. Reuse the
   existing config/credential rollback and pin verification.

The standalone workflow should look like:

```text
$ sase machine init
Tailnet peers:
  apollo              ready       fleet protocol 1
  kellys-macbook-pro  not ready   no SASE gateway on HTTPS
  pixel-10-pro-xl     offline

Enroll apollo? [y/N]
On apollo, run: sase machine bootstrap --json
Paste enrollment bundle: <hidden>
apollo enrolled; authenticated hello succeeded.
```

Bare `sase init` should render the same machine plan immediately after config identity
initialization and invoke exactly that apply function. It should not maintain a second
workflow.

### Phase 3: Complete the operator path and prove it on the real Tailnet

1. Add a short `docs/remote_dispatch.md` runbook and rows in `docs/init.md` and
   `docs/cli.md`; the current documentation contains no `sase machine` or remote-machine
   initialization instructions.
2. Prepare Apollo first: install the packaged gateway, run it loopback-bound, explicitly
   configure node-specific Tailscale Serve, and issue a bootstrap locally.
3. From Athena, verify both `sase machine init` and bare `sase init` discover Apollo,
   label protocol 1 compatible, enroll it, write only the credential reference/pin to
   config, and make `sase machine status apollo` succeed.
4. Repeat on the Mac while it is online. Account for macOS Tailscale CLI discovery—the
   CLI was not on the SSH `PATH` during this research—even though node-specific Serve can
   proxy ports on supported macOS installations.
5. Verify `%dispatch:apollo` launches once, survives a lost reply through its operation
   key, and appears in Fleet/Focus. This proves that initialization produced config the
   already-shipped data plane can consume.

## Required regression coverage

At minimum, add tests for:

- parser/help/completion parity containing `sase machine init`;
- `sase init machine` and bare init delegating to the same implementation;
- default Tailnet setup action after `config`, while check/diff/JSON perform zero
  subprocess/network calls;
- explicit rescan when another machine is already configured;
- real `tailscale status --json` fixtures, including the map-shaped `Peer` payload seen
  on Athena, extra/missing fields, trailing-dot DNS names, self exclusion, offline peers,
  and an Android peer;
- missing binary, command failure, malformed/oversized JSON, timeout, and cancellation;
- gateway health success, unrelated HTTPS server, incompatible protocol, peer timeout,
  and partial success;
- provider diagnostics surviving to human and JSON output;
- gateway console-script packaging on Linux and macOS;
- local bootstrap single use, TTL expiry, scope restriction, no secret in argv/log/error,
  and non-echoing init input;
- end-to-end enrollment writing a machine record only after pin-verified success;
- zero configured machines still causing no background provider imports, gateway worker,
  network traffic, or ACE timers outside explicit initialization.

The existing tests are not sufficient: `tests/main/test_parser_machine.py` only checks
that `sase init machine --check` does not discover and that machine appears after config
in the registry. No test exercises `run_init_machine()` selection/enrollment, and the
dispatch tests use a fake provider rather than the built-in Tailnet path.

## Recommended solution

Create one explicit child epic for “Tailnet machine initialization,” with three ordered
phases: **(1) core gateway packaging + local bootstrap + protocol-advertising health,
(2) canonical `sase machine init` + default bounded Tailnet discovery + diagnostic
reporting, and (3) target lifecycle/docs + real Athena/Apollo/Mac acceptance.** Keep
Tailnet discovery advisory and enrollment identity-pinned; do not add an unauthenticated
bootstrap endpoint or silently modify target services.

The minimum usable milestone is reached when a normally installed Apollo can run a
target-local bootstrap command, expose its loopback gateway through explicitly approved
Tailscale Serve, and Athena’s `sase machine init` discovers and enrolls it. Bare
`sase init` should then call that same workflow. Only after that path works should the
project consider `sase-xe`’s remote-dispatch initialization promise complete.
