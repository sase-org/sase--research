# MacBook → Apollo/Athena remote dispatch

Research date: 2026-09-19

## Current state

Most infrastructure is already ready. Read-only live checks confirmed that the Mac,
Apollo, and Athena run the same SASE (`0.17.1+897.g5d158ad65`) and core (`0.34.57`)
versions; both Linux gateways are supervised and healthy on `127.0.0.1:7629`; both
Tailscale Serve endpoints answer from the Mac; and discovery classifies Apollo and
Athena as protocol-v1 compatible. The Mac currently has no enrolled machines.

One issue should be fixed before enrollment: both gateway units omit an explicit agent
bridge. Athena's systemd PATH happens to contain `~/.local/bin`; Apollo's does not, so
Apollo can answer health/enrollment requests but a launch can fail with
`agent_bridge` unavailable.

## Steps

1. **Make the agent bridge explicit on both targets.** On Apollo and Athena, persist
   this systemd override (preferably through chezmoi) with
   `systemctl --user edit sase-gateway.service`:

   ```ini
   [Service]
   ExecStart=
   ExecStart=%h/.local/share/uv/tools/sase/bin/sase_gateway --bind 127.0.0.1:7629 --sase-home %h/.sase --agent-bridge-command %h/.local/bin/sase
   ```

   Then reload, restart, and verify on each target:

   ```bash
   systemctl --user daemon-reload
   systemctl --user restart sase-gateway.service
   systemctl --user status sase-gateway.service --no-pager
   curl -fsS http://127.0.0.1:7629/api/v1/health
   tailscale serve status
   ```

   Keep the gateway loopback-only and use Tailscale Serve, not Funnel. The existing
   Serve routes are already correct:
   `https://apollo.tail297af1.ts.net` and
   `https://athena.tail297af1.ts.net` proxy to port 7629.

2. **Enroll both machines from a normal Mac terminal.** Enrollment credentials are
   controller-local, so run this on the Mac. The pipe keeps each short-lived,
   single-use bootstrap secret out of argv, logs, and temporary files. Direct `add` is
   used because the aliases and live endpoints are already known and verified.

   ```zsh
   set -o pipefail
   for target in apollo athena; do
     ssh "$target" '$HOME/.local/bin/sase machine bootstrap --json' |
       sase machine add "$target" \
         -c "builtin@tailnet|https://${target}.tail297af1.ts.net" \
         -S "$target"
   done
   ```

   Each successful `add` stores the credential in the Mac's protected SASE state,
   writes/applies its machine record, reloads configuration, and requires an
   authenticated hello. If an add partially succeeds, follow its recovery message;
   issue a fresh bootstrap and use `sase machine repair TARGET` if credential rotation
   is requested. Never reuse a bootstrap.

3. **Verify the controller after enrollment.** On the Mac:

   ```bash
   sase machine list
   sase machine status apollo athena
   sase doctor -D -C dispatch
   ```

   Both status rows should be healthy and non-quarantined. `sase machine discover -j`
   is an optional independent check. If it says the Tailscale CLI is missing, ensure
   `/usr/local/bin` is on PATH; the Mac's CLI is currently installed there. This does
   not affect the direct enrollment commands above.

4. **Smoke-test real dispatch from a clean, published checkout on the Mac.** Use a
   project known to all three SASE installations (the `sase` project already is), with
   a clean worktree, a configured upstream, and `HEAD` pushed:

   ```bash
   git status --short
   git rev-list --count '@{upstream}..HEAD'  # must print 0
   sase run "%dispatch:apollo report hostname and SASE version; do not change files"
   sase run "%dispatch:athena report hostname and SASE version; do not change files"
   ```

   Also confirm each target has its own working LLM credentials and repository access;
   those are not copied from the Mac by enrollment.

5. **Use `%dispatch` normally.** The equivalent syntax is `%dispatch(apollo)`. In the
   TUI, choose a target with `gD` in prompt NORMAL mode or `Ctrl+G D` in INSERT mode.
   Current V1 constraints: exactly one target; omit the directive for local execution;
   do not combine it with `%wait`, `%queue`, `%clan`, or `%hold`; and do not attach
   local-only files/images/collected inputs. Ordinary CLI dispatch also requires the
   clean, upstream-published Git state checked above.

## Basis

Validated against SASE commit `5d158ad65ba99293e4cad22d013abbc0e064ad76`, especially
`docs/remote_dispatch.md`, `docs/xprompt.md`, current `sase machine` help, and read-only
live probes of all three machines. No enrollment credentials were issued and no machine
configuration or services were changed during this research.
