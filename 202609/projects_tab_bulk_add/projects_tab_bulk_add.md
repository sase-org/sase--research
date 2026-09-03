---
create_time: 2026-09-03
updated_time: 2026-09-03
status: research
---

# Bulk Project Add From The Admin Center Projects Tab

**Research question:** let users add new SASE projects *in bulk* from the **Projects**
tab of the SASE Admin Center, with excellent completion for the organizations/repos they
are most likely to pick, in a VCS-agnostic way that future workspace-provider plugins
get for free. As part of the same change, stop auto-enabling new projects created when a
VCS xprompt workflow ref names a repo this machine does not yet know. What is the best
UX, and what is the right way to build it?

**Provenance:** consolidation of two independent research reports
(`projects_tab_bulk_add__a.md`, `projects_tab_bulk_add__b.md`) plus lead verification.
Every load-bearing `file:line` claim from both reports was independently re-checked
against the current `sase` checkout (HEAD `ad1da7fc2`); all of them held. Where the two
reports disagree, §8 states the disagreement and how it was resolved.

---

## 1. Executive summary

**The feature is almost entirely assembly, not invention.** Both researchers converged
on this independently. SASE already has:

- a provider-agnostic, cached, ranked, error-classified repository catalog with a proven
  TUI presentation layer — the `#gh:sase-org/` completion menu;
- a multi-select project list whose `m`/`u` marks and `a` (enable) key already operate
  on the marked set (`docs/ace.md`, "When one or more projects are marked…");
- a canonical "browse a remote catalog → mark many → preview → execute as one tracked
  proc" flow in the Updates tab's plugin browser.

Bulk project add is the join of those three, and the join key is one optional dataclass
field.

**Recommendation:** a fourth Projects sub-tab, **`Add`**, whose single input is a
provider ref minus the `#` (`gh:sase-org/`) driven by the *identical* headless
completion helpers the prompt bar uses; whose rows are a **three-state reconciliation**
of the provider catalog against local records (`enabled` / `disabled` / `new`); whose
marked basket **persists across namespace and source changes**; and whose commit key is
the pane's existing `a`, routed through a new `sase project add` CLI with a dry-run
preview and one tracked proc. The only provider contract change is one optional field,
`VcsRepoEntry.workspace_dir`.

**For the auto-enable half:** keep minting the project on a one-off `#gh:owner/repo`
launch, but mint it **disabled** (host-side, provider-agnostic), let that one launch
through the claim gate via a narrowly scoped allowance, and stop treating
`namespace/repo`-form refs as adoption assertions on later launches. This is a
four-part change behind a `sunset` flag, not a one-liner (§5).

**The two halves compose.** After the auto-enable change, every one-off
`#gh:owner/repo` launch deposits a `disabled` record — which is exactly the zero-cost,
highest-intent band at the top of the new `Add` sub-tab. The change that stops the
clutter and the change that lets you adopt in bulk are the same feature from two sides.

---

## 2. What already exists (verified)

### 2.1 The provider contract is already VCS-agnostic

`src/sase/workspace_provider/_hookspec.py` defines pluggy hooks covering the whole
discovery lifecycle:

- `ws_list_ref_namespaces(workflow_type)` — fast, **local-only by contract** ("must use
  only fast local data such as project records or config");
- `ws_list_repo_candidates(workflow_type, namespace)` — remote repository listing;
- `ws_peek_ref(ref, workflow_type)` — read-only lookup with an explicit no-mutation
  contract ("must not clone repositories, create project records, write files, spawn
  network subprocesses");
- `ws_resolve_ref(...)` — the mutating twin that materializes a project.

The peek/resolve split is exactly the split this feature needs: peek for the browse
list, resolve for the commit. Payloads are already rich enough to rank and render:
`VcsRepoEntry(name, ref, description, visibility, is_fork, is_archived, pushed_at)` and
`VcsNamespaceEntry(name, description, kind_label)`.

The GitHub plugin (`sase-github` `workspace_plugin.py`) shells `gh repo list <owner>
--json ... --limit <max_repos>` and classifies failures into
`auth`/`not_found`/`network`/`tool_missing`/`unknown` with actionable messages.
Namespaces come from enabled project records (counted, "3 projects") plus the
`github_orgs` config key. The bare-git plugin deliberately implements **neither**
catalog hook — `#git` refs are paths, not `namespace/repo` — so any design that assumes
a catalog exists is not VCS-agnostic; it must degrade to a plain ref box.

### 2.2 The host-side completion stack is already headless

Four modules, none importing Textual: `xprompt/vcs_ref_completion.py` (namespace
candidates, ref-root parsing, `apply_vcs_ref_selection(..., chain=True)` which appends
`/` so repo completion takes over), `xprompt/vcs_repo_completion.py`
(`fetch_repo_candidates` with memo + on-disk TTL cache — default 600 s / 200 repos —
and stale-on-error fallback; `peek_cached_repo_candidates` as a provider-free hot path;
`filter_vcs_repo_entries`), `xprompt/vcs_project_completion.py` (the enabled
project/Patch catalog behind `+`), and the `ace/tui/widgets/` row builders with
loading/empty/error placeholders and `[private]`/`[fork]`/`[archived]` badges.

Ranking exists: `_repo_sort_key` (`vcs_repo_completion.py:548`) sorts prefix matches
first, then `pushed_at` descending, then name. Verified: it currently **ignores
`is_archived` and `is_fork`** even though both are rendered as badges.

### 2.3 The Projects tab and the bulk-operation house style

`ProjectsPane` hosts a three-tab strip (`Projects · Repos · Workspaces`,
`_SUBTAB_ORDER` at `projects_pane.py:63`, `]`/`[` to cycle) with marks that survive
filtering, bulk lifecycle keys running through the marked set (successes clear their
marks, failures stay marked), a filter input, jump hints, a debounced detail panel, and
per-sub-tab session state.

The Updates tab's plugin browser is the precedent for exactly this shape:
`plan_install_many()` off-thread → confirm modal → `execute_install_many()` as one
tracked proc → per-item outcome toast. The concurrent `projects_tab_init_ux` research
independently added the rule that the TUI **shells out to the CLI** rather than
importing the coordinator. `tui_perf.md` rule 11 names our exact hazard: provider
`resolve_ref` clones repos and allocates project records — never reachable from a
keystroke path.

---

## 3. The UX decision: a fourth `Add` sub-tab

Both reports agreed on the interaction vocabulary (browse namespace → mark many →
review → execute with per-item outcomes) but disagreed on the container: report A
proposed a dedicated modal opened with `n`; report B proposed a fourth sub-tab.
**The sub-tab wins** (§8.1 for the full resolution). Modals in this app are for
decisions (confirm, pick one); this is *browsing* a 200-row network-backed corpus that
wants a detail panel, marks, filter, jump hints, and session state — all of which the
pane provides for free and a modal would re-implement. Options considered and rejected:
a single-ref prompt (fails bulk), a scope filter on the existing Projects list (mixes a
network corpus into a disk-backed list; every existing key needs per-row
applicability), and the modal.

### 3.1 Layout

```
Projects · Repos · Workspaces · ADD                          2 selected
┌─ Source ────────────────────────────────────── GitHub · sase-org/ ─┐
│ gh:sase-org/                                                       │
└────────────────────────────────────────────────────────────────────┘
MARK  NAME              SRC  STATUS    PUSHED  DESCRIPTION
      sase              gh   enabled   2d      Structured Agentic SWE
 ●    sase-core         gh   disabled  5d      Rust core            ← adopt: instant
 ●    sase-telegram     gh   new       1w      Telegram integration ← adopt: clone
      old-experiment    gh   new       3y      [archived]
```

The **Source** input is a provider ref without the `#` — the CLI spelling already used
by `sase repo open gh:owner/repo`. It is focused on entry; `/` refocuses it. There is
no second filter concept: the input *is* the filter, narrowing exactly as in the prompt
bar. New module family mirroring the existing split: `project_add_pane.py`,
`project_add_source.py` (headless ref parsing), `project_add_rows.py`,
`project_add_actions.py`.

### 3.2 Input behavior, reusing the prompt-bar stack verbatim

| Input | Rows shown | Source |
| --- | --- | --- |
| *(empty)* | namespaces across every registered workflow | `vcs_ref_namespaces_by_workflow(get_workflow_names())` |
| `gh:` | namespaces for `gh`, then known projects/Patches | `build_vcs_ref_candidates("gh")` |
| `gh:sase-org/` | repos in the namespace, reconciled | `peek_cached_repo_candidates` → keyed worker → `fetch_repo_candidates` |
| `gh:sase-org/sa` | narrowed | `filter_vcs_repo_entries` |
| `git:` | placeholder: *"Git (bare) has no repository catalog — type a bare-repo path"* | provider returned `None` |

Accepting a namespace row chains into `<ns>/` via the same
`apply_vcs_ref_selection(..., chain=True)` the prompt bar uses. The `git:` row is **the
VCS-agnosticism test, and it passes without a special case**: a provider that
implements neither catalog hook degrades to a plain ref box whose `Enter` still adds by
ref; any future provider that implements the hooks gets the full browser for free.
Paint from cache or a loading placeholder immediately, fetch off-thread, show staleness
honestly, and offer `R` to bypass the TTL — all established patterns.

### 3.3 Keys: no new verbs

`m`/`u` mark/clear (existing), `a` **adopts** the marked set — else the highlighted row
(existing enable key, existing `_target_records()` semantics), `d` disables `enabled`
rows, `R` force-refreshes the catalog, `'` jump hints, `Esc` clears the input back to
the root, then leaves the tab. `check_action` gates sub-tab-inappropriate keys as
`_PROJECT_ONLY_ACTIONS` does today. Any new keymap field goes in both the app keymaps
and `src/sase/default_config.yml` (gotchas memory).

**One requirement carried over from report A: the basket must persist across namespace
and source changes.** Marks are keyed by full provider ref, survive input edits, and a
"N selected" count stays visible in the pane header. Cross-namespace batches
("onboard my repos from two orgs in one pass") are what make the flow genuinely
bulk-capable; without persistence the sub-tab degrades to one-namespace-at-a-time.
Archived rows are shown but ranked to the bottom (§4); already-`enabled` rows are
visible for orientation but excluded from the adopt set (adopting them is a reported
no-op).

### 3.4 Rows are a reconciliation; the join key is one optional field

The `Add` sub-tab does not show "repos you don't have" — it shows the provider catalog
reconciled against local records, in three states:

| Status | Meaning | Cost of `a` |
| --- | --- | --- |
| `enabled` | already adopted on this machine | none (no-op, reported) |
| `disabled` | ProjectSpec exists, not in the working set | **instant** — one `set_project_state_locked` |
| `new` | in the provider catalog only | clone + register + enable |

Add one backward-compatible field to the provider contract:

```python
@dataclass(frozen=True)
class VcsRepoEntry:
    ...
    workspace_dir: str = ""  # where this repo would live locally, if the provider knows
```

The GitHub provider already computes this (`_github_workspace_dir`); populating it is
one line. The host joins each catalog entry against
`{normalized(record.workspace_dir): record}` from one `list_project_records(..., "all")`
call — one dict lookup per row, no extra hooks. Providers that leave it empty fall back
to a bounded, off-thread `ws_peek_ref` per row (correct but O(N·M)) or render status
`unknown` and let the dry-run resolve it; both degradations are honest.

**Second payoff:** with a provider-supplied workspace dir, the hardcoded
`~/projects/github/<owner>/<repo>` guess in `xprompt/_parsing_vcs_refs.py:138`
(verified: a GitHub path layout baked into a provider-agnostic host module) can be
retired. Worth a follow-up bead even if it lands separately.

Name/destination conflicts (canonical-name collisions, existing directories) are
surfaced per-row in the dry-run preview (§6), not silently at clone time.

---

## 4. "Most likely to select": ranking in two regimes

The stated scenario — onboarding a new machine — is the hard case, because a fresh
machine has zero local records, so every locally derived signal is empty:

| Signal | Fresh machine? |
| --- | --- |
| Local `disabled` records | no |
| Namespaces from local records (with project counts) | no |
| Namespaces from `github_orgs` config | **yes** (config is chezmoi-synced) |
| Repo recency (`pushed_at` → `_repo_sort_key`) | **yes** |
| Fork / archived / visibility badges | **yes** |
| VCS xprompt MRU | no |

The fresh-machine path therefore runs on **`github_orgs` from synced config plus
provider-side push recency** — genuinely enough, and it should be documented as the
onboarding seed, because it makes `github_orgs` load-bearing in a way that is currently
only implied.

Render in provider-agnostic bands:

1. **local `disabled` records** matching the active namespace — highest intent, zero
   cost, labeled so;
2. catalog rows via the existing `_repo_sort_key` (prefix matches first, then
   `pushed_at` descending);
3. **new:** demote `is_archived` to the bottom and `is_fork` below non-forks within
   each band — roughly four lines in `_repo_sort_key`, and the badges already exist.
   On an org with years of history, archived-demotion is the single largest precision
   win available.

Namespace ordering needs no change: the GitHub provider already emits local-record orgs
before `github_orgs` entries.

**Deferred, as follow-up beads rather than v1** (§8.3): an optional async **remote
namespace-discovery hook** (authenticated user + org list, cached, never on the
prompt-completion fast path) for machines whose config is *not* synced — additive and
worthwhile, but `github_orgs` + a typed namespace covers the primary user today.
Also deferred: viewer-affinity ranking (`--affiliation` etc.) — a second network
round-trip on an interactive path for marginal gain over `pushed_at`.

---

## 5. Stop auto-enabling refs to unknown projects

### 5.1 Where it happens (verified)

Nothing calls "enable" — a new project is enabled **by omission**. The GitHub resolver
writes a ProjectSpec containing only `WORKSPACE_DIR` (`workspace_plugin.py:1647-1651`),
and missing `PROJECT_STATE` means enabled (`docs/project_spec.md:84`). The bare-git init
path and `create_project_file` (which writes empty content) behave identically. So:
type `#gh:some-org/some-repo` once, and that repo permanently joins this machine's `+`
catalog, launch pickers, and `sase project list`. Do **not** change the missing-state
default itself — it is an established compatibility rule with many consumers.

### 5.2 Why the fix is four changes, not one

Writing `PROJECT_STATE: disabled` at mint time collides with two verified behaviors:

- **The workspace claim gate.** `claim_workspace` refuses disabled projects
  (`running_field/_claim.py:38-42`), so the launch that *created* the project would
  fail against it — after doing the clone work. The gate is right in general; a project
  minted milliseconds ago was never shelved.
- **Launch-time re-adoption.** `enable_known_project_vcs_refs_for_launch_prompt`
  (`agent/launch_projects.py:67`) enables every disabled known-project VCS ref in the
  prompt, and runs *before* ref resolution (`launch_cwd_agents.py:125` vs. `:458`). On
  the second launch of the same `#gh:owner/repo`, the now-known record matches — via
  the hardcoded path guess in `_parsing_vcs_refs.py:138` — and the fix silently undoes
  itself.

### 5.3 The rule that resolves both

Draw a semantic line SASE already draws syntactically:

> A **provider ref** (`#gh:owner/repo`, `#git:/path/to/bare.git`) is a **locator**:
> "go work on that repo." It materializes a checkout and a ProjectSpec. It does not
> adopt.
>
> A **project ref** (`#gh:sase`, an alias, a display name) is an **adoption
> assertion**: it names a project this machine knows. Typing it against a disabled
> project is intent to resume — today's documented behavior, unchanged.

### 5.4 The change, behind one `sunset` flag

1. **Mint disabled, host-side.** In the `workspace_provider` registry's
   `resolve_ref()`, snapshot known project names before delegating to the hook; if the
   resolved project was not in the snapshot, write `PROJECT_STATE: disabled`
   explicitly. One place, zero plugin changes, automatically correct for every current
   and future provider.
2. **Let the minting launch proceed.** Thread a narrowly scoped allowance for the
   project *this launch just minted* into `claim_workspace` (via the existing
   `caller_tag` ledger). Scope it to that one project and that one launch; do not
   weaken `_new_work_lifecycle_error` generally.
3. **Stop re-adopting on later launches.** In the adoption consumers
   (`enable_known_project_vcs_refs_for_launch_prompt` /
   `enable_known_project_for_launch_ref`), treat only project-name/alias/display-name
   refs as adoption assertions and skip `namespace/repo` forms. Change the consumers,
   not `iter_known_project_vcs_refs` — history/display callers still need the written
   form.
4. **Docs:** `docs/workspace.md:224`, `docs/xprompt.md:523`,
   `docs/project_spec.md:84,218`, and the `docs/ace.md` Projects-tab section all state
   the current rule and all change.

This is user-reaching deprecation whose old branch must stay reachable, so per
`sase_flags.md` it needs `sase flag new <key> -k sunset` (On = mint disabled + no
`namespace/repo` re-adoption; Off = today's implicit-enable branch), with tests for
both states. Explicit launch of a *known disabled project by name* keeps its current
re-enable behavior — selecting a known project is stronger intent than mentioning a
remote locator, and changing it would be a separately named lifecycle decision.

**One hardening point from report A worth keeping regardless:** ACE's
`resolve_ref_from_prompt` swallows `(ValueError, RuntimeError)` and returns `None`
(`ace/tui/actions/agent_workflow/_ref_resolution.py:66`), silently falling back. If any
part of this change ever needs to *reject* a ref, it must use a structured error that
passes through — the existing `ProjectProviderMismatchError` re-raise at `:64` is the
in-tree precedent. Verify in tests that the new flag's failure modes are not swallowed
into a silent home-project fallback.

### 5.5 Alternatives rejected

- **Block unknown provider refs at launch and require adoption first** (report A's
  recommendation — see §8.2): turns a one-keystroke "review this PR in a repo I don't
  own" flow into a multi-step ceremony, and contradicts the request's own framing
  ("projects that are created" — creation continues, enabling stops).
- **A new lifecycle state** (`unadopted`): `PROJECT_LIFECYCLE_STATES` is Rust-core-owned
  (`decisions:rust-core-required`), every consumer needs a new branch, and `disabled`
  already means "not in this machine's working set".
- **A second ProjectSpec axis** (`PROJECT_ORIGIN: implicit`): two axes meaning nearly
  the same thing; every discovery consumer must learn the second.
- **Routing unknown refs to the external-repo path**: agent workflows need a project
  for workspaces, Patches, and claims; this breaks `#gh` launches outright.
- **A "machine profile" config key** listing projects per host: a second source of
  truth competing with `PROJECT_STATE`; the stdin form of `sase project add` covers the
  same need (`sase project list --json` on the old machine → refs → `sase project
  add -` on the new one).

---

## 6. Commit path: `sase project add`, plan/apply, one tracked proc

**New CLI** (verified absent today), alphabetically placed in the `project` group,
options short-aliased per `cli_rules.md`:

```
sase project add [<ref> ...]

  <ref>            [<workflow>:]<namespace>/<repo>, a bare-repo path, or a known
                   project name/alias. Reads newline-separated refs from stdin
                   when the only positional is '-'.
  -j, --json       Emit machine-readable plan/result
  -n, --dry-run    Resolve and print the plan without cloning or writing
  -s, --state      Lifecycle state to leave each project in (default: enabled)
```

Two phases, with the domain half in the Rust core per `rust_core_backend_boundary`:

1. **Plan:** normalize and deduplicate refs, compare against one lifecycle snapshot,
   classify each as `already-enabled` / `re-enable` / `create` / `conflict`, and derive
   the canonical project name and display alias per ref. Classification and transition
   policy are shared domain behavior → Rust core (or its wire API); provider I/O stays
   behind the pluggy hooks with a thin Python adapter.
2. **Apply, per item:** `resolve_ref` (the existing provider materialization primitive
   — no new mandatory hook) then explicitly `set_project_state_locked(name, state)`.
   Idempotent per item; bounded concurrency; a failure never rolls back completed
   items.

**TUI flow** (`a` on the `Add` sub-tab), matching the plugin-browser precedent:

1. off-thread `sase project add --dry-run --json <refs>` — the TUI shells out and never
   imports `resolve_ref` (`tui_perf.md` rule 11, `projects_tab_init_ux` rule);
2. a preview modal showing the exact argv, the split (*"3 already local — enable only;
   2 new — clone and register"*), and **the derived canonical name and alias per ref**,
   so name collisions surface before the clone rather than after;
3. on confirm, **one** tracked proc via `SessionProcReporter.run()` streaming into the
   Procs tab under a new durable op name `PROJECT_ADD = "project.add"`;
4. per-ref outcome toast; successful rows clear their marks, failed rows stay marked
   for retry (the pane's existing convention); refresh records in place.

Error/empty states are part of the design, and the provider error classification
already supplies them: no catalog provider (plain ref box), auth/tool failure
(actionable structured message), empty namespace vs. local filter miss, stale cache
(usable + refresh hint), truncation (§7), partial batch failure (successes and
failures both reported, nothing auto-closes).

---

## 7. Delivery sequence, risks, open questions

**Sequence** (the Add surface should exist before or with the flag flip, so users never
lose the implicit onboarding path without its replacement):

1. Core plan/classification types + tests (unknown, disabled, enabled, duplicate,
   conflicting refs).
2. `VcsRepoEntry.workspace_dir` (populate in `sase-github`) + reuse of the existing
   headless completion helpers; extract shared policy only where the pane genuinely
   needs different behavior from the prompt bar.
3. `sase project add` CLI with dry-run/JSON, then the tracked-proc execution path.
4. The `Add` sub-tab: input, reconciliation rows, basket persistence, preview modal,
   keymap config, help modal, narrow/wide PNG snapshots.
5. The auto-enable change (§5.4) behind its `sunset` flag.
6. Follow-up beads: optional remote namespace-discovery hook; emit each record's
   provider ref in `sase project list --json` (today only `workspace_dir`/`vcs_kind`);
   retire the `_parsing_vcs_refs.py` path guess; `truncated: bool` on
   `VcsRepoCandidates`.

**Risks:**

- **Silent truncation.** `max_repos` (200) passes straight to `gh --limit` and nothing
  reports a total; the pane must say *"showing 200 — narrow the filter"* when
  `len(entries) == max_repos`.
- **Bulk clones are the expensive part.** Ten repos is ten full checkouts; the preview
  states the count plainly and the proc is partial-tolerant with per-ref outcomes.
- **Name collisions at scale.** `_allocate_canonical_project_name` handles one at a
  time; the dry-run preview showing derived names per ref is the mitigation, not a
  nicety.
- **Peek-fallback cost.** Without `workspace_dir`, reconciliation is O(N·M)
  (`peek_gh_ref` re-lists records per call); the field is what keeps this off the
  common path.
- **Snapshot suite.** A fourth strip tab regenerates the Projects-pane PNG snapshots
  (`just check` remains the agent default; `just check-full` gates landing).

**Open questions for the user:**

- Should the empty-input root show **all** workflows' namespaces or default to one
  provider? Recommendation: show all — the root list is bounded by configured orgs, and
  the onboarding case has no "current provider" to default to.
- Should adopting a `new` row also run `sase init`? The concurrent
  `projects_tab_init_ux` work puts `i`/`I` on the same pane. Recommendation: keep
  separate — adopt ten quickly, then init deliberately — but confirm against the
  intended onboarding sequence.

---

## 8. Where the reports disagreed, and how it was resolved

### 8.1 Modal (A) vs. fourth sub-tab (B) → **sub-tab, with A's basket requirement**

A proposed a dedicated `n`-key modal with a source/namespace browser; B rejected the
modal on concrete grounds: no room for a 200-row list plus a detail panel, and it
re-implements marks, filter, hints, and session state the pane already has — modals in
this app are for decisions, browsing belongs in a pane. The Updates-tab plugin browser
(a pane, not a modal) is the house precedent. B's design wins, but A contributed the
requirement B under-specified: the marked basket must persist across namespace/source
changes, with a visible selected-count — that is what makes the flow bulk across
namespaces rather than per-namespace.

### 8.2 Block unknown launch refs (A) vs. mint disabled (B) → **mint disabled**

This was the sharpest conflict. A recommended rejecting unknown provider refs before
resolution with a structured error pointing at the Add flow, warning that mint-disabled
"does the clone work then fails at the claim gate" and that re-launch would trigger
known-disabled auto-enable. Both warnings are real (verified), but B's design already
answers each: a narrowly scoped claim allowance for the minting launch, and the
locator-vs-adoption rule that stops `namespace/repo` re-adoption by construction.
Blocking, by contrast, breaks the one-keystroke "work on a repo this machine hasn't
seen" flow — a real and valuable behavior — and diverges from the request's framing,
which says to stop auto-*enabling* projects "that are created", not to stop creating
them. What survives from A: the structured-error pass-through hardening (§5.4), the
insistence that the claim-gate allowance stay narrow, and preserving the
known-disabled-by-name re-enable behavior as a separate, unchanged policy.

### 8.3 Remote namespace-discovery hook: v1 (A) vs. unnecessary (B) → **follow-up bead**

A argued today's root completion is too weak on a pristine machine "unless
`github_orgs` happens to be synced"; B established that `github_orgs` *is* the
chezmoi-synced onboarding seed and is sufficient. For this user, B is right, and the
hook adds a network dependency v1 does not need. But A's hook is correctly shaped —
optional, additive, cached, never on the prompt-completion fast path — and is the right
answer for machines without synced config. File it as a follow-up, and document
`github_orgs` as load-bearing now.

### 8.4 Minor merges

- **Commit machinery:** A's plan/apply application service and B's `sase project add`
  CLI are the same design at different altitudes; merged as CLI entry + Rust-core
  classification + provider I/O behind pluggy (§6). Both independently agreed on:
  dry-run preview before mutation, per-item idempotent apply, no rollback, per-ref
  outcome reporting, and never importing `resolve_ref` into the TUI.
- **Ranking:** both independently proposed demoting archived repos; B added the
  fork demotion and the `disabled`-band-first insight; A added "selectable before
  already-enabled", which the band structure subsumes.
- **Keys:** A's `n`-plus-modal vocabulary is dropped with the modal; B's "no new
  verbs" reuse of `m`/`u`/`a` stands, keeping the keymap-config rule A flagged.
