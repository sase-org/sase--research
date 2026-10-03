---
narration: 1
title: Articles and papers in AntennaPod
source: research:202610/article_paper_audio_workflow/article_paper_audio_workflow__final.md
source_blob: fce262cf865b40f598602ae41b7dab8a715f3a89
date: 2026-10-03
kind: research
edition: brief
producer: agent
target_minutes: 4
---

## The recommended approach

Reuse the existing audio renderer and podcast feed. Add a small workflow that imports a source and prepares its spoken edition.

For prose articles, default to a checked reading. For technical papers, default to a short, clearly labeled briefing. Keep longer readings and selected sections available when requested.

The existing tool already handles speech synthesis, chapters, loudness, caching, and publishing. It does not directly acquire web articles or convert research PDFs. Those sources need a reviewable text intermediate.

This is a useful way to explore arguments while walking and decide what deserves focused reading. It cannot replace studying a proof, checking a detailed table, or inspecting a diagram. A smooth voice can make incomplete evidence sound more convincing than it deserves.

Start with four manually prepared episodes and one hosted comparison. Test whether listening leads to a useful next action. Avoid automatically converting the whole reading backlog. A large listening backlog would recreate the original problem.

## The deciding evidence

The researchers found both successes and failures in article extraction. One article produced meaningful chapters. Another lost its headings and acquired a newsletter chapter. A benchmark paper passed narration lint while losing important table values.

My own checks confirmed the limit of numeric lint. The source assigned 79.8% accuracy to one model and 58.0% to another. A script that swapped those scores passed without findings. A script that omitted both scores also passed.

The guard checks that spoken numbers appear somewhere in the source. It does not prove their attribution, meaning, or coverage. Keep lint, and also verify the few claims carrying the argument against the original paper.

Prefer full article or paper HTML when available. For arXiv, follow the actual full-text link and retain the paper version. An abstract page is not the complete paper.

Use a checked text extraction for a manual PDF pilot. For automated PDF support, compare structured converters on representative papers. Docling is the provisional choice, with a lighter alternative worth testing. Keep those dependencies optional.

Hosted alternatives deserve a fair trial. Audioread documents personal podcast feeds for articles and PDFs. Google now documents podcast generation APIs, correcting the reports that dismissed automation. Neither claim establishes faithful conversion of this reading list.

Choose based on the actual sources and the effort needed to produce useful listening. An editable script is particularly valuable when technical nuance matters.

## Make it useful on the phone

Delivery needs verification. The recent setup report recorded an unserved feed, a placeholder episode, quota problems, and a feed token needing replacement. Those are dated observations. Confirm current conditions before claiming the phone workflow works.

Prefer serving the feed within the existing private network when the phone can use it. Public serving behind a secret address has a different access model. Download episodes before leaving, then test chapters, seeking, playback position, and offline listening.

Keep the source identity, extraction diagnostics, and script together. Episode notes should link to the original work and identify whether this is a reading or briefing. The existing renderer needs a small metadata improvement to preserve general external-source links.

For paper briefings, retain the question, method, central evidence, limitations, and relevance. Preserve key magnitudes and their conditions. Disclose excluded visuals or technical material. Never silently replace a requested reading with a summary.

The recommended implementation is a thin listening workflow ahead of the existing renderer. Validate the small pilot first. Then automate HTML import, add optional PDF conversion when justified, and make phone capture convenient. Preserve the distinction between hearing an argument and studying all its evidence.
