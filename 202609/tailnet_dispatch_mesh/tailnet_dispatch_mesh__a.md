# Full-mesh remote dispatch across Athena, Apollo, and Mac

**Date:** 2026-09-11  
**Researcher:** A (`research.1v.cdx`)  
**Scope:** Independent assessment of what remains before each of `athena`, `apollo`,
and `mac` can use SASE's `%dispatch:<alias>` to launch an agent on either of the other
two machines.

## Executive conclusion

The network and service foundation is nearly ready for the two Linux machines, but the
fleet is not yet a three-machine mesh. There are six directed controller-to-target
relationships. Only **Athena → Apollo** is enrolled today. It has a healthy authenticated
hello, but the parent `sase-xe` epic still does not regard the end-to-end launch and
management proof as complete.

**Apollo → Athena is the next inexpensive edge.** Apollo already discovers Athena as a
compatible tailnet target, can reach Athena's HTTPS gateway, and can SSH to Athena. It
still needs its own Athena enrollment. Before enrolling it, Athena's persistent gateway
unit should be brought to the same launch-capable form as Apollo's: Athena's live unit
omits `--agent-bridge-command`, while Apollo's includes the absolute installed `sase`
path that was added after a real `agent_bridge` failure.

The Mac is the large unknown and the critical path for the other four relationships.
It was offline throughout this investigation, consistent with the tailnet memory's
warning that the Mac is unavailable unless powered on with its lid open. Its SASE
install, AXE state, machine identity, SSH configuration, gateway LaunchAgent, Tailscale
Serve endpoint, project availability, and controller enrollments therefore remain
unverified.

There is also a fleet-wide version-coherence gate. Athena and Apollo both report the
same installed SASE (`0.17.1+446.g8e3790c58`) and `sase-core-rs 0.34.7`, but both live
gateway health endpoints advertise gateway version `0.34.2`. The active closeout epic
`sase-xe.16.11.7.14.6.7` still includes publication/install and live-acceptance phases.
Additional enrollment should follow adoption of that repaired release rather than
expanding a known mixed runtime.

## Sources and method

I used the following independently, without consulting the other report in the current
research swarm:

- Audited SASE memory reads for tailnet conventions, beads, artifacts, and xprompt
  directives.
- Audited artifact reads of `plan:202609/remote_dispatch_fleet.md`,
  `plan:202609/launch_recovery_and_xe_closeout.md`, and the earlier consolidated
  `research:202609/agents_across_machines/agents_across_machines.md`.
- Current bead records for `sase-xe`, its live-proof descendants, the persistent-gateway
  epic `sase-yt`, and the active closeout child.
- The current `docs/remote_dispatch.md` runbook and relevant implementation references
  in the SASE checkout at `875447e2142f71dc04daeb49eab72c655c343be7`.
- Read-only live checks from Athena and Apollo on 2026-09-11: SASE/core versions,
  machine list/status/discovery, deep dispatch doctor, AXE status, Tailscale peer and
  Serve status, gateway unit definitions, local/cross-tailnet health, SSH alias
  expansion, and an Apollo → Athena SSH probe.

No bootstrap was issued, no enrollment or remote launch was attempted, no service was
restarted, and no credential material was read. Mac SSH timed out. The canonical
chezmoi repository could not be inspected because `sase repo open` currently resolved
this numbered checkout as the ad-hoc `gh_sase-org__sase` project and offered only the
primary repo, despite `sase repo list` inventorying the research sidecar and chezmoi
link. Live rendered config and service units were inspected instead; canonical desired
state should be checked when applying the recommendation.

## What the feature requires

Remote dispatch is directional. A target must expose one authenticated fleet gateway;
each controller must then hold its own enrollment record and credential for that target.
Tailnet membership and SSH access are useful setup transport, but neither is SASE
authorization.

For a machine to be a **target**, it needs:

1. A current compatible SASE install containing `sase`, `sase_gateway`, and
   `sase_federation_worker`.
2. A persistent gateway owned by the same OS user/SASE home that issues bootstraps,
   loopback-bound on `127.0.0.1:7629`, with an executable absolute agent-bridge command.
3. Tailscale Serve, tailnet-only HTTPS, proxying the node's MagicDNS name to the
   loopback gateway. Funnel is not appropriate.
4. A fresh one-time bootstrap for every controller enrollment.
5. The requested project/revision and target-side provider, model, plugin, finalizer,
   and runner prerequisites.

For a machine to be a **controller**, it needs:

1. Current SASE and a healthy AXE/runtime.
2. A local `dispatch.machines.<alias>` record plus protected credential for each target,
   created through canonical `sase machine init` or `sase machine add` activation.
3. A clean, upstreamed, published source revision, or trusted structured Patch/revision
   evidence. Ordinary remote launch rejects dirty/unpublished source and machine-local
   attachments. V1 also rejects `%dispatch` combined with `%wait`, `%queue`, or `%clan`.

These requirements imply three target deployments and six controller-local
enrollments. Credentials must not be copied from Athena or committed to chezmoi; every
missing edge should consume its own short-lived target-issued bootstrap.

## Live state by machine

| Machine | As a target | As a controller | Assessment |
| --- | --- | --- | --- |
| **Athena** | Persistent user-systemd gateway is enabled, active, loopback-only; Tailscale Serve proxies `https://athena.tail297af1.ts.net`; Apollo reaches health successfully. Live unit lacks explicit `--agent-bridge-command`. Gateway reports `0.34.2` while installed core is `0.34.7`. | AXE healthy. Exactly one machine is enrolled: Apollo. `sase machine status apollo` returns authenticated `hello ok`, protocol 1, not quarantined; deep dispatch doctor is OK. | Viewer path to Apollo exists. Target path needs bridge/release coherence before relying on launches from Apollo or Mac. |
| **Apollo** | Persistent user-systemd gateway is enabled, active, loopback-only; Serve proxies its MagicDNS HTTPS endpoint. Unit includes absolute `--agent-bridge-command`. Athena and Apollo both reach health. Gateway reports `0.34.2` while installed core is `0.34.7`. | AXE healthy, same installed SASE/core as Athena. Machine list is empty; doctor skips worker/live checks because no remotes are configured. Discovery sees Athena as compatible. | Strong target foundation and network-ready for becoming a controller, but no outbound edge is enrolled. |
| **Mac** | Offline; HTTPS discovery and SSH time out. Install, LaunchAgent, agent bridge, loopback health, Serve, and target project state are unknown. | Offline; SASE/AXE/config/project state unknown. | Four directed edges depend on an online Mac setup window. It cannot be an always-available target while asleep/offline. |

The two Linux machines also have symmetric SSH aliases for `athena`, `apollo`, and
`mac`; Apollo successfully SSHed to Athena using Athena's nonstandard port 34857. Mac's
own applied SSH configuration could not be checked. A transient Athena self-request to
its HTTPS Serve name produced a TLS internal error, but Apollo → Athena, Athena → Apollo,
and Apollo → Apollo HTTPS health all succeeded. Because the required cross-host path is
healthy, the self/hairpin result is diagnostic rather than a current dispatch blocker.

## Directed-edge matrix

| Controller → target | Current evidence | Remaining work |
| --- | --- | --- |
| **Athena → Apollo** | Enrolled, authenticated hello OK, protocol/capabilities advertised, deep doctor OK. Earlier epic notes proved discovery/Serve/init but repeatedly left receipt, fresh visibility, output/stop, dismissal/history, and restart acceptance incomplete. | Adopt the repaired released cohort and finish the currently assigned `sase-xe` live acceptance. This is close, but should not yet be called fully accepted. |
| **Apollo → Athena** | Apollo discovers Athena as compatible; cross-tailnet HTTPS and SSH both work. Apollo has no enrolled machines. | Fix or explicitly verify Athena's agent bridge; deploy/restart matching released gateway; issue a fresh Athena bootstrap; enroll alias `athena` from Apollo; run status/doctor and a remote launch proof. |
| **Athena → Mac** | Athena discovers the offline Mac only as unknown/unreachable; no Mac enrollment exists. | Prepare the Mac as a target, issue a Mac bootstrap for Athena, enroll alias `mac`, and verify while the Mac is awake. |
| **Apollo → Mac** | Apollo likewise sees the offline Mac as unknown/unreachable and has no enrollment. | After the same Mac target preparation, issue a separate Mac bootstrap for Apollo and enroll alias `mac`. Do not reuse Athena's token/credential. |
| **Mac → Athena** | Athena's target endpoint is reachable from another tailnet node, but Mac controller state is unknown. | Bring Mac online; update SASE/start AXE; verify its tailnet/SSH config; after Athena's bridge/release repair, issue a fresh Athena bootstrap and enroll alias `athena` from Mac. |
| **Mac → Apollo** | Apollo is the best-prepared target, but Mac controller state is unknown. | Bring Mac online; update SASE/start AXE; issue a fresh Apollo bootstrap; enroll alias `apollo` from Mac; validate project/source compatibility and launch. |

## Product work versus deployment work

The original feature implementation is broad, but its live acceptance is still open.
The newest closeout plan records a concrete failure in agent-origin approval launches:
an approved prompt retained `%dispatch:apollo` as text but lost the per-unit workspace
target and went through a local launcher, creating the proof agent locally. It also lost
the durable continuation back to the requesting worker. The plan assigns repairs for
workspace/remote targeting, requester continuation, inherited operation context,
explicit-name handling, release adoption, stale-row/dismissal proof, and a combined
acceptance matrix. The targeting and continuation phases have landed, while release and
live-proof work was still active during this research.

That defect does not prove every direct `sase run "%dispatch:..."` call is broken; the
incident specifically traversed approval/admission. It does prove that health plus
enrollment is not an adequate completion claim and that expanding to all six directions
before the current closeout lands would multiply a runtime that has not passed its own
acceptance gate.

Most remaining fleet work is nevertheless operational rather than a new architecture:

- finish and install the current repair cohort;
- make all three gateway services launch-capable and version-coherent;
- perform five additional directional enrollments;
- establish target-side project/tool parity, especially on Mac;
- execute a bounded six-direction acceptance matrix.

No new transport provider, transitive federation, credential sharing, automatic
placement, or cross-host `%wait` is needed.

## Acceptance criteria for the complete mesh

Before declaring the goal complete:

1. On each machine, `sase version` shows the intended released host/core cohort; the
   running gateway health/build matches it; AXE is healthy.
2. Each target has a persistent loopback gateway, explicit executable agent bridge,
   tailnet-only Serve config, stable installation identity, and cross-host HTTPS health.
3. `sase machine list -j` on every controller contains exactly the other two aliases;
   both `sase machine status` calls report authenticated protocol-1 hello without
   quarantine; `sase doctor -D -C dispatch` passes.
4. From a clean published test project, run one harmless xsmall observation launch for
   each of the six directed edges. Each must report the target hostname/project and
   produce an authoritative receipt/locator with no local fallback.
5. For each target, prove fresh visibility and nonempty output from another controller,
   then exact-instance stop or normal completion without affecting unrelated work.
6. Restart each target's managed gateway once. Enrollment identity and credentials must
   survive, and controller status/visibility must recover in the same session.
7. Repeat the Mac checks after a sleep/offline/reconnect cycle. The correct behavior is
   explicit unavailable/stale state while offline and recovery after wake—not silent
   local launch or fallback.
8. Verify project availability and the source preflight from every controller. Include
   one deliberate dirty-source refusal to prove the prompt is preserved and nothing is
   submitted.

## Recommended solution

Use a staged, explicit full mesh rather than trying to synchronize one machine's
dispatch state everywhere.

1. **Finish the active `sase-xe` closeout first.** Wait for the targeting/continuation
   fixes to be published and for the release-install/live-proof phases to complete.
   Update Athena and Apollo through the supported managed-update path, restart AXE and
   gateways, and require running gateway versions to match the adopted release.
2. **Make the Linux target services identical and launch-capable.** Add the absolute
   installed `sase` agent-bridge command to Athena's canonical chezmoi-managed gateway
   unit, preserve loopback bind and Serve, apply it, and confirm Apollo can launch on
   Athena. Re-audit the canonical unit source because this investigation could inspect
   only the live rendered units.
3. **Establish Apollo → Athena as the second edge.** Issue one fresh Athena bootstrap,
   transfer it over the protected SSH path, run canonical init/add on Apollo, delete both
   temporary copies, and complete status/doctor/launch/output/stop/restart checks.
4. **Schedule one Mac-online setup session.** Install/update SASE, confirm
   `id.machine_name: mac`, start/restart AXE, install a persistent same-user LaunchAgent
   for the loopback gateway **including the absolute agent bridge**, enable Tailscale
   Serve (not Funnel), and validate cross-host health. Ensure the canonical tailnet SSH
   aliases and required projects/plugins/models exist on the Mac.
5. **Create the four Mac-related enrollments with four fresh bootstraps:** Mac→Athena,
   Mac→Apollo, Athena→Mac, and Apollo→Mac. Use stable local aliases `athena`, `apollo`,
   and `mac`; never copy credentials or put secrets in YAML/git.
6. **Run the six-edge matrix above and record one requirement-to-evidence table.** Treat
   the Mac as best-effort while asleep. If “dispatch to Mac at any time” is a hard
   requirement, remote dispatch alone cannot satisfy it; change the Mac's power/sleep
   policy or use an always-on target.

This sequence reuses the working Athena→Apollo foundation, proves the cheap reverse
Linux path before introducing macOS variables, and leaves each controller with two
independent, repairable enrollments—the topology SASE's authorization and recovery
model is designed to support.
