# Release-copy checks — 2026-10-15

This historical record checked that preparing the distributed code did not
change the protected likelihood calculations or fixed numerical inputs.
"AST comparisons" below means comparisons of the Python code's parsed
structure, allowing the intended renaming; they are a software check, not a
test of the physical model. The later GitHub installation test is recorded in
[installation verification](input_installation_verification.md).

This is verification of the prepared copy, not completion of the full public
clean-clone/data-acquisition workflow or a scientific validation claim.

- A new checkout-local Python 3.12 virtual environment installed the pinned
  dependencies with pip `--require-hashes`.
- All 29 public runtime modules imported with PYTHONPATH unset and owner runtime
  namespaces/test modules absent. Public Python syntax and CLI startup passed.
- DR1 and DR2 preflight/input hash checks passed. 69 copied numerical/raw inputs
  matched the frozen original bytes and SHA-256 values, including all eight v3
  background files and four signal-energy tables.
- 19 protected scientific function/module AST comparisons matched after consistent
  name mapping. Other adaptations are described in `release_copy_changes.md`.
- The owner development checkout's 206 tests passed with no skips; its 20 golden
  language cases passed. These tests are not shipped and are not a full renamed-copy suite.
- Two real tasks went from READY to COMPLETED_WITH_WARNINGS in this isolated copy:
  NGC 1068 single-source and the three-source example's individual scan plus stack.
  Reports, configurations, CSVs, provenance, central reviews and run reviews were
  read; no failed review checks were present.

Both tasks used DR2 full14, spatial+energy, fitted ns and Gamma, default bounds
and frozen v3. The catalog used explicit uniform intrinsic weights. Warnings
record analytic local p-value approximation and missing empirical/catalog-global
calibration. No background trials were executed. No DR2 workbook/figure output
is asserted because this path does not generate them.

| Example | TS | ns | SkyLLH Gamma |
| --- | ---: | ---: | ---: |
| NGC 1068, RA 40.6696°, Dec -0.0133° | 22.9916185571 | 68.5674526052 | 3.0590345620 |
| Three-source uniform stack | 7.0044862836 | 18.8136506732 | 2.2906293703 |

These warning-bearing outputs are preliminary execution references, not calibrated
detections or unbiased parameter measurements. Small variations across numerical
platforms have not been characterized.

Raw inputs for these checks were copied from the owner's existing frozen local
inputs, not downloaded through public release instructions. Public download
publication, full clean-clone validation, time-dependent work and release metadata
remain pending. No commit, push or release tag was created.
