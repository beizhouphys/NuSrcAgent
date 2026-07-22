# Private-Alpha Collaboration Guide

## Access

The GitHub repository is private. Add collaborators by GitHub username, not by sharing account passwords. Each collaborator should authenticate with their own GitHub account.

## First run

1. Clone `NuSrcAgent`.
2. Create the environment from `environment_private_alpha_cdx.yml`.
3. Run `python3 verify_private_alpha_setup_cdx.py --hashes`; the required data are included in the clone.
4. Run the unit tests.
5. Open the repository in Codex and invoke `$he-neutrino-analysis-cdx`, or use `run_agent_wrap_cdx.py` directly.

## Development workflow

- Keep `main` usable; develop changes on a short-lived branch.
- Use pull requests for changes to agent behavior or LLH behavior.
- Do not add data beyond the manifest-approved tracked subset. Never commit generated run outputs, figures, credentials, or local caches.
- Record scientific parameter changes explicitly in the pull request.
- Add or update tests when changing planner, confirmation, recovery, or completion behavior.
- Tag stable collaborator snapshots; do not rewrite published tag history.

## Reporting problems

Include the task ID, terminal state, `agent_review_cdx.json`, and the relevant run `review_cdx.json`. Do not attach the full private event sample to an issue.

## Current boundary

This private alpha tests collaboration and usability. It does not authorize public redistribution, hosted analysis access, or publication-ready scientific claims.

Several legacy scientific scripts still contain disabled or historical absolute paths. The callable agent backend uses repository-relative paths, but collaborators should treat the legacy scripts as research history until those paths are refactored during the LLH workstream.
