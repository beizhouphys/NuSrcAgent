# DR2 catalog workflow

`create-catalog --catalog-operation stack|scan|scan_and_stack` selects the
requested operation. Scan-only requires no intrinsic stacking weights.
Stacking weights must identify the intended physical quantity or be explicitly
uniform/manual; a common unknown multiplicative unit cancels on normalization.

The scan uses identical single-source LLH settings for each input source and
writes input-ordered `source_results.csv`. Per-source fit details are nested in
`report.yaml`, source review checks in `review.json`, with run-level input and
configuration provenance in `provenance.yaml`; separate per-source directories
are not required. `scan_and_stack` additionally writes `fit_results.csv` for the stack.
Both spatial+energy and spatial-only use the same supported DR2 backend.
The general scan reloads data per source; assess runtime before large scans.

Ordinary local p-values are analytic approximations. No empirical catalog
post-trial significance is produced. The excluded 3386-source reproduction
workflow's six stacks, signed fits and paper comparison products are not
implicitly invoked by this general scan.

The [three-row example](../configs/examples/catalog_sources_example.csv)
contains public source coordinates and illustrative relative radio weights.
Use `--name-column name --ra-column ra_deg --dec-column dec_deg`.
The [quickstart](quickstart.md) gives a complete uniform-weight scan+stack
command and its observed numerical outputs; [column metadata](../configs/examples/README.md)
explains which values are illustrative.
The optional built-in RFC catalog loader requires an external catalog that is
not bundled; its source/redistribution documentation remains pending.
