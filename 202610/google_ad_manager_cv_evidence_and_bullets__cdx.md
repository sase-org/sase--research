# Google Ad Manager CV improvements: evidence and recommended bullets

Researcher: **cdx**  
Prepared: **2026-10-11**  
Scope: independent research for the main CV in `bbugyi200/CV`; recommendations only. The CV and Bob vault were not modified. No report, transcript, summary, or findings from another researcher in this swarm were consulted.

The main opportunity is to replace the Google entry's generic team/technology description with concrete achievements. The best-supported material is bidder declarations, manual creative-review category targeting, mobile-application service migration, and publisher controls for ad expansion and collapsible formats. Together these demonstrate product delivery, Java backend work, AngularDart development, data modeling, and production migration experience.

## Baseline and research method

The main source is **`BryanBugyi_CV.tex`**, with `BryanBugyi_CV.pdf` as its corresponding output. The files named Google, Batman, Databricks, and LangChain are separate variants. At CV revision `c46ba84eb2b3c39d514ae66c4827590675f14444`, the Google entry lists Software Engineer, June 2022–May 2026, and describes a full-stack Ad Manager team using Java, Dart, AngularDart, and Sass. It has no accomplishment bullets. See [the main CV source](https://github.com/bbugyi200/CV/blob/c46ba84eb2b3c39d514ae66c4827590675f14444/BryanBugyi_CV.tex#L110-L122).

I used read-only `bob query` Dataview searches against the default `~/bob` vault to discover Google-related project, changelist, manager-meeting, and daily-work notes. I then read selected source notes through an audited `sase repo open gh:bobs-org/bob` checkout. The checkout's revision, `e394820f1354d184fba94f08fe6a25d9002bba58`, matched both local and remote revisions in the live vault's successful sync-status record. This gives a reproducible snapshot of the synced vault; it does not establish that every uncommitted or ignored file was examined.

Searches covered Google/GAM/performance filenames, the Google-work reference hierarchy, project and changelist filenames, and selected work-log entries. The relevant notes were mostly converted from older Zorg records. A document's `status: READ` establishes reading activity, not authorship or shipment. Similarly, creating, mailing, testing, and submitting a changelist are different stages. I used explicit completed-work records and rollout notes where available, and avoided treating goals or review links as delivered outcomes.

The configured job research remote was unavailable. The report destination was therefore resolved through `sase repo open -p gh_sase-org__sase -w 10 research`, which opened the canonical `sase-org/sase--research` repository. This report belongs under that repository's `202610/` directory.

## Evidence and candidate wording

All Bob source paths below are relative to `~/bob`. Line references refer to the pinned vault revision above. Links open the user's local vault notes, and the named block IDs provide another way to locate the evidence.

### 1. Bidder declarations and publisher configuration guidance — primary recommendation

**Evidence.** [gbd_cls.md](/home/bryan/bob/gbd_cls.md:13) records DTO conversions, mismatch badges, support for the remaining eight of nine declaration types, tooltips, and declaration-specific table filters (lines 13–71; blocks `z-250429-0o`, `z-250512-0m`, and `z-250523-0c`). It also records shared suggestion logic and links to filtered bidder views (lines 83–145), the settings-suggestions table column (203–206), and privacy-policy data flowing through DAO/domain entities, DTO conversion, and the frontend (218–256). [prj_gbd.md](/home/bryan/bob/prj_gbd.md:171) lists all nine declaration types, including data collection, device identifiers, publisher-provided IDs/signals, and secure signals.

These are personal implementation records, not merely a product description. [fscarpel_meet_2025Q2.md](/home/bryan/bob/fscarpel_meet_2025Q2.md:102) explicitly records submitting the API conversion change. [2025/20250806_done.md](/home/bryan/bob/2025/20250806_done.md:46) records completed submission of the settings-suggestions table change and the privacy-URL DAO change.

The changelist register contains beta and GA launch changes (`cl_gbd_beta`, `cl_gbd_ga_launch`; lines 252–253 and 306–307). [2025/20251029_done.md](/home/bryan/bob/2025/20251029_done.md:55) confirms mailing the GA launch change and submitting the SB-account launch change. I did not locate an explicit completed submission of the GA launch change, so the recommended wording avoids asserting a particular GA date or reach.

**Suggested bullet:** “Implemented bidder data-use declarations and configuration guidance across nine declaration types, including mismatch warnings, filters, and setting suggestions to help publishers align settings with bidder preferences.”

**Attribution limit.** [prj_gbd.md](/home/bryan/bob/prj_gbd.md:121) documents a handoff in which a colleague had already implemented some extraction, API exposure, and UI pieces. Claim the work you implemented and completed; avoid “created the entire bidder-declarations platform.” The functional benefit is supported by the UI behavior. No measured revenue, adoption, or configuration-error reduction was found.

### 2. Category targeting for manual creative review — primary recommendation

**Evidence.** [mcr_cats_cls.md](/home/bryan/bob/mcr_cats_cls.md:13) records schema changes, a new protection domain entity, manager-layer validations, DTO support, restricted-category representation, and Dart model/converter work (lines 13–58). It then records category pickers, protection-detail integration, read-only support, activity tracking, help text, and feature gating (73–134). [prj_mcr_cats.md](/home/bryan/bob/prj_mcr_cats.md:32) attributes the category-targeting design and schema documents to Bryan. The implementation spans general, sensitive, and restricted categories.

The rollout register includes a beta-publisher change and a later change for the remaining 80 publishers (lines 146–160). [2025/20250806_done.md](/home/bryan/bob/2025/20250806_done.md:55) records completed launch communications, selecting a first group of 20 publishers, configuring protections, and coordination with the serving team. Later manager notes still discuss end-to-end testing, so implementation and phased availability should not be equated with a completed worldwide launch.

**Suggested bullet:** “Built category-based manual creative-review controls across database schema, Java APIs, and AngularDart UI, enabling publishers to configure review of general, sensitive, and restricted ad categories.”

**Attribution limit.** The notes support owning substantial API/UI implementation and coordinating with serving and ad-review teams. They do not support claiming ownership of the ad-serving implementation, reductions in review workload, or a final rollout to every publisher. The 20/80 figures describe planned or recorded rollout cohorts, not measured adoption; omit them from the default CV bullet.

### 3. Mobile-application service migration — primary recommendation

**Evidence.** [prj/mas/mas.md](/home/bryan/bob/prj/mas/mas.md:11) identifies the MobileApplicationService migration. [prj/mas/mas_status.md](/home/bryan/bob/prj/mas/mas_status.md:30) describes verifying service methods, mirroring production traffic, diagnosing RPC authorization failures, correcting the relevant access policy, and comparing errors across inventory and creatives shards (lines 30–76). It specifically records writing SQL/PLX queries to retrieve server stack traces.

[fscarpel_meet_2024Q1.md](/home/bryan/bob/fscarpel_meet_2024Q1.md:162) records a submitted change shadowing 100% of read-only traffic. [fscarpel_meet_2024Q2.md](/home/bryan/bob/fscarpel_meet_2024Q2.md:247) records increasing migrated traffic from 10% to 50%. [2024/20240531_done.md](/home/bryan/bob/2024/20240531_done.md:25) records verifying migration traffic and mailing the 100% rollout change. Finally, [fscarpel_meet_2024Q3.md](/home/bryan/bob/fscarpel_meet_2024Q3.md:124) records completed cleanup and the instruction to close the migration project and bug (lines 124–144).

**Suggested bullet:** “Completed a production migration of Google Ad Manager's mobile-application service between backend shards, validating behavior with shadow traffic and SQL log analysis and resolving RPC authorization issues before staged rollout.”

**Attribution limit.** Completion is supported by the final project records. The exact final percentage lacks a directly inspected submission record, so the default bullet uses “completed” with “staged rollout,” without a numerical endpoint. Avoid claiming zero downtime, reduced latency, fewer incidents, or financial impact without additional evidence. This is the strongest systems-oriented bullet and fits the CV's existing Linux/networking positioning.

### 4. Publisher size settings and collapsible-format controls — primary recommendation

**Evidence.** [prj/arms/arms.md](/home/bryan/bob/prj/arms/arms.md:69) describes publisher size-setting controls for mobile-web and desktop/tablet expansion and contraction, targeting, validation, and defaults. [fscarpel_meet_2023Q3.md](/home/bryan/bob/fscarpel_meet_2023Q3.md:103) records schema/service design work and the submitted schema change. [fscarpel_meet_2024Q2.md](/home/bryan/bob/fscarpel_meet_2024Q2.md:83) records all publishers enabled on April 17, 2024, in the open-beta rollout context. The same note records key-value targeting implemented on May 8 (lines 144–146).

[prj/anchor/anchor.md](/home/bryan/bob/prj/anchor/anchor.md:11) describes adding collapsible-anchor and banner controls to size-setting rules, with further open-beta launch records at lines 48–54. [2024/20240531_done.md](/home/bryan/bob/2024/20240531_done.md:21) records submission of the banner detail-page control and table status. [old_cls.md](/home/bryan/bob/old_cls.md:14) records browser tests for creating, editing, and deleting size-setting rules.

**Suggested bullet:** “Developed publisher controls for ad expansion, contraction, and collapsible anchor/banner formats, spanning backend data models, targeted rule configuration, and AngularDart interfaces.”

**Attribution limit.** This describes configuration controls. [prj/anchor/anchor.md](/home/bryan/bob/prj/anchor/anchor.md:31) explicitly distinguishes Bryan's frontend control from the underlying ad format's GA launch. Do not claim to have created the formats or their serving systems. The open-beta launch is established; avoid labeling it GA merely because all publishers could access it.

### 5. API modernization and compatibility work — strong alternative for backend roles

[prj/rap/rap_target_cls.md](/home/bryan/bob/prj/rap/rap_target_cls.md:60) records protobuf, Java, and Dart conversion work across publisher-provided signals, user domains, contextual targeting, data segments, operating systems, video position, request formats, and further technology targeting. It also records fixes to sparse-update and field-presence semantics (lines 260–301). [prj/rap/rap_order_cls.md](/home/bryan/bob/prj/rap/rap_order_cls.md:13) records create/approve operations, a batch-approval action, action handlers, and integration tests. [yserve_cls.md](/home/bryan/bob/yserve_cls.md:28) records partner/group service endpoints, filtering, protobuf/DTO conversions, and service tests.

**Alternative bullet:** “Implemented protobuf schemas and Java/Dart converters for Ad Manager API modernization, preserving targeting and partial-update semantics across legacy models and new service interfaces.”

This is credible implementation evidence. It does not establish that the entire migration launched. A manager note reports cancellation of the earlier Rapunzel initiative ([fscarpel_meet_2024Q4.md](/home/bryan/bob/fscarpel_meet_2024Q4.md:108)), and `prj_yserve.md` currently carries `status: canceled`. Use “implemented” or “contributed,” rather than “migrated all Ad Manager APIs.” Prefer this bullet over format controls when applying to backend/API roles.

### 6. Private-auction diagnostics — useful alternative, with delivery boundaries

[prj_pa_trouble.md](/home/bryan/bob/prj_pa_trouble.md:19) identifies improvements to rejection reasons and competing-deal details. [cls.md](/home/bryan/bob/cls.md:66) records a rejection-reason bucket fix and test run. [2025/20251117_done.md](/home/bryan/bob/2025/20251117_done.md:59) records feature-gating work, bug-bash preparation, and completion of the launch document. [2025/20251124_done.md](/home/bryan/bob/2025/20251124_done.md:50) records mailing beta, SB, and GA launch changes. [2026/20260301_poms.md](/home/bryan/bob/2026/20260301_poms.md:23) logs submission work for the competing-deals component.

**Alternative bullet:** “Improved private-auction troubleshooting with clearer bid-rejection diagnostics and competing-deal details, helping publishers investigate auction outcomes.”

The safest claim is implemented diagnostic improvements. These records do not prove final GA reach or measured troubleshooting-time savings. Line-chart implementation and API debugging continued into April 2026; a January note proposes reducing N RPCs to one, but no completed performance result was established. Do not add a numerical RPC or latency improvement on that basis.

## Other findings and claims to leave out

- **SDK bid health and publisher experiments:** `prj/3bts/3bts.md`, `prj/3bts/3bts_status.md`, and `prj/dcs_pie/dcs_pie.md` document substantive design, log analysis, prototypes, and collaboration. However, [2024_expectations.md](/home/bryan/bob/2024_expectations.md:24) explicitly lists handoffs, and [fscarpel_meet_2024Q3.md](/home/bryan/bob/fscarpel_meet_2024Q3.md:39) confirms both projects were handed off. A defensible optional statement is “Designed SDK bidding diagnostics and publisher-controlled experiments with reporting and product teams.” They are weaker default choices than the four completed implementation themes above.
- **ProtectionService migration:** `protect_cls.md` and `2025/20251030_done.md` document production shadowing and submitted 1% traffic migration. `2026/20260415_poms.md` records mailing a later 50% change. These support staged migration work, but not a completed 100% migration. The completed mobile-application migration is the better default example.
- **Preferred Deals custom creatives:** the project was paused shortly after initial research; manager notes ask about a replacement project. Do not present it as a shipped feature on the inspected evidence.
- **Impression-level revenue sharing:** `ilar_cls.md` documents schema/entity/DTO implementation. Several related launch tasks remain ambiguous in the inspected records. This is a reserve candidate after confirming the specific delivered UI/API scope and rollout.
- **Productivity and business metrics:** the notes contain quarterly changelist counts and output targets, but those are not customer outcomes. No supported revenue lift, latency reduction, scale of traffic handled, user-adoption total, or incident-reduction metric was established. A precise feature or migration claim is stronger than an invented percentage.
- **Earlier review packets:** `eval_docs.md` links Bryan's 2023/2024 reviews and L4 promotion document, but their full contents were not present in the inspected note. They are potential corroboration if available later, not evidence already reviewed here.

## Recommended updates to the main CV

1. **Edit only `BryanBugyi_CV.tex` and rebuild its matching `BryanBugyi_CV.pdf` during implementation.** Keep the Google title and dates unless separately corrected. Replace the present paragraph and three technology URL lines with: “Full-stack engineer on Google Ad Manager, building publisher controls and backend services in Java, Dart/AngularDart, and Sass.” Follow it with an `itemize` block using the existing `\resitem{...}` convention.
2. **Add the bidder-declarations bullet:** “Implemented bidder data-use declarations and configuration guidance across nine declaration types, including mismatch warnings, filters, and setting suggestions to help publishers align settings with bidder preferences.”
3. **Add the creative-review bullet:** “Built category-based manual creative-review controls across database schema, Java APIs, and AngularDart UI, enabling publishers to configure review of general, sensitive, and restricted ad categories.”
4. **Add the service-migration bullet:** “Completed a production migration of Google Ad Manager's mobile-application service between backend shards, validating behavior with shadow traffic and SQL log analysis and resolving RPC authorization issues before staged rollout.”
5. **Add the publisher-controls bullet:** “Developed publisher controls for ad expansion, contraction, and collapsible anchor/banner formats, spanning backend data models, targeted rule configuration, and AngularDart interfaces.”
6. **Tailor with substitutions, keeping four accomplishment bullets as the default.** For backend/API roles, substitute the API-modernization bullet for publisher controls. For product/full-stack roles emphasizing diagnostics, consider the private-auction bullet. If only three bullets fit, retain bidder declarations, creative review, and service migration. Use the evidence limits above when shortening; preserve the distinction between implementing controls, designing a feature, and completing a production rollout.
7. **Quantify only verified results.** Keep the supported nine-declaration scope; add adoption, revenue, reliability, or latency figures only if corroborating records supply a baseline and result. Omit internal project codenames, changelist URLs, publisher names, and proprietary service/framework names from the public CV; retain those details only in supporting research.
