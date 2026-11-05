# Regional Victoria workforce intelligence

A private, dependency-free Python 3.11+ research pipeline and self-contained HTML dashboard for the Bendigo, Shepparton and Mildura catchments. Adapted from the supplied BD Researcher Dashboard v2.

**Current status: implementation tested locally; live research and unattended operation are blocked.** The first real refresh encountered HTTP proxy policy denials for every configured source. No new live findings have been verified. All 27 supplied findings are retained as unverified historical research, with original values preserved. Do not use them as fresh or confirmed opportunities.

Open `dashboard.html` in a regular browser. It embeds its data, CSS and JavaScript; no web server, browser fetch requests or cloud database is required. Managed Chromium in this environment blocks `file://` by policy; UI behavior was tested through an ephemeral local HTTP server. Opening directly from disk on the user's browser remains to be verified.

```sh
cd /workspace/bd-dashboard
python3 -m bdintel init       # idempotent import, never overwrites existing state
python3 -m bdintel refresh    # manual research; exit 0 success, 2 incomplete/failed
python3 -m bdintel build      # regenerate HTML from accepted state without researching
python3 -m bdintel status
python3 -m unittest discover -s tests -v
```

Refresh always updates this checkout's `dashboard.html` and `data/weekly-brief.txt`. Reload the browser after running it. A downloaded or copied dashboard is a separate snapshot and does not receive future updates. The dashboard's manual refresh button explains the command; browser security prevents an HTML file from starting local programs.

No pip/npm install, credentials, paid APIs, Microsoft 365 integration, hosted database or public deployment is required. The browser smoke test optionally uses environment-provided Playwright and Chromium: `python3 -m tests.browser_smoke`.

## Data, evidence and privacy

- `data/legacy.json`: unchanged original 27 research records extracted from the supplied HTML.
- `data/state.json`: authoritative records, full material-change history and research run status.
- `data/evidence/`: original retrieved public-source bodies, named by SHA256 hash, with quote references in records.
- `data/runs/`: per-run source coverage and safe error reports.
- `data/staging/`: candidates withheld after incomplete collection; never shown as accepted new intelligence.
- `data/backups/`: pre-run state snapshots and pre-recovery snapshots. Backups are deliberately not automatically deleted.
- `dashboard.html`: generated self-contained browser view. Rebuilding does not change browser notes.
- `assets/dashboard-template.html`: original supplied dashboard, retained for traceability and reused design styles.

Private notes and research statuses are separate browser storage under `psw_bd_private_notes_v2`. Export **Backup + notes** regularly. Backend backups cannot see unexported browser notes. Moving the HTML file or switching browsers can change its storage location. **Restore notes** accepts the new export and the old dashboard's `psw-regional-bd-v1` backup. If old notes are visible in the same browser storage, the app migrates only notes/status, never stale source records. No private notes are sent to research sources.

Recover the research dataset with `python3 -m bdintel recover /path/to/backup.json`; this validates the backup and saves the current state before replacement. A browser backup includes research state and notes: recover the research via CLI and restore notes via the dashboard. Keep a private copy of exported backups outside this machine. Do not commit confidential notes or backup exports to a remote repository.

## Collection and accuracy

Configure indicative territories, additional outside-catchment towns, public sources, request interval and article limits in `config/sources.json`. These are research catchments, not verified Programmed branch territories. Outside-catchment matches are labelled separately. Match locations explicitly; avoid adding ambiguous place names without refining source coverage.

Collection uses robots checks, TLS validation, a descriptive user agent, per-host pacing, timeouts, bounded response sizes and same-host HTTPS redirects. It stops on denied robots access, paywall flags and detected access protection. No paywall, captcha or anti-bot bypass is implemented. Review publisher licensing conditions before enabling a new source; robots permission alone is not a licence.

The pipeline discovers bounded same-site article links from configured pages/RSS feeds and revisits imported sources on those configured hosts. It reads publication metadata and keeps exact source excerpts, rather than generating unsupported factual summaries. A source check establishes that a publisher said something, not that a claim is independently corroborated. Publication dates are never substituted with discovery dates. Undated, future-dated, stale or legacy records cannot receive actionable priority.

Known company names are matched literally. New named companies can be taken from explicit employer/about-organisation structured metadata when supported by the article text. Otherwise the finding is labelled **Organisation unverified** and held at Monitor. Named people, email addresses, supplier relationships and external provider demand are never inferred. Distinct article URLs remain distinct events; changed content at the same URL and company creates a preserved prior version. Canonical URLs remove tracking parameters while retaining meaningful query parameters.

Every configured source must complete, including article checks, before candidate records are promoted. Otherwise the accepted record set and last-successful timestamp are preserved; source failures and staged candidates remain available for diagnosis. Atomic state writes and a process lock prevent overlapping runs from corrupting JSON. HTML is derived from state and can be regenerated after interruption.

This is conservative source monitoring, not an unrestricted web-search or language-model research agent. Current adapters have **not been validated against accessible live pages**. Selectors, page paths, dynamic recruitment/tender portals, broad discovery of new companies, significant-finding corroboration and employer identity extraction require live validation before relying on the system operationally. Economic, risk and competitor records are separated from actionable opportunities. See [architecture and validation](docs/implementation.md).

## Schedule and access needed

See [scheduling](docs/scheduling.md). A Melbourne-aware systemd timer is supplied, but **not installed or running** in this task instance. There is no Codex scheduling tool exposed in this session and no active systemd/cron service in the machine. Publishing an environment snapshot does not schedule it or keep a process running.

The source-domain allowlist additions and reusable install/start instructions were saved to the environment draft. Review and save them in environment settings, then publish the environment. Retry `python3 -m bdintel refresh` once access is applied. A successful live research cycle that adds genuine checked findings, followed by a repeat run, is still required before declaring this system operational.

## GitHub automation prepared (not activated)

A weekly GitHub Actions workflow and a manual **Run workflow** button are prepared in `.github/workflows/weekly-intelligence.yml`. The repository was confirmed public, and the user requested **prepare files only**. No files have been pushed, no repository settings changed, and no workflow enabled or run on GitHub.

See [the plain-language GitHub instructions](docs/github-quick-start.md). Once uploaded to `main`, the two UTC schedule slots target Monday 07:00 Melbourne time with daylight-saving selection. GitHub can delay execution. A workflow stores research history in the repository and provides a downloadable dashboard artifact; downloaded copies do not update themselves. Live execution on GitHub and notification delivery remain untested. Keep private notes and confidential commercial information out of this public repository.

The 16 local tests pass, including workflow script parsing and summer/winter plus daylight-saving transition checks. These checks do not establish that a GitHub-hosted runner can collect all configured sources.
