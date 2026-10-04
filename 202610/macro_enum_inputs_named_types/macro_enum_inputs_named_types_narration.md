---
narration: 1
title: Macro Enum Inputs and Named Types
source: research:202610/macro_enum_inputs_named_types/macro_enum_inputs_named_types__final.md
source_blob: 266e1de340e224dd6bf27da325e491958df59625
date: 2026-10-04
kind: research
edition: brief
producer: agent
target_minutes: 4
---

## The question and short answer

Should SASE add enum macro inputs, with reusable value sets and completion in the prompt bar and external editors? Yes. But the research changes the shape of the request.

Enums already exist. Their implementation is unfinished. Neither the prompt bar nor the language server protocol, or LSP, completes enum values. There is no way to share a value set.

The recommendation is to finish those enums, then add named input types. An input's type should name what its value is. An inline enum has its own choices. A built-in domain, such as model, has its own validation and completion. A plugin can provide a shared enum under a qualified name.

This distinction matters because model selectors are not a closed list. They include aliases, explicit provider and model combinations, and optional effort levels. A closed enum would reject valid selectors or stop being closed.

The feature is worthwhile. Inputs are a macro's interface. Catching a typo before a swarm launches agents can save real money. Completion also makes available values easier to discover.

## The deciding evidence

The current implementation disagrees with itself. YAML parsing can turn unquoted yes and no into booleans. The editor and runtime then see different choices. Invalid defaults can load without validation. Empty values and whitespace are accepted. The literal null conflicts with a binder sentinel.

Long-form workflow inputs drop choices. Unknown types silently become line inputs. The authoring schemas omit enum support. These defects need fixing before a shared registry adds more complexity.

The strongest model example is a misspelled bare selector. Today it can silently fall back to the default provider. A typed model input should reject that mistake.

The report found an existing rule in SASE's doctor checks: a model token must route without silent fallback. Reuse that rule. Accept configured aliases and explicit provider and model forms, including models outside the local catalog. Reject unknown bare tokens, unknown aliases, and invalid effort suffixes.

Validation should make no network calls and never advance an alias rotation cursor. Accepted syntax and immediate provider availability are different promises.

Named types also have a local precedent: agent inputs already name a live domain. Built-ins should use bare names, such as model and effort. Plugin types should use the existing qualified naming convention. Installing another plugin must never change an existing type's meaning.

## What to build

Start with correctness. Enum choices must be unique, nonempty strings without whitespace. Reject the reserved null value. Membership stays exact and case-sensitive. Enforce these rules for macros and workflows, while leaving gate inputs unaffected.

Closed enum defaults must belong to the set. Model defaults get warnings when they fail validation. Editor model diagnostics also remain warnings because its catalog snapshot can become stale.

Next, carry choices through every hint interface. Provide completion, descriptions, hover information, and fixes for invalid values. Completion must insert the actual value, never its display label. Applying an editor completion should produce exactly the value the runtime accepts.

Then add model and effort types. Model inputs should reuse the model directive's menu. Effort is a closed enum. Keep validation, resolution, and completion in the Rust core. Python should provide discovery, snapshots, and presentation.

Finally, let plugins ship declarative input type files beside their macros. Start with the shared audio edition choices, brief and full. Defer configuration-defined sets, suggestion-only inputs, executable plugin callbacks, and narrowing until real consumers need them.

The recommended solution is one concept: a macro input's type names what its value is. Ship correctness first, enum completion second, model and effort third, and plugin-shared enums last.
