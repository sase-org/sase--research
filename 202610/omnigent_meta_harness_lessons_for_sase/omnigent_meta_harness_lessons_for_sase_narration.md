---
narration: 1
title: What Omnigent Teaches SASE
source: research:202610/omnigent_meta_harness_lessons_for_sase/omnigent_meta_harness_lessons_for_sase__final.md
source_blob: ee64d98bd88bab18c2a6bd323c5ecb3d3627a468
date: 2026-10-07
kind: research
edition: brief
producer: agent
target_minutes: 4
---

## The central comparison

What should Structured Agentic Software Engineering, or SASE, learn from Omnigent? The request called it omniagent. The project examined is Omnigent.

Both systems wrap vendor command line tools. Their organizing principles differ. Omnigent centers on a live session, reachable across devices. SASE centers on durable work records, outside any conversation.

SASE runs each agent for a single provider turn. Approval gates end that turn. The host handles completion. Omnigent supports long-running conversations, with approvals that can park a tool call inside the session.

All 5 researchers agree: keep SASE's model and borrow Omnigent's control mechanisms. Those include tool-call guardrails, minimal environments, provider capability checks, independent review, and cost accounting.

The strongest reason is durability. Omnigent keeps authoritative turn and steering state in runner memory. Its documentation records 8 known resilience failures. These include approval cards lost after restart and messages lost while the host is offline.

SASE's durable gates avoid holding a provider process while waiting. Its work records and host-owned completion remain strengths.

## What verification changed

The lead checked disputed claims against code, documentation, installed tools, and host settings. Several confident claims needed correction.

Omnigent's documentation describes native wrappers as sandboxed. Its code configures those wrappers without a sandbox. The sandbox machinery exists, but the claimed default does not.

Its hard cost cap does not terminate execution. It forces a cheaper model. A single turn can overshoot before the next check. Models without pricing trigger a request for approval.

SASE already supports third-party providers, queued follow-ups, and joins across research groups. Recommendations to add those capabilities were largely redundant.

A smaller gap remains: a launch request can resume its requester when approval settles, before the children finish.

The central SASE weakness is enforcement within a turn. Every provider launches with permission bypass flags and a full copy of the operator's environment. Important rules still depend on prose instructions.

SASE already enforces a helper restriction through a Claude tool hook. That provides a starting point. Codex also has hooks, but their behavior under SASE's bypass flags remains untested.

Another inexpensive opportunity is cost capture. Claude already reports a dollar cost. SASE records token counts and drops that figure.

These findings come from inspection. No hooks, sandboxes, or resilience tests were exercised end to end.

## Recommended changes

The report ranks 12 changes.

First, enforce prose rules through tool hooks. Begin in report-only mode. Denials should explain the approved route, including durable gates for permission.

Second, give each provider a minimal environment. Pass only required credentials and explicitly configured variables.

Third, declare provider capabilities and verify them with live probes. Missing observations must never count as passing evidence.

Fourth, add cross-vendor review at the epic land step. Reviewers should initially see the diff and acceptance contract alone.

Fifth, capture cost, aggregate it across work, and budget at launch boundaries. Unknown prices stay visible. Hard thresholds step down model size.

Sixth, introduce execution profiles. Start with vendor sandboxes for research and review. Consider a SASE-owned sandbox and credential broker later.

Seventh, build a read-only browser view over the existing gateway.

Eighth, map every entry point for features, so verification covers each route.

Ninth, resume requesters when launched agents finish.

Tenth, offer named recipes built from existing macros.

Eleventh, add a generic Agent Client Protocol provider only when a concrete new tool requires it.

Twelfth, improve operator workflows, including draining agents before upgrades.

The suggested starting order differs from the ranking. Begin with minimal environments, guardrails in report-only mode, and capability probes. Independent review and cost capture can follow alongside them.

Keep long-lived steering, cloud sandbox fleets, and model-judged authorization out of the immediate plan. Strengthen SASE's existing boundaries first.
