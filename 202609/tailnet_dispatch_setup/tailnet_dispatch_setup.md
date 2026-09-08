# Completing Tailnet Remote-Dispatch Setup

Research date: 2026-09-08. Consolidates the two independent reports and a third investigation of the current source, configuration writes, and live Tailnet.

**`sase init` cannot currently complete Tailnet remote-dispatch setup.** Its default planner skips machine setup, the Tailnet discoverer is a stub, and targets lack a normally packaged gateway and an operator command for issuing enrollment bundles. Fixing discovery alone would expose the next missing steps. The lead investigation also found that chezmoi-backed registry writes do not deploy the resulting configuration, so even successful enrollment needs an additional completion check.

The recommended unit of work is one complete setup flow: **prepare a target → discover its compatible gateway → explicitly enroll it → deploy and reload the controller's machine configuration → verify authenticated access.** Make `sase machine init` own that flow and have bare `sase init` and `sase init machine` call it.

## Evidence and provenance

The input identities were matched by dependency and their existing canonical suffixes, independently of list order:

| Dependency | Preserved report | Original canonical reference | Immutable snapshot |
| --- | --- | --- | --- |
| `research.1n.cdx` | [Researcher A](tailnet_dispatch_setup__a.md) | `research:202609/tailnet_remote_dispatch_initialization_gap_analysis__a.md` | `file:explicit:57955f67067081da4a741a2a` |
| `research.1n.cld` | [Researcher B](tailnet_dispatch_setup__b.md) | `research:202609/sase_init_tailnet_enrollment__b.md` | `file:explicit:328b1b343d274ae6b986947d` |

Both canonical reports were read using `sase artifact read`. Only their copies in this research checkout were moved; SHA-256 checks confirmed unchanged bytes. No predecessor transcripts were read.

Additional audited context: [earlier machine-management research](../remote_machine_management_enablement.md), `bead:sase-xe`, `plan:202609/remote_dispatch_fleet.md`, and `plan:202609/machine_cli_enrollment_1.md`. The epic artifact initially lacked a published page; a later audited read succeeded, and `sase bead show --no-links --format json` supplied its current notes and child status.

The lead inspected `sase` at `a0ac015e0bda1d0cc1e1eeb859e92e2f0314cdfe` and an explicitly opened `sase-core` checkout at `630323fcefea5ef266ce4653e4a0c0a39fa75f16` (v0.32.44). A and B inspected earlier revisions, `2edf986b6` and core `1396607`. Diffs show the relevant machine/discovery implementation and gateway/bootstrap surfaces remain unchanged; intervening default-config additions concern another subsystem. Live observations below are time-specific and distinguished from source findings.

## Why initialization stops

| Stage | Current implementation | Work remaining |
| --- | --- | --- |
| Command ownership | `machine` has no `init` child. `init machine` owns discovery and enrollment directly. | Add canonical `sase machine init`; share its planner and apply service with both onboarding entry points. |
| Scheduling | `plan_init_machine()` emits no action when discovery providers are absent, or when any machine already exists. The onboarding coordinator skips plans without actions. | Offer initial setup under usable defaults; let explicit machine initialization rescan and reconcile an existing registry. |
| Defaults | `builtin@tailnet.enabled: false` and `discovery.enabled_providers: []`. Even explicitly selecting a disabled provider silently skips it. | Enable Tailnet for explicit setup by default, preserve deliberate opt-out, and explain disabled selections. |
| Discovery | `BuiltinDispatchProviders.dispatch_discover()` returns `()` even with both settings enabled. | Enumerate peers and perform bounded gateway probes, returning diagnostics alongside candidates. |
| Compatibility | Public health identifies `sase_gateway` and its crate version. Fleet protocol/capabilities require authenticated hello. | Advertise minimal supported fleet protocols before enrollment; retain authoritative negotiation afterward. |
| Target readiness | The core wheel exposes `sase_federation_worker`, but no `sase_gateway` console script. Gateway startup presently depends on a separate executable/development build. | Distribute the gateway through normal supported installations and provide a target setup/runbook path. |
| Enrollment authorization | Rust `FleetCredentialStore::issue_bootstrap()` exists, but no production CLI or Python binding invokes it. | Expose a target-local bootstrap command using the existing store and identity semantics. |
| Configuration activation | Machine writes honor chezmoi source mapping but do not apply that source to the config path loaded at runtime. | Deploy the scoped change, reload, and verify the enrolled record and credential before declaring setup complete. |

Primary source anchors: [`init_machine_handler.py`](https://github.com/sase-org/sase/blob/a0ac015e0bda1d0cc1e1eeb859e92e2f0314cdfe/src/sase/main/init_machine_handler.py), [`providers.py`](https://github.com/sase-org/sase/blob/a0ac015e0bda1d0cc1e1eeb859e92e2f0314cdfe/src/sase/dispatch/providers.py), [`default_config.yml`](https://github.com/sase-org/sase/blob/a0ac015e0bda1d0cc1e1eeb859e92e2f0314cdfe/src/sase/default_config.yml), [`gateway routes`](https://github.com/sase-org/sase-core/blob/630323fcefea5ef266ce4653e4a0c0a39fa75f16/crates/sase_gateway/src/routes.rs), [`bootstrap store`](https://github.com/sase-org/sase-core/blob/630323fcefea5ef266ce4653e4a0c0a39fa75f16/crates/sase_gateway/src/fleet_auth.rs), and [`wheel entry points`](https://github.com/sase-org/sase-core/blob/630323fcefea5ef266ce4653e4a0c0a39fa75f16/crates/sase_core_py/pyproject.toml).

The accepted epic explicitly requires default Tailnet discovery during setup and defensive parsing of `tailscale status --json`. Its closure is not evidence that this works: landing notes 7–8 describe discovery as a remaining stub and record a separate acceptance/hardening draft. Note 11 says the epic was automatically closed after its landing commit, with no verification implied. The current epic has no child epics attached. Reconcile that draft before assigning implementation work. [Epic and notes](https://github.com/sase-org/sase--beads/blob/main/pages/sase-xe/README.md), [accepted plan](https://github.com/sase-org/sase--plans/blob/main/202609/remote_dispatch_fleet.md).

## What the third investigation added

**The failures remain reproducible on newer source.** With the Tailnet provider enabled and selected in an isolated in-process config, the real provider still returned `()`. Live `sase machine --help` still lacked `init`. Live `sase init --check --json` still reported the machine planner as “no remote machine discovery providers are configured,” with zero actions. Its aggregate result was `drift` because other planners had work; A's earlier aggregate `current` should not be generalized. The machine-specific finding is unchanged.

**Chezmoi activation is a separate missing step.** The live effective setting is `use_chezmoi: true`. A temporary-file reproduction of `write_machine_record(..., use_chezmoi=True)`, with only the write-target mapping redirected to the fixture source, produced:

```text
source_has_probe: true
applied_has_probe: false
```

`_edit_machine_mapping()` writes the mapped source and clears caches. `load_merged_config()` reads the applied user config and selected overlays, and neither the writer nor `MachineService.add_machine()` calls the existing `apply_chezmoi()` helper. Clearing caches cannot deploy a file. This was a reproduction of writer behavior, not a live enrollment attempt. The fix must respect the existing tracked-process requirement for chezmoi apply, preserve the machine-specific overlay, and report partial completion if deployment fails. [Registry writer](https://github.com/sase-org/sase/blob/a0ac015e0bda1d0cc1e1eeb859e92e2f0314cdfe/src/sase/dispatch/config.py), [config loader](https://github.com/sase-org/sase/blob/a0ac015e0bda1d0cc1e1eeb859e92e2f0314cdfe/src/sase/config/core.py), [write-target and apply helpers](https://github.com/sase-org/sase/blob/a0ac015e0bda1d0cc1e1eeb859e92e2f0314cdfe/src/sase/config/targets.py).

**The init wrapper loses enrollment outcomes.** `run_init_machine()` discards `add_machine()`'s result and always prints `Enrolled` after a non-throwing return. An injected quarantined result reproduced that message and exit code 0; this tests the wrapper contract, not a live gateway quarantine. The normal `machine add` handler does inspect the result. Reusing its outcome handling will prevent the new canonical init from inheriting the discrepancy. The current init prompt also echoes the bootstrap through `input()`, whereas `machine add` uses `getpass`. [Machine handlers](https://github.com/sase-org/sase/blob/a0ac015e0bda1d0cc1e1eeb859e92e2f0314cdfe/src/sase/main/machine_handler.py).

**Provider deadlines are not enforced.** `_safe_discover()` runs plugin code in-process, passes a timeout value, and converts exceptions to an empty result. A timeout argument is not a wall-clock bound. The accepted separately supervised provider helper remains unfinished. Discovery must distinguish unavailable tooling, malformed status, incompatible gateways, timeout, and a legitimately empty result; a thread pool alone does not guarantee cancellation of blocked work.

## What is actually ready on this Tailnet

The lead's read-only probes on 2026-09-08 confirmed:

| Observation | Meaning |
| --- | --- |
| Athena's Tailscale backend is running; Apollo and the Mac are online; the Pixel is offline. | Peer enumeration has useful input today. |
| MagicDNS is enabled; Athena reports `CertDomains: null`. | Certificate readiness needs confirmation; the admin console was not inspected. |
| Athena and Apollo return `{}` for Serve status. | Neither had a configured Serve route in these probes. |
| HTTPS health connections to Apollo and `kellys-macbook-pro.tail297af1.ts.net` fail on port 443. | The proposed default gateway endpoints are not reachable today. |
| Noninteractive SSH did not resolve the `sase`/gateway commands; the Mac also did not resolve `tailscale`. | An SSH-assisted setup must resolve the actual executable/environment, rather than infer package absence from `PATH`. |

A and B independently reported matching installed SASE versions across the three computers and no resolved gateway executable earlier in the dispatch. The host installation advanced during this research, so those version matches are historical evidence rather than a current equality claim. Neither package equality nor a running TUI/worker proves that a target serves the fleet API.

Tailscale status provides node metadata, not SASE installation or protocol metadata. Discovery therefore needs enumeration followed by probing. Use a validated node DNS name, stripping its trailing dot, to form a default `https://<node>.<tailnet>` endpoint. Allow explicit endpoint overrides. Tailscale documents JSON status for automation and warns its format can change. [Tailscale CLI](https://tailscale.com/docs/reference/tailscale-cli#status).

Tailscale Serve is the supported way to expose the loopback gateway within the Tailnet. It requires HTTPS enablement and remains subject to access controls; its interactive setup can guide the operator through unmet HTTPS requirements. B's claim that the admin console must be changed before code work is too strong: confirm readiness during target setup, using either that consent flow or the console. `CertDomains: null` alone was not an admin-setting inspection. A separate valid TLS terminator also satisfies SASE's HTTPS requirement. [Serve](https://tailscale.com/docs/features/tailscale-serve), [HTTPS setup](https://tailscale.com/docs/how-to/set-up-https-certificates).

## Decisions that resolve differences between the reports

1. **Make `machine init` canonical, while describing the history accurately.** The accepted plan required an init-registry integration and explicit machine operations, but did not list a `machine init` child. This command is the user's requested correction and fits existing onboarding conventions. `init machine` currently describes a discover-plus-enroll alias; it is misleading ownership, rather than literally an alias to a nonexistent command.
2. **Use fleet protocol compatibility, with package versions as diagnostic information.** Add a minimal public health field such as `fleet.supported_protocol_versions`. Do not rely on B's suggested 401-versus-protocol-error oracle: it depends on handler ordering and error interpretation. An older gateway without the field is “compatibility unknown”; manual, bundle-authorized enrollment can still use the existing protocol check. A public health response never supplies the trusted installation pin.
3. **Keep online state and OS advisory.** Prefer A's approach over an unconditional mobile/offline exclusion. Show offline or unsupported-looking peers with reasons, permit explicit probing, and let the gateway protocol determine readiness. Do not derive SASE's authoritative machine selector from Tailscale `HostName`: the Mac's display name, SSH alias, and SASE identity can differ.
4. **Respect the Rust backend boundary.** Both reports suggest a substantial new Python discovery implementation. Shared parsing, compatibility, identity, and reconciliation policy belong in `sase-core`, exposed through bindings; Python can retain CLI prompts, provider adapters, and platform process glue. The existing gateway dependency in `sase_core_py` makes packaging plausible, but a server entry point still needs argument handling, Tokio lifecycle, shutdown, and installed-wheel tests. It is not a verified three-line task.
5. **Separate first successful setup from dependable operation.** A foreground gateway can prove enrollment. A usable always-available Apollo needs supervision and restart verification; a Mac needs a supported lifecycle and explicit sleep/offline handling. These can be staged within the work, but must not disappear behind a “discovery fixed” close.

The earlier enablement report overstates downstream completeness and offers hand-editing the bootstrap store as a workaround. Presence of the downstream code is established; this research did not prove the complete operational path. Preserve the existing Rust-issued bootstrap contract instead of making manual credential-file construction the supported setup procedure.

## Implementation scope and acceptance

All new command names below are proposed; `sase machine bootstrap` and `sase machine init` do not exist in the inspected version.

**First, finish target preparation in core and its packaging.** Export a normal `sase_gateway` entry point using the existing federation-worker packaging pattern. Expose `FleetCredentialStore::issue_bootstrap()` through a narrow local binding and `sase machine bootstrap --json`. Preserve its default 600-second, single-use secret, target installation pin, and scoped authorization. Gateway and bootstrap must use the same OS user and SASE home. Keep issuance local; discovery must not gain an unauthenticated secret-minting endpoint. Extend health with the fleet protocol advertisement and regenerate the contract. Publish the core release and update the host dependency floor/pin together with callers.

**Second, finish discovery and canonical initialization.** Have `sase machine init`, `sase init machine`, and the onboarding registry share one machine-owned planner/apply service. Keep offline checks and previews free of network or provider execution; run discovery during explicit apply, after local identity setup. Enable Tailnet in both default settings, while honoring explicit disablement and the actual config-layer merge semantics. Selecting one existing machine must not suppress an explicit rescan for another.

Run `tailscale status --json` without a shell, with enforced process and output limits. Parse the map-shaped `Peer` payload defensively, exclude self, validate DNS endpoints, and probe independently with per-peer and overall bounds. Return ready candidates plus structured diagnostics. Missing Tailscale should leave local onboarding usable and explain that machine setup is unavailable. A broken provider must not render as an empty successful setup. Keep provider import/execution isolation consistent with the accepted helper contract.

**Third, make enrollment resumable and its result usable immediately.** Select peers explicitly and obtain the target bundle through a hidden prompt or supported file/stdin input. Reuse the existing pin-verified enrollment service. Reconcile existing aliases and pins, skip already enrolled identities, preserve offline records, and route changed identity to deliberate repair. Never infer trust from Tailnet membership or overwrite a pin during rescan. Write only provider, endpoint, pin, and credential reference into the controller's machine overlay; tokens stay in its protected local store. Deploy chezmoi changes through the established apply mechanism, reload, and perform authenticated hello before printing success. Partial enrollment/deployment must retain actionable recovery state because the target may already have consumed the bootstrap.

**Fourth, deliver the runbook and live proof.** Prepare Apollo first: install the packaged gateway, run it loopback-bound at `127.0.0.1:7629`, explicitly configure node-specific Serve, and issue a local bootstrap. From Athena, exercise the canonical command and bare init, then verify `machine list`, `machine status`, deep doctor, and a real remote launch on an eligible configured project. Repeat with the Mac while online; verify that sleep does not remove its enrollment or stall another peer. Include gateway supervision/restart steps for Linux and macOS. Optional SSH-assisted bootstrap can follow, using Bryan's configured aliases/users and explicit target selection; it is not necessary for the first complete path.

| Acceptance gate | Required evidence |
| --- | --- |
| Installed target | Supported Linux/macOS installation resolves and runs the gateway without a source checkout; bootstrap reaches the same identity/store. |
| Real discoverer | Fixture coverage for missing/extra fields, self, trailing-dot DNS, offline peers, missing CLI, malformed/oversized output, and cancellation; compatible live Apollo is found. |
| Compatibility and authorization | Unrelated HTTPS service and incompatible/unknown protocol get distinct states; expired/replayed bootstrap and wrong pin fail safely; no secret echo. |
| Shared command behavior | All three init entry points use the same flow; explicit rescan finds a second peer; checks/previews do no discovery; ordinary empty-registry runtime stays inert. |
| Configuration activation | On a chezmoi-enabled controller, the applied overlay reloads immediately and resolves its credential; apply failure and partial enrollment have a tested recovery path. |
| Operational completion | Authenticated hello and an eligible remote launch succeed; Fleet consumes the record; a sleeping Mac or restarted gateway does not break another target. |

Existing tests cover fake provider aggregation, portions of machine-service persistence, and offline init checks. They do not establish the built-in Tailnet path or this full setup ceremony. Run repository-required verification when implementing, with installed-wheel and cross-repository contract checks in addition to isolated fixtures. No implementation or service configuration was changed in this research turn; verification here consisted of source inspection, read-only live probes, and temporary/injected reproductions.

Local identity display, Focus/Fleet keybindings, and broader performance hardening remain useful surrounding work. They do not replace the setup acceptance gates above.

## Recommended solution

**Complete one focused Tailnet-initialization workstream spanning `sase-core`, `sase`, and target setup, reconciled with the unfinished draft recorded on `sase-xe`.** Its deliverable should be a normally installed Apollo that Athena can discover, explicitly enroll, and use immediately through `sase machine init`, with bare `sase init` wrapping the same workflow. Land gateway packaging, local bootstrap issuance, protocol-aware bounded discovery, and chezmoi deployment/reload verification together. Close the initialization gap only after the Athena → Apollo path succeeds and the Mac's offline/resume behavior is verified; changing defaults or producing a peer list alone does not fulfill the requested outcome.
