---
create_time: 2026-08-22
updated_time: 2026-08-22
status: research
---

# Stand-alone proc shells and the `%proc` directive

**Research question.** What is the best way to add stand-alone proc shells — named
supervised commands that do not belong to an agent family — so a user can launch them
from xprompt swarms via a new `%proc` directive, wait on them with `%wait`, and run
commands that claim and release SASE project workspaces?

**Scope.** `sase` at `a22ca4d61`, linked `sase-core` at `fc9e98c`, research sidecar at
this workspace's `sase/repos/research`. This note is architecture research, not an
implementation plan; no runtime behavior was changed. It extends three 2026-08 reports
that already predicted this capability and then left it off the critical path:

- [`proc_ownership_and_shell_taxonomy`](proc_ownership_and_shell_taxonomy/proc_ownership_and_shell_taxonomy.md)
  — taxonomy, `shell_name` vs `concurrency_keys`, stand-alone shells as a cheap option.
- [`sase_shell_named_procs`](sase_shell_named_procs/sase_shell_named_procs.md)
  — named proc = supervised command with a stable name; family attachment is optional.
- [`monitor_command_substrate`](monitor_command_substrate/monitor_command_substrate.md)
  / [`detached_proc_convergence`](detached_proc_convergence/detached_proc_convergence.md)
  — supervisor, settlement, and workspace-claim machinery `%proc` should reuse, not
  rebuild.

**Method.** Glossary read for Proc, Proc Shell, Sase Shell, Sase Agent, Agent Family,
Xprompt / Swarm / Part / Workflow, Artifact, Sase Workspace. Audited reads of the
reports above. Code inspection of directive extraction, `::` shorthand, wait-dependency
resolution, proc naming/service/settlement, operational workspace leases, xprompt input
types, swarm expansion, and the Rust directive/input-type contracts.

---

## Bottom line

Stand-alone proc shells are not a new execution substrate. They are **one-shell sase
agents whose only executing shell is a proc shell**. That single identity choice makes
`%wait`, `sase agent list`, ACE's Agents tab, and swarm fan-out work by construction.

Ship `%proc` as a **segment classifier**, not as an extra script glued onto an LLM
prompt. After alt/swarm split, a segment that carries `%proc` launches a named
supervised command instead of a provider run. `%id` names it, `%wait` delays it, and
settlement writes a normal `done.json` with `completed` or `failed` so existing wait
resolution does not need a second index.

Multi-line syntax should **not** reuse today's `%clan...:: prose` capture. Today's `::`
requires a space, then eats text until the next line-boundary `%`/`#`. For `%proc`,
`::` should skip whitespace and consume **exactly one Markdown fenced code block**.
Missing language defaults to Bash. That fence parser should be a new general-purpose
xprompt input type named `code`, so a later `#name::` + fence binds the same value.

Python scripts should run under **SASE's own interpreter** (`sys.executable`), which is
the only reason `python=` is worth having: `import sase` and the operational-lease APIs
work. Bash scripts should run under `/bin/bash` with SASE's bin directory prepended to
`PATH`, so `sase` CLI works the same way workflow `bash:` steps already do.

Do **not** auto-claim a workspace for every `%proc`. Default is command-owned claiming.
Offer an explicit opt-in (`workspace=true`, or a later equivalent) that uses the
existing `submit_via_lease` / settlement-policy path. A `#gh:` / `#git:` ref on a proc
segment selects the project; it must **not** wrap the segment in `#commit`/`#pr`
rollover.

---

## 1. What the request actually asks for

Restated as constraints the current tree either already satisfies or clearly does not.

| Constraint | Why it matters | Today's nearest object |
| --- | --- | --- |
| Shells that are **not** members of an agent family | Distinct from monitors (`<family>--mon`) | Named proc with `shell_name`, but qualification currently *forces* `agent--role` |
| Usable in **xprompt swarms** (`---` segments, including `#name` swarm expansion) | Mixed agent/proc DAGs in one paste | `spawn_segments_into` always calls the agent launch executor |
| New **`%proc` directive** with excellent single- and multi-line syntax | Directives are stripped and change runner behavior; this is not prompt text | Known directives are `auto, clan, effort, final, hide, model, id, repeat, wait` |
| Multi-line: **fenced code block after `::`**, optional language, default Bash | Scripts contain `#` and `%` at line starts | `::` is clan-summary prose; fences inside it are just characters |
| That fence form is a **new general-purpose input type** | Later `#script::` + fence, not `%proc`-only grammar | `InputType` is `word/line/text/path/agent/int/bool/float/enum` |
| Single-line: positional string, `bash=`, `python=` | One-liners in a swarm row | Parenthesized directive kwargs exist; `%proc` does not |
| `python=` injects SASE's environment | Otherwise Python is a worse Bash | Workflow `python:` steps already use `sys.executable -c` |
| Support **`%wait`** (and other directives when useful) | Swarm members depend on setup/teardown commands | `%wait` resolves **only** through the agent artifact index |
| Commands can **claim and release project workspaces** | Host work that needs a numbered clone, not workspace 0 | `acquire_operational_lease` + `submit_via_lease` + proc settlement |

Two glossary facts are load-bearing and easy to misread:

1. **"Stand-alone" means "not in an agent family", not "not a sase agent".** A sase
   agent is a sequence of sase shells. A one-shell agent may share its shell name. A
   family-attached proc shell is a monitor. The gap is the **one-shell proc agent**.
2. **`%wait` does not look at `~/.sase/procs/procs.jsonl`.** It indexes `ace-run`
   artifacts and treats `done.json` outcomes in
   `WAIT_SUCCESS_OUTCOMES = {completed, noop, epic_approved, plan_committed}`.
   Monitor members write `outcome: monitored`, which is **not** a wait-success
   outcome; family wait has special handoff logic. A stand-alone proc that should
   unblock `%wait:prep` must settle as `completed` (exit 0) or `failed` (nonzero).

---

## 2. What is already true

### 2.1 The taxonomy already has a hole shaped like this

Current glossary (and `sase_agent.py`):

```text
sase agent                         sase shell
├─ solo agent (one shell)          ├─ agent shell   (LLM/provider run)
└─ agent family (>= 2 shells)      └─ proc shell    (supervised command)
   ├─ agent shell                     today: family-attached ⇒ monitor
   ├─ proc shell  == monitor
   └─ agent shell
```

`proc_ownership_and_shell_taxonomy` §0.3 said stand-alone proc shells were *not* on
the TUI-migration critical path, and §9.2 recommended including them "if convenient"
because they unlock `%wait`/`#fork` over procs. That convenience window is this
feature.

The proc store already has the fields: `shell_name`, `shell_kind` (default `"proc"`),
`lifecycle: proc-shell`, `artifacts_dir`, `workspace_claim`, `timeout_seconds`.
`submit_proc_request` already double-forks, waits for ack, and exposes `after_ack`
so a caller can take a workspace claim before the launch barrier opens. Settlement
already releases `workspace_claim` exactly once, including operational leases.

What the store does *not* have is a name that is allowed to exist without `--`.

### 2.2 Named proc shells cannot be stand-alone today

`qualify_proc_shell_name` (`src/sase/procs/names.py`):

- empty, slash, proc-id-shaped, or more than one `--` → error
- a name that already contains `--` is fully qualified (`pc--mon`)
- a **bare** name is rewritten to `<calling sase agent>--<name>`
- **no calling agent** → `ProcShellNameError`: pass `<agent>--<shell>`

`sase proc run -N build -- just check` from a terminal therefore cannot create a
host-owned named shell. That is exactly the CLI spelling stand-alone shells want.
The Rust store does not care: uniqueness is `(project, shell_name)` via a derived
`shell:<project>:<name>` concurrency key. The `--` rule is Python qualification
policy, not a wire constraint.

### 2.3 `%wait` is an artifact protocol, not a proc-store protocol

Launch-time `%wait:name` is recorded on the waiter, then resolved by
`build_wait_dependency_index` over `ace-run` artifact dirs. A name is resolved when
the latest matching candidate is `is_resolved` and `is_done`, which for ordinary
agents means `done.json` outcome ∈ `WAIT_SUCCESS_OUTCOMES`.

Consequences:

- A proc row with no artifacts dir is invisible to `%wait`.
- A monitor is wait-able as a *family member*, not as a successful named agent, because
  its outcome is `monitored`.
- Teaching `%wait` to also scan `procs.jsonl` would split identity: `sase agent show`,
  ACE wait glyphs, `#fork`, `sase var`, and the wait-checks chop would each need a
  second lookup. That is how today's `kind` mistake happened.

Monitors already prove the dual-record pattern: proc store owns execution; artifacts
own wait/roster/chats. `_settle_artifacts` dispatches to `settle_monitor_artifacts`
when `agent_meta.json` carries `monitor_id`. Stand-alone shells need a sibling
settlement branch that writes `done.json` with `completed`/`failed` instead of
`monitored`.

### 2.4 Directive grammar is close, then fails the fence case

Known directives live in two contracts that tests pin together
(`tests/test_xprompt_directive_contract.py` ↔ `sase_core::editor::directive::DIRECTIVES`):

Python `_KNOWN_DIRECTIVES` and the Rust `DIRECTIVES` table must gain `%proc` in the
same change, plus ACE/LSP completion.

`::` shorthand today:

- Only `%clan` is allowlisted (`_DIRECTIVE_TEXT_BLOCK_ARGUMENTS = {clan: summary}`).
- The token is literally `:: ` — **colon-colon-space**. A newline after `::` does not
  match.
- Capture runs until the next line-start `%directive` or `#xprompt`, skipping those
  tokens inside fences (`find_directive_double_colon_text_end`).
- The captured text is rewritten to `summary=[[...]]`. Fences inside it are
  *content*, not a typed body. Verified by
  `test_clan_double_colon_shorthand_ignores_boundaries_in_fenced_code`.

So this does **not** parse as a script today:

```text
%proc::
```bash
echo hello
```
```

After `::` is a newline, not a space. Even if we added a space, the capture would
include the fence plus any trailing prose until the next directive — the opposite of
"the code block *is* the argument".

Fenced-block scanning already exists and is the right parser to reuse:
`fenced_block_details` in `src/sase/xprompt/_fenced_blocks.py` returns opening fence,
info-string range, content range, and closing fence. CommonMark rules (3-backtick
minimum, info string, matching closer) are already implemented.

### 2.5 Xprompt input types have no executable/fenced variant

Python `InputType` and Rust `editor/frontmatter.rs` `InputType` / `parse_input_type`
agree on `word, line, text, path, agent, int, bool, float, enum`. Unknown spellings
silently become `line` on the Rust catalog path. A new `code` type must be added in
**both** trees or LSP diagnostics, the frontmatter panel, and runtime validation will
diverge.

`text` is "any content". That is the wrong type for `%proc`: it does not carry a
language, does not require a fence, and does not default to Bash.

Workflow YAML already has `python:` and `bash:` *steps*. Those run in-process in the
workflow executor (`subprocess` with `sys.executable -c` or `shell=True`), are not
sase shells, do not appear in `sase agent list`, and do not participate in `%wait`.
They are a useful execution precedent, not a substitute for `%proc`.

### 2.6 Workspace claiming for non-agent work already exists

`src/sase/workspace_provider/lease.py` is the host path:

- `acquire_operational_lease` claims a unified-pool workspace (≥ 2, never #0),
  materializes the checkout, prepares from the primary remote.
- `submit_via_lease` binds `cwd` + `workspace_claim` onto a `ProcSubmitRequest`,
  transfers the RUNNING-field pid to the supervisor in `after_ack`, and lets proc
  settlement release the lease.
- Failures never fall back to the user-owned primary checkout.

Epic/task launch already uses this. `%proc` should not invent a third claim
mechanism. The design question is only *when* a `%proc` segment takes a lease
(never / always / opt-in).

### 2.7 Swarms already do the hard fan-out

`src/sase/agent/xprompt_swarm.py` expands `#name` bodies on `---`, prepends the
call-site's leading `#gh:`/`#git:` ref onto follow-up segments, and feeds
`spawn_segments_into`. Alt/model fan-out (`%alt` / `%{...}`) happens *per segment*
before launch. Classification of "this segment is a proc" belongs **after** that
split, so this works by construction:

```text
#gh:sase
%{%proc(bash="just fmt") | %id:coder Implement the formatter output}
```

Embedded swarms inherit VCS refs. A proc follow-up segment in a `#setup` swarm
should inherit `#gh:sase` as *project identity*, not as commit-rollover wrapping.

### 2.8 Runner slots are LLM admission, not proc admission

`is_runner_slot_user_agent_record` exempts serial family children and monitors from
waiting for their own slot; occupancy is per family. A stand-alone proc shell must
**not** take an LLM runner slot and must **not** go through `axe` `run_agent` just to
sit in `waiting.json`. Wait-checks can still observe its artifacts; starting the
command is `submit_proc_request`.

---

## 3. The identity decision

This is the one choice everything else follows from.

### Option I — Proc-store-only (no agent artifacts)

`%proc` calls `submit_proc_request` with a `shell_name`. `%wait` is taught to resolve
proc names from `procs.jsonl` (terminal `success` ⇒ resolved).

**Pros.** Smallest write path. No `done.json` fiction. No runner-slot confusion.

**Cons.** `%wait`, ACE wait glyphs, `sase agent list -a`, `sase var`, `#fork`, clan
membership, and the wait-checks chop all grow a second backend. Prior research
rejected this shape for monitors: dropping the artifacts record "deletes `%wait`,
`#fork`, family roster, claim transfer, and `sase chats`". Doing it for stand-alone
shells recreates that split on day one.

### Option II — Synthetic family (`prep--proc` as a one-member family)

Mint a family container so existing `agent--role` qualification keeps working.

**Pros.** Zero change to `qualify_proc_shell_name`. Monitor naming stays the only
`--` story.

**Cons.** The user asked for shells that do **not** belong to an agent family. A
one-member family is a family in the reservation registry, `sase agent list`
folding, and `%wait:prep` family-complete semantics (including monitor-handoff
logic that does not apply). It also spends the family-promotion machinery on
something that must never grow a second LLM shell by accident.

### Option III — One-shell sase agent (recommended)

`%id:prep %proc:: ...` creates sase agent `prep` whose only shell is a proc shell
also named `prep` (shared name, which the glossary already allows for one-shell
agents). Store:

- proc row: `shell_name="prep"`, `shell_kind="proc"`, `artifacts_dir=<ace-run dir>`
- artifacts: `agent_meta.json` with `name=prep`, **no** `agent_family_role`, **no**
  `monitor_id`; `pid`/proc id cross-link
- settlement: `done.json` `outcome=completed` if exit 0, `failed` otherwise

**Pros.** `%wait:prep` is the existing named-agent path. `sase agent show prep` and
`sase proc show prep` name the same shell. No family reservation. Matches "a sase
agent is a sequence of sase shells" with sequence length 1. Clan join (`%clan`) can
be a later additive if grouping procs with agents is useful.

**Cons.** `qualify_proc_shell_name` must accept a bare name **without** a calling
agent as a fully qualified stand-alone name. Inside an agent, bare `-N build`
should keep today's `agent--build` qualification so accidental stand-alone names
are not minted from monitors' cousins.

That last rule is the compatibility hinge:

| Caller | `-N build` / `%id` omitted | Result |
| --- | --- | --- |
| Host / swarm `%proc` | bare `build` | stand-alone shell `build` |
| Host, explicit `pc--build` | qualified | family-attached (existing) |
| Inside agent `pc` | bare `build` | `pc--build` (existing) |

### Recommendation

**Option III.** Relax qualification only for the no-caller case; do not invent a
family. Do not teach `%wait` a second store.

---

## 4. What `%proc` is in a swarm

### Option A — Side script on an LLM segment

The segment still launches a model; `%proc` additionally starts a command.

Rejected. The leftover "prompt" is either silently discarded or sent to a model that
should not exist. Workspace-claiming setup jobs are not chat turns.

### Option B — Segment classifier (recommended)

After swarm/alt/repeat expansion, each slot is either:

- an **agent-shell launch** (today), or
- a **proc-shell launch** iff `%proc` is present.

Rules:

- `%proc` is single-value. Two `%proc` in one segment is an error.
- Non-directive, non-script remainder in a proc segment is an error (no hidden LLM
  prompt).
- `%id` is required-or-auto, same as agents. Auto-name uses the existing
  `get_next_auto_name()` path so bare `%proc::` still wait-able via the allocated
  name.
- `%id(parent, suffix)` / `family=` on a `%proc` segment is a **v1 error** with a
  pointer to `sase monitor start`. Family-attached proc shells are monitors; this
  feature is the stand-alone case. Do not quietly start a monitor.
- Classification happens after `%alt` split, so mixed agent/proc fan-out works.

A solo (non-swarm) prompt that contains `%proc` is just a one-segment swarm.

### Embedded swarms

If `#setup` is itself a multi-segment xprompt whose first body segment is `%proc`,
the call-site segment *becomes* a proc launch and follow-ups append. That is
consistent with today's "first segment at the call site, rest appended" rule. It is
surprising only if authors expected `#setup` to expand to prose. Document it; do not
special-case it.

---

## 5. Syntax

### 5.1 Single-line

Parenthesized form, xprompt arg grammar (quotes, `[[...]]`, backticks):

```text
%proc("just check")
%proc(bash="just check")
%proc(python="from sase.workspace_provider.lease import acquire_operational_lease")
%proc:just check
```

Semantics:

| Spelling | Language | Notes |
| --- | --- | --- |
| positional string | bash | `%proc("…")` and `%proc:…` |
| `bash=` | bash | Same as positional; explicit |
| `python=` | python | SASE interpreter; see §7 |
| `bash=` and `python=` together | error | Mutual exclusion |
| positional and `bash=`/`python=` | error | Mutual exclusion |
| `%proc` with no body | error | Unlike `%hide`, a proc is not a flag |
| `%proc+` | error | No plus form |

Colon form is the one-liner people will actually type in a swarm row:
`%id:fmt %proc:just fmt`.

Optional kwargs worth allowing in v1, all actually optional (CLI rule: options are
never required):

| Kwarg | Default | Purpose |
| --- | --- | --- |
| `timeout=` | none | Same duration grammar as `%wait(time=5m)` |
| `cwd=` | launch cwd, or leased checkout if `workspace=true` | |
| `workspace=` | unset/false | Opt-in operational lease; see §8 |
| `label=` | derived from script preview | Proc label |

`idle_timeout=` can wait; it is monitor-shaped and not required for the motivation.

Do not require `--reason`. Monitors required it as facade policy and already violate
`cli_rules.md`'s "options must not be required". `%proc` should not repeat that.

### 5.2 Multi-line: fence after `::`

Intended spellings:

````text
%id:prep %proc::
```bash
just install
just check
```
````

````text
%id:prep %proc::
```
# no language ⇒ bash
sase workspace …   # illustrative; actual claim APIs are in §8
```
````

````text
%id:prep %proc::
```python
from pathlib import Path
print(Path(".").resolve())
```
````

Parser (shared with the `code` input type, §6):

1. After `%proc` / a `code`-typed `::`, allow `::` followed by horizontal
   whitespace, **or** `::` at end-of-line. Do not require the historical space.
2. Skip blank lines.
3. The next non-empty line must be a CommonMark opening fence (` ``` ` or `~~~`,
   length ≥ 3). Otherwise `DirectiveError`: `%proc::` expects a fenced code block.
4. Language = first info-string token, lowercased. Empty ⇒ `bash`.
5. Capture ends at the matching closer. Trailing prose before the next directive is
   an error on `%proc` (segment remainder rule) and is ordinary leftover prompt on a
   `#name::` xprompt whose `code` input already closed.
6. Unclosed fence is a `DirectiveError`, never a silent run to EOF.

Language map for *execution* (the type stores the raw token; `%proc` maps it):

| Info token | Runner |
| --- | --- |
| missing, `bash`, `shell` | `/bin/bash` |
| `sh` | `/bin/sh` (explicit opt-out of bash) |
| `python`, `py`, `python3` | SASE `sys.executable` |
| anything else | error in v1 |

v1 should not silently execute `ruby` / `node`. The type can still *parse* those
fences for future `#name` inputs; `%proc` refuses them.

Do **not** feed `%proc::` through `preprocess_directive_double_colon_shorthand`'s
clan-summary path. That path rewrites to `summary=[[text]]` and terminates on the
next directive. `%proc` needs fence-bounded capture *before* fenced-block
protection, using `fenced_block_details`.

`::` plus an unfenced script body (`%proc::\njust check`) should error, not default
to bash. The whole point of the fence is an unambiguous terminator that may contain
blank lines, `#` headings, and `%wait` strings.

### 5.3 Combining `::` with kwargs

Legal:

```text
%proc(timeout=30m, workspace=true)::
```bash
just check-full
```
```

Illegal: `::` plus `bash=` / `python=` / positional script (two bodies). Mirror
`%clan` "cannot combine `::` with explicit `summary=`".

### 5.4 Alias

`%p` is free in the directive alias table (`#p` is the *xprompt* alias for
`#propose`, a different prefix). Recommend **`%p` → `%proc`**, matching `%i`/`%w`.
Put it in both Python and the Rust `DIRECTIVES` alias field so completion stays
honest.

---

## 6. The `code` input type

This is the general-purpose piece, and it should land *with* `%proc` rather than as
a later cleanup. `%proc::` is just the first consumer.

### Shape

```python
class InputType(Enum):
    ...
    CODE = "code"  # fenced block; language + source
```

Runtime value is structured, not a bare string:

```python
@dataclass(frozen=True)
class CodeValue:
    language: str  # canonical, default "bash"
    source: str    # fence content, no surrounding fences
    info_string: str | None = None  # raw info string if present
```

Jinja/`str(value)` renders `source` so existing templates that interpolate an
argument do the useful thing. `{{ script.language }}` is available when authors
want it.

Validation:

- Binding from a fence (the `::` form, or a positional whose trimmed value is a
  single fence) → parse via `fenced_block_details`.
- Binding from a plain string (single-line `#name:echo hi` on a `code` input) →
  `CodeValue(language="bash", source=value)` so one-liners still work.
- `[[ ```python\n…\n``` ]]` inside parens → same fence parse.
- Multiple fences in one value → error.

### Why not reuse `text`

`text` cannot grow a language field without breaking every existing text input.
Silent "if it looks like a fence, treat as code" would mis-parse documentation
examples inside `text` arguments.

### Surfaces that must change together

| Surface | File | Failure if skipped |
| --- | --- | --- |
| Runtime enum + convert | `src/sase/xprompt/models.py`, `loader_parsing.py` | `#name` with `type: code` ignored or treated as line |
| Rust catalog parse | `sase-core` `xprompt_catalog.rs::parse_input_type` | unknown → `line` |
| Rust frontmatter schema | `editor/frontmatter.rs` `InputType::ALL` | LSP / TUI panel omit `code` |
| Gate input fragments | `notification_gates/model_inputs.py` | only if gates accept `code`; can wait |
| `%proc` `::` capture | new helper used by directive shorthand | first consumer |

v1 does **not** need every xprompt to start using `type: code`. It needs the type to
exist so `%proc` is not a one-off grammar and so a later `#run_script::` just works.

### Directive contract additions (Rust)

Add a `DirectiveSyntaxForm::DoubleColon` (or document `::` under parenthesized + a
new form) so `%proc` completion advertises:

- colon / parenthesized / double-colon
- keywords `bash`, `python`, `timeout`, `cwd`, `workspace`, `label`
- positional role `FreeText` (script) with language implied

`tests/test_xprompt_directive_contract.py` will fail until Python and Rust agree.
That test is the right ratchet.

---

## 7. How the command actually runs

Compile to `ProcSubmitRequest.argv`. Never `shell=True` at the supervisor (monitors
historically did; the merge path already compiles `-c` to argv). Persist the
**logical** command in `request.command` so fingerprints do not include wrapper
noise.

### Bash

```text
["/bin/bash", script_path]
```

or `["/bin/bash", "-c", source]` for tiny one-liners. Prefer a file for anything
that came from a fence: quoting, `sys.argv`, and `$0` all behave. Write the file
under the artifacts dir (or proc runtime dir) at mode `0600`, and put that path in
argv. `/bin/bash`, not `/bin/sh`, unless the fence said `sh`.

Environment:

- copy the host/launch env
- prepend `dirname(sys.executable)` to `PATH` (same as workflow bash steps) so
  `sase` resolves
- set `SASE_PROC_ID`, `SASE_SHELL_NAME`, `SASE_PROJECT` when known,
  `SASE_ARTIFACTS_DIR` when artifacts exist
- **do not** set `SASE_AGENT=1` (this is not an LLM run). `SASE_AGENT_NAME` may
  equal the shell name for provenance; do not copy a *parent* agent's identity.
  Monitors scrub parent identity for a reason (`sase bead work` running inside a
  monitor).

### Python (yes, inject SASE's environment)

```text
[sys.executable, script_path]
```

`sys.executable` is the SASE virtualenv interpreter. That is the entire
justification for `python=`:

```python
from sase.workspace_provider.lease import (
    acquire_operational_lease,
    submit_via_lease,
)
from sase.procs.request import ProcSubmitRequest
```

`python -c` works for one-liners and is what workflow steps use; fences should still
become files so `__file__`, encodings, and tracebacks are sane.

Do **not** reimplement `import sase` by mutating `PYTHONPATH` if the launching
interpreter already has the package (editable install in the workspace venv). Do
**not** use the system `python3`. A `%proc(python=...)` that cannot `import sase`
should fail at start with an explicit message, not at `ImportError` three lines
into user code — cheap check: `sys.executable -c "import sase"` during compile, or
trust the launcher's interpreter and document the requirement.

Optional sugar, not v1: auto-inject a prelude `from sase.workspace_provider.lease
import acquire_operational_lease`. Better to keep scripts explicit; a tiny
`#proc/python` xprompt can wrap later.

### Timeouts

Pass through `ProcSubmitRequest.timeout_seconds` (integer milliseconds on the wire;
Python currently still has `timeout_seconds: int | None` on the request object —
match whatever the live `ProcWire` field is, and do not reintroduce `f64` if the
store still derives `Eq`). Unset means no total timeout, same as `sase proc run`.

### Output

Proc log + artifacts dir. Head+tail capture like monitors is enough for later
`sase var` / follow-up; v1 does not need `--next`. A Python script that wants to
hand values to a later agent should write them with `sase var set` only if we
deliberately allow that CLI under `SASE_ARTIFACTS_DIR` without `SASE_AGENT=1`.
Safer v1: scripts write files in `SASE_ARTIFACTS_DIR` and later agents `%wait` then
`@file` / read. `sase var` as a follow-up is attractive but it currently requires
`SASE_AGENT=1`. Recommend a tracked follow-up, not a silent exception.

---

## 8. Workspace claims

Motivation: "run commands that claim (and release when appropriate) sase project
workspaces."

Two honest interpretations:

1. **The command claims** — Python/Bash calls lease APIs or a future `sase
   workspace` CLI; `%proc` just keeps the process alive long enough and does not
   itself take a RUNNING field.
2. **The directive claims** — `%proc` with a project context acquires an
   operational lease, `cwd` becomes the checkout, settlement releases.

Both are useful. Always doing (2) would lease a workspace for `%proc:sleep 5`,
which fights the unified pool. Never doing (2) would make the common case ("run
`just check` in a real sase clone") require boilerplate Python.

### Recommended policy

| Segment | Claim |
| --- | --- |
| `%proc` without project ref and without `workspace=` | none; cwd = launch cwd |
| `%proc(workspace=true)` | `acquire_operational_lease` + `submit_via_lease` for the segment's project |
| `#gh:sase %proc(...)` without `workspace=` | **no auto-lease**; the ref only selects project attribution / later opt-in |
| `#gh:sase %proc(workspace=true)` | lease that project |
| command-owned `acquire_operational_lease` inside Python | allowed; see leak note |

`#gh:` / `#git:` on a proc segment:

- **does** set `project` / `cl_name` on the proc row (and the lease target)
- **does not** inject rollover xprompts (`#commit`, `#pr`, `#propose`)
- **does not** run `normalize_default_vcs_workflow_segment` as if this were an
  agent

That last bullet is easy to get wrong: `spawn_segments_into` currently normalizes
bare segments to `#git:home` and resolves VCS workflow wrapping for every segment.
Proc classification must happen early enough to skip wrapping.

### Claim-leak hazard (command-owned)

If a Python script acquires a lease in-process and the supervisor SIGKILLs it, the
script's `finally` does not run. Proc settlement only releases claims listed in
`workspace_claim` on the request sidecar. Therefore:

- Directive-owned leases are safe (policy is on the sidecar before exec).
- Command-owned leases are safe only if the script **registers** the policy onto
  the live proc (a small helper, e.g. `attach_operational_lease_to_current_proc`)
  or uses a CLI that does. v1 should ship that helper with `python=`; without it,
  documenting "use `workspace=true`" is the honest answer.

Do not transfer an agent-held workspace onto a stand-alone proc. That is monitor
semantics (`after_ack` claim transfer from the starter). Stand-alone shells have
no starter agent.

---

## 9. Directives that should work on a `%proc` segment

| Directive | v1 | Notes |
| --- | --- | --- |
| `%id` / `%i` | **yes** | Name; auto-name if omitted |
| `%wait` / `%w` | **yes** | Agents, beads, `time=`, `runners=`, `priority=`, tribes, `#t:` |
| `%hide` / `%h` | **yes** | Same Agents-tab hide bit |
| `%repeat` / `%r` | **yes if cheap** | Repeat expansion already injects `%id`/`%wait` chains; classify after it |
| `%clan` / `%c` | later | Grouping procs into a clan is useful; not required for the motivation |
| `%id(..., tribe=)` | later | Same |
| `%auto` / `%model` / `%effort` / `%final` | **no** | No LLM, no plan gate, no finalizer selector |
| `%alt` | **indirect** | Allowed around the segment; not inside the script body |
| `%id(parent, suffix)` / `family=` | **error** | That is a monitor |
| `#fork` | **no** as producer | A proc has no chat history worth forking; waiters may still `#fork` *other* agents |

`%wait` on the proc segment uses the same deferred-start marker (`waiting.json`) so
wait-checks / `ready.json` work. The difference is the body that runs after ready:
`submit_proc_request` instead of the provider runner. Implementation sketch:

1. Create artifacts dir + `agent_meta.json` immediately (name is reserved, waiters
   can resolve the target).
2. If `%wait` / `#t:` present, write `waiting.json` and **do not** take a runner
   slot.
3. A small starter (wait-checks chop hook, or a dedicated non-LLM waiter) on
   `ready.json` / direct resolution calls `submit_proc_request` with
   `artifacts_dir` set.
4. If no wait, submit immediately.
5. Settlement writes `done.json` (`completed`/`failed`) **and** the proc row, in
   the existing checkpoint order (`claim_settled` before `artifacts_settled`).
   `%wait` waiters must not observe `completed` before the claim is released.

Do not hold the launch barrier closed for the entire wait — that ties a supervisor
pid up for a time floor. Wait first, then spawn.

`%wait(runners=N)` on a proc segment is well-defined (do not start the command
until the LLM runner count is ≤ N) but is rarely what authors want for a
workspace-claiming setup job. Support it because the directive says so; default
priority can stay 10.

Failed procs must **not** count as wait-success. A waiter for `%wait:prep` stays
blocked if prep exited nonzero — same as a failed agent. Surface the failure on
the Agents tab so it does not look like a hung wait.

---

## 10. Alternatives considered

### `%proc` as an xprompt (`#proc`) instead of a directive

Xprompts expand to prompt text. Directives are stripped and change launch. A
command that must never reach a model is a directive. `#proc` would also collide
with the mental model of `#commit`/`#pr` (prompt parts / workflows). Rejected.

### YAML workflow `bash:` / `python:` steps as the swarm member

Already exist, already inject PATH / `sys.executable`. They are not sase shells,
cannot `%wait`, cannot sit in a `---` swarm next to `%id:coder`, and do not claim
workspaces as first-class occupancy. Keep them; do not stretch them.

### Always use `/bin/sh -c` like monitors

The request is explicit: default Bash, and `python=` as a first-class language.
Compiling to argv is also the direction the proc/monitor merge already took.
Rejected as the `%proc` default; `sh` remains available via the fence info string.

### Auto-lease whenever a VCS ref is present

Attractive, but `#gh:sase` on a swarm is often *inherited* onto follow-up segments
(`prepend_inherited_vcs_ref`). An inherited ref would then lease a workspace for
every proc follow-up, including `sleep` and `sase proc`-style waits. Opt-in
`workspace=true` is noisier and correct.

### Feature-flag the whole directive off by default

New user-reaching launch behavior. The flags architecture report says unstable
launch paths start off. Recommend a boolean flag (name bikeshed: `proc_directive`)
created with `sase flag new` when implementation starts, default off, covering
parse-and-launch together (do not parse `%proc` into a known directive while
launch still treats it as leftover prompt — that would strip the script and still
send the remainder to a model). Unknown directives are left in the prompt today;
making `%proc` known without implementing launch is actively dangerous.

---

## 11. Suggested implementation sequence

Not a plan; a dependency order that avoids the dangerous intermediate states.

1. **Names.** Bare `shell_name` without a calling agent is legal and fully
   qualified. Inside an agent, bare names still qualify as `agent--role`. Tests
   around `qualify_proc_shell_name` and `sase proc run -N`.
2. **`code` type + fence-after-`::` parser.** Shared helper. Unit tests for
   default language, info-string, unclosed fence, `::\n`, `:: ``` `, inner `%`/`#`.
   Rust `parse_input_type` + frontmatter `InputType::ALL` in the same slice.
3. **`%proc` parse only**, behind the flag, mapping to a structured
   `ProcDirective` on `PromptDirectives` (`language`, `source`, kwargs). Unknown
   remainder detection. Rust `DIRECTIVES` row + contract test.
4. **Launch classifier** in `spawn_segments_into` / fan-out slots: proc vs agent.
   Skip VCS rollover wrapping. Create artifacts. Submit proc. Settlement writes
   `completed`/`failed` `done.json` (new branch next to `settle_monitor_artifacts`).
5. **`%wait`.** waiting.json + existing wait-checks; no runner slot; submit on
   ready. Tests: agent waits for proc; proc waits for agent; proc waits for
   `time=`; failed proc does not release waiters; `%wait` does not complete before
   claim settlement.
6. **`workspace=true`** via `submit_via_lease`. Helper for command-owned Python
   leases. Tests: kill during command releases lease; primary checkout never used.
7. **Docs / glossary / memory.** Proc Shell entry: stand-alone vs monitor.
   `docs/xprompt.md` directive table and completion matrix. Memory update still
   needs explicit user permission at implementation time.

`sase-core` must change in steps 2–3 (input type + directive contract) and should
own wait-success outcome documentation if we add a dedicated `proc_completed`
outcome later. v1 should **reuse** `completed` rather than extend
`WAIT_SUCCESS_OUTCOMES` — less core churn, same semantics.

---

## 12. Risks

1. **Known-but-unimplemented `%proc`.** If the name is added to
   `_KNOWN_DIRECTIVES` before launch classification, the extractor strips the
   script and the segment becomes an LLM prompt (possibly empty). Flag and
   classifier must land together.
2. **`:: ` space requirement** leaking into `%proc`. Authors will write
   `%proc::\n```bash`. If only the clan preprocessor is extended, this silently
   fails to parse and `%proc` is left in the prompt (unknown-directive behavior)
   or errors poorly. Fence capture must be a first-class scan.
3. **Inherited `#gh:` + auto-lease** (see §8). Inherited refs are the trap.
4. **Runner-slot occupancy.** Creating `ace-run` artifacts without marking the
   row as non-occupying can stall the LLM pool. Reuse monitor-aware occupancy
   logic: stand-alone proc shells occupy **zero** LLM slots.
5. **Wait on `monitored` vs `completed`.** Copy-pasting monitor settlement would
   make `%wait:prep` hang forever. Stand-alone settlement must not write
   `outcome: monitored`.
6. **Name lock.** Active `(project, shell_name)` uniqueness already exists. A
   wedged `%id:prep` blocks the next `%id:prep`. Collision errors must name
   `sase proc show prep` / `sase proc kill prep`.
7. **Python `-c` quoting** in swarm one-liners. Compile to argv/files; never
   wrap the user's string in another shell.
8. **Glossary drift.** "Proc shell = belonging to a sase agent" stays true;
   "family-attached proc shell = monitor" becomes the narrowing. Implementation
   must file a `memory` task (or update memory with user permission) or agents
   will keep treating every proc shell as a monitor.

---

## 13. Open questions for the owner

These do not block the recommendation; they change only surface spelling.

1. **Is `%p` the alias?** Recommended yes. `#p` remains `#propose`.
2. **Should `sase proc run -N prep` from a terminal create artifacts** (wait-able)
   or only a proc-store name? Recommended: CLI bare `-N` is a named proc without
   artifacts (today's proc UX); `%proc` is the wait-able one-shell agent. Mixing
   those later is easy; forcing artifacts onto every CLI named proc is not.
3. **`workspace=true` vs `lease=true` vs a `%workspace` directive.** Recommended
   `workspace=true` on `%proc` only, v1. A general `%workspace` is a different
   feature.
4. **Should a successful proc publish `sase var` snapshots?** Useful for
   `%wait:prep` then `{{ agents.prep.status }}`. Requires relaxing
   `SASE_AGENT=1`. Defer.
5. **Glyph / Agents-tab presentation.** Reuse monitor ⚙ or a distinct mark so a
   solo proc is not mistaken for a hung LLM row. Presentation-only; decide at
   implementation.

---

## Recommended solution

**Treat a `%proc` swarm segment as a one-shell sase agent whose shell is a proc
shell, not as a monitor, and not as a proc-store row that `%wait` must learn to
see.**

Concretely:

1. **Identity.** Allow a bare `shell_name` when there is no calling sase agent.
   `%id:prep %proc` stores `shell_name="prep"` and artifacts `name="prep"` with no
   family role. Inside an agent, bare names still become `agent--role`. Family
   attach on `%proc` is a v1 error pointing at `sase monitor`.

2. **Classifier.** After swarm, alt, and repeat expansion, `%proc` means "this
   slot is a proc-shell launch". Strip directives, compile argv, skip commit
   rollover, skip LLM runner slots. Remainder text is an error.

3. **Syntax.**
   - Single-line: `%proc:just check`, `%proc("just check")`, `%proc(bash=...)`,
     `%proc(python=...)`.
   - Multi-line: `%proc::` then exactly one fenced code block; missing language
     is Bash. Newline after `::` is legal. Do not reuse clan-summary `:: `
     capture.
   - Alias `%p`. Optional `timeout=`, `cwd=`, `workspace=`, `label=`.

4. **`code` input type.** Structured `{language, source}` value; default
   language bash; same fence parser as `%proc::`. Add it to Python `InputType`
   and Rust `parse_input_type` / frontmatter schema in the same change as the
   directive contract row. Future `#name::` + fence is then a config file, not
   another parser.

5. **Execution.** Bash → `/bin/bash` + script file + SASE bin on `PATH`. Python
   → **the launching SASE `sys.executable`** + script file so `import sase`
   works. Persist argv; use existing `submit_proc_request` supervisor, ack, and
   settlement.

6. **Wait.** Artifacts + `waiting.json` + existing wait index. Settlement writes
   `done.json` `completed`/`failed`, never `monitored`. Waiters block on
   success. Claim release happens before that outcome is visible.

7. **Workspaces.** Default no lease. `%proc(workspace=true)` uses
   `submit_via_lease`. `#gh:`/`#git:` select the project but do not auto-lease
   (inherited swarm refs). Ship a Python helper that attaches a command-owned
   lease to the current proc's settlement policy so SIGKILL cannot leak a
   RUNNING claim.

8. **Flag.** Parse and launch behind one boolean feature flag so `%proc` can
   never be stripped as a "known directive" while still launching an LLM.

This reuses the named-proc store, operational leases, wait-dependency index, swarm
fan-out, and fenced-block scanner. It adds three small, orthogonal pieces: bare
stand-alone names, a fence-bounded `code` type, and a launch classifier that is
allowed to not start a model.

The monitor path stays the family-attached story. `%proc` is the missing one-shell
story. Together they match the taxonomy the 2026-08-14 report already wrote down:
**a sase agent is a sequence of sase shells.**
