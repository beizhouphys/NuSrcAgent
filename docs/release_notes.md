# NuSrcAgent — draft release notes

Version and publication date: awaiting owner approval. Not a published release.

- DR2 time-integrated point-source single fits, individual catalog scans and
  stacking; spatial+energy fits ns/Gamma, spatial-only uses fixed acceptance Gamma.
- Existing DR1 spatial-only capabilities retained with separate inputs.
- Python 3.12 hash-locked environment and one-command bootstrap for the prepared
  raw-data, frozen v3 background and SEpdf bundles. Local installation verified;
  the public download endpoint is not published yet.
- Persistent tasks, configuration/input/code provenance and scientific reviews;
  two documented examples reproduced from an independent local Git clone.
- No-data CI configured; the GitHub Ubuntu run remains pending.
- Owner tests, private catalogs/transcripts, PDF construction and dedicated
  source/catalog comparison code excluded from the public copy.

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
