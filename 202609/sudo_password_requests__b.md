# Agent-Requested `sudo`: Password Prompts for SASE Agents (Researcher B)

**Date:** 2026-09-14 · **Author:** research.1w.cld (researcher B) · **Scope:** UX, password
handling, and the agent-facing contract for letting a SASE agent ask Bryan to type a
password so one or more `sudo` commands can run.

---

## 0. TL;DR

- **Build a typed gate kind, `sudo`, with its own front door (`sase sudo request`) and a
  generated `/sase_sudo` skill.** It should work the way `sase questions` does. The agent
  describes the root commands it needs and why, then hands off, and its turn ends. Bryan
  reviews the exact commands, types the password once, and they run. A follow-up agent
  gets the per-command results. The agent never gets the password in any form.
- **For v1, typing the password only in ACE or in a terminal (`sase sudo answer <id>`) is
  both the good UX and the safe one.** The password is the approval: one masked field,
  and Enter runs the selected commands. There is no separate "Approve" step before it.
  A wrong password is reported inline and the gate stays open, and nothing runs until
  authentication succeeds. Telegram and mobile announce the request and offer **Deny**,
  but never collect the password. Telegram already refuses secret inputs.
- **Password path: masked widget memory → anonymous pipe → a short-lived, non-dumpable
  runner → `/usr/bin/sudo -S -p ''`.** It never goes into argv, env, sidecar files,
  `response.json`, journals, digests, logs, notifications, chat transcripts, prompts, or
  the clipboard. After the batch the runner calls `sudo -k` and wipes its copy. SASE
  keeps no password cache of its own, and `timestamp_type=global` must never be used.
- **Do not build this as a `sase_gate` custom gate with `secret: true` today.** I traced
  the code, and a detached gate-shell answer currently writes raw `option_inputs` to disk
  and echoes them into proc results and logs. The journal also stores an unsalted SHA-256
  of the input, which can be cracked for a human password. Details are in §3.3. These
  substrate leaks need fixing first, whichever design is chosen.
- **Ground truth on this fleet changes the stakes.**
  - On **athena**, `bryan` has `(ALL : ALL) NOPASSWD: ALL`, so every agent can already
    run any root command silently. Kernel `ptrace_scope` is `0`.
  - On **apollo**, sudo asks for a password (`sudo: a password is required`), so this
    feature is needed there today.
  - The feature is what makes it possible to tighten athena later.

---

## 1. Ground Truth (Observed, 2026-09-14)

| Fact                                     | Evidence                                                                                                                                           | Why it matters                                                                                                                                                        |
| ---------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Agents have no TTY                       | `tty` → `not a tty`; the agent's `claude` and `zsh` processes have TTY `?`                                                                          | `sudo` can never prompt interactively inside an agent. Something has to supply the password out of band.                                                              |
| athena: passwordless sudo for everything | `sudo -n -l` → `(ALL : ALL) NOPASSWD: ALL`, Defaults only `mail_badpass`                                                                           | On athena the feature is **advisory** until NOPASSWD is narrowed. Agents can bypass it with a plain `sudo`.                                                           |
| apollo: password required                | `ssh apollo sudo -n -l` → `sudo: a password is required` (Linux 6.8)                                                                               | Real, current need.                                                                                                                                                   |
| mac: best-effort host                    | tailnet memory note                                                                                                                                | macOS `sudo` supports `-S`/`-A`, but has no `/proc`, so hardening differs.                                                                                            |
| sudo 1.9.16p2 on athena                  | `sudo --version`                                                                                                                                   | Modern flags are available (`-S`, `-A`, `-k`, `-v`, `-n`, `-p`).                                                                                                    |
| `sudo` is aliased to `sudo -E` in zsh    | `type sudo` → `sudo is an alias for sudo -E`                                                                                                        | The runner must call `/usr/bin/sudo` by absolute path and **never** preserve the agent's environment. `-E` would pass `LD_PRELOAD`-style and `PATH` hazards into root. |
| Same-UID agents, `ptrace_scope=0`        | `/proc/sys/kernel/yama/ptrace_scope` → `0`                                                                                                         | Any `bryan` process, including an agent, can attach to any other `bryan` process (ACE, a runner) and read its memory unless that process is non-dumpable.            |
| SASE policy text                         | `src/sase/main/parser_agent_cli.py:42`, `src/sase/agent_clis/operations.py:345`: "SASE never uses sudo"                                            | The feature must stay **user-initiated and per-request**. SASE itself still never escalates on its own initiative.                                                    |
| Agents are single-turn; gates never block | decisions `single-turn-agents`, `gates-never-block`; `/sase_gate` and `/sase_questions` skills                                                     | An askpass or MCP design that blocks the agent while it waits for a human conflicts with core SASE decisions.                                                         |

sudo semantics that the design depends on:

- `-S` writes the prompt to stderr and reads the password from **stdin**. Any remaining
  stdin goes to the command.
- `-A` runs a helper (`SUDO_ASKPASS`) that prints the password to stdout.
- `-n` never prompts.
- `-v` authenticates and refreshes the cache without running a command.
- `-k` invalidates the cached credentials for the current session. Used together with a
  command, it ignores the cache and does not update it.
- `timestamp_type` defaults to `tty`, and **"when no terminal is present, the ppid type is
  used"**. A no-TTY runner therefore gets a credential record scoped to its own PID, and
  that record is shared only by sudo children of the same parent.
- `global` makes one record for every session of the user, which for us means every
  agent.

---

## 2. What "Good" Means Here

### 2.1 UX principles

1. **Legible authority.** Before root does anything, Bryan sees the exact commands, in
   order. He also sees the run-as user, cwd, the environment policy, the **host** (the
   fleet spans athena, apollo, and mac), which agent and project asked, and why. An
   approval prompt that shows only "research.1w.cld wants sudo" is security theater.
2. **One password, N commands.** The request is naturally a batch, such as "update
   packages, restart the service, check status". Show it as a checklist with every item
   selected by default and Space to toggle. Default to stop on the first failure.
3. **The password is the confirmation.** Typing the password and pressing Enter is a
   deliberate act. Asking him to approve and then also type the password is redundant
   friction. **Deny** is a peer action with optional or required feedback.
4. **Never block the agent; never lose the result.** The agent hands off, and a
   follow-up agent resumes with a structured outcome: ran, failed, skipped, denied, or
   timed out, plus exit codes and bounded output tails.
5. **Mistakes are cheap.** A mistyped password gives an inline error, clears the field,
   and keeps the gate pending. Nothing has run, because authentication happens before
   the first command.
6. **Answer from where you are, but type secrets only on trusted surfaces.** Seeing and
   denying a request should work everywhere: ACE, Telegram, mobile, CLI. Typing the
   password should work only where the input is local and masked: ACE, or a local
   terminal via `getpass`, including over `ssh -t`.
7. **Attention proportional to urgency.** Use the existing notification transport: toast,
   a `sudo` panel with 🔐, a Telegram ping, and family status `SUDO` → `SUDOED`. Show
   live output while commands run, and a completion toast.
8. **No standing privilege.** Do not offer "remember my password for 15 minutes". In a
   multi-agent world, a warm credential is root for *every* agent. Repeated needs should
   become an explicit, reviewable sudoers `NOPASSWD` rule for one specific command
   (§5.8), not a SASE-side cache.

### 2.2 Threat model and honest limits

| Adversary / failure                                                                       | Realistic?                                          | Control                                                                                                                                                                                                                                                                             |
| ----------------------------------------------------------------------------------------- | --------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Accidental durable leak**: files, logs, transcripts, agents-sync publishing, research repos, Telegram history, push payloads | **Most likely**                                     | Password lives only in memory and pipes. It is never a gate input value that gets persisted (§3.3). Output is scrubbed.                                                                                                                                                               |
| **Password in model context**: the agent asks for it in chat, or it is echoed into a prompt | Likely, if the contract is loose                     | The skill forbids asking for passwords. The `sudo` kind has no password field that the agent can read. Follow-up prompts carry results only.                                                                                                                                         |
| **Misleading request**: benign-looking command, hidden payload                             | Plausible (prompt injection)                         | Commands are argv arrays shown verbatim. Scripts are snapshotted and hash-verified. Risky patterns (`bash -c`, agent-writable paths, `tee`, `cp` into system dirs, editors) get badges. There is no `-E`.                                                                              |
| **TOCTOU**: agent edits `./install.sh` after review, before run                            | Plausible                                            | Workspace files are refused as executables unless snapshotted into the hash-verified bundle. The gate executor already re-hashes bundle commands and execs `/proc/self/fd/N` (`command_runner.py:44-100`).                                                                              |
| **Malicious same-UID process reads memory**                                                 | Possible with `ptrace_scope=0`                       | The runner calls `prctl(PR_SET_DUMPABLE, 0)` and `RLIMIT_CORE=0`. Recommend `kernel.yama.ptrace_scope=1` so an agent cannot attach to ACE. Note that ACE is not a descendant of the agent.                                                                                           |
| **Warm credential abuse**                                                                   | Real if a global timestamp is used                   | No global timestamp. The runner's `ppid`-scoped record dies with the runner and is explicitly `sudo -k`'d.                                                                                                                                                                             |
| **Shoulder surfing, clipboard**                                                             | Minor, but free to fix                               | Masked render already exists. Block yank, registers, and OSC 52 for secret fields (§3.3).                                                                                                                                                                                              |

**Limit to state honestly:** while athena grants `NOPASSWD: ALL` and agents run as
`bryan`, a determined malicious agent does not need the password. It can run `sudo` or
read files directly. So "the agent never sees the password" protects against **leakage
and reuse**; it is not a sandbox. The feature becomes a real privilege boundary only once
NOPASSWD is narrowed and `ptrace_scope` is raised.

---

## 3. What the Existing SASE Substrate Offers (and Where It Leaks)

### 3.1 Useful building blocks

- **Durable gates and gate shells.** Bundles live under
  `~/.sase/interaction_requests/<kind>/<id>/`. They carry hashed resources and argv-only
  commands, and input reaches a command as JSON on stdin (`command_runner.py:1-10`).
  Gate shells hand off, settle `completed`, `failed`, `timeout`, `stopped`, or `lost`,
  and compose a follow-up prompt from typed results.
- **Typed kinds with front doors** (plan, question, launch, task triage). `sase questions`
  writes a handoff marker and SIGTERMs the runner group
  (`src/sase/main/questions_command_handler.py:50-85`). That is the exact precedent for
  `sase sudo request`.
- **Secret-typed gate inputs.**
  - `GateInputField.secret` (`notification_gates/model_inputs.py:106-134`).
  - ACE masks the field with `SecretVimTextArea`
    (`ace/tui/widgets/secret_vim_text_area.py`), wired through `typed_input_form.py:285`.
  - `response.json` redacts it and results are scrubbed
    (`notification_gates/executor_inputs.py:64-176`).
- **Telegram refuses secret inputs** with "Telegram cannot collect secret input: …"
  (`sase-telegram: src/sase_telegram/gate_inputs.py:59`, `scripts/sase_tg_inbound.py:1517`).
  That is the right precedent.
- **Live output streaming.** `run_owned_command(on_output_line=…)` provides it for the
  executing phase.

### 3.2 Why a generic custom gate is the wrong front door for sudo

- **The agent writes the privileged script.** The reviewer must audit a shell script, not
  a command list, and shell hides intent (`$(...)`, heredocs, sourced files).
- **A wrong password settles the gate as `failed`.** That creates a retry maze instead of
  an inline "try again".
- **UX is inconsistent across agents.** Each agent invents titles, notes, timeouts, and
  output handling, and some will get stdin handling wrong. For example, `sudo -S` consumes
  one line, and the rest of the JSON stdin flows into the root command.
- **It inherits the leaks below.**

### 3.3 Concrete password-handling defects in today's secret-input path

These come from reading the code, not from a reproduction, and all are file-level.

1. **Detached answers write raw secrets to disk.**
   - A gate with a `shell` block defaults to a detached answer
     (`notification_gates/cli_answer.py:253-265`).
   - `_submit_detached_answer` copies `option_inputs` unredacted into the proc's
     operation-request sidecar (`cli_answer.py:284-313`). `submit_proc_request` writes
     that to `~/.sase/procs/runtime/<proc>/operation-request.json` (mode 0600,
     `ops/io.py:49`, `procs/runtime.py:225`).
   - Runtime dirs are retained until proc history pruning (`procs.history_limit: 100`,
     `default_config.yml:81-87`). There are 196 runtime dirs on athena right now.
2. **ACE's own answer proc duplicates the secret twice more.**
   - ACE submits `sase gate answer --json` **without** `--no-detach` and passes
     `option_inputs` in the request sidecar
     (`ace/tui/actions/agents/_notification_gate_execution.py:82-97`). That is copy #1.
   - For a shell-backed gate, that proc detaches again (copy #2 above).
   - Its return payload contains `"option_inputs": dict(option_inputs)` raw
     (`cli_answer.py:321`). `handle_gate_answer` writes it to `operation-result.json` via
     `RESULT_ENV` (`procs/service.py:418`) and prints it with `--json` into the proc's
     combined output log (`cli_answer.py:95-103`).
3. **The journal digest can be cracked.** `value_digest` is a plain
   `sha256(canonical_json(input))` (`notification_gates/journal.py:74-76`), recorded per
   option for retry matching. For a human password inside a small, known JSON shape, that
   hash is offline-crackable.
4. **The secret widget copies out.** `SecretVimTextArea` masks rendering only. Its own
   docstring says vim registers and the app clipboard hold the unmasked value, and ACE's
   clipboard path emits OSC 52 (`ace/tui/actions/clipboard/_delivery.py:54-69`), which
   reaches tmux and the system clipboard.
5. **The mobile gateway accepts `option_inputs` with no secret refusal.** See
   `sase-core: crates/sase_gateway/src/routes.rs:3040-3083`, which forwards to the host
   bridge subprocess at `host_bridge.rs:769`. I did not trace the mobile client, but the
   API gives no Telegram-style refusal.

**Implication:** fix (1)–(4) in the generic gate substrate, and decide (5), before any
`secret: true` gate is used for real credentials. The recommended `sudo` kind avoids
routing the password through `option_inputs` at all (§5.4), but these fixes are worth
doing regardless.

---

## 4. Options Considered

| #     | Approach                                                                                                                                          | Password safety                                                                                                                                                  | UX                                                                                                                                 | Fit with SASE                                                                                                                                                                                                                                 | Verdict                                                   |
| ----- | ------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------- |
| A     | Agent asks Bryan to run commands himself (`/sase_questions` or chat)                                                                              | Excellent: never touches SASE                                                                                                                                    | Poor: copy/paste, context switch, results must be pasted back, error-prone                                                         | Works today                                                                                                                                                                                                                                   | Keep only as a fallback                                   |
| B     | Custom `/sase_gate` with a `secret: true` input and a script that pipes it to `sudo -S`                                                            | **Currently leaks** (§3.3); agent-authored root scripts                                                                                                          | Inconsistent; wrong password = failed gate                                                                                         | Existing substrate                                                                                                                                                                                                                            | Reject as the front door; fix its leaks anyway            |
| C     | `SUDO_ASKPASS=sase-askpass` so agents run `sudo -A cmd` and the helper pops a SASE prompt and blocks                                               | The helper must print the password to sudo's pipe (fine), but the command runs inside the **agent's** process tree, where the agent controls stdin/stdout and timing | Feels transparent to agents and build scripts, but the prompt cannot show the command reliably, and sudo's `passwd_timeout` (5 min) races the human | **Blocks the agent turn** (conflicts with `single-turn-agents` and `gates-never-block`); the provider's tool timeout kills it                                                                                                                  | Reject (at most a fail-fast shim that points to `/sase_sudo`) |
| D     | pkexec/polkit native dialog (Ivan Morgillo's `asroot`)                                                                                             | Good                                                                                                                                                             | Great on desktops                                                                                                                  | athena and apollo are headless; `pkttyagent` needs a TTY; ACE-in-tmux is Bryan's surface                                                                                                                                                      | Reject                                                    |
| E     | Provider hooks: deny, poll, and Bryan runs `sudo -v` elsewhere with `timestamp_type=global` (dgt.is)                                               | Password never near the agent, **but** the global timestamp gives *every* process root for the timeout window                                                   | Two-terminal dance; the approval is not tied to specific commands                                                                  | Provider-specific; polling                                                                                                                                                                                                                    | Reject (the global timestamp is disqualifying with many agents) |
| F     | MCP `execute_command` server with password prompts (suddo, sudo-MCP)                                                                              | Varies                                                                                                                                                           | OK                                                                                                                                 | Provider-specific, blocking tool call, bypasses SASE gates and notifications                                                                                                                                                                  | Reject                                                    |
| G     | GUI dialog + `sudo -S` wrapper (Claude Code issue #18316; closed as not planned)                                                                   | Good if done carefully                                                                                                                                           | Desktop-only                                                                                                                       | Headless hosts; blocking                                                                                                                                                                                                                      | Reject                                                    |
| **H** | **Typed `sudo` gate kind + `sase sudo request` + `/sase_sudo` skill + dedicated non-dumpable runner**                                              | **Best achievable**: memory and pipe only, no durable input, no digest                                                                                           | **Best**: one reviewed batch, one password, inline retry, live output, follow-up agent                                             | Same shape as `sase questions` and plan gates; gate shell; Telegram/mobile/ACE projections; single-turn                                                                                                                                       | **Recommend**                                             |

Community prior art converges on one principle: keep the credential out of model context,
logs, and transcripts, and tie each elevation to explicit human approval. Option H
applies that principle using the durable gate machinery SASE already has.

---

## 5. Recommended Design

### 5.1 Agent contract: `/sase_sudo` skill + `sase sudo request`

Generate a new skill from `src/sase/xprompts/skills/sase_sudo.md`, following the pattern
in the `generated_skills` memory. The CLI shape:

```bash
sase sudo request \
  --reason 'Apply the tailscale security update on apollo' \
  --cmd 'apt-get update' \
  --cmd 'apt-get install -y --only-upgrade tailscale' \
  --next 'Confirm `tailscale version` is >= 1.90 and continue the upgrade plan.'
```

or a JSON request on stdin, which is preferable for anything non-trivial:

```json
{
  "reason": "Apply the tailscale security update on apollo",
  "commands": [
    { "id": "update", "argv": ["apt-get", "update"], "why": "refresh package index" },
    {
      "id": "upgrade",
      "argv": ["apt-get", "install", "-y", "--only-upgrade", "tailscale"],
      "why": "install the patched package",
      "timeout_seconds": 600
    }
  ],
  "run_as": "root",
  "cwd": "/",
  "stop_on_failure": true,
  "output_to_agent": "tail",
  "next": { "prompt": "Confirm tailscale version and continue.", "model": null }
}
```

Validation and normalization, done at creation so a bad request fails loudly while the
agent is still running:

- **argv arrays by default.** `--cmd` strings are split with `shlex`, and the split form
  is shown to the reviewer. Shell strings need an explicit `"shell": true`, which renders
  a ⚠ `shell` badge and runs `/bin/sh -c` under sudo.
- **Reject** a leading `sudo`/`doas`/`su`/`pkexec` (strip it with a note), plus
  interactive or TTY-bound commands: `visudo`, `$EDITOR`, `-i`/`-s` shells, `passwd`,
  bare `bash`.
- **Executables or scripts that live in agent-writable locations** (the workspace,
  `$SASE_TMPDIR`, `/tmp`) are either refused or **snapshotted into the bundle**
  (`"snapshot": true`), hash-verified, and exec'd from the verified descriptor. This
  reuses `command_runner.py`'s model.
- **Risk badges:** writes into `/etc`, `/usr`, `/boot`, `~root`; `rm -r`; `chmod`/`chown -R`;
  `curl|sh`; `dd`; `tee`; `systemctl` on sshd/tailscaled (lock-out risk on a remote
  host); package managers (network plus maintainer scripts).
- **Never `sudo -E`.** Use sudo's `env_reset`. Allow an explicit `env` allowlist that is
  shown in review.
- **Bounds:** at most around 20 commands per request, each with a timeout, and a whole
  request timeout. The gate itself times out after 60 minutes by default and is
  configurable.

Behavior: `sase sudo request` builds a typed `sudo` bundle with a `shell` block. It uses
a handoff marker, like `sase questions`. The family shows `SUDO` while pending and
`SUDOED` once settled, and the agent's turn ends.

Skill rules for agents, stated bluntly:

- Never ask the user for a password in chat, questions, or gates, and never read,
  store, or pipe one.
- Never run raw `sudo`. Use `/sase_sudo`.
- Do all non-root prep first, then batch every root step into **one** request, with a
  one-line `why` for each command.
- Prefer non-root alternatives (`systemctl --user`, user-owned installs) and say why root
  is unavoidable.
- If a command's output must not return to the agent (for example, reading a secret
  file), set `output_to_agent: "none"`.

**Guardrail hook.** Add a provider `PreToolUse` deny for Bash commands whose argv invokes
`sudo` when `$SASE_AGENT` is set. This mirrors the existing plan-mode and AskUserQuestion
denials in `~/.claude/settings.json`, with the reason "Use /sase_sudo". Codex and other
providers get equivalents. This is guidance for well-behaved agents, not a security
boundary (§2.2).

### 5.2 Follow-up contract (what the next agent gets)

This is a typed, fenced, untrusted result section, the same shape gate shells already
compose:

```text
sudo request <id> on apollo — outcome: completed (2/2 ran)
- update   argv=[apt-get, update]                         exit=0  12.4s  stdout(tail 20 lines)…
- upgrade  argv=[apt-get, install, -y, --only-upgrade, …]  exit=0  31.0s  stdout(tail 20 lines)…
reviewer note: (none)
```

Outcomes:

- **`completed`**: all selected commands succeeded.
- **`failed`**: `ran`/`failed`/`skipped` per command.
- **`denied`**: carries the reviewer's feedback, and optionally follows the `branches.deny`
  prompt.
- **`partial`**: the reviewer deselected some commands, which are listed as
  "not approved".
- **`timeout`** and **`stopped`**.

The password, and the fact of how many attempts it took, never appear.

### 5.3 Human UX

**ACE review modal**, opened from the toast or from the `sudo` 🔐 panel or gates panel:

```text
╭─ 🔐 Root access · apollo ─────────────────────────────────────────────╮
│ research.1w.cld · project sase · requested 2m ago · expires in 58m    │
│ Why: Apply the tailscale security update on apollo                    │
│                                                                       │
│  [x] 1  apt-get update                                  📦 network    │
│  [x] 2  apt-get install -y --only-upgrade tailscale     📦 ⚠ tailscaled│
│                                                                       │
│  run as root · cwd / · env: sudo default · stop on first failure      │
│  output to agent: last 20 lines                                       │
│                                                                       │
│  Password for bryan@apollo: ••••••••••▏                               │
│                                                                       │
│  <enter> run 2 selected   <space> toggle   d deny…   v details   esc  │
╰───────────────────────────────────────────────────────────────────────╯
```

- The password field is focused on open. Enter runs the selected commands, and Enter is
  disabled if nothing is selected.
- `d` opens a Deny flow with a feedback box. `v` shows full argv, env, snapshotted script
  contents, and risk explanations.
- **Wrong password:** the field clears and shows "Incorrect password — nothing was run."
  The modal stays open and the gate stays pending. Show a hint the first time,
  "sudo mails root on bad attempts (mail_badpass)", since athena has that default.
- **Correct password:** the modal closes. The gate row goes `SUDO` → running with live
  per-command output, then a completion toast such as "2/2 root commands succeeded on
  apollo". The family settles as `SUDOED`.
- **Hosts that need no password** (NOPASSWD, detected with `sudo -n true` at answer
  time): the modal shows no password field, and the primary button reads
  **Approve & run**. A banner reads "This host does not require a sudo password." The
  human approval stays identical across hosts, so tightening athena later changes
  nothing for Bryan except the extra field.

**Terminal answer**, for when ACE is not handy or when using SSH from a phone:

```text
$ sase sudo answer 7f3c            # or: sase sudo list / sase sudo show 7f3c
🔐 research.1w.cld requests root on apollo — "Apply the tailscale security update"
  1 apt-get update
  2 apt-get install -y --only-upgrade tailscale
Run all 2? [Y/n/select/deny] y
[sudo] password for bryan@apollo: (hidden)
✓ 1 update (12.4s)   ✓ 2 upgrade (31.0s)
```

The password is read with `getpass` from `/dev/tty`, and the command refuses to run if
there is no TTY. `--deny --feedback '…'` works without a TTY.

**Telegram and mobile:** "🔐 *research.1w.cld* requests root on **apollo** (2 commands):
`apt-get update`, `apt-get install …` — answer in ACE or run `sase sudo answer 7f3c`."
They offer [Deny] and [Show commands] buttons, and no password collection. This follows
Telegram's existing secret refusal. The mobile gateway should get the same refusal.

**Remote hosts:** each host owns its own bundles and answers them locally, via its own
ACE (`ssh -t apollo` into tmux) or `ssh -t apollo sase sudo answer <id>`. Relaying the
password across the fleet gateway is out of scope for v1. If it is ever added, it must
be memory-only end to end over the tailnet with no relay persistence, and I would rather
not.

### 5.4 Execution and password pipeline

The goal is that the password exists only in (a) the answering process's widget or
`getpass` buffer, (b) one pipe, (c) the runner's memory, and (d) `sudo`'s own setuid
process, which is already non-dumpable.

```text
ACE modal / sase sudo answer
   │  (password in memory; never in option_inputs, sidecars, response.json, journal)
   │  spawn runner: setsid/start_new_session, stdin = anonymous pipe, stdout = status pipe
   ▼
sase-sudo-runner  (Rust, in sase-core; prctl(PR_SET_DUMPABLE,0), RLIMIT_CORE=0, mlock buf)
   1. read password line from stdin pipe; close pipe
   2. /usr/bin/sudo -k                                   # drop any stale record
   3. /usr/bin/sudo -S -p '' -v   (password via fresh pipe)
        ├─ auth fail → write {"auth":"failed"} to status pipe → exit (nothing ran; gate still pending)
        └─ auth ok   → write {"auth":"ok"} → answering process records the answer, closes modal
   4. for each selected command (in order):
        /usr/bin/sudo -n -u <run_as> -D <cwd> -- <argv…>   stdin=/dev/null
          (ppid-scoped record from step 3; parent = runner)
        if -n fails because policy re-prompts (e.g. timestamp_timeout=0):
          /usr/bin/sudo -S -p '' -u … -- <argv…>   password line via fresh pipe, then EOF
        stream stdout/stderr → bundle-local bounded logs (scrubbed for the password string)
   5. /usr/bin/sudo -k ; zeroize buffer ; write results ; settle gate shell
```

Design notes:

- **Why a dedicated runner, not the generic detached `sase gate answer` proc:** that path
  serializes inputs into sidecars (§3.3). A runner fed through a pipe avoids the file hop,
  gives an **inline** wrong-password result (step 3 happens while the modal is still
  open), and detaches so the batch outlives ACE. It fits the Rust-core boundary. The same
  execution semantics are needed by ACE, the CLI, and any future web or mobile front end.
  A small Rust binary also gets `zeroize`, `mlock`, and `prctl` without Python's
  immutable-string copies.
- **Validation before anything runs** makes "nothing ran" literally true on a wrong
  password. Allow up to 3 inline attempts per modal session, matching sudo's
  `passwd_tries` default, and then tell Bryan to reopen.
- **`sudo -D <cwd>`** needs `runcwd` permission in sudoers. Where that is missing, run
  `/bin/sh -c 'cd …'` only when the reviewer saw a ⚠ `cwd` badge, or default to `/`.
  `-u` and `-D` appear in the modal.
- **stdin to root commands is `/dev/null`** unless the request declares a snapshotted
  stdin resource. This prevents the classic `sudo -S` bug where the rest of stdin, such
  as gate JSON, flows into the command.
- **Output returned to the agent** is bounded (tail N lines) and scrubbed of the
  password string (defense in depth, like `redact_secrets_in_result`). It honors
  `output_to_agent: none|tail|full`. Full logs stay in the bundle for Bryan.
- **Gate records** (`response.json`) contain `approved_command_ids`,
  `auth_mode: password|nopasswd`, the per-command results, and reviewer feedback. There is
  **no password field, not even redacted, and no input digest.**
- **macOS:** no `/proc` or `PR_SET_DUMPABLE`. Use `ptrace(PT_DENY_ATTACH)` and the
  existing inode re-check exec path. `sudo -S` works; Touch ID `pam_tid` does not help
  without a TTY.

### 5.5 Security hygiene for the ACE widget

For the sudo password field, and for all `secret: true` fields:

- Disable yank, delete-to-register, the app clipboard, and OSC 52 for secret widgets.
  Allow paste **in**, so password managers work, but never copy **out**.
- Clear the widget on submit, deny, escape, and on losing screen. Never persist its undo
  history.
- Make sure no key-event debug logging or devtools capture happens while a secret widget
  has focus.
- The masked render already protects `tmux capture-pane` and screen sharing.

### 5.6 Fixes to the generic gate substrate (do regardless)

1. Redact secret fields before writing **any** operation-request sidecar, and stop
   echoing raw `option_inputs` in `_submit_detached_answer`'s return payload. If the
   detached proc truly needs the value, hand it over through an inherited pipe or fd, not
   a file.
2. Exclude secret fields from `value_digest`, or use an HMAC with an ephemeral in-memory
   key. A retry of a secret-bearing submission should require re-entry.
3. Secret widget copy-out protections (§5.5).
4. Mobile gateway: refuse gate actions that carry values for `secret: true` fields until
   a vetted client exists, mirroring Telegram.

These are discovered defects that deserve task beads. I have not filed them, to avoid
duplicate filing across the two-researcher swarm; the lead can file them after synthesis.

### 5.7 Host policy recommendations

- **athena:** once `/sase_sudo` ships, replace `(ALL : ALL) NOPASSWD: ALL` with password
  sudo, optionally keeping narrow `NOPASSWD` Cmnd_Aliases for routine, safe commands. Set
  `kernel.yama.ptrace_scope=1`. Keep the default `timestamp_type`; never use `global`. Do
  this only after the feature exists, or agents lose a capability they currently rely on,
  possibly silently.
- **apollo:** works as-is. Consider `Defaults log_subcmds` or `log_output` for an audit
  trail of agent-requested root work.
- **Everywhere:** the runner uses `/usr/bin/sudo` by absolute path, so the interactive
  `sudo -E` alias never applies.

### 5.8 Later phases

- **Allowlist promotion.** When Bryan approves the same normalized argv for the Nth time,
  offer a separate gate: "Add sudoers rule `bryan ALL=(root) NOPASSWD: /usr/bin/systemctl
  restart caddy`?" It would validate the rule with `visudo -cf` and itself run through
  `/sase_sudo`. This turns repeated friction into explicit, auditable policy instead of a
  warm credential.
- **Pluggable authentication.** Keep `auth_mode` open for a hardware token such as
  `pam_u2f` touch, which can satisfy PAM without typed text. The UX then becomes
  "touch your key" in place of the password field.
- **Fleet view.** Show pending remote `sudo` gates in athena's ACE as **read-only with
  Deny**, plus a one-key "open `ssh -t <host> sase sudo answer <id>`" action.

### 5.9 Rollout

1. **Phase 0:** substrate leak fixes (§5.6), independent and small.
2. **Phase 1:** the Rust runner, the `sudo` kind with `sase sudo request/answer/list/show`,
   the ACE modal, the `/sase_sudo` skill, and the PreToolUse guard. Put it behind a
   feature flag per the `sase_flags` memory, and dogfood on apollo.
3. **Phase 2:** Telegram and mobile deny-only projections, then allowlist promotion.
   Then tighten athena's sudoers and `ptrace_scope`.

---

## 6. Recommendation

Adopt **Option H**. Agents call `/sase_sudo` → `sase sudo request` with a batch of argv
commands and a reason per command, and their turn ends through a gate-shell handoff.
Bryan gets a 🔐 notification everywhere. He types the password **only** in an ACE modal
or with `sase sudo answer` on the executing host. One Enter runs every command he left
checked, and a mistyped password is corrected inline with nothing run.

The password travels from masked memory through a pipe into a non-dumpable Rust runner,
which validates with `sudo -S -v`, runs each command with `sudo -n` under its private
ppid-scoped credential, then calls `sudo -k` and wipes its copy. No password, redaction
marker, or digest ever lands on disk, in a prompt, or in a transcript. A follow-up agent
receives structured, bounded, scrubbed per-command results.

Before or alongside this, close the existing `secret: true` leaks in the gate substrate.
Once the feature is live, retire athena's blanket `NOPASSWD: ALL` and raise
`ptrace_scope`, so the reviewed-command approval becomes a real privilege boundary
rather than a courtesy.

### Open questions for Bryan

1. For v1, should NOPASSWD hosts (athena today) still require an explicit **Approve & run**?
   I recommend yes, for UX consistency and as preparation for tightening. Or should the
   request auto-run with a notification?
2. What is the default `output_to_agent`: `tail` (recommended) or `full`?
3. Is answering only on the executing host (ACE via SSH/tmux, or `ssh -t … sase sudo
   answer`) acceptable for v1, or is fleet-relayed password entry from athena's ACE a
   must-have?
4. Should the PreToolUse raw-`sudo` guard ship at the same time, even though athena
   agents currently use passwordless sudo successfully?

---

## Sources

- sudo(8) manual:
  [man.archlinux.org/man/sudo.8.en](https://man.archlinux.org/man/sudo.8.en). Covers
  `-A`, `-S`, `-n`, `-v`, `-k`, `-K`, `-p`, and `SUDO_ASKPASS`.
- sudoers(5):
  [man.archlinux.org/man/sudoers.5.en](https://man.archlinux.org/man/sudoers.5.en) and
  [Debian trixie sudoers(5)](https://manpages.debian.org/trixie/sudo/sudoers.5.en.html).
  Covers `timestamp_type` (default `tty`; `ppid` when no terminal), `timestamp_timeout`,
  `passwd_tries`, `use_pty`, `log_input`/`log_output`, and NOPASSWD.
- [sudoers_timestamp(5)](https://man.archlinux.org/man/core/sudo/sudoers_timestamp.5.en):
  TS_TTY and TS_PPID record keys.
- [Making sudo Work with AI Agents — Jono's Corner (dgt.is, 2026-03-10)](https://www.dgt.is/blog/2026-03-10-ai-sudo-with-agents/):
  hook deny/poll with `timestamp_type=global`, including its stated risk.
- [How I Let My AI Coding Agent Run sudo… pkexec (Ivan Morgillo, 2026-06-16)](https://www.ivanmorgillo.com/2026/06/16/ai-coding-agent-sudo-pkexec-asroot-linux/):
  polkit dialog, and rejection of password piping.
- [anthropics/claude-code#18316 — Native GUI Password Prompt for Sudo](https://github.com/anthropics/claude-code/issues/18316):
  zenity/osascript + `sudo -S` wrapper; closed as not planned.
- Seen in search results only, not read in depth:
  [suddo (DEV Community)](https://dev.to/sunu15712/suddo-sudo-password-prompts-without-leaving-your-ai-agents-chat-2dgg),
  [sudoplz](https://github.com/crypdick/sudoplz) (I did not open the repo),
  [immurok fingerprint gate](https://immurok.com/blog/fingerprint-gate-for-ai-agents/),
  [Codex escalated-permission approvals](https://vladimirsiedykh.com/blog/codex-cli-approval-modes-2025),
  and [openai/codex#32848](https://github.com/openai/codex/issues/32848).
- SASE code, at workspace HEAD `8ed00c4ed6`:
  - Gate substrate: `src/sase/notification_gates/{cli_answer,executor_inputs,journal,command_runner}.py`,
    `src/sase/procs/{service,runtime}.py`, `src/sase/ops/io.py`.
  - ACE: `src/sase/ace/tui/actions/agents/_notification_gate_execution.py`,
    `src/sase/ace/tui/widgets/secret_vim_text_area.py`,
    `src/sase/ace/tui/actions/clipboard/_delivery.py`.
  - Front doors and policy: `src/sase/main/questions_command_handler.py`,
    `src/sase/main/parser_agent_cli.py`, `src/sase/agent_clis/operations.py`.
  - sase-telegram: `src/sase_telegram/gate_inputs.py`, `scripts/sase_tg_inbound.py`.
  - sase-core: `crates/sase_gateway/src/{routes,host_bridge}.rs`.
