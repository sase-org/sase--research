# Selecting research reports for artifact file hooks

## Recommendation in brief

The goal is sound: a report should carry an explicit, positive indication that it is eligible for research file hooks. The proposed environment variable is the wrong place to keep that indication. Add a **per-file hook-intent tag at `sase artifact create`**, persist it with the exact source path and content, and let file-hook filters select that tag. Have `#research` request the tag by default, with a Boolean opt-out for every preliminary `#research_swarm` researcher. Have the lead register and tag the consolidated report every time.

Keep `research-highlights` on the committed-file producers initially. Its command, `bob highlights create --include-id`, uses the input basename to derive the PDF name and marker ID. Artifact dispatch currently passes a digest-suffixed stored copy, so changing only the selector and enabling the `artifact` producer would generate the wrong identity. Artifact-time execution is a separate improvement that needs a stable logical filename and a deliberate policy for duplicate commit events.

## Verified behavior and the actual gap

The current `FileHookFilters` supports project, sidecar, path glob, agent-name glob, operation, cause, and producer; it has no artifact label, tag, or environment field. Dimensions are ANDed. The research plugin's Highlights spec selects `research` sidecar ADDs from `commit`, `sdd`, or `finalizer`, then excludes `__<suffix>` paths at two depths, generated companions, and five named researcher agents. Those exclusions are not imaginary fragility: plugin commit `f524532` expanded them when Grok, Muse, and Gemini joined the swarm. An unknown researcher who writes a clean-looking path can pass. Negative-only agent-name globs also admit unattributed commits. See `sase/src/sase/config/file_hooks.py` and `sase-research-artifacts/src/sase_research_artifacts/provider.py`.

`#research` is a Markdown prompt part. It instructs an agent to create a durable snapshot labeled `research:<repo-relative-path>` after writing the report. The label is used to identify reports for the lead, but the file-hook event does not carry it, and both drafts and final reports use the same label form. Markdown xprompts do not provide the YAML workflow `environment:` mechanism. Turning a prose instruction to `export` a variable into reliable cross-provider behavior would be especially weak. See `sase-research-artifacts/src/sase_research_artifacts/xprompts/research.md` and `sase/memory/xprompts.md`.

The swarm lead does **not** invoke `#research`. The lead currently registers its final report only when the optional critique agent is enabled. Thus a default set by `#research` would mark standalone reports and preliminary researchers, while missing the normal consolidated report. The five researcher segments invoke `#research(suffix=...)`; the lead has its own instructions in `research_swarm.md`.

Artifact event matching uses the original repository-relative path, but hook execution receives the durable stored copy's digest-suffixed absolute path. Commit events execute against the checkout path. The batch runner appends that absolute path to the command. The current producer restriction is therefore an intentional filename safeguard, not a missing filter entry. See `sase/src/sase/file_hooks/{artifact,commit,models,dispatch,runner}.py` and the plugin's `docs/configuration.md`.

## What the four reports add, and where they disagree

| Report | Strongest contribution | Decision |
| --- | --- | --- |
| [Codex](artifact_hook_intent_matching__cdx.md) | Bind a positive tag to the exact registration and reconcile it against the later committed file; avoid ambient environment. | Adopt, with strict content and run scoping. |
| [Grok](artifact_hook_intent_matching__grk.md) | Identifies the stored-copy basename as the obstacle to artifact-time Highlights and calls out duplicate artifact/commit dispatch. | Preserve this warning; defer artifact-time execution. Passing a mutable source file just because it exists can process bytes different from the registered snapshot. |
| [Muse](artifact_hook_intent_matching__mus.md) | Stresses that the current two veto dimensions already provide useful defense and finds a real `status: research` versus provider enum skew. | Retain a limited path guard during migration. A command-level draft guard can prevent a bad PDF, but it does not make matching easier or remove the negative-list maintenance. Frontmatter is not ready as the selector. |
| [Gemini](artifact_hook_intent_matching__gem.md) | Supports artifact tags and unconditional lead registration. | Adopt those ideas. Reject its suggested positive agent glob: with the actual `wcmatch` flags, `["*.final", "!research.*.*"]` returns false for both `research.g.final` and `solo`; it would silently suppress intended reports. |

The reports disagree most on whether to switch Highlights to `producer: artifact` now. That switch is attractive for immediate processing, but it requires preserving a logical basename without reading a mutable source, and choosing what happens to manual committed reports and later commit events. Those are separate behavior changes. The current committed-file route already gives Bob the right filename. Improving selection there first gives the requested reliability with less execution risk.

## Critique of the environment-variable proposal

An environment value is scoped to a process or agent, while this decision is scoped to one file. A lead may register reports, critique material, and companions in one turn; a run-wide flag cannot distinguish them. Agent process state does not automatically survive host-owned commit/finalizer reconciliation. Matching live `os.environ` would make retries depend on which process performed them. Capturing arbitrary environment entries would also add secret and audit problems. A narrowly named variable could be CLI sugar later, but it adds no value over an explicit flag in the existing Markdown xprompt's registration command.

The override should describe the user's intent, not transport: for example, `file_hook_eligible=false`, rather than `set_environment=false`. This default-on behavior is sensible for standalone `#research`; each preliminary researcher must explicitly pass false. The lead needs a separate positive action because it does not call `#research`.

This is a policy signal, not a security boundary: an agent can choose its CLI arguments just as it can choose a filename. Its benefit is precise, durable, inspectable selection that fails closed when the signal is absent.

## Proposed contract and rollout

1. **Host primitive.** Add repeatable, validated `sase artifact create --file-hook-tag <slug>` and `filters.file_hook_tags`. Use an application-level semantic tag such as `research-final`, not the local hook name `research-highlights`. Keep tag matching exact initially. Unknown filter keys must continue to fail visibly. Persist each requested tag with the artifact ID, producing run, canonical repository identity, repository-relative source path, and source digest. Make an inability to persist a requested tag a visible registration failure, even though hook-command failures remain non-gating. The current artifact hook producer swallows ordinary hook errors, so intent persistence must be a distinct, checked step.

2. **Commit correlation.** Thread the producing run's artifact metadata into commit, SDD, and finalizer event construction; the current `reconcile_commit_file_hooks` call supplies agent name but no explicit artifacts directory. Attach a tag only when run, repository, path, and **committed blob contents** match the registration. Checking the working-tree file alone would be unsafe after a post-commit edit. A move or edit after registration should require registering the final path/bytes again. Avoid searching a global artifact index by path, which can find a stale registration from another run. Include tags in audit and deterministic batch identity so first dispatch and retry see the same facts. Follow the project's Rust core backend boundary for any shared schema or behavior that other frontends must consume; do not introduce a second divergent matcher.

3. **Research plugin.** Add a default-true Boolean input to `#research`, rendering `--file-hook-tag research-final` on its existing `sase artifact create` command only when true. Set it false on every preliminary swarm invocation (`cdx`, `cld`, `grk`, `mus`, `gem`, and future additions). Change the lead instructions to register the consolidated report **unconditionally**, once, with the same tag; keep critique and companion outputs untagged. Keep `#research` as Markdown, avoiding a YAML migration solely to set environment.

4. **Hook spec.** Require `file_hook_tags: [research-final]` alongside `sidecars: [research]`, committed-file producers, `ops: [ADD]`, and a broad dated Markdown path check. Remove the enumerated researcher-name exclusions after the new contract is deployed. A `__<suffix>` veto can remain briefly as a migration guard, but should not be the continuing source of truth: it can reject a legitimate final report whose stem contains `__`, and fixed-depth vetoes miss deeper drafts. Do not keep an untagged fallback indefinitely, since it restores the false positives this change is meant to prevent.

5. **Compatibility.** Release the host filter and CLI before publishing the plugin spec, then raise the plugin's minimum SASE version. Document the deliberate change for manual or unattributed commits: without a tag, they will no longer auto-generate Highlights. Their author can register the canonical file with the tag or run Bob explicitly. Also decide separately whether `#research/more` should retrigger Highlights: the current `ADD` filter excludes edits regardless of this proposal.

Verify default-on solo registration, every swarm researcher opt-out, one tagged lead registration, unrelated files in the same commit, stale run/path/digest rejection, commit/finalizer retry equivalence, and no tag on critique or image companions. Test a newly added researcher suffix without updating the hook spec; it must remain unselected. Keep a Bob basename regression test before any future artifact-time route.

## Artifact-time hooks, if wanted later

A future artifact producer should hand a hook an **immutable snapshot under the logical original basename**, for example a managed per-run materialization or an explicit logical-name argument, rather than simply reverting to the mutable checkout source. Then choose one producer for Highlights, or deduplicate artifact and commit attempts by hook plus artifact/content identity; hook name plus path alone would incorrectly suppress a later version of the same file. This later work can make Highlights run immediately after registration, but it is not a prerequisite for robust matching of today's committed-file events.

## Recommended solution

Implement a checked, per-artifact `--file-hook-tag research-final` and a matching `file_hook_tags` filter. Persist enough run, path, and content identity to carry that intent into host-owned commit/finalizer events. Have `#research` add the tag by default with a Boolean opt-out for every preliminary swarm researcher, and have the lead always register and tag its consolidated report. Keep Highlights on committed-file producers until artifact-time execution can preserve both immutable bytes and the report's logical basename.
