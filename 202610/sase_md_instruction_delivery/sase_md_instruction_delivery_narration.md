---
narration: 1
title: SASE Instructions Delivered Once
source: research:202610/sase_md_instruction_delivery/sase_md_instruction_delivery__final.md
source_blob: 3c6cdb8e7479818bcc2465170cd321a7c220198b
date: 2026-10-05
kind: research
edition: brief
producer: agent
target_minutes: 4
cover: sase_md_instruction_delivery_infographic.png
---

## The question and answer

Should SASE replace its many agent instruction files with one specification, then tailor instructions for each agent at launch?

The report recommends building this, with important changes. SASE means Structured Agentic Software Engineering. It already generates instructions and controls workspaces. The missing control is knowing what each provider actually receives.

Use one instruction bundle per provider invocation. Compose it from layered memory through an optional specification. Deliver it through each provider adapter. Verify that it arrives exactly once.

Keep the instruction text in memory notes. The specification should describe composition, conditions, and budgets. It should not become another large document holding everything.

The original bug descriptions are outdated. Grok has loaded no instruction files in SASE workspaces since about September 10. Project instructions require folder trust, which those workspaces lack. All 465 workspace sessions in the examined later period loaded nothing.

Codex does receive home instructions through SASE's temporary home configuration. Its real problem is receiving the shared contract twice. Claude also receives duplicate contracts, with conflicting repository lists. Muse and Grok miss the home layer entirely.

Antigravity probably loads duplicate files too. Vendor documentation supports that conclusion, but its transcripts do not independently confirm it.

## Why delivery matters

Writing a tailored file into each workspace sounds simple. The report finds that approach unreliable.

Tracked instruction rewrites can become commits. Reused workspaces can retain an earlier agent's instructions. Ancestor files can still load. Grok skips ignored files, while Codex cannot suppress a project instruction file that is present.

The actual provider can also change during routing or fallback. Therefore, render when each provider is invoked, including recovery calls.

Use explicit delivery channels where available. Grok can receive rules directly while its workspace stays untrusted. Claude has an appended system prompt channel. Codex already has a temporary home mechanism. Other adapters need their own supported delivery approach.

Provider channels have different semantics. Compaction and subagent behavior need testing. Claude subagents need a separate instruction variant without the parent agent's final declaration obligation.

Audience selection should begin with facts SASE already knows. These include provider, role, phase worker status, tribe, macro, commit method, and host.

Do not introduce the proposed tag directive. That name has historical meanings, and its short alias already means tribe. Free-form labels should wait until a real section needs something existing facts cannot express.

Conditions may trim optional material. They must preserve hard rules and baseline reference-reading triggers. An agent's research role does not prove it will never edit code.

The design also unlocks useful improvements. Plugins can contribute relevant instructions. Home context can match the target machine. Stored bundles can show exactly what an agent received. Instruction changes can avoid generated-file churn.

## What to build first

Start with Grok's direct rules channel and an initial delivery check. Check provider session records, rather than assuming files on disk were loaded.

Next, build the bundle renderer and adapter delivery, with a separate feature flag for each provider. Record each frozen bundle and its provenance.

Then stop committing the 20 generated instruction files. Give people local projections for interactive use. Convert nested instructions into path-scoped reference notes, with unconditional triggers to read them before editing relevant files.

Add conditional audiences after delivery works. Put shared schema validation and condition evaluation in the Rust core. Keep Markdown composition and provider delivery in Python.

Finally, add macro-declared labels only when demonstrated demand requires them.

Success means exactly one delivered bundle, complete home context, preserved hard rules, and no workspace changes caused by instruction generation. Measure behavior too. If a provider's explicit channel lowers compliance, reconsider that provider's delivery method.

The recommendation is per-invocation bundles, layered memory, facts-first audiences, and continuous verification of actual delivery.
