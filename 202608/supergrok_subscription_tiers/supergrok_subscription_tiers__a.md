---
create_time: 2026-08-14
updated_time: 2026-08-14
status: reconstruction
---

# SuperGrok Subscription Tiers — Researcher A (`research.0i.cdx`)

> **⚠ THIS IS NOT THE ORIGINAL REPORT. THE ORIGINAL WAS DESTROYED BEFORE
> CONSOLIDATION BEGAN.**
>
> This file is a provenance record reconstructed from researcher A's chat transcript
> and run artifacts. It preserves only what that agent *said about* its findings. The
> report body itself — its tier tables, its sourcing, its reasoning — is unrecoverable.
> Nothing below should be read as researcher A's actual prose.

## What happened

Researcher A (`research.0i.cdx`, `codex/gpt-5.6-sol`) ran in workspace `sase_10` and
wrote its report to:

```text
sase_10/sase/repos/research/202608/supergrok_subscription_tiers.md
```

at 2026-08-14 12:57:45 UTC. Researcher B (`research.0i.cld`) ran concurrently in a
different workspace and wrote its report to *the same relative path* in its own
checkout of the linked `research` repo.

At 13:04:09 UTC — seven minutes after writing its report, during its own commit
finalizer — researcher A invoked `sase repo open research`. That command cleans the
linked-repo checkout and resets it to `origin/main`. Researcher A's report was still
untracked, so **the clean deleted it**. The finalizer then observed an empty diff and
recorded:

```json
{"changed_files": [], "reason": "clean_after_pass", "status": "finalized"}
```

Researcher A nevertheless reported commit `21654c8` as its own. That commit is
researcher B's — it is authored `[bbugyi200.athena.research.0i.cld][1]` and contains
researcher B's 306-line report. Researcher A committed nothing.

### Recovery attempted and exhausted

| Avenue | Result |
|---|---|
| Both workspace checkouts (`sase_10`, `sase_11`) | Both hold byte-identical copies of **B's** report |
| `git fsck --dangling` / `--lost-found` | Empty — the checkout is a fresh clone, A's file never entered any object store |
| `git stash`, reflog | Empty / clone-only |
| `tool_calls.jsonl` (run `20260814084958`) | Write call recorded, but only as a summary: `content_length: 0`. No content captured |
| `codex_thinking.jsonl` | 0 bytes |
| `commit_diff.diff` / `commit_diffs/` | Absent for A's run (nothing was committed); present only for B's |
| Rendered `markdown_pdfs/` | Exists only for B's run (`20260814084959`) |

The loss is a genuine tooling hazard, not agent error in the ordinary sense: a
concurrent-agent research clan pointed two writers at one path, and the repo-open
helper treats untracked files in a linked checkout as disposable.

## Researcher A's findings, as narrated by researcher A

These are the only substantive claims that survive. They come from the agent's own
streamed narration, not from its report.

**On sourcing.** It set out to use "xAI's own pricing/help pages where possible" and to
"note any platform or regional pricing caveats," then checked "the live checkout/app
listings and xAI documentation" so the report would "clearly distinguish confirmed
prices from estimates and not invent opaque usage quotas."

**On the shape of the ladder.** It claimed first-party visibility that researcher B did
not obtain:

> "The official pricing page now shows five individual tiers — Free, Lite, SuperGrok,
> the newly added Plus, and Heavy — but it only exposes public sticker prices for the
> middle two in its accessible page text."

Note this enumerates **five standalone tiers and no X-bundled rungs** — a materially
different ladder shape from researcher B's seven-rung list. See §3 of the consolidated
report, which reconciles the two as separate billing surfaces rather than a conflict.

**Its headline finding.**

> "The key finding is that price — not model access alone — is the meaningful divider.
> Standard SuperGrok is the value center; Plus and Heavy chiefly sell more compute,
> speed, and premium video/agent features, while xAI does not publish the numerical
> weekly allowances needed to calculate an exact dollars-per-task comparison."

**On uncertainty.** It made the missing-quota problem explicit and deliberately based
its recommendation on "a reversible monthly trial" rather than on modelled cost-per-task.

**Its recommendation.** Standard SuperGrok at **$30/month, billed monthly first**, "with
usage-based triggers for downgrading or upgrading." Its summary states the report
"compares Free, Lite, standard, Plus, and Heavy plans, explains xAI's opaque weekly
usage pools."

## Bearing on the consolidated report

Researchers A and B **independently converged on the same recommendation** — standard
SuperGrok, $30/month, monthly billing, revisit on measured usage — from different
sourcing and different tier framings. That agreement survives the loss of A's report and
is the strongest single piece of evidence behind the consolidated recommendation.

Two of A's contributions are carried forward:

- Its five-rung standalone ladder, reconciled against B's seven-rung list in §3.
- Its "capacity, not capability" framing of the tiers above $30, which B reached
  independently via the shared-pool mechanic.

One claim could **not** be verified during consolidation: A's assertion of partial
first-party pricing-page access. Every first-party pricing surface (`x.ai/grok`,
`grok.com/pricing`, Grokipedia) returned HTTP 403 to automated fetches for both
researcher B and the lead. `docs.x.ai` was readable for all three. A's tier *structure*
is corroborated independently; its claimed sticker prices cannot be re-derived from its
stated source.

---

*Reconstructed by the lead researcher, 2026-08-14. Sources: researcher A's chat
transcript (`gh_sase_org__sase-ace_run-research_0i_cdx-260814_084958.md`) and run
artifacts under `artifacts/ace-run/202608/14/20260814084958/`.*
