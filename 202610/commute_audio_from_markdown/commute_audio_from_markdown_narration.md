---
narration: 1
title: Commute Audio From Markdown
source: research:202610/commute_audio_from_markdown/commute_audio_from_markdown.md
source_blob: 16154a30ea5fb02f1a86abfc4d0cd77f49e8bab3
date: 2026-10-01
kind: research
edition: full
producer: agent
target_minutes: 15
cover: commute_audio_from_markdown_infographic.png
---

## The question

How should Markdown become audio worth hearing on a commute or a walk? That is the question this report set out to answer, starting with the agent research in the SASE research sidecar. Structured Agentic Software Engineering, called SASE, produces long technical reports. The listener walks or rides very often, at one and a quarter to one and a half times speed, and cannot glance back at the text. So the audio has to carry the full argument, not just the vibe.

Three smaller questions sit underneath. What should be built, and what should be borrowed? How does the audio reach the phone? And which reports get narrated, since nobody can listen to everything? An earlier SASE report from June 2026 had already recommended a two-host overview mode, like a podcast about the report. This report keeps that design for an optional extra, and adds what it left open: listening to the report itself, getting the file onto the phone, and choosing what to narrate. Five independent researcher reports fed into it, plus the lead's own verification pass over vendor docs, machines, repos, keys, and code.

## The short answer

Build a small renderer called sase-listen. It turns a narration script into a chaptered, loudness-normalized MP3 episode. For research reports, a SASE agent writes that script, called an audio edition. For any other Markdown, a deterministic normalizer writes it. The default voice is Gemini 3.8 Flash text to speech, with a calm technical-briefing style. Delivery comes in two stages. First, Telegram audio messages, which need only a short change in sase-telegram. Then a private podcast feed served from the apollo server, which the AntennaPod app subscribes to. Generation stays on demand: one command or message per report, plus an opt-in swarm stage. Nothing narrates every report automatically. Audio stays out of git. Only the small narration script is committed next to its report.

The expected cost is a few dollars a month. Listening time, not money, is the real limit. September's reports alone would make 37 hours of narration, far more than a one-hour daily commute.

## Why scripts beat transcripts

The sharpest disagreement among the five reports was how to produce the spoken text. Three reports wanted a deterministic transcript by default, cleaned up by fixed rules. Two wanted a language-model-written spoken script. The lead settled it by measuring the corpus.

The numbers are stark. Across 117 September reports, the median raw length is 3,736 words, and a careful cleanup leaves a median of 2,808 words, about 19 minutes at 150 words per minute. The 90th percentile runs 29 minutes, and the longest reaches 70. 109 of the 117 reports contain at least one table, and a median of 18 percent of each report's words sit inside tables. Then comes the decisive finding. Of 97 reports with a recommendation-like section, 50 put a table inside that very section. A deterministic narrator drops tables, so it would delete the recommendation itself about half the time. Reading tables cell by cell does not rescue the big comparison tables that carry the argument.

The second finding is about residue. Even careful rule-based cleanup leaves exhausting noise. Real output from the prototype reads, quote, two mark sets that share the Space key with different meanings, open paren close paren, and hint lines the source comments themselves describe as out of room. Citations, keybindings, section symbols, and code-omitted markers survive as spoken garbage. One paragraph with four file-and-line citations took 36 seconds verbatim against 23 seconds cleaned, and a speech recognizer transcribed the citations back as, quote, Plugins browser agent clives actions. Pie, 87.

So the default for research is an agent-written audio edition, with faithfulness handled by design. The script writer already holds the report. Hard rules bind it: no new claims, every argument-carrying number kept exactly in digits, stated uncertainty preserved, tables spoken as comparisons naming the winner, the runner-up, and the deciding numbers. The script is committed next to the report, so it can be reviewed and diffed. And the deterministic normalizer still gets built, as the producer for arbitrary Markdown, the fallback with no agent around, and a final safety net that strips leftover Markdown from any script.

## The script contract

The narration script is the interface between agents and the renderer, and one contract serves both producers. Frontmatter carries the title, the source reference, the source hash, the date, the kind, the edition, and the producer. The body holds only second-level headings and plain paragraphs. Every second-level heading becomes an audio chapter and a synthesis boundary. Text before the first heading is an error.

Shape matters because the listener cannot re-read. The recommendation comes first, then the reasons, then a recap. Chapters get speakable titles that echo the report's section names, four to eight of them. Sentences stay short, acronyms are expanded on first use, and symbols are written as words. Length budgets assume 150 words per minute: a full edition holds at most about 2,400 words, roughly 16 minutes. A brief edition holds about 600 words, about 4 minutes. A digest item holds about 250 words. A pronunciation lexicon maps jargon to spoken forms before synthesis, seeded with words like ex-prompt, shay-mwah for chezmoi, you-vee, pie-pee-eye, my-pie, and loofs for L U F S. How to pronounce SASE itself is still an open question for the listener.

A lint command checks every rule, including a number-fidelity check against the source report, and the renderer refuses scripts with structural errors.

## Voices, engines, and cost

The engine table was verified against vendor pages on the first of October. ElevenLabs ranks first in listener preference at about 4 dollars 80 per audio hour. Cartesia is second at about 2 dollars 80. Gemini 3.8 Flash text to speech ranks third, at 81 cents per audio hour, doubling to 1 dollar 62 on the first of January 2027. Gemini Flash Lite is cheaper still. OpenAI's mini speech model is unranked and costs about 90 cents, with a per-request cap more than two times smaller. Kokoro 82M, the local open engine, ranks far lower but costs nothing beyond electricity. A 206-point preference gap means listeners pick Gemini over Kokoro in about 77 percent of blind pairs.

The default is Gemini 3.8 Flash: near the top in quality, the same price as the unranked mini model, generally available, and the key already exists. One fixed style prompt keeps every episode consistent: a calm, clear technical-briefing narrator at a moderate pace, with slight emphasis on numbers, reading the text exactly as written. Synthesis runs per chapter, well under the roughly 11-minute per-request cap, requesting raw audio for stitching. The local engine is Kokoro on the athena machine's graphics card, which renders a 15-minute episode in about 31 seconds, against apollo's processor at under twice real time. Two rules guard quality: never mix engines within one episode, and never fall back silently from local to cloud for private material.

Monthly cost stays small. Ten full editions run about 150 audio minutes, costing 2 dollars, rising to 4 dollars 10 next year. A daily digest plus ten full editions runs about 390 minutes, costing about 5 dollars 30. Narrating every new report would cost 24 dollars, still trivial. Again, the binding constraint is ears, not dollars.

## Sound, files, and the phone

Each episode is an MP3: mono, 24 kilohertz, 64 kilobits per second, loudness-normalized to minus 16 loudness units with a minus 1.5 decibel true peak. Chapters ride inside the file, one per heading, plus a Podcasting 2.0 chapters file in the feed. A 15-minute episode is about 7 megabytes, far under Telegram's 50 megabyte bot limit of roughly 100 minutes. Mastering concatenates the chunks with short pauses, about half a second between chunks and just over a second between chapters, trims long silences, and normalizes loudness in two passes. Quality gates check every chunk, the total duration, the chapter order, and the loudness before anything publishes. A manifest records the source, the script hash, the narrator, the chunk cache keys, and the cost estimate.

The phone is a Pixel 10 Pro on Android, and it had been off the tailnet for 11 days when checked, so anything needing the phone on the private network silently fails. That kills tailnet-only designs. Telegram audio messages give the music player with speed control, background play, and position resume, but no chapters. The private feed gives a real podcast app: queue, auto-download on Wi-Fi, skip-silence, and Android Auto. It is served from apollo over Tailscale Funnel on port 8443, under an unguessable secret path, with the feed marked blocked for public directories. Only published episodes are reachable, and a leaked token exposes only narrations of an already public repo. Private material must never enter this feed.

## What gets built first

The rollout runs in three stages. Stage zero is calibration with no code: compare the phone browser's read-aloud voices on one report, and audition candidate voices at real commute speed with traffic noise, since arena scores come from short clips and long-form fatigue may rank voices differently. Stage one is on-demand editions over Telegram: the render command, the deterministic producer with golden tests, the research audio xprompt, the Telegram audio branch, and a media engine on apollo. Stage two adds the podcast feed, the swarm audio stage, and the local Kokoro engine on athena. Stage three brings the morning digest, a speech-recognition quality gate, brief editions, and an optional two-host overview mode.

Two live checks are still owed. Render one 12-minute script end to end and measure wall time, consistency across chapters, billed silence, and the real cost against the roughly 16-cent estimate. And confirm the billing tier of the Gemini key, since free-tier quotas are too low for daily use. Those measurements become the field notes. Then the commute finally gets its library.
