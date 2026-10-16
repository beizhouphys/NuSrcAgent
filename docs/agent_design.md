# Agent design

Natural-language request → repository skill → persistent task → deterministic
likelihood backend → artifact/scientific review → report.

`run_agent_wrap.py` is the sole public analysis CLI. `agent_core/` owns parameter
provenance, readiness, orchestration, recovery, reporting and review;
`analysis_backend/` owns callable scientific implementations. `sources.py`
holds source quantities/catalog definitions, not detector acceptance.

Exactly one source selects single-source analysis. DR2 catalogs expose
`stack`, `scan` or `scan_and_stack`; DR1 retains its existing scan+stack workflow.
The public catalog scan calls the supported single-source fit in input order.
The specialized paper benchmark is excluded from this copy.

Only dependency, output-generation and transient I/O failures may retry once
with the same request hash. Scientific parameters, membership, PDFs and bounds
are never changed automatically. Readiness and completion reviews remain
separate from the numerical optimizer.

Tasks and runs write only under the selected checkout's output directories.
Historical owner task records are not copied or migrated into the release.
