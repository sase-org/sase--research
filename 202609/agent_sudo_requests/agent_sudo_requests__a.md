# Agent-requested sudo execution: security model and recommended UX

**Research date:** 2026-09-14  
**Scope:** A SASE agent needs to ask its human operator to authorize and authenticate
one or more commands that require `sudo`, without revealing the authentication secret
to the agent or turning authentication into a reusable ambient privilege.

## Executive conclusion

The right abstraction is **not “ask Bryan for a password.”** It is **“request a
privileged execution.”** The agent supplies a structured, immutable description of the
commands and why they are needed. A typed SASE gate presents that exact bundle to the
user. After explicit approval, a trusted host-side executor temporarily hands the
terminal directly to `sudo`; `sudo` and PAM conduct authentication, and the agent never
receives the password or any derivative of it.

My recommended full design is:

1. Add a typed `privileged_exec` gate and a discoverable `sase sudo request` front door,
   taught to agents by a generated `/sase_sudo` skill.
2. Make the request a gate shell so the requesting LLM turn ends while the human
   decides, then resume a successor with only structured execution results.
3. In ACE or a TTY CLI, show the exact ordered argv list, target host/user, working
   directory, environment changes, requesting agent, impact, and immutable request
   hash. Require an explicit **Approve & run** action; never auto-answer it.
4. Suspend ACE and invoke a small, root-owned, non-setuid
   `sase-privileged-runner` through **one** `sudo -k` command. Feed the reviewed command
   manifest to the runner on stdin. Do not use `sudo -S`: by default `sudo` reads its
   authentication conversation from the controlling terminal, leaving stdin available
   for the non-secret manifest.
5. The runner executes a bounded sequence of absolute argv arrays with `execve`-style
   semantics, a clean environment, no shell, and `/dev/null` stdin. It stops on the
   first failure unless the reviewed manifest explicitly says otherwise.
6. Do not put the authentication response in any SASE object—not in a gate input,
   draft, IPC payload, file, journal, digest, log, metric, environment variable, argv,
   clipboard, or model continuation. `sudo -k` with a command also avoids updating the
   sudo credential cache, so the operation does not mint a reusable timestamp for an
   unsandboxed agent.
7. Permit authentication only from a trusted local TTY surface (ACE or a headless CLI
   attached through SSH). Mobile and Telegram may display, reject, or send feedback,
   but must not carry the credential or trigger unattended execution.

This gives a one-password experience for a reviewed multi-command bundle, preserves
SASE's durable decision and continuation model, and keeps authentication on the trusted
side of the boundary.

There is one important policy tradeoff: `sudo` authorizes the root-owned runner rather
than each contained command. This is appropriate on Bryan's own workstation when his
sudoers policy already permits arbitrary root commands. It must **never** be made
`NOPASSWD`, setuid, or installed as an unprivileged daemon. On a host with narrowly
constrained per-command sudoers rules, fall back to direct, exact `sudo -k -- <argv>`
execution one command at a time, accepting a separate authentication prompt for each,
or install narrowly scoped administrator-owned actions instead of the general runner.

## What is being protected

The design has four distinct security decisions. Treating them as one “password
prompt” creates most of the dangerous shortcuts.

1. **Intent:** What does the agent claim it needs and why?
2. **Authorization:** Did the human approve these exact bytes, on this exact host, as
   this exact target user?
3. **Authentication:** Did the operating system's configured `sudo`/PAM stack accept
   the human's proof?
4. **Execution:** Did the system run exactly the reviewed command sequence and report
   its partial or final result accurately?

Authentication is not consent. A valid cached sudo timestamp or a `NOPASSWD` rule must
never bypass the SASE review gate. Conversely, clicking an approval button must not
cause SASE to learn or validate the password. SASE owns authorization and the
review-to-execution binding; `sudo`/PAM owns authentication.

The threat model should include more than an accidentally curious model:

- a prompt-injected or malicious agent intentionally trying to obtain root;
- an agent-authored gate command that reads or echoes its input;
- another concurrently running agent under the same Unix account;
- durable SASE transcripts, gate bundles, execution journals, telemetry, crash dumps,
  and clipboard/register state;
- a changed script or request between review and execution;
- a fake “sudo password” form authored by an agent to imitate trusted UI;
- credential-cache reuse after the approved operation;
- a partial multi-command failure followed by an unsafe automatic retry;
- remote notification transports whose servers, devices, or debug logs are not the
  local authentication endpoint.

Once an arbitrary command actually runs as root, it can compromise the machine. No
runner sandbox can make arbitrary approved root code safe. The meaningful security
boundary is therefore the exact-command review and the binding of that review to the
bytes executed.

## Why the current generic secret-input gate is unsuitable

SASE already has several useful building blocks: hashed gate bundles, write-once
responses, argv execution without a shell, gate shells, typed inputs, and redaction.
They should be reused for the request and lifecycle. The generic secret-input path
must not be reused for the sudo credential.

At SASE commit `8ed00c4ed67dc85abded7ea31ce8fce49b3cf865`:

- [`run_owned_command`](https://github.com/sase-org/sase/blob/8ed00c4ed67dc85abded7ea31ce8fce49b3cf865/src/sase/notification_gates/command_runner.py#L35-L74)
  intentionally sends the entire canonical gate input to the agent-authored command's
  stdin. Hash verification proves which command received the secret; it does not make
  that command trustworthy.
- The [secret redaction path](https://github.com/sase-org/sase/blob/8ed00c4ed67dc85abded7ea31ce8fce49b3cf865/src/sase/notification_gates/executor_inputs.py#L64-L153)
  redacts durable copies after execution, but explicitly allows the raw secret to reach
  the command.
- The executor computes an [`input_digest` for every submitted input](https://github.com/sase-org/sase/blob/8ed00c4ed67dc85abded7ea31ce8fce49b3cf865/src/sase/notification_gates/executor.py#L180-L189),
  and [`value_digest` is plain SHA-256 of canonical JSON](https://github.com/sase-org/sase/blob/8ed00c4ed67dc85abded7ea31ce8fce49b3cf865/src/sase/notification_gates/journal.py#L73-L76).
  For a human password, that durable, unsalted, fast digest is an offline dictionary
  oracle. Redacting the plaintext while retaining this digest is not acceptable.
- The current [masked Textual editor](https://github.com/sase-org/sase/blob/8ed00c4ed67dc85abded7ea31ce8fce49b3cf865/src/sase/ace/tui/widgets/secret_vim_text_area.py#L1-L24)
  documents that masking is only visual: the real value remains in widget state, Vim
  registers, and the application clipboard.
- Typed gate inputs are transport-neutral today. The [mobile wire](https://github.com/sase-org/sase/blob/8ed00c4ed67dc85abded7ea31ce8fce49b3cf865/docs/mobile_gateway.md#L407-L419)
  exposes declared secret fields and sends their values through the host bridge. That
  is useful for ordinary API tokens but is the wrong path for an operating-system login
  secret.

There is also an ambient-privilege issue. SASE launches several provider CLIs with
approval and sandbox controls bypassed; Codex's current invocation, for example, uses
[`--dangerously-bypass-approvals-and-sandbox`](https://github.com/sase-org/sase/blob/8ed00c4ed67dc85abded7ea31ce8fce49b3cf865/src/sase/llm_provider/codex.py#L411-L421).
Running `sudo -v` and leaving a broadly usable timestamp behind could let a concurrent
agent call `sudo -n` without ever seeing the password. A good design must protect the
post-authentication capability as carefully as the password itself.

The implication is strong: `secret: true` means “redact this ordinary command input
from SASE's durable presentation.” It does not mean “safe authentication channel for an
untrusted command.” A sudo credential needs a separate host-exclusive data path and, in
the recommended design, never becomes application data at all.

## Relevant sudo behavior

The upstream sudo manual provides the primitives needed for a safer design:

- Normally, sudo reads authentication from the user's terminal. With `-S`, it instead
  reads the password from stdin. With `-A`, it invokes an askpass helper whose stdout
  carries the password. See the upstream [`sudo(8)` source](https://github.com/sudo-project/sudo/blob/bb0d87c9164769fb9a5c14f644af94736a1e0c2d/docs/sudo.man.in#L186-L213)
  and its [`-S` description](https://github.com/sudo-project/sudo/blob/bb0d87c9164769fb9a5c14f644af94736a1e0c2d/docs/sudo.man.in#L727-L731).
- `sudo -v` authenticates and updates cached credentials without running a command.
  That convenience is exactly the wrong default when unsandboxed agents share the Unix
  account.
- When `-k` is used together with a command, sudo ignores cached credentials, prompts
  if policy requires authentication, and does not update the credential cache. This is
  the central reason to prefer one `sudo -k <runner>` invocation for a bundle. See the
  [`-k` semantics](https://github.com/sudo-project/sudo/blob/bb0d87c9164769fb9a5c14f644af94736a1e0c2d/docs/sudo.man.in#L535-L575).
- Sudo timestamps may be global, parent-process-scoped, or TTY-scoped, and the no-TTY
  case can fall back to parent-process scope. The application must not assume the
  machine uses the usual per-TTY default. See [`timestamp_type`](https://github.com/sudo-project/sudo/blob/bb0d87c9164769fb9a5c14f644af94736a1e0c2d/docs/sudoers.man.in#L5148-L5203).
- Sudo's own documentation warns that terminal input logging can store passwords even
  when they are not echoed. SASE must not add any keystroke or PTY-input recording to
  its authentication handoff. See the upstream [I/O logging warning](https://github.com/sudo-project/sudo/blob/bb0d87c9164769fb9a5c14f644af94736a1e0c2d/docs/sudoers.man.in#L6910-L6927).

`sudo` may use PAM, challenge-response, a target-user password policy, an OTP, or
another configured method. For that reason the UI should say **Authenticate** rather
than hard-code **Enter your password**, and it should relay the actual sudo/PAM
conversation rather than attempt to verify a password itself.

## Alternatives considered

| Approach | UX | Secret boundary | Main problem | Decision |
|---|---:|---:|---|---|
| Agent runs `sudo` in its own terminal | Familiar | Poor | Agent owns the process/PTY and can phish or capture input | Reject |
| Generic gate `secret: true` → wrapper → `sudo -S` | Smooth | Unacceptable | Plaintext reaches agent code; current journal retains a guessable digest; editor/remote transport retain copies | Reject |
| Put password in argv or environment | Simple | Unacceptable | Process arguments and environment are observable and inherited; this is the class of weakness described by [CWE-214](https://cwe.mitre.org/data/definitions/214.html) | Reject |
| Run `sudo -v`, then let agents use `sudo -n` | Very smooth | Poor | Creates an ambient cached capability whose scope depends on sudoers timestamp policy | Reject |
| Standard `sudo -A` / graphical askpass | Good desktop fallback | Moderate | Adds a helper that receives plaintext on stdout and is easier to spoof or replace; requires strong helper pinning and channel binding | Fallback only |
| `pkexec` / polkit | Good native auth UX | Strong when designed well | Different policy system and requires a privileged mechanism/action definition; not a drop-in implementation of sudoers semantics | Good future option for fixed actions |
| Narrow root-owned `NOPASSWD` wrappers | Excellent for repeated fixed tasks | No password involved | Creates standing privilege and cannot safely express arbitrary ad hoc commands | Complementary, opt-in |
| Typed gate + direct sudo TTY + one-shot root runner | Good after one-time install | Strong | Runner is a small privileged TCB; sudo authorizes the runner rather than each contained command | Recommend |

Polkit's architecture is a useful conceptual model: a privileged mechanism treats the
requesting subject as untrusted, while a separate session authentication agent proves
the human's identity. The [polkit reference manual](https://polkit.pages.freedesktop.org/polkit/polkit.8.html)
describes exactly this subject/mechanism/authority split. If SASE later grows a catalog
of stable privileged actions such as “restart this named service,” those should
probably become narrow polkit actions or root-owned sudoers wrappers. A general root
daemon for arbitrary agent commands would be a much larger and longer-lived attack
surface than the one-shot runner proposed here.

Systemd's [password-agent protocol](https://systemd.io/PASSWORD_AGENTS/) is also useful
precedent for expiring requests, hidden input, and multiple competing UI agents, but it
is primarily intended for system/service passphrases rather than the invoking user's
sudo/PAM authentication. It should not be used as an excuse to relay the sudo password
through SASE storage.

## Recommended user experience

### 1. Notification and review

The notification should look categorically different from a custom gate:

> 🔐 **Run 3 privileged commands on athena**  
> Requested by `agent-name` · as `root` · request `a1b2c3d4`

Opening it shows, in this order:

1. **Verified facts:** host, invoking Unix identity, target identity, number of commands,
   requesting agent/family, workspace/project, request hash, runner version, and whether
   a local TTY is available.
2. **Agent explanation (explicitly labeled untrusted):** why privilege is needed,
   expected effect, and suggested rollback.
3. **Exact execution:** one numbered command per row, rendered as an argv vector and as
   a copyable shell-escaped display. Show the absolute executable, cwd, environment
   additions, timeout, stdin policy, and output-return policy. Never hide arguments
   behind “install dependencies” or a collapsed summary.
4. **Risk callouts:** shell/interpreter use, executable or cwd writable by the invoking
   user, network access, package-manager hooks, destructive flags, service changes, and
   commands whose output will be returned to the model.
5. **Sequence warning:** “Commands run in order and are not atomic; completed commands
   remain applied if a later command fails.”

The primary action should be **Approve & run**, not **Enter password**. Other branches
should be **Request changes** (requires feedback and resumes the agent to revise the
bundle) and **Reject**. Do not make a privileged gate auto-resolvable. To avoid an
accidental Enter on a high-consequence gate, require an explicit activation such as
Ctrl+Enter or a focused confirmation button; a password prompt is not a substitute
because `NOPASSWD` policy may legitimately produce no prompt.

The review is accepted against the hash of the normalized manifest and any frozen
resources. The host re-verifies that hash immediately before launching sudo. Any change
returns the gate to review; it never silently re-prompts against different commands.

### 2. Trusted authentication handoff

After approval, ACE transitions the gate shell from `CONFIRM` to `AUTHENTICATE`,
suspends its Textual UI using the terminal-handoff machinery it already uses for
external tools, and prints a small host-authored banner:

```text
SASE privileged request a1b2c3d4 on athena
Approved: 3 commands as root. Ctrl-C cancels before execution.
Handing the terminal directly to sudo/PAM…
```

The host then launches, without a shell, the conceptual equivalent of:

```text
/usr/bin/sudo -k -p '[SASE a1b2c3d4 on %h] authenticate %p: ' -- \
  /usr/local/libexec/sase-privileged-runner
```

The canonical non-secret manifest is connected to the process's stdin. The controlling
terminal is inherited. Because `-S` is absent, sudo reads authentication directly from
the terminal, not from the manifest pipe. ACE does not receive key events, create a
password string, or render bullets; it is suspended while sudo owns the terminal.

This is both safer and simpler than writing a supposedly secure Python/Textual password
widget. It also preserves the configured PAM conversation and supports paste from a
password manager. NIST's current password guidance recommends allowing password
managers and paste and using a protected authentication channel; see
[SP 800-63B](https://pages.nist.gov/800-63-4/sp800-63b.html). SASE should not impose
composition, length, trimming, normalization, or retry rules on the response. Sudo/PAM
is the verifier and already owns those policies.

Wrong credentials, timeout, and Ctrl-C are reported as authentication outcomes, not as
command failures. SASE must not automatically retry a failed authentication. Only one
privileged authentication handoff may be active per host/user session, which prevents
stacked prompts and makes the origin of the active prompt unambiguous.

### 3. Execution and completion

The root-owned runner reads one bounded manifest, verifies its schema and request hash,
then executes commands serially:

- absolute executables only;
- argv arrays only—no implicit shell parsing;
- no nested `sudo`, `su`, `pkexec`, or agent-selected askpass helper;
- clean, fixed environment with a small reviewed allowlist; reject `LD_*`, language
  loader paths, `SUDO_*`, and arbitrary `PATH` changes;
- `/dev/null` stdin for every privileged child in the first version;
- a declared absolute cwd, defaulting to `/`, with a warning for user-writable cwd;
- process-group timeout and termination;
- stop on first nonzero status by default;
- per-command start/end/exit records, never terminal-input records.

Interactive root programs should be out of scope initially. Multiplexing a privileged
program's input with authentication makes prompt spoofing and accidental keystroke
capture much harder to reason about. Agents should use noninteractive program flags or
split the workflow so only a narrow final mutation is privileged.

After sudo exits, ACE restores itself and shows a result table. The durable audit should
contain the request hash, exact manifest, approval identity/surface, timestamps,
per-command exit or signal, and bounded output according to the reviewed output policy.
It must contain no authentication input, digest, length, prompt response, or
password-derived command result.

Privileged command output is a separate data-classification concern: a root command can
print secrets even when the password is safe. By default, return only status and a
bounded diagnostic tail to the successor agent. Make “return full output to agent” an
explicit reviewed property, and keep any user-only log mode `0600`. Never send the raw
sudo/PAM conversation to the successor.

For a partial command failure, the gate records exactly which indices completed. The
default retry is **Resume at command N**, after a fresh review and authentication.
**Re-run all** must be an explicit dangerous choice. There is no automatic rollback
claim; an agent-authored rollback is another privileged request.

## Password and authentication handling requirements

These should be hard invariants, not best-effort redaction:

- The credential is never an agent-visible parameter and never enters an LLM context.
- It is never accepted through chat, feedback, a custom gate, a raw JSON/YAML editor,
  the mobile API, Telegram, or `sase gate answer --option-input`.
- It is never placed in argv, environment, a shell command string, a filesystem object,
  an IPC message retained by SASE, stdout/stderr capture, telemetry, crash data,
  clipboard, Vim register, response JSON, journal, hash, or retry fingerprint.
- SASE never hashes the password. A fast unsalted digest is itself a verifier usable for
  offline guessing; NIST requires stored password verifiers to use salted, attack-
  resistant password hashing, which is another reason SASE should store no verifier at
  all.
- The terminal is handed directly to the setuid-root sudo executable. SASE records no
  terminal input during that interval and restores terminal modes on success, signal,
  timeout, and crash paths.
- The command is invoked with `sudo -k` so it neither trusts nor refreshes a sudo
  timestamp for the bundle. Do not run a separate `sudo -v` warm-up.
- Do not run `sudo -K` as cleanup: it removes every cached credential for the user and
  would unexpectedly disrupt unrelated sessions. The bundle should avoid creating a
  timestamp in the first place.
- The runner is root-owned and not writable by the SASE user, is not setuid, and has no
  listener or daemon mode. Do not add an unbounded `NOPASSWD` sudoers entry for it.
- The trusted authentication UI has a visual/terminal path an agent-authored custom gate
  cannot imitate. Custom gates that mention a sudo/root password should display a
  prominent warning: “Never enter your system password here.”
- Failure messages say whether authentication was canceled/failed or execution failed,
  but do not expose entered length, partial value, or derived diagnostics.

MITRE's [CWE-214](https://cwe.mitre.org/data/definitions/214.html) documents why argv
and environment are unsuitable for credentials. OWASP's
[logging guidance](https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html#data-to-exclude)
lists authentication passwords among data that should not be logged. The strongest
implementation is to make the secret absent from SASE rather than depend on finding and
redacting every copy later.

## Agent-facing API

Expose a provider-neutral CLI plus a generated skill, not a provider-specific native
approval feature and not a recipe for hand-authoring a custom gate.

Recommended names:

- CLI: `sase sudo request --spec <path>` (or canonical JSON on stdin)
- Agent skill: `/sase_sudo`
- Internal gate kind/action: `privileged_exec` / `PrivilegedExecution`
- User-facing noun: “privileged request,” because authentication might not be a
  password and the backend could later support a narrow polkit action.

The agent-authored schema should contain no field named password or secret. A compact
shape is:

```json
{
  "schema_version": 1,
  "intent": "Install the already-built binary into /usr/local/bin",
  "impact": "Replaces /usr/local/bin/example",
  "rollback": "Restore /usr/local/bin/example.bak",
  "commands": [
    {
      "argv": ["/usr/bin/install", "-o", "root", "-g", "root", "-m", "0755", "…", "/usr/local/bin/example"],
      "cwd": "/",
      "timeout_seconds": 60,
      "return_output": false
    }
  ],
  "on_success": "Verify the installed binary version"
}
```

The front door validates and normalizes the manifest, creates the typed gate shell, and
ends the creating agent's turn. It should strip no ambiguous shell text: if an agent
submits a leading `sudo`, reject it with guidance to express `run_as` separately. It
should reject implicit executables, relative cwd, inherited arbitrary environment,
interactive stdin, and nested privilege launchers. Shells/interpreters should be denied
in version one; later support can require a conspicuous risk flag and show the entire
program text.

The skill should teach agents to:

1. Try the unprivileged operation first when sensible and gather read-only context.
2. Minimize the privileged portion—build/download as the user, then ask root only for
   the final install, ownership, service, or package mutation.
3. Submit exact commands plus impact and rollback, never request a password and never
   use `sudo -S`, `SUDO_ASKPASS`, `sudo -v`, or a generic secret field.
4. Treat successful request creation as a gate-shell handoff and stop; never wait or
   poll.
5. Continue only through the gate's recorded successor, which receives structured
   command results but no authentication material.

This fits SASE's existing “gate never blocks an agent” decision and uses the same
durable bundle, notification, shell, and follow-up machinery. Because the gate registry
currently makes a newly registered branch-actionable kind available across ACE,
Telegram, and mobile, the adapter model needs one new capability such as
`requires_local_tty_auth`. Remote surfaces should render the review and allow safe
reject/feedback branches, but the run branch should answer with
`local_interaction_required` and instructions to open ACE or use a TTY CLI. Authentication
over an SSH-allocated TTY is fine: sudo still reads on the target host and the SSH
transport protects the terminal channel.

Shared manifest validation, review hashing, execution state, and result wire format are
backend/domain behavior and belong in `sase-core`; Python should provide thin adapters
and ACE's presentation/terminal suspension. The skill must be authored in the generated
skill source, not by editing deployed `SKILL.md` files.

## Root runner design and tradeoffs

`sase-privileged-runner` should be deliberately boring:

- a small Rust binary installed once under a root-owned system path;
- no setuid bit and no network listener;
- accepts exactly one versioned manifest on stdin with strict size/count/depth bounds;
- clears the environment and closes unrelated file descriptors;
- validates absolute executable/cwd, target user constraints, command count, argv and
  output limits;
- uses direct process spawning, never `sh -c`;
- places each child in a process group, enforces timeouts, and reports a structured
  record;
- never reads the controlling TTY and never prompts;
- never accepts an “already approved” boolean or reusable token from the agent.

The privileged helper does not validate the password and does not need a durable secret.
Its authority comes from the one live sudo invocation. The SASE host passes the same
canonical manifest bytes whose hash the user approved; the runner revalidates the
schema, while the unprivileged host rechecks the gate/resource hash immediately before
launch.

The downside is that sudoers sees one allowed executable, the runner. Do not suggest
adding a broad rule for it on a constrained machine. The safe compatibility modes are:

1. **Unrestricted sudo user:** use the general runner for one prompt and no timestamp.
2. **Constrained sudoers:** invoke each exact allowed program directly with `sudo -k --`
   so sudoers evaluates it; require authentication for each command, or ask the system
   administrator to provide a narrowly parameterized root-owned action.
3. **Repeated stable operation:** prefer a purpose-built root-owned wrapper or polkit
   action with a narrow argument contract. A `NOPASSWD` rule is acceptable only after a
   deliberate administrator decision that the standing capability is safe; the SASE
   human-approval gate should still remain.

Do not silently downgrade from runner mode to a generated root shell. `sudo sh -c` has
nearly the same policy-bypass property as the runner, but adds quoting and shell-
injection risk without providing a stable schema or audit protocol.

## Edge cases

- **Credential already cached:** `-k` forces this request through authentication when
  policy requires it and prevents a refresh. The SASE approval is still required.
- **`NOPASSWD` command:** no authentication prompt may appear. The UI should say “sudo
  did not require authentication” after the explicitly approved execution, not report a
  missing prompt as failure.
- **PAM/OTP/challenge-response:** relay sudo's terminal conversation; do not assume one
  hidden string or rewrite PAM prompts.
- **No TTY:** fail closed with “open this request in ACE or run `sase sudo answer …` from
  a TTY.” An askpass backend can be a later local-desktop fallback, but must be a pinned,
  trusted helper and must never use the generic gate-input transport.
- **Remote phone/Telegram:** display-only plus reject/feedback. Never send a sudo
  credential through notification APIs.
- **Multiple pending requests:** queue them and authenticate one at a time. Always show
  host, agent, and request ID before terminal handoff.
- **Request changed after review:** abort before sudo and require a new review.
- **Authentication succeeds, command 2 fails:** preserve the exact partial ledger;
  resume requires new approval/authentication and starts at command 2 by default.
- **Terminal closes:** mark the gate interrupted/partial. Do not promise the root child
  was rolled back; reconcile its process group and report what is known.
- **Long-running command:** in the first version, keep ACE suspended and stream numbered
  command progress. A later root-side supervisor may detach after authentication, but
  should not become a permanent arbitrary-command daemon.
- **Command needs stdin:** reject in version one. Add an explicitly separate privileged
  interactive-console design later rather than multiplexing it with authentication.
- **Root-readable mutable workspace inputs:** freeze/hash SASE-owned resources and
  reverify immediately before execution. Warn whenever a command intentionally consumes
  other user-writable paths; arbitrary root commands cannot be made race-free in the
  general case.

## Suggested acceptance tests

Security tests should use a unique canary credential and prove absence, not merely
redaction in the happy-path response.

1. Scan the gate bundle, response, journal, gate log, telemetry, subprocess argv, and
   environment: no canary, no canary hash, no length, and no password-derived value.
2. A malicious agent-authored custom command never receives terminal input or the sudo
   credential; privileged child stdin is EOF unless it is the root runner's manifest.
3. A custom gate labeled “sudo password” cannot acquire trusted styling and shows the
   unsafe-password warning.
4. Mutating the manifest or a frozen resource after approval aborts before sudo starts.
5. `sudo -k <runner>` ignores an existing timestamp and does not create or refresh a
   timestamp usable by a subsequent `sudo -n` probe in an isolated test account.
6. Wrong credential, PAM retry, timeout, Ctrl-C, no TTY, and terminal restoration all
   leave a coherent terminal gate state without recording input.
7. `NOPASSWD` policy still requires the SASE approval but succeeds without inventing a
   password prompt.
8. Mobile and Telegram cannot invoke the run branch or submit an authentication value.
9. Two clients racing to approve produce one accepted decision and at most one sudo
   invocation.
10. Multi-command success, failure at each index, timeout, resume, and explicit restart
    produce accurate partial ledgers and never automatically replay completed commands.
11. The runner rejects relative executables, shell strings, unsafe environment keys,
    nested privilege launchers, oversized manifests, unexpected fields, and interactive
    stdin.
12. Installation checks refuse a runner that is not root-owned or is writable by the
    invoking user/group.
13. A nonstandard PAM conversation (for example an OTP prompt) works because sudo owns
    the TTY rather than SASE assuming a single password field.
14. The successor agent receives only the reviewed output class and structured statuses,
    never the authentication transcript.

## Recommended solution / UX

Implement a dedicated **Privileged Execution gate shell** with a generated
`/sase_sudo` skill and `sase sudo request` CLI. The agent submits a minimal structured
argv bundle; SASE durably freezes and displays it; Bryan explicitly approves it in ACE;
ACE suspends and hands the real terminal directly to `sudo`; and one
`sudo -k /usr/local/libexec/sase-privileged-runner` invocation executes the approved
sequence without creating or refreshing a reusable sudo timestamp. The credential is
never modeled as SASE input and therefore never reaches the agent, generic command
runner, clipboard, mobile transport, log, or hash.

The visible flow should be:

```text
Agent requests privilege
  → 🔐 review exact commands, host, target, impact, and output policy
  → Approve & run / Request changes / Reject
  → trusted terminal handoff to sudo/PAM (no SASE password field)
  → numbered command progress
  → per-command result + explicit partial-failure state
  → successor agent receives only approved structured results
```

For the first implementation, keep the privileged runner noninteractive, root-owned,
one-shot, and available only to users whose existing sudo policy already permits a
general runner. Provide the exact-command/per-prompt fallback for constrained sudoers.
Do not ship the attractive but unsafe shortcut of `secret: true` plus `sudo -S`; its
plaintext-to-agent path, durable SHA-256 input digest, application clipboard/register
copies, remote transport, and credential-cache temptations all violate the required
boundary.

## Sources

- Sudo upstream source manual at commit `bb0d87c9`: [`sudo(8)`](https://github.com/sudo-project/sudo/blob/bb0d87c9164769fb9a5c14f644af94736a1e0c2d/docs/sudo.man.in),
  [`sudoers(5)`](https://github.com/sudo-project/sudo/blob/bb0d87c9164769fb9a5c14f644af94736a1e0c2d/docs/sudoers.man.in)
- [polkit architecture and authentication agents](https://polkit.pages.freedesktop.org/polkit/polkit.8.html)
- [systemd Password Agents specification](https://systemd.io/PASSWORD_AGENTS/)
- [NIST SP 800-63B, Authentication and Authenticator Management](https://pages.nist.gov/800-63-4/sp800-63b.html)
- [MITRE CWE-214: Invocation of Process Using Visible Sensitive Information](https://cwe.mitre.org/data/definitions/214.html)
- [OWASP Logging Cheat Sheet — data to exclude](https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html#data-to-exclude)
- SASE source at commit `8ed00c4e`: gate executor, redaction, journal, Textual secret
  input, mobile gate transport, provider invocation, and notification documentation
  linked inline above.
