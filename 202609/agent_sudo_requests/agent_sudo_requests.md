# Agent-Requested `sudo`: Consolidated Research and Recommendation

**Date:** 2026-09-14 · **Author:** lead researcher (consolidating
[`agent_sudo_requests__a.md`](agent_sudo_requests__a.md) and
[`agent_sudo_requests__b.md`](agent_sudo_requests__b.md) plus independent verification)
· **Question:** how should agents request that Bryan type a password so one or more
`sudo` commands can run — with good UX, safe password handling, and a clean agent-facing
contract?

---

## 1. TL;DR — the recommendation

Build a **typed `sudo` gate kind** with a `sase sudo request` front door and a generated
`/sase_sudo` skill. The agent submits a structured batch of argv commands plus a reason,
its turn ends through a gate-shell handoff, and a follow-up agent later receives
structured per-command results. Bryan reviews the exact commands in an ACE modal (or
`sase sudo answer <id>` in a terminal) and presses **Approve & run**.

For authentication, take researcher A's mechanism, not researcher B's: **ACE suspends
its TUI and hands the real terminal directly to `sudo`/PAM**. SASE never renders a
password field, and the password never exists in any SASE process, pipe, widget, file,
digest, or log — there is nothing to redact because nothing is collected. For execution,
take researcher B's mechanism, not researcher A's: an **unprivileged, non-dumpable Rust
runner in sase-core** that invokes `/usr/bin/sudo` per command (`sudo -v` on the TTY,
then `sudo -n` per command, then `sudo -k`), so sudoers evaluates the real commands and
no root-owned binary has to be installed.

Telegram and mobile can display and deny a request but never collect a password.
Independent of the design choice, the existing `secret: true` gate-input path has
concrete leak defects (verified below) that should be fixed regardless, and once the
feature ships, athena's blanket `NOPASSWD: ALL` should be narrowed so the reviewed
approval becomes a real privilege boundary instead of a courtesy.

---

## 2. Ground truth (independently verified 2026-09-14)

I re-ran researcher B's fleet checks and confirmed every load-bearing fact:

| Fact | Evidence | Consequence |
| --- | --- | --- |
| Agents have no TTY | `tty` → `not a tty` | `sudo` can never prompt inside an agent; authentication must happen on a human-attached surface. |
| athena: `(ALL : ALL) NOPASSWD: ALL` for `bryan`, Defaults `mail_badpass` | `/usr/bin/sudo -n -l` | On athena the feature is initially advisory — any agent can already run root commands silently. The feature is what makes tightening possible. |
| apollo: password required | `ssh apollo /usr/bin/sudo -n -l` → `sudo: a password is required` | The real, current need. |
| sudo 1.9.16p2 on athena | `sudo --version` | Modern flags available (`-S`, `-A`, `-k`, `-n`, `-v`, `-D`, `-p`). |
| zsh aliases `sudo` to `sudo -E` | `type sudo` | Any runner must call `/usr/bin/sudo` by absolute path with `env_reset`; `-E` would leak `LD_*`/`PATH` hazards into root. |
| `kernel.yama.ptrace_scope=0` | `/proc/sys/kernel/yama/ptrace_scope` | Any same-UID process (including a malicious agent) can read another `bryan` process's memory unless it is non-dumpable. This is the decisive fact for the authentication-channel choice (§4). |
| `sudo -k <command>` ignores and does not update the credential cache | local `sudo(8)` man page | A's central primitive is real. Also verified: timestamp records are per-TTY by default, falling back to parent-PID when no terminal is present. |

Also verified in SASE source at `8ed00c4ed6`: the `sase questions` front door
(validate → write pending-handoff marker → SIGTERM the runner group,
`src/sase/main/questions_command_handler.py:45-86`) is the exact precedent for
`sase sudo request`, and ACE already uses `app.suspend()` terminal handoff in a dozen-plus
places, so A's suspend-and-hand-to-sudo flow needs no new machinery.

---

## 3. Where the researchers agree (adopt all of it)

Both reports independently converge on the same core, and I found no reason to dissent:

1. **The abstraction is "request a privileged execution," never "ask for a password."**
   The agent-facing schema has no password or secret field at all. The credential never
   enters an LLM context, chat, gate input, journal, digest, log, clipboard, argv,
   environment, or notification transport — and neither does its length, attempt count,
   or any derivative.
2. **A typed gate kind with its own front door**, following `sase questions`: the agent
   calls `sase sudo request` (JSON on stdin preferred), the CLI validates loudly while
   the agent is still running, writes the bundle, and ends the turn via handoff. This
   respects the `single-turn-agents` and `gates-never-block` decisions. Blocking designs
   (askpass helpers the agent invokes, MCP sudo servers, provider-native approval hooks)
   were considered and rejected by both researchers for the same reason.
3. **Exact-command review is the security boundary.** Once an arbitrary command runs as
   root, no sandbox saves you; what matters is that Bryan approved these exact bytes on
   this exact host. Commands are argv arrays rendered verbatim, hash-bound between
   review and execution (reusing the existing bundle model — verified:
   `command_runner.py` re-hashes and execs `/proc/self/fd/N`). Scripts in agent-writable
   locations are refused or snapshotted into the bundle. Risk badges flag shell use,
   network, package managers, writes to system paths, and lock-out-prone service
   restarts (sshd/tailscaled on a remote host).
4. **One review, N commands, batch semantics:** stop on first failure by default, a
   per-command ledger (`ran`/`failed`/`skipped`), and resume-at-command-N (after fresh
   review) rather than automatic re-runs of completed commands.
5. **The generic `secret: true` custom gate is the wrong front door**, both because
   agent-authored root scripts are unauditable and because the substrate currently
   leaks (§6).
6. **No standing privilege.** Never `timestamp_type=global`, no "remember for 15
   minutes" cache, no `sudo -v` warm-up that leaves an ambient credential, and no
   `sudo -K` cleanup (it nukes every session's cache). Repeated needs graduate to
   explicit, narrow sudoers rules through a separate reviewed flow, not a warm
   credential.
7. **Remote surfaces are display-and-deny only.** Telegram already refuses secret
   inputs; mobile should mirror that. The password (when one is typed at all) is
   entered only on the executing host: ACE (including over `ssh`/tmux) or
   `ssh -t <host> sase sudo answer <id>`.
8. **Follow-up contract:** the successor agent gets a typed, fenced, untrusted result
   block — outcome, per-command exit codes, bounded output tails per the reviewed
   `output_to_agent` policy (`none|tail|full`, default `tail`) — never the
   authentication transcript.
9. **UI language:** say **Authenticate**, not "Enter your password" — sudo/PAM may be
   configured for OTP, U2F, or challenge-response, and `NOPASSWD` hosts legitimately
   show no prompt. SASE relays or delegates the real sudo conversation; it never
   verifies a password itself.

---

## 4. The two disagreements, resolved

### 4.1 Authentication channel: terminal handoff (A) vs. in-ACE masked field (B)

- **A:** after Approve & run, ACE suspends and the terminal is handed directly to
  `sudo`; PAM owns the conversation. The password never exists in any SASE process.
- **B:** a masked field inside the ACE modal; the password travels widget memory →
  anonymous pipe → hardened Rust runner → `sudo -S -p ''`. Better inline UX (retry
  without leaving the modal), at the cost of the password transiting SASE memory.

**Resolution: A's terminal handoff.** Three reasons:

1. **Python cannot be hardened.** B's own §3.3/§5.5 shows the required cleanup: block
   yank/registers/OSC-52, clear undo history, audit key-event logging — and even then
   the password sits in immutable Python strings inside ACE, which cannot be zeroized,
   while `ptrace_scope=0` means any same-UID agent can read ACE's memory. B hardens the
   Rust runner (`PR_SET_DUMPABLE`, `mlock`, zeroize) but the ACE side stays soft. A's
   design has no soft side: the only processes that ever hold the password are the
   terminal driver and setuid `sudo` itself (already non-dumpable).
2. **PAM generality.** `sudo -S -p ''` assumes exactly one hidden string. The TTY
   handoff supports whatever PAM does — retries, OTP, a second factor — with zero SASE
   code, and NIST SP 800-63B-friendly behavior (paste from a password manager works;
   sudo owns retry policy).
3. **The UX cost is small and familiar.** ACE already `app.suspend()`s for editors and
   external tools constantly; the flow is a sub-second flip to a host-authored banner
   plus the genuine `[sudo] password for bryan:` prompt, then back to ACE with results.
   The genuine prompt is also anti-spoofing: an agent-authored gate command runs
   detached without the TTY and cannot imitate this trusted path. Wrong password is
   handled by sudo's own `passwd_tries`; if all tries fail, the gate simply stays
   pending and is reopened — roughly the same friction as B's "3 inline attempts, then
   reopen."

The terminal-answer path becomes trivially consistent: `sase sudo answer <id>` shows the
review, then just runs sudo attached to `/dev/tty` — no `getpass`, no password
collection code anywhere in SASE, on any surface.

### 4.2 Execution vehicle: root-owned runner (A) vs. unprivileged per-command runner (B)

- **A:** one `sudo -k -- /usr/local/libexec/sase-privileged-runner` invocation executes
  the whole manifest as root. Elegant property: one prompt, zero timestamp footprint.
  Costs: a root-owned binary must be installed on every host; sudoers authorizes only
  the runner, not the real commands (a policy bypass A itself flags); and it forecloses
  B's best long-term idea — promoting repeated approvals into narrow per-command
  sudoers rules.
- **B:** an unprivileged, non-dumpable Rust runner calls `/usr/bin/sudo` per command.
  sudoers evaluates each real command; nothing needs root installation; works on a
  fresh host immediately.

**Resolution: B's unprivileged runner,** adapted to the TTY handoff. On Approve & run,
ACE suspends and spawns the runner attached to the terminal. The runner:

1. runs `/usr/bin/sudo -v` — sudo/PAM converses on the real TTY (on a `NOPASSWD` host
   this succeeds silently);
2. runs each approved command as
   `/usr/bin/sudo -n -u <run_as> -D <cwd> -- <argv…>` with stdin `/dev/null`, a clean
   environment (`env_reset`, reviewed allowlist only, reject `LD_*`/`SUDO_*`/`PATH`
   overrides), a process-group timeout, and streamed, bounded output;
3. runs `/usr/bin/sudo -k` and settles the gate with the per-command ledger.

The honest tradeoff versus A: between steps 1 and 3 a sudo timestamp record exists. It
is TTY-scoped (verified default), keyed to ACE's pts and session — agents have no TTY
and cannot adopt ACE's — and it lives only for the batch duration before `-k` drops it.
That bounded, session-confined window is a fair price for keeping sudoers pointed at
real commands and avoiding a permanently installed privileged TCB. Degradations are
graceful: if policy sets `timestamp_timeout=0`, the `-n` step fails and the runner falls
back to plain per-command `sudo` on the same TTY (N prompts, still safe); if `runcwd`
permission is missing, `-D` falls back to cwd `/` unless the reviewer approved a ⚠ cwd
badge. On macOS the same flow works unchanged — that is another advantage of TTY
authentication over B's `/proc`-dependent hardening.

Version-one exclusions (both reports agree): no interactive root programs (no stdin, no
`visudo`/`$EDITOR`/`-i` shells), no nested `sudo`/`su`/`pkexec`/askpass, shell strings
only behind an explicit `"shell": true` with a ⚠ badge and full program text shown.

---

## 5. Recommended UX

### Agent side

```bash
sase sudo request --json <<'EOF'
{
  "reason": "Apply the tailscale security update on apollo",
  "commands": [
    { "id": "update",  "argv": ["apt-get", "update"], "why": "refresh package index" },
    { "id": "upgrade", "argv": ["apt-get", "install", "-y", "--only-upgrade", "tailscale"],
      "why": "install the patched package", "timeout_seconds": 600 }
  ],
  "run_as": "root", "cwd": "/", "stop_on_failure": true, "output_to_agent": "tail",
  "next": { "prompt": "Confirm tailscale version and continue the upgrade plan." }
}
EOF
```

The `/sase_sudo` skill (generated from `src/sase/xprompts/skills/`, per the
`generated_skills` memory) teaches: never ask for a password anywhere; never run raw
`sudo`; do all non-root prep first and batch every root step into one request with a
one-line `why` per command; prefer non-root alternatives and justify why root is
unavoidable; set `output_to_agent: "none"` when a command's output must not reach the
model. A provider `PreToolUse` deny on raw `sudo` in agent Bash calls (mirroring the
existing plan-mode denials) redirects well-behaved agents to `/sase_sudo` — guidance,
not a boundary.

### Human side

Notification everywhere (toast, 🔐 panel, Telegram, mobile):
"🔐 research.1w.cld requests root on **apollo** (2 commands)". Remote surfaces offer
**Deny** and **Show commands** plus the `sase sudo answer <id>` hint; only ACE and a TTY
can run it.

ACE review modal: checklist of commands (all selected, Space toggles), verified facts
(host, run-as, cwd, env policy, requesting agent/project, expiry), the agent's reason
labeled as untrusted, risk badges, `v` for full argv/env/snapshot details, `d` for deny
with feedback. Primary action: **Approve & run** (explicit activation — approval is
required even on `NOPASSWD` hosts, so the experience is identical fleet-wide and
tightening athena later changes nothing for Bryan except one extra prompt).

On Approve & run, ACE suspends:

```text
SASE sudo request 7f3c on apollo — 2 commands as root (Ctrl-C cancels)
Handing the terminal to sudo/PAM…
[sudo] password for bryan:
✓ 1 update  (12.4s)
✓ 2 upgrade (31.0s)
```

…then ACE restores with a completion toast ("2/2 root commands succeeded on apollo"),
the family status flows `SUDO` → `SUDOED`, and the successor agent launches with the
structured ledger. A wrong password (after sudo's own retries) or Ctrl-C leaves the gate
pending with "nothing was run"; authentication failure is reported as an authentication
outcome, never as a command failure, and is never auto-retried. Only one authentication
handoff may be active at a time. Custom gates whose text mentions a sudo/root password
get a standing warning banner: "Never enter your system password here."

---

## 6. Fix the generic secret-input substrate regardless

Researcher B's code-level findings, which I independently verified at `8ed00c4ed6`
(items 1–4; item 5 is B's report, not re-verified):

1. **Detached gate answers write raw secrets to disk**: `_submit_detached_answer`
   copies `option_inputs` unredacted into the proc operation-request sidecar and echoes
   them raw in its return payload (`notification_gates/cli_answer.py:288-289,321`);
   shell-backed gates default to detached (`cli_answer.py:253-265`), and ACE's own
   answer proc adds further copies.
2. **The journal digest is crackable for passwords**: `value_digest` is unsalted
   `sha256(canonical_json(value))` (`notification_gates/journal.py:74-76`) — an offline
   dictionary oracle for any human password submitted through a secret field.
3. **The secret widget masks rendering only**: `SecretVimTextArea`'s own docstring
   confirms vim registers and the app clipboard hold the unmasked value, and ACE's
   clipboard path emits OSC 52.
4. **`run_owned_command` sends the full canonical input — secrets included — to the
   agent-authored command's stdin** (`notification_gates/command_runner.py:35-74`).
   Hash verification proves which command got the secret, not that it was trustworthy.
5. **The mobile gateway accepts `option_inputs` with no Telegram-style secret refusal**
   (B: `sase-core` `routes.rs:3040-3083`).

Fixes: redact secret fields from every sidecar and return payload (hand values to
detached procs via inherited fd if truly needed); exclude secrets from `value_digest`
(re-entry on retry); copy-out protection for secret widgets (paste-in stays allowed);
mobile refusal mirroring Telegram. These matter for ordinary API-token gates even though
the recommended sudo design bypasses `option_inputs` entirely. Filed as a task bead.

## 7. Host policy and rollout

- **Phase 0:** substrate leak fixes (§6) — small and independent.
- **Phase 1:** Rust runner in sase-core (per the `rust-core-required` boundary), the
  `sudo` gate kind with `sase sudo request/answer/list/show`, the ACE modal + terminal
  handoff, the `/sase_sudo` skill, the PreToolUse guard — behind a feature flag, dogfood
  on apollo (where the password prompt is real today).
- **Phase 2:** Telegram/mobile deny-only projections; allowlist promotion ("approve the
  same normalized argv N times → offer a reviewed narrow `NOPASSWD` sudoers rule,
  validated with `visudo -cf` and itself applied through `/sase_sudo`"); then tighten
  athena — replace `NOPASSWD: ALL` with password sudo plus narrow Cmnd_Aliases, and set
  `kernel.yama.ptrace_scope=1`. Until then the feature is honest advisory UX on athena
  and a real boundary on apollo.

Acceptance testing should prove **absence, not redaction**: a canary credential must
appear nowhere in bundles, responses, journals, logs, telemetry, argv, or environment —
and no hash or length of it either. Report A §"Suggested acceptance tests" has the full
14-case list; it applies nearly unchanged, minus the root-runner cases.

## 8. Answers to the open questions (from report B §6)

1. **NOPASSWD hosts still require explicit Approve & run** — yes; consistency, and it
   is the pre-tightening posture. Never auto-run.
2. **Default `output_to_agent`** — `tail` (bounded), with `none` available for
   secret-adjacent commands and `full` as an explicit reviewed choice.
3. **Answering only on the executing host is fine for v1.** Fleet-relayed password
   entry is out of scope; with the TTY-handoff design it would mean relaying a live PAM
   conversation, and `ssh -t apollo sase sudo answer <id>` already covers the need.
4. **Ship the PreToolUse raw-`sudo` guard with Phase 1** — but only alongside
   `/sase_sudo`, so athena agents don't silently lose a capability they rely on today.

## 9. Sources

The two source reports carry the full citation lists. Key primary sources:
local `sudo(8)`/`sudoers(5)` (1.9.16p2) verified on athena; upstream sudo manual at
`bb0d87c9` (`-k`/`-S`/`-A`/`timestamp_type` semantics); NIST SP 800-63B; MITRE CWE-214;
OWASP logging guidance; polkit and systemd password-agent architecture docs (report A);
community prior art on agent sudo flows — dgt.is global-timestamp hook, Ivan Morgillo's
pkexec approach, claude-code#18316 (report B). SASE source verified at commit
`8ed00c4ed6` as cited inline.
