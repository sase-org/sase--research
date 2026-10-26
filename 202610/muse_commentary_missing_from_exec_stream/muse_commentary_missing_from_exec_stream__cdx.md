# Muse’s empty live Reply card: commentary is missing from the exec stream

Researcher: **cdx** · Investigated: **2026-10-26** · Scope: independent diagnosis and recommended solution; no production changes.

## Finding

**The affected agent is producing commentary, but SASE is listening to a Muse output channel that does not deliver it.** On the installed **Muse Code 1.4.13 / 1.4.13-R6996.1**, `muse exec --json` emits tool lifecycle events and the final answer, while intermediate assistant messages with `phase: "commentary"` are retained in Muse’s session log and omitted from that stdout stream. SASE writes `live_reply.md` only when it receives `run.output.delta`. Consequently, the Reply card has no text to render until the final answer.

This conclusion is supported by inspection of the exact `bob-cli-cn.1` run on athena, a deterministic reproduction using the same Muse binary release against a local fake provider, and a positive control through SASE’s actual parser. Confidence is **high for this reported case**. I did not intercept the live agent’s stdout pipe; doing so could consume its data. The controlled reproduction establishes the stdout behavior independently.

The recommended immediate fix is a narrowly scoped session-log observer in the Muse adapter: stream committed root-run commentary into the existing reply artifacts while continuing to use exec stdout for final-answer deltas and terminal outcome. A TUI refresh change cannot recover text that never reaches those artifacts.

## Evidence from the reported agent

I inspected `/home/bryan/tmp/screenshots/20261026_134521.png`. It shows athena’s TUI at `v0.18.1+12.g60832648b`, selected agent `bob-cli-cn.1`, model `muse-spark-1.3-contributor`, effort `xhigh`, a running state, **131 tool entries**, and `Waiting for agent response...` in the Reply card.

Using read-only SSH and `sase agent show bob-cli-cn.1`, I resolved its current run artifacts to:

```text
athena:/home/bryan/.sase/projects/gh_bobs-org__bob-cli/artifacts/ace-run/202610/26/20261026131420/
```

At **17:52:55 UTC**, the observed state was:

| Observation | Value |
| --- | --- |
| Runner PID | `2223096` |
| Muse child PID | `2469869` |
| Executable | `/home/bryan/.local/bin/muse-bin-1.4.13-R6996.1` |
| `live_reply.md` | **0 bytes** |
| `live_reply_timestamps.jsonl` | **0 bytes** |
| `tool_calls.jsonl` | **244,276 bytes** |
| Muse’s `SASE_ARTIFACTS_DIR` | Correctly points to the artifact directory above |
| Session ID from Muse argv | `66b7ac36-396c-49f1-a3ef-58d4e1a43008` |
| Committed assistant messages in that session | **25; all explicitly `commentary`** |

These are live observations of the target run, not completed transcript evidence. The tool artifact increased from 242,206 to 244,276 bytes between observations while both reply files stayed empty. I did not modify this agent, its artifacts, or its processes.

The corresponding Muse log is:

```text
athena:/home/bryan/.local/share/muse/sessions/2026/10/26/66b7ac36-396c-49f1-a3ef-58d4e1a43008/session.jsonl
```

Examples of already committed commentary:

| UTC time | Session sequence | Text |
| --- | --- | --- |
| 17:24:00.691534 | 51 | “Fixing your phase bead — reading scope and landing the work.” |
| 17:24:37.217667 | 435 | “Plan is clear — building the additive typical field now.” |
| 17:43:40.558101 | 4477 | “Contract verified — measuring performance before/after.” |
| 17:50:46.490478 | 5387 | “Four new clippy warnings are mine — fixing them.” |

These are user-facing assistant messages, not hidden reasoning or tool output. The first message’s retained shape is:

```json
{
  "payload_type": "runtime.session",
  "payload": {
    "kind": "run",
    "run_id": "01a1793d-82c9-7ee1-acf6-38c7bca82e97",
    "event": {
      "kind": "assistant_message_committed",
      "message_id": "fbb3630d-1e2b-4f9b-8524-52be7bbccc7a",
      "phase": "commentary",
      "text": "Fixing your phase bead — reading scope and landing the work."
    }
  }
}
```

## Where the text is lost

Source inspection used SASE commit `60832648be4292fc5f49565a34b44402c40cba1b`, matching the screenshot’s short build revision.

1. **Launch.** `MuseProvider.invoke()` constructs `muse exec --json`, generates a fresh `--session-id`, and passes that ID into `stream_and_parse_muse_json_output()`. The concrete athena argv uses exactly this launch surface. [Provider launch and session creation](https://github.com/sase-org/sase/blob/60832648be4292fc5f49565a34b44402c40cba1b/src/sase/llm_provider/muse_provider.py#L351)
2. **Reply extraction.** `_process_muse_json_line()` routes `run.output.delta` to `_stream_output_delta()`. That function reads `payload.text`, appends it to the live artifact, and flushes. It does not consume `runtime.session` assistant-message records. `run.terminal.*` text is accumulated separately as the authoritative return value. [Muse parser, lines 180–223 and 252–321](https://github.com/sase-org/sase/blob/60832648be4292fc5f49565a34b44402c40cba1b/src/sase/llm_provider/_subprocess_muse.py#L180)
3. **Session-log access is late and usage-only.** The existing session reader runs after stdout processing/process completion and extracts `model_completed` usage. It never projects live commentary. The session ID is also written into `run_metadata.json` only after parsing finishes. [Parser lifecycle](https://github.com/sase-org/sase/blob/60832648be4292fc5f49565a34b44402c40cba1b/src/sase/llm_provider/_subprocess_muse.py#L128), [session lookup and usage reader](https://github.com/sase-org/sase/blob/60832648be4292fc5f49565a34b44402c40cba1b/src/sase/llm_provider/_muse_session_usage.py#L49)
4. **Artifacts and UI.** `append_stream_delta()` flushes the reply file even when `suppress_output=True`; suppression only affects console printing. The running-agent renderer reads the live text/chunks and shows the waiting placeholder if neither contains text. The completed-agent path instead reads the saved response. This directly explains the apparent arrival at completion. [Artifact writer](https://github.com/sase-org/sase/blob/60832648be4292fc5f49565a34b44402c40cba1b/src/sase/llm_provider/_subprocess_artifacts.py#L136), [Reply rendering](https://github.com/sase-org/sase/blob/60832648be4292fc5f49565a34b44402c40cba1b/src/sase/ace/tui/widgets/prompt_panel/_agent_display_render_main.py#L439)

The two paths are:

```text
Muse root assistant commentary
  -> session.jsonl / runtime.session / assistant_message_committed
  -> no live SASE consumer
  -> empty live_reply.md -> Reply card waits

Muse final answer
  -> exec stdout / run.output.delta + run.terminal.completed
  -> SASE live artifact + authoritative returned response
  -> reply becomes visible near completion
```

Unlike Muse’s adapter, the Claude adapter writes ordinary assistant text blocks and the Codex adapter writes completed `agent_message` items throughout the run. Their live-reply sources naturally include progress messages. [Claude handling](https://github.com/sase-org/sase/blob/60832648be4292fc5f49565a34b44402c40cba1b/src/sase/llm_provider/_subprocess_claude.py#L207), [Codex handling](https://github.com/sase-org/sase/blob/60832648be4292fc5f49565a34b44402c40cba1b/src/sase/llm_provider/_subprocess_codex.py#L410)

## Controlled reproduction and buffering control

I exercised the installed `muse-bin-1.4.13-R6996.1` on apollo, the same release as athena. This was a deterministic transport probe, not a model invocation: an ephemeral loopback HTTP server supplied scripted Responses-style SSE, a dummy credential, and a fake model catalog. The workspace and XDG data/config directories were isolated; the only tool operation was reading a disposable `probe.txt`. Reminders, shell execution, writes, and web tools were disabled. No real model endpoint was contacted.

The endpoint returned:

1. A completed assistant message containing `CDX EARLY COMMENTARY`, explicitly marked `phase: "commentary"`, plus a `read_file` call.
2. After the tool result and a one-second hold, a final message containing `CDX FINAL ANSWER`.

The binary exited **0** after **2.293 seconds** and **two provider requests**. Its session log contained both assistant messages. Its stdout contained **one** `run.output.delta`, carrying only `CDX FINAL ANSWER`, and a `run.terminal.completed` carrying that same final text. It contained no commentary record and no MSP `method` notification. The echo-provider control also emitted the legacy envelope format.

I then replayed this captured stdout through SASE’s real `stream_and_parse_muse_json_output()` with a child process held alive on stdin before the final-answer records. A separate positive control supplied an early `run.output.delta` through the same parser. Results:

| Test | While child still alive | After release |
| --- | --- | --- |
| Captured Muse stream, held before final delta | Reply empty; timestamp file 0 bytes; tool artifact 720 bytes | Returned and live reply both `CDX FINAL ANSWER`; exit 0 |
| Early-delta positive control | Reply immediately `EARLY CONTROL`; timestamp file 68 bytes | Parser completes normally |

This rules out a general “SASE waits for process exit before flushing” explanation. The common JSONL transport also already uses nonblocking descriptor reads and incremental decoding, rather than waiting for EOF. [Transport](https://github.com/sase-org/sase/blob/60832648be4292fc5f49565a34b44402c40cba1b/src/sase/llm_provider/_subprocess_stream.py#L151)

A local fake-provider reproduction script is preserved below so the finding does not depend solely on the captured athena state. Save it as a Python file in a disposable workspace directory before running; it creates probe files beneath that directory. Adjust the pinned binary path if needed.

<details>
<summary>Deterministic reproduction script</summary>

```python
import json, os, pathlib, subprocess, threading, time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from collections import Counter
root=pathlib.Path(__file__).resolve().parent
for d in ['config','data','probe-workspace']:(root/d).mkdir(exist_ok=True)
(root/'probe-workspace'/'probe.txt').write_text('read-only probe input\n')
class Handler(BaseHTTPRequestHandler):
 calls=0
 def log_message(self,*args):pass
 def do_GET(self):
  body=json.dumps({"object":"list","data":[{"id":"fake-model","object":"model","metadata":{"muse-code":{"release_date":"2026-01-01","is_hidden":False,"limit":{"context":1000000,"output":1024}}}}]}).encode()
  self.send_response(200);self.send_header("Content-Type","application/json");self.send_header("Content-Length",str(len(body)));self.end_headers();self.wfile.write(body)
 def do_POST(self):
  self.rfile.read(int(self.headers.get('content-length',0)))
  Handler.calls+=1;n=Handler.calls
  rid=f'resp_cdx_{n}';mid=f'msg_cdx_{n}';text='CDX EARLY COMMENTARY' if n==1 else 'CDX FINAL ANSWER'
  msg={'type':'message','role':'assistant','id':mid,'status':'completed','phase':'commentary' if n==1 else 'final_answer','content':[{'type':'output_text','text':text,'annotations':[]}]}
  output=[msg]
  events=[{'type':'response.created','response':{'id':rid,'object':'response','model':'fake-model','status':'in_progress','output':[]}}, {'type':'response.output_item.added','output_index':0,'item':dict(msg,status='in_progress',content=[])}, {'type':'response.output_text.delta','output_index':0,'item_id':mid,'content_index':0,'delta':text}, {'type':'response.output_text.done','output_index':0,'item_id':mid,'content_index':0,'text':text}, {'type':'response.output_item.done','output_index':0,'item':msg}]
  if n==1:
   args=json.dumps({'path':str(root/'probe-workspace'/'probe.txt')})
   tool={'type':'function_call','name':'read_file','id':'fc_cdx_read','call_id':'call_cdx_read','arguments':args,'status':'completed'};output.append(tool)
   events += [{'type':'response.function_call_arguments.done','output_index':1,'item_id':tool['id'],'name':tool['name'],'call_id':tool['call_id'],'arguments':args}, {'type':'response.output_item.done','output_index':1,'item':tool}]
  events += [{'type':'response.completed','response':{'id':rid,'object':'response','model':'fake-model','status':'completed','output':output,'usage':{'input_tokens':1,'output_tokens':1,'total_tokens':2}}}]
  self.send_response(200);self.send_header('Content-Type','text/event-stream');self.end_headers()
  if n==2:time.sleep(1)
  for i,e in enumerate(events,1):
   e['sequence_number']=i;self.wfile.write(('data: '+json.dumps(e)+'\n\n').encode());self.wfile.flush()
server=ThreadingHTTPServer(('127.0.0.1',0),Handler);threading.Thread(target=server.serve_forever,daemon=True).start()
env={k:v for k,v in os.environ.items() if not k.startswith(('SASE_','MUSE_','META_','OPENAI_'))}
env.update(XDG_CONFIG_HOME=str(root/'config'),XDG_DATA_HOME=str(root/'data'),MUSE_NO_AUTO_UPDATE='1')
args=['/home/bryan/.local/bin/muse-bin-1.4.13-R6996.1','exec','--json','--provider','meta','--model','fake-model','--base-url',f'http://127.0.0.1:{server.server_port}','--api-key-stdin','--workspace',str(root/'probe-workspace'),'--disable-reminders','--disable-write','--disable-shell','--disable-web-tools','--no-foreign-personal-context','--max-model-steps','2','Read probe.txt and report.']
started=time.monotonic()
try:
 p=subprocess.run(args,input='cdx-dummy-key\n',capture_output=True,text=True,env=env,timeout=30)
 (root/'fake.jsonl').write_text(p.stdout);(root/'fake.stderr').write_text(p.stderr)
 print('returncode',p.returncode,'requests',Handler.calls,'elapsed',round(time.monotonic()-started,3))
 rows=[]
 for l in p.stdout.splitlines():
  try:rows.append(json.loads(l))
  except json.JSONDecodeError:pass
 print('stdout types',dict(Counter(r.get('payload_type') or r.get('method') for r in rows)))
 for r in rows:
  if r.get('method') or 'output.delta' in r.get('payload_type','') or r.get('payload_type','').startswith('run.terminal'):
   print('stdout text event',json.dumps(r)[:2200])
 for log in (root/'data'/'muse'/'sessions').glob('*/*/*/*/session.jsonl'):
  print('session_log',log.relative_to(root))
  for l in log.read_text().splitlines():
   r=json.loads(l);pl=r.get('payload',{});event=pl.get('event') or {}
   if event.get('kind')=='assistant_message_committed': print('session message',json.dumps(event))
 if p.returncode: print('stderr',p.stderr[-3500:])
finally:server.shutdown();server.server_close()
```

</details>

## Why existing tests and earlier fixes miss this

The committed Muse stream fixtures are keyed to older releases (`R708.1`, plus a shell fixture for `R3401.1`). They contain final-answer deltas and terminal events. Their live-reply assertions inspect the artifact after replay completes; they do not require a commentary message to appear while tools are still running. Synthetic split-delta tests establish correct concatenation when deltas exist, not that the real provider supplies progress messages. [Tests](https://github.com/sase-org/sase/blob/60832648be4292fc5f49565a34b44402c40cba1b/tests/llm_provider/test_muse_provider_stream.py#L71)

The September 20 fix (`a0244d7599`) corrected mid-word fragmentation by coalescing deltas. The October 3 transport fix (`392983091d`) corrected JSONL draining. Neither adds a source for Muse commentary. Both can be correct while this symptom persists.

A documentation trap also matters: the current official SDK’s `UnframedViewNotification` schema says `view/page` and `muse exec --json` share `{method, params}` notifications. The **installed binary’s actual exec behavior in both probes remained the older envelope format**. Do not assume that simply handling MSP `item/completed` on today’s exec stdout will fix this installation. The schema describes a useful migration target, but does not prove that the active launch surface emits it. [Official SDK schema at inspected revision `3dce908f556bd8b3dfc9cd7f28f442b0504d74a4`](https://github.com/meta-models/muse-code-sdk/blob/3dce908f556bd8b3dfc9cd7f28f442b0504d74a4/schema/msp/msp.d.ts#L3503)

The official docs confirm that `exec --json` is the JSONL headless surface and describe `muse serve` as the session-protocol alternative. They do not establish that every commentary message reaches the exec channel used here. [Meta headless documentation](https://dev.meta.ai/docs/muse-code/extending), [Meta Muse Code overview](https://dev.meta.ai/docs/muse-code)

## Recommended solution

**Add a live, incremental commentary observer to the Muse provider using the session ID SASE already supplies. Keep the current terminal-answer behavior.** This repairs the observed installation with less lifecycle disruption than converting the provider to MSP immediately.

1. **Persist the session identity at launch.** Record `muse_session_id` before the long parse call; use the configured XDG data root and the existing exact-ID lookup. Bind the observer to this invocation’s session and root `run_stream.id` from `session.run.linked`. Never scan every session on each refresh or recurse into observer/subagent logs.
2. **Tail only new complete records.** Maintain a byte offset and incomplete-line buffer, retry discovery until the named log appears, and poll at a modest interval while stdout is quiet as well as busy. The observed version also writes `retained_frame` containers: support their ordered `children[].record_json` envelopes rather than assuming every line has `payload_type`. Handle cancellation and perform a final bounded drain when the process exits. Use the same writer/queue as stdout processing so timestamp offsets and text appends cannot race.
3. **Normalize only explicit root commentary.** Select `runtime.session`, `payload.kind == "run"`, the current run ID, `event.kind == "assistant_message_committed"`, and `event.phase == "commentary"`. Emit one timestamped chunk per unique `(session_id, run_id, message_id)` and retain source timestamps where practical. This provides live delivery per committed message; it does not promise token-level commentary streaming. Keep reasoning, tool output, reminder children, and foreign sessions out of the Reply card.
4. **Keep final text authoritative and separate.** Continue consuming `run.output.delta` and `run.terminal.*` for the existing final-answer path. Do not also append final session messages, which would duplicate that text. Commentary must not enter the final-answer accumulator or trigger wait-claim logic. If a future exec format supplies commentary too, choose one source per message and deduplicate by identity, rather than appending both. Terminal-without-delta display recovery can be tested separately without confusing it with the missing-commentary fix.
5. **Place shared semantics in Rust.** Following the repository’s backend boundary, put event normalization, root/message filtering, and deduplication state in `sase_core`; expose a versioned binding through `sase_core_rs`. Keep process supervision, filesystem polling, and artifact I/O as thin Python adapter code. Update `sase-core-revision.txt` when the binding lands. There is no need for a Muse-specific branch in the Textual Reply renderer.
6. **Verify the temporal contract.** Add an integration fixture with commentary, subsequent tool activity, and a withheld final response. Assert the live Reply artifact becomes nonempty while the child is still alive, then verify the rendered Reply card updates. Cover partial lines/UTF-8, retained frames, duplicate records, multiple sessions/continuations, non-root messages, no log, and final-answer deduplication. Preserve the positive early-delta test and current terminal-authority tests. Missing-log degradation should be observable instead of silently pretending live commentary is supported.

MSP is a credible longer-term replacement if SASE wants a single documented live view transport. Its `agentMessage` items, `messagePhase`, item IDs, and authoritative `item/completed` objects provide useful structure. However, migration also changes launch, completion, cancellation, and session lifecycle handling. Validate its installed behavior and version support before choosing that larger change. Merely adding MSP parsing to the legacy exec stream is insufficient for the reproduction above.

**My recommendation is to implement the bounded session-log commentary observer first, backed by the held-open integration test. The immediate defect is the gap between Muse’s retained commentary channel and SASE’s live-reply ingestion, not the deck renderer or an output-flush setting.**
