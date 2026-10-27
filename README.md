# wcif-snapshotter

A small Python CLI that periodically fetches the **private** WCIF of a WCA
competition you manage, stores each version in a local git repository, and lets
you browse or roll back to any previous snapshot.

## How it works

- Logs in with your WCA account via OAuth2 (authorization-code flow).
- Fetches `GET /api/v0/competitions/:id/wcif` using a Bearer token.
- Commits each changed snapshot to `~/.wcif-snapshotter/repos/<id>/` as `wcif.json`.

## Setup

1. Create a WCA OAuth application at
   <https://www.worldcubeassociation.org/oauth/applications/new>.
   Set the redirect URI to `http://127.0.0.1:8080/callback` and the scopes to
   `public manage_competitions`.

2. Install the tool:

   ```bash
   pip install -e .
   ```

3. Configure your credentials:

   ```bash
   wcif-snapshotter configure
   ```

   (Alternatively set `WCIF_CLIENT_ID` / `WCIF_CLIENT_SECRET` env vars.)

4. Log in with WCA (opens your browser):

   ```bash
   wcif-snapshotter login
   ```

## Usage

```bash
# One-off snapshot
wcif-snapshotter snapshot MyComp2026

# Snapshot repeatedly (stops on Ctrl-C)
wcif-snapshotter watch MyComp2026 --interval 60

# List snapshots
wcif-snapshotter history MyComp2026

# Show a previous version
wcif-snapshotter show MyComp2026 --at HEAD~2

# Diff two versions
wcif-snapshotter diff MyComp2026 HEAD~2 HEAD

# Restore a previous version to a file
wcif-snapshotter restore MyComp2026 HEAD~2 --out mycomp.json

# PATCH a previous version back to the WCA server
wcif-snapshotter restore MyComp2026 HEAD~2 --patch --yes
```

## Notes

- `restore --patch` sends the **full** snapshot document to
  `PATCH /api/v0/competitions/:id/wcif` (it is not a JSON merge patch). You must be a
  manager of the competition, and once results are submitted only admins may PATCH.
- The `--yes` flag skips the confirmation prompt before the server write.

- The private WCIF endpoint requires you to be a **manager** (organizer/delegate/trainee)
  of the competition. Otherwise use `--public`, which returns the public WCIF with
  confidential fields stripped.
- Secrets and tokens are stored in plain text in `~/.wcif-snapshotter/config.json`.
  Keep that file private.
- `watch` runs only while the process is alive (until you press Ctrl-C); it does not
  daemonize. For scheduled snapshots, point Task Scheduler / cron at
  `wcif-snapshotter snapshot <id>`.
- `restore` requires exactly one of `--out` (write locally) or `--patch`
  (write to the server).
