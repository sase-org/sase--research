# Research: Implementing Pi as a First-Class SASE LLM Provider

**Author**: researcher `gem` (Independent Swarm Turn)  
**Date**: 2026-10-19  
**Target Repository**: `sase-org/sase`  
**Reference Codebase**: `earendil-works/pi` (v1.3.0, snapshot at `sase/repos/external/gh/earendil-works/pi`)  
**Prior Research Reviewed**: `research:202610/sase_for_pi_users/sase_for_pi_users__final.md`  

---

## 1. Executive Summary & Recommended Solution

### 1.1 The Core Finding

Pi ([earendil-works/pi](https://github.com/earendil-works/pi)) is an exceptionally fast, modular, and hackable single-agent coding harness built on Node.js/TypeScript. SASE ([sase-org/sase](https://github.com/sase-org/sase)) is a multi-agent coordination system that provides workspace isolation (numbered checkouts `sase_<N>`), admission gating, dependency DAGs (`%wait`), host-owned commit landing (`host-owned-completion`), and durable task tracking (`beads`, `goals`, `ToolRuns`).

As concluded in the prior synthesis (`sase_for_pi_users__final.md`), **Pi and SASE operate at different architectural layers**: Pi owns the inner model loop, tools, session tree, and terminal UI, whereas SASE orchestrates harnesses across isolated git workspaces. Adding Pi as a fully supported SASE provider is not merely an interoperability feature; it allows SASE users to harness Pi's multi-provider reach (30+ providers, virtual models, and Codemode) within SASE's safe, multi-agent git operating system.

### 1.2 Recommended Solution at a Glance

The recommended path is a **phased adapter architecture** combining SASE's standard pluggy plugin system with Pi's native JSONL streaming and extension hooks:

1. **Phase 1 (Core Provider Engine - M Effort)**:
   Implement `sase.llm_provider.pi:PiProvider` registered under `[project.entry-points."sase_llm"]` in `pyproject.toml`. Invoke the Pi binary in non-interactive JSON stream mode:
   ```bash
   pi --mode json \
      --session-dir <artifacts_dir>/pi_sessions \
      --session-id <agent_session_id> \
      --model <model_name> \
      [--thinking <level>] \
      [--append-system-prompt <bundle_file>] \
      [-nc] \
      "<prompt>"
   ```
   Parse JSONL events via an asynchronous parser (`_subprocess_pi.py`) that maps Pi's streaming deltas to SASE's `live_reply.txt`, records `tool_execution_start`/`tool_execution_end` events into `tool_calls.jsonl` using `base_stream_tool_call_record`, extracts token and cost usage into `usage.json`, and strictly waits for **`agent_settled`** rather than relying on exit code 0.

2. **Phase 2 (Workspace & Instruction Delivery Integration - S Effort)**:
   - **Session Mobility**: Avoid Pi's default CWD-based session indexing by explicitly configuring `--session-dir` inside the SASE agent artifacts directory (`$SASE_ARTIFACTS_DIR/pi_sessions`). This prevents session collisions when agents move between ephemeral checkouts (`sase_17` to `sase_18`).
   - **Instruction Delivery**: Register the `pi.append_system_prompt` delivery channel under `llm_instruction_delivery()`. When explicit instruction bundles are active, pass `--append-system-prompt <path> -nc` to suppress uncoordinated native reads of ancestor `AGENTS.md` files, aligning with SASE's `instructions-per-invocation` decision.

3. **Phase 3 (Mechanical Invariant Enforcement via `sase-pi` Extension - M Effort)**:
   Ship a lightweight TypeScript extension (`sase-pi`) loaded via `-e`:
   - Expose a typed `sase_final` tool that returns `{ terminate: true }`.
   - Intercept `tool_call` to block raw `git commit`, `git push`, and `gh pr create` calls, directing the model to use SASE host finalization.
   - Attach an `agent_before_settle` hook that checks whether a valid final declaration was submitted, injecting a single continuation reminder before settlement.
   - Enforce `helpers-return-roots-declare` by verifying a root authentication token, ensuring native subagents cannot execute root-only finalizers.

4. **Phase 4 (Catalog, Tooling & Doctor Integration - S Effort)**:
   - Update `src/sase/llm_provider/models.yml` to define Pi's default tiers (`large: claude-3-7-sonnet`, `small: claude-3-5-haiku`) and short aliases.
   - Implement `llm_install_metadata()` for `@earendil-works/pi-coding-agent` via `npm`, integrating with `sase agent-cli install pi` and `sase doctor`.
   - Map SASE's 7 canonical reasoning effort levels (`none` -> `off`, `minimal`..`max` 1:1) to `--thinking <level>`.

---

## 2. Review and Synthesis of Prior Research

Prior SASE research (`sase_for_pi_users__final.md`) established key foundational truths regarding Pi and SASE. Reviewing this record yields several crucial insights that directly govern provider design:

### 2.1 Key Lessons from `sase_for_pi_users`
- **Pi and SASE are complementary, not competitors**: Pi users love its conversation features, fast feedback, model flexibility, and hackability. However, Pi deliberately omits multi-agent isolation, cross-repo coordination, task tracking, and host-managed landing. SASE provides all of these.
- **The Pitfalls of CWD Session Grouping**: Pi hashes `cwd` to group sessions under `~/.pi/agent/sessions/`. In SASE, agents run in ephemeral numbered clones (`sase_1`, `sase_17`, etc.) and may resume or fork across workspaces. Relying on default CWD grouping causes Pi to misidentify workspace transitions as foreign projects. An explicit `--session-dir` is required.
- **`agent_settled` vs `agent_end`**: A common pitfall in naive adapters is treating `agent_end` or process exit code 0 as task completion. In Pi:
  - `agent_end` indicates only that a low-level agent loop completed; retries, compactions, and follow-ups can follow.
  - `agent_settled` is the true terminal event.
  - Furthermore, in `--mode json`, an error or abort stop reason does **not** exit with a non-zero exit code! The adapter must parse event stop reasons directly.
- **Hooks Beat Paragraphs**: For Claude, Grok, and Muse, SASE relies heavily on instruction text to enforce rules ("never run git commit", "always call /sase_final", "helpers cannot declare"). Pi provides rich TypeScript lifecycle hooks (`tool_call`, `agent_before_settle`) that can convert these behavioral guidelines into hard, fail-safe programmatic gates.

### 2.2 Corrections to Past Overstatements
Prior research corrected earlier misconceptions that must be avoided in this implementation:
- **Codemode**: SASE should not attempt to reimplement Codemode or an internal QuickJS sandbox. Pi already possesses Codemode; SASE's role is to pass user tool choices through without impedance.
- **Process Lifetime**: Do not run a long-lived standing Pi daemon across multiple SASE turns. SASE agents are single-turn (`single-turn-agents` decision). Continuity across turns must be achieved via session files (`--session` or `--fork`), not daemon persistence.

---

## 3. Deep Dive into Pi's Architecture & Interfaces

An inspection of `earendil-works/pi` (specifically `packages/coding-agent/`) reveals the following interfaces for host integration:

### 3.1 Operating Modes Comparison

| Dimension | Print Mode (`-p`, `--print`) | JSON Stream Mode (`--mode json`) | RPC Mode (`--mode rpc`) |
|---|---|---|---|
| **Process Lifetime** | Runs prompt, prints text, exits | Runs prompt, streams JSONL, exits | Long-lived daemon over stdin/stdout |
| **Output Channel** | Final assistant text on `stdout` | JSONL events on `stdout`; logs on `stderr` | JSONL responses & events on `stdout` |
| **Intermediate Events** | None | Full lifecycle (tool calls, deltas, usage) | Full lifecycle + bidirectional commands |
| **Input Delivery** | CLI arguments / stdin pipe | CLI arguments / stdin pipe | JSON commands on `stdin` |
| **Mid-Turn Control** | Kill process only | Kill process only | `steer`, `follow_up`, `abort` commands |
| **Error Signaling** | Non-zero exit code | Exit code 0 on model error (events flag it) | Event stop reason / error response |
| **SASE Fit** | Degraded (no tool call tracking) | **Optimal for Phase 1 (Single-Turn)** | **Phase 5 (Mid-run Steering)** |

### 3.2 JSON Event Stream Specification (`--mode json`)

Pi emits newline-delimited JSON objects to `stdout`. Every record is a self-contained JSON line terminated by `\n`.

```
Session Start:
  {"type":"session","version":3,"id":"...","timestamp":"...","cwd":"..."}

Agent Loop:
  {"type":"agent_start"}
  {"type":"turn_start"}
  {"type":"message_start","message":{"role":"assistant","stopReason":"pending",...}}
  {"type":"message_update","usage":{...},"assistantMessageEvent":{"type":"text_delta","delta":"..."}}
  {"type":"message_update","assistantMessageEvent":{"type":"thinking_delta","delta":"..."}}
  {"type":"tool_execution_start","toolCallId":"call_123","toolName":"bash","args":{"command":"..."}}
  {"type":"tool_execution_end","toolCallId":"call_123","toolName":"bash","result":{...},"isError":false,"durationMs":42}
  {"type":"message_end","message":{"role":"assistant","stopReason":"stop",...}}
  {"type":"turn_end","message":{...},"toolResults":[...]}
  {"type":"agent_end","messages":[...],"willRetry":false}
  {"type":"agent_settled","aborted":false}
```

#### Vital Normalization Requirements:
1. **Deltas vs Snapshots**: `message_update` events emit incremental `text_delta` and `thinking_delta` chunks. They must be appended to the live stream. `message_end` provides the authoritative, complete message object.
2. **Usage & Cost Tracking**: `message_update.usage` provides cumulative token counts and estimated dollar costs:
   ```json
   {
     "input": 1520,
     "output": 340,
     "cacheRead": 1200,
     "cacheWrite": 0,
     "totalTokens": 1860,
     "cost": {"input": 0.0045, "output": 0.0051, "total": 0.0096}
   }
   ```
   SASE's `usage.json` artifact can consume these numbers directly.
3. **Tool Execution**: `tool_execution_start` and `tool_execution_end` provide exact call IDs, tool names, parameters, execution results, error booleans, and millisecond durations.

### 3.3 Extension & Hook Lifecycle (`packages/coding-agent/docs/extensions.md`)

Pi's extension system uses `jiti` to dynamically load TypeScript modules without precompilation. Extensions export a default factory taking `ExtensionAPI`:

```typescript
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";

export default function(pi: ExtensionAPI) {
  // 1. Tool Call Gate
  pi.on("tool_call", async (event, ctx) => {
    if (event.toolName === "bash") {
      const cmd = event.input.command;
      if (cmd.includes("git commit") || cmd.includes("gh pr create")) {
        return { block: true, reason: "SASE Policy: Use SASE host finalization, do not commit directly." };
      }
    }
  });

  // 2. Settlement Boundary
  pi.on("agent_before_settle", async (event, ctx) => {
    // Inject continuation if final declaration is missing
  });

  // 3. Custom Typed Tool
  pi.registerTool({
    name: "sase_final",
    description: "Submit SASE turn declaration",
    parameters: SaseFinalSchema,
    execute: async (args) => {
      // Execute finalization
      return { content: [{ type: "text", text: "Declared" }], terminate: true };
    }
  });
}
```

---

## 4. Detailed SASE Provider Implementation Blueprint

To integrate Pi as a first-class citizen alongside Claude, Codex, Grok, and OpenCode, the following components must be created within `src/sase/llm_provider/`:

### 4.1 Module Layout

```
src/sase/llm_provider/
├── pi.py                  # PiProvider (LLMProvider + hookimpl implementations)
├── _subprocess_pi.py      # Subprocess management & JSON stream parsing
├── _tool_call_pi.py       # Tool call artifact normalization for tool_calls.jsonl
└── extensions/
    └── sase_pi/           # Invariant-enforcement extension (TypeScript)
        ├── index.ts
        └── package.json
```

### 4.2 Entry Point & Pluggy Hook Registration

In `pyproject.toml`:
```toml
[project.entry-points."sase_llm"]
pi = "sase.llm_provider.pi:PiProvider"
```

In `src/sase/llm_provider/pi.py`:
```python
class PiProvider(LLMProvider):
    """LLM provider that invokes the Earendil Pi coding agent CLI."""

    @hookimpl
    def llm_provider_name(self) -> str:
        return "pi"

    @hookimpl
    def llm_provider_short_name(self) -> str:
        return "pi"

    @hookimpl
    def llm_cli_status_color(self) -> str:
        return "#8B5CF6"  # Distinct Violet/Purple for TUI

    @hookimpl
    def llm_autodetect_priority(self) -> int:
        return 22  # Preferred when installed locally

    @hookimpl
    def llm_autodetect_cli_name(self) -> str:
        return "pi"

    @hookimpl
    def llm_auth_evidence(self) -> dict[str, list[str]]:
        return {
            "credential_paths": [
                "~/.pi/agent/auth.json",
                "~/.pi/agent/models.json",
                "~/.pi/agent/settings.json",
            ],
            "api_key_env_vars": [
                "ANTHROPIC_API_KEY",
                "OPENAI_API_KEY",
                "GEMINI_API_KEY",
                "GROQ_API_KEY",
                "OPENROUTER_API_KEY",
                "MISTRAL_API_KEY",
            ],
        }

    @hookimpl
    def llm_install_metadata(self) -> dict[str, object]:
        return {
            "manager": "npm",
            "package": "@earendil-works/pi-coding-agent",
            "scope": "global",
            "display_name": "Pi Coding Agent",
            "vendor": "Earendil",
            "docs_url": "https://github.com/earendil-works/pi",
            "self_update_argv": ["update"],
            "latest_version_package": "@earendil-works/pi-coding-agent",
            "version_argv": ["--version"],
        }

    @hookimpl
    def llm_interactive_cli(self) -> dict[str, object]:
        return {
            "menu_key": "p",
            "bypass_args": [],
            "model_args": ["--model", "{model}"],
        }

    @hookimpl
    def llm_instruction_delivery(self) -> dict[str, object]:
        """Delivery plan using Pi's --append-system-prompt flag."""
        return {
            "root": {
                "status": "explicit",
                "channel": "pi.append_system_prompt",
                "max_bytes": 256 * 1024,
            },
            "subagent": {
                "status": "none",
                "reason": "Pi subagents inherit root context or use --no-session",
            },
        }

    def resolve_model_name(self, model_tier: ModelTier = "large") -> str:
        return provider_tier_model("pi", model_tier)

    @hookimpl
    def llm_resolve_model_name(self, model_tier: ModelTier) -> str:
        return self.resolve_model_name(model_tier)

    @hookimpl
    def llm_known_model_names(self) -> list[str]:
        return list(provider_model_names("pi"))

    @hookimpl
    def llm_model_short_aliases(self) -> dict[str, str]:
        return provider_short_aliases("pi")

    @hookimpl
    def llm_default_usage_limit_config(self) -> ProviderUsageLimitConfig:
        return ProviderUsageLimitConfig(
            patterns=[
                "rate limit reached",
                "quota exceeded",
                "insufficient_quota",
                "overloaded_error",
            ]
        )
```

### 4.3 Reasoning Effort & Model Catalog Mapping

In `src/sase/llm_provider/models.yml`:
```yaml
  pi:
    models:
      - claude-3-7-sonnet
      - claude-3-5-sonnet
      - claude-3-5-haiku
      - gpt-4o
      - gpt-4o-mini
      - o3-mini
      - gemini-2.5-pro
      - gemini-2.5-flash
      - deepseek-r1
      - deepseek-v3
    short_aliases:
      claude-3-7-sonnet: sonnet37
      claude-3-5-sonnet: sonnet35
      claude-3-5-haiku: haiku35
      gpt-4o: gpt4o
      gemini-2.5-pro: gem25pro
    tiers:
      large: claude-3-7-sonnet
      small: claude-3-5-haiku
```

Reasoning effort translation (`EFFORT_LEVELS` -> Pi `--thinking`):
```python
_EFFORT_MAP = {
    "none": "off",
    "minimal": "minimal",
    "low": "low",
    "medium": "medium",
    "high": "high",
    "xhigh": "xhigh",
    "max": "max",
}

def _effort_to_pi_args(options: LLMInvocationOptions | None) -> list[str]:
    if not options or not options.reasoning_effort:
        return []
    pi_level = _EFFORT_MAP.get(options.reasoning_effort)
    return ["--thinking", pi_level] if pi_level else []
```

### 4.4 Subprocess Execution & Stream Processing (`_subprocess_pi.py`)

The subprocess invoker launches `pi` and passes JSON lines through `stream_json_lines`:

```python
def stream_and_parse_pi_json_output(
    process: subprocess.Popen[str],
    suppress_output: bool = False,
) -> tuple[str, str, int, dict[str, int]]:
    assistant_texts: list[str] = []
    error_events: list[str] = []
    usage_totals = initial_usage_totals()
    live_reply_file = open_live_reply_file()
    timestamps_file = open_live_reply_timestamps_file()
    thinking_file = open_codex_thinking_file()
    settled = False
    stop_reason: str | None = None

    def _handle_line(line: str) -> None:
        nonlocal settled, stop_reason
        line = line.strip()
        if not line:
            return
        try:
            event = json.loads(line)
        except json.JSONDecodeError as exc:
            record_stdout_json_decode_diagnostic("pi", line, exc)
            return

        ev_type = event.get("type")

        if ev_type == "message_update":
            # Usage accumulation
            if "usage" in event:
                _accumulate_pi_usage(event["usage"], usage_totals)
            # Delta streaming
            asst_ev = event.get("assistantMessageEvent", {})
            delta_type = asst_ev.get("type")
            if delta_type == "text_delta":
                text = asst_ev.get("delta", "")
                append_stream_text(text, assistant_texts, suppress_output, live_reply_file, timestamps_file)
            elif delta_type == "thinking_delta":
                if thinking_file:
                    thinking_file.write(asst_ev.get("delta", ""))
                    thinking_file.flush()

        elif ev_type == "message_end":
            msg = event.get("message", {})
            stop_reason = msg.get("stopReason")
            if stop_reason in {"error", "aborted"}:
                error_events.append(f"Model ended with stopReason: {stop_reason}")

        elif ev_type in {"tool_execution_start", "tool_execution_end"}:
            append_pi_tool_call_event(event)

        elif ev_type == "agent_settled":
            settled = True
            if event.get("aborted"):
                error_events.append("Agent settled with aborted: true")

    stderr_content, return_code = stream_json_lines(process, _handle_line, suppress_output)
    
    # Synthesize effective status
    if not settled and return_code == 0:
        return_code = 1
        error_events.append("Pi exited before agent_settled was emitted.")

    if stop_reason in {"error", "aborted"} and return_code == 0:
        return_code = 1

    combined_text = "".join(assistant_texts)
    write_usage_artifact(usage_totals)
    stderr_content = append_error_events(stderr_content, return_code, error_events)
    return combined_text, stderr_content, return_code, usage_totals
```

### 4.5 Tool-Call Normalization (`_tool_call_pi.py`)

Pi emits discrete start and end events for each tool call:
- `tool_execution_start`: `toolCallId`, `toolName`, `args`
- `tool_execution_end`: `toolCallId`, `toolName`, `result`, `isError`, `durationMs`

These map directly into SASE's `base_stream_tool_call_record`:
```python
def normalize_pi_tool_call_event(event: Mapping[str, Any]) -> dict[str, Any] | None:
    ev_type = event.get("type")
    tool_name = string_or_none(event.get("toolName")) or "unknown"
    tool_use_id = string_or_none(event.get("toolCallId")) or ""

    if ev_type == "tool_execution_start":
        return base_stream_tool_call_record(
            runtime="pi",
            source="stream",
            event="start",
            status="running",
            tool_name=tool_name,
            tool_use_id=tool_use_id,
            tool_input_summary=summarize_tool_input(tool_name, event.get("args")),
        )
    elif ev_type == "tool_execution_end":
        is_error = bool(event.get("isError", False))
        duration = event.get("durationMs")
        duration_ms = int(duration) if isinstance(duration, (int, float)) else None
        return base_stream_tool_call_record(
            runtime="pi",
            source="stream",
            event="end",
            status="error" if is_error else "success",
            tool_name=tool_name,
            tool_use_id=tool_use_id,
            tool_response_summary=summarize_tool_response(event.get("result")),
            duration_ms=duration_ms,
        )
    return None
```

### 4.6 The `sase-pi` Invariant Enforcement Extension

To turn SASE's core invariants into mechanical guarantees, SASE should package a standard extension loaded via `-e <path>/sase-pi`:

```typescript
// src/sase/llm_provider/extensions/sase-pi/index.ts
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";
import { Type } from "@sinclair/typebox";

export default function(pi: ExtensionAPI) {
  let finalDeclared = false;
  const isRootAgent = process.env.SASE_ROOT_AGENT === "1";

  // 1. Register sase_final as a first-class tool
  pi.registerTool({
    name: "sase_final",
    description: "Submit your final declaration to end the turn. Once called, the agent run will terminate.",
    parameters: Type.Object({
      summary: Type.String({ description: "Summary of changes made" }),
      status: Type.String({ description: "Final status (e.g. complete, blocked)" }),
    }),
    execute: async (args) => {
      if (!isRootAgent) {
        throw new Error("SASE Helper Guard: Only the root SASE agent may submit the final declaration.");
      }
      finalDeclared = true;
      return {
        content: [{ type: "text", text: "Final declaration recorded. Terminating turn." }],
        terminate: true, // Instructs Pi to halt the agent loop cleanly
      };
    },
  });

  // 2. Intercept raw git and destructive CLI calls
  pi.on("tool_call", async (event) => {
    if (event.toolName === "bash") {
      const cmd = (event.input?.command || "").trim();
      
      // Block raw git commit/push
      if (/git\s+(commit|push|merge|rebase)/.test(cmd)) {
        return {
          block: true,
          reason: "SASE Policy Violation: SASE uses host-owned completion. Do not commit or push directly; finish your work and call sase_final.",
        };
      }
      
      // Block raw PR operations
      if (/gh\s+pr\s+create/.test(cmd)) {
        return {
          block: true,
          reason: "SASE Policy Violation: PR creation is managed by SASE finalizers.",
        };
      }

      // Block guarded recipes if not inside sase tool run
      if (/just\s+(check-full|release)/.test(cmd) && !process.env.SASE_TOOL_RUN) {
        return {
          block: true,
          reason: "SASE Policy Violation: Guarded recipes must run inside 'sase tool run'.",
        };
      }
    }
  });

  // 3. Remind before settlement if unfinalized
  pi.on("agent_before_settle", async (event) => {
    if (isRootAgent && !finalDeclared) {
      // Append a single reminder message
      return {
        entries: [{
          type: "custom_message",
          role: "user",
          content: "You are about to complete your turn, but you have not yet submitted a final declaration. Use your /sase_final skill or tool to declare your work.",
        }],
        continue: true, // Allows exactly one continuation turn to declare
      };
    }
  });
}
```

---

## 5. Architectural Trade-offs & Deep Design Choices

### 5.1 Invocation Strategy: `--mode json` vs `--mode rpc`
- **Choice**: Use `--mode json` for Phase 1.
- **Rationale**:
  - SASE's contract is strictly single-turn (`single-turn-agents` decision). An agent is launched with a prompt, runs its turn, records artifacts, and exits.
  - `--mode json` requires zero complex socket or IPC state; stdout streaming with JSON lines is robust, fault-tolerant, and already modeled by SASE's `stream_json_lines` utility (used by OpenCode, Codex, and Claude).
  - Both `--mode json` and `--mode rpc` share the **exact same event shapes** for `turn_start`, `message_update`, `tool_execution_*`, and `agent_settled`. The parser written for JSON mode will be directly reusable when RPC mode is later introduced for in-turn steering.

### 5.2 Session Directory Isolation
- **Choice**: Pass `--session-dir "$SASE_ARTIFACTS_DIR/pi_sessions"` and an explicit `--session-id`.
- **Rationale**:
  - Pi default: saves to `~/.pi/agent/sessions/--<hashed-cwd>--/`.
  - In SASE, workspace `sase_17` might execute step 1 of a task, and step 2 might execute in workspace `sase_18`. If Pi hashes `cwd`, it treats `sase_18` as a completely different project, refusing to continue or offering interactive prompt dialogs that break headless CLI runners.
  - Storing sessions in the agent's artifact directory guarantees that all session JSONL files are co-located with SASE logs, archived automatically with artifacts, and easily referenced by subsequent turns using `--session <path>`.

### 5.3 Instruction Delivery: Explicit Bundles vs Ancestor Scanning
- **Choice**: Use explicit delivery (`--append-system-prompt <file> -nc`).
- **Rationale**:
  - SASE's core architectural trajectory (`instructions-per-invocation` decision) renders tailored Markdown instruction bundles per agent turn and suppresses native discovery.
  - Pi supports `-nc` (`--no-context-files`), which turns off automatic scanning of `AGENTS.md` and `CLAUDE.md`.
  - Passing `--append-system-prompt <bundle_path> -nc` ensures Pi sees exactly what SASE intended—including core memories, active reference descriptors, and macro variables—without duplicated tokens or conflicting instructions.

---

## 6. Phased Implementation Roadmap

```mermaid
flowchart LR
    P1["Phase 1:<br/>JSON Stream Adapter"] --> P2["Phase 2:<br/>Session & Instructions"]
    P2 --> P3["Phase 3:<br/>sase-pi Extension"]
    P3 --> P4["Phase 4:<br/>CLI, Doctor & TUI"]
    P4 --> P5["Phase 5:<br/>RPC Steering (Future)"]
```

### Phase 1: Core JSON Stream Adapter (Estimate: 2–3 Days)
- Scaffold `src/sase/llm_provider/pi.py`, `_subprocess_pi.py`, and `_tool_call_pi.py`.
- Register `pi` entry point in `pyproject.toml`.
- Implement `_subprocess_pi.py` using `stream_json_lines`:
  - Live reply text aggregation (`live_reply.txt`).
  - Thinking delta capture (`thinking.txt`).
  - Tool execution logging (`tool_calls.jsonl`).
  - Usage and cost aggregation (`usage.json`).
  - Terminal condition handling on `agent_settled`.
- Add unit and fixture tests using captured Pi JSONL streams (patterned after `test_fakey.py` and `test_subprocess_opencode.py`).

### Phase 2: Session Portability & Instruction Delivery (Estimate: 1 Day)
- Connect `PiProvider.llm_instruction_delivery()` to the `pi.append_system_prompt` channel.
- Implement session path plumbing: pass `--session-dir` and `--session-id` into `_subprocess_pi.py`.
- Verify multi-turn fork compatibility: test `--fork <path>` behavior across distinct mock workspace roots.

### Phase 3: Contract Enforcement via `sase-pi` Extension (Estimate: 2 Days)
- Author `src/sase/llm_provider/extensions/sase-pi/` in TypeScript.
- Implement the `tool_call` interceptor blocking unapproved git mutations.
- Implement `sase_final` tool returning `terminate: true`.
- Implement `agent_before_settle` continuation reminder.
- Pass `-e <sase_pi_path>` from the adapter.

### Phase 4: SASE Tooling, Doctor & Model Catalog Integration (Estimate: 1 Day)
- Update `src/sase/llm_provider/models.yml` with Pi's catalog, aliases, and size-alias pool inclusion.
- Wire `llm_install_metadata()` to support `sase agent-cli install pi` and `sase agent-cli update pi`.
- Wire `llm_auth_evidence()` for `sase doctor` diagnostic checks.
- Add `llm_interactive_cli()` with keybinding `p` for the tmux Agent launcher.
- Verify `just check` passes with all Symvision and lint rules green.

### Phase 5: Mid-Turn Steering via RPC Mode (Future Follow-up / Epic)
- Revisit when mid-run steering is revived on the SASE Agents tab.
- Transition `_subprocess_pi.py` to launch `pi --mode rpc --session-dir ...`.
- Expose `steer(message)` and `abort()` methods over stdin.

---

## 7. Verification & Testing Strategy

1. **Synthetic Stream Fixtures**:
   Record real Pi JSONL outputs for simple prompts, multi-tool bash/edit runs, thinking models, and error conditions (`stopReason: length`, `aborted`, `rate_limit`). Test `_subprocess_pi.py` entirely offline against these fixtures.
2. **Offline Invariant Tests**:
   - Verify that an exit code of 0 without `agent_settled` raises an error.
   - Verify that `agent_settled` with `aborted: true` reports failure.
   - Verify that `tool_calls.jsonl` receives correctly structured duration, tool name, and input summaries.
3. **End-to-End Test (when Pi CLI is installed)**:
   - Run `sase run "+home summarize this repo" -m pi:claude-3-5-haiku`.
   - Confirm that the agent launches, workspace isolation is respected, live replies stream to TUI, tool calls record to artifacts, and the finalizer lands the turn declaration cleanly.

---

## 8. Summary Table: SASE LLM Provider Parity

| Capability | Claude Code | OpenCode | Codex | **Pi (Proposed)** |
|---|---|---|---|---|
| **Invocation Mode** | `stream-json` | `run --format json` | `exec --json` | `--mode json` |
| **Terminal Signal** | Stream close | Process exit 0 | `item.completed` | **`agent_settled`** |
| **Tool Recording** | `stream-json` events | `step_finish` | `item.started/completed` | `tool_execution_*` |
| **Live Reply Stream** | Delta append | Delta append | Delta append | **Delta append** |
| **Cost Tracking** | Token counts | Token counts | Token counts | **Tokens + Dollar Cost** |
| **Instruction Channel**| `--append-system-prompt-file`| Native `AGENTS.md` | `developer_instructions` | `--append-system-prompt` |
| **Git Safety Guard** | Hook binary | Instruction text | Instruction text | **`tool_call` hook (fail-safe)** |
| **Finalizer Enforce** | Instruction text | Instruction text | Instruction text | **`sase_final` tool + settle hook** |
| **Reasoning Effort** | `--effort` | `--variant` | `--effort` | **`--thinking`** |
| **Interactive TUI** | Key `c` | Key `o` | Key `x` | **Key `p`** |

---
_End of Research Report `pi_llm_provider_implementation__gem.md`_
