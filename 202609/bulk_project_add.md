---
create_time: 2026-09-03
updated_time: 2026-09-03
status: research
---

# Adding Projects In Bulk From The Admin Center Projects Tab

**Research question:** let users add new SASE projects *in bulk* from the **Projects** tab
of the SASE Admin Center (`#` then `4`), with excellent completion for the
organizations/repos they are most likely to pick, in a VCS-agnostic way that future
workspace-provider plugins get for free. As part of the same change, stop auto-enabling
new projects that a VCS xprompt workflow ref creates for a repo this machine does not yet
know. What is the best UX, and what is the right way to build it?

**Scope:** `sase` at master `9e2d95bb0`, plus the linked `sase-github` plugin checkout
(opened via `/sase_repo`). Read paths: the whole `project_*` modal family that implements
the Projects tab, the four-layer VCS completion stack (`xprompt/vcs_ref_completion.py`,
`xprompt/vcs_repo_completion.py`, `xprompt/vcs_project_completion.py`, and their
`ace/tui/widgets/` presentation halves), the workspace-provider hookspec and both
in-tree/out-of-tree implementations, the launch-time project-enablement path, the
workspace claim gate, `sase project`'s CLI surface, and the `plugins_browser_*` bulk
install flow used as the house precedent. Reference memory consulted: `cli_rules.md`,
`tui_perf.md`, `sase_flags.md`. No TUI instrumentation was collected; every structural
claim below is cited to source.

---

## Executive summary

**The feature is almost entirely assembly, not invention.** SASE already has a
provider-agnostic, cached, ranked, error-classified repository catalog with a proven TUI
presentation layer — it is the `#gh:sase-org/` completion menu. It already has a
multi-select project list with `m`/`u` marks whose `a` (enable) key already operates on
the marked set. It already has a canonical "browse a remote catalog, mark many, preview,
install as one tracked proc" pane in the Updates tab. Bulk project add is the join of
those three, and the join key is one optional dataclass field.

Three findings drove the recommendation:

- **The catalog stack is already VCS-agnostic and already headless.**
  `ws_list_ref_namespaces()` and `ws_list_repo_candidates()`
  (`src/sase/workspace_provider/_hookspec.py:209,202`) are pluggy hooks; the host-side
  `fetch_repo_candidates()` adds a memo + on-disk TTL cache with stale-on-error fallback
  (`src/sase/xprompt/vcs_repo_completion.py:305`), `peek_cached_repo_candidates()` gives a
  never-touches-the-provider hot path (`:369`), and the candidate/row builders in
  `ace/tui/widgets/vcs_repo_completion.py` and
  `ace/tui/widgets/_prompt_input_bar_completion_rows_vcs.py` are already decoupled from
  the prompt bar. A new pane consumes all of it unchanged.

- **"Add a project" is really "adopt a project", and adoption already has an encoding.**
  Every discovery surface — the `+` catalog (`vcs_project_completion.py:_build_entries`),
  the launch pickers (`project_discovery.py:41`), `sase project list` — keys off
  `PROJECT_STATE: enabled`. So bulk add is bulk *enable* over a row set that mixes local
  records with provider catalog entries. That collapses the new feature onto the pane's
  **existing** `m`/`u`/`a` gesture instead of inventing a verb.

- **The auto-enable "bug" is an absence, not a statement.** Nothing enables a new project.
  `_resolve_repo_path_ref` writes a ProjectSpec containing only `WORKSPACE_DIR`
  (`sase-github` `workspace_plugin.py:1650`), and *missing* `PROJECT_STATE` means enabled
  (`docs/project_spec.md:84`). Fixing it is one host-side write — but that write collides
  with the workspace claim gate (`running_field/_claim.py:39`) and with launch-time
  re-adoption (`agent/launch_projects.py:67`), so it is a four-part change plus a `sunset`
  flag, not a one-liner. §5 works this out.

**Recommendation (§6): a fourth Projects sub-tab, `Add`, whose single input is a provider
ref *minus the `#`* (`gh:sase-org/`) driven by the identical completion helpers the prompt
bar uses; whose rows are a three-state reconciliation of that catalog against local
records (`enabled` / `disabled` / `new`); and whose commit key is the pane's existing `a`,
routed through a new `sase project add` CLI as one tracked proc.** The only provider
contract change is one optional field, `VcsRepoEntry.workspace_dir`, which is the
reconciliation join key and simultaneously lets us delete a hardcoded GitHub path guess
that currently sits in a "provider-agnostic" host module (`_parsing_vcs_refs.py:138`).

---

## 1. What already exists

### 1.1 The provider contract

Two hooks already cover discovery, and both are documented as completion-path hooks:

```python
@hookspec(firstresult=True)
def ws_list_repo_candidates(
    self, workflow_type: str, namespace: str
) -> VcsRepoCandidates | None:
    """List repository completion candidates for a VCS namespace."""

@hookspec(firstresult=True)
def ws_list_ref_namespaces(self, workflow_type: str) -> VcsRefNamespaces | None:
    """List org/group-style namespace candidates for a workflow ref root.

    This hook runs on an interactive completion path and must use only
    fast local data such as project records or config.
    """
```

`src/sase/workspace_provider/_hookspec.py:202-219`

Their payloads are already rich enough to rank and to render:

- `VcsRepoEntry(name, ref, description, visibility, is_fork, is_archived, pushed_at)`
  — `_hookspec.py:68`
- `VcsNamespaceEntry(name, description, kind_label)` — `_hookspec.py:96`

A third hook, `ws_peek_ref(ref, workflow_type)`, is the **read-only** lookup, spec'd with
an explicit no-mutation contract ("must not clone repositories, create project records,
write files, spawn network subprocesses", `_hookspec.py:191`). Its mutating twin
`ws_resolve_ref` is the one that materializes a project. That split is exactly the split
this feature needs: peek for the browse list, resolve for the commit.

**The GitHub implementation** shells `gh repo list <owner> --json
name,description,visibility,isArchived,isFork,pushedAt --limit <max_repos>` with a
non-interactive env and `stdin=DEVNULL` (`sase-github` `workspace_plugin.py:1216-1260`),
and classifies failures into `auth` / `not_found` / `network` / `tool_missing` / `unknown`
with actionable messages ("run 'gh auth login'"). Namespaces come from enabled project
records (counted, "3 projects") plus the `github_orgs` config key
(`workspace_plugin.py:1445-1478`).

**The bare-git implementation deliberately implements neither hook**
(`plugins/bare_git_workspace.py` declares only `ws_get_workflow_metadata`,
`ws_detect_workflow_type`, `ws_get_change_label`, `ws_resolve_ref`, `ws_submit`,
`ws_setup_workflow`, `ws_get_workspace_directory`, `ws_prepare_mail`,
`ws_get_workspace_name`, `ws_format_commit_description`). `#git` refs are *paths* or
project names, not `namespace/repo`. **Any design that assumes a catalog exists is not
VCS-agnostic** — it must degrade to a plain ref box, which is what bare-git users get
today.

### 1.2 The host-side completion stack

Four headless modules, none of which import Textual:

| Module | Provides |
| --- | --- |
| `xprompt/vcs_ref_completion.py` | namespace candidates + ref-root trigger parsing + `apply_vcs_ref_selection(..., chain=True)`, which appends `/` so repo completion takes over |
| `xprompt/vcs_repo_completion.py` | `fetch_repo_candidates` (memo + disk TTL cache, default 600 s / 200 repos, stale-on-error), `peek_cached_repo_candidates` (provider-free), `filter_vcs_repo_entries` |
| `xprompt/vcs_project_completion.py` | the enabled project/Patch catalog behind `+` |
| `ace/tui/widgets/vcs_{ref,repo}_completion.py` | `CompletionCandidate` builders, loading/empty/error placeholders, panel titles |

Ranking already exists. `_repo_sort_key` sorts prefix matches first, then by `pushed_at`
descending, then by name (`vcs_repo_completion.py:548`). Row rendering already badges
`[private]` / `[fork]` / `[archived]` and truncates descriptions
(`_prompt_input_bar_completion_rows_vcs.py:123`).

The off-thread pattern is established too: paint from `peek_cached_repo_candidates` or a
loading placeholder immediately (`_file_completion_open.py:135`), then dedupe a keyed
thread worker (`_schedule_vcs_repo_completion_fetch`, `_file_completion_workers.py:121`).

### 1.3 The Projects tab

`ProjectsPane` (`ace/tui/modals/projects_pane.py:129`) hosts a three-tab strip
(`Projects · Repos · Workspaces`, `]`/`[` to cycle) over a `ContentSwitcher`. The Projects
sub-tab already has everything a bulk operation needs:

- marks: `m` toggle / `u` clear, with `_target_records()` returning **the marked set if
  non-empty, else the highlighted row** (`project_list_controller.py:254`);
- bulk lifecycle: `a` / `d` / `Ctrl+D` all run through `_target_records()`, with
  successful rows clearing their marks and failed rows staying marked
  (`docs/ace.md:2907`);
- a filter input, adaptive jump hints (`'`), a detail panel with a 150 ms debouncer, and
  per-sub-tab session state (`config_center_session.py`).

Keys currently bound (`ProjectsPaneKeymaps`, `app_keymaps.py:263`; mirrored in
`default_config.yml:388`): `j k / ] [ m u e A a d Ctrl+D F Enter R r w ' p Esc c`.
Free single letters include `n N i I s t x z o y b f v l h`.

### 1.4 The bulk-operation house style

The Updates tab's plugin browser is the precedent for exactly this shape: browse a remote
catalog, mark many, then `plan_install_many()` off-thread → `PluginActionConfirmModal`
preview → `execute_install_many()` as one tracked proc → per-item outcome toast
(`plugins_browser_install.py:100-140`, `plugins/operations.py`). The concurrent
`projects_tab_init_ux` research reached the same conclusion independently for `sase init`
and added the rule that the TUI **shells out to the CLI** rather than importing the
coordinator, so one code path serves both.

`tui_perf.md` rule 3 mandates tracked procs for slow user-initiated work, and rule 11
names our exact hazard: *"provider `resolve_ref` clones repos and allocates project
records"* — it must never be reachable from a keystroke path.

---

## 2. Three constraints

**C1 — Adoption is `PROJECT_STATE`, and every consumer already agrees.** The `+` catalog
builds from `list_project_records(projects_dir, "enabled")`
(`vcs_project_completion.py:_build_entries`); launch pickers drop anything whose
`state != "enabled"` (`project_discovery.py:41`); `sase project list` defaults to
`enabled` (`parser_project.py:127`). There is no second axis and no need for one.

**C2 — Materializing a project is slow, networked, and mutating.** `resolve_ref` on an
unknown `owner/repo` clones the repo (`workspace_plugin.py:1645`), allocates a canonical
project name, writes the ProjectSpec, and allocates a display-name alias
(`_ensure_useful_repo_name`, `:1548`). Multiply by a marked set of ten. This cannot run in
the TUI process (rule 11) and cannot run without a confirmation showing what it will do.

**C3 — The catalog is unbounded and network-flaky.** `max_repos` defaults to 200
(`vcs_repo_completion.py:21`) and the GitHub provider passes it straight to `gh --limit`.
The surface must show truncation honestly, must render the five classified error kinds
rather than an empty list, and must be usable while stale (the cache layer already returns
`stale=True` payloads on provider failure, `:357`).

---

## 3. The UX design space

Four options were considered against the four requirements: (R-bulk) select many at once,
(R-complete) excellent org/repo completion, (R-agnostic) new providers work for free,
(R-onboard) usable on a machine with zero local project records.

### Option A — an "add one project" prompt (`n` → text input → Enter)

Rejected outright: fails R-bulk. Worth noting only because it is the natural first
instinct and because the *input* it implies survives into the recommendation.

### Option B — a modal picker over the catalog

`n` opens a `ModalScreen` shaped like `InventoryProjectPicker`
(`inventory_project_picker.py`): title, filter input, `OptionList`, hints.

Pros: self-contained; matches an existing modal the user already knows; no strip change.

Cons that decided against it: a 200-row network-backed list in a modal has no room for a
detail panel, and the pane it covers already provides marks, jump hints, a filter, a
detail panel, and per-sub-tab session state that the modal would have to re-implement.
Modals in this app are for *decisions* (confirm, pick one); this is *browsing*.

### Option C — a scope filter on the existing Projects sub-tab

Cycle the Projects list between `Enabled` → `All` → `Available: <namespace>`. Bulk add
then *is* bulk enable: mark rows, press `a`. Maximally elegant on paper — one list, one
gesture, zero new concepts.

Rejected on two concrete grounds:

1. **Corpus mixing.** The Projects list is a disk-backed, always-available, instantly
   loadable list. Splicing a network-backed, auth-dependent, 600 s-cached corpus into it
   means every existing action needs per-row applicability (`e`, `A`, `c`, `d`, `Ctrl+D`,
   `r`, `w`, `F` are all meaningless on a catalog row), and the pane's summary/status/
   detail lines need to describe two different things.
2. **`]`/`[` is taken** by sub-tab cycling, so the scope cycle needs a new key anyway —
   giving up the main advantage.

Option C's *gesture* is right; its *container* is wrong.

### Option D — a fourth sub-tab, `Add` — **recommended**

`Projects · Repos · Workspaces · Add`. The strip, the cycling keys, the filter, the marks,
the jump hints, and the session state all come for free from the pane. The corpora stay
separate, so each list keeps one latency class and one set of applicable actions. The
commit key is Option C's `a`.

The `admin_center_updates_tab_unification` research argues *against* splitting a surface
along an axis users do not care about, so this addition has to answer that critique
directly. It does: `Add` differs from the other three sub-tabs in corpus (remote provider
catalog vs. local records), in latency class (network + 600 s cache vs. disk), and in verb
(adopt vs. manage). That is a real axis, not a subsystem-ownership artifact.

### The insight that makes Option D more than a picker

The `Add` sub-tab should not show "repos you don't have". It should show a
**reconciliation** of the provider catalog against local records, in three states:

| Status | Meaning | Cost of `a` |
| --- | --- | --- |
| `enabled` | already adopted on this machine | none (no-op, reported) |
| `disabled` | ProjectSpec exists, not in the working set | **instant** — one `set_project_state_locked` |
| `new` | in the provider catalog only | clone + register + enable |

This matters more after §5 lands. Once one-off `#gh:owner/repo` launches stop
auto-enabling, the `disabled` band becomes *"repos you have already worked on here but
never adopted"* — the highest-intent, zero-cost rows in the entire surface. Without
reconciliation the user would have to find those on the Projects sub-tab and the `Add`
sub-tab would happily offer to re-clone them.

---

## 4. "Most likely to select": what the ranking signal actually is

The user's stated scenario — onboarding a new machine — is the hard case, because a fresh
machine has **zero local records**, so every locally-derived signal is empty. Ranking
therefore has to work in two regimes.

**Signals available, and where each survives:**

| Signal | Source | Fresh machine? |
| --- | --- | --- |
| Local `disabled` records | `list_project_records(..., "all")` | no |
| Namespaces from local records (with project counts) | `ws_list_ref_namespaces` band 1 | no |
| Namespaces from `github_orgs` config | `ws_list_ref_namespaces` band 2 | **yes** (config is chezmoi-synced) |
| Repo recency | `VcsRepoEntry.pushed_at` → `_repo_sort_key` | **yes** |
| Fork / archived / visibility | `VcsRepoEntry` badges | **yes** |
| VCS xprompt MRU | `~/.sase/vcs_xprompt_mru.json` | no |

The fresh-machine path therefore runs on exactly two things: **`github_orgs` from synced
config, and provider-side push recency.** That is genuinely enough — `gh repo list <owner>`
returns the viewer-visible repos and the host re-ranks them by `pushed_at` descending —
and it should be documented as the onboarding seed, because it makes `github_orgs`
load-bearing in a way that is currently only implied.

Two cheap ranking improvements fall out:

1. **Demote archived, then forks.** `_repo_sort_key` currently ignores `is_archived` and
   `is_fork` (`vcs_repo_completion.py:548`) even though both are already rendered as
   badges. An archived repo is almost never the answer; on an org with years of history
   this is the single largest precision win available, and it is four lines.
2. **Band the local `disabled` records above the catalog.** Highest intent, zero cost.

Deliberately *not* recommended for v1: viewer-affinity ranking (`gh search prs
--author=@me`, `gh api /user/repos --affiliation`). It is a second network round-trip on
an interactive path, it is provider-specific enough to need a new optional
`VcsRepoEntry` field, and `pushed_at` already captures most of the signal. Revisit if
users report the top-20 being wrong.

---

## 5. Part two: stop auto-enabling refs to unknown projects

### 5.1 Where it happens

Nothing calls "enable". A new project is enabled **by omission**:

```python
if existing_record is None:
    project_name = _allocate_canonical_project_name(user, project, records)
    project_file = _project_file_for(projects_base, project_name)
    if not set_workspace_dir(project_file, primary_workspace_dir):
        raise ValueError(f"Failed to write WORKSPACE_DIR for '{project_name}'")
```

`sase-github` `workspace_plugin.py:1647-1651` — the resulting ProjectSpec contains only
`WORKSPACE_DIR`, and *"Missing `PROJECT_STATE` means `enabled`"* (`docs/project_spec.md:84`).

The same holds for the two other minting paths: `_init_missing_project_ref` →
`init_bare_git_project` (`plugins/bare_git_ref.py:174`) and `create_project_file`, which
writes literally `content = ""` (`workflows/commit/project_file_utils.py:103`).

So: **type `#gh:some-org/some-repo` once, and that repo permanently joins this machine's
`+` catalog, its launch pickers, and its `sase project list`.**

### 5.2 Why the fix is not one line

Writing `PROJECT_STATE: disabled` at mint time collides with two existing behaviors.

**Collision 1 — the workspace claim gate.** `claim_workspace` refuses disabled projects:

```python
def _new_work_lifecycle_error(project_file: str, content: str) -> str | None:
    lifecycle = read_project_lifecycle_from_content(content)
    if is_disabled_project_lifecycle_state(lifecycle.state):
        return _disabled_project_claim_error(project_file, lifecycle.state)
```

`src/sase/running_field/_claim.py:39`. The launch that *created* the project would then
fail against it. The gate is right in general — it stops new work on a shelved project —
but a project minted three milliseconds ago was never shelved.

**Collision 2 — launch-time re-adoption.** `enable_known_project_vcs_refs_for_launch_prompt`
enables every disabled known-project VCS ref in the prompt
(`agent/launch_projects.py:67`), and it is called *before* ref resolution
(`launch_cwd_agents.py:121` vs. resolution at `:458`). On the **first** launch the project
does not exist yet, so it is skipped. On the **second** launch of the same
`#gh:owner/repo`, `resolve_known_project_ref` matches the now-known record — via a
`~/projects/github/<owner>/<repo>` path guess hardcoded into a provider-agnostic host
module (`xprompt/_parsing_vcs_refs.py:138`) — and re-enables it. The fix would silently
undo itself.

### 5.3 The rule that resolves both

SASE already draws a line between two ref forms; it just does not draw a *semantic*
conclusion from it. Draw one:

> A **provider ref** (`#gh:owner/repo`, `#git:/path/to/bare.git`) is a **locator**: "go
> work on that repo." It materializes a checkout and a ProjectSpec. It does not adopt.
>
> A **project ref** (`#gh:sase`, `#gh_sase`, an alias, a display name) is an **adoption
> assertion**: it names a project this machine knows. Typing it against a disabled project
> is intent to resume — today's documented behavior (`docs/workspace.md:224`), unchanged.

Under that rule the second-launch re-adoption disappears by construction, the hardcoded
GitHub path guess stops being load-bearing for adoption decisions, and the only thing left
to solve is the claim gate for the single launch that did the minting.

### 5.4 Alternatives considered

- **A new lifecycle state** (`unadopted`) — rejected. `PROJECT_LIFECYCLE_STATES` is owned
  by the Rust core (`core/project_lifecycle_wire.py:16`, `decisions:rust-core-required`),
  every consumer would need a new branch, and `disabled` already means exactly "not in
  this machine's working set".
- **A second ProjectSpec axis** (`PROJECT_ORIGIN: implicit`, filtered out of discovery
  while `PROJECT_STATE` stays `enabled`) — rejected. Two axes meaning nearly the same
  thing, and every discovery consumer would have to learn the second one.
- **Route unknown provider refs to the external-repo path** (`ws_clone_external_repo` →
  `sase/repos/external/gh/owner/repo`, which correctly creates no project,
  `external_repos.py`) — rejected. Agent workflows need a project for workspaces, Patches,
  and claims; this would break `#gh` launches outright.
- **Don't mint at all; require adoption first** — rejected. It turns a one-keystroke
  "review this PR in a repo I don't own" flow into a multi-step ceremony.

---

## 6. Recommendation

### R1 — Surface: a fourth Projects sub-tab, `Add`

Strip becomes `Projects · Repos · Workspaces · Add`; `]`/`[` cycle as today
(`_SUBTAB_ORDER`, `projects_pane.py:63`). New module family mirroring the existing split:

```
project_add_pane.py       # the widget: input + list + hints + status
project_add_source.py     # headless: parse "gh:sase-org/foo" -> (workflow, namespace, query)
project_add_rows.py       # row model + rendering (extends the existing VCS row renderers)
project_add_actions.py    # mark/adopt actions, preview modal, proc submission
```

Layout:

```
Projects · Repos · Workspaces · ADD
┌─ Source ────────────────────────────────────── GitHub · sase-org/ ─┐
│ gh:sase-org/                                                       │
└────────────────────────────────────────────────────────────────────┘
MARK  NAME              SRC  STATUS    PUSHED  DESCRIPTION
      sase              gh   enabled   2d      Structured Agentic SWE
 ●    sase-core         gh   disabled  5d      Rust core            ← adopt: instant
 ●    sase-telegram     gh   new       1w      Telegram integration ← adopt: clone
      old-experiment    gh   new       3y      [archived]
```

The **Source** input is a provider ref *without* the `#`, i.e. the CLI spelling already
used by `sase repo open gh:owner/repo` (`main/parser_repo.py:175`). It is focused on
entry; `/` refocuses it. There is no second filter concept — the input *is* the filter, so
typing narrows exactly as it does in the prompt bar.

### R2 — Behavior of the input, reusing the prompt-bar stack verbatim

| Input | Rows shown | Source |
| --- | --- | --- |
| *(empty)* | namespaces across every registered workflow | `vcs_ref_namespaces_by_workflow(get_workflow_names())` |
| `gh:` | namespaces for `gh`, then known projects/Patches | `build_vcs_ref_candidates("gh")` + `filter_vcs_ref_candidates` |
| `gh:sase-org/` | repos in the namespace, reconciled | `peek_cached_repo_candidates` → keyed worker → `fetch_repo_candidates` |
| `gh:sase-org/sa` | narrowed | `filter_vcs_repo_entries` |
| `git:` | placeholder: *"Git (bare) has no repository catalog — type a bare-repo path"* | provider returned `None` |

Accepting a namespace row appends `/` and keeps the token open — reuse
`apply_vcs_ref_selection(..., chain=True)` (`vcs_ref_completion.py:275`), the same
function and therefore the same behavior as `#gh:sase-org/` in the prompt bar.

Note the `git:` row: **this is the VCS-agnosticism test, and it passes without a special
case.** A provider that implements neither catalog hook degrades to a plain ref box whose
`Enter` still adds by ref. Any future provider that implements them gets the full browser
for free.

### R3 — Keys: no new verbs

| Key | Action |
| --- | --- |
| typing | narrow / drill the ref |
| `Enter` / `Tab` on a namespace row | chain into `<ns>/` |
| `m` / `u` | toggle mark / clear marks *(existing)* |
| `a` | **adopt** the marked set, else the highlighted row *(existing enable key)* |
| `d` | disable — meaningful on `enabled` rows *(existing)* |
| `R` | force-refresh the catalog, bypassing the 600 s TTL *(existing reload key)* |
| `'` | jump hints *(existing)* |
| `Esc` | clear the input back to the workflow root; if already there, leave the tab |

`check_action` gates the sub-tab-inappropriate keys exactly as `_PROJECT_ONLY_ACTIONS`
does today (`projects_pane.py:143`). One new keymap field is needed only if a direct jump
into the sub-tab is wanted; `]`/`[` suffices for v1.

### R4 — Rows are a reconciliation; the join key is one new optional field

Add one backward-compatible field to the provider contract:

```python
@dataclass(frozen=True)
class VcsRepoEntry:
    ...
    workspace_dir: str = ""   # where this repo would live locally, if the provider knows
```

The GitHub provider already computes this (`_github_workspace_dir(user, project, host)`,
`workspace_plugin.py:1387`) — it is one line to populate. The host then joins each catalog
entry against `{normalized(record.workspace_dir): record}` from one
`list_project_records(..., "all")` call: **one dict lookup per row, no extra hooks, no
per-row `peek_ref`.**

Providers that leave it empty fall back to a bounded, off-thread `ws_peek_ref` per row —
correct but O(N·M), since `peek_gh_ref` re-lists project records on every call
(`workspace_plugin.py:1614`) — or, if that is too slow, render status `unknown` and let
the dry-run resolve it. Both degradations are honest.

**Second payoff:** with a provider-supplied workspace dir available, the hardcoded
`_github_owner_repo_workspace()` guess in `xprompt/_parsing_vcs_refs.py:138` — a GitHub
path layout baked into a provider-agnostic host module — can be retired in favor of asking
the provider. Worth a follow-up bead even if it lands separately.

### R5 — Ranking

Render in bands, all provider-agnostic:

1. local `disabled` records whose workspace matches the active namespace — highest intent,
   zero cost, labeled so;
2. catalog rows via the existing `_repo_sort_key`: prefix matches first, then `pushed_at`
   descending;
3. **new:** demote `is_archived` to the bottom and `is_fork` below non-forks inside each
   prefix band — four lines in `_repo_sort_key`, and the badges already exist.

Namespace ordering needs no change: `_list_github_ref_namespaces` already emits
local-record orgs (with `"3 projects"` descriptions) before `github_orgs` entries (labeled
`"from github_orgs"`). Document `github_orgs` as **the** onboarding seed, since on a fresh
machine it is the only namespace source that survives.

### R6 — Commit path: a CLI command, run as one tracked proc

**New CLI** (`sase project add`), alphabetically placed in the `project` group, every long
option short-aliased, no required options — per `cli_rules.md`:

```
sase project add [<ref> ...]

  <ref>            [<workflow>:]<namespace>/<repo>, a bare-repo path, or a known
                   project name/alias. Reads newline-separated refs from stdin
                   when the only positional is '-'.
  -j, --json       Emit machine-readable plan/result
  -n, --dry-run    Resolve and print the plan without cloning or writing
  -s, --state      Lifecycle state to leave each project in (default: enabled)
```

Implementation is host-side and provider-agnostic: for each ref, `resolve_ref(ref,
workflow)` then `set_project_state_locked(name, state)`. It is the only place project
materialization lives, so the TUI, the CLI, and any future web frontend share it —
`rust_core_backend_boundary` and the `projects_tab_init_ux` "shell out, always" rule both
point the same way.

**TUI flow** (`a` on the `Add` sub-tab), matching `plan_install_many` → confirm → proc:

1. off-thread `sase project add --dry-run --json <refs>`;
2. a preview modal built on `PluginActionConfirmModal`'s bones showing the exact argv, the
   split (*"3 already local — enable only; 2 new — clone ~? and register"*), and
   critically **the derived canonical project name and display alias per ref**, so
   `_allocate_canonical_project_name` collisions surface before the clone rather than
   after;
3. on confirm, **one** tracked proc via `SessionProcReporter.run()` streaming into the
   Procs tab, under a new durable op name `PROJECT_ADD = "project.add"`
   (`src/sase/ops/names.py`);
4. per-ref outcome toast, then `_load_records()` + `_refresh_options()` in place.

`resolve_ref` is never imported into the TUI process (`tui_perf.md` rule 11).

### R7 — Stop auto-enabling: four changes behind one `sunset` flag

1. **Mint disabled, host-side.** In `workspace_provider._registry.resolve_ref()`, snapshot
   known project names before delegating to the hook; if `resolved.project_name` was not in
   the snapshot, write `PROJECT_STATE: disabled` explicitly. One place, zero plugin
   changes, automatically correct for every current and future provider.
2. **Let the minting launch proceed.** Thread a narrowly scoped allowance for the project
   *this launch just minted* into `claim_workspace`, recorded in the existing claim ledger
   via `caller_tag` (`running_field/_claim.py`). Scope it to that one project and that one
   launch; do not weaken `_new_work_lifecycle_error` generally.
3. **Stop re-adopting on later launches.** In the adoption consumer
   (`enable_known_project_vcs_refs_for_launch_prompt` /
   `enable_known_project_for_launch_ref`, `agent/launch_projects.py`), treat only
   project-name/alias/display-name-form refs as adoption assertions and skip
   `namespace/repo` forms. Change the *consumer*, not `iter_known_project_vcs_refs` itself
   — history and display callers still need the written form
   (`_parsing_vcs_refs.py:238`).
4. **Docs**: `docs/workspace.md:224`, `docs/xprompt.md:523`, `docs/project_spec.md:84,218`,
   and the `docs/ace.md` Projects-tab section all state the current rule and all change.

This is user-reaching deprecation whose old branch must stay reachable, so per
`sase_flags.md` it needs a flag created with `sase flag new <key> -k sunset` (On = mint
disabled + no `namespace/repo` re-adoption; Off = today's implicit-enable branch), with
tests for both states.

**The two halves compose:** after this lands, every one-off `#gh:owner/repo` launch
deposits a `disabled` record, and those records are precisely the zero-cost `disabled`
band at the top of the new `Add` sub-tab. The feature that stops the clutter and the
feature that lets you adopt in bulk are the same feature seen from two sides.

### R8 — Explicitly not recommended

- **A modal picker** (§3 Option B) — no room for a 200-row list plus detail; re-implements
  what the pane already has.
- **A scope filter on the Projects sub-tab** (§3 Option C) — mixes a network corpus into a
  disk-backed list; every existing key needs per-row applicability.
- **A new lifecycle state** (§5.4) — Rust-core-owned, and `disabled` already means this.
- **Viewer-affinity ranking** (§4) — second network round-trip, provider-specific,
  marginal over `pushed_at`.
- **A "machine profile" config key** listing projects to enable per host. Tempting for the
  onboarding story, but it creates a second source of truth competing with
  `PROJECT_STATE`. The `-`/stdin form of `sase project add` covers the same need without
  the ambiguity: `sase project list --json` on the old machine, refs into `sase project
  add -` on the new one. (Closing that loop end-to-end wants `sase project list --json` to
  also emit each record's provider ref; today it emits `workspace_dir` and `vcs_kind`
  (`main/project_handler_render.py:13`), from which the ref is derivable but not stated.
  Small follow-up.)

---

## 7. Risks and open questions

- **Large orgs truncate silently.** `max_repos` (200) is passed straight to `gh --limit`,
  and neither the provider nor `VcsRepoCandidates` reports a total. The pane must say
  *"showing 200 — narrow the filter"* whenever `len(entries) == max_repos`; consider an
  optional `truncated: bool` on `VcsRepoCandidates` so the claim is accurate rather than
  inferred.
- **Bulk clones are the expensive part.** Ten repos is ten full checkouts. The preview
  must state the count plainly; the proc must be partial-tolerant and report per-ref
  outcomes like `execute_install_many` rather than aborting the batch on one failure.
- **Name collisions at scale.** `_allocate_canonical_project_name` and
  `allocate_project_name` handle one at a time; a bulk add surfaces them N times. R6's
  dry-run showing derived names per ref is the mitigation, not an optional nicety.
- **`ws_peek_ref` cost in the fallback path.** `peek_gh_ref` re-lists project records per
  call; a 200-row fallback reconciliation is O(N·M). R4's `workspace_dir` field is what
  keeps this off the common path — if it is dropped from scope, the fallback needs a
  provider-side memo or a batch hook instead.
- **Snapshot suite.** `just check-full`'s PNG snapshots pin the Projects pane layout; a
  fourth strip tab and a new sub-tab both regenerate. `just check` remains the agent
  default (`lint_and_test.md`, `decisions:two-speed-verification`).
- **Open question — should `Add` show *all* workflows' namespaces at the root, or default
  to the current project's provider?** Showing all is more discoverable and is what an
  empty input naturally implies; defaulting is fewer rows. Recommendation: show all, since
  the root list is bounded by configured orgs (small) and the onboarding case has no
  "current provider" to default to.
- **Open question — should adopting a `new` row also run `sase init` for it?** The
  concurrent `projects_tab_init_ux` work puts `i`/`I` on the Projects sub-tab for exactly
  that. Keeping them separate is the smaller change and lets the user adopt ten repos
  quickly, then init once; worth confirming against the intended onboarding sequence.
