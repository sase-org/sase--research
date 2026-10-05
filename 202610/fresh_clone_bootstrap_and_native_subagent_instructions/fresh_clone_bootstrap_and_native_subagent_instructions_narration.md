---
narration: 1
title: Fresh Clones and Subagent Instructions
source: research:202610/fresh_clone_bootstrap_and_native_subagent_instructions/fresh_clone_bootstrap_and_native_subagent_instructions__final.md
source_blob: e77dc3a104b7aa66b62d59067374e3c84641bff9
date: 2026-10-05
kind: research
edition: brief
producer: agent
target_minutes: 4
---

## The short answer

The question is how to generate agent instructions from SASE memory immediately before launch. SASE means Structured Agentic Software Engineering. The report focuses on fresh clones and provider subagents, which are helpers launched inside an agent session.

The recommendation keeps the earlier architecture: render instructions for each invocation, and deliver them through provider adapters. Add separate instructions for the main agent and its helpers. Add mechanical enforcement so only the main agent declares completion. Keep a small committed instruction stub for developers opening an ordinary interactive session.

These are different audiences. A SASE main agent has turn obligations. A helper returns findings to its parent. An interactive developer session needs repository guidance without SASE turn obligations. The same memory can supply shared conventions, but those lifecycle rules must stay separate.

For fresh clones, the bootstrap instruction belongs at the start of the committed stub. A missing file cannot tell an agent to generate itself. Keep a small Claude import shim alongside that stub. The stub provides orientation, setup commands, verification guidance, and essential contributor conventions.

## The deciding evidence

The subagent gap is already causing harm. Claude general-purpose helpers receive the main agent's completion contract. In 30 days, 13–15 of 200 invoked the finalizer. The lead identified 2 accepted declarations submitted by helpers for their parent's turn. One helper had only been asked to acknowledge a message.

Claude's Explore helpers have the opposite problem: they receive no project instructions. Switching from native instruction files to a main-agent prompt flag would not repair this. Tests found that Claude's main-agent prompt flag reaches only the main agent. A separate, hidden subagent prompt-file flag reaches Explore and general-purpose helpers.

The report recommends shipping the Claude repair immediately, before the full renderer. Give helpers a dedicated instruction bundle. Add a tool hook that blocks completion declarations when the caller is identified as a helper. Whether forked helpers carry that identity remains an open test.

Other providers need honest delivery status. Grok's explicit rules reach its main agent but not its helpers. Codex children can inherit the main agent's lifecycle overlay. The recommendation qualifies those obligations by actor and uses a dedicated helper override when available. Providers without a verified helper channel get a best-effort instruction-file pointer.

Fresh-clone behavior also needs care. Claude can import a generated, ignored file. Codex can load an ignored override instead of the committed stub. Grok skips ignored files during discovery. These differences require provider-specific delivery rather than a universal local filename.

## What to do

First, ship the Claude helper bundle and completion guard. Preserve existing project guidance until explicit delivery replaces it. Add diagnostics that show actual helper delivery and completion attempts.

Next, build the shared renderer with separate main-agent and helper delivery slots. Verify the instructions visible in child transcripts. Written files alone do not prove delivery.

Then replace full committed instruction copies with the generated stub and Claude import shim. Keep the stub within 80 lines. Check it for drift in continuous integration.

Setup should generate full interactive instructions into ignored files automatically. The fallback clause must tell an agent to generate instructions and then read them. Creating a file during a session does not update instructions already loaded.

The synchronization command must protect developer-owned files and refuse SASE workspaces. Home instruction files also need an interactive projection, so ordinary sessions are not told to finalize SASE turns.

The recommended endpoint is shared memory with distinct lifecycle overlays: fresh clones remain useful, helpers receive conventions, and completion stays with the main agent.
