---
narration: 1
title: A Listen Link for Research Reports
source: research:202610/research_swarm_listen_link/research_swarm_listen_link__final.md
source_blob: 885adda0b6232f6c6c4c3bfc4462b1f9a64567d8
date: 2026-10-04
kind: research
edition: brief
producer: agent
target_minutes: 4
---

## The question and short answer

The question is how to connect a research report to its narrated audio summary. The reader should find it quickly. The link should survive the report's journey into Highlights, the application used to read and annotate portable document format files. We will call those files PDFs.

The recommendation is to build it. Put a simple listen link near the top of the report. Store the MP3 audio file beside the report. Let Bob, the vault tooling, carry it alongside the PDF into Obsidian. Obsidian supplies the actual audio player.

There is a change in emphasis. This is a brief of about 4 minutes, rather than a synchronized reading. The useful invitation is to listen first, then read what matters. Label the link with its edition and actual duration.

The linker agent should assemble the published report after audio finishes. Audio should still begin immediately after the lead researcher. It should run alongside the image agent, without waiting for cover art.

## The deciding reasons

Timing is the first constraint. The file hook creates the PDF only when the published Markdown report is first added. Adding a listen link later will not rebuild that PDF. The audio must therefore exist before the linker publishes.

Today, requesting audio does not automatically start the linker. The linker also does not wait for audio. Both behaviors must change. With an infographic, observed audio and image completion times are about the same. Without an infographic, waiting for audio delays publication by about 10 minutes.

The second constraint is portability. A local audio-library path means nothing on the reader's Mac. A relative MP3 link survives across research checkouts and GitHub, but PDF viewers do not resolve it properly. Bob must rewrite the PDF link so it opens the vault's audio file in Obsidian.

The podcast feed is unsuitable as permanent report storage. Its address contains a secret, and episodes are pruned after 90 days or 200 episodes. The research repository is public. Publishing that address would disclose the secret. A token-free route on the public feed server could expose personal episodes too.

Committing the MP3 beside the report avoids a new server and gives the linker a dependable companion file. This reverses the earlier rule against storing generated audio in the research repository, specifically for linked swarm editions. A brief is about 2.2 MB. Reconsider storage when the research pack passes about 1 GB, or audio becomes enabled by default.

## The recommended solution

Ship Bob's support first. It should recognize local audio links, copy the companion into the intake queue, and rewrite the PDF target. Make that target configurable so the destination can change later.

When Bob imports the PDF into the vault, move its audio companion too. Put a native Obsidian player directly below the note's task for opening the PDF. If the MP3 arrives later, pair it on the next scan and insert the player once.

Then update the swarm. Requesting audio should imply the linker, and the linker should wait for audio. Add one restrained listen line inside the research-query quotation. Use a play triangle, an edition label, and the rounded duration. Keep cover art opportunistic.

A failed speech render should leave no MP3 and no listen line. The written report should still publish. An agent crash can still strand the linker, just as an image-agent crash can today. A future wait mode that accepts any terminal outcome would fix both cases.

Finally, test the real reading experience on the Mac. Confirm that Highlights opens the Obsidian link and that playback continues while reading the PDF. Those behaviors remain unverified. Keep the design simple, but make this acceptance test part of shipping it.
