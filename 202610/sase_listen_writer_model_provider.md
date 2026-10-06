# ✍️ Why sase-listen Always Writes Scripts with Gemini 3.1 Pro (and How to Use Claude)

> **Question:** why does `sase-listen render <url> -e full` always show
> `waiting on gemini-3.1-pro-preview`, and can a model from another provider, such as
> Claude, write the script instead?
>
> **Bottom line:** `gemini-3.1-pro-preview` is the hard-coded default of `writer.model`,
> and nothing on athena overrides it. `sase-listen config` reports
> `writer … # origin=default`. You can already switch to **any other Gemini text model**
> with `writer.model` or `SASE_LISTEN_WRITER_MODEL`. You **cannot** switch to another
> provider. `writer.engine` only accepts `gemini`: the config loader rejects any other
> value, and `create_writer()` only builds a `GeminiWriter`. Gemini was chosen because
> the episode epic reused the Gemini credentials and `google-genai` SDK that TTS already
> needed, and it shipped with "gemini (the only supported engine for now)". There are
> two ways to get Claude today: write the narration script outside sase-listen and render
> the file (works now, no code), or add a small `anthropic` writer engine (recommended,
> about one phase of work; design below).

_Checked 2026-10-06 against `sase-org/sase-listen@f8154ad` (master), the installed
sase-listen 0.1.0 on athena (google-genai 2.28.0), the chezmoi-managed
`~/.config/sase-listen/config.yml`, epic plan `plan:202610/listen_urls_any_machine.md`,
and phase bead `sase-1g7.3`._

---

## 1. Where the Gemini 3.1 Pro default comes from

The "Write script" stage is the **article writer**. It turns a fetched URL or PDF into a
`brief` or `full` narration script. It is separate from the **narrator** (TTS), which
already supports several providers (`gemini`, `gemini-lite`, `openai`, `tone`).

| Layer | What pins it to Gemini | Location |
| --- | --- | --- |
| Default model | `WriterConfig.model = "gemini-3.1-pro-preview"` | `src/sase_listen/config.py:100` |
| Config validation | any `writer.engine` other than `gemini` raises `Unknown config value 'writer.engine': use 'gemini'.` | `src/sase_listen/config.py:386-387` |
| Factory | `create_writer()` rejects non-`gemini` engines ("The only supported writer engine is gemini."), resolves the key from `engines.gemini`, and always returns a `GeminiWriter` | `src/sase_listen/writer/__init__.py:15-43` |
| Adapter | `GeminiWriter` calls `google.genai` `client.models.generate_content(...)` with `max_output_tokens=16384` | `src/sase_listen/writer/gemini.py` |
| Progress label | the live checklist prints `waiting on {cfg.writer.model}`, which is the line you saw | `src/sase_listen/writer/author.py:249,256` |
| Your config | `~/.config/sase-listen/config.yml` (chezmoi) sets `narrator`, `engines.gemini`, and `feed`, but has **no `writer:` section** | `sase-listen config` → `writer: {...} # origin=default` |

The run you pasted takes the default path: no `writer:` section in the file and no
`SASE_LISTEN_WRITER_MODEL` in the environment, so you get `gemini-3.1-pro-preview`.

### Why Gemini, and why this exact model

- **Gemini as the engine.** The writer came from epic `sase-1g7` (phase `sase-1g7.3`,
  commit `9f491ac`). Its plan says the `writer:` section has
  "`engine: gemini` (the only supported engine for now; validate it)". It also says
  "Credentials reuse `engines.gemini` through `engines.secrets.resolve_api_key`." Every
  machine already had a Gemini key (`pass show gemini_cli_api_key`) and the
  `google-genai` dependency for TTS. Gemini therefore needed no new secret, SDK, or
  config section. The `engine` key was kept, and validated, as the extension point for
  later providers.
- **This exact model ID.** The plan said to confirm the model live and pick a pro-class
  default, and named `gemini-pro-latest` as available. The phase agent's close note
  says live model listing failed because the key returned `API_KEY_INVALID`, the
  stale-key problem fixed on 2026-10-05. The agent therefore chose
  `gemini-3.1-pro-preview` from Google's published model guide. It is a pinned
  **preview** ID rather than the `gemini-pro-latest` alias, and that choice was never
  checked live.

---

## 2. What you can change today without code

| You set | Result |
| --- | --- |
| `writer.model: <gemini model>` in config.yml | Works. Any Gemini text model the key can see, for example `gemini-3.8-flash` (faster and cheaper) or `gemini-pro-latest` (the alias the plan intended). |
| `SASE_LISTEN_WRITER_MODEL=<gemini model>` | Works. The env var overrides the file (`config.py:447-451`); useful for one run. |
| `writer.temperature`, `max_attempts`, `timeout_s` | Work. These tune the Gemini call and the lint-repair loop. |
| `SASE_LISTEN_WRITER_MODEL=claude-opus-5-5` | **Fails at write time.** Config accepts any non-empty string, but the ID is sent to the Gemini API, which returns an error. That surfaces as `Article script writing failed: Gemini writer request failed (HTTP …)`. |
| `writer: {engine: anthropic}` (or `claude`) | **Fails at config load** with `Unknown config value 'writer.engine': use 'gemini'.` This breaks every command, not just `render`. |

Notes:

- Cached scripts are keyed on source SHA, prompt version, edition, **and model**
  (`author.py:142-150`). Changing the model re-writes each source once and then caches
  the result.
- Your config is chezmoi-managed (`home/dot_config/sase-listen/config.yml`). Make
  persistent changes there, not in `~/.config` directly.

---

## 3. Getting Claude to write the script

### Option A: write the script outside sase-listen, then render it (works now)

`render` and `lint` accept a hand-written narration Markdown file, and rendering a file
makes **no writer call**. Research audio already uses this path: a SASE agent writes the
script and sase-listen only speaks it.

```bash
sase-listen guide --edition full > /tmp/guide_full.md       # the same rules the writer gets
# Have Claude (a SASE agent, Claude Code, or `claude -p`) read the guide plus the
# article or PDF and write paper_narration.md: frontmatter plus ## chapters.
sase-listen lint paper_narration.md --source <source.md>    # repeat until clean
sase-listen render paper_narration.md
```

- **Pros:** no code change, and you can use any Claude model or subscription.
- **Cons:** you lose what `render <url>` does for you. Those steps are deterministic
  frontmatter, the article-adaptation and PDF rules from `writer/prompt.py`, the
  automatic lint-repair loop, and the per-source cache. To get the same quality, give
  Claude the `_ARTICLE_RULES` and `_PDF_RULES` text as well as the guide. The extracted
  source is cached as `$XDG_DATA_HOME/sase-listen/sources/<key>/source.md`, and
  `sase-listen script <url> -e verbatim` fills that cache without calling an LLM.

### Option B: route the Gemini SDK through a translating proxy (not recommended)

google-genai 2.28 reads `GOOGLE_GEMINI_BASE_URL` (`google/genai/_base_url.py:50`), and
the writer does not pin a base URL. You could put a proxy in front of it that speaks
Gemini's `generateContent` format and forwards to Anthropic.

Do not do this. The TTS engine builds its `google.genai.Client` the same way
(`engines/gemini.py:193-195`), so the variable redirects **narration traffic too**. The
proxy would also have to translate Gemini's request and usage shapes in both directions.
The result is fragile and only looks like a writer engine from the outside.

### Option C: add an `anthropic` writer engine (recommended)

The code was built for this. `Writer` is a one-method protocol
(`write(system, user) -> WriterReply`), and the lint, repair, cache, frontmatter, and
progress code in `author.py` never touches Gemini. Only the hint text at
`author.py:266` mentions it. The change has five parts.

**1. Config** (`config.py`): allow `writer.engine: anthropic`, and add an
`engines.anthropic` section that reuses `EngineConfig`:

```yaml
writer:
  engine: anthropic
  model: claude-opus-5-5
engines:
  anthropic:
    api_key_command: pass show anthropic_api_key   # or rely on ANTHROPIC_API_KEY
```

- Default `api_key_env` should be `[SASE_LISTEN_ANTHROPIC_API_KEY, ANTHROPIC_API_KEY]`,
  plus a `SASE_LISTEN_ANTHROPIC_API_KEY_COMMAND` override, matching the gemini and openai
  sections.
- Update `_TOP_LEVEL_KEYS`, the `engines` key allow-list (now `gemini`/`openai` only),
  and `masked_snapshot`.
- If `writer.model` is left at its Gemini default while `engine: anthropic` is set, use
  an engine-specific default (`claude-opus-5-5`) instead of sending a Gemini ID to
  Anthropic.

**2. Adapter** (`writer/anthropic.py`), using the official `anthropic` Python SDK. A
sketch:

```python
import anthropic

client = anthropic.Anthropic(api_key=api_key, timeout=timeout_s, max_retries=0)
with client.messages.stream(
    model=model,                       # e.g. "claude-opus-5-5"
    max_tokens=32000,                  # room for adaptive thinking + a ~3-4k-token script
    system=system,
    messages=[{"role": "user", "content": user}],
    output_config={"effort": effort},  # e.g. "high"; Opus 5.5 defaults to "medium"
) as stream:
    message = stream.get_final_message()
if message.stop_reason in ("refusal", "max_tokens"):
    ...  # map to PermanentEngineError / TransientEngineError
text = "".join(b.text for b in message.content if b.type == "text")
return WriterReply(text, model_version=message.model,
                   input_tokens=message.usage.input_tokens,
                   output_tokens=message.usage.output_tokens)
```

`max_retries=0` lets sase-listen's own `synthesize_with_retry` own retries and progress
countdowns, as it does for Gemini.

**3. Differences from the Gemini adapter that will bite:**

- **No `temperature`.** Claude Opus 5.5 rejects sampling parameters with HTTP 400, and
  Claude Sonnet 5.5 rejects non-default values. `writer.temperature` must be dropped for
  this engine, not passed through. Use an `effort` setting instead
  (`low`…`max`; the default on Opus 5.5 is `medium`).
- **Thinking is always on** for Opus 5.5 and cannot be disabled. The response contains
  `thinking` blocks before the `text` block, so join only the `text` blocks. Thinking
  tokens count against `max_tokens`. That is why the sketch uses about 32k with streaming
  instead of Gemini's 16,384 non-streaming.
- **Stop reasons.** `refusal` (check `stop_details`) and `max_tokens` arrive as HTTP 200,
  so check them before reading text. The Gemini adapter has no equivalent check.
- **Error mapping.** Catch the SDK's typed errors, most specific first:
  `AuthenticationError` → `CredentialsError`;
  `RateLimitError` → `TransientEngineError(retry_after=…)`;
  `APIStatusError` with status ≥ 500 → transient;
  `APIConnectionError` → transient. The `anthropic` 1.x SDK uses `httpx2`, so the Gemini
  adapter's `httpx.TimeoutException` handlers do not carry over.
- **Optional refusal fallback.** For `claude-opus-5-5`, Anthropic's server-side
  `fallbacks` parameter re-runs a declined request on a fallback model. It needs
  `client.beta.messages` with beta `server-side-fallback-2026-07-01` and
  `fallbacks="default"`. Refusals are unlikely for article narration, but turning this on
  is cheap insurance.

**4. Packaging and docs.**

- Add `anthropic` to `pyproject.toml` and refresh `uv.lock`.
- Update `docs/configuration.md` ("Article writer"), `docs/web-articles.md` (it says the
  writer "uses Gemini"), the `author.py:266` hint, the `create_writer` error hint, and
  the request-snapshot and error-mapping tests in `tests/test_writer.py`. The tests use a
  stub client, as `GeminiWriter` already does with `client_factory`.

**5. Rollout order.**

- The config loader rejects unknown keys. Upgrade sase-listen on athena, apollo, and the
  Mac **before** adding `writer.engine: anthropic` or `engines.anthropic` to the chezmoi
  config, or older installs stop loading config.
- Store an Anthropic key in `pass`. `pass` currently holds `gemini_cli_api_key`, and
  there is no Anthropic entry yet.

**Rough cost (assumption-laden).** A full edition of an arXiv paper sends about
20,000–30,000 input tokens (guide, rules, and source) and gets back about 3,000–4,000
script tokens, plus thinking. At Claude Opus 5.5 list prices ($4/$20 per MTok), one
attempt costs about $0.10–0.15 of input and $0.10–0.20 of output, so roughly $0.20–0.35.
The lint-repair loop allows up to three attempts. Claude Sonnet 5.5 ($2/$10) costs about
half as much. These are estimates, not measurements; `render --dry-run` already reports
writer token usage, so measure on two or three real papers before choosing a default.

### Option D: a generic `command` writer engine (alternative)

`writer.engine: command` would pipe `system` and `user` to a configured command, such as
`claude -p` or another provider's CLI, and read the script from stdout. This would bill
against a Claude subscription instead of the API and would support any provider at once.

The cost is weaker behavior:

- no token or `model_version` metadata
- CLI-specific exit codes and error text that must be classified by string matching
- agent harnesses that may add preamble or use tools

Keep it as a follow-up if API billing is the blocker. Option C is cleaner.

---

## 4. Recommendation

1. **Now:** to stop waiting on a preview model, set `writer.model` in the chezmoi config
   to a non-preview Gemini model (`gemini-pro-latest`, or `gemini-3.8-flash` for speed).
   To have Claude write a particular episode, use Option A.
2. **Next:** add the `anthropic` writer engine (Option C) as one sase-listen phase.
   Default it to `claude-opus-5-5` at `effort: high`, with no temperature. Roll it out in
   the upgrade-then-config order.
3. Leave the narrator as it is. Claude has no TTS endpoint, so speech stays on
   Gemini or OpenAI TTS whichever engine writes the script.

---

## Sources

- sase-listen `@f8154ad`: `src/sase_listen/config.py`, `src/sase_listen/writer/{__init__,base,gemini,author,prompt}.py`,
  `src/sase_listen/engines/gemini.py`, `docs/configuration.md`, `docs/web-articles.md`,
  `docs/cli.md`; commits `9f491ac` (writer) and `e085c63` (URL fetch).
- Epic plan `plan:202610/listen_urls_any_machine.md` (Phase url-editions → Writer; the
  "Gemini text models visible to the key" research note).
- Phase bead `sase-1g7.3`: close note on the live model-list failure and the
  `gemini-3.1-pro-preview` choice.
- Live on athena: `sase-listen config` (writer `origin=default`), the chezmoi-managed
  `~/.config/sase-listen/config.yml`, and installed google-genai 2.28.0
  (`_base_url.py` `GOOGLE_GEMINI_BASE_URL`).
- Claude API reference (bundled `claude-api` skill, model table cached 2026-09-25):
  model IDs, pricing, the Opus 5.5 always-on thinking and `medium` effort default,
  sampling parameters removed on Opus 5.5 and restricted on Sonnet 5.5, refusal stop
  reason and server-side fallbacks, and the `anthropic` 1.x `httpx2` transport.
