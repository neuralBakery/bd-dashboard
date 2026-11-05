# Inspection, architecture and validation

## Supplied dashboard

The original HTML embeds 27 records as JSON, a hardcoded initial date, a manually assigned priority, and separate browser localStorage keys for findings, weekly checklists and review date. It has useful branch/category/status filters, company cards, source links, a detail drawer, local notes, CSV/JSON exports, JSON merge import and manual search shortcuts.

Its checklist completion date is not a successful research timestamp. It performs no automated collection, rechecking, persistent shared research, event history, source snapshots, automatic prioritisation, failure-aware promotion or scheduling. Its company list has one card per finding rather than a consolidated company profile. Browser state can override stale seed records and is not a reliable unattended data store. The code and original JSON are preserved as source material, without assuming factual correctness or recency.

The implementation reuses the original design CSS and navigation structure with a generated embedded payload, consolidated company groups, independent private notes and new run/coverage views. No external scripts, fonts, APIs or file-origin fetch calls are needed. Search and filters cover company/town/free-text, branch, industry, category, priority, date and verification status. Profiles group exact company names; automatic alias reconciliation is deliberately absent to avoid merging unrelated organisations. Original named contacts are retained in the raw legacy file but not presented as verified people.

## Priority model

Maximum 14 points, explained per record:

| Criterion | Points | Rule |
| --- | --- | --- |
| Workforce demand | 0, 2 or 4 | 4 for explicit jobs/vacancies/recruitment/worker/operator terms in retained excerpts; 2 for expansion category; otherwise 0 |
| Service relevance | 0 or 3 | Industrial/workforce-fit terms in excerpts or known sector |
| Timing | 0 or 2 | Source checked and published within the past 45 days |
| Commercial potential | 0 or 2 | Explicit numerical jobs/workers/positions, seasonal demand, ongoing work or multiple-shift terms |
| Evidence strength | 0–3 | 3 for fresh primary source, 2 for fresh secondary, 1 for checked older/undated/future source, 0 for unverified |

High requires at least 11 points, fresh evidence and workforce demand of at least 2; Medium requires at least 7 and fresh evidence; otherwise Monitor. Closures/restructures, competitor activity, economic context, unknown company identity and unverified sources are capped at Monitor. Unknown dates, future dates and evidence older than 45 days are not current actionable opportunities. Points indicate investigation priority, not workforce quantities, buying intent, qualified pipeline or probability of winning a contract.

Rules are deliberately conservative and lexical. They can miss nuanced developments and must be calibrated against actual public source material. A positive keyword does not independently verify a workforce claim. No financial, contract, job-volume or named-person figures are generated beyond the exact retained source material.

## Pipeline

1. Lock the data store against concurrent refresh/recovery.
2. Read configuration and the last accepted state.
3. Check publisher robots and rate limits; discover bounded article URLs and revisit imported URLs on explicitly configured hosts.
4. Store raw evidence hashes and metadata; reject unsupported access restrictions and unreadable pages.
5. Extract dated source excerpts, identify locations and businesses conservatively, and score relevance separately from facts.
6. Match by canonical source URL plus company; preserve changed versions and user-owned fields.
7. If any source/article fails, quarantine candidates and keep accepted records and the last successful timestamp unchanged.
8. Back up prior JSON, atomically save accepted state plus run report, regenerate the dashboard and briefing.

No retention policy deletes historical backups. Disk use must be monitored on an eventual persistent host. Browser notes are independent of process state and require their own export/restore.

## Executed validation

- 13 Python unit/integration checks passed using temporary test-only datasets: import safety, deduplication, material-change history, notes preservation, URL canonicalisation, invalid/date/freshness handling, risk classification, geographic and signal filtering, new structured employer identity, outside-catchment labels, company-specific excerpt attribution, metadata/script/paywall handling, robots denial, failed/partial-run preservation, successful fixture promotion, backup recovery, invalid recovery rejection and HTML payload escaping. Fixtures are not live findings and never populate the shipped dataset.
- A real live refresh was attempted on all seven configured sources. All were denied with proxy `403 Forbidden`; run exited 2, preserved all 27 legacy records, generated failure status and created a pre-run backup. This is evidence of failure handling, **not live research success**.
- Chromium browser smoke check passed over a temporary loopback server: navigation, filtering, private notes persistence across reload, JSON backup download containing notes, empty date-filter outcome, weekly briefing, failure reporting, manual-refresh help, mobile viewport, no external browser requests and no JavaScript errors.
- Managed browser policy blocks `file://` navigation with `ERR_BLOCKED_BY_ADMINISTRATOR`. Direct-file compatibility is designed into the generated file but was not empirically verified in this environment. Firefox and Safari were not tested.
- Melbourne-aware timer expression parses; summer/winter UTC conversion checked. Actual service execution, persistence across reboot, unattended operation and external notifications remain untested and unconfigured.

## Remaining acceptance work

Apply the saved source-domain access changes, then verify actual source URLs, licensing/robots behavior and article discovery. Run a successful collection that adds or amends genuine source-checked findings and repeat it to validate live duplicate behavior. Expand adapters for recruitment, procurement and competitor coverage only after accessible sources are verified. Calibrate organisation identity, attribution and scoring against the resulting evidence, with corroboration for significant findings. Confirm opening the downloaded file in the user's regular browser.

Select an always-on private execution host and a persistent dashboard delivery path before installing any schedule. Test a scheduled run, reboot recovery, failure status and an authorized notification mechanism. Until these checks pass, this is an implemented and locally tested foundation, **not the requested fully unattended operational research service**.

## Repair after the first GitHub run

The original collector failed to parse RSS with whitespace before an XML declaration, searched script text for generic captcha references, and included navigation text in candidate excerpts. These are corrected. Visible access-challenge screens, denied robots policies and paywalls still stop collection. Article lists inside main content are retained; header/navigation and trailing page content are excluded. DCTERMS.issued publication metadata is supported. Company excerpts are selected from that company's paragraphs, and geographic relevance must be supported by the retained excerpts or headline.

Incomplete runs continue to preserve `records` and `lastSuccessfulRun`. Independently completed sources now populate a separate `partialRecords` collection, which is overlaid in the dashboard with explicit partial-coverage labels. The previous accepted dataset remains recoverable and unchanged. A full successful run promotes records normally. Backup exports retain the authoritative accepted/partial distinction. Overall incomplete runs still return exit 2 and report coverage failures rather than pretending the full research cycle succeeded.

A live cloud collection completed five sources and failed two. After reprocessing the original source snapshots with the corrected scope and metadata rules, 14 partial findings are displayed, including source-checked investment announcements for Bentrol, Hazeldenes, Grape Co Australia and GV Link. This is useful partial coverage, not complete regional intelligence. Shepparton Council returned a robots 503, and Mildura's current news listing did not provide discoverable article links. GitHub's datacentre can encounter different source restrictions from this cloud environment.

22 automated tests pass. Chromium UI checks also passed after partial findings were introduced. The published system remains a downloaded dashboard workflow; old downloaded copies never update themselves.
