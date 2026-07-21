# Agent Wrapper Release Checklist

## Implemented

- Persistent task schema and auditable parameter provenance.
- Source-count-based workflow selection.
- User confirmation gate for gamma and weighting choices.
- Catalog inspection before execution.
- Explicit task states and interrupted-task resume command.
- Error taxonomy, identical-request safe retry, and retry audit.
- Machine-enforced pass/warning/fail completion gate.
- Codex Skill integration and deterministic CLI.
- Unit tests and multilingual language-adapter evaluation corpus.
- Architecture, behavior, usage, and evaluation documentation.
- Private-alpha repository metadata, pinned Python environment, data manifest, setup verifier, and collaboration guide.

## Required before an external release announcement

- Choose and add a public-release software license; the private alpha currently grants no open-source license.
- Add author names, affiliations, repository URL, version, and preferred citation.
- Run the language-adapter suite in independent fresh Codex sessions and publish the raw predictions.
- Run an external-user usability test and record failure cases.
- Decide whether input catalogs and generated runs may be redistributed.
- Complete the separate LLH scientific-validation work before describing scientific results as publication-ready.

## Additional requirements for a hosted ChatGPT or web service

- Authentication, per-user data isolation, upload limits, quotas, timeouts, cancellation, privacy policy, and data-retention policy.
- A pinned server environment and worker queue.
- Operational logging without leaking private catalog content.
