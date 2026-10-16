# Frozen DR2 production background v3

Only the approved v3 numerical package is distributed. It is the byte-identical
release alias of frozen v3-RC1; neither v1/v2 nor diagnostic candidates are
included. Numerical artifact bytes and the original frozen RC1 manifest remain unchanged.

The release copy relocates the eight production model/table files to
`data_output/bkgd_pdfs/14yr_dr2_v3/`. Original and release paths and their
identical numerical SHA-256 values are in `pdf_release_manifest.json`.
The original frozen manifest identity is
`65ef8d7b84ae634f6ee58f046d7ccfac62a54616d2be7d14219de9fa2f88c6e3`.
The derived mapping manifest has its own pinned hash; it does not claim to be
byte-identical to the private historical manifest.

Loading requires the exact expected artifact set and hashes. There is no
fallback or automatic PDF rebuild. The release provenance retains the original
frozen parent identity and scientific limitations using release-relative paths.

BSpdf and pooled IC86 PDFs preserve the frozen definitions. IC40/59/79 BEpdf
uses the approved correction; IC79 residuals persist. These artifacts do not
alone validate significance, parameter coverage or sensitivity. DR1 inputs
remain a separate package.

The owner confirmed v3 as the formal PDF version on 2026-10-15; a subsequent
PDF-definition revision will be v4. The development checkout now also stores
these files in its formal `data_output/bkgd_pdfs_cdx/14yr_dr2_v3_cdx/` directory.
Release model/table paths and numerical hashes did not change during that move.
