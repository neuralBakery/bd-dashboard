# Weekly execution: Monday, 07:00 Australia/Melbourne

**No active schedule has been configured.** This managed task is not an always-on host: PID 1 is `tail`, systemd is not running, and `crontab` is not installed. No Codex automation/scheduling API is available in the session's tool catalog. The presence of a clock tool is not a scheduling capability.

The supplied `config/regional-bd.timer` uses:

```
OnCalendar=Mon *-*-* 07:00:00 Australia/Melbourne
Persistent=true
```

The expression was parsed successfully with `systemd-analyze calendar`. Timezone checks confirm 07:00 on 9 November 2026 is 20:00 UTC on the previous day; 07:00 on 7 June 2027 is 21:00 UTC on the previous day. Melbourne daylight-saving changes must not be implemented as one fixed UTC cron expression. `Persistent=true` catches up a missed timer when the host starts, rather than claiming the research ran while it was off.

## Options

| Execution location | Runs with your computer off? | Same dashboard and storage | Cost / limitations |
| --- | --- | --- | --- |
| Your Linux computer with systemd user timer | No; catches up after restart | Yes, if service points at the original private checkout | No hosting charge; requires machine and user service availability |
| Existing always-on private Linux server | Yes, while that server is on | Yes on that server; your local downloaded copy does not update itself | Existing infrastructure may have no incremental charge; private file access or transfer needs configuration |
| New private VPS / hosted runner with durable disk | Yes | Only if explicitly configured with durable storage and private delivery | Paid hosting and a security/account decision; not provisioned |
| Codex task / restored environment snapshot | Not established | Snapshot restoration does not establish shared writable persistent storage across runs | No scheduler tool or durability guarantee available in this session |
| GitHub Actions | Potentially, but not configured | Requires a private durable storage/delivery design; an ephemeral checkout alone loses updates | External workflow and access decisions; runtime quotas/costs depend on account |

Do not treat publishing the environment, saving a script, or starting a detached process as a verified weekly scheduler.

## Installing on a chosen persistent Linux host

First complete a successful live research run and a duplicate-safe repeat run on that host. Copy the checkout to a private durable location. Adjust both paths in `config/regional-bd.service` to that location, and ensure `python3` is 3.11+ with timezone data. Preserve any required proxy and CA bindings in the service environment without copying secret values into the service file.

Then install as the intended non-root user:

```sh
mkdir -p ~/.config/systemd/user
cp config/regional-bd.service config/regional-bd.timer ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now regional-bd.timer
systemctl --user list-timers regional-bd.timer
systemctl --user start regional-bd.service
journalctl --user -u regional-bd.service -n 100
```

These installation commands have **not been executed or validated** here. A user service usually requires a logged-in user or administrator-enabled lingering to run unattended. Confirm the host's behavior after logout and reboot; do not assume it.

## Results and notifications

A run updates `dashboard.html` in that persistent checkout, including its success/failure status, and writes JSON reports plus a text briefing. Open that same file and reload it to see the result. Keeping the same pathname on unrelated machines does not synchronize the file or browser notes.

Current notification is **in-dashboard status and local run logs only**. No email, Slack, or other outbound notification is configured, and none has been sent. A host-side systemd service reports a nonzero exit on incomplete collection; external alert delivery requires selecting and testing an authorized notification channel.
