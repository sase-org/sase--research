---
narration: 1
title: Splitting the Memory-Built Instruction Migration Into Epics
source: research:202610/memory_built_instruction_migration_epics/memory_built_instruction_migration_epics__final.md
source_blob: 9f13685d2a3bbbd8cd825272ad5556c06df194a6
date: 2026-10-05
kind: research
edition: brief
producer: agent
target_minutes: 4
---

## The short answer

The question is how to migrate existing agent instruction files to instructions built from memory immediately before launch. The recommendation is 5 core epics, run in order, plus 2 optional ones. Split at the points where real runs must be observed before proceeding. Do not split by provider or by earlier report.

The architecture from the earlier research largely holds. Build a bundle per invocation. Deliver it through explicit provider channels. Give root agents and helpers different instruction slots. Commit only a small export stub.

The generated-file inventory contains 35 files across the main project, home, and 2 other projects. Hand-written guides in linked repositories are outside this migration.

The stated goal for SASE agents is complete after the delivery cutover. Retiring full renders across the wider environment takes the remaining core epics.

## Why these boundaries matter

Epic size is not the deciding reason. The median completion time is 3.3 hours for epics with 1–4 phases. An epic launches all its phases and its landing agent together. It cannot pause for days to observe production.

There are 2 meaningful observation boundaries: after the stopgaps, and after explicit delivery begins. Separating rendering from delivery also keeps a compiler defect from immediately reaching every agent. Separating home changes keeps personal-environment rollout outside the repository retirement epic.

The earlier reports need corrections. The proposed Grok stopgap would duplicate the contract while still omitting the single-turn directive. Correct that fix before launching it.

Provider rollback switches should use sunset flags. Beta flags must disappear before their epic lands, too early for the required observation period.

Retiring files also affects their readers and producers. Memory History, validators, continuous integration, initialization, and memory maintenance all need coordinated changes.

Claude auto-memory depends on the workspace assigned to an agent. The report recommends disabling it in SASE runs. Grok's separate memory channel also needs an explicit decision.

Monitor and gate turns do not call a provider. Their later agent continuations are ordinary root turns. A special lean instruction audience for those turns has no current target.

## The recommended sequence

The first epic builds an instruction scoreboard and fixes the Grok and Claude-helper harms. Confirm that Grok receives the contract once and the directive. Confirm that Claude helpers cannot finalize the parent turn. Then observe real runs for at least 3 days.

The second epic builds bundles in shadow mode without delivering them. Confirm rendering parity and complete invocation coverage. This work can proceed during the first observation period.

The third epic switches providers to explicit delivery, with a rollback switch for each provider. Confirm one full bundle per invocation, correct helper instructions, and suppression of duplicate full native files. Confirm each rollback path with tests and a live probe. This completes launch-time memory-built instructions for SASE agents.

Watch delivery behavior for at least 7 days. Remove the sunset flags only after the readout is acceptable.

The fourth epic retires committed full files in the main repository. Confirm that only 2 instruction files remain tracked. Check export drift, fresh-clone bootstrap, interactive setup, and continuity across the Memory History transition. Retire producers and validators together.

The fifth epic rolls out the home layer, other projects, and interactive launches. Confirm that home instructions contain no SASE finalization obligations on every execution host. Confirm correct delivery in the other projects.

Optional visual instruction visibility comes after the manifest schema stabilizes. Audience filtering waits for at least 2 measured conditionals. Baseline triggers must remain present for every audience.

Approve each epic from the previous epic's evidence. Keep immediate exit checks separate from later watch metrics. The estimated calendar is about 2–3 weeks, mainly observation periods and reviews.
