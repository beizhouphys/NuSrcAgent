# Fitting individual catalog sources and their combined emission

A source catalog is a table of candidate objects and their sky coordinates.
A scan asks whether each object has an individual neutrino excess; a stack asks
whether their combined emission is favored under a specified weighting model.
These are different statistical hypotheses, so their TS values need not agree.

## Choose the analysis

Use `stack` for a joint fit, `scan` for independent fits of every catalog row,
or `scan_and_stack` for both. A scan fits each source's own `ns` and, in the
default spatial+energy analysis, its own `Gamma`. A stack fits one total `ns`
and one common `Gamma` for the catalog.

`create-catalog --catalog-operation stack|scan|scan_and_stack` selects the
requested operation. Scan-only requires no intrinsic stacking weights.
Stacking weights must identify the intended physical quantity or be explicitly
uniform/manual; a common unknown multiplicative unit cancels on normalization.
Intrinsic weights specify the relative source contributions assumed before
applying detector acceptance. Uniform intrinsic weights are equal model weights,
not equal expected detected event counts. If using a measured source quantity,
identify which column it is and what it represents; the software does not know
the physical meaning of an arbitrary numeric column.

## Read the source and stacking tables

The scan uses identical single-source LLH settings for each input source and
writes input-ordered `source_results.csv`. Per-source fit details are nested in
`report.yaml`, source review checks in `review.json`, with run-level input and
configuration provenance in `provenance.yaml`; separate per-source directories
are not required. `scan_and_stack` additionally writes `fit_results.csv` for the stack.
Both spatial+energy and spatial-only use the same supported DR2 backend.
The general scan reloads data per source; assess runtime before large scans.

Use `source_results.csv` for the individual-source results, and
`fit_results.csv` for the joint stack when requested. Open `report.md` and
`review.md` first for a readable account of the fit and its warnings. Provenance
means the saved record of data/code versions and settings used in that calculation.

## Significance and example inputs

Ordinary local p-values and significances are estimates: half-chi-square dof=2
for fitted Gamma and dof=1 for fixed Gamma. The source CSV records the method,
dof and estimate flag alongside each result. No empirical catalog
post-trial significance is produced. The excluded 3386-source reproduction
workflow's six stacks, signed fits and paper comparison products are not
implicitly invoked by this general scan.
A local p-value refers to one specified source hypothesis. Selecting the most
interesting source after scanning a catalog introduces a search over sources;
that search must also be repeated in the background trials used for a global
significance. A table of local approximations does not perform that calibration.

The [three-row example](../configs/examples/catalog_sources_example.csv)
contains public source coordinates and illustrative relative radio weights.
Use `--name-column name --ra-column ra_deg --dec-column dec_deg`.
The [quickstart](quickstart.md) gives a complete uniform-weight scan+stack
command and its observed numerical outputs; [column metadata](../configs/examples/README.md)
explains which values are illustrative.
The selected 3386-source radio-bright AGN CSVs are bundled in
`data_input/sources/`; use them with `--catalog`. The optional built-in reader
instead requires the original raw RFC file, which is not bundled. See the
[catalog notes](../data_input/sources/README.md) for columns, selection and attribution.
