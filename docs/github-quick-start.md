# Using the dashboard with GitHub

The automation is prepared in `.github/workflows/weekly-intelligence.yml`. It only becomes active after the files are uploaded to the repository's default branch and GitHub Actions is allowed. No public website is created.

## Prepared files — not yet installed

At your instruction, the repository remains public and no files have been uploaded. The download package contains the entire application, not just the automation file. Unzip it locally. GitHub does not extract uploaded ZIP files into a working application.

When you decide to install it, open the repository's **Code** tab, choose **Add file → Upload files**, and upload the extracted application files and folders at the repository root (not inside an extra enclosing folder). Ensure `.github/workflows/weekly-intelligence.yml` is included; some computers hide folders beginning with a dot. Uploading to `main` activates the schedule if Actions is enabled. Before uploading, remove any confidential research or private note exports. Do not upload `.git`, credentials, or the ZIP itself as a substitute for the extracted files.

If you prefer assistance with that upload, ask in this chat; the current instruction is to prepare only.

## Get an updated dashboard

1. Open https://github.com/neuralBakery/bd-dashboard/actions .
2. Click **Refresh regional dashboard** on the left.
3. Click the latest run. For a manual update, click **Run workflow**, keep **main** selected, then click the green **Run workflow** button.
4. Wait for it to finish. Allow up to 30 minutes.
5. Open the run and scroll to **Artifacts**. Click **regional-dashboard** to download the ZIP.
6. Unzip it and open **dashboard.html**. Replace your older downloaded copy when you want the latest results.

A red cross means a run failed or coverage was incomplete. The download still contains the last accepted findings and the updated failure notice when the report step succeeds. Never interpret a failed search as no market activity. Review the source errors in the run summary.

## Automatic weekly update

The two Sunday UTC schedules select the slot corresponding to **Monday 7 am Australia/Melbourne**, with daylight saving handled automatically. GitHub may delay scheduled runs, so this is a target time, not a guaranteed delivery deadline. Your computer can be switched off: GitHub runs the job on its own servers.

Accepted research, backups and evidence are committed to the repository; each runner starts from the current repository version. This provides persistence across runs without a hosted database. The same dashboard location on GitHub is updated, but previously downloaded files do not change automatically.

The workflow uses the repository's built-in `GITHUB_TOKEN`; no API key or paid research service is needed. GitHub Actions runner time and artifact storage are subject to your account's included allowance. Do not enable paid overages merely for this workflow. Branch protection or organisation policies may block workflow commits: if so, the run will fail and the policy needs review rather than bypassing it.

## Failure notifications

In your GitHub account, open **Settings → Notifications → System → Actions** and enable email notifications for failed workflows (labels may vary). Verify the email address on your GitHub account. No notification settings have been changed automatically and delivery must be tested with an actual run.

## Private notes

Private notes remain in your browser. Use **Export backup + notes** before replacing or moving the dashboard. Restore them with **Restore notes** in the new copy. Do not upload notes exports to GitHub. Keep this repository private before uploading commercial research, and do not enable GitHub Pages without a separate privacy decision.

## If the workflow is missing

The files may not have been uploaded yet, or Actions may be disabled under **Settings → Actions → General**. A linked GitHub account by itself does not upload this workspace or activate a schedule.
