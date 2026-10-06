---
narration: 1
title: Let a Wait Follow an Agent Into Its Epic
source: research:202610/wait_follows_agent_into_epic/wait_follows_agent_into_epic__final.md
source_blob: 300e556166977220d01c029ecd7e4e66012651c9
date: 2026-10-06
kind: research
edition: brief
producer: agent
target_minutes: 4
---

## Is this a good idea?

The proposed feature lets a wait follow a named agent into the epic that agent launches. An epic organizes implementation into phases. Today, users must wait for the planner to create it, copy its identifier, and submit another wait.

The recommendation is to build the feature. Keep the proposed default: following epics is enabled for user-authored agent targets. Allow users to disable it explicitly.

This lets users submit follow-up prompts earlier. Their execution still starts after the epic closes. The improvement is earlier authoring and submission, rather than earlier execution.

All 5 researchers support building it. They disagree about the default. The deciding evidence is an existing inconsistency in what waiting for a planner means.

When the planner chooses a tale, its implementation agent runs inside the planner's session. Waiting for the planner already waits for implementation. When the planner chooses an epic, the same wait stops after launch.

Users cannot know that choice when they submit their wait. Following epics makes the meaning consistent. The existing epic machinery already combines agent completion with bead closure for its phase dependencies.

## The reliability problem

The scheduling record needs more work than the original proposal assumes. Existing attribution identifies who proposed plans and created beads. It does not provide a reliable scheduling relationship.

An existing epic identifier has 2 meanings. For a planner, it identifies the epic launched. For a phase worker, it identifies the parent epic containing that worker.

Following that field blindly would deadlock every epic. A later phase would wait for the parent epic to close. The parent cannot close until that later phase finishes.

Instead, record launched epics separately when they become durable. Keep membership separate from creation. Derive artifact links from the durable record, rather than making links the scheduler's source of truth.

Discovery also needs a definite end. An empty lookup cannot mean that no epic exists. Launch may still be pending, especially on detached or fallback paths.

Use a small state machine. First wait for the agent. Then distinguish a pending launch, discovered epics, proven absence, and a blocked launch.

When discovery succeeds, promote the dependency into an ordinary bead wait. Pin the epic identity so rerunning the planner cannot redirect an existing waiter. Reuse the current closure rules and fail closed on unreadable state.

Follow only epics actually launched from a plan. Exclude backlog epics merely filed, and epics the agent was assigned to. Follow all launched epics from the resolved session. Never follow into the waiter's own subtree.

## Recommended solution

Add the boolean keyword per wait occurrence. Reject it without an agent target, with matching launch errors and editor diagnostics. Plan-only targets never follow epics.

Store the chosen behavior when the waiter launches. Already parked waits retain their existing meaning. Generated waits inside an epic explicitly disable following, preventing cycles between its phases and parent.

Make the handoff visible in the terminal user interface. Use a teal turning arrow, matching the existing epic-created color. Show the completed planner, the followed epic's identifier, and phase progress together.

While launch is pending, show its status and approval time. Add a coalesced notification and a timeline milestone. A failed launch should produce an actionable blocker and keep the waiter parked.

Ship in 5 phases: the durable record, the keyword contract, resolution, interface presentation, and the default change. Before changing the default, prove that the epic's own phases and landing agent still release correctly. Measure the resource cost of longer parking.

Canceled or superseded epics remain an explicit policy question. The report recommends releasing waiters visibly, consistent with ordinary bead waits.

Build the feature with default following, strict validation, durable discovery, pinned bead waits, and a visible handoff. That removes the manual synchronization step while preserving the epic machinery's safety.
