# How an analysis is requested, run and checked

NuSrcAgent separates the assistant's interpretation of your request from the
numerical likelihood fit. The assistant helps specify sources, spectra and
weights; the Python analysis code evaluates the likelihood. The language model
does not generate the fitted numbers or change settings to obtain a nicer result.

## From a request to results

1. Specify a sky position or catalog, the data sample and the intended analysis.
   Ordinary-language requests are interpreted using the project's skill, a set
   of instructions supplied to the assistant. Terminal commands supply the same
   settings explicitly.
2. Save the request as a task: an analysis record with an identifier, its settings
   and any questions still requiring an answer. `READY` means required choices
   and input checks are complete, not that a fit has already been performed.
3. Run the likelihood calculation. The analysis saves the submitted settings,
   the settings actually used, input/code fingerprints and output tables.
4. Read the report and checks. `COMPLETED_WITH_WARNINGS` means the calculation
   finished with limitations to acknowledge; `FAILED` means its results must
   not be treated as valid. The automated checks are not scientific peer review.

## Which calculation is performed?

Exactly one source selects single-source analysis. DR2 catalogs expose
`stack`, `scan` or `scan_and_stack`; DR1 retains its existing scan+stack workflow.
The public catalog scan calls the supported single-source fit in input order.
The specialized paper benchmark is excluded from this copy.

The [worked examples](quickstart.md) show the actual commands and output files.
Scientific definitions and limitations are in
[analysis settings](release_scientific_baseline.md) and
[scientific status](scientific_status.md).

## If a calculation fails

Only dependency, output-generation and transient I/O failures may retry once
with the same request hash. Scientific parameters, membership, PDFs and bounds
are never changed automatically. Readiness and completion reviews remain
separate from the numerical optimizer.

Tasks and runs write only under the selected checkout's output directories.
Historical owner task records are not copied or migrated into the release.

## For readers looking at the code

`run_agent_wrap.py` is the single Python command-line interface.
`agent_core/` saves requests/settings, runs analyses and prepares/checks reports.
`analysis_backend/` contains the likelihood and PDF calculations. `sources.py`
defines catalogs and intrinsic source quantities, not detector acceptance.
You do not need to understand these modules to run the examples.
