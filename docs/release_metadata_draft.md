# Release metadata — awaiting owner approval

The owner confirmed Bei Zhou as the sole current author. License and public
version remain unselected. Po-Wen Chang will be added when the collaborator's
time-dependent code is integrated, not to the current author list.
It is not a license grant, final citation or release announcement.

## Decisions needed

| Decision | Owner to supply |
| --- | --- |
| Software license | Exact license name/SPDX identifier; copyright holder(s) and year/range; confirm permission to release the included code |
| Citation authors | Confirmed: Bei Zhou, sole current author; ORCID and affiliation optional |
| Other contributors | No additional current authors confirmed; add Po-Wen Chang after time-dependent integration |
| Release version | Exact version and whether it is a prerelease; any tag spelling preference |

Existing runtime metadata says `0.2.0-private-alpha.4`; this is the current
development identifier, not an approved public version. Do not infer authorship
from the GitHub account, commit authors, source ownership shorthand or future
collaborator code that has not been merged. Publication date means the actual
publication date, not the date of a local verification run.

## Files to finalize after approval

- `LICENSE`: the approved license text with confirmed copyright details.
  Check any applicable third-party notices for included code; dependency/data
  attribution is separate from licensing NuSrcAgent itself.
- `CONTRIBUTORS.md`: approved citation authors and any separately acknowledged
  contributors/roles. Do not invent affiliations, authorship or contribution claims.
- `CITATION.cff`: approved software citation; no invented DOI or paper citation.
- `AGENT_VERSION.txt`, `agent_core/task_state.py` and the release notes: use the
  same owner-approved version. No tag is created as part of local preparation.

The existing [data attribution](data_attribution.md) is retained independently.
The [release notes](release_notes.md) are already drafted without a version/date.

## CITATION.cff template — not final metadata

Based on the [official Citation File Format example](https://citation-file-format.github.io/).
Replace placeholders and repeat the author entry as approved. Optional ORCID,
affiliation, DOI or preferred-paper fields should be omitted unless supplied and
verified. Validate the completed CFF once, after approval; no new runtime dependency
or citation automation is needed.

```yaml
cff-version: 1.2.0
message: "If you use NuSrcAgent, please cite this software."
type: software
title: NuSrcAgent
authors:
  - family-names: "Zhou"
    given-names: "Bei"
repository-code: "https://github.com/beizhouphys/NuSrcAgent"
version: "<approved release version>"
date-released: "<actual publication date, YYYY-MM-DD>"
license: "<approved SPDX identifier, if applicable>"
```

## Remaining work, in order

### Current code synchronization for collaborators

1. Confirm the metadata choices above to finalize their small files. For a
   source-code preview, unapproved metadata can remain explicitly pending;
   do not present that preview as an approved open-source or complete first release.
2. Inspect the current remote branch/history and the exact upload diff for private
   data, credentials, transcripts, excluded code and large generated files. An
   allowlisted working tree does not prove the existing remote history is clean.
   Preserve ordinary remote history if clean; do not force-push or rewrite it
   without a separate, explicit decision.
3. Commit/sync only the reviewed release files after owner authorization.
   Run the configured Ubuntu/Python 3.12 CI on GitHub and address actual failures.
   Until bundles are published, README must continue to identify the local-bundle
   route and the pending public endpoint. A code push is not a release/tag.

### Before claiming a complete, publicly installable release

4. Finalize the owner-approved license, contributor/authorship and citation
   metadata and version if still pending.
5. Complete the smallest real DR2 spatial-only and DR1 single/catalog checks
   for the additional advertised paths. Keep workbook support explicitly optional
   with its current limitation; do not build a new installer solely for it.
6. Publish the approved input bundles at fixed HTTPS URLs, update the bundled
   download location and its pinned manifest hash, and repeat installation plus
   both examples from the final GitHub candidate using only public instructions.
   Local snapshots/local bundles do not close this public-download gate.
7. Refresh the file inventory and notes for the final candidate, record remaining
   scientific warnings, then obtain owner approval before fixing the release
   commit/tag and publishing. Additional runtime changes require proportionate
   verification, not automatic reruns of unrelated owner tests.

### Deferred by owner: time-dependent analysis

On 2026-10-16 the owner explicitly deferred this work. Do not implement or
block the current code synchronization on time-dependent analysis. The owner
will integrate collaborator code first; synchronize it and verify the affected
paths afterward when authorized. The original full first-release target still
includes time-dependent capabilities, but they remain unimplemented in this
copy and must not be advertised as supported or validated. This deferral does
not authorize a push or release tag.

No new packaging framework, mandatory workbook integration, general significance
calibration service or PDF regeneration is proposed. Existing scientific
limitations remain explicit; these checks do not establish unbiased parameters
or calibrated significance for arbitrary user catalogs.
