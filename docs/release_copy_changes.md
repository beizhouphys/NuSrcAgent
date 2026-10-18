# Development → release-copy adaptations

This page is for collaborators comparing the developer's working directory
with the code distributed on GitHub. The distributed copy contains the files
needed to run supported analyses, not the private tests and historical studies.
Renaming code/paths must not change the likelihood or the numerical PDF tables.
For normal use, start with the [README](../README.md); no manual migration is needed.

The development checkout remains authoritative for implementation work.
The release copy changes filenames, imports, identifier suffixes and generated
artifact references consistently. It removes generation-only comment markers,
retains substantive explanations, and introduces no old-name import adapters.

| Development content | Release-copy content |
| --- | --- |
| Marker-suffixed runtime directories/modules | `agent_core/`, `analysis_backend/`, neutral module names |
| Marker-suffixed public wrapper | `run_agent_wrap.py` |
| Mixed general scan and 3386-source benchmark | General input-ordered scan only |
| DR1 original analysis plus controlled all-sky comparison | Original supported DR1 path only |
| PDF construction/validation tools and rebuild CLI | Excluded; frozen loading/interpolation retained |
| Background v1/v2/v3 selection | Production v3 only; unavailable versions rejected |
| Development production PDF paths with owner markers | Formal release v3 paths with unchanged numerical hashes |
| Selected radio-bright AGN CSVs in `data_input/sources_cdx/` | Versioned under `data_input/sources/`, unchanged numerical bytes |
| Local tests/transcripts/catalog experiments | Excluded |
| Historical research directories and old Python 3.8 environment | Excluded |
| Owner-specific documentation and broken test-report links | Adapted public definitions and explicit limitations |

Numerical PDFs are copied unchanged and excluded from Git. Small release
provenance and path/hash manifests remain source-controlled. Original frozen
manifests are not rewritten; their original SHA-256 identities are retained.
Signal tables are checked against the mapped hashes before interpolation.

Generic dominance, fixed-Gamma RA smoke tests and empirical orchestration are
retained with their existing scientific scope. No background trials are started
by source preparation. The original time-integrated fit formulas and optimizer
bounds are preserved. All substantive adaptations must pass owner-side review.
