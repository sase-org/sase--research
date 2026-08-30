# Naming a successor to `sase`

_Research date: 2026-08-30_

## Executive conclusion

The most useful way to describe the product is not merely “an orchestrator for coding
agents.” It is a **compound operational view**: it fans work out across agents and
systems, then brings live runs, durable history, artifacts, schedules, background work,
and human actions back into one keyboard-driven surface.

That observation favors names about **compound vision**, **fan-in**, and **composite
surfaces**. It disfavors generic names about autonomous agents, swarms, or orchestration;
those describe a crowded category rather than the product's most distinctive quality.

My strongest recommendation is **Ommat**. It is five letters, visually rich, unusually
ownable in the developer ecosystem, and derived from the individual visual units that
form a compound eye. **Fanin** is the strongest plain-technical alternative: the current
product already fans work out, while the TUI and durable state fan everything back in.
**Ommata** is the more lyrical, word-like version of the first idea.

The top three deserve real name testing:

1. **Ommat** — best distinctive brand
2. **Fanin** — best immediately legible systems metaphor
3. **Ommata** — best name-like compound-vision variant

Before adopting any finalist, commission a real trademark search and verify domains,
social handles, and distribution namespaces. The checks in this report are a technical
collision screen, not legal clearance.

## What is actually being named?

The current public description says that one prompt fans out to parallel agents in
isolated workspaces; ACE supervises them, AXE schedules work, and durable state tracks
Patches, beads, and artifacts. The TUI then compresses that system into three top-level
views:

- **Agents** makes live and completed execution legible: status, hierarchy, retries,
  chats, prompts, diffs, artifacts, and controls.
- **Artifacts** makes heterogeneous durable state navigable: agents, stitches, Patches,
  beads, provider documents, files, relationships, and history.
- **Axe** makes automation legible: scheduled work, daemon state, chops, and background
  commands.

The cross-tab artifact-link rail makes the idea even clearer. These are not three
independent dashboards; they are three projections of one working system.

There are two established descriptions for this design shape:

- A “single pane of glass” aggregates many data points and sources into an intelligible,
  centralized view. [IBM's definition](https://www.ibm.com/think/topics/single-pane-of-glass)
  is nearly a category-level description of what ACE does.
- A “common operating picture” fuses information from multiple sources into a shared
  reference that supports decisions and action.
  [JESIP's definition](https://www.jesip.org.uk/joint-doctrine/common-operating-picture/)
  emphasizes that it is updated as events and work results change.

The second phrase is particularly useful. `sase` is not just an information display: it
is a place from which the developer launches, steers, reviews, interrupts, resumes, and
lands work. A good name should imply **visibility in service of control**.

## Why renaming is reasonable

`sase` is short, pronounceable, and has accumulated a good internal vocabulary. Its
largest branding weakness is external: in mainstream infrastructure and security,
**SASE already means Secure Access Service Edge**. NIST lists that expansion in its
[official glossary](https://csrc.nist.gov/glossary/term/sase), and vendors such as
[Cisco](https://www.cisco.com/site/us/en/learn/topics/security/what-is-secure-access-service-edge-sase.html)
use the same “sassy” pronunciation. This is not a small package-name collision; it is a
large and growing enterprise technology category.

A replacement should therefore be more than a new acronym. It should be a compact,
searchable brand with a story that belongs to this project.

## Naming criteria

I used the following criteria, in this order:

1. **Semantic reach.** The story must cover the unified UI, parallel work, durable state,
   and human supervision—not only one feature.
2. **Distinctiveness.** A rename is expensive; the result should be easier to own in
   search and developer conversation than `sase`.
3. **CLI usability.** It should be easy to hear, type, and combine with commands such as
   `run`, `ace`, `doctor`, and `patch`.
4. **Length.** Seven characters is the hard preference; five or six is better.
5. **Visual identity.** The metaphor should support an icon, diagram language, or
   memorable launch story.
6. **Low conceptual debt.** Avoid a name that locks the project to today's exact agent
   providers, TUI tab count, or git workflow.

I also avoided names that lean primarily on surveillance (`Panopt`), militarism
(`SitRep`), or generic AI collectives (`Swarm`, `Hive`, `Crew`). They either bring the
wrong emotional tone or disappear into an overcrowded category.

## Candidate families

### 1. Compound vision

A compound eye consists of many visual units—**ommatidia**—arranged together on one
surface. Each unit has its own lens and input; the organism receives one useful field of
view. The [Feynman Lectures](https://www.feynmanlectures.caltech.edu/I_36.html) describe
the many ommatidia packed across the surface of a bee's eye, while a
[Vanderbilt description](https://www.vanderbilt.edu/hillyerlab/Hillyer_Lab_News/Entries/2012/1/4_Image_of_a_mosquito_Compound_Eye_Taken_by_Julian_Hillyer_is_displayed_in_Vanderbilts_Stevenson_Center.html)
explicitly notes that their separate information is decoded and assembled into a visual
image.

That is an unusually exact metaphor for the product:

- many agents, repositories, providers, and durable stores;
- several purpose-specific panes;
- one operator's field of view;
- compact facets that preserve their source identity;
- a natural visual system based on hexagonal facets.

The Greek combining root `ommat-` means “eye”; it appears in _ommatidium_. The Ancient
Greek noun `omma` means eye, and `ommata` is its plural. The Perseus/Scaife lexical entry
shows [`omma` and the plural `ommata`](https://atlas.perseus.tufts.edu/nodes/urn%3Acts%3AgreekLit%3Atlg0012.tlg002.perseus-grc2%3A1.208/).

This yields two strong forms:

- **Ommat** — clipped, technical, five letters, and highly distinctive.
- **Ommata** — a real plural form, six letters, softer and more name-like.

`Ommata` is also the name of a beetle genus. That creates biological search noise, but
not an adjacent software conflict; it also makes the insect/compound-eye association
feel less manufactured. `Ommat` avoids that collision and is shorter, at the cost of
needing its pronunciation and origin explained once.

Possible positioning:

> **Ommat** — Many sources. One field of view.

or:

> **Ommat** — The compound eye for agentic engineering.

### 2. Fan-in

The current README already supplies half of this metaphor: one prompt **fans out** to
parallel agents. In distributed workflows, fan-in is the complementary operation that
waits for parallel branches and aggregates their results. Microsoft's
[fan-out/fan-in documentation](https://learn.microsoft.com/en-us/azure/azure-functions/durable/durable-functions-fan-in-fan-out)
defines the pattern exactly that way. Its agent-orchestration guidance likewise describes
parallel agents whose results are aggregated into a comprehensive result.

The project performs fan-in at more than one level:

- execution results return from parallel agents;
- TUI panes aggregate live state from several subsystems;
- durable artifacts preserve outputs beyond a chat session;
- Patches and stitches turn scattered work into reviewable change;
- the developer makes one decision from the combined picture.

**Fanin** is therefore not just a dashboard name. It can describe the entire second half
of the product's loop.

Possible positioning:

> **Fanin** — Fan out the work. Fan in the picture.

Its disadvantages are brand rather than meaning. “Fan-in” is a generic engineering
term, so searchability and trademark strength will always be weaker than a coined name.
The exact npm name is already occupied by a small package implementing the concurrency
pattern. PyPI and crates.io did not have exact `fanin` projects in the registry snapshot
described below.

### 3. Compact optics

A Fresnel lens replaces a conventional thick lens with concentric sections, retaining a
large aperture and short focal length with much less mass and volume. It is literally a
[compact composite lens](https://en.wikipedia.org/wiki/Fresnel_lens). That gives
**Fresnel** a sophisticated version of the same story: multiple sections, one useful
view, less bulk.

It also provides excellent visual material: concentric rings, a lighthouse beam, focus,
and clarity. The costs are pronunciation (`freh-NELL` is not obvious to everyone), seven
characters, and occupied exact package names in all three registries checked.

### 4. Composite surfaces

An **inlay** is a design made by setting distinct pieces into one surface. The
[Cambridge definition](https://dictionary.cambridge.org/us/dictionary/english/inlay)
maps almost word-for-word to the UI insight, and the name is only five letters.

A **frieze** is a continuous visual band that can contain multiple scenes or panels. It
is a good metaphor for dense, horizontally organized information, though it says less
about agents and control.

This family is semantically strong but commercially crowded. `inlay.sh` is already an
active classroom product, and `inlay.dev` is an active AI/MCP product. “Frieze” is
strongly associated with the established contemporary-art brand, and its exact npm name
is occupied.

### 5. The whole assembled from parts

**Gestalt** communicates an organized whole whose meaning is not reducible to isolated
parts. It spans the UI and the broader agent system well, but it is widely used in
software and all three exact package names checked are occupied.

**Colimit** is the category-theory candidate. A colimit is a universal way of combining
a diagram of objects and their relationships into one object. It is delightfully precise
for an audience that knows the term, but opaque to everyone else. The exact npm name was
open during the snapshot, while PyPI and crates.io were occupied.

**Sheaf** has an even better local-to-global story: compatible local sections glue to a
unique global section, as expressed in the
[Stacks Project definition](https://stacks.math.columbia.edu/tag/006S). Unfortunately,
the name is now an active programming language and is also being used for a unified model
serving layer. It should not be adopted.

## Namespace and collision snapshot

On 2026-08-30 I checked exact, unscoped names through the PyPI JSON API, npm registry,
and crates.io API. “Open” below means the registry returned no exact project at that
moment; it is not a reservation or trademark conclusion. None of the shortlisted words
resolved to an executable already installed on the research machine, but that is only a
local smoke test.

| Name       | Chars | PyPI | npm | crates.io | Main collision concern |
| ---------- | ----: | ---- | --- | --------- | ---------------------- |
| `ommat`    |     5 | Open | Open | Open      | Scientific root; requires explanation |
| `ommata`   |     6 | Open | Open | Open      | Beetle genus and biological search noise |
| `fanin`    |     5 | Open | Taken | Open     | Generic workflow term; small exact npm package |
| `frieze`   |     6 | Open | Taken | Open     | Major contemporary-art brand |
| `fresnel`  |     7 | Taken | Taken | Taken    | Existing optics/rendering packages and projects |
| `colimit`  |     7 | Taken | Open | Taken     | Existing math/software packages |
| `gestalt`  |     7 | Taken | Taken | Taken    | Broad software use |
| `oversee`  |     7 | Taken | Taken | Taken    | Several active software companies/products |
| `inlay`    |     5 | Taken | Taken | Taken    | Active adjacent AI/MCP and classroom products |
| `epitome`  |     7 | Taken | Taken | Open     | Several enterprise/AI products |

Registry endpoints used:

- `https://pypi.org/pypi/<name>/json`
- `https://registry.npmjs.org/<name>`
- `https://crates.io/api/v1/crates/<name>`

I deliberately do not claim any domain is available. A DNS miss is not proof that a
domain is unregistered, and domain/handle availability can change immediately.

## Names that looked excellent but should be avoided

The 2026 agent-tool landscape is extraordinarily crowded. Several names that are nearly
perfect in the abstract are already active products in this project's immediate
neighborhood:

| Name | Why it looked good | Why to avoid it |
| ---- | ------------------ | --------------- |
| **Synopt** | Derived from “seeing together”; almost an exact description | [Synopt](https://synopt.dev/) is an active dashboard for organization-wide Claude Code, Codex, and Cursor usage. |
| **Conspect** | Means a general survey; many inputs into one view | [Conspect](https://conspect.studio/) is an active multiview engine that composites many live sources into one wall. |
| **Heddle** | A loom mechanism that organizes many threads | [Heddle](https://heddle.run/) is an active agent runtime, with several other adjacent Heddle products as well. |
| **Muster** | Assemble a team for inspection and action | [Muster](https://musterup.dev/) is already a cockpit for parallel coding agents; several other agent-control products use the same name. |
| **Cairn** | Many pieces become one navigational landmark | [Cairn](https://cairn.computer/) is already a local control center for multi-agent coding, with several other coding-agent Cairns. |
| **Sinter** | Compact particles into one solid whole | [Sinter](https://sinter.tech/) is already an AI project-context product; other current developer tools use the name too. |
| **Motet** | Independent voices coordinated into one work | [Motet](https://motet.dev/) is an active multi-agent runtime. |
| **Reticle** | One compact viewing and targeting surface | [Reticle](https://www.reticle.sh/) is an active coding-agent verification platform. |
| **Panopt** | “All-seeing,” compact, six letters | Active [display](https://panopt.co/) and [document-analysis](https://www.panopt.dev/) products already use it. |
| **Apercu** | An overview, impression, or compact summary | [Apercu](https://www.getapercu.com/) is an active AI product that turns large text datasets into organized themes and reports. |
| **Sheaf** | Local data glued into a coherent global object | [Sheaf](https://sheaf-lang.org/) is an active programming language, and the name has other current data/AI uses. |
| **Precis** | A compact summary of essentials | Several active AI summarization, meeting, and PR products already use Précis/Precis. |

This list is important evidence in favor of a distinctive coined or root-derived name.
The obvious English metaphors have been rapidly occupied, often by products launched in
2025–2026.

## CLI and identity test

The top candidates survive ordinary command grammar:

```text
ommat run "..."
ommat ace
ommat doctor
ommat patch list

fanin run "..."
fanin ace
fanin doctor
fanin patch list

fresnel run "..."
fresnel ace
fresnel doctor
```

`Ommat` has the cleanest visual identity. A compact hexagonal eye can represent the
whole project, while individual facets can identify Agents, Artifacts, and Axe without
hard-coding the number three into the name. It also leaves room for a future web or
mobile surface.

`Fanin` has the cleanest verbal identity. It makes the product loop easy to explain in
one sentence and pairs naturally with the existing public “fan out” story. Its icon is
less distinctive—converging arrows are common infrastructure imagery—and the unhyphenated
form will sometimes be read as a surname.

`Fresnel` has the most polished conventional-product feel, but the weakest namespace
position of the top three.

The component names ACE and AXE do not have to change in the first naming decision.
`ommat ace` and `fanin ace` both work as transitional command structures. A later pass
can decide whether those subbrands still help once the umbrella name has settled.

## Decision recommendation

Take **Ommat**, **Fanin**, and **Ommata** into a short real-world test rather than widening
the brainstorm further. Put each name on the README masthead, in the install command,
beside the current TUI screenshot, and into five spoken sentences. Ask a few developers
to recall and spell each one a day later.

The decision is then a clean preference between two strategies:

- Choose **Ommat** if the goal is a distinctive, ownable brand with a strong visual
  system and a story that precisely matches the product.
- Choose **Fanin** if immediate comprehension by systems-oriented developers matters
  more than search ownership.
- Choose **Ommata** if the compound-eye idea wins but `Ommat` feels too clipped.

My own choice is **Ommat**. It is the rare candidate that is short, technically grounded,
visually memorable, extensible beyond the current TUI, and not already occupied by a
neighboring agent product.

## Sources

- [SASE project site](https://sase.sh/)
- [ACE TUI guide](https://sase.sh/ace/)
- [IBM: Single pane of glass](https://www.ibm.com/think/topics/single-pane-of-glass)
- [JESIP: Common operating picture](https://www.jesip.org.uk/joint-doctrine/common-operating-picture/)
- [NIST glossary: SASE](https://csrc.nist.gov/glossary/term/sase)
- [Cisco: Secure Access Service Edge](https://www.cisco.com/site/us/en/learn/topics/security/what-is-secure-access-service-edge-sase.html)
- [Microsoft: Fan-out/fan-in pattern](https://learn.microsoft.com/en-us/azure/azure-functions/durable/durable-functions-fan-in-fan-out)
- [Feynman Lectures: Mechanisms of seeing](https://www.feynmanlectures.caltech.edu/I_36.html)
- [Vanderbilt: Compound-eye ommatidia](https://www.vanderbilt.edu/hillyerlab/Hillyer_Lab_News/Entries/2012/1/4_Image_of_a_mosquito_Compound_Eye_Taken_by_Julian_Hillyer_is_displayed_in_Vanderbilts_Stevenson_Center.html)
- [Perseus/Scaife lexical entry for `omma`](https://atlas.perseus.tufts.edu/nodes/urn%3Acts%3AgreekLit%3Atlg0012.tlg002.perseus-grc2%3A1.208/)
- [Cambridge Dictionary: inlay](https://dictionary.cambridge.org/us/dictionary/english/inlay)
- [Stacks Project: sheaves](https://stacks.math.columbia.edu/tag/006S)
- Product collision sources linked directly in the avoidance table

## Final ranked list of names to consider

### 1. Ommat — 5 characters

**Why it ranks first:** It captures the defining UI insight through the compound-eye
metaphor, extends naturally to multi-agent work, has exceptional visual potential, and
was clear in all three package registries checked. It is short enough to be an excellent
CLI and distinctive enough to become the first search result for its own name.

**Cost:** It is a technical combining form rather than a familiar word. The project must
teach “OM-at, from ommatidium” in its first sentence. That is a manageable one-time cost
for a durable brand.

### 2. Fanin — 5 characters

**Why it ranks second:** It is the most exact systems description of what makes the
project different. The product fans work out and fans the operational picture back in.
It is easy for engineers to type, pronounce, and remember, and it produces the best
tagline of the set.

**Cost:** It is generic engineering vocabulary, the npm name is occupied, and it will be
harder to own in search or protect as a mark.

### 3. Ommata — 6 characters

**Why it ranks third:** It preserves the compound-vision concept in a real, plural,
name-like form: “eyes.” It sounds more lyrical and complete than `Ommat`, while retaining
the same iconography and low software-registry collision.

**Cost:** Pronunciation still needs teaching (“OM-mah-tah”), and the beetle genus will
remain a persistent search neighbor. It is also one character longer than `Ommat`.

### 4. Fresnel — 7 characters

**Why it ranks fourth:** A compact composite lens is a beautiful physical analogue for
the product. It communicates reduced bulk without lost perspective, sounds like a mature
tool, and offers memorable lighthouse and lens visuals.

**Cost:** Pronunciation friction and occupied exact package namespaces. It is more about
information compaction than agent coordination.

### 5. Frieze — 6 characters

**Why it ranks fifth:** Multiple scenes arranged into one continuous, dense surface is a
strong TUI metaphor. The word is short, recognizable, and visually suggestive.

**Cost:** It says little about execution or supervision, and the established
[contemporary-art brand](https://www.frieze.com/) owns much of the word's cultural/search
space.

### 6. Gestalt — 7 characters

**Why it ranks sixth:** It cleanly communicates a coherent whole assembled from parts
and scales beyond the current UI. It is familiar enough to need little explanation.

**Cost:** It is heavily used across software, all exact package names checked are
occupied, and it lacks a uniquely operational edge.

### 7. Colimit — 7 characters

**Why it ranks seventh:** For a mathematically inclined audience, it is a precise and
powerful many-to-one metaphor that preserves relationships between the inputs. It is
more distinctive than common words such as `Merge`, `Nexus`, or `Unify`.

**Cost:** Most developers will not know the term, and unlike `Ommat`, it offers little
immediate visual or emotional identity. Two of the three exact package names are taken.

### 8. Oversee — 7 characters

**Why it ranks eighth:** It combines supervision and visibility in one ordinary English
verb. That spans the live Agents view and the human-in-the-loop philosophy well.

**Cost:** It is generic, crowded by active software companies and packages, and misses
the distinctive multi-source compaction idea.

### 9. Inlay — 5 characters

**Why it ranks ninth:** Of all ordinary English words, this is the cleanest image of
different materials fitted into one flush surface. It is short and easy to use.

**Cost:** Exact package names are occupied, [`inlay.sh`](https://www.inlay.sh/) is an
active product, and [`inlay.dev`](https://www.inlay.dev/) is an adjacent AI/MCP product.
It is worth retaining as a conceptual reference but probably not worth the collision
burden of an actual rename.
