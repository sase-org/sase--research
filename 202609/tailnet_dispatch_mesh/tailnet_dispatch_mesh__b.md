# Full-Mesh `%dispatch` Across athena, apollo, and mac

Research date: 2026-09-11. Researcher B. SASE host `875447e21`, linked core at v0.34.7
(`fcbecc0`). All live observations below are read-only probes taken 2026-09-11
between 12:30 and 13:10 UTC; no configuration, enrollment, or agent launch was
performed.

## Bottom line

The transport and enrollment machinery is **not** the thing standing between you and a
three-machine mesh. It already works in both directions between the two Linux boxes:
apollo's gateway is reachable and authenticated from athena, and — verified live today —
**athena's gateway is equally reachable from apollo and already advertises fleet protocol
v1**. Apollo simply has never been told to enroll athena.

What actually remains splits into four very different piles, and only one of them is
"more remote-dispatch code":

1. **One command away (hours).** apollo → athena. Issue a bootstrap on athena, run
   `sase machine init` on apollo. Everything else on that edge is already live.
2. **Target-side hardening that is currently accidental, not declared (hours, but do it
   first).** Athena's gateway unit omits `--agent-bridge-command`, and it only works at
   all because the unit happens to have inherited a rich `PATH`. Apollo's unit has the
   flag but is an *uncommitted local divergence* from the chezmoi source. Neither
   machine's target-side setup is reproducible, and the chezmoi source contains the
   broken variant — which is exactly what mac would be provisioned from.
3. **Genuinely new work for mac (days).** macOS has never been exercised as a target.
   Packaging is fine (macOS universal2 wheels are published and build in CI), but
   supervision, Tailscale Serve, machine identity, project parity, and sleep/offline
   behavior are all unproven. mac is also a *different SSH user* (`bbugyi`, not `bryan`).
4. **The open epic work you already have (unbounded until closed).** athena → apollo
   dispatch *submits* today but does not *settle*: 12 real launch intents on this
   machine, 7 accepted and 5 acceptance-uncertain, and **every single receipt is still
   `pending` with a null logical locator, and all 12 follows were never activated.**
   Adding two more machines multiplies that defect rather than exposing a new one.

Recommendation in one line: **do not expand the mesh edge-by-edge by hand. Make "this
machine is a dispatch target" a first-class, verifiable SASE operation, prove it by
fixing athena and apollo with it, then use it to onboard mac** — and land the
athena→apollo settlement/visibility repair before mac, not after.

---

## Part 1 — What is actually live right now

| Probe | athena | apollo | mac |
| --- | --- | --- | --- |
| Tailscale peer state | self | `active; direct` | **`offline, last seen 1m ago`** |
| `tailscale serve status` | `https://athena…ts.net → 127.0.0.1:7629` | `https://apollo…ts.net → 127.0.0.1:7629` | not checked (offline) |
| Loopback gateway health | `status: ok`, `fleet.supported_protocol_versions: [1]` | same | — |
| Gateway supervision | `sase-gateway.service` (user systemd), active | same | none known |
| **Cross-tailnet HTTPS health** | reachable **from apollo** | reachable from athena | SSH and 443 both time out |
| `sase machine list` | `apollo  configured  builtin@tailnet` | **`No remote machines are configured.`** | — |
| `sase machine discover` | finds apollo `compatible`; mac/pixel `unknown; TimeoutError; offline` | **finds athena `compatible`** | — |
| `sase machine status <peer>` | `apollo` → `ok`, `protocol_version 1`, capabilities include `fleet.launch` | not enrolled | — |
| `sase` / `sase-core-rs` | `0.17.1+446.g8e3790c58` / `0.34.7` (editable) | identical | unknown |
| Registered projects | `sase`, `actstat`, `bob-cli` | `sase`, `bob-cli` (+ duplicate `sase` record) | unknown |

Two things are worth pulling out of that table.

**The apollo → athena edge is transport-complete today.** From apollo:

```
$ curl -fsS https://athena.tail297af1.ts.net/api/v1/health
{"status":"ok","service":"sase_gateway",…,"fleet":{"supported_protocol_versions":[1]}}
```

and `sase machine discover` on apollo returns athena with
`compatibility=compatible; fleet protocol v1 advertised; tailscale=online`. The only
missing ingredient on that edge is a credential — i.e. one `sase machine bootstrap` on
athena and one `sase machine init` on apollo.

**mac is offline as its normal resting state.** `tailscale status` reports it offline
having been seen one minute earlier — i.e. it flaps with the lid. This is not an
incidental detail; it changes what "enrolled" has to mean for that machine (see Part 4).

---

## Part 2 — The unit of work is not "a machine", it is "a target" plus "an edge"

It is worth being precise about what scales, because it determines the whole plan.

**Per-target setup (3 items total, one per machine).** A machine that can *receive*
dispatched agents needs: installed `sase` + packaged `sase_gateway`/
`sase_federation_worker`; a supervised loopback gateway with a working
`--agent-bridge-command`; an HTTPS terminator (Tailscale Serve); a machine identity
(`~/.sase/machine_name` + `sase_<name>.yml` overlay); and the projects/credentials a
launched agent will need.

**Per-edge enrollment (6 directed edges for 3 machines).** Enrollment is one-directional
and non-transitive by construction. `sase machine bootstrap` mints a single-use secret on
the target, pinned to that target's installation id
(`src/sase/dispatch/credentials.py`), and the controller stores a bearer token in its own
protected `~/.sase/fleet/credentials.json` while the alias record goes into the
controller's **machine-scoped** config overlay (`_registry_target_path()`,
`src/sase/dispatch/config.py:254`). athena knowing apollo tells apollo nothing.

Good news on the mesh shape: nothing in the code caps the host count.
`load_federation_config` (`src/sase/dispatch/federation/_hosts.py:69`) builds one host per
configured machine with no limit, `select_candidates`
(`src/sase/dispatch/_machine_init_interaction.py:86`) accepts a comma-separated
multi-select, and the per-machine overlay convention means apollo's `sase_apollo.yml` and
athena's `sase_athena.yml` cannot collide even though both live in the same chezmoi
source. A mesh is 3 target setups + 6 enrollments, not an N² redesign.

So the arithmetic is: **1 of 6 edges done, 2 of 3 targets half-done, 0 of 3 targets
reproducible.**

---

## Part 3 — Target-side readiness is the real hidden debt

This is the finding I would act on first, because it is currently invisible and it is
what mac will inherit.

### 3.1 athena's gateway can say hello but was never configured to launch

```
# athena: ~/.config/systemd/user/sase-gateway.service
ExecStart=%h/.local/share/uv/tools/sase/bin/sase_gateway --bind 127.0.0.1:7629 --sase-home %h/.sase

# apollo: same file
ExecStart=… --bind 127.0.0.1:7629 --sase-home %h/.sase --agent-bridge-command /home/bryan/.local/share/uv/tools/sase/bin/sase
```

`docs/remote_dispatch.md` is explicit about the consequence: "Without it, authenticated
hello can succeed while remote launch fails with `agent_bridge` unavailable." athena is
currently in that shape. It happens to work anyway — but only by accident:

```
athena gateway PATH: …:/home/bryan/.local/bin:/usr/local/bin:…     ← `sase` resolves
apollo gateway PATH: /usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:…
```

athena's gateway process inherited a rich environment from however it was first started;
apollo's got the stock systemd user-manager `PATH`. A reboot or a
`systemctl --user daemon-reexec` on athena can silently move it to apollo's `PATH` and
break remote launch, with a green `sase machine status`.

### 3.2 The working configuration is not the configuration in chezmoi

```
athena$ chezmoi status | grep -i sase      →  MM .sase            (unit NOT listed = in sync)
apollo$ chezmoi status                     →  MM .config/systemd/user/sase-gateway.service
```

Both machines manage `.config/systemd/user/sase-gateway.service` through chezmoi. athena's
applied copy matches the source and **lacks** `--agent-bridge-command`; apollo's applied
copy **has** it and is therefore `MM` — modified in both source and target, i.e. a local
hand-edit that was never committed. The canonical source unit is the broken one. Any
third machine provisioned from chezmoi gets the broken one, and apollo's fix is one
unscoped `chezmoi apply` away from being reverted.

Nothing about Tailscale Serve is chezmoi-managed at all — `chezmoi managed` shows no
serve-related script on either machine. Serve was configured by hand, twice.

### 3.3 The gateway's environment is thinner than an agent needs

Under apollo's actual gateway `PATH`:

```
sase=MISSING   uv=MISSING   chezmoi=MISSING   opencode=MISSING
git=/usr/bin/git   gh=/usr/bin/gh   tmux=/usr/bin/tmux   claude=/usr/local/bin/claude   codex=/usr/local/bin/codex
```

The gateway spawns `sase mobile agent-bridge …` (`crates/sase_gateway/src/host_bridge.rs:220`),
which launches a *normal* SASE agent inside that environment. `git`, `gh`, `tmux`,
`claude` and `codex` survive; `uv`, `chezmoi` and `opencode` do not. Notably
`apply_chezmoi()` (`src/sase/config/targets.py:128`) invokes a bare `"chezmoi"` from
`PATH` — so any config write a dispatched agent performs on apollo will fail to deploy.
The runbook already recommends an `Environment="PATH=…"` property; neither unit sets one.

### 3.4 There is no command for any of this

```
$ grep -rln "sase-gateway.service|LaunchAgent" src/ docs/ tools/
docs/remote_dispatch.md
```

Target provisioning exists only as prose. `sase doctor -C dispatch` has four checks
(`src/sase/doctor/checks_dispatch.py:28`) — config, credentials, federation worker,
outbound hello — **all controller-side**. There is no check that answers "can *this*
machine be dispatched *to*": no gateway-running check, no Serve check, no
agent-bridge-resolvable check. On a mesh every machine is both roles, so half the
diagnostic surface is missing on every node.

---

## Part 4 — mac: what is genuinely new

Packaging is the part that is *not* a problem. `sase-core-rs` publishes
`…-cp312-abi3-macosx_10_12_x86_64.macosx_11_0_arm64.macosx_10_12_universal2.whl`, the
release workflow has a dedicated `macos universal2` job
(`.github/workflows/release-plz.yml:228`), and `sase_gateway` /
`sase_federation_worker` are ordinary console scripts into
`sase_core_rs.gateway:main`, so they ship wherever the wheel ships. The dispatch package
contains **zero** `sys.platform`/`darwin` branches, and the worker command resolver
(`src/sase/dispatch/federation/_supervisor.py:27`) is platform-neutral. `sase` itself
already carries darwin fallbacks in `core/process_identity.py` and `doctor/checks_tools.py`,
and every `systemd` call site is guarded by `shutil.which`.

What is unproven or missing:

- **Tailscale CLI and Serve on macOS.** The gateway must be fronted by HTTPS —
  `src/sase/dispatch/fleet_client.py:99` rejects any non-`https` scheme and the Rust
  contract does the same (`validate_absolute_https_endpoint`,
  `crates/sase_core/src/fleet_contract.rs:6629`). There is no HTTP escape hatch. Earlier
  research on this tailnet recorded that `tailscale` did not resolve on mac at all. Which
  Tailscale build is installed there decides whether `tailscale serve` is even available;
  on App Store builds the CLI lives at
  `/Applications/Tailscale.app/Contents/MacOS/Tailscale`. **Verify this before planning
  anything else for mac — it is the single most likely hard blocker.**
- **LaunchAgent supervision.** `docs/remote_dispatch.md` has a plist template that has
  never been run. It hardcodes `/Users/YOU`; mac's user is `bbugyi`, not `bryan`, so every
  absolute path in the runbook and in apollo's unit differs. A `gui/$(id -u)` LaunchAgent
  also only runs while that user is logged in — and does not run while the machine is
  asleep at all.
- **Machine identity.** Enrollment writes into `sase_<machine_name>.yml`, selected by
  `~/.sase/machine_name` (`src/sase/core/paths.py:131`). If that selector is unset on mac,
  `_registry_target_path()` falls back to `CONFIG_DIR/sase.yml` — the layer chezmoi shares
  with **every** machine. A mac enrollment written there would be applied to athena and
  apollo too, with a credential ref neither of them holds. Set the selector and create
  `sase_mac.yml` **before** the first `sase machine init` on mac.
- **Project parity.** The target resolves the project by name from its own registry
  (`project_context_from_project_value`, `src/sase/integrations/_mobile_agent_context.py:62`).
  If the name is unknown it returns `None` — and the launch **silently proceeds from the
  gateway's cwd** rather than failing. mac needs the `sase` project registered with a real
  workspace, or `%dispatch:mac` will "succeed" into the wrong directory.
- **Agent provider credentials.** A dispatched agent is a normal agent; it needs `claude` /
  `codex` authenticated on mac under `bbugyi`.
- **Offline-as-normal.** mac spends most of its life offline. Today discovery handles that
  honestly (`compatibility=unknown; TimeoutError; tailscale=offline; os=macos` plus
  `tailnet_peer_offline` / `tailnet_probe_unreachable` diagnostics). What is *not* proven is
  the enrolled-and-unreachable case in the Fleet read path — see Part 6.

---

## Part 5 — Cross-cutting defects the mesh will amplify

These are real, reproduced today, and they are worse with three machines than with two.

### 5.1 `sase machine init -B <file>` reuses one single-use bundle for every candidate

```python
# src/sase/dispatch/machine_init.py:205
for candidate in selected:
    alias = read_alias(input_func, candidate)
    bundle = bundle_text if bundle_text is not None else read_bundle_once(getpass_func, stdin)
```

Interactive mode prompts once *per candidate* — correct. But `-B` pins `bundle_text` for
the whole loop, so selecting two candidates replays one target's single-use,
installation-pinned secret against a second target. It will fail, and it fails *after* the
first target has already consumed its bundle. The very workflow a mesh wants — "enroll both
of my peers in one run" — is the one that is broken. The loop also returns on the first
error, abandoning remaining candidates.

### 5.2 Nothing suggests an alias, for any tailnet candidate

`_suggested_alias` (`src/sase/dispatch/_machine_init_interaction.py:118`) derives the
default from `candidate.machine_selector`, which the tailnet discoverer leaves empty for
every candidate (confirmed: `"machine_selector": ""` on all three rows from both machines).
So every alias is hand-typed, and the display name it would otherwise fall back to is
`Kelly's MacBook Pro` — which `validate_machine_alias` rejects anyway (curly apostrophe,
spaces). Minor, but it is six hand-typed aliases across the mesh with no consistency
enforcement.

### 5.3 The portable revision is validated at the source and then discarded

`%dispatch` makes you prove your tree is clean, has an upstream, and that `HEAD` is pushed
(`_published_git_revision`, `src/sase/dispatch/launch.py:304`), and packs `revision` into
the portable context. The target-bound wire type has **no revision field**:

```rust
// crates/sase_gateway/src/wire.rs:665
pub struct MobileAgentTextLaunchRequestWire {
    … prompt, request_id, display_name, name, model, provider, runtime,
    pub project: Option<String>,      // ← only this survives
    pub device_id, pub dry_run,
}
```

and the construction site (`crates/sase_gateway/src/routes.rs:1128`) passes only
`project_id`. A dispatched agent runs against whatever revision the target's workspace
happens to be on. With two Linux boxes you keep in sync by habit this is invisible; with a
laptop that is offline for days it becomes the default failure mode — you will get silent
version skew, not an error. Either honor the revision on the target or stop demanding the
proof; the current state is the worst of both.

### 5.4 `sase repo open` cannot resolve this project's sidecars or linked repos

Incidental to your question but it cost me time and will cost agents doing this work time:
`sase repo list` reports the project as `sase` with sidecars `research`, `plans`, `beads`,
`agents` and linked `chezmoi`, `sase-core`, … while `sase repo open <any of them>` answers
`Unknown repo … for project 'gh_sase-org__sase'. Valid repos: gh_sase-org__sase`. Passing
`-p sase` fails differently: `Project 'sase' has no WORKSPACE_DIR`. Two project records
(`sase` and `gh_sase-org__sase`) exist and the open resolver picks the one with no repo
inventory. The same duplicate pair is visible in `sase project list` on apollo. External
opens (`gh:sase-org/sase-core`) work fine.

---

## Part 6 — The open epic work, and why it gates mac rather than follows it

`sase-xe` → `sase-xe.16` → `sase-xe.16.11` → `sase-xe.16.11.7` → `.14` → `.14.6` is five
levels of reopened epic, and the still-open leaves are all *acceptance*, not design:

| Bead | State | Scope |
| --- | --- | --- |
| `sase-xe.16.10` | OPEN | Runbook + live athena→apollo proof |
| `sase-xe.16.11.3` | OPEN | Real deadlines, instance fencing, bootstrap enrollment under faults |
| `sase-xe.16.11.5` | OPEN | The real athena→apollo workflow |
| `sase-xe.16.11.7.13` | IN_PROGRESS | Live acceptance of the unified Agents experience |
| `sase-xe.16.11.7.14.6` | IN_PROGRESS | Fleet snapshot correctness + released live acceptance |

The live state on this machine corroborates that these are genuinely unmet, and does it
more sharply than the bead notes do. `~/.sase/fleet/dispatch_launch_intents.json` holds
**12 real dispatch launches to apollo** (10 Sep, prompts like *"You are the Apollo
exact-stop acceptance observer…"*): 7 `accepted`, 5 `acceptance_uncertain`, and

- every `receipt.state` is `pending`,
- every `receipt.logical_locator` is `null`,
- all 12 records in `follows.json` are `state: pending` with `activated_at_unix: null`.

So: **submission works, settlement does not.** Launch requests reach apollo and are
admitted; the controller never learns the resulting agent's identity, so the agent never
becomes a followed, manageable row. That is precisely the "launch visibility and recovery"
gap `sase-xe.16.11` note #5 describes, still live.

Two adjacent facts, verified today:

- **One fleet test fails on clean master.** `tests/ace/tui/test_agents_fleet_refresh_laziness.py::test_fleet_catalog_refresh_requests_legal_pages_and_logical_keys` — expected a second catalog page request with `cursor: 'off:100'`, got `[]`. Per-host continuation is not being issued. (97 other fleet/dispatch tests pass, including
  `tests/dispatch/test_machine_bootstrap_real_gateway.py`, which does a genuine
  issue→enroll→hello round trip against a real gateway.) With one remote machine you may
  never exceed 100 rows. With three you will.
- **Flag bead `sase-z6` (`ace_unified_agents`) has no definition**, so
  `tools/check_feature_flags` rule 8 fails and `just check` stops at lint before tests.
  Reported independently twice on 2026-09-11 by unrelated agents, and consistent with
  `sase flag list` showing no such flag. Whoever picks up this work hits it immediately.

Finally, one discrepancy I could not fully explain and would confirm before any live
acceptance run: **both gateways advertise `sase_gateway` package version `0.34.2`** while
both hosts report `sase-core-rs 0.34.7` and both run editable installs pointing at a local
`sase-core` checkout whose `.so` was rebuilt this morning. The health field is
`env!("CARGO_PKG_VERSION")` at compile time (`crates/sase_gateway/src/daemon.rs:99`). Either
the compiled gateway genuinely predates the fleet-normalization repairs that landed in
0.34.3–0.34.7 — in which case the wire you are testing against is not the wire you fixed —
or the installed dist-info is stale metadata. Both are worth knowing; the first would
explain a lot of the acceptance churn.

---

## Part 7 — Recommended solution

**Make target readiness a command, prove it on the two machines you already have, repair
settlement, then onboard mac. Four stages, strictly ordered.**

### Stage A — Declare what a dispatch target is (do this first; it is small)

1. Add `Environment="PATH=%h/.local/bin:%h/bin:%h/.local/share/uv/tools/sase/bin:/usr/local/bin:/usr/bin:/bin"`
   and `--agent-bridge-command %h/.local/share/uv/tools/sase/bin/sase` to the **chezmoi
   source** `sase-gateway.service`, so both machines converge on the working variant and
   apollo's `MM` divergence disappears.
2. Bring Tailscale Serve under chezmoi as a `run_onchange` script, the same pattern
   `~/.ssh/tailnet.conf` already uses. It is currently hand-configured on two machines and
   will be hand-configured on a third.
3. Extend `sase doctor -C dispatch` with **target-side** checks: gateway process reachable
   on loopback; health advertises `fleet.supported_protocol_versions`; the configured
   agent-bridge command resolves *from the gateway's own environment*; the HTTPS endpoint
   answers from off-box. Today all four dispatch checks look outward only.
4. Package the two supervision recipes as something executable — `sase machine serve
   --install` emitting the systemd unit or LaunchAgent for the current platform — rather
   than leaving them as prose in `docs/remote_dispatch.md`. This is what makes mac
   onboarding a command instead of a transcription exercise.

### Stage B — Close the apollo → athena edge (the cheap win, and the honest test of Stage A)

```
athena$ umask 077 && sase machine bootstrap --json > /tmp/athena-bootstrap.json
apollo$ sase machine init -B /path/to/athena-bootstrap.json      # select athena, alias `athena`
apollo$ sase machine status athena -j && sase doctor -D -C dispatch
```

Transport, discovery, compatibility and protocol are already proven on this edge, so a
failure here is a Stage-A failure and you will learn it immediately. Confirm afterwards
that apollo's record landed in `sase_apollo.yml` (not shared `sase.yml`) and that the
chezmoi apply succeeded — apollo's `chezmoi` is at `~/bin/chezmoi`, which is on an
interactive `PATH` but not a systemd one.

### Stage C — Repair settlement before adding a third machine

Fix, inside the existing `sase-xe.16.11.7.14.6` scope:

- launch settlement — a receipt must reach a logical locator and a follow must activate;
  12 live records say it currently does not;
- per-host catalog continuation (the failing test above);
- the enrolled-but-unreachable host path, which today has no live proof and which mac will
  exercise constantly;
- flag bead `sase-z6`, which blocks `just check` for everyone.

Decide explicitly on the discarded `revision` (5.3): either thread it to the target or
drop the source-side proof requirement. Do not carry a validated-then-ignored field into a
three-machine fleet.

Stage C is where the schedule risk lives, and it is the reason I would *not* onboard mac
first even though it is the more interesting machine. Every defect above is currently
being debugged against one remote host; adding an intermittently-offline macOS host mid-repair
makes every symptom ambiguous.

### Stage D — Onboard mac, then complete the mesh

1. **Verify `tailscale serve` is available on mac at all.** If not, stop and solve that —
   there is no HTTP fallback anywhere in the stack.
2. `uv tool install sase`; confirm `sase_gateway --help` and `sase_federation_worker --help`
   resolve from the tool venv.
3. Set `~/.sase/machine_name` and add `sase_mac.yml` (with `id.machine_name: mac`) to the
   chezmoi source **before** any enrollment, so records never land in shared `sase.yml`.
4. Install the LaunchAgent from Stage A step 4 under `/Users/bbugyi`; `tailscale serve
   --bg --yes 7629`; verify health from athena.
5. Register the `sase` project and authenticate the agent CLIs on mac.
6. Enroll the four remaining edges — athena→mac, mac→athena, apollo→mac, mac→apollo — one
   bootstrap per edge. Until 5.1 is fixed, **do not use `-B` with a multi-candidate
   selection**; run init once per peer, or use the interactive per-candidate prompt.
7. Decide the sleep policy explicitly. `%dispatch:mac` on a sleeping laptop has no
   defined behavior today beyond a timeout. Either document "wake it first" or add a
   pre-submission liveness check — `_target_machine` (`src/sase/dispatch/launch.py:249`)
   checks only enrollment and quarantine, never health.

### Acceptance for "the mesh is done"

- All 6 edges: `sase machine status <peer>` returns `ok` with `fleet.launch` in
  capabilities, from each machine.
- Each machine's `sase doctor -D -C dispatch` is green **including the new target-side
  checks**, and the passing configuration is the one in the chezmoi source, not a local
  edit — `chezmoi status` clean for the gateway unit on all three.
- One `%dispatch` launch per directed edge reaches a **settled** receipt with a non-null
  logical locator, appears as a followed row in the launching machine's Agents list, and
  can be stopped from there.
- A gateway restart on each target leaves its enrollments intact (no re-bootstrap).
- With mac asleep, athena's and apollo's Agents/Fleet views stay responsive and show mac as
  an explicit unreachable host with a diagnostic, not as silently-missing or stale rows.
- Onboarding a hypothetical fourth machine is a documented command sequence with no
  hand-edited unit files.

---

## Provenance and method

- Live read-only probes on athena and over SSH to apollo (`tailscale status`,
  `tailscale serve status`, `curl …/api/v1/health`, `systemctl --user cat`, `/proc/<pid>/environ`,
  `chezmoi status`/`managed`, `sase machine list|discover|status`, `sase project list`,
  `sase version`, `sase doctor -D -C dispatch`). mac was probed only for reachability; SSH
  timed out and `tailscale status` reports it offline.
- Local state read from `~/.sase/fleet/{dispatch_launch_intents,follows}.json`. No secrets
  are reproduced here.
- Source read at SASE `875447e21` and at a `sase repo open gh:sase-org/sase-core` checkout
  at `fcbecc0` (v0.34.7).
- Tests executed: `tests/ace/tui/test_agents_fleet_refresh_laziness.py`,
  `test_fleet_agents_projection.py`, `test_fleet_agents_catalog_pages.py`,
  `test_fleet_agents_following.py`, `tests/test_fleet_contract_counts_sase_core_rs.py`,
  `tests/dispatch/` — 97 passed, 1 failed.
- Beads read: `sase-xe`, `sase-xe.16`, `sase-xe.16.11`, `sase-xe.16.11.7`,
  `sase-xe.16.11.7.14`. Memory: `tailnet.md`. Prior art: audited
  `sase artifact read research:202609/tailnet_dispatch_setup/tailnet_dispatch_setup.md`
  (2026-09-08) — most of its recommended workstream has since landed; its target-readiness
  and Mac-lifecycle cautions have not.
- PyPI wheel metadata for `sase-core-rs` 0.34.7 read from the public JSON API.
- No configuration, enrollment, agent launch, service restart, or repository mutation was
  performed during this research. No peer researcher's report from this swarm was consulted.
