# Release metadata — awaiting owner approval

This page concerns software credit, citation and permission for public reuse.
It is not an installation guide or an additional analysis requirement. Invited
collaborators can use the current private installation; a future public release
still needs the owner's licensing and publication decisions.

The owner confirmed Bei Zhou as the sole current author and code version 0.2.0.
License remains unselected. Po-Wen Chang will be added when the collaborator's
time-dependent code is integrated, not to the current author list.
It is not a license grant, final citation or release announcement.

## Decisions needed

| Decision | Owner to supply |
| --- | --- |
| Software license | Exact license name/SPDX identifier; copyright holder(s) and year/range; confirm permission to release the included code |
| Citation authors | Confirmed: Bei Zhou, sole current author; ORCID and affiliation optional |
| Other contributors | No additional current authors confirmed; add Po-Wen Chang after time-dependent integration |
| Code version | Confirmed: 0.2.0 for current code; 0.1.0 identifies the previous snapshot. No tag/Release authorized |

Current runtime metadata is `0.2.0`; old private-alpha commits/tags are retained.
This does not imply a tagged release or public repository. Do not infer authorship
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
The [release notes](release_notes.md) record the approved code-version mapping;
an actual release publication date is not assigned.

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
version: "0.2.0"
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
   The bundles are now hosted on the existing private-alpha Release and the
   installer pins their asset IDs and hashes. A code push is not a new release/tag.

### Before claiming a complete, publicly installable release

4. Finalize the owner-approved license, contributor/authorship and citation
   metadata and version if still pending.
5. Complete the smallest real DR2 spatial-only and DR1 single/catalog checks
   for the additional advertised paths. Keep workbook support explicitly optional
   with its current limitation; do not build a new installer solely for it.
6. The approved bundles now have pinned GitHub locations and hashes. Record
   installation and both examples from a GitHub clean clone using the default
   command and collaborator authentication. This private installation check
   does not make the repository or its assets anonymously accessible.
7. Refresh the file inventory and notes for the final candidate, record remaining
   scientific warnings, then obtain owner approval before fixing the release
   commit/tag and publishing. Additional runtime changes require proportionate
   verification, not automatic reruns of unrelated owner tests.

### Time-dependent implementation update (20261024)

The owner's earlier deferral is superseded for DR2 time-dependent single-source
analysis and independent catalog scans. These paths use SkyLLH with explicit
Gaussian/box profiles and fixed/fitted temporal parameters; see
[the method and validation scope](time_dependent.md). Time-dependent stacking
still awaits collaborator-provided code. The single-source/catalog integration
does not add collaborator code or change the author list. Time-dependent
scrambling is unapproved; significance calibration and flux/fluence remain
unavailable. No release tag is implied by this synchronization.

No new packaging framework, mandatory workbook integration, general significance
calibration service or PDF regeneration is proposed. Existing scientific
limitations remain explicit; these checks do not establish unbiased parameters
or calibrated significance for arbitrary user catalogs.
