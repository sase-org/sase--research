# Completing the Athena–Apollo–Mac dispatch mesh

Research date: 2026-09-11. Lead research checked against live state through approximately 17:00 UTC.

**The remaining work is three reliable target installations plus six directional enrollments and launch proofs. Athena → Apollo is the only enrollment confirmed today; even that direction still awaits completed end-to-end acceptance.** Apollo → Athena is the easiest next direction because its network path already works. The four Mac-related directions depend on an online setup session. The existing architecture supports this topology; a new transport or mesh coordinator is unnecessary.

This report combines [researcher A](tailnet_dispatch_mesh__a.md), [researcher B](tailnet_dispatch_mesh__b.md), and independent source, configuration, runtime, and upstream-documentation checks. The main additions are concrete evidence that both Linux gateways retain old loaded code, discovery of the Mac’s existing machine profile, confirmation that macOS Serve supports the required proxy, and narrower conclusions about historical launch failures.

**What is established, by direction**

| Controller → target | Verified state | Work remaining |
| --- | --- | --- |
| Athena → Apollo | Enrolled; authenticated protocol-1 hello succeeds and advertises `fleet.launch`. | Adopt the repaired runtime and finish launch settlement, correct project/revision, fresh output, control, and recovery acceptance. A successful hello is insufficient. |
| Apollo → Athena | Apollo reaches Athena’s HTTPS gateway; A/B also observed compatible discovery and working SSH. Apollo’s machine registry is empty. | Make Athena’s gateway configuration reproducible, update/restart it, issue an Athena bootstrap, enroll `athena` on Apollo, and prove a launch. |
| Athena → Mac | Athena has no `mac` enrollment. Mac is offline and SSH times out. | Prepare Mac as a target, then enroll it from Athena using a fresh Mac-issued bootstrap. |
| Apollo → Mac | Apollo has no enrollments; Mac is offline. | Reuse the same Mac target installation, but issue a separate bootstrap and enroll `mac` from Apollo. |
| Mac → Athena | Mac’s local enrollment/runtime state is unknown. Athena’s endpoint works from Apollo. | Inspect Mac’s existing state, establish controller prerequisites, and enroll or repair `athena` after Athena is launch-ready. |
| Mac → Apollo | Mac’s local enrollment/runtime state is unknown. Apollo is the best-proven target. | Inspect Mac’s existing state, establish controller prerequisites, and enroll or repair `apollo`. This is the easiest first Mac launch. |

There are **five unproven directions, requiring up to five additional enrollments**. Three missing enrollments are directly established from the Linux registries; the Mac’s two outbound enrollments cannot be counted as absent without inspecting it.

Enrollment is directional and non-transitive. Each target has one gateway and installation identity; each controller stores a separate credential for each target. Athena knowing Apollo does not authorize Apollo to launch on Athena. Do not copy `~/.sase/fleet/credentials.json` between machines. SSH is useful for setup and protected bootstrap transfer; ordinary dispatch uses authenticated HTTPS.

**The Linux services need deployment repair before more health checks will be meaningful**

Both gateways return health version `0.34.2`, while installed core metadata is in the `0.34.7` cohort. The lead check additionally found that **both running gateway processes map `sase_core_rs.abi3.so (deleted)`**. This is stronger than a version-string discrepancy: they retain an earlier native extension after its on-disk replacement. The current core checkout gives the gateway and Python binding the same workspace version, and health reports the gateway’s compile-time package version. Updating package metadata or rebuilding the extension does not update a running process. Restart and verify the deployed gateway, AXE, and controller workers after adopting the intended release.

The canonical chezmoi unit at `home/dot_config/systemd/user/sase-gateway.service` contains:

```ini
ExecStart=%h/.local/share/uv/tools/sase/bin/sase_gateway --bind 127.0.0.1:7629 --sase-home %h/.sase
```

Athena runs that form. Apollo’s live unit additionally passes an absolute `--agent-bridge-command`, but that addition is absent from the inspected canonical source. Neither unit declares a PATH. This independently confirms the reproducibility problem identified by B, although `chezmoi status` alone does not establish the edit’s exact commit history.

The bridge defaults to executing bare `sase` and inherits the gateway environment. A gateway can therefore answer hello while failing to start an agent. Declare the absolute installed bridge executable and a deliberate PATH in the source unit. Include the tools actually needed by dispatched work, such as `git`, `gh`, provider CLIs, `uv`, and `chezmoi`; validate under the service’s environment. Apollo’s ordinary noninteractive SSH shell also failed to find bare `sase` during the lead check, while its absolute installed command worked.

Keep the gateway under the correct user and SASE home, bound to `127.0.0.1:7629`, with persistent supervision and tailnet-only Serve. Confirm Linux user-service startup after logout/reboot, including the intended linger policy. Preserve installation state across updates so existing enrollments remain valid.

**The Mac requires onboarding, but two proposed prerequisites need correction**

The canonical chezmoi checkout already has:

```yaml
# home/dot_config/sase/sase_kellys_mbp.yml
id:
  username: bbugyi200
  machine_name: kellys_mbp
```

Its `.chezmoiignore` deploys that overlay, and the tailnet SSH configuration, only when chezmoi’s hostname is `Kellys-MBP`. There is no managed SASE gateway LaunchAgent in the inspected source.

Preserve this existing identity unless a deliberate migration is wanted. **The controller alias `mac` does not have to equal the target’s SASE machine name.** Verify the Mac’s actual hostname, `~/.sase/machine_name`, selected overlay, and chezmoi ignore evaluation before enrollment. A missing selector can make enrollment fall back to shared `sase.yml`; creating a second `sase_mac.yml` blindly would introduce competing identities. Tailnet memory identifies the SSH/OS user as `bbugyi`; the profile’s SASE username `bbugyi200` is a separate setting.

Tailscale’s current documentation explicitly supports **port sharing through Serve on both the App Store and Standalone macOS variants**. Their restriction concerns serving files/directories, which this gateway does not require. A variant change is therefore not an automatic prerequisite. [Tailscale Serve documentation](https://tailscale.com/docs/reference/tailscale-cli/serve)

Confirm that `tailscale` is executable from noninteractive processes. The Standalone app offers a CLI launcher; the App Store app bundles its CLI at `/Applications/Tailscale.app/Contents/MacOS/Tailscale`. Scripts can set `TAILSCALE_BE_CLI=1` to force CLI behavior. A shell alias alone does not make an executable available to SASE subprocesses. [Tailscale CLI documentation](https://tailscale.com/docs/reference/tailscale-cli?tab=macos)

A macOS universal2 wheel exists for core 0.34.7 and requires Python 3.12 or newer. This establishes packaging availability, not a working Mac installation. Verify the chosen release’s host/core/plugin combination and provider authentication under the gateway user. [Published package metadata](https://pypi.org/pypi/sase-core-rs/0.34.7/json)

For inbound dispatch, add a chezmoi-managed LaunchAgent using the Mac’s actual absolute paths, the explicit bridge command, and an intentional environment. The runbook plist currently omits the latter two. Configure Serve to proxy the loopback gateway over HTTPS and check it from both Linux machines. Confirm tailnet HTTPS permissions and access policy for every direction; successful Linux-to-Linux traffic does not prove the Mac’s access rules.

Treat the Mac as an available target **while awake and logged in**. The proposed GUI-domain LaunchAgent is session-scoped, and Tailscale’s GUI variants do not run before login. If pre-login unattended operation is required, that is a separate service/network deployment decision; it is not solved by enrolling the machine. [Tailscale macOS variant comparison](https://tailscale.com/docs/concepts/macos-variants)

**The remaining correctness work belongs with the existing dispatch closeout**

The active plan is `plan:202609/launch_recovery_and_xe_closeout.md`, under `sase-xe.16.11.7.14.6.7`. At the lead check, its targeting, requester-continuation, and regression phases were closed; publication/install and both live acceptance phases remained in progress. Older Apollo proof obligations are deliberately still open.

That plan documents an approval-path defect where an Apollo/project request became a local home-project agent and its requester was not resumed. This does not establish that every direct CLI launch fails. It does require acceptance through the actual launch surfaces the user intends to use, including approval/admission, with an observed remote hostname and project.

B’s historical state evidence also needs precision. The lead check found 12 intents created September 9–10: seven `accepted` with pending receipts, and five `acceptance_uncertain` **without receipts**. None has an authoritative receipt locator. All 12 follow records remain pending and unactivated, although they contain provisional locators. These are unresolved historical records, not 12 fresh failures reproduced against the repaired release. Preserve/reconcile them and prove a new launch settles; do not infer a universal present-day settlement failure from the old journal alone.

There is a separate source-level gap with practical importance for a laptop. The controller validates a published revision and carries it in portable context, but the inspected gateway constructs `MobileAgentTextLaunchRequestWire` with the project name and no revision/Patch field. Explicit workspace syntax in the prompt can affect target setup, but it does not establish enforcement of the separately validated revision. The mobile project resolver can also return no context for an unknown project, leaving the bridge’s current directory unchanged when no explicit workspace reference supplies one.

The original epic explicitly requires target-side project/revision admission and forbids silent use of the target’s default branch. **Preserve that contract: carry and enforce portable revision/Patch context and reject unresolved projects. Do not remove the source validation to hide the gap.** This shared behavior belongs in Rust core and the gateway wire, with the Python bridge as a thin adapter. Until demonstrated, a deliberately synchronized test project can support connectivity experiments, but general coding dispatch is not fully accepted.

Other findings affect convenience and diagnostics rather than requiring a new architecture:

- `machine init -B` reuses one file’s bundle across all selected candidates. Select exactly one target per invocation, or supply a fresh bundle interactively for each candidate. Explicit `machine add` is also suitable for a known endpoint.
- Current dispatch doctor checks cover configuration, credentials, controller worker, and outbound hello. Green doctor output does not certify local target readiness.
- B’s dated pagination-test and flag-lint failures should be reassessed by the active closeout. The current plan already assigns relevant acceptance and flag retirement; they do not justify a second broad repair epic.
- Acceptance should use the current unified Agents list with machine filtering. Older Focus/Fleet terminology in predecessor material is superseded.

**Evidence and limits**

A and B were matched by dependency identity and their existing suffixes, not list order. Their original canonical paths were `research:202609/remote_dispatch_all_tailnet_machines__a.md` and `research:202609/tailnet_full_mesh_dispatch__b.md`. Immutable provenance remains `file:explicit:26dd2765ab4ebf1a55284640` and `file:explicit:8a4a4ee4da90a168a7f12409`, respectively. Both were read through `sase artifact read` and moved byte-for-byte only within this workspace’s research checkout.

Additional audited artifacts were the original `plan:202609/remote_dispatch_fleet.md` and the closeout plan above. The epic’s published artifact page was missing, so its live record and current child statuses were inspected with `sase bead show`. No predecessor chat transcripts were read.

Source baselines: SASE `71717d95a009`, core `fcbecc0f8982`, chezmoi `0d334e8d0cf9`. Key inspected files were:

| Repository | Evidence |
| --- | --- |
| SASE | `docs/remote_dispatch.md`; `src/sase/dispatch/{config,machine_init,launch,launch_intent}.py`; `src/sase/integrations/_mobile_agent_context.py`; `src/sase/doctor/checks_dispatch.py` |
| sase-core | Gateway `Cargo.toml`, `src/{daemon,host_bridge,routes,wire}.rs`; workspace `Cargo.toml` |
| chezmoi | `home/dot_config/systemd/user/sase-gateway.service`; `home/dot_config/sase/sase_kellys_mbp.yml`; `home/.chezmoiignore` |

The repository opener’s display-name/canonical-key mismatch affected this investigation too. A process-local compatibility adapter normalized inventory project keys while retaining the normal `sase repo open` materialization and audit path. It enabled inspection of the canonical source; no product source was edited.

Live checks were read-only: Tailscale peer state, gateway health, systemd definitions and mapped-extension metadata, local/remote machine inventory, authenticated Apollo hello, and redacted journal counts. Mac SSH timed out. No bootstrap issuance, enrollment, agent launch, service restart, or fleet configuration change was performed. The report establishes remaining work; it does not claim that the mesh has been deployed.

**Recommended solution**

Use **chezmoi-managed target services, existing SASE enrollment commands, and staged acceptance**, with these priorities:

1. **Converge the Linux service definitions and finish the existing closeout.** Add the explicit bridge and environment to the canonical unit. Adopt the published repair cohort, restart the relevant services, and confirm running health/build identity. Require a fresh Athena → Apollo launch to settle to an authoritative locator and produce usable remote output. Include the approval path, project/revision enforcement, and recovery evidence; avoid launching another broad redesign.
2. **Prove Apollo → Athena.** Issue a short-lived Athena bootstrap immediately before setup, transfer it privately, and enroll alias `athena` on Apollo. For a fixed endpoint, the current command shape is `sase machine add athena https://athena.tail297af1.ts.net -p builtin@tailnet -B /path/to/bootstrap.json`. Alternatively, run guided init with only Athena selected. Delete the temporary bootstrap copies after activation, then verify status, doctor, and an actual launch.
3. **Bring the Mac online and make it a controller first.** Verify the existing `kellys_mbp` selector/profile, apply matching configuration, update SASE, start AXE, and check project/provider prerequisites. Inspect existing enrollments before adding anything. Prove Mac → Apollo, then Mac → Athena. Outbound dispatch does not require the Mac to host a gateway.
4. **Make the Mac a target and add both inbound directions.** Install the managed LaunchAgent with explicit bridge/PATH, configure private Serve, and check cross-host HTTPS. Register the required projects and verify their revision handling. Issue separate fresh Mac bootstraps for Athena and Apollo; both controllers may call the target `mac`.
5. **Accept all six directions with a small evidence matrix.** On every controller, both peers must pass authenticated status. Each edge must launch on the intended hostname, project, and revision; settle; appear correctly in Agents; and expose fresh output. Exercise exact-instance stop, dismissal/history and gateway restart recovery for every target without disturbing unrelated work. Test Mac sleep/wake explicitly: bounded unavailable/stale state while asleep, responsive Linux views, and recovery without duplicate execution or local fallback.

A target-readiness doctor check would make this easier to maintain and is worth adding. A new `sase machine serve --install` command is optional convenience, not a prerequisite for three machines: declarative Linux units and a Mac LaunchAgent can supply reproducibility now. The recommended endpoint is two persistent Linux targets plus a best-effort Mac target, each controller holding its own two enrollments, with correctness proven before routine cross-machine coding work.

