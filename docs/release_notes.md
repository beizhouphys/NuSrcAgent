# NuSrcAgent 0.2.0 — development snapshot notes

This version provides time-integrated searches at specified source positions,
independent fits across a source catalog, and a joint stacking fit. See the
[README](../README.md) for installation and the [worked examples](quickstart.md)
for commands and result interpretation. "Snapshot" here means a recorded
development version, not a publication-ready scientific result.

Code version: 0.2.0, approved by the owner. No tag or GitHub Release is created.

Version mapping:

- `0.1.0`: the previous snapshot, commit `58dc2f582bf3037513974e91b5772c3018cc190a`.
- `0.2.0`: the current time-integrated code, based on the reviewed upload
  `1cd3d0ee9d97ec86ba924361f640f41645c9e8c9`, with this version metadata update.

This records the owner's snapshot names without rewriting old commits or
renaming existing private-alpha tags. Repository visibility is independent of
these version numbers.

- DR2 time-integrated point-source single fits, individual catalog scans and
  stacking; spatial+energy fits ns/Gamma, spatial-only uses fixed acceptance Gamma.
- Existing DR1 spatial-only capabilities retained with separate inputs.
- Python 3.12 hash-locked environment and one-command bootstrap for the prepared
  raw-data, frozen v3 background and SEpdf bundles. All seven bundles are hosted
  on the existing private-alpha Release, with pinned asset IDs and hashes;
  installation reuses collaborators' GitHub credentials. No new tag/Release.
- Persistent tasks, configuration/input/code provenance and scientific reviews;
  two documented examples reproduced from an independent local Git clone.
- Ubuntu/Python 3.12 no-data CI passed. A fresh GitHub clone completed plain
  `bash install.sh` using hosted inputs and reproduced both real DR2 examples;
  configuration/provenance/reviews passed, with the documented warnings retained.
- Owner tests, private catalogs/transcripts, PDF construction and dedicated
  source/catalog comparison code excluded from the public copy.

Documentation updated on 2026-10-17 explains installation, analysis choices,
result files and scientific limitations for astrophysicists and particle
physicists without assuming AI/software expertise. This is a documentation-only
change: likelihood definitions, commands, fit settings and numerical inputs
are unchanged.

This draft covers implemented time-integrated behavior, not the complete approved
first-release scope. Time-dependent work is deferred by the owner until
collaborator code is integrated; it does not block the current source-code
synchronization and must not be advertised as supported in this copy.
Ordinary fits execute no background trials; analytic local p-values are not
empirical or catalog-global significance. Frozen v3 residuals and possible
ns/Gamma/flux bias remain. Warning-bearing results are preliminary.

See [scientific status](scientific_status.md),
[release checks](testing_and_release.md) and
[metadata awaiting approval](release_metadata_draft.md).

## Requested spectra — 2026-10-22

Conventional PLs retain the existing frozen SEpdfs. A PL outside interpolation
coverage, an explicitly selected fitted exponent range, or a fixed tabulated
non-PL spectrum now prepares the matching signal-energy PDFs and detector
acceptance before interpolation and fitting. The Agent announces preparation
and reports a current measured pilot ETA. Single-source analyses, catalog scans
and stacking use the same interface; spatial-only computes acceptance without
energy PDFs. See [requested spectra](requested_spectra.md) for spectrum columns,
units, support conventions, provenance and current fixed-shape scope.

## General background trials — 2026-10-23

Use `dr2-empirical-scramble --action prepare --baseline-task <id_or_path>` after
a reviewed DR2 single-source or stacking analysis. Trials inherit its scientific
settings and import its primary result. The workflow retains checkpointed
running/stopping/resumption and exports probability, significance, Monte Carlo
intervals and PNG/PDF figures. Random-catalog generation is no longer a runtime
operation. See [background trials](dr2_empirical_scrambling.md) for scope and commands.
